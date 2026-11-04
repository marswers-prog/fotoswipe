import Foundation
import Photos
import SwiftUI

/// A cancellable, bounded-memory read; PhotoKit callbacks are synchronized here.
private final class ResourceReadOperation: @unchecked Sendable {
    private let lock = NSLock()
    private var digest = StreamingResourceDigest()
    private var continuation: CheckedContinuation<ResourceFingerprint, Error>?
    private var requestID: PHAssetResourceDataRequestID?
    private var finished = false
    private var cancelled = false
    private var file: FileHandle?
    private let role: Int
    private let uniformType: String

    init(resource: PHAssetResource, destination: URL?) throws {
        role = resource.type.rawValue
        uniformType = resource.uniformTypeIdentifier
        if let destination {
            guard FileManager.default.createFile(atPath: destination.path, contents: nil) else { throw DuplicateIssue.unreadable }
            file = try FileHandle(forWritingTo: destination)
        }
    }

    func start(_ resource: PHAssetResource, network: Bool, continuation: CheckedContinuation<ResourceFingerprint, Error>) {
        lock.lock()
        if finished || cancelled {
            lock.unlock()
            continuation.resume(throwing: CancellationError())
            return
        }
        self.continuation = continuation
        lock.unlock()
        let options = PHAssetResourceRequestOptions()
        options.isNetworkAccessAllowed = network
        let id = PHAssetResourceManager.default().requestData(for: resource, options: options) { [self] data in
            lock.lock()
            guard !finished else { lock.unlock(); return }
            var ioError: Error?
            do {
                try file?.write(contentsOf: data)
                digest.update(data)
            } catch { ioError = error }
            lock.unlock()
            if let ioError {
                finish(ioError)
                cancelRequest()
            }
        } completionHandler: { [self] error in finish(error) }
        lock.lock()
        requestID = id
        let shouldCancel = cancelled
        lock.unlock()
        if shouldCancel { PHAssetResourceManager.default().cancelDataRequest(id) }
    }

    func cancel() {
        lock.lock(); cancelled = true; lock.unlock()
        finish(CancellationError())
        cancelRequest()
    }

    private func cancelRequest() {
        lock.lock(); let id = requestID; lock.unlock()
        if let id { PHAssetResourceManager.default().cancelDataRequest(id) }
    }

    private func finish(_ error: Error?) {
        lock.lock()
        guard !finished else { lock.unlock(); return }
        finished = true
        let callback = continuation
        continuation = nil
        let output = file
        file = nil
        var result: Result<ResourceFingerprint, Error>
        if let error { result = .failure(error) }
        else { result = .success(digest.fingerprint(role: role, uniformType: uniformType)) }
        lock.unlock()
        do { try output?.close() } catch { result = .failure(error) }
        callback?.resume(with: result)
    }

    deinit { try? file?.close() }
}

private struct HashedPhotoResource {
    let resource: PHAssetResource
    let fingerprint: ResourceFingerprint
}

private struct PhotoProof {
    let asset: PHAsset
    let resources: [HashedPhotoResource]
    var signature: ExactDuplicateSignature {
        ExactDuplicateSignature(width: asset.pixelWidth, height: asset.pixelHeight,
                                subtype: asset.mediaSubtypes.rawValue, resources: resources.map(\.fingerprint))
    }
}

struct ExactDuplicateGroup: Identifiable {
    let id = UUID().uuidString
    let members: [PHAsset]
    let signature: ExactDuplicateSignature
}

private struct DuplicateCandidateKey: Hashable {
    let width: Int
    let height: Int
    let subtype: UInt
    let roles: [Int]
}

private enum DuplicateWorker {
    static func read(_ resource: PHAssetResource, network: Bool, destination: URL? = nil) async throws -> ResourceFingerprint {
        try Task.checkCancellation()
        let operation = try ResourceReadOperation(resource: resource, destination: destination)
        return try await withTaskCancellationHandler(operation: {
            try await withCheckedThrowingContinuation { continuation in
                operation.start(resource, network: network, continuation: continuation)
            }
        }, onCancel: { operation.cancel() })
    }

    static func proof(_ asset: PHAsset, network: Bool) async throws -> PhotoProof {
        try Task.checkCancellation()
        guard asset.mediaType == .image, asset.burstIdentifier == nil else { throw DuplicateIssue.unreadable }
        let resources = PHAssetResource.assetResources(for: asset)
        guard !resources.isEmpty, resources.contains(where: { $0.type == .photo }) else { throw DuplicateIssue.unreadable }
        var parts: [HashedPhotoResource] = []
        for resource in resources {
            parts.append(HashedPhotoResource(resource: resource, fingerprint: try await read(resource, network: network)))
        }
        parts.sort {
            let a = $0.fingerprint, b = $1.fingerprint
            return (a.role, a.uniformType, a.byteCount, a.sha256) < (b.role, b.uniformType, b.byteCount, b.sha256)
        }
        return PhotoProof(asset: asset, resources: parts)
    }

