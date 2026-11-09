"""Native campaign tests with fake renderer/policy; NEVER count as ONNX inference."""
from __future__ import annotations

import unittest
import math
from types import SimpleNamespace

from bigbench.camera import RGBFrame
from bigbench.camera_rig import SchematicPair
from bigbench.kinematics import ModelAction
from bigbench.native_model_campaign import (
    CampaignSpec,BenchmarkProtocolError,compare_episode_receipts,
    run_target_lane_episode,
)


class StraightTarget:
    index=('explicit','target',0)
    length=100.
    def position(self,s,r):
        return (float(s),-float(r))
    def heading_theta_at(self,s):
        return 0.
    def width_at(self,s):
        return 3.5
    def local_coordinates(self,p):
        return (p[0],-p[1])


class FakePairCamera:
    def capture(self,pose):
        # Stereo images differ, and the next image depends on physical pose.
        pixel=max(0,min(255,round(50+pose.x+pose.y*10)))
        a=RGBFrame(16,16,bytes((pixel,40,50))*256)
        b=RGBFrame(16,16,bytes((pixel,35,45))*256)
        return SchematicPair(a,b)


class FakePolicy:
    is_mock=True
    def __init__(self,curvature=0.0,name='mock'):
        self.curvature=curvature
        self.name=name
        self.times=[]
    def reset(self):
        self.times=[]
    def step(self,obs):
        self.times.append(obs.time_s)
        return ModelAction(self.curvature,-.1)


class TestNativeCampaign(unittest.TestCase):
    def test_lateral_same_clock_and_fixed_target(self):
        conf=CampaignSpec(scenario='s_curve_left_right',steps=8,speed_mps=10)
        a=run_target_lane_episode(FakePolicy(0.0),FakePairCamera(),StraightTarget(),conf)
        b=run_target_lane_episode(FakePolicy(.008,name='second'),FakePairCamera(),StraightTarget(),conf)
        self.assertEqual(a['status'],'DIAGNOSTIC_EXECUTED')
        self.assertEqual(b['completed_steps'],8)
        self.assertEqual(a['lane_truth']['intrusion_count'],0)
        self.assertNotEqual(a['frames'][-1]['world_y_m'],b['frames'][-1]['world_y_m'])
        receipt=compare_episode_receipts(a,b)
        self.assertTrue(receipt['first_camera_sha_equal'])
        self.assertFalse(receipt['model_scoring_allowed'])
        self.assertEqual(receipt['steps'],8)

    def test_invalid_step_rate_fails(self):
        with self.assertRaises(BenchmarkProtocolError):
            CampaignSpec(scenario='s_curve_left_right',dt_s=.06)
        with self.assertRaises(BenchmarkProtocolError):
            CampaignSpec(scenario='bogus')
        with self.assertRaises(BenchmarkProtocolError):
            CampaignSpec(scenario='in_ramp',steps=1)

    def test_out_of_target_segment_fails_instead_of_switch(self):
        conf=CampaignSpec(scenario='in_ramp',steps=30,speed_mps=20)
        lane=StraightTarget()
        lane.length=3.0
        run=run_target_lane_episode(FakePolicy(),FakePairCamera(),lane,conf)
        self.assertEqual(run['status'],'FAILED_OR_INCOMPLETE')
        self.assertTrue(run['completed_steps'] < conf.steps)
        with self.assertRaises(BenchmarkProtocolError):
            compare_episode_receipts(run,run)

    def test_differing_conditions_cannot_compare(self):
        c1=CampaignSpec(scenario='in_ramp',steps=3)
        c2=CampaignSpec(scenario='out_ramp',steps=3)
        a=run_target_lane_episode(FakePolicy(),FakePairCamera(),StraightTarget(),c1)
        b=run_target_lane_episode(FakePolicy(),FakePairCamera(),StraightTarget(),c2)
        with self.assertRaises(BenchmarkProtocolError):
            compare_episode_receipts(a,b)


if __name__=='__main__':
    unittest.main()
