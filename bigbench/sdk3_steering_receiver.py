"""Check a trial's retained evidence and emit world-space plan samples offline."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import stat
import sys
from types import SimpleNamespace

import cv2
import numpy as np

from bigbench.full_s_receipts import recorded_route, validate_trajectory
from bigbench.optical_calibration import PinholeIntrinsics, PinholeRectifier
from bigbench.preprocess_experiment import LiveInput
from bigbench.sdk3_steering_contract import VARIANT
from scripts.panda_sdk3_runtime import MODEL_SHA


FILE_LAYOUT = {
    'road.rgb': ('u1', (604, 964, 3)),
    'wide.rgb': ('u1', (604, 964, 3)),
    'new_img.bin': ('u1', (2, 6, 128, 256)),
    'action.bin': ('<f4', (4,)),
    'plan.bin': ('<f4', (990,)),
}
TIME_SECONDS = 10 * (np.arange(33) / 32)**2


def required(condition, message):
    if not condition:
        raise ValueError(message)


def read_bytes(path, limit, *, exact=False):
    try:
        status = path.lstat()
        required(stat.S_ISREG(status.st_mode) and status.st_size <= limit,
                 f'invalid regular file or extent: {path}')
        with path.open('rb') as stream:
            data = stream.read(limit + 1)
    except OSError as exc:
        raise ValueError(f'missing or unreadable evidence: {path}') from exc
    required(len(data) == status.st_size and (not exact or len(data) == limit),
             f'invalid evidence extent: {path}')
    return data


def selected_steps(report):
    trajectory = report['trajectory']
    frames = trajectory['frames']
    straight_length = trajectory['geometry'][1]['length_m']
    return [f['step'] for previous, f in zip(frames, frames[1:])
            if previous['route']['lane_index'] == 1
            and 0 <= straight_length - previous['route']['longitudinal_m'] <= 35]


def decode_plan(raw, input_pose):
    required(raw.shape == (990,) and raw.dtype == np.float32 and np.isfinite(raw).all(),
             'expected 990 finite float32 MD-V3 plan values')
    mean = raw[:495].reshape(33, 15)
    std = np.exp(np.minimum(raw[495:], np.float32(11))).reshape(33, 15)
    forward, right = mean[:, 0].astype(float), mean[:, 1].astype(float)
    c, s = math.cos(input_pose['heading']), math.sin(input_pose['heading'])
    xy = np.column_stack((input_pose['x'] + c*forward + s*right,
                          input_pose['y'] + s*forward - c*right))
    return mean, std, xy


def frame_evidence(folder, digests, report, step):
    required(folder.is_dir() and not folder.is_symlink(), 'step folder must be a real directory')
    required(digests.keys() == FILE_LAYOUT.keys(), 'invalid per-step file inventory')
    arrays = {}
    for name, (dtype, shape) in FILE_LAYOUT.items():
        size = np.dtype(dtype).itemsize * math.prod(shape)
        blob = read_bytes(folder/name, size, exact=True)
        required(hashlib.sha256(blob).hexdigest() == digests[name], f'hash mismatch: {folder/name}')
        arrays[name] = np.frombuffer(blob, dtype=dtype).reshape(shape)

    frame = report['trajectory']['frames'][step-1]
    feed = report['input_rows'][step-1]
    required(step == frame['step'] == feed['step'], 'wrong step binding')
    required(digests['new_img.bin'] == feed['actual_tensor_sha256'] == frame['new_img_sha256'],
             'retained tensor does not match the actual feed')
    required(digests['action.bin'] == frame['raw_action_sha256'], 'raw action receipt mismatch')
    images = {role: arrays[f'{role}.rgb'] for role in ('road', 'wide')}
    hashes = {role: digests[f'{role}.rgb'] for role in images}
    required(hashes == feed['source_sha256'], 'retained RGB does not match the camera receipt')
    intrinsics = {role: PinholeIntrinsics(**report['intrinsics'][role]) for role in images}
    pair, _ = PinholeRectifier().rectify_pair(images['road'], images['wide'],
                                            road_intrinsics=intrinsics['road'],
                                            wide_intrinsics=intrinsics['wide'])
    observed = [pair.road.sha256, pair.wide.sha256]
    required(observed == feed['canvas_sha256'], 'recomputed canvas hash mismatch')
    # Reuse the experiment's preprocessor while suppressing its initial capture
    # writer. This does not instantiate a real camera or a model.
    prepare = LiveInput(SimpleNamespace(), intrinsics, report['variant'], folder)
    prepare.count = 1
    prepare.record_native_rgb(images, hashes)
    prepare.expected = tuple(observed)
    rebuilt = prepare.prepare(pair.road, pair.wide)
    required(np.array_equal(rebuilt, arrays['new_img.bin']), 'input tensor recomputation mismatch')
    required(prepare.rows[-1]['baseline_tensor_sha256'] == feed['baseline_tensor_sha256'],
             'recomputed baseline hash mismatch')
    return arrays['plan.bin']


def receive(report_path, evidence):
    required((np.__version__, cv2.__version__) == ('2.4.6', '5.0.0'), 'matching NumPy/OpenCV required')
    required(evidence.is_dir() and not evidence.is_symlink(), 'missing evidence directory')
    manifest = json.loads(read_bytes(evidence/'manifest.json', 2*1024**2))
    required(manifest.get('format') == 'mdv3-steering-evidence-v1', 'unsupported evidence manifest')
    blob = read_bytes(report_path, 16*1024**2)
    required(manifest['report_sha256'] == hashlib.sha256(blob).hexdigest(), 'report SHA-256 mismatch')
    report = json.loads(blob)
    required(report['status']=='RETURNED' and report['protocol']=='sdk3-steering-plan-v1'
             and report['variant']==VARIANT and report['model_sha256']==MODEL_SHA
             and report['real_session'] is True and report['providers']==['CPUExecutionProvider']
             and report['ort_version']=='1.20.1' and report['provider_closed'] is True,
             'complete actual CPU model receipt required')
    trajectory = report['trajectory']
    validate_trajectory(trajectory, report['seed'], report['scenario'])

    steps = selected_steps(report)
    reached_entry = bool(steps and trajectory['frames'][steps[-1]-1]['route']['lane_index'] == 2)
    required(reached_entry and steps == list(range(steps[0], steps[-1]+1)),
             'trial does not cover a contiguous connector window through second-bend entry')
    files = manifest['steps']
    required(files.keys() == {str(step) for step in steps}, 'capture inventory misses or exceeds the registered window')
    _, straight, bend = recorded_route(trajectory['geometry'])
    bend_sign = bend.shape['direction']
    results = []
    for step in steps:
        plan = frame_evidence(evidence / str(step), files[str(step)], report, step)
        frame = trajectory['frames'][step-1]
        before = trajectory['frames'][step-2]
        pose = {'x': before['world_x_m'], 'y': before['world_y_m'], 'heading': before['heading_rad']}
        mean, std, xy = decode_plan(plan, pose)
        samples = []
        for i, point in enumerate(xy):
            s, right = straight.local_coordinates(point)
            segment = straight
            if s >= straight.length:
                segment = bend
                s, right = bend.local_coordinates(point)
            heading = pose['heading'] - float(mean[i, 11])
            tangent = segment.heading_theta_at(min(max(s, 0), segment.length))
            samples.append({'t_s': TIME_SECONDS[i], 'world_xy_m': point.tolist(),
                            'inside_offset_m': -bend_sign*right,
                            'heading_into_bend_change_rad': -bend_sign*float(mean[i,11]),
                            'inside_heading_error_rad': bend_sign*math.remainder(heading-tangent, 2*math.pi),
                            'lateral_std_body_m': float(std[i,1]),
                            'segment': 'straight' if segment is straight else 'second_bend',
                            'within_segment_extent': bool(0 <= s <= segment.length)})
        results.append({'step': step, 'input_pose_step': step-1,
                        'input_inside_offset_m': -bend_sign*before['route']['lateral_right_m'],
                        'input_inside_heading_error_rad': bend_sign*before['route']['heading_error_rad'],
                        'applied_inside_curvature_1pm': bend_sign*frame['applied_world_action']['curvature_1pm'],
                        'samples': samples})
    return {'status':'OBSERVATIONS_VERIFIED', 'run_id':report['run_id'], 'seed':report['seed'],
            'scenario':report['scenario'], 'new_inferences':0,
            'scope':'Internal evidence binding. Authenticate the source archive separately.',
            'observations':results}


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('report', type=Path)
    cli.add_argument('evidence', type=Path)
    args = cli.parse_args()
    try:
        result = receive(args.report, args.evidence)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        cli.exit(2, f'Evidence blocked: {exc}\n')
    print(json.dumps(result, allow_nan=False))
