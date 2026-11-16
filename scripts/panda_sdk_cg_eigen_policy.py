"""New one-use compile-only authority; no old window or target-execution permission."""
import json,os,re
from pathlib import Path
from scripts import panda_sdk_cg_inputs as inputs
from scripts import panda_sdk_cg_eigen_inputs as eigen
ROOT=inputs.ROOT;need=inputs.need;sha=inputs.sha;read=inputs.read;parse=inputs.parse
REPO='rownlvh8875-coder/big-model-closed-loop-benchmark';REPO_ID=1447652055;OWNER=REPO.split('/')[0]
SOURCE_BRANCH='feature/panda-sdk-cg-eigen-candidate-v2';BRANCH='prepare/panda-sdk-cg-eigen-build-20261116-02';ID='panda-sdk-cg-eigen-build-20261116-02';WORKFLOW='.github/workflows/panda-sdk-cg-eigen-build-v2.yml';REQUEST='docs/requests/'+ID+'.json';ARTIFACT=ID
OLD_CLOSURE='docs/evidence/panda-sdk-cg-candidate-01/review/source-closure.json';OLD_SHA='2448766e317df62ad4afd288ebd743a650da47359781ea0c02dee0a74c5e0b5d'
IMAGE_ARTIFACT=dict(id=14156262448,run_id=43700449423,head_sha='7cf0f0157f8100f0aa0e05b01a815d7395c3383f',name='panda-sdk-image-20261115-03',size_in_bytes=1738137175,sha256='47711425a5a48fb2ef0cab140da6e394516f9cbb7f04b294c5f6583d7efbc687')
def hexstr(v,n=64):return type(v) is str and re.fullmatch('[0-9a-f]{'+str(n)+'}',v) is not None
def positive(v,limit=2**63):return type(v) is int and 0<v<=limit
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def closure(root):
 c=eigen.contract(root);raw=read(root/OLD_CLOSURE,1024**2);need(sha(raw)==OLD_SHA,'old282 closure authority');old=parse(raw);need(len(old)==282 and all(sha(read(root/p,16*1024**2))==h for p,h in old.items()),'old282 source identities changed')
 names=set(old)|{str(p.relative_to(root)) for p in (root/'scripts').glob('*.py')}|{WORKFLOW,eigen.CONTRACT,c['eigen_package_path'],c['eigen_headers_path'],'docs/evidence/panda-sdk-cg-residual-01/eigen-input.json',OLD_CLOSURE,'native/panda_sdk_cg_v2/layout_contract.cxx','docs/evidence/panda-sdk-cg-candidate-01/actual/acceptance/candidate/reports/configuration.json'}
 return {p:sha(read(root/p,16*1024**2)) for p in sorted(names)}
def request_template(source_sha,source_ci,root):
 c=eigen.contract(root);return dict(schema='panda-sdk-cg-eigen-build-request-v2',request_id=ID,repository=REPO,source_branch=SOURCE_BRANCH,source_sha=source_sha,branch=BRANCH,workflow_path=WORKFLOW,source_closure=closure(root),source_ci=source_ci,contract_sha256=eigen.CONTRACT_SHA,budget=c['candidate_limits'],permissions=c['future_candidate_permissions'],image_artifact=IMAGE_ARTIFACT)
def validate_request(r,root):
 need(type(r) is dict and hexstr(r.get('source_sha'),40),'source identity');need(r==request_template(r.get('source_sha'),r.get('source_ci'),root),'closed request fields');need(all(type(v) is int for v in r['budget'].values()) and all(type(v) is bool for v in r['permissions'].values()),'request scalar types');ci=r['source_ci'];need(type(ci) is list and len(ci)==2 and [x.get('event') for x in ci]==['push','pull_request'] and all(set(x)=={'event','run_id'} and positive(x['run_id']) for x in ci) and ci[0]['run_id']!=ci[1]['run_id'],'source CI registrations');return r

def validate_ci(r,proofs):
 need(type(proofs) is list and len(proofs)==2,'two exact source CI runs')
 for x,p in zip(r['source_ci'],proofs):
  run=p['run'];need(run['id']==x['run_id'] and run['head_sha']==r['source_sha'] and run['head_branch']==SOURCE_BRANCH and run['event']==x['event'] and run['workflow_id']==411705464 and run['path']=='.github/workflows/ci.yml' and type(run['run_attempt']) is int and run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='success' and run['repository']['full_name']==REPO,'source CI identity/outcome');j=p['jobs'];need(j['total_count']==len(j['jobs'])==2 and {v['name'] for v in j['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(v['run_id']==x['run_id'] and v['status']=='completed' and v['conclusion']=='success' for v in j['jobs']),'source CI jobs');need(p['artifacts']==dict(total_count=0,artifacts=[]),'source CI artifact closure')
def validate_activation(r,head,commit,delta,mode):
 need(hexstr(head,40) and head!=r['source_sha'] and commit['sha']==head and [p['sha'] for p in commit['parents']]==[r['source_sha']] and mode=='100644','activation parent/mode');need(delta['status']=='ahead' and type(delta['ahead_by']) is int and delta['ahead_by']==1 and type(delta['total_commits']) is int and delta['total_commits']==1 and [p['sha'] for p in delta['commits']]==[head],'activation delta');files=delta['files'];need(len(files)==1 and files[0]['filename']==REQUEST and files[0]['status']=='added' and hexstr(files[0]['sha'],40),'request-only activation')
def validate_run(ctx,run,workflow,listing,completed=False):
 need(ctx['repository']==REPO and ctx['event']=='push' and type(ctx['attempt']) is int and ctx['attempt']==1 and positive(ctx['run_id']) and hexstr(ctx['head_sha'],40) and ctx['actor']==OWNER,'closed context');need(run['id']==ctx['run_id'] and run['head_sha']==ctx['head_sha'] and run['head_branch']==BRANCH and run['event']=='push' and type(run['run_attempt']) is int and run['run_attempt']==1 and run['path']==WORKFLOW and run['actor']['login']==OWNER,'closed build run')
 need(all(run[k]['full_name']==REPO and run[k]['id']==REPO_ID for k in ['repository','head_repository']),'build repository');need(run['status']==('completed' if completed else 'in_progress') and (run['conclusion'] in ('success','failure','cancelled','timed_out') if completed else run['conclusion'] is None),'build run state');need(workflow['id']==run['workflow_id'] and workflow['path']==WORKFLOW and workflow['state']=='active','workflow identity');need(type(listing['total_count']) is int and listing['total_count']==len(listing['workflow_runs'])==1 and listing['workflow_runs'][0]['id']==run['id'],'unique build run')
def reserve_build(path):
 try:
  with Path(path).open('x') as f:json.dump(dict(schema='panda-sdk-cg-eigen-build-start-v2',build_start_attempts=1,target_execution=False),f);f.write('\n')
 except FileExistsError as e:raise ValueError('build already reserved') from e

def validate_artifact(run,listing):
 need(type(listing['total_count']) is int and listing['total_count']==len(listing['artifacts'])==1,'one closed build artifact');r=listing['artifacts'][0];w=r['workflow_run'];need(r['name']==ARTIFACT and positive(r['id']) and positive(r['size_in_bytes'],256*1024**2) and r['expired'] is False and type(r['digest']) is str and r['digest'].startswith('sha256:') and hexstr(r['digest'][7:]),'artifact metadata');need(w['id']==run['id'] and w['head_sha']==run['head_sha'] and w['head_branch']==BRANCH and w['repository_id']==w['head_repository_id']==REPO_ID,'artifact run binding');return r
