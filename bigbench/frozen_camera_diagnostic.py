"""Isolate stateful ONNX repeatability using ONE frozen actual MetaDrive RGB pair.

This is intentionally OPEN-LOOP camera input (replayed fixed pixels). It must
never be marked as native image feedback or a driving-model performance score.
The two independent ONNX sessions run the same source pixels and state-reset
sequence; any mismatch cannot be blamed on new MetaDrive rendered frames.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Any

from .camera_rig import SchematicPair
from .native_model_campaign import CampaignSpec,run_target_lane_episode
from .reproducibility import compare_repeat_receipts


@dataclass
class FrozenCamera:
    pair: SchematicPair
    calls: int = 0

    def capture(self, pose: Any) -> SchematicPair:
        self.calls += 1
        return self.pair


def isolate_model_repeatability(*, make_policy, native_camera: Any,
                                lane: Any, spec: CampaignSpec) -> dict:
    """Capture native RGB ONCE; invoke two new ONNX sessions with fixed pixels."""
    initial_s=float(lane.length)*spec.initial_fraction
    xy=lane.position(initial_s,0.)
    from .kinematics import AgentState
    start=AgentState(0.,float(xy[0]),float(xy[1]),
                     float(lane.heading_theta_at(initial_s)),spec.speed_mps)
    pair=native_camera.capture(start)
    if pair.road.sha256==pair.wide.sha256:
        raise ValueError('native paired camera views unexpectedly identical')
    reports=[]
    for i in range(2):
        policy=make_policy()
        frozen=FrozenCamera(pair)
        receipt=run_target_lane_episode(policy,frozen,lane,spec)
        receipt['frozen_camera_calls']=frozen.calls
        receipt['run_index']=i
        receipt['camera_mode']='ONE_NATIVE_RGB_CAPTURE_REPLAYED_OPEN_LOOP_FOR_INFERENCE_ISOLATION'
        receipt['model_scoring_allowed']=False
        reports.append(receipt)
        if receipt['status']!='DIAGNOSTIC_EXECUTED':
            break
    status='INCOMPLETE'
    comparison=None
    action_bit_exact=None
    max_lateral_action_delta=None
    max_longitudinal_action_delta=None
    if len(reports)==2 and all(x['status']=='DIAGNOSTIC_EXECUTED' for x in reports):
        comparison=compare_repeat_receipts(reports[0],reports[1],pose_tol_m=1e-7)
        a_frames,b_frames=reports[0]['frames'],reports[1]['frames']
        actions_a=[(f['desired_curvature_1pm'],f['desired_acceleration_mps2']) for f in a_frames]
        actions_b=[(f['desired_curvature_1pm'],f['desired_acceleration_mps2']) for f in b_frames]
        action_bit_exact=actions_a==actions_b
        max_lateral_action_delta=max(abs(x[0]-y[0]) for x,y in zip(actions_a,actions_b))
        max_longitudinal_action_delta=max(abs(x[1]-y[1]) for x,y in zip(actions_a,actions_b))
        status=(comparison['status'] if action_bit_exact else 'ONNX_ACTION_OUTPUT_MISMATCH')
        comparison['action_values_exactly_equal']=action_bit_exact
        comparison['max_curvature_delta_1pm']=max_lateral_action_delta
        comparison['max_accel_delta_mps2']=max_longitudinal_action_delta
    return {
        'classification':('OPEN_LOOP_FIXED_NATIVE_RGB_ONNX_REPRODUCIBILITY_ONLY'
                          if reports and reports[0].get('model_sha256')
                          else 'OPEN_LOOP_FIXED_RGB_TEST_DOUBLE_NOT_ONNX'),
        'status':status,
        'camera_captured_once':True,
        'camera_pixels_replayed':True,
        'actual_closed_loop_camera_feedback':False,
        'model_scoring_allowed':False,
        'real_vehicle_testing':False,
        'model_sha256':reports[0].get('model_sha256') if reports else None,
        'source_camera_sha256':{
            'road':pair.road.sha256,'wide':pair.wide.sha256,
        },
        'comparison':comparison,
        'model_action_values_exactly_equal':action_bit_exact,
        'max_curvature_delta_1pm':max_lateral_action_delta,
        'max_acceleration_delta_mps2':max_longitudinal_action_delta,
        'runs':reports,
    }
