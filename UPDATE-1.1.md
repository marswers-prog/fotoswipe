# FotoSwipe 1.1 – Löschliste und Update ohne Zurücksetzen

## Was sich ändert

Rechts wischen merkt ein Foto zum Löschen vor und zeigt sofort das nächste. Es wird dabei noch kein Foto aus Apple Fotos gelöscht. Über das Papierkorb-Symbol oder „Löschliste prüfen“ öffnest du die Liste. Du kannst ein Foto groß ansehen und mit „Behalten“ wieder aus der Löschliste nehmen. Dieses Foto gilt anschließend als bearbeitet.

Mit „… Fotos jetzt löschen“ werden die aktuell zugänglichen vorgemerkten Fotos gemeinsam an iOS übergeben. iOS zeigt die gemeinsame Bestätigung. Bei Abbruch oder Fehler bleibt die Löschliste gespeichert. Erfolgreich gelöschte Bilder werden aus der Liste genommen. Nicht zugängliche Einträge bleiben erhalten, damit eine eingeschränkte Fotoauswahl keine Vormerkungen verloren gehen lässt.

Die Löschliste bleibt auch nach dem Schließen der App erhalten. Ein ausdrückliches Zurücksetzen der Merkliste leert nur den abgeschlossenen Fortschritt, nicht die Löschliste.

## Fotos genauer ansehen

Ein Tippen auf die Bildmitte öffnet das Foto in einer Vollbildansicht. Mit zwei Fingern lässt sich das Bild bis zum Achtfachen der eingepassten Ansicht vergrößern und der vergrößerte Ausschnitt verschieben. Doppeltippen vergrößert den angetippten Bereich bzw. setzt den Zoom zurück. „Schließen“ führt zurück zum Sortieren. Die Ansicht selbst führt keine Behalten- oder Löschentscheidung aus. Bei Bedarf wird eine höher aufgelöste Vorschau mit bis zu 4.096 Pixeln an der längsten Kante geladen; bei iCloud-Fotos kann dafür Internet nötig sein. Auch aus der Detailansicht der Löschliste lässt sich die Zoomansicht öffnen.

## Bestehende Installation aktualisieren

1. Notiere vorab den angezeigten Fortschritt in den FotoSwipe-Einstellungen. Wenn du ohnehin ein iPhone-Backup auf dem PC verwendest, aktualisiere es vor dem Update.
2. Die neue `FotoSwipe.ipa` aus dem erfolgreichen GitHub-Build herunterladen und die Artefakt-ZIP entpacken.
3. **FotoSwipe nicht vom iPhone löschen.** Auch „Alle vorhandenen Fotos erneut durchsehen“ nicht verwenden.
4. Verwende dieselbe Installationsmethode wie vorher: AltServer auf demselben Windows-PC, dasselbe iPhone und **denselben Apple Account**. Das USB-Kabel anschließen, das iPhone entsperren und bei Bedarf dem PC vertrauen.
5. Bei gedrückter Shift-Taste das AltServer-Symbol anklicken, „Sideload .ipa…“ wählen, dein iPhone und die neue `FotoSwipe.ipa` auswählen. Die vorhandene App soll überschrieben/aktualisiert werden.
6. Wenn stattdessen eine andere App-Kennung, ein zweites FotoSwipe-Symbol oder die Aufforderung zur Deinstallation erscheint: **nicht deinstallieren**, sondern die Meldung zur Klärung weitergeben.
7. Nach dem Update die App öffnen und prüfen, dass der vorherige Fortschritt und die beiden Zielalben erhalten sind. Rechts wischen anschließend mit wenigen Fotos testen; zunächst ein vorgemerktes Foto wieder „Behalten“ und die Liste nach einem App-Neustart kontrollieren.

Die ursprüngliche App-Kennung `de.personal.FotoSwipe` bleibt im Projekt unverändert. Vorhandene `reviewed`-Einträge sowie `upAlbum` und `downAlbum` werden übernommen. Die neue gemeinsame Speicherung nutzt zusätzlich `reviewStateV2`; der alte `reviewed`-Schlüssel bleibt mit den abgeschlossenen Entscheidungen gefüllt. Version: 1.1, Build 2.

Der Erhalt der Daten setzt voraus, dass iOS die Installation als Update derselben signierten App akzeptiert. Das Verhalten der tatsächlichen Installation kann erst auf deinem iPhone überprüft werden.

## Automatische Prüfungen

Der Workflow führt vor dem iPhone-Build echte Swift-Prüfungen der gespeicherten Merkliste aus. Sie prüfen unter anderem die Migration von 2.307 alten Einträgen, den Erhalt beider Albumkennungen, doppelte Vormerkungen, Speicherung über App-Neustarts, das Zurücknehmen einzelner Vormerkungen, die Verarbeitung nur tatsächlich gelöschter Einträge sowie das explizite Zurücksetzen bei erhaltener Löschliste.

Die Systemabfrage, die tatsächliche Löschung in Apple Fotos und das Update über AltServer müssen auf einem echten iPhone getestet werden.
