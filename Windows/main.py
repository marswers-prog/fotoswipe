import argparse
import ctypes
import hashlib
import logging
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test-result')
    parser.add_argument('--data-dir')
    args = parser.parse_args()
    if args.self_test_result:
        from fotoswipe.selftest import run_gui_test
        try:
            return run_gui_test(args.self_test_result)
        except Exception as error:
            import json, traceback
            Path(args.self_test_result).write_text(json.dumps({'passed': False, 'error': str(error), 'traceback': traceback.format_exc()}), encoding='utf-8')
            return 1
    data_dir = Path(args.data_dir) if args.data_dir else Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'FotoSwipeWindows'
    data_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=str(data_dir / 'fehler.log'), level=logging.ERROR,
                        format='%(asctime)s %(message)s', encoding='utf-8')
    import tkinter as tk
    from tkinter import messagebox
    mutex = None
    kernel = None
    if os.name == 'nt':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        kernel.CreateMutexW.restype = ctypes.c_void_p
        name = 'Local\\FotoSwipeWindows-' + hashlib.sha256(str(data_dir.resolve()).encode()).hexdigest()[:20]
        mutex = kernel.CreateMutexW(None, False, name)
        if ctypes.get_last_error() == 183:
            messagebox.showinfo('FotoSwipe', 'FotoSwipe ist bereits geöffnet. Bitte das bestehende Fenster verwenden.')
            return 0
    root = tk.Tk()
    if os.name == 'nt':
        icon = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'assets/app.ico'
        if icon.exists():
            root.iconbitmap(default=str(icon))
    root.withdraw()
    try:
        from fotoswipe.core import PhotoLibrary
        from fotoswipe.gui import PhotoApp
        library = PhotoLibrary(data_dir)
        def callback_error(kind, error, trace):
            logging.error('Oberflächenfehler', exc_info=(kind, error, trace))
            messagebox.showerror('FotoSwipe', str(error), parent=root)
        root.report_callback_exception = callback_error
        PhotoApp(root, library)
        root.deiconify()
        root.mainloop()
        return 0
    except Exception as error:
        logging.exception('Programmfehler')
        messagebox.showerror('FotoSwipe', 'FotoSwipe konnte nicht gestartet werden.\n\n' + str(error), parent=root)
        root.destroy()
        return 1
    finally:
        if mutex and kernel:
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel.CloseHandle(mutex)


if __name__ == '__main__':
    sys.exit(main())
