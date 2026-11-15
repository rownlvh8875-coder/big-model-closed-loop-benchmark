"""Closed mapping-only window policy; dictionaries alone grant no runtime authority."""
import hashlib,json,re
from pathlib import Path
from scripts.panda_dispatch_coverage import read_input
from scripts.engine_clock_runtime_inventory import validate_inventory
from scripts import panda_sdk_image_binding as base
ROOT=Path(__file__).resolve().parents[1]
REPO='rownlvh8875-coder/big-model-closed-loop-benchmark';REPO_ID=1447652055;OWNER=REPO.split('/')[0]
SOURCE_BRANCH='feature/panda-real-glx-canary-v1';BRANCH='diagnostic/panda-real-glx-20261115-01';ID='panda-real-glx-20261115-01'
WORKFLOW='.github/workflows/panda-real-glx-canary-v1.yml';REQUEST='docs/requests/'+ID+'.json';ARTIFACT=ID
SDK='docs/evidence/panda-sdk-link-audit-01/before-review/build/candidate-libpandagl.so.data';SDK_SHA='8d302ae2a610b56db4f7feca08fd736004cf6d3d9650fdb9834f19389a0b7342';SDK_SIZE=992200
HANDOFF='docs/evidence/panda-sdk-link-audit-01/selection.json';HANDOFF_SHA='eac57e3537dfe1b9b1062df76bb8897f1755df70fdc3452569732347b541ec4d'
LINK_AUDIT='docs/evidence/panda-sdk-link-audit-01/after-fix/replacement/audit.json';LINK_SHA='777f907c2bb2fce36b5fa34fd6d518d57a001244c2d1335dfaed360178846242'
SDK_PATH='/opt/venv/lib/python3.11/site-packages/panda3d/libpandagl.so'
AUTH='docs/evidence/panda-sdk-abi0-image-01/actual/acceptance/acceptance.json';AUTH_SHA='def7de2aef68ae4c8fff6925dc5514aaae18362fe8a8f78481b535e3b39aa531'
INVENTORY='docs/evidence/panda-sdk-abi0-image-01/actual/acceptance/candidate/installed-files.json'
PROFILE='docs/evidence/panda-real-glx-01/profile.json'
DISPATCH_ACCEPTANCE='docs/evidence/panda-sdk-dispatch-01/actual/acceptance/acceptance.json'
DISPATCH_SHA='ecfa69fad3d35cfca0581b35fd887858447fc3c2e6c1b6ef6308b97dbc1cdf7e'
GLDATA='docs/evidence/panda-real-glx-01/libGL.so.data'
PREFLIGHT='docs/evidence/panda-real-glx-01/preflight.json'
CORE_PATH='/opt/venv/lib/python3.11/site-packages/panda3d/core.cpython-311-x86_64-linux-gnu.so'
CORE_SHA='8b0372f1df91a930f18b2551f7fde5d5687e21bc79dee9ecd0dd2018cba72490'
XVFB='/usr/bin/Xvfb'
SITE='/opt/venv/lib/python3.11/site-packages'
GL_PATH='/usr/lib/x86_64-linux-gnu/libGL.so.1.7.0'
GALLIUM='/usr/lib/x86_64-linux-gnu/libgallium-25.2.8-0ubuntu0.24.04.4.so'
GLX_MESA='/usr/lib/x86_64-linux-gnu/libGLX_mesa.so.0.0.0'
PANDA='/opt/venv/lib/python3.11/site-packages/panda3d';PRELOAD=PANDA+'/libpanda.so.1.10'
SDK_PATH=PANDA+'/libpandagl.so';IMAGE_SHA='4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698';IMAGE_SIZE=1727678464;CONFIG='sha256:b9d673de93f1857e4dfa5ed6a48330d568ef96fce7f3cc975f0c688877e6e26e'
IMAGE_ARTIFACT=dict(id=14156262448,run_id=43700449423,head_sha='7cf0f0157f8100f0aa0e05b01a815d7395c3383f',name='panda-sdk-image-20261115-03',size_in_bytes=1738137175,sha256='47711425a5a48fb2ef0cab140da6e394516f9cbb7f04b294c5f6583d7efbc687')
BUDGET=dict(total_seconds=1800,minimum_free=16*1024**3,real_glx_windows=1,container_starts=1,panda_preloads=1,sdk_loads=1,core_imports=1,xvfb_starts=1,engines=1,output_requests=1,render_frames=4,ram_reads=2,width=8,height=8,memory_bytes=2*1024**3,pids=64,cpu=1,tmpfs_bytes=64*1024**2,container_seconds=240,protocol_seconds=180,phase_seconds=45,xvfb_ready_seconds=15,output_bytes=16*1024**2,runtime_bytes=8*1024**2,runtime_proof_bytes=12*1024**2,execution_bytes=4*1024**2,log_bytes=2*1024**2,mapped_files=192,mapped_file_bytes=192*1024**2,mapped_bytes=768*1024**2,generated_exec_regions=16,generated_exec_bytes=4*1024**2,driver_shared_regions=32,driver_shared_bytes=64*1024**2)
PERMISSIONS=dict(real_panda_glx_canary=True,dependency_initializers=True,read_process_memory=True,panda_core=True,owned_xvfb=True,explicit_gl_calls=True,render=True,texture_ram_read=True,software_driver_only=True,active_capture=False,source_observer_armed=False,metadrive=False,model=False,official_ort=False,scientific_native=False,native_admission=False,registry_publish=False,cloud_publish=False,main_merge=False)
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
 return sorted({str(p.relative_to(root)) for p in (root/'scripts').glob('*.py')}|{WORKFLOW,SDK,AUTH,INVENTORY,PROFILE,HANDOFF,LINK_AUDIT,DISPATCH_ACCEPTANCE,GLDATA,PREFLIGHT}|{str(p.relative_to(root)) for p in (root/'native/panda_sdk_routes_v2').iterdir() if p.is_file()})
