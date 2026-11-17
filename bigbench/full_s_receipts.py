"""Portable pure-math verification; caller separately authenticates runtime evidence."""
from dataclasses import asdict
import math
from .kinematics import AgentState,ModelAction,step_ideal
from .model_world_frame import basis_receipt
from .full_s_validation import validate_route,route_state

def need(value,message):
 if not value:raise ValueError(message)
def finite(value):return type(value) in (int,float) and math.isfinite(value)
def close(a,b):return finite(a) and finite(b) and abs(a-b)<=1e-8
def digest64(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)

class RecordedLane:
 def __init__(self,r):
  self.row=r;self.index=r['lane_id'];self.length=r['length_m'];self.width=r['width_m'];self.shape=r['shape'];need(finite(self.length) and self.length>0 and finite(self.width) and self.width>1.8,'valid recorded lane dimensions');s=self.shape;need(s.get('kind') in ('circular','straight'),'supported native primitive')
  if s['kind']=='circular':
   need(all(finite(s.get(k)) for k in ('radius','start_phase','end_phase')) and s['radius']>0 and s.get('direction') in (-1,1) and isinstance(s.get('center'),list) and len(s['center'])==2 and all(finite(v) for v in s['center']) and close(abs((s['end_phase']-s['start_phase'])*s['radius']),self.length),'original circular primitive')
  else:need(isinstance(s.get('direction'),list) and len(s['direction'])==2 and all(finite(v) for v in s['direction']) and close(sum(v*v for v in s['direction']),1.),'original straight unit vector')
  for key,value in s.items():
   if key!='kind':setattr(self,key,value)
 def position(self,longitudinal,lateral):
  s=self.shape
  if s['kind']=='circular':
   phi=s['direction']*longitudinal/s['radius']+s['start_phase'];radius=s['radius']+lateral*s['direction'];return (s['center'][0]+radius*math.cos(phi),s['center'][1]+radius*math.sin(phi))
  direction=s['direction'];return (self.row['start'][0]+longitudinal*direction[0]+lateral*direction[1],self.row['start'][1]+longitudinal*direction[1]-lateral*direction[0])
 def heading_theta_at(self,longitudinal):
  s=self.shape;return s['direction']*longitudinal/s['radius']+s['start_phase']+math.pi/2*s['direction'] if s['kind']=='circular' else self.row['start_heading_rad']
 def width_at(self,longitudinal):return self.width
 def local_coordinates(self,position):
  s=self.shape
  if s['kind']=='straight':
   x,y=position[0]-self.row['start'][0],position[1]-self.row['start'][1];d=s['direction'];return x*d[0]+y*d[1],x*d[1]-y*d[0]
  x,y=position[0]-s['center'][0],position[1]-s['center'][1]
  def wrap(v):v%=2*math.pi;return v-2*math.pi*(v>math.pi)
  phase=wrap(math.atan2(y,x));start=wrap(s['start_phase']);end=wrap(s['end_phase']);near_end=abs(wrap(phase-start))>abs(wrap(phase-end));reference=s['end_phase'] if near_end else s['start_phase'];difference=reference-phase if s['direction']==-1 else phase-reference;longitudinal=wrap(difference)*s['radius']+(self.length if near_end else 0.);return longitudinal,s['direction']*(math.sqrt(x**2+y**2)-s['radius'])

def recorded_route(rows,*,geometry_context='metadrive-native'):
 need(isinstance(rows,list) and 2<=len(rows)<=16,'bounded native route');contexts={'metadrive-native':{'metadrive.component.lane.circular_lane.CircularLane','metadrive.component.lane.straight_lane.StraightLane'},'carla-prescribed':{'bigbench.carla_validation.RegisteredCarlaLane'}};need(geometry_context in contexts,'registered explicit geometry context');allowed=contexts[geometry_context];need(all(r.get('lane_class') in allowed for r in rows),'actual lane classes must match explicit geometry context');lanes=[RecordedLane(r) for r in rows];recomputed=validate_route(lanes)
 for raw,again in zip(rows,recomputed):
  need(raw['lane_id']==again['lane_id'] and all(close(raw[k],again[k]) for k in ('length_m','width_m','start_heading_rad','end_heading_rad','curvature_1pm')) and all(close(x,y) for k in ('start','end') for x,y in zip(raw[k],again[k])),'independent native geometric consistency')
 return lanes


