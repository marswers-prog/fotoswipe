import SwiftUI
import Photos
import PhotosUI
import UIKit

struct AlbumChoice: Identifiable {
    let id: String
    let title: String
}

enum SwipeAction { case keep, delete, up, down }

@MainActor
final class PhotoStore: NSObject, ObservableObject, PHPhotoLibraryChangeObserver {
    @Published var authorization = PHPhotoLibrary.authorizationStatus(for: .readWrite)
    @Published var current: PHAsset?
    @Published var image: UIImage?
    @Published var albums: [AlbumChoice] = []
    @Published var remaining = 0
    @Published var busy = false
    @Published var loading = false
    @Published var loadFailed = false
    @Published var message: String?
    @Published var status = "Dein nächstes Foto wartet."
    @Published var upID: String { didSet { defaults.set(upID, forKey: "upAlbum") } }
    @Published var downID: String { didSet { defaults.set(downID, forKey: "downAlbum") } }
    private let defaults = UserDefaults.standard
    private let manager = PHCachingImageManager()
    @Published private(set) var reviewState: ReviewState
    @Published private(set) var pendingAssets: [PHAsset] = []
    private var requestID: PHImageRequestID = PHInvalidImageRequestID
    private var loadToken = UUID()
    private var observing = false

    var accessible: Bool { authorization == .authorized || authorization == .limited }
    var canAct: Bool { current != nil && image != nil && !loading && !busy }
    var reviewedCount: Int { reviewState.reviewed.count }
    var pendingCount: Int { reviewState.pending.count }
    var unavailablePendingCount: Int { pendingCount - pendingAssets.count }

    override init() {
        let saved = UserDefaults.standard
        var restoreError: String?
        do {
            reviewState = try ReviewState(defaults: saved)
        } catch {
            reviewState = ReviewState(reviewed: Set(saved.stringArray(forKey: "reviewed") ?? []))
            restoreError = "Die Löschliste konnte nicht gelesen werden. Deine bisherige Merkliste bleibt erhalten. Es wurden keine Fotos gelöscht."
        }
        upID = saved.string(forKey: "upAlbum") ?? ""
        downID = saved.string(forKey: "downAlbum") ?? ""
        super.init()
        message = restoreError
    }

    func start() {
        if !observing {
            PHPhotoLibrary.shared().register(self)
            observing = true
        }
        refresh()
    }

    nonisolated func photoLibraryDidChange(_ changeInstance: PHChange) {
        Task { @MainActor [weak self] in self?.refresh() }
    }

    func requestAccess() {
        PHPhotoLibrary.requestAuthorization(for: .readWrite) { [weak self] _ in
            Task { @MainActor in self?.refresh() }
        }
    }

