"""CPU fixture metadata only; no real session/renderer/model evidence."""
import copy
import hashlib
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from bigbench import full_s_recorded_receiver as receiver
except ImportError:
    receiver=None
from bigbench import full_s_recorded_worker as worker
from bigbench.full_s_failure_capture import verify_recording

ROOT=Path(__file__).resolve().parents[1]


def trial_fixture(out,kind='complete',*,metadata_real=True):
    from tests.test_full_s_recorded_worker import RecordedTrialBodyTests
    case=RecordedTrialBodyTests();case.setUp()
    def execute():
        try:case.execute(out,fail_on=2 if kind in ('graph','both') else None,
            close_error=kind in ('close','both'),constructor_error=kind=='constructor')
        except worker.TrialFailure:pass
    if kind=='audited-no-frame':
        with patch('bigbench.full_s_validation.route_state',side_effect=ValueError('unit route failure after audit')):execute()
    elif kind=='write':
        with patch('bigbench.full_s_failure_capture._write_blob',side_effect=OSError('unit blob write failure')):execute()
    elif kind=='snapshot':
        from bigbench import full_s_failure_capture as capture
        original=capture._states;calls=[]
        def fail_once(*args,**kwargs):
            calls.append(1)
            if len(calls)==2:raise ValueError('unit post snapshot failure')
            return original(*args,**kwargs)
        with patch.object(capture,'_states',side_effect=fail_once):execute()
    elif kind=='final-lifecycle':
        original=worker._write_receipt
        def fail_final(path,value,**kwargs):
            if path.name=='recorded-trial-lifecycle.json' and value.get('status')=='RECORDED':raise OSError('unit final lifecycle write failed')
            return original(path,value,**kwargs)
        with patch.object(worker,'_write_receipt',side_effect=fail_final):execute()
    elif kind=='source-unavailable':
        with patch.object(worker,'_source_snapshot',side_effect=OSError('unit source fingerprint unavailable')):execute()
    elif kind=='runtime-unavailable':
        with patch.object(worker,'_runtime_context',side_effect=OSError('unit runtime receipt unavailable')):execute()
    elif kind=='abort':
        with patch('tests.test_full_s_failure_capture.GraphBoundary.run',side_effect=OSError('unit graph I/O abort')):execute()
    else:execute()
    if not metadata_real:return
    tp=out/'recorded-trial.json';t=json.loads(tp.read_text())
    if t['model_test_double'] is not None:
        t.update(model_test_double=False,injected_session=False)
        if t['onnxruntime'] is not None:t['onnxruntime']=dict(version='1.20.1',real_session=True,providers=['CPUExecutionProvider'],
            session_class='onnxruntime.capi.onnxruntime_inference_collection.InferenceSession')
    rp=out/'recording/report.json';mp=out/'recording/manifest.json'
    if rp.exists():
        r=json.loads(rp.read_text());old_size=rp.stat().st_size
        r.update(model_test_double=False,injected_session=False)
        for lane in r['geometry']:
            lane['lane_class']='metadrive.component.lane.'+('circular_lane.CircularLane' if lane['shape']['kind']=='circular' else 'straight_lane.StraightLane')
        raw=(json.dumps(r,indent=2)+'\n').encode();rp.write_bytes(raw)
        if mp.exists():
            m=json.loads(mp.read_text());m['report_sha256']=hashlib.sha256(raw).hexdigest();m['payload_and_report_bytes']+=len(raw)-old_size;mp.write_text(json.dumps(m))
            t.update(recording_verification=verify_recording(out/'recording'),recording_binding=dict(
                manifest_sha256=hashlib.sha256(mp.read_bytes()).hexdigest(),report_sha256=hashlib.sha256(raw).hexdigest(),
                process_uuid=r['process_uuid']))
    tp.write_text(json.dumps(t))


