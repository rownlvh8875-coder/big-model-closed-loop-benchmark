"""One owned dedicated-CARLA trial; no shared server or Linux renderer qualification."""
from pathlib import Path
import argparse,hashlib,importlib.metadata,json,os,sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROOT=Path(__file__).resolve().parents[1];REFERENCE_SHA='4fc27cac81099a1ef7cc842b4c63bff832f3a83e499c895871a1baeabe638bb5'

def need(ok,message):
 if not ok:raise ValueError(message)
def context():
 import numpy as np,cv2,carla
 from scripts.laptop_native_trial import digest
 need(np.__version__=='2.4.6' and cv2.__version__=='5.0.0','registered image libraries required');files=['scripts/laptop_carla_trial.py','scripts/run_laptop_validation.py','bigbench/worker_ownership.py','bigbench/carla_validation.py','bigbench/full_s_validation.py','bigbench/full_s_receipts.py','bigbench/optical_calibration.py','scripts/native_mdv3_repeat_trial.py','bigbench/model_world_frame.py','model_specs/md-v3.json','docs/fixtures/sdk3-full-s-native-route-v1.json'];return dict(protocol='carla-common-route-full-s-context-v1',client='0.9.16',server='0.9.16',client_distribution=importlib.metadata.version('carla'),numpy=np.__version__,opencv=cv2.__version__,source_sha256={f:digest(ROOT/f) for f in files},reference_sha256=REFERENCE_SHA,plant='common fixed-speed ideal kinematics; no CARLA vehicle physics',camera='CarlaWorldCamera actual BGRA sensors, synchronized frame IDs',hardware_gpu_qualified=False,physical_optics_validated=False,linux_sdk3_qualified=False)
def run(a):
 from scripts.run_laptop_validation import write,check_model
 from bigbench.worker_ownership import await_parent_ack,ownership_snapshot,prepare_interpreter
 assigned=await_parent_ack(a.out,parent=a.parent,nonce=a.nonce,seed=a.seed,scene=a.scenario)
 if getattr(a,'ownership_only',False):
  report=ownership_snapshot(assigned,'carla');write(a.out/'ownership.json',report);return report
 from bigbench.validation_resources import endpoint
 need(a.parent==os.getppid() and len(a.nonce)==32 and all(c in '0123456789abcdef' for c in a.nonce) and a.dedicated_carla,'owned child with explicit dedicated CARLA scope required');endpoint(a.carla_host,a.carla_port);ref=ROOT/'docs/fixtures/sdk3-full-s-native-route-v1.json';need(hashlib.sha256(ref.read_bytes()).hexdigest()==REFERENCE_SHA,'immutable authenticated native geometry reference');references=json.loads(ref.read_text());found=[r for r in references['cases'] if (r['seed'],r['scenario'])==(a.seed,a.scenario)];need(len(found)==1,'registered CARLA condition');rows=found[0]['geometry'];owner=None;result=None;life=dict(protocol='carla-laptop-model-lifecycle-v1',process_id=os.getpid(),nonce=a.nonce,policy_constructor_entered=False,policy_created=False,inference_bounds=[0,0],status='PRE_RUNTIME',owned_sensor_ids=[],world_mutation_entered=False,world_restored=False);write(a.out/'lifecycle.json',life)
 def progress(row):life.update(row);write(a.out/'lifecycle.json',life)
 try:
  prepare_interpreter(native=True)
  from bigbench.carla_validation import DedicatedCarlaWorld,CarlaWorldCamera,RegisteredCarlaLane
  from bigbench.full_s_validation import validate_route,run_full_s
  owner=DedicatedCarlaWorld(a.carla_host,a.carla_port,rows,dedicated=a.dedicated_carla,on_spawn=lambda ids:progress(dict(owned_sensor_ids=ids)),on_state=progress);camera=CarlaWorldCamera(owner);lanes=[RegisteredCarlaLane(r) for r in rows];ctx=context()
  if a.probe:
   from dataclasses import asdict
   from bigbench.kinematics import AgentState
   frames=[]
   for delta in (0.,2.):
    s=lanes[0].length*.12+delta;p=lanes[0].position(s,0.);pose=AgentState(0.,float(p[0]),float(p[1]),float(lanes[0].heading_theta_at(s)),8.);pair=camera.capture(pose);frames.append(dict(pose=asdict(pose),source=dict(camera.last_source_rgb_sha256),canvas=dict(road=pair.road.sha256,wide=pair.wide.sha256)))
   need(all(frames[0][kind][role]!=frames[1][kind][role] for kind in ('source','canvas') for role in ('road','wide')),'both CARLA cameras must change with actual pose');result=dict(protocol='carla-common-route-camera-probe-v1',passed=True,frames=frames,geometry=validate_route(lanes),official_model_processes=0,inferences=0)
  else:
   check_model(a.model)
   import onnxruntime as ort
   need(ort.__version__=='1.20.1','ORT1.20.1 required')
   from scripts.native_mdv3_repeat_trial import AuditedOfficialOnnx
   from bigbench.model_world_frame import WorldFramePolicyAdapter,SOURCE_ACTION_FRAME
   progress(dict(policy_constructor_entered=True,status='POLICY_LOADING'));inner=AuditedOfficialOnnx(a.model,ROOT/'model_specs/md-v3.json');need(isinstance(inner.session,ort.InferenceSession) and inner.session.get_providers()==['CPUExecutionProvider'],'original real CPU ORT session');progress(dict(policy_created=True,status='POLICY_CREATED'));policy=WorldFramePolicyAdapter(inner,source_action_frame=SOURCE_ACTION_FRAME);result=run_full_s(policy,camera,lanes,seed=a.seed,scene=a.scenario,max_steps=600,progress=progress);result.update(onnxruntime_version=ort.__version__,providers=inner.session.get_providers())
  result.update(context=ctx,process_id=os.getpid(),nonce=a.nonce,seed=a.seed,scenario=a.scenario,actual_waypoints=owner.waypoint_rows,waypoint_validation=owner.waypoint_validation,sensor_frames=camera.sensor_frames,physical_optics_validated=False,hardware_gpu_qualified=False,elapsed_server_clock_restored=False);return result
 finally:
  if owner is not None:owner.close()
  progress(dict(provider_closed=owner is not None,carla_cleanup_restored=bool(owner and owner.restored),status='RECORDED' if result is not None else 'ERROR'))
  if result is not None:result.update(provider_closed=True,carla_cleanup_restored=owner.restored);write(a.out/('probe.json' if a.probe else 'run.json'),result)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parent',type=int,required=True);p.add_argument('--nonce',required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--scenario',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--carla-host',required=True);p.add_argument('--carla-port',type=int,default=2000);p.add_argument('--dedicated-carla',action='store_true');g=p.add_mutually_exclusive_group(required=True);g.add_argument('--probe',action='store_true');g.add_argument('--ownership-only',action='store_true');g.add_argument('--model',type=Path);a=p.parse_args();run(a);return 0
if __name__=='__main__':raise SystemExit(main())
