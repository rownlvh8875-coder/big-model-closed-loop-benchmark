"""Synthetic camera-test-double tests; not MetaDrive camera evidence."""
import unittest
from bigbench.camera import RGBFrame
from bigbench.camera_rig import SchematicPair
from bigbench.camera_convergence import (
    StrictConsecutiveCamera,CameraConvergenceError,
)


def pair(value):
    return SchematicPair(
        RGBFrame(4,4,bytes((value,40,50))*16),
        RGBFrame(4,4,bytes((value,25,80))*16),
    )


class SequenceRenderer:
    def __init__(self,frames):
        self.frames=frames
        self.poses=[]
    def capture(self,pose):
        self.poses.append(pose)
        return self.frames[min(len(self.poses)-1,len(self.frames)-1)]


class CameraConvergenceTests(unittest.TestCase):
    def test_repeated_same_pose_captures_until_two_identical(self):
        original=SequenceRenderer([pair(1),pair(2),pair(2)])
        cam=StrictConsecutiveCamera(original,max_captures=4)
        pose=object()
        result=cam.capture(pose)
        self.assertEqual(result.road.sha256,pair(2).road.sha256)
        self.assertEqual(len(original.poses),3)
        self.assertTrue(all(p is pose for p in original.poses))
        self.assertEqual(cam.max_attempts_observed,3)
        self.assertTrue(cam.receipts[0].stable)

    def test_nonconvergent_captures_fail_instead_of_faking_input(self):
        source=SequenceRenderer([pair(1),pair(2),pair(1),pair(2)])
        cam=StrictConsecutiveCamera(source,max_captures=4)
        with self.assertRaises(CameraConvergenceError):
            cam.capture('p')
        self.assertFalse(cam.receipts[0].stable)
        self.assertIsNone(cam.receipts[0].road_sha256)

    def test_initial_stable_pair_does_not_replay_across_changed_poses(self):
        cam=StrictConsecutiveCamera(SequenceRenderer([pair(1),pair(1),pair(3),pair(3)]))
        a=cam.capture('pose-a')
        b=cam.capture('pose-b')
        self.assertNotEqual(a.road.sha256,b.road.sha256)
        self.assertEqual(len(cam.receipts),2)

    def test_invalid_repeat_bound_fails(self):
        with self.assertRaises(ValueError):
            StrictConsecutiveCamera(None,max_captures=1)


if __name__=='__main__':
    unittest.main()
