"""Offline held-out spatial reprojection; no fitting on validation images."""
from pathlib import Path
import hashlib,json,math
PROVENANCE='OFFLINE_MEASURED_CAMERA_CORRESPONDENCES'
POSE_SOURCE='INDEPENDENT_BOARD_POSE_NOT_FIT_ON_HOLDOUT'

def need(ok,message):
 if not ok:raise ValueError(message)
def finite(x):return type(x) in (int,float) and math.isfinite(x)
def vector(v,n):return isinstance(v,list) and len(v)==n and all(finite(x) for x in v)
def sha(data):return hashlib.sha256(data).hexdigest()
def load_json(path):
 data=Path(path).read_bytes();need(len(data)<=128*1024,'bounded manifest');return json.loads(data,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
def local_bytes(root,row,limit):
 name=row.get('file');need(isinstance(name,str) and not Path(name).is_absolute() and '..' not in Path(name).parts,'relative local file required');path=(root/name).resolve();need(path.is_relative_to(root.resolve()) and path.is_file() and path.stat().st_size<=limit,'bounded existing dataset file within manifest directory');data=path.read_bytes();need(sha(data)==row.get('sha256'),'dataset file SHA mismatch');return data

def score_correspondences(points,pixels,k,distortion):
 need(isinstance(points,list) and isinstance(pixels,list) and len(points)==len(pixels)>0 and all(vector(p,3) and p[2]>0 for p in points) and all(vector(p,2) for p in pixels),'finite positive-depth points and measured pixels required')
 need(isinstance(k,list) and len(k)==3 and all(vector(row,3) for row in k) and k[0][0]>0 and k[1][1]>0 and k[0][1]==k[1][0]==k[2][0]==k[2][1]==0 and k[2][2]==1 and vector(distortion,5),'pinhole K and Brown k1,k2,p1,p2,k3 required');k1,k2,p1,p2,k3=distortion;errors=[]
 for (x,y,z),(u,v) in zip(points,pixels):
  x/=z;y/=z;r2=x*x+y*y;radial=1+k1*r2+k2*r2*r2+k3*r2**3;xd=x*radial+2*p1*x*y+p2*(r2+2*x*x);yd=y*radial+p1*(r2+2*y*y)+2*p2*x*y;projected=(k[0][0]*xd+k[0][2],k[1][1]*yd+k[1][2]);error=math.dist(projected,(u,v));need(finite(error),'finite reprojection required');errors.append(error)
 rms=math.sqrt(sum(e*e for e in errors)/len(errors));maximum=max(errors);return dict(passed=rms<=1. and maximum<=2.,rms_error_px=rms,max_error_px=maximum,points=len(errors),fixed_thresholds=dict(rms_px=1.,max_px=2.))

def transformed_board(board,pose):
 cols,rows=board.get('inner_columns'),board.get('inner_rows');size=board.get('square_size_m');rotation=pose.get('rotation');translation=pose.get('translation_m')
 need(type(cols) is int and 4<=cols<=20 and type(rows) is int and 3<=rows<=20 and finite(size) and .001<=size<=.5,'measured bounded board dimensions');need(isinstance(rotation,list) and len(rotation)==3 and all(vector(row,3) for row in rotation) and vector(translation,3),'independently measured board-to-camera rigid pose')
 for i in range(3):
  for j in range(3):need(abs(sum(rotation[i][a]*rotation[j][a] for a in range(3))-(1 if i==j else 0))<=1e-6,'orthonormal board pose')
 a,b,c=rotation;det=a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0]);need(abs(det-1)<=1e-6,'proper rotation required')
 return [[sum(rotation[i][j]*p[j] for j in range(3))+translation[i] for i in range(3)] for y in range(rows) for x in range(cols) for p in [(x*size,y*size,0.)]]

def canonical_pose_key(role,pose):
 rotation=pose.get('rotation');translation=pose.get('translation_m');need(isinstance(rotation,list) and len(rotation)==3 and all(vector(row,3) for row in rotation) and vector(translation,3),'finite independent pose');return (role,*[float(x) for row in rotation for x in row],*[float(x) for x in translation])
