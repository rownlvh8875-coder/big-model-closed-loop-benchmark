"""Verify ramp camera products and compare owned official ramp results offline."""

import argparse
import json
from hashlib import sha256
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace

import cv2
import numpy as np

from bigbench.benchmark_results import (
    CORE_SHA, MODELS, SDK_SHA, common_camera_key, read, verify_capture_rows, verify_owner_and_model,
)
from bigbench.full_s_receipts import RecordedLane, close, validate_trajectory
from bigbench.full_s_validation import STRICT, angle, need, route_state
from bigbench.optical_calibration import PinholeIntrinsics, PinholeRectifier
from bigbench.preprocess_experiment import LiveInput
from bigbench.recorded_official_execution import clone
from bigbench.sdk3_native_ramp import DT, SCENES, SEEDS, SPEED, START_FRACTION, camera_pose
from scripts.run_sdk3_benchmark_case import write_json
from scripts.verify_sdk3_wide_capture import ROLES, SOURCE_NBYTES, SOURCE_SHAPE, load_pixels, verify_timing


def recorded_ramp(rows, *, geometry_context):
    need(geometry_context == 'metadrive-native', 'native MetaDrive geometry required')
    need([row['kind'] for row in rows] == ['StraightLane', 'CircularLane', 'StraightLane',
                                          'CircularLane', 'StraightLane'], 'five recorded native segments')
    lanes = []
    for row in rows:
        length = row['length_m']
        if row['kind'] == 'StraightLane':
            shape = dict(kind='straight', direction=[(b - a) / length for a, b in zip(row['start'], row['end'])])
        else:
            radius, direction, phase = (row[k] for k in ('radius', 'direction', 'start_phase'))
            shape = dict(kind='circular', radius=radius, direction=direction, start_phase=phase,
                         end_phase=phase + direction * length / radius, center=row['center'])
        lane = RecordedLane(dict(row, shape=shape))
        need(row['width_m'] == 3.5 and all(close(actual, expected)
             for distance, key in ((0., 'start'), (length, 'end'))
             for actual, expected in zip(lane.position(distance, 0.), row[key])),
             'recorded primitive must reproduce both native endpoints')
        lanes.append(lane)
    for before, after in zip(rows, rows[1:]):
        need(math.dist(before['end'], after['start']) < 1e-7
             and abs(angle(before['end_heading_rad'] - after['start_heading_rad'])) < 1e-7,
             'continuous native ramp branch required')
    return lanes


def owned(folder, mode, seed, scene):
    report = read(folder / 'report.json')
    owner = read(folder / 'native-child.json')
    life = read(folder / 'lifecycle.json')
    state = read(folder / 'container-state.json')
    cid = (folder / 'container-id.txt').read_text().strip()
    need((report['mode'], report['seed'], report['scenario']) == (mode, seed, scene)
         and report['runtime'] == 'cloud-local' and report['status'] == 'RETURNED'
         and owner['spawn_attempted'] and owner['returncode'] == owner['server_returncode'] == 0
         and report['pid'] == owner['pid'] == life['pid'] and report['nonce'] == life['nonce']
         and report['provider_closed'] and report['child_finalized_before_server_stop']
         and report['sdk_sha256'] == SDK_SHA and report['core_sha256'] == CORE_SHA
         and report['input_variant'] == 'source_yuv_nearest_even'
         and 'llvmpipe' in report['driver']['renderer']
         and len(cid) == 64 and (folder / 'remove.log').read_text().strip() in (cid, cid[:12])
         and int((folder / 'returncode.txt').read_text()) == state['ExitCode'] == 0
         and state['Running'] is False and state['OOMKilled'] is False,
         'reaped isolated Linux SDK3 worker required')
    return report, cid


