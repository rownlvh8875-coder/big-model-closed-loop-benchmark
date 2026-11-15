"""Real harmless CPU child at Docker boundary; never invoke Docker daemon."""
import os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
try:from scripts import produce_panda_sdk_image as p
except ImportError:p=None
class ProducerBoundaryTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(p,'portable COPY-only producer missing')
 def child(self,root):
  f=root/'handwritten-cpu-docker';f.write_text('#!/usr/bin/python3\nimport os,sys,time\nassert sys.argv[1]=="--host=unix:///var/run/docker.sock"\nassert "GH_TOKEN" not in os.environ and "LD_PRELOAD" not in os.environ and "DOCKER_HOST" not in os.environ\nassert os.environ["DOCKER_CONFIG"]=="cpu-config"\nprint("CPU only",flush=True)\nif sys.argv[2]=="info":time.sleep(5)\n');f.chmod(0o755);return f
 def test_real_cpu_child_endpoint_secret_filter_and_timeout(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);f=self.child(root)
   with patch.dict(os.environ,{'GH_TOKEN':'cpu-token','LD_PRELOAD':'cpu-unset','DOCKER_HOST':'foreign','DOCKER_CONFIG':'cpu-config'}):d=p.DockerData(f,root/'logs',time.monotonic()+8)
   self.assertEqual(d.call(['version'],timeout=2).strip(),'CPU only')
   with self.assertRaises(ValueError):d.call(['info'],timeout=.1)
   self.assertTrue((root/'logs/command-1/receipt.json').exists())
 def test_forbidden_commands_and_tool_drift_reject_before_child(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);f=self.child(root);d=p.DockerData(f,root/'logs',time.monotonic()+5)
   for cmd in (['run','x'],['start','x'],['exec','x'],['push','x'],['pull','x'],['system','prune'],['rm','--force','x']):
    with self.subTest(cmd=cmd),self.assertRaises(ValueError):d.call(cmd)
   f.write_text('changed pinned bytes')
   with self.assertRaises(ValueError):d.call(['version'])
   self.assertFalse(any((root/'logs').glob('command-*')))
 def test_extra_credentials_are_excluded_but_proxy_and_config_survive(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);f=self.child(root);f.write_text(f.read_text().replace('print("CPU only",flush=True)', 'assert not any(k in os.environ for k in ("GH_ENTERPRISE_TOKEN","AWS_SECRET_ACCESS_KEY","ARBITRARY_PRIVATE_VALUE"))\nassert os.environ["HTTPS_PROXY"]=="http://cpu-proxy:80"\nprint("CPU only",flush=True)'))
   with patch.dict(os.environ,{'GH_ENTERPRISE_TOKEN':'CPU','AWS_SECRET_ACCESS_KEY':'CPU','ARBITRARY_PRIVATE_VALUE':'CPU','HTTPS_PROXY':'http://cpu-proxy:80','DOCKER_CONFIG':'cpu-config'}):d=p.DockerData(f,root/'logs',time.monotonic()+5)
   self.assertEqual(d.call(['version']).strip(),'CPU only')
 def test_entry_cannot_execute_outside_exact_github_context(self):
  with patch.dict(os.environ,{},clear=True),self.assertRaises(ValueError):p.run_production()
 def test_workflow_is_push_filtered_pinned_and_has_no_payload_start(self):
  s=(p.a.ROOT/p.a.WORKFLOW).read_text();self.assertIn("branches: ['"+p.a.BRANCH+"']",s);self.assertIn('persist-credentials: false',s);self.assertIn('compression-level: 0',s);self.assertNotIn('workflow_dispatch',s);self.assertNotIn('docker run',s);self.assertNotIn('id-token: write',s)
if __name__=='__main__':unittest.main()
