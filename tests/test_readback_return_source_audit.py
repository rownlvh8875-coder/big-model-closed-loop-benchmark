"""Run audit validation on real zip bytes and the existing pure environment guard."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile
try:
    from scripts import audit_readback_return_source as audit
except ImportError:
    audit=None

class ReturnSourceAuditTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(audit,'static return-boundary audit required')
    def test_wheel_member_must_match_exactly_one_installed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            wheel=Path(tmp)/'fixture.whl'
            with zipfile.ZipFile(wheel,'w') as z:z.writestr('panda3d/fixture.so',b'elf')
            sha=hashlib.sha256(b'elf').hexdigest()
            entry=dict(path='/opt/venv/lib/python3.11/site-packages/panda3d/fixture.so',kind='file',nbytes=3,sha256=sha)
            self.assertEqual(audit.verified_member(wheel,'panda3d/fixture.so',[entry],sha,3),b'elf')
            for entries in ([],[entry,entry],[entry|{'sha256':'0'*64}],[entry|{'nbytes':4}],[entry|{'kind':'symlink'}]):
                with self.subTest(entries=entries),self.assertRaises(ValueError):audit.verified_member(wheel,'panda3d/fixture.so',entries,sha,3)
            with self.assertRaises(ValueError):audit.verified_member(wheel,'panda3d/fixture.so',[entry],'0'*64,3)
    def test_duplicate_zip_member_cannot_be_an_audited_identity(self):
        import warnings
        with tempfile.TemporaryDirectory() as tmp:
            wheel=Path(tmp)/'fixture.whl'
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning)
                with zipfile.ZipFile(wheel,'w') as z:
                    z.writestr('panda3d/fixture.so',b'elf');z.writestr('panda3d/fixture.so',b'elf')
            with self.assertRaises(ValueError):audit.verified_member(wheel,'panda3d/fixture.so',[],hashlib.sha256(b'elf').hexdigest(),3)
    def test_existing_environment_guard_rejects_preload_without_relaxation(self):
        result=audit.probe_environment()
        self.assertTrue(result['baseline_accepted']);self.assertTrue(result['added_preload_rejected'])
        self.assertIs(result['runtime_admission_ready'],False)

if __name__=='__main__':unittest.main()
