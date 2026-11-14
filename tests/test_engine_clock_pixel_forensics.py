"""Offline campaign adapter: falsifiable association and counter examples."""
from copy import deepcopy
from hashlib import sha256
import importlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

import cv2
import numpy as np

try:
    tool = importlib.import_module('scripts.engine_clock_pixel_forensics')
except ModuleNotFoundError as exc:
    if exc.name != 'scripts.engine_clock_pixel_forensics':
        raise
    tool = None


def observation(*, capture=1, camera='road', enabled=True, rgb='a', time=1.):
    return dict(capture=capture, camera=camera, raw_sha256=rgb * 64,
                counts=[10,11,11,11] if enabled else None,
                times=[time,time+1,time+1,time+1] if enabled else None,
                markers=[12,12])


class ClockPixelForensicsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(tool, 'new saved03 analysis module required')

    def test_same_numeric_signatures_do_not_erase_different_rgb(self):
        # Break: using counters as image identity would omit this real counterexample.
        result=tool.compare_observations([observation()], [observation(rgb='b',time=9.)])
        self.assertEqual(result['same_counts_and_markers_different_rgb'],[1])
        self.assertEqual(result['same_rgb_different_times'],[])
        self.assertEqual(result['same_counts'],[1])
        self.assertFalse(result['rows'][0]['raw_equal'])

    def test_equal_rgb_can_have_different_times_without_a_causal_claim(self):
        result=tool.compare_observations([observation()], [observation(time=9.)])
        self.assertEqual(result['same_rgb_different_times'],[1])
        self.assertEqual(result['same_counts_and_markers_different_rgb'],[])

    def test_off_clocks_are_unobserved_even_with_equal_texture_values(self):
        for left,right in ((False,False),(True,False),(False,True)):
            with self.subTest(left=left,right=right):
                result=tool.compare_observations([observation(enabled=left)],
                                                 [observation(enabled=right,rgb='b')])
                self.assertFalse(result['clock_observed'])
                self.assertIsNone(result['same_counts'])
                self.assertIsNone(result['same_counts_and_markers_different_rgb'])
                self.assertIsNone(result['rows'][0]['times_equal'])
                self.assertTrue(result['rows'][0]['markers_equal'])

    def test_wrong_call_association_and_partial_clock_data_are_rejected(self):
        for change in ({'camera':'wide'},{'capture':2},{'counts':[True,11,11,11]},
                       {'times':None},{'times':[1.,float('nan'),2.,2.]},
                       {'raw_sha256':'not-a-hash'},{'markers':[True,12]}):
            right=observation();right.update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):
                tool.compare_observations([observation()],[right])

    def test_mixed_on_off_calls_and_empty_or_unbounded_traces_fail(self):
        for rows in ([],[observation()]*13,[observation(),observation(enabled=False,camera='wide')]):
            with self.subTest(length=len(rows)),self.assertRaises(ValueError):
                tool.compare_observations(rows,rows)

    def test_pinned_archive_rejects_corruption_duplicates_and_unsafe_members(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'original.zip'
            for names in (['safe.json'],['../escape'],['/absolute'],['a\\b'],['x','x']):
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore',UserWarning)
                    with zipfile.ZipFile(path,'w') as z:
                        for name in names:z.writestr(name,b'{}')
                raw=path.read_bytes()
                pin=dict(archive_bytes=len(raw),archive_sha256=sha256(raw).hexdigest(),
                         members=len(names),uncompressed_bytes=2*len(names))
                if names==['safe.json']:
                    with tool.open_archive(path,pin) as z:
                        self.assertEqual(tool.read_member(z,'safe.json',2),b'{}')
                        with self.assertRaises(ValueError):tool.read_member(z,'safe.json',1)
                    path.write_bytes(raw+b'changed')
                with self.subTest(names=names),self.assertRaises(ValueError):
                    with tool.open_archive(path,pin):pass

    def test_symlink_archive_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'original.zip'; info=zipfile.ZipInfo('link')
            info.create_system=3;info.external_attr=0o120777<<16
            with zipfile.ZipFile(path,'w') as z:z.writestr(info,b'target')
            raw=path.read_bytes();pin=dict(archive_bytes=len(raw),archive_sha256=sha256(raw).hexdigest(),
                                           members=1,uncompressed_bytes=6)
            with self.assertRaises(ValueError):
                with tool.open_archive(path,pin):pass

    def saved_pair(self):
        stream=io.BytesIO();row=dict(intrinsics={},raw={},canvas={},packed={})
        packed=np.full((2,6,128,256),128,np.uint8);packed[:,:4]=16
        with zipfile.ZipFile(stream,'w') as z:
            for cam in ('road','wide'):
                focal=1324. if cam=='road' else 283.5
                row['intrinsics'][cam]=dict(width=964,height=604,fx=focal,fy=focal,cx=482.,cy=302.)
                for kind,shape in (('raw',(604,964,3)),('canvas',(256,512,3))):
                    image=np.zeros(shape,np.uint8);ok,png=cv2.imencode('.png',image)
                    assert ok
                    payload=png.tobytes();name=f'capture_01/{kind}_{cam}.png'
                    row[kind][cam]=dict(path=name,nbytes=len(payload),sha256=sha256(payload).hexdigest(),
                                        rgb_sha256=sha256(image.tobytes()).hexdigest())
                    z.writestr('output/case_00/'+name,payload)
            name='capture_01/packed_i420.bin';data=packed.tobytes()
            row['packed']=dict(path=name,nbytes=len(data),sha256=sha256(data).hexdigest(),
                               actual_input_sha256=None,association='DERIVED_ONLY_NO_MODEL_CALL')
            z.writestr('output/case_00/'+name,data)
        stream.seek(0)
        return stream,row

    def test_reconstructs_derived_endpoint_without_claiming_real_model_input(self):
        stream,row=self.saved_pair()
        with zipfile.ZipFile(stream) as z:
            raw,intrinsics,packed=tool.load_capture(z,'output/case_00/',row,1)
        self.assertEqual(set(raw),{'road','wide'})
        self.assertFalse(raw['road'].flags.writeable)
        self.assertEqual(packed.sum(),20971520)
        self.assertEqual(intrinsics['road'].width,964)

    def test_wrong_endpoint_hash_shape_path_or_model_association_fails(self):
        stream,original=self.saved_pair()
        edits=[('raw','road','rgb_sha256','f'*64),('canvas','wide','rgb_sha256','f'*64),
               ('raw','road','path','../escape'),('raw','road','path','capture_02/raw_road.png'),
               ('packed',None,'sha256','f'*64),('packed',None,'actual_input_sha256','a'*64),
               ('packed',None,'association','REAL_INPUT')]
        with zipfile.ZipFile(stream) as z:
            for group,cam,key,value in edits:
                row=deepcopy(original);target=row[group] if cam is None else row[group][cam];target[key]=value
                with self.subTest(edit=(group,cam,key)),self.assertRaises(ValueError):
                    tool.load_capture(z,'output/case_00/',row,1)

    def test_catalog_keeps_broad_first_state_without_sparse_filtering(self):
        # Break: deleting first captures would hide the 16-pixel broad state.
        images=[np.zeros((4,4,3),np.uint8),np.ones((4,4,3),np.uint8)]
        catalog=tool.catalog_group(images,[{'case':'C','capture':i+1} for i in range(2)])
        self.assertEqual(len(catalog['states']),2)
        self.assertEqual(catalog['differences'][0]['changed_pixels'],16)
        self.assertEqual(len(catalog['sequence']),2)


if __name__=='__main__':unittest.main()
