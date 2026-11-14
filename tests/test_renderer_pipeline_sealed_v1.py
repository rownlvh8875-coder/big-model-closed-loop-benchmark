"""New campaign authority/schedules; all witnesses here are synthetic CPU data."""
import copy
import json
from pathlib import Path
import unittest
try:
    from scripts import renderer_pipeline_sealed_v1 as n
except ImportError:n=None
ROOT=Path(__file__).resolve().parents[1]


def request(mode='canary'):
    approval=dict(canary_head_sha='2'*40,source_sha='1'*40,run_id=21,workflow_id=31,job_id=41,
        artifact_id=51,artifact_name=n.artifact('canary'),artifact_size_bytes=1234,artifact_sha256='a'*64,
        attestor_job_id=42,attestor_artifact_id=52,attestor_artifact_name=n.artifact('attestation'),
        attestor_artifact_size_bytes=987,attestor_artifact_sha256='b'*64,lease_sha256='c'*64,
        root_raw_accepted=True,fresh_raw_review_accepted=True)
    return dict(schema=n.REQUEST_SCHEMA,mode=mode,acceptance=approval if mode=='abba' else None,
        request_id=n.ID,repository=n.REPOSITORY,branch=n.BRANCH,workflow_path=n.WORKFLOW,
        reviewed_source_branch=n.SOURCE_BRANCH,reviewed_source_sha='1'*40,
        source_closure={p:'0'*64 for p in n.source_paths(ROOT)},
        source_ci=[dict(event='push',run_id=11),dict(event='pull_request',run_id=12)],
        budget=copy.deepcopy(n.BUDGET),lifecycle=copy.deepcopy(n.LIFECYCLE),native_budget=n.native_budget(mode),
        image_evidence=n.image_evidence(ROOT),official_model_calls=0,ort_sessions=0)


class RendererSealedProtocolTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(n,'separate callback campaign protocol required')
    def test_all_clocks_on_callback_abba_and_new_getter_allowance(self):
        self.assertEqual(n.schedule('abba'),[(True,0),(True,0),(True,1),(True,1)])
        self.assertEqual(n.callback_schedule('canary'),[True])
        self.assertEqual(n.callback_schedule('abba'),[False,True,True,False])
        c,a=n.native_budget('canary'),n.native_budget('abba')
        self.assertEqual((c['clock_getters'],a['clock_getters']),(96,384))
        self.assertEqual((c['callback_named_getters'],a['callback_named_getters']),(1680,3360))
        self.assertEqual((c['observer_getters'],a['observer_getters']),(2592,5472))
        self.assertEqual(c['providers']+a['providers'],5)
        self.assertEqual((c['submission_named_getters'],a['submission_named_getters']),(768,1536))
        self.assertEqual(n.BUDGET['observer_encoded_retention_bytes'],832*1024)
    def test_new_request_admits_only_complete_closure_and_own_schema(self):
        r=request();self.assertIs(n.validate_request(r,ROOT),r)
        from scripts import renderer_tasks_sealed_v1 as previous
        old=dict(r,schema=previous.REQUEST_SCHEMA)
        with self.assertRaises(ValueError):n.validate_request(old,ROOT)
        r['source_closure'].pop('scripts/renderer_task_callbacks.py')
        with self.assertRaises(ValueError):n.validate_request(r,ROOT)
    def test_original_frozen_paths_and_reviewed_observers_remain_in_closure(self):
        previous=json.loads((ROOT/'docs/evidence/STAGE7_ENGINE_CLOCK_PIXEL_FORENSICS_03.json').read_text())
        paths=n.source_paths(ROOT)
        self.assertTrue(set(previous['source_snapshot'])<=paths)
        self.assertTrue({'scripts/renderer_task_callbacks.py','scripts/renderer_task_binding.py',n.WORKFLOW}<=paths)
    def test_only_request_addition_can_activate_each_phase(self):
        for mode,parent,path in [('canary','1'*40,n.C_REQUEST),('abba','2'*40,n.A_REQUEST)]:
            r=request(mode);n.validate_activation(r,'3'*40,[parent],b'A\0'+path.encode()+b'\0','100644',n.BRANCH)
            with self.assertRaises(ValueError):n.validate_activation(r,'3'*40,[parent],b'M\0'+path.encode()+b'\0','100644',n.BRANCH)
            with self.assertRaises(ValueError):n.validate_activation(r,'3'*40,[parent],b'A\0'+path.encode()+b'\0A\0scripts/renderer_task_callbacks.py\0','100644',n.BRANCH)


if __name__=='__main__':unittest.main()
