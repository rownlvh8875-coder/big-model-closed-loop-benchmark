"""Bounded retained-host lease and successful metadata polling, no import actions."""
import base64
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import time
from scripts import engine_clock_held_abba_v3 as n


def boot_identity():
    with open('/proc/sys/kernel/random/boot_id','rb') as f:raw=f.read(65)
    n.need(re.fullmatch(rb'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\n',raw) is not None)
    return raw


def create_lease(context,boot,now):
    n.need(type(now) in (float,int) and math.isfinite(now) and now>=0)
    n.need(re.fullmatch(rb'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\n',boot) is not None)
    return dict(schema='engine-clock-retained-host-lease-v1',producer_head_sha=context['head_sha'],
        source_sha=context['source_sha'],run_id=context['run_id'],workflow_id=context['workflow_id'],
        host_job_id=context['job_id'],nonce=secrets.token_hex(32),boot_sha256=n.sha(boot),
        started_monotonic=float(now),deadline_monotonic=float(now)+n.LIFECYCLE['total_seconds'])


def validate_lease(value,context,boot,now):
    n.need(type(value) is dict and set(value)=={'schema','producer_head_sha','source_sha','run_id',
        'workflow_id','host_job_id','nonce','boot_sha256','started_monotonic','deadline_monotonic'})
    n.need(value['schema']=='engine-clock-retained-host-lease-v1'
        and value['producer_head_sha']==context['head_sha']==context.get('producer_head_sha',context['head_sha'])
        and value['source_sha']==context['source_sha'] and value['run_id']==context['run_id']
        and value['workflow_id']==context['workflow_id'] and value['host_job_id']==context['job_id']
        and n.image._hex(value['nonce']) and value['boot_sha256']==n.sha(boot)
        and all(type(value[k]) is int and value[k]>0 for k in ('run_id','workflow_id','host_job_id'))
        and type(now) in (int,float) and math.isfinite(now))
    start=value['started_monotonic'];stop=value['deadline_monotonic']
    n.need(type(start) is float and type(stop) is float and math.isfinite(start) and math.isfinite(stop)
        and start<=now<stop and math.isclose(stop-start,n.LIFECYCLE['total_seconds'],rel_tol=0,abs_tol=1e-6))
    return value


def write_lease(path,value):
    path=Path(path);n.need(not path.exists() and not path.is_symlink())
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write(n.canonical(value))
    path.chmod(0o600)


def read_lease(path):
    path=Path(path);n.need(not path.is_symlink())
    try:raw=n.image.read_regular(path,65536)
    except OSError:raise ValueError('HELD_LEASE_REJECTED') from None
    s=path.stat()
    n.need(s.st_uid==os.geteuid() and s.st_mode&0o777==0o600)
    return n.image.parse(raw)


def bounded_poll(fetch,ready,record,*,clock=time.monotonic,pause=time.sleep,seconds=900,maximum=181,deadline=None):
    n.need(type(maximum) is int and 0<maximum<=181 and type(seconds) in (int,float) and 0<seconds<=900)
    stop=min(clock()+seconds,deadline) if deadline is not None else clock()+seconds
    for index in range(maximum):
        n.need(clock()<stop)
        value=fetch()  # Errors propagate immediately; no HTTP retry.
        record(index,value)
        n.need(clock()<stop)
        if ready(value):return value
        if index+1<maximum:
            left=stop-clock();n.need(left>0);pause(min(5,left))
    n.need(False)


