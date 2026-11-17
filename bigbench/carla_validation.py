"""Dedicated CARLA 0.9.16 adapter, common geometry/ideal plant, distinct RGB engine."""
import hashlib,math,queue,time,xml.etree.ElementTree as ET
from .full_s_receipts import RecordedLane

def need(ok,message):
 if not ok:raise ValueError(message)
class RegisteredCarlaLane(RecordedLane):
 """Prescribed native-reference geometry, independently bound to CARLA waypoints."""
 pass

def carla_pose(x,y,heading):return dict(x=float(x),y=-float(y),z=1.22,yaw_deg=-heading*180/math.pi,pitch_deg=0.,roll_deg=0.)
def require_dedicated(dedicated,client,server,actor_types):
 need(dedicated is True and client==server=='0.9.16','explicit dedicated matching CARLA0.9.16 server required');need(not any(kind.startswith(('vehicle.','walker.','sensor.','controller.')) for kind in actor_types),'refuse world mutation with existing dynamic actors/controllers/sensors')
def opendrive(rows):
 from .full_s_validation import validate_route
 lanes=[RegisteredCarlaLane(r) for r in rows];validate_route(lanes);widths={r['width_m'] for r in rows};need(len(widths)==1,'common constant lane width required');width=widths.pop();root=ET.Element('OpenDRIVE');ET.SubElement(root,'header',revMajor='1',revMinor='4',name='registered-native-full-S',version='1.00',date='',north='0',south='0',east='0',west='0');road=ET.SubElement(root,'road',name='registered-native-full-S',length=str(sum(r['length_m'] for r in rows)),id='1',junction='-1');ET.SubElement(road,'link');plan=ET.SubElement(road,'planView');offset=0.
 for r in rows:
  g=ET.SubElement(plan,'geometry',s=str(offset),x=str(r['start'][0]),y=str(r['start'][1]),hdg=str(r['start_heading_rad']),length=str(r['length_m']));shape=r['shape']
  if shape['kind']=='circular':ET.SubElement(g,'arc',curvature=str(shape['direction']/shape['radius']))
  else:ET.SubElement(g,'line')
  offset+=r['length_m']
 elevation=ET.SubElement(road,'elevationProfile');ET.SubElement(elevation,'elevation',s='0',a='0',b='0',c='0',d='0');ET.SubElement(road,'lateralProfile');lanes_node=ET.SubElement(road,'lanes');ET.SubElement(lanes_node,'laneOffset',s='0',a=str(width/2),b='0',c='0',d='0');section=ET.SubElement(lanes_node,'laneSection',s='0');center=ET.SubElement(section,'center');ET.SubElement(center,'lane',id='0',type='none',level='false');right=ET.SubElement(section,'right');lane=ET.SubElement(right,'lane',id='-1',type='driving',level='false');ET.SubElement(lane,'link');ET.SubElement(lane,'width',sOffset='0',a=str(width),b='0',c='0',d='0');ET.SubElement(lane,'roadMark',sOffset='0',type='solid',weight='standard',color='white',width='0.15',laneChange='none');return ET.tostring(root,encoding='unicode')
def verify_waypoints(rows):
 need(isinstance(rows,list) and rows,'actual CARLA waypoint samples required');maximum=0.;angle=0.
 for r in rows:
  values=[r[k] for k in ('expected_x','expected_y','expected_heading_rad','actual_x','actual_y','actual_yaw_deg')];need(all(type(x) in (int,float) and math.isfinite(x) for x in values),'finite actual waypoint coordinates');error=math.hypot(r['actual_x']-r['expected_x'],r['actual_y']+r['expected_y']);difference=math.radians(r['actual_yaw_deg'])+r['expected_heading_rad'];yaw_error=abs(math.atan2(math.sin(difference),math.cos(difference)));need(r['road_id']==1 and r['lane_id']==-1 and error<=.02 and yaw_error<=.005,'actual CARLA lane center/yaw must match the registered common route');maximum=max(maximum,error);angle=max(angle,yaw_error)
 return dict(passed=True,samples=len(rows),max_center_error_m=maximum,max_yaw_error_rad=angle,thresholds=dict(center_m=.02,yaw_rad=.005),scope='CARLA mesh/waypoint binding, not physical sensor fidelity')
