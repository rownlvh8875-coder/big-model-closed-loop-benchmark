"""Original native camera with controlled Mesa cache availability; no ONNX.

All inventories/snapshots happen outside native process lifetimes. They may
affect OS page-cache state and do not prove individual shader cache hits.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from time import perf_counter

from scripts.compare_native_capture_schedule import validate_schedule_trial, compare_schedule_repeats
from scripts.compare_native_pssm_cross_process import SEEDS, SCENES, scene_directory

ARMS = ('shared', 'isolated', 'disabled')
SCOPE = 'parent_inventory_and_snapshot_outside_native_process'


def execution_order(seed: int, scene: str) -> tuple[str, ...]:
    if seed not in SEEDS or scene not in SCENES:
        raise ValueError('unsupported cache scene')
    abba = ('shared-0', 'isolated-0', 'isolated-1', 'shared-1')
    baab = ('isolated-0', 'shared-0', 'shared-1', 'isolated-1')
    disabled = ('disabled-0', 'disabled-1')
    index = SEEDS.index(seed) * 2 + SCENES.index(scene)
    return (abba + disabled, disabled + baab, baab + disabled, disabled + abba)[index]


def inventory(path: Path) -> dict:
    files = []
    total = 0
    if path.is_symlink():
        raise ValueError('cache root must not be a symlink')
    if path.exists() and not path.is_dir():
        raise ValueError('cache root must be a directory')
    if path.exists():
        for p in sorted(path.rglob('*'), key=lambda p: p.relative_to(path).as_posix()):
            if p.is_symlink():
                raise ValueError('cache symlinks cannot establish safe snapshot evidence')
            if p.is_dir():
                continue
            if not p.is_file():
                raise ValueError('nonregular cache entry')
            size = p.stat().st_size
            if size > 64 * 1024 * 1024:
                raise ValueError('cache entry exceeds snapshot bound')
            files.append({'path': p.relative_to(path).as_posix(), 'bytes': size,
                          'sha256': sha256(p.read_bytes()).hexdigest()})
            total += size
            if len(files) > 10000 or total > 64 * 1024 * 1024:
                raise ValueError('cache tree exceeds snapshot bound')
    return {'file_count': len(files), 'total_bytes': sum(f['bytes'] for f in files),
            'files': files}


def write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def cache_relative(arm: str, index: int) -> str:
    return 'live/shared' if arm == 'shared' else f'live/{arm}-{index}'


def validate_native(d: dict, seed: int, scene: str):
    validate_schedule_trial(d, seed, scene, 'sequential_road_first')
    if d.get('shadow_sampler_diagnostic') is not None:
        raise ValueError('original sampler and no GPU observer required')
    previous = None
    for row in d['clock_timeline']:
        before, after = row['before'], row['after']
        values = [b.get(k) for b in (before, after)
                  for k in ('frame_time_s', 'real_time_s', 'dt_s')]
        values += [row.get('global_clock_time_delta_s'), row.get('real_time_delta_s')]
        if (any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values)
                or after['frame_time_s'] - before['frame_time_s'] != row['global_clock_time_delta_s']
                or after['real_time_s'] - before['real_time_s'] != row['real_time_delta_s']
                or (previous is not None and
                    (before['frame_time_s'] != previous['frame_time_s']
                     or before['real_time_s'] < previous['real_time_s']))):
            raise ValueError('incomplete or inconsistent native raw clock evidence')
        previous = after


def run_case(root: Path, seed: int, scene: str) -> dict:
    order = execution_order(seed, scene)
    folder = scene_directory(root, seed, scene)
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'native').mkdir()
    (folder / 'logs').mkdir()
    (folder / 'snapshots').mkdir()
    execution = []
    write_json(folder / 'execution.json', execution)
    for position, label in enumerate(order):
        arm, repeat = label.rsplit('-', 1)
        repeat = int(repeat)
        cache = folder / cache_relative(arm, repeat)
        cache.mkdir(parents=True, exist_ok=arm == 'shared' and repeat == 1)
        before = inventory(cache)
        out = folder / 'native' / f'{label}.json'
        env = dict(os.environ)
        env['MESA_SHADER_CACHE_DIR'] = str(cache.resolve())
        env.pop('MESA_SHADER_CACHE_DISABLE', None)
        if arm == 'disabled':
            env['MESA_SHADER_CACHE_DISABLE'] = 'true'
        command = [sys.executable, '-m', 'scripts.run_native_capture_trial',
                   '--seed', str(seed), '--scene', scene,
                   '--arm', 'sequential_road_first', '--out', str(out)]
        print('CACHE_NATIVE_START', seed, scene, label, before['file_count'], flush=True)
        started = perf_counter()
        with (folder / 'logs' / f'{label}.log').open('wb') as log:
            status = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
        elapsed = perf_counter() - started
        execution.append({'label': label, 'native_launcher_return_code': status})
        write_json(folder / 'execution.json', execution)
        if status != 0:
            raise RuntimeError(f'{label}: native launcher failed with status {status}')
        validate_native(json.loads(out.read_text()), seed, scene)
        after = inventory(cache)
        snapshot = folder / 'snapshots' / label
        shutil.copytree(cache, snapshot)
        if inventory(snapshot) != after:
            raise ValueError('cache changed while creating its after-process snapshot')
        write_json(folder / f'{label}.json', {
            'seed': seed, 'scenario': scene, 'label': label, 'arm': arm, 'repeat': repeat,
            'execution_index': position, 'measurement_scope': SCOPE,
            'cache_directory_relative': cache_relative(arm, repeat),
            'cache_disable': env.get('MESA_SHADER_CACHE_DISABLE'),
            'cache_before': before, 'cache_after': after,
            'native_sha256': sha256(out.read_bytes()).hexdigest(),
            'native_process_wall_s': elapsed, 'native_launcher_return_code': status,
        })
    result = compare_case(root, seed, scene)
    write_json(folder / 'case_comparison.json', result)
    return result


def validate_inventory(value: dict):
    files = value.get('files')
    if not isinstance(files, list):
        raise ValueError('missing cache file manifest')
    paths = []
    for f in files:
        name, size, digest = f.get('path'), f.get('bytes'), f.get('sha256')
        if (not isinstance(name, str) or not name or '\\' in name
                or Path(name).is_absolute() or '..' in Path(name).parts
                or type(size) is not int or size < 0
                or not isinstance(digest, str) or len(digest) != 64
                or any(c not in '0123456789abcdef' for c in digest)):
            raise ValueError('invalid cache file manifest')
        paths.append(name)
    if (paths != sorted(set(paths)) or value.get('file_count') != len(files)
            or value.get('total_bytes') != sum(f['bytes'] for f in files)):
        raise ValueError('cache manifest summary differs from file entries')


def compare_case(root: Path, seed: int, scene: str) -> dict:
    order = execution_order(seed, scene)
    folder = scene_directory(root, seed, scene)
    execution = json.loads((folder / 'execution.json').read_text())
    if execution != [{'label': label, 'native_launcher_return_code': 0} for label in order]:
        raise ValueError('native execution order or completion differs from assigned balance')
    trials, metadata, uuids, pids, poses = {}, {}, set(), set(), []
    for position, label in enumerate(order):
        arm, repeat = label.rsplit('-', 1); repeat = int(repeat)
        d = json.loads((folder / f'{label}.json').read_text())
        native_path = folder / 'native' / f'{label}.json'
        if (d.get('seed') != seed or d.get('scenario') != scene or d.get('label') != label
                or d.get('arm') != arm or d.get('repeat') != repeat
                or d.get('execution_index') != position or d.get('measurement_scope') != SCOPE
                or d.get('cache_directory_relative') != cache_relative(arm, repeat)
                or d.get('cache_disable') != ('true' if arm == 'disabled' else None)
                or d.get('native_launcher_return_code') != 0
                or type(d.get('native_process_wall_s')) not in (int, float)
                or not math.isfinite(d['native_process_wall_s']) or d['native_process_wall_s'] <= 0
                or d.get('native_sha256') != sha256(native_path.read_bytes()).hexdigest()):
            raise ValueError('mislabeled cache/native process receipt')
        native = json.loads(native_path.read_text())
        validate_native(native, seed, scene)
        for inv in (d.get('cache_before', {}), d.get('cache_after', {})):
            validate_inventory(inv)
        if inventory(folder / 'snapshots' / label) != d['cache_after']:
            raise ValueError('cache snapshot differs from recorded after-process manifest')
        before, after = d['cache_before'], d['cache_after']
        if arm == 'shared' and repeat == 1:
            if before != metadata['shared-0']['cache_after'] or before['total_bytes'] <= 0:
                raise ValueError('shared process did not start with prior populated cache')
        elif before['file_count'] != 0:
            raise ValueError('fresh cache arm did not start empty')
        if ((arm == 'disabled' and after['file_count'] != 0)
                or (arm != 'disabled' and after['total_bytes'] <= 0)):
            raise ValueError('cache availability intervention not verified')
        if native['process_uuid'] in uuids or native['process_id'] in pids:
            raise ValueError('same-runner native process reused between cache trials')
        uuids.add(native['process_uuid']); pids.add(native['process_id']); poses.append(native['camera_pose'])
        trials[label] = native; metadata[label] = d
    if any(p != poses[0] for p in poses):
        raise ValueError('cache trials used different WORLD camera poses')
    results = {}
    for arm in ARMS:
        result = compare_schedule_repeats(trials[f'{arm}-0'], trials[f'{arm}-1'], seed, scene,
                                         'sequential_road_first')
        result.update(arm=arm, cache_runtime_control_is_experimental=True)
        results[arm] = result
    return {'status': 'NATIVE_SHADER_CACHE_CASE_VERIFIED', 'seed': seed, 'scenario': scene,
            'execution_order': list(order), 'independent_process_count': len(uuids),
            'arms': results, 'cache_process_receipts': metadata,
            'cross_cache_comparisons_are_different_conditions_not_repeatability_gates': True,
            'cross_cache_image_comparisons': {
                label: compare_schedule_repeats(trials[a], trials[b], seed, scene, 'sequential_road_first')
                for label, a, b in (
                    ('shared_cold_vs_isolated_cold', 'shared-0', 'isolated-0'),
                    ('shared_cold_vs_disabled_cold', 'shared-0', 'disabled-0'),
                    ('isolated_cold_vs_disabled_cold', 'isolated-0', 'disabled-0'),
                    ('shared_later_vs_isolated_cold', 'shared-1', 'isolated-1'))},
            'individual_cache_hits_proven': False, 'unique_renderer_cause_proven': False,
            'original_mdv3_repeatability_proven': False, 'onnx_inference_used': False,
            'model_scoring_allowed': False, 'real_vehicle_testing': False}


def aggregate_scenes(root: Path) -> dict:
    cases, uuids = [], set()
    for seed in SEEDS:
        for scene in SCENES:
            result = compare_case(root, seed, scene)
            stored = json.loads((scene_directory(root, seed, scene) / 'case_comparison.json').read_text())
            if result != stored:
                raise ValueError('stale or modified shader-cache case summary')
            for arm in result['arms'].values():
                for uid in arm['process_uuids']:
                    if uid in uuids:
                        raise ValueError('native process UUID reused across cache scenes')
                    uuids.add(uid)
            cases.append(result)
    return {'status': 'FOUR_NATIVE_SHADER_CACHE_SCENES_VERIFIED',
            'independent_process_count': len(uuids), 'per_scene': cases,
            'individual_cache_hits_proven': False, 'unique_renderer_cause_proven': False,
            'original_mdv3_repeatability_proven': False, 'onnx_inference_used': False,
            'model_scoring_allowed': False, 'real_vehicle_testing': False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('native-case', 'case', 'aggregate'), required=True)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--seed', type=int, choices=SEEDS)
    p.add_argument('--scene', choices=SCENES)
    p.add_argument('--out', type=Path)
    a = p.parse_args(argv)
    if a.mode != 'aggregate' and (a.seed is None or a.scene is None):
        p.error('case modes require --seed and --scene')
    if a.mode == 'native-case':
        result = run_case(a.root, a.seed, a.scene)
    elif a.mode == 'case':
        result = compare_case(a.root, a.seed, a.scene)
    else:
        result = aggregate_scenes(a.root)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        write_json(a.out, result)
    print(result['status'], result['independent_process_count'], flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