def decode_image(raw,camera):
 import numpy as np,cv2
 need(type(camera.get('width')) is int and type(camera.get('height')) is int and 1<=camera['width']<=8192 and 1<=camera['height']<=8192,'bounded declared image dimensions');frame=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_GRAYSCALE);need(frame is not None and list(frame.shape)==[camera['height'],camera['width']],'decoded actual image dimensions must match calibration');return frame

def decoded_image_digest(frame):return sha(str(tuple(frame.shape)).encode('ascii')+b'\0'+frame.tobytes(order='C'))

def validate_dataset(manifest):
 if manifest is None or not Path(manifest).is_file():return dict(protocol='offline-camera-holdout-v1',status='BLOCKED',missing=['MEASURED_CAMERA_HOLDOUT_MANIFEST_REQUIRED'],physical_optics_validated=False,model_loaded=False)
 path=Path(manifest).resolve();root=path.parent;m=load_json(path);need(m.get('schema')=='offline-camera-holdout-v1' and m.get('provenance')==PROVENANCE and m.get('pose_source')==POSE_SOURCE,'measured provenance and independently obtained hold-out poses required')
 # This is a declared provenance contract, not remote authentication of a real camera.
 calibration_bytes=local_bytes(root,m['calibration'],128*1024);calibration=json.loads(calibration_bytes);need(calibration.get('model')=='PINHOLE_BROWN5','only explicitly registered Brown5 model supported');board=m['board'];heldout=m['heldout'];need(isinstance(heldout,list) and 6<=len(heldout)<=32,'at least three held-out images per camera required');train=calibration['training_images'];need(isinstance(train,list) and 6<=len(train)<=128,'independent calibration training images required');train_hashes=set();train_pixels=set()
 for image in train:
  need(image.get('camera') in ('road','wide'),'training camera role');raw=local_bytes(root,image,32*1024**2);frame=decode_image(raw,calibration['cameras'][image['camera']]);pixels=decoded_image_digest(frame);need(image['sha256'] not in train_hashes and pixels not in train_pixels,'unique decoded training images');train_hashes.add(image['sha256']);train_pixels.add(pixels)
 need(all(sum(x['camera']==role for x in train)>=3 for role in ('road','wide')),'training images for both cameras')
 seen=set();seen_pixels=set();poses=set();results=[]
 import numpy as np,cv2
 for image in heldout:
  role=image.get('camera');need(role in ('road','wide'),'held-out camera role');raw=local_bytes(root,image,32*1024**2);digest=sha(raw);need(digest not in train_hashes and digest not in seen,'training/hold-out leakage or duplicate image');seen.add(digest);frame=decode_image(raw,calibration['cameras'][role]);pixels=decoded_image_digest(frame);need(pixels not in train_pixels and pixels not in seen_pixels,'decoded image training/hold-out leakage or duplicate');seen_pixels.add(pixels);pose=image['board_to_camera'];pose_key=canonical_pose_key(role,pose);need(pose_key not in poses,'distinct independent held-out board poses');poses.add(pose_key);points=transformed_board(board,pose);camera=calibration['cameras'][role];ok,corners=cv2.findChessboardCornersSB(frame,(board['inner_columns'],board['inner_rows']));need(ok and corners is not None and len(corners)==len(points),'actual checkerboard detection failed; supplied pixel coordinates are not accepted');score=score_correspondences(points,corners.reshape(-1,2).astype(float).tolist(),camera['K'],camera['distortion']);results.append(dict(camera=role,image_sha256=digest,decoded_image_sha256=pixels,**score))
 need(all(sum(x['camera']==role for x in results)>=3 for role in ('road','wide')),'both cameras require three independent held-out poses');passed=all(x['passed'] for x in results)
 return dict(protocol='offline-camera-holdout-v1',status='SCOPED_PASS' if passed else 'SCOPED_FAIL',correspondences_passed=passed,physical_optics_validated=False,provenance='USER_DECLARED_MEASURED_DATA_NOT_REMOTELY_AUTHENTICATED',scope='held-out Brown5 spatial reprojection only; no photometry, timing, rolling shutter, mounting or full physical fidelity certification',manifest_sha256=sha(path.read_bytes()),calibration_sha256=sha(calibration_bytes),results=results,libraries=dict(numpy=np.__version__,opencv=cv2.__version__),model_loaded=False,files_remain_local=True)
