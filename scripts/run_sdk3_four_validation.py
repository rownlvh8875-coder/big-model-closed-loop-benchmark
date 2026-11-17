"""Authenticated native full-S/virtual-optics cohort; external tracks stay explicit."""
from pathlib import Path
from dataclasses import asdict
import argparse,hashlib,json,math,os,shutil,subprocess,sys,zlib
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk3_runtime as p,sdk3_four_validation_runtime as runtime,sdk3_four_validation_trial as trial
from scripts.continue_panda_sdk3_models import PROFILE,unpack_prior
from scripts.run_sdk3_priority_models import validate_off_stats,DEPS
from scripts.run_sdk3_draw_trace import validate_candidate_receipt
from bigbench.full_s_validation import validate_route,route_state,compare_full_s
from bigbench.full_s_receipts import RecordedLane,recorded_route,validate_trajectory
from bigbench.kinematics import AgentState,ModelAction,step_ideal
from bigbench.model_world_frame import basis_receipt
ROOT=Path(__file__).resolve().parents[1];BASE='8380e8a0c0583fa0e47af6b8bbb4b6446060e420';REQUEST='docs/requests/sdk3-four-validation-20261118-02.json'


def read(path):return json.loads(Path(path).read_text())
def need(v,message):p.need(v,message)
def digest64(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def validate_delta(rows):need(rows and all(r.startswith('A\t') or r=='M\ttests/test_engine_clock_native.py' for r in rows),'all previous producer/evidence files remain unchanged')
def finite(v):return type(v) in (int,float) and math.isfinite(v)
def close(a,b):return finite(a) and finite(b) and abs(a-b)<=1e-8

def software_driver(d):need(isinstance(d,dict) and isinstance(d.get('renderer'),str) and 'llvmpipe' in d['renderer'].lower() and isinstance(d.get('vendor'),str) and d['vendor'] and isinstance(d.get('version'),str) and d['version'],'registered measured llvmpipe software context')

def same_driver(actual,qualified):
 software_driver(actual);software_driver(qualified);need(all(actual.get(k)==qualified.get(k) for k in ('renderer','vendor','version')),'actual model driver must match qualified probe context')


def rgb(folder,name,expected):
 path=Path(folder)/name;need(path.is_file() and not path.is_symlink() and path.stat().st_size<=expected*2,'bounded retained RGB file');compressed=path.read_bytes();decoder=zlib.decompressobj()
 try:data=decoder.decompress(compressed,expected+1)
 except zlib.error as exc:raise ValueError('invalid compressed original RGB') from exc
 need(len(data)==expected and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,'exact complete original RGB extent');return data

def validate_virtual_probe(folder,seed,scene):
 import numpy as np,cv2
 from bigbench.optical_calibration import PinholeIntrinsics,PinholeRectifier
 folder=Path(folder);r=read(folder/'probe.json');need(r.get('protocol')=='sdk3-four-native-probe-v1' and (r.get('seed'),r.get('scenario'))==(seed,scene) and (seed,scene) in p.CASES,'registered zero-model probe');need(r.get('libraries')==dict(numpy=np.__version__,opencv=cv2.__version__),'matching actual numpy/OpenCV warp environment');software_driver(r.get('driver'));validate_candidate_receipt(r.get('renderer_candidate'));need(r.get('source_context')==trial.source_context() and r.get('provider_closed') is True and r.get('ort_module_loaded') is False and r.get('capture_calls')==2 and r.get('official_model_processes')==r.get('onnx_inferences')==r.get('extra_render_tasks')==0,'original complete zero-model context')
 need(all(r.get(k) is False for k in ('physical_optics_validated','hardware_gpu_validated','carla_validated')),'virtual optical data cannot certify external tracks');lanes=recorded_route(r['geometry']);caps=r.get('captures');need(isinstance(caps,list) and len(caps)==2,'two actual poses');rectifier=PinholeRectifier();hashes=[]
 for index,cap in enumerate(caps):
  need(cap.get('index')==index and finite(cap.get('capture_wall_s')) and cap['capture_wall_s']>=0 and [x.get('camera') for x in cap.get('images',[])]==['road','wide'],'complete original camera pair');pose=cap['pose'];s=lanes[0].length*.12+2*index;xy=lanes[0].position(s,0.);need(close(pose['x'],xy[0]) and close(pose['y'],xy[1]) and close(pose['heading'],lanes[0].heading_theta_at(s)) and pose['t']==0. and pose['speed']==8.,'actual declared shifted pose')
  arrays={};intrinsics={}
  for image in cap['images']:
   role=image['camera'];need(image.get('source_file')==f'pose-{index}-{role}-source.rgb.zlib' and image.get('canvas_file')==f'pose-{index}-{role}-canvas.rgb.zlib' and image.get('source_shape')==[604,964,3],'exact original RGB members');data=rgb(folder,image['source_file'],604*964*3);need(hashlib.sha256(data).hexdigest()==image.get('source_sha256'),'retained original source digest');arrays[role]=np.frombuffer(data,dtype=np.uint8).reshape(604,964,3);intrinsics[role]=PinholeIntrinsics(**image['measured_intrinsics'])
  rebuilt,audits=rectifier.rectify_pair(arrays['road'],arrays['wide'],road_intrinsics=intrinsics['road'],wide_intrinsics=intrinsics['wide']);pair_hashes={}
  for image in cap['images']:
   role=image['camera'];data=rgb(folder,image['canvas_file'],512*256*3);need(data==getattr(rebuilt,role).rgb and hashlib.sha256(data).hexdigest()==image.get('canvas_sha256') and image.get('source_coverage')==audits[role].fraction_valid_source_pixels and image.get('warp_matrix')==[list(v) for v in audits[role].warp_dst_to_src],'unchanged CPU warp/coverage and original canvas binding');pair_hashes[role]=(image['source_sha256'],image['canvas_sha256'])
  hashes.append(pair_hashes)
 need(all(hashes[0][role][i]!=hashes[1][role][i] for role in ('road','wide') for i in (0,1)),'both source/canvas positive pose controls');minimum=math.ceil((sum(l.length for l in lanes)-lanes[0].length*.12)/.4);rate=trial.rate_admission(minimum,caps[1]['capture_wall_s']);need(r.get('minimum_steps')==minimum and r.get('rate')==rate,'independent rate/route budget');return dict(seed=seed,scenario=scene,virtual_pinhole_passed=True,physical_optics_passed=False,hardware_gpu_passed=False,carla_passed=False,rate=rate,driver=r['driver'])

def validate_full_report(r,seed,scene):
 need(r.get('protocol')=='full-s-closed-loop-v1' and (r.get('seed'),r.get('scenario'))==(seed,scene) and (seed,scene) in p.CASES and r.get('max_steps')==600 and r.get('initial_fraction')==.12,'registered full-S case');need(r.get('model_sha256')==p.MODEL_SHA and r.get('selected_sdk_sha256')==p.SDK_SHA and r.get('source_context')==trial.source_context(),'immutable model/SDK/source');validate_candidate_receipt(r.get('renderer_candidate'));software_driver(r.get('driver'));need(r.get('trial_evidence')=='CORRECTED_WORLD_FRAME_RGB_PRIORITY_FULL_S' and r.get('action_basis')==basis_receipt(),'explicit original model-to-world frame boundary')
 for key in ('model_test_double','injected_session','raw_rgb_observer_used','ld_preload_present','draw_trace_modules_loaded','ground_truth_control_used','model_scoring_allowed','real_vehicle_testing'):need(r.get(key) is False,'no counterfeit/intervention: '+key)
 need(r.get('onnxruntime_version')=='1.20.1' and r.get('onnxruntime_providers')==['CPUExecutionProvider'] and r.get('real_ort_session') is True and r.get('original_camera_class_preserved') is True and r.get('original_policy_class_preserved') is True and r.get('provider_closed') is True and r.get('pixel_tolerance')==r.get('extra_render_tasks')==0,'original real ORT/camera path');validate_off_stats(r.get('source_stats_after'));return validate_trajectory(r,seed,scene)

def aggregate_cases(rows):
 need(len(rows)==4 and {(r['seed'],r['scenario']) for r in rows}==p.CASES,'all four fresh conditions');need(len({r['container_id'] for r in rows})==4 and len({u for r in rows for u in r['process_uuids']})==8,'four containers/eight fresh model identities');return dict(full_s_passed_cases=sum(r['verdict']['passed'] for r in rows),strict_repeat_passed_cases=sum(r['verdict']['strict_repeat_passed'] for r in rows),total=4,official_model_processes=8,inference_bounds=[sum(r['inference_bounds'][i] for r in rows) for i in (0,1)],all_four_validation_tracks_passed=False,physical_optics='BLOCKED_MISSING_MEASURED_DATA',hardware_gpu='BLOCKED_NO_CLOUD_DEVICE',carla='BLOCKED_NO_SERVER',stage7_complete=False)

def validate_request(r):
 need(r.get('schema')=='sdk3-four-validation-request-v2' and r.get('cases')==[dict(seed=s,scenario=c) for s,c in sorted(p.CASES)] and r.get('max_model_processes')==8 and r.get('max_inferences')==4800 and r.get('max_steps')==600 and r.get('child_timeout_seconds')==9000 and r.get('driver')=='llvmpipe' and r.get('lp_num_threads')==2 and r.get('model_sha256')==p.MODEL_SHA and r.get('base_sha')==BASE,'exact registered new four-validation scope')

def authenticate_source(bundle):
 request=read(ROOT/REQUEST);validate_request(request);source=request['source_sha'];git=lambda *args:subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip();head=git('rev-parse','HEAD');need(os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and os.environ.get('GITHUB_SHA')==head,'fresh request attempt1');need(git('diff','--name-only',source,head).splitlines()==[REQUEST],'request-only activation');validate_delta(git('diff','--name-status',BASE,source).splitlines())
 for event,key in [('push','push_ci'),('pull_request','pr_ci')]:
  run=p.api('actions/runs/'+str(request[key]));jobs=p.api('actions/runs/'+str(request[key])+'/jobs');artifacts=p.api('actions/runs/'+str(request[key])+'/artifacts');need(run['head_sha']==source and run['event']==event and run['workflow_id']==411705464 and run['run_attempt']==1 and run['conclusion']=='success' and jobs['total_count']==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(j['conclusion']=='success' for j in jobs['jobs']) and artifacts['total_count']==0,'four exact canonical source CI jobs');p.write(bundle/('source-ci-'+event+'.json'),dict(run=run,jobs=jobs,artifacts=artifacts))
 p.write(bundle/'request.json',request);return request

def stage_runtime(work,bundle):
 need(shutil.disk_usage(work).free>=8*1024**3,'8GiB ephemeral staging disk');iz=p.artifact(work,bundle,14156262448,1738137175,'47711425a5a48fb2ef0cab140da6e394516f9cbb7f04b294c5f6583d7efbc687',43700449423,'7cf0f0157f8100f0aa0e05b01a815d7395c3383f','image');sz=p.artifact(work,bundle,14191115165,61661546,'2a44226962b3175081566918dd55eb845ac8ce1c9f9f5a396f469c8f6eca5d26',43786081196,'40dd7187ce8d3c5de510aa8c7a8ac2a6d37b0f38','sdk3');image=p.verify_member(iz,'image.tar',1727678464,'4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698',work/'image.tar');sdk=p.verify_member(sz,'candidate/libpandagl.so.data',1052968,p.SDK_SHA,work/'libpandagl.so');subprocess.run(['docker','load','-i',str(image)],check=True,timeout=600);need(json.loads(subprocess.check_output(['docker','image','inspect',p.IMAGE],text=True))[0]['Id']==p.IMAGE,'same loaded immutable image');mem={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines()) if k in ('MemTotal','MemAvailable')};p.write(bundle/'host-memory.json',mem);need(mem['MemAvailable']>=12*1024**3,'12GiB host availability required');return sdk

