"""The new lifecycle retains admission and stops on genuine failure prefixes."""
import unittest
import subprocess
import sys
from pathlib import Path
try:
    from scripts import renderer_tasks_sealed_v1 as n
    from scripts import renderer_tasks_sealed_v1_container as child
    from scripts import renderer_tasks_sealed_v1_lifecycle as life
    from scripts import renderer_tasks_sealed_v1_archive as archive
except ImportError:n=child=life=archive=None


class RendererSealedLifecycleTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(life,'new retained host lifecycle required')
    def test_failed_callback_case_stops_before_next_provider(self):
        seen=[];prefixes=[]
        def run(index,enabled,repeat):
            seen.append(index)
            return dict(error='callback failure',cleanup_errors=[],exit_code=1,reaped=True,group_gone=True)
        rows,complete=child.execute_cases('abba',run,lambda r:prefixes.append(list(r)))
        self.assertFalse(complete);self.assertEqual(seen,[0]);self.assertEqual(len(rows),1)
    def test_control_poll_does_not_retry_api_error_or_grant_approval(self):
        seen=[]
        def fetch():seen.append(1);raise ValueError('HTTP rejected')
        with self.assertRaises(ValueError):life.bounded_poll(fetch,lambda _:True,lambda *_:None)
        self.assertEqual(seen,[1])
    def test_metadata_attestor_import_stays_stdlib_and_provider_free(self):
        root=Path(__file__).resolve().parents[1]
        code="import sys;sys.path.insert(0,'.');from scripts import renderer_tasks_sealed_v1_attest;assert not any(k.split('.')[0] in {'numpy','cv2','panda3d','metadrive','onnxruntime'} for k in sys.modules)"
        result=subprocess.run([sys.executable,'-I','-S','-B','-c',code],cwd=root,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
    def test_attestor_does_not_promote_callback_metadata_to_pixel_replay(self):
        fields=('run_id','workflow_id','host_job_id','producer_head_sha','source_sha','artifact_id',
                'artifact_sha256','artifact_size_bytes','lease_sha256','phase_sha256','source_closure_sha256','producer_request_sha256')
        checked={k:1 for k in fields};checked['identity']={'core_sha256':'a'*64}
        record=archive.attestation_record(checked,42)
        self.assertFalse(record['independent_pixel_replay']);self.assertEqual(record['native_providers'],0)
        self.assertEqual(record['schema'],'renderer-tasks-canary-attestation-v1')


if __name__=='__main__':unittest.main()
