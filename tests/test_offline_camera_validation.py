"""Pure synthetic contracts; this suite contains no physical camera evidence."""
import copy,tempfile,unittest
from pathlib import Path
try:from bigbench import offline_camera_validation as c
except ImportError:c=None
class OfflineCalibrationContracts(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(c,'held-out camera correspondence validator missing')
 def test_missing_manifest_is_blocked_without_importing_image_libraries(self):
  r=c.validate_dataset(None);self.assertEqual(r['status'],'BLOCKED');self.assertFalse(r['physical_optics_validated'])
 def test_known_projection_and_first_bad_correspondence_fail(self):
  points=[[0,0,2],[1,0,2],[0,1,2],[1,1,2]];k=[[100,0,50],[0,100,50],[0,0,1]];pixels=[[50,50],[100,50],[50,100],[100,100]]
  good=c.score_correspondences(points,pixels,k,[0]*5);self.assertTrue(good['passed']);self.assertEqual(good['max_error_px'],0.)
  bad=copy.deepcopy(pixels);bad[-1][0]+=3;self.assertFalse(c.score_correspondences(points,bad,k,[0]*5)['passed'])
 def test_invalid_geometry_nonfinite_or_behind_camera_rejected(self):
  for point in ([0,0,-1],[0,0,0],[float('nan'),0,2]):
   with self.subTest(point=point),self.assertRaises(ValueError):c.score_correspondences([point]*12,[[0,0]]*12,[[100,0,50],[0,100,50],[0,0,1]],[0]*5)
 def test_brown_distortion_is_applied_not_ignored(self):
  r=c.score_correspondences([[1,0,2]],[[101.25,50]],[[100,0,50],[0,100,50],[0,0,1]],[.1,0,0,0,0]);self.assertTrue(r['passed']);self.assertAlmostEqual(r['max_error_px'],0)
 def test_training_holdout_image_leakage_is_rejected_before_decoding(self):
  import json,hashlib,cv2,numpy as np
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);images=[]
   for index in range(6):
    raw=cv2.imencode('.png',np.full((48,64),index*20,np.uint8))[1].tobytes();name=str(index)+'.png';(root/name).write_bytes(raw);images.append(dict(camera='road' if index<3 else 'wide',file=name,sha256=hashlib.sha256(raw).hexdigest()))
   calibration=json.dumps(dict(model='PINHOLE_BROWN5',training_images=images,cameras={role:dict(width=64,height=48) for role in ('road','wide')})).encode();(root/'cal.json').write_bytes(calibration);manifest=dict(schema='offline-camera-holdout-v1',provenance=c.PROVENANCE,pose_source=c.POSE_SOURCE,calibration=dict(file='cal.json',sha256=hashlib.sha256(calibration).hexdigest()),board={},heldout=[images[0]]*6);path=root/'manifest.json';path.write_text(json.dumps(manifest))
   with self.assertRaisesRegex(ValueError,'leakage'):c.validate_dataset(path)
 def test_png_reencoding_cannot_leak_same_decoded_image_to_holdout(self):
  import cv2,numpy as np,json,hashlib
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);train=[]
   for index in range(6):
    raw=cv2.imencode('.png',np.full((48,64),index*20,np.uint8),[cv2.IMWRITE_PNG_COMPRESSION,0])[1].tobytes();name=str(index)+'.png';(root/name).write_bytes(raw);train.append(dict(camera='road' if index<3 else 'wide',file=name,sha256=hashlib.sha256(raw).hexdigest()))
   raw=cv2.imencode('.png',np.zeros((48,64),np.uint8),[cv2.IMWRITE_PNG_COMPRESSION,9])[1].tobytes();(root/'reencoded.png').write_bytes(raw);self.assertNotEqual(hashlib.sha256(raw).hexdigest(),train[0]['sha256']);camera=dict(width=64,height=48,K=[[100,0,32],[0,100,24],[0,0,1]],distortion=[0]*5);cal=json.dumps(dict(model='PINHOLE_BROWN5',training_images=train,cameras=dict(road=camera,wide=camera))).encode();(root/'cal.json').write_bytes(cal);held=dict(camera='road',file='reencoded.png',sha256=hashlib.sha256(raw).hexdigest(),board_to_camera=dict(rotation=[[1,0,0],[0,1,0],[0,0,1]],translation_m=[0,0,2]));manifest=dict(schema='offline-camera-holdout-v1',provenance=c.PROVENANCE,pose_source=c.POSE_SOURCE,calibration=dict(file='cal.json',sha256=hashlib.sha256(cal).hexdigest()),board=dict(inner_columns=4,inner_rows=3,square_size_m=.025),heldout=[held]*6);path=root/'manifest.json';path.write_text(json.dumps(manifest))
   with self.assertRaisesRegex(ValueError,'decoded.*leakage'):c.validate_dataset(path)
 def test_numeric_pose_aliases_are_same_pose(self):
  a=dict(rotation=[[1,0,0],[0,1,0],[0,0,1]],translation_m=[0,0,2]);b=dict(rotation=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]],translation_m=[0.,0.,2.]);self.assertEqual(c.canonical_pose_key('road',a),c.canonical_pose_key('road',b))
 def test_manifest_cannot_self_award_pass(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'forged.json';path.write_text('{"provenance":"SYNTHETIC","passed":true}')
   with self.assertRaises(ValueError):c.validate_dataset(path)
if __name__=='__main__':unittest.main()
