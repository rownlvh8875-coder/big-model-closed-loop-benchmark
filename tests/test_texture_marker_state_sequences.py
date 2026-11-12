"""Saved-byte analysis contracts; no graphics/provider/model fixtures."""
import hashlib
import importlib
from pathlib import Path
import tempfile
import unittest
import warnings
from unittest.mock import patch
import zipfile

import numpy as np

try:
    atlas = importlib.import_module('scripts.texture_marker_state_sequences')
except ModuleNotFoundError as exc:
    if exc.name != 'scripts.texture_marker_state_sequences':
        raise
    atlas = None


class TextureStateSequenceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(atlas, 'CPU state atlas implementation required')

    def image(self):
        return np.zeros((3, 4, 3), np.uint8)

    def marker(self, value, digest='a', camera='road'):
        return dict(camera=camera, before=value, after=value, raw_sha256=digest*64)

    def archive(self, temp, entries=(('one.bin', b'abc'),)):
        root=Path(temp)/'data';root.mkdir();archive=Path(temp)/'original.zip'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(archive,'w') as z:
                for name,data in entries:z.writestr(name,data)
        for name,data in entries:
            if '/' not in name and name!='..':(root/name).write_bytes(data)
        pin=dict(archive_bytes=archive.stat().st_size,
                 archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                 members=len(entries),uncompressed_bytes=sum(len(data) for _,data in entries))
        return root,archive,pin

    def test_catalog_keeps_distinct_first_state_and_repeated_images(self):
        a=self.image();b=a.copy();b[0,0]=[1,2,3]
        result=atlas.state_catalog([a,b,a.copy()])
        self.assertEqual(len(result['states']),2)
        self.assertEqual(result['sequence'][0],result['sequence'][2])
        self.assertNotEqual(result['sequence'][0],result['sequence'][1])
        self.assertEqual(sorted(len(s['indices']) for s in result['states']),[1,2])

    def test_state_ids_are_stable_under_sample_permutation(self):
        a=self.image();b=a.copy();b[1,2]=42
        x=atlas.state_catalog([a,b,a]);y=atlas.state_catalog([b,a,a])
        self.assertEqual(x['sequence'],[y['sequence'][1],y['sequence'][0],y['sequence'][2]])

    def test_noncontiguous_equal_pixels_match_without_input_mutation(self):
        a=np.arange(36,dtype=np.uint8).reshape(3,4,3)[:,::-1]
        a.setflags(write=False);b=a.copy();before=a.tobytes()
        self.assertEqual(len(atlas.state_catalog([a,b])['states']),1)
        self.assertEqual(atlas.sparse_locations([a,b]),[])
        self.assertEqual(a.tobytes(),before)

    def test_malformed_or_unbounded_image_cohorts_rejected(self):
        good=self.image()
        for values in ([],[good]*33,[good,good.astype(np.int16)],
                       [good,good[:2]],[good[:,:,:2]],[np.empty((0,4,3),np.uint8)]):
            with self.subTest(count=len(values)),self.assertRaises(ValueError):
                atlas.state_catalog(values)

    def test_sparse_signed_deltas_and_coordinates_do_not_wrap(self):
        a=self.image();a[2,3]=[255,10,0];b=a.copy();b[2,3]=[0,12,255]
        points=atlas.sparse_locations([a,b])
        self.assertEqual(len(points),1)
        self.assertEqual(points[0]['xy'],[3,2])
        self.assertEqual(points[0]['rgb'],[[255,10,0],[0,12,255]])
        self.assertEqual(points[0]['delta_from_first'],[[0,0,0],[-255,2,255]])

    def test_sparse_cap_is_union_not_individual_pair_count(self):
        a=self.image();b=a.copy();c=a.copy();b[0,0:2]=1;c[0,1:3]=1
        with self.assertRaisesRegex(ValueError,'sparse'):
            atlas.sparse_locations([a,b,c],limit=2)
        self.assertEqual(len(atlas.sparse_locations([a,b,c],limit=3)),3)

    def test_unchanged_images_have_no_sparse_variants(self):
        a=self.image()
        self.assertEqual(atlas.sparse_locations([a,a.copy()],limit=0),[])
        b=a.copy();b[0,0]=1
        with self.assertRaises(ValueError):atlas.sparse_locations([a,b],limit=0)

    def test_equal_observed_counters_do_not_hide_raw_counterexample(self):
        r=atlas.compare_markers([self.marker(12)],[self.marker(12,'b')])
        self.assertTrue(r['observed']);self.assertTrue(r['values_equal'])
        self.assertTrue(r['patterns_equal']);self.assertFalse(r['raw_trace_equal'])
        self.assertEqual(r['same_values_different_raw'],[dict(row=1,camera='road',before=12,after=12)])

    def test_off_nulls_remain_unobserved_even_when_both_are_null(self):
        r=atlas.compare_markers([self.marker(None)],[self.marker(None,'b')])
        self.assertFalse(r['observed'])
        for key in ('values_equal','patterns_equal','same_values_different_raw'):
            self.assertIsNone(r[key])
        self.assertFalse(r['raw_trace_equal'])

    def test_different_counters_can_have_identical_raw_bytes(self):
        r=atlas.compare_markers([self.marker(-1)],[self.marker(-(2**31))])
        self.assertTrue(r['observed']);self.assertFalse(r['values_equal'])
        self.assertTrue(r['patterns_equal']);self.assertTrue(r['raw_trace_equal'])
        self.assertEqual(r['same_values_different_raw'],[])

    def test_invalid_counter_type_range_or_camera_order_rejected(self):
        for wrong in (self.marker(True),self.marker(2**31),self.marker(12,camera='wide')):
            with self.subTest(wrong=wrong),self.assertRaises(ValueError):
                atlas.compare_markers([self.marker(12)],[wrong])

    def test_partial_marker_pair_or_mixed_on_off_trace_rejected(self):
        wrong=self.marker(12);wrong['after']=None
        for rows in ([wrong],[self.marker(None),self.marker(12)]):
            with self.assertRaises(ValueError):atlas.compare_markers(rows,rows)

    def test_original_archive_is_verified_without_writing_or_extracting(self):
        with tempfile.TemporaryDirectory() as temp:
            root,archive,pin=self.archive(temp);before=archive.read_bytes()
            result=atlas.verify_archive(root,archive,pin)
            self.assertEqual(result['members'],1)
            self.assertEqual(archive.read_bytes(),before)
            self.assertEqual([p.name for p in root.iterdir()],['one.bin'])

    def test_changed_extraction_or_zip_digest_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root,archive,pin=self.archive(temp);(root/'one.bin').write_bytes(b'abd')
            with self.assertRaises(ValueError):atlas.verify_archive(root,archive,pin)
            (root/'one.bin').write_bytes(b'abc');pin['archive_sha256']='0'*64
            with self.assertRaises(ValueError):atlas.verify_archive(root,archive,pin)

    def test_extra_extracted_member_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root,archive,pin=self.archive(temp);(root/'extra').write_bytes(b'x')
            with self.assertRaises(ValueError):atlas.verify_archive(root,archive,pin)
            (root/'extra').unlink();(root/'one.bin').unlink();(root/'one.bin').symlink_to(archive)
            with self.assertRaises(ValueError):atlas.verify_archive(root,archive,pin)

    def test_unsafe_duplicate_and_directory_zip_members_rejected(self):
        for entries in ((('../escape',b'x'),),(('one.bin',b'a'),('one.bin',b'b')),(('dir/',b''),)):
            with self.subTest(entries=entries),tempfile.TemporaryDirectory() as temp:
                root,archive,pin=self.archive(temp,entries)
                with self.assertRaises(ValueError):atlas.verify_archive(root,archive,pin)

    def test_existing_output_and_output_inside_either_input_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a=root/'a';b=root/'b';a.mkdir();b.mkdir()
            out=root/'keep.json';out.write_text('keep')
            for target in (out,a/'new.json',b/'new.json'):
                with self.assertRaises(ValueError):atlas.run(a,root/'a.zip',b,root/'b.zip',target)
            self.assertEqual(out.read_text(),'keep')
            self.assertEqual(list(a.iterdir()),[]);self.assertEqual(list(b.iterdir()),[])

    def test_wrong_cpu_runtime_rejected(self):
        with patch.object(atlas.importlib.metadata,'version',return_value='wrong'):
            with self.assertRaisesRegex(ValueError,'runtime'):atlas.require_cpu_runtime()


if __name__=='__main__':unittest.main()
