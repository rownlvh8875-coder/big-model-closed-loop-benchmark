"""New sealed-image canary protocol. Import performs no native/API/Docker action."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
from scripts import engine_clock_image_preparation_v5 as image
from scripts import engine_clock_runtime_contract as contract

REPOSITORY=image.REPOSITORY
SOURCE_BRANCH='diagnostic/engine-clock-sealed-native-v1'
ID='sealed-native-20261114-01'
BRANCH='diagnostic/engine-clock-'+ID
REQUEST='docs/requests/engine-clock-'+ID+'.json'
WORKFLOW='.github/workflows/engine-clock-sealed-native-v1.yml'
OUTPUT='output/stage7-sealed-native/'+ID
AUTH='docs/evidence/engine-clock-sealed-image-06/'
MIB=1024**2
BUDGET=dict(total_seconds=1800,download_seconds=300,archive_seconds=180,load_seconds=180,
            prestart_seconds=180,container_seconds=780,child_seconds=420,native_seconds=120,
            inventory_seconds=180,cleanup_seconds=12,http_gets=64,payload_bytes=2*1024**3,
            execution_bytes=2*1024**3-16*MIB,copy_archive_bytes=512*MIB,
            minimum_free_union_bytes=16*1024**3,case_bytes=192*MIB,cache_bytes=64*MIB,
            cache_files=1024,ledger_bytes=2*MIB,log_bytes=MIB,providers=1,containers=1,
            image_loads=1,workflow_visibility_seconds=30,workflow_visibility_snapshots=6,
            workflow_visibility_interval_seconds=5)
NATIVE_BUDGET=dict(providers=1,capture_pairs=6,task_steps=12,ram_reads=12,
                   texture_readings=24,texture_getters=48,clock_snapshots=48,
                   clock_getters=96,observer_getters=144,extra_gpu_reads=0,
                   extra_gl_getters=0,official_model_calls=0,ort_sessions=0)
NATIVE_BUDGET.update(maps_snapshots=4,module_origin_snapshots=2)
EXTRA_PATHS={
 'scripts/engine_clock_runtime_contract.py','tests/test_engine_clock_runtime_contract.py',
 'scripts/engine_clock_sealed_native.py','scripts/engine_clock_sealed_native_run.py',
 'scripts/engine_clock_sealed_native_container.py','tests/test_engine_clock_sealed_native.py',
 WORKFLOW,'docs/superpowers/specs/2026-11-14-engine-clock-sealed-native-design.md',
 'docs/superpowers/plans/2026-11-14-engine-clock-sealed-native.md',
 *[AUTH+p for p in ('preparation.json','preparation-request.json','preflight-request.json',
                    'installed-files.json','root-acceptance.json')]}


def need(value):
    if not value:raise ValueError('SEALED_NATIVE_REJECTED')


def exact(a,b):
    return type(a) is type(b) and (set(a)==set(b) and all(exact(a[k],b[k]) for k in a) if isinstance(a,dict)
           else len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b)) if isinstance(a,list) else a==b)


def canonical(value):
    return image.canonical(value)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def image_evidence(root):
    raw=image.read_regular(Path(root)/(AUTH+'preflight-request.json'))
    need(sha(raw)=='c474a7380d20cb6d56f36a63473bbb1ae851e58ef81b137d37d6bf3597d3e18d')
    return image.parse(raw)['image_evidence']


def source_paths(root):
    # Read the frozen literal registry without importing NumPy or native packages.
    tree=ast.parse(image.read_regular(Path(root)/'bigbench/first_divergence.py'))
    values={}
    for node in tree.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in ('FROZEN_SOURCE_PINS','EXISTING_BIGBENCH_PINS','PRODUCER_SOURCE_PATHS'):
                    values[target.id]=ast.literal_eval(node.value)
    need(len(values)==3)
    old=set().union(*(set(v) for v in values.values()))
    old.update({'scripts/texture_generation_markers.py','tests/test_texture_generation_markers.py',
                '.github/workflows/stage7-texture-generation-markers.yml',
                'scripts/engine_clock_boundaries.py','tests/test_engine_clock_boundaries.py',
                'scripts/engine_clock_native.py','tests/test_engine_clock_native.py',
                '.github/workflows/stage7-engine-clock-boundaries.yml'})
    need(len(old)==70)
    return frozenset(old|set(image.source_paths(root))|EXTRA_PATHS)


def verify_sources(root,snapshot):
    root=Path(root)
    for name,digest in snapshot.items():
        need(type(name) is str and not name.startswith('/') and all(p not in ('','.','..') for p in name.split('/')))
        current=root
        for part in name.split('/'):
            current=current/part;need(not current.is_symlink())
        need(sha(image.read_regular(current))==digest)


def validate_request(value,root):
    need(type(value) is dict and set(value)=={'schema','request_id','repository','branch','workflow_path',
         'reviewed_source_branch','reviewed_source_sha','source_closure','source_ci','budget',
         'native_budget','image_evidence','official_model_calls','ort_sessions'})
    for key,want in dict(schema='engine-clock-sealed-native-request-v1',request_id=ID,
        repository=REPOSITORY,branch=BRANCH,workflow_path=WORKFLOW,reviewed_source_branch=SOURCE_BRANCH,
        budget=BUDGET,native_budget=NATIVE_BUDGET,image_evidence=image_evidence(root),
        official_model_calls=0,ort_sessions=0).items():need(exact(value[key],want))
    need(image._hex(value['reviewed_source_sha'],40))
    need(type(value['source_closure']) is dict and set(value['source_closure'])==source_paths(root)
         and all(image._hex(v) for v in value['source_closure'].values()))
    ci=value['source_ci'];need(type(ci) is list and len(ci)==2 and [r.get('event') for r in ci]==['push','pull_request'])
    need(all(set(r)=={'event','run_id'} and type(r['run_id']) is int and r['run_id']>0 for r in ci) and ci[0]['run_id']!=ci[1]['run_id'])
    return value


def validate_activation(request,head,parents,changes,mode,branch):
    need(image._hex(head,40) and head!=request['reviewed_source_sha'] and parents==[request['reviewed_source_sha']]
         and changes==b'A\0'+REQUEST.encode()+b'\0' and mode=='100644' and branch==BRANCH)


def validate_source_ci(request,proofs):
    need(type(proofs) is list and len(proofs)==2)
    for ci,p in zip(request['source_ci'],proofs):
        r=p['run'];jobs=p['jobs'];arts=p['artifacts'];rid=ci['run_id']
        need(exact(r['id'],rid) and r['head_sha']==request['reviewed_source_sha'] and r['head_branch']==SOURCE_BRANCH
             and r['event']==ci['event'] and r['path']=='.github/workflows/ci.yml' and exact(r['run_attempt'],1)
             and r['status']=='completed' and r['conclusion']=='success' and r['repository']['full_name']==REPOSITORY)
        need(exact(jobs['total_count'],2) and len(jobs['jobs'])==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'}
             and all(exact(j['run_id'],rid) and j['status']=='completed' and j['conclusion']=='success' for j in jobs['jobs']))
        need(exact(arts['total_count'],0) and arts['artifacts']==[])


def validate_live(request,context,run,workflow,unique):
    need(context['repository']==REPOSITORY and context['event']=='push' and exact(context['attempt'],1)
         and type(context['run_id']) is int and context['run_id']>0 and image._hex(context['head_sha'],40))
    need(exact(run['id'],context['run_id']) and run['head_sha']==context['head_sha'] and run['head_branch']==BRANCH
         and run['path']==WORKFLOW and run['event']=='push' and exact(run['run_attempt'],1)
         and run['status']=='in_progress' and run['repository']['full_name']==REPOSITORY)
    need(type(run['workflow_id']) is int and workflow['id']==run['workflow_id'] and workflow['path']==WORKFLOW and workflow['state']=='active')
    need(exact(unique['total_count'],1) and len(unique['workflow_runs'])==1
         and unique['workflow_runs'][0]['id']==run['id'] and unique['workflow_runs'][0]['head_sha']==run['head_sha']
         and exact(unique['workflow_runs'][0]['run_attempt'],1))


def environment_profile():
    return dict(PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                LIBGL_ALWAYS_SOFTWARE='1',PYOPENGL_PLATFORM='glx',OMP_NUM_THREADS='2',
                HOME='/tmp',TMPDIR='/tmp',LANG='C.UTF-8',LC_ALL='C.UTF-8',
                HOSTNAME='stage7-sealed-native',GITHUB_ACTIONS='true',RUNNER_TEMP='/work')


def check_environment(environment,role):
    env=dict(environment);need(role in ('parent','child'))
    if role=='child':
        need(re.fullmatch('[1-9][0-9]*',env.pop('FIRST_DIVERGENCE_TRIAL_FD','')) is not None)
        need(env.pop('MESA_SHADER_CACHE_DIR','')=='/work/cache/case_00')
        # xvfb-run owns these per-process routes; no native selector is discarded.
        display=env.pop('DISPLAY',None);auth=env.pop('XAUTHORITY',None)
        if display is not None:need(re.fullmatch(':[0-9]+',display) is not None)
        if auth is not None:need(re.fullmatch('/tmp/xvfb-run\.[A-Za-z0-9]+/Xauthority',auth) is not None)
        if 'PWD' in env:need(env.pop('PWD')=='/work/repo')
    need(exact(env,environment_profile()))
    return env


def validate_permit(p,*,ancestors,group,nonce,binding_sha,identity_sha):
    need(type(p) is dict and set(p)=={'schema','parent_pid','parent_uuid','process_group','nonce','binding_sha256','identity_sha256'})
    need(p['schema']=='engine-clock-sealed-native-permit-v1' and type(p['parent_pid']) is int and p['parent_pid']>0
         and p['parent_pid'] in ancestors and type(group) is int and group>1 and exact(p['process_group'],group)
         and image._hex(p['parent_uuid'],32) and image._hex(nonce) and p['nonce']==nonce
         and image._hex(binding_sha) and p['binding_sha256']==binding_sha
         and image._hex(identity_sha) and p['identity_sha256']==identity_sha)
    return p


def make_identity(receipt,expected,host,engine):
    core=dict(image=dict(distribution='actions-docker-save-v1',artifact_id=expected['artifact_id'],
         artifact_zip_sha256=expected['artifact_zip_sha256'],image_tar_sha256=receipt['image_tar_sha256'],
         config_digest=receipt['config_digest'],rootfs_diff_ids=receipt['rootfs_diff_ids'],platform='linux/amd64',
         installed_files_sha256=receipt['installed_files_sha256'],build_recipe_sha256=receipt['recipe_sha256'],
         lock_sha256=receipt['lock_sha256'],assets_zip_sha256=contract.ASSETS_SHA256),
         versions=dict(contract.VERSIONS),host=host,engine=engine,
         configuration=dict(contract.CONFIGURATION,render_env=dict(contract.RENDER_ENV),
                            environment_profile_sha256=sha(contract._encode(environment_profile()))))
    return contract.validate_identity(dict(schema='engine-clock-installed-identity-v1',core=core,core_sha256=sha(contract._encode(core))))


CONTAINER_COMMAND=['-I','-S','-B','/work/repo/scripts/engine_clock_sealed_native_container.py','parent']
TMPFS='rw,nosuid,nodev,noexec,size=67108864,mode=0700'


def validate_launch(raw,routes,expected):
    """Validate sensitive inspect in memory; return only reviewed safe fields."""
    h=raw['HostConfig'];c=raw['Config']
    need(image._hex(raw['Id']) and raw['Image']==expected['config_digest'])
    wanted=dict(ReadonlyRootfs=True,NetworkMode='none',Privileged=False,CapDrop=['ALL'],
                SecurityOpt=['no-new-privileges'],PidMode='',IpcMode='private',PidsLimit=128,
                Memory=2147483648,NanoCpus=2000000000,Tmpfs={'/tmp':TMPFS})
    for key,value in wanted.items():need(exact(h[key],value))
    for key in ('CapAdd','Devices','DeviceRequests','Binds','GroupAdd','ExtraHosts','PortBindings'):
        need(not h.get(key))
    env={}
    for row in c['Env']:
        key,sep,value=row.partition('=');need(sep and key not in env);env[key]=value
    check_environment(env,'parent')
    for key,value in dict(Entrypoint=['/opt/venv/bin/python'],Cmd=CONTAINER_COMMAND,User='0:0',
                         WorkingDir='/work/repo',Hostname='stage7-sealed-native',Tty=False,OpenStdin=False).items():need(exact(c[key],value))
    need(c['Labels']=={'stage7.request':ID,'stage7.nonce':expected['nonce'],'stage7.source':expected['source_sha'],
                       'org.opencontainers.image.version':'24.04'})
    want_mounts={('/work/'+k):dict(type='bind',source=routes[k],rw=k in ('output','cache')) for k in routes}
    need(set(routes)=={'repo','binding','output','cache'})
    want_mounts['/tmp']=dict(type='tmpfs',source='',rw=True)
    mounts={}
    for row in raw['Mounts']:
        dest=row['Destination'];need(dest not in mounts)
        mounts[dest]=dict(type=row['Type'],source=row['Source'],rw=row['RW'])
        if row['Type']=='bind':need(row.get('Propagation')=='rprivate')
    need(exact(mounts,want_mounts))
    return dict(validated=True,container_id=raw['Id'],image_id=raw['Image'],host_configuration=wanted,
                mounts=mounts,environment=env,command=CONTAINER_COMMAND,labels=c['Labels'])