def validate_trajectory(r,seed,scene,*,geometry_context='metadrive-native'):
 need((r.get('seed'),r.get('scenario'))==(seed,scene),'exact trajectory condition');lanes=recorded_route(r['geometry'],geometry_context=geometry_context);state=AgentState(**r['initial_state']);xy=lanes[0].position(lanes[0].length*.12,0.);need(state.t==0. and state.speed==8. and close(state.x,xy[0]) and close(state.y,xy[1]) and close(state.heading,lanes[0].heading_theta_at(lanes[0].length*.12)),'declared native initial pose');frames=r.get('frames');audits=r.get('inference_audit_rows');bridges=r.get('bridge_receipts');bounds=r.get('actual_inference_bounds');need(isinstance(frames,list) and len(frames)==r.get('completed_steps') and 0<=len(frames)<=600 and isinstance(audits,list) and isinstance(bridges,list) and isinstance(bounds,list) and len(bounds)==2 and all(type(x) is int for x in bounds) and len(audits)==bounds[0] and 0<=bounds[0]<=bounds[1]<=min(600,bounds[0]+1) and len(audits)>=len(frames) and len(bridges)>=len(frames),'truthful actual inference bounds and committed rows');active=0;visited=[str(lanes[0].index)];last=None
 for index,row in enumerate(frames,1):
  need(row.get('step')==index and all(digest64(row.get(k)) for k in ('source_road_rgb_sha256','source_wide_rgb_sha256','road_frame_sha256','wide_frame_sha256','new_img_sha256','raw_action_sha256','state_after_step_sha256')) and row['road_frame_sha256']!=row['wide_frame_sha256'],'original ordered source/feed/action/state evidence');audit=audits[index-1];bridge=bridges[index-1];need(all(row.get(k)==audit.get(k) for k in ('new_img_sha256','raw_model_action','raw_action_sha256','state_after_step_sha256')) and row.get('parent_model_action')==bridge.get('parent_model_action') and row.get('applied_world_action')==bridge.get('applied_world_action') and bridge.get('step')==index and all(bridge.get(k)==v for k,v in basis_receipt().items()),'original audit and single untouched bridge receipt')
  raw=row['raw_model_action'];need(isinstance(raw,list) and len(raw) in (2,4) and all(finite(v) for v in raw),'finite raw official action');parent=ModelAction(**row['parent_model_action']);applied=ModelAction(**row['applied_world_action']);need(parent.curvature_1pm==raw[0]/64. and parent.acceleration_mps2==raw[1] and applied.curvature_1pm==-parent.curvature_1pm and applied.acceleration_mps2==parent.acceleration_mps2,'unmodified raw action and exact FRD-to-FLU application');state=step_ideal(state,applied,.05,speed_override=8.);need(all(row.get(k)==v for k,v in dict(time_s=state.t,world_x_m=state.x,world_y_m=state.y,heading_rad=state.heading,speed_mps=state.speed).items()),'exact original ideal kinematics, no steering rescue or pose clamp');truth=route_state(lanes,active,state)
  need(set(truth)==set(row['route']) and all((row['route'][k]==v if isinstance(v,(bool,str)) or type(v) is int else close(row['route'][k],v)) for k,v in truth.items()) and (row['route']['intrusion_m']>0)==(truth['intrusion_m']>0),'independent prescribed-route truth; no intrusion tolerance')
  for idx in range(active+1,truth['lane_index']+1):visited.append(str(lanes[idx].index))
  active=truth['lane_index'];last=truth
  if truth['intrusion_m']>0 or truth['terminal_crossed']:need(index==len(frames),'trial must stop at first departure or completed terminal')
 need(r.get('final_state')==asdict(state) and r.get('visited_lane_ids')==visited,'complete real final pose and prescribed visits');outcome=r.get('outcome');passed=bool(last and last['terminal_crossed'] and last['intrusion_m']==0 and visited==[str(l.index) for l in lanes]);need(r.get('traversal_passed')==passed,'no unearned full-S completion')
 if outcome=='RUNTIME_ERROR':need(r.get('trial_completed') is False and isinstance(r.get('error'),str) and r['error'],'explicit incomplete failure')
 else:
  need(r.get('trial_completed') is True and bounds[0]==bounds[1]==len(frames),'complete actual inference accounting');expected='LANE_INTRUSION' if last and last['intrusion_m']>0 else 'FULL_S_COMPLETED' if passed else 'STEP_LIMIT';need(outcome==expected and (outcome!='STEP_LIMIT' or len(frames)==600),'exact actual traversal outcome')
 return dict(seed=seed,scenario=scene,traversal_passed=passed,outcome=outcome,inference_bounds=bounds)


def bind_case_geometry(report,qualified):
 need(isinstance(qualified,dict) and (report.get('seed'),report.get('scenario'))==(qualified.get('seed'),qualified.get('scenario')),'exact qualified geometry case identity')
 geometry=qualified.get('geometry');need(isinstance(geometry,list) and geometry and report.get('geometry')==geometry,'model trajectory geometry must equal its qualified case probe')
