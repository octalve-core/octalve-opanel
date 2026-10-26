import hashlib
import tempfile
from pathlib import Path
from unittest import TestCase
from native_agent.filesystem import AccountFiles, Refused

class HostingBackupTests(TestCase):
    def test_snapshot_restores_actual_bytes_and_empty_directories(self):
        from native_agent.backups import capture, restore
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); fs=AccountFiles(root)
            try:
                fs.mkdir('empty'); fs.write('hello.txt',b'original')
                archive=capture(fs,service_id=13)
                fs.write('hello.txt',b'changed',expected=hashlib.sha256(b'original').hexdigest())
                result=restore(fs,archive,service_id=13,target='recovered',expected_digest=hashlib.sha256(archive).hexdigest())
                self.assertEqual(result['status'],'restored_to_new_directory')
                self.assertEqual((root/'recovered/hello.txt').read_bytes(),b'original')
                self.assertTrue((root/'recovered/empty').is_dir())
                self.assertEqual((root/'hello.txt').read_bytes(),b'changed')
            finally: fs.close()
    def test_wrong_service_corruption_and_overwrite_refused(self):
        from native_agent.backups import capture, restore
        with tempfile.TemporaryDirectory() as tmp:
            fs=AccountFiles(tmp)
            try:
                fs.write('file',b'important'); archive=capture(fs,service_id=13)
                digest=hashlib.sha256(archive).hexdigest()
                for data,service,target in ((archive,14,'new'),(archive+b'x',13,'new'),(archive,13,'file')):
                    with self.assertRaises(Refused): restore(fs,data,service_id=service,target=target,expected_digest=digest)
                self.assertEqual(fs.read('file'),b'important')
                self.assertFalse((Path(tmp)/'new').exists())
            finally: fs.close()
    def test_symlinks_not_followed_by_backup(self):
        from native_agent.backups import capture
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'link').symlink_to('/etc/passwd'); fs=AccountFiles(tmp)
            try:
                with self.assertRaises(Refused): capture(fs,service_id=13)
            finally: fs.close()
    def test_long_filename_manifest_roundtrip(self):
        from native_agent.backups import capture, validated
        with tempfile.TemporaryDirectory() as tmp:
            fs=AccountFiles(tmp)
            try:
                for i in range(850): fs.write(str(i).zfill(4)+'x'*220,b'x')
                archive=capture(fs,service_id=13)
                rows=validated(archive,service_id=13,expected_digest=hashlib.sha256(archive).hexdigest())
                self.assertEqual(len(rows),850)
            finally: fs.close()
    def test_restore_target_path_budget_checked_before_writes(self):
        from native_agent.backups import capture, restore
        with tempfile.TemporaryDirectory() as tmp:
            fs=AccountFiles(tmp)
            try:
                for depth in range(1,33): fs.mkdir('/'.join(['d']*depth))
                archive=capture(fs,service_id=13)
                with self.assertRaises(Refused): restore(fs,archive,service_id=13,target='new',expected_digest=hashlib.sha256(archive).hexdigest())
                self.assertFalse((Path(tmp)/'new').exists())
            finally: fs.close()
