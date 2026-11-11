"""CPU behavior tests: no native provider, GPU, ORT, weights or network."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from hashlib import sha256
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from bigbench.camera import RGBFrame
from bigbench.camera_rig import SchematicPair
from bigbench.camera_convergence import StrictConsecutiveCamera
from bigbench.kinematics import AgentState
from bigbench.optical_calibration import PinholeRectifier, reference_source
from bigbench.policies import ModelObservation
from bigbench import native_model_campaign as campaign

try:
    fd = importlib.import_module('bigbench.first_divergence')
except ModuleNotFoundError as exc:
    if exc.name != 'bigbench.first_divergence':
        raise
    fd = None


class Lens:
    def __init__(self, kind):
        self.k = reference_source(kind)
    def getFilmSize(self):
        return (964 / self.k.fx, 604 / self.k.fy)
    def getFilmOffset(self):
        return (0, 0)
    def getFocalLength(self):
        return 1


class Sensor:
    def __init__(self, kind):
        self.lens = Lens(kind)
    def get_lens(self):
        return self.lens


class Provider:
    source_width, source_height = 964, 604
    def __init__(self):
        from types import SimpleNamespace
        self.env = SimpleNamespace(engine=SimpleNamespace(sensors={
            'bigbench_' + k: Sensor(k) for k in ('road', 'wide')}))


class CopiedBufferCamera:
    """Boundary double for only native readback; uses real pure rectification."""
    def __init__(self, provider, raw_rgb_observer=None):
        self.provider, self.observer = provider, raw_rgb_observer
        self.calls = 0
        self.fault = None
        self.arrays = None
        self.last_source_rgb_sha256 = {}
    def capture(self, pose):
        self.calls += 1
        if self.fault == 'throw':
            raise RuntimeError('native capture failure')
        # Attempts 1, 2 differ; attempts 2, 3 converge. Selected raw is 40.
        v = 20 if self.calls == 1 else 40
        self.arrays = {'road': np.full((604, 964, 3), v, np.uint8),
                       'wide': np.full((604, 964, 3), 255, np.uint8)}
        pair, _ = PinholeRectifier().rectify_pair(self.arrays['road'], self.arrays['wide'])
        hashes = {k: sha256(a.tobytes()).hexdigest() for k, a in self.arrays.items()}
        self.last_source_rgb_sha256 = hashes
        if self.fault != 'missing':
            self.observer.record_native_rgb(self.arrays, hashes)
        if self.fault == 'double':
            self.observer.record_native_rgb(self.arrays, hashes)
        if self.fault == 'mutate':
            self.arrays['road'][0, 0, 0] = 9
        return pair


class FirstDivergenceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(fd, 'capture collector must implement accepted-buffer association')
        self.pose = AgentState(0., 0., 0., 0., 8.)

    def capture(self, collector, converge=False):
        with patch.object(campaign, 'NativeWorldCamera', CopiedBufferCamera):
            with fd.capture_scope(collector.arm, collector):
                camera = campaign.NativeWorldCamera(Provider())
                source = StrictConsecutiveCamera(camera, max_captures=6,
                    max_changed_pixels=16, max_rgb_delta=10) if converge else camera
                pair = source.capture(self.pose)
                camera.test_receipts = [asdict(r) for r in source.receipts] if converge else []
        return pair, camera

    def accept(self, collector, pair):
        return collector.accept_observation(ModelObservation(pair.road, self.pose.speed, self.pose.t, wide_frame=pair.wide))

    def dataset(self, root):
        c = fd.CaptureCollector()
        pair, first = self.capture(c, converge=True)
        self.accept(c, pair)
        initial = self.pose
        self.pose = AgentState(.05, .4, 0., 0., 8.)
        pair, second = self.capture(c, converge=True)
        self.accept(c, pair)
        self.pose = initial
        c.mark_closed()
        c.write_dataset(root, metadata={'convergence_receipts': first.test_receipts + second.test_receipts})
        return c

    @contextmanager
    def canary_fixture(self, temp):
        from bigbench import metadrive_camera, curved_lane_scenarios
        from types import SimpleNamespace
        out = Path(temp)/'canary'
        lifecycle = []
        class CanaryProvider(Provider):
            def __init__(self, **kwargs):
                super().__init__(); self.env.current_map = object(); lifecycle.append('created')
            def close(self):
                if out.exists():
                    raise AssertionError('serialized before provider close')
                lifecycle.append('closed')
        lane = SimpleNamespace(length=10., position=lambda s,l:(s,l), heading_theta_at=lambda s:0.)
        with patch.dict('os.environ',{'GITHUB_ACTIONS':'true','RUNNER_TEMP':temp}), \
             patch.object(metadrive_camera,'NativeMetaDriveProvider',CanaryProvider), \
             patch.object(curved_lane_scenarios,'select_native_curve_lanes',return_value=[lane]), \
             patch.object(campaign,'NativeWorldCamera',CopiedBufferCamera):
            yield out, lifecycle

    def rewrite_manifest(self, root, change):
        path = root / 'manifest.json'
        d = json.loads(path.read_text())
        change(d)
        path.write_text(json.dumps(d))

    def test_accepts_only_last_convergence_attempt_and_does_no_extra_captures(self):
        c = fd.CaptureCollector()
        pair, camera = self.capture(c, converge=True)
        accepted = self.accept(c, pair)
        self.assertEqual(camera.delegate.calls, 3)
        self.assertEqual(c.capture_count, 3)
        self.assertEqual(accepted.capture_index, 3)
        self.assertIs(accepted.pair.road, pair.road)
        self.assertEqual(accepted.raw_rgb['road'][0, 0].tolist(), [40, 40, 40])
        self.assertEqual(len(c.records), 1)
        self.assertEqual(c.capture_rows[-1]['capture_index'], 3)
        self.assertGreaterEqual(c.capture_rows[-1]['capture_inclusive_wall_s'],
                                c.capture_rows[-1]['raw_callback_nested_wall_s'])
        self.assertIsNotNone(c.capture_rows[-1].get('capture_wrapper_wall_s'))
        self.assertGreaterEqual(c.capture_rows[-1]['capture_wrapper_wall_s'],
                                c.capture_rows[-1]['capture_inclusive_wall_s'])
        self.assertGreaterEqual(c.capture_rows[-1]['wrapper_observer_arithmetic_wall_s'], 0.)

    def test_same_bytes_wrong_objects_and_stale_pair_are_rejected(self):
        c = fd.CaptureCollector()
        pair, _ = self.capture(c)
        impostor = SchematicPair(RGBFrame(512, 256, pair.road.rgb), pair.wide)
        with self.assertRaises(ValueError):
            self.accept(c, impostor)
        self.accept(c, pair)
        with self.assertRaises(ValueError):
            self.accept(c, pair)
        newer, _ = self.capture(c)
        with self.assertRaises(ValueError):
            self.accept(c, pair)
        self.accept(c, newer)

    def test_mutation_after_callback_or_return_is_rejected(self):
        for fault in ('mutate', 'missing', 'double'):
            with self.subTest(fault=fault):
                c = fd.CaptureCollector()
                with patch.object(campaign, 'NativeWorldCamera', CopiedBufferCamera):
                    with fd.capture_scope('retention', c):
                        cam = campaign.NativeWorldCamera(Provider())
                        cam.delegate.fault = fault
                        with self.assertRaises(ValueError):
                            cam.capture(self.pose)
        c = fd.CaptureCollector()
        pair, cam = self.capture(c)
        cam.delegate.arrays['wide'][0, 0, 1] = 2
        with self.assertRaises(ValueError):
            self.accept(c, pair)

    def test_hashes_and_shape_are_checked_at_callback(self):
        c = fd.CaptureCollector()
        with self.assertRaises(ValueError):
            c.record_native_rgb({'road': np.zeros((2, 2, 3), np.uint8)}, {'road': '0'*64})
        with patch.object(campaign, 'NativeWorldCamera', CopiedBufferCamera):
            with fd.capture_scope('retention', c):
                cam = campaign.NativeWorldCamera(Provider())
                original = cam.delegate.capture
                def incorrect(pose):
                    def bad(images, hashes):
                        hashes['road'] = '0'*64
                        c.record_native_rgb(images, hashes)
                    cam.delegate.observer = type('Hook', (), {'record_native_rgb': staticmethod(bad)})()
                    return original(pose)
                cam.delegate.capture = incorrect
                with self.assertRaises(ValueError):
                    cam.capture(self.pose)

    def test_restores_factory_on_capture_and_scope_exceptions_and_original_is_untouched(self):
        with patch.object(campaign, 'NativeWorldCamera', CopiedBufferCamera):
            original = campaign.NativeWorldCamera
            with fd.capture_scope('original', fd.CaptureCollector(arm='original')):
                self.assertIs(campaign.NativeWorldCamera, original)
            with self.assertRaisesRegex(RuntimeError, 'native capture failure'):
                with fd.capture_scope('retention', fd.CaptureCollector()):
                    cam = campaign.NativeWorldCamera(Provider())
                    cam.delegate.fault = 'throw'
                    cam.capture(self.pose)
            self.assertIs(campaign.NativeWorldCamera, original)
            with self.assertRaisesRegex(RuntimeError, 'body'):
                with fd.capture_scope('proxy', fd.CaptureCollector(arm='proxy')):
                    raise RuntimeError('body')
            self.assertIs(campaign.NativeWorldCamera, original)
            with fd.capture_scope('retention', fd.CaptureCollector()):
                with self.assertRaises(ValueError):
                    with fd.capture_scope('original', fd.CaptureCollector(arm='original')):
                        pass
            self.assertIs(campaign.NativeWorldCamera, original)

    def test_proxy_counts_without_retaining_payload_and_rejects_duplicate_selection(self):
        c = fd.CaptureCollector(arm='proxy')
        pair, _ = self.capture(c)
        record = self.accept(c, pair)
        self.assertIsNone(record.raw_rgb)
        self.assertTrue(record.pair is None, 'proxy retained a full canvas pair')
        self.assertEqual(c.payload_bytes, 0)
        self.assertEqual(c.capture_count, 1)
        with self.assertRaises(ValueError):
            self.accept(c, pair)

    def test_payload_cap_and_capture_limit_fail_before_extra_capture(self):
        c = fd.CaptureCollector(payload_cap_bytes=1)
        with self.assertRaises(ValueError):
            self.capture(c)
        c = fd.CaptureCollector(max_captures=1)
        with patch.object(campaign, 'NativeWorldCamera', CopiedBufferCamera):
            with fd.capture_scope('retention', c):
                cam = campaign.NativeWorldCamera(Provider())
                cam.capture(self.pose)
                with self.assertRaises(ValueError):
                    cam.capture(self.pose)
                self.assertEqual(cam.delegate.calls, 1)

    def test_serialization_requires_closure_and_validates_literal_gray_i420(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            c = fd.CaptureCollector()
            pair, _ = self.capture(c)
            self.accept(c, pair)
            with self.assertRaises(ValueError):
                c.write_dataset(root)
            self.assertEqual(list(root.iterdir()), [])
            c = self.dataset(root)
            result = fd.validate_capture_dataset(root)
            self.assertEqual(result['accepted_pairs'], 2)
            d = json.loads((root/'manifest.json').read_text())
            row = d['accepted'][0]
            # RGB(40,40,40) -> limited-range Y=50, U=V=128; white Y=235.
            # Road y_src(255)=603.752: INTER_LINEAR samples 25% gray at
            # the bottom border. RGB10 -> Y25 on odd-row planes 1 and 3.
            plane = bytes([50])*(128*256)
            bottom = bytes([50])*(127*256) + bytes([25])*256
            expected = plane + bottom + plane + bottom + bytes([128])*(2*128*256)
            expected += bytes([235])*(4*128*256) + bytes([128])*(2*128*256)
            self.assertEqual((root/row['packed']['path']).read_bytes(), expected)
            self.assertEqual(row['packed']['actual_input_sha256'], None)
            self.assertEqual(row['intrinsics']['road'], asdict(reference_source('road')))
            self.assertFalse(d['claims']['original_strict_pass'])

    def test_dataset_rejects_missing_unsafe_symlink_and_unregistered_files(self):
        mutations = ('missing', 'unsafe', 'symlink', 'extra')
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.dataset(root)
                d = json.loads((root/'manifest.json').read_text())
                member = root / d['accepted'][0]['raw']['road']['path']
                if mutation == 'missing':
                    member.unlink()
                elif mutation == 'unsafe':
                    self.rewrite_manifest(root, lambda x: x['accepted'][0]['raw']['road'].update(path='../outside.png'))
                elif mutation == 'symlink':
                    other = root/'outside'
                    member.rename(other)
                    member.symlink_to(other)
                else:
                    (root/'extra.bin').write_bytes(b'unregistered')
                with self.assertRaises(ValueError):
                    fd.validate_capture_dataset(root)

    def test_valid_file_hash_cannot_hide_canvas_warp_or_packed_tampering(self):
        for boundary in ('raw', 'canvas', 'packed', 'intrinsics'):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.dataset(root)
                d = json.loads((root/'manifest.json').read_text())
                row = d['accepted'][0]
                if boundary == 'intrinsics':
                    row['intrinsics']['road']['fx'] *= 1.2
                else:
                    desc = row['packed'] if boundary == 'packed' else row[boundary]['road']
                    path = root/desc['path']
                    if boundary == 'packed':
                        data = bytearray(path.read_bytes()); data[0] ^= 1; path.write_bytes(data)
                    else:
                        width, height = (964,604) if boundary == 'raw' else (512,256)
                        RGBFrame(width,height,bytes([80])*(width*height*3)).save_png(path)
                        desc['rgb_sha256'] = sha256(bytes([80])*(width*height*3)).hexdigest()
                    desc.update(sha256=sha256(path.read_bytes()).hexdigest(), nbytes=path.stat().st_size)
                (root/'manifest.json').write_text(json.dumps(d))
                with self.assertRaises(ValueError):
                    fd.validate_capture_dataset(root)

    def test_validator_rejects_png_crc_budget_claims_and_feed_mismatch(self):
        for mutation in ('crc', 'budget', 'claims', 'actual_feed'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); self.dataset(root)
                d = json.loads((root/'manifest.json').read_text())
                if mutation == 'crc':
                    desc = d['accepted'][0]['raw']['road']
                    path = root/desc['path']; data = bytearray(path.read_bytes()); data[-1] ^= 1; path.write_bytes(data)
                    desc['sha256'] = sha256(data).hexdigest()
                elif mutation == 'budget':
                    d['retained_payload_bytes'] = 2**30
                elif mutation == 'claims':
                    d['claims']['original_strict_pass'] = True
                else:
                    d['accepted'][0]['packed']['actual_input_sha256'] = '0'*64
                (root/'manifest.json').write_text(json.dumps(d))
                with self.assertRaises(ValueError):
                    fd.validate_capture_dataset(root)

    def test_late_feed_binding_verifies_exact_derived_bytes_after_closure(self):
        c = fd.CaptureCollector()
        pair, cam = self.capture(c)
        record = self.accept(c, pair)
        before = record.raw_rgb['road'].tobytes()
        cam.delegate.arrays['road'][:] = 0
        self.assertEqual(record.raw_rgb['road'].tobytes(), before)
        record.bind_actual_input('0'*64)
        with self.assertRaises(ValueError):
            record.bind_actual_input('1'*64)
        c.mark_closed()
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                c.serialize_captures(Path(temp))

    def test_protocol_and_attempt_identity_tampering_fails_closed(self):
        for mutation in ('protocol', 'attempt_raw', 'attempt_canvas', 'observation', 'pose'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); self.dataset(root)
                d = json.loads((root/'manifest.json').read_text())
                if mutation == 'protocol':
                    d['protocol']['convergence']['max_captures'] = 12
                elif mutation == 'attempt_raw':
                    d['capture_rows'][2].setdefault('raw_sha256', {})['road'] = '0'*64
                elif mutation == 'attempt_canvas':
                    d['capture_rows'][2].setdefault('canvas_sha256', {})['wide'] = '0'*64
                elif mutation == 'observation':
                    d['accepted'][1]['observation']['time_s'] = 9.
                else:
                    d['capture_rows'][1]['pose']['x'] += 1.
                (root/'manifest.json').write_text(json.dumps(d))
                with self.assertRaises(ValueError):
                    fd.validate_capture_dataset(root)

    def test_cli_validation_returns_nonzero_for_invalid_dataset_without_native_imports(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([sys.executable, '-m', 'scripts.first_divergence_audit',
                                     'validate-canary', '--root', temp], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['status'], 'FAILED_OR_INCOMPLETE')

    def test_canary_uses_one_provider_two_selected_pairs_and_writes_after_close(self):
        from bigbench import metadrive_camera, curved_lane_scenarios
        from types import SimpleNamespace
        lifecycle = []
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'canary'
            class CanaryProvider(Provider):
                def __init__(self, *, seed, map_config):
                    self_seed = seed
                    if self_seed != 20261109:
                        raise AssertionError('unregistered native seed')
                    super().__init__()
                    self.env.current_map = object()
                    lifecycle.append('created')
                def close(self):
                    if out.exists():
                        raise AssertionError('evidence serialized before close')
                    lifecycle.append('closed')
            lane = SimpleNamespace(length=10., position=lambda s,l: (s,l), heading_theta_at=lambda s: 0.)
            with patch.dict('os.environ', {'GITHUB_ACTIONS':'true','RUNNER_TEMP':temp}), \
                 patch.object(metadrive_camera,'NativeMetaDriveProvider',CanaryProvider), \
                 patch.object(curved_lane_scenarios,'select_native_curve_lanes',return_value=[lane]), \
                 patch.object(campaign,'NativeWorldCamera',CopiedBufferCamera):
                result = fd.capture_canary(out)
            self.assertEqual(lifecycle, ['created','closed'])
            self.assertEqual(result['capture_count'], 5)
            self.assertEqual(result['model_calls'], 0)
            self.assertEqual(result['ort_sessions'], 0)
            self.assertEqual([r['attempts'] for r in result['metadata']['convergence_receipts']], [3,2])
            self.assertEqual(result['accepted'][1]['observation'], {'speed_mps':8.,'time_s':.05})
            self.assertEqual(result['capture_rows'][-1]['pose']['x'], 1.6)

    def test_manifest_rejects_unregistered_claims_and_convergence_receipt_lies(self):
        for mutation in ('top_claim','metadata_claim','receipt'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); self.dataset(root)
                d = json.loads((root/'manifest.json').read_text())
                if mutation == 'top_claim':
                    d['original_strict_pass'] = True
                elif mutation == 'metadata_claim':
                    d['metadata']['original_strict_pass'] = True
                else:
                    d['metadata']['convergence_receipts'] = [dict(attempts=1,stable=True)]*2
                (root/'manifest.json').write_text(json.dumps(d))
                with self.assertRaises(ValueError):
                    fd.validate_capture_dataset(root)

    def test_symlink_output_ancestor_is_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            (base/'real').mkdir()
            (base/'alias').symlink_to(base/'real',target_is_directory=True)
            c = fd.CaptureCollector()
            pair, _ = self.capture(c); self.accept(c,pair); c.mark_closed()
            with self.assertRaises(ValueError):
                c.serialize_captures(base/'alias'/'new')
            self.assertEqual(list((base/'real').iterdir()), [])

    def test_canary_failure_preserves_prefix_bounds_and_primary_error_after_close(self):
        from bigbench import metadrive_camera, curved_lane_scenarios
        from types import SimpleNamespace
        for close_fails in (False, True):
            with self.subTest(close_fails=close_fails), tempfile.TemporaryDirectory() as temp:
                out = Path(temp)/'partial'
                class FailureProvider(Provider):
                    def __init__(self, **kwargs):
                        super().__init__(); self.env.current_map = object()
                    def close(self):
                        if out.exists():
                            raise AssertionError('serialized before provider close attempt')
                        if close_fails:
                            raise RuntimeError('close failed')
                class ThrowLater(CopiedBufferCamera):
                    def capture(self,pose):
                        if self.calls == 3:
                            raise RuntimeError('primary capture failed')
                        return super().capture(pose)
                lane = SimpleNamespace(length=10.,position=lambda s,l:(s,l),heading_theta_at=lambda s:0.)
                with patch.dict('os.environ',{'GITHUB_ACTIONS':'true','RUNNER_TEMP':temp}), \
                     patch.object(metadrive_camera,'NativeMetaDriveProvider',FailureProvider), \
                     patch.object(curved_lane_scenarios,'select_native_curve_lanes',return_value=[lane]), \
                     patch.object(campaign,'NativeWorldCamera',ThrowLater):
                    with self.assertRaisesRegex(RuntimeError,'primary capture failed'):
                        fd.capture_canary(out)
                self.assertTrue((out/'manifest.json').is_file(), 'failed canary lost its accepted prefix ledger')
                data = json.loads((out/'manifest.json').read_text())
                self.assertEqual(data['status'],'FAILED_OR_INCOMPLETE')
                self.assertEqual(data['accepted_pairs'],1)
                self.assertEqual(data['capture_count'],4)
                self.assertIsNone(data['sensor_calls'])
                self.assertEqual(data['sensor_calls_lower_bound'],6)
                self.assertEqual(data['sensor_calls_upper_bound'],8)
                self.assertEqual(data['provider_closed'],not close_fails)
                self.assertIn('primary capture failed',data['error'])
                if close_fails:
                    self.assertIn('close failed',data['cleanup_error'])
                    self.assertEqual(list(out.rglob('*.png')),[])
                else:
                    self.assertEqual(len(list(out.rglob('*.png'))),4)
                with self.assertRaises(ValueError):
                    fd.validate_capture_dataset(out)

    def test_post_close_png_error_preserves_partial_members_without_reserializing(self):
        original = RGBFrame.save_png
        writes = []
        def save(frame,path):
            writes.append(path)
            if len(writes) == 3:
                raise OSError('third PNG write failed')
            return original(frame,path)
        with tempfile.TemporaryDirectory() as temp, self.canary_fixture(temp) as (out,lifecycle):
            with patch.object(RGBFrame,'save_png',save):
                with self.assertRaisesRegex(OSError,'third PNG write failed'):
                    fd.capture_canary(out)
            self.assertEqual(lifecycle,['created','closed'])
            self.assertEqual(len(writes),3, 'failure handling retried bulk serialization')
            self.assertEqual(len(list(out.rglob('*.png'))),2)
            self.assertTrue((out/'manifest.json').exists(), 'post-close error lost failure ledger')
            failed = json.loads((out/'manifest.json').read_text())
            self.assertEqual(failed['status'],'FAILED_OR_INCOMPLETE')
            self.assertIn('third PNG write failed',failed['error'])
            self.assertEqual(failed['accepted_pairs'],2)
            self.assertEqual(failed['capture_count'],5)
            self.assertTrue(failed['provider_closed'])
            with self.assertRaises(ValueError):
                fd.validate_capture_dataset(out)

    def test_post_close_real_validation_error_never_publishes_success(self):
        mark_closed = fd.CaptureCollector.mark_closed
        def invalidate(collector):
            mark_closed(collector)
            collector.capture_rows[0]['status'] = 'FAILED_OR_INCOMPLETE'
        with tempfile.TemporaryDirectory() as temp, self.canary_fixture(temp) as (out,lifecycle):
            with patch.object(fd.CaptureCollector,'mark_closed',invalidate):
                with self.assertRaises(ValueError):
                    fd.capture_canary(out)
            self.assertEqual(lifecycle,['created','closed'])
            self.assertEqual(len(list(out.rglob('*.png'))),8)
            self.assertTrue((out/'manifest.json').exists())
            failed = json.loads((out/'manifest.json').read_text())
            self.assertEqual(failed['status'],'FAILED_OR_INCOMPLETE')
            self.assertEqual(failed['accepted_pairs'],2)
            self.assertEqual(failed['capture_count'],5)
            self.assertIn('error',failed)
            with self.assertRaises(ValueError):
                fd.validate_capture_dataset(out)

    def test_failure_ledger_preserves_existing_manifest_and_original_io_error(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); collector = self.dataset(root)
            original = (root/'manifest.json').read_bytes()
            try:
                result = collector.write_failure_dataset(root,OSError('publish failed'),provider_closed=True)
            except Exception as exc:
                self.fail('existing manifest prevented failure ledger: '+str(exc))
            self.assertEqual(result['status'],'FAILED_OR_INCOMPLETE')
            self.assertEqual((root/'manifest.json').read_bytes(),original)
            self.assertEqual(json.loads((root/'failure.json').read_text())['error'],'OSError: publish failed')
            with self.assertRaises(ValueError):
                fd.validate_capture_dataset(root)
        original_save = RGBFrame.save_png
        calls = []
        def bad_save(frame,path):
            calls.append(path)
            if len(calls)==3:
                raise OSError('primary serialization failed')
            return original_save(frame,path)
        with tempfile.TemporaryDirectory() as temp, self.canary_fixture(temp) as (out,lifecycle):
            with patch.object(RGBFrame,'save_png',bad_save), \
                 patch.object(fd.CaptureCollector,'write_failure_dataset',side_effect=OSError('ledger unavailable')):
                with self.assertRaisesRegex(OSError,'primary serialization failed') as raised:
                    fd.capture_canary(out)
            self.assertTrue(any('ledger unavailable' in note for note in getattr(raised.exception,'__notes__',[])),
                            'secondary ledger I/O was lost or replaced the primary error')
            self.assertEqual(lifecycle,['created','closed'])

    def test_nested_record_claims_and_wrong_types_are_rejected(self):
        cases = [
            (('accepted',0), 'original_strict_pass', True),
            (('accepted',0), 'model_calls', 1),
            (('capture_rows',0), 'model_calls', 1),
            (('accepted',0,'raw','road'), 'original_strict_pass', True),
            (('accepted',0,'packed'), 'model_calls', 1),
            (('accepted',0,'raw'), 'model_calls', 1),
            (('accepted',0,'intrinsics'), 'original_strict_pass', True),
            (('accepted',0,'observation'), 'model_calls', 1),
            (('capture_rows',0,'pose'), 'original_strict_pass', True),
            (('capture_rows',0,'raw_sha256'), 'model_calls', 1),
            (('capture_rows',0), 'capture_index', True),
            (('accepted',0), 'accepted_index', True),
            (('accepted',0,'intrinsics','road'), 'fx', True),
            (('accepted',0,'observation'), 'time_s', False),
            (('accepted',0,'observation'), 'time_s', 10**1000),
            ((), 'accepted_pairs', 2.0),
            ((), 'sensor_calls', 12.0),
            (('metadata',), 'process_id', True),
            (('metadata',), 'process_uuid', []),
            (('metadata',), 'source_binding', {}),
            (('metadata',), 'runtime_versions', {'original_strict_pass':True}),
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.dataset(root)
            saved = (root/'manifest.json').read_text()
            for route,key,value in cases:
                with self.subTest(route=route,key=key,value=value):
                    data = json.loads(saved); container=data
                    for part in route:
                        container=container[part]
                    container[key]=value
                    (root/'manifest.json').write_text(json.dumps(data))
                    with self.assertRaises(ValueError):
                        fd.validate_capture_dataset(root)

    def test_missing_negative_or_contradictory_wrapper_acceptance_timings_are_rejected(self):
        cases = [
            (0,'capture_wrapper_wall_s',None),
            (0,'capture_wrapper_wall_s',-1),
            (0,'capture_wrapper_wall_s',0),
            (0,'wrapper_observer_arithmetic_wall_s',None),
            (0,'wrapper_observer_arithmetic_wall_s',-1),
            (0,'wrapper_observer_arithmetic_wall_s',100),
            (0,'capture_wrapper_wall_s',True),
            (0,'wrapper_observer_arithmetic_wall_s',float('inf')),
            (2,'accept_observation_wall_s',None),
            (2,'accept_observation_wall_s',-1),
            (2,'accept_observation_wall_s',True),
            (2,'accept_observation_wall_s',float('nan')),
            (0,'accept_observation_wall_s',0),
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.dataset(root)
            saved = (root/'manifest.json').read_text()
            for index,key,value in cases:
                with self.subTest(index=index,key=key,value=value):
                    data=json.loads(saved)
                    if value is None:
                        del data['capture_rows'][index][key]
                    else:
                        data['capture_rows'][index][key]=value
                    (root/'manifest.json').write_text(json.dumps(data))
                    with self.assertRaises(ValueError):
                        fd.validate_capture_dataset(root)

    def test_post_close_manifest_size_failure_is_preserved_before_publication(self):
        versions = fd.runtime_versions()
        versions['python'] = 'x'*(8*1024*1024)
        with tempfile.TemporaryDirectory() as temp, self.canary_fixture(temp) as (out,lifecycle):
            with patch.object(fd,'runtime_versions',return_value=versions):
                with self.assertRaises(ValueError):
                    fd.capture_canary(out)
            self.assertEqual(lifecycle,['created','closed'])
            failed=json.loads((out/'manifest.json').read_text())
            self.assertEqual(failed['status'],'FAILED_OR_INCOMPLETE')
            self.assertIn('manifest',failed['error'])
            self.assertEqual(failed['accepted_pairs'],2)
            self.assertEqual(len(list(out.rglob('*.png'))),8)

    def test_source_snapshot_rejects_changed_dependency_and_canary_requires_ephemeral_ci(self):
        snapshot = fd.source_snapshot()
        self.assertIn('bigbench/public_action_frame.py', snapshot)
        self.assertIn('bigbench/image_adapter.py', snapshot)
        self.assertIn('model_specs/md-v3.json', snapshot)
        changed = dict(snapshot); changed['bigbench/image_adapter.py'] = '0'*64
        with self.assertRaises(ValueError):
            fd.verify_source_snapshot(changed)
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError):
                fd.capture_canary(Path('/tmp/no-native-first-divergence-test'))


if __name__ == '__main__':
    unittest.main()
