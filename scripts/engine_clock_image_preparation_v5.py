"""One-use source-qualified Actions renderer image preparation and independent preflight.

No operation occurs at import. Live entry requires actual owner/run/workflow,
qualified source CI, exact request-only activation and preserved closed inputs.
"""
import argparse
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.parse

if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from scripts import engine_clock_image_archive_v2 as archive
from scripts import engine_clock_image_process as process
from scripts import engine_clock_image_transport as transport
from scripts import engine_clock_image_inventory as inventory

REPOSITORY='rownlvh8875-coder/big-model-closed-loop-benchmark'
SOURCE_BRANCH='prepare/engine-clock-sealed-image-v5'
INPUT_SHA='f33c2558295efb57fcb22b2116c3f9f97d5e9f29c1ae017423e7a8423869c26a'
RENDERER_SHA='052b6dd97b126bb2b79ea1b0573b6bf6dc70a800d587dec7316cb3e5fe99d51c'
EFFECTIVE_SHA='8f214a1454557e588425d473cefa946c14e443e4cc47f85c1bfce02673d9552a'
LAYOUT_SHA='701e4d9754700b96b2b9daaf18602bc69dd34d98bf4fbe1d7608a54831e7cc79'
INPUT_PATH='docs/locks/engine-clock-image-inputs.lock.json'
RENDERER_PATH='docs/locks/engine-clock-renderer-wheels.lock.json'
LAYOUT_PATH='docs/locks/engine-clock-python-layout.json'
EFFECTIVE_PATH='docs/locks/engine-clock-sealed-image-v2.lock.json'
GIB=1024**3
MIB=1024**2
IMAGE_TAG='stage7-engine-clock:image-20261114-01'
BASE_TAG='stage7-engine-clock-base:7da97f743f397971'
SCRIPT_PATH='/usr/local/libexec/stage7/scripts/engine_clock_image_inventory.py'
ROLES={}
for _role,_id,_workflow in [('prepare','image-20261114-06','engine-clock-image-preparation-v5.yml'),('preflight','image-preflight-20261114-06','engine-clock-image-preflight-v5.yml')]:
    ROLES[_role]={'request_id':_id,'branch':'prepare/engine-clock-'+_id,'request_path':'docs/requests/engine-clock-'+_id+'.json','output':'output/stage7-image-operations/'+_id,'workflow':'.github/workflows/'+_workflow,'artifact_name':'engine-clock-'+_id,'execution_artifact_name':'engine-clock-'+_id+'-execution'}
BUDGETS={
 'prepare':{'workflow_visibility_seconds':30,'workflow_visibility_snapshots':6,'workflow_visibility_interval_seconds':5,'total_seconds':1800,'download_seconds':900,'build_seconds':600,'save_seconds':180,'inventory_seconds':180,'http_gets':384,'payload_bytes':1536*MIB,'context_bytes':GIB,'execution_bytes':2*GIB-16*MIB,'image_tar_bytes':2*GIB,'image_zip_bytes':2*GIB,'log_bytes':MIB,'metadata_json_bytes':4*MIB,'minimum_free_union_bytes':16*GIB,'cleanup_seconds':12,'docker_base_loads':1,'docker_builds':1,'docker_saves':1,'containers':1,'docker_image_loads':0},
 'preflight':{'workflow_visibility_seconds':30,'workflow_visibility_snapshots':6,'workflow_visibility_interval_seconds':5,'total_seconds':900,'download_seconds':300,'inventory_seconds':180,'http_gets':64,'payload_bytes':2*GIB,'execution_bytes':2*GIB-16*MIB,'image_tar_bytes':2*GIB,'image_zip_bytes':2*GIB,'log_bytes':MIB,'metadata_json_bytes':4*MIB,'minimum_free_union_bytes':16*GIB,'cleanup_seconds':12,'docker_base_loads':0,'docker_builds':0,'docker_saves':0,'containers':1,'docker_image_loads':1,'copy_archives':3,'copy_archive_bytes':512*MIB}}
PERMISSIONS={role:{'payload_downloads':True,'docker_metadata':True,'host_root_filesystem_metadata':True,'docker_build':role=='prepare','docker_load':True,'metadata_container':True,'signed_package_install':role=='prepare','offline_wheel_install':role=='prepare','source_package_build':False,'native_engine':False,'official_model':False,'ort_session':False,'registry_publish':False,'cloud_publish':False,'main_merge':False} for role in ROLES}

