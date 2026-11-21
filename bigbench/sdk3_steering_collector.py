"""Opt-in evidence retention for an independently approved SDK3 diagnostic."""
import hashlib
import json
from pathlib import Path

import numpy as np

from bigbench.full_s_validation import route_state
from bigbench.preprocess_experiment import LiveInput, policy_class


def sha(data):
    return hashlib.sha256(data).hexdigest()


def array_bytes(value, shape, dtype):
    if value.shape != shape or value.dtype != np.dtype(dtype) or not np.isfinite(value).all():
        raise ValueError(f'invalid captured {dtype} array for {shape}')
    return value.tobytes(order='C')


class CaptureInput(LiveInput):
    """Preserve exactly the original observer's buffers inside the last 35 m."""

    def __init__(self, camera, intrinsics, variant, out, lanes):
        super().__init__(camera, intrinsics, variant, out)
        self.lanes = lanes
        self.active_lane = 0
        self.collect = False
        self.staged = None
        self.records = {}
        self.root = Path(out) / 'steering-evidence'
        self.root.mkdir()

    def capture(self, pose):
        if self.staged is not None:
            raise ValueError('previous selected inference was not finalized')
        state = route_state(self.lanes, self.active_lane, pose)
        self.active_lane = state['lane_index']
        self.collect = self.active_lane == 1 and 0 <= self.lanes[1].length - state['longitudinal_m'] <= 35
        return super().capture(pose)

    def prepare(self, road, wide):
        pending = self.pending
        tensor = super().prepare(road, wide)
        if self.collect:
            images, hashes = pending
            files = {f'{role}.rgb': array_bytes(images[role], (604, 964, 3), 'u1')
                     for role in ('road', 'wide')}
            if any(sha(files[f'{role}.rgb']) != hashes[role] for role in ('road', 'wide')):
                raise ValueError('original RGB hash mismatch')
            files['new_img.bin'] = array_bytes(tensor, (2, 6, 128, 256), 'u1')
            self.staged = (self.count, files)
        return tensor

    def record_outputs(self, outputs, audit):
        if self.staged is None:
            return
        step, files = self.staged
        files['action.bin'] = array_bytes(outputs['action'], (4,), '<f4')
        files['plan.bin'] = array_bytes(outputs['plan'], (990,), '<f4')
        digests = {name:sha(blob) for name,blob in files.items()}
        if digests['new_img.bin'] != audit['new_img_sha256']:
            raise ValueError('staged tensor does not match the actual inference receipt')
        if digests['action.bin'] != audit['raw_action_sha256']:
            raise ValueError('staged action does not match the actual inference receipt')
        folder = self.root / str(step)
        folder.mkdir()
        for name, blob in files.items():
            with (folder/name).open('xb') as stream:
                stream.write(blob)
        self.records[str(step)] = digests
        self.staged = None

def seal_capture_manifest(report_path, root, records):
    """Bind retained bytes to the final report after the launcher reaps its child."""
    blob = Path(report_path).read_bytes()
    trajectory = json.loads(blob)['trajectory']
    frames = trajectory['frames']
    straight_length = trajectory['geometry'][1]['length_m']
    selected = [current['step'] for previous,current in zip(frames,frames[1:])
                if previous['route']['lane_index'] == 1
                and 0 <= straight_length - previous['route']['longitudinal_m'] <= 35]
    if (not selected or frames[selected[-1]-1]['route']['lane_index'] != 2
            or selected != list(range(selected[0], selected[-1]+1))
            or set(records) != {str(step) for step in selected}):
        raise ValueError('incomplete connector capture window')
    for step in selected:
        frame = frames[step-1]
        digests = records[str(step)]
        mapping = {'road.rgb':'source_road_rgb_sha256','wide.rgb':'source_wide_rgb_sha256',
                   'new_img.bin':'new_img_sha256','action.bin':'raw_action_sha256'}
        if any(digests[file] != frame[key] for file,key in mapping.items()):
            raise ValueError(f'original report hash mismatch at step {step}')
    envelope = dict(format='mdv3-steering-evidence-v1',
                    report_sha256=sha(blob), steps=records)
    with (Path(root)/'manifest.json').open('x') as stream:
        json.dump(envelope,stream,indent=2)
        stream.write('\n')
    return selected


def capturing_policy_class():
    """Add one post-return observer to the existing model/preprocessing policy."""
    class CapturingPolicy(policy_class()):
        def step(self, observation):
            action = super().step(observation)
            self.preparer.record_outputs(self.last_model_outputs, self.audit_rows[-1])
            return action
    return CapturingPolicy