def verify_probe(folder, seed, scene):
    report, cid = owned(folder, 'probe', seed, scene)
    need(report['official_model_process_bounds'] == report['official_inference_bounds'] == [0, 0]
         and report['ort_imported'] is False and report['policy_created'] is False
         and report['libraries'] == {'numpy': '2.4.6', 'opencv': '5.0.0'}
         and np.__version__ == '2.4.6' and cv2.__version__ == '5.0.0'
         and report['camera_attempts'] == len(report['probe_rows']) == 5,
         'five model-free native poses and pinned offline reader required')
    lenses = {role: PinholeIntrinsics(**report['intrinsics'][role]) for role in ROLES}
    lanes = recorded_ramp(report['geometry'], geometry_context='metadrive-native')
    expected_minimum = math.ceil((sum(l.length for l in lanes) - lanes[0].length * START_FRACTION) / (SPEED * DT))
    need(report['rate']['minimum_steps'] == expected_minimum, 'trajectory length accounting')
    reconstructed = []
    previous = 0
    with tempfile.TemporaryDirectory() as directory:
        preparer = LiveInput(SimpleNamespace(), lenses, report['input_variant'], directory)
        rectifier = PinholeRectifier()
        for index, (row, lane, fraction) in enumerate(zip(
                report['probe_rows'], lanes, (START_FRACTION, .5, .5, .5, .9), strict=True)):
            step = index + 1
            verify_timing(row, previous, 0)
            previous = row['evidence_write_end_ns']
            pose = camera_pose(lane, fraction, index * DT)
            observed = row['pose']
            need(row['step'] == step and all(close(observed[key], getattr(pose, key))
                 for key in ('x', 'y', 'speed', 't')) and abs(angle(observed['heading'] - pose.heading)) < 1e-8
                 and route_state(lanes, index, pose)['intrusion_m'] == row['route']['intrusion_m'] == 0.
                 and row['route']['lane_index'] == index, 'prescribed ramp camera pose and footprint')
            images, hashes = {}, {}
            for role in ROLES:
                raw = load_pixels(folder, row['pixels'][role]['source'], f'{step:02d}-{role}-source.rgb.zlib',
                                  SOURCE_NBYTES)
                hashes[role] = sha256(raw).hexdigest()
                images[role] = np.frombuffer(raw, dtype=np.uint8).reshape(SOURCE_SHAPE)
            pair, _ = rectifier.rectify_pair(images['road'], images['wide'], road_intrinsics=lenses['road'],
                                              wide_intrinsics=lenses['wide'])
            for role in ROLES:
                rgb = getattr(pair, role).rgb
                need(load_pixels(folder, row['pixels'][role]['canvas'], f'{step:02d}-{role}-canvas.rgb.zlib',
                                 len(rgb)) == rgb, 'offline canvas must exactly match retained native capture')
            preparer.record_native_rgb(images, hashes)
            preparer.expected = (pair.road.sha256, pair.wide.sha256)
            tensor = preparer.prepare(pair.road, pair.wide).tobytes()
            need(load_pixels(folder, row['pixels']['tensor'], f'{step:02d}-input.bin.zlib', len(tensor)) == tensor
                 and row['hashes'] == preparer.rows[-1], 'offline tensor must exactly match retained model input')
            reconstructed.append(row['hashes'])
    for role in ROLES:
        need(len({row['source_sha256'][role] for row in reconstructed}) == 5,
             'all registered lane poses must change each actual camera source')
    terrain = {key: v for key, v in report['terrain'].items() if key != 'cameras'}
    return dict(context=dict(geometry=report['geometry'], intrinsics=report['intrinsics'],
                             driver=report['driver'], input_variant=report['input_variant'], terrain=terrain),
                path=str(folder), cid=cid, nonce=report['nonce'], pid=report['pid'], rows=reconstructed,
                source=read(folder / 'source.json'), rate=report['rate'])


