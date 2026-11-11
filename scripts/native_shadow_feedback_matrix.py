"""Independent 48-process shadow-feedback factorial experiment (SIM ONLY).

The native child calls the unchanged raw-clock API. OFF repeats measure exact
static repeatability; OFF/ON comparisons are temporal/process observations.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
from time import time_ns
import uuid

from scripts.compare_native_capture_schedule import validate_schedule_trial, compare_schedule_repeats
from scripts.compare_native_pssm_cross_process import SEEDS, SCENES, scene_directory
from scripts.compare_native_shadow_sampler import SHADER_SHA256, duration, image_comparison
from scripts.native_shadow_feedback_probe import METHOD, SCOPE, PRIORITY, validate_feedback_binding

CONDITIONS = ('baseline', 'linear', 'shadow_guard', 'both')
RUNS = ((False, 0), (False, 1), (True, 0))
CLAIMS = dict(original_mdv3_repeatability_proven=False, unique_renderer_cause_proven=False,
              onnx_inference_used=False, model_scoring_allowed=False, real_vehicle_testing=False)


def condition_order(seed, scene):
    if seed not in SEEDS or scene not in SCENES:
        raise ValueError('unknown feedback scene/seed')
    offset = SEEDS.index(seed)*len(SCENES) + SCENES.index(scene)
    return list(CONDITIONS[offset:] + CONDITIONS[:offset])


def _configuration(seed, scene, condition, probe, repeat):
    condition_order(seed, scene)
    if condition not in CONDITIONS or type(probe) is not bool or (probe, repeat) not in RUNS or type(repeat) is not int:
        raise ValueError('unknown feedback trial configuration')


def _uuid(value):
    return isinstance(value, str) and len(value) == 32 and all(c in '0123456789abcdef' for c in value)


def trial_filename(condition, probe, repeat):
    return f'{condition}-{"on" if probe else "off"}_{repeat}.json'


def validate_trial(d, seed, scene, condition, probe, repeat):
    _configuration(seed, scene, condition, probe, repeat)
    validate_schedule_trial(d, seed, scene, 'sequential_road_first')
    if any(d.get(key, False) is not False for key in CLAIMS):
        raise ValueError('static feedback experiment cannot claim a gate, unique cause or scoring')
    if not _uuid(d.get('process_uuid')) or d['process_id'] <= 0:
        raise ValueError('valid native process UUID and positive PID required')
    previous = None
    for row in d['clock_timeline']:
        before, after = row['before'], row['after']
        if (any(not duration(boundary.get(key)) for boundary in (before, after)
                for key in ('frame_time_s', 'real_time_s', 'dt_s'))
                or not duration(row.get('global_clock_time_delta_s'))
                or not duration(row.get('real_time_delta_s'))
                or after['frame_time_s'] - before['frame_time_s'] != row['global_clock_time_delta_s']
                or after['real_time_s'] - before['real_time_s'] != row['real_time_delta_s']
                or (previous is not None and (before['frame_time_s'] != previous['frame_time_s']
                                             or before['real_time_s'] < previous['real_time_s']))):
            raise ValueError('raw clock timestamps and deltas are inconsistent')
        previous = after
    trial = d.get('shadow_feedback_trial', {})
    if (trial.get('condition') != condition or trial.get('terminal_probe_enabled') is not probe
            or type(trial.get('repeat')) is not int or trial['repeat'] != repeat
            or not _uuid(trial.get('request_uuid'))):
        raise ValueError('missing or mislabeled feedback child request receipt')
    guarded, linear = condition in ('shadow_guard', 'both'), condition in ('linear', 'both')
    diagnostic = d.get('shadow_sampler_diagnostic', {})
    c = diagnostic.get('configuration', {})
    guard = dict(enabled=guarded, original_camera_states_empty=[True, True], camera_count=2,
                 shader_replaced=False, input_priority=PRIORITY,
                 inputs=['use_pssm', 'PSSMShadowAtlas'] if guarded else [],
                 placeholder=dict(dimensions=[1, 1], format='RGBA8', rgba=[255]*4, filters=[1, 1]) if guarded else None)
    if (c.get('mode') != 'feedback_' + condition or c.get('filters_before') != [6, 6]
            or c.get('filters_after') != ([1, 1] if linear else [6, 6])
            or c.get('metadrive_version') != '0.4.3'
            or c.get('loaded_fragment_shader_sha256') != SHADER_SHA256
            or c.get('shader_edited') is not False or c.get('manual_pcf_sampler2d_confirmed') is not True
            or c.get('renderer_semantics_experimental') is not (condition != 'baseline')
            or c.get('shadow_guard') != guard
            or not duration(diagnostic.get('terminal_diagnostic_wall_time_s'))
            or diagnostic.get('no_render_after_terminal_probe') is not True):
        raise ValueError('invalid or mislabeled sampler/shadow guard treatment')
    p = diagnostic.get('terminal_probe', {})
    rows = p.get('records')
    if (not isinstance(rows, list) or p.get('scope') != SCOPE or p.get('method') != METHOD
            or p.get('per_primitive_state_trace') is not False
            or p.get('primary_frames_instrumented') is not False
            or p.get('texture_pixel_extraction') is not False or p.get('callbacks_removed') is not True
            or not duration(p.get('query_duration_s'))):
        raise ValueError('missing terminal-only feedback observer isolation receipt')
    if not probe:
        if p.get('status') != 'OFF' or rows or p['query_duration_s'] != 0:
            raise ValueError('OFF installed feedback observations')
        return
    if (p.get('status') != 'TERMINAL_QUERY' or len(rows) != 8
            or any(sum(r.get('camera') == camera for r in rows) != 2
                   for camera in ('road', 'wide', 'shadow0', 'shadow1'))):
        raise ValueError('four shadow and four RGB terminal observations required')
    for row in rows:
        validate_feedback_binding(row, guarded=guarded, linear=linear)
    if (not math.isclose(sum(r['query_duration_s'] for r in rows), p['query_duration_s'], rel_tol=1e-12, abs_tol=1e-9)
            or diagnostic['terminal_diagnostic_wall_time_s'] < p['query_duration_s']):
        raise ValueError('query overhead differs from raw rows or exceeds terminal interval')
    if len({r['expected_atlas_texture'] for r in rows}) != 1 or len({r['expected_placeholder_texture'] for r in rows}) != 1:
        raise ValueError('atlas/placeholder identity changed within terminal observations')


def native_clock(**kwargs):
    # Lazy import: aggregation needs only NumPy and must not initialize Panda/GL.
    from scripts.native_raw_pixel_clock import native_pixel_clock
    return native_pixel_clock(**kwargs)


def native_trial(*, seed, scene, condition, probe, repeat, request_uuid):
    _configuration(seed, scene, condition, probe, repeat)
    if not _uuid(request_uuid):
        raise ValueError('fresh launch request UUID required')
    d = native_clock(seed=seed, scenario=scene, fraction=.12, mode='perceive_sequential',
                     ablation='baseline', frames=10, warmup=2,
                     shadow_sampler_mode='feedback_' + condition, terminal_shadow_probe=probe)
    d['shadow_feedback_trial'] = dict(condition=condition, terminal_probe_enabled=probe,
                                     repeat=repeat, request_uuid=request_uuid)
    d.update(CLAIMS)
    return d


def launch_trial(*, seed, scene, condition, probe, repeat, out, request_uuid=None, status_receipt=None):
    _configuration(seed, scene, condition, probe, repeat)
    request_uuid = request_uuid or uuid.uuid4().hex
    if not _uuid(request_uuid):
        raise ValueError('invalid launch request UUID')
    out = Path(out)
    log = out.with_suffix('.log')
    if out.exists() or log.exists():
        raise ValueError('preexisting output/log cannot prove a fresh native process')
    out.parent.mkdir(parents=True, exist_ok=True)
    command = ['xvfb-run', '-a', sys.executable, '-m', 'scripts.native_shadow_feedback_matrix',
               '--mode', 'native', '--seed', str(seed), '--scene', scene,
               '--condition', condition, '--probe', 'on' if probe else 'off', '--repeat', str(repeat),
               '--request-uuid', request_uuid, '--out', str(out)]
    with log.open('x') as stream:
        status = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
    if status_receipt is not None:
        status_receipt.append(status)
    if status not in (0, 5):
        return status
    d = json.loads(out.read_text())
    validate_trial(d, seed, scene, condition, probe, repeat)
    if d['shadow_feedback_trial']['request_uuid'] != request_uuid:
        raise ValueError('fresh native receipt belongs to a different launch request')
    if status == 5:
        print('XVFB_CLEANUP_STATUS_5_WITH_VALIDATED_FRESH_FEEDBACK_RECEIPT', out, flush=True)
    return 0


def _write(path, d):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d, indent=2, allow_nan=False) + '\n')


def run_case(*, root, seed, scene):
    folder = scene_directory(root, seed, scene)
    if folder.exists():
        raise ValueError('feedback case directory must be fresh')
    folder.mkdir(parents=True)
    ledger = dict(seed=seed, scenario=scene, condition_order=condition_order(seed, scene), entries=[])
    for condition in ledger['condition_order']:
        for probe, repeat in RUNS:
            request = uuid.uuid4().hex
            filename = trial_filename(condition, probe, repeat)
            entry = dict(sequence_index=len(ledger['entries']), condition=condition,
                         terminal_probe_enabled=probe, repeat=repeat, filename=filename,
                         request_uuid=request, started_ns=time_ns(), finished_ns=None,
                         native_exit_status=None, accepted_exit_status=None)
            ledger['entries'].append(entry)
            _write(folder / 'execution_ledger.json', ledger)
            # Preserve raw return codes in the ledger as well as the native log.
            native_status = []
            try:
                status = launch_trial(seed=seed, scene=scene, condition=condition,
                    probe=probe, repeat=repeat, out=folder/filename, request_uuid=request,
                    status_receipt=native_status)
                entry['accepted_exit_status'] = status
                if status == 0:
                    d = json.loads((folder/filename).read_text())
                    entry.update(process_uuid=d['process_uuid'], process_id=d['process_id'])
            finally:
                entry['finished_ns'] = time_ns()
                entry['native_exit_status'] = native_status[0] if native_status else None
                _write(folder/'execution_ledger.json', ledger)
            if status != 0:
                return status
    _write(folder/'case_comparison.json', compare_case(root, seed, scene))
    return 0


def compare_case(root, seed, scene):
    folder = scene_directory(root, seed, scene)
    ledger = json.loads((folder/'execution_ledger.json').read_text())
    order = condition_order(seed, scene)
    if ledger.get('seed') != seed or ledger.get('scenario') != scene or ledger.get('condition_order') != order:
        raise ValueError('mislabeled or unbalanced execution ledger')
    expected = [(c, p, r) for c in order for p, r in RUNS]
    entries = ledger.get('entries')
    if not isinstance(entries, list) or len(entries) != 12:
        raise ValueError('complete twelve-process execution ledger required')
    uuids, pids, requests, trials, poses = set(), set(), set(), {}, []
    previous_end = 0
    for index, (entry, (condition, probe, repeat)) in enumerate(zip(entries, expected)):
        filename = trial_filename(condition, probe, repeat)
        if (entry.get('sequence_index') != index or entry.get('condition') != condition
                or entry.get('terminal_probe_enabled') is not probe or entry.get('repeat') != repeat
                or entry.get('filename') != filename or entry.get('native_exit_status') not in (0, 5)
                or entry.get('accepted_exit_status') != 0
                or type(entry.get('started_ns')) is not int or type(entry.get('finished_ns')) is not int
                or entry['started_ns'] < previous_end or entry['finished_ns'] < entry['started_ns']):
            raise ValueError('execution ledger order, timestamps or native status invalid')
        previous_end = entry['finished_ns']
        d = json.loads((folder/filename).read_text())
        validate_trial(d, seed, scene, condition, probe, repeat)
        request = d['shadow_feedback_trial']['request_uuid']
        if (entry.get('process_uuid') != d['process_uuid'] or entry.get('process_id') != d['process_id']
                or entry.get('request_uuid') != request or request in requests
                or d['process_uuid'] in uuids or d['process_id'] in pids):
            raise ValueError('ledger/receipt identities disagree or a native process was reused')
        uuids.add(d['process_uuid']); pids.add(d['process_id']); requests.add(request)
        poses.append(d['camera_pose']); trials[condition, probe, repeat] = d
    if any(pose != poses[0] for pose in poses):
        raise ValueError('feedback conditions used different WORLD camera poses')
    conditions = {}
    for condition in CONDITIONS:
        a, b, on = (trials[condition, p, r] for p, r in RUNS)
        off = compare_schedule_repeats(a, b, seed, scene, 'sequential_road_first')
        off.update(arm=condition, is_original_sequential_control=condition == 'baseline')
        conditions[condition] = dict(off_repeat_comparison=off,
            off_on_primary_comparison=image_comparison(a, on),
            off_on_comparison_scope='temporal_process_observation_only',
            terminal_observations=on['shadow_sampler_diagnostic']['terminal_probe'],
            process_uuids=[d['process_uuid'] for d in (a, b, on)])
    return dict(status='NATIVE_SHADOW_FEEDBACK_CASE_VERIFIED', seed=seed, scenario=scene,
        conditions=conditions, condition_order=order, execution_ledger=ledger,
        independent_process_count=len(uuids), same_runner_distinct_pid_count=len(pids),
        baseline_to_treatment_off0_primary_comparisons={c: image_comparison(trials['baseline',False,0], trials[c,False,0])
                                                       for c in CONDITIONS if c != 'baseline'}, **CLAIMS)


def aggregate_cases(root):
    cases, uuids = [], set()
    for seed in SEEDS:
        for scene in SCENES:
            case = compare_case(root, seed, scene)
            stored = json.loads((scene_directory(root,seed,scene)/'case_comparison.json').read_text())
            if stored != case:
                raise ValueError('stale or modified feedback case summary')
            for result in case['conditions'].values():
                for uid in result['process_uuids']:
                    if uid in uuids:
                        raise ValueError('native process UUID reused across feedback cases')
                    uuids.add(uid)
            cases.append(case)
    return dict(status='FOUR_NATIVE_SHADOW_FEEDBACK_CASES_VERIFIED',
                independent_process_count=len(uuids), per_scene=cases, **CLAIMS)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('native','run-case','case','aggregate'), required=True)
    p.add_argument('--root', type=Path)
    p.add_argument('--seed', type=int, choices=SEEDS)
    p.add_argument('--scene', choices=SCENES)
    p.add_argument('--condition', choices=CONDITIONS)
    p.add_argument('--probe', choices=('off','on'))
    p.add_argument('--repeat', type=int, choices=(0,1))
    p.add_argument('--request-uuid')
    p.add_argument('--out', type=Path)
    a = p.parse_args(argv)
    if a.mode == 'run-case':
        if a.root is None or a.seed is None or a.scene is None:
            p.error('run-case requires --root --seed --scene')
        return run_case(root=a.root, seed=a.seed, scene=a.scene)
    if a.out is None:
        p.error('--out is required')
    if a.mode == 'native':
        if None in (a.seed,a.scene,a.condition,a.probe,a.repeat,a.request_uuid):
            p.error('native requires seed, scene, condition, probe, repeat and request UUID')
        if a.out.exists():
            raise ValueError('native output must be fresh')
        try:
            result = native_trial(seed=a.seed, scene=a.scene, condition=a.condition,
                probe=a.probe=='on', repeat=a.repeat, request_uuid=a.request_uuid)
        except Exception as exc:
            result = dict(status='ERROR', seed=a.seed, scenario=a.scene,
                          error=f'{type(exc).__name__}: {exc}', **CLAIMS)
        _write(a.out,result)
        print('NATIVE_SHADOW_FEEDBACK', result['status'], flush=True)
        return 0 if result['status']=='OBSERVED_NATIVE_PIXEL_CLOCK' else 2
    if a.root is None or a.mode == 'case' and (a.seed is None or a.scene is None):
        p.error('comparison requires --root; case also requires --seed --scene')
    result = compare_case(a.root,a.seed,a.scene) if a.mode=='case' else aggregate_cases(a.root)
    _write(a.out,result)
    print(result['status'],result['independent_process_count'],flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
