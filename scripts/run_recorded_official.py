"""Authenticate and run one one official-model recorded diagnostic on ephemeral CI."""
from pathlib import Path
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigbench import recorded_official_execution as c
from bigbench.full_s_recorded_worker import need,_read_receipt,_write_receipt

ROOT=Path(__file__).resolve().parents[1]
FEATURE='feature/recorded-official-v1'
ENTRY='/work/repo/scripts/recorded_official_native.py'


def plan():
    return dict(mode=c.MODE,limits=c.LIMITS,case=dict(seed=c.CASE[0],scenario=c.CASE[1]),
        execution_activated=False,official_model_processes=0,official_inferences=0,
        native_host='ephemeral GitHub Actions only',private_task_state='UNKNOWN',
        heavy_modules_loaded=sorted(n for n in sys.modules if n.split('.')[0] in
            ('numpy','cv2','panda3d','direct','metadrive','onnxruntime','carla')),
        scope='One independent instrumented official-model case on ephemeral CI only. Plan is inert; no native/model activity here.')


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True,timeout=30).strip()


def git_bytes(args,limit):
    import tempfile
    with tempfile.TemporaryFile() as errors:
        proc=subprocess.Popen(['git',*args],cwd=ROOT,stdout=subprocess.PIPE,stderr=errors)
        try:
            raw=proc.stdout.read(limit+1)
            need(len(raw)<=limit,'bounded Git output required before allocation')
            need(proc.wait(timeout=30)==0,'immutable Git object read failed')
            return raw
        finally:
            if proc.poll() is None:proc.kill();proc.wait(timeout=10)
            proc.stdout.close()


def source_manifest(source):
    need(isinstance(source,str) and len(source)==40 and all(v in '0123456789abcdef' for v in source),'source SHA required before Git allocation')
    raw=git_bytes(['ls-tree','-r','-l','-z',source],4*1024**2)
    rows=raw.split(b'\0');need(len(rows)<=20001,'bounded tracked source namespace required')
    selected=[]
    for row in rows:
        if not row:continue
        metadata,name=row.split(b'\t',1);mode,kind,oid,extent=metadata.split()
        name=name.decode('utf-8')
        if not ((name.startswith(('bigbench/','scripts/')) and name.endswith('.py')) or
            name.startswith(('model_specs/','.github/workflows/')) or name in (c.QUALIFIED_PROBE,c.RUNTIME) or
            name in ('pyproject.toml','setup.py','setup.cfg','uv.lock') or name.startswith('requirements') and name.endswith(('.txt','.in'))):continue
        need(mode==b'100644' or mode==b'100755','regular runnable Git source required')
        need(kind==b'blob' and extent.isdigit() and int(extent)<=16*1024**2 and len(selected)<4096,'bounded source blobs required before read')
        selected.append((name,oid.decode(),int(extent)))
    need(c.WORKFLOW in {n for n,_,_ in selected} and 'bigbench/recorded_official_execution.py' in {n for n,_,_ in selected},'new canary source closure required')
    result={}
    for name,oid,extent in selected:
        raw=git_bytes(['cat-file','blob',oid],extent)
        need(len(raw)==extent,'immutable source blob extent required');result[name]=hashlib.sha256(raw).hexdigest()
    return result


def validate_request(request):
    need(request.get('schema')=='recorded-official-request-v1' and
         request.get('active') is True and request.get('mode')==c.MODE and
         json.dumps(request.get('limits'),sort_keys=True)==json.dumps(c.LIMITS,sort_keys=True) and
         request.get('case')==dict(seed=c.CASE[0],scenario=c.CASE[1]) and
         isinstance(request.get('source'),str) and len(request['source'])==40 and
         all(v in '0123456789abcdef' for v in request['source']) and
         all(type(request.get(k)) is int and request[k]>0 for k in ('push_ci','pr_ci')) and
         isinstance(request.get('aux_ci'),dict) and set(request['aux_ci'])=={'windows_push','windows_pr','software_api_pr'} and
         all(type(v) is int and v>0 for v in request['aux_ci'].values()),
         'sealed active one-model request required')


