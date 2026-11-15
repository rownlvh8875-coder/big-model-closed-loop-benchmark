"""Closed SDK-image policy. Pure validators alone authenticate no external origin."""
import hashlib,json,re
from pathlib import Path
from scripts.panda_dispatch_coverage import read_input
from scripts.engine_clock_runtime_inventory import validate_inventory
from scripts import panda_sdk_image_binding as base
ROOT=Path(__file__).resolve().parents[1]
REPO='rownlvh8875-coder/big-model-closed-loop-benchmark';REPO_ID=1447652055;OWNER=REPO.split('/')[0]
SOURCE_BRANCH='feature/panda-sdk-image-auth-v1';BRANCH='prepare/panda-sdk-image-20261115-02';ID='panda-sdk-image-20261115-02'
WORKFLOW='.github/workflows/panda-sdk-image-production-v2.yml';REQUEST='docs/requests/'+ID+'.json';ARTIFACT=ID
SDK='docs/evidence/panda-sdk-routes-02/before-review/build/candidate-libpandagl.so.data';SDK_SHA='3e9fa983023cb1f30b08a2bc650d0803686bef032a2c5d7a5700e1d3ad60553b';SDK_SIZE=998200
SDK_PATH='/opt/venv/lib/python3.11/site-packages/panda3d/libpandagl.so'
INVENTORY='docs/evidence/engine-clock-sealed-image-06/installed-files.json';TAG='stage7-panda-sdk:actions-20261115-02'
BASE_ARTIFACT=dict(id=14078483374,run_id=43512140336,head_sha='382b2ad201c12836b0adcc54cb2719a47b0cdcb4',name='engine-clock-image-20261114-06',size_in_bytes=1735029078,sha256='62e09e31d565890a82b4965bafe855ad382e9a22794d12310fe0f06e695e920a')
BUDGET=dict(total_seconds=1800,transfer_seconds=300,docker_seconds=180,cleanup_seconds=12,http_gets=96,producer_payload=2*1024**3,consumer_payload=4*1024**3,producer_output=10*1024**3,minimum_free=16*1024**3,log_bytes=1024**2)
PERMISSIONS=dict(docker_load=True,docker_copy_build=True,stopped_export=True,container_start=False,native=False,model=False,registry_publish=False,cloud_publish=False,main_merge=False)
def need(ok,message='SDK_IMAGE_POLICY_REJECTED'):
 if not ok:raise ValueError(message)
def sha(data):return hashlib.sha256(data).hexdigest()
def hexstr(v,n=64):return type(v) is str and re.fullmatch('[0-9a-f]{'+str(n)+'}',v) is not None
def positive(v,limit=2**63):return type(v) is int and 0<v<=limit
def pairs(rows):
 d={}
 for k,v in rows:need(k not in d,'duplicate JSON field');d[k]=v
 return d
def parse(raw):return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def source_paths(root):
 return sorted({str(p.relative_to(root)) for p in (root/'scripts').glob('*.py')}|{WORKFLOW,SDK,base.RESULT,INVENTORY,'docs/evidence/panda-sdk-routes-02/selection.json'}|{str(p.relative_to(root)) for p in (root/'native/panda_sdk_routes_v2').iterdir() if p.is_file()})
def closure(root):return {p:sha(read_input(root/p,16*1024**2)) for p in source_paths(root)}
def request_template(source,ci,root):
 return dict(schema='panda-sdk-image-request-v1',request_id=ID,repository=REPO,source_branch=SOURCE_BRANCH,source_sha=source,branch=BRANCH,workflow_path=WORKFLOW,source_closure=closure(root),source_ci=ci,sdk_sha256=SDK_SHA,sdk_nbytes=SDK_SIZE,base_artifact=BASE_ARTIFACT,budget=BUDGET,permissions=PERMISSIONS)
def validate_request(r,root):
 need(type(r) is dict and set(r)==set(request_template('0'*40,[],root)))
 for k,v in request_template(r.get('source_sha'),r.get('source_ci'),root).items():need(r[k]==v,'request field drift: '+k)
 need(hexstr(r['source_sha'],40) and all(type(v) is int for v in r['budget'].values()) and all(type(v) is bool for v in r['permissions'].values()))
 need(type(r['sdk_nbytes']) is int and 0<len(r['source_closure'])<=512)
 ci=r['source_ci'];need(type(ci) is list and len(ci)==2 and [x.get('event') for x in ci]==['push','pull_request'] and all(set(x)=={'event','run_id'} and positive(x['run_id']) for x in ci) and ci[0]['run_id']!=ci[1]['run_id'])
 data=read_input(root/SDK,2*1024**2);need(len(data)==SDK_SIZE and sha(data)==SDK_SHA,'committed SDK bytes drift')
 return r
