"""Fresh official MD-V3 candidate cases; strict differences stay failed gates."""
from pathlib import Path
import argparse,hashlib,json,math,os,shutil,subprocess,sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigbench import sdk3_terrain_priority as repair
from scripts import panda_sdk3_runtime as pins,run_sdk3_draw_trace as renderer
from scripts.sdk3_priority_model_trial import CANDIDATE_EVIDENCE,clone,function_sha
from scripts.compare_fresh_native_mdv3 import compare_fresh_trials,ROWS
from scripts.continue_panda_sdk3_models import PROFILE,unpack_prior
ROOT=Path(__file__).resolve().parents[1]
BASE='ae836ad09f410dd38f2503ac250863e889974c27'
REQUEST='docs/requests/sdk3-priority-models-20261117-01.json'
ENTRY='/work/repo/scripts/sdk3_priority_model_native.py'
ORT_VERSION='1.20.1'

def need(value,message):pins.need(value,message)
def read(path):return json.loads(Path(path).read_text())
def sha(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def native_command(*args,**kwargs):
    command=pins.container_command(*args,**kwargs);command[command.index('/work/repo/scripts/panda_sdk3_diagnostic.py')]=ENTRY;return command

def validate_renderer_delta(rows):need(all(row.startswith('A\t') for row in rows),'qualified renderer files must remain unchanged')

def expected_source_context():
    from scripts.native_mdv3_repeat_trial import run_trial,AuditedOfficialOnnx
    from bigbench.native_model_campaign import run_native_episode,NativeWorldCamera
    return dict(original_episode_implementation_sha256=function_sha(run_native_episode),original_trial_implementation_sha256=function_sha(run_trial),policy_step_implementation_sha256=function_sha(AuditedOfficialOnnx.step),camera_capture_implementation_sha256=function_sha(NativeWorldCamera.capture),candidate_wrapper_sha256=pins.digest(ROOT/'scripts/sdk3_priority_model_trial.py'),policy_class_preserved=True,policy_step_implementation_preserved=True,camera_class_preserved=True,camera_capture_implementation_preserved=True)

def validate_off_stats(value):
    need(isinstance(value,dict) and value.get('returned')==0 and value.get('guards_ok') is True and value.get('values')==dict.fromkeys(pins.STATS_FIELDS,0) and all(type(v) is int for v in value['values'].values()),'actual guarded SDK default-OFF stats')

def validate_model_report(r,seed,scene):
    need(r.get('status')=='DIAGNOSTIC_EXECUTED' and r.get('seed')==seed and r.get('scenario')==scene and (seed,scene) in pins.CASES and r.get('requested_steps')==r.get('completed_steps')==12 and r.get('initial_fraction')==.12,'complete registered native12step condition')
    need(r.get('model_sha256')==pins.MODEL_SHA and r.get('selected_sdk_sha256')==pins.SDK_SHA and r.get('sdk_load_order')=='core-first','actual official weights and immutable SDK')
    need(r.get('trial_evidence')==CANDIDATE_EVIDENCE and r.get('renderer_candidate_id')==repair.REPAIR_ID and r.get('renderer_policy_modified') is True and r.get('original_unmodified_pipeline') is False,'separate modified candidate evidence');renderer.validate_candidate_receipt(r.get('renderer_candidate'))
    need(r.get('source_context')==expected_source_context(),'exact original policy/camera/episode/trial and candidate wrapper source')
    for key in ('raw_rgb_observer_used','draw_trace_modules_loaded','ld_preload_present','draw_trace_library_mapped','injected_session','model_scoring_allowed','real_vehicle_testing','camera_image_interpolation_or_replay','gpu_hdr_extraction','cd210_fallback','carrot_tuning_used'):need(r.get(key) is False,'prohibited model intervention: '+key)
    for key in ('extra_gpu_queries','extra_render_tasks','diagnostic_depth_clear_pixels','camera_convergence_attempts','camera_pixel_tolerance'):need(type(r.get(key)) is int and r[key]==0,'zero model intervention counter: '+key)
    need(r.get('pssm_update_preserved') is True and r.get('onnxruntime_version')==ORT_VERSION and r.get('onnxruntime_providers')==['CPUExecutionProvider'] and r.get('real_ort_session') is True,'actual pinned CPU ORT and original PSSM path')
    need(type(r.get('actual_onnx_inferences_completed')) is int and r['actual_onnx_inferences_completed']==12 and r.get('actual_onnx_inference_bounds')==[12,12],'twelve completed real original audit steps');validate_off_stats(r.get('source_stats_after'))
    need(r.get('camera_capture_mode')=='native_MetaDrive_perceive_sequential_per_step' and all(r.get(k) is True for k in ('actual_onnx_image_feed_sha_captured_per_step','native_source_964x604_rgb_sha_captured_per_step','raw_action_and_recurrent_sha_captured_per_step')),'complete original source/warp/feed/action/state evidence')
    need(type(r.get('process_id')) is int and r['process_id']>0 and isinstance(r.get('process_uuid'),str) and len(r['process_uuid'])==32 and all(c in '0123456789abcdef' for c in r['process_uuid']),'owned independent model identity');frames=r.get('frames');need(isinstance(frames,list) and len(frames)==12,'complete model frames');clock=0.
    for step,row in enumerate(frames,1):
        clock+=.05;need(row.get('step')==step and row.get('time_s')==clock and row.get('speed_mps')==8.,'original virtualclock and fixedspeed');need(all(key in row for key in ROWS),'all strict comparator fields')
        need(all(type(row[k]) in (int,float) and math.isfinite(row[k]) for k in ('time_s','world_x_m','world_y_m','heading_rad','speed_mps','desired_curvature_1pm','desired_acceleration_mps2')),'finite original pose/action');need(isinstance(row['raw_model_action'],list) and row['raw_model_action'] and all(type(v) in (int,float) and math.isfinite(v) for v in row['raw_model_action']),'finite raw ONNX output');need(all(sha(row[k]) for k in ROWS if k.endswith('sha256')),'strict native/feed/action/state digest shape')
    return r

def validate_command(command,container,seed,scene):
    cmd=command.get('argv');need(isinstance(cmd,list) and cmd.count(ENTRY)==1 and cmd.count(pins.IMAGE)==1,'versioned actual model command');mounts={}
    for i,value in enumerate(cmd):
        if value=='--mount':
            parts=dict(p.split('=',1) for p in cmd[i+1].split(',') if '=' in p);need(parts.get('dst') not in mounts,'unique actual model mount');mounts[parts.get('dst')]=parts.get('src')
    need(set(mounts)=={'/work/repo',pins.SDK_PATH,'/out','/model.onnx','/model-deps'},'only immutable source/SDK/weights/deps and writable output mounts');owner=command.get('ownership_label');need(isinstance(owner,str) and len(owner)==32 and all(c in '0123456789abcdef' for c in owner) and container.get('ownership_label')==owner,'bound owned model container')
    expected=native_command(container['name'],Path(mounts['/work/repo']),Path(mounts[pins.SDK_PATH]),Path(mounts['/out']),['--model-pair','--seed',str(seed),'--scenario',scene],model=Path(mounts['/model.onnx']),deps=Path(mounts['/model-deps']),owner=owner);need(cmd==expected,'exact isolated model resource/environment/entrypoint command')

def observed_counts(pair):
    pair=Path(pair);ledger=read(pair/'pair-ledger.json') if (pair/'pair-ledger.json').exists() else [];known=upper=low_inferences=high_inferences=attempts=0
    for row in ledger:
        index=row['index'];path=pair/f'run-{index}'/'native-child.json';native=read(path) if path.exists() else row;pid=native.get('pid');certain=type(pid) is int and pid>0;possible=certain or native.get('spawn_attempted') is True or row.get('launcher_spawn_attempted') is True;known+=int(certain);upper+=int(possible);attempts+=int(native.get('spawn_attempted') is True)
        if possible:
            path=pair/f'run-{index}'/'model-trial-lifecycle.json';life=read(path) if path.exists() else {};lo,hi=life.get('inferences_completed_lower_bound'),life.get('inferences_completed_upper_bound');valid=certain and life.get('pid')==pid and type(lo) is int and type(hi) is int and 0<=lo<=hi<=12;low_inferences+=lo if valid else 0;high_inferences+=hi if valid else 12
    return dict(known_model_processes=known,upper_model_processes=upper,spawn_attempts=attempts,inferences_lower_bound=low_inferences,inferences_upper_bound=high_inferences)

def validate_case(folder,seed,scene):
    folder=Path(folder);pair=folder/'pair';execution=read(pair/'execution.json');container=read(pair/'container.json');command=read(pair/'command.json');cid=container.get('id');need(sha(cid) and execution.get('container_id')==cid and container.get('image')==pins.IMAGE and container.get('effective_limits')==PROFILE,'actual immutable isolated model pair');validate_command(command,container,seed,scene)
    need(execution.get('returncode')==0 and execution.get('failure') is None and execution.get('ownership_unresolved') is False and execution.get('owned_container_removed') is True and execution.get('cleanup_failure') is None,'complete owned model container cleanup');state=execution.get('stopped_state',{});need(state.get('Running') is False and state.get('Pid')==0 and state.get('OOMKilled') is False and state.get('ExitCode')==0,'complete non-OOM pair exit');ledger=read(pair/'pair-ledger.json');need(isinstance(ledger,list) and [r.get('index') for r in ledger]==[0,1],'two original fresh launchers')
    reports=[]
    for index in (0,1):
        dest=pair/f'run-{index}';raw=(dest/'run.json').read_bytes();need(raw==(folder/f'run_{index}.json').read_bytes(),'unchanged duplicate raw reports');r=validate_model_report(json.loads(raw),seed,scene);native=read(dest/'native-child.json');owner=read(dest/'report.json');life=read(dest/'model-trial-lifecycle.json');pid=r['process_id'];need(native.get('spawn_attempted') is True and native.get('pid')==owner.get('pid')==life.get('pid')==pid and native.get('returncode')==native.get('server_returncode')==0 and owner.get('child_finalized_before_server_stop') is True and owner.get('server_returncode')==0,'owned native model/display lifetime');need(ledger[index].get('pid')==pid and ledger[index].get('spawn_attempted') is True and ledger[index].get('returncode')==0,'actual ledger/native identity')
        need(owner.get('status')=='OFFICIAL_MODEL_TRIAL_OBSERVED' and owner.get('core_sha256')==pins.CORE_SHA and owner.get('sdk_sha256')==pins.SDK_SHA and owner.get('load_order')=='core-first' and owner.get('factory')=='manual','actual SDK/core bootstrap');before=owner.get('source_stats');need(isinstance(before,list) and len(before)==1,'original model default-OFF before stats');validate_off_stats(before[0]);need(life.get('protocol')=='sdk3-priority-model-lifecycle-v1' and life.get('completed') is True and life.get('status')=='COMPLETED' and life.get('seed')==seed and life.get('scenario')==scene and life.get('nonce')==owner.get('nonce') and isinstance(life.get('nonce'),str) and len(life['nonce'])==32 and life.get('inferences_completed_lower_bound')==life.get('inferences_completed_upper_bound')==12 and life.get('policy_created') is True,'twelve unambiguous completed original inference steps');need(life.get('model_spec_sha256')==pins.digest(ROOT/'model_specs/md-v3.json') and life.get('native_entry_sha256')==pins.digest(ROOT/'scripts/sdk3_priority_model_native.py'),'actual model spec and versioned entry source');validate_off_stats(life.get('source_stats_after'));reports.append(r)
    counts=observed_counts(pair);need(counts==dict(known_model_processes=2,upper_model_processes=2,spawn_attempts=2,inferences_lower_bound=24,inferences_upper_bound=24),'exact two children and24completedinferences');pair_result=read(pair/'pair.json');need(pair_result.get('status')=='PAIR_COMPLETED' and pair_result.get('failure') is None and pair_result.get('counts')==dict(known=2,upper=2,spawn_attempts=2),'pair lifecycle complete');verdict=compare_fresh_trials(*reports);need(read(folder/'strict_native_repeat_verdict.json')==verdict,'unchanged strict comparator regenerated from raw bytes')
    return dict(seed=seed,scenario=scene,container_id=cid,process_uuids=[r['process_uuid'] for r in reports],official_model_processes=2,onnx_inferences=24,model_sha256=pins.MODEL_SHA,repair_id=repair.REPAIR_ID,adapter_sha256=pins.digest(ROOT/'bigbench/sdk3_terrain_priority.py'),verdict=verdict)

def aggregate_cases(rows):
    need(len(rows)==4 and {(r['seed'],r['scenario']) for r in rows}==pins.CASES,'four unique fresh complete conditions');need(len({r['container_id'] for r in rows})==4 and len({v for r in rows for v in r['process_uuids']})==8,'four independent containers/eight model identities');need(all(r['official_model_processes']==2 and r['onnx_inferences']==24 and r['model_sha256']==pins.MODEL_SHA and r['repair_id']==repair.REPAIR_ID and r['adapter_sha256']==pins.digest(ROOT/'bigbench/sdk3_terrain_priority.py') for r in rows),'same candidate/weights and exact8processes96inferences');gate=pins.model_gate([dict(seed=r['seed'],scenario=r['scenario'],**{k:r['verdict'][k] for k in ('status','exact_repeated_execution_gate_passed')}) for r in rows]);return dict(gate,classification='FRESH_MODIFIED_RGB_PRIORITY_OFFICIAL_MDV3_COHORT',official_model_processes=8,onnx_inferences=96,repair_id=repair.REPAIR_ID,historical_original_passed=3,historical_original_total=4,historical_original_matrix_replaced=False,model_scoring_allowed=False,real_vehicle_testing=False)

RENDERER=dict(run_id=44106362913,workflow_id=421335903,attempt=1,source_sha='1d1763f5279581be499450c99857504697e9a695',activation_sha='4bca03fa3c81212fd22aa1878dbb1fd22b595031',artifact_id=14338669738,artifact_size=25032261,artifact_sha256='f9a9ad68b77cad51f80e8dd4da6664f6df13b2b24ff62fe61789fa49a5cecaba')
DEPS={'onnxruntime':'1.20.1','flatbuffers':'24.3.25','coloredlogs':'15.0.1','humanfriendly':'10.0','packaging':'24.2','protobuf':'5.29.5','sympy':'1.13.3','mpmath':'1.3.0'}

def validate_request(request):
    need(request.get('schema')=='sdk3-priority-models-request-v1' and request.get('official_model_processes')==8 and request.get('onnx_inferences')==96 and request.get('cases')==[dict(seed=s,scenario=c) for s,c in sorted(pins.CASES)],'exact fresh8child96inference four-condition scope')
    need(request.get('repair_id')==repair.REPAIR_ID and request.get('adapter_sha256')==pins.digest(ROOT/'bigbench/sdk3_terrain_priority.py') and request.get('model_sha256')==pins.MODEL_SHA and request.get('renderer')==RENDERER,'qualified renderer/model/adapter binding')

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True,timeout=60).strip()

