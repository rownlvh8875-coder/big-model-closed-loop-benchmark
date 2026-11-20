"""One combined review fix pass; all local fixtures are NOT native evidence."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from bigbench import preprocess_experiment_protocol as c
from scripts import run_preprocess_experiment as host


def metadata():
    from tests.test_recorded_official import AdmissionTests
    obj=AdmissionTests()
    r,x,m,ci=c.clone(AdmissionTests.good,c=c,host=host)(obj)
    for role in ('windows_push','windows_pr','software_api_pr'):
        ci[role]['jobs']['jobs'][0]['name']='software-host-allocation' if role=='software_api_pr' else 'windows-contracts'
    external=c.clone(AdmissionTests.external,c=c)(obj,r,x,m,ci)
    return r,x,m,ci,external


class ReviewTests(unittest.TestCase):
    def test_package_style_admission_invocation(self):
        import os
        env=dict(os.environ);env.pop('PYTHONPATH',None)
        p=subprocess.run([sys.executable,'-S','-B','-m','unittest',
            'tests.test_preprocess_protocol.ProtocolTests.test_fresh_admission_binds_all_seven_source_jobs_and_cohort'],
            cwd=host.ROOT,env=env,capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stderr)

    @unittest.skipUnless(sys.platform=='linux','original handoff Linux-only')
    def test_actual_host_directory_contract_reaches_owned_handoff(self):
        from scripts import run_recorded_worker_canary as old
        with tempfile.TemporaryDirectory() as tmp:
            native=host.trial_directory(Path(tmp),0);native.mkdir(parents=True)
            with patch.object(old.subprocess,'run',return_value=subprocess.CompletedProcess([],0)):
                result=old.handoff_evidence(native,dict(owned_container_removed=True,ownership_unresolved=False))
            self.assertEqual(result['status'],'EVIDENCE_HANDED_TO_RUNNER')

    def test_valid_container_pid_one(self):
        from tests.test_preprocess_protocol import ProtocolTests
        # Reuse the minimal receipt fixture captured through the validator call.
        seen=[]
        original=c.validate_trial_receipt
        with patch.object(c,'validate_trial_receipt',side_effect=lambda r:seen.append(copy.deepcopy(r))):
            with self.assertRaises(AssertionError):ProtocolTests().test_real_session_and_completion_are_mandatory()
        r=seen[0];r['parent_pid']=1
        original(r)
        identity={k:r[k] for k in ('seed','scenario','variant','source','activation','approval','run_id','dependencies_sha256') if k in r}
        launch=dict(identity,parent_pid=1,nonce=r['nonce'])
        native=dict(pid=r['pid'])
        completion=dict(identity,parent_pid=1,nonce=r['nonce'])
        c.bind_owner(r,launch,native,completion)
        with self.assertRaises(ValueError):c.bind_owner(r,dict(launch,parent_pid=2),native,completion)

    def test_pair_eligibility_requires_initial_state_and_fresh_process_namespaces(self):
        a=dict(seed=20261109,scenario='s_curve_left_right',variant='rgb_linear',nonce='a'*32,
            container_hostname='a'*12,intrinsics={'road':'fixed','wide':'fixed'},initial_recurrent_sha256='e'*64,
            input_rows=[dict(source_sha256={'road':'r','wide':'w'},canvas_sha256=['r','w'],
                baseline_tensor_sha256='b',initial_recurrent_sha256='e'*64)],
            trajectory=dict(process_uuid='a'*32,initial_state={'t':0},geometry=['fixed']))
        b=copy.deepcopy(a);b.update(variant='source_yuv_nearest_even',nonce='b'*32,container_hostname='b'*12)
        b['trajectory']['process_uuid']='b'*32
        self.assertTrue(c.pair_eligibility(a,b)['eligible'])
        for mutate in (lambda v:v.update(initial_recurrent_sha256='f'*64),
                       lambda v:v['input_rows'][0]['source_sha256'].update(road='changed'),
                       lambda v:v.update(nonce=a['nonce'])):
            bad=copy.deepcopy(b);mutate(bad)
            self.assertFalse(c.pair_eligibility(a,bad)['eligible'])

    def test_partial_activity_keeps_known_calls_and_primary_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            identity=dict(seed=20261109,scenario='s_curve_left_right',variant='rgb_linear',
                source='b'*40,activation='c'*40,approval='d'*40,run_id='123')
            for name,obj in {'launch.json':dict(identity,parent_pid=1,nonce='a'*32),
                'native-child.json':dict(pid=10),
                'report.json':dict(identity,protocol=c.TRIAL_PROTOCOL,pid=10,parent_pid=1,nonce='a'*32,
                    model_process_bounds=[1,1],inference_bounds=[60,60],failure='native primary',secondary_errors=[])}.items():
                (p/name).write_text(json.dumps(obj))
            got=c.partial_activity(p,identity,dict(start_attempted=True))
            self.assertEqual(got['inference_bounds'],[60,60]);self.assertEqual(got['primary_error'],'native primary')
            self.assertEqual(c.partial_activity(p,identity,dict(start_attempted=True,ownership_unresolved=True))['inference_bounds'],[60,600])
            q=json.loads((p/'report.json').read_text());q.update(inference_bounds=[5,6],failure='inflight')
            (p/'report.json').write_text(json.dumps(q))
            self.assertEqual(c.partial_activity(p,identity,dict(start_attempted=True))['inference_bounds'],[5,6])
            q['trajectory']={'error':'raw original failure'}
            (p/'report.json').write_text(json.dumps(q))
            self.assertEqual(c.partial_activity(p,identity,dict(start_attempted=True))['primary_error'],'raw original failure')
            q.pop('trajectory')
            q.update(model_process_bounds=[0,1],inference_bounds=[0,0],failure='constructor')
            (p/'report.json').write_text(json.dumps(q))
            self.assertEqual(c.partial_activity(p,identity,dict(start_attempted=True))['model_process_bounds'],[0,1])
            (p/'report.json').unlink()
            self.assertEqual(c.partial_activity(p,identity,dict(start_attempted=True,ownership_unresolved=True))['inference_bounds'],[0,600])

    def test_auxiliary_job_names_and_per_arm_resources(self):
        r,x,m,ci,external=metadata()
        host.validate_admission(r,x,manifest=m,ci=ci,**external)
        for role in ('windows_push','windows_pr','software_api_pr'):
            bad=copy.deepcopy(ci);bad[role]['jobs']['jobs'][0]['name']='unrelated-job'
            with self.assertRaises(ValueError):host.validate_admission(r,x,manifest=m,ci=bad,**external)
        good=dict(memory_available_bytes=12*1024**3,disk_free_bytes=1024**3)
        c.resource_gate(good)
        for changes in ({'memory_available_bytes':12*1024**3-1},{'disk_free_bytes':1024**3-1}):
            with self.assertRaises(ValueError):c.resource_gate(dict(good,**changes))

    def test_real_bound_step_feeds_literal_tensor_and_keeps_recurrence(self):
        import numpy as np
        from tests.test_onnx_runtime_policy import TinySession,make_manifest
        from bigbench.preprocess_experiment import policy_class
        from bigbench.onnx_policy import OnnxBigModelPolicy
        from bigbench.policies import ModelObservation
        from bigbench.camera import RGBFrame
        from types import MethodType
        from bigbench.preprocess_experiment import scoped_step
        expected=np.full((2,6,128,256),73,np.uint8)
        class FixtureInput:
            rows=[]
            def prepare(self,road,wide):
                import hashlib
                self.rows.append(dict(actual_tensor_sha256=hashlib.sha256(expected.tobytes()).hexdigest()))
                return expected.copy()
        with tempfile.TemporaryDirectory() as tmp:
            model,spec,manifest=make_manifest(Path(tmp));session=TinySession(manifest)
            klass=policy_class();p=klass.__new__(klass);p.preparer=FixtureInput()
            OnnxBigModelPolicy.__init__(p,model,spec,session=session)
            p.original_step_with_explicit_input=MethodType(scoped_step(lambda a,b:p.preparer.prepare(a,b)),p)
            frame=RGBFrame(512,256,bytes(512*256*3))
            for _ in (0,1):p.step(ModelObservation(frame,8.,0.,wide_frame=frame))
            np.testing.assert_array_equal(session.feeds[0]['new_img'],expected)
            np.testing.assert_array_equal(session.feeds[1]['new_img'],expected)
            self.assertEqual(float(session.feeds[0]['state_feat_q'].flat[0]),0.)
            self.assertEqual(float(session.feeds[1]['state_feat_q'].flat[0]),1.)
            self.assertIn('initial_recurrent_sha256',p.preparer.rows[0])

    def test_offline_verifier_replays_order_and_bindings(self):
        r,x,m,ci,external=metadata()
        auth=host.validate_admission(r,x,manifest=m,ci=ci,**external)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'authentication.json').write_text(json.dumps(auth))
            ledger=[]
            for index,trial in enumerate(c.TRIALS):
                ledger.append(dict(index=index,trial=list(trial),status='COMPLETE_DIAGNOSTIC',model_process_bounds=[1,1],inference_bounds=[1,1]))
                (p/f'authentication-trial-{index}.json').write_text(json.dumps(auth))
                (p/f'resources-trial-{index}.json').write_text(json.dumps(dict(memory_available_bytes=12*1024**3,disk_free_bytes=1024**3)))
                (p/f'public-activity-trial-{index}.json').write_text(json.dumps(dict(pages=[dict(total_count=1,workflow_runs=[dict(id=987,workflow_id=98765,status='in_progress')])])))
            (p/'trial-ledger.json').write_text(json.dumps(ledger))
            (p/'summary.json').write_text(json.dumps(dict(status='EIGHT_EXPERIMENTAL_TRIALS_RETURNED',official_model_process_bounds=[8,8],official_inference_bounds=[8,8])))
            (p/'pairing.json').write_text('[]')
            with patch.object(host,'source_manifest',return_value=m),patch.object(c,'verify_native',return_value=dict(steps=1)),patch.object(c,'pairing_verdicts',return_value=[]):
                self.assertEqual(c.verify_bundle(p)['status'],'EIGHT_EXPERIMENTAL_TRIALS_RETURNED')
                bad=copy.deepcopy(ledger);bad[0]['trial']=list(c.TRIALS[1]);(p/'trial-ledger.json').write_text(json.dumps(bad))
                with self.assertRaises(ValueError):c.verify_bundle(p)
                (p/'trial-ledger.json').write_text(json.dumps(ledger))
                changed=copy.deepcopy(auth);changed['context']['env_head']='f'*40
                (p/'authentication-trial-0.json').write_text(json.dumps(changed))
                with self.assertRaises(ValueError):c.verify_bundle(p)
                (p/'authentication-trial-0.json').write_text(json.dumps(auth))
                (p/'trial-ledger.json').write_text(json.dumps(ledger[:1]))
                self.assertEqual(c.verify_bundle(p)['status'],'INCOMPLETE_OR_FAILED')

    def test_local_real_track_commands_keep_installed_packages_visible(self):
        text=(host.ROOT/'docs/remaining-validation-handoff.md').read_text(encoding='utf-8')
        for line in text.splitlines():
            if line.startswith('& $py') and '--mode process-check' not in line:
                self.assertNotIn(' -S ',line)

    def test_handoff_reader_with_windows_default_encoding(self):
        original=Path.read_text
        def windows_default(path,*args,**kwargs):
            kwargs.setdefault('encoding','cp1252')
            return original(path,*args,**kwargs)
        with patch.object(Path,'read_text',windows_default):
            self.test_local_real_track_commands_keep_installed_packages_visible()


if __name__=='__main__':unittest.main()
