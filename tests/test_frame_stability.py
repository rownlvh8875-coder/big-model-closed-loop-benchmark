"""Tests for actual pixels, not misleading camera hashes or model ranking."""
import unittest

from bigbench.camera import RGBFrame
from bigbench.frame_stability import compare_rgb_frames,pixel_consistency_summary


class FrameConsistencyTests(unittest.TestCase):
    def sample(self, *, width=8, height=4, changed=None):
        data=bytearray(bytes((20,40,60))*(width*height))
        if changed is not None:
            x,y,value=changed
            data[(y*width+x)*3]=value
        return RGBFrame(width,height,bytes(data))

    def test_identical_and_single_changed_pixel(self):
        a=self.sample()
        b=self.sample(changed=(4,2,22))
        same=compare_rgb_frames(a,a)
        self.assertTrue(same.identical)
        self.assertEqual(same.changed_pixels,0)
        diff=compare_rgb_frames(a,b)
        self.assertFalse(diff.identical)
        self.assertEqual(diff.changed_pixels,1)
        self.assertEqual(diff.changed_bbox_xyxy,(4,2,4,2))
        self.assertAlmostEqual(diff.changed_fraction,1/32)
        self.assertEqual(diff.max_absolute_channel_delta,2)

    def test_warmup_does_not_mask_subsequent_drift(self):
        a=self.sample()
        b=self.sample(changed=(4,2,22))
        result=pixel_consistency_summary([b,a,a,b],warmup=1)
        self.assertEqual(result['unique_sha256'],2)
        self.assertEqual(result['status'],'PIXEL_DRIFT_DETECTED')
        self.assertEqual(result['first_divergence_index_after_warmup'],2)

    def test_stable_after_real_warmup(self):
        a=self.sample()
        b=self.sample(changed=(2,2,100))
        result=pixel_consistency_summary([b,a,a,a],warmup=1)
        self.assertEqual(result['status'],'BIT_EXACT_STABLE')
        self.assertEqual(result['unique_sha256'],1)

    def test_reject_unequal_frames(self):
        with self.assertRaises(ValueError):
            compare_rgb_frames(self.sample(),self.sample(width=10))
        with self.assertRaises(ValueError):
            pixel_consistency_summary([])
        with self.assertRaises(ValueError):
            pixel_consistency_summary([self.sample()],warmup=1)


if __name__=='__main__':
    unittest.main()
