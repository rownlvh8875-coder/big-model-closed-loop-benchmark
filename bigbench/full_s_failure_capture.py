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


def _states(parent):
    need(set(parent.state) == set(STATE), 'exact MD-V3 recurrent keys required')
    return {name: _snapshot(parent.state[name], *contract) for name, contract in STATE.items()}


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
    if phase in ('INFERENCE_PENDING', 'COMMITTED'):
        result.update({'pre/' + name: value for name, value in STATE.items()})
    if phase == 'COMMITTED':
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

    @property
    def last_source_rgb_sha256(self):
        return self.camera.last_source_rgb_sha256

    def record_native_rgb(self, images, hashes):
        need(self.raw is None and set(images) == set(hashes) == {'road', 'wide'},
             'one original source callback per capture required')
        raw = {role: _snapshot(images[role], [604, 964, 3], 'uint8') for role in ('road', 'wide')}
        need(all(sha(raw[role]) == hashes[role] for role in raw), 'source callback byte binding required')
        self.raw = raw

    def capture(self, state):
        from .image_adapter import camera_pair_to_model
        need(self.current is None and self.raw is None and len(self.steps) < 600, 'bounded sequential capture required')
        self.capture_calls += 1
        pair = self.camera.capture(state)
        need(self.raw is not None, 'original CPU source callback required')
        blobs = {'source/' + role: raw for role, raw in self.raw.items()}
        self.raw = None
        for role in ('road', 'wide'):
            frame = getattr(pair, role)
            need((frame.width, frame.height) == (512, 256) and len(frame.rgb) == 393216,
                 'original 512x256 RGB canvas required')
            blobs['canvas/' + role] = bytes(frame.rgb)
        blobs['new_img'] = _snapshot(camera_pair_to_model(pair.road, pair.wide), [2, 6, 128, 256], 'uint8')
        step = len(self.steps) + 1
        entry = dict(step=step, phase='CAPTURED', capture_pose=asdict(state),
            source_road_rgb_sha256=sha(blobs['source/road']), source_wide_rgb_sha256=sha(blobs['source/wide']),
            road_frame_sha256=sha(blobs['canvas/road']), wide_frame_sha256=sha(blobs['canvas/wide']),
            derived_new_img_sha256=sha(blobs['new_img']), actual_new_img_sha256=None,
            pre_state_sha256=None, post_state_sha256=None, raw_action_sha256=None)
        self.steps.append(entry)
        self.packages[step] = blobs
        self.current = step
        for old in set(self.packages) - set(_retained(step)):
            del self.packages[old]
        return pair

    def progress(self, payload):
        status = payload['status']
        if status == 'INFERENCE_PENDING':
            need(self.current is not None, 'capture before model state observation required')
            entry = self.steps[-1]
            states = _states(self.parent)
            self.packages[self.current].update({'pre/' + k: v for k, v in states.items()})
            entry.update(phase='INFERENCE_PENDING', pre_state_sha256=_state_digest(states))
        elif status == 'STEP_COMMITTED':
            need(self.current is not None and self.steps[-1]['phase'] == 'INFERENCE_PENDING', 'one committed inference required')
            entry = self.steps[-1]
            audit = self.parent.audit_rows[-1]
            states = _states(self.parent)
            raw = _snapshot(self.parent.last_model_outputs['action'], [4], 'float32')
            need(entry['derived_new_img_sha256'] == audit['new_img_sha256'] == self.parent.last_input_image_sha256,
                 'derived bytes must bind actual committed input digest')
            need(_state_digest(states) == audit['state_after_step_sha256'] and sha(raw) == audit['raw_action_sha256'],
                 'original action and recurrent audit binding required')
            self.packages[self.current].update({'post/' + k: v for k, v in states.items()})
            self.packages[self.current]['raw_action'] = raw
            entry.update(phase='COMMITTED', actual_new_img_sha256=audit['new_img_sha256'],
                         post_state_sha256=audit['state_after_step_sha256'], raw_action_sha256=sha(raw))
            self.current = None


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
    need(out.parent.is_dir() and shutil.disk_usage(out.parent).free >= recording_plan()['minimum_output_free_bytes'],
         '384MiB output headroom required before capture')
    out.mkdir(mode=0o700)
    recorder = _Recorder(policy.inner, camera)
    context = _context()
    camera.raw_rgb_observer = recorder
    def observe(payload):
        recorder.progress(payload)
        if progress is not None:
            progress(payload)
    try:
        report = run_full_s(policy, recorder, lanes, seed=seed, scene=scene, max_steps=max_steps, progress=observe)
    finally:
        camera.raw_rgb_observer = None
    report_raw = _json_bytes(report, REPORT_CAP)
    # Preserve the original result before any payload serialization can fail.
    with (out / 'report.json').open('xb') as stream:
        stream.write(report_raw)
    packages = {}
    total = len(report_raw)
    for step, blobs in sorted(recorder.packages.items()):
        phase = recorder.steps[step-1]['phase']
        contracts = _contracts(phase)
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
    manifest = dict(protocol='full-s-failure-recording-v1', seed=seed, scene=scene, max_steps=max_steps,
        intrinsics={k: asdict(v) for k, v in intrinsics.items()},
        intrinsics_provenance='CALLER_SUPPLIED_NOT_INDEPENDENTLY_ATTESTED',
        libraries=dict(numpy=np.__version__, opencv=cv2.__version__), source_context=context,
        report_sha256=sha(report_raw), steps=recorder.steps, retained_steps=_retained(len(recorder.steps)),
        packages=packages, capture_calls=recorder.capture_calls, payload_and_report_bytes=total,
        origin_authenticated=False, all_four_validation_tracks_passed=False,
        scope='Separate observed diagnostic; copies change wall timing/allocation. Parent states observed at step boundaries; non-image feeds are not intercepted session tensors. No extra steps after departure.')
    raw = _json_bytes(manifest, MANIFEST_CAP)
    need(total + len(raw) <= OUTPUT_CAP, 'total output cap required')
    _write_blob(out / 'manifest.json', raw)
    return report


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
    return json.loads(data, object_pairs_hook=_pairs,
                      parse_constant=lambda value: need(False, 'nonfinite JSON forbidden'))


