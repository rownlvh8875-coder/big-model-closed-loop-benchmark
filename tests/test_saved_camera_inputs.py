"""Synthetic contract fixtures; actual saved-pixel replay is a separate command."""
from pathlib import Path
from unittest import mock
import copy,hashlib,io,json,tempfile,unittest,zipfile,zlib
import numpy as np,cv2
from bigbench.optical_calibration import PinholeRectifier,PinholeIntrinsics
try:from scripts import verify_saved_camera_inputs as s
except ImportError:s=None
ROOT=Path(__file__).resolve().parents[1]

def independent_pack(frames):
 values=[]
 for rgb in frames:
  data=cv2.cvtColor(rgb,cv2.COLOR_RGB2YUV_I420).reshape(-1);y=data[:131072].reshape(256,512)
  values.append(np.stack([y[dy::2,dx::2] for dy,dx in [(0,0),(1,0),(0,1),(1,1)]]+[data[131072:163840].reshape(128,256),data[163840:].reshape(128,256)]))
 return np.ascontiguousarray(np.stack(values))

class SavedCameraInputTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(s,'saved real-pixel input receiver missing')
  self.enterContext(mock.patch('numpy.__version__','2.4.6'));self.enterContext(mock.patch('cv2.__version__','5.0.0'))
 def fixture(self):
  p=json.loads((ROOT/'docs/evidence/four-validation-20261118/actual-02/20261109-s_curve_left_right/probe.json').read_text());bundle={};tensors=[]
  yy,xx=np.indices((604,964));rect=PinholeRectifier()
  for i,cap in enumerate(p['captures']):
   arrays={role:np.stack(((xx+3*yy+13*j+i)%256,(2*xx+5*yy+29*j+i)%256,(7*xx+11*yy+43*j+i)%256),axis=-1).astype(np.uint8) for j,role in enumerate(('road','wide'))}
   intr={r['camera']:PinholeIntrinsics(**r['measured_intrinsics']) for r in cap['images']};pair,audit=rect.rectify_pair(arrays['road'],arrays['wide'],road_intrinsics=intr['road'],wide_intrinsics=intr['wide'])
   frames=[]
   for row in cap['images']:
    role=row['camera'];frame=getattr(pair,role);row['source_sha256']=hashlib.sha256(arrays[role].tobytes()).hexdigest();row['canvas_sha256']=frame.sha256;row['source_coverage']=audit[role].fraction_valid_source_pixels;row['warp_matrix']=[list(x) for x in audit[role].warp_dst_to_src];bundle[row['source_file']]=zlib.compress(arrays[role].tobytes());bundle[row['canvas_file']]=zlib.compress(frame.rgb);frames.append(np.frombuffer(frame.rgb,dtype=np.uint8).reshape(256,512,3))
   tensors.append(independent_pack(frames))
  digest=hashlib.sha256(tensors[0].tobytes()).hexdigest();first=dict(step=1,new_img_sha256=digest)
  for row in p['captures'][0]['images']:first['source_'+row['camera']+'_rgb_sha256']=row['source_sha256'];first[row['camera']+'_frame_sha256']=row['canvas_sha256']
  reports=[dict(seed=p['seed'],scenario=p['scenario'],geometry=p['geometry'],initial_state=p['captures'][0]['pose'],frames=[copy.deepcopy(first)],inference_audit_rows=[dict(new_img_sha256=digest)]) for _ in range(2)];bundle['probe.json']=json.dumps(p).encode();return bundle,reports
 def test_two_original_first_inputs_and_shifted_pose_control_are_bound(self):
  b,models=self.fixture();r=s.replay_case(b,models,20261109,'s_curve_left_right');self.assertEqual(r['first_model_inputs_bound'],2);self.assertTrue(r['first_step_only']);self.assertEqual(r['input_shape'],[2,6,128,256]);self.assertEqual(r['first_new_img_sha256'],models[0]['frames'][0]['new_img_sha256']);self.assertNotEqual(r['pose_control_new_img_sha256'],r['first_new_img_sha256']);self.assertFalse(r['later_model_frame_pixels_verified'])
 def test_case_role_or_audit_hash_swap_is_rejected(self):
  b,reports=self.fixture()
  for field in ('case','role','audit','first-step'):
   models=copy.deepcopy(reports)
   if field=='case':models[0]['seed']=20261110
   elif field=='role':models[0]['frames'][0]['source_road_rgb_sha256']=models[0]['frames'][0]['source_wide_rgb_sha256']
   elif field=='audit':models[0]['inference_audit_rows'][0]['new_img_sha256']='0'*64
   else:models[0]['frames'][0]['step']=2
   with self.subTest(field=field),self.assertRaises(ValueError):s.replay_case(b,models,20261109,'s_curve_left_right')
 def test_pose_swap_or_changed_saved_pixels_is_rejected(self):
  b,reports=self.fixture()
  for field in ('pose','pixels','trailing'):
   bad=dict(b)
   if field=='pose':
    p=json.loads(bad['probe.json']);p['captures'][0]['images'],p['captures'][1]['images']=p['captures'][1]['images'],p['captures'][0]['images'];bad['probe.json']=json.dumps(p).encode()
   elif field=='pixels':bad['pose-0-road-canvas.rgb.zlib']=zlib.compress(bytes(512*256*3))
   else:bad['pose-0-road-source.rgb.zlib']+=b'trailing'
   with self.subTest(field=field),self.assertRaises(ValueError):s.replay_case(bad,reports,20261109,'s_curve_left_right')
 def test_adapter_role_order_defect_cannot_agree_with_independent_packing(self):
  from bigbench import image_adapter
  b,reports=self.fixture();original=image_adapter.camera_pair_to_model
  with mock.patch.object(image_adapter,'camera_pair_to_model',side_effect=lambda road,wide:original(wide,road)):
   with self.assertRaises(ValueError):s.replay_case(b,reports,20261109,'s_curve_left_right')
 def test_duplicate_or_oversize_zip_member_is_rejected(self):
  stream=io.BytesIO()
  with zipfile.ZipFile(stream,'w') as z:z.writestr('x.json',b'12345')
  with zipfile.ZipFile(stream) as z:
   with self.assertRaises(ValueError):s.read_member(z,'x.json',4)
  import warnings
  stream=io.BytesIO()
  with warnings.catch_warnings():
   warnings.simplefilter('ignore',UserWarning)
   with zipfile.ZipFile(stream,'w') as z:z.writestr('x.json',b'a');z.writestr('x.json',b'b')
  with zipfile.ZipFile(stream) as z:
   with self.assertRaises(ValueError):s.read_member(z,'x.json',100)
 def test_cold_help_needs_no_native_or_image_libraries(self):
  import subprocess,sys
  r=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/verify_saved_camera_inputs.py'),'--help'],capture_output=True,text=True,timeout=10);self.assertEqual(r.returncode,0,r.stderr)
 def test_authenticated_archive_bytes_survive_path_replacement(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'archive.zip'
   with zipfile.ZipFile(path,'w') as z:z.writestr('x.json',b'original')
   original=path.read_bytes();meta=dict(id=1,name='unit',size_in_bytes=len(original),digest='sha256:'+hashlib.sha256(original).hexdigest(),workflow_run=dict(id=s.RUN_ID,head_sha=s.ACTIVATION))
   verified=s.authenticate_archive(path,meta)
   self.assertIsInstance(verified,tuple,'authentication must retain the immutable consumed bytes')
   origin,snapshot=verified
   with zipfile.ZipFile(path,'w') as z:z.writestr('x.json',b'replaced')
   with zipfile.ZipFile(io.BytesIO(snapshot)) as z:self.assertEqual(s.read_member(z,'x.json',100),b'original')
   self.assertEqual(origin['sha256'],hashlib.sha256(snapshot).hexdigest())

if __name__=='__main__':unittest.main()
