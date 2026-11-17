"""Schema-only CPU fixtures. No actual native/GPU/physical/model evidence here."""
from pathlib import Path
import copy,json,tempfile,unittest
try:from scripts import run_sdk3_four_validation as h
except ImportError:h=None
from tests.test_sdk3_four_validation_trial import ProbeCamera
from tests.full_s_fakes import route,Policy,Camera
from bigbench.full_s_validation import run_full_s
from bigbench.model_world_frame import WorldFramePolicyAdapter,SOURCE_ACTION_FRAME,basis_receipt
from bigbench.optical_calibration import reference_source
from scripts import sdk3_four_validation_trial as t,panda_sdk3_runtime as p
from bigbench.sdk3_terrain_priority import REPAIR_ID
from tests.test_sdk3_terrain_priority import fixture
from bigbench import sdk3_terrain_priority as repair
def receipt():
 engine,core=fixture();return repair.install_rgb_terrain_priority(engine,terrain_label='terrain',tag_key='rgb',core=core)
class HostContracts(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(h,'strict four-validation host missing')
 def probe(self,out):
  raw=t.RawFrames();c=ProbeCamera(raw);r=t.capture_probe(c,raw,route(),dict(renderer='llvmpipe CPU_UNIT',vendor='Mesa',version='unit'),intrinsics={role:reference_source(role) for role in ('road','wide')},out=Path(out),seed=20261109,scene='s_curve_left_right',receipt=receipt());r.update(ort_module_loaded=False,provider_closed=True)
  for row in r['geometry']:row['lane_class']='metadrive.component.lane.'+('circular_lane.CircularLane' if row['shape']['kind']=='circular' else 'straight_lane.StraightLane')
  (Path(out)/'probe.json').write_text(json.dumps(r));return r
 def model(self):
  r=run_full_s(WorldFramePolicyAdapter(Policy(),source_action_frame=SOURCE_ACTION_FRAME),Camera(),route(),seed=20261109,scene='s_curve_left_right',max_steps=600);r.update(model_test_double=False,injected_session=False,model_sha256=p.MODEL_SHA,trial_evidence='CORRECTED_WORLD_FRAME_RGB_PRIORITY_FULL_S',source_context=t.source_context(),renderer_candidate=receipt(),action_basis=basis_receipt(),driver=dict(renderer='llvmpipe CPU_UNIT',vendor='Mesa',version='unit'),onnxruntime_version='1.20.1',onnxruntime_providers=['CPUExecutionProvider'],real_ort_session=True,raw_rgb_observer_used=False,ld_preload_present=False,draw_trace_modules_loaded=False,selected_sdk_sha256=p.SDK_SHA,original_camera_class_preserved=True,original_policy_class_preserved=True,provider_closed=True,source_stats_after=dict(returned=0,guards_ok=True,values=dict.fromkeys(p.STATS_FIELDS,0)))
  for row in r['geometry']:row['lane_class']='metadrive.component.lane.'+('circular_lane.CircularLane' if row['shape']['kind']=='circular' else 'straight_lane.StraightLane')
  return r
 def test_raw_virtual_probe_recomputes_warps_and_preserves_physical_limits(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.probe(d);v=h.validate_virtual_probe(Path(d),20261109,'s_curve_left_right');self.assertTrue(v['virtual_pinhole_passed']);self.assertFalse(v['physical_optics_passed']);self.assertFalse(v['hardware_gpu_passed'])
 def test_corrupt_source_stale_pose_bad_lens_or_unqualified_driver_reject(self):
  for kind in ('source','stale','lens','driver','scope'):
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
    r=self.probe(d)
    if kind=='source':(Path(d)/r['captures'][0]['images'][0]['source_file']).write_bytes(b'bad')
    elif kind=='stale':r['captures'][1]['images'][0]['source_sha256']=r['captures'][0]['images'][0]['source_sha256']
    elif kind=='lens':r['captures'][0]['images'][0]['measured_intrinsics']['fx']*=1.2
    elif kind=='driver':r['driver']['renderer']='softpipe'
    else:r['physical_optics_validated']=True
    (Path(d)/'probe.json').write_text(json.dumps(r))
    with self.assertRaises(ValueError):h.validate_virtual_probe(Path(d),20261109,'s_curve_left_right')
 def test_full_s_receipt_reconstructs_actions_and_real_route_completion(self):
  r=self.model();v=h.validate_full_report(r,20261109,'s_curve_left_right');self.assertTrue(v['traversal_passed']);self.assertEqual(v['inference_bounds'],[29,29])
 def test_wrong_bridge_unearned_completion_and_test_double_are_rejected(self):
  for kind in ('bridge','pose','completion','testdouble','source','counts'):
   r=self.model()
   if kind=='bridge':r['frames'][2]['applied_world_action']['curvature_1pm']=.1
   elif kind=='pose':r['frames'][2]['world_x_m']+=.01
   elif kind=='completion':r['outcome']='STEP_LIMIT';r['traversal_passed']=False
   elif kind=='testdouble':r['model_test_double']=True
   elif kind=='source':r['frames'][2]['source_road_rgb_sha256']='bad'
   else:r['actual_inference_bounds']=[0,0]
   with self.subTest(kind=kind),self.assertRaises(ValueError):h.validate_full_report(r,20261109,'s_curve_left_right')
 def test_all_four_cases_are_required_and_traversal_failure_stays_failed(self):
  rows=[dict(seed=s,scenario=c,container_id=str(i)*64,process_uuids=[str(i)+'a'*31,str(i)+'b'*31],inference_bounds=[58,58],verdict=dict(strict_repeat_passed=True,traversal_passed=True,passed=True)) for i,(s,c) in enumerate(sorted(p.CASES))];r=h.aggregate_cases(rows);self.assertEqual(r['full_s_passed_cases'],4);self.assertFalse(r['all_four_validation_tracks_passed']);rows[2]['verdict'].update(traversal_passed=False,passed=False);self.assertEqual(h.aggregate_cases(rows)['full_s_passed_cases'],3)
  with self.assertRaises(ValueError):h.aggregate_cases(rows[:3])
 def test_request_cannot_expand_model_calls_or_change_driver(self):
  r=dict(schema='sdk3-four-validation-request-v1',cases=[dict(seed=s,scenario=c) for s,c in sorted(p.CASES)],max_model_processes=8,max_inferences=4800,max_steps=600,driver='llvmpipe',lp_num_threads=2,model_sha256=p.MODEL_SHA,base_sha=h.BASE);h.validate_request(r)
  for key,value in [('max_inferences',4801),('driver','softpipe'),('max_steps',601)]:
   x=copy.deepcopy(r);x[key]=value
   with self.assertRaises(ValueError):h.validate_request(x)
 def test_missing_lifecycle_never_becomes_zero_inferences(self):
  with tempfile.TemporaryDirectory() as d:
   pair=Path(d);child=pair/'run-0';child.mkdir();(child/'native-child.json').write_text(json.dumps(dict(spawn_attempted=True,pid=123)));r=h.observed_counts(pair);self.assertEqual(r['known_processes'],1);self.assertEqual(r['inference_bounds'],[0,600]);(child/'model-lifecycle.json').write_text(json.dumps(dict(pid=123,inference_bounds=[3,4])));self.assertEqual(h.observed_counts(pair)['inference_bounds'],[3,4])
 def test_measured_driver_must_match_qualified_probe_context(self):
  good=dict(renderer='llvmpipe',vendor='Mesa',version='3.3 Mesa25');h.same_driver(good,good)
  for key in good:
   bad=dict(good);bad[key]+=' changed'
   with self.assertRaises(ValueError):h.same_driver(bad,good)
 def test_immutable_base_files_cannot_be_modified(self):
  h.validate_delta(['A\tscripts/new.py']);h.validate_delta(['M\ttests/test_engine_clock_native.py'])
  with self.assertRaises(ValueError):h.validate_delta(['M\tbigbench/onnx_policy.py'])
if __name__=='__main__':unittest.main()