def camera_gate(root):
    cases = []
    candidate_sha, source_hashes = None, None
    for seed in SEEDS:
        for scene in SCENES:
            cases.append(result := dict(seed=seed, scenario=scene, admitted=False, probes=[], differences=[]))
            for index in range(2):
                folder = root / f'{seed}-{scene}' / f'run-{index}'
                try:
                    result['probes'].append(verify_probe(folder, seed, scene))
                except (ValueError, TypeError, KeyError, OSError) as exc:
                    result.setdefault('errors', []).append(dict(path=str(folder), message=f'{type(exc).__name__}: {exc}'))
            if len(result['probes']) != 2:
                continue
            first, second = result['probes']
            distinct = first['cid'] != second['cid'] and first['nonce'] != second['nonce']
            same_source = first['source'] == second['source']
            if candidate_sha is None:
                candidate_sha = first['source']['baseline_sha']
                source_hashes = first['source']['ramp_source_sha256']
            same_source &= first['source'] == dict(baseline_sha=candidate_sha, ramp_source_sha256=source_hashes)
            for index, (left, right) in enumerate(zip(first['rows'], second['rows'], strict=True), 1):
                fields = [key for key in left if left[key] != right[key]]
                if fields:
                    result['differences'].append(dict(pose=index, fields=fields))
            result['same_context'] = first['context'] == second['context']
            result['fresh_workers'] = distinct
            result['same_source'] = same_source
            result['admitted'] = (distinct and same_source and result['same_context'] and not result['differences']
                                  and first['rate']['admitted'] and second['rate']['admitted'])
    probes = [probe for case in cases for probe in case['probes']]
    independent = all(len({probe[key] for probe in probes}) == 8 for key in ('cid', 'nonce'))
    return dict(candidate_sha=candidate_sha, ramp_source_sha256=source_hashes, cases=cases,
                all_cases_admitted=independent and all(case['admitted'] for case in cases))


def portable_camera_gate(gate):
    # A moved receipt must keep every field except the original directory pathname.
    return dict(gate, cases=[
        dict(case, probes=[{k: v for k, v in probe.items() if k != 'path'} for probe in case['probes']])
        for case in gate['cases']
    ])



def verify_model(folder, model, case, gate_sha):
    seed, scene = case['seed'], case['scenario']
    report, cid = owned(folder, 'model', seed, scene)
    verify_owner_and_model(folder, model, seed, scene)
    qualified = case['probes'][0]
    trial = read(folder / 'run.json')
    admission = read(folder / 'admission.json')
    source = read(folder / 'source.json')
    need(admission['gate_sha256'] == gate_sha and (admission['seed'], admission['scenario']) == (seed, scene)
         and admission['weight_sha256'] == MODELS[model]
         and admission['probe_source_sha256'] == qualified['source']['ramp_source_sha256']
         and admission['model_source_sha256'] == source['ramp_source_sha256']
         and source['baseline_sha'] == report['candidate_sha'] == qualified['source']['baseline_sha'],
         'model source, weights, case and exact camera gate must match the native receipts')
    need(report['geometry'] == trial['geometry'] and report['model_sha256'] == trial['model_sha256']
         and trial['protocol'] == 'sdk3-native-ramp-closed-loop-v1' and not trial['model_test_double']
         and not trial['injected_session'] and not trial['ground_truth_control_used']
         and trial['pixel_tolerance'] == trial['extra_render_tasks'] == 0
         and trial['trial_completed'] and trial['process_id'] == report['pid'],
         'owned original ramp result bound to the exact camera admission')
    validate = clone(validate_trajectory, recorded_route=recorded_ramp)
    normalized = dict(trial, completed_steps=len(trial['frames']))
    if trial['outcome'] == 'RAMP_COMPLETED':
        normalized['outcome'] = 'FULL_S_COMPLETED'
    proof = validate(normalized, seed, scene)
    bounds = proof['inference_bounds']
    need(bounds == report['official_inference_bounds'], 'verified trajectory and lifecycle bounds agree')
    images = verify_capture_rows(folder, trial['frames'], trial['inference_audit_rows'])
    need(common_camera_key(qualified['context'], qualified['rows'][0]) == common_camera_key(report, images[0]),
         'live first frame of model worker must bind to the qualified ramp start')
    last = trial['frames'][-1]
    route = last['route']
    return dict(container_id=cid, nonce=report['nonce'], process_uuid=trial['process_uuid'], pid=report['pid'],
                inference_bounds=bounds, model_process_bounds=[1, 1], outcome=trial['outcome'],
                traversal_passed=proof['traversal_passed'], final_state=trial['final_state'],
                final_route=route, last_model_action=last['raw_model_action'],
                route_progress_m=sum(r['length_m'] for r in trial['geometry'][:route['lane_index']])
                + route['longitudinal_m']), trial