    static func equalBytes(_ first: PhotoProof, _ second: PhotoProof, network: Bool) async throws -> Bool {
        guard first.signature == second.signature else { return false }
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("FotoSwipe-compare-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let a = directory.appendingPathComponent("first"), b = directory.appendingPathComponent("second")
        for (left, right) in zip(first.resources, second.resources) {
            try Task.checkCancellation()
            let leftNow = try await read(left.resource, network: network, destination: a)
            let rightNow = try await read(right.resource, network: network, destination: b)
            guard leftNow == left.fingerprint, rightNow == right.fingerprint,
                  ExactFileComparison.equal(a, b) else { return false }
            try FileManager.default.removeItem(at: a)
            try FileManager.default.removeItem(at: b)
        }
        return true
    }

    static func validate(_ groups: [ExactDuplicateGroup], plan: DuplicateDeletionPlan, network: Bool) async throws -> [PHAsset] {
        let ids = Array(plan.deleteIDs.union(plan.keepIDs))
        let fetch = PHAsset.fetchAssets(withLocalIdentifiers: ids, options: nil)
        var current: [String: PHAsset] = [:]
        fetch.enumerateObjects { asset, _, _ in current[asset.localIdentifier] = asset }
        guard current.count == ids.count else { throw DuplicateIssue.changed }
        for group in groups {
            try Task.checkCancellation()
            guard let keeperID = group.members.map(\.localIdentifier).first(where: { plan.keepIDs.contains($0) }),
                  let keeper = current[keeperID] else { throw DuplicateIssue.invalidSelection }
            let first = try await proof(keeper, network: network)
            guard first.signature == group.signature else { throw DuplicateIssue.changed }
            for member in group.members where member.localIdentifier != keeperID {
                guard let asset = current[member.localIdentifier] else { throw DuplicateIssue.changed }
                let candidate = try await proof(asset, network: network)
                guard candidate.signature == group.signature,
                      try await equalBytes(first, candidate, network: network) else { throw DuplicateIssue.changed }
            }
        }
        return plan.deleteIDs.compactMap { current[$0] }
    }

    static func scan(network: Bool, progress: @escaping @Sendable (Int, Int, String, Int) async -> Void) async throws -> [ExactDuplicateGroup] {
        let options = PHFetchOptions()
        options.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: true)]
        let fetch = PHAsset.fetchAssets(with: .image, options: options)
        var buckets: [DuplicateCandidateKey: [PHAsset]] = [:]
        var skipped = 0
        for index in 0..<fetch.count {
            try Task.checkCancellation()
            let asset = fetch.object(at: index)
            let resources = PHAssetResource.assetResources(for: asset)
            if asset.burstIdentifier != nil || resources.isEmpty || !resources.contains(where: { $0.type == .photo }) {
                skipped += 1; continue
            }
            let key = DuplicateCandidateKey(width: asset.pixelWidth, height: asset.pixelHeight,
                                            subtype: asset.mediaSubtypes.rawValue, roles: resources.map { $0.type.rawValue }.sorted())
            buckets[key, default: []].append(asset)
        }
        let candidates = buckets.values.filter { $0.count > 1 }.flatMap { $0 }
            .sorted { ($0.creationDate ?? .distantPast) < ($1.creationDate ?? .distantPast) }
        await progress(0, candidates.count, "\(fetch.count) Fotos gefunden. Vollständiger Dateivergleich …", skipped)
        var hashed: [ExactDuplicateSignature: [PhotoProof]] = [:]
        for (index, asset) in candidates.enumerated() {
            try Task.checkCancellation()
            do {
                let value = try await proof(asset, network: network)
                hashed[value.signature, default: []].append(value)
            } catch is CancellationError { throw CancellationError() }
            catch { skipped += 1 }
            await progress(index + 1, candidates.count, "\(index + 1) von \(candidates.count) möglichen Kandidaten geprüft", skipped)
        }
        var groups: [ExactDuplicateGroup] = []
        let matches = hashed.values.filter { $0.count > 1 }
        for (index, values) in matches.enumerated() {
            try Task.checkCancellation()
            await progress(index, matches.count, "Dateien bytegenau vergleichen: Gruppe \(index + 1) von \(matches.count)", skipped)
            guard let first = values.first else { continue }
            var confirmed: [PHAsset] = [first.asset]
            for candidate in values.dropFirst() {
                do {
                    if try await equalBytes(first, candidate, network: network) { confirmed.append(candidate.asset) }
                    else { skipped += 1 }
                } catch is CancellationError { throw CancellationError() }
                catch { skipped += 1 }
            }
            if confirmed.count > 1 {
                // Prefer an existing favorite, then the older entry, as the default keeper.
                confirmed.sort {
                    if $0.isFavorite != $1.isFavorite { return $0.isFavorite }
                    return ($0.creationDate ?? .distantPast) < ($1.creationDate ?? .distantPast)
                }
                groups.append(ExactDuplicateGroup(members: confirmed, signature: first.signature))
            }
        }
        await progress(candidates.count, candidates.count, "\(groups.count) Gruppen mit exakt gleichen Dateien gefunden", skipped)
        return groups.sorted { ($0.members.first?.creationDate ?? .distantPast) < ($1.members.first?.creationDate ?? .distantPast) }
    }
}

