"""Authenticate one bounded zero-model capture-progress observation."""
from __future__ import annotations
import argparse,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
from types import FunctionType
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk3_runtime as p,sdk3_pixel_geometry as g,run_sdk3_pixel_geometry as prior
from scripts.sdk3_capture_progress import read_journal
from scripts.continue_panda_sdk3_models import PROFILE,unpack_prior
from scripts.compare_native_mdv3_rgb_pixels import read_verified_pixels
ROOT=Path(__file__).resolve().parents[1];BASE='ee1203b12cf6e185b754ef8095097296650d8270';REQUEST='docs/requests/sdk3-capture-progress-20261116-01.json'
ENTRY='/work/repo/scripts/sdk3_capture_progress_native.py';OLD_ENTRY='/work/repo/scripts/sdk3_pixel_geometry_native.py'


def native_command(*args,**kwargs):
    command=prior.native_command(*args,**kwargs);i=command.index(OLD_ENTRY);command[i]=ENTRY;return command


def validate_proc_snapshot(snapshot,pid):
    names=('stat','status','wchan');allowed={n for name in names for n in (name,name+'_error')}
    p.need(isinstance(snapshot,dict) and set(snapshot)<=allowed,'declared proc snapshot fields')
    for name in names:
        p.need((name in snapshot)!=(name+'_error' in snapshot),'explicit available/unavailable proc field')
    p.need(all(type(value) is str and 0<len(value.encode())<=16384 for value in snapshot.values()),'bounded proc strings')
    p.need('stat' in snapshot,'actual child stat required,not errors-only evidence')
    stat=snapshot['stat'];head,separator,tail=stat.rpartition(')');p.need(bool(separator) and head.startswith(str(pid)+' ('),'proc stat PID bound to child')
    fields=tail.split();p.need(len(fields)>=22 and fields[0] in ('R','S','D','Z','T','t','X','x','K','W','P','I'),'proc stat structure')
    try:values=[int(value) for value in fields[1:]]
    except ValueError as error:raise ValueError('proc stat numeric fields') from error
    p.need(values[10]>=0 and values[11]>=0 and values[20]>=0,'proc CPU/RSS fields')
    if 'status' in snapshot:p.need(re.findall(r'^Pid:\s+(\d+)\s*$',snapshot['status'],re.MULTILINE)==[str(pid)],'proc status PID bound to child')
    return dict(available=[n for n in names if n in snapshot],unavailable=[n for n in names if n+'_error' in snapshot])


def observation_summary(summary,analysis):
    return dict(summary,status=analysis['status'],native_completed=analysis['native_completed'],renderer_diagnostic_passed=analysis['renderer_diagnostic_passed'])


