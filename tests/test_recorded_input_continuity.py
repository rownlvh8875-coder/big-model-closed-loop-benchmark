"""CPU fixtures for comparisons; real pinned artifacts are checked separately."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

try:
    from bigbench import recorded_input_continuity as continuity
except ImportError:
    continuity=None


@unittest.skipUnless(sys.platform=='linux','canary body fixture is Linux-only')
class InputContinuityTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(continuity,'actual canary to historical first-input comparison missing')

    def fixture(self,root):
        from tests.test_recorded_worker_canary import CanaryTests
        case=CanaryTests();case.setUp();case.fixture(root)
        source=json.loads((root/'recording/report.json').read_text())
        reports=[]
        for index in (0,1):
            value=copy.deepcopy(source);value.update(max_steps=600,model_test_double=False,injected_session=False,
                real_ort_session=True,process_id=1234+index,process_uuid=str(index+1)*32)
            reports.append(value)
        return reports

    def test_exact_first_inputs_match_two_original_audits_without_claiming_graph_feed_for_canary(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'trial';reports=self.fixture(root)
            result=continuity.compare_first_step(root/'recording',reports)
            self.assertEqual(result['original_first_graph_inputs_matched'],2)
            self.assertTrue(result['first_input_continuity_confirmed'])
            self.assertFalse(result['canary_actual_graph_feed_attested'])
            self.assertFalse(result['model_camera_qualified'])
            self.assertEqual(result['new_inferences'],0)

    def test_consistent_different_graph_input_is_reported_and_inconsistent_audit_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'trial';reports=self.fixture(root)
            reports[1]['frames'][0]['new_img_sha256']='a'*64
            reports[1]['inference_audit_rows'][0]['new_img_sha256']='a'*64
            result=continuity.compare_first_step(root/'recording',reports)
            self.assertFalse(result['first_input_continuity_confirmed'])
            self.assertEqual(result['original_first_graph_inputs_matched'],1)
            reports[1]['inference_audit_rows'][0]['new_img_sha256']='b'*64
            with self.assertRaises(ValueError):continuity.compare_first_step(root/'recording',reports)

    def test_case_initial_pose_duplicates_and_model_fixture_metadata_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'trial';reports=self.fixture(root)
            for mutate in (lambda r:r[1].update(scenario='s_curve_right_left'),
                           lambda r:r[1]['initial_state'].update(speed=7.),
                           lambda r:r[1].update(process_uuid=r[0]['process_uuid']),
                           lambda r:r[1].update(real_ort_session=False),
                           lambda r:r[1].update(injected_session=True)):
                bad=copy.deepcopy(reports);mutate(bad)
                with self.assertRaises(ValueError):continuity.compare_first_step(root/'recording',bad)


if __name__=='__main__':unittest.main()