def _run_identity(value):
    keys=('id','workflow_id','path','head_sha','head_branch','event','run_attempt')
    return {k:value.get(k) for k in keys}|dict(repository=value.get('head_repository',{}).get('full_name'))


def validate_authority(request,manifest,authority):
    need(isinstance(authority,dict),'independent reviewed-source authority required')
    ref=authority.get('ref',{});commit=authority.get('commit',{});doc=authority.get('document',{})
    sha=request.get('approval_sha')
    need(isinstance(sha,str) and len(sha)==40 and all(v in '0123456789abcdef' for v in sha) and
         ref.get('ref')=='refs/heads/'+c.APPROVAL_BRANCH and ref.get('object',{}).get('sha')==sha and
         ref['object'].get('type')=='commit' and commit.get('sha')==sha and
         [p.get('sha') for p in commit.get('parents',[])]==[request['source']] and
         [(f.get('filename'),f.get('status')) for f in commit.get('files',[])]==[(c.APPROVAL_PATH,'added')],
         'immutable separate approval commit must have the reviewed source as sole parent')
    need(doc==dict(schema='recorded-official-reviewed-source-approval-v1',source=request['source'],
         source_map=manifest,push_ci=request['push_ci'],pr_ci=request['pr_ci'],request_path=c.REQUEST,
         mode=c.MODE,limits=c.LIMITS,aux_ci=request['aux_ci']),'request must equal the independent source approval')


