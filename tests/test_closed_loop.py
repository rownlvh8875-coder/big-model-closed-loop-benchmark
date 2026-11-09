import json
import tempfile
from pathlib import Path
import unittest
from bigbench.camera import SchematicCamera
from bigbench.kinematics import AgentState,ModelAction
from bigbench.metrics import summarize,FrameMetric
from bigbench.policies import CameraLaneMock
from bigbench.runner import run_episode
from bigbench.report import write_run
from bigbench.scenario import get_scenario


class ClosedLoopTests(unittest.TestCase):
    def test_schematic_camera_changes_when_ego_position_changes(self):
        scene=get_scenario('s_curve'); cam=SchematicCamera()
        base=cam.render(scene,AgentState(0,0,0,0,15),0)
        shifted=cam.render(scene,AgentState(0,0,2,0,15),0)
        self.assertNotEqual(base.sha256,shifted.sha256)
        self.assertEqual(len(base.rgb),160*96*3)

    def test_mock_loop_is_reproducible(self):
        scene=get_scenario('s_curve')
        a=run_episode(scene,CameraLaneMock(.04,name='MOCK_a'))
        b=run_episode(scene,CameraLaneMock(.04,name='MOCK_a'))
        self.assertEqual(a.summary,b.summary)
        self.assertEqual([v.camera_sha256 for v in a.frames],[v.camera_sha256 for v in b.frames])
        self.assertGreater(a.summary['distinct_camera_frames'],1)
        self.assertEqual(a.classification,'SYNTHETIC_MOCK_ONLY')

    def test_distinct_mock_commands_change_trajectory(self):
        scene=get_scenario('ramp_left')
        a=run_episode(scene,CameraLaneMock(.025,name='MOCK_slow'))
        b=run_episode(scene,CameraLaneMock(.095,name='MOCK_fast'))
        self.assertNotEqual(a.frames[-1].lateral_error_m,b.frames[-1].lateral_error_m)
        self.assertNotEqual(a.frames[-1].camera_sha256,b.frames[-1].camera_sha256)

    def test_lead_gap_is_measured_but_not_leaked(self):
        scene=get_scenario('lead_brake')
        r=run_episode(scene,CameraLaneMock(.04,name='MOCK_lead'))
        self.assertIsNotNone(r.summary['min_lead_gap_m'])
        self.assertTrue(all(v.lead_distance_m is not None for v in r.frames))

    def test_can_write_images_and_json(self):
        scene=get_scenario('straight')
        r=run_episode(scene,CameraLaneMock(.05,name='MOCK_test'))
        with tempfile.TemporaryDirectory() as dirname:
            p=Path(dirname); report=write_run(p,r)
            self.assertEqual((p/'first_camera.png').read_bytes()[:8],b'\x89PNG\r\n\x1a\n')
            self.assertEqual(json.loads((p/'summary.json').read_text())['evidence_class'],'SYNTHETIC_MOCK_ONLY')
            self.assertTrue((p/'frames.csv').exists())

if __name__ == '__main__': unittest.main()
