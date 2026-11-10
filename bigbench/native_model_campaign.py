"""Native MetaDrive large-ONNX diagnostic with explicit target-lane ground truth.

No real vehicle, no CD210 and no Carrot controller. A short, bounded native
curve segment is used first. Camera/renderer photometric fidelity is not
established: no driving model *ranking* is authorized by this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import math
from pathlib import Path
from typing import Any

import numpy as np

from .camera import RGBFrame
from .camera_rig import SchematicPair
from .curved_lane_scenarios import SCENARIOS, select_native_curve_lanes
from .kinematics import AgentState, ModelAction, step_ideal
from .lane_truth import LaneTruthError, evaluate_target_lane_by_id, summarize_lane_truth
from .optical_calibration import PinholeRectifier, intrinsics_from_panda_lens
from .policies import ModelObservation


class BenchmarkProtocolError(ValueError):
    pass


@dataclass(frozen=True)
class CampaignSpec:
    scenario: str
    seed: int = 20261109
    steps: int = 12
    speed_mps: float = 8.0
    dt_s: float = .05
    fixed_speed: bool = True
    initial_fraction: float = .12

    def __post_init__(self):
        if self.scenario not in SCENARIOS:
            raise BenchmarkProtocolError('unknown native curve/ramp scene')
        if type(self.seed) is not int or type(self.steps) is not int or not 2 <= self.steps <= 2000:
            raise BenchmarkProtocolError('seed or bounded steps invalid')
        values=(self.speed_mps,self.dt_s,self.initial_fraction)
        if not all(math.isfinite(v) for v in values):
            raise BenchmarkProtocolError('nonfinite comparison configuration')
        if not 0 < self.speed_mps <= 35 or self.dt_s != .05 or not 0 <= self.initial_fraction <= .75:
            raise BenchmarkProtocolError('invalid fixed virtual timestep/speed/start')


class NativeWorldCamera:
    """Real Panda3D MetaDrive camera borrowed into WORLD space, not vehicle space."""
    def __init__(self, provider: Any):
        self.provider=provider
        self.last_source_rgb_sha256: dict[str, str] = {}
        self.rectifier=PinholeRectifier(source_width=provider.source_width,
                                        source_height=provider.source_height)

    def capture(self, pose: AgentState) -> SchematicPair:
        env=self.provider.env
        if env is None:
            raise BenchmarkProtocolError('native MetaDrive renderer closed')
        if not all(math.isfinite(v) for v in (pose.x,pose.y,pose.heading)):
            raise BenchmarkProtocolError('invalid virtual camera world pose')
        img={}
        raw_sha={}
        matrices={}
        # MetaDrive's camera faces local +Y. World-heading zero (+X)
        # therefore corresponds to Panda heading -90 degrees.
        position=(pose.x,pose.y,self.provider.height_m)
        hpr=(math.degrees(pose.heading)-90.0,0.,0.)
        for kind in ('road','wide'):
            cam=env.engine.sensors['bigbench_'+kind]
            raw=cam.perceive(to_float=False,new_parent_node=env.engine.origin,
                             position=position,hpr=hpr)
            if not isinstance(raw,np.ndarray):
                raw=raw.get()
            # Snapshot EACH native sensor immediately, before another camera
            # task tick. Hash the actual 964x604 RGB bytes, before any warp.
            img[kind]=np.array(raw,copy=True,order='C')
            if img[kind].dtype != np.uint8 or img[kind].shape != (
                    self.provider.source_height,self.provider.source_width,3):
                raise BenchmarkProtocolError('unexpected raw MetaDrive sensor RGB shape/dtype')
            raw_sha[kind]=sha256(img[kind].tobytes(order='C')).hexdigest()
            matrices[kind]=intrinsics_from_panda_lens(cam.get_lens(),
                                self.provider.source_width,self.provider.source_height)
        pair,_=self.rectifier.rectify_pair(img['road'],img['wide'],
                        road_intrinsics=matrices['road'],wide_intrinsics=matrices['wide'])
        self.last_source_rgb_sha256=raw_sha
        return pair


def run_target_lane_episode(policy: Any, camera: Any, lane: Any,
                            spec: CampaignSpec, route: Any | None = None) -> dict:
    """Run fixed-speed lateral-only model feedback on a preselected NATIVE lane.

    At every step: rendered RGB -> ONNX action -> common kinematics ->
    target-lane geometric truth. Ground truth NEVER appears in ModelObservation.
    Failure remains a failed diagnostic; no alternate-lane fallback.
    """
    index=str(getattr(lane,'index',''))
    if not index or index=='None':
        raise BenchmarkProtocolError('explicit native target lane ID required')
    s=float(lane.length)*spec.initial_fraction
    xy=lane.position(s,0.)
    state=AgentState(0.,float(xy[0]),float(xy[1]),
                     float(lane.heading_theta_at(s)),spec.speed_mps)
    if route is not None and (not getattr(route,'lanes',None) or route.lanes[0] is not lane):
        raise BenchmarkProtocolError('explicit native route must start on the chosen lane')
    policy.reset()
    rows=[]
    truths=[]
    failure=None
    try:
        for i in range(spec.steps):
            pair=camera.capture(state)
            source_sha=getattr(camera,'last_source_rgb_sha256',{})
            if pair.road.sha256==pair.wide.sha256:
                raise BenchmarkProtocolError('road/wide camera unexpectedly identical')
            action=policy.step(ModelObservation(pair.road,state.speed,state.t,
                                                wide_frame=pair.wide))
            if not isinstance(action,ModelAction) or not all(
                math.isfinite(v) for v in (action.curvature_1pm,action.acceleration_mps2)):
                raise BenchmarkProtocolError('invalid raw model action')
            after=step_ideal(state,action,spec.dt_s,
                             speed_override=spec.speed_mps if spec.fixed_speed else None)
            truth=(route.evaluate(after.x,after.y,after.heading)
                   if route is not None
                   else evaluate_target_lane_by_id([lane],index,after.x,after.y,after.heading))
            truths.append(truth)
            rows.append({
                'step':i+1,'time_s':after.t,'world_x_m':after.x,'world_y_m':after.y,
                'heading_rad':after.heading,'speed_mps':after.speed,
                'desired_curvature_1pm':action.curvature_1pm,
                'desired_acceleration_mps2':action.acceleration_mps2,
                'target_lane_id':truth.lane_id,'lateral_right_m':truth.signed_lateral_right_m,
                'inside_turn_offset_m':truth.inside_turn_offset_m,
                'lane_intrusion_m':truth.intrusion_depth_m,
                'road_frame_sha256':pair.road.sha256,'wide_frame_sha256':pair.wide.sha256,
                'source_road_rgb_sha256':source_sha.get('road'),
                'source_wide_rgb_sha256':source_sha.get('wide'),
            })
            state=after
    except (LaneTruthError,BenchmarkProtocolError,ValueError,RuntimeError) as exc:
        failure=f'{type(exc).__name__}: {exc}'
    if not rows and failure is None:
        raise BenchmarkProtocolError('empty native model execution')
    quality=summarize_lane_truth(truths,dt_s=spec.dt_s) if truths else None
    return {
        'status':'DIAGNOSTIC_EXECUTED' if failure is None and len(rows)==spec.steps else 'FAILED_OR_INCOMPLETE',
        'error':failure,'scenario':spec.scenario,'seed':spec.seed,
        'requested_steps':spec.steps,'completed_steps':len(rows),
        'model_label':policy.name,
        'model_sha256':getattr(getattr(policy,'contract',None),'sha256',None),
        'evidence_class':'NATIVE_METADRIVE_PINHOLE_MODEL_DIAGNOSTIC_NOT_VALIDATED_RANKING'
                         if not getattr(policy,'is_mock',True)
                         else 'MOCK_POLICY_TEST_ONLY',
        'model_scoring_allowed':False,
        'real_vehicle_testing':False,'cd210_fallback':False,'carrot_tuning_used':False,
        'lane_truth':quality,'frames':rows,
    }


def run_native_episode(policy: Any, spec: CampaignSpec, *,
                       full_s_route: bool = False,
                       camera_convergence: int = 0,
                       camera_pixel_tolerance: int = 0,
                       camera_rgb_delta: int = 0) -> dict:
    """Create fresh identical native world per model: never share model state."""
    if type(camera_convergence) is not int or (camera_convergence!=0 and not 2<=camera_convergence<=12):
        raise BenchmarkProtocolError('camera convergence bound must be 0 or 2..12')
    if (not camera_convergence and (camera_pixel_tolerance or camera_rgb_delta)):
        raise BenchmarkProtocolError('pixel tolerance requires explicit multi-capture experiment')
    from .metadrive_camera import NativeMetaDriveProvider
    provider=NativeMetaDriveProvider(seed=spec.seed,map_config=SCENARIOS[spec.scenario].map_config())
    try:
        lanes=select_native_curve_lanes(provider.env.current_map,SCENARIOS[spec.scenario])
        if not lanes:
            raise BenchmarkProtocolError('scene does not contain a native curve')
        route=None
        if full_s_route:
            if not SCENARIOS[spec.scenario].expected_curve_directions or len(lanes)!=2:
                raise BenchmarkProtocolError('full native route requires two S-curve bends')
            from .native_route import NativeRouteProgress,forward_contiguous_chain
            chain=forward_contiguous_chain(provider.env.current_map.road_network,
                                           lanes[0],str(lanes[1].index))
            route=NativeRouteProgress(chain)
        renderer=NativeWorldCamera(provider)
        if camera_convergence:
            from .camera_convergence import StrictConsecutiveCamera
            renderer=StrictConsecutiveCamera(renderer,max_captures=camera_convergence,
                                             max_changed_pixels=camera_pixel_tolerance,
                                             max_rgb_delta=camera_rgb_delta)
        out=run_target_lane_episode(policy,renderer,lanes[0],spec,route=route)
        out['strict_same_pose_convergence']={
            'enabled':bool(camera_convergence),
            'max_captures':camera_convergence,
            'sample_count':len(renderer.receipts) if camera_convergence else 0,
            'max_attempts_observed':renderer.max_attempts_observed if camera_convergence else 0,
            'failed_samples':sum(not x.stable for x in renderer.receipts) if camera_convergence else 0,
            'pixel_tolerance_count':camera_pixel_tolerance,
            'pixel_channel_delta_tolerance':camera_rgb_delta,
            'maximum_changed_pixels_accepted':(
                max((max(q.road_changed_pixels,q.wide_changed_pixels)
                     for q in renderer.receipts if q.stable),default=0)
                if camera_convergence else 0),
            'classification':('EXPERIMENTAL_TOLERANT_CAMERA_NOT_BIT_EXACT'
                 if camera_pixel_tolerance else 'EXPERIMENTAL_MULTI_CAPTURE_NOT_NATIVE_CAMERA_EQUIVALENT'),
        }
        out['explicit_route_lane_ids']=[str(z.index) for z in route.lanes] if route else [str(lanes[0].index)]
        out['full_s_route_requested']=full_s_route
        return out
    finally:
        provider.close()


def compare_episode_receipts(first: dict,second: dict) -> dict:
    """Pair only if both completed on the EXACT same scene and clock.

    This is an engineering diagnostic comparison, not a ranking. The
    inputs diverge after actions because feedback is genuinely closed loop.
    """
    fields=('scenario','seed','requested_steps','completed_steps')
    if any(first.get(f)!=second.get(f) for f in fields):
        raise BenchmarkProtocolError('paired simulations have different conditions')
    if first.get('status')!='DIAGNOSTIC_EXECUTED' or second.get('status')!='DIAGNOSTIC_EXECUTED':
        raise BenchmarkProtocolError('cannot compare incomplete or failed runs')
    frames_a,frames_b=first['frames'],second['frames']
    if [r['time_s'] for r in frames_a]!=[r['time_s'] for r in frames_b]:
        raise BenchmarkProtocolError('different virtual timestamps')
    return {
        'classification':'TWO_ONNX_NATIVE_METADRIVE_TECHNICAL_COMPARISON_ONLY',
        'model_scoring_allowed':False,'real_vehicle_testing':False,
        'scenario':first['scenario'],'steps':len(frames_a),
        'models':[first['model_label'],second['model_label']],
        'max_abs_lateral_error_m':[first['lane_truth']['absolute_lateral_error_max_m'],
                                   second['lane_truth']['absolute_lateral_error_max_m']],
        'max_intrusion_m':[first['lane_truth']['intrusion_depth_max_m'],
                           second['lane_truth']['intrusion_depth_max_m']],
        'first_camera_sha_equal': frames_a[0]['road_frame_sha256']==frames_b[0]['road_frame_sha256'],
        'warning':'Raw virtual geometry diagnostics ONLY. No driving quality rank/real vehicle generalization.',
    }
