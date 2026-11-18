"""Opt-in CPU recording around the unchanged full-S loop; no native runner.

Observer copies/hashes change allocation and wall timing. Saved arrays prove
neither origin nor optics/model quality. Other feeds are not intercepted ORT
tensors. No original evidence or scientific producer is modified by this module.
"""
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
MIB = 1024**2
OUTPUT_CAP = 320 * MIB
MANIFEST_CAP = 4 * MIB
REPORT_CAP = 8 * MIB
STATE = {'state_img_q': ([2, 5, 6, 128, 256], 'uint8'),
         'state_desire_q': ([132, 1, 8], 'float32'),
         'state_feat_q': ([128, 1, 16384], 'float32')}
BASE = {'source/road': ([604, 964, 3], 'uint8'), 'source/wide': ([604, 964, 3], 'uint8'),
        'canvas/road': ([256, 512, 3], 'uint8'), 'canvas/wide': ([256, 512, 3], 'uint8'),
        'new_img': ([2, 6, 128, 256], 'uint8')}
SOURCES = ('bigbench/full_s_failure_capture.py', 'bigbench/full_s_validation.py',
    'bigbench/native_model_campaign.py', 'bigbench/metadrive_camera.py',
    'bigbench/optical_calibration.py', 'bigbench/image_adapter.py', 'bigbench/onnx_policy.py',
    'bigbench/model_world_frame.py', 'bigbench/kinematics.py',
    'scripts/native_mdv3_repeat_trial.py', 'model_specs/md-v3.json')


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _extent(shape, dtype):
    return math.prod(shape) * (1 if dtype == 'uint8' else 4)


def recording_plan():
    state = sum(_extent(*v) for v in STATE.values())
    step = sum(_extent(*v) for v in BASE.values()) + 2 * state + 16
    return dict(protocol='full-s-failure-recording-plan-v1', max_steps=600, tail_steps=8,
        max_retained_packages=9, complete_step_payload_bytes=step,
        observer_payload_estimate_bytes=12 * step + MANIFEST_CAP,
        output_cap_bytes=OUTPUT_CAP, minimum_output_free_bytes=384 * MIB,
        hypothetical_eight_trial_reserve_bytes=3 * 1024**3,
        execution_activated=False, new_model_processes=0, new_inferences=0,
        heavy_modules_loaded=_heavy(),
        scope='Preparation only. Payload accounting excludes model/native allocations and Python overhead. No whole-RSS or hardware qualification.')


def _heavy():
    return sorted(n for n in sys.modules if n.split('.')[0] in ('panda3d', 'direct', 'metadrive', 'onnxruntime', 'carla'))


def _context():
    return {name: sha((ROOT / name).read_bytes()) for name in SOURCES}


def _retained(n):
    return sorted({1} | set(range(max(1, n - 7), n + 1))) if n else []


def _snapshot(value, shape, dtype):
    import numpy as np
    need(isinstance(value, np.ndarray) and list(value.shape) == shape and
         value.dtype == np.dtype(dtype) and value.flags.c_contiguous,
         'exact bounded array shape/dtype/layout required')
    need(bool(np.all(np.isfinite(value))), 'finite array required')
    return value.tobytes(order='C')


def _states(parent, sink=None, prefix=''):
    need(set(parent.state) == set(STATE), 'exact MD-V3 recurrent keys required')
    result = {}
    for name, contract in STATE.items():
        result[name] = _snapshot(parent.state[name], *contract)
        if sink is not None:
            sink[prefix+name] = result[name]
    return result


class RecordingFailure(RuntimeError):
    """Available result/bounds survive even if the evidence sink fails."""
    def __init__(self, message, report, bounds, recording):
        super().__init__(message)
        self.report, self.inference_bounds, self.recording = report, bounds, recording


class RecordingWriteError(OSError):
    def __init__(self, message, report, bounds, recording):
        super().__init__(message)
        self.report, self.inference_bounds, self.recording = report, bounds, recording


