"""Opt-in Panda3D deterministic virtual clock for renderer diagnostics.

Do NOT use to claim exact GPU render determinism without fresh native tests.
The previous engine clock mode is restored on shutdown; no real car involved.
"""
from __future__ import annotations
import math


class PandaClockContractError(RuntimeError):
    pass


class VirtualPandaClock:
    def __init__(self, dt_s: float=1/60):
        if not math.isfinite(dt_s) or dt_s<=0 or dt_s>.1:
            raise PandaClockContractError('invalid virtual camera render frame interval')
        self.dt_s=dt_s
        self.clock=None
        self.old=None

    def start(self):
        if self.clock is not None:
            raise PandaClockContractError('virtual Panda clock already active')
        try:
            from panda3d.core import ClockObject
        except ImportError as exc:
            raise PandaClockContractError('Panda3D not installed') from exc
        clock=ClockObject.getGlobalClock()
        self.old=(clock.getMode(),clock.getDt())
        clock.setMode(ClockObject.MNonRealTime)
        clock.setDt(self.dt_s)
        # Reset BEFORE constructing a fresh simulator environment, so task
        # deadlines and shader clocks share the same virtual epoch per run.
        clock.reset()
        self.clock=clock

    def close(self):
        if self.clock is not None:
            mode,dt=self.old
            self.clock.setMode(mode)
            self.clock.setDt(dt)
            self.clock=None
            self.old=None