FIXED_PATHS={
 'scripts/engine_clock_image_preparation_v2.py','scripts/engine_clock_image_staging_v2.py','tests/test_engine_clock_image_retained.py',
 'docs/locks/engine-clock-retained-image-debs-01.lock.json','docs/evidence/STAGE7_ENGINE_CLOCK_IMAGE_01_RESULT.json',
 'docs/superpowers/specs/2026-11-14-engine-clock-retained-image-design.md','docs/superpowers/plans/2026-11-14-engine-clock-retained-image.md',
 'scripts/engine_clock_image_preparation_v5.py','scripts/engine_clock_image_archive_v2.py','tests/test_engine_clock_image_docker_save_compat.py','docs/evidence/STAGE7_ENGINE_CLOCK_IMAGE_05_RESULT.json',
 'docs/superpowers/specs/2026-11-14-engine-clock-docker-save-compat-design.md','docs/superpowers/plans/2026-11-14-engine-clock-docker-save-compat.md',
 'scripts/engine_clock_image_preparation_v4.py','tests/test_engine_clock_image_run_visibility.py','docs/evidence/STAGE7_ENGINE_CLOCK_IMAGE_04_RESULT.json',
 'docs/superpowers/specs/2026-11-14-engine-clock-run-visibility-design.md','docs/superpowers/plans/2026-11-14-engine-clock-run-visibility.md',
 'tests/test_engine_clock_image_pager_alias.py','docs/locks/engine-clock-sealed-image.lock.json',
 'scripts/engine_clock_image_backend_v2.py',
 'scripts/engine_clock_image_preparation_v3.py','scripts/engine_clock_image_staging_v3.py','scripts/engine_clock_image_installer_v2.py','tests/test_engine_clock_image_assets_bootstrap.py','tests/test_engine_clock_image_payloads.py',
 'docs/locks/engine-clock-retained-image-payloads-02.lock.json','docs/evidence/STAGE7_ENGINE_CLOCK_IMAGE_02_RESULT.json',
 'docs/superpowers/specs/2026-11-14-engine-clock-assets-bootstrap-design.md','docs/superpowers/plans/2026-11-14-engine-clock-assets-bootstrap.md',
 'scripts/__init__.py','scripts/engine_clock_runtime_inventory.py','scripts/engine_clock_wheel_derivative.py',
 'scripts/engine_clock_image_archive.py','scripts/engine_clock_image_inventory.py','scripts/engine_clock_image_installer.py',
 'scripts/engine_clock_image_process.py','scripts/engine_clock_image_transport.py','scripts/engine_clock_image_preparation.py',
 'scripts/engine_clock_image_backend.py','scripts/engine_clock_image_staging.py','tests/test_engine_clock_image_backend.py','tests/test_engine_clock_image_staging.py',
 'tests/test_engine_clock_image_archive.py','tests/test_engine_clock_image_inventory.py','tests/test_engine_clock_image_installer.py',
 'tests/test_engine_clock_image_process.py','tests/test_engine_clock_image_transport.py','tests/test_engine_clock_image_preparation.py',
 INPUT_PATH,RENDERER_PATH,LAYOUT_PATH,EFFECTIVE_PATH,'docs/evidence/engine-clock-python-bootstrap/archive-members.json',
 'docs/evidence/STAGE7_ENGINE_CLOCK_WHEEL_DERIVATIVE_POLICY.json','docs/evidence/STAGE7_ENGINE_CLOCK_COMPLETE_IMAGE_INPUTS_REVIEW.json',
 'docs/evidence/engine-clock-image-sealed-inputs/base-overlay-receipt.json',
 'docs/superpowers/specs/2026-11-14-engine-clock-sealed-image-design.md',
 'docs/superpowers/plans/2026-11-14-engine-clock-sealed-image.md','docker/engine-clock-sealed-image.Dockerfile',
 *[r['workflow'] for r in ROLES.values()]}


def _need(value,code='IMAGE_CONTEXT_REJECTED'):
    if not value:raise ValueError(code)


def _hex(value,n=64):return type(value) is str and re.fullmatch('[0-9a-f]{'+str(n)+'}',value) is not None

