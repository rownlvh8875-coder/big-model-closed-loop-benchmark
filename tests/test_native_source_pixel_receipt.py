"""Synthetic native sensor fakes to check source RGB hashing boundaries.

The fake camera is NOT MetaDrive; CI native execution separately verifies the
actual 964x604 sensor path. No model-performance claim is made here.
"""
import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from bigbench.camera import RGBFrame
from bigbench.camera_rig import SchematicPair
from bigbench.kinematics import AgentState
from bigbench.native_model_campaign import NativeWorldCamera


class FakeSensor:
    def __init__(self, value):
        self.buffer=np.full((604,964,3),value,dtype=np.uint8)
        self.calls=0
    def perceive(self, *, to_float, new_parent_node, position, hpr):
        self.calls+=1
        return self.buffer
    def get_lens(self): return object()


class FakeRectifier:
    def rectify_pair(self, a, b, *, road_intrinsics, wide_intrinsics):
        assert a.shape == b.shape == (604,964,3)
        p=RGBFrame(2,2,bytes([int(a[0,0,0]),20,30])*4)
        q=RGBFrame(2,2,bytes([int(b[0,0,0]),40,50])*4)
        return SchematicPair(p,q), {}


class NativeSourceBoundaryTests(unittest.TestCase):
    def test_real_sensor_bytes_hashed_before_model_warp(self):
        road,wide=FakeSensor(71),FakeSensor(113)
        engine=SimpleNamespace(origin="native-world",sensors={
            "bigbench_road":road,"bigbench_wide":wide,
        })
        provider=SimpleNamespace(source_width=964,source_height=604,
                                 height_m=1.22,env=SimpleNamespace(engine=engine))
        camera=NativeWorldCamera(provider)
        camera.rectifier=FakeRectifier()
        with patch("bigbench.native_model_campaign.intrinsics_from_panda_lens",
                   return_value="mock-intrinsics"):
            pair=camera.capture(AgentState(0.,10.,5.,0.,8.))
        road_original=np.full((604,964,3),71,dtype=np.uint8)
        wide_original=np.full((604,964,3),113,dtype=np.uint8)
        self.assertEqual(camera.last_source_rgb_sha256["road"],
                         hashlib.sha256(road_original.tobytes()).hexdigest())
        self.assertEqual(camera.last_source_rgb_sha256["wide"],
                         hashlib.sha256(wide_original.tobytes()).hexdigest())
        self.assertNotEqual(camera.last_source_rgb_sha256["road"],pair.road.sha256)
        self.assertEqual((road.calls,wide.calls),(1,1))
        old_sha=camera.last_source_rgb_sha256["road"]
        road.buffer[:]=255
        self.assertEqual(camera.last_source_rgb_sha256["road"],old_sha)


if __name__=="__main__":
    unittest.main()
