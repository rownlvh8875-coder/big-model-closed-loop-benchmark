"""CPU fixtures only: real loop/adapter/policy; external renderer/graph doubled."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

try:
    from bigbench import full_s_failure_capture as capture
except ImportError:
    capture = None

from bigbench.full_s_validation import run_full_s, STRICT
from bigbench.model_world_frame import WorldFramePolicyAdapter, SOURCE_ACTION_FRAME
from bigbench.onnx_contract import ModelContract
from bigbench.optical_calibration import PinholeRectifier, reference_source
from scripts.native_mdv3_repeat_trial import AuditedOfficialOnnx
from tests.full_s_fakes import route, Arc, Straight

ROOT = Path(__file__).resolve().parents[1]
INTRINSICS = {role: reference_source(role) for role in ('road', 'wide')}


class SourceCamera:
    def __init__(self):
        self.raw_rgb_observer = None
        self.last_source_rgb_sha256 = {}
        self.calls = 0
        self.pairs = []

    def capture(self, state):
        self.calls += 1
        arrays = {role: np.full((604, 964, 3), value + self.calls % 9, np.uint8)
                  for role, value in (('road', 13), ('wide', 71))}
        hashes = {key: hashlib.sha256(value.tobytes()).hexdigest() for key, value in arrays.items()}
        pair, _ = PinholeRectifier().rectify_pair(arrays['road'], arrays['wide'],
            road_intrinsics=INTRINSICS['road'], wide_intrinsics=INTRINSICS['wide'])
        self.last_source_rgb_sha256 = hashes
        if self.raw_rgb_observer is not None:
            self.raw_rgb_observer.record_native_rgb(arrays, hashes)
        self.pairs.append((id(pair.road), id(pair.wide)))
        return pair


class GraphBoundary:
    def __init__(self, fail_on=None):
        self.calls = 0
        self.fail_on = fail_on
        self.pre_feature_values = []

    def run(self, names, feed):
        self.calls += 1
        self.pre_feature_values.append(float(feed['state_feat_q'].flat[0]))
        if self.calls == self.fail_on:
            raise RuntimeError('unit fixture graph failure; actual outcome unknown')
        outputs = np.zeros((1, 18452), np.float32)
        outputs[0, 2062:2066] = [-.064, .1, 1., 2.]
        result = {'outputs': outputs}
        result.update({'next_' + key: np.full_like(feed[key], self.calls % 251)
                       for key in ('state_img_q', 'state_desire_q', 'state_feat_q')})
        return [result[name] for name in names]


def inner_policy(fail_on=None):
    # Avoid only the external official file/session constructor. Every step,
    # packing, audit, recurrent commit and action conversion uses original code.
    p = object.__new__(AuditedOfficialOnnx)
    p.contract = ModelContract.load(ROOT / 'model_specs/md-v3.json')
    types = {k: ('uint8' if k in ('new_img', 'state_img_q', 'next_state_img_q') else 'float32')
             for k in set(p.contract.input_shapes) | set(p.contract.output_shapes)}
    p._types = {k: np.dtype(v) for k, v in types.items()}
    p._injected_session = True
    p.is_mock = True
    p.name = 'UNIT_FIXTURE_NOT_MODEL_EVIDENCE'
    p.traffic_convention = np.array([[1., 0.]], np.float32)
    p.action_t = np.array([[.175, .175]], np.float32)
    p.session = GraphBoundary(fail_on)
    p.reset()
    return p


def long_route():
    a = Arc((0., 0.), 0., 1, ('A', 'B', 0))
    a.length = 1000.
    b = Straight(a.position(a.length, 0.), a.heading_theta_at(a.length), ('B', 'C', 0))
    c = Arc(b.position(b.length, 0.), b.heading_theta_at(b.length), -1, ('C', 'D', 0))
    return a, b, c


class FullSFailureCaptureTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(capture, 'bounded full-S failure recorder is missing')

    def record(self, out, steps=3, fail_on=None, lanes=None, progress=None):
        inner = inner_policy(fail_on)
        policy = WorldFramePolicyAdapter(inner, source_action_frame=SOURCE_ACTION_FRAME)
        camera = SourceCamera()
        report = capture.capture_full_s(policy, camera, lanes or route(), intrinsics=INTRINSICS,
            out=out, seed=20261109, scene='s_curve_left_right', max_steps=steps, progress=progress)
        return report, inner, camera

    def test_original_scientific_rows_capture_calls_and_parent_states_are_unchanged(self):
        inner = inner_policy()
        baseline_camera = SourceCamera()
        baseline = run_full_s(WorldFramePolicyAdapter(inner, source_action_frame=SOURCE_ACTION_FRAME),
            baseline_camera, route(), seed=20261109, scene='s_curve_left_right', max_steps=12)
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'record'
            events = []
            report, parent, camera = self.record(out, steps=12, progress=events.append)
            self.assertEqual([{k: r[k] for k in STRICT} for r in report['frames']],
                             [{k: r[k] for k in STRICT} for r in baseline['frames']])
            self.assertEqual(report['outcome'], baseline['outcome'])
            self.assertEqual(camera.calls, 12)
            self.assertEqual(parent.session.calls, 12)
            self.assertEqual(parent.session.pre_feature_values, list(map(float, range(12))))
            self.assertEqual(len(parent.trace), 12)
            self.assertIsNone(camera.raw_rgb_observer)
            self.assertEqual(events[-1]['status'], 'TRIAL_RECORDED')
            result = capture.verify_recording(out)
            self.assertTrue(result['recording_structure_valid'])
            self.assertFalse(result['origin_authenticated'])
            self.assertFalse(result['model_camera_qualified'])
            self.assertFalse(result['all_four_validation_tracks_passed'])

    def test_six_hundred_steps_keep_only_first_and_last_eight_packages(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'record'
            report, parent, camera = self.record(out, steps=600, lanes=long_route())
            manifest = json.loads((out / 'manifest.json').read_text())
            self.assertEqual(report['completed_steps'], 600)
            self.assertEqual(parent.session.calls, camera.calls)
            self.assertEqual(camera.calls, 600)
            self.assertEqual(manifest['retained_steps'], [1, 593, 594, 595, 596, 597, 598, 599, 600])
            self.assertEqual(len(manifest['steps']), 600)
            self.assertLessEqual(sum(p.stat().st_size for p in out.rglob('*') if p.is_file()), 335544320)
            self.assertEqual(capture.verify_recording(out)['retained_steps_verified'], 9)

    def test_uncertain_inference_retains_pre_state_without_inventing_post_state(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'record'
            report, parent, camera = self.record(out, steps=5, fail_on=3)
            self.assertEqual(report['actual_inference_bounds'], [2, 3])
            self.assertEqual(report['completed_steps'], 2)
            self.assertEqual(parent.session.calls, 3)
            manifest = json.loads((out / 'manifest.json').read_text())
            pending = manifest['steps'][-1]
            self.assertEqual(pending['phase'], 'INFERENCE_PENDING')
            self.assertIsNone(pending['post_state_sha256'])
            self.assertNotIn('post/state_feat_q', manifest['packages']['3']['blobs'])
            result = capture.verify_recording(out)
            self.assertEqual(result['recording_status'], 'PARTIAL')
            self.assertEqual(result['actual_inference_bounds'], [2, 3])
            self.assertIsNone(camera.raw_rgb_observer)

    def test_occupied_hook_is_not_replaced_and_original_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = inner_policy()
            camera = SourceCamera()
            marker = object()
            camera.raw_rgb_observer = marker
            with self.assertRaises(ValueError):
                capture.capture_full_s(WorldFramePolicyAdapter(parent, source_action_frame=SOURCE_ACTION_FRAME),
                    camera, route(), intrinsics=INTRINSICS, out=Path(temp)/'record', seed=20261109,
                    scene='s_curve_left_right', max_steps=3)
            self.assertIs(camera.raw_rgb_observer, marker)
            self.assertEqual(parent.session.calls, 0)
            out = Path(temp) / 'already'
            out.mkdir()
            (out / 'keep.txt').write_text('keep')
            with self.assertRaises((ValueError, FileExistsError)):
                self.record(out)
            self.assertEqual((out / 'keep.txt').read_text(), 'keep')

    def test_low_disk_stops_before_capture_and_creates_no_recording(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'record'
            with patch.object(capture.shutil, 'disk_usage', return_value=type('Usage', (), {'free': 1024})()):
                with self.assertRaises(ValueError):
                    self.record(out)
            self.assertFalse(out.exists())

    def test_corrupt_blobs_and_case_step_chain_report_swaps_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'record'
            self.record(out)
            path = out / 'manifest.json'
            original = json.loads(path.read_text())
            mutations = [
                lambda d: d.update(seed=20261110),
                lambda d: d['steps'][0].update(step=2),
                lambda d: d['steps'][1].update(pre_state_sha256='0'*64),
                lambda d: d.update(retained_steps=[2, 3]),
                lambda d: d['packages']['1']['blobs']['source/road'].update(path='../outside'),
                lambda d: d['packages']['1']['blobs']['source/road'].update(nbytes=999999999),
                lambda d: d['packages']['1']['blobs']['pre/state_feat_q'].update(dtype='object'),
            ]
            for mutate in mutations:
                bad = copy.deepcopy(original)
                mutate(bad)
                path.write_text(json.dumps(bad))
                with self.subTest(mutation=mutate), self.assertRaises((ValueError, OSError)):
                    capture.verify_recording(out)
            path.write_text(json.dumps(original))
            blob = out / original['packages']['1']['blobs']['source/road']['path']
            data = blob.read_bytes()
            blob.write_bytes(bytes([data[0] ^ 1]) + data[1:])
            with self.assertRaises(ValueError):
                capture.verify_recording(out)

    def test_hash_consistent_wrong_canvas_and_recurrent_state_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'record'
            self.record(out)
            manifest_path = out / 'manifest.json'
            original = json.loads(manifest_path.read_text())
            for key in ('canvas/road', 'pre/state_feat_q'):
                data = copy.deepcopy(original)
                desc = data['packages']['1']['blobs'][key]
                path = out / desc['path']
                raw = path.read_bytes()
                damaged = bytes([raw[0] ^ 1]) + raw[1:]
                path.write_bytes(damaged)
                desc['sha256'] = hashlib.sha256(damaged).hexdigest()
                manifest_path.write_text(json.dumps(data))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    capture.verify_recording(out)
                path.write_bytes(raw)
            manifest_path.write_text(json.dumps(original))
            self.assertTrue(capture.verify_recording(out)['recording_structure_valid'])

    def test_report_and_symlink_payload_swaps_cannot_certify_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'record'
            self.record(out)
            report = out / 'report.json'
            raw = report.read_bytes()
            data = json.loads(raw)
            data['frames'][0]['raw_model_action'][0] = 12.
            report.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                capture.verify_recording(out)
            report.write_bytes(raw)
            if os.name != 'nt':
                manifest = json.loads((out / 'manifest.json').read_text())
                blob = out / manifest['packages']['1']['blobs']['source/road']['path']
                saved = blob.read_bytes()
                blob.unlink()
                outside = Path(temp) / 'outside'
                outside.write_bytes(saved)
                blob.symlink_to(outside)
                with self.assertRaises(ValueError):
                    capture.verify_recording(out)

    def test_failed_serialization_keeps_original_report_and_does_not_publish_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'record'
            with patch.object(capture, '_write_blob', side_effect=OSError('disk write failure')):
                with self.assertRaises(OSError):
                    self.record(out)
            self.assertTrue((out / 'report.json').exists())
            self.assertFalse((out / 'manifest.json').exists())

    def test_unregistered_empty_directories_and_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'record'
            self.record(out)
            extra = out / 'unregistered'
            extra.mkdir()
            with self.assertRaises(ValueError):
                capture.verify_recording(out)
            extra.rmdir()
            path = out / 'manifest.json'
            text = path.read_text()
            path.write_text(text.replace('"seed": 20261109,', '"seed": 20261109, "seed": 20261109,', 1))
            with self.assertRaises(ValueError):
                capture.verify_recording(out)
            path.write_text(text)

    def test_plan_and_cold_help_never_need_native_dependencies(self):
        plan = capture.recording_plan()
        self.assertEqual(plan['complete_step_payload_bytes'], 25391024)
        self.assertEqual(plan['minimum_output_free_bytes'], 402653184)
        self.assertLess(plan['observer_payload_estimate_bytes'], 335544320)
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'plan'
            for arguments in (['--help'], ['plan', '--out', str(out)]):
                result = subprocess.run([sys.executable, '-I', '-S', '-B', str(ROOT/'scripts/full_s_failure_capture.py'), *arguments],
                    capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((out / 'plan.json').read_text())
            self.assertEqual(data['new_model_processes'], 0)
            self.assertFalse(data['execution_activated'])
            self.assertEqual(data['heavy_modules_loaded'], [])


if __name__ == '__main__':
    unittest.main()
