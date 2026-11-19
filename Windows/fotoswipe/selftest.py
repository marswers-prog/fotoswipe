"""Packaged desktop smoke test, exclusively using temporary synthetic pictures."""
import json
import os
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
from .core import PhotoLibrary, windows_recycle


def run_gui_test(result_path):
    import tkinter as tk
    from .gui import PhotoApp, ImageCanvas
    result_path = Path(result_path)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='FotoSwipe-Smoke-') as directory:
        base = Path(directory)
        source, upper, lower = [base / name for name in ('Photos', 'Oben', 'Unten')]
        for folder in (source, upper, lower):
            folder.mkdir()
        for index in range(6):
            Image.new('RGB', (240, 160), (20 + index * 35, 130, 90)).save(source / f'{index}.png')
        lib = PhotoLibrary(base / 'state')
        lib.configure(source, upper, lower)
        root = tk.Tk()
        app = PhotoApp(root, lib)
        deadline = time.monotonic() + 60
        phase = [0]
        moved = {}
        def finish(error=None):
            result_path.write_text(json.dumps({'passed': error is None, 'error': str(error) if error else None, 'phase': phase[0]}), encoding='utf-8')
            lib.close()
            root.destroy()
        def poll():
            try:
                if time.monotonic() > deadline:
                    raise AssertionError('Desktop smoke test timed out')
                if app.busy or app.current is None:
                    root.after(50, poll)
                    return
                if phase[0] == 0:
                    assert app.current_image.width > 0
                    app.key(SimpleNamespace(keysym='Left', state=0))
                    app.key(SimpleNamespace(keysym='Left', state=0))
                    app._key_down = None
                elif phase[0] == 1:
                    assert lib.counts(source) == (1, 0)
                    app.key(SimpleNamespace(keysym='Right', state=0))
                    app._key_down = None
                elif phase[0] == 2:
                    assert lib.counts(source) == (1, 1)
                    assert Path(lib.pending(source)[0].path).exists()
                    moved['upper'] = Path(app.current.path)
                    app.key(SimpleNamespace(keysym='Up', state=0))
                    app._key_down = None
                elif phase[0] == 3:
                    assert not moved['upper'].exists()
                    assert (upper / moved['upper'].name).is_file()
                    moved['lower'] = Path(app.current.path)
                    app.key(SimpleNamespace(keysym='Down', state=0))
                    app._key_down = None
                else:
                    assert not moved['lower'].exists()
                    assert (lower / moved['lower'].name).is_file()
                    assert lib.counts(source) == (3, 1)
                    # All three secondary views must instantiate from the packaged program.
                    app.settings(); root.update_idletasks(); root.grab_current().destroy()
                    app.open_queue(); root.update_idletasks(); root.grab_current().destroy()
                    app.open_duplicates(); root.update_idletasks(); root.grab_current().destroy()
                    canvas = ImageCanvas(root, zoomable=True, width=300, height=200)
                    canvas.place(x=0, y=0, width=300, height=200)
                    canvas.show(app.current_image)
                    root.update_idletasks()
                    canvas.change_zoom(3)
                    assert canvas.zoom == 3
                    canvas.reset()
                    assert canvas.zoom == 1
                    canvas.destroy()
                    if os.name == 'nt':
                        probe = base / 'papierkorb-test.txt'
                        probe.write_text('FotoSwipe synthetic smoke-test file', encoding='utf-8')
                        windows_recycle(str(probe))
                        assert not probe.exists(), 'Packaged Windows Recycle Bin backend failed'
                        assert '.heic' in Image.registered_extensions(), 'HEIC decoder was not bundled'
                    finish()
                    return
                phase[0] += 1
                root.after(80, poll)
            except Exception as error:
                finish(error)
        root.after(200, poll)
        root.mainloop()
    result = json.loads(result_path.read_text(encoding='utf-8'))
    return 0 if result['passed'] else 1
