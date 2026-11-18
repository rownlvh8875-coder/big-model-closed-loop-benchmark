"""Actual stdlib processes only; no simulator, CARLA server or model."""
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import errno,inspect,json,os,subprocess,sys,tempfile,unittest,venv
from scripts import run_laptop_validation as l
try:from bigbench import worker_ownership as w
except ImportError:w=None
ROOT=Path(__file__).resolve().parents[1]

class WorkerOwnershipTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(w,'shared worker ownership helper missing')
 def owner(self,path):
  value=dict(parent_pid=os.getppid(),nonce='a'*32,seed=20261109,scenario='s_curve_left_right',pid=os.getpid(),spawn_succeeded=True,returncode=None,child_reaped=False);l.write(path/'owner.json',value);return value
 def test_shared_launch_preserves_windows_venv_without_redirector(self):
  with mock.patch.object(w.sys,'platform','win32'),mock.patch.object(w.sys,'executable','C:/venv/Scripts/python.exe'),mock.patch.object(w.sys,'_base_executable','C:/Python311/python.exe'):
   exe,env=w.worker_launch()
  self.assertEqual(exe,'C:/Python311/python.exe');self.assertEqual(env['__PYVENV_LAUNCHER__'],'C:/venv/Scripts/python.exe')
 def test_parent_ack_rejects_unknown_or_wrong_assigned_identity(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d);original=self.owner(path)
   r=w.await_parent_ack(path,parent=os.getppid(),nonce='a'*32,seed=20261109,scene='s_curve_left_right',timeout=0);self.assertEqual(r['pid'],os.getpid())
   for key,value in [('pid',None),('spawn_succeeded',None),('parent_pid',-1),('nonce','b'*32),('seed',20261110),('scenario','s_curve_right_left'),('returncode',0),('child_reaped',True)]:
    owner=dict(original);owner[key]=value;l.write(path/'owner.json',owner)
    with self.subTest(key=key),self.assertRaises(ValueError):w.await_parent_ack(path,parent=os.getppid(),nonce='a'*32,seed=20261109,scene='s_curve_left_right',timeout=0)
 def test_interrupted_legacy_launch_keeps_model_bounds_unknown(self):
  with tempfile.TemporaryDirectory() as d,mock.patch.object(l.subprocess,'Popen',side_effect=KeyboardInterrupt()):
   dest=Path(d)/'20261109-s_curve_left_right/run-0'
   with self.assertRaises(BaseException):l.launch_worker(dest=dest,seed=20261109,scene='s_curve_left_right',probe=False,model=Path('not-loaded.onnx'))
   owner=json.loads((dest/'owner.json').read_text());self.assertIsNone(owner['spawn_succeeded']);self.assertTrue(owner['ownership_unresolved'])
   self.assertEqual(l.observed_laptop_counts(d),dict(known_model_processes=0,upper_model_processes=1,inference_bounds=[0,600]))
 def test_legacy_both_backends_use_direct_venv_in_ownership_only_mode(self):
  self.assertIn('ownership_only',inspect.signature(l.launch_worker).parameters)
  class Child:
   pid=2345;returncode=0
   def wait(self,timeout):return 0
   def poll(self):return 0
  for backend in ('metadrive','carla'):
   with tempfile.TemporaryDirectory() as d:
    dest=Path(d)/'owned';observed={}
    def popen(argv,**kwargs):
     observed.update(exe=argv[0],env=kwargs['env']);nonce=argv[argv.index('--nonce')+1]
     l.write(dest/'ownership.json',dict(protocol='owned-worker-process-check-v1',process_id=2345,parent_process_id=os.getpid(),nonce=nonce,seed=20261109,scenario='s_curve_left_right',backend=backend,prefix=sys.prefix,ownership_check_complete=True,site_hooks_disabled=True,native_modules_loaded=False,model_loaded=False,server_connection_attempted=False,official_model_processes=0,inferences=0));return Child()
    with mock.patch.object(l.sys,'platform','win32'),mock.patch.object(l.sys,'executable','C:/venv/Scripts/python.exe'),mock.patch.object(l.sys,'_base_executable','C:/Python311/python.exe'),mock.patch.object(l.subprocess,'Popen',side_effect=popen):
     l.launch_worker(dest=dest,seed=20261109,scene='s_curve_left_right',probe=True,model=None,backend=backend,ownership_only=True)
    self.assertEqual(observed['exe'],'C:/Python311/python.exe');self.assertEqual(observed['env']['__PYVENV_LAUNCHER__'],'C:/venv/Scripts/python.exe')
 def test_cold_process_check_runs_both_real_entry_points(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'check';r=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/run_laptop_validation.py'),'--mode','process-check','--out',str(out)],capture_output=True,text=True,timeout=45)
   self.assertEqual(r.returncode,0,r.stderr);report=json.loads((out/'process-check.json').read_text());self.assertEqual(report['status'],'PROCESS_CHECK_PASS');self.assertEqual(set(report['checks']),{'metadrive','carla'})
   for backend,child in report['checks'].items():
    owner=json.loads((out/backend/'owner.json').read_text());self.assertEqual(owner['pid'],child['process_id']);self.assertEqual(owner['parent_pid'],child['parent_process_id']);self.assertFalse(child['native_modules_loaded']);self.assertFalse(child['model_loaded']);self.assertFalse(child['server_connection_attempted'])
   summary=json.loads((out/'summary.json').read_text());self.assertEqual(summary['full_s'],'NOT_RUN');self.assertFalse(summary['all_four_validation_tracks_passed'])
 def test_empty_venv_runs_actual_legacy_worker_modes_with_matching_prefix(self):
  with tempfile.TemporaryDirectory() as d:
   env=Path(d)/'venv';venv.EnvBuilder(with_pip=False,symlinks=False).create(env);exe=env/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python');out=Path(d)/'check'
   r=subprocess.run([str(exe),'-I','-S','-B',str(ROOT/'scripts/run_laptop_validation.py'),'--mode','process-check','--out',str(out)],capture_output=True,text=True,timeout=60)
   self.assertEqual(r.returncode,0,r.stderr)
   for child in json.loads((out/'process-check.json').read_text())['checks'].values():self.assertEqual(Path(child['prefix']).resolve(),env.resolve());self.assertFalse(child['native_modules_loaded'])
 def test_nonzero_model_counters_cannot_pass_ownership_only_receipt(self):
  class Child:
   pid=3456;returncode=0
   def wait(self,timeout):return 0
   def poll(self):return 0
  with tempfile.TemporaryDirectory() as d:
   dest=Path(d)/'owned'
   def popen(argv,**kwargs):
    l.write(dest/'ownership.json',dict(protocol='owned-worker-process-check-v1',process_id=3456,parent_process_id=os.getpid(),nonce=argv[argv.index('--nonce')+1],seed=20261109,scenario='s_curve_left_right',backend='metadrive',prefix=sys.prefix,ownership_check_complete=True,site_hooks_disabled=True,native_modules_loaded=False,model_loaded=False,server_connection_attempted=False,official_model_processes=1,inferences=1));return Child()
   with mock.patch.object(l.subprocess,'Popen',side_effect=popen):
    with self.assertRaises(ValueError):l.launch_worker(dest=dest,seed=20261109,scene='s_curve_left_right',probe=True,model=None,ownership_only=True)
 def test_eintr_keeps_both_launch_paths_unknown_and_siteless(self):
  from scripts import probe_laptop_camera as c
  for kind in ('legacy','camera'):
   with tempfile.TemporaryDirectory() as d:
    root=Path(d);dest=root/'20261109-s_curve_left_right'/'run-0' if kind=='legacy' else root/'child'
    if kind=='camera':c.write(root/'cohort.json',dict(parent_pid=os.getpid(),cohort_id='a'*32))
    seen=[]
    def interrupted(argv,**kw):seen.extend(argv);raise InterruptedError(errno.EINTR,'interrupted creation')
    with mock.patch.object(l.subprocess,'Popen',side_effect=interrupted):
     with self.assertRaises(BaseException):
      if kind=='legacy':l.launch_worker(dest=dest,seed=20261109,scene='s_curve_left_right',probe=False,model=Path('not-loaded.onnx'))
      else:c.launch_worker(dest,20261109,'s_curve_left_right')
    owner=json.loads((dest/'owner.json').read_text());self.assertIsNone(owner['spawn_succeeded']);self.assertFalse(owner['child_reaped']);self.assertIn('-S',seen)
    if kind=='legacy':self.assertEqual(l.observed_laptop_counts(root)['inference_bounds'],[0,600])
 def test_site_marker_never_runs_during_unknown_spawn_or_process_check(self):
  real_popen=subprocess.Popen
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);env=root/'venv';venv.EnvBuilder(with_pip=False,symlinks=False).create(env);exe=env/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
   packages=env/'Lib/site-packages' if sys.platform=='win32' else env/f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages';packages.mkdir(parents=True,exist_ok=True)
   marker=root/'startup-marker';(packages/'sitecustomize.py').write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("started")\n')
   held=[]
   def interrupted(argv,**kwargs):held.append(real_popen(argv,**kwargs));raise InterruptedError(errno.EINTR,'lost handle delivery')
   try:
    with mock.patch.object(l.sys,'executable',str(exe)),mock.patch.object(l.subprocess,'Popen',side_effect=interrupted):
     with self.assertRaises(BaseException):l.launch_worker(dest=root/'unknown',seed=20261109,scene='s_curve_left_right',probe=True,model=None,ownership_only=True)
    for child in held:child.wait(timeout=10)
    self.assertFalse(marker.exists(),'venv startup code executed before parent acknowledgement')
   finally:
    for child in held:
     if child.poll() is None:child.kill();child.wait(timeout=10)
   out=root/'check';result=subprocess.run([str(exe),'-I','-S','-B',str(ROOT/'scripts/run_laptop_validation.py'),'--mode','process-check','--out',str(out)],capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stderr);self.assertFalse(marker.exists())
   for report in json.loads((out/'process-check.json').read_text())['checks'].values():self.assertEqual(Path(report['prefix']).resolve(),env.resolve())

if __name__=='__main__':unittest.main()