def verify_recording(root):
    """Validate local structure/bytes, without authenticating external run origin."""
    import numpy as np
    import cv2
    from .camera import RGBFrame
    from .image_adapter import camera_pair_to_model
    from .optical_calibration import PinholeIntrinsics, PinholeRectifier
    root = Path(root).absolute()
    m = _decode(_read(root, 'manifest.json', MANIFEST_CAP))
    need(m.get('protocol') == 'full-s-failure-recording-v1' and m.get('source_context') == _context(), 'recording protocol/source context required')
    need(m.get('libraries') == dict(numpy=np.__version__, opencv=cv2.__version__), 'same image reader versions required')
    report_raw = _read(root, 'report.json', REPORT_CAP)
    need(sha(report_raw) == m.get('report_sha256'), 'original report byte binding required')
    r = _decode(report_raw)
    need((m.get('seed'), m.get('scene'), m.get('max_steps')) == (r.get('seed'), r.get('scenario'), r.get('max_steps')),
         'case and step limit report binding required')
    steps = m.get('steps')
    frames = r.get('frames')
    need(isinstance(steps, list) and isinstance(frames, list) and len(frames) == r.get('completed_steps')
         and 0 <= len(frames) <= len(steps) <= min(600, len(frames)+1), 'bounded committed/pending sequence required')
    n = len(frames)
    bounds = r.get('actual_inference_bounds')
    need(isinstance(bounds, list) and len(bounds) == 2 and all(type(v) is int for v in bounds) and
         bounds[0] == n and n <= bounds[1] <= min(600, n+1), 'original conservative inference bounds required')
    need(m.get('retained_steps') == _retained(len(steps)) and set(m.get('packages', {})) == {str(i) for i in _retained(len(steps))},
         'exact first and final-eight selection required')
    previous_post = None
    for index, entry in enumerate(steps, 1):
        need(type(entry.get('step')) is int and entry['step'] == index, 'ordered unique step required')
        phase = entry.get('phase')
        need(phase == 'COMMITTED' if index <= n else phase in ('CAPTURED', 'INFERENCE_PENDING'), 'explicit committed/pending phase required')
        expected_pose = r['initial_state'] if index == 1 else dict(t=frames[index-2]['time_s'], x=frames[index-2]['world_x_m'],
            y=frames[index-2]['world_y_m'], heading=frames[index-2]['heading_rad'], speed=frames[index-2]['speed_mps'])
        need(entry.get('capture_pose') == expected_pose, 'original pre-step pose binding required')
        if phase != 'CAPTURED':
            need(isinstance(entry.get('pre_state_sha256'), str) and (previous_post is None or entry['pre_state_sha256'] == previous_post),
                 'continuous parent recurrent state chain required')
        if index <= n:
            frame = frames[index-1]
            for key in ('source_road_rgb_sha256', 'source_wide_rgb_sha256', 'road_frame_sha256', 'wide_frame_sha256', 'raw_action_sha256'):
                need(entry.get(key) == frame.get(key), 'original per-step source/action binding required')
            need(entry.get('actual_new_img_sha256') == entry.get('derived_new_img_sha256') == frame.get('new_img_sha256') and
                 entry.get('post_state_sha256') == frame.get('state_after_step_sha256'), 'committed input/state binding required')
            need(sha(struct.pack('<4f', *frame['raw_model_action'])) == frame['raw_action_sha256'], 'original raw FP32 action bytes required')
            previous_post = entry['post_state_sha256']
        else:
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
        contracts = _contracts(entry['phase'])
        package = m['packages'][str(step)]
        need(set(package['blobs']) == set(contracts), 'exact phase payload keys required')
        data = {}
        for name, (shape, dtype) in contracts.items():
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
        arrays = {role: np.frombuffer(data['source/'+role], np.uint8).reshape(604, 964, 3) for role in ('road', 'wide')}
        pair, _ = PinholeRectifier().rectify_pair(arrays['road'], arrays['wide'],
            road_intrinsics=intrinsics['road'], wide_intrinsics=intrinsics['wide'])
        for role in ('road', 'wide'):
            need(getattr(pair, role).rgb == data['canvas/'+role] and
                 sha(data['source/'+role]) == entry['source_'+role+'_rgb_sha256'] and
                 sha(data['canvas/'+role]) == entry[role+'_frame_sha256'], 'exact retained source/warp/canvas binding required')
        packed = camera_pair_to_model(RGBFrame(512, 256, data['canvas/road']), RGBFrame(512, 256, data['canvas/wide'])).tobytes()
        need(packed == data['new_img'] and sha(packed) == entry['derived_new_img_sha256'], 'exact retained I420 binding required')
        for phase in ('pre', 'post'):
            if phase+'/state_img_q' in data:
                states = {name: data[phase+'/'+name] for name in STATE}
                need(_state_digest(states) == entry[phase+'_state_sha256'], 'typed recurrent snapshot/audit binding required')
                if step == 1 and phase == 'pre':
                    need(all(not any(value) for value in states.values()), 'initial parent reset state must be zero')
        if entry['phase'] == 'COMMITTED':
            need(sha(data['raw_action']) == entry['raw_action_sha256'], 'retained actual raw action required')
    need(total == m.get('payload_and_report_bytes') and total + (root/'manifest.json').stat().st_size <= OUTPUT_CAP,
         'exact bounded output accounting required')
    actual_paths = set()
    for parent, dirs, files in os.walk(root, followlinks=False):
        expected_dirs = {f'step-{step:06d}' for step in m['retained_steps']} if Path(parent) == root else set()
        need(set(dirs) == expected_dirs and all(not (Path(parent)/d).is_symlink() for d in dirs),
             'exact bounded nonsymlink recording directories required')
        for name in files:
            actual_paths.add((Path(parent)/name).relative_to(root).as_posix())
            need(len(actual_paths) <= 128, 'bounded recording namespace required')
    need(actual_paths == expected_paths, 'no missing or unregistered recording members')
    return dict(protocol='full-s-failure-recording-receiver-v1', recording_structure_valid=True,
        recording_status='COMPLETE' if r.get('trial_completed') is True else 'PARTIAL',
        completed_steps=n, retained_steps_verified=len(m['retained_steps']), actual_inference_bounds=bounds,
        origin_authenticated=False, model_camera_qualified=False, physical_optics_validated=False,
        carla_validated=False, hardware_gpu_qualified=False, all_four_validation_tracks_passed=False,
        new_model_processes=0, new_inferences=0, new_native_render_calls=0,
        scope='Local byte/association validation only; not original-run authenticity, baseline repeatability, causal model quality, or native qualification.')
