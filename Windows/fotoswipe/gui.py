from __future__ import annotations

import math
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
from .core import KEY_ACTIONS, Cancelled, PhotoError, PhotoLibrary
from .imaging import load_photo, preview

BG = '#0d1419'
PANEL = '#17252d'
TEXT = '#eef5f3'
MUTED = '#9bafb5'
MINT = '#8cebbb'
CORAL = '#ff9b91'


def button(parent, text, command, color=TEXT, **kwargs):
    return tk.Button(parent, text=text, command=command, font=('Segoe UI', 10),
                     bg=PANEL, fg=color, activebackground='#263e48', activeforeground=color,
                     disabledforeground='#64767c', relief='flat', bd=0, padx=14, pady=10,
                     cursor='hand2', highlightthickness=0, **kwargs)


def label(parent, text='', **kwargs):
    options = dict(bg=BG, fg=TEXT, font=('Segoe UI', 10))
    options.update(kwargs)
    return tk.Label(parent, text=text, **options)


def readable_size(size):
    return f'{size / 1024 / 1024:.1f} MB' if size >= 1024 * 1024 else f'{size / 1024:.0f} KB'


class ImageCanvas(tk.Canvas):
    def __init__(self, master, zoomable=False, **kwargs):
        super().__init__(master, bg='#090e12', highlightthickness=0, **kwargs)
        self.image = None
        self.photo = None
        self.zoom = 1.0
        self.pan = [0.0, 0.0]
        self.drag_start = None
        self.bind('<Configure>', lambda event: self.draw())
        if zoomable:
            self.bind('<MouseWheel>', self.wheel)
            self.bind('<Button-4>', lambda e: self.change_zoom(1.25, e.x, e.y))
            self.bind('<Button-5>', lambda e: self.change_zoom(0.8, e.x, e.y))
            self.bind('<ButtonPress-1>', self.start_drag)
            self.bind('<B1-Motion>', self.drag)
            self.bind('<Double-Button-1>', lambda e: self.reset() if self.zoom > 1.01 else self.change_zoom(3, e.x, e.y))

    def show(self, image):
        self.image = image
        self.draw()

    def reset(self):
        self.zoom = 1.0
        self.pan = [0.0, 0.0]
        self.draw()

    def geometry_values(self):
        if self.image is None:
            return None
        width, height = max(self.winfo_width(), 1), max(self.winfo_height(), 1)
        scale = min(width / self.image.width, height / self.image.height) * self.zoom
        for i, (extent, viewport) in enumerate(((self.image.width * scale, width), (self.image.height * scale, height))):
            limit = max(0, (extent - viewport) / 2)
            self.pan[i] = max(-limit, min(limit, self.pan[i]))
        x = (width - self.image.width * scale) / 2 + self.pan[0]
        y = (height - self.image.height * scale) / 2 + self.pan[1]
        return width, height, scale, x, y

    def draw(self):
        self.delete('all')
        geometry = self.geometry_values()
        if geometry is None:
            self.create_text(max(self.winfo_width(), 2) / 2, max(self.winfo_height(), 2) / 2,
                             text='Bilderordner wählen, dann mit den Pfeiltasten sortieren.',
                             fill=MUTED, font=('Segoe UI', 12), width=max(self.winfo_width() - 40, 200))
            return
        width, height, scale, x, y = geometry
        left, top = max(0, math.floor(-x / scale)), max(0, math.floor(-y / scale))
        right = min(self.image.width, math.ceil((width - x) / scale))
        bottom = min(self.image.height, math.ceil((height - y) / scale))
        if right <= left or bottom <= top:
            return
        # Render only the visible crop, even at 8x zoom. Never allocate an enormous zoom bitmap.
        crop = self.image.crop((left, top, right, bottom))
        crop = crop.resize((max(1, round((right - left) * scale)), max(1, round((bottom - top) * scale))), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(crop)
        self.create_image(x + left * scale, y + top * scale, anchor='nw', image=self.photo)

    def change_zoom(self, factor, x=None, y=None):
        geometry = self.geometry_values()
        if geometry is None:
            return
        width, height, scale, offset_x, offset_y = geometry
        x, y = (width / 2 if x is None else x), (height / 2 if y is None else y)
        point_x, point_y = (x - offset_x) / scale, (y - offset_y) / scale
        self.zoom = max(1, min(8, self.zoom * factor))
        new_scale = min(width / self.image.width, height / self.image.height) * self.zoom
        self.pan = [x - point_x * new_scale - (width - self.image.width * new_scale) / 2,
                    y - point_y * new_scale - (height - self.image.height * new_scale) / 2]
        self.draw()

    def wheel(self, event):
        self.change_zoom(1.25 if event.delta > 0 else 0.8, event.x, event.y)
        return 'break'

    def start_drag(self, event):
        self.drag_start = (event.x, event.y, *self.pan)

    def drag(self, event):
        if self.drag_start:
            x, y, px, py = self.drag_start
            self.pan = [px + event.x - x, py + event.y - y]
            self.draw()


class PhotoApp:
    def __init__(self, root, library):
        self.root, self.library = root, library
        self.source = ''
        self.current = None
        self.current_image = None
        self.current_path = ''
        self.skipped = set()
        self.busy = False
        self.events = queue.SimpleQueue()
        root.title('FotoSwipe für Windows')
        root.geometry('1180x820')
        root.minsize(850, 620)
        root.configure(bg=BG)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self._style()
        self._build()
        root.bind('<KeyPress>', self.key)
        root.after(40, self._drain)
        previous = library.last_root()
        if previous and Path(previous).is_dir():
            self.source = previous
            root.after(100, self.refresh)

    def _style(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('Treeview', background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                        rowheight=31, font=('Segoe UI', 10), borderwidth=0)
        style.configure('Treeview.Heading', background='#243840', foreground=TEXT, font=('Segoe UI', 10, 'bold'))
        style.map('Treeview', background=[('selected', '#355e61')], foreground=[('selected', TEXT)])
        style.configure('TProgressbar', troughcolor=PANEL, background=MINT)

    def _build(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill='x', padx=22, pady=(18, 10))
        label(header, 'FotoSwipe', font=('Segoe UI', 23, 'bold')).pack(side='left')
        label(header, '  WINDOWS', fg=MINT).pack(side='left', pady=(10, 0))
        self.settings_button = button(header, 'Einstellungen', self.settings)
        self.settings_button.pack(side='right')
        self.queue_button = button(header, 'Löschliste (0)', self.open_queue, CORAL)
        self.queue_button.pack(side='right', padx=8)
        self.folder_button = button(header, 'Bilderordner wählen', self.choose_folder, MINT)
        self.folder_button.pack(side='right', padx=8)
        self.folder_label = label(self.root, 'Wähle einen Ordner mit deinen Bildern.', anchor='w', fg=MUTED)
        self.folder_label.pack(fill='x', padx=24, pady=(0, 10))
        area = tk.Frame(self.root, bg=BG)
        area.pack(fill='both', expand=True, padx=18)
        area.rowconfigure(1, weight=1)
        area.columnconfigure(1, weight=1)
        self.upper_button = button(area, '↑  Oberen Zielordner wählen', lambda: self.action('upper'), MINT)
        self.upper_button.grid(row=0, column=1, sticky='ew', padx=20, pady=(0, 12))
        self.keep_button = button(area, '←\n\nBehalten', lambda: self.action('keep'), MINT, width=10)
        self.keep_button.grid(row=1, column=0, sticky='ns', padx=(0, 12))
        self.canvas = ImageCanvas(area)
        self.canvas.grid(row=1, column=1, sticky='nsew')
        self.canvas.bind('<Double-Button-1>', lambda event: self.open_zoom())
        self.stage_button = button(area, '→\n\nLöschen\nvormerken', lambda: self.action('stage'), CORAL, width=10)
        self.stage_button.grid(row=1, column=2, sticky='ns', padx=(12, 0))
        self.lower_button = button(area, '↓  Unteren Zielordner wählen', lambda: self.action('lower'), MINT)
        self.lower_button.grid(row=2, column=1, sticky='ew', padx=20, pady=(12, 0))
        self.filename_label = label(self.root, '', fg=MUTED, anchor='w')
        self.filename_label.pack(fill='x', padx=24, pady=(14, 3))
        self.status_label = label(self.root, '← behalten · → vormerken · ↑/↓ verschieben · Enter oder Doppelklick: Vollbild', fg=MINT, anchor='w')
        self.status_label.pack(fill='x', padx=24, pady=3)
        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill='x', padx=24, pady=(8, 16))
        self.progress_label = label(footer, '', fg=MUTED)
        self.progress_label.pack(side='left')
        self.zoom_button = button(footer, 'Bild vergrößern', self.open_zoom)
        self.zoom_button.pack(side='right')
        self.skip_button = button(footer, 'Vorläufig überspringen', self.skip)
        self.skip_button.pack(side='right', padx=8)
        self.sort_buttons = [self.upper_button, self.lower_button, self.keep_button, self.stage_button, self.zoom_button]
        self.update_controls()

    def update_controls(self):
        for widget in self.sort_buttons:
            widget.configure(state='normal' if self.current and not self.busy else 'disabled')
        for widget in (self.folder_button, self.settings_button):
            widget.configure(state='disabled' if self.busy else 'normal')
        self.queue_button.configure(state='normal' if self.source and not self.busy else 'disabled')
        self.skip_button.configure(state='normal' if self.current_path and not self.busy else 'disabled')
        if self.source:
            cfg = self.library.settings(self.source)
            self.folder_label.configure(text=self.source)
            self.upper_button.configure(text='↑  ' + (Path(cfg['upper_path']).name if cfg['upper_path'] else 'Oberen Zielordner wählen'))
            self.lower_button.configure(text='↓  ' + (Path(cfg['lower_path']).name if cfg['lower_path'] else 'Unteren Zielordner wählen'))
            reviewed, pending = self.library.counts(self.source)
            self.queue_button.configure(text=f'Löschliste ({pending})')
            self.progress_label.configure(text=f'{reviewed} bearbeitet  ·  {pending} vorgemerkt')

    def _drain(self):
        try:
            while True:
                callback = self.events.get_nowait()
                try:
                    callback()
                except Exception:
                    import sys
                    self.root.report_callback_exception(*sys.exc_info())
        except queue.Empty:
            pass
        self.root.after(40, self._drain)

    def run(self, work, done, text='Bitte warten …', parent=None):
        if self.busy:
            return
        self.busy = True
        self.status_label.configure(text=text)
        self.update_controls()
        def worker():
            try:
                result, error = work(), None
            except Exception as problem:
                result, error = None, problem
            def finish():
                self.busy = False
                self.update_controls()
                if error:
                    self.status_label.configure(text=str(error))
                    if not isinstance(error, Cancelled):
                        messagebox.showerror('FotoSwipe', str(error), parent=parent if parent and parent.winfo_exists() else self.root)
                done(result, error)
            self.events.put(finish)
        threading.Thread(target=worker, daemon=True).start()

    def choose_folder(self):
        if self.busy:
            return
        chosen = filedialog.askdirectory(title='Bilderordner wählen', initialdir=self.source or str(Path.home()), parent=self.root)
        if not chosen:
            return
        cfg = self.library.settings(chosen)
        self.library.configure(chosen, cfg['upper_path'], cfg['lower_path'], cfg['recursive'])
        self.source, self.skipped = cfg['root'], set()
        self.refresh()

    def refresh(self, message=None, after=None):
        if not self.source or self.busy:
            return
        self.current = None
        self.current_image = None
        self.current_path = ''
        self.canvas.show(None)
        def work():
            paths, inaccessible = self.library.files(self.source)
            paths = [p for p in paths if p not in self.skipped]
            result = dict(paths=paths, inaccessible=inaccessible, item=None, image=None, error=None)
            if paths:
                try:
                    result['item'], result['image'] = load_photo(paths[0], self.source)
                except Exception as error:
                    result['error'] = str(error)
            return result
        def done(result, error):
            if error:
                return
            self.current = result['item']
            self.current_image = result['image']
            self.current_path = result['paths'][0] if result['paths'] else ''
            self.canvas.show(self.current_image)
            self.filename_label.configure(text=f'{Path(self.current_path).name}  ·  {len(result["paths"])} Bilder übrig' if self.current_path else 'Alle erreichbaren Bilder durchgesehen.')
            if result['error']:
                self.status_label.configure(text='Bild konnte nicht geladen werden. Du kannst es vorläufig überspringen.')
            else:
                self.status_label.configure(text=message or ('Bereit. Mit den Pfeiltasten sortieren.' if self.current else 'Keine unbearbeiteten Bilder verfügbar. Die Löschliste bleibt gespeichert.'))
            if result['inaccessible']:
                self.status_label.configure(text=self.status_label.cget('text') + f'  {result["inaccessible"]} Einträge nicht lesbar.')
            self.update_controls()
            if after:
                after()
        self.run(work, done, 'Bilder werden geladen …')

    def key(self, event):
        if self.busy or event.state & 0x000C:
            return
        # A key must be released before it can make another sorting decision.
        if getattr(self, '_key_down', None) == event.keysym:
            return 'break'
        if event.keysym in KEY_ACTIONS:
            self._key_down = event.keysym
            self.root.bind('<KeyRelease-' + event.keysym + '>', lambda e: setattr(self, '_key_down', None))
            self.action(KEY_ACTIONS[event.keysym])
            return 'break'
        if event.keysym == 'Return':
            self.open_zoom()
            return 'break'

    def action(self, action):
        if self.busy or not self.current:
            return
        item = self.current
        if action in ('upper', 'lower') and not self.library.settings(self.source)[action + '_path']:
            self.settings()
            return
        def work():
            if action == 'keep':
                self.library.keep(item)
                return 'Behalten.'
            if action == 'stage':
                self.library.stage(item)
                return 'Zum Löschen vorgemerkt. Die Datei ist noch nicht gelöscht.'
            destination = self.library.move(item, action)
            return 'Verschoben nach ' + str(Path(destination).parent)
        self.run(work, lambda result, error: self.refresh(result) if not error else None, 'Entscheidung wird gespeichert …')

    def skip(self):
        if self.current_path and not self.busy:
            self.skipped.add(self.current_path)
            self.refresh('Vorläufig übersprungen. Beim nächsten Programmstart erscheint das Bild wieder.')

    def modal(self, title, size='1000x720'):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry(size)
        win.minsize(760, 520)
        win.configure(bg=BG)
        win.transient(self.root)
        win.grab_set()
        win.protocol('WM_DELETE_WINDOW', lambda: win.destroy() if not self.busy else messagebox.showinfo('FotoSwipe', 'Bitte den laufenden Vorgang abwarten.', parent=win))
        return win

    def settings(self):
        if self.busy:
            return
        if not self.source:
            self.choose_folder()
            if not self.source:
                return
        win = self.modal('Einstellungen', '900x600')
        cfg = self.library.settings(self.source)
        top = tk.Frame(win, bg=BG)
        top.pack(fill='both', expand=True, padx=24, pady=22)
        label(top, 'Deine Ordner', font=('Segoe UI', 18, 'bold')).pack(anchor='w', pady=(0, 16))
        label(top, 'Bilderordner: ' + self.source, anchor='w', wraplength=800, fg=MUTED).pack(fill='x', pady=8)
        variables = []
        for key, text in (('upper_path', '↑  Oberer Zielordner'), ('lower_path', '↓  Unterer Zielordner')):
            label(top, text).pack(anchor='w', pady=(14, 5))
            row = tk.Frame(top, bg=BG)
            row.pack(fill='x')
            variable = tk.StringVar(value=cfg[key])
            variables.append(variable)
            tk.Entry(row, textvariable=variable, state='readonly', readonlybackground=PANEL, fg=TEXT,
                     relief='flat', font=('Segoe UI', 10)).pack(side='left', fill='x', expand=True, ipady=11)
            def browse(value=variable):
                chosen = filedialog.askdirectory(title='Zielordner wählen oder neu anlegen', initialdir=value.get() or self.source, parent=win)
                if chosen:
                    value.set(chosen)
            button(row, 'Wählen / anlegen', browse, MINT).pack(side='right', padx=(8, 0))
        recursive = tk.BooleanVar(value=bool(cfg['recursive']))
        tk.Checkbutton(top, text='Unterordner mit durchsuchen', variable=recursive, bg=BG, fg=TEXT, selectcolor=PANEL,
                       activebackground=BG, activeforeground=TEXT, font=('Segoe UI', 10)).pack(anchor='w', pady=18)
        label(top, '↑ und ↓ verschieben die Bilddatei in den gewählten Ordner. Gleiche Dateinamen werden nummeriert.',
              wraplength=800, justify='left', fg=MUTED).pack(anchor='w', pady=4)
        row = tk.Frame(win, bg=BG)
        row.pack(fill='x', padx=24, pady=(0, 22))
        button(row, 'Exakte Duplikate suchen', lambda: (win.destroy(), self.open_duplicates()), MINT).pack(side='left')
        def reset():
            if messagebox.askyesno('Merkliste zurücksetzen?', 'Bereits bearbeitete Bilder dieses Ordners erneut anbieten? Die Löschliste und Dateien bleiben erhalten.', parent=win):
                self.library.reset(self.source)
                self.skipped.clear()
                win.destroy()
                self.refresh()
        button(row, 'Fortschritt zurücksetzen', reset, CORAL).pack(side='left', padx=8)
        def save():
            try:
                self.library.configure(self.source, variables[0].get(), variables[1].get(), recursive.get())
            except Exception as error:
                messagebox.showerror('FotoSwipe', str(error), parent=win)
                return
            win.destroy()
            self.skipped.clear()
            self.refresh('Ordner gespeichert.')
        button(row, 'Speichern', save, MINT).pack(side='right')

    def open_zoom(self, item=None):
        if self.busy or (item is None and self.current is None):
            return
        item = item or self.current
        win = tk.Toplevel(self.root)
        win.configure(bg=BG)
        win.title(Path(item.path).name)
        win.attributes('-fullscreen', True)
        win.grab_set()
        row = tk.Frame(win, bg=BG)
        row.pack(fill='x', padx=20, pady=10)
        label(row, Path(item.path).name).pack(side='left')
        button(row, 'Schließen  ·  Esc', win.destroy, MINT).pack(side='right')
        canvas = ImageCanvas(win, zoomable=True)
        canvas.pack(fill='both', expand=True, padx=12)
        bottom = tk.Frame(win, bg=BG)
        bottom.pack(fill='x', padx=20, pady=10)
        label(bottom, 'Mausrad: zoomen  ·  Ziehen: Ausschnitt verschieben  ·  Doppelklick: vergrößern / zurücksetzen', fg=MUTED).pack(side='left')
        button(bottom, 'Einpassen', canvas.reset).pack(side='right')
        win.bind('<Escape>', lambda e: win.destroy())
        if self.current and self.current.key == item.key:
            canvas.show(self.current_image)
        def done(result, error):
            if win.winfo_exists() and not error:
                canvas.show(result[1])
        self.run(lambda: load_photo(item.path, item.root, (4096, 4096)), done, 'Vollbild wird geladen …', parent=win)

    def open_queue(self):
        if self.busy or not self.source:
            return
        win = self.modal('Löschliste', '1080x760')
        label(win, 'Vorgemerkt ist noch nicht gelöscht. Bilder prüfen oder wieder behalten.', fg=MUTED).pack(anchor='w', padx=20, pady=16)
        body = tk.Frame(win, bg=BG)
        body.pack(fill='both', expand=True, padx=20)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        tree = ttk.Treeview(body, columns=('name', 'size'), show='headings', selectmode='extended')
        tree.heading('name', text='Datei'); tree.heading('size', text='Größe')
        tree.column('name', width=310); tree.column('size', width=80, stretch=False)
        tree.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(body, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=0, sticky='nse')
        canvas = ImageCanvas(body)
        canvas.grid(row=0, column=1, sticky='nsew', padx=(18, 0))
        entries = {}
        note = label(win, '', fg=MUTED, anchor='w')
        note.pack(fill='x', padx=20, pady=10)
        def refresh_list():
            if not win.winfo_exists():
                return
            tree.delete(*tree.get_children())
            entries.clear()
            for index, item in enumerate(self.library.pending(self.source)):
                key = str(index)
                entries[key] = item
                tree.insert('', 'end', iid=key, values=(os.path.relpath(item.path, item.root), readable_size(item.size)))
            note.configure(text=f'{len(entries)} Bilder vorgemerkt. Dateien außerhalb eines lokalen Papierkorbs bleiben bei Fehlern erhalten.')
            self.update_controls()
        def selected():
            return [entries[key] for key in tree.selection() if key in entries]
        def show_selected(event=None):
            items = selected()
            if not items or self.busy:
                return
            def done(result, error):
                if win.winfo_exists() and not error:
                    canvas.show(result)
            self.run(lambda: preview(items[0].path), done, 'Vorschau wird geladen …', parent=win)
        tree.bind('<<TreeviewSelect>>', show_selected)
        canvas.bind('<Double-Button-1>', lambda e: self.open_zoom(selected()[0]) if selected() else None)
        row = tk.Frame(win, bg=BG)
        row.pack(fill='x', padx=20, pady=(0, 18))
        def keep_selected():
            if self.busy:
                return
            for item in selected():
                self.library.keep_pending(item)
            refresh_list()
            self.refresh('Auswahl behalten und aus der Löschliste genommen.')
        button(row, 'Auswahl behalten', keep_selected, MINT).pack(side='left')
        def recycle():
            if self.busy:
                return
            items = list(entries.values())
            if not items or not messagebox.askyesno('In den Windows-Papierkorb verschieben?',
                    f'{len(items)} vorgemerkte Bilder in den Windows-Papierkorb verschieben?\n\nGeänderte oder nicht erreichbare Dateien bleiben in der Löschliste.', parent=win):
                return
            def progress(done, total):
                self.events.put(lambda d=done, t=total: note.configure(text=f'{d} von {t} verarbeitet') if win.winfo_exists() else None)
            def done(result, error):
                refresh_list()
                self.refresh()
                if not error:
                    success, errors = result
                    text = f'{len(success)} Bilder in den Windows-Papierkorb verschoben.'
                    if errors:
                        text += '\n\nNicht verarbeitet:\n' + '\n'.join(errors[:8])
                    messagebox.showinfo('FotoSwipe', text, parent=win)
            self.run(lambda: self.library.recycle(items, progress), done, 'Bilder werden in den Papierkorb verschoben …', parent=win)
        button(row, 'Alle vorgemerkten Bilder in Papierkorb', recycle, CORAL).pack(side='right')
        refresh_list()

    def open_duplicates(self):
        if self.busy or not self.source:
            return
        win = self.modal('Exakte Duplikate', '1100x780')
        label(win, 'Vergleicht vollständige Dateien. Gleiche Vorschauen allein reichen nicht aus.', fg=MUTED).pack(anchor='w', padx=20, pady=14)
        top = tk.Frame(win, bg=BG)
        top.pack(fill='x', padx=20)
        info = label(top, 'Bereit für die Suche.', fg=MUTED)
        info.pack(side='left')
        cancel = threading.Event()
        groups = []
        keepers = {}
        chosen = set()
        entries = {}
        body = tk.Frame(win, bg=BG)
        body.pack(fill='both', expand=True, padx=20, pady=12)
        tree = ttk.Treeview(body, columns=('file', 'choice'), show='tree headings', selectmode='browse')
        tree.heading('#0', text='Gruppe'); tree.heading('file', text='Datei'); tree.heading('choice', text='Entscheidung')
        tree.column('#0', width=150); tree.column('file', width=300); tree.column('choice', width=160)
        tree.pack(side='left', fill='both', expand=True)
        canvas = ImageCanvas(body, width=360)
        canvas.pack(side='right', fill='both', expand=True, padx=(16, 0))
        def refresh_tree():
            selected = tree.selection()
            tree.delete(*tree.get_children())
            entries.clear()
            for index, members in enumerate(groups):
                parent = f'g{index}'
                tree.insert('', 'end', iid=parent, text=f'Gruppe {index + 1}', values=(f'{len(members)} gleiche Dateien', 'Ausgewählt' if index in chosen else 'Nicht ausgewählt'), open=True)
                for j, item in enumerate(members):
                    key = f'{index}:{j}'
                    entries[key] = (index, j, item)
                    decision = 'BEHALTEN' if keepers[index] == j else ('Vormerken' if index in chosen else 'Zusätzliche Kopie')
                    tree.insert(parent, 'end', iid=key, values=(os.path.relpath(item.path, item.root), decision))
            if selected and tree.exists(selected[0]):
                tree.selection_set(selected[0])
        def show_selected(event=None):
            key = tree.selection()[0] if tree.selection() else ''
            if key not in entries or self.busy:
                return
            item = entries[key][2]
            self.run(lambda: preview(item.path), lambda result, error: canvas.show(result) if not error and win.winfo_exists() else None,
                     'Duplikat-Vorschau wird geladen …', parent=win)
        tree.bind('<<TreeviewSelect>>', show_selected)
        def zoom_selected(event=None):
            key = tree.selection()[0] if tree.selection() else ''
            if key in entries:
                self.open_zoom(entries[key][2])
        canvas.bind('<Double-Button-1>', zoom_selected)
        def search():
            if self.busy:
                return
            cancel.clear()
            def progress(done, total):
                self.events.put(lambda d=done, t=total: info.configure(text=f'{d} von {t} Kandidaten geprüft') if win.winfo_exists() else None)
            def done(result, error):
                if not win.winfo_exists():
                    return
                if error:
                    info.configure(text=str(error))
                    return
                matches, skipped = result
                groups[:] = matches
                keepers.clear(); chosen.clear()
                for i in range(len(groups)):
                    keepers[i] = 0
                refresh_tree()
                info.configure(text=f'{len(groups)} Gruppen gefunden · {skipped} Einträge ausgelassen. Keine Gruppe ist vorab ausgewählt.')
            self.run(lambda: self.library.duplicates(self.source, cancel, progress), done, 'Exakte Duplikate werden gesucht …', parent=win)
        button(top, 'Suche abbrechen', cancel.set, CORAL).pack(side='right')
        button(top, 'Suche starten', search, MINT).pack(side='right', padx=8)
        row = tk.Frame(win, bg=BG)
        row.pack(fill='x', padx=20, pady=(0, 18))
        def group_index():
            key = tree.selection()[0] if tree.selection() else ''
            if key.startswith('g'):
                return int(key[1:])
            return entries[key][0] if key in entries else None
        def toggle_group():
            if self.busy:
                return
            index = group_index()
            if index is not None:
                chosen.remove(index) if index in chosen else chosen.add(index)
                refresh_tree()
        def select_keeper():
            key = tree.selection()[0] if tree.selection() else ''
            if not self.busy and key in entries:
                index, j, _ = entries[key]
                keepers[index] = j
                refresh_tree()
        button(row, 'Gruppe auswählen / abwählen', toggle_group).pack(side='left')
        button(row, 'Dieses Exemplar behalten', select_keeper, MINT).pack(side='left', padx=8)
        def stage_groups():
            if self.busy or not chosen:
                return
            choices = [(groups[i], keepers[i]) for i in sorted(chosen)]
            def done(result, error):
                if not error:
                    win.destroy()
                    self.refresh(f'{result} Duplikate vorgemerkt. Löschen erst über die Löschliste.', after=self.open_queue)
            self.run(lambda: self.library.stage_duplicates(choices), done, 'Ausgewählte Duplikate werden erneut geprüft …', parent=win)
        button(row, 'Kopien zur Löschliste', stage_groups, CORAL).pack(side='right')

    def close(self):
        if self.busy:
            messagebox.showinfo('FotoSwipe', 'Bitte den laufenden Vorgang abwarten. Eine Suche kannst du über „Suche abbrechen“ beenden.', parent=self.root)
            return
        self.library.close()
        self.root.destroy()
