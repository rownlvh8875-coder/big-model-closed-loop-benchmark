"""Owned Linux SDK3 entry for native ramp camera probes and official model trials."""

import argparse
from contextlib import ExitStack
from dataclasses import asdict
import math
import os
from pathlib import Path
import secrets
import sys
from time import perf_counter_ns

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bigbench.curved_lane_scenarios import SCENARIOS
from bigbench.full_s_validation import need, route_state
from bigbench.recorded_official_execution import clone
from bigbench.sdk3_native_ramp import (
    CHILD_LIMIT_S, DT, MAX_STEPS, SCENES, SEEDS, SPEED, START_FRACTION, camera_pose,
    describe, registered_lanes, run_ramp,
)
from scripts import panda_sdk3_diagnostic as owner
from scripts.sdk3_four_validation_native import bootstrap
from scripts.sdk3_four_validation_trial import atomic_json, driver_info, rate_admission
from scripts.sdk3_sidewalk_full_s import INPUT_VARIANT, OFFICIAL_MODELS, open_official_policy, retained_file


def probe(provider, lanes, inputs, out, receipt):
    import cv2
    import numpy as np
    from scripts.sdk3_wide_capture_native import CameraTiming
    from scripts.verify_sdk3_wide_capture import verify_timing

    receipt.update(probe_rows=[], libraries=dict(numpy=np.__version__, opencv=cv2.__version__))
    need(receipt['libraries'] == {'numpy': '2.4.6', 'opencv': '5.0.0'}, 'pinned camera preprocessing versions')
    fractions = (START_FRACTION, .5, .5, .5, .9)
    with ExitStack() as stack:
        timing = CameraTiming(provider, stack)
        previous_end = 0
        for index, (lane, fraction) in enumerate(zip(lanes, fractions)):
            step = index + 1
            pose = camera_pose(lane, fraction, index * DT)
            truth = route_state(lanes, index, pose)
            need(truth['intrusion_m'] == 0. and truth['lane_index'] == index, 'each native lane probe is in bounds')
            timing.events = []
            receipt['camera_attempts'] += 1
            begin = perf_counter_ns()
            pair = inputs.capture(pose)
            end = perf_counter_ns()
            rgb, _ = inputs.pending
            tensor = inputs.prepare(pair.road, pair.wide)
            prepared = perf_counter_ns()
            need(pair.road.sha256 != pair.wide.sha256, 'distinct original road and wide feeds')
            files = {}
            for role in ('road', 'wide'):
                files[role] = dict(
                    source=retained_file(out, f'{step:02d}-{role}-source.rgb.zlib', rgb[role].tobytes()),
                    canvas=retained_file(out, f'{step:02d}-{role}-canvas.rgb.zlib', getattr(pair, role).rgb))
            files['tensor'] = retained_file(out, f'{step:02d}-input.bin.zlib', tensor.tobytes())
            ledger = dict(step=step, pose=asdict(pose), events=timing.events, wait_begin_ns=begin,
                          capture_begin_ns=begin, capture_end_ns=end, preprocessing_end_ns=prepared,
                          evidence_write_end_ns=perf_counter_ns())
            verify_timing(ledger, previous_end, 0)
            previous_end = ledger['evidence_write_end_ns']
            receipt['probe_rows'].append(dict(**ledger, pixels=files, hashes=inputs.rows[-1], route=truth))
            atomic_json(out / 'report.json', receipt)
    lengths = [float(lane.length) for lane in lanes]
    minimum = math.ceil((sum(lengths) - START_FRACTION * lengths[0]) / (SPEED * DT))
    steady_max = max(row['capture_end_ns'] - row['capture_begin_ns'] for row in receipt['probe_rows'][1:])
    receipt['rate'] = rate_admission(minimum, steady_max / 1e9)


