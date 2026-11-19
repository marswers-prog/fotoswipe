"""Folder-based photo review. All destructive operations use verified snapshots."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sqlite3
import threading
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tif', '.tiff', '.heic', '.heif', '.avif'}
KEY_ACTIONS = {'Left': 'keep', 'Right': 'stage', 'Up': 'upper', 'Down': 'lower'}


class PhotoError(Exception):
    pass


class Cancelled(PhotoError):
    pass


def normalized(path) -> str:
    return os.path.normcase(str(Path(path).resolve()))


def within(path, root) -> bool:
    try:
        return os.path.commonpath([normalized(path), normalized(root)]) == normalized(root)
    except ValueError:
        return False


def linklike(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())


@dataclass(frozen=True)
class Snapshot:
    root: str
    path: str
    size: int
    mtime_ns: int
    sha256: str

    @property
    def key(self):
        return (normalized(self.path), self.size, self.mtime_ns)


def checked_file(path, root):
    p, r = Path(path), Path(root)
    if not p.is_file() or not within(p, r):
        raise PhotoError('Die Datei ist nicht mehr im gewählten Bilderordner verfügbar.')
    current = p
    while current != r and current != current.parent:
        if linklike(current):
            raise PhotoError('Verknüpfungen werden zum Schutz anderer Ordner ausgelassen.')
        current = current.parent
    return p


def snapshot(path, root, cancel: threading.Event | None = None) -> Snapshot:
    p = checked_file(path, root)
    before = p.stat()
    digest = hashlib.sha256()
    with p.open('rb') as stream:
        while True:
            if cancel and cancel.is_set():
                raise Cancelled('Vorgang abgebrochen.')
            data = stream.read(1024 * 1024)
            if not data:
                break
            digest.update(data)
        after = os.fstat(stream.fileno())
    final = p.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or (after.st_size, after.st_mtime_ns) != (final.st_size, final.st_mtime_ns):
        raise PhotoError('Das Bild wurde während des Lesens verändert. Bitte erneut laden.')
    return Snapshot(str(Path(root).resolve()), str(p.resolve()), final.st_size, final.st_mtime_ns, digest.hexdigest())


def validate(item: Snapshot, cancel=None):
    actual = snapshot(item.path, item.root, cancel)
    if actual.key != item.key or actual.sha256 != item.sha256 or normalized(actual.root) != normalized(item.root):
        raise PhotoError('Die Datei wurde seit der Anzeige verändert. Sie bleibt unangetastet: ' + Path(item.path).name)
    return actual


def equal_files(first, second, cancel=None):
    with open(first, 'rb') as a, open(second, 'rb') as b:
        while True:
            if cancel and cancel.is_set():
                raise Cancelled('Suche abgebrochen.')
            x, y = a.read(1024 * 1024), b.read(1024 * 1024)
            if x != y:
                return False
            if not x:
                return True


class PhotoLibrary:
    def __init__(self, data_dir, recycler: Callable[[str], None] | None = None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(self.data_dir / 'fortschritt.sqlite3'), check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS settings(root TEXT PRIMARY KEY, upper_path TEXT NOT NULL DEFAULT '', lower_path TEXT NOT NULL DEFAULT '', recursive INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reviewed(root TEXT NOT NULL, path TEXT NOT NULL, size INTEGER NOT NULL, mtime INTEGER NOT NULL, PRIMARY KEY(root,path,size,mtime));
            CREATE TABLE IF NOT EXISTS pending(root TEXT NOT NULL, path TEXT NOT NULL, size INTEGER NOT NULL, mtime INTEGER NOT NULL, sha TEXT NOT NULL, PRIMARY KEY(root,path));
            CREATE TABLE IF NOT EXISTS duplicate_guards(root TEXT NOT NULL, path TEXT NOT NULL, keeper TEXT NOT NULL, PRIMARY KEY(root,path));
            CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY, root TEXT NOT NULL, kind TEXT NOT NULL, source TEXT NOT NULL, destination TEXT NOT NULL, staging TEXT NOT NULL, size INTEGER NOT NULL, mtime INTEGER NOT NULL, sha TEXT NOT NULL, phase TEXT NOT NULL);
        ''')
        self.recycler = recycler or windows_recycle
        self.recover()
        backup = sqlite3.connect(str(self.data_dir / 'fortschritt-backup.sqlite3'))
        try:
            self.db.backup(backup)
        finally:
            backup.close()

    @contextlib.contextmanager
    def transaction(self):
        with self.lock:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                yield
                self.db.execute('COMMIT')
            except BaseException:
                self.db.execute('ROLLBACK')
                raise

    def close(self):
        with self.lock:
            self.db.close()

    def last_root(self):
        with self.lock:
            row = self.db.execute("SELECT value FROM meta WHERE key='last_root'").fetchone()
            return row[0] if row else ''

    def configure(self, root, upper='', lower='', recursive=False):
        root = normalized(root)
        if not Path(root).is_dir():
            raise PhotoError('Der Bilderordner ist nicht erreichbar.')
        targets = [normalized(p) if p else '' for p in (upper, lower)]
        if any(p and p == root for p in targets):
            raise PhotoError('Ein Zielordner muss sich vom Bilderordner unterscheiden.')
        if targets[0] and targets[0] == targets[1]:
            raise PhotoError('Bitte zwei unterschiedliche Zielordner wählen.')
        for p in targets:
            if p and not Path(p).is_dir():
                raise PhotoError('Ein Zielordner ist nicht erreichbar: ' + p)
        with self.transaction():
            self.db.execute('INSERT OR REPLACE INTO settings VALUES(?,?,?,?)', (root, *targets, int(recursive)))
            self.db.execute("INSERT OR REPLACE INTO meta VALUES('last_root',?)", (root,))
        return self.settings(root)

    def settings(self, root):
        root = normalized(root)
        with self.lock:
            row = self.db.execute('SELECT * FROM settings WHERE root=?', (root,)).fetchone()
        return dict(row) if row else dict(root=root, upper_path='', lower_path='', recursive=0)

    def files(self, root, include_reviewed=False):
        root = normalized(root)
        cfg = self.settings(root)
        targets = [p for p in (cfg['upper_path'], cfg['lower_path']) if p and within(p, root)]
        with self.lock:
            reviewed = {(r['path'], r['size'], r['mtime']) for r in self.db.execute('SELECT path,size,mtime FROM reviewed WHERE root=?', (root,))}
            pending = {r[0] for r in self.db.execute('SELECT path FROM pending WHERE root=?', (root,))}
        result, skipped = [], 0
        stack = [Path(root)]
        while stack:
            folder = stack.pop()
            try:
                children = sorted(folder.iterdir(), key=lambda p: p.name.casefold())
            except OSError:
                skipped += 1
                continue
            for p in children:
                try:
                    if linklike(p):
                        continue
                    if p.is_dir():
                        if cfg['recursive'] and not any(within(p, t) for t in targets):
                            stack.append(p)
                    elif p.suffix.lower() in EXTENSIONS and p.is_file():
                        st = p.stat()
                        key = (normalized(p), st.st_size, st.st_mtime_ns)
                        if include_reviewed or (key not in reviewed and normalized(p) not in pending):
                            result.append(str(p.resolve()))
                except OSError:
                    skipped += 1
        return sorted(result, key=lambda p: os.path.relpath(p, root).casefold()), skipped

    def counts(self, root):
        root = normalized(root)
        with self.lock:
            return tuple(self.db.execute('SELECT COUNT(*) FROM ' + table + ' WHERE root=?', (root,)).fetchone()[0] for table in ('reviewed', 'pending'))

    def _review(self, item):
        self.db.execute('INSERT OR IGNORE INTO reviewed VALUES(?,?,?,?)', (normalized(item.root), *item.key))

    def keep(self, item):
        validate(item)
        with self.transaction():
            self._review(item)
            self.db.execute('DELETE FROM pending WHERE root=? AND path=?', (normalized(item.root), normalized(item.path)))
            self.db.execute('DELETE FROM duplicate_guards WHERE root=? AND path=?', (normalized(item.root), normalized(item.path)))

    def stage(self, item):
        validate(item)
        with self.transaction():
            self._stage(item)

    def _stage(self, item, keeper=None):
        self.db.execute('INSERT OR REPLACE INTO pending VALUES(?,?,?,?,?)', (normalized(item.root), normalized(item.path), item.size, item.mtime_ns, item.sha256))
        self.db.execute('DELETE FROM duplicate_guards WHERE root=? AND path=?', (normalized(item.root), normalized(item.path)))
        if keeper is not None:
            self.db.execute('INSERT INTO duplicate_guards VALUES(?,?,?)', (normalized(item.root), normalized(item.path), json.dumps(asdict(keeper))))

    def pending(self, root):
        root = normalized(root)
        with self.lock:
            return [Snapshot(root, r['path'], r['size'], r['mtime'], r['sha']) for r in self.db.execute('SELECT * FROM pending WHERE root=? ORDER BY rowid', (root,))]

    def keep_pending(self, item):
        # This only changes the saved choice; it never changes a file.
        with self.transaction():
            self._review(item)
            self.db.execute('DELETE FROM pending WHERE root=? AND path=?', (normalized(item.root), normalized(item.path)))
            self.db.execute('DELETE FROM duplicate_guards WHERE root=? AND path=?', (normalized(item.root), normalized(item.path)))

    def reset(self, root):
        with self.transaction():
            self.db.execute('DELETE FROM reviewed WHERE root=?', (normalized(root),))

    def _operation(self, op_id, item, kind, destination='', staging='', phase='planned'):
        with self.transaction():
            self.db.execute('INSERT OR REPLACE INTO operations VALUES(?,?,?,?,?,?,?,?,?,?)',
                            (op_id, normalized(item.root), kind, item.path, destination, staging, item.size, item.mtime_ns, item.sha256, phase))

    def _finish(self, op_id, item):
        with self.transaction():
            self._review(item)
            self.db.execute('DELETE FROM pending WHERE root=? AND path=?', (normalized(item.root), normalized(item.path)))
            self.db.execute('DELETE FROM duplicate_guards WHERE root=? AND path=?', (normalized(item.root), normalized(item.path)))
            self.db.execute('DELETE FROM operations WHERE id=?', (op_id,))

    def _clear(self, op_id):
        with self.transaction():
            self.db.execute('DELETE FROM operations WHERE id=?', (op_id,))

    def move(self, item, direction):
        validate(item)
        if direction not in ('upper', 'lower'):
            raise PhotoError('Ungültiger Zielordner.')
        target = self.settings(item.root)[direction + '_path']
        if not target or normalized(target) == normalized(Path(item.path).parent):
            raise PhotoError('Bitte zuerst einen anderen Zielordner in den Einstellungen wählen.')
        if not Path(target).is_dir():
            raise PhotoError('Der Zielordner ist nicht erreichbar.')
        source = Path(item.path)
        op_id = uuid.uuid4().hex
        staging = Path(target) / ('.FotoSwipe-' + op_id + '.tmp')
        destination = Path(target) / source.name
        self._operation(op_id, item, 'move', str(destination), str(staging), 'copying')
        try:
            digest = hashlib.sha256()
            with source.open('rb') as src, staging.open('xb') as dst:
                while True:
                    block = src.read(1024 * 1024)
                    if not block:
                        break
                    digest.update(block)
                    dst.write(block)
                dst.flush()
                os.fsync(dst.fileno())
            if digest.hexdigest() != item.sha256:
                raise PhotoError('Die Quelldatei wurde verändert. Verschieben wurde abgebrochen.')
            os.utime(staging, ns=(source.stat().st_atime_ns, item.mtime_ns))
            for suffix in range(100000):
                name = source.name if suffix == 0 else f'{source.stem} ({suffix}){source.suffix}'
                destination = Path(target) / name
                if destination.exists():
                    continue
                self._operation(op_id, item, 'move', str(destination), str(staging), 'ready')
                try:
                    if os.name == 'nt':
                        os.rename(staging, destination)  # Windows fails if destination exists.
                    else:
                        os.link(staging, destination)    # Test path: atomic, no-overwrite publish.
                        staging.unlink()
                    break
                except FileExistsError:
                    continue
            else:
                raise PhotoError('Es konnte kein freier Dateiname gefunden werden.')
            validate(item)
            if snapshot(destination, target).sha256 != item.sha256:
                raise PhotoError('Die Zielkopie konnte nicht vollständig geprüft werden.')
            source.unlink()  # Only after the complete target file has been verified.
            self._finish(op_id, item)
            return str(destination)
        except BaseException:
            self.recover()
            raise

    def recover(self):
        with self.lock:
            operations = [dict(r) for r in self.db.execute('SELECT * FROM operations')]
        for row in operations:
            item = Snapshot(row['root'], row['source'], row['size'], row['mtime'], row['sha'])
            src = Path(item.path)
            if row['kind'] == 'recycle':
                if not src.exists():
                    self._finish(row['id'], item)
                else:
                    self._clear(row['id'])  # Never automatically repeat a deletion.
                continue
            dst, stage = Path(row['destination']), Path(row['staging'])
            if not src.exists():
                if dst.is_file() and snapshot(dst, dst.parent).sha256 == item.sha256:
                    self._finish(row['id'], item)
                    continue
                raise PhotoError('Ein unterbrochener Verschiebevorgang muss geprüft werden: ' + str(dst))
            if stage.exists():
                if dst.exists() and os.path.samefile(stage, dst):
                    dst.unlink()
                if stage.name == '.FotoSwipe-' + row['id'] + '.tmp':
                    stage.unlink()  # Only our own unfinished copy; the source still exists.
            elif row['phase'] == 'ready' and dst.exists():
                if snapshot(dst, dst.parent).sha256 != item.sha256:
                    raise PhotoError('Die Zielkopie eines unterbrochenen Vorgangs wurde verändert: ' + str(dst))
                dst.unlink()
            self._clear(row['id'])

    def recycle(self, items, progress=lambda done, total: None):
        succeeded, errors = [], []
        for index, item in enumerate(items):
            op_id = uuid.uuid4().hex
            try:
                with self.lock:
                    row = self.db.execute('SELECT * FROM pending WHERE root=? AND path=?', (normalized(item.root), normalized(item.path))).fetchone()
                if not row or (row['size'], row['mtime'], row['sha']) != (item.size, item.mtime_ns, item.sha256):
                    raise PhotoError('Die Vormerkung ist nicht mehr aktuell.')
                validate(item)
                with self.lock:
                    guard = self.db.execute('SELECT keeper FROM duplicate_guards WHERE root=? AND path=?', (normalized(item.root), normalized(item.path))).fetchone()
                if guard:
                    keeper = Snapshot(**json.loads(guard['keeper']))
                    validate(keeper)
                    if not equal_files(item.path, keeper.path):
                        raise PhotoError('Das zu behaltende Duplikat ist nicht mehr identisch. Bitte erneut prüfen.')
                self._operation(op_id, item, 'recycle')
                self.recycler(item.path)
                if Path(item.path).exists():
                    raise PhotoError('Windows hat die Datei nicht in den Papierkorb verschoben.')
                self._finish(op_id, item)
                succeeded.append(item.path)
            except Exception as error:
                self.recover()
                errors.append(Path(item.path).name + ': ' + str(error))
            progress(index + 1, len(items))
        return succeeded, errors

    def duplicates(self, root, cancel, progress=lambda done, total: None):
        paths, skipped = self.files(root, include_reviewed=True)
        by_size = {}
        for path in paths:
            try:
                by_size.setdefault(Path(path).stat().st_size, []).append(path)
            except OSError:
                skipped += 1
        candidates = [p for size, group in by_size.items() if size > 0 and len(group) > 1 for p in group]
        by_hash = {}
        for index, path in enumerate(candidates):
            if cancel.is_set():
                raise Cancelled('Suche abgebrochen. Es wurde nichts verändert.')
            try:
                value = snapshot(path, root, cancel)
                by_hash.setdefault((value.size, value.sha256), []).append(value)
            except Cancelled:
                raise
            except (OSError, PhotoError):
                skipped += 1
            progress(index + 1, len(candidates))
        groups = []
        for matches in by_hash.values():
            if len(matches) < 2:
                continue
            confirmed = []
            for candidate in matches:
                placed = False
                for group in confirmed:
                    if equal_files(group[0].path, candidate.path, cancel):
                        group.append(candidate)
                        placed = True
                        break
                if not placed:
                    confirmed.append([candidate])
            groups.extend(g for g in confirmed if len(g) > 1)
        return groups, skipped

    def stage_duplicates(self, choices):
        # Revalidate every group, including each keeper, before storing choices.
        staged, kept, seen = [], [], set()
        guards = {}
        for members, keeper_index in choices:
            if len(members) < 2 or not 0 <= keeper_index < len(members):
                raise PhotoError('Ungültige Duplikat-Auswahl.')
            if len({normalized(m.path) for m in members}) != len(members):
                raise PhotoError('Eine Gruppe enthält dieselbe Datei mehrfach.')
            keeper = members[keeper_index]
            for member in members:
                if normalized(member.path) in seen:
                    raise PhotoError('Die Duplikat-Gruppen überschneiden sich.')
                seen.add(normalized(member.path))
                validate(member)
                if not equal_files(keeper.path, member.path):
                    raise PhotoError('Die Dateien sind nicht mehr identisch. Bitte erneut suchen.')
            kept.append(keeper)
            for i, member in enumerate(members):
                if i != keeper_index:
                    staged.append(member)
                    guards[member.path] = keeper
        with self.transaction():
            for member in staged:
                self._stage(member, guards[member.path])
            for keeper in kept:
                self._review(keeper)
                self.db.execute('DELETE FROM pending WHERE root=? AND path=?', (normalized(keeper.root), normalized(keeper.path)))
                self.db.execute('DELETE FROM duplicate_guards WHERE root=? AND path=?', (normalized(keeper.root), normalized(keeper.path)))
        return len(staged)


def windows_recycle(path):
    if os.name != 'nt':
        raise PhotoError('Der Windows-Papierkorb ist hier nicht verfügbar.')
    import ctypes
    root = Path(path).anchor
    ctypes.windll.kernel32.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
    ctypes.windll.kernel32.GetDriveTypeW.restype = ctypes.c_uint
    if ctypes.windll.kernel32.GetDriveTypeW(root) != 3:
        raise PhotoError('Für diesen Datenträger wird kein sicherer Windows-Papierkorb verwendet. Die Datei bleibt vorgemerkt.')
    # Explicit modern backend: never fall back to SHFileOperation / permanent deletion.
    from send2trash.win.modern import send2trash
    send2trash(str(Path(path).resolve()))
