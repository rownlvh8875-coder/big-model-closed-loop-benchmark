"""Portable trajectory verifier must not import Linux-only hosted runtime code."""
from pathlib import Path
import copy,subprocess,sys,unittest
try:from bigbench import full_s_receipts as r
except ImportError:r=None
from bigbench.full_s_validation import run_full_s
from bigbench.kinematics import ModelAction
from bigbench.model_world_frame import WorldFramePolicyAdapter,SOURCE_ACTION_FRAME
from tests.full_s_fakes import Policy,Camera,route
class PortableReceipts(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(r,'portable full-S receipt verifier missing')
 def fixture(self):
  value=run_full_s(WorldFramePolicyAdapter(Policy(),source_action_frame=SOURCE_ACTION_FRAME),Camera(),route(),seed=20261109,scene='s_curve_left_right',max_steps=600)
  for row in value['geometry']:row['lane_class']='metadrive.component.lane.'+('circular_lane.CircularLane' if row['shape']['kind']=='circular' else 'straight_lane.StraightLane')
  return value
 def test_cold_import_does_not_require_resource_panda_numpy_or_ort(self):
  root=str(Path(__file__).resolve().parents[1]);code="import sys;sys.path.insert(0,"+repr(root)+");\nclass Fence:\n def find_spec(self,fullname,path=None,target=None):\n  if fullname.split('.')[0] in ('resource','panda3d','numpy','onnxruntime'):raise RuntimeError('forbidden import '+fullname)\nsys.meta_path.insert(0,Fence());import bigbench.full_s_receipts\n";out=subprocess.run([sys.executable,'-I','-S','-B','-c',code],capture_output=True,text=True,timeout=10);self.assertEqual(out.returncode,0,out.stderr)
 def test_portable_verifier_reconstructs_actual_recorded_trajectory(self):
  value=self.fixture();self.assertTrue(r.validate_trajectory(value,20261109,'s_curve_left_right')['traversal_passed'])
 def test_model_route_cannot_borrow_another_case_probe(self):
  value=self.fixture();other=copy.deepcopy(value);other['geometry'][0]['length_m']+=1
  with self.assertRaises(ValueError):r.bind_case_geometry(value,other)
  other=copy.deepcopy(value);other['scenario']='s_curve_right_left'
  with self.assertRaises(ValueError):r.bind_case_geometry(value,other)
 def test_corrupt_pose_is_rejected_in_portable_context(self):
  value=self.fixture();value['frames'][3]['world_x_m']+=.001
  with self.assertRaises(ValueError):r.validate_trajectory(value,20261109,'s_curve_left_right')
 def test_integrated_reconstructs_both_axes_at_the_observed_speed(self):
  class DrivingPolicy(Policy):
   def step(self, observation):
    super().step(observation)
    raw = [.1, 1., 0., 0.]
    self.audit_rows[-1]['raw_model_action'] = raw
    acceleration, lateral = raw[1], raw[0]
    return ModelAction(lateral / max(2.5, observation.speed_mps)**2, acceleration)

  camera = Camera()
  value = run_full_s(WorldFramePolicyAdapter(DrivingPolicy(), source_action_frame=SOURCE_ACTION_FRAME),
                     camera, route(), seed=20261109, scene='s_curve_left_right', integrated=True)
  for lane in value['geometry']:
   tag = 'circular_lane.CircularLane' if lane['shape']['kind']=='circular' else 'straight_lane.StraightLane'
   lane['lane_class'] = 'metadrive.component.lane.' + tag

  first, second = value['frames'][:2]
  self.assertEqual(first['speed_mps'], 8.05)
  self.assertEqual(camera.poses[1].speed, first['speed_mps'])
  self.assertEqual(second['parent_model_action']['curvature_1pm'], .1 / 8.05**2)
  self.assertTrue(r.validate_trajectory(value, 20261109, 's_curve_left_right', integrated=True)['traversal_passed'])
  with self.assertRaises(ValueError):
   r.validate_trajectory(value, 20261109, 's_curve_left_right')
  second['speed_mps'] = 8.
  with self.assertRaises(ValueError):
   r.validate_trajectory(value, 20261109, 's_curve_left_right', integrated=True)

if __name__=='__main__':unittest.main()
