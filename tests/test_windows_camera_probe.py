"""Pure/fake camera contracts only; never Windows/native optical evidence."""
from pathlib import Path
import copy, hashlib, json, tempfile, unittest, zlib
from unittest import mock
import numpy as np
from bigbench.optical_calibration import PinholeRectifier, reference_source
from bigbench.full_s_receipts import RecordedLane
try: from bigbench import windows_camera_probe as p
except ImportError: p=None
ROOT=Path(__file__).resolve().parents[1]

def lanes():
    rows=json.loads((ROOT/'docs/fixtures/sdk3-full-s-native-route-v1.json').read_text())['cases'][0]['geometry']
    result=[]
    for row in rows:
        module,name=row['lane_class'].rsplit('.',1)
        klass=type(name,(RecordedLane,),{'__module__':module})
        result.append(klass(row))
    return result

class RawCamera:
    def __init__(self,raw,*,stale=False,same=False): self.raw=raw;self.calls=0;self.stale=stale;self.same=same
    def capture(self,pose):
        self.calls+=1;step=0 if self.stale else self.calls
        images={role:np.full((604,964,3),base+step,dtype=np.uint8) for role,base in [('road',31),('wide',31 if self.same else 87)]}
        self.raw.record_native_rgb(images,{role:hashlib.sha256(a.tobytes()).hexdigest() for role,a in images.items()})
        pair,_=PinholeRectifier().rectify_pair(images['road'],images['wide']);return pair

class WindowsCameraProbeContracts(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(p,'model-free Windows camera evidence module missing')
        # These constant synthetic arrays are generated and replayed in the same
        # reader. CI may install newer readers; no fixture is native evidence.
        self.enterContext(mock.patch('numpy.__version__','2.4.6'))
        self.enterContext(mock.patch('cv2.__version__','5.0.0'))
    def make(self,directory):
        raw=p.RawFrames();camera=RawCamera(raw)
        report=p.capture_probe(camera,raw,lanes(),{role:reference_source(role) for role in ('road','wide')},Path(directory),20261109,'s_curve_left_right')
        self.assertEqual(camera.calls,2)
        return report
    def test_camera_only_allows_recorded_ram_without_admitting_full_s(self):
        from scripts.run_laptop_validation import windows_readiness
        o=dict(system='Windows',machine='AMD64',python_version='3.11.9',memory_available_bytes=4550258688,disk_free_bytes=52635979776)
        versions={'panda3d':'1.10.13','metadrive-simulator':'0.4.3','numpy':'2.4.6','opencv-python':'5.0.0.93'}
        self.assertTrue(p.camera_readiness(o,versions,'0.4.3')['ready'])
        self.assertFalse(windows_readiness(o)['ready'])
        for change in ('assets','version','disk','system'):
            a=copy.deepcopy(o);v=dict(versions);assets='0.4.3'
            if change=='assets':assets=None
            elif change=='version':v['panda3d']='1.10.16'
            elif change=='disk':a['disk_free_bytes']=128*1024**2-1
            else:a['system']='Linux'
            self.assertFalse(p.camera_readiness(a,v,assets)['ready'])
    def test_original_rgb_and_warp_can_be_independently_recomputed(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.make(d);v=p.verify_probe(r,Path(d))
            self.assertTrue(v['virtual_pinhole_passed']);self.assertEqual(v['source_images_verified'],4)
            self.assertFalse(v['model_camera_qualified']);self.assertFalse(v['physical_optics_validated'])
            self.assertEqual(r['official_model_processes'],0);self.assertEqual(r['inferences'],0)
            self.assertEqual(r['capture_calls'],2)
    def test_payload_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.make(d);image=r['captures'][0]['images'][0];file=Path(d)/image['canvas_file']
            file.write_bytes(zlib.compress(bytes(512*256*3)))
            with self.assertRaises(ValueError):p.verify_probe(r,Path(d))
    def test_valid_zlib_with_trailing_bytes_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.make(d);file=Path(d)/r['captures'][0]['images'][0]['source_file'];file.write_bytes(file.read_bytes()+b'extra')
            with self.assertRaises(ValueError):p.verify_probe(r,Path(d))
    def test_oversized_decoded_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.make(d);file=Path(d)/r['captures'][0]['images'][0]['canvas_file'];file.write_bytes(zlib.compress(bytes(512*256*3+1)))
            with self.assertRaises(ValueError):p.verify_probe(r,Path(d))
    def test_case_geometry_pose_and_warp_matrix_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.make(d)
            for field in ('case','geometry','pose','matrix','role','path'):
                bad=copy.deepcopy(r)
                if field=='case':bad['scenario']='s_curve_right_left'
                elif field=='geometry':bad['geometry'][0]['shape']['radius']+=1
                elif field=='pose':bad['captures'][1]['pose']['x']+=.1
                elif field=='matrix':bad['captures'][0]['images'][0]['warp_matrix'][0][0]+=.01
                elif field=='role':bad['captures'][0]['images'][1]['camera']='road'
                else:bad['captures'][0]['images'][0]['source_file']='../outside'
                with self.subTest(field=field),self.assertRaises(ValueError):p.verify_probe(bad,Path(d))
    def test_stale_pose_or_same_view_never_passes(self):
        for stale,same in ((True,False),(False,True)):
            with tempfile.TemporaryDirectory() as d:
                raw=p.RawFrames();camera=RawCamera(raw,stale=stale,same=same)
                with self.assertRaises(ValueError):p.capture_probe(camera,raw,lanes(),{r:reference_source(r) for r in ('road','wide')},Path(d),20261109,'s_curve_left_right')
    def test_source_does_not_match_original_camera_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.make(d);bad=copy.deepcopy(r);bad['captures'][0]['images'][0]['source_sha256']='0'*64
            with self.assertRaises(ValueError):p.verify_probe(bad,Path(d))
    def test_exchanging_both_pose_image_lists_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.make(d);r['captures'][0]['images'],r['captures'][1]['images']=r['captures'][1]['images'],r['captures'][0]['images']
            with self.assertRaises(ValueError):p.verify_probe(r,Path(d))

if __name__=='__main__':unittest.main()
