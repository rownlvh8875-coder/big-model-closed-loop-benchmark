"""Deterministic unit checks for independent camera render schedule isolation.

All engine classes below are test doubles. These tests do NOT prove native
MetaDrive rendering until the actual GitHub Actions optical job executes.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from bigbench.camera import RGBFrame
from bigbench.render_causality import (
    difference, interpret_pipeline, raw_rgb_frame,
    summarize_frame_sequence, summarize_readback_groups,
)
from scripts.metadrive_render_causality import (
    _packed_summary, capture_with_readback,
)


class FakeNode:
    def __init__(self):
        self.parent='initial'
        self.position=(0.,0.,0.)
        self.hpr=(0.,0.,0.)
    def getParent(self):
        return self.parent
    def getPos(self):
        return self.position
    def getHpr(self):
        return self.hpr
    def reparentTo(self,parent):
        self.parent=parent
    def setPos(self,*args):
        self.position=tuple(args[0]) if len(args)==1 else args
    def setHpr(self,*args):
        self.hpr=tuple(args[0]) if len(args)==1 else args


class FakePandaData:
    def __init__(self, payload):
        self.payload=payload
    def getData(self):
        return self.payload


class FakeTexture:
    def __init__(self,sensor):
        self.sensor=sensor
    def getRamImageAs(self,format):
        assert format=='RGB'
        return FakePandaData(self.sensor.data[::-1].tobytes())


class FakeSensor:
    def __init__(self,engine,color):
        self.engine=engine
        self.node=FakeNode()
        self.color=color
        self.data=np.full((4,6,3),color,dtype=np.uint8)
        self.copy_texture=FakeTexture(self)
    def get_cam(self):
        return self.node
    def perceive(self,*,to_float,new_parent_node,position,hpr):
        assert to_float is False
        assert new_parent_node == self.engine.origin
        self.engine.taskMgr.step()
        return self.data.copy()


class FakeTickManager:
    def __init__(self,engine):
        self.engine=engine
        self.calls=0
    def step(self):
        self.calls+=1
        self.engine.update()


class FakeGraphics:
    def __init__(self,engine):
        self.engine=engine
        self.calls=0
    def renderFrame(self):
        self.calls+=1
        self.engine.update()


class FakeEngine:
    def __init__(self):
        self.origin='world'
        self.taskMgr=FakeTickManager(self)
        self.graphicsEngine=FakeGraphics(self)
        self.sensors={
            'bigbench_road':FakeSensor(self,10),
            'bigbench_wide':FakeSensor(self,100),
        }
    def update(self):
        for cam in self.sensors.values():
            cam.data=np.clip(cam.data.astype(np.int16)+1,0,255).astype(np.uint8)


class FakeProvider:
    def __init__(self):
        self.env=SimpleNamespace(engine=FakeEngine())
        self.source_width=6
        self.source_height=4


def frame(value):
    return RGBFrame(4,3,bytes([value,20,30])*12)


class RenderCausalityUnitTests(unittest.TestCase):
    def test_frame_snapshots_are_immutable(self):
        arr=np.full((3,4,3),13,dtype=np.uint8)
        frozen=raw_rgb_frame(arr)
        arr[:]=255
        self.assertEqual(frozen.rgb_at(1,1),(13,13,13))
        with self.assertRaises(ValueError):
            raw_rgb_frame(np.zeros((3,4,3),dtype=np.float32))

    def test_readbacks_without_render_are_identical(self):
        data=summarize_readback_groups([[frame(10),frame(10),frame(10)]])
        self.assertTrue(data['readback_bit_exact'])
        data=summarize_readback_groups([[frame(10),frame(11)]])
        self.assertFalse(data['readback_bit_exact'])
        self.assertEqual(data['samples'][0]['max_changed_pixels'],12)

    def test_warmup_does_not_hide_original_hash_change(self):
        seq=[frame(10),frame(11),frame(12),frame(12),frame(12)]
        d=summarize_frame_sequence(seq,warmup=2)
        self.assertEqual(d['all_unique_sha256'],3)
        self.assertFalse(d['bit_exact_all'])
        self.assertTrue(d['bit_exact_after_warmup'])
        with self.assertRaises(ValueError):
            summarize_frame_sequence([frame(10)],warmup=0)

    def test_each_render_schedule_steps_expected_clock(self):
        for mode,expected_task,expected_render in (
                ('perceive_sequential',2,0),
                ('task_step_pair',1,0),
                ('graphics_frame_pair',0,1)):
            provider=FakeProvider()
            before={k:v.node.parent for k,v in provider.env.engine.sensors.items()}
            raws,groups=capture_with_readback(provider,mode=mode,repeat_reads=3)
            self.assertEqual(provider.env.engine.taskMgr.calls,expected_task)
            self.assertEqual(provider.env.engine.graphicsEngine.calls,expected_render)
            self.assertEqual(set(raws),{'road','wide'})
            self.assertTrue(all(len(reads)==3 for reads in groups.values()))
            self.assertTrue(all(np.array_equal(x,groups[k][0])
                                for k,x in raws.items()))
            self.assertTrue(all(np.array_equal(x,groups[k][-1])
                                for k,x in raws.items()))
            # Camera parent must never remain altered after a manual frame.
            self.assertEqual({k:v.node.parent
                for k,v in provider.env.engine.sensors.items()},before)

    def test_packed_tensor_summary_separates_single_pixel_values(self):
        a=np.zeros((2,6,128,256),dtype=np.uint8)
        b=a.copy()
        b[0,0,3,5]=7
        result=_packed_summary([a,b,b],warmup=1)
        self.assertFalse(result['bit_exact_all'])
        self.assertTrue(result['after_warmup_bit_exact'])
        self.assertEqual(result['max_changed_tensor_elements_after_warmup'],0)
        self.assertEqual(result['shape'],[2,6,128,256])

    def test_result_interpretation_is_cautious(self):
        stable={'road':{'bit_exact_after_warmup':True},
                'wide':{'bit_exact_after_warmup':True}}
        drift={'road':{'bit_exact_after_warmup':False},
               'wide':{'bit_exact_after_warmup':True}}
        data={
           'ego_hidden_task_step_pair':{'status':'OBSERVED',
                                     'model_frame_stability':drift},
           'ego_hidden_graphics_frame_pair':{'status':'OBSERVED',
                                     'model_frame_stability':stable},
           'ego_visible_perceive_sequential':{'status':'OBSERVED',
                                     'model_frame_stability':drift},
           'ego_hidden_perceive_sequential':{'status':'OBSERVED',
                                     'model_frame_stability':stable},
        }
        report=interpret_pipeline(data)
        self.assertEqual(report['task_vs_graphics'],
                         'GRAPHICS_ONLY_STABLER_THAN_TASK_STEP_IN_THIS_SCENE')
        self.assertEqual(report['scene_visibility'],
                         'HIDING_DEFAULT_EGO_CORRELATED_WITH_STABILITY')
        self.assertFalse(report['model_scoring_allowed'])
        self.assertIn('CAUSE_NOT_PROVEN',report['status'])


if __name__=='__main__':
    unittest.main()
