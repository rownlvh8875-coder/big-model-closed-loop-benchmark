"""Frozen-camera isolation tests: test double is NOT real ONNX or camera rendering."""
from __future__ import annotations

import unittest
from bigbench.camera import RGBFrame
from bigbench.camera_rig import SchematicPair
from bigbench.kinematics import ModelAction
from bigbench.native_model_campaign import CampaignSpec
from bigbench.frozen_camera_diagnostic import isolate_model_repeatability


class Lane:
    index=('native','fixed',0)
    length=70.
    def position(self,s,r):return (s,-r)
    def heading_theta_at(self,s):return 0.
    def width_at(self,s):return 3.5
    def local_coordinates(self,xy):return xy[0],-xy[1]


class SourceCamera:
    def __init__(self): self.calls=0
    def capture(self,pose):
        self.calls+=1
        return SchematicPair(
            RGBFrame(4,4,bytes((80,60,50))*16),
            RGBFrame(4,4,bytes((40,60,75))*16))


class FakePolicy:
    name='FAKE_NOT_REAL_ONNX'
    is_mock=True
    def __init__(self,drift=False):self.drift=drift
    def reset(self):self.calls=0
    def step(self,observation):
        self.calls+=1
        curvature=.001 if not self.drift else .002*self.calls
        return ModelAction(curvature,0.)


class FrozenIsolationTests(unittest.TestCase):
    def test_one_image_capture_and_two_model_sessions(self):
        camera=SourceCamera()
        spec=CampaignSpec('s_curve_left_right',steps=6,speed_mps=5.)
        result=isolate_model_repeatability(make_policy=FakePolicy,
                 native_camera=camera,lane=Lane(),spec=spec)
        self.assertEqual(camera.calls,1)
        self.assertEqual(result['status'],'SYNTHETIC_REPEATED_DIAGNOSTIC_MATCH')
        self.assertFalse(result['actual_closed_loop_camera_feedback'])
        self.assertTrue(result['camera_pixels_replayed'])
        self.assertFalse(result['model_scoring_allowed'])
        self.assertEqual(len(result['runs']),2)
        self.assertTrue(result['model_action_values_exactly_equal'])
        self.assertEqual(result['max_curvature_delta_1pm'],0.0)
        self.assertEqual(result['runs'][0]['frozen_camera_calls'],6)

    def test_two_independent_sessions_detect_differences(self):
        camera=SourceCamera()
        policies=[FakePolicy(False),FakePolicy(True)]
        spec=CampaignSpec('s_curve_left_right',steps=6,speed_mps=5.)
        result=isolate_model_repeatability(make_policy=lambda:policies.pop(0),
                 native_camera=camera,lane=Lane(),spec=spec)
        self.assertEqual(result['status'],'ONNX_ACTION_OUTPUT_MISMATCH')
        self.assertFalse(result['model_action_values_exactly_equal'])
        self.assertTrue(result['comparison']['frame_hashes_identical'])
        self.assertGreater(result['comparison']['max_pose_disagreement_m'],0.)


if __name__=='__main__':
    unittest.main()
