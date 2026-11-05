# FotoSwipe 1.2 – exakte Duplikate finden

[FotoSwipe 1.2 herunterladen](https://github.com/marswers-prog/fotoswipe/actions/runs/41970804630/artifacts/13389229182) · [Erfolgreicher Build](https://github.com/marswers-prog/fotoswipe/actions/runs/41970804630). Bei GitHub anmelden, die ZIP entpacken und `FotoSwipe.ipa` entnehmen. Download verfügbar bis zum 12. November 2026; danach bei Bedarf erneut bauen.

## Bedienung

1. FotoSwipe öffnen und oben rechts die Einstellungen wählen.
2. Unter „Fotos aufräumen“ auf „Exakte Duplikate suchen“ tippen.
3. Entscheiden, ob iCloud-Fotos bei Bedarf geladen werden dürfen, und die Suche starten. Sie kann jederzeit abgebrochen werden. Für große Mediatheken kann der vollständige Dateivergleich länger dauern und größere Datenmengen laden.
4. Die gefundenen Gruppen prüfen. Mit einem Tipp auf die Vorschau öffnet sich die bestehende Vollbild- und Zoomansicht.
5. Für jede gewünschte Gruppe „Zusätzliche Kopien auswählen“ einschalten. Mit „Behalten“ das Exemplar wählen, das bleiben soll. Standardmäßig wird ein vorhandener Favorit bevorzugt, sonst der ältere Eintrag. Keine Gruppe ist vorab zum Löschen ausgewählt.
6. Auf „… Kopien löschen“ tippen, die Auswahl bestätigen und anschließend den iOS-Löschdialog bestätigen. Bis dahin wird nichts gelöscht.

Vor der tatsächlichen Löschung werden alle ausgewählten Dateien einschließlich der zu behaltenden Exemplare erneut gelesen und geprüft. Bei Änderungen, fehlenden Dateien oder einem Fehler wird der Vorgang abgebrochen. Pro ausgewählter Gruppe bleibt ein Foto erhalten. Die nicht ausgewählten Gruppen bleiben unverändert.

## Was „exakt“ bedeutet

Die App sucht keine bloß ähnlichen Motive. Sie liest alle von PhotoKit bereitgestellten Ressourcen eines Bildes, unter anderem Originaldatei, Live-Photo-Bewegtbild und vorhandene Bearbeitungsdaten. Dimensionen, Medienuntertyp, Ressourcenrollen, Dateityp, Datenlänge und SHA-256-Prüfsummen dienen zur Kandidatensuche. Anschließend werden Kandidaten nochmals in vorübergehende lokale Dateien geschrieben und tatsächlich byteweise verglichen. Die temporären Vergleichsdateien werden nach jedem Vergleich entfernt. Es wird kein Foto an einen eigenen Server übertragen.

Die Suche umfasst alle zugänglichen Bilder, auch bereits bearbeitete. Bei eingeschränktem Fotozugriff wird nur die freigegebene Auswahl durchsucht. Serienfotos sowie nicht vollständig lesbare oder nicht unterstützte Ressourcen werden vorsichtshalber ausgelassen und als ausgelassen gemeldet. Unterschiedlich komprimierte, exportierte oder bearbeitete Bilder können gleich aussehen, haben aber unterschiedliche Dateien und gelten hier nicht als exakt gleich.

Fotodateien können identisch sein, obwohl die Einträge in Apple Fotos unterschiedliche Aufnahmedaten, Favoritenmarkierungen oder Albumzuordnungen haben. Diese Unterschiede können bei der Auswahl des zu behaltenden Exemplars relevant sein. Albumzuordnungen der gelöschten Kopien werden nicht automatisch auf das verbleibende Foto übertragen.

Wenn die Duplikat-Löschung erfolgreich ist, gelten die gelöschten Kopien und das ausdrücklich gewählte verbleibende Foto als bearbeitet. Diese Einträge werden auch aus einer eventuell vorhandenen manuellen Löschliste genommen; alle übrigen bisherigen Entscheidungen und Vormerkungen bleiben erhalten. Bei Abbruch oder Fehler wird der bisherige Fortschritt nicht durch die Duplikatfunktion verändert.

## Als Update installieren

Die neue IPA wie bei Version 1.1 mit AltServer auf demselben iPhone und mit demselben Apple Account über die vorhandene App installieren. **FotoSwipe vorher nicht deinstallieren und die Merkliste nicht zurücksetzen.** Falls ein Signierungskonflikt auftritt oder eine Deinstallation verlangt wird, dort stoppen und die Meldung zur Klärung weitergeben.

Danach zuerst Fortschrittszähler, Zielalben und die bestehende Löschliste kontrollieren. Die App-Kennung `de.personal.FotoSwipe` sowie die Speicherfelder `reviewed`, `reviewStateV2`, `upAlbum` und `downAlbum` bleiben erhalten. Version 1.2, Build 3.

## Prüfung

Am 5. November 2026 sind beide automatischen Swift-Testgruppen und der iPhone-Build erfolgreich abgeschlossen worden. Die automatischen Prüfungen decken die Migration von 2.307 alten Entscheidungen mit bestehender Löschliste, den Erhalt der Albumkennungen, unterschiedliche Live-Photo- und Bearbeitungsressourcen, blockweises Hashen, den abschließenden Bytevergleich und ungültige Löschpläne ab. Die gebaute Version ist 1.2 (Build 3). Die Suche in einer echten Mediathek, das Abbrechen eines iOS-Löschdialogs und das Update auf dem eigenen iPhone müssen anschließend am Gerät geprüft werden.