def closure(root):return {p:sha(read_input(root/p,16*1024**2)) for p in source_paths(root)}
def request_template(source,ci,root):
 return dict(schema='panda-real-glx-request-v1',request_id=ID,repository=REPO,source_branch=SOURCE_BRANCH,source_sha=source,branch=BRANCH,workflow_path=WORKFLOW,source_closure=closure(root),source_ci=ci,sdk_sha256=SDK_SHA,sdk_nbytes=SDK_SIZE,image_artifact=dict(IMAGE_ARTIFACT),image_sha256=IMAGE_SHA,config_digest=CONFIG,profile_sha256=sha(read_input(root/PROFILE,1024**2)),dispatch_acceptance_sha256=DISPATCH_SHA,budget=dict(BUDGET),permissions=dict(PERMISSIONS))
def validate_request(r,root):
 image_authority(root);glx_profile(root);need(sha(read_input(root/DISPATCH_ACCEPTANCE,1024**2))==DISPATCH_SHA,'consumed dispatch authority pin')
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
 need(run['status']==('completed' if completed else 'in_progress') and (run['conclusion'] in ('success','failure') if completed else run['conclusion'] is None),'run outcome')
 need(workflow['id']==run['workflow_id'] and workflow['path']==WORKFLOW and workflow['state']=='active','workflow identity')
 need(type(listing['total_count']) is int and listing['total_count']==len(listing['workflow_runs'])==1 and listing['workflow_runs'][0]['id']==run['id'],'one-use run uniqueness')
def validate_artifacts(run,listing):
 need(type(listing.get('total_count')) is int and listing['total_count']==1 and len(listing['artifacts'])==1,'one canary artifact');row=listing['artifacts'][0];need(row['name']==ARTIFACT and positive(row['id']) and positive(row['size_in_bytes'],16*1024**2) and row['expired'] is False and row['digest'].startswith('sha256:') and hexstr(row['digest'][7:]),'canary artifact');w=row['workflow_run'];need(w['id']==run['id'] and w['head_sha']==run['head_sha'] and w['head_branch']==BRANCH and w['repository_id']==w['head_repository_id']==REPO_ID,'canary artifact run');return row

def image_authority(root):
 raw=read_input(root/AUTH,4*1024**2);need(sha(raw)==AUTH_SHA,'current image authority pin');r=parse(raw);need(r['status']=='AUTHENTICATED_ABI0_IMAGE_ROOT_SYMBOLS_AVAILABLE_NATIVE_BLOCKED' and r['actions_output_origin_authenticated'] is True and r['native_admitted'] is False and r['candidate_sdk_installed'] is True,'current image authority scope');need(r['archive']['image_tar_sha256']==IMAGE_SHA and r['archive']['image_tar_nbytes']==IMAGE_SIZE and r['archive']['config_digest']==CONFIG and r['sdk_sha256']==SDK_SHA and r['sdk_nbytes']==SDK_SIZE,'current image/SDK identity');return r

def expected_inventory(root):
 auth=image_authority(root);raw=read_input(root/INVENTORY,16*1024**2);need(sha(raw)==auth['installed_manifest_sha256'],'current manifest pin');return validate_inventory(parse(raw))

def glx_profile(root):
 from scripts.panda_real_glx_profile import make_profile
 raw=read_input(root/PROFILE,1024**2);r=parse(raw);need(r==make_profile(read_input(root/SDK,2*1024**2),read_input(root/GLDATA,1024**2)),'exact mapping profile');return r

def validate_production_job(run,jobs):
 need(type(jobs) is dict and type(jobs.get('total_count')) is int and jobs['total_count']==1 and type(jobs.get('jobs')) is list and len(jobs['jobs'])==1,'exact one production job')
 row=jobs['jobs'][0];need(positive(row.get('id')) and row.get('name')=='canary' and row.get('run_id')==run['id'] and type(row.get('run_attempt')) is int and row['run_attempt']==1 and row.get('head_sha')==run['head_sha'] and row.get('head_branch')==BRANCH and row.get('status')=='completed' and row.get('conclusion')==run['conclusion'] and run['conclusion'] in ('success','failure'),'production job identity/outcome');return row['id']