def authenticate_source(bundle):
    request=read(ROOT/REQUEST);validate_request(request);source=request['source_sha'];head=git('rev-parse','HEAD')
    need(os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and os.environ.get('GITHUB_SHA')==head,'fresh activation attempt1');need(git('diff','--name-only',source,head).splitlines()==[REQUEST],'request-only activation');renderer.validate_source_delta(git('diff','--name-status',BASE,source).splitlines());validate_renderer_delta(git('diff','--name-status',RENDERER['source_sha'],source).splitlines())
    for event,key in [('push','push_ci'),('pull_request','pr_ci')]:
        run=pins.api('actions/runs/'+str(request[key]));jobs=pins.api('actions/runs/'+str(request[key])+'/jobs');artifacts=pins.api('actions/runs/'+str(request[key])+'/artifacts');need(run['head_sha']==source and run['event']==event and run['workflow_id']==411705464 and run['run_attempt']==1 and run['conclusion']=='success' and jobs['total_count']==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(j['conclusion']=='success' for j in jobs['jobs']) and artifacts['total_count']==0,'four exact source CI jobs');pins.write(bundle/('source-ci-'+event+'.json'),dict(run=run,jobs=jobs,artifacts=artifacts))
    pins.write(bundle/'request.json',request);return request

def validate_renderer_bundle(folder):
    folder=Path(folder);summary=read(folder/'summary.json');request=read(folder/'request.json');need(summary.get('source_sha')==request.get('source_sha')==RENDERER['source_sha'] and summary.get('status')=='DRAW_OBSERVATION_RECORDED' and summary.get('official_model_processes')==summary.get('onnx_inferences')==0,'qualified renderer-only source outcome');need(request.get('repair_id')==repair.REPAIR_ID and request.get('arms')==['canary','candidate-off','candidate-trace'],'qualified original renderer scope')
    library_sha=pins.digest(folder/'drawtrace.so.data');need(library_sha==read(folder/'build.json')['sha256'],'retained renderer helper bytes, never load on host');results={}
    for mode in ('canary','candidate-off','candidate-trace'):
        dest=folder/mode;command=read(dest/'command.json')['argv'];mounts={}
        for i,v in enumerate(command):
            if v=='--mount':
                item=dict(p.split('=',1) for p in command[i+1].split(',') if '=' in p);need(item['dst'] not in mounts,'unique renderer mounts');mounts[item['dst']]=item['src']
        spec=dict(name=command[command.index('--name')+1],repo=mounts['/work/repo'],sdk=mounts[pins.SDK_PATH],out=mounts['/out'],args=command[command.index(renderer.ENTRY)+3:],reference=mounts['/reference.json'],library=mounts.get('/drawtrace.so'));results[mode]=renderer.validate_receipt(dest,folder/'reference.json',summary['arms'][mode]['nonce'],mode,None if mode=='candidate-off' else library_sha,spec)
    canary=results['canary'];need(canary.get('priority_tie_canary_qualified') is True and canary.get('one_pixel_depth_probe_qualified') is True and canary.get('terrain_row_read_qualified') is True,'all tiny actual GPU gates');off=read(folder/'candidate-off/report.json');on=read(folder/'candidate-trace/report.json');draws,_=renderer.read_trace(folder/'candidate-trace',on['pid']);gate=renderer.candidate_repeat_gate(off,on,draws,results['candidate-off']['target_road_rgb'],results['candidate-trace']['target_road_rgb']);need(gate==read(folder/'candidate-repeat-verdict.json') and gate.get('passed') is True,'independently qualified all14source images/earlyterrain/LESS/no-depth-clear gate');return dict(descriptor=RENDERER,gate=gate,arms=results)

