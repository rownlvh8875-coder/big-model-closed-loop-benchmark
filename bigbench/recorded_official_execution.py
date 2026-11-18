"""Sealed one-case official recorded diagnostic; portable metadata readers only."""
from pathlib import Path
import hashlib
import json
import os
from .full_s_recorded_worker import need, _read_receipt, _receipt_bytes
from .recorded_worker_canary import check_source_map, qualified_geometry, QUALIFIED_PROBE, QUALIFIED_PROBE_SHA, STAT_FIELDS

ROOT=Path(__file__).resolve().parents[1]
MODE='OFFICIAL_RECORDED_DIAGNOSTIC'
CASE=(20261109,'s_curve_left_right')
REQUEST='docs/requests/recorded-official-20261118-01.json'
BRANCH='diagnostic/recorded-official-20261118-01'
WORKFLOW='.github/workflows/recorded-official.yml'
APPROVAL_BRANCH='approval/recorded-official-20261118-01'
APPROVAL_PATH='docs/approvals/recorded-official-20261118-01.json'
RUNTIME='configs/recorded-official-runtime.json'
LIMITS=dict(steps=600,official_models=1,official_inferences=600,child_seconds=9000,container_seconds=9030,
    memory_bytes=10*1024**3,cpus=2,pids=128,tmp_bytes=512*1024**2)
FALSE_FLAGS=('origin_authenticated','native_execution_authenticated','model_camera_qualified',
    'physical_optics_validated','carla_validated','hardware_gpu_qualified','all_four_validation_tracks_passed')


def clone(function,**changes):
    from types import FunctionType
    value=FunctionType(function.__code__,dict(function.__globals__,**changes),function.__name__,function.__defaults__,function.__closure__)
    value.__kwdefaults__=dict(function.__kwdefaults__ or {})
    return value


def read_native_ack(path):
    root=Path(path).parent
    launch=_read_receipt(root/'launch.json');native=_read_receipt(root/'native-child.json')
    need(launch.get('mode')==MODE and (launch.get('seed'),launch.get('scenario'))==CASE and
         launch.get('parent_pid')==os.getppid(),'sealed official parent/case required')
    need(all(k in native for k in ('pid','spawn_attempted','returncode','server_returncode')) and
         native['spawn_attempted'] is True and native['returncode'] is None and native['server_returncode'] is None,
         'live nonfinal native acknowledgement required')
    pid=native.get('pid')
    need(pid is None or type(pid) is int and pid==os.getpid(),'actual native child PID required')
    return dict(launch,pid=pid,spawn_succeeded=True if pid is not None else None,child_reaped=False,returncode=None)


def activity_bounds(life):
    if life is None:return dict(official_model_process_bounds=[0,1],official_inference_bounds=[0,600])
    entered=life.get('policy_constructor_entered');created=life.get('policy_created');bounds=life.get('inference_bounds')
    need(type(entered) is bool and type(created) is bool and (not created or entered),'typed original policy milestones required')
    need(isinstance(bounds,list) and len(bounds)==2 and all(type(v) is int for v in bounds) and
         0<=bounds[0]<=bounds[1]<=600 and bounds[1]-bounds[0]<=1 and (created or bounds==[0,0]),'bounded original calls required')
    return dict(official_model_process_bounds=[1,1] if created else [0,1] if entered else [0,0],official_inference_bounds=bounds)


def validate_public_activity(pages,*,current_id,require_current=True):
    need(type(current_id) is int and current_id>0 and isinstance(pages,list) and 0<len(pages)<=100,'bounded whole-repository pages required')
    total=pages[0].get('total_count');need(type(total) is int and 0<=total<=10000,'typed repository run count required')
    rows=[]
    for i,page in enumerate(pages):
        values=page.get('workflow_runs')
        need(page.get('total_count')==total and isinstance(values,list) and len(values)<=100 and
             (i==len(pages)-1 or len(values)==100),'complete stable pagination required')
        rows.extend(values)
    need(len(rows)==total and all(isinstance(r,dict) and type(r.get('id')) is int and r['id']>0 and
         type(r.get('workflow_id')) is int and r['workflow_id']>0 for r in rows) and
         len({r['id'] for r in rows})==total,'complete duplicate-free repository history required')
    active=[r for r in rows if r.get('status')!='completed']
    need(not require_current or any(r['id']==current_id for r in active),'authenticated current run must be present and active in full repository snapshot')
    need(all(r.get('status') in ('queued','in_progress','waiting','pending','requested') for r in active),'recognized active status required')
    unknown=[r for r in active if r['id']!=current_id and r['workflow_id'] not in (411705464,421897387,422015100)]
    need(not unknown,'unknown publicly active job forbids new official-model staging/execution')
    return dict(protocol='recorded-official-public-activity-v1',total_count=total,active_runs=active,
        unknown_active_runs=[],private_task_state='UNKNOWN',private_task_observable=False)


