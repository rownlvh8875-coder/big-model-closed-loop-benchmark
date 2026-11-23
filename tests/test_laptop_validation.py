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
 def test_carla_probe_mode_runs_cold_without_model_or_configured_endpoint(self):
  import json,tempfile
  driver=Path(l.__file__)
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp)/'new-output'
   returned=subprocess.run([sys.executable,'-I','-S','-B',str(driver),'--mode','carla-probe','--out',str(folder)],capture_output=True,text=True,timeout=10)
   self.assertEqual(returned.returncode,0,returned.stderr)
   receipt=json.loads((folder/'carla-probe-summary.json').read_text())
   self.assertEqual(receipt['status'],'BLOCKED')
   self.assertEqual(receipt['model_processes'],0)
   self.assertEqual(receipt['inferences'],[0,0])
   self.assertFalse(receipt['readiness']['world_mutated'])
   self.assertEqual(list(folder.glob('probe-*')),[])
 def test_carla_probe_dispatches_only_registered_model_free_workers(self):
  from unittest.mock import patch
  from bigbench import carla_validation as c
  ready={'status':'READY_FOR_PROBE','world_mutated':False}
  probe={'protocol':'carla-common-route-camera-probe-v1','passed':True,
         'official_model_processes':0,'inferences':0,'context':{'server':'0.9.16'},
         'frames':[{'pose':{},'source':{}},{'pose':{},'source':{}}],'sensor_frames':[]}
  with patch.object(l,'carla_readiness',return_value=ready), patch.object(l,'launch_worker',return_value=probe) as launch, patch.object(l,'validate_carla_route_receipt') as route, patch.object(c,'validate_sensor_bindings') as sensors, patch.object(l,'check_model') as model:
   result=l.run_carla_probe_cohort(Path('out'),'127.0.0.1',2000,True)
  self.assertEqual(result['status'],'PROBES_MEASURED')
  self.assertEqual(result['qualified_cases'],4)
  self.assertFalse(result['cross_engine_contracts_passed'])
  self.assertEqual([(call.kwargs['seed'],call.kwargs['scene']) for call in launch.call_args_list],l.CASES)
  self.assertTrue(all(call.kwargs['probe'] is True and call.kwargs['model'] is None for call in launch.call_args_list))
  self.assertEqual(route.call_count,4)
  self.assertEqual(sensors.call_count,4)
  model.assert_not_called()
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
