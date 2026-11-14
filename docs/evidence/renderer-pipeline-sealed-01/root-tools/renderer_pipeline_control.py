import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path('/workspace/big-model-closed-loop-benchmark');sys.path.insert(0,str(ROOT))
from scripts import renderer_pipeline_sealed_v1 as n
SOURCE='09ad7e3272713ec86031ab8158e3f9fdf0cf245d'
BASE=ROOT/'output/stage7-renderer-pipeline-sealed-01'
PREFIX='repos/'+n.REPOSITORY+'/'

def run(*args):return subprocess.check_output(list(args),cwd=ROOT,text=True).strip()
def api(path):
    for i in range(3):
        p=subprocess.run(['gh','api',PREFIX+path],cwd=ROOT,capture_output=True,text=True,timeout=90)
        if p.returncode==0:return json.loads(p.stdout)
        if not any(x in p.stderr for x in ('HTTP 502','HTTP 503','HTTP 504')) or i==2:raise RuntimeError(p.stderr[:500])
        time.sleep(2)
def write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(n.canonical(data))
def read(path):return json.loads(Path(path).read_bytes())
def c_request(ci):
    return dict(schema=n.REQUEST_SCHEMA,mode='canary',acceptance=None,request_id=n.ID,repository=n.REPOSITORY,
        branch=n.BRANCH,workflow_path=n.WORKFLOW,reviewed_source_branch=n.SOURCE_BRANCH,reviewed_source_sha=SOURCE,
        source_closure={p:n.sha((ROOT/p).read_bytes()) for p in sorted(n.source_paths(ROOT))},
        source_ci=ci,budget=n.BUDGET,lifecycle=n.LIFECYCLE,native_budget=n.native_budget('canary'),
        image_evidence=n.image_evidence(ROOT),official_model_calls=0,ort_sessions=0)
def qualify():
    assert run('git','rev-parse','HEAD')==SOURCE and run('git','status','--porcelain')==''
    value=api('actions/runs?branch=feature%2Frenderer-pipeline-sealed-v1&per_page=100')
    runs=[r for r in value['workflow_runs'] if r['head_sha']==SOURCE and r['workflow_id']==411705464]
    assert len(runs)==2 and {r['event'] for r in runs}=={'push','pull_request'}
    if any(r['status']!='completed' for r in runs):print(json.dumps(dict(status='SOURCE_CI_PENDING',runs=[{k:r[k] for k in ('id','event','status','conclusion')} for r in runs])));return 2
    ci=[dict(event=e,run_id=next(r['id'] for r in runs if r['event']==e)) for e in ('push','pull_request')]
    proofs=[]
    for c in ci:
        rid=c['run_id'];proof=dict(run=api('actions/runs/'+str(rid)),jobs=api(f'actions/runs/{rid}/jobs'),artifacts=api(f'actions/runs/{rid}/artifacts'))
        proofs.append(proof)
    request=c_request(ci);n.validate_request(request,ROOT);n.validate_source_ci(request,proofs)
    for p,h in request['source_closure'].items():assert n.sha(subprocess.check_output(['git','show',SOURCE+':'+p],cwd=ROOT))==h
    target=BASE/'source/qualified.json';write(target,dict(status='EXACT_SOURCE_CI_QUALIFIED',source_sha=SOURCE,source_ci=ci,proofs=proofs,request=request,source_review_accepted=True,review='C0/I0/M0',full_tests=1285,skips=7,full_seconds=120.713))
    print(json.dumps(dict(status='EXACT_SOURCE_CI_QUALIFIED',source_sha=SOURCE,source_ci=ci,paths=len(request['source_closure']))));return 0
def activate_canary():
    q=read(BASE/'source/qualified.json');r=q['request'];assert q['status']=='EXACT_SOURCE_CI_QUALIFIED'
    assert run('git','rev-parse','HEAD')==SOURCE and run('git','status','--porcelain')==''
    run('git','switch','-c',n.BRANCH);path=ROOT/n.C_REQUEST;write(path,r)
    run('git','add',n.C_REQUEST);run('git','commit','-m','Activate one reviewed sealed renderer pipeline canary')
    head=run('git','rev-parse','HEAD');parents=run('git','rev-list','--parents','-n','1','HEAD').split()[1:]
    changes=subprocess.check_output(['git','diff-tree','--no-commit-id','--name-status','-z','-r','HEAD'],cwd=ROOT)
    n.validate_activation(r,head,parents,changes,'100644',n.BRANCH)
    run('git','push','-u','origin',n.BRANCH)
    write(BASE/'canary-activation.json',dict(head_sha=head,source_sha=SOURCE,request_sha256=n.sha(n.canonical(r)),branch=n.BRANCH))
    print(json.dumps(dict(status='ONE_USE_CANARY_PUSHED',head_sha=head,request_sha256=n.sha(n.canonical(r)))));return 0
