"""Full prescribed-route traversal, separate from repeatability and model ranking."""
from dataclasses import asdict
from hashlib import sha256
import math,os,uuid
from .kinematics import AgentState,step_ideal
from .model_world_frame import WorldFramePolicyAdapter
from .policies import ModelObservation
from .lane_truth import lane_curvature
from .curved_lane_scenarios import TIGHT_FULL_S_CASE

SCENES={'s_curve_left_right','s_curve_right_left'}
FIXED_FULL_S = 'full-s-closed-loop-v1'
INTEGRATED_FULL_S = 'full-s-integrated-v1'
STRICT=('step','time_s','world_x_m','world_y_m','heading_rad','speed_mps','source_road_rgb_sha256','source_wide_rgb_sha256','road_frame_sha256','wide_frame_sha256','new_img_sha256','raw_model_action','raw_action_sha256','state_after_step_sha256','parent_model_action','applied_world_action','route')

def need(value,message):
 if not value:raise ValueError(message)
def angle(x):return math.atan2(math.sin(x),math.cos(x))

def validate_route(lanes):
 need(isinstance(lanes,(list,tuple)) and 2<=len(lanes)<=16,'bounded explicit full-S lane chain required');rows=[]
 for lane in lanes:
  length=float(lane.length);need(math.isfinite(length) and length>0,'finite positive lane length');start=tuple(float(v) for v in lane.position(0.,0.));end=tuple(float(v) for v in lane.position(length,0.));head0=float(lane.heading_theta_at(0.));head1=float(lane.heading_theta_at(length));width=float(lane.width_at(length/2));curvature=lane_curvature(lane,length/2);name=str(getattr(lane,'index',''))
  need(name not in ('','None') and all(math.isfinite(v) for v in (*start,*end,head0,head1,width,curvature)) and len(start)==len(end)==2 and width>1.8,'valid native lane geometry and virtual footprint');rows.append(dict(lane_id=name,length_m=length,start=list(start),end=list(end),start_heading_rad=head0,end_heading_rad=head1,width_m=width,curvature_1pm=curvature,lane_class=type(lane).__module__+'.'+type(lane).__qualname__))
  if abs(curvature)>1e-6:
   radius=float(lane.radius);center=[float(x) for x in lane.center];phase=float(getattr(lane,'start_phase',getattr(lane,'phase',math.atan2(start[1]-center[1],start[0]-center[0]))));direction=1 if curvature>0 else -1;rows[-1]['shape']=dict(kind='circular',center=center,radius=radius,start_phase=phase,end_phase=float(getattr(lane,'end_phase',phase+direction*length/radius)),direction=direction)
  else:
   vector=getattr(lane,'direction',None);vector=[float(v) for v in vector] if hasattr(vector,'__len__') and len(vector)==2 else [math.cos(head0),math.sin(head0)];rows[-1]['shape']=dict(kind='straight',direction=vector,lateral_direction=[vector[1],-vector[0]])
 need(len({r['lane_id'] for r in rows})==len(rows),'route cannot repeat lane IDs')
 for a,b in zip(rows,rows[1:]):need(math.dist(a['end'],b['start'])<=.35 and abs(angle(a['end_heading_rad']-b['start_heading_rad']))<=.35,'prescribed lanes must join continuously')
 bends=[r for r in rows if abs(r['curvature_1pm'])>1e-6];need(len(bends)==2 and bends[0]['lane_id']==rows[0]['lane_id'] and bends[-1]['lane_id']==rows[-1]['lane_id'] and bends[0]['curvature_1pm']*bends[1]['curvature_1pm']<0,'two opposite native bends required')
 return rows

def route_state(lanes,index,state):
 while True:
  lane=lanes[index];s,right=map(float,lane.local_coordinates((state.x,state.y)));need(math.isfinite(s) and math.isfinite(right),'finite native route coordinates')
  if s>=float(lane.length) and index<len(lanes)-1:index+=1;continue
  break
 need(s>=0,'ego left prescribed segment behind its start');length=float(lane.length);at=min(s,length);width=float(lane.width_at(at));heading=float(lane.heading_theta_at(at));need(math.isfinite(width) and width>1.8 and math.isfinite(heading),'finite terminal-boundary lane geometry')
 # Clamp only the parameter for bounded geometry getters. Never change ego pose/progress.
 return dict(lane_index=index,lane_id=str(lane.index),longitudinal_m=s,length_m=length,lateral_right_m=right,lane_width_m=width,half_width_m=.9,intrusion_m=max(0.,abs(right)+.9-width/2),heading_error_rad=angle(state.heading-heading),terminal_crossed=index==len(lanes)-1 and s>=length)

def registered_case(seed, scene, *, integrated=False):
 return type(seed) is int and ((seed in (20261109,20261110) and scene in SCENES)
                               or (integrated and (seed,scene)==TIGHT_FULL_S_CASE))