def observe_running(client,context,*,clock=time.monotonic,pause=time.sleep):
    """Only an authenticated active original response can leave this boundary."""
    original=client.deadline;started=clock()
    stop=min(original,started+n.LIFECYCLE['run_visibility_seconds']);client.deadline=stop
    counter=[0];names=[];workflow_id=[None];queued=[0]
    def fetch():
        name='live-run-%02d.json'%counter[0];names.append(name)
        return client.get_json('actions/runs/'+str(context['run_id']),name)
    def record(index,value):counter[0]=index+1
    def ready(value):
        n.need(type(value) is dict and value['id']==context['run_id']
            and value['head_sha']==context['head_sha'] and value['head_branch']==n.BRANCH
            and value['event']=='push' and n.exact(value['run_attempt'],1)
            and value['path']==n.WORKFLOW and value['repository']['full_name']==n.REPOSITORY
            and type(value['workflow_id']) is int and value['workflow_id']>0
            and value['status'] in ('queued','in_progress') and value['conclusion'] is None)
        if workflow_id[0] is None:workflow_id[0]=value['workflow_id']
        n.need(value['workflow_id']==workflow_id[0])
        if value['status']=='queued':queued[0]+=1;return False
        return True
    try:
        value=bounded_poll(fetch,ready,record,clock=clock,pause=pause,
            seconds=n.LIFECYCLE['run_visibility_seconds'],maximum=n.LIFECYCLE['run_visibility_snapshots'],deadline=stop)
        # Exact selected response bytes, not a relabeled or canonicalized snapshot.
        raw=n.image.read_regular(client.out/names[-1]);n.need(n.exact(n.image.parse(raw),value))
        with (client.out/'live-run.json').open('xb') as stream:stream.write(raw)
        return value,dict(status='ACTUAL_RUNNING_RUN_OBSERVED',snapshots=len(names),queued_snapshots=queued[0],
            elapsed_seconds=clock()-started,maximum_seconds=60,maximum_snapshots=13,interval_seconds=5,
            original_snapshot_paths=names,selected_original_snapshot=names[-1],selected_original_sha256=n.sha(raw))
    finally:client.deadline=original


def find_job(client,context,name,prefix,*,clock=time.monotonic,pause=time.sleep):
    def fetch():return client.get_json('actions/runs/'+str(context['run_id'])+'/jobs?per_page=100',prefix+'-%03d.json'%counter[0])
    counter=[0]
    def record(index,value):counter[0]=index+1
    def ready(value):
        n.need(type(value['jobs']) is list and value['total_count']==len(value['jobs'])<=2)
        names=[j['name'] for j in value['jobs']]
        n.need(len(names)==len(set(names)) and set(names)<={'native-host','canary-attestor'})
        rows=[j for j in value['jobs'] if j['name']==name]
        if not rows:return False
        job=rows[0]
        n.need(job['run_id']==context['run_id'] and job['head_sha']==context['head_sha'] and n.exact(job['run_attempt'],1)
            and job['status'] in ('queued','in_progress') and job['conclusion'] is None)
        return job['status']=='in_progress'
    original=client.deadline;stop=min(original,clock()+n.LIFECYCLE['caller_visibility_seconds']);client.deadline=stop
    try:value=bounded_poll(fetch,ready,record,clock=clock,pause=pause,seconds=30,maximum=7,deadline=stop)
    finally:client.deadline=original
    return next(j for j in value['jobs'] if j['name']==name)


def observe_control(client,producer,context,lease,out):
    out=Path(out);counter=[0]
    def fetch():
        if counter[0]%6==0:
            jobs=client.get_json('actions/runs/'+str(context['run_id'])+'/jobs?per_page=100','control-peer-jobs-%03d.json'%counter[0])
            for job in jobs['jobs']:
                n.need(job['name'] in ('native-host','canary-attestor') and job['run_id']==context['run_id']
                    and job['head_sha']==context['head_sha'] and n.exact(job['run_attempt'],1))
                if job['name']=='canary-attestor' and job['status']=='completed':n.need(job['conclusion']=='success')
        return client.get_json('git/ref/heads/'+n.BRANCH,'control-ref-%03d.json'%counter[0])
    def record(index,value):counter[0]=index+1
    def ready(value):
        n.need(value['ref']=='refs/heads/'+n.BRANCH and value['object']['type']=='commit' and n.image._hex(value['object']['sha'],40))
        return value['object']['sha']!=context['head_sha']
    head=bounded_poll(fetch,ready,record,seconds=n.LIFECYCLE['control_seconds'],maximum=n.LIFECYCLE['control_snapshots'],
        deadline=min(client.deadline,lease['deadline_monotonic']-n.BUDGET['cleanup_seconds']))['object']['sha']
    commit=client.get_json('git/commits/'+head,'control-commit.json')
    compare=client.get_json('compare/'+context['head_sha']+'...'+head,'control-compare.json')
    content=client.get_json('contents/'+n.A_REQUEST+'?ref='+head,'control-content.json')
    n.need(content['type']=='file' and content['path']==n.A_REQUEST and content['encoding']=='base64')
    raw=base64.b64decode(content['content'],validate=False)
    n.need(len(raw)<=128*1024);effective=n.validate_request(n.image.parse(raw),Path(__file__).resolve().parents[1])
    n.validate_control_delta(producer,effective,head,commit,compare,content['sha'],raw)
    tree=client.get_json('git/trees/'+commit['tree']['sha']+'?recursive=1','control-tree.json')
    n.validate_control_tree(tree,commit['tree']['sha'],content['sha'])
    n.need(effective['acceptance']['canary_head_sha']==context['head_sha'])
    (out/'control-request.json').write_bytes(raw)
    return head,effective,raw


