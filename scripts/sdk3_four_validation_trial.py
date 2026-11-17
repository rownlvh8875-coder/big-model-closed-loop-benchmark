"""Native trial bodies; imports of simulator and official model are lazy."""
from pathlib import Path
from dataclasses import asdict
import hashlib,inspect,json,math,os,sys,time,zlib
from bigbench import sdk3_terrain_priority as repair
from scripts import panda_sdk3_runtime as pins
ROOT=Path(__file__).resolve().parents[1]

def atomic_json(path,value):
 path=Path(path);temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temporary.replace(path)

def source_context():
 from scripts.native_mdv3_repeat_trial import AuditedOfficialOnnx
 from bigbench.native_model_campaign import NativeWorldCamera
 from bigbench.model_world_frame import WorldFramePolicyAdapter
 def digest(fn):return hashlib.sha256(inspect.getsource(fn).encode()).hexdigest()
 return dict(native_entry_sha256=pins.digest(ROOT/'scripts/sdk3_four_validation_native.py'),trial_sha256=pins.digest(__file__),full_s_protocol_sha256=pins.digest(ROOT/'bigbench/full_s_validation.py'),original_camera_capture_sha256=digest(NativeWorldCamera.capture),original_policy_step_sha256=digest(AuditedOfficialOnnx.step),existing_frame_adapter_step_sha256=digest(WorldFramePolicyAdapter.step),terrain_adapter_sha256=pins.digest(ROOT/'bigbench/sdk3_terrain_priority.py'),model_spec_sha256=pins.digest(ROOT/'model_specs/md-v3.json'))

class RawFrames:
 def __init__(self):self.rows=[]
 def record_native_rgb(self,images,hashes):self.rows.append((images,dict(hashes)))

def rate_admission(minimum_steps,second_capture_s):
 if type(minimum_steps) is not int or minimum_steps<1 or type(second_capture_s) not in (int,float) or not math.isfinite(second_capture_s) or second_capture_s<0:raise ValueError('finite measured rate and positive route steps')
 estimate=2*second_capture_s*minimum_steps+600.;return dict(admitted=minimum_steps<=600 and estimate<=3600,minimum_steps=minimum_steps,second_capture_s=second_capture_s,conservative_child_estimate_s=estimate,child_limit_s=3600,max_steps=600)

def capture_probe(camera,raw,lanes,driver,*,intrinsics,out,seed,scene,receipt):
 from bigbench.full_s_validation import validate_route
 from bigbench.kinematics import AgentState
 from bigbench.optical_calibration import PinholeRectifier,assert_intrinsics_match,reference_source
 geometry=validate_route(lanes);out=Path(out);out.mkdir(parents=True,exist_ok=True);rectifier=PinholeRectifier()
 for role in ('road','wide'):assert_intrinsics_match(intrinsics[role],reference_source(role))
 pairs=[];captures=[];first=lanes[0];start=float(first.length)*.12
 for i in range(2):
  s=start+2*i;p=first.position(s,0.);pose=AgentState(0.,float(p[0]),float(p[1]),float(first.heading_theta_at(s)),8.);begin=time.perf_counter();pair=camera.capture(pose);elapsed=time.perf_counter()-begin;pairs.append(pair);captures.append(dict(index=i,pose=asdict(pose),capture_wall_s=elapsed,images=[]))
 pins.need(len(raw.rows)==2,'two original CPU source pairs')
 for i,((images,hashes),pair) in enumerate(zip(raw.rows,pairs)):
  rebuilt,audits=rectifier.rectify_pair(images['road'],images['wide'],road_intrinsics=intrinsics['road'],wide_intrinsics=intrinsics['wide'])
  for role in ('road','wide'):
   rawbytes=images[role].tobytes(order='C');digest=hashlib.sha256(rawbytes).hexdigest();pins.need(digest==hashes[role] and getattr(rebuilt,role).sha256==getattr(pair,role).sha256,'actual original source/canvas byte binding');source=f'pose-{i}-{role}-source.rgb.zlib';canvas=f'pose-{i}-{role}-canvas.rgb.zlib';(out/source).write_bytes(zlib.compress(rawbytes,6));(out/canvas).write_bytes(zlib.compress(getattr(pair,role).rgb,6));captures[i]['images'].append(dict(camera=role,source_file=source,source_sha256=digest,source_shape=[604,964,3],canvas_file=canvas,canvas_sha256=getattr(pair,role).sha256,source_coverage=audits[role].fraction_valid_source_pixels,measured_intrinsics=asdict(intrinsics[role]),warp_matrix=[list(x) for x in audits[role].warp_dst_to_src]))
 for role in ('road','wide'):
  images=[next(r for r in c['images'] if r['camera']==role) for c in captures];pins.need(images[0]['source_sha256']!=images[1]['source_sha256'] and images[0]['canvas_sha256']!=images[1]['canvas_sha256'],'positive pose change must alter both actual source and canvas')
 minimum=math.ceil((sum(r['length_m'] for r in geometry)-start)/.4)
 return dict(protocol='sdk3-four-native-probe-v1',seed=seed,scenario=scene,driver=driver,renderer_candidate=receipt,geometry=geometry,minimum_steps=minimum,capture_calls=2,captures=captures,rate=rate_admission(minimum,captures[1]['capture_wall_s']),physical_optics_validated=False,hardware_gpu_validated=False,carla_validated=False,official_model_processes=0,onnx_inferences=0,extra_render_tasks=0,source_rgb_observer='ZERO_MODEL_CPU_RETENTION_ONLY',source_context=source_context(),scope='native virtual pinhole only; no physical camera dataset')