def _state_digest(values):
    digest = hashlib.sha256()
    for name, data in sorted(values.items()):
        shape, dtype = STATE[name]
        digest.update(name.encode() + b'\0' + dtype.encode() + b'\0')
        digest.update(json.dumps(shape, separators=(',', ':')).encode() + b'\0')
        digest.update(data)
    return digest.hexdigest()


def _json_bytes(value, cap):
    raw = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    need(len(raw) <= cap, 'bounded JSON required')
    return raw


def _write_blob(path, data):
    with path.open('xb') as stream:
        stream.write(data)


def _contracts(phase):
    result = dict(BASE)
    if phase in ('INFERENCE_PENDING', 'AUDITED', 'COMMITTED'):
        result.update({'pre/' + name: value for name, value in STATE.items()})
    if phase in ('AUDITED', 'COMMITTED'):
        result.update({'post/' + name: value for name, value in STATE.items()})
        result['raw_action'] = ([4], 'float32')
    return result


def _blob_path(step, name):
    return f'step-{step:06d}/' + name.replace('/', '-') + '.bin'


class _Recorder:
    def __init__(self, parent, camera):
        self.parent, self.camera = parent, camera
        self.steps, self.packages = [], {}
        self.raw = None
        self.current = None
        self.capture_calls = 0
        self.errors = []

    def failure(self, exc, stage):
        message = stage + ': ' + type(exc).__name__ + ': ' + str(exc)[:1200]
        self.errors.append(message)
        if self.steps:
            self.steps[-1]['snapshot_errors'].append(message)

    @property
    def last_source_rgb_sha256(self):
        return self.camera.last_source_rgb_sha256

    def record_native_rgb(self, images, hashes):
        need(self.raw is None and set(images) == set(hashes) == {'road', 'wide'},
             'one original source callback per capture required')
        self.raw = {}
        for role in ('road', 'wide'):
            raw = _snapshot(images[role], [604, 964, 3], 'uint8')
            need(sha(raw) == hashes[role], 'source callback byte binding required')
            self.raw[role] = raw
            self.packages[self.current]['source/'+role] = raw
            self.steps[-1]['source_'+role+'_rgb_sha256'] = sha(raw)

    def capture(self, state):
        from .image_adapter import camera_pair_to_model
        need(self.current is None and self.raw is None and len(self.steps) < 600, 'bounded sequential capture required')
        self.capture_calls += 1
        step = len(self.steps) + 1
        entry = dict(step=step, phase='CAPTURE_FAILED', capture_pose=asdict(state),
            source_road_rgb_sha256=None, source_wide_rgb_sha256=None,
            road_frame_sha256=None, wide_frame_sha256=None,
            derived_new_img_sha256=None, actual_new_img_sha256=None,
            pre_state_sha256=None, post_state_sha256=None, raw_action_sha256=None,
            snapshot_errors=[], frame_committed=False, audit_available=False,
            pre_snapshot_attempted=False, post_snapshot_attempted=False)
        self.steps.append(entry)
        self.packages[step] = blobs = {}
        self.current = step
        for old in set(self.packages) - set(_retained(step)):
            del self.packages[old]
        try:
            pair = self.camera.capture(state)
            need(self.raw is not None, 'original CPU source callback required')
        except Exception as exc:
            if self.raw is not None:
                blobs.update({'source/'+role: raw for role, raw in self.raw.items()})
                self.raw = None
            self.failure(exc, 'capture')
            raise RuntimeError(self.errors[-1]) from exc
        blobs.update({'source/' + role: raw for role, raw in self.raw.items()})
        self.raw = None
        for role in ('road', 'wide'):
            frame = getattr(pair, role)
            need((frame.width, frame.height) == (512, 256) and len(frame.rgb) == 393216,
                 'original 512x256 RGB canvas required')
            blobs['canvas/' + role] = bytes(frame.rgb)
        blobs['new_img'] = _snapshot(camera_pair_to_model(pair.road, pair.wide), [2, 6, 128, 256], 'uint8')
        entry.update(phase='CAPTURED',
            source_road_rgb_sha256=sha(blobs['source/road']), source_wide_rgb_sha256=sha(blobs['source/wide']),
            road_frame_sha256=sha(blobs['canvas/road']), wide_frame_sha256=sha(blobs['canvas/wide']),
            derived_new_img_sha256=sha(blobs['new_img']), actual_new_img_sha256=None,
            pre_state_sha256=None, post_state_sha256=None, raw_action_sha256=None)
        return pair

    def audited(self, phase):
        entry = self.steps[-1]
        audit = self.parent.audit_rows[entry['step']-1]
        entry.update(phase=phase, audit_available=True,
            actual_new_img_sha256=audit['new_img_sha256'], post_state_sha256=audit['state_after_step_sha256'],
            raw_action_sha256=audit['raw_action_sha256'])
        need(entry['derived_new_img_sha256'] == audit['new_img_sha256'] == self.parent.last_input_image_sha256,
             'derived bytes must bind actual committed input digest')
        blobs = self.packages[entry['step']]
        raw = _snapshot(self.parent.last_model_outputs['action'], [4], 'float32')
        blobs['raw_action'] = raw
        need(sha(raw) == audit['raw_action_sha256'], 'original raw action audit binding required')
        entry['post_snapshot_attempted'] = True
        states = _states(self.parent, blobs, 'post/')
        need(_state_digest(states) == audit['state_after_step_sha256'], 'original recurrent audit binding required')
        self.current = None

    def progress(self, payload):
        status = payload['status']
        if status == 'INFERENCE_PENDING':
            need(self.current is not None, 'capture before model state observation required')
            entry = self.steps[-1]
            entry.update(phase='INFERENCE_PENDING', pre_snapshot_attempted=True)
            states = _states(self.parent, self.packages[self.current], 'pre/')
            entry.update(pre_state_sha256=_state_digest(states))
        elif status == 'STEP_COMMITTED':
            need(self.current is not None and self.steps[-1]['phase'] == 'INFERENCE_PENDING', 'one committed inference required')
            self.steps[-1]['frame_committed'] = True
            self.audited('COMMITTED')

    def finish(self, report):
        for entry in self.steps:
            entry['frame_committed'] = entry['step'] <= len(report['frames'])
            entry['audit_available'] = entry['step'] <= len(report['inference_audit_rows'])
        if self.current is not None and self.steps[-1]['audit_available']:
            entry = self.steps[-1]
            if not entry['post_snapshot_attempted']:
                try:
                    self.audited('COMMITTED' if entry['frame_committed'] else 'AUDITED')
                except Exception as exc:
                    self.failure(exc, 'final audited snapshot')
        if self.steps and self.steps[-1]['phase'] == 'CAPTURE_FAILED' and not self.steps[-1]['snapshot_errors']:
            self.failure(ValueError(report.get('error', 'incomplete original capture')), 'capture payload')


