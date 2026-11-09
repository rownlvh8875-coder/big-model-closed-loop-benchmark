"""Run geometry-only target-lane evaluation against actual native MetaDrive lanes.

No driving model, road control, vehicle dynamics or real car hardware. This
checks the evaluation math on native curve/ramp objects, independently of the
camera pixel evidence.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from bigbench.curved_lane_scenarios import SCENARIOS, select_native_curve_lanes
from bigbench.lane_truth import evaluate_target_lane_by_id, summarize_lane_truth
from bigbench.metadrive_camera import NativeMetaDriveProvider


def check_native_lane(lane) -> dict:
    """Check lane center and intentional virtual footprint intrusion."""
    target = str(getattr(lane, 'index', ''))
    if not target or target == 'None':
        raise ValueError('native target lane has no unique index')
    center_samples = []
    intrusion_samples = []
    for proportion in (.2, .5, .8):
        s = float(lane.length) * proportion
        heading = float(lane.heading_theta_at(s))
        center = lane.position(s, 0.)
        c = evaluate_target_lane_by_id([lane], target, float(center[0]),
                                       float(center[1]), heading)
        width = float(lane.width_at(s))
        if width <= 0 or not math.isfinite(width):
            raise ValueError('native lane width is invalid')
        # Deliberately move common geometric agent 0.2m across right paint.
        lateral = width / 2 - 0.9 + 0.2
        edge = lane.position(s, lateral)
        o = evaluate_target_lane_by_id([lane], target, float(edge[0]),
                                       float(edge[1]), heading)
        center_samples.append(c)
        intrusion_samples.append(o)
        if abs(c.signed_lateral_right_m) > .05 or abs(c.longitudinal_m - s) > .1:
            raise ValueError('native centerline coordinate is not self-consistent')
        if abs(o.signed_lateral_right_m - lateral) > .05:
            raise ValueError('native right-positive lane coordinate is inconsistent')
        if abs(o.intrusion_depth_m - .2) > .05:
            raise ValueError('common ideal agent intrusion depth differs from analytic expectation')
    report = summarize_lane_truth(intrusion_samples, dt_s=.05)
    if report['intrusion_count'] != 1 or abs(report['intrusion_duration_s']-.15) > 1e-8:
        raise ValueError('native lane intrusion event/duration aggregation mismatch')
    return {
        'target_lane_id': target,
        'native_lane_length_m': float(lane.length),
        'native_lane_radius_m': float(getattr(lane,'radius',0)),
        'center_samples': [x.to_dict() for x in center_samples],
        'right_edge_samples': [x.to_dict() for x in intrusion_samples],
        'intrusion_summary': report,
        'status': 'PASS_NATIVE_TARGET_LANE_GEOMETRY_GATE',
    }


def audit_native_lane_truth(*, output: Path, names: list[str], seed: int,
                            strict: bool = True) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    cases = {}
    for name in names:
        if name not in SCENARIOS:
            raise ValueError('unknown native MetaDrive scenario: '+name)
        case = SCENARIOS[name]
        provider = None
        try:
            provider = NativeMetaDriveProvider(seed=seed,map_config=case.map_config())
            lanes = select_native_curve_lanes(provider.env.current_map,case)
            if not lanes:
                raise ValueError('no native curve/ramp lane geometry')
            if len({str(lane.index) for lane in lanes}) != len(lanes):
                raise ValueError('native target lane ids are not unique')
            receipts = [check_native_lane(lane) for lane in lanes]
            cases[name] = {
                'status':'PASS_NATIVE_TARGET_LANE_GEOMETRY_GATE',
                'tested_lanes':len(receipts),
                'samples_per_lane':3,
                'receipts':receipts,
            }
        except Exception as exc:
            cases[name] = {
                'status':'INCONCLUSIVE_OR_MISMATCH',
                'error':f'{type(exc).__name__}: {exc}',
            }
        finally:
            if provider is not None:
                provider.close()
        print('NATIVE_TARGET_LANE_RESULT',name,cases[name]['status'],
              cases[name].get('error',''),flush=True)
    result = {
        'phase':2,
        'scope':'SYNTHETIC_NATIVE_METADRIVE_CURVE_RAMP_GROUND_TRUTH',
        'real_vehicle_testing':False,
        'model_scoring_allowed':False,
        'cd210_or_carrot_tuning':False,
        'seed':seed,
        'scenario_results':cases,
        'all_pass':bool(cases) and all(
            r['status']=='PASS_NATIVE_TARGET_LANE_GEOMETRY_GATE'
            for r in cases.values()),
    }
    (output/'native_lane_truth_report.json').write_text(
        json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',
        encoding='utf-8')
    if strict and not result['all_pass']:
        raise RuntimeError('native lane truth evaluation failed; inspect JSON report')
    return result


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description='Native MetaDrive target-lane truth audit, simulation only')
    p.add_argument('--out',type=Path,default=Path('output/metadrive-lane-truth'))
    p.add_argument('--seed',type=int,default=20261109)
    p.add_argument('--scenarios',nargs='+',choices=sorted(SCENARIOS),default=list(SCENARIOS))
    p.add_argument('--allow-inconclusive',action='store_true')
    a=p.parse_args(argv)
    audit_native_lane_truth(output=a.out,names=a.scenarios,seed=a.seed,
                            strict=not a.allow_inconclusive)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
