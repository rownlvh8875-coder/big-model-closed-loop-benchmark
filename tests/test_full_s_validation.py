import copy,math,unittest
try:from bigbench import full_s_validation as f
except ImportError:f=None
from bigbench.model_world_frame import WorldFramePolicyAdapter,SOURCE_ACTION_FRAME
from tests.full_s_fakes import Camera,Policy,route
class FullSContracts(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(f,'full S completion protocol missing')
 def run_case(self,*,steps=80,curvature=0.,fail_on=None,progress=None):
  inner=Policy(curvature,fail_on);policy=WorldFramePolicyAdapter(inner,source_action_frame=SOURCE_ACTION_FRAME);camera=Camera();r=f.run_full_s(policy,camera,route(),seed=20261109,scene='s_curve_left_right',max_steps=steps,progress=progress);return r,policy,camera
 def test_full_route_completion_is_not_a_twelve_step_prefix(self):
  r,p,c=self.run_case();self.assertEqual(r['outcome'],'FULL_S_COMPLETED');self.assertTrue(r['traversal_passed']);self.assertEqual(r['visited_lane_ids'],[str(l.index) for l in route()]);self.assertGreater(r['completed_steps'],12);self.assertEqual(r['actual_inference_bounds'],[r['completed_steps']]*2)
  short,_,_=self.run_case(steps=12);self.assertEqual(short['outcome'],'STEP_LIMIT');self.assertFalse(short['traversal_passed'])
 def test_terminal_overshoot_keeps_real_pose_and_does_not_clamp_it(self):
  r,_,_=self.run_case();last=r['frames'][-1];self.assertGreaterEqual(last['route']['longitudinal_m'],4.);self.assertEqual(last['route']['lane_index'],2);self.assertEqual(last['time_s'],sum([.05]*r['completed_steps']));self.assertAlmostEqual(math.hypot(last['world_x_m']-r['initial_state']['x'],last['world_y_m']-r['initial_state']['y']),r['completed_steps']*.4,places=8)
 def test_lane_intrusion_fails_without_rescue_or_extra_policy_calls(self):
  r,p,c=self.run_case(curvature=.5);self.assertEqual(r['outcome'],'LANE_INTRUSION');self.assertFalse(r['traversal_passed']);self.assertGreater(r['frames'][-1]['route']['intrusion_m'],0.);self.assertEqual(len(p.inner.observations),r['completed_steps']);self.assertEqual(len(c.poses),r['completed_steps'])
 def test_original_parent_outputs_bridge_clock_and_state_are_preserved(self):
  r,p,c=self.run_case(steps=3,curvature=.001);self.assertEqual(p.inner.reset_count,2);self.assertEqual(p.adapter_reset_calls,1);self.assertEqual(len(p.inner.audit_rows),3)
  for i,row in enumerate(r['frames']):
   self.assertEqual(row['raw_model_action'],[.001,0.,0.,0.]);self.assertEqual(row['parent_model_action']['curvature_1pm'],.001);self.assertEqual(row['applied_world_action']['curvature_1pm'],-.001);self.assertEqual(row['source_road_rgb_sha256'],'a'*64);self.assertEqual(p.inner.observations[i].time_s,c.poses[i].t);self.assertFalse(hasattr(p.inner.observations[i],'lane_truth'))
 def test_missing_or_repeated_frame_bridge_cannot_start_capture(self):
  camera=Camera()
  with self.assertRaises(ValueError):f.run_full_s(Policy(),camera,route(),seed=20261109,scene='s_curve_left_right')
  self.assertEqual(camera.poses,[])
 def test_route_exports_primitives_for_independent_geometry_reconstruction(self):
  rows=f.validate_route(route());self.assertEqual(rows[0]['shape']['kind'],'circular');self.assertEqual(rows[0]['shape']['radius'],1000.);self.assertEqual(rows[1]['shape']['kind'],'straight');self.assertEqual(rows[2]['shape']['direction'],-1)
 def test_non_s_discontinuous_or_repeated_route_rejected_before_inference(self):
  a,b,c=route()
  for lanes in ((a,b),(a,b,a),(a,b,c)):
   if lanes[-1] is c:c.center=(c.center[0]+2.,c.center[1])
   with self.subTest(lanes=len(lanes)),self.assertRaises(ValueError):f.validate_route(lanes)
 def test_inference_exception_retains_lower_upper_bounds_and_partial_audits(self):
  events=[];r,p,c=self.run_case(fail_on=3,progress=events.append);self.assertEqual(r['outcome'],'RUNTIME_ERROR');self.assertFalse(r['trial_completed']);self.assertEqual(r['actual_inference_bounds'],[2,3]);self.assertEqual(len(r['inference_audit_rows']),2);self.assertEqual(events[-1]['inference_bounds'],[2,3])
 def test_repeated_failures_are_not_promoted_to_traversal_pass(self):
  a,_,_=self.run_case(steps=12);b,_,_=self.run_case(steps=12);b['process_id']=a['process_id']+1;v=f.compare_full_s(a,b);self.assertTrue(v['strict_repeat_passed']);self.assertFalse(v['traversal_passed']);self.assertFalse(v['passed'])
 def test_strict_comparison_keeps_raw_source_and_bridge_disagreements(self):
  a,_,_=self.run_case();b=copy.deepcopy(a);b['process_uuid']='b'*32;b['process_id']=a['process_id']+1;self.assertTrue(f.compare_full_s(a,b)['passed'])
  for key in ('source_road_rgb_sha256','state_after_step_sha256','applied_world_action'):
   bad=copy.deepcopy(b);bad['frames'][4][key]='different';v=f.compare_full_s(a,bad);self.assertFalse(v['strict_repeat_passed']);self.assertEqual(v['first_diverging_step'],5)
if __name__=='__main__':unittest.main()