    func refresh() {
        guard !busy else { return }
        authorization = PHPhotoLibrary.authorizationStatus(for: .readWrite)
        guard accessible else {
            current = nil; image = nil; albums = []; pendingAssets = []; remaining = 0
            cancelImage(); return
        }
        refreshAlbums()
        refreshPendingAssets()
        let skipped = reviewState.reviewed.union(reviewState.pending)
        let options = PHFetchOptions()
        options.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: true)]
        let fetched = PHAsset.fetchAssets(with: .image, options: options)
        var first: PHAsset?
        var stillCurrent: PHAsset?
        var count = 0
        let currentID = current?.localIdentifier
        fetched.enumerateObjects { asset, _, _ in
            if !skipped.contains(asset.localIdentifier) {
                count += 1
                if first == nil { first = asset }
                if asset.localIdentifier == currentID { stillCurrent = asset }
            }
        }
        remaining = count
        let next = stillCurrent ?? first
        if next?.localIdentifier != current?.localIdentifier {
            current = next
            loadImage()
        } else if next == nil {
            cancelImage(); image = nil
        }
    }

    func refreshAlbums() {
        guard authorization == .authorized else { albums = []; return }
        let fetched = PHAssetCollection.fetchAssetCollections(with: .album, subtype: .albumRegular, options: nil)
        var choices: [AlbumChoice] = []
        fetched.enumerateObjects { album, _, _ in
            if album.canPerform(.addContent) {
                choices.append(AlbumChoice(id: album.localIdentifier, title: album.localizedTitle ?? "Album"))
            }
        }
        albums = choices.sorted { $0.title.localizedStandardCompare($1.title) == .orderedAscending }
    }

    func title(for id: String, fallback: String) -> String {
        albums.first(where: { $0.id == id })?.title ?? fallback
    }

    private func cancelImage() {
        loadToken = UUID()
        if requestID != PHInvalidImageRequestID { manager.cancelImageRequest(requestID) }
        requestID = PHInvalidImageRequestID
        loading = false
    }

    func loadImage() {
        cancelImage()
        image = nil; loadFailed = false
        guard let asset = current else { return }
        loading = true
        let token = loadToken
        let options = PHImageRequestOptions()
        options.isNetworkAccessAllowed = true
        options.deliveryMode = .highQualityFormat
        options.resizeMode = .fast
        let size = CGSize(width: 1600, height: 2200)
        requestID = manager.requestImage(for: asset, targetSize: size, contentMode: .aspectFit, options: options) { [weak self] photo, info in
            let cancelled = (info?[PHImageCancelledKey] as? Bool) == true
            let degraded = (info?[PHImageResultIsDegradedKey] as? Bool) == true
            Task { @MainActor in
                guard let self, self.loadToken == token, !cancelled else { return }
                if let photo { self.image = photo }
                if !degraded {
                    self.loading = false
                    self.loadFailed = photo == nil
                }
            }
        }
    }

    func act(_ action: SwipeAction) async {
        guard canAct, let asset = current else { return }
        if action == .keep {
            finish(asset, text: "Behalten")
            return
        }
        if action == .delete {
            var changed = reviewState
            changed.stageDeletion(asset.localIdentifier)
            guard saveState(changed) else { return }
            status = "Zum Löschen vorgemerkt – noch nicht gelöscht."
            UIImpactFeedbackGenerator(style: .light).impactOccurred()
            refresh()
            return
        }
        if action == .up || action == .down {
            guard authorization == .authorized else {
                message = "Für Alben bitte in den iPhone-Einstellungen vollständigen Fotozugriff erlauben."; return
            }
            let id = action == .up ? upID : downID
            guard !id.isEmpty,
                  let album = PHAssetCollection.fetchAssetCollections(withLocalIdentifiers: [id], options: nil).firstObject,
                  album.canPerform(.addContent) else {
                message = "Wähle zuerst in den Einstellungen ein verfügbares Album für diese Wischrichtung."; return
            }
            busy = true
            do {
                try await PHPhotoLibrary.shared().performChanges {
                    PHAssetCollectionChangeRequest(for: album)?.addAssets([asset] as NSArray)
                }
                finish(asset, text: "In „\(album.localizedTitle ?? "Album")“ abgelegt")
            } catch { report(error) }
            endOperation()
        }
    }

    private func finish(_ asset: PHAsset, text: String) {
        var changed = reviewState
        changed.markReviewed(asset.localIdentifier)
        guard saveState(changed) else { return }
        status = text
        UIImpactFeedbackGenerator(style: .light).impactOccurred()
        if !busy { refresh() }
    }

    private func saveState(_ changed: ReviewState) -> Bool {
        do {
            try changed.save(to: defaults)
            reviewState = changed
            return true
        } catch {
            message = "Dein Fortschritt konnte nicht gespeichert werden. Bitte versuche es erneut."
            return false
        }
    }

    private func refreshPendingAssets() {
        guard !reviewState.pending.isEmpty else { pendingAssets = []; return }
        let fetched = PHAsset.fetchAssets(withLocalIdentifiers: reviewState.pending, options: nil)
        var available: [String: PHAsset] = [:]
        fetched.enumerateObjects { asset, _, _ in available[asset.localIdentifier] = asset }
        pendingAssets = reviewState.pending.compactMap { available[$0] }
        // Missing / unshared identifiers remain saved; limited access isn't deletion.
    }

    func keepPending(_ id: String) {
        guard !busy, reviewState.pending.contains(id) else { return }
        var changed = reviewState
        changed.markReviewed(id)
        guard saveState(changed) else { return }
        status = "Foto behalten und aus der Löschliste genommen."
        refresh()
    }

    func deletePending() async {
        guard !busy, accessible, !pendingAssets.isEmpty else { return }
        let assets = pendingAssets
        let ids = Set(assets.map(\.localIdentifier))
        busy = true
        do {
            // Exactly one change request and one system confirmation for the batch.
            try await PHPhotoLibrary.shared().performChanges {
                PHAssetChangeRequest.deleteAssets(assets as NSArray)
            }
            var changed = reviewState
            changed.completeDeletion(ids)
            if saveState(changed) {
                status = "\(assets.count) Fotos gelöscht."
            }
        } catch {
            let ns = error as NSError
            if ns.domain == PHPhotosErrorDomain && ns.code == PHPhotosError.Code.userCancelled.rawValue {
                status = "Löschen abgebrochen – deine Löschliste bleibt gespeichert."
            } else {
                message = "Die Fotos konnten nicht gelöscht werden. Deine Löschliste bleibt gespeichert.\n\n\(error.localizedDescription)"
            }
        }
        endOperation()
    }

    private func endOperation() {
        busy = false
        refresh()
    }

    private func report(_ error: Error) {
        let ns = error as NSError
        if ns.domain == PHPhotosErrorDomain && ns.code == PHPhotosError.Code.userCancelled.rawValue {
            status = "Abgebrochen – das Foto bleibt unverändert."
        } else {
            message = "Die Änderung wurde nicht abgeschlossen. Das Foto bleibt zur Bearbeitung angezeigt.\n\n\(error.localizedDescription)"
        }
    }

    func createAlbum(name: String, forTop: Bool) async -> Bool {
        let name = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty, !busy else { return false }
        guard authorization == .authorized else {
            message = "Für Alben wird vollständiger Fotozugriff benötigt."; return false
        }
        if let existing = albums.first(where: { $0.title.compare(name, options: [.caseInsensitive, .diacriticInsensitive]) == .orderedSame }) {
            if forTop { upID = existing.id } else { downID = existing.id }
            return true
        }
        busy = true
        do {
            // Refresh after the committed creation; no identifier is assumed before success.
            try await PHPhotoLibrary.shared().performChanges {
                PHAssetCollectionChangeRequest.creationRequestForAssetCollection(withTitle: name)
            }
            refreshAlbums()
            guard let created = albums.first(where: { $0.title == name }) else {
                message = "Album angelegt. Bitte wähle es in der Liste aus."
                endOperation(); return false
            }
            if forTop { upID = created.id } else { downID = created.id }
            endOperation(); return true
        } catch {
            report(error); endOperation(); return false
        }
    }

    func restart() {
        guard !busy else { return }
        var changed = reviewState
        changed.resetReviewed()
        guard saveState(changed) else { return }
        status = "Neue Runde gestartet."
        refresh()
    }

    func openSettings() {
        guard let url = URL(string: UIApplication.openSettingsURLString) else { return }
        UIApplication.shared.open(url)
    }

    func chooseMorePhotos() {
        guard let scene = UIApplication.shared.connectedScenes.first(where: { $0.activationState == .foregroundActive }) as? UIWindowScene,
              var controller = scene.windows.first(where: { $0.isKeyWindow })?.rootViewController else { return }
        while let presented = controller.presentedViewController { controller = presented }
        PHPhotoLibrary.shared().presentLimitedLibraryPicker(from: controller) { [weak self] _ in
            Task { @MainActor in self?.refresh() }
        }
    }
}