@unittest.skipUnless(sys.platform=='linux','frozen native-body orchestration fixtures are Linux-only')
class OfficialReceiptTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(receiver,'complete/partial recorded receiver missing')

    def test_complete_recording_is_only_local_structure_never_native_or_quality_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'trial';trial_fixture(root)
            value=receiver.inspect_trial(root)
            self.assertEqual(value['status'],'COMPLETE_DIAGNOSTIC')
            self.assertTrue(value['recording_structure_valid'])
            self.assertIs(value['producer_reported_body_success'],True)
            self.assertEqual(value['reported_inference_bounds'],value['verified_recording_inference_bounds'])
            self.assertFalse(value['origin_authenticated']);self.assertFalse(value['model_camera_qualified'])
            self.assertFalse(value['all_four_validation_tracks_passed']);self.assertFalse(value['native_execution_authenticated'])
            self.assertEqual(value['new_inferences'],0)

    def test_graph_pending_audited_no_frame_and_cleanup_failures_keep_distinct_milestones(self):
        for kind,bounds,closed in (('graph',[1,2],True),('audited-no-frame',[1,1],True),('both',[1,2],False),('close',None,False)):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                root=Path(temp)/'trial';trial_fixture(root,kind)
                value=receiver.inspect_trial(root)
                self.assertEqual(value['status'],'PARTIAL_DIAGNOSTIC')
                self.assertTrue(value['recording_structure_valid'])
                self.assertIs(value['producer_reported_body_success'],False)
                if bounds is not None:self.assertEqual(value['verified_recording_inference_bounds'],bounds)
                self.assertIs(value['provider_closed'],closed)
                if kind=='audited-no-frame':
                    self.assertEqual(value['completed_frames'],0)
                    self.assertEqual(value['verified_recording_inference_bounds'],[1,1])
                if kind=='both':
                    self.assertIn('graph failure',value['primary_error'])
                    self.assertTrue(any('provider close failure' in e for e in value['secondary_errors']))

    def test_constructor_failure_and_missing_final_receipts_never_invent_verified_calls(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'trial';trial_fixture(root,'constructor')
            value=receiver.inspect_trial(root)
            self.assertEqual(value['status'],'INCOMPLETE_EVIDENCE')
            self.assertEqual(value['reported_inference_bounds'],[0,0])
            self.assertIsNone(value['verified_recording_inference_bounds'])
            self.assertFalse(value['recording_structure_valid'])
            (root/'recorded-trial.json').unlink()
            value=receiver.inspect_trial(root)
            self.assertEqual(value['reported_inference_bounds'],[0,0])
            self.assertIn('recorded-trial.json',value['unavailable_evidence'])
            life=root/'recorded-trial-lifecycle.json';data=json.loads(life.read_text());data['inference_bounds']=[1,2];life.write_text(json.dumps(data))
            with self.assertRaises(ValueError):receiver.inspect_trial(root)
            data.update(status='INFERENCE_PENDING',policy_constructor_entered=True,policy_created=True,provider_created=True,
                provider_received=True,provider_close_attempted=False,body_provider_close_attempted=False,provider_closed=False,completed_rows=1)
            data.pop('primary_error');data.pop('secondary_errors');life.write_text(json.dumps(data))
            value=receiver.inspect_trial(root)
            self.assertEqual(value['reported_inference_bounds'],[1,2])
            self.assertIsNone(value['verified_recording_inference_bounds'])

    def test_failed_session_construction_can_report_loaded_runtime_without_inventing_session(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'trial';trial_fixture(root,'constructor')
            path=root/'recorded-trial.json';data=json.loads(path.read_text())
            data['onnxruntime']['version']='1.20.1';path.write_text(json.dumps(data))
            result=receiver.inspect_trial(root)
            self.assertEqual(result['status'],'INCOMPLETE_EVIDENCE')
            self.assertEqual(result['reported_inference_bounds'],[0,0])
            self.assertIsNone(result['verified_recording_inference_bounds'])

    def test_storage_and_snapshot_errors_keep_available_partial_or_unverified_evidence(self):
        for kind in ('write','snapshot'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                root=Path(temp)/'trial';trial_fixture(root,kind)
                result=receiver.inspect_trial(root)
                self.assertIs(result['producer_reported_body_success'],False)
                self.assertIsNotNone(result['primary_error'])
                self.assertFalse(result['origin_authenticated'])
                if kind=='write':
                    self.assertEqual(result['status'],'INCOMPLETE_EVIDENCE')
                    self.assertIsNone(result['verified_recording_inference_bounds'])
                else:
                    self.assertEqual(result['status'],'PARTIAL_DIAGNOSTIC')
                    self.assertEqual(result['verified_recording_inference_bounds'],result['reported_inference_bounds'])

    def test_fixture_session_nonce_pid_bounds_cleanup_and_source_contradictions_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'trial';trial_fixture(root,'graph')
            changes=(('recorded-trial.json',{'nonce':'b'*32}),('recorded-trial.json',{'pid':123}),
                ('recorded-trial.json',{'actual_inference_bounds':[0,0]}),('recorded-trial.json',{'model_test_double':True}),
                ('recorded-trial.json',{'injected_session':True}),('recorded-trial.json',{'provider_closed':False}),
                ('recorded-trial.json',{'source_context':{}}),('recorded-trial.json',{'recording_binding':{}}),
                ('recorded-trial-lifecycle.json',{'status':'RECORDED'}),
                ('recorded-trial.json',{'onnxruntime':dict(version='1.20.1',real_session=True,providers=['CPUExecutionProvider'],session_class='tests.FakeSession')}))
            for name,update in changes:
                path=root/name;raw=path.read_bytes();data=json.loads(raw);data.update(update);path.write_text(json.dumps(data))
                with self.subTest(name=name,update=update),self.assertRaises(ValueError):receiver.inspect_trial(root)
                path.write_bytes(raw)

    def test_real_camera_canary_and_raw_fixture_flags_cannot_be_official_receipts(self):
        from tests.test_recorded_worker_canary import CanaryTests
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'fixture';trial_fixture(root,metadata_real=False)
            with self.assertRaises(ValueError):receiver.inspect_trial(root)
            canary=Path(temp)/'canary';f=CanaryTests();f.setUp();f.fixture(canary)
            with self.assertRaises(ValueError):receiver.inspect_trial(canary)

    def test_recording_swap_or_corrupt_snapshot_cannot_borrow_the_worker_receipt(self):
        import shutil
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a=root/'a';b=root/'b';trial_fixture(a,'graph');trial_fixture(b,'graph')
            shutil.rmtree(a/'recording');shutil.copytree(b/'recording',a/'recording')
            with self.assertRaises(ValueError):receiver.inspect_trial(a)


class PortableReceiverCLI(unittest.TestCase):
    def test_cold_plan_help_have_zero_optional_imports_and_no_execution_mode(self):
        script=ROOT/'scripts/full_s_recorded_receiver.py'
        for args in (['--help'],['plan']):
            result=subprocess.run([sys.executable,'-I','-S','-B',str(script),*args],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            if args==['plan']:
                data=json.loads(result.stdout);self.assertEqual(data['heavy_modules_loaded'],[])
                self.assertEqual(data['new_inferences'],0);self.assertFalse(data['model_execution_command_available'])
        result=subprocess.run([sys.executable,'-I','-S','-B',str(script),'run'],capture_output=True,text=True,timeout=20)
        self.assertNotEqual(result.returncode,0)

    @unittest.skipUnless(sys.platform=='linux','recorded native-body fixture is Linux-only')
    def test_nested_output_and_symlink_ancestor_leave_evidence_unmodified(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);trial=root/'trial';trial_fixture(trial,'graph')
            before={p.relative_to(trial).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in trial.rglob('*') if p.is_file()}
            output=trial/'inside'
            result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/full_s_recorded_receiver.py'),
                'verify','--trial-dir',str(trial),'--out',str(output)],capture_output=True,text=True,timeout=20)
            self.assertNotEqual(result.returncode,0);self.assertFalse(output.exists())
            self.assertEqual(before,{p.relative_to(trial).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in trial.rglob('*') if p.is_file()})
            alias=trial/'..'/'trial'
            result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/full_s_recorded_receiver.py'),
                'verify','--trial-dir',str(alias),'--out',str(output)],capture_output=True,text=True,timeout=20)
            self.assertNotEqual(result.returncode,0);self.assertFalse(output.exists())
            link=root/'link';link.symlink_to(trial,target_is_directory=True)
            result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/full_s_recorded_receiver.py'),
                'verify','--trial-dir',str(trial),'--out',str(link/'fresh')],capture_output=True,text=True,timeout=20)
            self.assertNotEqual(result.returncode,0);self.assertFalse((trial/'fresh').exists())


