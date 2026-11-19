import os
from pathlib import Path
from PyInstaller.__main__ import run

base = Path(__file__).resolve().parent
run([
    '--noconfirm', '--clean', '--onefile', '--windowed', '--name', 'FotoSwipe',
    '--icon', str(base / 'build/app.ico'),
    '--add-data', str(base / 'build/app.ico') + os.pathsep + 'assets',
    '--collect-all', 'pillow_heif',
    '--hidden-import', 'send2trash.win.modern', '--hidden-import', 'win32timezone',
    '--paths', str(base), '--distpath', str(base / 'dist'),
    '--workpath', str(base / 'build/pyinstaller'), '--specpath', str(base / 'build'),
    str(base / 'main.py'),
])
