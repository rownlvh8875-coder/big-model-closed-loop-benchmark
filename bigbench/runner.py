"""Closed-loop orchestration: changed actions -> new pose -> new camera frame."""
from __future__ import annotations
from dataclasses import dataclass
from .camera import SchematicCamera, RGBFrame
from .geometry import RoadPoint
from .kinematics import AgentState, ModelAction, step_ideal
from .metrics import FrameMetric, summarize
from .policies import DrivingPolicy, ModelObservation
from .scenario import Scenario

MODEL_DT_S = 0.05   # 20 Hz is a benchmark configuration, not a real-time claim.
GENERIC_AGENT_HALF_WIDTH_M = 0.9  # Geometric reference footprint only; NOT vehicle dimensions.


@dataclass
class BenchmarkRun:
    model_name: str
    scenario_name: str
    classification: str
    frames: list[FrameMetric]
    summary: dict
    first_frame: RGBFrame
    last_frame: RGBFrame


def run_episode(scenario: Scenario, policy: DrivingPolicy, *,
                dt_s: float = MODEL_DT_S, fixed_speed: bool = True,
                camera: SchematicCamera | None = None) -> BenchmarkRun:
    if dt_s <= 0 or dt_s > 0.25:
        raise ValueError('invalid benchmark timestep')
    if scenario.duration_s / dt_s > 20000:
        raise ValueError('benchmark run too long')
    renderer = camera or SchematicCamera()
    policy.reset()
    p: RoadPoint = scenario.road.at(0)
    state = AgentState(0, p.x, p.y, p.heading, scenario.initial_speed_mps)
    station = 0.0
    frames: list[FrameMetric] = []
    initial_frame: RGBFrame | None = None
    last_frame: RGBFrame | None = None
    steps = round(scenario.duration_s / dt_s)
    if abs(steps * dt_s - scenario.duration_s) > 1e-9:
        raise ValueError('scenario duration must be a multiple of dt_s')
    for _ in range(steps):
        # Reprojection closes the actual observation loop. Model only sees RGB + time + speed.
        rgb = renderer.render(scenario, state, station)
        if initial_frame is None:
            initial_frame = rgb
        action: ModelAction = policy.step(ModelObservation(rgb, state.speed, state.t))
        state = step_ideal(state, action, dt_s,
                           speed_override=scenario.initial_speed_mps if fixed_speed else None)
        station, lateral, curvature = scenario.road.project(state.x, state.y, station)
        intrusion = max(0.0, abs(lateral) + GENERIC_AGENT_HALF_WIDTH_M - scenario.lane_width_m / 2)
        lead_gap = scenario.lead.station(state.t) - station if scenario.lead else None
        frames.append(FrameMetric(state.t, station, state.speed, lateral,
                                  lateral * (1 if curvature > 1e-6 else -1 if curvature < -1e-6 else 0),
                                  curvature, action.curvature_1pm, action.acceleration_mps2,
                                  lead_gap, intrusion, rgb.sha256))
        last_frame = rgb
    assert initial_frame and last_frame
    return BenchmarkRun(policy.name, scenario.name, 'SYNTHETIC_MOCK_ONLY' if policy.is_mock else 'UNVERIFIED_MODEL',
                        frames, summarize(frames, dt_s), initial_frame, last_frame)