def frame_for(q,frame,timeout=10.):
 end=time.monotonic()+timeout
 while True:
  remaining=end-time.monotonic();need(remaining>0,'owned synchronous sensor deadline');image=q.get(timeout=remaining)
  if image.frame<frame:continue
  need(image.frame==frame,'sensor frame arrived ahead of owned world tick');return image

def observed_image_pose(image):
 transform=image.transform;return dict(x=float(transform.location.x),y=float(transform.location.y),z=float(transform.location.z),yaw_deg=float(transform.rotation.yaw),pitch_deg=float(transform.rotation.pitch),roll_deg=float(transform.rotation.roll))
def verify_sensor_pose(actual,expected):
 need(isinstance(actual,dict) and set(actual)==set(expected) and all(type(v) in (int,float) and math.isfinite(v) for v in actual.values()),'actual returned sensor pose required')
 position=max(abs(actual[k]-expected[k]) for k in ('x','y','z'));angular=max(abs(math.degrees(math.atan2(math.sin(math.radians(actual[k]-expected[k])),math.cos(math.radians(actual[k]-expected[k]))))) for k in ('yaw_deg','pitch_deg','roll_deg'));need(position<=1e-4 and angular<=1e-3,'actual returned image pose differs from pre-step ideal camera pose');return dict(max_position_error_m=position,max_angle_error_deg=angular)
def validate_sensor_bindings(frames,poses,sources):
 need(isinstance(frames,list) and len(frames)==len(poses)==len(sources),'complete actual sensor pose/frame/source bindings');previous=None
 for sensor,pose,hashes in zip(frames,poses,sources):
  need(sensor.get('pre_step_state')==pose,'exact pre-step ideal pose receipt');expected=carla_pose(pose['x'],pose['y'],pose['heading']);cameras=sensor['cameras'];frame=sensor['world_frame'];need(type(frame) is int and frame>=0,'actual world frame ID')
  for role in ('road','wide'):
   r=cameras[role];need(r.get('frame')==frame and r.get('source_sha256')==hashes[role] and type(r.get('timestamp')) in (int,float) and math.isfinite(r['timestamp']),'actual sensor frame/source/time');verify_sensor_pose(r.get('transform'),expected)
  need(abs(cameras['road']['timestamp']-cameras['wide']['timestamp'])<=1e-9,'dual sensor time agreement')
  if previous is not None:need(frame==previous['world_frame']+1 and abs(cameras['road']['timestamp']-previous['cameras']['road']['timestamp']-.05)<=1e-6,'uninterrupted synchronous CARLA .05s ticks')
  previous=sensor
 return dict(passed=True,frames=len(frames),scope='actual returned image transforms bound to pre-step ideal poses')

