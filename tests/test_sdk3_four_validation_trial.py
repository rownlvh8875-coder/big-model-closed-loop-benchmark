from pathlib import Path
import hashlib,math,tempfile,unittest,zlib
import numpy as np
try:from scripts import sdk3_four_validation_trial as t
except ImportError:t=None
from bigbench.optical_calibration import PinholeRectifier,reference_source
from tests.full_s_fakes import route
class ProbeCamera:
 def __init__(self,collector,*,stale=False):self.collector=collector;self.stale=stale;self.calls=0;self.rectifier=PinholeRectifier()
 def capture(self,pose):
  self.calls+=1;n=0 if self.stale else self.calls;data={c:np.full((604,964,3),base+n,dtype=np.uint8) for c,base in [('road',31),('wide',87)]};hashes={c:hashlib.sha256(a.tobytes()).hexdigest() for c,a in data.items()};self.collector.record_native_rgb(data,hashes);pair,_=self.rectifier.rectify_pair(data['road'],data['wide']);return pair
class ProbeContracts(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(t,'native virtual optical trial missing')
 def test_two_original_captures_are_bound_to_raw_bytes_warps_and_geometry(self):
  with tempfile.TemporaryDirectory() as d:
   raw=t.RawFrames();camera=ProbeCamera(raw);r=t.capture_probe(camera,raw,route(),{'renderer':'llvmpipe UNIT','vendor':'Mesa','version':'unit'},intrinsics={c:reference_source(c) for c in ('road','wide')},out=Path(d),seed=20261109,scene='s_curve_left_right',receipt={'unit_fixture':True});self.assertEqual(camera.calls,2);self.assertEqual(r['capture_calls'],2);self.assertFalse(r['physical_optics_validated']);self.assertFalse(r['hardware_gpu_validated']);self.assertEqual(r['minimum_steps'],29);self.assertEqual(len(r['captures']),2)
   for capture in r['captures']:
    for row in capture['images']:
     data=zlib.decompress((Path(d)/row['source_file']).read_bytes());self.assertEqual(len(data),604*964*3);self.assertEqual(hashlib.sha256(data).hexdigest(),row['source_sha256']);self.assertGreaterEqual(row['source_coverage'],.99)
 def test_stale_frames_do_not_pass_positive_pose_control(self):
  with tempfile.TemporaryDirectory() as d:
   raw=t.RawFrames();camera=ProbeCamera(raw,stale=True)
   with self.assertRaisesRegex(ValueError,'pose'):t.capture_probe(camera,raw,route(),{'renderer':'unit'},intrinsics={c:reference_source(c) for c in ('road','wide')},out=Path(d),seed=20261109,scene='s_curve_left_right',receipt={})
 def test_rate_admission_respects_route_step_limit_and_whole_child_budget(self):
  self.assertTrue(t.rate_admission(100,1.)['admitted']);self.assertFalse(t.rate_admission(100,20.)['admitted']);self.assertFalse(t.rate_admission(601,.01)['admitted'])
  for steps,seconds in [(True,1.),(100,float('nan')),(0,1.)]:
   with self.assertRaises(ValueError):t.rate_admission(steps,seconds)
if __name__=='__main__':unittest.main()