def capture_full_s(policy, camera, lanes, *, intrinsics, out, seed, scene, max_steps=600, progress=None):
    """Integration helper only; caller owns native admission, creation and cleanup.

    No additional reset/step/capture. Errors during recording are incomplete
    diagnostics, never traversal certification. Serialization follows the loop.
    """
    from .full_s_validation import run_full_s
    from .model_world_frame import WorldFramePolicyAdapter
    from .optical_calibration import PinholeIntrinsics
    import numpy as np
    import cv2
    need(type(policy) is WorldFramePolicyAdapter, 'original single frame adapter required')
    need(getattr(camera, 'raw_rgb_observer', None) is None and hasattr(camera, 'raw_rgb_observer'), 'unoccupied CPU source hook required')
    need(type(seed) is int and seed in (20261109, 20261110) and scene in ('s_curve_left_right', 's_curve_right_left')
         and type(max_steps) is int and 2 <= max_steps <= 600, 'registered bounded full-S case required')
    need(set(intrinsics) == {'road', 'wide'} and all(isinstance(v, PinholeIntrinsics) for v in intrinsics.values()),
         'caller-measured pinhole intrinsics required')
    need(policy.inner.contract.sha256 == '35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199',
         'registered MD-V3 contract required')
    out = Path(out)
    need(not out.exists() and not out.is_symlink(), 'fresh recording output required')
    need(all(not p.is_symlink() for p in out.absolute().parents), 'symlink output ancestors forbidden')
    need(out.parent.is_dir() and shutil.disk_usage(out.parent).free >= recording_plan()['minimum_output_free_bytes'],
         '384MiB output headroom required before capture')
    out.mkdir(mode=0o700)
    recorder = _Recorder(policy.inner, camera)
    context = _context()
    camera.raw_rgb_observer = recorder
    callback_failed = False
    def observe(payload):
        nonlocal callback_failed
        try:
            recorder.progress(payload)
        except Exception as exc:
            recorder.failure(exc, 'observer '+payload['status'])
            if payload['status'] != 'TRIAL_RECORDED':
                raise RuntimeError(recorder.errors[-1]) from exc
        if progress is not None and not callback_failed:
            try:
                progress(payload)
            except Exception as exc:
                callback_failed = True
                recorder.failure(exc, 'lifecycle '+payload['status'])
                if payload['status'] != 'TRIAL_RECORDED':
                    raise RuntimeError(recorder.errors[-1]) from exc
    report = None
    escaped = None
    try:
        report = run_full_s(policy, recorder, lanes, seed=seed, scene=scene, max_steps=max_steps, progress=observe)
    except Exception as exc:
        escaped = exc
        recorder.failure(exc, 'original report unavailable')
    finally:
        camera.raw_rgb_observer = None
    if escaped is None:
        recorder.finish(report)
        stored, bounds = report, report['actual_inference_bounds']
    else:
        lower = len(policy.inner.audit_rows)
        pending = bool(recorder.steps and recorder.steps[-1]['phase'] == 'INFERENCE_PENDING'
                       and lower < len(recorder.steps))
        bounds = [lower, min(max_steps, lower+int(pending))]
        committed = sum(entry['frame_committed'] for entry in recorder.steps)
        recorder.finish(dict(frames=[None]*committed,
            inference_audit_rows=policy.inner.audit_rows, error=str(escaped)))
        stored = dict(protocol='original-full-s-report-unavailable-v1',
            original_report_available=False, actual_inference_bounds=bounds,
            completed_rows=committed, error=type(escaped).__name__+': '+str(escaped)[:1200])
    try:
        manifest = _save_recording(out, stored, report is not None, recorder, context,
            intrinsics, seed, scene, max_steps, np.__version__, cv2.__version__)
    except (OSError, ValueError) as exc:
        raise RecordingWriteError(str(exc), report, bounds, dict(recording_errors=recorder.errors)) from exc
    if recorder.errors:
        raise RecordingFailure('; '.join(recorder.errors), report, bounds, manifest) from escaped
    return report


