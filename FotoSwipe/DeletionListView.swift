import SwiftUI
import Photos

private struct PendingPhotoSelection: Identifiable {
    let asset: PHAsset
    var id: String { asset.localIdentifier }
}

struct DeletionListView: View {
    @ObservedObject var store: PhotoStore
    @Environment(\.dismiss) private var dismiss
    @State private var selection: PendingPhotoSelection?
    @State private var zoomSelection: PhotoZoomSelection?

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Text("Hier sind Fotos nur vorgemerkt. Tippe auf ein Foto, um es groß anzusehen. Mit „Behalten“ nimmst du es aus der Löschliste.")
                        .font(.subheadline)
                    if !store.status.isEmpty {
                        Text(store.status).font(.footnote).foregroundStyle(.secondary)
                    }
                }
                if store.pendingCount == 0 {
                    Section {
                        Label("Deine Löschliste ist leer", systemImage: "checkmark.circle")
                    }
                } else {
                    Section("\(store.pendingAssets.count) verfügbare Fotos") {
                        ForEach(store.pendingAssets, id: \.localIdentifier) { asset in
                            HStack(spacing: 12) {
                                Button {
                                    selection = PendingPhotoSelection(asset: asset)
                                } label: {
                                    HStack(spacing: 12) {
                                        AssetPreview(asset: asset, thumbnail: true)
                                            .frame(width: 72, height: 82).clipped()
                                            .clipShape(RoundedRectangle(cornerRadius: 8))
                                        VStack(alignment: .leading, spacing: 5) {
                                            Text(asset.creationDate?.formatted(date: .abbreviated, time: .omitted) ?? "Foto")
                                                .foregroundStyle(.primary)
                                            Text("Groß ansehen").font(.caption).foregroundStyle(.secondary)
                                        }
                                    }.contentShape(Rectangle())
                                }.buttonStyle(.plain)
                                Spacer(minLength: 4)
                                Button("Behalten") { store.keepPending(asset.localIdentifier) }
                                    .buttonStyle(.bordered).tint(.green)
                            }.disabled(store.busy)
                        }
                    }
                }
                if store.unavailablePendingCount > 0 {
                    Section {
                        Text("\(store.unavailablePendingCount) vorgemerkte Fotos sind derzeit nicht zugänglich oder wurden außerhalb der App gelöscht. Ihre Einträge bleiben gespeichert. Bei eingeschränktem Fotozugriff kannst du sie durch vollständigen Zugriff wieder verfügbar machen.")
                            .font(.footnote).foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Löschliste (\(store.pendingCount))")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Fertig") { dismiss() }.disabled(store.busy)
                }
            }
            .safeAreaInset(edge: .bottom) {
                VStack(spacing: 8) {
                    Button(role: .destructive) {
                        Task { await store.deletePending() }
                    } label: {
                        HStack {
                            if store.busy { ProgressView() }
                            Image(systemName: "trash")
                            Text("\(store.pendingAssets.count) Fotos jetzt löschen")
                        }.frame(maxWidth: .infinity).padding(.vertical, 6)
                    }.buttonStyle(.borderedProminent).tint(.red)
                        .disabled(store.busy || store.pendingAssets.isEmpty)
                    Text("iOS fragt einmal für diese Fotos nach. Erst nach deiner Bestätigung werden sie gelöscht.")
                        .font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
                }.padding().background(.regularMaterial)
            }
            .sheet(item: $selection) { item in
                NavigationStack {
                    VStack(spacing: 12) {
                        AssetPreview(asset: item.asset, thumbnail: false)
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                            .contentShape(Rectangle())
                            .onTapGesture {
                                zoomSelection = PhotoZoomSelection(asset: item.asset, preview: nil)
                            }
                        Text("Bild antippen zum Zoomen").font(.caption).foregroundStyle(.secondary)
                        Button("Dieses Foto behalten") {
                            store.keepPending(item.id)
                            selection = nil
                        }.buttonStyle(.borderedProminent).tint(.green).padding(.bottom)
                    }.padding(.horizontal)
                    .fullScreenCover(item: $zoomSelection) { selected in
                        PhotoZoomView(asset: selected.asset, preview: selected.preview)
                    }
                    .navigationTitle("Vorgemerktes Foto")
                    .navigationBarTitleDisplayMode(.inline)
                    .toolbar {
                        ToolbarItem(placement: .confirmationAction) {
                            Button("Schließen") { selection = nil }
                        }
                    }
                }
            }
            .alert("FotoSwipe", isPresented: Binding(get: { store.message != nil }, set: { if !$0 { store.message = nil } })) {
                Button("OK") { store.message = nil }
            } message: { Text(store.message ?? "") }
        }.interactiveDismissDisabled(store.busy)
    }
}

struct AssetPreview: View {
    let asset: PHAsset
    let thumbnail: Bool
    @State private var image: UIImage?
    @State private var failed = false
    @State private var token = UUID()
    @State private var requestID: PHImageRequestID = PHInvalidImageRequestID

    var body: some View {
        ZStack {
            Color.gray.opacity(0.12)
            if let image {
                Image(uiImage: image).resizable().scaledToFit()
            } else if failed {
                VStack(spacing: 8) {
                    Image(systemName: "icloud.slash")
                    if !thumbnail {
                        Text("Foto konnte nicht geladen werden.")
                        Button("Erneut laden") { load() }
                    }
                }.font(.footnote).padding(8)
            } else { ProgressView() }
        }
        .onAppear { load() }
        .onChange(of: asset.localIdentifier) { _, _ in load() }
        .onDisappear {
            token = UUID()
            PHImageManager.default().cancelImageRequest(requestID)
        }
    }

    private func load() {
        PHImageManager.default().cancelImageRequest(requestID)
        let generation = UUID()
        token = generation
        image = nil; failed = false
        let options = PHImageRequestOptions()
        options.isNetworkAccessAllowed = true
        options.deliveryMode = .highQualityFormat
        options.resizeMode = .fast
        let size = thumbnail ? CGSize(width: 180, height: 220) : CGSize(width: 1600, height: 2200)
        requestID = PHImageManager.default().requestImage(for: asset, targetSize: size, contentMode: .aspectFit, options: options) { result, info in
            let cancelled = (info?[PHImageCancelledKey] as? Bool) == true
            Task { @MainActor in
                guard token == generation, !cancelled else { return }
                image = result
                failed = result == nil
            }
        }
    }
}
