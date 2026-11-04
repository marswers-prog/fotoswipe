import SwiftUI
import Photos

struct ExactDuplicatesView: View {
    @ObservedObject var store: PhotoStore
    @StateObject private var scanner = ExactDuplicateScanner()
    @State private var zoom: PhotoZoomSelection?
    @State private var confirmDeletion = false

    var body: some View {
        List {
            Section {
                Text("Findet Fotos mit exakt gleichen Dateien. Live Photos und Bearbeitungsdaten werden mitverglichen. Pro Gruppe bleibt mindestens ein von dir gewähltes Foto erhalten.")
                    .font(.subheadline)
                Text("Es werden alle freigegebenen Fotos durchsucht, auch bereits bearbeitete. Deine Merkliste wird durch die Suche nicht zurückgesetzt.")
                    .font(.footnote).foregroundStyle(.secondary)
                if store.authorization == .limited {
                    Label("Es werden nur die für FotoSwipe freigegebenen Fotos durchsucht.", systemImage: "lock")
                        .font(.footnote)
                }
                Toggle("iCloud-Fotos bei Bedarf laden", isOn: $scanner.networkAllowed)
                    .disabled(scanner.scanning || scanner.deleting)
                Text("Für den Dateivergleich können größere Datenmengen geladen werden. Die Suche läuft auf deinem iPhone. Serienfotos und nicht lesbare Dateien werden ausgelassen.")
                    .font(.caption).foregroundStyle(.secondary)
                if scanner.scanning {
                    ProgressView(value: Double(scanner.completed), total: Double(max(scanner.total, 1)))
                    Button("Suche abbrechen", role: .cancel) { scanner.cancel() }
                } else {
                    Button(scanner.groups.isEmpty ? "Duplikate suchen" : "Erneut suchen", systemImage: "magnifyingglass") {
                        scanner.start(revision: store.libraryRevision)
                    }.disabled(store.busy || scanner.deleting || !store.accessible)
                }
                Text(scanner.info).font(.footnote).foregroundStyle(.secondary)
                if scanner.skipped > 0 {
                    Text("\(scanner.skipped) Fotos bzw. Vergleiche ausgelassen, etwa wegen Serienfotos, fehlender Dateien oder Ladefehlern.")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
            ForEach(scanner.groups) { group in
                duplicateSection(group)
            }
            if !scanner.groups.isEmpty {
                Section {
                    Text("Die Fotos können unterschiedlichen Alben zugeordnet sein. Die App übernimmt keine Albumzuordnungen von den gelöschten Kopien. Das gewählte Foto bleibt mit seinen eigenen Zuordnungen erhalten.")
                        .font(.footnote).foregroundStyle(.secondary)
                    Text("Bei erfolgreichem Löschen wird das behaltene Foto auch aus einer vorhandenen manuellen Löschliste genommen.")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle("Exakte Duplikate")
        .navigationBarTitleDisplayMode(.inline)
        .navigationBarBackButtonHidden(scanner.deleting)
        .safeAreaInset(edge: .bottom) {
            if !scanner.groups.isEmpty || scanner.deleting {
                VStack(spacing: 8) {
                    Button(role: .destructive) { confirmDeletion = true } label: {
                        HStack {
                            if scanner.deleting { ProgressView() }
                            Text(scanner.deleting ? "Dateien werden erneut geprüft …" : "\(scanner.selectionCount) Kopien löschen")
                        }.frame(maxWidth: .infinity).padding(.vertical, 6)
                    }.buttonStyle(.borderedProminent).tint(.red)
                        .disabled(scanner.selectionCount == 0 || scanner.scanning || store.busy || scanner.deleting)
                    Text("Nur ausgewählte Gruppen. iOS fragt zusätzlich nach deiner Bestätigung.")
                        .font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
                }.padding().background(.regularMaterial)
            }
        }
        .confirmationDialog("\(scanner.selectionCount) doppelte Fotos löschen?", isPresented: $confirmDeletion, titleVisibility: .visible) {
            Button("Ausgewählte Kopien löschen", role: .destructive) { scanner.deleteSelected(using: store) }
            Button("Abbrechen", role: .cancel) { }
        } message: {
            Text("Pro ausgewählter Gruppe bleibt das mit „Behalten“ markierte Foto erhalten. Die ausgewählten Kopien werden auch aus ihren Alben entfernt.")
        }
        .fullScreenCover(item: $zoom) { item in PhotoZoomView(asset: item.asset, preview: item.preview) }
        .onChange(of: store.libraryRevision) { _, _ in scanner.libraryChanged() }
        .onDisappear { scanner.cancel() }
        .alert("FotoSwipe", isPresented: Binding(get: { store.message != nil }, set: { if !$0 { store.message = nil } })) {
            Button("OK") { store.message = nil }
        } message: { Text(store.message ?? "") }
    }

    private func duplicateSection(_ group: ExactDuplicateGroup) -> some View {
        Section {
            Toggle("Zusätzliche Kopien auswählen", isOn: Binding(
                get: { scanner.selectedGroups.contains(group.id) },
                set: { if $0 { scanner.selectedGroups.insert(group.id) } else { scanner.selectedGroups.remove(group.id) } }
            ))
            ForEach(group.members, id: \.localIdentifier) { asset in
                duplicateRow(asset, group: group)
            }
        } header: {
            Text("\(group.members.count) identische Fotos · \(group.members.count - 1) zusätzliche Kopien")
        } footer: {
            Text("Tippe bei dem Foto, das bleiben soll, auf „Behalten“. Zum Vergrößern auf die Vorschau tippen.")
        }.disabled(scanner.scanning || scanner.deleting || store.busy)
    }

    private func duplicateRow(_ asset: PHAsset, group: ExactDuplicateGroup) -> some View {
        let kept = scanner.keepers[group.id] == asset.localIdentifier
        return HStack(spacing: 12) {
            Button {
                zoom = PhotoZoomSelection(asset: asset, preview: nil)
            } label: {
                AssetPreview(asset: asset, thumbnail: true)
                    .frame(width: 70, height: 82).clipped().clipShape(RoundedRectangle(cornerRadius: 8))
            }.buttonStyle(.plain).accessibilityLabel("Foto in Vollbild ansehen")
            VStack(alignment: .leading, spacing: 5) {
                Text(asset.creationDate?.formatted(date: .abbreviated, time: .shortened) ?? "Foto").font(.caption)
                if asset.isFavorite { Label("Favorit", systemImage: "heart.fill").font(.caption).foregroundStyle(.pink) }
                if kept {
                    Label("Bleibt erhalten", systemImage: "checkmark.circle.fill").font(.caption).foregroundStyle(.green)
                } else {
                    Text(scanner.selectedGroups.contains(group.id) ? "Zum Löschen ausgewählt" : "Zusätzliche Kopie")
                        .font(.caption).foregroundStyle(scanner.selectedGroups.contains(group.id) ? .red : .secondary)
                }
            }
            Spacer(minLength: 2)
            Button(kept ? "Behalten ✓" : "Behalten") { scanner.keepers[group.id] = asset.localIdentifier }
                .font(.caption.bold()).buttonStyle(.bordered).tint(kept ? .green : .gray)
        }
    }
}
