"""Portable owned entry and Linux orchestration fixtures; never native evidence."""
import errno
import builtins
import json
import os
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest
import venv
from unittest.mock import patch

try:
    from bigbench import full_s_recorded_worker as worker
except ImportError:
    worker = None

ROOT = Path(__file__).resolve().parents[1]


class PortableRecordedWorkerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(worker, 'recorded worker connection missing')

    def test_cold_preflight_and_actual_owned_entry_never_load_native_dependencies(self):
        with tempfile.TemporaryDirectory() as temp:
            for mode in ('preflight', 'process-check'):
                out = Path(temp)/mode
                result = subprocess.run([sys.executable, '-I', '-S', '-B', str(ROOT/'scripts/full_s_recorded_worker.py'),
                    mode, '--out', str(out)], capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads((out/(mode+'.json')).read_text())
                self.assertFalse(data['execution_activated'])
                self.assertEqual(data['official_model_processes'], 0)
                self.assertEqual(data['inferences'], 0)
                self.assertFalse(data['all_four_validation_tracks_passed'])
                if mode == 'preflight':
                    self.assertEqual(data['private_task_state'], 'NOT_OBSERVED')
                else:
                    self.assertEqual(data['status'], 'PROCESS_CHECK_PASS')
                    owner = json.loads((out/'owner.json').read_text())
                    child = data['worker']
                    self.assertEqual(child['process_id'], owner['pid'])
                    self.assertEqual(child['parent_process_id'], owner['parent_pid'])
                    self.assertTrue(owner['child_reaped'])
                    self.assertFalse(child['native_modules_loaded'])

    def test_empty_venv_preserves_actual_child_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            env = root/'venv'
            venv.EnvBuilder(with_pip=False, symlinks=False).create(env)
            exe = env/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            out = root/'check'
            result = subprocess.run([str(exe), '-I', '-S', '-B', str(ROOT/'scripts/full_s_recorded_worker.py'),
                'process-check', '--out', str(out)], capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((out/'process-check.json').read_text())
            self.assertEqual(Path(data['worker']['prefix']).resolve(), env.resolve())
            self.assertTrue(data['worker']['site_hooks_disabled'])

    def test_interrupted_spawn_remains_unknown_and_missing_interpreter_is_known_failure(self):
        for exc, state in ((InterruptedError(errno.EINTR, 'interrupted handle'), None),
                           (FileNotFoundError(errno.ENOENT, 'missing executable'), False)):
            with tempfile.TemporaryDirectory() as temp:
                out = Path(temp)/'check'
                with patch.object(worker.subprocess, 'Popen', side_effect=exc):
                    with self.assertRaises(Exception):
                        worker.process_check(out)
                owner = json.loads((out/'owner.json').read_text())
                self.assertIs(owner['spawn_succeeded'], state)
                self.assertEqual(owner['child_reaped'], state is False)

    def test_wrong_owner_mode_is_rejected_before_optional_imports(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            data = dict(parent_pid=os.getppid(), nonce='a'*32, seed=20261109,
                scenario='s_curve_left_right', pid=os.getpid(), spawn_succeeded=True,
                returncode=None, child_reaped=False, mode='NATIVE_EXECUTION')
            (out/'owner.json').write_text(json.dumps(data))
            args = SimpleNamespace(out=out, parent=os.getppid(), nonce='a'*32, seed=20261109, scene='s_curve_left_right')
            with self.assertRaises(ValueError):
                worker.worker_check(args)
            self.assertFalse((out/'worker.json').exists())

    def test_existing_output_and_symlink_ancestors_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root/'existing'
            out.mkdir()
            (out/'keep').write_text('keep')
            with self.assertRaises((ValueError, FileExistsError)):
                worker.process_check(out)
            self.assertEqual((out/'keep').read_text(), 'keep')
            if os.name != 'nt':
                link = root/'link'
                link.symlink_to(root, target_is_directory=True)
                with self.assertRaises(ValueError):
                    worker.process_check(link/'new')
                self.assertFalse((root/'new').exists())

    def test_owner_persistence_failure_never_publishes_pass(self):
        original = worker._write_receipt
        def fail_final(path, value, **kwargs):
            if Path(path).name == 'owner.json' and value.get('child_reaped') is True:
                raise OSError('owner final persistence failed')
            return original(path, value, **kwargs)
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'check'
            with patch.object(worker, '_write_receipt', side_effect=fail_final):
                with self.assertRaises(Exception):
                    worker.process_check(out)
            self.assertFalse((out/'process-check.json').exists())

    def test_owner_finalization_does_not_mask_interrupted_spawn(self):
        original = worker._write_receipt
        def fail_final(path, value, **kwargs):
            if Path(path).name == 'owner.json' and kwargs.get('replace'):
                raise OSError('owner final persistence failed')
            return original(path, value, **kwargs)
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'check'
            caught = None
            with patch.object(worker, '_write_receipt', side_effect=fail_final), \
                 patch.object(worker.subprocess, 'Popen', side_effect=InterruptedError(errno.EINTR,'first spawn interruption')):
                try: worker.process_check(out)
                except Exception as exc: caught = exc
            self.assertIsInstance(caught, InterruptedError)
            self.assertTrue(any('owner final persistence failed' in v for v in caught.secondary_errors))
            self.assertIsNone(caught.owner['spawn_succeeded'])

    def test_receipt_size_is_checked_before_opening_in_both_directions(self):
        original = Path.open
        def forbid_large_read(path, mode='r', *args, **kwargs):
            if path.name in ('owner.json','worker.json') and 'r' in mode and path.stat().st_size > 65536:
                raise AssertionError('oversized receipt opened before rejection')
            return original(path, mode, *args, **kwargs)
        class Child:
            pid=23456; returncode=0
            def wait(self, timeout): return 0
            def poll(self): return 0
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'parent'
            def launch(*args, **kwargs):
                (out/'worker.json').write_bytes(b' '*70000)
                return Child()
            with patch.object(worker.subprocess,'Popen',side_effect=launch), patch.object(Path,'open',new=forbid_large_read):
                caught=None
                try: worker.process_check(out)
                except Exception as exc: caught=exc
                self.assertIsInstance(caught,ValueError)
            child=root/'child';child.mkdir();(child/'owner.json').write_bytes(b' '*70000)
            args=SimpleNamespace(out=child,parent=os.getppid(),nonce='a'*32,seed=20261109,scene='s_curve_left_right')
            with patch.object(Path,'open',new=forbid_large_read):
                caught=None
                try: worker.worker_check(args)
                except Exception as exc: caught=exc
                self.assertIsInstance(caught,ValueError)


@unittest.skipUnless(sys.platform == 'linux', 'recorded SDK3 trial body is Linux-only')
class RecordedTrialBodyTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(worker, 'recorded worker connection missing')
        from tests.test_full_s_failure_capture import inner_policy, SourceCamera, INTRINSICS, route
        self.inner_policy, self.source_camera, self.intrinsics, self.route = inner_policy, SourceCamera, INTRINSICS, route

    def execute(self, out, fail_on=None, close_error=False, constructor_error=False):
        from scripts import sdk3_four_validation_trial as original
        from scripts import native_mdv3_repeat_trial as model
        from bigbench import native_model_campaign as campaign
        p = self.inner_policy(fail_on)
        fixture = self
        class Lens:
            def __init__(self, role): self.i = fixture.intrinsics[role]
            def getFilmSize(self): return 964/self.i.fx, 604/self.i.fy
            def getFilmOffset(self): return 0., 0.
            def getFocalLength(self): return 1.
        class Provider:
            calls = 0
            def __init__(self):
                sensors = {('bigbench_'+role): SimpleNamespace(get_lens=lambda role=role: Lens(role)) for role in ('road', 'wide')}
                self.env = SimpleNamespace(engine=SimpleNamespace(sensors=sensors))
            def close(self):
                self.calls += 1
                if close_error: raise RuntimeError('provider close failure')
                self.env = None
        provider = Provider()
        class Camera(self.source_camera):
            def __init__(self, value): super().__init__(); self.provider = value
        args = SimpleNamespace(out=out, nonce='a'*32, seed=20261109, scenario='s_curve_left_right')
        stats = dict(returned=0, guards_ok=True, values={k:0 for k in ('configured','closed','error','forwarded','resolutions','paths','events')})
        with patch.object(model, 'AuditedOfficialOnnx', side_effect=ValueError('constructor failure') if constructor_error else lambda *a, **kw:p), \
             patch.object(original, '_world', return_value=(provider, self.route(), {'fixture_only':True})), \
             patch.object(original, 'driver_info', return_value={'renderer':'CPU_UNIT_FIXTURE_ONLY'}), \
             patch.object(campaign, 'NativeWorldCamera', Camera), \
             patch('scripts.sdk3_priority_model_native.source_stats_after', return_value=stats):
            try:
                result = worker.run_recorded_trial(args)
                return result, p, provider
            except Exception as exc:
                exc.fixture_provider = provider
                raise

    def test_original_loop_is_connected_and_provider_closed_once(self):
        from bigbench.full_s_failure_capture import verify_recording
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'trial'
            result, parent, provider = self.execute(out)
            self.assertEqual(provider.calls, 1)
            self.assertTrue(result['provider_closed'])
            self.assertTrue(result['raw_rgb_observer_used'])
            self.assertTrue(result['model_test_double'])
            self.assertIsInstance(result.get('onnxruntime'), dict)
            self.assertIs(result['onnxruntime']['real_session'], False)
            self.assertEqual(result['max_steps'], 600)
            self.assertEqual(result['actual_inference_bounds'], [parent.session.calls]*2)
            self.assertFalse(result['all_four_validation_tracks_passed'])
            self.assertFalse(result['origin_authenticated'])
            self.assertTrue(verify_recording(out/'recording')['recording_structure_valid'])

    def test_partial_graph_failure_retains_original_bounds_and_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'trial'
            with self.assertRaises(worker.TrialFailure) as caught:
                self.execute(out, fail_on=2)
            self.assertEqual(caught.exception.inference_bounds, [1, 2])
            self.assertEqual(caught.exception.fixture_provider.calls, 1)
            saved = json.loads((out/'recording/report.json').read_text())
            self.assertEqual(caught.exception.report, saved)
            receipt = json.loads((out/'recorded-trial.json').read_text())
            self.assertIn('graph failure', receipt['primary_error'])
            self.assertTrue(receipt['provider_closed'])

    def test_constructor_failure_has_zero_inferences_and_no_world_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'trial'
            with self.assertRaises(worker.TrialFailure) as caught:
                self.execute(out, constructor_error=True)
            self.assertEqual(caught.exception.inference_bounds, [0, 0])
            self.assertEqual(caught.exception.fixture_provider.calls, 0)
            self.assertIsNone(caught.exception.report)
            self.assertIs(json.loads((out/'recorded-trial.json').read_text())['raw_rgb_observer_used'], False)

    def test_close_failure_does_not_mask_primary_inference_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'trial'
            with self.assertRaises(worker.TrialFailure) as caught:
                self.execute(out, fail_on=2, close_error=True)
            self.assertIn('graph failure', caught.exception.primary_error)
            self.assertTrue(any('provider close failure' in v for v in caught.exception.secondary_errors))
            self.assertEqual(caught.exception.inference_bounds, [1, 2])
            self.assertEqual(caught.exception.fixture_provider.calls, 1)

    def test_close_only_failure_keeps_completed_original_report(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'trial'
            with self.assertRaises(worker.TrialFailure) as caught:
                self.execute(out, close_error=True)
            self.assertIsNotNone(caught.exception.report)
            self.assertEqual(caught.exception.inference_bounds[0], caught.exception.report['completed_steps'])
            self.assertEqual(caught.exception.fixture_provider.calls, 1)
            self.assertFalse(json.loads((out/'recorded-trial.json').read_text())['provider_closed'])

    def test_receipt_write_failure_exposes_original_report_and_bounds(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'trial'
            original = worker._write_receipt
            def fail_final(path, value, **kwargs):
                if Path(path).name == 'recorded-trial.json':
                    raise OSError('final receipt write failure')
                return original(path, value, **kwargs)
            with patch.object(worker, '_write_receipt', side_effect=fail_final):
                with self.assertRaises(worker.TrialFailure) as caught:
                    self.execute(out)
            self.assertIsNotNone(caught.exception.report)
            self.assertTrue(any('receipt write failure' in v for v in [caught.exception.primary_error]+caught.exception.secondary_errors))
            self.assertEqual(caught.exception.fixture_provider.calls, 1)
            life = json.loads((out/'recorded-trial-lifecycle.json').read_text())
            self.assertEqual(life['status'], 'FAILED_OR_INCOMPLETE')
            self.assertIn('receipt write failure', life['primary_error'])

    def test_source_receipt_failure_does_not_mask_original_graph_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'trial'
            with patch.object(worker, '_source_snapshot', side_effect=OSError('fingerprint read failed'), create=True):
                with self.assertRaises(worker.TrialFailure) as caught:
                    self.execute(out, fail_on=2)
            self.assertIn('graph failure', caught.exception.primary_error)
            self.assertTrue(any('fingerprint read failed' in value for value in caught.exception.secondary_errors))
            self.assertEqual(caught.exception.inference_bounds, [1, 2])

    def test_lazy_import_failure_is_a_recorded_zero_inference_failure(self):
        original=builtins.__import__
        def fail_import(name,*args,**kwargs):
            if name=='scripts.native_mdv3_repeat_trial':raise ImportError('dependency import failed')
            return original(name,*args,**kwargs)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'trial';caught=None
            with patch.object(builtins,'__import__',side_effect=fail_import):
                try:self.execute(out)
                except Exception as exc:caught=exc
            self.assertIsInstance(caught,worker.TrialFailure)
            self.assertEqual(caught.inference_bounds,[0,0])
            self.assertIn('dependency import failed',caught.primary_error)
            self.assertFalse(json.loads((out/'recorded-trial-lifecycle.json').read_text())['policy_constructor_entered'])

    def test_graph_error_precedes_later_capture_serialization_error(self):
        from bigbench import full_s_failure_capture as capture
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'trial'
            with patch.object(capture,'_write_blob',side_effect=OSError('blob write failed')):
                with self.assertRaises(worker.TrialFailure) as caught:self.execute(out,fail_on=2)
            self.assertIn('graph failure',caught.exception.primary_error)
            self.assertTrue(any('blob write failed' in v for v in caught.exception.secondary_errors))
            self.assertEqual(caught.exception.inference_bounds,[1,2])

    def test_finalization_path_probe_errors_keep_primary_graph_error_and_bounds(self):
        for method,name in (('is_file','manifest.json'),('exists','report.json')):
            original=getattr(Path,method)
            def fail_stat(path,original=original,name=name):
                if path.name==name and path.parent.name=='recording':raise OSError(errno.EIO,'path probe failed')
                return original(path)
            with self.subTest(method=method),tempfile.TemporaryDirectory() as temp:
                out=Path(temp)/'trial';caught=None
                with patch.object(Path,method,new=fail_stat):
                    try:self.execute(out,fail_on=2)
                    except Exception as exc:caught=exc
                self.assertIsInstance(caught,worker.TrialFailure)
                self.assertIn('graph failure',caught.primary_error)
                self.assertEqual(caught.inference_bounds,[1,2])
                self.assertTrue(any('path probe failed' in v for v in caught.secondary_errors))

    def test_failed_capture_without_callback_does_not_claim_raw_observation(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'trial'
            with patch.object(self.source_camera,'capture',side_effect=RuntimeError('camera failed before callback')):
                with self.assertRaises(worker.TrialFailure):self.execute(out)
            receipt=json.loads((out/'recorded-trial.json').read_text())
            self.assertIsNone(receipt['raw_rgb_observer_used'])
            self.assertTrue(receipt['raw_rgb_observer_requested'])

    def test_frozen_world_pre_handoff_cleanup_preserves_exception_chain(self):
        from scripts import native_mdv3_repeat_trial as model
        from bigbench import metadrive_camera,curved_lane_scenarios
        parent=self.inner_policy()
        class Provider:
            calls=0
            env=SimpleNamespace(current_map=object())
            def close(self):self.calls+=1;raise RuntimeError('factory close failure')
        provider=Provider()
        fake_constants=SimpleNamespace(Semantics=object(),CameraTagStateKey=object())
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'trial';args=SimpleNamespace(out=out,nonce='a'*32,seed=20261109,scenario='s_curve_left_right')
            with patch.object(model,'AuditedOfficialOnnx',return_value=parent), \
                 patch.object(metadrive_camera,'NativeMetaDriveProvider',return_value=provider), \
                 patch.object(curved_lane_scenarios,'select_native_curve_lanes',side_effect=ValueError('lane failure')), \
                 patch.dict(sys.modules,{'metadrive.constants':fake_constants}), \
                 patch('scripts.sdk3_priority_model_native.source_stats_after',return_value={}):
                with self.assertRaises(worker.TrialFailure) as caught:worker.run_recorded_trial(args)
            self.assertIn('lane failure',caught.exception.primary_error)
            self.assertTrue(any('factory close failure' in v for v in caught.exception.secondary_errors))
            self.assertEqual(provider.calls,1)
            life=json.loads((out/'recorded-trial-lifecycle.json').read_text())
            self.assertIsNone(life['provider_created'])
            self.assertFalse(life['provider_received'])


if __name__ == '__main__':
    unittest.main()