def failure_activity(folder):
    life = folder / 'lifecycle.json'
    if life.is_file():
        status = read(life)
        return (status['official_model_process_bounds'], status['official_inference_bounds'])
    if (folder / 'admission.json').exists() and not (folder / 'returncode.txt').exists():
        return [0, 1], [0, 600]
    return [0, 0], [0, 0]


def model_pair(root, model, case, gate_sha):
    output = dict(seed=case['seed'], scenario=case['scenario'], runs=[], differences=[],
                  strict_repeat_passed=None, traversal_passed=None)
    trials = []
    for index in range(2):
        folder = root / model / f"{case['seed']}-{case['scenario']}" / f'run-{index}'
        relative = folder.relative_to(root).as_posix()
        try:
            summary, trial = verify_model(folder, model, case, gate_sha)
            output['runs'].append(dict(path=relative, **summary))
            trials.append(trial)
        except (ValueError, TypeError, IndexError, KeyError, OSError) as exc:
            model_bounds, inference_bounds = failure_activity(folder)
            output['runs'].append(dict(path=relative, error=f'{type(exc).__name__}: {exc}',
                                       model_process_bounds=model_bounds, inference_bounds=inference_bounds))
    if len(trials) == 2:
        first, second = output['runs']
        need(all(first[key] != second[key] for key in ('container_id', 'nonce', 'process_uuid')),
             'independently owned model worker identities required')
        left, right = trials
        for index, (a, b) in enumerate(zip(left['frames'], right['frames']), 1):
            fields = [key for key in STRICT if a[key] != b[key]]
            if fields:
                output['differences'].append(dict(step=index, fields=fields))
        output['traversal_passed'] = all(run['traversal_passed'] for run in output['runs'])
        output['strict_repeat_passed'] = (not output['differences'] and left['outcome'] == right['outcome']
                                          and len(left['frames']) == len(right['frames']))
    return output


def verify_campaign(root, gate_file, *, probe_root=None):
    gate_bytes = gate_file.read_bytes()
    gate = json.loads(gate_bytes)
    need(gate['all_cases_admitted'] is True, 'verified four-case camera admission required')
    if probe_root is not None:
        rebuilt = camera_gate(probe_root)
        need(rebuilt['all_cases_admitted'] and portable_camera_gate(gate) == portable_camera_gate(rebuilt),
             'supplied raw ramp camera evidence does not reproduce the original admission')
    gate_sha = sha256(gate_bytes).hexdigest()
    summaries = {}
    for model in ('md-v3', 'light-speed-2'):
        cases = [model_pair(root, model, case, gate_sha) for case in gate['cases']]
        runs = [run for case in cases for run in case['runs']]
        summaries[model] = dict(cases=cases,
            model_process_bounds=[sum(r['model_process_bounds'][i] for r in runs) for i in range(2)],
            inference_bounds=[sum(r['inference_bounds'][i] for r in runs) for i in range(2)],
            verified_runs=sum('error' not in r for r in runs),
            traversal_passed=sum(case['traversal_passed'] is True for case in cases),
            strict_repeat_passed=sum(case['strict_repeat_passed'] is True for case in cases))
    return dict(gate_sha256=gate_sha, camera_pairs_verified=len(gate['cases']), models=summaries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('probe', 'model'))
    parser.add_argument('root', type=Path)
    parser.add_argument('--gate', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = camera_gate(args.root.resolve()) if args.mode == 'probe' else verify_campaign(args.root, args.gate)
    write_json(args.out, result)
    return int(args.mode == 'probe' and not result['all_cases_admitted'])


if __name__ == '__main__':
    raise SystemExit(main())
