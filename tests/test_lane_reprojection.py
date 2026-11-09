"""Synthetic independent tests for lane world geometry and RGB paint diagnostics."""
from __future__ import annotations

import math
import sys
import types
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from bigbench.camera import RGBFrame
from bigbench.lane_reprojection import (
    BoundaryLandmark, _paint_mask, draw_lane_alignment,
    evaluate_visible_lane_paint, lane_boundary_landmarks, map_boundary_landmarks,
    project_panda_camera_points,
)
from bigbench.optical_calibration import OpticalContractError, PinholeIntrinsics, reference_model


def painted_fixture(shift_px: int = 0):
    img=np.full((256,512,3),(65,67,68),dtype=np.uint8)
    spots=[]
    for v in (170,185,200,215,230,242):
        x=212 + (v-170)//6
        cv2.rectangle(img,(x+shift_px-2,v-2),(x+shift_px+2,v+2),(228,232,231),-1)
        spots.append(dict(model_uv=[float(x),float(v)],paint_color='white'))
    for v in (180,196,212,228,240):
        x=380 - (v-180)//5
        cv2.rectangle(img,(x+shift_px-2,v-2),(x+shift_px+2,v+2),(240,196,18),-1)
        spots.append(dict(model_uv=[float(x),float(v)],paint_color='yellow'))
    return RGBFrame(512,256,img.tobytes()),spots


class LanePaintMetricTests(unittest.TestCase):
    def test_correct_independent_paint_projection_has_small_error(self):
        frame,points=painted_fixture()
        result=evaluate_visible_lane_paint(frame,points)
        self.assertEqual(result['matched_count'],len(points))
        self.assertAlmostEqual(result['median_pixel_error_px'],0.0)
        self.assertEqual(result['classification'],'LANE_PIXEL_MEASUREMENT_AVAILABLE')
        overlay=draw_lane_alignment(frame,result)
        self.assertNotEqual(frame.sha256,overlay.sha256)

    def test_wrong_projection_cannot_self_validate(self):
        frame,points=painted_fixture(shift_px=24)
        result=evaluate_visible_lane_paint(frame,points,search_radius_px=8)
        self.assertEqual(result['matched_count'],0)
        self.assertIsNone(result['median_pixel_error_px'])
        self.assertEqual(result['classification'],'INSUFFICIENT_OBSERVED_LANE_PAINT')

    def test_dark_asphalt_and_bright_sky_are_not_accepted_as_paint(self):
        img=np.empty((256,512,3),dtype=np.uint8)
        img[:120]=(180,200,220)
        img[120:]=(75,75,75)
        frame=RGBFrame(512,256,img.tobytes())
        points=[{'model_uv':[250.,float(i)],'paint_color':'white'} for i in range(160,220,6)]
        result=evaluate_visible_lane_paint(frame,points)
        self.assertEqual(result['matched_count'],0)

    def test_invalid_windows_fail(self):
        frame,pts=painted_fixture()
        with self.assertRaises(ValueError):
            evaluate_visible_lane_paint(frame,pts,search_radius_px=41)


class FakeLane:
    def __init__(self, idx, width, types, colors):
        self.length=100.0
        self.width=width
        self.index=('A','B',idx)
        self.line_types=types
        self.line_colors=colors
        self.offset=float(idx)*width
    def local_coordinates(self, pos): return float(pos[0]),float(pos[1])-self.offset
    def width_at(self,s): return self.width
    def position(self,s,r): return np.array([s,self.offset+r])


class FakePGLineType:
    NONE='none'
    GUARDRAIL='guardrail'
    SIDE='side'
    CONTINUOUS='continuous'
    BROKEN='broken'


class FakePGLineColor:
    YELLOW=(1.0,.7843,0,1)
    GREY=(1,1,1,1)