def status():
    act=read(BASE/'canary-activation.json');head=act['head_sha']
    obj=api('actions/workflows/renderer-pipeline-sealed-v1.yml/runs?per_page=100')
    items=[r for r in obj['workflow_runs'] if r['head_sha']==head]
    assert len(items)<=1
    if not items:return dict(status='NATIVE_RUN_NOT_VISIBLE',total_count=obj['total_count'])
    r=items[0];assert r['run_attempt']==1 and r['event']=='push' and r['head_branch']==n.BRANCH
    jobs=api(f"actions/runs/{r['id']}/jobs?per_page=100");arts=api(f"actions/runs/{r['id']}/artifacts?per_page=100")
    host=next((j for j in jobs['jobs'] if j['name']=='native-host'),None);att=next((j for j in jobs['jobs'] if j['name']=='canary-attestor'),None)
    def step(name):return next((s for s in host['steps'] if s['name']==name),{}) if host else {}
    ready=bool(host and host['status']=='in_progress' and all(step(k).get('conclusion')=='success' for k in (n.C_STEP,n.C_UPLOAD)) and att and att['status']=='completed' and att['conclusion']=='success')
    return dict(status=r['status'],conclusion=r['conclusion'],run_id=r['id'],workflow_id=r['workflow_id'],host_job_id=host['id'] if host else None,host_status=host['status'] if host else None,
        attestor_status=att['status'] if att else None,attestor_conclusion=att['conclusion'] if att else None,canary_step=step(n.C_STEP),canary_upload=step(n.C_UPLOAD),
        ready_for_root_canary=ready,artifacts=[{k:a[k] for k in ('id','name','size_in_bytes','digest')} for a in arts['artifacts']],run=r,jobs=jobs,artifact_response=arts)
def activate_abba():
    root=read(BASE/'canary/root-acceptance.json');fresh=read(BASE/'canary/fresh-raw-acceptance.json')
    assert root['accepted'] is True and fresh['accepted'] is True and fresh['artifact_sha256']==root['artifact_sha256']
    live=status();assert live['ready_for_root_canary']
    act=read(BASE/'canary-activation.json');assert run('git','rev-parse','HEAD')==act['head_sha'] and run('git','status','--porcelain')==''
    c=next(a for a in live['artifact_response']['artifacts'] if a['name']==n.artifact('canary'))
    att=next(a for a in live['artifact_response']['artifacts'] if a['name']==n.artifact('attestation'))
    attjob=next(j for j in live['jobs']['jobs'] if j['name']=='canary-attestor')
    a=dict(canary_head_sha=act['head_sha'],source_sha=SOURCE,run_id=live['run_id'],workflow_id=live['workflow_id'],job_id=live['host_job_id'],
        artifact_id=c['id'],artifact_name=c['name'],artifact_size_bytes=c['size_in_bytes'],artifact_sha256=c['digest'][7:],
        attestor_job_id=attjob['id'],attestor_artifact_id=att['id'],attestor_artifact_name=att['name'],attestor_artifact_size_bytes=att['size_in_bytes'],attestor_artifact_sha256=att['digest'][7:],
        lease_sha256=root['lease_sha256'],root_raw_accepted=True,fresh_raw_review_accepted=True)
    n.validate_completion_api(a,live['run'],live['jobs'],c,att,workflow_id=live['workflow_id'])
    producer=read(ROOT/n.C_REQUEST);r=dict(producer,mode='abba',acceptance=a,native_budget=n.native_budget('abba'));n.validate_request(r,ROOT)
    write(ROOT/n.A_REQUEST,r);run('git','add',n.A_REQUEST);run('git','commit','-m','Authorize ABBA after genuine sealed pipeline canary raw acceptance')
    head=run('git','rev-parse','HEAD');parents=run('git','rev-list','--parents','-n','1','HEAD').split()[1:]
    changes=subprocess.check_output(['git','diff-tree','--no-commit-id','--name-status','-z','-r','HEAD'],cwd=ROOT);n.validate_activation(r,head,parents,changes,'100644',n.BRANCH)
    run('git','push','origin',n.BRANCH);write(BASE/'abba-activation.json',dict(control_head_sha=head,producer_head_sha=act['head_sha'],request_sha256=n.sha(n.canonical(r))))
    print(json.dumps(dict(status='DISTINCT_ABBA_CONTROL_PUSHED',control_head_sha=head,producer_head_sha=act['head_sha'])));return 0
def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['qualify','canary','status','abba','collect-canary','collect-abba']);a=p.parse_args()
    if a.command=='qualify':return qualify()
    if a.command=='canary':return activate_canary()
    if a.command=='abba':return activate_abba()
    if a.command=='status':
        s=status();print(json.dumps({k:v for k,v in s.items() if k not in ('run','jobs','artifact_response')}));return 0
    from renderer_pipeline_root import collect
    return collect('canary' if a.command=='collect-canary' else 'abba')
if __name__=='__main__':raise SystemExit(main())
