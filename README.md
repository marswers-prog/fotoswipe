# FotoSwipe 1.2 – exakte Duplikate prüfen

SwiftUI + PhotoKit, für iPhone mit iOS 17 oder neuer. Deutsches Interface.

## Neues in Version 1.2

Unter **Einstellungen → Fotos aufräumen → Exakte Duplikate suchen** lassen sich vollständige Fotodateien einschließlich Live-Photo- und Bearbeitungsressourcen vergleichen. SHA-256 findet Kandidaten; ein zusätzlicher Bytevergleich bestätigt die Gleichheit. Pro ausgewählter Gruppe bleibt ein ausdrücklich gewähltes Exemplar erhalten. Vor dem Löschen wird erneut geprüft und iOS fragt nach Bestätigung. Die bisherige Merkliste, Löschliste und Albumkonfiguration werden übernommen.

[Update-Anleitung für Version 1.2](UPDATE-1.2.md) · [Aktueller Build](https://github.com/marswers-prog/fotoswipe/actions/runs/41863090797)

**Build-Status:** Der Quellcode und die automatischen Prüfungen sind vorbereitet. GitHub hat bislang keinen freien Standard-Mac zugeteilt. Die neuen Swift-Prüfungen und der iPhone-Build sind daher noch nicht ausgeführt; eine geprüfte IPA für Version 1.2 liegt noch nicht vor. Nach einem erfolgreichen Lauf steht die Datei unter dem Artefakt **FotoSwipe-iPhone** bereit. Bestehende Installation nicht löschen.

## Bedienung

| Wischen | Aktion |
| --- | --- |
| Links | Behalten und nächstes Foto anzeigen |
| Rechts | Zum Löschen vormerken und sofort das nächste Foto anzeigen |
| Oben | Behalten und dem oben eingestellten Album hinzufügen |
| Unten | Behalten und dem unten eingestellten Album hinzufügen |

Die Beschriftungen stehen links, rechts, oben und unten um das Bild. Sie lassen sich auch antippen. Oben rechts öffnet sich die Albumauswahl. Dort entweder vorhandene beschreibbare Alben wählen oder eigene Alben anlegen. Beide Richtungen sind unabhängig konfigurierbar.

Alben sind in Apple Fotos keine exklusiven Dateisystemordner. Ein Foto bleibt nach dem Einsortieren auch in der Mediathek und gegebenenfalls in anderen Alben. Es wird nicht dupliziert. Bei Live Photos wird das Standbild angezeigt und das gesamte Asset verarbeitet. Videos werden ausgeblendet. Reihenfolge: älteste Aufnahme zuerst. Bearbeitete Fotos werden lokal vermerkt und beim nächsten Start übersprungen. Die Merkliste lässt sich zurücksetzen, ohne Fotos zu verändern. Neuinstallation kann den lokalen Fortschritt verlieren.

Die App überträgt keine Fotos an einen eigenen Server und enthält keine Analyse- oder Werbedienste. Für iCloud-Fotos kann Apples Fotoverwaltung das Bild aus iCloud herunterladen. Beim Löschen gelten die Einstellungen deiner Apple-Fotomediathek, einschließlich möglicher Synchronisierung mit anderen Geräten. Wiederherstellung erfolgt über Apples „Zuletzt gelöscht“, soweit verfügbar, nicht über diese App.

Ein Tippen auf die Bildmitte öffnet die Vollbildansicht mit Zwei-Finger-Zoom und Doppeltippen. Die Löschliste wird über das Papierkorb-Symbol geöffnet; dort lassen sich einzelne Fotos behalten oder alle verfügbaren Vormerkungen mit einer gemeinsamen iOS-Bestätigung löschen. Die Liste bleibt nach einem App-Neustart erhalten.

**Bestehende Installation aktualisieren:** [Update-Anleitung für Version 1.2](UPDATE-1.2.md). FotoSwipe nicht deinstallieren; dieselbe App-Kennung und denselben Apple Account für die Installation über AltServer verwenden.

## Kostenlos mit Windows installieren

Die Anleitung [START-WINDOWS.md](START-WINDOWS.md) beschreibt den Weg über ein öffentliches GitHub-Projekt, den mitgelieferten automatischen Build und AltStore Classic. Dafür ist kein eigener Mac und keine kostenpflichtige Apple-Developer-Mitgliedschaft vorgesehen. Für diesen Weg muss die kostenlose Signierung regelmäßig erneuert werden. Der Workflow erstellt nach erfolgreicher Kompilierung `FotoSwipe.ipa`; die persönliche Signierung erfolgt anschließend lokal über AltStore. Version 1.1 wurde erfolgreich gebaut und die Fortschrittsübernahme automatisch geprüft. Das Update sowie die neuen Funktionen müssen anschließend auf dem eigenen iPhone getestet werden.

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

## Prüfstatus der bisherigen Version 1.1

Version 1.1 (Build 2) wurde am 3. November 2026 auf dem kostenlosen Standard-Runner `macos-15-intel` erfolgreich für iPhone kompiliert und als unsignierte IPA verpackt. Die App-Kennung `de.personal.FotoSwipe` ist unverändert.

[Erfolgreicher Build](https://github.com/marswers-prog/fotoswipe/actions/runs/41709532313) · [FotoSwipe 1.1 herunterladen](https://github.com/marswers-prog/fotoswipe/actions/runs/41709532313/artifacts/13266827393) (bei GitHub anmelden, ZIP entpacken; dieses Artefakt wird am 10. November 2026 entfernt und kann durch einen neuen Build erneut erzeugt werden).

Die automatischen Swift-Prüfungen sind bestanden: Migration von 2.307 bereits bearbeiteten Fotos, Erhalt beider Albumkennungen, persistente und eindeutige Löschliste, Zurücknehmen einzelner Vormerkungen, Verarbeitung nur der tatsächlich gelöschten Einträge und Zurücksetzen bei erhaltener Löschliste. Die Speicherfelder der bestehenden Installation werden übernommen. Simulator- und Gerätetests der neuen Funktionen sowie das tatsächliche Update auf dem iPhone stehen noch aus.

## Geräteprüfung vor produktiver Verwendung

- Vollständigen Zugriff erlauben: Fotos erscheinen einzeln mit korrekter Ausrichtung; Hoch- und Querformat bleiben vollständig sichtbar.
- Zugriff ablehnen: App zeigt Anleitung zu den Einstellungen; nach Freigabe werden Fotos geladen.
- Eingeschränkten Zugriff erlauben: nur ausgewählte Fotos; Auswahl erweitern; keine Albumaktion möglich.
- Links wischen: Foto bleibt in Apple Fotos und wird nach App-Neustart übersprungen.
- Rechts wischen: Foto wird ohne Systemabfrage vorgemerkt; sofort erscheint das nächste. App neu starten: Vormerkung bleibt erhalten.
- Löschliste öffnen, Bild prüfen und „Behalten“ wählen: nur dieses Foto verlässt die Liste und bleibt in Apple Fotos.
- Gemeinsame Löschabfrage abbrechen: alle Vormerkungen bleiben erhalten.
- Gemeinsam löschen und bestätigen: nur erfolgreich gelöschte zugängliche Fotos werden aus der Liste entfernt.
- Bildmitte antippen: Vollbild öffnet sich. Pinch-Zoom, Ausschnitt verschieben, Doppeltippen und Schließen prüfen; dabei wird keine Sortierentscheidung gespeichert.
- Zwei verschiedene Alben anlegen und auswählen; oben und unten wischen; Zuordnung in Apple Fotos kontrollieren.
- Bereits vorhandene Albumzugehörigkeit sowie extern gelöschtes Zielalbum prüfen.
- iCloud-Bild ohne lokale Kopie bei aktiver und fehlender Internetverbindung prüfen; bei Ladefehler erneut laden.
- App während einer Systembestätigung in den Hintergrund bringen: danach weder doppelter Zugriff noch übersprungene Fotos.
- Schnelle Mehrfachgesten, kleine Displays, große Schrift, VoiceOver und Live Photos prüfen.
- Fortschritt zurücksetzen: Fotos und Alben bleiben unverändert, abgeschlossene Bilder werden erneut angeboten; die Löschliste bleibt erhalten.

Build ohne Signierung auf dem Mac:

```sh
xcodebuild -project FotoSwipe.xcodeproj -scheme FotoSwipe -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO build
```

Apple-Referenzen:
- https://developer.apple.com/documentation/photos/phphotolibrary
- https://developer.apple.com/documentation/photos/phassetcollectionchangerequest
- https://developer.apple.com/documentation/photos/phassetchangerequest
- https://developer.apple.com/documentation/xcode/running-your-app-on-simulated-or-physical-devices
