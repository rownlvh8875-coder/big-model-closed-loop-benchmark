"""Cross-renderer landmark comparison protocol: requires TWO actual engines.

This pure evaluator does not launch CARLA or MetaDrive. It refuses to label
two copies of one simulator as an independent cross-engine validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot,isfinite


class CrossEngineError(ValueError):
    pass


@dataclass(frozen=True)
class LandmarkMeasurement:
    world_id: str
    u_model_px: float
    v_model_px: float

    def __post_init__(self):
        if not self.world_id or not all(isfinite(x) for x in (self.u_model_px,self.v_model_px)):
            raise CrossEngineError('invalid optical landmark')


@dataclass(frozen=True)
class EngineReceipt:
    engine: str
    revision: str
    scenario_geometry_id: str
    camera_profile: str
    observed: tuple[LandmarkMeasurement,...]
    real_renderer_executed: bool

    def __post_init__(self):
        if not all((self.engine,self.revision,self.scenario_geometry_id,self.camera_profile)):
            raise CrossEngineError('engine provenance is mandatory')
        ids=[x.world_id for x in self.observed]
        if len(ids)!=len(set(ids)):
            raise CrossEngineError('duplicate landmark identities')


def compare_engine_landmarks(first: EngineReceipt, second: EngineReceipt, *,
                             max_median_error_px: float=5.) -> dict:
    if first.engine==second.engine:
        raise CrossEngineError('distinct real rendering engines required')
    if not first.real_renderer_executed or not second.real_renderer_executed:
        raise CrossEngineError('both engines must have REAL rendering evidence')
    if first.scenario_geometry_id!=second.scenario_geometry_id or first.camera_profile!=second.camera_profile:
        raise CrossEngineError('scenario geometry and camera profiles must be identical')
    if not isfinite(max_median_error_px) or max_median_error_px<=0:
        raise CrossEngineError('invalid predeclared optical residual threshold')
    a={x.world_id:x for x in first.observed};b={x.world_id:x for x in second.observed}
    matched=sorted(set(a)&set(b))
    if len(matched)<5:
        raise CrossEngineError('insufficient shared 3D world landmarks')
    errors=sorted(hypot(a[k].u_model_px-b[k].u_model_px,
                        a[k].v_model_px-b[k].v_model_px) for k in matched)
    n=len(errors)
    median=(errors[n//2] if n%2 else (errors[n//2-1]+errors[n//2])/2)
    return {
        'classification':'CROSS_ENGINE_GEOMETRY_ONLY_NOT_DRIVING_MODEL_SCORE',
        'first_engine':first.engine,'second_engine':second.engine,
        'matched_landmarks':n,'median_disagreement_px':median,
        'status':'CROSS_ENGINE_LANDMARK_GATE_PASS' if median<=max_median_error_px
                 else 'CROSS_ENGINE_LANDMARK_MISMATCH',
        'model_scoring_allowed':False,'real_vehicle_testing':False,
        'warning':'No model performance inference from camera landmark agreement',
    }
