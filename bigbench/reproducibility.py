"""Repeatability gate for synthetic long-run model/camera receipts.

Does not invent a repeat run, automatic cross-engine equivalence, actual
camera calibration, or real-road safety claims. No vehicle-specific physics.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any


class ReproducibilityError(ValueError):
    pass


def canonical_digest(value: Any) -> str:
    try:
        payload=json.dumps(value,sort_keys=True,separators=(',',':'),
                           allow_nan=False,ensure_ascii=False).encode('utf-8')
    except (ValueError,TypeError) as exc:
        raise ReproducibilityError('noncanonical reproducibility payload') from exc
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class RepeatSpec:
    model_sha256: str
    scenario: str
    seeds: tuple[int,...]
    initial_speeds_mps: tuple[float,...]
    steps: int
    dt_s: float = .05
    renderer: str = 'MetaDrive-0.4.3-ideal-pinhole'

    def __post_init__(self):
        import re
        if not re.fullmatch(r'[0-9a-f]{64}',self.model_sha256):
            raise ReproducibilityError('pinned weight sha256 required')
        if not self.scenario or type(self.steps) is not int or self.steps<=0 or self.steps>2000:
            raise ReproducibilityError('invalid scenario or bounded steps')
        if not self.seeds or len(set(self.seeds))!=len(self.seeds) or any(type(s) is not int for s in self.seeds):
            raise ReproducibilityError('unique integer seeds required')
        if not self.initial_speeds_mps or any(not math.isfinite(v) or v<=0 or v>35 for v in self.initial_speeds_mps):
            raise ReproducibilityError('invalid common virtual speeds')
        if abs(self.dt_s-.05)>1e-12:
            raise ReproducibilityError('model clock must remain 20 Hz')
        if not self.renderer:
            raise ReproducibilityError('renderer identity required')


def planned_trials(spec: RepeatSpec) -> dict:
    matrix=[{'model_sha256':spec.model_sha256,'scenario':spec.scenario,
             'seed':seed,'speed_mps':speed,'steps':spec.steps,
             'dt_s':spec.dt_s,'renderer':spec.renderer}
            for seed in spec.seeds for speed in spec.initial_speeds_mps]
    return {'status':'PLAN_ONLY_NO_TRIALS_EXECUTED',
            'real_vehicle_testing':False,'model_scoring_allowed':False,
            'trial_count_planned':len(matrix),'manifest_sha256':canonical_digest(matrix),
            'trials':matrix}


def compare_repeat_receipts(first: dict, second: dict, *,
                            pose_tol_m: float=1e-5) -> dict:
    if not math.isfinite(pose_tol_m) or pose_tol_m<0 or pose_tol_m>1:
        raise ReproducibilityError('pose tolerance out of range')
    exact=('model_sha256','scenario','seed','requested_steps','completed_steps')
    if any(first.get(k)!=second.get(k) for k in exact):
        raise ReproducibilityError('repeat identities differ')
    if first.get('status')!='DIAGNOSTIC_EXECUTED' or second.get('status')!='DIAGNOSTIC_EXECUTED':
        raise ReproducibilityError('incomplete diagnostics cannot pass repeatability')
    a=first.get('frames',[])
    b=second.get('frames',[])
    if not a or len(a)!=len(b):
        raise ReproducibilityError('missing/mismatched frame count')
    if [r.get('time_s') for r in a]!=[r.get('time_s') for r in b]:
        raise ReproducibilityError('different virtual time grid')
    errors=[]
    for rowa,rowb in zip(a,b):
        if any(not isinstance(row.get(k),(int,float)) or not math.isfinite(row[k])
               for k in ('world_x_m','world_y_m') for row in (rowa,rowb)):
            raise ReproducibilityError('missing or nonfinite world pose')
        errors.append(math.hypot(rowa['world_x_m']-rowb['world_x_m'],
                                 rowa['world_y_m']-rowb['world_y_m']))
    frame_equal=all(aa.get('road_frame_sha256')==bb.get('road_frame_sha256') and
                    aa.get('wide_frame_sha256')==bb.get('wide_frame_sha256')
                    for aa,bb in zip(a,b))
    passed=max(errors)<=pose_tol_m and frame_equal
    return {'status':'SYNTHETIC_REPEATED_DIAGNOSTIC_MATCH' if passed else 'REPEATED_DIAGNOSTIC_MISMATCH',
            'repeatability_checked':True,'max_pose_disagreement_m':max(errors),
            'frame_hashes_identical':frame_equal,
            'model_scoring_allowed':False,'real_vehicle_testing':False,
            'first_digest':canonical_digest(first),'second_digest':canonical_digest(second),
            'warning':'Only identical engine/inputs reproducibility; no CARLA or real-world validation',
           }
