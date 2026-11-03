import SwiftUI
import Photos

struct ContentView: View {
    @StateObject private var store = PhotoStore()
    @Environment(\.scenePhase) private var scenePhase
    @State private var settings = false
    @State private var deletionList = false
    @State private var drag = CGSize.zero
    private let mint = Color(red: 0.55, green: 0.92, blue: 0.73)
    private let coral = Color(red: 1, green: 0.53, blue: 0.49)

    var body: some View {
        ZStack {
            Color(red: 0.055, green: 0.075, blue: 0.085).ignoresSafeArea()
            VStack(spacing: 16) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("FotoSwipe").font(.title.bold())
                        Text(store.accessible ? "\(store.remaining) Fotos übrig" : "Platz für die guten Erinnerungen.")
                            .font(.subheadline).foregroundStyle(.gray)
                    }
                    Spacer()
                    Button { deletionList = true } label: {
                        Label("\(store.pendingCount)", systemImage: "trash")
                            .font(.subheadline.bold()).padding(11)
                            .background(coral.opacity(0.12), in: Capsule())
                    }.accessibilityLabel("Löschliste, \(store.pendingCount) Fotos vorgemerkt")
                        .disabled(store.busy || !store.accessible)
                    Button { settings = true } label: {
                        Image(systemName: "slider.horizontal.3").font(.title3).padding(13)
                            .background(.white.opacity(0.08), in: Circle())
                    }.accessibilityLabel("Alben und Einstellungen").disabled(store.busy)
                }.padding(.horizontal, 22)
                if store.accessible { sortingView } else { accessView }
            }.padding(.top, 12).padding(.bottom, 8)
        }
        .preferredColorScheme(.dark)
        .sheet(isPresented: $settings) { SettingsView(store: store) }
        .sheet(isPresented: $deletionList) { DeletionListView(store: store) }
        .alert("FotoSwipe", isPresented: Binding(get: { store.message != nil }, set: { if !$0 { store.message = nil } })) {
            Button("OK") { store.message = nil }
        } message: { Text(store.message ?? "") }
        .onAppear { store.start() }
        .onChange(of: scenePhase) { _, value in if value == .active { store.refresh() } }
    }

    private var sortingView: some View {
        VStack(spacing: 12) {
            if store.authorization == .limited {
                Button("Nur freigegebene Fotos · Auswahl ändern") { store.chooseMorePhotos() }
                    .font(.caption).foregroundStyle(mint).disabled(store.busy)
            }
            edgeButton(store.title(for: store.upID, fallback: "Album oben wählen"), icon: "arrow.up", color: mint, action: .up)
                .padding(.horizontal, 38)
            GeometryReader { geo in
                HStack(spacing: 4) {
                    Button { perform(.keep) } label: {
                        VStack(spacing: 9) {
                            Image(systemName: "arrow.left")
                            Text("behalten").font(.caption2.bold()).rotationEffect(.degrees(-90))
                                .fixedSize().frame(width: 30, height: 78)
                        }.foregroundStyle(mint).frame(width: 38, height: geo.size.height)
                    }.disabled(!store.canAct).accessibilityLabel("Foto behalten")
                    photoCard
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .offset(drag)
                        .rotationEffect(.degrees(Double(drag.width / 28)))
                        .gesture(DragGesture(minimumDistance: 20)
                            .onChanged { value in if store.canAct { drag = value.translation } }
                            .onEnded { value in
                                let delta = value.translation
                                withAnimation(.spring(response: 0.3)) { drag = .zero }
                                guard store.canAct, max(abs(delta.width), abs(delta.height)) > 85 else { return }
                                if abs(delta.width) > abs(delta.height) {
                                    perform(delta.width < 0 ? .keep : .delete)
                                } else { perform(delta.height < 0 ? .up : .down) }
                            })
                    Button { perform(.delete) } label: {
                        VStack(spacing: 9) {
                            Image(systemName: "arrow.right")
                            Text("löschen").font(.caption2.bold()).rotationEffect(.degrees(90))
                                .fixedSize().frame(width: 30, height: 78)
                        }.foregroundStyle(coral).frame(width: 38, height: geo.size.height)
                    }.disabled(!store.canAct).accessibilityLabel("Foto zum Löschen vormerken")
                }
            }
            edgeButton(store.title(for: store.downID, fallback: "Album unten wählen"), icon: "arrow.down", color: mint, action: .down)
                .padding(.horizontal, 38)
            if store.pendingCount > 0 {
                Button {
                    deletionList = true
                } label: {
                    Label("Löschliste prüfen (\(store.pendingCount))", systemImage: "trash")
                        .font(.subheadline.bold()).frame(maxWidth: .infinity).padding(.vertical, 10)
                }.buttonStyle(.bordered).tint(coral).padding(.horizontal, 38)
                    .disabled(store.busy)
            }
            VStack(spacing: 5) {
                Text(store.status).font(.footnote).foregroundStyle(mint).lineLimit(2)
                Text("Wischen oder auf die Randbeschriftung tippen")
                    .font(.caption2).foregroundStyle(.gray)
            }.frame(minHeight: 38).padding(.horizontal)
        }
    }

    private var photoCard: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 24).fill(.white.opacity(0.045))
            if let image = store.image {
                Image(uiImage: image).resizable().scaledToFit().clipShape(RoundedRectangle(cornerRadius: 24))
                    .accessibilityLabel("Aktuelles Foto")
            } else if store.current == nil {
                VStack(spacing: 16) {
                    Image(systemName: "checkmark.circle").font(.system(size: 46)).foregroundStyle(mint)
                    Text("Alles durchgesehen").font(.title3.bold())
                    Text("Keine unbearbeiteten Fotos verfügbar. Neue Fotos erscheinen automatisch.")
                        .font(.subheadline).foregroundStyle(.gray).multilineTextAlignment(.center)
                    Button("Einstellungen öffnen") { settings = true }.foregroundStyle(mint)
                }.padding(20)
            } else if store.loadFailed {
                VStack(spacing: 15) {
                    Image(systemName: "icloud.slash").font(.largeTitle)
                    Text("Foto konnte nicht geladen werden.").multilineTextAlignment(.center)
                    Text("Bei iCloud-Fotos kann eine Internetverbindung nötig sein.").font(.caption).foregroundStyle(.gray)
                    Button("Erneut laden") { store.loadImage() }
                }.padding()
            }
            if store.loading || store.busy {
                ProgressView(store.busy ? "Änderung wird ausgeführt …" : "Foto wird geladen …")
                    .padding(18).background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
            }
            if let date = store.current?.creationDate, store.image != nil {
                VStack { Spacer(); Text(date.formatted(date: .abbreviated, time: .omitted))
                    .font(.caption).padding(.horizontal, 12).padding(.vertical, 7)
                    .background(.black.opacity(0.65), in: Capsule()).padding(.bottom, 12)
                }.allowsHitTesting(false)
            }
        }.clipped()
    }

    private func edgeButton(_ title: String, icon: String, color: Color, action: SwipeAction) -> some View {
        Button {
            if (action == .up ? store.upID : store.downID).isEmpty { settings = true }
            else { perform(action) }
        } label: {
            HStack(spacing: 8) {
                Image(systemName: icon)
                Text(title).lineLimit(1)
                Image(systemName: "folder")
            }.font(.subheadline.weight(.semibold)).foregroundStyle(color)
                .frame(maxWidth: .infinity).padding(.vertical, 13)
                .background(color.opacity(0.08), in: Capsule())
        }.disabled(store.busy || (store.current != nil && !store.canAct))
    }

    private var accessView: some View {
        VStack(spacing: 22) {
            Spacer()
            Image(systemName: "photo.stack").font(.system(size: 64)).foregroundStyle(mint)
            Text("Ein Foto. Eine Entscheidung.").font(.title2.bold()).multilineTextAlignment(.center)
            Text("Links behalten, rechts zum Löschen vormerken. Nach oben oder unten in deine zwei Lieblingsalben einsortieren.")
                .foregroundStyle(.gray).multilineTextAlignment(.center)
            Text("Deine Fotos werden nicht an einen eigenen Server übertragen. iCloud-Fotos werden bei Bedarf von Apple geladen.")
                .font(.caption).foregroundStyle(.gray).multilineTextAlignment(.center)
            if store.authorization == .notDetermined {
                Button("Fotozugriff erlauben") { store.requestAccess() }.buttonStyle(.borderedProminent).tint(mint).foregroundStyle(.black)
            } else {
                Text("Bitte erlaube den Fotozugriff in den iPhone-Einstellungen. Für Alben ist vollständiger Zugriff nötig.")
                    .font(.subheadline).multilineTextAlignment(.center)
                Button("iPhone-Einstellungen öffnen") { store.openSettings() }.buttonStyle(.borderedProminent).tint(mint)
            }
            Spacer()
        }.padding(28)
    }

    private func perform(_ action: SwipeAction) {
        Task { await store.act(action) }
    }
}