@unittest.skipUnless(sys.platform=='linux','frozen body fixtures are Linux-only')
class ReceiverReviewRegressions(unittest.TestCase):
    def test_nonfinal_lifecycle_and_missing_source_or_runtime_preserve_known_later_evidence(self):
        for kind in ('final-lifecycle','source-unavailable','runtime-unavailable'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                root=Path(temp)/'trial';trial_fixture(root,kind)
                value=receiver.inspect_trial(root)
                self.assertEqual(value['status'],'INCOMPLETE_EVIDENCE')
                self.assertTrue(value['recording_structure_valid'])
                self.assertIsNotNone(value['verified_recording_inference_bounds'])
                self.assertIsNotNone(value['primary_error'])
                self.assertFalse(value['native_execution_authenticated'])

    def test_missing_trial_does_not_make_impossible_constructor_counts_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'trial';trial_fixture(root,'constructor');(root/'recorded-trial.json').unlink()
            path=root/'recorded-trial-lifecycle.json';life=json.loads(path.read_text());life['inference_bounds']=[1,2];path.write_text(json.dumps(life))
            with self.assertRaises(ValueError):receiver.inspect_trial(root)

    def test_missing_manifest_still_validates_the_available_original_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'trial';trial_fixture(root,'write')
            path=root/'recording/report.json';r=json.loads(path.read_text());r['process_id']=999999;path.write_text(json.dumps(r))
            with self.assertRaises(ValueError):receiver.inspect_trial(root)

    def test_abort_metadata_is_preserved_and_any_conflicting_bounds_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'trial';trial_fixture(root,'abort')
            value=receiver.inspect_trial(root)
            self.assertTrue(value['abort_metadata_available'])
            self.assertEqual(value['reported_inference_bounds'],[0,1])
            self.assertEqual(value['abort_reported_completed_rows'],0)
            self.assertIsNone(value['verified_recording_inference_bounds'])
            path=root/'recording/abort.json';r=json.loads(path.read_text());r['actual_inference_bounds']=[0,0];path.write_text(json.dumps(r))
            with self.assertRaises(ValueError):receiver.inspect_trial(root)

    def rebind(self,root,mutate):
        rp=root/'recording/report.json';mp=root/'recording/manifest.json';tp=root/'recorded-trial.json'
        r=json.loads(rp.read_text());m=json.loads(mp.read_text());t=json.loads(tp.read_text());size=rp.stat().st_size
        mutate(r);raw=(json.dumps(r,indent=2)+'\n').encode();rp.write_bytes(raw)
        m['report_sha256']=hashlib.sha256(raw).hexdigest();m['payload_and_report_bytes']+=len(raw)-size;mp.write_text(json.dumps(m))
        t.update(recording_verification=verify_recording(root/'recording'),recording_binding=dict(
            manifest_sha256=hashlib.sha256(mp.read_bytes()).hexdigest(),report_sha256=hashlib.sha256(raw).hexdigest(),process_uuid=r['process_uuid']))
        tp.write_text(json.dumps(t))

    def test_uuid_and_committed_progress_are_typed_and_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'trial';trial_fixture(root)
            self.rebind(root,lambda r:r.update(process_uuid=None))
            with self.assertRaises(ValueError):receiver.inspect_trial(root)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'trial';trial_fixture(root,'graph')
            path=root/'recorded-trial-lifecycle.json';life=json.loads(path.read_text());life['completed_rows']+=1;path.write_text(json.dumps(life))
            with self.assertRaises(ValueError):receiver.inspect_trial(root)

    def test_verified_source_requires_a_reported_observer_request_and_returns_milestones(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'trial';trial_fixture(root,'graph')
            value=receiver.inspect_trial(root)
            self.assertTrue(value['raw_rgb_observer_requested']);self.assertTrue(value['raw_rgb_source_evidence_present'])
            path=root/'recorded-trial.json';t=json.loads(path.read_text());t['raw_rgb_observer_requested']=False;path.write_text(json.dumps(t))
            with self.assertRaises(ValueError):receiver.inspect_trial(root)

    def test_structural_receipt_never_emits_an_actual_execution_success_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'trial';trial_fixture(root)
            value=receiver.inspect_trial(root)
            self.assertNotIn('body_execution_succeeded',value)
            self.assertIs(value['producer_reported_body_success'],True)
            (root/'recorded-trial.json').unlink()
            path=root/'recorded-trial-lifecycle.json';life=json.loads(path.read_text())
            life.update(status='TRIAL_RECORDED',provider_closed=False,provider_close_attempted=False,body_provider_close_attempted=False)
            life.pop('primary_error');life.pop('secondary_errors');path.write_text(json.dumps(life))
            value=receiver.inspect_trial(root)
            self.assertIsNone(value['producer_reported_body_success'])

    def test_long_original_error_uses_the_frozen_producers_bounded_serialization(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'trial';trial_fixture(root,'graph')
            self.rebind(root,lambda r:r.update(error='RuntimeError: '+'x'*5000))
            original=json.loads((root/'recording/report.json').read_text())['error']
            for name in ('recorded-trial.json','recorded-trial-lifecycle.json'):
                path=root/name;data=json.loads(path.read_text());data['primary_error']=worker._error(RuntimeError(original));path.write_text(json.dumps(data))
            result=receiver.inspect_trial(root)
            self.assertEqual(result['status'],'PARTIAL_DIAGNOSTIC')


if __name__=='__main__':unittest.main()
