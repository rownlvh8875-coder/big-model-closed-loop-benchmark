from pathlib import Path
import unittest
try:
    from scripts import panda_sdk_image_binding as image
except ImportError:image=None
NEW='a'*64;OLD='b'*64
class ImageBindingTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(image,'new SDK image membership check required')
    def entries(self,sdk):return [dict(path='/opt/python/lib/libpython3.11.so.1.0',kind='file',sha256='c'*64),dict(path='/opt/python/lib/python3.11/site-packages/metadrive/__init__.py',kind='file',sha256='d'*64),dict(path='/opt/python/lib/python3.11/site-packages/panda3d/libpandagl.so',kind='file',sha256=sdk)]
    def test_old_accepted_image_is_not_new_sdk_image(self):
        r=image.compare_installed(self.entries(OLD),NEW);self.assertFalse(r['candidate_sdk_installed']);self.assertIn('CANDIDATE_SDK_NOT_INSTALLED',r['blockers']);self.assertEqual(r['panda_gl_files'][0]['sha256'],OLD)
    def test_candidate_membership_is_not_runtime_qualification(self):
        r=image.compare_installed(self.entries(NEW),NEW);self.assertTrue(r['candidate_sdk_installed']);self.assertFalse(r['runtime_binding_qualified']);self.assertFalse(r['native_admitted'])
    def test_unrelated_copy_cannot_replace_panda_library(self):
        rows=self.entries(OLD)+[dict(path='/tmp/libpandagl.so',kind='file',sha256=NEW)]
        r=image.compare_installed(rows,NEW);self.assertFalse(r['candidate_sdk_installed'])
    def test_duplicate_paths_and_multiple_panda_candidates_reject(self):
        rows=self.entries(NEW)
        with self.assertRaises(ValueError):image.compare_installed(rows+[rows[-1]],NEW)
        rows.append(dict(path='/opt/python/lib/python3.11/site-packages/panda3d/libpandagl.so.1.10',kind='file',sha256=NEW))
        with self.assertRaises(ValueError):image.compare_installed(rows,NEW)
    def test_missing_python_or_metadrive_stays_blocked(self):
        for index,want in [(0,'PYTHON_RUNTIME_NOT_IN_INVENTORY'),(1,'METADRIVE_NOT_IN_INVENTORY')]:
            rows=self.entries(NEW);del rows[index];r=image.compare_installed(rows,NEW);self.assertIn(want,r['blockers'])
    def test_bad_digest_or_noncanonical_inventory_path_rejects(self):
        for path,sha in [('/opt/../tmp/libpandagl.so',NEW),('/tmp/libpandagl.so','z'*64)]:
            with self.assertRaises(ValueError):image.compare_installed([dict(path=path,kind='file',sha256=sha)],NEW)
if __name__=='__main__':unittest.main()
