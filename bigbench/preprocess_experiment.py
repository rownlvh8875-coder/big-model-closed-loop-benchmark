"""Experimental RGB-derived YUV preprocessing; no sensor/GPU parity claim.

Core NumPy sampler transcribed from the independently checked CPU study.
Original policy code/session/output/state/control and native renderer stay frozen.
"""
import numpy as np


def _coords(matrix,width,height):
 if type(width) is not int or type(height) is not int or not 0<width<=4096 or not 0<height<=4096:raise ValueError('bounded positive dimensions required')
 m=np.asarray(matrix,dtype=np.float32)
 if m.shape!=(3,3) or not np.isfinite(m).all():raise ValueError('finite 3x3 matrix required')
 x,y=np.meshgrid(np.arange(width,dtype=np.float32),np.arange(height,dtype=np.float32))
 dx=m[0,0]*x+m[0,1]*y+m[0,2];dy=m[1,0]*x+m[1,1]*y+m[1,2];dw=m[2,0]*x+m[2,1]*y+m[2,2]
 if np.any(np.abs(dw)<1e-12):raise ValueError('projective depth unavailable')
 sx=dx/dw;sy=dy/dw
 if not np.isfinite(sx).all() or not np.isfinite(sy).all() or np.any(np.abs(sx)>1e9) or np.any(np.abs(sy)>1e9):raise ValueError('bounded projected coordinates required')
 return sx,sy


def nearest_plane(plane,matrix,width,height):
 plane=np.asarray(plane)
 if plane.dtype!=np.uint8 or plane.ndim!=2 or not plane.size or max(plane.shape)>4096:raise ValueError('bounded uint8 plane required')
 x,y=_coords(matrix,width,height)
 rx,ry=np.rint(x),np.rint(y)
 ix=np.clip(rx,0,plane.shape[1]-1).astype(np.int32);iy=np.clip(ry,0,plane.shape[0]-1).astype(np.int32)
 return np.ascontiguousarray(plane[iy,ix])


