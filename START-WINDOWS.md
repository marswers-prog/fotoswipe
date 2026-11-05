# FotoSwipe kostenlos auf dein iPhone bringen

Du brauchst deinen Windows-PC, dein iPhone (iOS 17 oder neuer), ein USB-Kabel, einen kostenlosen GitHub-Account und einen kostenlosen Apple Account. Eine kostenpflichtige Apple-Developer-Mitgliedschaft oder ein eigener Mac ist für diesen Weg nicht vorgesehen. Die App wird nicht im App Store veröffentlicht.

Für dieses Repository wurde bereits eine IPA erfolgreich gebaut: [FotoSwipe-iPhone herunterladen](https://github.com/marswers-prog/fotoswipe/actions/runs/41970804630/artifacts/13389229182). Bei GitHub anmelden, die heruntergeladene ZIP entpacken und `FotoSwipe.ipa` entnehmen. Danach kannst du direkt bei Abschnitt 2 fortfahren. Dieses Artefakt wird am 12. November 2026 entfernt; über Abschnitt 1 lässt sich bei Bedarf eine neue IPA bauen. Die persönliche Signierung und der Funktionstest auf deinem iPhone stehen noch aus. Wenn FotoSwipe schon installiert ist, verwende die [Update-Anleitung](UPDATE-1.2.md), damit der bisherige Fortschritt erhalten bleibt.

## 1. Auf GitHub bauen

Wenn ChatGPT mit deinem GitHub-Account verbunden ist, können wir das Repository gemeinsam einrichten. Alternativ geht es im Browser:

1. Melde dich unter https://github.com an bzw. erstelle einen kostenlosen Account.
2. Erstelle über **New repository** ein neues Repository, zum Beispiel `fotoswipe`. Wähle **Public**. Füge beim Erstellen eine README hinzu, damit das Repository einen Hauptzweig hat. Der vorbereitete Workflow baut auf dem Zweig `main`; später ist er auch manuell startbar.
3. Entpacke die heruntergeladene Projekt-ZIP unter Windows über **Alle extrahieren**.
4. Öffne den entpackten Ordner `FotoSwipe`. Darin müssen unter anderem die Ordner `.github`, `scripts`, `FotoSwipe` und `FotoSwipe.xcodeproj` liegen.
5. Öffne auf GitHub das Repository und **Add file → Upload files**. Ziehe den **Inhalt** dieses entpackten Ordners auf die Uploadfläche, einschließlich `.github`. Nicht die ZIP-Datei und nicht den äußeren Ordner hochladen. Änderungen mit **Commit changes** speichern. GitHub soll die Projektdateien direkt im Repository-Hauptverzeichnis finden.
6. Prüfe im Tab **Code**, ob `.github/workflows/build-ios.yml` vorhanden ist. Ohne diese Datei erscheint der Build nicht. Der Ordner mit einem führenden Punkt kann beim Hochladen übergangen werden; dann die Datei über **Add file → Create new file** mit exakt diesem Pfad und dem Inhalt der mitgelieferten YAML-Datei anlegen.
7. Öffne **Actions → FotoSwipe fuer iPhone bauen**. Falls GitHub danach fragt, aktiviere Actions für dieses Repository. Der Upload auf `main` startet den Build normalerweise selbst. Alternativ **Run workflow → Run workflow** wählen.
8. Warte auf das grüne Häkchen. Öffne den erfolgreichen Lauf. Im Abschnitt **Artifacts** unten **FotoSwipe-iPhone** herunterladen und die ZIP-Datei entpacken. Darin liegt `FotoSwipe.ipa`. Zum Download der Artefakte musst du bei GitHub angemeldet sein.
9. Bei einem roten Häkchen den fehlgeschlagenen Schritt öffnen und dessen Fehlermeldung mit mir teilen. Keine Apple-Zugangsdaten werden für diesen Build benötigt.

Die IPA ist zunächst **unsigniert**: Sie lässt sich nicht einfach antippen und installieren. AltStore übernimmt anschließend die persönliche Signierung.

## 2. AltStore Classic unter Windows einrichten

Nutze **AltStore Classic** mit **AltServer für Windows**. AltStore PAL ist ein anderer Installationsweg.

Folge der aktuellen offiziellen Windows-Anleitung:
https://faq.altstore.io/altstore-classic/how-to-install-altstore-windows

Dort stehen die passenden Apple-Komponenten (iTunes/iCloud), Installationslinks sowie gegebenenfalls abweichende Schritte für bereits vorhandene Microsoft-Store-Versionen. Lade diese Komponenten aus den dort verlinkten offiziellen Quellen.

Der Ablauf ist grundsätzlich:

1. Benötigte Apple-Komponenten und AltServer nach Anleitung installieren.
2. iPhone per USB verbinden, entsperren und dem Computer vertrauen.
3. AltServer starten und über das Symbol im Windows-Infobereich **Install AltStore → dein iPhone** auswählen.
4. Deinen kostenlosen Apple Account nach Aufforderung in AltServer angeben. Zugangsdaten weder hier im Chat noch auf GitHub eintragen.
5. Auf dem iPhone gegebenenfalls unter **Einstellungen → Allgemein → VPN und Geräteverwaltung** deinem eigenen Entwicklerprofil vertrauen. Die genaue Bezeichnung hängt von der iOS-Version ab.
6. Falls iOS dazu auffordert, **Einstellungen → Datenschutz & Sicherheit → Entwicklermodus** aktivieren und die Neustart-/Bestätigungsschritte befolgen.

## 3. FotoSwipe installieren

1. Übertrage `FotoSwipe.ipa` in die Dateien-App deines iPhones, beispielsweise über iCloud Drive. Die Datei enthält den Programmcode, keine Fotos.
2. Lass AltServer auf deinem PC laufen. PC und iPhone müssen für diesen Weg per USB verbunden oder nach entsprechender Einrichtung im selben WLAN erreichbar sein.
3. Öffne auf dem iPhone AltStore Classic und im Bereich **My Apps** die Funktion zum Importieren einer IPA (Plus-Schaltfläche). Wähle `FotoSwipe.ipa` aus und folge den Anweisungen.
4. Nach erfolgreicher Installation FotoSwipe starten und den Fotozugriff erlauben. Für die Albumfunktionen vollständigen Zugriff wählen.
5. In FotoSwipe über das Einstellungs-Symbol die Alben für oben und unten auswählen bzw. selbst benennen.
6. Zunächst mit wenigen unwichtigen Fotos alle vier Wischrichtungen testen. Rechts wischen merkt ein Foto ohne Systemabfrage vor. Die Löschliste wird über das Papierkorb-Symbol geöffnet; erst der gemeinsame Löschknopf fordert die Löschung über iOS an. Bei Abbruch bleibt die Liste gespeichert.

## 4. Kostenlos weiter nutzen

Bei der kostenlosen Signierung läuft die Freigabe nach sieben Tagen ab. AltStore **Refresh All** erneuert sie. Dabei wird die App normalerweise aktualisiert, ohne dass du sie vorher löschen musst. AltStore versucht dies auch im Hintergrund; dazu muss AltServer erreichbar sein. Aktiviere unter Windows den Start von AltServer beim Anmelden, wenn du diese automatische Erneuerung nutzen möchtest.

Falls AltStore selbst abgelaufen ist, kann AltServer es erneut installieren, **ohne es vorher zu löschen**. Folge dann der offiziellen Anleitung. Die App-Freigabe und der Download des GitHub-Artefakts sind getrennt: Das Artefakt wird nach sieben Tagen auf GitHub entfernt, eine bereits heruntergeladene IPA kannst du lokal behalten und erneut verwenden.

Bewahre dieselbe App-Kennung und denselben Apple Account für spätere Updates bei. Ein vorheriges Löschen der App kann den lokal gespeicherten Sortierfortschritt entfernen. Ein abgelaufenes Signierungsprofil allein verändert deine Fotomediathek nicht.

## Kosten und Sichtbarkeit

Der Workflow nutzt ausschließlich einen Standard-macOS-Runner von GitHub und überspringt private Repositorys. Standard-Runner sind in öffentlichen Repositorys laut GitHub kostenlos. Es gibt keinen Veröffentlichungs-, App-Store- oder TestFlight-Schritt, keinen Zeitplan und keine Einrichtung kostenpflichtiger Dienste. Build-Ergebnisse werden nur vorübergehend als Artefakte gespeichert.

Der öffentliche Quellcode und die Build-Ergebnisse sind auf GitHub einsehbar. Deine Fotos, deine später gewählten Albumnamen und dein Apple-Passwort gehören nicht zum Repository. Die App selbst enthält keinen Upload zu GitHub oder einem eigenen Server.

Offizielle Referenzen:
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- https://docs.github.com/en/actions/tutorials/store-and-share-data
- https://faq.altstore.io/altstore-classic/how-to-install-altstore-windows
- https://faq.altstore.io/altstore-classic/your-altstore
- https://faq.altstore.io/altstore-classic/altserver
