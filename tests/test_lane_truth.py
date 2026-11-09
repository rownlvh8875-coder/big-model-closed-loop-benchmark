"""Ground-truth-only math tests; deliberately no actual vehicle response model."""
from __future__ import annotations
import math
import unittest
import numpy as np
from bigbench.lane_truth import (
    LaneTruthError, evaluate_native_lane_state, evaluate_closest_native_lane, lane_curvature
)

class AnalyticLane:
    def __init__(self, curvature=0., width=3.5, length=70., index=('C','D',1)):
        self.k=float(curvature);self.width=float(width);self.length=float(length);self.index=index
    def heading_theta_at(self,s):return self.k*s
    def width_at(self,s):return self.width
    def position(self,s,lateral):
        h=self.heading_theta_at(s)
        if abs(self.k)>1e-10:
            x=math.sin(h)/self.k;y=(1-math.cos(h))/self.k
        else:x=s;y=0.
        return np.array([x+math.sin(h)*lateral,y-math.cos(h)*lateral])
    def local_coordinates(self,p):
        x,y=p
        if abs(self.k)<1e-10:return x,-y
        # Circle with center at (0,1/k). The forward angle is k*s.
        cx,cy=0.,1/self.k
        radial_x=x-cx;radial_y=y-cy
        phase=math.atan2(self.k*radial_x, -self.k*radial_y)
        s=phase/self.k
        h=self.k*s
        line_xy=self.position(s,0.)
        # right = (sin(h), -cos(h))
        r=(x-line_xy[0])*math.sin(h)-(y-line_xy[1])*math.cos(h)
        return s,r

class NativeLaneTruthTests(unittest.TestCase):
    def test_centerline_zero_error_and_vehicle_independence(self):
        lane=AnalyticLane(0.)
        sample=evaluate_native_lane_state(lane,8.,0.,0.)
        self.assertAlmostEqual(sample.signed_lateral_right_m,0.)
        self.assertAlmostEqual(sample.intrusion_depth_m,0.)
        self.assertIsNone(sample.inside_turn_offset_m)
        self.assertEqual(sample.classification,'SYNTHETIC_WORLD_TRUTH_ONLY')

    def test_virtual_footprint_intrusion_and_clearance(self):
        lane=AnalyticLane(0.,width=3.5)
        # Right-positive lane coordinate means negative physical world y.
        p=lane.position(15.,1.50)
        sample=evaluate_native_lane_state(lane,*p,0.,half_width_m=.9)
        self.assertAlmostEqual(sample.signed_lateral_right_m,1.5,places=8)
        self.assertAlmostEqual(sample.right_edge_clearance_m,-.65,places=8)
        self.assertAlmostEqual(sample.intrusion_depth_m,.65,places=8)
        self.assertGreater(sample.left_edge_clearance_m,0.)

    def test_inside_turn_sign_reverses_with_curvature(self):
        for curvature in (.012,-.012):
            lane=AnalyticLane(curvature)
            r=-.55 if curvature>0 else .55
            p=lane.position(12.,r)
            sample=evaluate_native_lane_state(lane,float(p[0]),float(p[1]),lane.heading_theta_at(12.))
            self.assertAlmostEqual(sample.curvature_1pm,curvature,places=7)
            self.assertAlmostEqual(sample.inside_turn_offset_m,.55,places=7)
            self.assertAlmostEqual(sample.heading_error_rad,0.,places=7)

    def test_nearest_lane_and_segment_boundaries(self):
        a=AnalyticLane(width=3.5)
        b=AnalyticLane(width=3.5,index=('C','D',2))
        b.local_coordinates=lambda xy:(xy[0],2.0)
        sample=evaluate_closest_native_lane([a,b],12.,0.,0.)
        self.assertEqual(sample.lane_id,str(a.index))
        with self.assertRaises(LaneTruthError):evaluate_native_lane_state(a,100.,0.,0.)
        with self.assertRaises(LaneTruthError):evaluate_closest_native_lane([],12.,0.,0.)

    def test_rejects_nan_bogus_width_or_footprint(self):
        lane=AnalyticLane(width=0.)
        with self.assertRaises(LaneTruthError):evaluate_native_lane_state(lane,10.,0.,0.)
        with self.assertRaises(LaneTruthError):evaluate_native_lane_state(AnalyticLane(),10.,0.,0.,half_width_m=float('nan'))
        with self.assertRaises(LaneTruthError):lane_curvature(AnalyticLane(),-1.)

if __name__=='__main__':unittest.main()
