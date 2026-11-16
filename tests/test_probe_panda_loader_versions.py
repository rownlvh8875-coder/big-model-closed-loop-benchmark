import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import probe_panda_loader_versions as p
from scripts import panda_loader_cpu_fixture as f
from scripts import panda_sdk_cg_runpath_json as historical

HOST=Path('/lib64/ld-linux-x86-64.so.2').resolve()

class FixedLoaderProbeTests(unittest.TestCase):
    def negative(self,result,out):
        self.assertEqual(result,json.loads((out/'acceptance.json').read_text()));self.assertEqual(result['status'],'FAILED');self.assertFalse(result['actions_output_origin_authenticated']);self.assertFalse(result['fixed_image_cpu_profile_observed']);self.assertFalse(result['sdk_target_execution']);self.assertEqual(result['scientific_native_runs'],0)
        for flag in historical.FORBIDDEN:self.assertIs(result[flag],False)
    def test_frozen322_and_prior_witness_and_original_verdicts_are_bound(self):
        state=p.frozen_state();self.assertEqual(len(state['source_closure']),322);self.assertEqual(state['old_failure_sha256'],'d21eca8a87c507f2cabc6f86e3a293b2c48ce23105a4864344655a94acad789d');self.assertEqual(state['prior_acceptance_sha256'],'4045e856383d3bf947688f1f4998083f1cb5d8b4ceea5dad94b430ce6e6c0a46')
        target=f.ROOT/f.contract()['prior_receipt_path'];original=f.read
        with patch.object(f,'read',side_effect=lambda path,limit:b'changed witness receipt' if Path(path)==target else original(path,limit)),self.assertRaises(ValueError):p.frozen_state()
        with self.assertRaises(ValueError):p.verify_source('f'*40)
    def test_no_explicit_cpu_flag_means_no_loader_attempts(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'probe';r=p.probe('a'*40,[],out);self.negative(r,out);self.assertEqual(r['loader_start_attempts'],0);self.assertEqual(r['loader_invocations'],0)
    def test_wrong_source_and_alternate_actual_output_are_negative_before_probes(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'probe';r=p.probe('f'*40,[],out,run_cpu_fixtures=True);self.negative(r,out);self.assertEqual(r['loader_start_attempts'],0)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'alternate'
            with patch.object(p,'verify_source',return_value=p.frozen_state()):r=p.probe('a'*40,[],out,run_cpu_fixtures=True)
            self.negative(r,out);self.assertEqual(r['loader_invocations'],0)
    def test_private_loader_copy_preserves_source_and_rejects_wrong_bytes_or_aliases(self):
        pin=f._record(HOST);before=HOST.stat();raw=HOST.read_bytes()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);record=p.stage_loader(HOST,root/'private'/'loader',pin);self.assertEqual(record['sha256'],pin['sha256']);self.assertEqual((root/'private/loader').read_bytes(),raw);self.assertEqual((root/'private/loader').stat().st_mode&0o777,0o500)
            with self.assertRaises(ValueError):p.stage_loader(HOST,root/'private'/'loader',pin)
            bad=dict(pin,sha256='0'*64)
            with self.assertRaises(ValueError):p.stage_loader(HOST,root/'bad',bad)
            (root/'alias').symlink_to(HOST)
            with self.assertRaises(ValueError):p.stage_loader(root/'alias',root/'bad2',pin)
            true=Path('/usr/bin/true').resolve()
            with self.assertRaises(ValueError):p.stage_loader(true,root/'bad3',f._record(true))
        self.assertEqual(HOST.read_bytes(),raw);self.assertEqual((before.st_mode,before.st_size,before.st_mtime_ns),(HOST.stat().st_mode,HOST.stat().st_size,HOST.stat().st_mtime_ns))
    def test_partial_and_unknown_execution_counts_are_preserved_without_sdk_admission(self):
        report=dict(loader_start_attempts=2,loader_invocations=None,loader_invocations_lower_bound=1,loader_invocations_upper_bound=2,verified_fixture_entries=1,controlled_loader_failures=0,sdk_target_execution=False,scientific_native_runs=0)
        result={};p.merge_execution_facts(result,report);self.assertIsNone(result['loader_invocations']);self.assertEqual((result['loader_invocations_lower_bound'],result['loader_invocations_upper_bound']),(1,2))
        for field,value in [('loader_start_attempts',5),('loader_start_attempts',True),('loader_invocations',0),('loader_invocations_lower_bound',3),('verified_fixture_entries',2),('sdk_target_execution',True)]:
            bad=dict(report,**{field:value})
            with self.subTest(field=field),self.assertRaises(ValueError):p.merge_execution_facts({},bad)
    def child(self,code,out):
        r=subprocess.run([sys.executable,'-B','-c',code,str(out)],cwd=f.ROOT,capture_output=True,text=True,timeout=30);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.negative(json.loads((out/'acceptance.json').read_text()),out)
    def test_fresh_import_failure_keeps_negative_without_a_false_zero_execution_claim(self):
        code="""
import os,sys
from pathlib import Path
original=os.open
def blocked(path,*args,**kwargs):
    if str(path).endswith('docs/evidence/panda-sdk-cg-residual-01/contract.json'):raise OSError('fixture dependency failure')
    return original(path,*args,**kwargs)
os.open=blocked
from scripts import probe_panda_loader_versions as p
r=p.probe('f'*40,[],Path(sys.argv[1]),run_cpu_fixtures=True)
assert r['status']=='FAILED' and r['loader_start_attempts']==0
"""
        with tempfile.TemporaryDirectory() as d:self.child(code,Path(d)/'probe')
    def test_final_write_failure_retains_negative_with_conservative_execution_bounds(self):
        code="""
import json,resource,signal,sys
from pathlib import Path
from unittest.mock import patch
from scripts import probe_panda_loader_versions as p
signal.signal(signal.SIGXFSZ,signal.SIG_IGN)
def fail(source):
    resource.setrlimit(resource.RLIMIT_FSIZE,(0,resource.getrlimit(resource.RLIMIT_FSIZE)[1]))
    raise ValueError('fixture late bootstrap write failure')
with patch.object(p,'verify_source',side_effect=fail):r=p.probe('a'*40,[],Path(sys.argv[1]),run_cpu_fixtures=True)
saved=json.loads((Path(sys.argv[1])/'acceptance.json').read_text())
assert r==saved and saved['loader_invocations'] is None and saved['loader_invocations_upper_bound']==4
assert not saved['fixed_image_cpu_profile_observed']
"""
        with tempfile.TemporaryDirectory() as d:self.child(code,Path(d)/'probe')
    def test_old_results_and_existing_output_are_never_overwritten(self):
        paths=[f.ROOT/f.contract()['prior_receipt_path'],f.ROOT/historical.contract()['old_failure_path']];before=[path.read_bytes() for path in paths]
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'probe';out.mkdir();(out/'acceptance.json').write_text('old DATA')
            with self.assertRaises(ValueError):p.probe('a'*40,[],out,run_cpu_fixtures=True)
            self.assertEqual((out/'acceptance.json').read_text(),'old DATA')
        self.assertEqual([path.read_bytes() for path in paths],before)

if __name__=='__main__':unittest.main()