def validate_receipt(folder,reference_path,nonce):
    folder=Path(folder);reference_path=Path(reference_path)
    def read(name):return json.loads((folder/name).read_text())
    r=read('report.json');n=read('native-child.json');e=read('execution.json');c=read('container.json');w=read('watchdog.json');command=read('command.json');reference=json.loads(reference_path.read_text())
    cmd=command.get('argv',[]);p.need(cmd.count(ENTRY)==1 and OLD_ENTRY not in cmd,'actual capture-progress entry');normalized=dict(command,argv=[OLD_ENTRY if value==ENTRY else value for value in cmd]);prior.validate_command(normalized,c,0,nonce)
    cid=c.get('id');p.need(type(cid) is str and len(cid)==64 and all(v in '0123456789abcdef' for v in cid) and e.get('container_id')==cid and c.get('image')==p.IMAGE and c.get('effective_limits')==PROFILE,'actual frozen isolated container')
    p.need(e.get('failure') is None and e.get('owned_container_removed') is True and e.get('ownership_unresolved') is False,'owned capture container removed')
    state=e.get('stopped_state',{});p.need(state.get('Running') is False and state.get('Pid')==0 and state.get('OOMKilled') is False,'stopped non-OOM capture renderer')
    pid=n.get('pid');p.need(n.get('spawn_attempted') is True and type(pid) is int and pid>0 and r.get('pid')==w.get('pid')==pid and n.get('server_returncode')==w.get('server_returncode')==0,'bound child/display identity')
    p.need(r.get('protocol')=='sdk3-capture-progress-v1' and r.get('nonce')==nonce and r.get('repeat')==0 and r.get('seed')==20261110 and r.get('scenario')=='s_curve_left_right' and type(r.get('process_uuid')) is str and len(r['process_uuid'])==32,'fresh scoped capture report')
    p.need(r.get('core_sha256')==p.CORE_SHA and r.get('sdk_sha256')==p.SDK_SHA and r.get('panda_version')=='1.10.13' and r.get('base_camera_sha256')=='23d90c3d12894f855ae64d4607c03f3bf34e31e28dd7f5ce82bd0ddc7b37faf5' and r.get('reference_sha256')==p.digest(reference_path),'actual frozen renderer and reference')
    p.need(all(type(r.get(k)) is int and r[k]==0 for k in ('official_model_processes','onnx_inferences')) and all(r.get(k) is False for k in ('model_weights_used','repair_proven','stage7_complete')),'zero-model observation only')
    p.need(w.get('timeout_seconds')==160 and type(w.get('timed_out')) is bool and type(w.get('elapsed_s')) in (int,float) and 0<=w['elapsed_s']<=180,'fixed watchdog receipt')
    proc_availability=None;timed_out=w['timed_out'];rc=n.get('returncode');p.need(type(rc) is int and rc==w.get('child_returncode'),'known terminal native code')
    if timed_out:
        p.need(rc==-9 and e.get('returncode')==state.get('ExitCode')==1 and w['elapsed_s']>=160,'observed timeout/kill,never native PASS');proc_availability=validate_proc_snapshot(w.get('proc_before_kill'),pid)
    else:p.need(rc==0 and e.get('returncode')==state.get('ExitCode')==0 and r.get('provider_closed') is True and r.get('observers_restored') is True and r.get('ort_module_loaded') is False and r.get('extra_gpu_queries')==r.get('extra_render_tasks')==0,'complete finalized zero-model capture')
    rows=read_journal(folder/'progress.jsonl');p.need(all(row['identity']==dict(pid=pid,nonce=nonce,protocol='sdk3-capture-progress-v1') for row in rows),'all progress rows bound to actual child')
    active=[];returns=[]
    for row in rows:
        if row['event']=='checkpoint':continue
        operation,phase=row['event'].split('.',1)
        if phase=='enter':active.append(dict(operation=operation,step=row['step'],camera=row['camera']))
        else:
            active.pop()
            if operation=='capture' and phase=='return':returns.append(row['step'])
    p.need(returns==list(range(1,len(returns)+1)),'successful capture steps form an exact prefix')
    captures=r.get('captures');p.need(isinstance(captures,list) and len(captures)<=7 and len(captures)<=len(returns)<=len(captures)+1,'durable completed captures,not assumed zero at timeout')
    matches=[];images_verified=0
    for step,record in enumerate(captures,1):
        p.need(record.get('step')==step,'ordered durable capture prefix')
        if step>1:p.need(record.get('pose')==reference['previous_states'][step-2],'same fixed camera entry pose')
        images=record.get('images');p.need(isinstance(images,list) and [i.get('camera') for i in images]==['road','wide'],'original copied Road/Wide pair')
        for image in images:
            camera=image['camera'];p.need(image.get('file')==f'step{step}-{camera}.rgb.zlib' and image.get('shape')==[604,964,3] and image.get('sha256')==record.get(camera+'_sha256'),'capture-bound raw image');read_verified_pixels(folder,image);images_verified+=1
        if step<=6:matches.append(all(record[c+'_sha256']==reference['prefix_sha256'][step-1][c] for c in ('road','wide')))
        else:matches.append(record['road_sha256'] in reference['target_road_sha256'] and record['wide_sha256']==reference['target_wide_sha256'])
    stacks_path=folder/'stacks.log';p.need(stacks_path.stat().st_size<=4*1024**2,'bounded timed Python stacks');stacks=stacks_path.read_text()
    if timed_out:p.need('Timeout (' in stacks and 'File "' in stacks,'pre-timeout stacks retained')
    else:p.need(len(captures)==7 and not active and r.get('status')=='CAPTURE_REPLAY_RECORDED' and r.get('task_frame_count_delta')==14 and r.get('tasks_before')==r.get('tasks_after'),'complete original capture/tick/task protocol')
    prefix=all(matches) if matches else None;equivalent=(prefix if len(captures)==7 or prefix is False else None)
    status='TRACE_RECORDED_NATIVE_TIMEOUT' if timed_out else 'TRACE_RECORDED_NATIVE_COMPLETED' if equivalent is True else 'TRACE_RECORDED_NATIVE_COMPLETED_SOURCE_MISMATCH'
    return dict(status=status,native_completed=not timed_out,renderer_diagnostic_passed=not timed_out and equivalent is True,process_uuid=r['process_uuid'],pid=pid,container_id=cid,native_returncode=rc,known_renderer_processes=1,completed_capture_returns=len(returns),persisted_capture_count=len(captures),verified_source_images=images_verified,completed_prefix_matches_reference=prefix,source_image_equivalence=equivalent,active_boundaries=active,proc_snapshot_availability=proc_availability,last_event=rows[-1],progress_records=len(rows),timed_stack_dumps=stacks.count('Timeout ('),official_model_processes=0,onnx_inferences=0,original_matrix_passed=3,original_matrix_total=4,original_matrix_gate_passed=False,gpu_pixel_owner_proven=False,unique_cause_proven=False,repair_proven=False,stage7_complete=False)


