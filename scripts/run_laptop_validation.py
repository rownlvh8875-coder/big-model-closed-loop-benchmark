"""Explicit Windows laptop checks; inventory never installs or downloads anything."""
from pathlib import Path
import argparse,hashlib,json,os,secrets,subprocess,sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROOT=Path(__file__).resolve().parents[1]
MODEL_SHA='35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199'
CASES=[(seed,scene) for seed in (20261109,20261110) for scene in ('s_curve_left_right','s_curve_right_left')]

def write(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8');tmp.replace(path)
def check_model(path):
 path=Path(path)
 if not path.is_file() or path.stat().st_size!=768750198:raise ValueError('explicit official model path with 768750198 bytes required')
 digest=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024**2),b''):digest.update(block)
 if digest.hexdigest()!=MODEL_SHA:raise ValueError('official model SHA mismatch')
 return dict(sha256=MODEL_SHA,bytes=768750198)
def windows_readiness(o):
 missing=[]
 if o.get('system')!='Windows' or o.get('machine','').lower() not in ('amd64','x86_64'):missing.append('WINDOWS_NATIVE_REQUIRED')
 if not str(o.get('python_version','')).startswith('3.11.'):missing.append('PYTHON_3_11_REQUIRED')
 if type(o.get('memory_available_bytes')) is not int or o['memory_available_bytes']<8*1024**3:missing.append('8_GIB_AVAILABLE_RAM_REQUIRED')
 if type(o.get('disk_free_bytes')) is not int or o['disk_free_bytes']<4*1024**3:missing.append('4_GIB_FREE_DISK_REQUIRED')
 return dict(ready=not missing,missing=missing,scope='separate Windows stock-Panda full-S cohort; not frozen Linux SDK3')
def aggregate_laptop(inventory,*,gpu,physical,carla,full_s):
 physical_status='BLOCKED_NO_MEASURED_DATA' if not physical or physical.get('status')=='BLOCKED' else 'SCOPED_HOLDOUT_ONLY' if physical.get('status')=='SCOPED_PASS' else 'FAIL'
 gpu_status='NOT_RUN' if gpu is None else 'PASS' if gpu.get('validation',{}).get('passed') is True else 'BLOCKED' if gpu.get('status')=='BLOCKED' else 'FAIL'
 carla_status='BLOCKED_NO_DEDICATED_SERVER' if carla is None or carla.get('status')=='BLOCKED' else 'SCOPED_CONTRACT_PASS' if carla.get('cross_engine_contracts_passed') is True else 'FAIL' if carla.get('status')=='MEASURED' else 'NOT_RUN'
 full_status='NOT_RUN' if full_s is None else 'PASS' if full_s.get('passed') is True else 'BLOCKED' if full_s.get('status')=='BLOCKED' else 'FAIL'
 return dict(protocol='laptop-four-validation-summary-v1',full_s=full_status,hardware_gpu=gpu_status,physical_optics=physical_status,carla=carla_status,all_four_validation_tracks_passed=False,resource_observation=inventory)
def carla_readiness(host,port,dedicated):
 from bigbench.validation_resources import endpoint
 if not host or not dedicated:return dict(status='BLOCKED',missing=['EXPLICIT_DEDICATED_CARLA_0_9_16_ENDPOINT_REQUIRED'],cross_engine_validated=False,world_mutated=False)
 remote=endpoint(host,port)
 try:
  import carla
  client=carla.Client(remote['host'],remote['port']);client.set_timeout(10.);local=client.get_client_version();server=client.get_server_version()
  if local!='0.9.16' or server!='0.9.16':return dict(status='BLOCKED',missing=['EXACT_CLIENT_SERVER_0_9_16_REQUIRED'],client_version=local,server_version=server,cross_engine_validated=False,world_mutated=False)
  return dict(status='READY_FOR_PROBE',client_version=local,server_version=server,cross_engine_validated=False,world_mutated=False,scope='read-only endpoint/version readiness only; not a cross-engine model validation')
 except Exception as e:return dict(status='BLOCKED',missing=['CARLA_CLIENT_OR_SERVER_UNAVAILABLE'],error=type(e).__name__+': '+str(e),cross_engine_validated=False,world_mutated=False)