def validate_admission(request,context,*,manifest,ci,authority=None,current=None,history=None):
    validate_request(request)
    source=request['source']
    need(context.get('attempt')==1 and type(context.get('attempt')) is int and context.get('event')=='push' and
         context.get('branch')==c.BRANCH and context.get('env_head')==context.get('head') and
         context.get('parents')==[source] and context.get('delta')==['M\t'+c.REQUEST] and
         isinstance(context.get('head'),str) and len(context['head'])==40 and context['head']!=source and
         context.get('repository')=='rownlvh8875-coder/big-model-closed-loop-benchmark' and
         str(context.get('run_id','')).isdecimal(), 'exact fresh request-only activation required before staging')
    need(request.get('source_map')==manifest and isinstance(manifest,dict) and manifest,
         'full immutable source closure required before staging')
    validate_authority(request,manifest,authority)
    need(isinstance(current,dict) and isinstance(history,dict),'current workflow API authentication required')
    identity=_run_identity(current) if 'head_repository' in current else current
    need(type(identity.get('id')) is int and str(identity['id'])==str(context['run_id']) and
         type(identity.get('workflow_id')) is int and identity['workflow_id']>0 and
         identity.get('path')==c.WORKFLOW and identity.get('head_sha')==context['head'] and
         identity.get('head_branch')==c.BRANCH and identity.get('event')=='push' and
         type(identity.get('run_attempt')) is int and identity['run_attempt']==1 and
         identity.get('repository')==context['repository'], 'actual current run/workflow/repository identity required')
    identities=[_run_identity(v) if 'head_repository' in v else v for v in history.get('workflow_runs',[])]
    need(history.get('total_count')==len(identities)==1 and identities==[identity],
         'one-shot request already consumed or concurrent activations present')
    need(isinstance(ci,dict) and set(ci)=={'push','pull_request','windows_push','windows_pr','software_api_pr'},'complete retained canonical source CI required')
    for event in ('push','pull_request'):
        value=ci[event];run=value['run'];jobs=value['jobs'];artifacts=value['artifacts']
        need(run.get('id')==request['push_ci' if event=='push' else 'pr_ci'] and
             run.get('head_sha')==source and run.get('head_branch')==FEATURE and run.get('event')==event and
             run.get('workflow_id')==411705464 and run.get('run_attempt')==1 and run.get('conclusion')=='success' and
             run.get('status')=='completed' and run.get('head_repository',{}).get('full_name')==context['repository'] and
             jobs.get('total_count')==len(jobs.get('jobs',[]))==2 and
             {j.get('name') for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and
             all(j.get('conclusion')=='success' and j.get('status')=='completed' for j in jobs['jobs']) and
             artifacts.get('total_count')==0 and artifacts.get('artifacts')==[], 'four exact canonical source CI jobs required')
    for role,workflow,event in (('windows_push',421897387,'push'),('windows_pr',421897387,'pull_request'),('software_api_pr',422015100,'pull_request')):
        value=ci[role];run=value['run'];jobs=value['jobs']
        need(run.get('id')==request['aux_ci'][role] and run.get('head_sha')==source and run.get('head_branch')==FEATURE and
             run.get('event')==event and run.get('workflow_id')==workflow and type(run.get('run_attempt')) is int and run['run_attempt']==1 and
             run.get('conclusion')=='success' and run.get('status')=='completed' and run.get('head_repository',{}).get('full_name')==context['repository'] and
             jobs.get('total_count')==len(jobs.get('jobs',[]))==1 and all(j.get('status')=='completed' and j.get('conclusion')=='success' for j in jobs['jobs']),
             'all seven exact reviewed-source CI jobs required')
    return dict(request=request,source=source,activation=context['head'],run_id=str(context['run_id']),
        branch=c.BRANCH,event='push',attempt=1,source_ci=ci,context=context,authority=authority,
        current_identity=identity,history=dict(total_count=1,workflow_runs=identities))


def fetch_authority(request):
    from scripts import panda_sdk3_runtime as pins
    ref=pins.api('git/ref/heads/'+c.APPROVAL_BRANCH)
    sha=request['approval_sha']
    need(ref.get('object',{}).get('sha')==sha,'request must name the separate current approval')
    commit=pins.api('commits/'+sha)
    contents=pins.api('contents/'+c.APPROVAL_PATH+'?ref='+sha)
    need(contents.get('type')=='file' and contents.get('encoding')=='base64' and
         type(contents.get('size')) is int and 0<contents['size']<=1024**2 and
         isinstance(contents.get('content'),str) and len(contents['content'])<=2*1024**2,'bounded approval document required')
    raw=base64.b64decode(contents['content'])
    need(len(raw)==contents['size'] and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==contents.get('sha'),
         'immutable approval Git blob bytes required')
    from bigbench.full_s_failure_capture import _decode
    return dict(ref=ref,commit=commit,document=_decode(raw))


def authenticate_request(bundle,*,name='authentication.json'):
    from scripts import panda_sdk3_runtime as pins
    request=_read_receipt(ROOT/c.REQUEST,4*1024**2)
    validate_request(request)
    # Local/event checks before any network, staging, native code or Docker.
    head=git('rev-parse','HEAD')
    context=dict(attempt=int(os.environ.get('GITHUB_RUN_ATTEMPT','0')),event=os.environ.get('GITHUB_EVENT_NAME'),
        branch=os.environ.get('GITHUB_REF_NAME'),env_head=os.environ.get('GITHUB_SHA'),head=head,
        parents=git('show','-s','--format=%P',head).split(),delta=git('diff','--name-status',request['source'],head).splitlines(),
        repository=os.environ.get('GITHUB_REPOSITORY'),run_id=os.environ.get('GITHUB_RUN_ID'))
    need(context['attempt']==1 and context['event']=='push' and context['branch']==c.BRANCH and
        context['env_head']==head and context['parents']==[request['source']] and
        context['delta']==['M\t'+c.REQUEST] and context['repository']==pins.REPO and
        str(context['run_id']).isdecimal() and not git('status','--porcelain','--untracked-files=no'),
        'fresh immutable activation required before network/staging')
    manifest=source_manifest(request['source'])
    c.check_source_map(ROOT,manifest)
    authority=fetch_authority(request)
    current=pins.api('actions/runs/'+context['run_id'])
    workflow=pins.api('actions/workflows/recorded-official.yml')
    need(current.get('workflow_id')==workflow.get('id') and workflow.get('path')==c.WORKFLOW and
         workflow.get('state')=='active','current registered canary workflow required')
    history=pins.api('actions/workflows/'+str(workflow['id'])+'/runs?branch='+c.BRANCH+'&event=push&per_page=100')
    ci={}
    for event,key in (('push','push_ci'),('pull_request','pr_ci')):
        prefix='actions/runs/'+str(request[key])
        ci[event]=dict(run=pins.api(prefix),jobs=pins.api(prefix+'/jobs'),artifacts=pins.api(prefix+'/artifacts'))
    for role,run_id in request['aux_ci'].items():
        prefix='actions/runs/'+str(run_id)
        ci[role]=dict(run=pins.api(prefix),jobs=pins.api(prefix+'/jobs'),artifacts=pins.api(prefix+'/artifacts'))
    auth=validate_admission(request,context,manifest=manifest,ci=ci,authority=authority,current=current,history=history)
    _write_receipt(bundle/name,auth)
    return auth


def refresh_admission(bundle,label,original):
    fresh=authenticate_request(bundle,name='authentication-'+label+'.json')
    keys=('request','source','activation','run_id','branch','event','attempt','context','current_identity','history')
    need(all(fresh[k]==original[k] for k in keys),'same immutable authority/current activation required after staging')
    public_activity(bundle,label,fresh['run_id'])
    return fresh


def official_command(name,repo,sdk,out,args,*,owner,model=None,deps=None):
    need(model is not None and deps is not None,'exact official model and dependency mounts required')
    from scripts import sdk3_four_validation_runtime as runtime
    command=runtime.native_command(name,repo,sdk,out,args,owner=owner,model=model,deps=deps)
    command[command.index(runtime.ENTRY)]=ENTRY
    return command


class DeadlineProcess:
    @staticmethod
    def run(argv,**kwargs):
        if argv[:3]==['docker','start','--attach']:
            need(kwargs.get('timeout')==18180,'original model attach deadline required before scoped override')
            kwargs['timeout']=c.LIMITS['container_seconds']
        return subprocess.run(argv,**kwargs)


def public_activity(bundle,label,current_id,*,require_current=True):
    from scripts import panda_sdk3_runtime as pins
    pages=[]
    for number in range(1,101):
        value=pins.api('actions/runs?per_page=100&page='+str(number))
        pages.append(dict(total_count=value.get('total_count'),workflow_runs=[
            {k:r.get(k) for k in ('id','workflow_id','status','head_sha','head_branch','run_attempt','event')} for r in value.get('workflow_runs',[])]))
        if len(value.get('workflow_runs',[]))<100:break
    _write_receipt(bundle/('public-activity-'+label+'.json'),dict(pages=pages))
    result=c.validate_public_activity(pages,current_id=int(current_id),require_current=require_current)
    _write_receipt(bundle/('public-activity-'+label+'-verdict.json'),result)
    return result


def retain_runner_evidence(out,quarantine):
    """Unresolved handoff: preserve readable runner-owned receipts, follow no links."""
    import shutil
    import stat
    out=Path(out);quarantine=Path(quarantine)
    need(out.is_dir() and not out.is_symlink() and out.stat().st_uid==os.getuid() and not quarantine.exists(),
         'fresh runner-owned partial snapshot required')
    moved=quarantine
    out.rename(moved);out.mkdir()
    retained=[]
    with os.scandir(moved) as scan:
        for count,entry in enumerate(scan):
            need(count<512,'bounded partial runner evidence namespace required')
            info=entry.stat(follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_size>16*1024**2:continue
            source=Path(entry.path)
            with source.open('rb') as stream:
                raw=stream.read(16*1024**2+1)
            need(len(raw)==info.st_size,'stable partial runner file required')
            (out/entry.name).write_bytes(raw);retained.append(entry.name)
    return dict(protocol='recorded-official-readable-partial-v1',retained=retained,
        original_directory_moved_outside_artifact=True,unsafe_ownership_handoff_attempted=False,
        official_model_process_bounds=[0,1],official_inference_bounds=[0,600])


def failure_detail(bundle,execution,verdict=None):
    if verdict and verdict.get('body',{}):
        value=verdict['body'].get('primary_error')
        if value:return value
    for name,key in (('observed-trial/recorded-trial.json','primary_error'),('report.json','failure')):
        try:
            value=_read_receipt(bundle/'native'/name,4*1024**2).get(key)
            if isinstance(value,str) and value:return value
        except (OSError,ValueError):pass
    return execution.get('failure') or 'Native diagnostic incomplete; see retained receipts'


def run():
    need(sys.platform=='linux','ephemeral Linux Actions runtime required')
    root=ROOT/'output/recorded-official-20261118-01'
    need(not root.exists(),'fresh single official diagnostic output required')
    work=root/'work';bundle=root/'bundle'
    work.mkdir(parents=True);bundle.mkdir()
    summary=dict(protocol='recorded-official-host-v1',status='FAILED',mode=c.MODE,
        official_model_process_bounds=[0,1],official_inference_bounds=[0,600],
        private_task_state='UNKNOWN',**{k:False for k in c.FALSE_FLAGS})
    primary=None
    secondary=summary.setdefault('secondary_errors',[])
    try:
        auth=authenticate_request(bundle)
        public_activity(bundle,'before-staging',auth['run_id'])
        from scripts.run_sdk3_four_validation import stage_runtime
        from scripts import sdk3_four_validation_runtime as runtime, panda_sdk3_runtime as pins
        from bigbench import recorded_official_dependencies as dependencies
        sdk=stage_runtime(work,bundle)
        deps,descriptor=dependencies.stage(work)
        _write_receipt(bundle/'model-dependencies.json',descriptor)
        dep_sha=hashlib.sha256(_read_bytes(bundle/'model-dependencies.json')).hexdigest()
        from bigbench.model_inventory import download_checked
        auth=refresh_admission(bundle,'before-model',auth)
        model=download_checked(path=pins.MODEL_ID,sha256=pins.MODEL_SHA,output_dir=work/'models',max_bytes=900000000)
        need(model.stat().st_size==768750198,'official model extent required')
        auth=refresh_admission(bundle,'before-container',auth)
        def mounted_command(name,repo,sdk,out,args,**kwargs):
            import shutil
            shutil.copyfile(bundle/'model-dependencies.json',out/'model-dependencies.json')
            return official_command(name,repo,sdk,out,args,**kwargs)
        execution=c.clone(runtime.run_container,container_command=mounted_command,subprocess=DeadlineProcess)(
            'recorded-official-'+auth['run_id'],sdk,bundle/'native',
            ['--source',auth['source'],'--activation',auth['activation'],'--run-id',auth['run_id'],
             '--approval',auth['request']['approval_sha'],'--dependencies-sha256',dep_sha],model=model,deps=deps)
        summary['execution']=execution
        from scripts.run_recorded_worker_canary import handoff_evidence
        summary['primary_error']=failure_detail(bundle,execution) if execution.get('returncode')!=0 or execution.get('failure') else None
        try:
            _write_receipt(bundle/'evidence-handoff.json',handoff_evidence(bundle/'native',execution))
        except BaseException as exc:
            secondary.append(type(exc).__name__+': '+str(exc)[:2048])
            _write_receipt(bundle/'readable-partial.json',retain_runner_evidence(bundle/'native',work/'unhanded-native'))
        verdict=c.validate_native_bundle(bundle)
        _write_receipt(bundle/'receiver.json',verdict)
        summary.update(status=verdict['status'],source=auth['source'],activation=auth['activation'],run_id=auth['run_id'],
            official_model_process_bounds=verdict['official_model_process_bounds'],official_inference_bounds=verdict['official_inference_bounds'])
        if execution.get('returncode')!=0 or execution.get('failure') is not None or verdict['status']!='COMPLETE_DIAGNOSTIC':
            summary['primary_error']=failure_detail(bundle,execution,verdict)
            raise RuntimeError(summary['primary_error'])
        return 0
    except BaseException as exc:
        primary=exc
        summary['failure']=summary.get('primary_error') or type(exc).__name__+': '+str(exc)[:2048]
        raise
    finally:
        c.finalize_preserving_primary(primary,[lambda:_write_receipt(bundle/'summary.json',summary)],secondary)


def _read_bytes(path):
    from bigbench.full_s_recorded_worker import _receipt_bytes
    return _receipt_bytes(path,4*1024**2)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('plan')
    sub.add_parser('run')
    verify=sub.add_parser('verify');verify.add_argument('--bundle',required=True,type=Path)
    args=parser.parse_args(argv)
    if args.command=='plan':print(json.dumps(plan(),indent=2));return 0
    if args.command=='run':return run()
    print(json.dumps(c.validate_native_bundle(args.bundle),indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
