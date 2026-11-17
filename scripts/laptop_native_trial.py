"""One owned Windows stock-Panda probe/trial; intentionally independent of Linux SDK3."""
from pathlib import Path
import argparse,hashlib,importlib.metadata,os,platform,sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROOT=Path(__file__).resolve().parents[1]

def need(ok,message):
 if not ok:raise ValueError(message)
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def windows_context(provider):
 import numpy as np,cv2,panda3d.core as core
 from bigbench.laptop_gpu import TARGET
 need(platform.system()=='Windows' and platform.machine().lower() in ('amd64','x86_64'),'Windows native x64 only');need(core.PandaSystem.getVersionString()=='1.10.13' and importlib.metadata.version('metadrive-simulator')=='0.4.3' and np.__version__=='2.4.6' and cv2.__version__=='5.0.0','explicit Windows Panda/MetaDrive/NumPy/OpenCV versions required');gsg=provider.env.engine.sensors['bigbench_road'].buffer.get_gsg();need(gsg is not None and gsg.is_valid(),'actual original RGB context');renderer=gsg.get_driver_renderer();vendor=gsg.get_driver_vendor();need(TARGET.lower() in renderer.lower() and 'nvidia' in vendor.lower(),'original model camera must use target NVIDIA renderer')
 files=['scripts/laptop_native_trial.py','bigbench/full_s_validation.py','bigbench/native_model_campaign.py','scripts/native_mdv3_repeat_trial.py','bigbench/model_world_frame.py','bigbench/sdk3_terrain_priority.py','model_specs/md-v3.json']
 return dict(protocol='windows-native-full-s-context-v1',system=platform.system(),python=platform.python_version(),panda=core.PandaSystem.getVersionString(),metadrive=importlib.metadata.version('metadrive-simulator'),numpy=np.__version__,opencv=cv2.__version__,renderer=renderer,vendor=vendor,driver_version=gsg.get_driver_version(),core_sha256=digest(core.__file__),panda_dll_sha256={p.name:digest(p) for p in sorted(Path(core.__file__).parent.glob('*.dll'))},source_sha256={name:digest(ROOT/name) for name in files},linux_sdk3_qualified=False,physical_optics_validated=False)
def world(seed,scene):
 from bigbench.metadrive_camera import NativeMetaDriveProvider
 from bigbench.curved_lane_scenarios import SCENARIOS,select_native_curve_lanes
 from bigbench.native_route import forward_contiguous_chain
 from bigbench.sdk3_terrain_priority import install_rgb_terrain_priority
 from metadrive.constants import Semantics,CameraTagStateKey
 provider=NativeMetaDriveProvider(seed=seed,map_config=SCENARIOS[scene].map_config())
 try:
  bends=select_native_curve_lanes(provider.env.current_map,SCENARIOS[scene]);need(len(bends)==2,'two original native bends');lanes=forward_contiguous_chain(provider.env.current_map.road_network,bends[0],str(bends[1].index));receipt=install_rgb_terrain_priority(provider.env.engine,terrain_label=Semantics.TERRAIN.label,tag_key=CameraTagStateKey.RGB);return provider,lanes,receipt
 except BaseException:provider.close();raise

def run(args):
 from scripts.run_laptop_validation import write,check_model
 need(args.parent==os.getppid() and len(args.nonce)==32 and all(c in '0123456789abcdef' for c in args.nonce) and platform.system()=='Windows','live owned Windows child required before any simulator or model import');need((args.seed,args.scenario) in [(s,c) for s in (20261109,20261110) for c in ('s_curve_left_right','s_curve_right_left')],'registered condition')
 out=args.out;life=dict(protocol='windows-laptop-model-lifecycle-v1',process_id=os.getpid(),nonce=args.nonce,policy_constructor_entered=False,policy_created=False,inference_bounds=[0,0],status='PRE_RUNTIME');write(out/'lifecycle.json',life);provider=None;result=None
 def progress(row):life.update(row);write(out/'lifecycle.json',life)
 try:
  from bigbench.native_model_campaign import NativeWorldCamera
  from bigbench.full_s_validation import validate_route,run_full_s
  provider,lanes,repair=world(args.seed,args.scenario);context=windows_context(provider);camera=NativeWorldCamera(provider)
  if args.probe:
   from dataclasses import asdict
   from bigbench.kinematics import AgentState
   from bigbench.optical_calibration import reference_source,intrinsics_from_panda_lens,assert_intrinsics_match
   geometry=validate_route(lanes);frames=[];intrinsics={}
   for role in ('road','wide'):
    k=intrinsics_from_panda_lens(provider.env.engine.sensors['bigbench_'+role].get_lens(),964,604);assert_intrinsics_match(k,reference_source(role));intrinsics[role]=asdict(k)
   for delta in (0.,2.):
    s=lanes[0].length*.12+delta;p=lanes[0].position(s,0.);pose=AgentState(0.,float(p[0]),float(p[1]),float(lanes[0].heading_theta_at(s)),8.);pair=camera.capture(pose);frames.append(dict(pose=asdict(pose),source=dict(camera.last_source_rgb_sha256),canvas=dict(road=pair.road.sha256,wide=pair.wide.sha256)))
   need(all(frames[0][kind][role]!=frames[1][kind][role] for kind in ('source','canvas') for role in ('road','wide')),'both original cameras must change with actual pose');result=dict(protocol='windows-native-camera-probe-v1',passed=True,frames=frames,geometry=geometry,intrinsics=intrinsics,context=context,official_model_processes=0,inferences=0,scope='virtual lens/source/pose checks only; not physical calibration or model repeatability')
  else:
   check_model(args.model)
   import onnxruntime as ort
   need(ort.__version__=='1.20.1','ORT1.20.1 CPU required')
   from scripts.native_mdv3_repeat_trial import AuditedOfficialOnnx
   from bigbench.model_world_frame import WorldFramePolicyAdapter,SOURCE_ACTION_FRAME
   progress(dict(policy_constructor_entered=True,status='POLICY_LOADING'));inner=AuditedOfficialOnnx(args.model,ROOT/'model_specs/md-v3.json');need(isinstance(inner.session,ort.InferenceSession) and inner.session.get_providers()==['CPUExecutionProvider'],'original real ORT CPU session required');progress(dict(policy_created=True,status='POLICY_CREATED'));policy=WorldFramePolicyAdapter(inner,source_action_frame=SOURCE_ACTION_FRAME);result=run_full_s(policy,camera,lanes,seed=args.seed,scene=args.scenario,max_steps=600,progress=progress);result.update(context=context,onnxruntime_version=ort.__version__,providers=inner.session.get_providers())
  result.update(seed=args.seed,scenario=args.scenario,process_id=os.getpid(),nonce=args.nonce,renderer_candidate=repair);return result
 finally:
  if provider is not None:provider.close()
  progress(dict(provider_closed=provider is not None,status='RECORDED' if result is not None else 'ERROR'))
  if result is not None:result['provider_closed']=True;write(out/('probe.json' if args.probe else 'run.json'),result)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parent',type=int,required=True);p.add_argument('--nonce',required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--scenario',required=True);p.add_argument('--out',type=Path,required=True);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--probe',action='store_true');g.add_argument('--model',type=Path);a=p.parse_args();run(a);return 0
if __name__=='__main__':raise SystemExit(main())