def run_full_s(policy,camera,lanes,*,seed,scene,max_steps=600,progress=None,integrated=False):
 speed_override = None if integrated else 8.
 need(type(policy) is WorldFramePolicyAdapter,'exact single existing FRD-to-FLU adapter required');need(registered_case(seed,scene,integrated=integrated) and type(max_steps) is int and 2<=max_steps<=600,'registered full-S condition and bounded steps');geometry=validate_route(lanes);first=lanes[0];start=float(first.length)*.12;xy=first.position(start,0.);state=AgentState(0.,float(xy[0]),float(xy[1]),float(first.heading_theta_at(start)),8.);initial=asdict(state);policy.reset();rows=[];active=0;visited=[str(first.index)];outcome='STEP_LIMIT';error=None;inflight=False;audit_before=0
 def bounds():
  known=len(policy.inner.audit_rows);return [known,min(max_steps,known+1) if inflight and known==audit_before else known]
 def emit(status):
  if progress is not None:progress(dict(status=status,inference_bounds=bounds(),completed_rows=len(rows)))
 try:
  emit('EPISODE_READY')
  for step in range(1,max_steps+1):
   pair=camera.capture(state);need(pair.road.sha256!=pair.wide.sha256,'distinct original road/wide feeds');audit_before=len(policy.inner.audit_rows);inflight=True;emit('INFERENCE_PENDING');action=policy.step(ModelObservation(pair.road,state.speed,state.t,wide_frame=pair.wide));inflight=False
   need(len(policy.inner.audit_rows)==audit_before+1 and len(policy.bridge_receipts)==audit_before+1,'one original audit and single bridge per model step');after=step_ideal(state,action,.05,speed_override=speed_override);truth=route_state(lanes,active,after)
   for idx in range(active+1,truth['lane_index']+1):visited.append(str(lanes[idx].index))
   active=truth['lane_index'];raw=policy.inner.audit_rows[-1];bridge=policy.bridge_receipts[-1];source=getattr(camera,'last_source_rgb_sha256',{});row=dict(step=step,time_s=after.t,world_x_m=after.x,world_y_m=after.y,heading_rad=after.heading,speed_mps=after.speed,road_frame_sha256=pair.road.sha256,wide_frame_sha256=pair.wide.sha256,source_road_rgb_sha256=source.get('road'),source_wide_rgb_sha256=source.get('wide'),parent_model_action=bridge['parent_model_action'],applied_world_action=bridge['applied_world_action'],route=truth,**raw);rows.append(row);state=after;emit('STEP_COMMITTED')
   if truth['intrusion_m']>0:outcome='LANE_INTRUSION';break
   if truth['terminal_crossed']:outcome='FULL_S_COMPLETED';break
 except (ValueError,RuntimeError,TypeError,KeyError,IndexError) as exc:outcome='RUNTIME_ERROR';error=type(exc).__name__+': '+str(exc)
 report=dict(protocol=INTEGRATED_FULL_S if integrated else FIXED_FULL_S,process_id=os.getpid(),process_uuid=uuid.uuid4().hex,seed=seed,scenario=scene,initial_fraction=.12,max_steps=max_steps,completed_steps=len(rows),initial_state=initial,final_state=asdict(state),outcome=outcome,error=error,trial_completed=outcome!='RUNTIME_ERROR',traversal_passed=outcome=='FULL_S_COMPLETED',actual_inference_bounds=bounds(),inference_audit_rows=policy.inner.audit_rows,bridge_receipts=policy.bridge_receipts,frames=rows,geometry=geometry,visited_lane_ids=visited,full_s_route_requested=True,model_sha256=getattr(getattr(policy,'contract',None),'sha256',None),model_test_double=getattr(policy,'is_mock',True),injected_session=getattr(policy,'_injected_session',True),ground_truth_control_used=False,pixel_tolerance=0,extra_render_tasks=0,model_scoring_allowed=False,real_vehicle_testing=False)
 emit('TRIAL_RECORDED');return report

def compare_full_s(a,b,*,integrated=False):
 protocol = INTEGRATED_FULL_S if integrated else FIXED_FULL_S
 for r in (a,b):need(r.get('protocol')==protocol and r.get('model_scoring_allowed') is False and r.get('real_vehicle_testing') is False and r.get('ground_truth_control_used') is False and r.get('pixel_tolerance')==0 and r.get('extra_render_tasks')==0 and r.get('completed_steps')==len(r.get('frames',[])),'complete typed original full-S report required')
 need(a.get('process_uuid')!=b.get('process_uuid') and a.get('process_id')!=b.get('process_id'),'independent native model processes required');need(all(a.get(k)==b.get(k) for k in ('seed','scenario','initial_fraction','max_steps','model_sha256','geometry')),'identical full-S scenario/model/geometry')
 differences=[]
 for index,(left,right) in enumerate(zip(a['frames'],b['frames']),1):
  need(all(k in left and k in right for k in STRICT),'all source/feed/action/state/route fields required');fields=[k for k in STRICT if left[k]!=right[k]]
  if fields:differences.append(dict(step=index,fields=fields))
 complete=a['trial_completed'] is True and b['trial_completed'] is True;exact=complete and len(a['frames'])==len(b['frames']) and a['outcome']==b['outcome'] and not differences;traversal=a['traversal_passed'] is True and b['traversal_passed'] is True and a['outcome']==b['outcome']=='FULL_S_COMPLETED'
 return dict(protocol='full-s-integrated-strict-pair-v1' if integrated else 'full-s-strict-pair-v1',strict_repeat_passed=exact,traversal_passed=traversal,passed=exact and traversal,first_diverging_step=differences[0]['step'] if differences else min(len(a['frames']),len(b['frames']))+1 if len(a['frames'])!=len(b['frames']) else None,differences=differences,outcomes=[a['outcome'],b['outcome']],no_tolerance=True,model_scoring_allowed=False)
