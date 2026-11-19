import importlib.metadata
import shutil
import sys
from pathlib import Path
from PIL import Image

base = Path(__file__).resolve().parent
build = base / 'build'
build.mkdir(exist_ok=True)
source = base.parent / 'FotoSwipe/Assets.xcassets/AppIcon.appiconset/AppIcon.png'
Image.open(source).save(build / 'app.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
licenses = build / 'licenses'
licenses.mkdir(exist_ok=True)
for name in ('Pillow', 'pillow-heif', 'Send2Trash', 'pywin32', 'pyinstaller'):
    distribution = importlib.metadata.distribution(name)
    for entry in distribution.files or []:
        if any(word in str(entry).lower() for word in ('license', 'copying', 'copyright')):
            path = Path(distribution.locate_file(entry))
            if path.is_file() and path.stat().st_size < 2_000_000:
                target = licenses / name / str(entry).replace('..', '_').replace('/', '_').replace('\\', '_')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
for relative in ('LICENSE.txt', 'LICENSE', 'tcl/tcl8.6/license.terms', 'tcl/tk8.6/license.terms'):
    source_license = Path(sys.base_prefix) / relative
    if source_license.is_file():
        shutil.copyfile(source_license, licenses / ('Python-' + relative.replace('/', '-')))
