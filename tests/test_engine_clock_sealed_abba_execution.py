"""Execution boundaries with controlled child/engine doubles; no native imports."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
try:
    from scripts import engine_clock_sealed_abba as n
    from scripts import engine_clock_sealed_abba_container as c
    from scripts import engine_clock_sealed_abba_run as r
except ImportError:
    n=c=r=None
ROOT=Path(__file__).resolve().parents[1]


class SealedAbbaExecutionTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(c,'sequential sealed ABBA execution missing')

    def test_four_fresh_case_order_and_each_prefix_is_persisted(self):
        seen=[];saved=[]
        def run_case(index,enabled,repeat):
            seen.append((index,enabled,repeat))
            return dict(index=index,error=None,cleanup_errors=[],exit_code=0,reaped=True,group_gone=True)
        rows,complete=c.execute_cases('abba',run_case,lambda rows:saved.append(copy.deepcopy(rows)))
        self.assertTrue(complete)
        self.assertEqual([(0,False,0),(1,True,0),(2,True,1),(3,False,1)],seen)
        self.assertEqual([1,2,3,4],[len(v) for v in saved]);self.assertEqual(4,len(rows))

    def test_failure_stops_before_next_case_and_preserves_prefix(self):
        seen=[];saved=[]
        def run_case(index,enabled,repeat):
            seen.append(index)
            return dict(index=index,error='rejected' if index==1 else None,cleanup_errors=[],exit_code=1 if index==1 else 0,reaped=True,group_gone=True)
        rows,complete=c.execute_cases('abba',run_case,lambda rows:saved.append(copy.deepcopy(rows)))
        self.assertFalse(complete);self.assertEqual([0,1],seen)
        self.assertEqual([1,2],[len(v) for v in saved]);self.assertEqual('rejected',rows[-1]['error'])

    def test_indexed_environment_does_not_inherit_cv2_loader_mutation(self):
        proof=dict(launch_environment=n.environment_profile(),environment=dict(n.environment_profile(),LD_LIBRARY_PATH=n.CV2_LD_LIBRARY_PATH))
        for index in (0,3):
            env=c.build_child_environment(proof,10,index)
            self.assertEqual('/work/cache/case_0'+str(index),env['MESA_SHADER_CACHE_DIR'])
            self.assertNotIn('LD_LIBRARY_PATH',env)
        with self.assertRaises(ValueError):c.build_child_environment(proof,10,4)
        bad=copy.deepcopy(proof);bad['launch_environment']['LD_LIBRARY_PATH']='/host'
        with self.assertRaises(ValueError):c.build_child_environment(bad,10,0)

    def test_permit_cannot_cross_case_or_phase(self):
        p=dict(schema='engine-clock-sealed-abba-permit-v1',mode='abba',index=2,parent_pid=1,parent_uuid='a'*32,process_group=37,nonce='b'*64,binding_sha256='c'*64,identity_sha256='d'*64)
        facts=dict(ancestors=[36,1],group=37,nonce='b'*64,binding_sha='c'*64,identity_sha='d'*64,mode='abba',index=2)
        n.validate_permit(p,**facts)
        for key,value in [('mode','canary'),('index',1),('nonce','e'*64),('group',38)]:
            bad=dict(facts);bad[key]=value
            with self.assertRaises(ValueError):n.validate_permit(p,**bad)

    def test_identity_gate_persists_exact_difference_before_rejecting(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'identity.json'
            with self.assertRaises(ValueError):r.identity_gate(dict(host='a'),dict(host='b'),path)
            report=json.loads(path.read_bytes())
            self.assertFalse(report['equal']);self.assertEqual('host',report['differences'][0]['path'])
            self.assertEqual('a',report['differences'][0]['accepted'])
            self.assertEqual('b',report['differences'][0]['observed'])

    def test_broken_accepted_canary_rejects_before_any_replay_or_provider(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):c.replay_canary(Path(td),dict(mode='abba'),dict(mode='abba'))

    def test_prestart_failure_never_starts_container(self):
        from time import perf_counter
        calls=[]
        class Engine:
            deadline=perf_counter()+3600
            host=json.loads((ROOT/(n.AUTH+'root-acceptance.json')).read_bytes())['host']
            profile=json.loads((ROOT/(n.AUTH+'root-acceptance.json')).read_bytes())['engine']
            def once(self,name):calls.append(name)
            def call(self,args,**kwargs):
                calls.append(args[0])
                if args[0]!='create':raise AssertionError('start before copied executable proof')
                return {'_stdout':b'b'*64+b'\n'}
            def copied_tree(self,*args):raise ValueError('owned prestart failure')
            def terminate(self,cid):calls.append('terminate')
        receipt=json.loads((ROOT/(n.AUTH+'preparation.json')).read_bytes())
        with tempfile.TemporaryDirectory() as td:
            work=Path(td)/'execution';work.mkdir()
            request=dict(mode='canary',reviewed_source_sha='1'*40,image_evidence=n.image_evidence(ROOT))
            with self.assertRaisesRegex(ValueError,'owned prestart failure'):
                r.launch_phase(Engine(),dict(config_digest=receipt['config_digest']),request,
                    dict(request_sha256='a'*64),receipt,(ROOT/(n.AUTH+'installed-files.json')).read_bytes(),work,ROOT)
            self.assertNotIn('start',calls);self.assertIn('terminate',calls)

    def test_mapping_accepts_only_current_case_nonexecutable_cache(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            raw='1000-2000 r--s 0 00:01 12 /work/cache/case_01/mesa_shader_cache/index\n'
            result=c.classify_map_view(raw,set(),set(),root/'good.json',cache_index=1)
            self.assertEqual([],result)
            self.assertTrue(json.loads((root/'good.json').read_bytes())['accepted'])
            for index,text,name in [(0,raw,'wrong-case'),(1,raw.replace('r--s','r-xs'),'executable')]:
                with self.assertRaises(ValueError):
                    c.classify_map_view(text,set(),set(),root/(name+'.json'),cache_index=index)
                self.assertFalse(json.loads((root/(name+'.json')).read_bytes())['accepted'])

    def test_genuine_cpu_fixture_is_replayed_and_tampered_raw_rejects(self):
        from test_engine_clock_native import DatasetTests
        from test_engine_clock_sealed_abba import SealedAbbaProtocolTests
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);output=root/'output';output.mkdir()
            old_phase,cases=DatasetTests().fixture(output)
            request=SealedAbbaProtocolTests().request('abba')
            consumed=dict(request,mode='canary',acceptance=None,native_budget=n.native_budget('canary'))
            raw=n.canonical(consumed);(root/'consumed-request.json').write_bytes(raw)
            context=dict(repository=n.REPOSITORY,event='push',attempt=1,run_id=21,workflow_id=31,
                head_sha='2'*40,source_sha='1'*40,request_sha256=n.sha(raw),source_closure_verified=True,
                authenticated_api_origin='https://api.github.com',mode='canary')
            identity=dict(synthetic_cpu_fixture=True)
            case=cases[0];case.update(context=context,source_snapshot=consumed['source_closure'],runtime=identity,request_sha256=n.sha(raw))
            (output/'case_00/case.json').write_bytes(n.canonical(case))
            phase=dict(mode='canary',status='SEALED_ABBA_CANARY_RECORDED',context=context,identity=identity,
                parent_pid=old_phase['parent_pid'],parent_uuid=old_phase['parent_uuid'],launches=old_phase['launches'],
                comparisons=[],native_budget=n.native_budget('canary'),budget=n.BUDGET,
                official_model_calls=0,ort_sessions=0,scientific_result_promoted=False)
            self.assertEqual(6,c.replay_canary(output,phase,request)['capture_pairs'])
            path=output/'case_00/capture_01/raw_road.png';path.write_bytes(b'changed')
            with self.assertRaises(ValueError):c.replay_canary(output,phase,request)

    def test_parent_child_identity_mismatches_persist_independent_observations(self):
        from unittest.mock import patch
        self.assertTrue(callable(getattr(c,'admission_comparison',None)), 'typed inner admission evidence missing')
        for tag in ('parent','child-00'):
            for kind,left,right,path in [('host',dict(release='a'),dict(release='b'),'release'),
                ('identity',dict(host_details=dict(affinity_ids=[0,1],memory_total_bytes=8*1024**3)),
                 dict(host_details=dict(affinity_ids=[1,2],memory_total_bytes=9*1024**3)),'host_details.affinity_ids')]:
                with tempfile.TemporaryDirectory() as td,patch.object(c,'OUT',Path(td)):
                    constructed=[]
                    with self.assertRaises(ValueError):
                        c.admission_comparison(tag,kind,left,right)
                        constructed.append('provider')
                    report=json.loads((Path(td)/(tag+'-'+kind+'-comparison.json')).read_bytes())
                    self.assertEqual([],constructed);self.assertFalse(report['equal'])
                    self.assertEqual(right,report['observed'])
                    self.assertTrue(any(d['path']==path for d in report['differences']))

    def test_parent_selection_failure_preserves_bound_phase_before_provider(self):
        from unittest.mock import patch
        binding=dict(request=dict(mode='canary'),context=dict(run_id=21,head_sha='2'*40),identity=dict(expected=True))
        with tempfile.TemporaryDirectory() as td,patch.object(c,'OUT',Path(td)),\
            patch.object(c,'read_binding',return_value=(binding,'a'*64),create=True),\
            patch.object(c,'preflight',side_effect=ValueError('owned selection rejection')),\
            patch.object(c,'run_case',side_effect=AssertionError('provider must not start')):
            try:result=c.parent()
            except ValueError:result=None
            path=Path(td)/'phase.json'
            self.assertTrue(path.is_file(),'parent admission rejection lost its phase ledger')
            report=json.loads(path.read_bytes())
            self.assertEqual(1,result);self.assertEqual('FAILED_OR_INCOMPLETE',report['status'])
            self.assertEqual(binding['context'],report['context']);self.assertEqual([],report['launches'])
            self.assertFalse(report['identity_verified']);self.assertEqual('parent-preflight',report['admission_stage'])
            self.assertIn('owned selection rejection',str(report['error']))


if __name__=='__main__':unittest.main()
