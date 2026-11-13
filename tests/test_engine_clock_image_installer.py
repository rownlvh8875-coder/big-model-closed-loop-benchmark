"""Owned offline install/asset fixtures; callback tools never install or import packages."""
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
try:
 from scripts import engine_clock_image_installer as install
except ImportError:install=None
from test_engine_clock_python_wheel_closure import make_wheel

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def setup_context(root):
 context=root/'sealed';context.mkdir();(context/'wheels').mkdir()
 wheel=make_wheel(context/'wheels',name='sample',version='1.0')
 assets=context/'assets.zip'
 with zipfile.ZipFile(assets,'w') as z:z.writestr('assets/version.txt','0.4.3\n');z.writestr('assets/owned.dat',b'owned fixture asset')
 tool=context/'pip-tool.whl';tool.write_bytes(b'owned fake tool, never executed')
 plan={'schema':'engine-clock-model-free-renderer-wheel-lock-v1','renderer_input_graph_closed':True,'forbidden_distribution_prefix':'onnxruntime','wheels':[{'name':'sample','version':'1.0','filename':wheel.name,'nbytes':wheel.stat().st_size,'sha256':digest(wheel)}]}
 p=context/'renderer-wheels.lock.json';p.write_text(json.dumps(plan))
 pins={'plan_sha256':digest(p),'tool':{'path':'pip-tool.whl','nbytes':tool.stat().st_size,'sha256':digest(tool)},'assets':{'path':'assets.zip','nbytes':assets.stat().st_size,'sha256':digest(assets)}}
 return context,pins

class ImageInstallerTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(install,'owned offline image installer missing')
 def test_command_uses_only_isolated_no_site_offline_fixed_wheels(self):
  cmd=install.pip_command(Path('/owned-root'),Path('/owned-root/sealed/pip-tool.whl'),[Path('/owned-root/sealed/wheels/sample-1-py3-none-any.whl')])
  self.assertEqual('/owned-root/opt/venv/bin/python',cmd[0]);self.assertEqual(['-I','-S','-B'],cmd[1:4])
  self.assertIn('--no-index',cmd);self.assertIn('--no-deps',cmd);self.assertIn('--no-compile',cmd);self.assertIn('--only-binary=:all:',cmd);self.assertNotIn('download',cmd);self.assertNotIn('https://pypi.org',cmd)
 def test_invalid_payload_fails_before_any_venv_or_pip_callback(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);context,pins=setup_context(root);next((context/'wheels').iterdir()).write_bytes(b'changed');calls=[]
   with self.assertRaisesRegex(ValueError,'^IMAGE_INSTALL_REJECTED$'):install.install_renderer(root,context,pins,create_venv=lambda *args:calls.append('venv'),run_pip=lambda *args:calls.append('pip'))
   self.assertEqual([],calls)
 def test_owned_callbacks_integrate_verified_plan_metadata_and_asset_retention(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);context,pins=setup_context(root);calls=[]
   def create(prefix):
    calls.append('venv');(prefix/'bin').mkdir(parents=True);(prefix/'bin/python').write_bytes(b'never execute')
   def pip(cmd):
    calls.append('pip');site=root/'opt/venv/lib/python3.11/site-packages';dist=site/'sample-1.0.dist-info';dist.mkdir(parents=True);(dist/'METADATA').write_text('Metadata-Version: 2.1\nName: sample\nVersion: 1.0\n\n');(site/'metadrive/assets').mkdir(parents=True);(site/'metadrive/assets/old').write_bytes(b'original');return {'returncode':0,'payload_imports':False}
   result=install.install_renderer(root,context,pins,create_venv=create,run_pip=pip);self.assertEqual(['venv','pip'],calls);self.assertEqual('OFFLINE_RENDERER_INSTALL_RECORDED',result['status']);self.assertEqual(b'original',(context/'original-metadrive-assets/old').read_bytes());self.assertFalse(result['native_admission'])
 def test_failed_pip_callback_runs_once_and_preserves_original_asset_tree(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);context,pins=setup_context(root);calls=[]
   def create(prefix):
    (prefix/'lib/python3.11/site-packages/metadrive/assets').mkdir(parents=True);(prefix/'lib/python3.11/site-packages/metadrive/assets/old').write_bytes(b'original')
   def fail(cmd):calls.append('pip');return {'returncode':3,'payload_imports':False}
   with self.assertRaisesRegex(ValueError,'^IMAGE_INSTALL_REJECTED$'):install.install_renderer(root,context,pins,create_venv=create,run_pip=fail)
   self.assertEqual(['pip'],calls);self.assertEqual(b'original',(root/'opt/venv/lib/python3.11/site-packages/metadrive/assets/old').read_bytes());self.assertFalse((context/'original-metadrive-assets').exists())
 def test_fresh_prefix_required_without_deleting_existing_state(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);context,pins=setup_context(root);prefix=root/'opt/venv';prefix.mkdir(parents=True);(prefix/'old').write_bytes(b'preserve');calls=[]
   with self.assertRaisesRegex(ValueError,'^IMAGE_INSTALL_REJECTED$'):install.install_renderer(root,context,pins,create_venv=lambda *args:calls.append('venv'),run_pip=lambda *args:calls.append('pip'))
   self.assertEqual(b'preserve',(prefix/'old').read_bytes());self.assertFalse(calls)
 def test_plan_rejects_ort_duplicate_or_unsafe_wheel_even_with_caller_digest(self):
  for change in ('ort','duplicate','path'):
   with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);context,pins=setup_context(root);path=context/'renderer-wheels.lock.json';plan=json.loads(path.read_bytes())
    if change=='ort':plan['wheels'][0]['name']='onnxruntime'
    elif change=='duplicate':plan['wheels'].append(dict(plan['wheels'][0]))
    else:plan['wheels'][0]['filename']='../SECRET.whl'
    path.write_text(json.dumps(plan));pins['plan_sha256']=digest(path)
    with self.assertRaisesRegex(ValueError,'^IMAGE_INSTALL_REJECTED$'):install.install_renderer(root,context,pins,create_venv=lambda *args:None,run_pip=lambda *args:None)
 def test_metadata_exact_set_and_global_ort_absence_without_import(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);site=root/'opt/venv/lib/python3.11/site-packages';dist=site/'sample-1.0.dist-info';dist.mkdir(parents=True);(dist/'METADATA').write_text('Metadata-Version: 2.1\nName: sample\nVersion: 1.0\n\n')
   r=install.verify_installed_metadata(root,[{'name':'sample','version':'1.0'}]);self.assertEqual({'sample':'1.0'},r['installed_distributions']);self.assertFalse(r['payload_imports'])
   other=root/'opt/python/lib/python3.11/site-packages/onnxruntime';other.mkdir(parents=True)
   with self.assertRaisesRegex(ValueError,'^IMAGE_INSTALL_REJECTED$'):install.verify_installed_metadata(root,[{'name':'sample','version':'1.0'}])
 def test_genuine_python_bootstrap_underscore_and_hook_names_are_data_only(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);site=root/'opt/venv/lib/python3.11/site-packages';dist=site/'sample-1.0.dist-info';dist.mkdir(parents=True);(dist/'METADATA').write_text('Metadata-Version: 2.1\nName: sample\nVersion: 1.0\n\n')
   global_site=root/'opt/python/lib/python3.11/site-packages';(global_site/'_distutils_hack').mkdir(parents=True);(global_site/'distutils-precedence.pth').write_text('NEVER_EXECUTE_FIXTURE');(global_site/'README.txt').write_text('owned fixture')
   r=install.verify_installed_metadata(root,[{'name':'sample','version':'1.0'}]);self.assertFalse(r['payload_imports']);self.assertEqual({'sample':'1.0'},r['installed_distributions'])
 def test_asset_audit_rejects_escape_before_original_subtree_moves(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);target=root/'metadrive';(target/'assets').mkdir(parents=True);(target/'assets/old').write_bytes(b'original');archive=root/'bad.zip'
   with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape',b'bad')
   with self.assertRaisesRegex(ValueError,'^IMAGE_INSTALL_REJECTED$'):install.replace_assets(target,archive,root/'backup',expected_sha256=digest(archive))
   self.assertEqual(b'original',(target/'assets/old').read_bytes());self.assertFalse((root/'backup').exists())
 def test_asset_replacement_preserves_old_bytes_and_verifies_all_new_bytes(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);context,pins=setup_context(root);target=root/'metadrive';(target/'assets').mkdir(parents=True);(target/'assets/old').write_bytes(b'original');archive=context/'assets.zip'
   r=install.replace_assets(target,archive,root/'backup',expected_sha256=digest(archive));self.assertEqual(b'original',(root/'backup/old').read_bytes());self.assertEqual(b'owned fixture asset',(target/'assets/owned.dat').read_bytes());self.assertEqual('0.4.3',r['version']);self.assertEqual(2,r['members']);self.assertFalse(r['payload_execution'])
 def test_real_renderer_lock_matches_model_free_contract_without_changing_full_graph(self):
  root=Path(__file__).resolve().parent.parent;plan=json.loads((root/'docs/locks/engine-clock-renderer-wheels.lock.json').read_bytes());self.assertEqual(53,len(plan['wheels']));self.assertFalse(any(r['name'].startswith('onnxruntime') for r in plan['wheels']));full=json.loads((root/'docs/locks/engine-clock-python-wheels.lock.json').read_bytes());self.assertEqual(56,len(full['wheels']));self.assertIn('onnxruntime',[r['name'] for r in full['wheels']])

if __name__=='__main__':unittest.main()
