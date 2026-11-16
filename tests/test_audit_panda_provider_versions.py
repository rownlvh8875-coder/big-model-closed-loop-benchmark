import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import audit_panda_provider_versions as receiver
from scripts import panda_provider_version_witness as w
from scripts import panda_sdk_cg_runpath_json as prior
from tests.test_panda_provider_version_witness import ci_fixture

class ProviderAuditTests(unittest.TestCase):
    def assert_negative(self,result,out):
        self.assertEqual(result,json.loads((out/'acceptance.json').read_text()));self.assertEqual(result['status'],'FAILED');self.assertFalse(result['actions_output_origin_authenticated']);self.assertFalse(result['diagnostic_witnesses_complete']);self.assertFalse(result['legacy_provider_blocks_removed'])
        for flag in w.FORBIDDEN:self.assertIs(result[flag],False)
        for key in ['new_sdk_builds','new_workflow_activations','artifact_downloads','image_operations','scientific_native_runs']:self.assertEqual(result[key],0)
    def test_frozen318_and_both_prior_verdicts_are_bound(self):
        state=receiver.frozen_state();self.assertEqual(len(state['source_closure']),318);self.assertEqual(state['prior_acceptance_sha256'],'4045e856383d3bf947688f1f4998083f1cb5d8b4ceea5dad94b430ce6e6c0a46');self.assertEqual(state['old_failure_sha256'],'d21eca8a87c507f2cabc6f86e3a293b2c48ce23105a4864344655a94acad789d')
        target=w.ROOT/w.contract()['prior_acceptance_path'];original=w.read
        with patch.object(w,'read',side_effect=lambda p,limit:b'corrupt positive receipt' if Path(p)==target else original(p,limit)),self.assertRaises(ValueError):receiver.frozen_state()
        target=w.ROOT/prior.contract()['old_failure_path'];original=prior.read
        with patch.object(prior,'read',side_effect=lambda p,limit:b'corrupt failed receipt' if Path(p)==target else original(p,limit)),self.assertRaises(ValueError):receiver.frozen_state()
    def test_source318_contains_only_the_four_new_paths_beyond_frozen314(self):
        result=w.source_closure();self.assertEqual(len(result),318);frozen=w.parse(w.read(w.ROOT/w.contract()['frozen_source_path'],1024**2));self.assertEqual(set(result)-set(frozen),set(w.contract()['new_source_paths']));self.assertEqual({p:result[p] for p in frozen},frozen)
        with self.assertRaises(ValueError):receiver.verify_source('f'*40)
    def test_prior_gate_hash_flags_and_canonical_regular_path_are_checked(self):
        gate=dict(schema='panda-sdk-cg-runpath-static-gate-v3',status='CG_EIGEN_RUNPATH_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME',loader_metadata={},provider_audit={},**{k:False for k in w.FORBIDDEN})
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'gate.json';path.write_text(json.dumps(gate));digest=w.sha(path.read_bytes());self.assertEqual(receiver.read_prior_gate(path,digest),gate)
            with self.assertRaises(ValueError):receiver.read_prior_gate(path,'0'*64)
            raw=path.read_bytes();path.write_bytes(raw.replace(b'NOT_RUNTIME',b'BAD_RUNTIME'))
            with self.assertRaises(ValueError):receiver.read_prior_gate(path,digest)
            gate['native_admitted']=True;path.write_text(json.dumps(gate))
            with self.assertRaises(ValueError):receiver.read_prior_gate(path,w.sha(path.read_bytes()))
            path.unlink();path.symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):receiver.read_prior_gate(path,'0'*64)
    def test_wrong_source_and_client_bootstrap_failures_leave_negative(self):
        for mode in ['source','client']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                out=Path(d)/'audit'
                if mode=='source':result=receiver.audit('f'*40,[],out)
                else:
                    with patch.object(receiver,'verify_source',return_value=receiver.frozen_state()),patch.object(receiver,'make_client',side_effect=ValueError('client unavailable')):result=receiver.audit('a'*40,[],out)
                self.assert_negative(result,out)
    def test_wrong_own_ci_is_rejected_before_any_original_producer_read(self):
        source,registrations,proofs=ci_fixture();proofs[0]['jobs']['jobs'][0]['head_sha']='b'*40
        class OnlyCiReads:
            def get_json(self,path,name):
                for registration,proof in zip(registrations,proofs):
                    for key,suffix in [('run',''),('jobs','/jobs'),('artifacts','/artifacts')]:
                        if path=='actions/runs/'+str(registration['run_id'])+suffix:return proof[key]
                raise AssertionError('original producer read before invalid CI was rejected')
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'audit'
            with patch.object(receiver,'verify_source',return_value=receiver.frozen_state()),patch.object(receiver,'make_client',return_value=OnlyCiReads()):result=receiver.audit(source,registrations,out)
            self.assert_negative(result,out);self.assertTrue(result['failure'].startswith('ValueError:'))
    def child(self,code,out):
        process=subprocess.run([sys.executable,'-B','-c',code,str(out)],cwd=w.ROOT,capture_output=True,text=True,timeout=30);self.assertEqual(process.returncode,0,process.stdout+process.stderr);self.assert_negative(json.loads((out/'acceptance.json').read_text()),out)
    def test_fresh_import_failure_has_a_negative_before_frozen_dependency_reads(self):
        code="""
import os,sys
from pathlib import Path
original=os.open
def blocked(path,*args,**kwargs):
    if str(path).endswith('docs/evidence/panda-sdk-cg-residual-01/contract.json'):raise OSError('fixture frozen import read failure')
    return original(path,*args,**kwargs)
os.open=blocked
from scripts import audit_panda_provider_versions as receiver
result=receiver.audit('f'*40,[],Path(sys.argv[1]))
assert result['status']=='FAILED' and not result['diagnostic_witnesses_complete']
"""
        with tempfile.TemporaryDirectory() as d:self.child(code,Path(d)/'audit')
    def test_actual_final_write_error_retains_initial_negative(self):
        code="""
import json,resource,signal,sys
from pathlib import Path
from unittest.mock import patch
from scripts import audit_panda_provider_versions as receiver
signal.signal(signal.SIGXFSZ,signal.SIG_IGN)
def fail(source):
    resource.setrlimit(resource.RLIMIT_FSIZE,(0,resource.getrlimit(resource.RLIMIT_FSIZE)[1]))
    raise ValueError('fixture after initial negative')
with patch.object(receiver,'verify_source',side_effect=fail):result=receiver.audit('a'*40,[],Path(sys.argv[1]))
assert result==json.loads((Path(sys.argv[1])/'acceptance.json').read_text())
assert sorted(p.name for p in Path(sys.argv[1]).iterdir())==['acceptance.json']
"""
        with tempfile.TemporaryDirectory() as d:self.child(code,Path(d)/'audit')
    def test_fresh_output_guard_preserves_existing_results_and_prior_receipts(self):
        paths=[w.ROOT/w.contract()['prior_acceptance_path'],w.ROOT/prior.contract()['old_failure_path']];before=[p.read_bytes() for p in paths]
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'audit';out.mkdir();(out/'acceptance.json').write_text('existing DATA')
            with self.assertRaises(ValueError):receiver.audit('a'*40,[],out)
            self.assertEqual((out/'acceptance.json').read_text(),'existing DATA')
        self.assertEqual([p.read_bytes() for p in paths],before)

if __name__=='__main__':unittest.main()
