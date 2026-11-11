"""Capture dispatch/restore contracts, not native rendering measurements."""
from types import SimpleNamespace
import unittest

import numpy as np

from scripts.metadrive_render_causality import capture_with_readback


class Node:
    def __init__(self, name):
        self.parent=name
        self.pos=(1.,2.,3.)
        self.hpr=(4.,5.,6.)
    def getParent(self): return self.parent
    def getPos(self): return self.pos
    def getHpr(self): return self.hpr
    def reparentTo(self, parent): self.parent=parent
    def setPos(self, *pos): self.pos=pos[0] if len(pos)==1 else pos
    def setHpr(self, *hpr): self.hpr=hpr[0] if len(hpr)==1 else hpr


def provider_fixture(*, fail_wide=False):
    events=[]
    sensors={}
    engine=SimpleNamespace(origin='WORLD',sensors=sensors)
    def step():
        events.append(('tick',[(s.node.parent,s.node.pos,s.node.hpr)
                               for s in sensors.values()]))
    engine.taskMgr=SimpleNamespace(step=step)
    class Sensor:
        def __init__(self, kind):
            self.kind=kind
            self.node=Node(kind)
            self.copy_texture=SimpleNamespace(getRamImageAs=self.read)
        def get_cam(self): return self.node
        def read(self, fmt):
            events.append(('read',self.kind))
            if fail_wide and self.kind=='wide': raise RuntimeError('read failed')
            return SimpleNamespace(getData=lambda:bytes([10 if self.kind=='road' else 20])*24)
        def perceive(self, **kwargs):
            events.append(('perceive',self.kind,kwargs))
            engine.taskMgr.step()
            return np.frombuffer(self.read('RGB').getData(),dtype=np.uint8).reshape(2,4,3)
    for kind in ('road','wide'): sensors['bigbench_'+kind]=Sensor(kind)
    return SimpleNamespace(env=SimpleNamespace(engine=engine),source_width=4,source_height=2),events


class CaptureScheduleIsolationTests(unittest.TestCase):
    def test_original_and_reversed_perceive_order_use_the_requested_world_pose(self):
        for mode,order in [('perceive_sequential',['road','wide']),
                           ('perceive_reverse',['wide','road'])]:
            with self.subTest(mode=mode):
                provider,events=provider_fixture()
                pose=((7.,8.,1.22),(-84.,0.,0.))
                rgb,groups=capture_with_readback(provider,mode=mode,pose=pose)
                calls=[e for e in events if e[0]=='perceive']
                self.assertEqual([e[1] for e in calls],order)
                self.assertEqual(len([e for e in events if e[0]=='tick']),2)
                for _,_,kwargs in calls:
                    self.assertEqual(kwargs['position'],pose[0])
                    self.assertEqual(kwargs['hpr'],pose[1])
                    self.assertEqual(kwargs['new_parent_node'],'WORLD')
                self.assertEqual(int(rgb['road'][0,0,0]),10)
                self.assertEqual(int(rgb['wide'][0,0,0]),20)
                self.assertEqual(len(groups['road']),3)

    def test_both_cameras_stay_mounted_until_one_or_two_ticks_complete(self):
        for mode,ticks in [('task_step_pair',1),('task_step_pair_twice',2)]:
            with self.subTest(mode=mode):
                provider,events=provider_fixture()
                pose=((7.,8.,1.22),(-84.,0.,0.))
                capture_with_readback(provider,mode=mode,pose=pose)
                observed=[e for e in events if e[0]=='tick']
                self.assertEqual(len(observed),ticks)
                for _,nodes in observed:
                    self.assertEqual(nodes,[('WORLD',pose[0],pose[1])]*2)
                self.assertTrue(all(e[0]=='tick' for e in events[:ticks]))
                for kind,s in provider.env.engine.sensors.items():
                    self.assertEqual(s.node.parent,kind.removeprefix('bigbench_'))
                    self.assertEqual(s.node.pos,(1.,2.,3.))
                    self.assertEqual(s.node.hpr,(4.,5.,6.))

    def test_two_tick_capture_restores_both_cameras_when_readback_fails(self):
        provider,_=provider_fixture(fail_wide=True)
        with self.assertRaisesRegex(RuntimeError,'read failed'):
            capture_with_readback(provider,mode='task_step_pair_twice')
        for kind,s in provider.env.engine.sensors.items():
            self.assertEqual(s.node.parent,kind.removeprefix('bigbench_'))
            self.assertEqual(s.node.pos,(1.,2.,3.))
            self.assertEqual(s.node.hpr,(4.,5.,6.))