def observed_counts(pair):
 pair=Path(pair);known=upper=low=high=attempts=0
 for i in (0,1):
  dest=pair/f'run-{i}'
  if not dest.exists():continue
  try:native=read(dest/'native-child.json')
  except (OSError,ValueError):native={}
  pid=native.get('pid');certain=type(pid) is int and pid>0;possible=certain or native.get('spawn_attempted') is True or dest.exists();known+=int(certain);upper+=int(possible);attempts+=int(native.get('spawn_attempted') is True)
  if possible:
   try:life=read(dest/'model-lifecycle.json')
   except (OSError,ValueError):life={}
   bounds=life.get('inference_bounds');valid=certain and life.get('pid')==pid and isinstance(bounds,list) and len(bounds)==2 and all(type(v) is int for v in bounds) and 0<=bounds[0]<=bounds[1]<=600;low+=bounds[0] if valid else 0;high+=bounds[1] if valid else 600
 return dict(known_processes=known,upper_processes=upper,spawn_attempts=attempts,inference_bounds=[low,high])

def validate_container(folder,seed,scene,*,model):
 folder=Path(folder);c=read(folder/'container.json');e=read(folder/'execution.json');command=read(folder/'command.json');need(digest64(c.get('id')) and c.get('id')==e.get('container_id') and c.get('image')==p.IMAGE and c.get('effective_limits')==PROFILE,'actual immutable owned resource profile');need(e.get('returncode')==0 and e.get('failure') is None and e.get('owned_container_removed') is True and e.get('ownership_unresolved') is False and e.get('cleanup_failure') is None,'complete owned cleanup');state=e.get('stopped_state') or {};need(state.get('Running') is False and state.get('Pid')==0 and state.get('OOMKilled') is False and state.get('ExitCode')==0,'complete stopped non-OOM scope');cmd=command.get('argv');need(isinstance(cmd,list) and cmd.count(runtime.ENTRY)==1,'versioned native entry');mounts={}
 for index,value in enumerate(cmd):
  if value=='--mount':
   parts=dict(x.split('=',1) for x in cmd[index+1].split(',') if '=' in x);need(parts.get('dst') not in mounts,'unique immutable mount');mounts[parts['dst']]=parts['src']
 need(set(mounts)=={'/work/repo',p.SDK_PATH,'/out'}|({'/model.onnx','/model-deps'} if model else set()),'exact scoped mounts');owner=command.get('ownership_label');need(isinstance(owner,str) and len(owner)==32 and all(x in '0123456789abcdef' for x in owner) and owner==c.get('ownership_label'),'exact ownership label');args=['--model-pair' if model else '--probe','--seed',str(seed),'--scenario',scene];expected=runtime.native_command(c['name'],Path(mounts['/work/repo']),Path(mounts[p.SDK_PATH]),Path(mounts['/out']),args,model=Path(mounts['/model.onnx']) if model else None,deps=Path(mounts['/model-deps']) if model else None,owner=owner);need(cmd==expected,'exact isolated driver/resource/native command');return c

