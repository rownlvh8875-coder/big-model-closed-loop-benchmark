"""Reproduce the illustrative 19-condition score from the comparison JSON."""

import argparse
import json
from pathlib import Path

FULL_S = ('lateral', 'integrated55', 'integrated45')
MODELS = ('fairy-tale', 'light-speed-2', 'light-speed', 'md-v3')
LONGITUDINAL = {'lead_brake': 240, 'stop_go': 240, 'cut_in': 200}
CASE_GRID = {(seed, scene) for seed in (20261109, 20261110)
             for scene in ('s_curve_left_right', 's_curve_right_left')}
RAMP_GRID = {(seed, scene) for seed in (20261109, 20261110)
             for scene in ('in_ramp', 'out_ramp')}


def keyed_cases(rows, expected, *, compare=False):
    keys = {(row['seed'], row['scenario']) for row in rows}
    if keys != expected or len(rows) != len(expected):
        raise ValueError('the comparison must contain each registered condition exactly once')
    if compare and any(row['comparable'] is not True for row in rows):
        raise ValueError('the comparison contains an unverified common input')
    return rows


def traversal(rows):
    outcome = [row['traversal_passed'] for row in rows]
    if any(type(value) is not bool for value in outcome):
        raise ValueError('the comparison contains an unverified traversal')
    return sum(outcome)


def calculate(report):
    if set(report['model_sha256']) != set(MODELS):
        raise ValueError('score requires all four registered models')
    full_s = {}
    for name in FULL_S:
        grid = ({(seed, scene+'_radius45') for seed, scene in CASE_GRID}
                if name == 'integrated45' else CASE_GRID)
        full_s[name] = keyed_cases(report[name], grid, compare=True)
    if report['ramp']['camera_pairs_verified'] != 4:
        raise ValueError('the ramp cohort requires all four qualified camera conditions')
    rows = report['longitudinal']
    if ({r['scenario'] for r in rows} != LONGITUDINAL.keys()
            or len(rows) != len(LONGITUDINAL)
            or any(row['seed'] != 20261109 or row['comparable'] is not True for row in rows)):
        raise ValueError('score requires all three comparable longitudinal conditions')
    result = {}
    for model in MODELS:
        counts = {key: traversal([row['models'][model] for row in values]) for key, values in full_s.items()}
        ramp = keyed_cases(report['ramp']['models'][model]['cases'], RAMP_GRID)
        counts['ramps'] = traversal(ramp)
        counts['longitudinal'] = 0
        for case in rows:
            trial = case['models'][model]
            if trial['status'] != 'VERIFIED':
                raise ValueError('score requires verified longitudinal trial results')
            passed = (trial['termination'] == 'STEP_LIMIT'
                      and trial['steps'] == LONGITUDINAL[case['scenario']]
                      and trial['minimum_synthetic_gap_m'] > 0)
            counts['longitudinal'] += passed
        earned = sum(counts.values())
        full_s_passes = sum(counts[name] for name in FULL_S)
        result[model] = {
            'passed_conditions': counts,
            'points': earned,
            'score_out_of_100': round(100*earned/19, 1),
            'illustration_heavier_ramp_weight': round(20*full_s_passes/12 + 60*counts['ramps']/4
                                                      + 20*counts['longitudinal']/3, 1),
        }
    return {'protocol': 'sdk3-illustrative-score-v1', 'engine': report['runtime'],
            'conditions_per_model': 19, 'basis': 'equal weight per condition',
            'alternate_weights_percent': {'full_s':20, 'ramps':60, 'longitudinal':20}, 'models': result}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('comparison', nargs='?', type=Path,
                        default=Path(__file__).with_name('comparison.json'))
    print(json.dumps(calculate(json.loads(parser.parse_args().comparison.read_bytes())), indent=2))
