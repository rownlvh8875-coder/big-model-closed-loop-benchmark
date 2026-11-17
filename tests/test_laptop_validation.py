"""Laptop orchestration contracts, no actual Windows GPU, simulator or model."""
import subprocess,sys,unittest
from pathlib import Path
try:from scripts import run_laptop_validation as l
except ImportError:l=None
class LaptopExecutionContracts(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(l,'Windows laptop execution entry missing')
 def test_cold_help_and_inventory_do_not_require_optional_engines(self):
  root=Path(__file__).resolve().parents[1]
  for entry in ('run_laptop_validation.py','laptop_native_trial.py','laptop_carla_trial.py'):
   r=subprocess.run([sys.executable,'-I','-S','-B',str(root/'scripts'/entry),'--help'],capture_output=True,text=True,timeout=10);self.assertEqual(r.returncode,0,r.stderr)
 def test_carried_inventory_is_not_four_verifications(self):
  r=l.aggregate_laptop(dict(),gpu=None,physical=None,carla=None,full_s=None);self.assertFalse(r['all_four_validation_tracks_passed']);self.assertEqual(r['hardware_gpu'],'NOT_RUN');self.assertEqual(r['carla'],'BLOCKED_NO_DEDICATED_SERVER')
 def test_scoped_physical_or_server_readiness_does_not_certify_full_track(self):
  r=l.aggregate_laptop({},gpu={'validation':{'passed':True}},physical={'status':'SCOPED_PASS','physical_optics_validated':False},carla={'status':'READY_FOR_PROBE'},full_s={'passed':True});self.assertFalse(r['all_four_validation_tracks_passed']);self.assertEqual(r['physical_optics'],'SCOPED_HOLDOUT_ONLY');self.assertEqual(r['carla'],'NOT_RUN')
 def test_unavailable_windows_resources_are_blocked_before_engine_import(self):
  r=l.windows_readiness(dict(system='Linux',machine='x86_64',memory_available_bytes=20*1024**3,disk_free_bytes=20*1024**3,python_version='3.11.9'));self.assertFalse(r['ready']);self.assertIn('WINDOWS_NATIVE_REQUIRED',r['missing'])
 def test_crashed_worker_without_lifecycle_keeps_unknown_inference_bound(self):
  import tempfile,json
  with tempfile.TemporaryDirectory() as tmp:
   dest=Path(tmp)/'20261109-s_curve_left_right'/'run-0';dest.mkdir(parents=True);(dest/'owner.json').write_text(json.dumps(dict(spawn_attempted=True,pid=42,model=True)))
   self.assertEqual(l.observed_laptop_counts(tmp),dict(known_model_processes=0,upper_model_processes=1,inference_bounds=[0,600]))
 def test_reference_model_file_required_before_worker_launch(self):
  with self.assertRaises(ValueError):l.check_model(Path('/definitely/missing/model.onnx'))
if __name__=='__main__':unittest.main()