def _world(seed,scene):
 from bigbench.metadrive_camera import NativeMetaDriveProvider
 from bigbench.curved_lane_scenarios import SCENARIOS,select_native_curve_lanes
 from bigbench.native_route import forward_contiguous_chain
 from metadrive.constants import Semantics,CameraTagStateKey
 provider=NativeMetaDriveProvider(seed=seed,map_config=SCENARIOS[scene].map_config())
 try:
  bends=select_native_curve_lanes(provider.env.current_map,SCENARIOS[scene]);pins.need(len(bends)==2,'two actual native S bends');lanes=forward_contiguous_chain(provider.env.current_map.road_network,bends[0],str(bends[1].index));receipt=repair.install_rgb_terrain_priority(provider.env.engine,terrain_label=Semantics.TERRAIN.label,tag_key=CameraTagStateKey.RGB);return provider,lanes,receipt
 except BaseException:provider.close();raise

def driver_info(provider):
 gsg=provider.env.engine.sensors['bigbench_road'].buffer.get_gsg();pins.need(gsg is not None and gsg.is_valid(),'actual original RGB GSG');return dict(renderer=gsg.get_driver_renderer(),vendor=gsg.get_driver_vendor(),version=gsg.get_driver_version(),physical_device_binding_verified=False,actual_msaa_samples=None)

def probe_trial(args):
 from bigbench.native_model_campaign import NativeWorldCamera
 from bigbench.optical_calibration import intrinsics_from_panda_lens
 provider=None;r=None
 try:
  provider,lanes,receipt=_world(args.seed,args.scenario);raw=RawFrames();camera=NativeWorldCamera(provider,raw_rgb_observer=raw);intrinsics={role:intrinsics_from_panda_lens(provider.env.engine.sensors['bigbench_'+role].get_lens(),964,604) for role in ('road','wide')};r=capture_probe(camera,raw,lanes,{},intrinsics=intrinsics,out=Path(args.out),seed=args.seed,scene=args.scenario,receipt=receipt);r['driver']=driver_info(provider);r['ort_module_loaded']='onnxruntime' in sys.modules;return r
 finally:
  if provider is not None:provider.close()
  if r is not None:r['provider_closed']=True

def full_trial(args):
 from scripts.native_mdv3_repeat_trial import AuditedOfficialOnnx
 from bigbench.model_world_frame import WorldFramePolicyAdapter,SOURCE_ACTION_FRAME,basis_receipt
 from bigbench.native_model_campaign import NativeWorldCamera
 from bigbench.full_s_validation import run_full_s
 from scripts.sdk3_priority_model_native import source_stats_after
 life=dict(protocol='sdk3-four-model-lifecycle-v1',pid=os.getpid(),nonce=args.nonce,seed=args.seed,scenario=args.scenario,policy_constructor_entered=True,policy_created=False,status='POLICY_LOADING',inference_bounds=[0,0],completed_rows=0);path=Path(args.out)/'model-lifecycle.json';atomic_json(path,life);provider=None;r=None
 def progress(payload):life.update(payload);atomic_json(path,life)
 try:
  inner=AuditedOfficialOnnx(Path('/model.onnx'),ROOT/'model_specs/md-v3.json');policy=WorldFramePolicyAdapter(inner,source_action_frame=SOURCE_ACTION_FRAME);life.update(policy_created=True,status='WORLD_LOADING');atomic_json(path,life);provider,lanes,receipt=_world(args.seed,args.scenario);camera=NativeWorldCamera(provider);r=run_full_s(policy,camera,lanes,seed=args.seed,scene=args.scenario,max_steps=600,progress=progress)
  import onnxruntime as ort
  r.update(trial_evidence='CORRECTED_WORLD_FRAME_RGB_PRIORITY_FULL_S',source_context=source_context(),renderer_candidate=receipt,action_basis=basis_receipt(),driver=driver_info(provider),onnxruntime_version=ort.__version__,onnxruntime_providers=inner.session.get_providers(),real_ort_session=isinstance(inner.session,ort.InferenceSession),raw_rgb_observer_used=False,ld_preload_present=bool(os.environ.get('LD_PRELOAD')),draw_trace_modules_loaded=any(k in sys.modules for k in ('scripts.sdk3_draw_trace','scripts.sdk3_draw_trace_native')),selected_sdk_sha256=pins.SDK_SHA,original_camera_class_preserved=type(camera) is NativeWorldCamera,original_policy_class_preserved=type(inner) is AuditedOfficialOnnx);return r
 finally:
  if provider is not None:provider.close()
  life.update(provider_closed=provider is not None,status='TRIAL_RETURNED' if r is not None else 'FAILED_BEFORE_RETURN',trial_completed=r.get('trial_completed') if r is not None else False,source_stats_after=source_stats_after());atomic_json(path,life)
  if r is not None:r['provider_closed']=True;r['source_stats_after']=life['source_stats_after']
