# FotoSwipe – erste native iPhone-Version

SwiftUI + PhotoKit, für iPhone mit iOS 17 oder neuer. Deutsches Interface.

## Bedienung

| Wischen | Aktion |
| --- | --- |
| Links | Behalten und nächstes Foto anzeigen |
| Rechts | Löschen über PhotoKit; iOS fragt nach Bestätigung |
| Oben | Behalten und dem oben eingestellten Album hinzufügen |
| Unten | Behalten und dem unten eingestellten Album hinzufügen |

Die Beschriftungen stehen links, rechts, oben und unten um das Bild. Sie lassen sich auch antippen. Oben rechts öffnet sich die Albumauswahl. Dort entweder vorhandene beschreibbare Alben wählen oder eigene Alben anlegen. Beide Richtungen sind unabhängig konfigurierbar.

Alben sind in Apple Fotos keine exklusiven Dateisystemordner. Ein Foto bleibt nach dem Einsortieren auch in der Mediathek und gegebenenfalls in anderen Alben. Es wird nicht dupliziert. Bei Live Photos wird das Standbild angezeigt und das gesamte Asset verarbeitet. Videos werden ausgeblendet. Reihenfolge: älteste Aufnahme zuerst. Bearbeitete Fotos werden lokal vermerkt und beim nächsten Start übersprungen. Die Merkliste lässt sich zurücksetzen, ohne Fotos zu verändern. Neuinstallation kann den lokalen Fortschritt verlieren.

Die App überträgt keine Fotos an einen eigenen Server und enthält keine Analyse- oder Werbedienste. Für iCloud-Fotos kann Apples Fotoverwaltung das Bild aus iCloud herunterladen. Beim Löschen gelten die Einstellungen deiner Apple-Fotomediathek, einschließlich möglicher Synchronisierung mit anderen Geräten. Wiederherstellung erfolgt über Apples „Zuletzt gelöscht“, soweit verfügbar, nicht über diese App.

## Kostenlos mit Windows installieren

Die Anleitung [START-WINDOWS.md](START-WINDOWS.md) beschreibt den Weg über ein öffentliches GitHub-Projekt, den mitgelieferten automatischen Build und AltStore Classic. Dafür ist kein eigener Mac und keine kostenpflichtige Apple-Developer-Mitgliedschaft vorgesehen. Für diesen Weg muss die kostenlose Signierung regelmäßig erneuert werden. Der Workflow erstellt nach erfolgreicher Kompilierung `FotoSwipe.ipa`; die persönliche Signierung erfolgt anschließend lokal über AltStore. Der erste echte Build und Gerätetest stehen noch aus.

## Alternativ mit einem Mac starten

Voraussetzungen: Mac mit Xcode und installierter iOS-Plattformunterstützung, Apple Account, iPhone mit iOS 17+.

1. ZIP entpacken und `FotoSwipe.xcodeproj` in Xcode öffnen.
2. Unter Xcode → Settings → Accounts den eigenen Apple Account hinzufügen.
3. Im Projekt das Target **FotoSwipe** wählen. Unter **Signing & Capabilities** das eigene Team setzen und **Automatically manage signing** aktivieren. Den Bundle Identifier bei Bedarf auf einen eigenen eindeutigen Wert ändern.
4. iPhone mit dem Mac verbinden, dem Computer vertrauen und es in Xcode als Ausführungsziel auswählen. Falls Xcode dazu auffordert, auf dem iPhone den Entwicklermodus aktivieren und die angezeigten Schritte befolgen.
5. Mit ▶ / Cmd+R bauen und starten. Eventuell angezeigte Vertrauens- oder Signierungsanweisungen von Xcode/iPhone befolgen.
6. In FotoSwipe den Fotozugriff erlauben. Für die Albumfunktionen vollständigen Zugriff wählen. Bei eingeschränktem Zugriff funktionieren Anzeige, Behalten und Löschen nur für freigegebene Fotos; die Albumfunktionen bleiben gesperrt.
7. In den App-Einstellungen die beiden Zielalben einrichten. Zunächst mit wenigen unwichtigen Testfotos prüfen.

Ein kostenloses persönliches Xcode-Team kann zum Testen dienen. Signierung und Gültigkeitsdauer hängen vom Apple Account ab; ein erneuter Start über Xcode kann erforderlich sein. Dies ist noch keine App-Store- oder TestFlight-Veröffentlichung und keine fertig signierte IPA-Datei. Für eine spätere Verteilung sind separate Apple-Signierung und gegebenenfalls weitere Veröffentlichungsschritte nötig.

## Prüfstatus

Das Projekt wurde in einer Linux-Umgebung erstellt. Dort sind Xcode, SwiftUI und das iOS SDK nicht verfügbar. Daher wurden weder ein iOS-Build noch Simulator- oder Gerätetests durchgeführt. Geprüft wurden die Dateistruktur, XML-/Plist-Dateien, Projektverweise und das ZIP-Archiv. Der erste echte Kompilierungslauf steht auf dem vorbereiteten GitHub-macOS-Runner oder einem eigenen Mac aus. Der neue Workflow, die Shell-Syntax und das IPA-Packen wurden separat lokal geprüft; eine erfolgreich gebaute IPA liegt noch nicht vor.

## Geräteprüfung vor produktiver Verwendung

- Vollständigen Zugriff erlauben: Fotos erscheinen einzeln mit korrekter Ausrichtung; Hoch- und Querformat bleiben vollständig sichtbar.
- Zugriff ablehnen: App zeigt Anleitung zu den Einstellungen; nach Freigabe werden Fotos geladen.
- Eingeschränkten Zugriff erlauben: nur ausgewählte Fotos; Auswahl erweitern; keine Albumaktion möglich.
- Links wischen: Foto bleibt in Apple Fotos und wird nach App-Neustart übersprungen.
- Rechts wischen und den iOS-Dialog abbrechen: dasselbe Foto bleibt angezeigt.
- Rechts wischen und bestätigen: Foto wird erst nach erfolgreicher PhotoKit-Änderung übersprungen.
- Zwei verschiedene Alben anlegen und auswählen; oben und unten wischen; Zuordnung in Apple Fotos kontrollieren.
- Bereits vorhandene Albumzugehörigkeit sowie extern gelöschtes Zielalbum prüfen.
- iCloud-Bild ohne lokale Kopie bei aktiver und fehlender Internetverbindung prüfen; bei Ladefehler erneut laden.
- App während einer Systembestätigung in den Hintergrund bringen: danach weder doppelter Zugriff noch übersprungene Fotos.
- Schnelle Mehrfachgesten, kleine Displays, große Schrift, VoiceOver und Live Photos prüfen.
- Fortschritt zurücksetzen: Fotos und Alben bleiben unverändert, vorhandene Bilder werden erneut angeboten.

Build ohne Signierung auf dem Mac:

```sh
xcodebuild -project FotoSwipe.xcodeproj -scheme FotoSwipe -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO build
```

Apple-Referenzen:
- https://developer.apple.com/documentation/photos/phphotolibrary
- https://developer.apple.com/documentation/photos/phassetcollectionchangerequest
- https://developer.apple.com/documentation/photos/phassetchangerequest
- https://developer.apple.com/documentation/xcode/running-your-app-on-simulated-or-physical-devices
