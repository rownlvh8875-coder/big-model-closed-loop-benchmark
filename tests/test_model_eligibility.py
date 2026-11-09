"""No network and no model download; contract-only eligibility tests."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from bigbench.model_eligibility import scan_candidates,inspect_candidate
from bigbench.onnx_contract import ModelContractError


class CandidateEligibilityTests(unittest.TestCase):
    def test_existing_candidates_are_only_manifests(self):
        r=scan_candidates(Path('model_specs'))
        self.assertGreaterEqual(r['candidate_count'],4)
        self.assertFalse(r['model_scoring_allowed'])
        self.assertIn('n16',r['navigation_required'])
        self.assertTrue(all(v['status']=='MANIFEST_ONLY_MODEL_WEIGHTS_NOT_VERIFIED'
                            for v in r['candidates']))

    def test_navigation_never_marked_as_plain_video(self):
        n=inspect_candidate(Path('model_specs/n16.json'))
        self.assertTrue(n.needs_navigation)
        self.assertIn('state_navigation_features_q',n.recurrent_states)

    def test_absent_directory_fails(self):
        with TemporaryDirectory() as d:
            with self.assertRaises(ModelContractError):
                scan_candidates(Path(d)/'missing')

    def test_duplicate_weight_identity_not_silently_double_counted(self):
        with TemporaryDirectory() as d:
            a=json.loads(Path('model_specs/md-v3.json').read_text(encoding='utf-8'))
            for name in ('a','b'):
                (Path(d)/(name+'.json')).write_text(json.dumps(a),encoding='utf-8')
            with self.assertRaises(ModelContractError):
                scan_candidates(Path(d))


if __name__=='__main__':
    unittest.main()