def authenticate_producer(client,root,environment,job_name):
    """Read-only actual Ccheckout/run/source auth, shared by both jobs and phases."""
    root=Path(root)
    n.need(job_name in ('native-host','canary-attestor') and environment.get('GITHUB_JOB')==job_name
        and environment.get('GITHUB_ACTIONS')=='true' and environment.get('GITHUB_EVENT_NAME')=='push'
        and environment.get('GITHUB_REPOSITORY')==n.REPOSITORY and environment.get('GITHUB_REF_NAME')==n.BRANCH
        and environment.get('GITHUB_RUN_ATTEMPT')=='1')
    def git(*args):
        r=subprocess.run(['git','-C',str(root),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
        n.need(r.returncode==0 and len(r.stdout)<=16*n.MIB);return r.stdout
    head=git('rev-parse','HEAD').decode().strip();n.need(head==environment['GITHUB_SHA'])
    n.need(not git('status','--porcelain','--untracked-files=no'))
    raw=n.image.read_regular(root/n.C_REQUEST);producer=n.validate_request(n.image.parse(raw),root)
    n.need(producer['mode']=='canary' and n.canonical(producer)==raw and raw==git('show',head+':'+n.C_REQUEST))
    parents=[r[7:].decode() for r in git('cat-file','-p',head).split(b'\n\n',1)[0].splitlines() if r.startswith(b'parent ')]
    mode=git('ls-tree',head,'--',n.C_REQUEST).decode().split()[0]
    n.validate_activation(producer,head,parents,git('diff-tree','--no-commit-id','--name-status','-r','-z',head),mode,n.BRANCH)
    n.verify_sources(root,producer['source_closure'])
    ctx=dict(repository=n.REPOSITORY,event='push',attempt=1,run_id=int(environment['GITHUB_RUN_ID']),head_sha=head)
    run,run_visibility=observe_running(client,ctx);wid=run['workflow_id']
    workflow=client.get_json('actions/workflows/'+str(wid),'live-workflow.json')
    unique,visibility=n.image.observe_unique(client,'actions/workflows/'+str(wid)+'/runs?branch='+n.BRANCH+'&event=push&per_page=100')
    n.validate_live(producer,ctx,run,workflow,unique)
    commit=client.get_json('git/commits/'+head,'producer-activation-commit.json')
    source=producer['reviewed_source_sha']
    n.need(commit['sha']==head and [p['sha'] for p in commit['parents']]==[source]
        and commit['tree']['sha']==git('rev-parse','HEAD^{tree}').decode().strip())
    compare=client.get_json('compare/'+source+'...'+head,'producer-activation-compare.json')
    n.need(compare['status']=='ahead' and compare['ahead_by']==1 and compare['behind_by']==0
        and compare['total_commits']==1 and compare['base_commit']['sha']==compare['merge_base_commit']['sha']==source
        and len(compare['commits'])==1 and compare['commits'][0]['sha']==head and len(compare['files'])==1
        and compare['files'][0]['filename']==n.C_REQUEST and compare['files'][0]['status']=='added')
    proofs=[]
    for item in producer['source_ci']:
        rid=str(item['run_id']);prefix='source-'+item['event']
        proofs.append({key:client.get_json(endpoint,prefix+'-'+key+'.json') for key,endpoint in
            [('run','actions/runs/'+rid),('jobs','actions/runs/'+rid+'/jobs?per_page=100'),('artifacts','actions/runs/'+rid+'/artifacts?per_page=100')]})
    n.validate_source_ci(producer,proofs)
    job=find_job(client,ctx,job_name,'caller-job')
    n.need(job['status']=='in_progress' and job['conclusion'] is None)
    ctx.update(workflow_id=wid,job_id=job['id'],producer_head_sha=head,control_head_sha=head,
        source_sha=source,request_sha256=n.sha(raw),producer_request_sha256=n.sha(raw),mode='canary',
        source_closure_verified=True,authenticated_api_origin='https://api.github.com',workflow_visibility=visibility,
        run_status_visibility=run_visibility)
    return producer,raw,ctx
