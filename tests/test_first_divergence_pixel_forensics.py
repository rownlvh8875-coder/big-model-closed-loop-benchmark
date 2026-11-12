"""CPU-only sparse-pixel interventions; no provider or model fixtures."""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from bigbench.optical_calibration import PinholeIntrinsics

try:
    forensic = importlib.import_module('scripts.first_divergence_pixel_forensics')
except ModuleNotFoundError as exc:
    if exc.name != 'scripts.first_divergence_pixel_forensics':
        raise
    forensic = None


class PixelForensicsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(forensic, 'standalone CPU forensic tool required')

    def pair(self):
        return {name: np.zeros((604, 964, 3), np.uint8) for name in ('road', 'wide')}

    def intrinsics(self):
        return dict(road=PinholeIntrinsics(964,604,1324.,1324.,482.,302.),
                    wide=PinholeIntrinsics(964,604,283.5,283.5,482.,302.))

    def test_signed_delta_and_top_left_patch_do_not_wrap(self):
        a=np.zeros((6,7,3),np.uint8);b=a.copy()
        a[0,0]=[255,10,1];b[0,0]=[0,12,1]
        point=forensic.pixel_locations(a,b)[0]
        self.assertEqual(point['xy'],[0,0])
        self.assertEqual(point['delta_rgb'],[-255,2,0])
        self.assertEqual(point['patch_bounds_xyxy'],[0,0,2,2])
        self.assertEqual(np.array(point['patch_a']).shape,(3,3,3))
        self.assertEqual(point['patch_a'][0][0],[255,10,1])

    def test_bottom_right_patch_is_clipped_and_locations_row_major(self):
        a=np.zeros((6,7,3),np.uint8);b=a.copy();b[5,6]=1;b[0,3]=2
        points=forensic.pixel_locations(a,b)
        self.assertEqual([p['xy'] for p in points],[[3,0],[6,5]])
        self.assertEqual(points[1]['patch_bounds_xyxy'],[4,3,6,5])

    def test_invalid_images_rejected(self):
        good=np.zeros((3,4,3),np.uint8)
        for wrong in (good.astype(np.int16),good[:,:,:2],good[:2],None):
            with self.subTest(wrong=type(wrong)),self.assertRaises(ValueError):
                forensic.pixel_locations(good,wrong)

    def test_unchanged_pair_has_only_empty_minimal_subset(self):
        a=self.pair();result=forensic.analyze_pair(a,a,self.intrinsics())
        self.assertEqual(result['pixels'],[])
        self.assertEqual([r['mask'] for r in result['subsets']],[0])
        self.assertEqual(result['subsets'][0]['packed_checksum'],20971520)
        self.assertEqual(result['minimal_exact_subsets'],[0])
        self.assertTrue(result['joint_delta_equals_sum_of_singles'])

    def test_raw_corner_outside_model_warp_does_not_change_input(self):
        a=self.pair();b={k:v.copy() for k,v in a.items()};b['road'][0,0]=255
        result=forensic.analyze_pair(a,b,self.intrinsics())
        self.assertEqual(len(result['pixels']),1)
        self.assertEqual([r['changed_packed_values'] for r in result['subsets']],[0,0])
        self.assertEqual(result['minimal_exact_subsets'],[0])

    def test_camera_interventions_are_independent_and_inputs_immutable(self):
        a=self.pair();b={k:v.copy() for k,v in a.items()}
        b['road'][302,482]=[200,50,20];b['wide'][302,482]=[30,170,80]
        before={('a',k):v.tobytes() for k,v in a.items()}
        before.update({('b',k):v.tobytes() for k,v in b.items()})
        for v in (*a.values(),*b.values()):v.setflags(write=False)
        result=forensic.analyze_pair(a,b,self.intrinsics())
        self.assertEqual([p['camera'] for p in result['pixels']],['road','wide'])
        rows={r['mask']:r for r in result['subsets']}
        self.assertEqual(set(rows),{0,1,2,3})
        self.assertGreater(rows[1]['camera_changed_values']['road'],0)
        self.assertEqual(rows[1]['camera_changed_values']['wide'],0)
        self.assertEqual(rows[2]['camera_changed_values']['road'],0)
        self.assertGreater(rows[2]['camera_changed_values']['wide'],0)
        self.assertEqual(result['minimal_exact_subsets'],[3])
        self.assertEqual(rows[3]['packed_sha256'],result['target_packed_sha256'])
        for group,values in (('a',a),('b',b)):
            for key,value in values.items():self.assertEqual(value.tobytes(),before[(group,key)])

    def test_five_changed_pixels_fail_before_subset_enumeration(self):
        a=self.pair();b={k:v.copy() for k,v in a.items()};b['road'][302,480:485]=255
        with self.assertRaisesRegex(ValueError,'four'):
            forensic.analyze_pair(a,b,self.intrinsics())

    def test_pixel_neighborhood_allocation_is_bounded(self):
        a=np.zeros((4,5,3),np.uint8);b=a.copy();b[0,:]=255
        with self.assertRaisesRegex(ValueError,'four'):forensic.pixel_locations(a,b)

    def test_neighboring_pixel_effects_are_not_assumed_additive(self):
        a=self.pair();b={k:v.copy() for k,v in a.items()}
        b['wide'][302,482]=[30,170,80];b['wide'][302,483]=[30,170,80]
        result=forensic.analyze_pair(a,b,self.intrinsics())
        self.assertFalse(result['joint_delta_equals_sum_of_singles'])
        self.assertEqual(result['minimal_exact_subsets'],[3])

    def test_wrong_pair_keys_and_shape_rejected(self):
        a=self.pair()
        for b in ({'road':a['road']},{**a,'extra':a['road']},
                  {**a,'wide':a['wide'][:600]}):
            with self.subTest(keys=b.keys()),self.assertRaises(ValueError):
                forensic.analyze_pair(a,b,self.intrinsics())

    def test_wrong_runtime_fails_closed(self):
        with patch.object(forensic.importlib.metadata,'version',return_value='wrong'):
            with self.assertRaisesRegex(ValueError,'runtime'):forensic._require_runtime()

    def test_wrong_archive_is_rejected_without_extraction(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=root/'data';data.mkdir();archive=root/'old.zip';archive.write_bytes(b'wrong')
            with self.assertRaises(ValueError):forensic.verify_archive(data,archive)
            self.assertEqual(list(data.iterdir()),[])
            self.assertEqual(archive.read_bytes(),b'wrong')

    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data').mkdir();(root/'link').symlink_to(root/'data',target_is_directory=True)
            with self.assertRaises(ValueError):forensic.verify_archive(root/'link',root/'missing.zip')

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'report.json';out.write_text('keep')
            with self.assertRaises(ValueError):forensic.run(root/'data',root/'archive.zip',out)
            self.assertEqual(out.read_text(),'keep')

    def test_output_inside_input_rejected_before_allocation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'data';root.mkdir()
            with self.assertRaises(ValueError):forensic.run(root,root/'archive.zip',root/'new/report.json')
            self.assertEqual(list(root.iterdir()),[])


if __name__=='__main__':unittest.main()