def validate_activation(r,head,commit,delta,mode):
 need(hexstr(head,40) and head!=r['source_sha'] and commit['sha']==head and [x['sha'] for x in commit['parents']]==[r['source_sha']] and mode=='100644','activation parent/mode')
 need(delta['status']=='ahead' and type(delta['ahead_by']) is int and delta['ahead_by']==1 and type(delta['total_commits']) is int and delta['total_commits']==1 and [x['sha'] for x in delta['commits']]==[head],'activation delta')
 files=delta['files'];need(len(files)==1 and files[0]['filename']==REQUEST and files[0]['status']=='added' and hexstr(files[0]['sha'],40),'request-only activation')
def validate_ci(r,proofs):
 need(type(proofs) is list and len(proofs)==2,'two CI runs required')
 for expected,p in zip(r['source_ci'],proofs):
  run=p['run'];rid=expected['run_id'];need(run['id']==rid and type(run['run_attempt']) is int and run['run_attempt']==1 and run['head_sha']==r['source_sha'] and run['head_branch']==SOURCE_BRANCH and run['event']==expected['event'] and run['workflow_id']==411705464 and run['path']=='.github/workflows/ci.yml' and run['status']=='completed' and run['conclusion']=='success' and run['repository']['full_name']==REPO,'source CI identity')
  jobs=p['jobs'];need(jobs['total_count']==len(jobs['jobs'])==2 and {x['name'] for x in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(x['run_id']==rid and x['status']=='completed' and x['conclusion']=='success' for x in jobs['jobs']),'source CI jobs')
  need(p['artifacts']==dict(total_count=0,artifacts=[]),'source CI artifacts')
def validate_run(r,ctx,run,workflow,listing,completed=False):
 need(ctx['repository']==REPO and ctx['event']=='push' and type(ctx['attempt']) is int and ctx['attempt']==1 and positive(ctx['run_id']) and hexstr(ctx['head_sha'],40) and ctx['actor']==OWNER,'run context')
 need(run['id']==ctx['run_id'] and run['head_sha']==ctx['head_sha'] and run['head_branch']==BRANCH and run['event']=='push' and type(run['run_attempt']) is int and run['run_attempt']==1 and run['path']==WORKFLOW and run['actor']['login']==OWNER,'run identity')
 need(all(run[k]['full_name']==REPO and run[k]['id']==REPO_ID for k in ('repository','head_repository')),'run repository')
 need(run['status']==('completed' if completed else 'in_progress') and run['conclusion']==('success' if completed else None),'run outcome')
 need(workflow['id']==run['workflow_id'] and workflow['path']==WORKFLOW and workflow['state']=='active','workflow identity')
 need(type(listing['total_count']) is int and listing['total_count']==len(listing['workflow_runs'])==1 and listing['workflow_runs'][0]['id']==run['id'],'one-use run uniqueness')
def validate_artifacts(run,listing):
 need(type(listing['total_count']) is int and listing['total_count']==len(listing['artifacts'])==2,'two output artifacts')
 rows={}
 for row in listing['artifacts']:
  name=row['name'];need(name in (ARTIFACT,ARTIFACT+'-execution') and name not in rows and positive(row['id']) and positive(row['size_in_bytes'],2*1024**3 if name==ARTIFACT else 16*1024**2) and row['expired'] is False and type(row['digest']) is str and row['digest'].startswith('sha256:') and hexstr(row['digest'][7:]),'artifact metadata')
  w=row['workflow_run'];need(w['id']==run['id'] and w['head_sha']==run['head_sha'] and w['head_branch']==BRANCH and w['repository_id']==w['head_repository_id']==REPO_ID,'artifact run binding');rows[name]=row
 return rows
def authority(root):
 raw=read_input(root/base.RESULT,1024**2);need(sha(raw)==base.RESULT_SHA,'base authority pin');return parse(raw)
def expected_inventory(root):
 auth=authority(root);raw=read_input(root/INVENTORY,16*1024**2);need(sha(raw)==auth['installed_files_sha256'],'old inventory pin');m=parse(raw);hits=[x for x in m['entries'] if x['path']==SDK_PATH];need(len(hits)==1 and hits[0]['kind']=='file','old SDK membership');hits[0].update(mode=0o755,nbytes=SDK_SIZE,sha256=SDK_SHA);return validate_inventory(m)