class LaneGeometryTests(unittest.TestCase):
    def test_extracts_only_actual_constructed_lane_boundaries(self):
        module=types.ModuleType('metadrive')
        constants=types.ModuleType('metadrive.constants')
        constants.PGLineType=FakePGLineType
        constants.PGLineColor=FakePGLineColor
        lanes=[FakeLane(0,3.5,(FakePGLineType.CONTINUOUS,FakePGLineType.BROKEN),
                        (FakePGLineColor.YELLOW,FakePGLineColor.GREY)),
               FakeLane(1,3.5,(FakePGLineType.BROKEN,FakePGLineType.SIDE),
                        (FakePGLineColor.GREY,FakePGLineColor.GREY))]
        with patch.dict(sys.modules,{'metadrive':module,'metadrive.constants':constants}):
            data=lane_boundary_landmarks(lanes,(0.0,0.0),distances_m=(6,8,10,12))
        self.assertTrue(any(p.paint_color=='yellow' for p in data))
        self.assertTrue(any(p.lane_id==1 and p.side=='right' for p in data))
        self.assertFalse(any(p.lane_id==0 and p.side=='right' for p in data))
        self.assertTrue(all(math.isfinite(p.world_x_m) and math.isfinite(p.world_y_m) for p in data))

    def test_entire_map_finds_painted_road_after_unpainted_spawn_section(self):
        module=types.ModuleType('metadrive')
        constants=types.ModuleType('metadrive.constants')
        constants.PGLineType=FakePGLineType
        constants.PGLineColor=FakePGLineColor
        empty=FakeLane(0,3.5,(FakePGLineType.NONE,FakePGLineType.NONE),
                       (FakePGLineColor.GREY,FakePGLineColor.GREY))
        painted=FakeLane(1,3.5,(FakePGLineType.CONTINUOUS,FakePGLineType.SIDE),
                         (FakePGLineColor.YELLOW,FakePGLineColor.GREY))
        fake_map=types.SimpleNamespace(graph={'A':{'B':[empty]},'B':{'C':[painted]}})
        with patch.dict(sys.modules,{'metadrive':module,'metadrive.constants':constants}):
            landmarks=map_boundary_landmarks(fake_map,(0.0,0.0),max_radius_m=75)
        self.assertGreater(len(landmarks),5)
        self.assertTrue(all(p.lane_id==0 for p in landmarks))
        self.assertTrue(any(p.paint_color=='yellow' for p in landmarks))

    def test_rejects_no_lanes(self):
        with self.assertRaises(OpticalContractError):
            lane_boundary_landmarks([],(0,0))


class FakePoint3:
    def __init__(self,x,y,z): self.x,self.y,self.z=x,y,z


class FakeCamera:
    def getRelativePoint(self,ref,pt):
        return FakePoint3(pt.x,pt.y,pt.z-1.22)


class ProjectionTests(unittest.TestCase):
    def test_panda_forward_y_ground_point_projects_below_model_horizon(self):
        panda=types.ModuleType('panda3d')
        core=types.ModuleType('panda3d.core')
        core.Point3=FakePoint3
        src=PinholeIntrinsics(964,604,480,480,482,302)
        model=reference_model('wide')
        p=BoundaryLandmark('A',0,'left','white','SIDE',12.0,1.0,12.0)
        with patch.dict(sys.modules,{'panda3d':panda,'panda3d.core':core}):
            found=project_panda_camera_points(FakeCamera(),None,[p],964,604,src,model)
        self.assertEqual(len(found),1)
        x,y=found[0]['model_uv']
        self.assertGreater(x,model.cx)
        self.assertGreater(y,model.cy)
        self.assertAlmostEqual(x,model.cx+model.fx/12.0,places=4)

    def test_rejects_behind_camera(self):
        panda=types.ModuleType('panda3d')
        core=types.ModuleType('panda3d.core')
        core.Point3=FakePoint3
        src=PinholeIntrinsics(964,604,480,480,482,302)
        p=BoundaryLandmark('A',0,'right','white','SIDE',0,-1.0,-12.0)
        with patch.dict(sys.modules,{'panda3d':panda,'panda3d.core':core}):
            found=project_panda_camera_points(FakeCamera(),None,[p],964,604,src,reference_model('wide'))
        self.assertEqual(found,[])


if __name__=='__main__': unittest.main()
