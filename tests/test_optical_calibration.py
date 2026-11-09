"""Reference ideal pinhole camera tests; not actual comma optical certification."""
from __future__ import annotations

import math
import unittest

import cv2
import numpy as np

from bigbench.image_adapter import camera_pair_to_model
from bigbench.kinematics import AgentState, ModelAction
from bigbench.metadrive_camera import MetaDriveOpticalRig, probe_model_with_metadrive
from bigbench.optical_calibration import (
    OpticalContractError, PinholeIntrinsics, PinholeRectifier,
    assert_intrinsics_match, destination_to_source_homography,
    intrinsics_from_panda_lens, reference_model, reference_source,
    transform_points,
)


class FakeLens:
    """Panda3D film/focal API double with zero film offset."""
    def __init__(self, kind, w=964, h=604, scale=1.0, offset=(0.0,0.0)):
        ref=reference_source(kind,w,h)
        self.focal=ref.fx*scale
        self.w,self.h=w,h
        self.offset=offset
    def getFilmSize(self): return (float(self.w),float(self.h))
    def getFilmOffset(self): return self.offset
    def getFocalLength(self): return self.focal


class FakeFrameProvider:
    """Artificial RGB data: tests *adapter wiring*, NOT MetaDrive rendering."""
    def __init__(self): self.poses=[]
    def capture(self, state):
        self.poses.append(state)
        yy,xx=np.indices((604,964))
        road=np.empty((604,964,3),dtype=np.uint8)
        wide=np.empty_like(road)
        dx=round(state.x*2)
        road[...,0]=(xx+dx)%256
        road[...,1]=(yy//2)%256
        road[...,2]=40
        wide[...,0]=(xx//2+dx)%256
        wide[...,1]=(yy+30)%256
        wide[...,2]=75
        return road,wide,FakeLens('road'),FakeLens('wide')
    def close(self): pass


class ConstPolicy:
    name='test-double'
    is_mock=True
    def reset(self): self.calls=0
    def step(self, obs):
        self.calls+=1
        assert obs.wide_frame is not None
        return ModelAction(curvature_1pm=0.01,acceleration_mps2=0.0)


class OpticalCalibrationTests(unittest.TestCase):
    def test_road_and_wide_reference_match_published_pinhole_constants(self):
        road=reference_source('road',1928,1208)
        wide=reference_source('wide',1928,1208)
        self.assertEqual((road.fx,road.cx,road.cy),(2648.0,964.0,604.0))
        self.assertEqual((wide.fx,wide.cx,wide.cy),(567.0,964.0,604.0))
        self.assertEqual((reference_model('road').fx,reference_model('road').cy),(910.0,47.6))
        self.assertEqual((reference_model('wide').fx,reference_model('wide').cy),(455.0,151.8))
        self.assertAlmostEqual(reference_source('road').fov_h_deg,40.01,places=1)
        self.assertAlmostEqual(reference_source('wide').fov_h_deg,119.07,places=1)

    def test_projection_center_line_maps_to_virtual_principal_point(self):
        for kind in ('road','wide'):
            src=reference_source(kind)
            dst=reference_model(kind)
            H=destination_to_source_homography(src,dst)
            center=transform_points(H, np.array([[dst.cx,dst.cy]]))[0]
            np.testing.assert_allclose(center,[src.cx,src.cy],atol=1e-9)
            pts=np.array([[0.,0.],[511.,255.],[256.,160.],[120.,200.]])
            np.testing.assert_allclose(transform_points(np.linalg.inv(H),transform_points(H,pts)),pts,atol=1e-9)

    def test_actual_warp_places_known_colored_landmarks_at_predicted_pixels(self):
        rect=PinholeRectifier()
        source={kind:np.zeros((604,964,3),dtype=np.uint8) for kind in ('road','wide')}
        # Model centers lie in very different rows (47.6 vs 151.8).
        positions={'road':(256,60),'wide':(256,166)}
        for kind,(u,v) in positions.items():
            H=destination_to_source_homography(reference_source(kind),reference_model(kind))
            x,y=transform_points(H,np.array([[u,v]]))[0]
            cv2.circle(source[kind],(round(x),round(y)),7,(250,30,20),-1)
        result,audits=rect.rectify_pair(source['road'],source['wide'])
        self.assertEqual((result.road.width,result.road.height),(512,256))
        self.assertEqual((result.wide.width,result.wide.height),(512,256))
        self.assertGreater(audits['road'].fraction_valid_source_pixels,0.99)
        self.assertGreater(audits['wide'].fraction_valid_source_pixels,0.99)
        for kind,(u,v) in positions.items():
            frame=getattr(result,kind)
            arr=np.frombuffer(frame.rgb,dtype=np.uint8).reshape(256,512,3)
            self.assertGreater(int(arr[v,u,0]),180,kind)
            self.assertLess(int(arr[v,u,1]),75,kind)
        self.assertEqual(camera_pair_to_model(result.road,result.wide).shape,(2,6,128,256))
        self.assertIn('PINHOLE_GEOMETRY',audits['road'].evidence_class)

    def test_reject_wrong_aspect_ratio_or_camera_focal(self):
        with self.assertRaises(OpticalContractError):
            reference_source('road',640,480)
        with self.assertRaises(OpticalContractError):
            assert_intrinsics_match(reference_source('road'),reference_source('wide'))
        rect=PinholeRectifier()
        raw=np.zeros((604,964,3),dtype=np.uint8)
        with self.assertRaises(OpticalContractError):
            rect.rectify_pair(raw,raw,road_intrinsics=PinholeIntrinsics(964,604,800,800,482,302))
        with self.assertRaises(OpticalContractError):
            rect.rectify_pair(raw,raw,wide_intrinsics=PinholeIntrinsics(964,604,283.5,283.5,500,302))
        with self.assertRaises(OpticalContractError):
            rect.rectify_pair(raw[:500],raw)

    def test_reject_nonzero_panda_film_offset_and_zoom_drift(self):
        with self.assertRaises(OpticalContractError):
            intrinsics_from_panda_lens(FakeLens('road',offset=(.1,0.)),964,604)
        measured=intrinsics_from_panda_lens(FakeLens('wide',scale=1.001),964,604)
        assert_intrinsics_match(measured, reference_source('wide'))
        with self.assertRaises(OpticalContractError):
            assert_intrinsics_match(intrinsics_from_panda_lens(FakeLens('road',scale=.75),964,604), reference_source('road'))

    def test_frame_provider_and_model_feedback_change_camera_view(self):
        provider=FakeFrameProvider()
        rig=MetaDriveOpticalRig(provider)
        p=ConstPolicy()
        result,last=probe_model_with_metadrive(p,rig,steps=3,initial_speed_mps=12.0)
        self.assertEqual(result['classification'],'CAMERA_PROVIDER_TEST_DOUBLE_NOT_METADRIVE')
        self.assertFalse(result['scoring_allowed'])
        self.assertEqual(result['steps'],3)
        self.assertEqual(len(provider.poses),3)
        self.assertNotEqual(provider.poses[0].x,provider.poses[-1].x)
        self.assertGreater(result['distinct_road_frames'],1)
        self.assertEqual(last.pair.road.width,512)
        self.assertEqual(p.calls,3)


if __name__=='__main__':
    unittest.main()
