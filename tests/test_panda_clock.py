"""Fake Panda clock proves that an uninitialized dt=0 is not restored."""
from __future__ import annotations
import sys
import types
import unittest
from unittest.mock import patch

from bigbench.panda_clock import PandaClockContractError, VirtualPandaClock


class FakePandaClock:
    MNonRealTime=100
    fake=None
    def __init__(self):
        self.mode=1
        self.dt=0.0
        self.history=[]
    @classmethod
    def getGlobalClock(cls):
        return cls.fake
    def getMode(self): return self.mode
    def getDt(self): return self.dt
    def setMode(self,mode):
        self.history.append(('mode',mode))
        self.mode=mode
    def setDt(self,dt):
        if dt==0.0: raise AssertionError('dt != 0.0')
        self.history.append(('dt',dt))
        self.dt=dt
    def reset(self): self.history.append(('reset',))


class VirtualPandaClockTests(unittest.TestCase):
    def test_default_zero_dt_restores_mode_without_assertion(self):
        fake=FakePandaClock()
        FakePandaClock.fake=fake
        panda=types.ModuleType('panda3d')
        core=types.ModuleType('panda3d.core')
        core.ClockObject=FakePandaClock
        with patch.dict(sys.modules,{'panda3d':panda,'panda3d.core':core}):
            obj=VirtualPandaClock()
            obj.start()
            obj.close()
        self.assertEqual(fake.mode,1)
        self.assertNotIn(('dt',0.0),fake.history)

    def test_nonzero_dt_restored_correctly(self):
        fake=FakePandaClock()
        fake.dt=0.02
        FakePandaClock.fake=fake
        panda=types.ModuleType('panda3d')
        core=types.ModuleType('panda3d.core')
        core.ClockObject=FakePandaClock
        with patch.dict(sys.modules,{'panda3d':panda,'panda3d.core':core}):
            obj=VirtualPandaClock()
            obj.start()
            obj.close()
        self.assertEqual(fake.mode,1)
        self.assertAlmostEqual(fake.dt,.02)

    def test_invalid_dt_rejected(self):
        with self.assertRaises(PandaClockContractError):VirtualPandaClock(0.0)
        with self.assertRaises(PandaClockContractError):VirtualPandaClock(float('nan'))


if __name__=='__main__':
    unittest.main()
