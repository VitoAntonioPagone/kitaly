import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import backup_kitaly as backup


class BackupStorageTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.backups = self.root / 'backups'
        self.backups.mkdir()
        (self.root / '.env').write_text('DATABASE_URL=mysql+pymysql://test@localhost/test\n')

    def tearDown(self):
        self.directory.cleanup()

    def archive(self, name, age_days=0, size=10):
        path = self.backups / ('kitaly_backup_' + name + '.tar.gz')
        path.write_bytes(b'x' * size)
        timestamp = time.time() - age_days * 86400
        os.utime(path, (timestamp, timestamp))
        return path

    def arguments(self):
        return patch('sys.argv', ['backup', '--project-dir', str(self.root),
                                 '--backup-dir', str(self.backups)])

    def test_budget_removes_oldest_and_preserves_latest(self):
        oldest = self.archive('old', age_days=3)
        middle = self.archive('middle', age_days=2)
        latest = self.archive('latest', age_days=1)
        removed = backup.prune_old_backups(self.backups, 30, max_bytes=15)
        self.assertEqual(removed, [oldest.name, middle.name])
        self.assertTrue(latest.exists())

    def test_retention_never_removes_only_recovery_point(self):
        only = self.archive('only', age_days=40, size=100)
        self.assertEqual(backup.prune_old_backups(self.backups, 30, max_bytes=1), [])
        self.assertTrue(only.exists())

    def test_age_limit_applies_under_budget(self):
        old = self.archive('old', age_days=31)
        new = self.archive('new')
        self.assertEqual(backup.prune_old_backups(self.backups, 30), [old.name])
        self.assertTrue(new.exists())

    def test_full_disk_stops_before_dump_and_preserves_backups(self):
        existing = self.archive('existing')
        with self.arguments(), patch.object(backup.shutil, 'disk_usage', return_value=SimpleNamespace(free=1)), \
                patch.object(backup, 'run_mysqldump') as dump:
            with self.assertRaisesRegex(SystemExit, 'Insufficient disk space'):
                backup.main()
        dump.assert_not_called()
        self.assertTrue(existing.exists())

    def test_failed_archive_cleans_partial_and_preserves_recovery_point(self):
        existing = self.archive('existing')
        def dump(database, destination):
            destination.write_text('test dump')
        def fail(archive, source, arcname):
            raise OSError('disk write failed')
        with self.arguments(), patch.object(backup.shutil, 'disk_usage', return_value=SimpleNamespace(free=10**12)), \
                patch.object(backup, 'run_mysqldump', side_effect=dump), \
                patch.object(backup, 'add_directory_to_tar', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'disk write failed'):
                backup.main()
        self.assertEqual(list(self.backups.iterdir()), [existing])


if __name__ == '__main__':
    unittest.main()