def model_memory_gate(host_available,cgroup_limit,cgroup_current):
    need(all(type(v) is int and v>=0 for v in (host_available,cgroup_limit,cgroup_current)) and
         cgroup_limit==LIMITS['memory_bytes'] and cgroup_current<=cgroup_limit,'typed actual bounded cgroup/host memory required')
    available=min(host_available,cgroup_limit-cgroup_current)
    need(available>=8*1024**3,'8GiB available model RAM required immediately before original constructor')
    return dict(host_available_bytes=host_available,cgroup_limit_bytes=cgroup_limit,cgroup_current_bytes=cgroup_current,
        effective_available_bytes=available,minimum_model_ram_bytes=8*1024**3,admitted=True)


def finalize_preserving_primary(primary,actions,secondary):
    import sys
    failures=[]
    for action in actions:
        try:action()
        except BaseException as exc:
            failures.append(exc);secondary.append(type(exc).__name__+': '+str(exc)[:2048])
            print('SECONDARY_FINALIZATION_ERROR '+secondary[-1],file=sys.stderr,flush=True)
    if failures and primary is None:raise failures[0]


def _optional(path,limit=65536):
    try:path.lstat()
    except FileNotFoundError:return None
    return _read_receipt(path,limit)


def validate_native_bundle(root,*,qualified=None):
    """Validate surviving bytes independently; never infer execution from absence."""
    from scripts import run_recorded_official as host
    from scripts import panda_sdk3_runtime as pins
    from . import full_s_recorded_receiver as receiver, recorded_official_dependencies as deps
    root=Path(root);unavailable=[];infra=[]
    auth=_read_receipt(root/'authentication.json',4*1024**2)
    def validate_auth(value):
        host.validate_request(value['request'])  # Validate SHA before any Git read.
        expected=host.validate_admission(value['request'],value['context'],manifest=host.source_manifest(value['request']['source']),
            ci=value['source_ci'],authority=value['authority'],current=value['current_identity'],history=value['history'])
        need(value==expected,'exact retained approval/source/current admission required')
    validate_auth(auth)
    source_hash=check_source_map(ROOT,auth['request']['source_map'])
    for label in ('before-staging','before-model','before-container'):
        snapshot=_optional(root/('public-activity-'+label+'.json'),4*1024**2)
        if snapshot is None:unavailable.append('public-activity-'+label+'.json')
        else:validate_public_activity(snapshot['pages'],current_id=int(auth['run_id']))
        if label!='before-staging':
            fresh=_optional(root/('authentication-'+label+'.json'),4*1024**2)
            if fresh is None:unavailable.append('authentication-'+label+'.json')
            else:
                validate_auth(fresh)
                need(all(fresh[k]==auth[k] for k in ('request','source','activation','run_id','branch','event','attempt','context','current_identity','history')),
                     'same immutable approval/current run across all admission snapshots required')
    folder=root/'native'
    top=_optional(folder/'report.json');launch=_optional(folder/'launch.json');native=_optional(folder/'native-child.json')
    completion=_optional(folder/'parent-completion.json');life=_optional(folder/'observed-trial/recorded-trial-lifecycle.json')
    trial=_optional(folder/'observed-trial/recorded-trial.json',4*1024**2)
    body=receiver.inspect_trial(folder/'observed-trial') if life is not None or trial is not None else None
    bounds=activity_bounds(None)
    for name,value in (('launch.json',launch),('report.json',top),('native-child.json',native),('parent-completion.json',completion),
                        ('observed-trial/recorded-trial-lifecycle.json',life),('observed-trial/recorded-trial.json',trial)):
        if value is None:unavailable.append(name)
    for value in (launch,top,completion):
        if value is None:continue
        need(all(value.get(k)==auth[k] for k in ('source','activation','run_id')) and value.get('approval')==auth['request']['approval_sha'] and
             value.get('mode')==MODE and receiver._hex(value.get('nonce'),32) and type(value.get('parent_pid')) is int and value['parent_pid']>0,
             'native source/approval/current run/parent identity required')
        if launch is not None:need(all(value.get(k)==launch.get(k) for k in ('nonce','parent_pid')),'same launch nonce/live parent required')
    for value in (launch,top):
        if value is not None:need((value.get('seed'),value.get('scenario'))==CASE and
            json.dumps(value.get('limits'),sort_keys=True)==json.dumps(LIMITS,sort_keys=True),'sealed official case/budget required')
    linked=launch is not None and native is not None and type(native.get('pid')) is int and native['pid']>0
    for value in (life,trial):
        if value is None:continue
        need((value.get('seed'),value.get('scenario'))==CASE,'single registered original case required')
        if linked:
            need(value['pid']==native['pid'] and all(value[k]==launch[k] for k in ('parent_pid','nonce','seed','scenario')),'original body/launch/native PID binding required')
        else:unavailable.append('body/native launch association')
    if life is not None and linked:bounds=activity_bounds(life)
    if trial is not None and linked:
        bounds['official_inference_bounds']=list(body['reported_inference_bounds'])
        if trial.get('onnxruntime',{}).get('real_session') is True:bounds['official_model_process_bounds']=[1,1]
    descriptor=_optional(root/'model-dependencies.json',4*1024**2);dep_sha=None
    if descriptor is None:unavailable.append('model-dependencies.json')
    else:
        raw=_receipt_bytes(root/'model-dependencies.json',4*1024**2);dep_sha=hashlib.sha256(raw).hexdigest()
        need(descriptor.get('protocol')=='recorded-official-installed-dependencies-v1' and descriptor.get('versions')==deps.VERSIONS and
             descriptor.get('declaration_sha256')==deps.DECLARATION_SHA,'exact original pinned dependency declaration required')
        files=descriptor.get('files');need(isinstance(files,dict) and 0<len(files)<=deps.MAX_FILES,'bounded dependency file map required')
        from pathlib import PurePosixPath
        for name,entry in files.items():
            need(isinstance(name,str) and name==PurePosixPath(name).as_posix() and not PurePosixPath(name).is_absolute() and
                 all(v not in ('','..','.') for v in name.split('/')) and '\\' not in name and ':' not in name and
                 isinstance(entry,dict) and type(entry.get('nbytes')) is int and 0<=entry['nbytes']<=deps.MAX_MEMBER and
                 receiver._hex(entry.get('sha256'),64),'bounded canonical installed dependency namespace required')
        need(sum(v['nbytes'] for v in files.values())<=deps.MAX_TOTAL,'bounded installed dependency extent required')
        mounted_desc=_optional(folder/'model-dependencies.json',4*1024**2)
        if mounted_desc is None:unavailable.append('native/model-dependencies.json')
        else:need(_receipt_bytes(folder/'model-dependencies.json',4*1024**2)==raw,'exact host/native dependency descriptor bytes required')
        for value in (top,launch):
            if value is not None:need(value.get('dependencies_sha256')==dep_sha,'admitted descriptor SHA required')
    container=_optional(folder/'container.json');execution=_optional(folder/'execution.json');command=_optional(folder/'command.json')
    mounted={}
    for name,value in (('container.json',container),('execution.json',execution),('command.json',command)):
        if value is None:unavailable.append(name)
    if command is not None:
        argv=command.get('argv');need(isinstance(argv,list) and all(isinstance(v,str) for v in argv),'actual Docker argv required')
        mounts=[argv[i+1] for i,v in enumerate(argv[:-1]) if v=='--mount'];need(len(mounts)==5,'five original mounts required')
        for mount in mounts:
            fields=dict(part.split('=',1) if '=' in part else (part,'') for part in mount.split(','))
            need(fields.get('type')=='bind' and 'src' in fields and 'dst' in fields and fields['dst'] not in mounted,'unique canonical bind mount required')
            mounted[fields['dst']]=fields['src']
        need(set(mounted)=={'/work/repo','/out',pins.SDK_PATH,'/model.onnx','/model-deps'},'exact original official mounts required')
        if container is not None and dep_sha is not None:
            expected=host.official_command(container['name'],Path(mounted['/work/repo']),Path(mounted[pins.SDK_PATH]),Path(mounted['/out']),
                ['--source',auth['source'],'--activation',auth['activation'],'--run-id',auth['run_id'],'--approval',auth['request']['approval_sha'],
                 '--dependencies-sha256',dep_sha],owner=command['ownership_label'],model=Path(mounted['/model.onnx']),deps=Path(mounted['/model-deps']))
            need(argv==expected,'exact source/resource/dependency official command required')
    if container is not None:
        need(container.get('name')=='recorded-official-'+auth['run_id'] and container.get('image')==pins.IMAGE and receiver._hex(container.get('id'),64) and
             container.get('effective_limits')==dict(Memory=10*1024**3,MemorySwap=10*1024**3,NanoCpus=2_000_000_000,
                PidsLimit=128,ReadonlyRootfs=True,NetworkMode='none',IpcMode='private'),'actual immutable container/resource identity required')
        if command is not None:need(receiver._hex(command.get('ownership_label'),32) and command['ownership_label']==container.get('ownership_label'),'same owned container label required')
        for value in (top,completion):
            if value is not None:need(value.get('container_hostname')==container['id'][:12],'native actual container identity required')
    if execution is not None:
        if container is not None:need(execution.get('container_id')==container['id'],'same owned container execution required')
        for key,expected in (('create_attempted',True),('start_attempted',True),('owned_container_removed',True),('ownership_unresolved',False),('cleanup_failure',None),('failure',None)):
            if execution.get(key)!=expected:infra.append('execution '+key+': '+str(execution.get(key))[:2048])
        state=execution.get('stopped_state') or {}
        if not (state.get('Running') is False and state.get('Pid')==0 and state.get('OOMKilled') is False):infra.append('stopped non-OOM container state unavailable/failed')
        if execution.get('returncode') is None:infra.append('container exit unavailable')
        elif state and type(state.get('ExitCode')) is int:need(state['ExitCode']==execution['returncode'],'container actual exit contradiction')
    handoff=_optional(root/'evidence-handoff.json')
    if handoff is None:unavailable.append('evidence-handoff.json')
    elif mounted:
        need(handoff.get('protocol')=='recorded-worker-evidence-handoff-v1' and handoff.get('status')=='EVIDENCE_HANDED_TO_RUNNER' and
             handoff.get('native_dir')==mounted['/out'] and type(handoff.get('uid')) is int and handoff['uid']>0 and handoff['uid']!=65534 and
             type(handoff.get('gid')) is int and handoff['gid']>=0 and handoff.get('writer_uid')==handoff.get('writer_gid')==65534 and
             handoff.get('symlinks_followed') is False and handoff.get('container_removed') is True and handoff.get('argv')==
             ['sudo','-n','chown','-R','--no-dereference','--from=65534:65534',str(handoff['uid'])+':'+str(handoff['gid']),'--',mounted['/out']],
             'exact stopped evidence handoff required')
    if top is not None:
        need(top.get('protocol')=='recorded-official-native-v1' and all(top.get(k) is False for k in FALSE_FLAGS),'actual native protocol and unqualified scope required')
        if top.get('source_map_sha256') is None:unavailable.append('native source-map check')
        else:need(top['source_map_sha256']==source_hash,'native full source hash contradiction')
        if linked:need(top.get('pid')==native['pid'],'native PID contradiction')
        for key,budget in (('official_model_process_bounds',1),('official_inference_bounds',600)):
            declared=top.get(key)
            need(isinstance(declared,list) and len(declared)==2 and all(type(v) is int for v in declared) and 0<=declared[0]<=declared[1]<=budget,'typed bounded native count declaration required')
            if linked and (life is not None or trial is not None):
                earlier=activity_bounds(life)[key] if life is not None else bounds[key]
                need(declared==bounds[key] or declared==earlier,'native count must bind latest trial or valid earlier lifecycle checkpoint')
        if life is not None or trial is not None:
            need(top.get('parent_admission_checked') is True and top.get('model_sha256')==pins.MODEL_SHA and top.get('model_nbytes')==768750198 and
                 top.get('sdk_sha256')==pins.SDK_SHA and top.get('core_sha256')==pins.CORE_SHA and top.get('load_order')=='core-first' and top.get('panda_version')=='1.10.13',
                 'original body requires admitted real model/SDK/core bootstrap')
            if descriptor is not None:need(top.get('dependencies')==dict(versions=deps.VERSIONS,declaration_sha256=deps.DECLARATION_SHA,file_count=len(descriptor['files'])),'mounted original dependency bytes must have been verified')
            memory=top.get('model_memory')
            if memory is None:unavailable.append('pre-constructor model RAM gate')
            else:need(memory==model_memory_gate(memory.get('host_available_bytes'),memory.get('cgroup_limit_bytes'),memory.get('cgroup_current_bytes')),'actual 8GiB pre-constructor model RAM gate required')
        if trial is not None:
            if top.get('recorded_trial_sha256') is None:unavailable.append('native recorded trial digest')
            else:need(top['recorded_trial_sha256']==hashlib.sha256(_receipt_bytes(folder/'observed-trial/recorded-trial.json',4*1024**2)).hexdigest(),'exact original worker digest required')
        if top.get('failure') is not None:infra.append('native '+str(top['failure'])[:2048])
        if top.get('secondary_errors'):infra.extend('native secondary '+str(v)[:2048] for v in top['secondary_errors'])
    if completion is not None:
        need(completion.get('protocol')=='recorded-official-parent-completion-v1','registered parent completion required')
        for name,value,key in (('native-child.json',native,'native_child_sha256'),('report.json',top,'report_sha256')):
            if value is not None:
                if completion.get(key) is None:unavailable.append('parent '+key)
                else:need(completion[key]==hashlib.sha256(_receipt_bytes(folder/name)).hexdigest(),'parent finalization byte contradiction')
        if native is not None:
            need(completion.get('pid')==native.get('pid'),'parent/native actual PID contradiction')
            if completion.get('returncode') is not None and native.get('returncode') is not None:need(completion['returncode']==native['returncode'],'parent/native exit contradiction')
        if completion.get('failure') is not None or completion.get('status')!='NATIVE_CHILD_REAPED':infra.append('parent completion failed')
        if completion.get('secondary_errors'):infra.extend('parent secondary '+str(v)[:2048] for v in completion['secondary_errors'])
    if native is not None:
        if native.get('failure') is not None:infra.append('native owner '+str(native['failure'])[:2048])
        if native.get('returncode') is None:unavailable.append('final native exit')
        if native.get('server_returncode')!=0:infra.append('owned display stop failed/unavailable')
        if execution is not None and native.get('returncode') is not None and execution.get('returncode') is not None and not infra:
            need(native['returncode']==execution['returncode'],'native/container exit contradiction')
        if top is not None:
            if top.get('server_returncode') is not None:need(top['server_returncode']==native.get('server_returncode'),'native display exit contradiction')
            if top.get('child_finalized_before_server_stop') is not True:infra.append('child finalization before display stop unavailable')
    if top is not None:
        for stats in (top.get('source_stats_before'),top.get('source_stats_after'),trial.get('source_stats_after') if trial else None):
            if stats is None:
                if top.get('status')=='OFFICIAL_RECORDED_DIAGNOSTIC_RETURNED':unavailable.append('default-off SDK counters')
                continue
            need(isinstance(stats,dict) and type(stats.get('returned')) is int and stats['returned']==0 and stats.get('guards_ok') is True and
                 stats.get('values')=={k:0 for k in STAT_FIELDS} and all(type(v) is int for v in stats['values'].values()),'default-off SDK counters must remain zero')
    visual=body is not None and body.get('recording_structure_valid') is True
    if visual:
        report=_optional(folder/'observed-trial/recording/report.json',16*1024**2)
        probe=qualified if qualified is not None else qualified_geometry()
        if report is not None:
            from .full_s_receipts import bind_case_geometry
            bind_case_geometry(report,probe)
        driver=trial.get('driver') if trial else None
        if driver is None:unavailable.append('measured visual renderer')
        else:
            need(isinstance(driver,dict) and 'llvmpipe' in str(driver.get('renderer')).lower() and
                 all(isinstance(driver.get(k),str) and driver[k] and driver[k]==probe.get('driver',{}).get(k) for k in ('renderer','vendor','version')),
                 'actual measured renderer/vendor/version must match pinned qualified probe')
    status='INCOMPLETE_EVIDENCE'
    if body is not None and not unavailable:
        status=body['status']
        if status=='COMPLETE_DIAGNOSTIC':
            if infra or native.get('returncode')!=0 or top.get('status')!='OFFICIAL_RECORDED_DIAGNOSTIC_RETURNED':status='PARTIAL_DIAGNOSTIC'
        if status=='PARTIAL_DIAGNOSTIC' and not infra and native.get('returncode')==0:infra.append('body incomplete despite zero native exit')
    return dict(protocol='recorded-official-bundle-receiver-v1',status=status,source=auth['source'],activation=auth['activation'],run_id=auth['run_id'],
        container_id=container.get('id') if container else None,source_map_sha256=source_hash,dependencies_sha256=dep_sha,body=body,
        unavailable_outer_evidence=unavailable,infrastructure_errors=infra,private_task_state='UNKNOWN',**bounds,**{k:False for k in FALSE_FLAGS})