def authenticate_renderer(work,bundle):
    d=RENDERER;run=pins.api('actions/runs/'+str(d['run_id']));need(run['workflow_id']==d['workflow_id'] and run['head_sha']==d['activation_sha'] and run['run_attempt']==d['attempt'] and run['conclusion']=='success','exact qualified renderer workflow origin');pins.write(bundle/'renderer-run.json',run)
    need(git('diff','--name-only',d['source_sha'],d['activation_sha']).splitlines()==[renderer.REQUEST],'renderer request-only activation')
    archive=pins.artifact(work,bundle,d['artifact_id'],d['artifact_size'],d['artifact_sha256'],d['run_id'],d['activation_sha'],'qualified-renderer');folder=work/'qualified-renderer';unpack_prior(archive,folder);result=validate_renderer_bundle(folder);pins.write(bundle/'renderer-independent-validation.json',result);return result

def stage_runtime(work,bundle,summary):
    need(shutil.disk_usage(work).free>=8*1024**3,'8GiB ephemeral staging space')
    iz=pins.artifact(work,bundle,14156262448,1738137175,'47711425a5a48fb2ef0cab140da6e394516f9cbb7f04b294c5f6583d7efbc687',43700449423,'7cf0f0157f8100f0aa0e05b01a815d7395c3383f','image');sz=pins.artifact(work,bundle,14191115165,61661546,'2a44226962b3175081566918dd55eb845ac8ce1c9f9f5a396f469c8f6eca5d26',43786081196,'40dd7187ce8d3c5de510aa8c7a8ac2a6d37b0f38','sdk3')
    image=pins.verify_member(iz,'image.tar',1727678464,'4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698',work/'image.tar');sdk=pins.verify_member(sz,'candidate/libpandagl.so.data',1052968,pins.SDK_SHA,work/'libpandagl.so');subprocess.run(['docker','load','-i',str(image)],check=True,timeout=600);need(json.loads(subprocess.check_output(['docker','image','inspect',pins.IMAGE],text=True))[0]['Id']==pins.IMAGE,'immutable loaded image')
    mem={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines()) if k in ('MemTotal','MemAvailable')};summary['host_memory_before_model']=mem;pins.write(bundle/'summary.json',summary);need(mem['MemAvailable']>=12*1024**3,'12GiB available for10GiB bounded model container')
    from importlib.metadata import distributions
    deps=Path(os.environ['SDK3_MODEL_DEPS']);actual={d.metadata['Name'].lower():d.version for d in distributions(path=[str(deps)])};need(actual==DEPS,'exact ephemeral ORT dependency versions');pins.write(bundle/'model-dependencies.json',actual)
    from bigbench.model_inventory import download_checked
    model=download_checked(path=pins.MODEL_ID,sha256=pins.MODEL_SHA,output_dir=work/'models',max_bytes=900000000);need(model.stat().st_size==768750198,'official weights extent');return sdk,model,deps