def child(args):
    out = Path(args.out)
    life = out / 'lifecycle.json'
    receipt = dict(protocol='sdk3-native-ramp-runtime-v1', status='FAILED', runtime='cloud-local',
                   candidate_sha=os.environ['SDK3_CANDIDATE_SHA'], mode=args.mode, pid=os.getpid(),
                   nonce=args.nonce, seed=args.seed, scenario=args.scenario, provider_closed=False,
                   official_inference_bounds=[0, 0], official_model_process_bounds=[0, 0],
                   policy_created=False, camera_attempts=0)
    provider = None

    def progress(payload):
        receipt.update(progress=payload, official_inference_bounds=payload['inference_bounds'])
        atomic_json(life, receipt)

    try:
        atomic_json(life, receipt)
        need(os.getppid() == args.server_owner and Path('/tmp/.X11-unix/X99').exists()
             and not os.environ.get('LD_PRELOAD'), 'owned native SDK3 display and standard loader required')
        bootstrap(receipt)
        from bigbench.metadrive_camera import NativeMetaDriveProvider
        from bigbench.model_world_frame import SOURCE_ACTION_FRAME, WorldFramePolicyAdapter
        from bigbench.native_model_campaign import NativeWorldCamera
        from bigbench.optical_calibration import assert_intrinsics_match, intrinsics_from_panda_lens, reference_source
        from bigbench.preprocess_experiment import LiveInput
        from bigbench.sdk3_terrain_priority import install_rgb_terrain_priority
        from metadrive.constants import CameraTagStateKey, Semantics

        if args.mode == 'model':
            inner = open_official_policy(args.model_id, Path('/model.onnx'), receipt, life)

        provider = NativeMetaDriveProvider(seed=args.seed, map_config=SCENARIOS[args.scenario].map_config())
        lanes = registered_lanes(provider.env.current_map, args.scenario)
        receipt['geometry'] = describe(lanes, args.scenario)
        receipt['terrain'] = install_rgb_terrain_priority(
            provider.env.engine, terrain_label=Semantics.TERRAIN.label, tag_key=CameraTagStateKey.RGB)
        lenses = {role: intrinsics_from_panda_lens(
            provider.env.engine.sensors['bigbench_' + role].get_lens(), 964, 604) for role in ('road', 'wide')}
        for role, lens in lenses.items():
            assert_intrinsics_match(lens, reference_source(role))
        receipt.update(intrinsics={role: asdict(lens) for role, lens in lenses.items()},
                       driver=driver_info(provider), input_variant=INPUT_VARIANT)
        need('llvmpipe' in receipt['driver']['renderer'], 'expected the observed frozen software renderer')
        inputs = LiveInput(NativeWorldCamera(provider), lenses, INPUT_VARIANT, out)
        if args.mode == 'probe':
            need(not Path('/model.onnx').exists(), 'no weights in model-free process')
            probe(provider, lanes, inputs, out, receipt)
        else:
            inner.preparer = inputs
            policy = WorldFramePolicyAdapter(inner, source_action_frame=SOURCE_ACTION_FRAME)
            result = run_ramp(policy, inputs, lanes, seed=args.seed, scene=args.scenario, progress=progress)
            atomic_json(out / 'run.json', result)
            atomic_json(out / 'input-rows.json', inputs.rows)
            need(result['trial_completed'], result['error'] or 'official ramp run failed')
        receipt['status'] = 'RETURNED'
    except BaseException as exc:
        receipt['failure'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        try:
            if provider is not None:
                provider.close()
                receipt['provider_closed'] = True
        finally:
            receipt['ort_imported'] = any(name == 'onnxruntime' or name.startswith('onnxruntime.') for name in sys.modules)
            atomic_json(out / 'report.json', receipt)
            atomic_json(life, receipt)
    return 0


def child_command(args, parent_pid):
    return [sys.executable, '-I', '-S', '-B', __file__, args.mode, '--out', args.out,
            '--seed', str(args.seed), '--scenario', args.scenario, '--model-id', args.model_id,
            '--nonce', args.nonce, '--server-owner', str(parent_pid)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('probe', 'model'))
    parser.add_argument('--out', required=True)
    parser.add_argument('--seed', required=True, type=int, choices=SEEDS)
    parser.add_argument('--scenario', required=True, choices=SCENES)
    parser.add_argument('--model-id', choices=OFFICIAL_MODELS, default='md-v3')
    parser.add_argument('--nonce')
    parser.add_argument('--server-owner', type=int)
    args = parser.parse_args()
    if args.server_owner is not None:
        need(args.nonce is not None and len(args.nonce) == 32, 'owned child nonce required')
        return child(args)
    args.nonce = secrets.token_hex(16)
    args.model_trial = args.mode == 'model'

    def wait(worker, server, _):
        return owner.wait_child_then_stop_server(worker, server, CHILD_LIMIT_S if args.model_trial else 240)

    return clone(owner.run_with_server, owned_child_command=child_command, wait_child_then_stop_server=wait)(args)


if __name__ == '__main__':
    raise SystemExit(main())
