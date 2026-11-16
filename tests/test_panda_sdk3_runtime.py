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

    def test_owned_display_outlives_the_child_finalization(self):
        import subprocess,sys,time
        from scripts import panda_sdk3_diagnostic as child_module
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);ready=d/'ready';finished=d/'finalized'
            server_code="import signal,sys,time;from pathlib import Path;signal.signal(signal.SIGTERM,lambda *_:sys.exit(0 if Path(sys.argv[2]).exists() else 2));Path(sys.argv[1]).write_text('ready');time.sleep(10)"
            server=subprocess.Popen([sys.executable,'-B','-c',server_code,str(ready),str(finished)])
            try:
                until=time.monotonic()+3
                while not ready.exists() and time.monotonic()<until:time.sleep(.01)
                self.assertTrue(ready.exists())
                program="import atexit,time;from pathlib import Path;atexit.register(lambda:Path(%r).write_text('finalized'));time.sleep(.02)" % str(finished)
                child=subprocess.Popen([sys.executable,'-B','-c',program])
                rc=child_module.wait_child_then_stop_server(child,server,3)
                self.assertEqual(rc,0);self.assertEqual(server.returncode,0);self.assertEqual(finished.read_text(),'finalized')
            finally:
                if 'child' in locals():
                    if child.poll() is None:child.kill()
                    child.wait()
                if server.poll() is None:server.kill();server.wait()

    def test_standard_showbase_checkpoint_is_required_for_that_factory(self):
        e,r=self.probe();prefix=[x['stage'] for x in e[:11]]
        names=prefix+['SHOWBASE_BEFORE','SHOWBASE_AFTER','DRIVER_AFTER','FRAME_0_BEFORE','FRAME_0_AFTER','FRAME_1_BEFORE','FRAME_1_AFTER','CLEANUP_BEFORE','CLEANUP_AFTER']
        events=[dict(stage=n,nonce=r['nonce'],pid=r['pid'],monotonic=float(i)) for i,n in enumerate(names)]
        r['factory']='showbase'
        self.assertTrue(runtime.validate_probe(events,r,0,r['nonce'],'core-first',factory='showbase')['selected_runtime_compatible'])
        with self.assertRaises(ValueError):runtime.validate_probe(events[:-1],r,0,r['nonce'],'core-first',factory='showbase')

    def test_publisher_reference_is_accepted_only_as_a_separate_control(self):
        e,r=self.probe();r.update(status='PANDA_REFERENCE_GLX_FRAMES_OBSERVED',sdk_sha256=runtime.REFERENCE_SHA,source_stats=[],observer_instrumented=False)
        value=runtime.validate_reference_probe(e,r,0,r['nonce'],'core-first')
        self.assertTrue(value['reference_frames_verified']);self.assertFalse(value['selected_runtime_compatible'])
        with self.assertRaises(ValueError):runtime.validate_probe(e,r,0,r['nonce'],'core-first')

    def test_reference_extraction_uses_the_pinned_original_layer_not_the_sdk_overlay(self):
        import io,tarfile
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);layers=[]
            for raw in [b'publisher',b'new-sdk']:
                stream=io.BytesIO()
                with tarfile.open(fileobj=stream,mode='w') as t:
                    info=tarfile.TarInfo(runtime.SDK_PATH.lstrip('/'));info.size=len(raw);t.addfile(info,io.BytesIO(raw))
                layers.append(stream.getvalue())
            image=d/'image.tar'
            with tarfile.open(image,'w') as t:
                manifest=json.dumps([dict(Layers=['base.tar','overlay.tar'])]).encode()
                for name,raw in [('manifest.json',manifest),('base.tar',layers[0]),('overlay.tar',layers[1])]:
                    info=tarfile.TarInfo(name);info.size=len(raw);t.addfile(info,io.BytesIO(raw))
            out=runtime.extract_reference(image,d/'reference.so',expected_size=9,expected_sha=hashlib.sha256(b'publisher').hexdigest())
            self.assertEqual(out.read_bytes(),b'publisher')

    def prior_bundle(self,root):
        root=Path(root);probes=[]
        for index in [3,4]:
            d=root/f'probe-{index}-sdk3-showbase';d.mkdir(parents=True)
            e,r=self.probe();names=[x['stage'] for x in e[:11]]+['SHOWBASE_BEFORE','SHOWBASE_AFTER','DRIVER_AFTER','FRAME_0_BEFORE','FRAME_0_AFTER','FRAME_1_BEFORE','FRAME_1_AFTER','CLEANUP_BEFORE','CLEANUP_AFTER']
            e=[dict(stage=n,nonce=r['nonce'],pid=r['pid'],monotonic=float(i)) for i,n in enumerate(names)];r.update(factory='showbase',child_finalized_before_server_stop=True,server_returncode=0)
            execution=dict(returncode=0,failure=None,owned_container_removed=True,container_id=str(index)*64,stopped_state=dict(OOMKilled=False,Running=False,Pid=0))
            row=dict(index=index,role='sdk3',factory='showbase',load_order='core-first',nonce=r['nonce'],selected_runtime_compatible=True,execution=execution);probes.append(row)
            for name,v in [('report.json',r),('execution.json',execution),('native-child.json',dict(pid=r['pid'],returncode=0,server_returncode=0,spawn_attempted=True))]:(d/name).write_text(json.dumps(v))
            (d/'stdout.log').write_text(''.join('STAGE7_EVENT '+json.dumps(x)+'\n' for x in e))
        (root/'summary.json').write_text(json.dumps(dict(source_sha='3bc46af75a2ef1f8cec415139c3688e0c14428ed',sdk_sha256=runtime.SDK_SHA,image=runtime.IMAGE,showbase_compatible=True,probes=probes,official_model_processes=1,strict_result='NOT_RUN')))
        return root

    def test_prior_glx_is_recomputed_without_promoting_the_failed_model_cohort(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.prior_bundle(d);v=runtime.validate_prior_glx(root)
            self.assertTrue(v['selected_sdk_glx_qualified']);self.assertEqual(v['verified_sdk_glx_children'],2)
            self.assertFalse(v['prior_model_cohort_qualified']);self.assertFalse(v['stage7_complete'])

    def test_prior_success_flag_cannot_hide_bad_pixels_or_a_missing_second_child(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.prior_bundle(d);p=root/'probe-4-sdk3-showbase'/'report.json';r=json.loads(p.read_text());r['frames'][0]['raw_hex']='00'*192;r['frames'][0]['sha256']=hashlib.sha256(bytes(192)).hexdigest();p.write_text(json.dumps(r))
            with self.assertRaises(ValueError):runtime.validate_prior_glx(root)
            p.unlink()
            with self.assertRaises((ValueError,FileNotFoundError)):runtime.validate_prior_glx(root)

    def test_runtime_container_is_bounded_readonly_and_has_no_network_or_extra_sdk(self):
        with tempfile.TemporaryDirectory() as d:
            cmd=runtime.container_command('owned-sdk3-test',Path(d),Path(d)/'sdk',Path(d)/'out',['--load-order','core-first'])
            for literal in ['--read-only','none','65534:65534','ALL','no-new-privileges','2g','128']:
                self.assertIn(literal,cmd)
            self.assertEqual(sum('dst='+runtime.SDK_PATH in x for x in cmd),1)
            self.assertNotIn('--privileged',cmd)


if __name__=='__main__':unittest.main()
