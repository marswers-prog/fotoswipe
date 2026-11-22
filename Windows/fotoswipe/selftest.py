"""Packaged desktop smoke test, exclusively using temporary synthetic pictures."""
import json
import os
import tempfile
import time
from pathlib import Path
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
        def press(widget, keysym, locks=0, repeat=False):
            # Send actual Tk events through the focused widget's bindtags.
            # Calling app.key directly missed the Windows Num Lock regression.
            widget.focus_force()
            root.update()
            assert root.focus_get() == widget, 'Keyboard focus was not assigned'
            state = locks if app.window_system == 'win32' else 0
            widget.event_generate('<KeyPress>', keysym=keysym, state=state)
            if repeat:
                widget.event_generate('<KeyPress>', keysym=keysym, state=state)
            widget.event_generate('<KeyRelease>', keysym=keysym, state=state)
            assert app._key_down is None, 'Key release was lost while busy'
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
                    press(app.canvas, 'Left', repeat=True)
                elif phase[0] == 1:
                    assert lib.counts(source) == (1, 0)
                    press(app.stage_button, 'Right', locks=0x8)
                elif phase[0] == 2:
                    assert lib.counts(source) == (1, 1)
                    assert Path(lib.pending(source)[0].path).exists()
                    moved['upper'] = Path(app.current.path)
                    press(app.upper_button, 'Up', locks=0xA)
                elif phase[0] == 3:
                    assert not moved['upper'].exists()
                    assert (upper / moved['upper'].name).is_file()
                    moved['lower'] = Path(app.current.path)
                    press(app.lower_button, 'Down', locks=0x2A)
                else:
                    assert not moved['lower'].exists()
                    assert (lower / moved['lower'].name).is_file()
                    assert lib.counts(source) == (3, 1)
                    before = app.current.path
                    for modifier in (0x4, 0x20000 if app.window_system == 'win32' else 0x8):
                        app.canvas.focus_force()
                        root.update()
                        app.canvas.event_generate('<KeyPress>', keysym='Right', state=modifier)
                        app.canvas.event_generate('<KeyRelease>', keysym='Right', state=modifier)
                        assert not app.busy and app.current.path == before, 'Modified shortcut sorted a picture'
                    # All three secondary views must instantiate from the packaged program.
                    app.settings()
                    root.update_idletasks()
                    dialog = root.grab_current()
                    press(dialog, 'Right', locks=0x8)
                    assert not app.busy and app.current.path == before, 'Modal window allowed background sorting'
                    dialog.destroy()
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
