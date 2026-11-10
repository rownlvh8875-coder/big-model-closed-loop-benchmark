"""Opt-in strict, same-pose virtual camera convergence gate.

Repeated *real* renderer captures are compared byte-for-byte. No temporal
averaging, image interpolation, pixel smoothing or substitution with recorded
frames is allowed. Failure is explicit; this does NOT prove photometric fidelity
or repeatability across independently initialized MetaDrive processes.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from .camera_rig import SchematicPair


class CameraConvergenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class CaptureReceipt:
    attempts: int
    stable: bool
    road_sha256: str | None
    wide_sha256: str | None


class StrictConsecutiveCamera:
    """Require 2 identical adjacent road+wide images at a fixed pose.

    Typical use is a *diagnostic experiment*, not the unqualified default
    input path. Graphics engine task time may advance during repeated captures.
    """
    def __init__(self, renderer: Any, *, max_captures: int = 6):
        if type(max_captures) is not int or not 2<=max_captures<=12:
            raise ValueError('bounded camera convergence requires 2..12 captures')
        self.renderer=renderer
        self.max_captures=max_captures
        self.receipts: list[CaptureReceipt] = []

    def capture(self, pose: Any) -> SchematicPair:
        previous: SchematicPair | None=None
        for k in range(1,self.max_captures+1):
            current=self.renderer.capture(pose)
            if not isinstance(current,SchematicPair):
                raise CameraConvergenceError('renderer did not return native paired RGB')
            if previous is not None and (previous.road.sha256==current.road.sha256 and
                                         previous.wide.sha256==current.wide.sha256):
                self.receipts.append(CaptureReceipt(k,True,current.road.sha256,current.wide.sha256))
                return current
            previous=current
        self.receipts.append(CaptureReceipt(self.max_captures,False,None,None))
        raise CameraConvergenceError('same-pose native RGB pair did not converge byte-for-byte')

    @property
    def max_attempts_observed(self)->int:
        return max((x.attempts for x in self.receipts), default=0)
