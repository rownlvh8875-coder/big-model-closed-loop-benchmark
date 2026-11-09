"""Deterministic scenario metadata and high-integrity curved road admission tests."""
from __future__ import annotations
import math
import unittest
from types import SimpleNamespace
import numpy as np

from bigbench.curved_lane_scenarios import (
    SCENARIOS, ScenarioGeometryError, select_native_curve_lanes,world_camera_pose,
)

class TestLane:
    def __init__(self,index,direction=1,radius=50,length=50):
        self.index=index;self.direction=direction;self.radius=radius;self.length=length
        self.speed_limit=12
    def position(self,s,offset):return np.array([float(s),float(offset)],dtype=float)
    def heading_theta_at(self,s):return (0.12*s/self.length)*self.direction

class TestBlock:
    def __init__(self,blockid,direction=None):
        self.ID=blockid
        self._dir=direction
        self.pre_block_socket=SimpleNamespace(positive_road=SimpleNamespace(end_node='S'))
        self.block_network=SimpleNamespace(graph={'S':{'T':[TestLane((blockid, direction),direction=(-1 if direction==0 else 1))]}})
    def get_config(self):return {'dir':self._dir}

class Tests(unittest.TestCase):
    def test_s_curves_are_explicitly_opposite_not_random(self):
        l=SCENARIOS['s_curve_left_right'].map_config()
        r=SCENARIOS['s_curve_right_left'].map_config()
        self.assertEqual(l['type'],'pg_map_file')
        self.assertEqual([b['dir'] for b in l['config'][1:]],[0,1])
        self.assertEqual([b['dir'] for b in r['config'][1:]],[1,0])
        self.assertEqual([b['id'] for b in r['config']],['I','C','C'])

    def test_ramp_cases_map_to_correct_metadrive_blocks(self):
        self.assertEqual(SCENARIOS['in_ramp'].map_config()['config'],'r')
        self.assertEqual(SCENARIOS['out_ramp'].map_config()['config'],'R')

    def test_s_curve_selection_checks_forward_native_sign_change(self):
        case=SCENARIOS['s_curve_left_right']
        map_=SimpleNamespace(blocks=[TestBlock('I'),TestBlock('C',0),TestBlock('C',1)])
        output=select_native_curve_lanes(map_,case)
        self.assertEqual([x.direction for x in output],[-1,1])
        with self.assertRaises(ScenarioGeometryError):
            select_native_curve_lanes(SimpleNamespace(blocks=[TestBlock('I'),TestBlock('C',0),TestBlock('C',0)]),case)

    def test_missing_native_ramp_geometry_is_not_assumed(self):
        block=TestBlock('r')
        block.block_network=SimpleNamespace(graph={})
        with self.assertRaises(ScenarioGeometryError):
            select_native_curve_lanes(SimpleNamespace(blocks=[TestBlock('I'),block]),SCENARIOS['in_ramp'])

    def test_world_camera_yaw_is_panda_y_forward_not_car_rotated(self):
        lane=TestLane('x')
        pose=world_camera_pose(lane,0.5)
        self.assertEqual(pose[:3],(25.,0.,1.22))
        self.assertAlmostEqual(pose[3],math.degrees(.06)-90,places=8)
        upstream=world_camera_pose(lane,0.0,lookback_m=12.0)
        self.assertAlmostEqual(upstream[0],-12.0)
        self.assertAlmostEqual(upstream[1],0.0)
        for lb in (-1.,21.,float('nan')):
            with self.assertRaises(ValueError):world_camera_pose(lane,0.0,lookback_m=lb)
        for f in (-.1,1.1,float('nan')):
            with self.assertRaises(ValueError):world_camera_pose(lane,f)

if __name__=='__main__':unittest.main()