def _save_recording(out, report, original_available, recorder, context, intrinsics, seed, scene, max_steps, numpy_version, cv_version):
    report_raw = _json_bytes(report, REPORT_CAP)
    # Preserve the original result before any payload serialization can fail.
    with (out / ('report.json' if original_available else 'abort.json')).open('xb') as stream:
        stream.write(report_raw)
    packages = {}
    total = len(report_raw)
    for step, blobs in sorted(recorder.packages.items()):
        phase = recorder.steps[step-1]['phase']
        contracts = _contracts(phase)
        entry = recorder.steps[step-1]
        if entry['snapshot_errors']:
            need(set(blobs) <= set(contracts), 'only typed known partial snapshots required')
        else:
            need(set(blobs) == set(contracts), 'partial recording has explicit complete phase payloads')
        package = {'blobs': {}}
        (out / f'step-{step:06d}').mkdir()
        for name, data in blobs.items():
            shape, dtype = contracts[name]
            need(len(data) == _extent(shape, dtype), 'typed snapshot extent required')
            total += len(data)
            need(total + MANIFEST_CAP <= OUTPUT_CAP, 'recording output byte cap before write')
            relative = _blob_path(step, name)
            _write_blob(out / relative, data)
            package['blobs'][name] = dict(path=relative, shape=shape, dtype=dtype, nbytes=len(data), sha256=sha(data))
        packages[str(step)] = package
    manifest = dict(protocol='full-s-failure-recording-v1' if original_available else 'full-s-aborted-failure-recording-v1',
        original_report_available=original_available, recording_errors=recorder.errors,
        seed=seed, scene=scene, max_steps=max_steps,
        intrinsics={k: asdict(v) for k, v in intrinsics.items()},
        intrinsics_provenance='CALLER_SUPPLIED_NOT_INDEPENDENTLY_ATTESTED',
        libraries=dict(numpy=numpy_version, opencv=cv_version), source_context=context,
        report_sha256=sha(report_raw), steps=recorder.steps, retained_steps=_retained(len(recorder.steps)),
        packages=packages, capture_calls=recorder.capture_calls, payload_and_report_bytes=total,
        origin_authenticated=False, all_four_validation_tracks_passed=False,
        scope='Separate observed diagnostic; copies change wall timing/allocation. Parent states observed at step boundaries; non-image feeds are not intercepted session tensors. No extra steps after departure.')
    raw = _json_bytes(manifest, MANIFEST_CAP)
    need(total + len(raw) <= OUTPUT_CAP, 'total output cap required')
    _write_blob(out / 'manifest.json', raw)
    return manifest