def run(seed,scene):
    out=ROOT/'output/stage7-sdk3-priority-models-01'/f'{seed}-{scene}'/'producer';need(not out.exists(),'fresh official case output');work=out/'work';bundle=out/'bundle';work.mkdir(parents=True);bundle.mkdir();summary=dict(status='FAILED',seed=seed,scenario=scene,repair_id=repair.REPAIR_ID,counts=dict(known_model_processes=0,upper_model_processes=0,spawn_attempts=0,inferences_lower_bound=0,inferences_upper_bound=0),model_scoring_allowed=False,real_vehicle_testing=False,historical_original_matrix_replaced=False,stage7_complete=False);pins.write(bundle/'summary.json',summary);pair=bundle/'pair'
    try:
        request=authenticate_source(bundle);summary['source_sha']=request['source_sha'];summary['renderer_validation']=authenticate_renderer(work,bundle);pins.write(bundle/'summary.json',summary);sdk,model,deps=stage_runtime(work,bundle,summary)
        print('FRESH_OFFICIAL_CASE_START',seed,scene,flush=True);execution=clone(pins.run_container,container_command=native_command,ROOT=ROOT)('sdk3-priority-'+os.environ['GITHUB_RUN_ID']+f'-{seed}-{scene}',sdk,pair,['--model-pair','--seed',str(seed),'--scenario',scene],model=model,deps=deps);summary['execution']=execution;summary['counts']=observed_counts(pair);pins.write(bundle/'summary.json',summary)
        need(execution['returncode']==0 and execution['failure'] is None,'actual official pair completed')
        raw=[]
        for index in (0,1):
            data=(pair/f'run-{index}'/'run.json').read_bytes();(bundle/f'run_{index}.json').write_bytes(data);raw.append(json.loads(data))
        pins.write(bundle/'strict_native_repeat_verdict.json',compare_fresh_trials(*raw));row=validate_case(bundle,seed,scene);pins.write(bundle/'case-validation.json',row);summary.update(status='FRESH_OFFICIAL_CANDIDATE_CASE_OBSERVED',case=row,strict_pass=row['verdict']['exact_repeated_execution_gate_passed']);pins.write(bundle/'summary.json',summary);print(json.dumps(summary),flush=True);return summary
    except BaseException as exc:
        summary['failure']=type(exc).__name__+': '+str(exc)
        if pair.exists():summary['counts']=observed_counts(pair)
        pins.write(bundle/'summary.json',summary);raise

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true',required=True);parser.add_argument('--seed',required=True,type=int);parser.add_argument('--scenario',required=True,choices=('s_curve_left_right','s_curve_right_left'));args=parser.parse_args();need((args.seed,args.scenario) in pins.CASES,'registered official cohort case');run(args.seed,args.scenario)
if __name__=='__main__':main()