class DedicatedCarlaWorld:
 def __init__(self,host,port,rows,*,dedicated,on_spawn=None,on_state=None):
  self.client=None;self.world=None;self.original=None;self.actors=[];self.mutated=False;self.closed=False;self.restored=False;self.rows=rows;self.on_spawn=on_spawn;self.on_state=on_state
  import carla
  self.carla=carla;client=carla.Client(host,port);client.set_timeout(60.);old=client.get_world();require_dedicated(dedicated,client.get_client_version(),client.get_server_version(),[a.type_id for a in old.get_actors()]);self.client=client;self.original=dict(map_name=old.get_map().name,xodr=old.get_map().to_opendrive(),settings=old.get_settings(),weather=old.get_weather())
  try:
   self.mutated=True
   if self.on_state is not None:self.on_state(dict(world_mutation_entered=True,world_restored=False))
   self.world=client.generate_opendrive_world(opendrive(rows),carla.OpendriveGenerationParameters(vertex_distance=1.,max_road_length=50.,wall_height=0.,additional_width=.6,smooth_junctions=False,enable_mesh_visibility=True));settings=self.world.get_settings();settings.synchronous_mode=True;settings.fixed_delta_seconds=.05;settings.no_rendering_mode=False;self.world.apply_settings(settings);self.world.set_weather(carla.WeatherParameters.ClearNoon);self.waypoint_rows=self.bind_waypoints();self.waypoint_validation=verify_waypoints(self.waypoint_rows)
  except BaseException:self.close();raise
 def bind_waypoints(self):
  rows=[];offset=0.;roadmap=self.world.get_map()
  for lane in [RegisteredCarlaLane(r) for r in self.rows]:
   for f in (.01,.25,.5,.75,.99):
    s=lane.length*f;point=lane.position(s,0.);heading=lane.heading_theta_at(s);wp=roadmap.get_waypoint_xodr(1,-1,offset+s);need(wp is not None,'actual CARLA waypoint missing');rows.append(dict(expected_x=float(point[0]),expected_y=float(point[1]),expected_heading_rad=float(heading),actual_x=wp.transform.location.x,actual_y=wp.transform.location.y,actual_yaw_deg=wp.transform.rotation.yaw,road_id=wp.road_id,lane_id=wp.lane_id))
   offset+=lane.length
  return rows
 def close(self):
  if self.closed:return
  self.closed=True;errors=[]
  for actor in reversed(self.actors):
   try:actor.stop();need(actor.destroy(),'owned CARLA sensor destroy returned false')
   except Exception as e:errors.append(type(e).__name__+': '+str(e))
  if self.client is not None and self.mutated:
   try:
    restore_world(self.client,self.original,[actor.id for actor in self.actors]);self.restored=True
    if self.on_state is not None:self.on_state(dict(world_restored=True))
   except Exception as e:errors.append(type(e).__name__+': '+str(e))
  self.cleanup_errors=errors
  if errors:raise RuntimeError('CARLA owned cleanup/restore failed: '+repr(errors))

class CarlaWorldCamera:
 def __init__(self,owner):
  from .optical_calibration import reference_source,PinholeRectifier,PinholeIntrinsics,assert_intrinsics_match
  self.owner=owner;self.rectifier=PinholeRectifier();self.sensors={};self.queues={};self.intrinsics={};self.last_source_rgb_sha256={};self.sensor_frames=[]
  for role in ('road','wide'):
   k=reference_source(role);bp=owner.world.get_blueprint_library().find('sensor.camera.rgb')
   for key,value in dict(image_size_x='964',image_size_y='604',fov=str(k.fov_h_deg),sensor_tick='0.05',enable_postprocess_effects='false',lens_k='0',lens_kcube='0').items():bp.set_attribute(key,value)
   sensor=owner.world.spawn_actor(bp,owner.carla.Transform(owner.carla.Location(z=1.22)));owner.actors.append(sensor)
   if owner.on_spawn is not None:owner.on_spawn([a.id for a in owner.actors])
   q=queue.Queue(maxsize=32)
   def retain(image,q=q):
    try:q.put_nowait(image)
    except queue.Full:pass # Missing owned frame subsequently fails the bounded join.
   sensor.listen(retain);self.sensors[role]=sensor;self.queues[role]=q;attributes=sensor.attributes;need(int(attributes['image_size_x'])==964 and int(attributes['image_size_y'])==604,'actual CARLA camera dimensions');focal=964/(2*math.tan(math.radians(float(attributes['fov']))/2));actual=PinholeIntrinsics(964,604,focal,focal,482.,302.);assert_intrinsics_match(actual,k);self.intrinsics[role]=actual
 def capture(self,state):
  import numpy as np
  p=carla_pose(state.x,state.y,state.heading);carla=self.owner.carla;transform=carla.Transform(carla.Location(x=p['x'],y=p['y'],z=p['z']),carla.Rotation(yaw=p['yaw_deg']))
  for sensor in self.sensors.values():sensor.set_transform(transform)
  frame=self.owner.world.tick();images={};metadata={}
  for role in ('road','wide'):
   image=frame_for(self.queues[role],frame);observed=observed_image_pose(image);verify_sensor_pose(observed,p);need(image.width==964 and image.height==604,'actual CARLA source dimensions');bgra=np.frombuffer(image.raw_data,dtype=np.uint8);need(bgra.size==964*604*4,'actual CARLA BGRA buffer');rgb=np.ascontiguousarray(bgra.reshape(604,964,4)[:,:,[2,1,0]]);images[role]=rgb;metadata[role]=dict(frame=image.frame,timestamp=image.timestamp,source_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),transform=observed)
  need(metadata['road']['frame']==metadata['wide']['frame']==frame and abs(metadata['road']['timestamp']-metadata['wide']['timestamp'])<=1e-9,'actual dual-camera synchronous frame binding');self.last_source_rgb_sha256={role:r['source_sha256'] for role,r in metadata.items()};from dataclasses import asdict
  self.sensor_frames.append(dict(world_frame=frame,pre_step_state=asdict(state),cameras=metadata));pair,_=self.rectifier.rectify_pair(images['road'],images['wide'],road_intrinsics=self.intrinsics['road'],wide_intrinsics=self.intrinsics['wide']);return pair