def sample_six(y,u,v,matrix,width=512,height=256):
 y,u,v=map(np.asarray,(y,u,v))
 if y.ndim!=2 or y.shape[0]%2 or y.shape[1]%2 or width%2 or height%2 or u.shape!=(y.shape[0]//2,y.shape[1]//2) or v.shape!=u.shape:raise ValueError('even I420 dimensions required')
 h=np.asarray(matrix,dtype=np.float32)
 if h.shape!=(3,3):raise ValueError('3x3 matrix required')
 uv=h*np.array([[1,1,.5],[1,1,.5],[2,2,1]],np.float32)
 raw=nearest_plane(y,h,width,height)
 return np.stack((raw[::2,::2],raw[1::2,::2],raw[::2,1::2],raw[1::2,1::2],nearest_plane(u,uv,width//2,height//2),nearest_plane(v,uv,width//2,height//2)))



def scoped_step(adapter):
 from .onnx_policy import OnnxBigModelPolicy
 from .recorded_official_execution import clone
 return clone(OnnxBigModelPolicy.step, camera_pair_to_model=adapter)


class LiveInput:
 """One camera capture -> one input; retain first source/canvas/tensor only."""
 def __init__(self, camera, intrinsics, variant, out):
  from pathlib import Path
  if variant not in ('rgb_linear', 'source_yuv_nearest_even'):
   raise ValueError('registered input intervention required')
  self.camera, self.intrinsics, self.variant = camera, intrinsics, variant
  self.out = Path(out)
  self.pending = None
  self.expected = None
  self.count = 0
  self.rows = []
  camera.raw_rgb_observer = self

 def record_native_rgb(self, images, hashes):
  if self.pending is not None: raise ValueError('previous input was not consumed')
  self.pending = (images, dict(hashes))

 @property
 def last_source_rgb_sha256(self):
  return self.camera.last_source_rgb_sha256

 def capture(self, pose):
  pair = self.camera.capture(pose)
  if self.pending is None: raise ValueError('fresh source pair absent')
  self.expected = (pair.road.sha256, pair.wide.sha256)
  return pair

 def prepare(self, road, wide):
  import cv2
  import hashlib
  from .image_adapter import camera_pair_to_model
  from .optical_calibration import reference_model
  if self.pending is None or self.expected != (road.sha256, wide.sha256):
   raise ValueError('one fresh source/canvas binding required')
  images, hashes = self.pending
  baseline = camera_pair_to_model(road, wide)
  if self.variant == 'rgb_linear':
   result = baseline
  else:
   planes = []
   for role in ('road', 'wide'):
    source = images[role]
    if source.dtype != np.uint8 or source.shape != (604,964,3):
     raise ValueError('original source dimensions required')
    if hashlib.sha256(source.tobytes()).hexdigest() != hashes[role]:
     raise ValueError('source snapshot changed')
    i420 = cv2.cvtColor(source, cv2.COLOR_RGB2YUV_I420).reshape(-1)
    n = 604*964
    y = i420[:n].reshape(604,964)
    u = i420[n:n+n//4].reshape(302,482)
    v = i420[n+n//4:].reshape(302,482)
    h = self.intrinsics[role].matrix @ np.linalg.inv(reference_model(role).matrix)
    planes.append(sample_six(y,u,v,h))
   result = np.ascontiguousarray(np.stack(planes))
  if result.shape != (2,6,128,256) or result.dtype != np.uint8:
   raise ValueError('exact new_img contract required')
  self.count += 1
  row = dict(step=self.count,source_sha256=hashes,canvas_sha256=list(self.expected),
      baseline_tensor_sha256=hashlib.sha256(baseline.tobytes()).hexdigest(),
      actual_tensor_sha256=hashlib.sha256(result.tobytes()).hexdigest())
  self.rows.append(row)
  if self.count == 1:
   for role in ('road','wide'):
    (self.out/('first-'+role+'.rgb')).write_bytes(images[role].tobytes())
   (self.out/'first-input.bin').write_bytes(result.tobytes())
   (self.out/'first-baseline.bin').write_bytes(baseline.tobytes())
  self.pending = self.expected = None
  return result


def policy_class():
 # Lazy: a CPU-only sampler import does not import a native/model runtime.
 from .onnx_policy import OnnxBigModelPolicy
 from scripts.native_mdv3_repeat_trial import recurrent_receipt
 import hashlib
 class ExperimentalInputOnnx(OnnxBigModelPolicy):
  def __init__(self, model, spec, preparer):
   self.preparer = preparer
   super().__init__(model,spec)
   from types import MethodType
   self.original_step_with_explicit_input = MethodType(scoped_step(lambda road,wide:self.preparer.prepare(road,wide)),self)
   self.evidence_class = 'EXPERIMENTAL_INPUT_INTERVENTION_REAL_ONNX_NOT_BASELINE_CLASS'
  def reset(self):
   super().reset()
   self.audit_rows = []
   self.initial_recurrent_sha256 = recurrent_receipt(self.state)
  def step(self, observation):
   before = recurrent_receipt(self.state) if not self.audit_rows else None
   if before is not None and before != self.initial_recurrent_sha256:
    raise ValueError('reset-state changed before the first actual inference')
   action = self.original_step_with_explicit_input(observation)
   if before is not None:self.preparer.rows[-1]['initial_recurrent_sha256']=before
   raw = self.last_model_outputs['action']
   if self.preparer.rows[-1]['actual_tensor_sha256'] != self.last_input_image_sha256:
    raise ValueError('actual feed did not match the prepared input')
   self.audit_rows.append(dict(new_img_sha256=self.last_input_image_sha256,
      raw_model_action=[float(x) for x in raw],
      raw_action_sha256=hashlib.sha256(raw.tobytes()).hexdigest(),
      state_after_step_sha256=recurrent_receipt(self.state)))
   return action
 return ExperimentalInputOnnx