def canonical(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def _pairs(items):
    result={}
    for k,v in items:_need(k not in result);result[k]=v
    return result

def parse(raw):return json.loads(raw,object_pairs_hook=_pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('IMAGE_CONTEXT_REJECTED')))


def read_regular(path,limit=16*MIB):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as f:
        before=os.fstat(f.fileno());_need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<=before.st_size<=limit);raw=f.read(limit+1);after=os.fstat(f.fileno());_need(len(raw)==before.st_size and archive._signature(before)==archive._signature(after));return raw


def source_paths(root):
    raw=read_regular(Path(root)/INPUT_PATH);_need(hashlib.sha256(raw).hexdigest()==INPUT_SHA)
    lock=parse(raw);paths=set(FIXED_PATHS)
    for row in lock['authority_files'].values():
        path=row['path'];_need(type(path) is str and path.startswith('docs/evidence/engine-clock-image-sealed-inputs/') and '..' not in path.split('/'));paths.add(path)
    return frozenset(paths)


def validate_request(value,role,root):
    try:
        def need(v):_need(v,'IMAGE_REQUEST_REJECTED')
        cfg=ROLES[role];need(type(value) is dict and set(value)=={'schema','role','request_id','repository','branch','reviewed_source_branch','reviewed_source_sha','output_directory','workflow_path','source_closure','source_ci','input_lock_sha256','renderer_lock_sha256','python_layout_sha256','effective_lock_sha256','budget','permissions','image_evidence'})
        for key,expected in {'schema':'engine-clock-image-operation-request-v1','role':role,'request_id':cfg['request_id'],'repository':REPOSITORY,'branch':cfg['branch'],'reviewed_source_branch':SOURCE_BRANCH,'output_directory':cfg['output'],'workflow_path':cfg['workflow'],'input_lock_sha256':INPUT_SHA,'renderer_lock_sha256':RENDERER_SHA,'python_layout_sha256':LAYOUT_SHA,'effective_lock_sha256':EFFECTIVE_SHA,'budget':BUDGETS[role],'permissions':PERMISSIONS[role]}.items():need(value[key]==expected)
        need(_hex(value['reviewed_source_sha'],40) and all(type(v) is int for v in value['budget'].values()) and all(type(v) is bool for v in value['permissions'].values()))
        need(type(value['source_closure']) is dict and set(value['source_closure'])==source_paths(root) and all(_hex(v) for v in value['source_closure'].values()))
        ci=value['source_ci'];need(type(ci) is list and len(ci)==2 and [r['event'] for r in ci]==['push','pull_request'] and all(set(r)=={'run_id','event'} and type(r['run_id']) is int and r['run_id']>0 for r in ci) and ci[0]['run_id']!=ci[1]['run_id'])
        if role=='prepare':need(value['image_evidence'] is None)
        else:
            image=value['image_evidence'];need(type(image) is dict and set(image)=={'expected','candidate_receipt_sha256','installed_files_nbytes'})
            expected=image['expected'];need(type(expected) is dict and expected['repository']==REPOSITORY and expected['source_sha']==value['reviewed_source_sha'] and expected['request_id']==ROLES['prepare']['request_id'] and expected['branch']==ROLES['prepare']['branch'] and expected['workflow_path']==ROLES['prepare']['workflow'] and expected['image_tag']==IMAGE_TAG and expected['lock_sha256']==EFFECTIVE_SHA)
            need(all(type(expected[k]) is int and expected[k]>0 for k in ('run_id','workflow_id','artifact_id','artifact_zip_nbytes')) and expected['artifact_zip_nbytes']<=2*GIB and _hex(image['candidate_receipt_sha256']) and type(image['installed_files_nbytes']) is int and 0<image['installed_files_nbytes']<=16*MIB)
            need(all(_hex(expected[k]) for k in ('artifact_zip_sha256','recipe_sha256','installed_files_sha256')) and _hex(expected['activation_sha'],40))
        return value
    except Exception:raise ValueError('IMAGE_REQUEST_REJECTED') from None


def validate_activation(request,head,parents,changes,mode,branch):
    cfg=ROLES[request['role']];_need(_hex(head,40) and parents==[request['reviewed_source_sha']] and head!=request['reviewed_source_sha'] and changes==b'A\0'+cfg['request_path'].encode()+b'\0' and mode=='100644' and branch==cfg['branch'])