def validate_child(folder,seed,scene,*,model):
 folder=Path(folder);native=read(folder/'native-child.json');owner=read(folder/'report.json');pid=native.get('pid');need(type(pid) is int and pid>0 and native.get('spawn_attempted') is True and owner.get('pid')==pid and native.get('returncode')==native.get('server_returncode')==owner.get('server_returncode')==0 and owner.get('child_finalized_before_server_stop') is True,'owned native/display lifetime');need(owner.get('status')=='FOUR_VALIDATION_NATIVE_RECORDED' and owner.get('model_trial') is model and owner.get('sdk_sha256')==p.SDK_SHA and owner.get('core_sha256')==p.CORE_SHA and owner.get('panda_version')=='1.10.13' and owner.get('load_order')=='core-first' and (owner.get('seed'),owner.get('scenario'))==(seed,scene),'actual immutable bootstrap/case');need(isinstance(owner.get('nonce'),str) and len(owner['nonce'])==32 and owner['nonce']!='0'*32 and all(x in '0123456789abcdef' for x in owner['nonce']),'fresh owned native nonce');validate_off_stats(owner.get('source_stats_before'));validate_off_stats(owner.get('source_stats_after'));return native,owner

def validate_full_case(folder,seed,scene):
 folder=Path(folder);pair=folder/'pair';container=validate_container(pair,seed,scene,model=True);ledger=read(pair/'pair-ledger.json');need([r.get('index') for r in ledger]==[0,1] and len(ledger)==2,'two fresh owned launchers');reports=[]
 for index in (0,1):
  dest=pair/f'run-{index}';native,owner=validate_child(dest,seed,scene,model=True);data=(dest/'run.json').read_bytes();need(data==(folder/f'run_{index}.json').read_bytes(),'unchanged raw report duplicate');r=json.loads(data);validate_full_report(r,seed,scene);qualified=read(folder/'independent-probe-validation.json');matched=[q for q in qualified if (q.get('seed'),q.get('scenario'))==(seed,scene)];need(len(matched)==1,'exact admitted condition');same_driver(r['driver'],matched[0]['driver']);life=read(dest/'model-lifecycle.json');need(r.get('process_id')==native['pid']==life.get('pid')==ledger[index].get('pid') and ledger[index].get('spawn_attempted') is True and ledger[index].get('returncode')==0,'actual model/ledger/lifecycle PID');need(life.get('nonce')==owner.get('nonce') and life.get('policy_created') is True and life.get('provider_closed') is True and life.get('inference_bounds')==r['actual_inference_bounds'],'owned real model lifecycle/bounds');validate_off_stats(life.get('source_stats_after'));reports.append(r)
 counts=observed_counts(pair);need(counts['known_processes']==counts['upper_processes']==counts['spawn_attempts']==2,'two independent actual model children');result=read(pair/'pair.json');need(result.get('status')=='PAIR_RECORDED' and result.get('failure') is None and result.get('counts')==dict(known=2,upper=2,spawn_attempts=2),'complete pair lifecycle');verdict=compare_full_s(*reports);need(read(folder/'strict-full-s-verdict.json')==verdict,'unchanged strict full-S verdict regenerated from raw');return dict(seed=seed,scenario=scene,container_id=container['id'],process_uuids=[r['process_uuid'] for r in reports],inference_bounds=counts['inference_bounds'],verdict=verdict,outcomes=[r['outcome'] for r in reports])

