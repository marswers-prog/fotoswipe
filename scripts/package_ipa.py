#!/usr/bin/env python3
"""Pack an unsigned device .app as an IPA for local signing with AltStore."""
import argparse
from pathlib import Path
import plistlib
import zipfile


def package(app: Path, output: Path) -> None:
    if not app.is_dir() or app.suffix != '.app':
        raise ValueError('Keine .app-Datei gefunden. Zuerst den Xcode-Build ausführen.')
    info = plistlib.loads((app / 'Info.plist').read_bytes())
    if info.get('CFBundleSupportedPlatforms') != ['iPhoneOS']:
        raise ValueError('Eine Geräte-App wird benötigt; Simulator-Apps sind nicht installierbar.')
    executable = info.get('CFBundleExecutable')
    if not executable or not (app / executable).is_file():
        raise ValueError('Das ausführbare App-Programm fehlt.')
    if not info.get('NSPhotoLibraryUsageDescription'):
        raise ValueError('Die Erklärung zum Fotozugriff fehlt.')
    files = sorted(p for p in app.rglob('*') if p.is_file())
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.ipa.tmp')
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, (Path('Payload') / app.name / path.relative_to(app)).as_posix())
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError('Die erzeugte IPA ist beschädigt.')
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    package(args.app, args.output)
