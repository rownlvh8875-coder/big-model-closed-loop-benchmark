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

class PinnedBaseLabelTests(unittest.TestCase):
 def test_actual_pinned_ubuntu_label_is_required_without_allowing_other_labels(self):
  from scripts import engine_clock_image_preparation_v3 as p
  from test_engine_clock_image_archive import launch_fixture
  import copy
  cid='sha256:'+'4'*64;nonce='a'*32;clean=launch_fixture(cid,nonce)
  h={'ReadonlyRootfs':True,'NetworkMode':'none','Privileged':False,'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges'],'PidMode':'','IpcMode':'private','PidsLimit':128,'Memory':2147483648,'NanoCpus':2000000000,'Devices':[],'DeviceRequests':None,'Binds':None,'Tmpfs':clean['tmpfs']}
  labels={'stage7.request':'image-20261114-03','stage7.nonce':nonce,'stage7.source':'1'*40,'org.opencontainers.image.version':'24.04'}
  raw={'Id':clean['container_id'],'Image':cid,'HostConfig':h,'Mounts':[],'Config':{'Entrypoint':clean['entrypoint'],'Cmd':clean['command'],'User':'0:0','WorkingDir':'/','Env':[k+'='+v for k,v in clean['env'].items()],'Labels':labels}}
  expected={'config_digest':cid,'request_id':'image-20261114-03','source_sha':'1'*40,'command':clean['command']}
  self.assertEqual(labels,p.normalize_launch(raw,expected,nonce)['labels'])
  for key,value in [('org.opencontainers.image.version','24.10'),('unregistered','SECRET_SENTINEL')]:
   bad=copy.deepcopy(raw);bad['Config']['Labels'][key]=value
   with self.assertRaisesRegex(ValueError,'^IMAGE_LAUNCH_REJECTED$'):p.normalize_launch(bad,expected,nonce)

if __name__=='__main__':unittest.main()