def launch_worker(*,dest,seed,scene,probe,model,backend='metadrive',carla_host=None,carla_port=2000):
 dest=Path(dest);dest.mkdir(parents=True,exist_ok=False);nonce=secrets.token_hex(16);cmd=[sys.executable,'-I','-B',str(ROOT/('scripts/laptop_carla_trial.py' if backend=='carla' else 'scripts/laptop_native_trial.py')),'--parent',str(os.getpid()),'--nonce',nonce,'--seed',str(seed),'--scenario',scene,'--out',str(dest),'--probe' if probe else '--model',*([str(model.resolve())] if not probe else [])];ledger=dict(nonce=nonce,spawn_attempted=False,pid=None,returncode=None,model=not probe);lease=None;report=None
 if backend=='carla':
  from bigbench.carla_validation import CarlaParentLease
  lease=CarlaParentLease(carla_host,carla_port,True);cmd.extend(['--carla-host',carla_host,'--carla-port',str(carla_port),'--dedicated-carla'])
 try:
  with (dest/'stdout.log').open('wb') as stdout,(dest/'stderr.log').open('wb') as stderr:
   child=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,cwd=ROOT,env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2'));ledger.update(spawn_attempted=True,pid=child.pid);write(dest/'owner.json',ledger)
   try:ledger['returncode']=child.wait(timeout=(600 if backend=='carla' else 240) if probe else 9000)
   except subprocess.TimeoutExpired:child.kill();child.wait(timeout=15);ledger.update(returncode=child.returncode,timeout=True);raise RuntimeError('owned laptop child deadline exceeded')
  if ledger['returncode']!=0:raise RuntimeError('laptop child failed; inspect retained lifecycle/stdout/stderr')
  report=json.loads((dest/'probe.json' if probe else dest/'run.json').read_text(encoding='utf-8'))
  if report.get('nonce')!=nonce or report.get('process_id')!=child.pid or report.get('seed')!=seed or report.get('scenario')!=scene or report.get('provider_closed') is not True:raise ValueError('owned complete laptop receipt required')
  return report
 finally:
  write(dest/'owner.json',ledger)
  if lease is not None and (report is None or report.get('carla_cleanup_restored') is not True):
   life=json.loads((dest/'lifecycle.json').read_text()) if (dest/'lifecycle.json').is_file() else {}
   try:write(dest/'parent-recovery.json',lease.recover(life.get('owned_sensor_ids',[])))
   except Exception as e:write(dest/'parent-recovery.json',dict(restored=False,error=type(e).__name__+': '+str(e)));raise
def run_full_cohort(out,model,inventory):
 ready=windows_readiness(inventory)
 if not ready['ready']:return dict(status='BLOCKED',**ready,model_processes=0,inferences=[0,0])
 check_model(model)
 from bigbench.laptop_gpu import run_gpu_probe
 gpu=run_gpu_probe();write(out/'gpu.json',gpu)
 if not gpu.get('validation',{}).get('passed'):return dict(status='BLOCKED',missing=['ACTUAL_WINDOWS_GPU_CANARY_REQUIRED'],model_processes=0,inferences=[0,0])
 probes=[]
 for seed,scene in CASES:probes.append(launch_worker(dest=out/f'probe-{seed}-{scene}',seed=seed,scene=scene,probe=True,model=None))
 if len({json.dumps(p['context'],sort_keys=True) for p in probes})!=1 or not all(p.get('passed') is True for p in probes):raise ValueError('all four zero-model camera probes must qualify the same Windows context')
 from bigbench.full_s_receipts import validate_trajectory
 from bigbench.full_s_validation import compare_full_s
 cases=[]
 for seed,scene in CASES:
  pair=[]
  for index in (0,1):
   r=launch_worker(dest=out/f'{seed}-{scene}'/f'run-{index}',seed=seed,scene=scene,probe=False,model=model)
   if r.get('context')!=probes[0]['context'] or r.get('model_sha256')!=MODEL_SHA or r.get('model_test_double') is not False or r.get('injected_session') is not False:raise ValueError('real official model in qualified Windows context required')
   validate_trajectory(r,seed,scene);pair.append(r)
  result=compare_full_s(*pair);cases.append(dict(seed=seed,scenario=scene,**result));write(out/'case-results.json',cases)
 return dict(status='MEASURED',passed=all(c['passed'] for c in cases),cases=cases,model_processes=8,inferences=[sum(json.loads(p.read_text())['actual_inference_bounds'][i] for p in out.glob('20*/run-*/run.json')) for i in (0,1)],linux_sdk3_qualified=False,physical_optics_validated=False,carla_validated=False)
