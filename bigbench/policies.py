"""Camera-only mock policies for testing simulator wiring.

These policies are NOT real big driving models; never include them in a model ranking.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from .camera import RGBFrame
from .kinematics import ModelAction


@dataclass(frozen=True)
class ModelObservation:
    frame: RGBFrame
    speed_mps: float
    time_s: float
    wide_frame: RGBFrame | None = None
    nav_inputs: dict | None = None


class DrivingPolicy(Protocol):
    name: str
    is_mock: bool

    def reset(self) -> None: ...
    def step(self, observation: ModelObservation) -> ModelAction: ...


class CameraLaneMock:
    """Simple lane-color detector; intentionally not a substitute for ONNX inference."""
    is_mock = True

    def __init__(self, gain: float, lookahead: float = 0.65, name: str = 'mock'):
        self.gain = gain
        self.lookahead = lookahead
        self.name = name

    def reset(self):
        pass

    @staticmethod
    def _lane_center(frame: RGBFrame, y: int) -> float | None:
        xs = []
        for x in range(frame.width):
            r, g, b = frame.rgb_at(x, y)
            if min(r, g, b) >= 225:
                xs.append(x)
        if len(xs) < 2:
            return None
        groups = []
        for x in xs:
            if not groups or x > groups[-1][-1] + 1:
                groups.append([x])
            else:
                groups[-1].append(x)
        groups = [(sum(group) / len(group)) for group in groups]
        if len(groups) < 2:
            return None
        return (groups[0] + groups[-1]) * .5

    def step(self, observation: ModelObservation) -> ModelAction:
        frame = observation.frame
        mid = frame.width / 2
        near = self._lane_center(frame, frame.height - 27)
        far = self._lane_center(frame, frame.height - 42)
        if near is None and far is None:
            return ModelAction(0.0, 0.0)
        if near is None:
            near = far
        if far is None:
            far = near
        assert near is not None and far is not None
        error = (mid - near) / frame.width
        future = (mid - far) / frame.width
        curvature = self.gain * (error + self.lookahead * (future - error))
        return ModelAction(max(-0.035, min(0.035, curvature)), 0.0)
