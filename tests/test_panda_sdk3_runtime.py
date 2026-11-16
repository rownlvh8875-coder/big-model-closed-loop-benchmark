"""Pinned SDK runtime evidence rejects incomplete or unrelated observations."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from scripts import panda_sdk3_runtime as runtime


class Sdk3RuntimeEvidence(unittest.TestCase):
    def probe(self, order='core-first'):
        nonce='1a'*16
        core=['CORE_BEFORE','CORE_AFTER'];sdk=['PRELOAD_BEFORE','PRELOAD_AFTER','SDK_BEFORE','SDK_AFTER']
        stages=['BOOT']+(core+sdk if order=='core-first' else sdk+core)+['SERVER_BEFORE','SERVER_AFTER','PRC_BEFORE','PRC_AFTER','ENGINE_BEFORE','ENGINE_AFTER','PIPE_BEFORE','PIPE_AFTER','OUTPUT_BEFORE','OUTPUT_AFTER','DRIVER_AFTER','FRAME_0_BEFORE','FRAME_0_AFTER','FRAME_1_BEFORE','FRAME_1_AFTER','CLEANUP_BEFORE','CLEANUP_AFTER']
        events=[dict(stage=s,nonce=nonce,pid=73,monotonic=float(i)) for i,s in enumerate(stages)]
        frames=[]
        for i in range(2):
            raw=bytes([(249,209,230),(226,141,88)][i])*64
            frames.append(dict(index=i,raw_hex=raw.hex(),nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        report=dict(status='SDK3_GLX_FRAMES_OBSERVED',nonce=nonce,pid=73,load_order=order,
                    sdk_sha256=runtime.SDK_SHA,core_sha256=runtime.CORE_SHA,panda_version='1.10.13',
                    driver=dict(vendor='Mesa',renderer='softpipe',version='4.5'),frames=frames,
                    objects={k:i+100 for i,k in enumerate(['pipe','output','gsg','texture','camera'])},
                    source_stats=[dict(returned=0,guards_ok=True,values={k:0 for k in runtime.STATS_FIELDS}) for _ in range(2)],
                    cleanup=dict(windows_after=0,texture_ram_after=False,render_calls=4,ram_reads=2,cpp_deallocation_verified=False))
        return events,report

    def test_exact_challenged_frames_and_selected_objects_pass_for_each_load_order(self):
        for order in ['core-first','sdk-first']:
            e,r=self.probe(order)
            self.assertTrue(runtime.validate_probe(e,r,0,r['nonce'],order)['selected_runtime_compatible'])

    def test_missing_or_reordered_checkpoint_and_nonzero_exit_never_pass(self):
        e,r=self.probe()
        for events,rc in [(e[:-1],0),(e[1:]+e[:1],0),(e,-6)]:
            with self.assertRaises(ValueError):runtime.validate_probe(events,r,rc,r['nonce'],'core-first')

    def test_frame_bytes_are_checked_even_when_digest_is_recomputed(self):
        e,r=self.probe();raw=bytes([0])*192;r['frames'][0].update(raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError):runtime.validate_probe(e,r,0,r['nonce'],'core-first')

    def test_wrong_identity_driver_observer_or_cleanup_reject(self):
        e,valid=self.probe()
        for key,value in [('sdk_sha256','0'*64),('core_sha256','0'*64),('nonce','ff'*16),
                          ('driver',dict(vendor='Mesa',renderer='llvmpipe',version='4.5')),
                          ('cleanup',dict(windows_after=1,texture_ram_after=False,render_calls=4,ram_reads=2))]:
            r=copy.deepcopy(valid);r[key]=value
            with self.assertRaises(ValueError):runtime.validate_probe(e,r,0,valid['nonce'],'core-first')
        r=copy.deepcopy(valid);r['source_stats'][1]['values']['forwarded']=1
        with self.assertRaises(ValueError):runtime.validate_probe(e,r,0,valid['nonce'],'core-first')

    def test_exact_archive_member_is_extracted_without_unselected_payloads(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);z=d/'proof.zip'
            with ZipFile(z,'w') as f:f.writestr('candidate/lib.so.data',b'sdk');f.writestr('reports/a.json',b'{}')
            result=runtime.verify_member(z,'candidate/lib.so.data',3,hashlib.sha256(b'sdk').hexdigest(),d/'lib.so')
            self.assertEqual(result.read_bytes(),b'sdk');self.assertFalse((d/'reports').exists())

    def test_duplicate_unsafe_or_wrong_archive_bytes_are_rejected_before_publication(self):
        import warnings
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            for i,rows in enumerate([[('candidate/lib.so.data',b'bad')],
                                     [('candidate/lib.so.data',b'sdk'),('../escape',b'x')],
                                     [('candidate/lib.so.data',b'sdk'),('candidate/lib.so.data',b'sdk')]]):
                z=d/f'{i}.zip';out=d/f'{i}.so'
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore',UserWarning)
                    with ZipFile(z,'w') as f:
                        for name,raw in rows:f.writestr(name,raw)
                with self.assertRaises(ValueError):runtime.verify_member(z,'candidate/lib.so.data',3,hashlib.sha256(b'sdk').hexdigest(),out)
                self.assertFalse(out.exists())

    def test_strict_gate_requires_four_unique_complete_conditions(self):
        rows=[dict(seed=s,scenario=c,exact_repeated_execution_gate_passed=True,status='STRICT_NATIVE_ONNX_REPEAT_MATCH')
              for s in [20261109,20261110] for c in ['s_curve_left_right','s_curve_right_left']]
        self.assertTrue(runtime.model_gate(rows)['strict_pass'])
        for bad in [rows[:-1],rows+[rows[0]],rows[:3]+[rows[0]]]:
            with self.assertRaises(ValueError):runtime.model_gate(bad)
        rows[2].update(exact_repeated_execution_gate_passed=False,status='STRICT_NATIVE_ONNX_REPEAT_MISMATCH')
        gate=runtime.model_gate(rows);self.assertFalse(gate['strict_pass']);self.assertEqual(gate['passed'],3)
        self.assertFalse(gate['expansion_admitted'])

    def test_failed_pair_counts_only_observed_pids_and_retains_unknown_spawn_bounds(self):
        ledger=[dict(index=0,spawn_attempted=True,pid=37,returncode=0),dict(index=1,spawn_attempted=True,pid=None,returncode=None)]
        self.assertEqual(runtime.observed_model_processes(ledger),dict(known=1,upper=2,spawn_attempts=2))
        ledger[1]['pid']=41
        self.assertEqual(runtime.observed_model_processes(ledger),dict(known=2,upper=2,spawn_attempts=2))

    def test_actual_renderer_cleanup_schema_is_accepted_without_full_deallocation_claim(self):
        from scripts.panda_real_glx_objects import Renderer
        renderer=Renderer(None);renderer.render_calls=4;renderer.ram_reads=2
        e,r=self.probe();r['cleanup']=renderer.close()
        self.assertTrue(runtime.validate_probe(e,r,0,r['nonce'],'core-first')['selected_runtime_compatible'])
        self.assertFalse(r['cleanup']['cpp_deallocation_verified'])

    def docker_stub(self,mode):
        from subprocess import CompletedProcess,TimeoutExpired,PIPE
        state=dict(created=False,owner='',calls=[])
        def invoke(cmd,**kw):
            state['calls'].append((cmd,kw));action=cmd[1]
            if action=='create':
                state['created']=True
                if '--label' in cmd:state['owner']=cmd[cmd.index('--label')+1].split('=',1)[1]
                if mode=='create-timeout':raise TimeoutExpired(cmd,kw['timeout'])
                if hasattr(kw.get('stdout'),'write'):kw['stdout'].write(b'abc123\n')
                return CompletedProcess(cmd,0,stdout='abc123\n',stderr='')
            if action=='inspect':
                row=dict(Id='abc123',Config=dict(Labels={'stage7.sdk3.owner':state['owner']}),State=dict(Running=False,Pid=0,OOMKilled=False,ExitCode=0))
                return CompletedProcess(cmd,0 if state['created'] else 1,stdout=json.dumps([row]) if state['created'] else '[]',stderr='')
            if action=='start':return CompletedProcess(cmd,0,stdout='',stderr='')
            if action=='rm' and mode=='remove-timeout':raise TimeoutExpired(cmd,kw['timeout'])
            return CompletedProcess(cmd,0,stdout='',stderr='')
        return state,invoke

    def test_removal_timeout_still_publishes_negative_execution_receipt(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);state,stub=self.docker_stub('remove-timeout')
            with patch.object(runtime.subprocess,'run',side_effect=stub):
                try:runtime.run_container('owned-test',d/'sdk',d/'out',[])
                except Exception:pass
            receipt=d/'out'/'execution.json'
            self.assertTrue(receipt.exists(),'Docker removal failure lost execution facts')
            value=json.loads(receipt.read_text());self.assertFalse(value['owned_container_removed']);self.assertTrue(value['failure'])

    def test_ambiguous_create_is_recovered_only_by_owned_label_and_removed(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);state,stub=self.docker_stub('create-timeout')
            with patch.object(runtime.subprocess,'run',side_effect=stub):value=runtime.run_container('owned-test',d/'sdk',d/'out',[])
            self.assertTrue(value['owned_container_removed']);self.assertTrue(value['failure'])
            self.assertFalse(any(c[0][1]=='start' for c in state['calls']))

    def test_glx_start_is_limited_to_the_declared_180_seconds(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);state,stub=self.docker_stub('ok')
            with patch.object(runtime.subprocess,'run',side_effect=stub):runtime.run_container('owned-test',d/'sdk',d/'out',[])
            self.assertEqual([kw['timeout'] for cmd,kw in state['calls'] if cmd[1]=='start'],[180])

    def test_independent_model_aggregate_rejects_a_self_consistent_wrong_model(self):
        from tests.test_aggregate_original_mdv3_current_recheck import mock_trial
        from scripts.compare_fresh_native_mdv3 import compare_fresh_trials
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for seed in [20261109,20261110]:
                for scene in ['s_curve_left_right','s_curve_right_left']:
                    folder=root/f'seed-{seed}'/scene;folder.mkdir(parents=True)
                    a=mock_trial(seed,scene,100);b=mock_trial(seed,scene,200)
                    for row in [a,b]:row['model_sha256']='0'*64
                    for name,row in [('run_0.json',a),('run_1.json',b),('strict_native_repeat_verdict.json',compare_fresh_trials(a,b))]:
                        (folder/name).write_text(json.dumps(row))
            with self.assertRaises(ValueError):runtime.aggregate_model_pairs(root)

    def test_runtime_container_is_bounded_readonly_and_has_no_network_or_extra_sdk(self):
        with tempfile.TemporaryDirectory() as d:
            cmd=runtime.container_command('owned-sdk3-test',Path(d),Path(d)/'sdk',Path(d)/'out',['--load-order','core-first'])
            for literal in ['--read-only','none','65534:65534','ALL','no-new-privileges','2g','128']:
                self.assertIn(literal,cmd)
            self.assertEqual(sum('dst='+runtime.SDK_PATH in x for x in cmd),1)
            self.assertNotIn('--privileged',cmd)


if __name__=='__main__':unittest.main()
