"""Independently verify the 32-process static PSSM sampler experiment."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from scripts.compare_native_capture_schedule import validate_schedule_trial, compare_schedule_repeats
from scripts.compare_native_pssm_cross_process import SEEDS, SCENES, scene_directory, verified_hash_series, _matches
from scripts.native_shadow_sampler_probe import classify_binding

ARMS = {'original_off': ('original', False), 'original_probe': ('original', True),
        'raw_linear_off': ('raw_linear', False), 'raw_linear_probe': ('raw_linear', True)}
SHADER_SHA256 = '8eef67eb4384d6a74136b8e99b4c9bf0711e51ee88db7a248cd164c7a69f9ceb'
SCOPE = 'moved_pose_positive_control_after_all_primary_frames'


def duration(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def validate_sampler_trial(d: dict, seed: int, scene: str, arm: str) -> None:
    if arm not in ARMS:
        raise ValueError('unknown sampler arm')
    validate_schedule_trial(d, seed, scene, 'sequential_road_first')
    mode, enabled = ARMS[arm]
    diagnostic = d.get('shadow_sampler_diagnostic', {})
    c = diagnostic.get('configuration', {})
    if (c.get('mode') != mode or c.get('filters_before') != [6, 6]
            or c.get('filters_after') != ([1, 1] if mode == 'raw_linear' else [6, 6])
            or c.get('metadrive_version') != '0.4.3'
            or c.get('loaded_fragment_shader_sha256') != SHADER_SHA256
            or c.get('shader_edited') is not False
            or c.get('manual_pcf_sampler2d_confirmed') is not True
            or c.get('renderer_semantics_experimental') is not (mode != 'original')
            or not duration(diagnostic.get('terminal_diagnostic_wall_time_s'))
            or diagnostic.get('no_render_after_terminal_probe') is not True):
        raise ValueError('invalid or mislabeled PSSM sampler treatment')
    p = diagnostic.get('terminal_probe', {})
    rows = p.get('records')
    if (not isinstance(rows, list) or p.get('scope') != SCOPE
            or p.get('method') != 'terminal_inherited_state_zero_geometry_callback'
            or p.get('per_primitive_state_trace') is not False
            or p.get('primary_frames_instrumented') is not False
            or p.get('callbacks_removed') is not True
            or not duration(p.get('query_duration_s'))):
        raise ValueError('missing terminal-only probe isolation receipt')
    if not enabled:
        if p.get('status') != 'OFF' or rows or p['query_duration_s'] != 0:
            raise ValueError('OFF probe unexpectedly instrumented')
        return
    if (p.get('status') != 'TERMINAL_QUERY' or len(rows) != 4
            or any(sum(r.get('camera') == camera for r in rows) != 2
                   for camera in ('road', 'wide'))):
        raise ValueError('two terminal scene observations per camera required')
    expected = ('RAW_DEPTH_SAMPLER_CONSISTENT' if mode == 'raw_linear'
                else 'NONSHADOW_DEPTH_COMPARE_ENABLED')
    for row in rows:
        driver = row.get('driver', {})
        if (classify_binding(row) != expected or row.get('classification') != expected
                or row.get('min_filter') != 0x2601 or row.get('mag_filter') != 0x2601
                or not duration(row.get('query_duration_s'))
                or row['query_duration_s'] <= 0
                or any(not isinstance(driver.get(k), str) or not driver[k]
                       for k in ('vendor', 'renderer', 'version'))
                or row.get('comparison_state_source') !=
                   ('sampler_object' if row.get('sampler', 0) else 'texture')):
            raise ValueError('GPU state does not verify the claimed sampler treatment')
    if not math.isclose(sum(r['query_duration_s'] for r in rows), p['query_duration_s'],
                        rel_tol=1e-12, abs_tol=1e-9):
        raise ValueError('probe overhead summary differs from raw observations')


def image_comparison(a, b):
    return {'source_rgb': {k: _matches(verified_hash_series(a, 'source_rgb', k),
                                      verified_hash_series(b, 'source_rgb', k))
                           for k in ('road', 'wide')},
            'warped_rgb': {k: _matches(verified_hash_series(a, 'model_rgb', k),
                                      verified_hash_series(b, 'model_rgb', k))
                           for k in ('road', 'wide')},
            'i420': _matches(verified_hash_series(a, 'onnx_i420'),
                             verified_hash_series(b, 'onnx_i420'))}


def compare_scene(root: Path, seed: int, scene: str) -> dict:
    folder = scene_directory(root, seed, scene)
    results, trials, uuids, pids, poses = {}, {}, set(), set(), []
    for arm, (mode, enabled) in ARMS.items():
        pair = [json.loads((folder / f'{arm}-run_{i}.json').read_text()) for i in (0, 1)]
        for d in pair:
            validate_sampler_trial(d, seed, scene, arm)
            if d['process_uuid'] in uuids or d['process_id'] in pids:
                raise ValueError('all same-runner sampler trials require separate processes')
            uuids.add(d['process_uuid']); pids.add(d['process_id']); poses.append(d['camera_pose'])
        r = compare_schedule_repeats(*pair, seed, scene, 'sequential_road_first')
        r.update(arm=arm, sampler_mode=mode, terminal_probe_enabled=enabled,
                 is_original_sequential_control=mode == 'original',
                 sampler_change_is_experimental=mode != 'original',
                 terminal_observations=[d['shadow_sampler_diagnostic']['terminal_probe'] for d in pair])
        results[arm] = r
        trials[arm] = pair
    if any(p != poses[0] for p in poses):
        raise ValueError('sampler treatments used different WORLD poses')
    return {'status': 'NATIVE_SHADOW_SAMPLER_CASE_VERIFIED', 'seed': seed, 'scenario': scene,
            'arms': results, 'independent_process_count': len(uuids),
            'probe_off_on_primary_comparisons': {
                mode: [image_comparison(trials[mode + '_off'][i], trials[mode + '_probe'][i])
                       for i in (0, 1)] for mode in ('original', 'raw_linear')},
            'original_to_linear_primary_comparisons': {
                suffix: [image_comparison(trials['original_' + suffix][i], trials['raw_linear_' + suffix][i])
                         for i in (0, 1)] for suffix in ('off', 'probe')},
            'original_mdv3_repeatability_proven': False, 'unique_renderer_cause_proven': False,
            'onnx_inference_used': False, 'model_scoring_allowed': False, 'real_vehicle_testing': False}


def aggregate_scenes(root: Path) -> dict:
    cases, uuids = [], set()
    for seed in SEEDS:
        for scene in SCENES:
            r = compare_scene(root, seed, scene)
            stored = json.loads((scene_directory(root, seed, scene) / 'case_comparison.json').read_text())
            if r != stored:
                raise ValueError('stale or modified sampler case summary')
            for arm in r['arms'].values():
                for uid in arm['process_uuids']:
                    if uid in uuids:
                        raise ValueError('process UUID reused across sampler scenes')
                    uuids.add(uid)
            cases.append(r)
    return {'status': 'FOUR_NATIVE_SHADOW_SAMPLER_SCENES_VERIFIED',
            'independent_process_count': len(uuids), 'per_scene': cases,
            'original_mdv3_repeatability_proven': False, 'unique_renderer_cause_proven': False,
            'onnx_inference_used': False, 'model_scoring_allowed': False, 'real_vehicle_testing': False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--mode', choices=('case', 'aggregate'), required=True)
    p.add_argument('--seed', type=int, choices=SEEDS)
    p.add_argument('--scene', choices=SCENES)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(argv)
    result = compare_scene(a.root, a.seed, a.scene) if a.mode == 'case' else aggregate_scenes(a.root)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(result['status'], result['independent_process_count'], flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