def _read(root, name, limit):
    need(isinstance(name, str) and '\\' not in name and ':' not in name and
         not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts, 'canonical evidence path required')
    path = root / name
    need(all(not p.is_symlink() for p in (path, *path.parents)), 'symlink evidence forbidden')
    info = path.stat()
    need(stat.S_ISREG(info.st_mode) and 0 <= info.st_size <= limit, 'bounded regular evidence file required')
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    need(len(data) <= limit and len(data) == info.st_size, 'bounded stable evidence snapshot required')
    return data


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate JSON keys forbidden')
        result[key] = value
    return result


def _decode(data):
    def finite_float(value):
        number = float(value)
        need(math.isfinite(number), 'finite JSON float required')
        return number
    return json.loads(data, object_pairs_hook=_pairs,
                      parse_float=finite_float,
                      parse_constant=lambda value: need(False, 'nonfinite JSON forbidden'))


def _namespace(root, expected_paths, retained):
    """Reject unexpected entries while streaming; never list an entire directory."""
    actual = set()
    expected_dirs = {f'step-{step:06d}' for step in retained}
    with os.scandir(root) as entries:
        found_dirs = set()
        for entry in entries:
            need(not entry.is_symlink(), 'symlink recording member forbidden')
            if entry.name in expected_dirs:
                need(entry.is_dir(follow_symlinks=False), 'step directory required')
                found_dirs.add(entry.name)
            else:
                need(entry.name in expected_paths and entry.is_file(follow_symlinks=False), 'unexpected recording entry')
                actual.add(entry.name)
            need(len(actual)+len(found_dirs) <= 128, 'bounded recording namespace required')
    need(found_dirs == expected_dirs, 'all retained step directories required')
    for name in expected_dirs:
        with os.scandir(root/name) as entries:
            for entry in entries:
                relative = name+'/'+entry.name
                need(relative in expected_paths and not entry.is_symlink() and entry.is_file(follow_symlinks=False),
                     'unexpected step member')
                actual.add(relative)
                need(len(actual) <= 128, 'bounded recording namespace required')
    need(actual == expected_paths, 'no missing or unregistered recording members')