class CarlaParentLease:
 """Parent retains original settings even when an owned Python worker times out."""
 def __init__(self,host,port,dedicated):
  import carla
  self.client=carla.Client(host,port);self.client.set_timeout(60.);world=self.client.get_world();require_dedicated(dedicated,self.client.get_client_version(),self.client.get_server_version(),[a.type_id for a in world.get_actors()]);self.original=dict(map_name=world.get_map().name,xodr=world.get_map().to_opendrive(),weather=world.get_weather(),settings=world.get_settings())
 def recover(self,owned_ids):
  world=self.client.get_world();dynamic=require_owned_dynamic(world,owned_ids)
  for actor in dynamic:actor.stop();need(actor.destroy(),'owned sensor cleanup failed')
  if same_original_world(world,self.original):return dict(restored=True,reset_performed=False,owned_sensor_ids=owned_ids,elapsed_server_clock_restored=False)
  restore_world(self.client,self.original,owned_ids);return dict(restored=True,reset_performed=True,owned_sensor_ids=owned_ids,elapsed_server_clock_restored=False)

def require_owned_dynamic(world,owned_ids):
 dynamic=[a for a in world.get_actors() if a.type_id.startswith(('vehicle.','walker.','sensor.','controller.'))];need(all(a.id in owned_ids and a.type_id=='sensor.camera.rgb' for a in dynamic),'foreign dynamic actor detected; refuse world reset');return dynamic

def same_original_world(world,original):
 if world.get_map().name!=original['map_name'] or world.get_map().to_opendrive()!=original['xodr']:return False
 for current,expected,names in [(world.get_settings(),original['settings'],('synchronous_mode','fixed_delta_seconds','no_rendering_mode','substepping','max_substep_delta_time','max_substeps','max_culling_distance','deterministic_ragdolls','tile_stream_distance','actor_active_distance','spectator_as_ego')),(world.get_weather(),original['weather'],('cloudiness','precipitation','precipitation_deposits','wind_intensity','sun_azimuth_angle','sun_altitude_angle','fog_density','fog_distance','fog_falloff','wetness','scattering_intensity','mie_scattering_scale','rayleigh_scattering_scale','dust_storm'))]:
  for name in names:
   if hasattr(expected,name) and (not hasattr(current,name) or getattr(current,name)!=getattr(expected,name)):return False
 return True

def restore_world(client,original,owned_ids):
 world=client.get_world();dynamic=require_owned_dynamic(world,owned_ids)
 for actor in dynamic:actor.stop();need(actor.destroy(),'owned sensor cleanup failed')
 restored=client.generate_opendrive_world(original['xodr']) if original['map_name'].endswith('OpenDriveMap') else client.load_world(original['map_name']);restored.set_weather(original['weather']);restored.apply_settings(original['settings']);return restored