def validate_source_ci(request,proofs):
    try:
        def need(v):_need(v,'IMAGE_SOURCE_CI_REJECTED')
        need(type(proofs) is list and len(proofs)==2)
        for registration,p in zip(request['source_ci'],proofs):
            run=p['run'];jobs=p['jobs'];arts=p['artifacts'];rid=registration['run_id']
            need(type(run['id']) is int and run['id']==rid and run['head_sha']==request['reviewed_source_sha'] and run['head_branch']==SOURCE_BRANCH and run['event']==registration['event'] and run['path']=='.github/workflows/ci.yml' and type(run['run_attempt']) is int and run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='success' and run['repository']['full_name']==REPOSITORY)
            need(type(jobs['total_count']) is int and jobs['total_count']==2 and len(jobs['jobs'])==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(j['run_id']==rid and j['status']=='completed' and j['conclusion']=='success' for j in jobs['jobs']))
            need(type(arts['total_count']) is int and arts['total_count']==0 and arts['artifacts']==[])
    except Exception:raise ValueError('IMAGE_SOURCE_CI_REJECTED') from None


def validate_live_run(request,context,run,workflow,unique):
    cfg=ROLES[request['role']]
    _need(context['repository']==REPOSITORY and context['event']=='push' and type(context['attempt']) is int and context['attempt']==1 and type(context['run_id']) is int and context['run_id']>0 and _hex(context['head_sha'],40))
    _need(type(run['id']) is int and run['id']==context['run_id'] and run['head_sha']==context['head_sha'] and run['head_branch']==cfg['branch'] and run['event']=='push' and type(run['run_attempt']) is int and run['run_attempt']==1 and run['status']=='in_progress' and run['repository']['full_name']==REPOSITORY and run['path']==cfg['workflow'])
    _need(type(run['workflow_id']) is int and workflow['id']==run['workflow_id'] and workflow['path']==cfg['workflow'] and workflow['state']=='active')
    _need(type(unique['total_count']) is int and unique['total_count']==1 and len(unique['workflow_runs'])==1 and unique['workflow_runs'][0]['id']==run['id'] and unique['workflow_runs'][0]['head_sha']==run['head_sha'] and type(unique['workflow_runs'][0]['run_attempt']) is int and unique['workflow_runs'][0]['run_attempt']==1)
    return {'status':'LIVE_CONTEXT_SEMANTICS_MATCH','workflow_id':run['workflow_id'],'external_api_origin_authenticated':False}


def observe_unique(client,endpoint,*,clock=time.monotonic,sleep=time.sleep):
    """Retain successful empty visibility snapshots; never retry a failed request."""
    original=client.deadline;started=clock();stop=min(original,started+30);client.deadline=stop;names=[]
    try:
        for index in range(6):
            _need(clock()<stop,'IMAGE_WORKFLOW_VISIBILITY_REJECTED')
            name='live-unique-%02d.json'%index;value=client.get_json(endpoint,name);names.append(name)
            _need(clock()<stop,'IMAGE_WORKFLOW_VISIBILITY_REJECTED')
            if not (type(value) is dict and type(value.get('total_count')) is int and value['total_count']==0 and value.get('workflow_runs')==[]):
                return value,{'status':'NONEMPTY_WORKFLOW_LIST_OBSERVED','snapshots':len(names),'elapsed_seconds':clock()-started,'maximum_seconds':30,'maximum_snapshots':6,'empty_interval_seconds':5,'raw_snapshot_paths':names,'external_api_origin_authenticated':False}
            if index==5:break
            left=stop-clock();_need(left>0,'IMAGE_WORKFLOW_VISIBILITY_REJECTED');sleep(min(5,left))
        raise ValueError('IMAGE_WORKFLOW_VISIBILITY_REJECTED')
    finally:client.deadline=original


