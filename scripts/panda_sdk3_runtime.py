"""Fresh SDK3 runtime cohort; historical requests and verdicts stay immutable."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import resource
import stat
import subprocess
import sys
import time
import tarfile
from zipfile import ZipFile

REPO='rownlvh8875-coder/big-model-closed-loop-benchmark'
ROOT=Path(__file__).resolve().parents[1]
SITE='/opt/venv/lib/python3.11/site-packages'
SDK_PATH=SITE+'/panda3d/libpandagl.so'
SDK_SHA='27cd80fb1c06feaa7da8b5658cce918d1e3ab71c304a0c0ce42e30688ac008f3'
CORE_SHA='8b0372f1df91a930f18b2551f7fde5d5687e21bc79dee9ecd0dd2018cba72490'
IMAGE='sha256:b9d673de93f1857e4dfa5ed6a48330d568ef96fce7f3cc975f0c688877e6e26e'
MODEL_SHA='35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199'
MODEL_ID='1365126a-e71e-4778-be00-8ab92dc82c09/12864/big_driving_supercombo.onnx'
REQUEST='docs/requests/panda-sdk3-runtime-20261116-03.json'
REFERENCE_SHA='f38e0734a5344eda9a11e3024695febf2cea0177aa80985b67ceef5837a088d7'
STATS_FIELDS=('configured','closed','error','forwarded','resolutions','paths','events')
CASES={(s,c) for s in (20261109,20261110) for c in ('s_curve_left_right','s_curve_right_left')}


def need(value,message):
    if not value:raise ValueError(message)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp');tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');tmp.replace(path)


def challenge(nonce,index):
    need(type(nonce) is str and len(nonce)==32 and all(c in '0123456789abcdef' for c in nonce),'nonce')
    need(type(index) is int and index in (0,1),'two frame indices')
    return list(hashlib.sha256(bytes.fromhex(nonce)+bytes([index])).digest()[:3])


def expected_stages(order,factory='manual'):
    need(order in ('core-first','sdk-first') and factory in ('manual','showbase'),'load order/factory')
    core=['CORE_BEFORE','CORE_AFTER'];sdk=['PRELOAD_BEFORE','PRELOAD_AFTER','SDK_BEFORE','SDK_AFTER']
    setup=['SHOWBASE_BEFORE','SHOWBASE_AFTER'] if factory=='showbase' else ['ENGINE_BEFORE','ENGINE_AFTER','PIPE_BEFORE','PIPE_AFTER','OUTPUT_BEFORE','OUTPUT_AFTER']
    return ['BOOT']+(core+sdk if order=='core-first' else sdk+core)+['SERVER_BEFORE','SERVER_AFTER','PRC_BEFORE','PRC_AFTER']+setup+[
        'DRIVER_AFTER','FRAME_0_BEFORE','FRAME_0_AFTER','FRAME_1_BEFORE','FRAME_1_AFTER','CLEANUP_BEFORE','CLEANUP_AFTER']


def validate_common_probe(events,report,returncode,nonce,order,factory):
    need(returncode==0,'complete child exit')
    need(report.get('nonce')==nonce and report.get('load_order')==order and report.get('factory','manual')==factory,'probe identity/order/factory')
    need([e.get('stage') for e in events]==expected_stages(order,factory),'complete ordered checkpoints')
    need(type(report.get('pid')) is int and report['pid']>0 and all(e.get('nonce')==nonce and e.get('pid')==report['pid'] for e in events),'owned checkpoint identity')
    times=[e['monotonic'] for e in events];need(all(type(t) in (int,float) for t in times) and all(a<b for a,b in zip(times,times[1:])),'ordered checkpoint times')
    need(report.get('core_sha256')==CORE_SHA and report.get('panda_version')=='1.10.13','pinned actual core')
    need(report['driver']['renderer'].strip().lower()=='softpipe' and all(type(v) is str and 0<len(v)<=512 for v in report['driver'].values()),'actual softpipe driver')
    objects=report['objects'];need(set(objects)=={'pipe','output','gsg','texture','camera'} and all(type(v) is int and v>0 for v in objects.values()) and len(set(objects.values()))==5,'distinct Panda objects')
    need(len(report['frames'])==2,'two frames')
    for i,row in enumerate(report['frames']):
        raw=bytes.fromhex(row['raw_hex']);need(row['index']==i and row['nbytes']==len(raw)==192 and raw==bytes(challenge(nonce,i))*64 and row['sha256']==hashlib.sha256(raw).hexdigest(),'exact fresh challenged RGB bytes')
    need(report['frames'][0]['sha256']!=report['frames'][1]['sha256'],'distinct challenges')
    need(report['cleanup']==dict(windows_after=0,texture_ram_after=False,render_calls=4,ram_reads=2,cpp_deallocation_verified=False),'owned cleanup')


def validate_probe(events,report,returncode,nonce,order,*,factory='manual'):
    need(report.get('status')=='SDK3_GLX_FRAMES_OBSERVED' and report.get('sdk_sha256')==SDK_SHA,'pinned SDK3 outcome')
    validate_common_probe(events,report,returncode,nonce,order,factory)
    need(len(report['source_stats'])==2,'complete observer interval')
    for s in report['source_stats']:
        need(s['returned']==0 and s['guards_ok'] is True and set(s['values'])==set(STATS_FIELDS) and all(type(v) is int and v==0 for v in s['values'].values()),'default-off observer')
    return dict(selected_runtime_compatible=True,verified_frames=2,full_object_abi_qualified=False,stage7_complete=False)


def validate_reference_probe(events,report,returncode,nonce,order,*,factory='manual'):
    need(report.get('status')=='PANDA_REFERENCE_GLX_FRAMES_OBSERVED' and report.get('sdk_sha256')==REFERENCE_SHA and report.get('source_stats')==[] and report.get('observer_instrumented') is False,'publisher wheel control only')
    validate_common_probe(events,report,returncode,nonce,order,factory)
    return dict(reference_frames_verified=True,selected_runtime_compatible=False,verified_frames=2,stage7_complete=False)


def extract_reference(image,out,*,expected_size=913073,expected_sha=REFERENCE_SHA):
    out=Path(out);need(not out.exists(),'fresh reference output')
    with tarfile.open(image,'r:*') as archive:
        manifest=json.load(archive.extractfile('manifest.json'));need(len(manifest)==1,'one image manifest')
        for name in manifest[0]['Layers']:
            with tarfile.open(fileobj=archive.extractfile(name),mode='r|*') as layer:
                for member in layer:
                    if member.name.lstrip('./')==SDK_PATH.lstrip('/') and member.isreg() and member.size==expected_size:
                        raw=layer.extractfile(member).read(expected_size+1)
                        if len(raw)==expected_size and hashlib.sha256(raw).hexdigest()==expected_sha:
                            with out.open('xb') as target:target.write(raw)
                            out.chmod(0o644);return out
    raise ValueError('pinned publisher reference absent from original image layers')


def verify_member(zip_path,member,size,sha,out):
    out=Path(out);need(not out.exists(),'fresh extracted output')
    with ZipFile(zip_path) as z:
        names=set()
        for info in z.infolist():
            path=PurePosixPath(info.filename);mode=info.external_attr>>16
            need(info.filename not in names and not path.is_absolute() and '..' not in path.parts and '\\' not in info.filename and not stat.S_ISLNK(mode),'unsafe/duplicate ZIP member')
            names.add(info.filename)
        info=z.getinfo(member);need(info.file_size==size,'member size')
        h=hashlib.sha256();tmp=out.with_name(out.name+'.partial')
        try:
            with z.open(info) as src,tmp.open('xb') as dst:
                for b in iter(lambda:src.read(1024**2),b''):h.update(b);dst.write(b)
            need(tmp.stat().st_size==size and h.hexdigest()==sha,'member digest');tmp.chmod(0o644);tmp.replace(out)
        finally:
            if tmp.exists():tmp.unlink()
    return out


def model_gate(verdicts):
    keys=[(v['seed'],v['scenario']) for v in verdicts]
    need(len(keys)==4 and len(set(keys))==4 and set(keys)==CASES,'four unique complete conditions')
    for v in verdicts:
        need(type(v['exact_repeated_execution_gate_passed']) is bool and v['status']==('STRICT_NATIVE_ONNX_REPEAT_MATCH' if v['exact_repeated_execution_gate_passed'] else 'STRICT_NATIVE_ONNX_REPEAT_MISMATCH'),'coherent strict verdict')
    passed=sum(v['exact_repeated_execution_gate_passed'] for v in verdicts)
    return dict(strict_pass=passed==4,passed=passed,total=4,expansion_admitted=passed==4,stage7_complete=False)


def observed_model_processes(ledger):
    known=sum(type(row.get('pid')) is int and row['pid']>0 for row in ledger)
    attempted=sum(row.get('spawn_attempted') is True for row in ledger)
    unknown=sum(row.get('spawn_attempted') is True and row.get('pid') is None for row in ledger)
    return dict(known=known,upper=known+unknown,spawn_attempts=attempted)


def log_limits():
    resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024**2,16*1024**2))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))


def container_command(name,repo,sdk,out,args,*,model=None,deps=None,owner=None):
    cmd=['docker','create','--name',name,'--read-only','--network','none','--user','65534:65534',
         '--cap-drop','ALL','--security-opt','no-new-privileges','--memory','10g' if model else '2g',
         '--memory-swap','10g' if model else '2g','--cpus','2' if model else '1','--pids-limit','128','--ipc','private','--ulimit','core=0',
         '--tmpfs','/tmp:rw,nosuid,nodev,size='+('512m' if model else '256m'),
         '--mount',f'type=bind,src={repo.resolve()},dst=/work/repo,readonly',
         '--mount',f'type=bind,src={sdk.resolve()},dst={SDK_PATH},readonly',
         '--mount',f'type=bind,src={out.resolve()},dst=/out',
         '--workdir','/work/repo','--env','DISPLAY=:99','--env','HOME=/tmp',
         '--env','XDG_CACHE_HOME=/tmp/cache','--env','LIBGL_ALWAYS_SOFTWARE=1',
         '--env','GALLIUM_DRIVER=softpipe','--env','LP_NUM_THREADS=0',
         '--env','MESA_SHADER_CACHE_DISABLE=true','--env','PYOPENGL_PLATFORM=glx',
         '--env','OMP_NUM_THREADS=2']
    if owner is not None:cmd+=['--label','stage7.sdk3.owner='+owner]
    if not model:cmd+=['--env','LD_DEBUG=bindings,versions']
    if model:
        cmd+=['--mount',f'type=bind,src={model.resolve()},dst=/model.onnx,readonly',
              '--mount',f'type=bind,src={deps.resolve()},dst=/model-deps,readonly']
    return cmd+['--entrypoint','/opt/venv/bin/python',IMAGE,'-I','-S','-B','/work/repo/scripts/panda_sdk3_diagnostic.py','--out','/out']+args


def api(path):
    return json.loads(subprocess.check_output(['gh','api','repos/'+REPO+'/'+path],text=True,timeout=60))


def authenticate_source(bundle):
    request=json.loads((ROOT/REQUEST).read_text());source=request['source_sha']
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    need(os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and head==os.environ.get('GITHUB_SHA'),'fresh actual activation')
    need(subprocess.check_output(['git','diff','--name-only',source,head],cwd=ROOT,text=True).splitlines()==[REQUEST],'request-only activation')
    for event,key in [('push','push_ci'),('pull_request','pr_ci')]:
        run=api('actions/runs/'+str(request[key]));jobs=api('actions/runs/'+str(request[key])+'/jobs')
        need(run['head_sha']==source and run['event']==event and run['workflow_id']==411705464 and run['run_attempt']==1 and run['conclusion']=='success','exact reviewed-source CI')
        need(jobs['total_count']==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(j['conclusion']=='success' for j in jobs['jobs']),'four canonical jobs')
        write(bundle/('source-ci-'+event+'.json'),dict(run=run,jobs=jobs))
    write(bundle/'request.json',request);return request


def artifact(work,bundle,aid,size,sha,run,head,label):
    meta=api('actions/artifacts/'+str(aid));need(meta['id']==aid and meta['size_in_bytes']==size and not meta['expired'] and meta['workflow_run']['id']==run and meta['workflow_run']['head_sha']==head,'fixed artifact origin')
    write(bundle/(label+'-artifact.json'),meta);path=work/(label+'.zip')
    with path.open('xb') as out:subprocess.run(['gh','api','repos/'+REPO+'/actions/artifacts/'+str(aid)+'/zip'],stdout=out,check=True,timeout=600)
    need(path.stat().st_size==size and digest(path)==sha,'artifact ZIP digest');return path


def inspect_container(identity):
    result=subprocess.run(['docker','inspect',identity],capture_output=True,text=True,timeout=15)
    if result.returncode:return None
    rows=json.loads(result.stdout);need(len(rows)==1,'one inspected container');return rows[0]


def run_container(name,sdk,out,args,*,model=None,deps=None):
    out.mkdir(parents=True);out.chmod(0o777);owner=secrets.token_hex(16)
    cmd=container_command(name,ROOT,sdk,out,args,model=model,deps=deps,owner=owner)
    write(out/'command.json',dict(argv=cmd,ownership_label=owner))
    cid=None;rc=None;failure=None;state=None;create_attempted=False;start_attempted=False;removed=False;cleanup_failure=None
    write(out/'execution.json',dict(status='PREPARING',create_attempted=False,start_attempted=False,owned_container_removed=False))
    try:
        need(inspect_container(name) is None,'fresh owned container name')
        create_attempted=True
        write(out/'execution.json',dict(status='CREATE_IN_FLIGHT',create_attempted=True,start_attempted=False,ownership_label=owner,owned_container_removed=False))
        with (out/'create.stdout.log').open('wb') as stdout,(out/'create.stderr.log').open('wb') as stderr:
            creation=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=90)
        need(creation.returncode==0,'Docker create failed; see retained creation logs')
        actual=inspect_container(name)
        need(actual is not None and actual['Config']['Labels'].get('stage7.sdk3.owner')==owner,'created ownership label')
        cid=actual['Id'];write(out/'container.json',dict(id=cid,name=name,image=IMAGE,ownership_label=owner,effective_limits={k:actual.get('HostConfig',{}).get(k) for k in ('Memory','MemorySwap','NanoCpus','PidsLimit','ReadonlyRootfs','NetworkMode','IpcMode')}))
        start_attempted=True
        with (out/'stdout.log').open('wb') as stdout,(out/'stderr.log').open('wb') as stderr:
            rc=subprocess.run(['docker','start','--attach',cid],stdout=stdout,stderr=stderr,timeout=1800 if model else 180,preexec_fn=log_limits).returncode
        actual=inspect_container(cid);need(actual is not None,'retained stopped container');state=actual['State']
        need(not state['Running'] and state['Pid']==0 and not state['OOMKilled'],'stopped non-OOM child')
        need(all((out/n).stat().st_size<=16*1024**2 for n in ['stdout.log','stderr.log']),'complete bounded logs')
    except BaseException as e:failure=type(e).__name__+': '+str(e)
    finally:
        # A create timeout can follow daemon-side creation. Recover only our exact label.
        if create_attempted and cid is None:
            try:
                actual=inspect_container(name)
                if actual is not None and actual['Config']['Labels'].get('stage7.sdk3.owner')==owner:cid=actual['Id'];state=actual['State']
            except BaseException as e:cleanup_failure='ownership recovery '+type(e).__name__+': '+str(e)
        if cid is not None:
            try:
                with (out/'remove.stdout.log').open('wb') as stdout,(out/'remove.stderr.log').open('wb') as stderr:
                    removal=subprocess.run(['docker','rm','--force',cid],stdout=stdout,stderr=stderr,timeout=30)
                removed=removal.returncode==0
                if not removed:cleanup_failure='owned removal returned '+str(removal.returncode)
            except BaseException as e:cleanup_failure='owned removal '+type(e).__name__+': '+str(e)
        if cleanup_failure:failure=((failure+'; ') if failure else '')+cleanup_failure
        execution=dict(status='FAILED' if failure else 'EXIT_OBSERVED',returncode=rc,failure=failure,stopped_state=state,
            create_attempted=create_attempted,start_attempted=start_attempted,container_id=cid,
            ownership_unresolved=create_attempted and cid is None,owned_container_removed=removed,cleanup_failure=cleanup_failure)
        write(out/'execution.json',execution)
    return execution


def aggregate_model_pairs(root):
    from scripts.aggregate_original_mdv3_current_recheck import aggregate_original_mdv3
    aggregate=aggregate_original_mdv3(root)
    rows=[dict(seed=r['seed'],scenario=r['scenario'],status=r['strict_status'],exact_repeated_execution_gate_passed=r['exact_repeated_execution_gate_passed']) for r in aggregate['per_seed_scene']]
    gate=model_gate(rows);need(gate['passed']==aggregate['strict_gate_pass_count'],'independent aggregate coherence')
    return dict(aggregate=aggregate,gate=gate)


def validate_prior_glx(root):
    root=Path(root);summary=json.loads((root/'summary.json').read_text())
    need(summary['source_sha']=='3bc46af75a2ef1f8cec415139c3688e0c14428ed' and summary['image']==IMAGE and summary['sdk_sha256']==SDK_SHA and summary['showbase_compatible'] is True,'pinned prior selected GLX context')
    ids=[]
    for index in (3,4):
        rows=[p for p in summary['probes'] if p['index']==index];need(len(rows)==1,'exact prior child');row=rows[0]
        need(row['role']=='sdk3' and row['factory']=='showbase' and row['load_order']=='core-first','prior SDK3 standard path')
        folder=root/f'probe-{index}-sdk3-showbase';report=json.loads((folder/'report.json').read_text());execution=json.loads((folder/'execution.json').read_text());native=json.loads((folder/'native-child.json').read_text())
        need(execution['failure'] is None and execution['owned_container_removed'] is True and execution['stopped_state']['OOMKilled'] is False and execution['stopped_state']['Running'] is False and execution['stopped_state']['Pid']==0,'prior clean stopped scope')
        need(native['spawn_attempted'] is True and native['pid']==report['pid'] and native['returncode']==execution['returncode']==0 and native['server_returncode']==report['server_returncode']==0 and report['child_finalized_before_server_stop'] is True,'prior child/display lifecycle')
        events=[json.loads(line.removeprefix('STAGE7_EVENT ')) for line in (folder/'stdout.log').read_text().splitlines() if line.startswith('STAGE7_EVENT ')]
        validate_probe(events,report,execution['returncode'],row['nonce'],'core-first',factory='showbase');ids.append(execution['container_id'])
    need(len(set(ids))==2,'two independent prior containers')
    return dict(selected_sdk_glx_qualified=True,verified_sdk_glx_children=2,prior_model_cohort_qualified=False,prior_official_model_processes=summary['official_model_processes'],prior_strict_result=summary['strict_result'],full_object_abi_qualified=False,stage7_complete=False)


def run_host(out:Path,model_phase:bool):
    out=out.resolve();need(not out.exists(),'fresh cohort output');work=out/'work';bundle=out/'bundle';work.mkdir(parents=True);bundle.mkdir()
    summary=dict(status='FAILED',sdk_sha256=SDK_SHA,image=IMAGE,probes=[],official_model_processes=0,strict_result='NOT_RUN',stage7_complete=False)
    write(bundle/'summary.json',summary)
    try:
        request=authenticate_source(bundle);summary['source_sha']=request['source_sha']
        import shutil
        summary['disk_before']=shutil.disk_usage(work)._asdict();write(bundle/'summary.json',summary)
        need(summary['disk_before']['free']>=8*1024**3,'8GiB ephemeral free space required')
        imagezip=artifact(work,bundle,14156262448,1738137175,'47711425a5a48fb2ef0cab140da6e394516f9cbb7f04b294c5f6583d7efbc687',43700449423,'7cf0f0157f8100f0aa0e05b01a815d7395c3383f','image')
        sdkzip=artifact(work,bundle,14191115165,61661546,'2a44226962b3175081566918dd55eb845ac8ce1c9f9f5a396f469c8f6eca5d26',43786081196,'40dd7187ce8d3c5de510aa8c7a8ac2a6d37b0f38','sdk3')
        image=verify_member(imagezip,'image.tar',1727678464,'4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698',work/'image.tar')
        sdk=verify_member(sdkzip,'candidate/libpandagl.so.data',1052968,SDK_SHA,work/'libpandagl.so')
        subprocess.run(['docker','load','-i',str(image)],check=True,timeout=600)
        need(json.loads(subprocess.check_output(['docker','image','inspect',IMAGE],text=True))[0]['Id']==IMAGE,'loaded image config')
        prefix='sdk3-'+os.environ['GITHUB_RUN_ID']+'-'
        priorzip=artifact(work,bundle,14206869856,4627908,'c6db9f8cb5a4e26f570fce6a8e91d6da96b5ec0c45f15d33f263bc20770a6d3b',43827976143,'523d1525c9a960a804605dabfb7b8a38ac96d906','prior-glx')
        priorroot=bundle/'prior-glx';priorroot.mkdir()
        selected=['summary.json']+[f'probe-{i}-sdk3-showbase/'+n for i in (3,4) for n in ('report.json','execution.json','native-child.json','stdout.log')]
        with ZipFile(priorzip) as z:
            need(len(z.namelist())==len(set(z.namelist())),'prior duplicate members')
            for name in selected:
                info=z.getinfo(name);need(info.file_size<=1024**2,'bounded prior member');dest=priorroot/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(info))
        summary['prior_glx']=validate_prior_glx(priorroot)
        summary['showbase_compatible']=True;summary['core_first_compatible']=True;summary['status']='SDK3_GLX_SELECTED_RUNTIME_OBSERVED'
        if model_phase:
            meminfo={}
            for line in Path('/proc/meminfo').read_text().splitlines():
                key,value=line.split(':',1)
                if key in ('MemTotal','MemAvailable'):meminfo[key]=int(value.split()[0])*1024
            summary['host_memory_before_model']=meminfo;write(bundle/'summary.json',summary)
            need(meminfo['MemAvailable']>=12*1024**3,'12GiB host availability required for10GiB model container')
            from bigbench.model_inventory import download_checked
            model=download_checked(path=MODEL_ID,sha256=MODEL_SHA,output_dir=work/'models',max_bytes=900000000)
            need(Path(model).stat().st_size==768750198,'official model extent')
            deps=Path(os.environ['SDK3_MODEL_DEPS']);need(deps.is_dir(),'ephemeral ORT dependencies')
            from scripts.compare_fresh_native_mdv3 import compare_fresh_trials
            verdicts=[]
            for seed,scene in sorted(CASES):
                case=bundle/'models'/f'seed-{seed}'/scene
                dest=case/'pair'
                e=run_container(prefix+f'{seed}-{scene}',sdk,dest,['--model-pair','--seed',str(seed),'--scenario',scene],model=Path(model),deps=deps)
                ledger=json.loads((dest/'pair-ledger.json').read_text()) if (dest/'pair-ledger.json').exists() else []
                counts=observed_model_processes(ledger)
                summary['official_model_processes']+=counts['known']
                summary.setdefault('model_pairs',[]).append(dict(seed=seed,scenario=scene,counts=counts,execution=e))
                write(bundle/'summary.json',summary)
                need(e['returncode']==0 and e['failure'] is None and e['owned_container_removed'],'completed actual model pair')
                need(counts==dict(known=2,upper=2,spawn_attempts=2),'two actual model children')
                rows=[json.loads((dest/f'run-{n}'/'run.json').read_text()) for n in range(2)]
                need(rows[0]['process_uuid']!=rows[1]['process_uuid'],'fresh independent process UUIDs')
                v=compare_fresh_trials(*rows);write(case/'strict_native_repeat_verdict.json',v);verdicts.append(v)
                for n in range(2):(case/f'run_{n}.json').write_bytes((dest/f'run-{n}'/'run.json').read_bytes())
            independent=aggregate_model_pairs(bundle/'models');write(bundle/'independent-model-aggregate.json',independent['aggregate'])
            summary['model_gate']=independent['gate'];summary['strict_result']=str(summary['model_gate']['passed'])+'/4 '+('PASS' if summary['model_gate']['strict_pass'] else 'FAIL')
            summary['status']='SDK3_MODEL_COHORT_OBSERVED';summary['expansion']='PENDING_SEPARATE_MATRIX' if summary['model_gate']['strict_pass'] else 'BLOCKED_BY_STRICT_FAILURE'
        write(bundle/'summary.json',summary);return summary
    except BaseException as e:
        summary['failure']=type(e).__name__+': '+str(e);write(bundle/'summary.json',summary);raise


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true',required=True);p.add_argument('--model-phase',action='store_true');args=p.parse_args()
    value=run_host(ROOT/'output/stage7-panda-sdk3-runtime-01/producer',args.model_phase);print(json.dumps(value))

if __name__=='__main__':sys.path.insert(0,str(ROOT));main()
