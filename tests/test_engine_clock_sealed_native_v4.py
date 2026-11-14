"""Artifact filesystem topology and bounded redacted failure fixtures only."""
import json
from pathlib import Path
import tempfile
import unittest
try:from scripts import engine_clock_sealed_native_run_v4 as r
except ImportError:r=None

class NativeEvidenceTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(r,'physical evidence/cache boundary absent')
    def test_private_cache_is_outside_artifact_walk(self):
        with tempfile.TemporaryDirectory() as td:
            work=Path(td)/'execution';work.mkdir();routes=r.prepare_routes(work,Path(td)/'repo')
            private=Path(routes['cache'])/'case_00/mesa_shader_cache';private.mkdir(parents=True)
            private.chmod(0)
            try:
                self.assertFalse(Path(routes['cache']).is_relative_to(work))
                self.assertEqual(Path(td)/'native-cache',Path(routes['cache']))
                self.assertNotIn(private,list(work.rglob('*')))
                self.assertTrue(Path(routes['output']).is_relative_to(work))
            finally:private.chmod(0o700)
    def context(self):return dict(request_sha256='a'*64,source_sha='b'*40,head_sha='c'*40)
    def put(self,work,name,value):
        path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))
    def test_missing_malformed_or_unbound_case_preserves_unknown_bounds(self):
        with tempfile.TemporaryDirectory() as td:
            work=Path(td);ctx=self.context()
            self.assertEqual([0,1],r.failure_summary(work,ctx,{})['provider_bounds'])
            self.put(work,'output/phase.json',dict(context={'request_sha256':'wrong'},launch={'nonce':'d'*64}))
            self.put(work,'output/case_00/case.json',dict(provider_lower_bound=0,provider_upper_bound=0))
            self.assertEqual([0,1],r.failure_summary(work,ctx,{})['provider_bounds'])
            (work/'output/phase.json').write_bytes(b'{bad')
            self.assertEqual([0,1],r.failure_summary(work,ctx,{})['provider_bounds'])
    def test_bound_failure_is_redacted_without_claiming_acceptance(self):
        with tempfile.TemporaryDirectory() as td:
            work=Path(td);ctx=self.context();secret='SENTINEL_PRIVATE_TOKEN'
            self.put(work,'output/phase.json',dict(context=ctx,parent_pid=1,parent_uuid='e'*32,status='FAILED_OR_INCOMPLETE',launch=dict(nonce='d'*64,error='child '+secret)))
            self.put(work,'output/case_00/case.json',dict(context=ctx,nonce='d'*64,parent_pid=1,parent_uuid='e'*32,request_sha256='a'*64,provider_lower_bound=1,provider_upper_bound=1,error='https://name:password@host/path?token='+secret))
            result=r.failure_summary(work,ctx,{'GH_TOKEN':secret});encoded=json.dumps(result)
            self.assertNotIn(secret,encoded);self.assertNotIn('password',encoded)
            self.assertEqual([1,1],result['provider_bounds']);self.assertFalse(result['accepted'])
    def test_symlink_and_oversized_failure_metadata_not_followed(self):
        with tempfile.TemporaryDirectory() as td:
            work=Path(td);(work/'output').mkdir();(work/'output/phase.json').symlink_to('/etc/passwd')
            self.assertEqual([0,1],r.failure_summary(work,self.context(),{})['provider_bounds'])
            (work/'output/phase.json').unlink();(work/'output/phase.json').write_bytes(b'x'*(2*1024**2+1))
            self.assertEqual([0,1],r.failure_summary(work,self.context(),{})['provider_bounds'])

if __name__=='__main__':unittest.main()
