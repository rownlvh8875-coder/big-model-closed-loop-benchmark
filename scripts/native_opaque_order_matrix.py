"""Observer-OFF opaque-bin ordering factorial, 32 independent processes.

This diagnostic changes only opaque bin type and optional existing feedback
treatments. Setup CPU reads are not actual per-draw order observations.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
from time import time_ns
import uuid

from scripts.compare_native_capture_schedule import compare_schedule_repeats
from scripts.compare_native_pssm_cross_process import SEEDS, SCENES, scene_directory
from scripts.compare_native_shadow_sampler import image_comparison
from scripts.native_shadow_feedback_matrix import (
    native_trial as feedback_native_trial, validate_trial as validate_feedback_trial,
)

CONDITIONS = {'original_state_sorted': ('baseline', 2), 'original_unsorted': ('baseline', 1),
              'both_state_sorted': ('both', 2), 'both_unsorted': ('both', 1)}
CLAIMS = dict(original_mdv3_repeatability_proven=False, unique_renderer_cause_proven=False,
              renderer_equivalence_proven=False, onnx_inference_used=False,
              model_scoring_allowed=False, real_vehicle_testing=False)
CPU_RECEIPT = dict(setup_cpu_checks=True, before_provider=True, type_only_policy=True,
                   type_change_may_apply_next_frame=True, extra_render_ticks=0,
                   observer_enabled=False, gpu_queries_used=False, actual_draw_trace=False,
                   setup_overhead_free=False)


def condition_order(seed, scene):
    if seed not in SEEDS or scene not in SCENES:
        raise ValueError('unknown opaque-order seed/scene')
    names = list(CONDITIONS)
    offset = SEEDS.index(seed)*len(SCENES) + SCENES.index(scene)
    return names[offset:] + names[:offset]


def _configuration(seed, scene, condition, repeat):
    condition_order(seed, scene)
    if condition not in CONDITIONS or type(repeat) is not int or repeat not in (0, 1):
        raise ValueError('unknown opaque-order condition/repeat')


def _uuid(value):
    return isinstance(value, str) and len(value) == 32 and all(c in '0123456789abcdef' for c in value)


def get_bin_manager():
    # Aggregation imports this module without loading Panda or libGL.
    from panda3d.core import CullBinManager
    return CullBinManager.getGlobalPtr()


def _bin_snapshot(manager):
    index = manager.findBin('opaque')
    if index < 0 or manager.getBinName(index) != 'opaque':
        raise RuntimeError('expected existing opaque bin')
    return dict(index=int(index), name=manager.getBinName(index),
                type=int(manager.getBinType(index)), sort=int(manager.getBinSort(index)),
                active=bool(manager.getBinActive(index)))


@contextmanager
def opaque_bin_policy(requested_type, *, manager=None):
    if type(requested_type) is not int or requested_type not in (1, 2):
        raise ValueError('opaque bin policy must be unsorted1 or state_sorted2')
    manager = get_bin_manager() if manager is None else manager
    before = _bin_snapshot(manager)
    if before['type'] != 2:
        raise RuntimeError('original opaque bin must be state_sorted type2')
    expected = dict(before, type=requested_type)
    receipt = dict(CPU_RECEIPT, before=before, requested_type=requested_type,
                   configured=None, after_capture=None, restored=None)
    try:
        if requested_type != 2:
            manager.setBinType(before['index'], requested_type)
        receipt['configured'] = _bin_snapshot(manager)
        if receipt['configured'] != expected:
            raise RuntimeError('opaque bin setup changed unexpected metadata')
        yield receipt
        receipt['after_capture'] = _bin_snapshot(manager)
        if receipt['after_capture'] != expected:
            raise RuntimeError('requested opaque bin policy did not survive capture')
    finally:
        if int(manager.getBinType(before['index'])) != before['type']:
            manager.setBinType(before['index'], before['type'])
        receipt['restored'] = _bin_snapshot(manager)
        if receipt['restored'] != before:
            raise RuntimeError('opaque bin metadata was not restored')


def native_trial(*, seed, scene, condition, repeat, request_uuid):
    _configuration(seed, scene, condition, repeat)
    if not _uuid(request_uuid):
        raise ValueError('fresh opaque launch request UUID required')
    feedback, requested = CONDITIONS[condition]
    result, receipt = None, None
    try:
        with opaque_bin_policy(requested) as receipt:
            result = feedback_native_trial(seed=seed, scene=scene, condition=feedback,
                                           probe=False, repeat=repeat, request_uuid=request_uuid)
    except Exception as exc:
        if result is None:
            result = dict(status='ERROR', seed=seed, scenario=scene)
        else:
            result['native_capture_status_before_policy_error'] = result.get('status')
            result['status'] = 'ERROR'
        result['opaque_order_error'] = f'{type(exc).__name__}: {exc}'
    result['opaque_order_trial'] = dict(condition=condition, repeat=repeat, request_uuid=request_uuid)
    result['opaque_bin_diagnostic'] = receipt
    result.update(CLAIMS)
    return result


def validate_trial(d, seed, scene, condition, repeat):
    _configuration(seed, scene, condition, repeat)
    feedback, requested = CONDITIONS[condition]
    validate_feedback_trial(d, seed, scene, feedback, False, repeat)
    if any(d.get(key) is not False for key in CLAIMS):
        raise ValueError('opaque-order results cannot claim a gate, cause or renderer equivalence')
    trial = d.get('opaque_order_trial', {})
    if (trial.get('condition') != condition or type(trial.get('repeat')) is not int
            or trial['repeat'] != repeat or not _uuid(trial.get('request_uuid'))
            or trial['request_uuid'] != d['shadow_feedback_trial']['request_uuid']):
        raise ValueError('mislabeled opaque-order child request receipt')
    diagnostic = d.get('opaque_bin_diagnostic')
    if not isinstance(diagnostic, dict):
        raise ValueError('missing CPU opaque bin diagnostic')
    for stage in ('before', 'configured', 'after_capture', 'restored'):
        state = diagnostic.get(stage)
        if (not isinstance(state, dict) or set(state) != {'index', 'name', 'type', 'sort', 'active'}
                or any(type(state.get(k)) is not int for k in ('index', 'type', 'sort'))
                or type(state.get('active')) is not bool):
            raise ValueError('opaque bin snapshot has invalid wire field types')
    before = diagnostic.get('before')
    if (not isinstance(before, dict) or set(before) != {'index', 'name', 'type', 'sort', 'active'}
            or type(before.get('index')) is not int or before['index'] < 0
            or before.get('name') != 'opaque' or type(before.get('type')) is not int or before['type'] != 2
            or type(before.get('sort')) is not int or type(before.get('active')) is not bool
            or type(diagnostic.get('requested_type')) is not int or diagnostic['requested_type'] != requested
            or diagnostic.get('configured') != dict(before, type=requested)
            or diagnostic.get('after_capture') != dict(before, type=requested)
            or diagnostic.get('restored') != before
            or any(type(diagnostic.get(k)) is not type(v) or diagnostic[k] != v for k, v in CPU_RECEIPT.items())
            or 'opaque_order_error' in d):
        raise ValueError('opaque bin type or preserved metadata does not verify treatment')


def trial_filename(condition, repeat):
    return f'{condition}-run_{repeat}.json'


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def launch_trial(*, seed, scene, condition, repeat, out, request_uuid=None, status_receipt=None):
    _configuration(seed, scene, condition, repeat)
    request_uuid = uuid.uuid4().hex if request_uuid is None else request_uuid
    if not _uuid(request_uuid):
        raise ValueError('invalid opaque launch request UUID')
    out = Path(out); log = out.with_suffix('.log')
    if out.exists() or log.exists():
        raise ValueError('preexisting receipt/log cannot prove a fresh native process')
    out.parent.mkdir(parents=True, exist_ok=True)
    command = ['xvfb-run', '-a', sys.executable, '-m', 'scripts.native_opaque_order_matrix',
               '--mode', 'native', '--seed', str(seed), '--scene', scene, '--condition', condition,
               '--repeat', str(repeat), '--request-uuid', request_uuid, '--out', str(out)]
    with log.open('x') as stream:
        status = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
    if status_receipt is not None:
        status_receipt.append(status)
    if status not in (0, 5):
        return status
    d = json.loads(out.read_text())
    validate_trial(d, seed, scene, condition, repeat)
    if d['opaque_order_trial']['request_uuid'] != request_uuid:
        raise ValueError('fresh native receipt belongs to a different opaque launch request')
    if status == 5:
        print('XVFB_CLEANUP_STATUS_5_WITH_VALIDATED_FRESH_OPAQUE_RECEIPT', out, flush=True)
    return 0


def run_case(*, root, seed, scene):
    folder = scene_directory(root, seed, scene)
    if folder.exists():
        raise ValueError('opaque-order case directory must be fresh')
    folder.mkdir(parents=True)
    ledger = dict(seed=seed, scenario=scene, condition_order=condition_order(seed, scene), entries=[])
    for condition in ledger['condition_order']:
        for repeat in (0, 1):
            request = uuid.uuid4().hex
            entry = dict(sequence_index=len(ledger['entries']), condition=condition, repeat=repeat,
                         filename=trial_filename(condition, repeat), request_uuid=request,
                         started_ns=time_ns(), finished_ns=None, native_exit_status=None,
                         accepted_exit_status=None)
            ledger['entries'].append(entry); _write(folder/'execution_ledger.json', ledger)
            raw_status = []
            try:
                status = launch_trial(seed=seed, scene=scene, condition=condition, repeat=repeat,
                    request_uuid=request, out=folder/entry['filename'], status_receipt=raw_status)
                entry['accepted_exit_status'] = status
                if status == 0:
                    d = json.loads((folder/entry['filename']).read_text())
                    entry.update(process_uuid=d['process_uuid'], process_id=d['process_id'])
            except Exception as exc:
                entry['error'] = f'{type(exc).__name__}: {exc}'
                raise
            finally:
                entry['finished_ns'] = time_ns()
                entry['native_exit_status'] = raw_status[0] if raw_status else None
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
        raise ValueError('mislabeled or unbalanced opaque-order execution ledger')
    entries = ledger.get('entries')
    if not isinstance(entries, list) or len(entries) != 8:
        raise ValueError('complete eight-process opaque-order execution ledger required')
    ids, pids, requests, trials, poses, originals = set(), set(), set(), {}, [], []
    previous_end = 0
    for index, (entry, (condition, repeat)) in enumerate(zip(entries, ((c, r) for c in order for r in (0, 1)))):
        filename = trial_filename(condition, repeat)
        if (type(entry.get('sequence_index')) is not int or entry['sequence_index'] != index
                or entry.get('condition') != condition or type(entry.get('repeat')) is not int or entry['repeat'] != repeat
                or entry.get('filename') != filename
                or type(entry.get('native_exit_status')) is not int or entry['native_exit_status'] not in (0, 5)
                or type(entry.get('accepted_exit_status')) is not int or entry['accepted_exit_status'] != 0
                or type(entry.get('started_ns')) is not int or type(entry.get('finished_ns')) is not int
                or entry['started_ns'] <= 0 or entry['started_ns'] < previous_end
                or entry['finished_ns'] < entry['started_ns'] or 'error' in entry):
            raise ValueError('opaque-order ledger order, timing or exit status invalid')
        previous_end = entry['finished_ns']
        d = json.loads((folder/filename).read_text()); validate_trial(d, seed, scene, condition, repeat)
        nonce = d['opaque_order_trial']['request_uuid']
        if (entry.get('request_uuid') != nonce or entry.get('process_uuid') != d['process_uuid']
                or entry.get('process_id') != d['process_id'] or nonce in requests
                or d['process_uuid'] in ids or d['process_id'] in pids):
            raise ValueError('opaque-order ledger identities disagree or native process was reused')
        requests.add(nonce); ids.add(d['process_uuid']); pids.add(d['process_id'])
        trials[condition, repeat] = d; poses.append(d['camera_pose']); originals.append(d['opaque_bin_diagnostic']['before'])
    if any(pose != poses[0] for pose in poses) or any(state != originals[0] for state in originals):
        raise ValueError('opaque-order conditions changed WORLD pose or original bin metadata')
    results = {}
    for condition in CONDITIONS:
        pair = [trials[condition, r] for r in (0, 1)]
        comparison = compare_schedule_repeats(*pair, seed, scene, 'sequential_road_first')
        comparison.update(arm=condition, is_original_sequential_control=condition == 'original_state_sorted', **CLAIMS)
        results[condition] = dict(repeat_comparison=comparison, feedback_condition=CONDITIONS[condition][0],
                                 opaque_bin_type=CONDITIONS[condition][1], process_uuids=[d['process_uuid'] for d in pair],
                                 cpu_bin_receipts=[d['opaque_bin_diagnostic'] for d in pair])
    return dict(status='NATIVE_OPAQUE_ORDER_CASE_VERIFIED', seed=seed, scenario=scene,
        condition_order=order, execution_ledger=ledger, conditions=results,
        independent_process_count=len(ids), same_runner_distinct_pid_count=len(pids),
        sorting_cross_condition_comparisons={family: [image_comparison(trials[family+'_state_sorted',r],trials[family+'_unsorted',r])
                                                    for r in (0,1)] for family in ('original','both')},
        cross_condition_comparison_is_renderer_equivalence_proof=False, actual_draw_trace=False, **CLAIMS)


def aggregate_cases(root):
    cases, ids = [], set()
    for seed in SEEDS:
        for scene in SCENES:
            case = compare_case(root, seed, scene)
            if case != json.loads((scene_directory(root,seed,scene)/'case_comparison.json').read_text()):
                raise ValueError('stale or modified opaque-order case summary')
            for condition in case['conditions'].values():
                for uid in condition['process_uuids']:
                    if uid in ids:
                        raise ValueError('native process UUID reused across opaque-order cases')
                    ids.add(uid)
            cases.append(case)
    result = dict(status='FOUR_NATIVE_OPAQUE_ORDER_CASES_VERIFIED', independent_process_count=len(ids),
                  per_scene=cases, actual_draw_trace=False, **CLAIMS)
    stored = Path(root)/'aggregate_summary.json'
    if stored.exists() and json.loads(stored.read_text()) != result:
        raise ValueError('stale or modified opaque-order aggregate summary')
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('native','run-case','case','aggregate'), required=True)
    p.add_argument('--root', type=Path)
    p.add_argument('--seed', type=int, choices=SEEDS)
    p.add_argument('--scene', choices=SCENES)
    p.add_argument('--condition', choices=CONDITIONS)
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
        if None in (a.seed,a.scene,a.condition,a.repeat,a.request_uuid):
            p.error('native requires seed, scene, condition, repeat and request UUID')
        if a.out.exists():
            raise ValueError('native output must be fresh')
        try:
            result = native_trial(seed=a.seed, scene=a.scene, condition=a.condition,
                                  repeat=a.repeat, request_uuid=a.request_uuid)
        except Exception as exc:
            result = dict(status='ERROR', seed=a.seed, scenario=a.scene,
                          error=f'{type(exc).__name__}: {exc}', **CLAIMS)
        # Native poses may be tuples. Preserve the complete raw receipt FIRST;
        # strict existing validators consume only the reloaded JSON wire schema.
        _write(a.out, result)
        try:
            wire = json.loads(a.out.read_text())
            validate_trial(wire, a.seed, a.scene, a.condition, a.repeat)
            if wire['opaque_order_trial']['request_uuid'] != a.request_uuid:
                raise ValueError('native opaque request UUID mismatch')
        except Exception as exc:
            print('NATIVE_OPAQUE_ORDER_INVALID', f'{type(exc).__name__}: {exc}', file=sys.stderr, flush=True)
            return 2
        print('NATIVE_OPAQUE_ORDER', wire['status'], flush=True)
        return 0
    if a.root is None or a.mode == 'case' and (a.seed is None or a.scene is None):
        p.error('comparison requires root; case also requires seed and scene')
    result = compare_case(a.root,a.seed,a.scene) if a.mode == 'case' else aggregate_cases(a.root)
    _write(a.out, result)
    print(result['status'], result['independent_process_count'], flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