def authenticate_source(bundle):
    request=json.loads((ROOT/REQUEST).read_text());source=request['source_sha'];head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    p.need(os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and head==os.environ.get('GITHUB_SHA'),'fresh request attempt1')
    p.need(request.get('schema')=='sdk3-capture-progress-request-v1' and request.get('renderer_processes')==1 and request.get('official_model_processes')==request.get('onnx_inferences')==0,'one renderer/zero models scope')
    p.need(subprocess.check_output(['git','diff','--name-only',source,head],cwd=ROOT,text=True).splitlines()==[REQUEST],'request-only activation')
    delta=subprocess.check_output(['git','diff','--name-status',BASE,source],cwd=ROOT,text=True).splitlines();p.need(delta and all(x.startswith('A\t') for x in delta),'all old source/verdict bytes preserved')
    for event,key in [('push','push_ci'),('pull_request','pr_ci')]:
        run=p.api('actions/runs/'+str(request[key]));jobs=p.api('actions/runs/'+str(request[key])+'/jobs');artifacts=p.api('actions/runs/'+str(request[key])+'/artifacts')
        p.need(run['head_sha']==source and run['event']==event and run['workflow_id']==411705464 and run['run_attempt']==1 and run['conclusion']=='success' and jobs['total_count']==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(j['conclusion']=='success' for j in jobs['jobs']) and artifacts['total_count']==0,'four exact source CI jobs')
        p.write(bundle/('source-ci-'+event+'.json'),dict(run=run,jobs=jobs,artifacts=artifacts))
    p.write(bundle/'request.json',request);return request


