"""Opt-in strict, same-pose virtual camera convergence gate.

Repeated *real* renderer captures are compared byte-for-byte by default.
An explicit bounded pixel tolerance is an EXPERIMENT, not exact reproducibility. No temporal
averaging, image interpolation, pixel smoothing or substitution with recorded
frames is allowed. Failure is explicit; this does NOT prove photometric fidelity
or repeatability across independently initialized MetaDrive processes.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from .camera_rig import SchematicPair
from .frame_stability import compare_rgb_frames


class CameraConvergenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class CaptureReceipt:
    attempts: int
    stable: bool
    road_sha256: str | None
    wide_sha256: str | None
    road_changed_pixels: int = 0
    wide_changed_pixels: int = 0
    max_rgb_delta: int = 0


class StrictConsecutiveCamera:
    """Require 2 stable adjacent road+wide images at a fixed pose.

    With zero tolerance this is bit-exact; nonzero tolerance accepts slight
    pixel deviations WITHOUT modifying the selected real rendered frame.
    Typical use is a *diagnostic experiment*, not the unqualified default
    input path. Graphics engine task time may advance during repeated captures.
    """
    def __init__(self, renderer: Any, *, max_captures: int = 6,
                 max_changed_pixels: int = 0, max_rgb_delta: int = 0):
        if type(max_captures) is not int or not 2<=max_captures<=12:
            raise ValueError('bounded camera convergence requires 2..12 captures')
        if type(max_changed_pixels) is not int or not 0<=max_changed_pixels<=32:
            raise ValueError('camera pixel tolerance is bounded at 0..32')
        if type(max_rgb_delta) is not int or not 0<=max_rgb_delta<=16:
            raise ValueError('RGB channel tolerance must be 0..16')
        if bool(max_changed_pixels)!=bool(max_rgb_delta):
            raise ValueError('nonzero pixel and channel thresholds must be provided together')
        self.renderer=renderer
        self.max_captures=max_captures
        self.max_changed_pixels=max_changed_pixels
        self.max_rgb_delta=max_rgb_delta
        self.receipts: list[CaptureReceipt] = []

    def capture(self, pose: Any) -> SchematicPair:
        previous: SchematicPair | None=None
        for k in range(1,self.max_captures+1):
            current=self.renderer.capture(pose)
            if not isinstance(current,SchematicPair):
                raise CameraConvergenceError('renderer did not return native paired RGB')
            if previous is not None:
                rd=compare_rgb_frames(previous.road,current.road)
                wd=compare_rgb_frames(previous.wide,current.wide)
                accept=(rd.changed_pixels<=self.max_changed_pixels and
                        wd.changed_pixels<=self.max_changed_pixels and
                        rd.max_absolute_channel_delta<=self.max_rgb_delta and
                        wd.max_absolute_channel_delta<=self.max_rgb_delta)
                if accept:
                    self.receipts.append(CaptureReceipt(
                        k,True,current.road.sha256,current.wide.sha256,
                        rd.changed_pixels,wd.changed_pixels,
                        max(rd.max_absolute_channel_delta,wd.max_absolute_channel_delta)))
                    return current
            previous=current
        self.receipts.append(CaptureReceipt(self.max_captures,False,None,None))
        raise CameraConvergenceError('same-pose native RGB pair did not converge byte-for-byte')

    @property
    def max_attempts_observed(self)->int:
        return max((x.attempts for x in self.receipts), default=0)