def receive_probe(work,bundle):
 aid=int(os.environ['FOUR_PROBE_ARTIFACT_ID']);sha=os.environ['FOUR_PROBE_ARTIFACT_SHA'];need(digest64(sha),'published gate artifact digest');meta=p.api('actions/artifacts/'+str(aid));need(meta.get('name')=='sdk3-four-validation-probe-20261118-02','exact unique probe role');archive=p.artifact(work,bundle,aid,meta['size_in_bytes'],sha,int(os.environ['GITHUB_RUN_ID']),os.environ['GITHUB_SHA'],'qualified-probe');folder=work/'qualified-probe';unpack_prior(archive,folder);rows=[]
 for seed,scene in sorted(p.CASES):
  dest=folder/f'{seed}-{scene}';validate_container(dest,seed,scene,model=False);validate_child(dest,seed,scene,model=False);rows.append(validate_virtual_probe(dest,seed,scene))
 need(all(row['rate']['admitted'] for row in rows) and len({json.dumps(row['driver'],sort_keys=True) for row in rows})==1,'all four native optical/rate conditions qualify same context');p.write(bundle/'independent-probe-validation.json',rows);return rows

def run(phase,seed=None,scene=None):
 need(phase in ('probe','full-s') and (phase=='probe' or (seed,scene) in p.CASES),'registered phase/case before output');out=ROOT/'output/stage7-four-validation-02'/('probe' if phase=='probe' else f'{seed}-{scene}')/'producer';need(not out.exists(),'fresh phase output');work=out/'work';bundle=out/'bundle';work.mkdir(parents=True);bundle.mkdir();summary=dict(status='FAILED',phase=phase,official_model_processes=0,inference_bounds=[0,0],physical_optics_passed=False,hardware_gpu_passed=False,carla_passed=False,stage7_complete=False);p.write(bundle/'summary.json',summary)
 try:
  request=authenticate_source(bundle);summary['source_sha']=request['source_sha']
  if phase=='full-s':summary['probe_validation']=receive_probe(work,bundle)
  sdk=stage_runtime(work,bundle)
  if phase=='probe':
   rows=[]
   for seed,scene in sorted(p.CASES):
    dest=bundle/f'{seed}-{scene}';runtime.run_container(f'four-probe-{os.environ["GITHUB_RUN_ID"]}-{seed}-{scene}',sdk,dest,['--probe','--seed',str(seed),'--scenario',scene]);validate_container(dest,seed,scene,model=False);validate_child(dest,seed,scene,model=False);rows.append(validate_virtual_probe(dest,seed,scene));summary['cases']=rows;p.write(bundle/'summary.json',summary)
   admitted=all(row['rate']['admitted'] for row in rows) and len({json.dumps(row['driver'],sort_keys=True) for row in rows})==1;summary.update(status='NATIVE_VIRTUAL_PROBE_RECORDED',model_admitted=admitted)
   if os.environ.get('GITHUB_OUTPUT'):
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as f:f.write('admitted='+str(admitted).lower()+'\n')
  else:
   from importlib.metadata import distributions
   deps=Path(os.environ['SDK3_MODEL_DEPS']);actual={d.metadata['Name'].lower():d.version for d in distributions(path=[str(deps)])};need(actual==DEPS,'exact ORT dependency mount');p.write(bundle/'model-dependencies.json',actual)
   from bigbench.model_inventory import download_checked
   model=download_checked(path=p.MODEL_ID,sha256=p.MODEL_SHA,output_dir=work/'models',max_bytes=900000000);need(model.stat().st_size==768750198,'official model extent');pair=bundle/'pair';execution=runtime.run_container(f'four-full-{os.environ["GITHUB_RUN_ID"]}-{seed}-{scene}',sdk,pair,['--model-pair','--seed',str(seed),'--scenario',scene],model=model,deps=deps);counts=observed_counts(pair);summary.update(official_model_processes=counts['known_processes'],inference_bounds=counts['inference_bounds'],execution=execution);p.write(bundle/'summary.json',summary);need(execution.get('returncode')==0 and execution.get('failure') is None,'complete actual full-S pair')
   reports=[]
   for index in (0,1):
    data=(pair/f'run-{index}'/'run.json').read_bytes();(bundle/f'run_{index}.json').write_bytes(data);reports.append(json.loads(data))
   p.write(bundle/'strict-full-s-verdict.json',compare_full_s(*reports));row=validate_full_case(bundle,seed,scene);p.write(bundle/'case-validation.json',row);summary.update(status='FULL_S_CASE_RECORDED',case=row)
  p.write(bundle/'summary.json',summary);print(json.dumps(summary),flush=True);return summary
 except BaseException as exc:
  summary['failure']=type(exc).__name__+': '+str(exc)
  if (bundle/'pair').exists():counts=observed_counts(bundle/'pair');summary.update(official_model_processes=counts['known_processes'],inference_bounds=counts['inference_bounds'])
  p.write(bundle/'summary.json',summary);raise

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true',required=True);parser.add_argument('--phase',choices=('probe','full-s'),required=True);parser.add_argument('--seed',type=int);parser.add_argument('--scenario',choices=('s_curve_left_right','s_curve_right_left'));a=parser.parse_args();run(a.phase,a.seed,a.scenario)
if __name__=='__main__':main()