def run():
    out=ROOT/'output/stage7-sdk3-capture-progress-01/producer';p.need(not out.exists(),'fresh output');work=out/'work';bundle=out/'bundle';work.mkdir(parents=True);bundle.mkdir();summary=dict(status='FAILED',known_renderer_processes=0,renderer_spawn_attempts=0,official_model_processes=0,onnx_inferences=0,repair_proven=False,stage7_complete=False);p.write(bundle/'summary.json',summary)
    try:
        request=authenticate_source(bundle);summary['source_sha']=request['source_sha'];p.write(bundle/'summary.json',summary)
        prior_run=p.api('actions/runs/43854755697');p.need(prior_run['workflow_id']==420027188 and prior_run['head_sha']=='bddd41d9f607a6ba20fc65da4291b76837db4b2f' and prior_run['run_attempt']==1 and prior_run['conclusion']=='success','prior RGB origin');p.write(bundle/'prior-run.json',prior_run)
        archive=p.artifact(work,bundle,14220249832,43506956,'6136240ea3894d5c90b16fa9c0e6c10e5829c59d7565daa00556084f1789aba1',43854755697,'bddd41d9f607a6ba20fc65da4291b76837db4b2f','prior-full-rgb');old=work/'prior-full-rgb';unpack_prior(archive,old)
        from scripts.run_sdk3_rgb_forensics import validate_observed_pair
        prior_analysis=validate_observed_pair(old,'full_rgb');p.need(prior_analysis['first_raw_source_diff_step']==7 and prior_analysis['strict_pair_pass'] is False,'preserve prior failure');p.write(bundle/'prior-validation.json',prior_analysis)
        reports=[json.loads((old/'pair'/f'run-{i}'/'run.json').read_text()) for i in (0,1)];reference_path=bundle/'reference.json';p.write(reference_path,g.reference_from_reports(*reports))
        for i,r in enumerate(reports):p.write(bundle/'prior-reference'/f'run-{i}.json',r)
        p.need(shutil.disk_usage(work).free>=8*1024**3,'8GiB staging disk')
        iz=p.artifact(work,bundle,14156262448,1738137175,'47711425a5a48fb2ef0cab140da6e394516f9cbb7f04b294c5f6583d7efbc687',43700449423,'7cf0f0157f8100f0aa0e05b01a815d7395c3383f','image');sz=p.artifact(work,bundle,14191115165,61661546,'2a44226962b3175081566918dd55eb845ac8ce1c9f9f5a396f469c8f6eca5d26',43786081196,'40dd7187ce8d3c5de510aa8c7a8ac2a6d37b0f38','sdk3')
        image=p.verify_member(iz,'image.tar',1727678464,'4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698',work/'image.tar');sdk=p.verify_member(sz,'candidate/libpandagl.so.data',1052968,p.SDK_SHA,work/'libpandagl.so')
        subprocess.run(['docker','load','-i',str(image)],check=True,timeout=600);p.need(json.loads(subprocess.check_output(['docker','image','inspect',p.IMAGE],text=True))[0]['Id']==p.IMAGE,'same immutable image')
        mem={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines()) if k in ('MemTotal','MemAvailable')};summary['host_memory']=mem;p.need(mem['MemAvailable']>=12*1024**3,'12GiB host availability')
        import secrets
        nonce=secrets.token_hex(16);summary['nonce']=nonce;p.write(bundle/'summary.json',summary)
        def command(*a,**kw):return native_command(*a,reference=reference_path,**kw)
        original=p.run_container;function=FunctionType(original.__code__,dict(original.__globals__,container_command=command),original.__name__,original.__defaults__,original.__closure__);function.__kwdefaults__=dict(original.__kwdefaults__ or {})
        summary['execution']=function('sdk3-progress-'+os.environ['GITHUB_RUN_ID'],sdk,bundle/'renderer',['--repeat','0','--nonce',nonce])
        path=bundle/'renderer/native-child.json'
        if path.exists():n=json.loads(path.read_text());summary.update(known_renderer_processes=int(type(n.get('pid')) is int and n['pid']>0),renderer_spawn_attempts=int(n.get('spawn_attempted') is True))
        p.write(bundle/'summary.json',summary);analysis=validate_receipt(bundle/'renderer',reference_path,nonce);p.write(bundle/'analysis.json',analysis);summary=observation_summary(summary,analysis);p.write(bundle/'summary.json',summary);print(json.dumps(summary));return summary
    except BaseException as error:summary['failure']=type(error).__name__+': '+str(error);p.write(bundle/'summary.json',summary);raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true',required=True);parser.parse_args();run()
if __name__=='__main__':main()
