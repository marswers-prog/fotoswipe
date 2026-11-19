import hashlib
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock
from fotoswipe.core import KEY_ACTIONS, Cancelled, PhotoError, PhotoLibrary, Snapshot, normalized, snapshot


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.source, self.upper, self.lower, self.trash = [self.base / n for n in ('Bilder ü', 'Ziel oben', 'Ziel unten', 'Testpapierkorb')]
        for p in (self.source, self.upper, self.lower, self.trash):
            p.mkdir()
        self.lib = PhotoLibrary(self.base / 'state', recycler=lambda p: os.rename(p, self.trash / Path(p).name))
        self.lib.configure(self.source, self.upper, self.lower)

    def tearDown(self):
        self.lib.close()
        self.temp.cleanup()

    def photo(self, name='Bild.jpg', data=b'photo-data'):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return snapshot(path, self.source)

    def reload(self):
        self.lib.close()
        self.lib = PhotoLibrary(self.base / 'state', recycler=lambda p: os.rename(p, self.trash / Path(p).name))

    def test_four_keys(self):
        self.assertEqual(KEY_ACTIONS, {'Left': 'keep', 'Right': 'stage', 'Up': 'upper', 'Down': 'lower'})

    def test_keep_and_pending_survive_restart(self):
        kept, pending = self.photo('kept.jpg'), self.photo('pending.jpg')
        self.lib.keep(kept); self.lib.stage(pending)
        self.assertTrue(Path(pending.path).exists())
        self.reload()
        self.assertEqual(self.lib.counts(self.source), (1, 1))
        self.assertEqual(self.lib.files(self.source)[0], [])
        self.assertEqual(self.lib.pending(self.source)[0].sha256, pending.sha256)
        self.assertEqual(self.lib.settings(self.source)['upper_path'], normalized(self.upper))

    def test_large_progress_survives(self):
        item = self.photo()
        with self.lib.transaction():
            for i in range(2307):
                self.lib.db.execute('INSERT INTO reviewed VALUES(?,?,?,?)', (normalized(self.source), normalized(self.source / f'old-{i}.jpg'), 100, i))
        self.lib.stage(item)
        self.reload()
        self.assertEqual(self.lib.counts(self.source), (2307, 1))

    def test_reset_keeps_pending_and_files(self):
        a, b = self.photo('a.jpg'), self.photo('b.jpg')
        self.lib.keep(a); self.lib.stage(b)
        self.lib.reset(self.source)
        self.assertEqual(self.lib.counts(self.source), (0, 1))
        self.assertEqual(self.lib.files(self.source)[0], [a.path])
        self.assertTrue(Path(b.path).exists())

    def test_keep_pending_never_changes_file(self):
        item = self.photo()
        self.lib.stage(item); self.lib.keep_pending(item)
        self.assertEqual(self.lib.counts(self.source), (1, 0))
        self.assertEqual(Path(item.path).read_bytes(), b'photo-data')

    def test_folder_sessions_are_separate(self):
        item = self.photo(); self.lib.keep(item)
        self.lib.configure(self.upper)
        self.assertEqual(self.lib.counts(self.upper), (0, 0))
        self.assertEqual(self.lib.counts(self.source), (1, 0))

    def test_recursive_scan_excludes_destination_folders(self):
        nested = self.source / 'Sortiert'; nested.mkdir()
        (nested / 'processed.jpg').write_bytes(b'done')
        item = self.photo('Unterordner/incoming.jpg')
        self.lib.configure(self.source, nested, self.lower, recursive=True)
        self.assertEqual(self.lib.files(self.source)[0], [item.path])

    def test_no_following_symlink(self):
        outside = self.upper / 'outside.jpg'; outside.write_bytes(b'outside')
        link = self.source / 'linked.jpg'
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest('Symlinks unavailable in this Windows account')
        self.assertEqual(self.lib.files(self.source)[0], [])
        with self.assertRaises(PhotoError): snapshot(link, self.source)
        self.assertEqual(outside.read_bytes(), b'outside')

    def test_move_does_not_overwrite_and_preserves_bytes(self):
        item = self.photo('Sommer ü.jpg')
        collision = self.upper / Path(item.path).name
        collision.write_bytes(b'do-not-overwrite')
        target = self.lib.move(item, 'upper')
        self.assertEqual(Path(target).name, 'Sommer ü (1).jpg')
        self.assertEqual(collision.read_bytes(), b'do-not-overwrite')
        self.assertEqual(Path(target).read_bytes(), b'photo-data')
        self.assertFalse(Path(item.path).exists())
        self.assertEqual(self.lib.counts(self.source), (1, 0))

    def test_copy_failure_preserves_source_and_collision(self):
        item = self.photo()
        collision = self.upper / Path(item.path).name; collision.write_bytes(b'existing')
        with mock.patch('fotoswipe.core.os.fsync', side_effect=OSError('Synthetic disk-full error')):
            with self.assertRaises(OSError): self.lib.move(item, 'upper')
        self.assertEqual(Path(item.path).read_bytes(), b'photo-data')
        self.assertEqual(collision.read_bytes(), b'existing')
        self.assertEqual(list(self.upper.glob('.FotoSwipe-*')), [])

    def test_source_removal_failure_rolls_back_owned_target_copy(self):
        item = self.photo()
        original_unlink = Path.unlink
        def failing_unlink(path, *args, **kwargs):
            if normalized(path) == normalized(item.path):
                raise PermissionError('Synthetic file lock')
            return original_unlink(path, *args, **kwargs)
        with mock.patch.object(Path, 'unlink', failing_unlink):
            with self.assertRaises(PermissionError): self.lib.move(item, 'lower')
        self.assertEqual(Path(item.path).read_bytes(), b'photo-data')
        self.assertEqual(list(self.lower.iterdir()), [])

    def test_recover_completed_move_without_losing_progress(self):
        item = self.photo()
        destination = self.upper / 'Bild.jpg'; destination.write_bytes(Path(item.path).read_bytes())
        self.lib._operation('crash', item, 'move', str(destination), str(self.upper / '.FotoSwipe-crash.tmp'), 'ready')
        Path(item.path).unlink()
        self.reload()
        self.assertTrue(destination.exists())
        self.assertEqual(self.lib.counts(self.source), (1, 0))

    def test_recover_unfinished_copy_keeps_other_file(self):
        item = self.photo()
        destination = self.upper / 'Bild.jpg'; destination.write_bytes(b'existing-user-file')
        staging = self.upper / '.FotoSwipe-crash.tmp'; staging.write_bytes(b'partial')
        self.lib._operation('crash', item, 'move', str(destination), str(staging), 'copying')
        self.reload()
        self.assertEqual(destination.read_bytes(), b'existing-user-file')
        self.assertTrue(Path(item.path).exists())
        self.assertFalse(staging.exists())

    def test_changed_pending_file_is_never_recycled(self):
        item = self.photo(data=b'AAAA'); self.lib.stage(item)
        Path(item.path).write_bytes(b'BBBB')
        os.utime(item.path, ns=(item.mtime_ns, item.mtime_ns))
        succeeded, errors = self.lib.recycle([item])
        self.assertEqual(succeeded, [])
        self.assertEqual(len(errors), 1)
        self.assertEqual(Path(item.path).read_bytes(), b'BBBB')
        self.assertEqual(self.lib.counts(self.source), (0, 1))

    def test_partial_recycle_keeps_failed_entries(self):
        a, b = self.photo('a.jpg'), self.photo('b.jpg')
        self.lib.stage(a); self.lib.stage(b)
        def recycle(path):
            if Path(path).name == 'b.jpg': raise PermissionError('Synthetic recycle failure')
            os.rename(path, self.trash / Path(path).name)
        self.lib.recycler = recycle
        succeeded, errors = self.lib.recycle([a, b])
        self.assertEqual(len(succeeded), 1); self.assertEqual(len(errors), 1)
        self.assertEqual(self.lib.counts(self.source), (1, 1))
        self.assertTrue(Path(b.path).exists()); self.assertTrue((self.trash / 'a.jpg').exists())

    def test_recycle_crash_recovery_does_not_delete_again(self):
        item = self.photo(); self.lib.stage(item)
        self.lib._operation('crash', item, 'recycle')
        os.rename(item.path, self.trash / 'saved.jpg')
        self.reload()
        self.assertEqual(self.lib.counts(self.source), (1, 0))
        self.assertTrue((self.trash / 'saved.jpg').exists())

    def test_exact_duplicates_use_bytes_not_only_hashes(self):
        self.photo('a.jpg', b'same'); self.photo('b.jpg', b'same'); self.photo('c.jpg', b'diff')
        class SameHash:
            def update(self, data): pass
            def hexdigest(self): return 'same-fake-hash'
        with mock.patch('fotoswipe.core.hashlib.sha256', return_value=SameHash()):
            groups, _ = self.lib.duplicates(self.source, threading.Event())
        self.assertEqual(len(groups), 1)
        self.assertEqual({Path(i.path).name for i in groups[0]}, {'a.jpg', 'b.jpg'})

    def test_duplicate_stage_retains_keeper_and_unrelated_queue(self):
        a, b, other = self.photo('a.jpg'), self.photo('b.jpg'), self.photo('other.jpg', b'other')
        self.lib.stage(a); self.lib.stage(other)
        self.lib.stage_duplicates([([a, b], 0)])
        self.assertEqual({Path(i.path).name for i in self.lib.pending(self.source)}, {'b.jpg', 'other.jpg'})
        self.assertTrue(Path(a.path).exists()); self.assertTrue(Path(b.path).exists())
        self.assertEqual(self.lib.counts(self.source), (1, 2))

    def test_invalid_duplicate_plan_does_not_store_any_choices(self):
        a, b = self.photo('a.jpg'), self.photo('b.jpg')
        with self.assertRaises(PhotoError): self.lib.stage_duplicates([([a, b], 4)])
        self.assertEqual(self.lib.counts(self.source), (0, 0))
        Path(b.path).write_bytes(b'changed')
        with self.assertRaises(PhotoError): self.lib.stage_duplicates([([a, b], 0)])
        self.assertEqual(self.lib.counts(self.source), (0, 0))

    def test_cancellation_changes_nothing(self):
        self.photo('a.jpg'); self.photo('b.jpg')
        stop = threading.Event(); stop.set()
        with self.assertRaises(Cancelled): self.lib.duplicates(self.source, stop)
        self.assertEqual(self.lib.counts(self.source), (0, 0))


if __name__ == '__main__': unittest.main()
