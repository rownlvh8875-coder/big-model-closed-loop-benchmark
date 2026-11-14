"""Separate immutable C/ABBA campaign admission; no actions occur on import."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from scripts import engine_clock_image_preparation_v5 as image
from scripts import engine_clock_runtime_contract as contract

REPOSITORY=image.REPOSITORY
SOURCE_BRANCH='fix/engine-clock-held-abba-members-v3'
ID='held-abba-20261114-03'
BRANCH='diagnostic/engine-clock-'+ID
C_REQUEST='docs/requests/engine-clock-'+ID+'-canary.json'
A_REQUEST='docs/requests/engine-clock-'+ID+'-abba.json'
REQUEST=C_REQUEST
WORKFLOW='.github/workflows/engine-clock-held-abba-v3.yml'
OUTPUT='output/stage7-held-abba/'+ID
AUTH='docs/evidence/engine-clock-sealed-image-06/'
MIB=1024**2
BUDGET=dict(total_seconds=2400,download_seconds=600,archive_seconds=180,load_seconds=180,
            prestart_seconds=180,container_seconds=1800,child_seconds=420,native_seconds=120,
            inventory_seconds=180,cleanup_seconds=12,http_gets=64,payload_bytes=3*1024**3,
            execution_bytes=2*1024**3-16*MIB,copy_archive_bytes=512*MIB,
            minimum_free_union_bytes=16*1024**3,case_bytes=192*MIB,cache_bytes=64*MIB,
            cache_files=1024,ledger_bytes=2*MIB,log_bytes=MIB,providers=4,containers=1,
            image_loads=1,workflow_visibility_seconds=30,workflow_visibility_snapshots=6,
            workflow_visibility_interval_seconds=5)
NATIVE_BUDGET=dict(providers=1,capture_pairs=6,task_steps=12,ram_reads=12,
                   texture_readings=24,texture_getters=48,clock_snapshots=48,
                   clock_getters=96,observer_getters=144,extra_gpu_reads=0,
                   extra_gl_getters=0,official_model_calls=0,ort_sessions=0)
BUDGET.update(memory_bytes=4294967296,minimum_host_memory_bytes=6*1024**3,
    phase_files=dict(canary=129,abba=256),phase_entries=dict(canary=256,abba=512))
NATIVE_BUDGET.update(maps_snapshots=4,module_origin_snapshots=2,memory_snapshots=4)
LIFECYCLE=dict(total_seconds=6000,control_seconds=900,control_interval=5,control_snapshots=181,
    control_http_gets=256,control_json_bytes=64*MIB,attestor_seconds=1500,attestor_wait_seconds=900,
    attestor_http_gets=256,attestor_zip_bytes=512*MIB,attestor_decoded_bytes=1024*MIB,attestor_members=256,
    run_visibility_seconds=60,run_visibility_snapshots=13,run_visibility_interval_seconds=5,
    caller_visibility_seconds=30,caller_visibility_snapshots=7)
C_STEP='Run sealed canary C'
C_UPLOAD='Upload original canary C'
EXTRA_PATHS={
 'scripts/engine_clock_held_abba_v3.py','scripts/engine_clock_held_abba_v3_run.py',
 'scripts/engine_clock_held_abba_v3_container.py','scripts/engine_clock_held_abba_v3_archive.py',
 'scripts/engine_clock_held_abba_v3_lifecycle.py','scripts/engine_clock_held_abba_v3_attest.py',
 'tests/test_engine_clock_held_abba_v3.py','tests/test_engine_clock_held_abba_v3_lifecycle.py',
 'tests/test_engine_clock_held_abba_v3_execution.py',WORKFLOW,
 'docs/superpowers/specs/2026-11-14-engine-clock-held-abba-members-design.md',
 'docs/superpowers/plans/2026-11-14-engine-clock-held-abba-members.md',
 'docs/evidence/engine-clock-held-abba-01/terminal-failure/selected/engine-clock-held-abba-20261114-01-canary/api/live-run.json',
 'docs/evidence/engine-clock-held-abba-02/abba/engine-clock-held-abba-20261114-02-abba.members.json'}


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
    from scripts import engine_clock_held_abba_v2 as previous
    return frozenset(previous.source_paths(root)|EXTRA_PATHS)


def audit_phase_members(root,mode):
    """Bound only phase membership/stat bytes; case content has separate validators."""
    stage='mode'
    try:
        schedule(mode);file_limit=BUDGET['phase_files'][mode];entry_limit=BUDGET['phase_entries'][mode]
        root=Path(root);stage='root';need(root.is_dir() and not root.is_symlink())
        stage='phase-route';need((root/'phase.json').is_file() and not (root/'phase.json').is_symlink())
        files=set();directories=set();total=0;entries=0
        for path in root.rglob('*'):
            stage='entries';entries+=1;need(entries<=entry_limit)
            stage='entry-type';info=path.lstat()
            need(stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode))
            relative=path.relative_to(root).as_posix()
            if stat.S_ISDIR(info.st_mode):directories.add(relative);continue
            need(info.st_nlink==1)
            stage='files';files.add(relative);need(len(files)<=file_limit)
            stage='bytes';need(info.st_size>=0);total+=info.st_size;need(total<=BUDGET['case_bytes'])
        stage='directories'
        expected={parent.as_posix() for name in files for parent in Path(name).parents if parent!=Path('.')}
        need(directories==expected)
        return dict(status='BOUNDED_PHASE_MEMBER_SNAPSHOT',mode=mode,files=len(files),entries=entries,
            nbytes_before_final_phase_ledger=total,before_final_phase_ledger=True,
            file_limit=file_limit,entry_limit=entry_limit,byte_limit=BUDGET['case_bytes'],
            case_content_verified_here=False)
    except (OSError,ValueError,KeyError,TypeError):
        raise ValueError('PHASE_MEMBERS_REJECTED:'+stage) from None


def verify_sources(root,snapshot):
    root=Path(root)
    for name,digest in snapshot.items():
        need(type(name) is str and not name.startswith('/') and all(p not in ('','.','..') for p in name.split('/')))
        current=root
        for part in name.split('/'):
            current=current/part;need(not current.is_symlink())
        need(sha(image.read_regular(current))==digest)


def validate_request(value,root):
    need(type(value) is dict and set(value)=={'lifecycle','mode','acceptance','schema','request_id','repository','branch','workflow_path',
         'reviewed_source_branch','reviewed_source_sha','source_closure','source_ci','budget',
         'native_budget','image_evidence','official_model_calls','ort_sessions'})
    for key,want in dict(schema=REQUEST_SCHEMA,request_id=ID,
        repository=REPOSITORY,branch=BRANCH,workflow_path=WORKFLOW,reviewed_source_branch=SOURCE_BRANCH,
        budget=BUDGET,lifecycle=LIFECYCLE,native_budget=native_budget(value['mode']),image_evidence=image_evidence(root),
        official_model_calls=0,ort_sessions=0).items():need(exact(value[key],want))
    need(image._hex(value['reviewed_source_sha'],40))
    if value['mode']=='canary':need(value['acceptance'] is None)
    else:validate_acceptance(value['acceptance'],value['reviewed_source_sha'])
    need(type(value['source_closure']) is dict and set(value['source_closure'])==source_paths(root)
         and all(image._hex(v) for v in value['source_closure'].values()))
    ci=value['source_ci'];need(type(ci) is list and len(ci)==2 and [r.get('event') for r in ci]==['push','pull_request'])
    need(all(set(r)=={'event','run_id'} and type(r['run_id']) is int and r['run_id']>0 for r in ci) and ci[0]['run_id']!=ci[1]['run_id'])
    return value


def validate_activation(request,head,parents,changes,mode,branch):
    accepted=request['acceptance']
    parent=request['reviewed_source_sha'] if request['mode']=='canary' else accepted['canary_head_sha']
    delta=b'A';path=C_REQUEST if request['mode']=='canary' else A_REQUEST
    need(image._hex(head,40) and head!=parent and parents==[parent]
         and changes==delta+b'\0'+path.encode()+b'\0' and mode=='100644' and branch==BRANCH)


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
    need(exact(unique['total_count'],1) and len(unique['workflow_runs'])==1)
    current=unique['workflow_runs'][0]
    need(current['id']==run['id'] and current['head_sha']==run['head_sha'] and exact(current['run_attempt'],1))


def environment_profile():
    return dict(PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                LIBGL_ALWAYS_SOFTWARE='1',PYOPENGL_PLATFORM='glx',OMP_NUM_THREADS='2',
                HOME='/tmp',TMPDIR='/tmp',LANG='C.UTF-8',LC_ALL='C.UTF-8',
                HOSTNAME='stage7-sealed-native',GITHUB_ACTIONS='true',RUNNER_TEMP='/work')


CV2_LD_LIBRARY_PATH='/opt/venv/lib/python3.11/site-packages/cv2/../../lib64:'


def environment_identity():
    return dict(launch=environment_profile(),post_cv2=dict(environment_profile(),LD_LIBRARY_PATH=CV2_LD_LIBRARY_PATH),
                child_launch_policy='validated-preimport-snapshot-v1',container_resources=dict(memory_bytes=4294967296,nano_cpus=2000000000,pids_limit=128,cgroup_namespace='private'),selection_policy='image-source-and-indexed-runtime-data-v1',campaign_policy='held-C-completion-plus-terminal-attestor-plus-root-fresh-before-A-v1')


def check_post_import_environment(environment,role):
    observed=dict(environment)
    need(observed.pop('LD_LIBRARY_PATH',None)==CV2_LD_LIBRARY_PATH)
    return check_environment(observed,role)


def check_environment(environment,role):
    env=dict(environment);need(role in ('parent','child'))
    if role=='child':
        need(re.fullmatch('[1-9][0-9]*',env.pop('FIRST_DIVERGENCE_TRIAL_FD','')) is not None)
        need(re.fullmatch(r'/work/cache/case_0[0-3]',env.pop('MESA_SHADER_CACHE_DIR','')) is not None)
        # xvfb-run owns these per-process routes; no native selector is discarded.
        display=env.pop('DISPLAY',None);auth=env.pop('XAUTHORITY',None)
        if display is not None:need(re.fullmatch(':[0-9]+',display) is not None)
        if auth is not None:need(re.fullmatch(r'/tmp/xvfb-run\.[A-Za-z0-9]+/Xauthority',auth) is not None)
        if 'PWD' in env:need(env.pop('PWD')=='/work/repo')
    need(exact(env,environment_profile()))
    return env


def validate_permit(p,*,ancestors,group,nonce,binding_sha,identity_sha,mode,index):
    need(type(p) is dict and set(p)=={'mode','index','schema','parent_pid','parent_uuid','process_group','nonce','binding_sha256','identity_sha256'})
    need(p['schema']=='engine-clock-sealed-abba-permit-v1' and exact(p['mode'],mode) and exact(p['index'],index) and 0<=index<len(schedule(mode)) and type(p['parent_pid']) is int and p['parent_pid']>0
         and p['parent_pid'] in ancestors and type(group) is int and group>1 and exact(p['process_group'],group)
         and image._hex(p['parent_uuid'],32) and image._hex(nonce) and p['nonce']==nonce
         and image._hex(binding_sha) and p['binding_sha256']==binding_sha
         and image._hex(identity_sha) and p['identity_sha256']==identity_sha)
    return p


def identity_from_profiles(receipt,expected,host,engine,details):
    core=dict(image=dict(distribution='actions-docker-save-v1',artifact_id=expected['artifact_id'],
         artifact_zip_sha256=expected['artifact_zip_sha256'],image_tar_sha256=receipt['image_tar_sha256'],
         config_digest=receipt['config_digest'],rootfs_diff_ids=receipt['rootfs_diff_ids'],platform='linux/amd64',
         installed_files_sha256=receipt['installed_files_sha256'],build_recipe_sha256=receipt['recipe_sha256'],
         lock_sha256=receipt['lock_sha256'],assets_zip_sha256=contract.ASSETS_SHA256),
         versions=dict(contract.VERSIONS),host=host,engine=engine,
         configuration=dict(contract.CONFIGURATION,render_env=dict(contract.RENDER_ENV),
                            environment_profile_sha256=sha(contract._encode(environment_identity()))))
    installed=contract.validate_identity(dict(schema='engine-clock-installed-identity-v1',core=core,core_sha256=sha(contract._encode(core))))
    need(type(details) is dict and set(details)=={'affinity_ids','memory_total_bytes'})
    ids=details['affinity_ids'];memory=details['memory_total_bytes']
    need(type(ids) is list and ids==sorted(set(ids)) and len(ids)==host['affinity_cpus']
        and all(type(v) is int and 0<=v<2**20 for v in ids)
        and type(memory) is int and BUDGET['minimum_host_memory_bytes']<=memory<2**63)
    value=dict(installed_identity=installed,host_details=details)
    return dict(schema='engine-clock-held-abba-identity-v3',**value,core_sha256=sha(canonical(value)))


def make_identity(receipt,expected,host,engine):
    return identity_from_profiles(receipt,expected,host,engine,host_details())


CONTAINER_COMMAND=['-I','-S','-B','/work/repo/scripts/engine_clock_held_abba_v3_container.py','parent']
TMPFS='rw,nosuid,nodev,noexec,size=67108864,mode=0700'


def validate_launch(raw,routes,expected):
    """Validate sensitive inspect in memory; return only reviewed safe fields."""
    h=raw['HostConfig'];c=raw['Config']
    need(image._hex(raw['Id']) and raw['Image']==expected['config_digest'])
    wanted=dict(ReadonlyRootfs=True,NetworkMode='none',Privileged=False,CapDrop=['ALL'],
                SecurityOpt=['no-new-privileges'],PidMode='',IpcMode='private',CgroupnsMode='private',PidsLimit=128,
                Memory=4294967296,NanoCpus=2000000000,Tmpfs={'/tmp':TMPFS})
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
    # Docker28 reports --tmpfs in HostConfig.Tmpfs alone. Its exact options
    # were already checked above; Mounts may additionally project that same /tmp.
    if '/tmp' not in mounts:want_mounts.pop('/tmp')
    need(exact(mounts,want_mounts))
    return dict(validated=True,container_id=raw['Id'],image_id=raw['Image'],host_configuration=wanted,
                mounts=mounts,environment=env,command=CONTAINER_COMMAND,labels=c['Labels'])


def launch_diagnostics(raw,routes,expected):
    """Bounded equality facts only; never disclose arbitrary inspect strings."""
    result=dict(schema='sealed-native-launch-diagnostics-v1',gate_passed=False,failed=[],
                host={},config={},environment={},labels_match=False,mounts={},unknown_mounts=0)
    def check(code,ok):
        if not ok:result['failed'].append(code)
        return bool(ok)
    try:
        h=raw['HostConfig'];c=raw['Config']
        check('container_id',image._hex(raw['Id']))
        check('image_id',raw['Image']==expected['config_digest'])
        wanted=dict(ReadonlyRootfs=True,NetworkMode='none',Privileged=False,CapDrop=['ALL'],
            SecurityOpt=['no-new-privileges'],PidMode='',IpcMode='private',CgroupnsMode='private',PidsLimit=128,
            Memory=4294967296,NanoCpus=2000000000,Tmpfs={'/tmp':TMPFS})
        safe_enums={'none','private','rprivate','rslave','rshared','slave','shared','',
                    'ALL','no-new-privileges','no-new-privileges:true','no-new-privileges=true'}
        def safe(value):
            if type(value) is bool or value is None:return value
            if type(value) is int and -(2**48)<value<2**48:return value
            if type(value) is str and value in safe_enums:return value
            if type(value) is list and len(value)<=8 and all(type(v) is str and v in safe_enums for v in value):return value
            return 'REDACTED_OR_UNREGISTERED'
        for key,value in wanted.items():
            ok=exact(h.get(key),value);check('host.'+key,ok)
            result['host'][key]=dict(matches=ok,observed=safe(h.get(key)))
        for key in ('CapAdd','Devices','DeviceRequests','Binds','GroupAdd','ExtraHosts','PortBindings'):
            ok=not h.get(key);check('host.'+key,ok);result['host'][key]=dict(empty=ok)
        environment={};duplicates=0
        for row in c['Env']:
            key,sep,value=row.partition('=')
            if not sep or key in environment:duplicates+=1
            environment[key]=value
        profile=environment_profile()
        result['environment']=dict(unexpected_names=len(set(environment)-set(profile)),duplicate_or_invalid=duplicates,
            known_key_matches={key:environment.get(key)==value for key,value in profile.items()})
        check('environment',not duplicates and exact(environment,profile))
        wanted_config=dict(Entrypoint=['/opt/venv/bin/python'],Cmd=CONTAINER_COMMAND,User='0:0',
                          WorkingDir='/work/repo',Hostname='stage7-sealed-native',Tty=False,OpenStdin=False)
        for key,value in wanted_config.items():
            ok=exact(c.get(key),value);check('config.'+key,ok);result['config'][key]=dict(matches=ok)
        labels={'stage7.request':ID,'stage7.nonce':expected['nonce'],'stage7.source':expected['source_sha'],
                'org.opencontainers.image.version':'24.04'}
        result['labels_match']=check('labels',c.get('Labels')==labels)
        desired={('/work/'+key):dict(type='bind',source=routes[key],rw=key in ('output','cache')) for key in routes}
        desired['/tmp']=dict(type='tmpfs',source='',rw=True)
        observed={};mount_ok=True
        for row in raw['Mounts']:
            dest=row.get('Destination')
            if dest not in desired:result['unknown_mounts']+=1;mount_ok=False;continue
            if dest in observed:mount_ok=False
            observed[dest]=dict(type=row.get('Type'),source=row.get('Source'),rw=row.get('RW'))
            propagation=row.get('Propagation')
            if row.get('Type')=='bind' and propagation!='rprivate':mount_ok=False
            result['mounts'][dest]=dict(type_matches=row.get('Type')==desired[dest]['type'],
                source_matches=row.get('Source')==desired[dest]['source'],rw_matches=exact(row.get('RW'),desired[dest]['rw']),
                propagation=safe(propagation))
        result['tmpfs_representation']='host_config_and_mounts' if '/tmp' in observed else 'host_config_only'
        if '/tmp' not in observed:desired.pop('/tmp')
        check('mounts',mount_ok and exact(observed,desired))
        try:validate_launch(raw,routes,expected);result['gate_passed']=True
        except Exception:result['gate_passed']=False
        if not result['gate_passed'] and not result['failed']:result['failed'].append('unclassified_gate_rejection')
    except Exception:result['failed'].append('invalid_structure')
    need(len(canonical(result))<=65536)
    return result


REQUEST_SCHEMA='engine-clock-held-abba-request-v3'


def artifact(phase):
    need(phase in ('canary','abba','attestation','attestor-diagnostics'))
    return 'engine-clock-'+ID+'-'+('canary-attestation' if phase=='attestation' else phase)


def recorded_status(mode):
    schedule(mode)
    return 'HELD_CANARY_NATIVE_RECORDED' if mode=='canary' else 'HELD_ABBA_DATASET_RECORDED'


def schedule(mode):
    need(type(mode) is str and mode in ('canary','abba'))
    return [(True,0)] if mode=='canary' else [(False,0),(True,0),(True,1),(False,1)]


def native_budget(mode):
    rows=schedule(mode);count=len(rows);on=sum(enabled for enabled,_ in rows)
    return dict(providers=count,capture_pairs=6*count,task_steps=12*count,ram_reads=12*count,
        texture_readings=24*count,texture_getters=48*count,clock_snapshots=48*on,clock_getters=96*on,
        observer_getters=48*count+96*on,extra_gpu_reads=0,extra_gl_getters=0,official_model_calls=0,
        ort_sessions=0,maps_snapshots=2+2*count,module_origin_snapshots=1+count,memory_snapshots=2+2*count)


def validate_acceptance(a,source):
    fields={'canary_head_sha','source_sha','run_id','workflow_id','job_id','artifact_id','artifact_name',
        'artifact_size_bytes','artifact_sha256','attestor_job_id','attestor_artifact_id','attestor_artifact_name',
        'attestor_artifact_size_bytes','attestor_artifact_sha256','lease_sha256','root_raw_accepted','fresh_raw_review_accepted'}
    need(type(a) is dict and set(a)==fields)
    need(image._hex(a['canary_head_sha'],40) and a['source_sha']==source and a['canary_head_sha']!=source
        and a['artifact_name']==artifact('canary') and a['attestor_artifact_name']==artifact('attestation')
        and all(image._hex(a[k]) for k in ('artifact_sha256','attestor_artifact_sha256','lease_sha256'))
        and a['root_raw_accepted'] is True and a['fresh_raw_review_accepted'] is True
        and all(type(a[k]) is int and a[k]>0 for k in ('run_id','workflow_id','job_id','artifact_id',
            'artifact_size_bytes','attestor_job_id','attestor_artifact_id','attestor_artifact_size_bytes'))
        and a['job_id']!=a['attestor_job_id'] and a['artifact_id']!=a['attestor_artifact_id']
        and a['artifact_size_bytes']<=512*MIB and a['attestor_artifact_size_bytes']<=2*MIB)


def host_details():
    with open('/proc/meminfo','rb') as f:raw=f.read(65537)
    need(len(raw)<=65536)
    rows=re.findall(rb'^MemTotal:\s+([0-9]+) kB$',raw,re.M);need(len(rows)==1)
    total=int(rows[0])*1024;ids=sorted(os.sched_getaffinity(0))
    need(BUDGET['minimum_host_memory_bytes']<=total<2**63 and 0<len(ids)<=4096
         and all(type(v) is int and 0<=v<2**20 for v in ids))
    return dict(affinity_ids=ids,memory_total_bytes=total)


def identity_difference(left,right):
    result=[]
    def visit(a,b,path):
        need(len(result)<128)
        if type(a) is not type(b):result.append(dict(path=path,accepted=a,observed=b));return
        if isinstance(a,dict):
            for key in sorted(set(a)|set(b)):
                child=(path+'.' if path else '')+key
                if key not in a or key not in b:result.append(dict(path=child,accepted=a.get(key),observed=b.get(key)))
                else:visit(a[key],b[key],child)
        elif a!=b:result.append(dict(path=path,accepted=a,observed=b))
    visit(left,right,'')
    need(len(canonical(result))<=65536)
    return result



def git_blob_sha(raw):
    need(type(raw) is bytes)
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def validate_control_delta(producer,effective,head,commit,compare,blob,raw):
    need(producer['mode']=='canary' and effective['mode']=='abba')
    expected=dict(producer,mode='abba',acceptance=effective['acceptance'],native_budget=native_budget('abba'))
    need(exact(expected,effective) and canonical(effective)==raw and git_blob_sha(raw)==blob)
    parent=effective['acceptance']['canary_head_sha']
    need(image._hex(head,40) and head!=parent and commit['sha']==head
        and [p['sha'] for p in commit['parents']]==[parent])
    need(compare['status']=='ahead' and exact(compare['ahead_by'],1) and exact(compare['behind_by'],0)
        and exact(compare['total_commits'],1) and compare['base_commit']['sha']==parent
        and compare['merge_base_commit']['sha']==parent and len(compare['commits'])==1
        and compare['commits'][0]['sha']==head and len(compare['files'])==1)
    row=compare['files'][0]
    need(row['filename']==A_REQUEST and row['status']=='added' and row['sha']==blob
        and not row.get('previous_filename'))


def validate_control_tree(tree,root_sha,blob):
    need(tree['sha']==root_sha and tree['truncated'] is False and type(tree['tree']) is list)
    rows=[v for v in tree['tree'] if v['path']==A_REQUEST]
    need(len(rows)==1 and rows[0]['mode']=='100644' and rows[0]['type']=='blob' and rows[0]['sha']==blob)


def validate_binding_requests(binding,producer_raw,root):
    producer=validate_request(binding['producer_request'],root)
    request=validate_request(binding['request'],root);ctx=binding['context']
    need(producer['mode']=='canary' and canonical(producer)==producer_raw
        and ctx['head_sha']==ctx['producer_head_sha'] and image._hex(ctx['head_sha'],40)
        and ctx['source_sha']==producer['reviewed_source_sha']==request['reviewed_source_sha']
        and ctx['producer_request_sha256']==sha(producer_raw)
        and ctx['request_sha256']==sha(canonical(request)) and ctx['mode']==request['mode']
        and ctx['repository']==REPOSITORY and type(ctx['run_id']) is int and ctx['run_id']>0)
    expected=dict(producer,mode=request['mode'],acceptance=request['acceptance'],native_budget=native_budget(request['mode']))
    need(exact(expected,request))
    if request['mode']=='canary':need(ctx['control_head_sha']==ctx['head_sha'])
    else:
        a=request['acceptance']
        need(ctx['control_head_sha']!=ctx['head_sha'] and image._hex(ctx['control_head_sha'],40)
            and a['canary_head_sha']==ctx['head_sha'] and a['run_id']==ctx['run_id']
            and a['workflow_id']==ctx['workflow_id'] and a['job_id']==ctx['job_id']
            and a['lease_sha256']==ctx['lease_sha256'])


def step_complete(job,name):
    rows=[s for s in job['steps'] if s['name']==name]
    need(len(rows)==1 and rows[0]['status']=='completed' and rows[0]['conclusion']=='success')


def validate_completion_api(a,run,jobs,canary_artifact,attest_artifact,*,workflow_id,live=True):
    validate_acceptance(a,a['source_sha'])
    need(run['id']==a['run_id'] and run['workflow_id']==workflow_id==a['workflow_id']
        and run['head_sha']==a['canary_head_sha'] and run['head_branch']==BRANCH and run['path']==WORKFLOW
        and run['event']=='push' and exact(run['run_attempt'],1) and run['repository']['full_name']==REPOSITORY)
    if live:need(run['status']=='in_progress' and run['conclusion'] is None)
    need(exact(jobs['total_count'],2) and len(jobs['jobs'])==2
        and {j['name'] for j in jobs['jobs']}=={'native-host','canary-attestor'})
    byname={j['name']:j for j in jobs['jobs']};host=byname['native-host'];attest=byname['canary-attestor']
    need(host['id']==a['job_id'] and attest['id']==a['attestor_job_id']
        and all(j['run_id']==a['run_id'] and j['head_sha']==a['canary_head_sha'] and exact(j['run_attempt'],1) for j in jobs['jobs'])
        and attest['status']=='completed' and attest['conclusion']=='success')
    if live:need(host['status']=='in_progress' and host['conclusion'] is None)
    step_complete(host,C_STEP);step_complete(host,C_UPLOAD)
    for item,aid,name,size,digest in ((canary_artifact,a['artifact_id'],a['artifact_name'],a['artifact_size_bytes'],a['artifact_sha256']),
        (attest_artifact,a['attestor_artifact_id'],a['attestor_artifact_name'],a['attestor_artifact_size_bytes'],a['attestor_artifact_sha256'])):
        wr=item['workflow_run']
        need(item['id']==aid and item['name']==name and item['expired'] is False and exact(item['size_in_bytes'],size)
            and item['digest']=='sha256:'+digest and wr['id']==a['run_id'] and wr['head_sha']==a['canary_head_sha']
            and wr['head_branch']==BRANCH and wr.get('repository_id',run['repository']['id'])==run['repository']['id'])