def observed_laptop_counts(out):
 known=upper=low=high=0
 for path in Path(out).glob('20*/run-*/owner.json'):
  owner=json.loads(path.read_text());life_path=path.parent/'lifecycle.json';life=json.loads(life_path.read_text()) if life_path.is_file() else {}
  if not owner.get('spawn_attempted'):continue
  if life.get('policy_constructor_entered') is True:known+=1;upper+=1
  elif life.get('policy_constructor_entered') is False:continue
  else:upper+=1
  bounds=life.get('inference_bounds',[0,600]);need_bounds=isinstance(bounds,list) and len(bounds)==2 and all(type(x) is int for x in bounds) and 0<=bounds[0]<=bounds[1]<=600
  if not need_bounds:bounds=[0,600]
  low+=bounds[0];high+=bounds[1]
 return dict(known_model_processes=known,upper_model_processes=upper,inference_bounds=[low,high])
def validate_carla_report(r,seed,scene):
 from bigbench.carla_validation import RegisteredCarlaLane,verify_waypoints
 from bigbench.full_s_validation import validate_route
 from bigbench.full_s_receipts import validate_trajectory
 from scripts.laptop_carla_trial import context
 if r.get('context')!=context() or r.get('carla_cleanup_restored') is not True:raise ValueError('owned qualified CARLA context and cleanup required')
 ref=json.loads((ROOT/'docs/fixtures/sdk3-full-s-native-route-v1.json').read_text());rows=next(x['geometry'] for x in ref['cases'] if (x['seed'],x['scenario'])==(seed,scene));lanes=[RegisteredCarlaLane(row) for row in rows]
 if r.get('geometry')!=validate_route(lanes):raise ValueError('CARLA prescribed geometry differs from registered native reference')
 actual=r['actual_waypoints'];expected=[]
 for lane in lanes:
  for fraction in (.01,.25,.5,.75,.99):
   point=lane.position(lane.length*fraction,0.);expected.append((float(point[0]),float(point[1]),float(lane.heading_theta_at(lane.length*fraction))))
 if len(actual)!=len(expected) or any((row['expected_x'],row['expected_y'],row['expected_heading_rad'])!=point for row,point in zip(actual,expected)):raise ValueError('actual CARLA waypoints must bind the independently registered sample positions')
 if verify_waypoints(actual)!=r['waypoint_validation']:raise ValueError('CARLA waypoint verdict recomputation')
 frames=r.get('sensor_frames');committed=r.get('frames',[])
 if not isinstance(frames,list) or len(frames)!=len(committed):raise ValueError('complete actual CARLA sensor frame evidence required')
 previous=None
 for sensor,row in zip(frames,committed):
  cameras=sensor['cameras'];frame=sensor['world_frame']
  if cameras['road']['frame']!=cameras['wide']['frame'] or cameras['road']['frame']!=frame or abs(cameras['road']['timestamp']-cameras['wide']['timestamp'])>1e-9 or any(cameras[role]['source_sha256']!=row['source_'+role+'_rgb_sha256'] for role in ('road','wide')):raise ValueError('actual dual sensor frame/source binding')
  if previous is not None and (frame!=previous['world_frame']+1 or abs(cameras['road']['timestamp']-previous['cameras']['road']['timestamp']-.05)>1e-6):raise ValueError('uninterrupted synchronous CARLA .05s ticks')
  previous=sensor
 return validate_trajectory(r,seed,scene,geometry_context='carla-prescribed')