@MainActor
final class ExactDuplicateScanner: ObservableObject {
    @Published private(set) var groups: [ExactDuplicateGroup] = []
    @Published var keepers: [String: String] = [:]
    @Published var selectedGroups = Set<String>()
    @Published private(set) var scanning = false
    @Published private(set) var deleting = false
    @Published private(set) var completed = 0
    @Published private(set) var total = 0
    @Published private(set) var skipped = 0
    @Published private(set) var info = "Bereit für die Suche."
    @Published var networkAllowed = true
    private var task: Task<Void, Never>?
    private var generation = UUID()
    private var scannedRevision = 0

    var selectionCount: Int { (try? makePlan().deleteIDs.count) ?? 0 }

    private func makePlan() throws -> DuplicateDeletionPlan {
        try DuplicateDeletionPlan(choices: groups.map {
            DuplicateChoice(members: $0.members.map(\.localIdentifier), keeper: keepers[$0.id] ?? "", selected: selectedGroups.contains($0.id))
        })
    }

    func start(revision: Int) {
        cancel()
        let id = UUID()
        generation = id; scannedRevision = revision
        groups = []; keepers = [:]; selectedGroups = []
        scanning = true; completed = 0; total = 0; skipped = 0
        info = "Fotos werden erfasst …"
        let network = networkAllowed
        task = Task { [weak self] in
            do {
                let result = try await DuplicateWorker.scan(network: network) { [weak self] done, count, text, skipped in
                    await self?.update(id: id, done: done, count: count, text: text, skipped: skipped)
                }
                guard let self, self.generation == id else { return }
                self.groups = result
                self.keepers = Dictionary(uniqueKeysWithValues: result.compactMap { group in
                    group.members.first.map { (group.id, $0.localIdentifier) }
                })
                self.scanning = false
            } catch {
                guard let self, self.generation == id else { return }
                self.scanning = false
                self.info = error is CancellationError ? "Suche abgebrochen. Es wurde nichts verändert." : error.localizedDescription
            }
        }
    }

    private func update(id: UUID, done: Int, count: Int, text: String, skipped: Int) {
        guard generation == id else { return }
        completed = done; total = count; info = text; self.skipped = skipped
    }

    func cancel() {
        task?.cancel(); task = nil
        generation = UUID()
        if scanning { scanning = false; info = "Suche abgebrochen. Es wurde nichts verändert." }
    }

    func libraryChanged() {
        guard !deleting else { return }
        cancel()
        groups = []; keepers = [:]; selectedGroups = []
        info = "Die Fotomediathek hat sich geändert. Bitte erneut suchen."
    }

    func deleteSelected(using store: PhotoStore) {
        guard !scanning, !deleting, !store.busy, selectionCount > 0 else { return }
        do {
            let plan = try makePlan()
            let selected = groups.filter { selectedGroups.contains($0.id) }
            let revision = scannedRevision
            let network = networkAllowed
            deleting = true; info = "Auswahl wird vor dem Löschen erneut geprüft …"
            task = Task { [weak self] in
                let success = await store.deleteExactDuplicates(plan, expectedRevision: revision) {
                    try await DuplicateWorker.validate(selected, plan: plan, network: network)
                }
                guard let self else { return }
                self.deleting = false
                self.info = store.status
                if success {
                    let removed = Set(selected.map(\.id))
                    self.groups.removeAll { removed.contains($0.id) }
                    self.selectedGroups.subtract(removed)
                    self.scannedRevision = store.libraryRevision
                }
            }
        } catch { info = error.localizedDescription }
    }
}
