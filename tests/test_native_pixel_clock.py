"""Pure test doubles: NOT an actual Panda3D or model performance test."""
import unittest

import numpy as np

from bigbench.native_pixel_clock import (
    rgb_delta, rgb_sequence, packed_i420_delta, packed_i420_sequence,
)


class NativePixelReceiptTests(unittest.TestCase):
    def test_x_y_coordinate_and_changed_pixels_are_exact(self):
        a = np.zeros((5, 7, 3), dtype=np.uint8)
        b = a.copy()
        b[3, 5, 1] = 13
        b[1, 2, 0] = 7
        value = rgb_delta(a, b)
        self.assertEqual(value["changed_pixels"], 2)
        self.assertEqual(value["changed_channel_values"], 2)
        self.assertEqual(value["bounding_box_xyxy_inclusive"], [2, 1, 5, 3])
        self.assertEqual(value["first_changed_pixel_xy"], [2, 1])
        self.assertEqual(value["changed_pixel_examples"][1]["x"], 5)
        self.assertEqual(value["changed_pixel_examples"][1]["y"], 3)
        self.assertEqual(value["max_channel_delta"], 13)
        self.assertFalse(value["identical"])

    def test_exact_match_is_not_a_failure(self):
        a = np.arange(36, dtype=np.uint8).reshape(3, 4, 3)
        result = rgb_delta(a, a.copy())
        self.assertTrue(result["identical"])
        self.assertIsNone(result["first_changed_pixel_xy"])
        self.assertIsNone(result["bounding_box_xyxy_inclusive"])
        self.assertEqual(result["changed_pixels"], 0)

    def test_full_warmup_sha_preserved_and_first_later_change(self):
        f = [np.full((4, 5, 3), i, dtype=np.uint8) for i in (1, 2, 3, 3, 4)]
        v = rgb_sequence(f, warmup=2)
        self.assertEqual(len(v["all_frame_sha256"]), 5)
        self.assertEqual(v["all_unique_sha256"], 4)
        self.assertEqual(v["first_divergence_frame_index_zero_based"], 4)
        self.assertEqual(v["max_changed_pixels_post_warmup"], 20)
        self.assertFalse(v["bit_exact_after_warmup"])

    def test_uint8_and_shape_contract(self):
        a = np.zeros((3, 4, 3), dtype=np.uint8)
        with self.assertRaises(ValueError):
            rgb_delta(a, a.astype(np.float32))
        with self.assertRaises(ValueError):
            rgb_delta(a, np.zeros((4, 4, 3), dtype=np.uint8))
        with self.assertRaises(ValueError):
            rgb_sequence([a, a], warmup=2)

    def test_i420_location_does_not_relabel_byte_as_pixel(self):
        a = np.zeros((2, 6, 128, 256), dtype=np.uint8)
        b = a.copy()
        b[1, 5, 127, 255] = 11
        delta = packed_i420_delta(a, b)
        self.assertFalse(delta["bit_exact"])
        self.assertEqual(delta["changed_elements"], 1)
        self.assertEqual(delta["first_changed_indices_camera_plane_row_col"], [1, 5, 127, 255])
        self.assertEqual(delta["max_element_delta"], 11)
        summary = packed_i420_sequence([a, a, a, b], warmup=2)
        self.assertEqual(summary["first_divergence_frame_index_zero_based"], 3)
        self.assertEqual(summary["max_changed_elements_post_warmup"], 1)
        with self.assertRaises(ValueError):
            packed_i420_delta(a, np.zeros((2, 6, 256, 128), dtype=np.uint8))


if __name__ == "__main__":
    unittest.main()
