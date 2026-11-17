"""CPU-only unit fixtures. These are never native or optical evidence."""
import math
from types import SimpleNamespace
from hashlib import sha256
from bigbench.camera import RGBFrame
from bigbench.camera_rig import SchematicPair
from bigbench.kinematics import ModelAction
class Arc:
 def __init__(self,start,heading,direction,index):
  self.radius=1000.;self.direction=direction;self.length=4.;self.index=index;self.phase=heading-direction*math.pi/2;self.center=(start[0]-self.radius*math.cos(self.phase),start[1]-self.radius*math.sin(self.phase))
 def position(self,s,r):
  phase=self.phase+self.direction*s/self.radius;radius=self.radius+self.direction*r;return (self.center[0]+radius*math.cos(phase),self.center[1]+radius*math.sin(phase))
 def heading_theta_at(self,s):return self.phase+self.direction*(math.pi/2+s/self.radius)
 def local_coordinates(self,p):
  x,y=p[0]-self.center[0],p[1]-self.center[1];angle=math.atan2(y,x)-self.phase;angle=math.atan2(math.sin(angle),math.cos(angle));return self.direction*angle*self.radius,self.direction*(math.hypot(x,y)-self.radius)
 def width_at(self,s):return 3.5
class Straight:
 def __init__(self,start,heading,index):self.start=start;self.heading=heading;self.length=4.;self.index=index
 def position(self,s,r):return self.start[0]+s*math.cos(self.heading)+r*math.sin(self.heading),self.start[1]+s*math.sin(self.heading)-r*math.cos(self.heading)
 def heading_theta_at(self,s):return self.heading
 def local_coordinates(self,p):
  x,y=p[0]-self.start[0],p[1]-self.start[1];return x*math.cos(self.heading)+y*math.sin(self.heading),x*math.sin(self.heading)-y*math.cos(self.heading)
 def width_at(self,s):return 3.5

def route():
 a=Arc((0.,0.),0.,1,('A','B',0));b=Straight(a.position(a.length,0.),a.heading_theta_at(a.length),('B','C',0));c=Arc(b.position(b.length,0.),b.heading_theta_at(b.length),-1,('C','D',0));return (a,b,c)
class Camera:
 def __init__(self):self.poses=[];self.last_source_rgb_sha256={}
 def capture(self,state):
  self.poses.append(state);self.last_source_rgb_sha256=dict(road='a'*64,wide='b'*64);return SchematicPair(RGBFrame(512,256,bytes([13])*512*256*3),RGBFrame(512,256,bytes([29])*512*256*3))
class Policy:
 is_mock=True;_injected_session=True;name='UNIT_FIXTURE';contract=SimpleNamespace(sha256='f'*64)
 def __init__(self,curvature=0.,fail_on=None):self.curvature=curvature;self.fail_on=fail_on;self.observations=[];self.reset_count=0;self.reset()
 def reset(self):self.reset_count+=1;self.audit_rows=[];self.trace=[];self.attempts=0
 def step(self,observation):
  self.observations.append(observation);self.attempts+=1
  if self.attempts==self.fail_on:raise RuntimeError('uncertain native inference failure')
  raw=[self.curvature,0.,0.,0.];self.trace.append({'unit_fixture':True});self.audit_rows.append(dict(raw_model_action=raw,raw_action_sha256=sha256(repr(raw).encode()).hexdigest(),state_after_step_sha256=sha256(str(self.attempts).encode()).hexdigest(),new_img_sha256='c'*64));return ModelAction(self.curvature,0.)
