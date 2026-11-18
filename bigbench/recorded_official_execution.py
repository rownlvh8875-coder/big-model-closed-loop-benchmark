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


def validate_public_activity(pages,*,current_id):
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
    need(all(r.get('status') in ('queued','in_progress','waiting','pending','requested') for r in active),'recognized active status required')
    unknown=[r for r in active if r['id']!=current_id and r['workflow_id'] not in (411705464,421897387,422015100)]
    need(not unknown,'unknown publicly active job forbids new official-model staging/execution')
    return dict(protocol='recorded-official-public-activity-v1',total_count=total,active_runs=active,
        unknown_active_runs=[],private_task_state='UNKNOWN',private_task_observable=False)


def _optional(path,limit=65536):
    try:path.lstat()
    except FileNotFoundError:return None
    return _read_receipt(path,limit)


def validate_native_bundle(root,*,qualified=None):
    """Local structure/byte binding only; API artifact origin is a separate gate."""
    from scripts import run_recorded_official as host
    from scripts import panda_sdk3_runtime as pins
    from . import full_s_recorded_receiver as receiver, recorded_official_dependencies as deps
    root=Path(root)
    auth=_read_receipt(root/'authentication.json',4*1024**2)
    need(all(k in auth for k in ('request','context','source_ci','authority','current_identity','history')),'complete source approval/API admission required')
    reconstructed=host.validate_admission(auth['request'],auth['context'],manifest=host.source_manifest(auth['source']),
        ci=auth['source_ci'],authority=auth['authority'],current=auth['current_identity'],history=auth['history'])
    need(reconstructed==auth,'exact retained admission required')
    source_hash=check_source_map(ROOT,auth['request']['source_map'])
    for label in ('before-staging','before-container'):
        validate_public_activity(_read_receipt(root/('public-activity-'+label+'.json'),4*1024**2)['pages'],current_id=int(auth['run_id']))
    descriptor_raw=_receipt_bytes(root/'model-dependencies.json',4*1024**2)
    descriptor=_read_receipt(root/'model-dependencies.json',4*1024**2)
    dep_sha=hashlib.sha256(descriptor_raw).hexdigest()
    need(descriptor.get('protocol')=='recorded-official-installed-dependencies-v1' and
         descriptor.get('versions')==deps.VERSIONS and descriptor.get('declaration_sha256')==deps.DECLARATION_SHA,
         'exact original dependency declaration/versions required')
    files=descriptor.get('files');need(isinstance(files,dict) and 0<len(files)<=deps.MAX_FILES,'bounded dependency file map required')
    from pathlib import PurePosixPath
    for name,entry in files.items():
        need(isinstance(name,str) and name==PurePosixPath(name).as_posix() and not PurePosixPath(name).is_absolute() and
             all(v not in ('','..','.') for v in name.split('/')) and '\\' not in name and ':' not in name and
             isinstance(entry,dict) and type(entry.get('nbytes')) is int and 0<=entry['nbytes']<=deps.MAX_MEMBER and
             receiver._hex(entry.get('sha256'),64),'canonical bounded dependency file map required')
    need(sum(v['nbytes'] for v in files.values())<=deps.MAX_TOTAL,'bounded dependency namespace required')
    folder=root/'native'
    need(_receipt_bytes(folder/'model-dependencies.json',4*1024**2)==descriptor_raw,'host/native dependency descriptor binding required')
    container=_read_receipt(folder/'container.json');execution=_read_receipt(folder/'execution.json')
    command=_read_receipt(folder/'command.json');argv=command.get('argv')
    need(isinstance(argv,list) and all(isinstance(v,str) for v in argv),'actual Docker command required')
    mounts=[argv[i+1] for i,v in enumerate(argv[:-1]) if v=='--mount'];mounted={}
    need(len(mounts)==5,'exact original model/dependency mount count required')
    for mount in mounts:
        fields=dict(part.split('=',1) if '=' in part else (part,'') for part in mount.split(','))
        need(fields.get('type')=='bind' and 'src' in fields and 'dst' in fields and fields['dst'] not in mounted,'canonical unique bind mount required')
        mounted[fields['dst']]=fields['src']
    need(set(mounted)=={'/work/repo','/out',pins.SDK_PATH,'/model.onnx','/model-deps'},'exact official-model mount namespace required')
    expected=host.official_command(container['name'],Path(mounted['/work/repo']),Path(mounted[pins.SDK_PATH]),Path(mounted['/out']),
        ['--source',auth['source'],'--activation',auth['activation'],'--run-id',auth['run_id'],
         '--approval',auth['request']['approval_sha'],'--dependencies-sha256',dep_sha],
        owner=command['ownership_label'],model=Path(mounted['/model.onnx']),deps=Path(mounted['/model-deps']))
    need(argv==expected,'exact sealed official Docker command/resources/environment required')
    need(container.get('name')=='recorded-official-'+auth['run_id'] and container.get('image')==pins.IMAGE and
         receiver._hex(container.get('id'),64) and container['id']==execution.get('container_id') and
         command.get('ownership_label')==container.get('ownership_label') and receiver._hex(command.get('ownership_label'),32) and
         container.get('effective_limits')==dict(Memory=10*1024**3,MemorySwap=10*1024**3,NanoCpus=2_000_000_000,
            PidsLimit=128,ReadonlyRootfs=True,NetworkMode='none',IpcMode='private'),'immutable owned container/resources required')
    need(execution.get('create_attempted') is True and execution.get('start_attempted') is True and
         execution.get('owned_container_removed') is True and execution.get('ownership_unresolved') is False and
         execution.get('cleanup_failure') is None,'resolved stopped/removed owned container required')
    handoff=_read_receipt(root/'evidence-handoff.json')
    need(handoff.get('protocol')=='recorded-worker-evidence-handoff-v1' and handoff.get('status')=='EVIDENCE_HANDED_TO_RUNNER' and
         handoff.get('native_dir')==mounted['/out'] and type(handoff.get('uid')) is int and handoff['uid']>0 and handoff['uid']!=65534 and
         type(handoff.get('gid')) is int and handoff['gid']>=0 and handoff.get('writer_uid')==handoff.get('writer_gid')==65534 and
         handoff.get('symlinks_followed') is False and handoff.get('container_removed') is True and handoff.get('argv')==
         ['sudo','-n','chown','-R','--no-dereference','--from=65534:65534',str(handoff['uid'])+':'+str(handoff['gid']),'--',mounted['/out']],
         'stopped evidence ownership handoff required')
    top=_optional(folder/'report.json');launch=_optional(folder/'launch.json')
    native=_optional(folder/'native-child.json');completion=_optional(folder/'parent-completion.json')
    life=_optional(folder/'observed-trial/recorded-trial-lifecycle.json')
    trial=_optional(folder/'observed-trial/recorded-trial.json',4*1024**2)
    bounds=activity_bounds(None);unavailable=[]
    if life is not None:
        receiver._lifecycle(life);bounds=activity_bounds(life)
        need((life['seed'],life['scenario'])==CASE,'single registered official body case required')
    for name,value in (('launch.json',launch),('report.json',top),('native-child.json',native),('parent-completion.json',completion)):
        if value is None:unavailable.append(name)
    for value in (top,launch,completion):
        if value is None:continue
        need(all(value.get(k)==auth[k] for k in ('source','activation','run_id')) and value.get('approval')==auth['request']['approval_sha'] and
             value.get('mode')==MODE and receiver._hex(value.get('nonce'),32) and type(value.get('parent_pid')) is int and value['parent_pid']>0,
             'native parent/source/approval/run/mode identity required')
        if launch is not None:need(all(value.get(k)==launch.get(k) for k in ('nonce','parent_pid')),'same native launch required')
    for value in (top,launch):
        if value is not None:need((value.get('seed'),value.get('scenario'))==CASE and value.get('limits')==LIMITS and
            value.get('dependencies_sha256')==dep_sha,'sealed case/resources/dependency descriptor required')
    if life is not None:
        need(launch is not None and native is not None and all(life.get(k)==launch.get(k) for k in ('nonce','parent_pid','seed','scenario')) and
             life['pid']==native.get('pid'),'original worker/native/live launch binding required')
    body=receiver.inspect_trial(folder/'observed-trial') if life is not None or trial is not None else None
    if body is not None:
        need(body.get('reported_inference_bounds') in (None,bounds['official_inference_bounds']),'outer bounds must match original receiver')
    if top is not None:
        need(top.get('protocol')=='recorded-official-native-v1' and all(top.get(k) is False for k in FALSE_FLAGS) and
             top.get('container_hostname')==container['id'][:12] and top.get('source_map_sha256')==source_hash and
             all(top.get(k)==v for k,v in bounds.items()),'exact native source/container/count/qualification binding required')
        if life is not None:need(top.get('parent_admission_checked') is True and top.get('pid')==life['pid'] and
             top.get('model_sha256')==pins.MODEL_SHA and top.get('model_nbytes')==768750198 and
             top.get('dependencies')==dict(versions=deps.VERSIONS,declaration_sha256=deps.DECLARATION_SHA,file_count=len(files)) and
             top.get('sdk_sha256')==pins.SDK_SHA and top.get('core_sha256')==pins.CORE_SHA and
             top.get('load_order')=='core-first' and top.get('panda_version')=='1.10.13','real admitted model/dependencies/SDK/core bootstrap required')
        if trial is not None:need(top.get('recorded_trial_sha256')==hashlib.sha256(_receipt_bytes(folder/'observed-trial/recorded-trial.json',4*1024**2)).hexdigest(),'exact original worker receipt hash required')
    if completion is not None:
        need(completion.get('protocol')=='recorded-official-parent-completion-v1' and
             completion.get('container_hostname')==container['id'][:12],'registered parent completion required')
        for name,value,key in (('native-child.json',native,'native_child_sha256'),('report.json',top,'report_sha256')):
            if value is not None:need(completion.get(key)==hashlib.sha256(_receipt_bytes(folder/name)).hexdigest(),'exact parent finalization byte binding required')
        if native is not None:need(completion.get('pid')==native.get('pid') and completion.get('returncode')==native.get('returncode'),'final child exit/PID binding required')
    status='INCOMPLETE_EVIDENCE'
    if not unavailable and body is not None:
        need(type(native.get('pid')) is int and native['pid']>0 and top.get('pid')==native['pid'] and native.get('spawn_attempted') is True,
             'actual spawned native PID required')
        rc=native.get('returncode');state=execution.get('stopped_state') or {}
        need(type(rc) is int and execution.get('returncode')==rc and state.get('Running') is False and state.get('Pid')==0 and
             state.get('OOMKilled') is False and state.get('ExitCode')==rc and execution.get('failure') is None and execution.get('status')=='EXIT_OBSERVED' and
             native.get('server_returncode')==top.get('server_returncode')==0 and native.get('failure') is None and
             top.get('child_finalized_before_server_stop') is True and completion.get('status')=='NATIVE_CHILD_REAPED' and completion.get('failure') is None,
             'reaped child/display and stopped non-OOM native execution required')
        need((rc==0)==(top.get('status')=='OFFICIAL_RECORDED_DIAGNOSTIC_RETURNED') and
             (top.get('failure') is None)==(rc==0),'native status/failure/exit binding required')
        need((rc==0)==(body.get('producer_reported_body_success') is True),'body result must agree with actual native return code')
        for stats in (top.get('source_stats_before'),top.get('source_stats_after'),trial.get('source_stats_after') if trial else None):
            if stats is None:
                need(rc!=0,'complete body requires all source counters');continue
            need(isinstance(stats,dict) and type(stats.get('returned')) is int and stats['returned']==0 and stats.get('guards_ok') is True and
                 stats.get('values')=={k:0 for k in STAT_FIELDS} and all(type(v) is int for v in stats['values'].values()),'default-off immutable SDK counters required')
        report=_optional(folder/'observed-trial/recording/report.json',16*1024**2)
        if report is not None:
            from .full_s_receipts import bind_case_geometry
            bind_case_geometry(report,qualified if qualified is not None else qualified_geometry())
        status=body['status']
    return dict(protocol='recorded-official-bundle-receiver-v1',status=status,source=auth['source'],activation=auth['activation'],
        run_id=auth['run_id'],container_id=container['id'],source_map_sha256=source_hash,dependencies_sha256=dep_sha,
        body=body,unavailable_outer_evidence=unavailable,private_task_state='UNKNOWN',**bounds,**{k:False for k in FALSE_FLAGS})