def verify_recording(root):
    """Validate local structure/bytes, without authenticating external run origin."""
    import numpy as np
    import cv2
    from .camera import RGBFrame
    from .image_adapter import camera_pair_to_model
    from .optical_calibration import PinholeIntrinsics, PinholeRectifier
    from .model_world_frame import basis_receipt
    root = Path(root).absolute()
    m = _decode(_read(root, 'manifest.json', MANIFEST_CAP))
    need(m.get('protocol') == 'full-s-failure-recording-v1' and m.get('source_context') == _context(), 'recording protocol/source context required')
    need(m.get('original_report_available') is True and isinstance(m.get('recording_errors'), list) and
         all(isinstance(v, str) for v in m['recording_errors']), 'explicit original-report/error status required')
    need(m.get('libraries') == dict(numpy=np.__version__, opencv=cv2.__version__), 'same image reader versions required')
    report_raw = _read(root, 'report.json', REPORT_CAP)
    need(sha(report_raw) == m.get('report_sha256'), 'original report byte binding required')
    r = _decode(report_raw)
    need((m.get('seed'), m.get('scene'), m.get('max_steps')) == (r.get('seed'), r.get('scenario'), r.get('max_steps')),
         'case and step limit report binding required')
    need(r.get('protocol') == 'full-s-closed-loop-v1' and type(r.get('seed')) is int and
         r['seed'] in (20261109, 20261110) and r.get('scenario') in ('s_curve_left_right', 's_curve_right_left') and
         type(r.get('max_steps')) is int and 2 <= r['max_steps'] <= 600 and
         r.get('model_sha256') == '35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199',
         'registered full-S report/model/condition required')
    need(type(r.get('trial_completed')) is bool and type(r.get('model_test_double')) is bool and
         type(r.get('injected_session')) is bool and r.get('ground_truth_control_used') is False and
         r.get('model_scoring_allowed') is False and r.get('real_vehicle_testing') is False and
         type(r.get('pixel_tolerance')) is int and r['pixel_tolerance'] == 0 and
         type(r.get('extra_render_tasks')) is int and r['extra_render_tasks'] == 0,
         'original no-tuning/no-extra-render protocol flags required')
    steps = m.get('steps')
    frames = r.get('frames')
    need(isinstance(steps, list) and isinstance(frames, list) and len(frames) == r.get('completed_steps')
         and 0 <= len(frames) <= len(steps) <= min(r['max_steps'], len(frames)+1), 'bounded committed/pending sequence required')
    n = len(frames)
    bounds = r.get('actual_inference_bounds')
    audits, bridges = r.get('inference_audit_rows'), r.get('bridge_receipts')
    need(isinstance(bounds, list) and len(bounds) == 2 and all(type(v) is int for v in bounds) and
         isinstance(audits, list) and isinstance(bridges, list) and bounds[0] == len(audits) and
         n <= bounds[0] <= bounds[1] <= min(r['max_steps'], n+1) and n <= len(bridges) <= len(audits),
         'original conservative inference bounds and audit counts required')
    need(type(m.get('capture_calls')) is int and m['capture_calls'] == len(steps) and len(steps) >= bounds[1],
         'every known pending/audited capture attempt must remain present')
    need(m.get('retained_steps') == _retained(len(steps)) and set(m.get('packages', {})) == {str(i) for i in _retained(len(steps))},
         'exact first and final-eight selection required')
    previous_post = None
    for index, entry in enumerate(steps, 1):
        need(type(entry.get('step')) is int and entry['step'] == index, 'ordered unique step required')
        phase = entry.get('phase')
        audited = index <= len(audits)
        need(phase == ('COMMITTED' if index <= n else 'AUDITED') if audited else
             phase in ('CAPTURE_FAILED', 'CAPTURED', 'INFERENCE_PENDING'), 'explicit observation/audit/frame phase required')
        need(type(entry.get('frame_committed')) is bool and entry['frame_committed'] == (index <= n) and
             type(entry.get('audit_available')) is bool and entry['audit_available'] == audited and
             isinstance(entry.get('snapshot_errors'), list), 'separate frame/audit/snapshot milestones required')
        if index > n and not audited and bounds[1] > bounds[0]:
            need(phase == 'INFERENCE_PENDING', 'uncertain inference requires its pending attempt')
        expected_pose = r['initial_state'] if index == 1 else dict(t=frames[index-2]['time_s'], x=frames[index-2]['world_x_m'],
            y=frames[index-2]['world_y_m'], heading=frames[index-2]['heading_rad'], speed=frames[index-2]['speed_mps'])
        need(entry.get('capture_pose') == expected_pose, 'original pre-step pose binding required')
        if entry.get('pre_state_sha256') is not None:
            need(isinstance(entry.get('pre_state_sha256'), str) and (previous_post is None or entry['pre_state_sha256'] == previous_post),
                 'continuous parent recurrent state chain required')
        else:
            need(phase in ('CAPTURE_FAILED', 'CAPTURED') or entry['snapshot_errors'], 'missing pre-state must be an explicit observation failure')
        if audited:
            audit = audits[index-1]
            need(entry.get('actual_new_img_sha256') == entry.get('derived_new_img_sha256') == audit.get('new_img_sha256') and
                 entry.get('post_state_sha256') == audit.get('state_after_step_sha256') and
                 entry.get('raw_action_sha256') == audit.get('raw_action_sha256') and
                 sha(struct.pack('<4f', *audit['raw_model_action'])) == audit['raw_action_sha256'],
                 'original completed audit must bind actual input/raw action/state')
            previous_post = entry['post_state_sha256']
        if index <= n:
            frame = frames[index-1]
            bridge = bridges[index-1]
            need(type(frame.get('step')) is int and frame['step'] == index and type(bridge.get('step')) is int and bridge['step'] == index and
                 all(frame.get(k) == audits[index-1].get(k) for k in
                     ('new_img_sha256', 'raw_model_action', 'raw_action_sha256', 'state_after_step_sha256')) and
                 frame.get('parent_model_action') == bridge.get('parent_model_action') and
                 frame.get('applied_world_action') == bridge.get('applied_world_action') and
                 all(bridge.get(k) == v for k, v in basis_receipt().items()), 'original frame/audit/bridge association required')
            for key in ('source_road_rgb_sha256', 'source_wide_rgb_sha256', 'road_frame_sha256', 'wide_frame_sha256', 'raw_action_sha256'):
                need(entry.get(key) == frame.get(key), 'original per-step source/action binding required')
            need(entry.get('actual_new_img_sha256') == entry.get('derived_new_img_sha256') == frame.get('new_img_sha256') and
                 entry.get('post_state_sha256') == frame.get('state_after_step_sha256'), 'committed input/state binding required')
            need(sha(struct.pack('<4f', *frame['raw_model_action'])) == frame['raw_action_sha256'], 'original raw FP32 action bytes required')
        elif not audited:
            need(entry.get('post_state_sha256') is None and entry.get('actual_new_img_sha256') is None and
                 entry.get('raw_action_sha256') is None, 'unknown inference must not invent post-state or action')
    if r.get('trial_completed') is True:
        need(len(steps) == n and bounds == [n, n], 'complete trial cannot contain pending inference')
    expected_paths = {'manifest.json', 'report.json'}
    total = len(report_raw)
    intrinsics = {k: PinholeIntrinsics(**v) for k, v in m['intrinsics'].items()}
    need(set(intrinsics) == {'road', 'wide'}, 'two lens intrinsics required')
    for step in m['retained_steps']:
        entry = steps[step-1]
        for name in m['packages'][str(step)]['blobs']:
            need(name in _contracts(entry['phase']), 'only registered snapshot names permitted')
            expected_paths.add(_blob_path(step, name))
    _namespace(root, expected_paths, m['retained_steps'])
    missing = []
    for step in m['retained_steps']:
        entry = steps[step-1]
        contracts = _contracts(entry['phase'])
        package = m['packages'][str(step)]
        absent = set(contracts) - set(package['blobs'])
        need(not absent or entry['snapshot_errors'], 'missing snapshots require explicit observation error')
        need(set(package['blobs']) <= set(contracts), 'exact phase payload keys required')
        missing.extend(f'{step}:{name}' for name in sorted(absent))
        data = {}
        for name, (shape, dtype) in contracts.items():
            if name not in package['blobs']:
                continue
            desc = package['blobs'][name]
            path = _blob_path(step, name)
            size = _extent(shape, dtype)
            need(desc.get('path') == path and desc.get('shape') == shape and desc.get('dtype') == dtype and
                 type(desc.get('nbytes')) is int and desc['nbytes'] == size, 'canonical bounded typed payload required')
            raw = _read(root, path, size)
            need(len(raw) == size and sha(raw) == desc.get('sha256'), 'payload byte digest required')
            need(bool(np.all(np.isfinite(np.frombuffer(raw, dtype=dtype)))), 'finite saved tensor required')
            data[name] = raw
            total += size
            expected_paths.add(path)
        if set(BASE) <= set(data):
            arrays = {role: np.frombuffer(data['source/'+role], np.uint8).reshape(604, 964, 3) for role in ('road', 'wide')}
            pair, _ = PinholeRectifier().rectify_pair(arrays['road'], arrays['wide'],
                road_intrinsics=intrinsics['road'], wide_intrinsics=intrinsics['wide'])
            for role in ('road', 'wide'):
                need(getattr(pair, role).rgb == data['canvas/'+role] and
                     sha(data['source/'+role]) == entry['source_'+role+'_rgb_sha256'] and
                     sha(data['canvas/'+role]) == entry[role+'_frame_sha256'], 'exact retained source/warp/canvas binding required')
            packed = camera_pair_to_model(RGBFrame(512, 256, data['canvas/road']), RGBFrame(512, 256, data['canvas/wide'])).tobytes()
            need(packed == data['new_img'] and sha(packed) == entry['derived_new_img_sha256'], 'exact retained I420 binding required')
        else:
            need(entry['phase'] == 'CAPTURE_FAILED' and entry['snapshot_errors'], 'incomplete capture must be explicit')
        for phase in ('pre', 'post'):
            if all(phase+'/'+name in data for name in STATE):
                states = {name: data[phase+'/'+name] for name in STATE}
                need(_state_digest(states) == entry[phase+'_state_sha256'], 'typed recurrent snapshot/audit binding required')
                if step == 1 and phase == 'pre':
                    need(all(not any(value) for value in states.values()), 'initial parent reset state must be zero')
        if 'raw_action' in data:
            need(sha(data['raw_action']) == entry['raw_action_sha256'], 'retained actual raw action required')
    need(total == m.get('payload_and_report_bytes') and total + (root/'manifest.json').stat().st_size <= OUTPUT_CAP,
         'exact bounded output accounting required')
    return dict(protocol='full-s-failure-recording-receiver-v1', recording_structure_valid=True,
        recording_status='COMPLETE' if r.get('trial_completed') is True and not m.get('recording_errors') and not missing else 'PARTIAL',
        recording_errors=m.get('recording_errors'), missing_snapshot_blobs=missing,
        completed_steps=n, retained_steps_verified=len(m['retained_steps']), actual_inference_bounds=bounds,
        origin_authenticated=False, model_camera_qualified=False, physical_optics_validated=False,
        carla_validated=False, hardware_gpu_qualified=False, all_four_validation_tracks_passed=False,
        new_model_processes=0, new_inferences=0, new_native_render_calls=0,
        scope='Local byte/association validation only; not original-run authenticity, baseline repeatability, causal model quality, or native qualification.')