struct SettingsView: View {
    @ObservedObject var store: PhotoStore
    @Environment(\.dismiss) private var dismiss
    @State private var topName = ""
    @State private var bottomName = ""
    @State private var confirmRestart = false

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text("Wähle zwei Alben oder lege sie mit eigenen Namen an. Einsortierte Fotos bleiben auch in der Mediathek und in anderen Alben erhalten.")
                }
                if store.authorization == .authorized {
                    albumSection(top: true)
                    albumSection(top: false)
                } else {
                    Section("Fotozugriff") {
                        Text("Zum Anlegen und Auswählen von Alben bitte vollständigen Fotozugriff erlauben.")
                        Button("iPhone-Einstellungen öffnen") { store.openSettings() }
                    }
                }
                Section {
                    LabeledContent("Bereits bearbeitet", value: "\(store.reviewedCount)")
                    Button("Alle vorhandenen Fotos erneut durchsehen", role: .destructive) { confirmRestart = true }
                } header: {
                    Text("Fortschritt")
                } footer: {
                    Text("Setzt nur die Merkliste zurück. Fotos und Albumzuordnungen werden dadurch nicht verändert. Deine Löschliste bleibt gespeichert.")
                }
                Section("So funktioniert’s") {
                    Label("Links: behalten", systemImage: "arrow.left")
                    Label("Rechts: zum Löschen vormerken", systemImage: "arrow.right")
                    Label("Oben: im oberen Album behalten", systemImage: "arrow.up")
                    Label("Unten: im unteren Album behalten", systemImage: "arrow.down")
                    Text("Rechts wischen speichert das Foto in deiner Löschliste und zeigt sofort das nächste. Öffne die Liste über das Papierkorb-Symbol. Dort kannst du Fotos behalten oder alle verfügbaren vorgemerkten Fotos mit einer gemeinsamen iOS-Bestätigung löschen. Bei Abbruch bleibt die Liste gespeichert. Gelöschte Fotos können auch aus iCloud und von synchronisierten Geräten verschwinden.")
                        .font(.footnote).foregroundStyle(.secondary)
                    Text("Live Photos werden als Standbild angezeigt, aber als ganzes Foto einsortiert oder gelöscht. Videos sind in dieser Version ausgeblendet.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
            }
            .disabled(store.busy)
            .navigationTitle("Deine Alben")
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Fertig") { dismiss() }.disabled(store.busy) } }
            .confirmationDialog("Merkliste zurücksetzen?", isPresented: $confirmRestart, titleVisibility: .visible) {
                Button("Erneut durchsehen", role: .destructive) { store.restart() }
            }
            .alert("FotoSwipe", isPresented: Binding(get: { store.message != nil }, set: { if !$0 { store.message = nil } })) {
                Button("OK") { store.message = nil }
            } message: { Text(store.message ?? "") }
        }.interactiveDismissDisabled(store.busy)
    }

    private func albumSection(top: Bool) -> some View {
        Section(top ? "↑ Nach oben wischen" : "↓ Nach unten wischen") {
            Picker("Zielalbum", selection: top ? $store.upID : $store.downID) {
                Text("Bitte wählen").tag("")
                let selected = top ? store.upID : store.downID
                if !selected.isEmpty && !store.albums.contains(where: { $0.id == selected }) {
                    Text("Album nicht verfügbar").tag(selected)
                }
                ForEach(store.albums) { album in Text(album.title).tag(album.id) }
            }
            TextField("Name für neues Album", text: top ? $topName : $bottomName)
                .textInputAutocapitalization(.sentences)
            Button("Album anlegen und zuweisen") {
                Task {
                    if await store.createAlbum(name: top ? topName : bottomName, forTop: top) {
                        if top { topName = "" } else { bottomName = "" }
                    }
                }
            }.disabled((top ? topName : bottomName).trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        }
    }
}