def storage_union(observations):
    try:
        _need(type(observations) is list and {r['label'] for r in observations}=={'archive','docker'} and len(observations)==2,'IMAGE_STORAGE_REJECTED');devices={}
        for row in observations:
            _need(type(row['st_dev']) is int and row['st_dev']>=0 and type(row['free_bytes']) is int and row['free_bytes']>=0,'IMAGE_STORAGE_REJECTED');dev=row['st_dev'];devices[dev]=min(devices.get(dev,row['free_bytes']),row['free_bytes'])
        available=sum(devices.values());_need(available>=16*GIB and (len(devices)==1 or all(v>=8*GIB for v in devices.values())),'IMAGE_STORAGE_REJECTED')
        return {'free_union_bytes':available,'filesystem_count':len(devices),'devices':[{'st_dev':k,'free_bytes':v} for k,v in sorted(devices.items())],'shared_capacity_counted_once':True}
    except Exception:raise ValueError('IMAGE_STORAGE_REJECTED') from None


def make_redactor(environment):
    values=[]
    for key,value in environment.items():
        if value and len(value)>=8 and (key.startswith(('GH_','GITHUB_','AWS_','AZURE_','OPENAI_','ANTHROPIC_')) or key.upper() in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY')):values.append(value.encode())
    def redact(raw):
        for value in sorted(values,key=len,reverse=True):raw=raw.replace(value,b'[REDACTED]')
        raw=re.sub(rb'(https?://)[^/\s@]+@',rb'\1[REDACTED]@',raw)
        raw=re.sub(rb'(https?://[^\s?]+)\?[^\s]+',rb'\1?[REDACTED]',raw)
        return raw
    return redact


def normalize_launch(raw,expected,nonce):
    """Validate all sensitive launch metadata in memory before returning a projection."""
    try:
        h=raw['HostConfig'];c=raw['Config'];environment={}
        for item in c['Env']:
            key,sep,value=item.partition('=');_need(sep and key not in environment);environment[key]=value
        mounts=[]
        for row in raw['Mounts']:
            _need(row['Type']=='tmpfs' and row['Destination']=='/tmp' and row['RW'] is True)
            mounts.append({'type':row['Type'],'destination':row['Destination'],'rw':row['RW']})
        result={'container_id':raw['Id'],'image_id':raw['Image'],'read_only_rootfs':h['ReadonlyRootfs'],'network_mode':h['NetworkMode'],'privileged':h['Privileged'],'cap_drop':h['CapDrop'],'security_opt':h['SecurityOpt'],'pid_mode':h['PidMode'],'ipc_mode':h['IpcMode'],'pids_limit':h['PidsLimit'],'memory_bytes':h['Memory'],'nano_cpus':h['NanoCpus'],'devices':h['Devices'] or [],'device_requests':h['DeviceRequests'] or [],'binds':h['Binds'] or [],'mounts':mounts,'tmpfs':h['Tmpfs'],'entrypoint':c['Entrypoint'],'command':c['Cmd'],'user':c['User'],'working_dir':c['WorkingDir'],'env':environment,'labels':c['Labels'],'unknown_env_count':len(set(environment)-set(archive.IMAGE_ENV))}
        archive.validate_launch(result,expected,nonce)
        _need(set(result['labels'])=={'stage7.request','stage7.nonce','stage7.source','org.opencontainers.image.version'} and result['labels']['org.opencontainers.image.version']=='24.04')
        return result
    except Exception:raise ValueError('IMAGE_LAUNCH_REJECTED') from None


def prepare_image(request,context,work,*,engine,stage):
    """Compose an explicit backend; owned fixtures confer no external authenticity."""
    _need(request['role']=='prepare')
    staged=stage(request,context,work)
    engine.load_base(staged['base_archive'],staged['base_config_digest'],staged['base_diff_ids'])
    image=engine.build(staged['context'],context['source_sha'])
    collection=engine.collect(image,request)
    raw=collection['manifest_raw'];_need(type(raw) is bytes and len(raw)<=16*MIB)
    manifest=inventory.core.validate_inventory(parse(raw));_need(inventory.core._canonical(manifest)==raw)
    summary=collection['summary'];versions=summary['version_evidence'];wanted={r['name']:r['version'] for r in staged['renderer']['wheels']}
    _need(summary['status']=='CANDIDATE_INSTALLED_MANIFEST_COLLECTED' and summary['complete'] is True and summary['canonical_manifest_sha256']==hashlib.sha256(raw).hexdigest() and summary['host']==engine.host and summary['prefix']['status']=='PREFIX_LAYOUT_AND_OBSERVATION_MATCH' and summary['native_admission'] is False and type(summary['official_model_calls']) is int and summary['official_model_calls']==0)
    _need(versions['python']=='3.11.18' and versions['installed_distributions']==wanted and versions['cv2_imported'] is False and versions['renderer_packages_imported'] is False and versions['ort_installed'] is False)
    image_dir=Path(work).parent/'image';image_dir.mkdir(mode=0o700,exist_ok=False);(image_dir/'installed-files.json').write_bytes(raw)
    engine.save(image,image_dir/'image.tar')
    checked=archive.inspect_save_archive(image_dir/'image.tar',expected_tag=IMAGE_TAG,deadline=time.perf_counter()+180)
    _need(image['config_digest']==checked['config_digest'] and image['rootfs_diff_ids']==checked['rootfs_diff_ids'] and image['platform']==checked['platform'])
    receipt={'schema':'engine-clock-image-candidate-v1','status':'IMAGE_CANDIDATE_PREPARED','request_id':request['request_id'],'activation_sha':context['activation_sha'],'source_sha':context['source_sha'],'run_id':context['run_id'],'workflow_id':context['workflow_id'],'request_sha256':context['request_sha256'],'source_closure_verified':context['source_closure_verified'],'image_tar_sha256':checked['image_tar_sha256'],'image_tar_nbytes':checked['image_tar_nbytes'],'config_digest':checked['config_digest'],'rootfs_diff_ids':checked['rootfs_diff_ids'],'platform':checked['platform'],'archive_layout':checked['archive_layout'],'lock_sha256':EFFECTIVE_SHA,'full_input_lock_sha256':INPUT_SHA,'renderer_lock_sha256':RENDERER_SHA,'python_layout_sha256':LAYOUT_SHA,'recipe_sha256':staged['recipe_sha256'],'installed_files_sha256':hashlib.sha256(raw).hexdigest(),'installed_files_nbytes':len(raw),'candidate_summary':summary,'launch':collection['launch'],'host':engine.host,'engine':engine.profile,'native_admission':False,'installed_runtime_verified':False,'image_preparation_ready':False,'official_model_calls':0,'scientific_result_promoted':False}
    (image_dir/'preparation.json').write_bytes(canonical(receipt))
    _need(sum(p.stat().st_size for p in image_dir.iterdir())+MIB<=2*GIB)
    return receipt


def authenticate_delta(client,request,head,tree=None,prefix='activation'):
    """Actual API commit/compare binds the sole added request."""
    source=request['reviewed_source_sha'];cfg=ROLES[request['role']]
    commit=client.get_json('git/commits/'+head,prefix+'-commit.json')
    _need(commit['sha']==head and [p['sha'] for p in commit['parents']]==[source])
    if tree is not None:_need(commit['tree']['sha']==tree)
    comparison=client.get_json('compare/'+source+'...'+head,prefix+'-compare.json')
    _need(comparison['status']=='ahead' and comparison['ahead_by']==1 and comparison['behind_by']==0 and comparison['total_commits']==1 and comparison['base_commit']['sha']==source and comparison['merge_base_commit']['sha']==source and len(comparison['commits'])==1 and comparison['commits'][0]['sha']==head)
    _need(len(comparison['files'])==1 and comparison['files'][0]['filename']==cfg['request_path'] and comparison['files'][0]['status']=='added')


def authenticate_image(client,request,work,root):
    import base64
    image=request['image_evidence'];ex=image['expected'];rid=ex['run_id']
    proofs={}
    for key,endpoint in [('run','actions/runs/'+str(rid)),('jobs','actions/runs/'+str(rid)+'/jobs?per_page=100'),('artifacts','actions/runs/'+str(rid)+'/artifacts?per_page=100'),('workflow','actions/workflows/'+str(ex['workflow_id'])),('unique_runs','actions/workflows/'+str(ex['workflow_id'])+'/runs?branch='+ex['branch']+'&event=push&per_page=100')]:
        proofs[key]=client.get_json(endpoint,'producer-'+key+'.json')
    content=client.get_json('contents/'+ROLES['prepare']['request_path']+'?ref='+ex['activation_sha'],'producer-request-content.json')
    _need(content['type']=='file' and content['encoding']=='base64' and content['path']==ROLES['prepare']['request_path'])
    raw=base64.b64decode(content['content'],validate=False);producer=validate_request(parse(raw),'prepare',root)
    _need(producer['reviewed_source_sha']==request['reviewed_source_sha'] and producer['source_closure']==request['source_closure'] and producer['source_ci']==request['source_ci'])
    authenticate_delta(client,producer,ex['activation_sha'],prefix='producer')
    payloads=Path(work).parent/'producer-transport';payloads.mkdir(mode=0o700)
    zpath=payloads/'producer-original-artifact.zip'
    client.download('https://api.github.com/repos/'+REPOSITORY+'/actions/artifacts/'+str(ex['artifact_id'])+'/zip',zpath,nbytes=ex['artifact_zip_nbytes'],sha256=ex['artifact_zip_sha256'],kind='artifact')
    directory=payloads/'authenticated-image';bundle=archive.extract_image_bundle(zpath,directory)
    _need(bundle['files']['preparation.json']['sha256']==image['candidate_receipt_sha256'] and bundle['files']['installed-files.json']=={'sha256':ex['installed_files_sha256'],'nbytes':image['installed_files_nbytes']})
    receipt=parse(read_regular(directory/'preparation.json'));_need(receipt['run_id']==rid and receipt['workflow_id']==ex['workflow_id'] and receipt['request_sha256']==hashlib.sha256(raw).hexdigest() and receipt['source_closure_verified'] is True)
    _need(receipt['recipe_sha256']==hashlib.sha256(read_regular(Path(root)/'docker/engine-clock-sealed-image.Dockerfile')).hexdigest())
    checked=archive.validate_preparation(receipt,proofs,directory/'image.tar',expected=ex);checked['external_api_origin_authenticated']=True
    manifest_raw=read_regular(directory/'installed-files.json')
    manifest=inventory.core.validate_inventory(parse(manifest_raw));_need(inventory.core._canonical(manifest)==manifest_raw)
    (work/'producer-authentication.json').write_bytes(canonical(checked))
    return directory,receipt,manifest_raw,checked


def run_operation(role):
    from scripts.engine_clock_image_backend_v2 import Docker
    from scripts.engine_clock_image_staging_v3 import stage_inputs,RetainedClient
    started=time.perf_counter();cfg=ROLES[role];root=Path(__file__).resolve().parent.parent
    def git(*args):
        r=subprocess.run(['git','-C',str(root),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
        _need(r.returncode==0 and len(r.stdout)<=16*MIB);return r.stdout
    raw=read_regular(root/cfg['request_path']);request=validate_request(parse(raw),role,root)
    output=root/cfg['output'];output.mkdir(parents=True,mode=0o700,exist_ok=False)
    work=output/'execution';work.mkdir(mode=0o700);(work/'consumed-request.json').write_bytes(raw)
    stop=started+request['budget']['total_seconds'];status='FAILED_OR_INCOMPLETE';stage='activation'
    try:
        head=git('rev-parse','HEAD').decode().strip();_need(head==os.environ['GITHUB_SHA'] and not git('status','--porcelain','--untracked-files=no'))
        header=git('cat-file','-p',head).split(b'\n\n',1)[0].splitlines();parents=[r[7:].decode() for r in header if r.startswith(b'parent ')]
        mode=git('ls-tree',head,'--',cfg['request_path']).decode().split()[0]
        validate_activation(request,head,parents,b'A\0'+cfg['request_path'].encode()+b'\0',mode,os.environ['GITHUB_REF_NAME'])
        for path,sha in request['source_closure'].items():_need(hashlib.sha256(read_regular(root/path)).hexdigest()==sha)
        client=RetainedClient(work/'api',repository=REPOSITORY,token=os.environ['GH_TOKEN'],deadline=min(stop,started+request['budget']['download_seconds']),max_requests=request['budget']['http_gets'],max_payload_bytes=request['budget']['payload_bytes'])
        ctx={'repository':REPOSITORY,'event':os.environ['GITHUB_EVENT_NAME'],'attempt':int(os.environ['GITHUB_RUN_ATTEMPT']),'run_id':int(os.environ['GITHUB_RUN_ID']),'head_sha':head}
        rid=ctx['run_id'];run=client.get_json('actions/runs/'+str(rid),'live-run.json');wid=run['workflow_id']
        wf=client.get_json('actions/workflows/'+str(wid),'live-workflow.json')
        unique,visibility=observe_unique(client,'actions/workflows/'+str(wid)+'/runs?branch='+cfg['branch']+'&event=push&per_page=100')
        validate_live_run(request,ctx,run,wf,unique)
        authenticate_delta(client,request,head,git('rev-parse','HEAD^{tree}').decode().strip())
        proofs=[]
        for ci in request['source_ci']:
            id=str(ci['run_id']);prefix='source-'+ci['event']
            proofs.append({key:client.get_json(endpoint,prefix+'-'+key+'.json') for key,endpoint in [('run','actions/runs/'+id),('jobs','actions/runs/'+id+'/jobs?per_page=100'),('artifacts','actions/runs/'+id+'/artifacts?per_page=100')]})
        validate_source_ci(request,proofs)
        context={'workflow_visibility':visibility,'activation_sha':head,'source_sha':request['reviewed_source_sha'],'run_id':rid,'workflow_id':wid,'request_sha256':hashlib.sha256(raw).hexdigest(),'source_closure_verified':True,'authenticated_api_origin':'https://api.github.com'}
        (work/'source-authentication.json').write_bytes(canonical(context))
        stage='engine-qualification';engine=Docker(work/'docker',deadline=stop,source_root=root);engine.qualify(output)
        if role=='prepare':
            stage='single-image-preparation'
            receipt=prepare_image(request,context,work,engine=engine,stage=lambda r,c,w:stage_inputs(r,c,w,client=client,root=root))
            status=receipt['status']
        else:
            stage='producer-authentication';directory,producer,manifest_raw,checked=authenticate_image(client,request,work,root)
            stage='single-image-preflight';image=engine.load(directory/'image.tar',producer['config_digest'],producer['rootfs_diff_ids'])
            result=engine.collect(image,request,expected_manifest=manifest_raw,precheck=True)
            _need(result['summary']['complete'] is True and result['summary']['native_admission'] is False and result['summary']['official_model_calls']==0 and result['summary']['canonical_manifest_sha256']==producer['installed_files_sha256'])
            receipt={'schema':'engine-clock-image-preflight-v1','status':'AUTHENTICATED_INSTALLED_IMAGE_MATCH','request_id':request['request_id'],**context,'producer_run_id':producer['run_id'],'producer_artifact_id':request['image_evidence']['expected']['artifact_id'],'config_digest':image['config_digest'],'image_tar_sha256':checked['archive']['image_tar_sha256'],'installed_files_sha256':producer['installed_files_sha256'],'collector':result,'host':engine.host,'engine':engine.profile,'producer_host':producer['host'],'producer_engine':producer['engine'],'producer_host_equal':producer['host']==engine.host,'producer_engine_equal':producer['engine']==engine.profile,'installed_runtime_verified':True,'native_admission':False,'official_model_calls':0,'scientific_result_promoted':False}
            (work/'preflight.json').write_bytes(canonical(receipt));status=receipt['status']
        return 0
    except Exception as exc:
        if role=='prepare':
            image=output/'image';image.mkdir(mode=0o700,exist_ok=True)
            failure={'schema':'engine-clock-image-candidate-v1','status':'FAILED_OR_INCOMPLETE','request_id':request['request_id'],'failure_stage':stage,'error_type':type(exc).__name__,'image_tar_sha256':None,'config_digest':None,'installed_files_sha256':None,'image_preparation_ready':False,'installed_runtime_verified':False,'native_admission':False,'official_model_calls':0}
            if not (image/'preparation.json').exists():(image/'preparation.json').write_bytes(canonical(failure))
        return 1
    finally:
        report={'schema':'engine-clock-image-operation-result-v1','status':status,'role':role,'request_id':request['request_id'],'last_stage':stage,'elapsed_seconds':time.perf_counter()-started,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'native_admission':False,'official_model_calls':0}
        (work/'result.json').write_bytes(canonical(report));print(json.dumps(report,sort_keys=True))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true',required=True);parser.add_argument('--role',choices=sorted(ROLES),required=True);args=parser.parse_args(argv)
    try:
        _need(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_REPOSITORY')==REPOSITORY and os.environ.get('GITHUB_EVENT_NAME')=='push' and os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and os.environ.get('GITHUB_REF_NAME')==ROLES[args.role]['branch'])
        return run_operation(args.role)
    except Exception:print('IMAGE_OPERATION_REJECTED');return 1


if __name__=='__main__':raise SystemExit(main())
