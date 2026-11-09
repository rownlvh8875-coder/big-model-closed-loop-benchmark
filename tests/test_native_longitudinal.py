"""Native longitudinal loop unit tests with a camera double, not model evidence."""
import unittest

from bigbench.camera import RGBFrame
from bigbench.camera_rig import SchematicPair
from bigbench.kinematics import ModelAction
from bigbench.longitudinal_world import scenario,LongitudinalContractError
from bigbench.native_longitudinal import run_longitudinal_native,DeterministicLeadTimeline


class FakeCamera:
    def capture(self,ego,lead,*,in_lane=True):
        v=max(0,min(255,round(lead.station_m-ego.x)+80))
        a=RGBFrame(16,16,bytes((v,50,10))*256)
        b=RGBFrame(16,16,bytes((10,v,45))*256)
        return SchematicPair(a,b)


class FakePolicy:
    is_mock=True
    name='FAKE_ACTIONS_NOT_ONNX'
    def reset(self):
        self.count=0
    def step(self,obs):
        self.count+=1
        return ModelAction(curvature_1pm=.02,acceleration_mps2=-1.)


class NativeLongitudinalTests(unittest.TestCase):
    def test_braking_feedback_oracle_lateral_no_model_rank(self):
        p=FakePolicy()
        a=run_longitudinal_native(p,scenario('lead_brake'),FakeCamera(),steps=22)
        self.assertEqual(a['status'],'DIAGNOSTIC_EXECUTED')
        self.assertTrue(a['oracle_lateral_path'])
        self.assertFalse(a['model_scoring_allowed'])
        self.assertEqual(p.count,22)
        self.assertLess(a['trace'][-1]['ego_speed_mps'],14.)

    def test_cut_in_is_only_in_lane_after_exogenous_event(self):
        r=run_longitudinal_native(FakePolicy(),scenario('cut_in'),FakeCamera(),steps=45)
        self.assertFalse(r['trace'][0]['lead_in_target_lane'])
        self.assertFalse(r['trace'][39]['lead_in_target_lane'])
        self.assertTrue(r['trace'][40]['lead_in_target_lane'])

    def test_bad_dt_rejected(self):
        with self.assertRaises(LongitudinalContractError):
            run_longitudinal_native(FakePolicy(),scenario('lead_brake'),FakeCamera(),steps=10,dt_s=.04)

    def test_deterministic_lead_reinit(self):
        w=DeterministicLeadTimeline(scenario('stop_go'))
        a=[w.step(i*.05,.05) for i in range(20)]
        w.reset()
        b=[w.step(i*.05,.05) for i in range(20)]
        self.assertEqual(a,b)


if __name__=='__main__':unittest.main()
