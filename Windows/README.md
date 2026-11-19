# FotoSwipe für Windows

Ein kleines Ordner-Werkzeug für Windows 10 mit 64 Bit. Die fertige EXE enthält
Python und die benötigten Bilddecoder; Python muss nicht separat installiert werden.

- Links behalten, rechts für die gemeinsame Papierkorb-Aktion vormerken.
- Oben und unten in zwei frei wählbare Ordner verschieben; keine Überschreibung.
- Vollbildansicht mit Mauszoom und Verschieben des Ausschnitts.
- Gespeicherte Merkliste, Löschliste und Zielordner je Bilderordner.
- Exakte Dateiduplikate mit SHA-256-Vorauswahl und abschließendem Bytevergleich.
- JPEG, PNG, WebP, BMP, GIF, TIFF, HEIC/HEIF und AVIF über Pillow / pillow-heif.

[Bedienungsanleitung](ANLEITUNG.txt)

## Bauen und prüfen

Der kostenlose GitHub-Actions-Workflow `build-windows.yml` läuft auf
`windows-2022`, installiert Python 3.12 und die festgelegten Abhängigkeiten,
führt die Unit-Tests aus und erzeugt mit PyInstaller `FotoSwipe.exe`.
Anschließend startet er die gepackte EXE mit synthetischen Testbildern. Dabei
werden die vier Tastenaktionen, gespeicherte Zustände, der Zoom-Canvas,
die eingebundenen HEIC-Module und der native Windows-Papierkorb geprüft.
Die resultierende ZIP enthält die EXE, Anleitung und Lizenzhinweise.

Lokal aus Quellcode:

```powershell
python -m pip install -r Windows/requirements.txt
$env:PYTHONPATH = "Windows"
python -m unittest discover -s Windows/tests -v
python Windows/main.py
```

Die Dateioperationen verwenden einen persistenten Vorgangsvermerk. Verschieben
kopiert zunächst in eine eigene temporäre Datei im Zielordner, prüft den Inhalt,
veröffentlicht sie ohne Überschreibung und entfernt erst danach die Quelldatei.
Nach einem Abbruch wird die abgeschlossene Verschiebung erfasst oder eine
unfertige eigene Kopie zurückgenommen. Die Papierkorb-Aktion verwendet ausdrücklich
den modernen IFileOperation-Backend mit RECYCLEONDELETE und fällt nicht auf
endgültiges Löschen zurück. Geänderte oder nicht unterstützte Dateien bleiben in
der Löschliste. Nicht-Bild-Begleitdateien werden nicht mitverarbeitet.

Der Fortschritt liegt unter `%LOCALAPPDATA%\FotoSwipeWindows`, nicht neben der EXE.
Die Merkliste der iPhone-App bleibt eigenständig.

## Prüfstatus

Die lokalen Kernprüfungen sind bestanden. Windows-Build und Test der gepackten
EXE stehen vor dem ersten erfolgreichen Workflow noch aus. Der tatsächliche
Start auf dem eigenen Windows-10-PC muss anschließend geprüft werden.
