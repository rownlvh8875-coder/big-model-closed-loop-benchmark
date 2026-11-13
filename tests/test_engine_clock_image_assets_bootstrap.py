"""Owned fixtures only; no actual pip, Docker, package import or network."""
import hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
try:from scripts import engine_clock_image_installer_v2 as installer
except ImportError:from scripts import engine_clock_image_installer as installer
class AssetsBootstrapTests(unittest.TestCase):
 def test_missing_assets_is_populated_and_original_absence_is_truthful(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);package=root/'metadrive';package.mkdir();z=root/'assets.zip'
   with zipfile.ZipFile(z,'w') as out:out.writestr('assets/version.txt','0.4.3\n');out.writestr('assets/owned',b'data')
   result=installer.replace_assets(package,z,root/'backup',expected_sha256=hashlib.sha256(z.read_bytes()).hexdigest())
   self.assertEqual(b'data',(package/'assets/owned').read_bytes());self.assertFalse((root/'backup').exists());self.assertFalse(result['original_assets_present']);self.assertFalse(result['original_assets_preserved'])
 def test_existing_asset_directory_is_retained_with_truthful_receipt(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);package=root/'metadrive';(package/'assets').mkdir(parents=True);(package/'assets/old').write_bytes(b'keep');z=root/'assets.zip'
   with zipfile.ZipFile(z,'w') as out:out.writestr('assets/version.txt','0.4.3')
   r=installer.replace_assets(package,z,root/'backup',expected_sha256=hashlib.sha256(z.read_bytes()).hexdigest())
   self.assertTrue(r['original_assets_present']);self.assertTrue(r['original_assets_preserved']);self.assertEqual(b'keep',(root/'backup/old').read_bytes())
 def test_missing_asset_path_may_not_be_a_symlink_or_regular_file(self):
  for kind in ('symlink','file'):
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);package=root/'metadrive';package.mkdir();z=root/'assets.zip'
    with zipfile.ZipFile(z,'w') as out:out.writestr('assets/version.txt','0.4.3\n')
    if kind=='symlink':(package/'assets').symlink_to(root/'outside')
    else:(package/'assets').write_bytes(b'keep')
    with self.assertRaisesRegex(ValueError,'^IMAGE_INSTALL_REJECTED$'):installer.replace_assets(package,z,root/'backup',expected_sha256=hashlib.sha256(z.read_bytes()).hexdigest())
if __name__=='__main__':unittest.main()
