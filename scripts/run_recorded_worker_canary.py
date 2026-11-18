"""Authenticate and run one zero-model camera/recorder canary on ephemeral CI."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigbench import recorded_worker_canary as c
from bigbench.full_s_recorded_worker import need,_read_receipt,_write_receipt

ROOT=Path(__file__).resolve().parents[1]
FEATURE='feature/recorded-worker-canary-v1'
ENTRY='/work/repo/scripts/recorded_worker_canary_native.py'


def plan():
    return dict(mode=c.MODE,limits=c.LIMITS,case=dict(seed=c.CASE[0],scenario=c.CASE[1]),
        execution_activated=False,official_model_processes=0,official_inferences=0,
        native_host='ephemeral GitHub Actions only',private_task_state='UNKNOWN',
        heavy_modules_loaded=sorted(n for n in sys.modules if n.split('.')[0] in
            ('numpy','cv2','panda3d','direct','metadrive','onnxruntime','carla')),
        scope='Real camera/recorder plumbing with synthetic policy data. No graph feed or full-S qualification.')


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True,timeout=30).strip()


def source_manifest(source):
    names=git('ls-tree','-r','--name-only',source).splitlines()
    selected=[name for name in names if
        (name.startswith(('bigbench/','scripts/')) and name.endswith('.py')) or
        name.startswith(('model_specs/','.github/workflows/')) or
        name in ('pyproject.toml','setup.py','setup.cfg','uv.lock') or
        name.startswith('requirements') and name.endswith(('.txt','.in'))]
    need(c.WORKFLOW in selected and 'bigbench/recorded_worker_canary.py' in selected,
        'new canary source closure required')
    return {name:hashlib.sha256(subprocess.check_output(['git','show',source+':'+name],cwd=ROOT,timeout=30)).hexdigest()
            for name in selected}


def validate_request(request):
    need(request.get('schema')=='recorded-worker-camera-canary-request-v1' and
         request.get('active') is True and request.get('mode')==c.MODE and
         json.dumps(request.get('limits'),sort_keys=True)==json.dumps(c.LIMITS,sort_keys=True) and
         request.get('case')==dict(seed=c.CASE[0],scenario=c.CASE[1]) and
         isinstance(request.get('source'),str) and len(request['source'])==40 and
         all(v in '0123456789abcdef' for v in request['source']) and
         all(type(request.get(k)) is int and request[k]>0 for k in ('push_ci','pr_ci')),
         'sealed active zero-model request required')


def validate_admission(request,context,*,manifest,ci):
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
    return dict(request=request,source=source,activation=context['head'],run_id=str(context['run_id']),
        branch=c.BRANCH,event='push',attempt=1,source_ci=ci)


def authenticate_request(bundle):
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
    ci={}
    for event,key in (('push','push_ci'),('pull_request','pr_ci')):
        prefix='actions/runs/'+str(request[key])
        ci[event]=dict(run=pins.api(prefix),jobs=pins.api(prefix+'/jobs'),artifacts=pins.api(prefix+'/artifacts'))
    auth=validate_admission(request,context,manifest=manifest,ci=ci)
    _write_receipt(bundle/'authentication.json',auth)
    return auth


def canary_command(name,repo,sdk,out,args,*,owner,model=None,deps=None):
    need(model is None and deps is None,'camera canary forbids graph/dependency mounts')
    from scripts import sdk3_four_validation_runtime as runtime
    command=runtime.native_command(name,repo,sdk,out,args,owner=owner,model=None,deps=None)
    command[command.index(runtime.ENTRY)]=ENTRY
    return command


def run():
    need(sys.platform=='linux','ephemeral Linux Actions runtime required')
    root=ROOT/'output/recorded-worker-canary-20261118-01'
    need(not root.exists(),'fresh single canary output required')
    work=root/'work';bundle=root/'bundle'
    work.mkdir(parents=True);bundle.mkdir()
    summary=dict(protocol='recorded-camera-canary-host-v1',status='FAILED',mode=c.MODE,
        official_model_processes=0,official_inferences=0,capture_count_bounds=[0,2],
        sensor_perceive_bounds=[0,4],private_task_state='UNKNOWN',**{k:False for k in c.FALSE_FLAGS})
    try:
        auth=authenticate_request(bundle)
        from scripts.run_sdk3_four_validation import stage_runtime
        from scripts import sdk3_four_validation_runtime as runtime
        from scripts.sdk3_priority_model_trial import clone
        sdk=stage_runtime(work,bundle)
        execution=clone(runtime.run_container,container_command=canary_command)(
            'recorded-camera-canary-'+auth['run_id'],sdk,bundle/'native',
            ['--source',auth['source'],'--activation',auth['activation'],'--run-id',auth['run_id']])
        summary['execution']=execution
        verdict=c.validate_native_bundle(bundle)
        _write_receipt(bundle/'receiver.json',verdict)
        summary.update(status='CAMERA_RECORDER_CANARY_PASS',capture_count_bounds=[2,2],sensor_perceive_bounds=[4,4],
            fixture_policy_audit_bounds=[2,2],source=auth['source'],activation=auth['activation'],run_id=auth['run_id'])
        return 0
    except BaseException as exc:
        summary['failure']=type(exc).__name__+': '+str(exc)[:2048]
        raise
    finally:
        _write_receipt(bundle/'summary.json',summary)


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