def run_carla_cohort(out,model,host,port,dedicated):
 readiness=carla_readiness(host,port,dedicated)
 if readiness['status']!='READY_FOR_PROBE':return dict(status='BLOCKED',readiness=readiness,model_processes=0,inferences=[0,0],cross_engine_contracts_passed=False)
 check_model(model);probes=[]
 for seed,scene in CASES:probes.append(launch_worker(dest=out/f'probe-{seed}-{scene}',seed=seed,scene=scene,probe=True,model=None,backend='carla',carla_host=host,carla_port=port))
 if not all(p.get('passed') is True and p.get('carla_cleanup_restored') is True for p in probes) or len({json.dumps(p['context'],sort_keys=True) for p in probes})!=1:raise ValueError('four actual qualified CARLA camera/route probes required before model loading')
 from bigbench.full_s_validation import compare_full_s
 cases=[]
 for seed,scene in CASES:
  pair=[]
  for index in (0,1):
   r=launch_worker(dest=out/f'{seed}-{scene}'/f'run-{index}',seed=seed,scene=scene,probe=False,model=model,backend='carla',carla_host=host,carla_port=port)
   if r.get('context')!=probes[0]['context'] or r.get('model_sha256')!=MODEL_SHA or r.get('model_test_double') is not False or r.get('injected_session') is not False:raise ValueError('original real official model in qualified CARLA context')
   validate_carla_report(r,seed,scene);pair.append(r)
  cases.append(dict(seed=seed,scenario=scene,**compare_full_s(*pair)));write(out/'case-results.json',cases)
 return dict(status='MEASURED',passed=all(c['passed'] for c in cases),cross_engine_contracts_passed=all(c['strict_repeat_passed'] for c in cases),cases=cases,counts=observed_laptop_counts(out),scope='common geometry, camera/clock/action/ideal-plant contracts across MetaDrive and CARLA; each engine driving outcome separately; no across-engine pixel equality or model ranking',hardware_gpu_qualified=False,physical_optics_validated=False)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('inventory','gpu','physical','carla-readiness','full-s','carla-full-s'),default='inventory');p.add_argument('--out',type=Path,required=True);p.add_argument('--model',type=Path);p.add_argument('--calibration',type=Path);p.add_argument('--carla-host');p.add_argument('--carla-port',type=int,default=2000);p.add_argument('--dedicated-carla',action='store_true');a=p.parse_args();out=a.out.resolve()
 if out.exists():p.error('--out must be a fresh directory; preserve previous results')
 out.mkdir(parents=True)
 from bigbench.validation_resources import collect_resources
 inventory=collect_resources(calibration=a.calibration,carla_host=a.carla_host,carla_port=a.carla_port,dedicated_server=a.dedicated_carla);write(out/'inventory.json',inventory);write(out/'windows-readiness.json',windows_readiness(inventory));gpu=physical=carla=full=None
 try:
  if a.mode=='gpu':
   from bigbench.laptop_gpu import run_gpu_probe
   gpu=run_gpu_probe();write(out/'gpu.json',gpu)
  elif a.mode=='physical':
   from bigbench.offline_camera_validation import validate_dataset
   physical=validate_dataset(a.calibration);write(out/'physical.json',physical)
  elif a.mode=='carla-readiness':carla=carla_readiness(a.carla_host,a.carla_port,a.dedicated_carla);write(out/'carla-readiness.json',carla)
  elif a.mode=='carla-full-s':
   if a.model is None:p.error('--model is required; no automatic model download')
   full=run_carla_cohort(out,a.model,a.carla_host,a.carla_port,a.dedicated_carla);write(out/'carla-full-s-summary.json',full);carla=full;full=None
  elif a.mode=='full-s':
   if a.model is None:p.error('--model is required; no automatic model download')
   full=run_full_cohort(out,a.model,inventory);write(out/'full-s-summary.json',full)
   if (out/'gpu.json').is_file():gpu=json.loads((out/'gpu.json').read_text(encoding='utf-8'))
  write(out/'summary.json',aggregate_laptop(inventory,gpu=gpu,physical=physical,carla=carla,full_s=full));return 0
 except Exception as e:
  write(out/'error.json',dict(status='ERROR',error=type(e).__name__+': '+str(e),all_four_validation_tracks_passed=False,counts=observed_laptop_counts(out),scope='incomplete children remain uncertain; retained lifecycle receipts are authoritative, never assume zero model calls'));return 2
if __name__=='__main__':raise SystemExit(main())
