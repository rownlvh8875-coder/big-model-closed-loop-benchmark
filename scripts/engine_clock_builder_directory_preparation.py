"""One-use builder07 with safe final source directory preparation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from time import monotonic,perf_counter
import urllib.parse

if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from scripts import engine_clock_builder_preparation as prep
from scripts import engine_clock_builder_retention as retention
from scripts import engine_clock_builder_namespace as namespace
from scripts import engine_clock_builder_observed_preparation as previous
from scripts import engine_clock_bwrap_profile_confirmation as confirmation
sandbox=prep.sandbox
staging,driver_logic,wheel_check=prep.staging,prep.driver_logic,prep.wheel_check
_need,_json,canonical=prep._need,prep._json,prep.canonical
REQUEST_ID='builder-20261113-07'
BRANCH='prepare/engine-clock-builder-20261113-07'
WORKFLOW='.github/workflows/engine-clock-builder-preparation-v7.yml'
REQUEST_PATH='docs/requests/engine-clock-'+REQUEST_ID+'.json'
SUPPORT='docs/evidence/STAGE7_ENGINE_CLOCK_BWRAP_PROFILE_CONFIRMATION_RESULT.json'
PROFILE=confirmation.PROFILE
HELPER=confirmation.HELPER
CLOSURE=frozenset([*previous.CLOSURE,WORKFLOW,
    'scripts/engine_clock_builder_source_directory.py','scripts/engine_clock_builder_directory_build.py',
    'scripts/engine_clock_builder_directory_preparation.py','tests/test_engine_clock_builder_source_directory.py',
    'docs/superpowers/specs/2026-11-13-engine-clock-builder-source-directory-design.md',
    'docs/superpowers/plans/2026-11-13-engine-clock-builder-source-directory.md'])


def validate_request(value):
    try:
        _need(type(value) is dict and set(value)=={'schema','request_id','repository','branch','workflow_path','reviewed_source_sha','budget','source_closure','inputs','expected_plan'},'INVALID_REQUEST')
        expected={'schema':'builder-preparation-request-v7','request_id':REQUEST_ID,'repository':prep.REPOSITORY,'branch':BRANCH,'workflow_path':WORKFLOW}
        _need(all(value[k]==v for k,v in expected.items()) and prep._digest(value['reviewed_source_sha'],40),'INVALID_REQUEST')
        _need(type(value['budget']) is dict and value['budget']=={'runs':1,'attempts':1,'builds':1,'probes':2,'profile_loads':1,'candidate_userns_assertions':1,'source_directory_preparations':1}
              and all(type(v) is int for v in value['budget'].values()),'INVALID_REQUEST')
        _need(type(value['source_closure']) is dict and set(value['source_closure'])==CLOSURE and all(prep._digest(d) for d in value['source_closure'].values()),'INVALID_REQUEST')
        _need(type(value['inputs']) is list and len(value['inputs'])==51 and sum(r['nbytes'] for r in value['inputs'])==109285137,'INVALID_REQUEST')
        ep=value['expected_plan']
        _need(type(ep) is dict and set(ep)=={'plan_sha256','serialized_sha256','nbytes'} and prep._digest(ep['plan_sha256']) and prep._digest(ep['serialized_sha256'])
              and type(ep['nbytes']) is int and 0<ep['nbytes']<=16777216,'INVALID_REQUEST')
        # Legacy syntax normalization excludes the v3-only plan after closing v3 identity/budget/closure.
        legacy={**{k:v for k,v in value.items() if k!='expected_plan'},'schema':'builder-preparation-request-v1','workflow_path':'.github/workflows/engine-clock-builder-preparation.yml',
                'budget':{'runs':1,'attempts':1,'builds':1},'source_closure':{p:value['source_closure'][p] for p in prep.CLOSURE_PATHS}}
        prep.validate_request(legacy)
        return value
    except (ValueError,TypeError,KeyError):raise ValueError('INVALID_REQUEST') from None


def validate_support(value):
    try:
        _need(type(value) is dict and value['schema']=='bwrap-profile-confirmation-consumption-v1' and value['request_id']=='namespace-diagnostic-20261113-04'
              and value['status']=='SUPPORTED_SCOPED_PROFILE' and value['run_id']==43419969613 and value['workflow_id']==417212710
              and value['run_attempt']==value['unique_workflow_branch_runs']==1 and value['request_consumed'] is True and value['after_validated'] is True,'INVALID_SUPPORT')
        _need(value['source_sha']=='197cd79fe3ee26342f970a1c8f153ef0215652e5' and value['activation_sha']=='4c02fb15e3a671c9aa2c9b42645260cd1d21ef41'
              and value['files']['original-artifact.zip']['sha256']=='c1a3a2f7d99b8a362838bc7e312ef1842daf228097f07767c688dc5f4d6f28f3','INVALID_SUPPORT')
        _need(all(value[k] is False for k in ('candidate_execution','model_execution','native_admission','image_ready')),'INVALID_SUPPORT')
        confirmation.validate_observation(value['observation'],value['host']['namespaces'],after=True)
        return value
    except (ValueError,TypeError,KeyError):raise ValueError('INVALID_SUPPORT') from None


def supported(q):
    try:
        def passed(row):return row['validated'] is True and row['process']['status']=='EXITED' and type(row['process']['returncode']) is int and row['process']['returncode']==0
        if q['status']=='SUPPORTED_WITHOUT_PROFILE':return passed(q['before']) and q['profile_load'] is None and q['after'] is None
        return (q['status']=='SUPPORTED_SCOPED_PROFILE' and q['before']['process']['status']=='EXITED' and q['before']['process']['returncode']==1
                and q['profile_load']['loaded'] is True and q['profile_load']['process']['status']=='EXITED' and q['profile_load']['process']['returncode']==0 and passed(q['after']))
    except (TypeError,KeyError):return False


def independent_device(probe_device,candidate_device):
    return type(probe_device) is int and type(candidate_device) is int and probe_device>0 and candidate_device>0 and probe_device!=candidate_device


def private_launch_argv(rootfd,buildfd):
    args=sandbox.launch_argv(rootfd,buildfd);args[0]=HELPER;args[-1]='--registered-builder-v3'
    return args


def make_sources(root,request):
    sources,payloads=previous.make_sources(root,request)
    payloads['run/builder/build.py']=(root/'scripts/engine_clock_builder_directory_build.py').read_bytes()
    payloads['run/builder/source-directory.py']=(root/'scripts/engine_clock_builder_source_directory.py').read_bytes()
    rows=[]
    for row in sources[-1]['entries']:
        if row['kind']=='file':
            raw=payloads[row['path']];row={**row,'nbytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        rows.append(row)
    raw=payloads['run/builder/source-directory.py'];rows.append({'path':'run/builder/source-directory.py','kind':'file','mode':0o644,'nbytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    return sources[:-1]+[{**sources[-1],'entries':rows,'archive_sha256':hashlib.sha256(canonical(rows)).hexdigest()}],payloads


def verify_plan(plan,request):
    raw=canonical(plan)
    _need(request['expected_plan']=={'plan_sha256':plan['plan_sha256'],'serialized_sha256':hashlib.sha256(raw).hexdigest(),'nbytes':len(raw)},'ROOT_PLAN_CHANGED')


def decode_envelope(raw):
    try:
        _need(type(raw) is bytes and 0<len(raw)<=3145728,'INVALID_DRIVER_WIRE')
        value=_json(raw)
        _need(type(value) is dict and set(value)=={'schema','namespace','result'} and value['schema']=='builder-driver-envelope-v2','INVALID_DRIVER_WIRE')
        if value['namespace'] is not None:namespace.validate_shape(value['namespace'])
        _need(type(value['result']) is dict,'INVALID_DRIVER_WIRE')
        return value['namespace'],(json.dumps(value['result'],sort_keys=True,separators=(',',':'))+'\n').encode()
    except (ValueError,TypeError,KeyError,UnicodeError,RecursionError,OverflowError):raise ValueError('INVALID_DRIVER_WIRE') from None


def compact(value):return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()


def decode_failure(raw):
    try:
        value=_json(raw)
        _need(sandbox.failure_code(raw)!='UNAVAILABLE','INVALID_DRIVER_WIRE')
        stages=('VENV','ENSUREPIP','TOOLS','BUILD','SMOKE')
        _need([r.get('stage') if type(r) is dict else None for r in value['steps']]==list(stages[:len(value['steps'])]),'INVALID_DRIVER_WIRE')
        for row in value['steps']:
            _need(set(row)=={'stage','status','returncode','stdout_bytes','stderr_bytes','stdout_sha256','stderr_sha256'} and
                  row['status'] in ('EXITED','TIMEOUT','CLEANUP_FAILED','OUTPUT_LIMIT','SPAWN_FAILED','TRANSPORT_FAILED'),'INVALID_DRIVER_WIRE')
            _need(row['returncode'] is None or type(row['returncode']) is int and -2**31<=row['returncode']<2**31,'INVALID_DRIVER_WIRE')
            # Capture stops at the first failed budget after one <=64KiB read.
            # Cleanup/transport failure may subsequently replace OUTPUT_LIMIT.
            overshoot=0 if row['status']=='EXITED' else 65536
            _need(all(type(row[k]) is int and 0<=row[k]<=limit+overshoot for k,limit in (('stdout_bytes',3145728),('stderr_bytes',1048576))) and
                  all(prep._digest(row[k]) for k in ('stdout_sha256','stderr_sha256')),'INVALID_DRIVER_WIRE')
        return value
    except (ValueError,TypeError,KeyError,UnicodeError,RecursionError,OverflowError):raise ValueError('INVALID_DRIVER_WIRE') from None


def qualify_host(root,work,env,facts):
    tool=Path(HELPER);st=tool.stat()
    _need(not tool.is_symlink() and st.st_uid==0 and st.st_mode&0o7777==0o755 and st.st_size<=1048576,'UNSUPPORTED_HOST_TOOL')
    out=root/'output/stage7-builder-preparation'/REQUEST_ID
    raw=tool.read_bytes();facts['helper']={'sha256':hashlib.sha256(raw).hexdigest(),'nbytes':len(raw),'owner':0,'mode':0o755}
    _need((out/'host-helper.bwrap').read_bytes()==raw and hashlib.sha256((out/'source.tar.xz').read_bytes()).hexdigest()=='9760d007363e3abba7c747489910f9f82d9fca53ba3bd3282e396fa3c97a3314'
          and (out/'profile.apparmor').read_bytes()==(root/PROFILE).read_bytes(),'UNSUPPORTED_HOST_TOOL')
    facts['version_process'],version=sandbox.capture([HELPER,'--version'],timeout=5)
    facts['help_process'],help_raw=sandbox.capture([HELPER,'--help'],timeout=5)
    _need(facts['version_process']['status']=='EXITED' and facts['version_process']['returncode']==0 and version==b'bubblewrap 0.12.0\n'
          and facts['help_process']['status']=='EXITED' and facts['help_process']['returncode']==0 and sandbox.supported_options(help_raw.decode('utf-8')),'UNSUPPORTED_HOST_OPTIONS')
    probe=work/'host-probe';probe.mkdir(mode=0o700)
    fd,facts['probe_mount']=prep.open_build_mount(REQUEST_ID+'-probe')
    try:
        facts['probe_device']=os.fstat(fd).st_dev
        backend=confirmation.Backend(root,probe,fd)
        backend.host['kernel']=os.uname().release
        image=env.get('ImageVersion','');backend.host['image_version']=image if re.fullmatch(r'[0-9.\-]{1,64}',image) else None
        facts['host']=backend.host
        facts['qualification']=confirmation.qualify(backend)
    finally:os.close(fd)


def authenticate(root,request,env):
    prep.require_remote_environment(env);validate_request(request)
    _need(_json((root/REQUEST_PATH).read_bytes())==request,'INVALID_REQUEST')
    _need(env.get('GITHUB_REF')=='refs/heads/'+BRANCH and env.get('GITHUB_WORKFLOW_REF')==prep.REPOSITORY+'/'+WORKFLOW+'@refs/heads/'+BRANCH and Path(env.get('GITHUB_WORKSPACE','')).resolve()==root.resolve(),'INVALID_REMOTE_ENVIRONMENT')
    api=lambda path:prep.api_json('/repos/'+prep.REPOSITORY+path,env['GH_TOKEN'])
    run=api('/actions/runs/'+env['GITHUB_RUN_ID']);listing=api('/actions/workflows/engine-clock-builder-preparation-v7.yml/runs?branch='+urllib.parse.quote(BRANCH,safe='')+'&per_page=2')
    prep.validate_context(request,run,listing,run_id=int(env['GITHUB_RUN_ID']),head=env['GITHUB_SHA'])
    commit=api('/git/commits/'+env['GITHUB_SHA']);prior=api('/git/commits/'+request['reviewed_source_sha'])
    _need(prior['sha']==request['reviewed_source_sha'],'INVALID_ACTIVATION')
    current=api('/git/trees/'+commit['tree']['sha']+'?recursive=1');reviewed=api('/git/trees/'+prior['tree']['sha']+'?recursive=1')
    prep.verify_source_closure(root,request,current);prep.verify_source_closure(root,request,reviewed)
    validate_activation(request,env['GITHUB_SHA'],current,reviewed,commit)
    blobs={r['path']:r['sha'] for r in current['tree'] if r['type']=='blob'}
    _need(blobs.get(REQUEST_PATH)==prep.git_blob_sha((root/REQUEST_PATH).read_bytes()),'SOURCE_CLOSURE_MISMATCH')
    _need(request['inputs']==prep.expected_inputs(root),'INPUT_REGISTRATION_MISMATCH')
    support=validate_support(_json((root/SUPPORT).read_bytes()))
    _need(support['profile_sha256']==hashlib.sha256((root/PROFILE).read_bytes()).hexdigest(),'INVALID_SUPPORT')
    return {'repository':prep.REPOSITORY,'run_id':int(env['GITHUB_RUN_ID']),'run_attempt':1,'head_sha':env['GITHUB_SHA'],'workflow_path':WORKFLOW,
            'request_sha256':hashlib.sha256((root/REQUEST_PATH).read_bytes()).hexdigest(),'support_receipt_sha256':hashlib.sha256((root/SUPPORT).read_bytes()).hexdigest()}


def validate_activation(request,head,current,reviewed,commit):
    try:
        prep._need(commit['sha']==head and len(commit['parents'])==1 and commit['parents'][0]['sha']==request['reviewed_source_sha'] and commit['tree']['sha']==current['sha'],'INVALID_ACTIVATION')
        def leaves(tree):
            prep._need(tree['truncated'] is False,'INVALID_ACTIVATION')
            result={}
            for row in tree['tree']:
                prep._need(row['type'] in ('tree','blob','commit'),'INVALID_ACTIVATION')
                if row['type']=='tree': continue
                prep._need(row['path'] not in result,'INVALID_ACTIVATION')
                result[row['path']]=(row['type'],row['mode'],row['sha'])
            return result
        before,after=leaves(reviewed),leaves(current)
        changes={p for p in set(before)|set(after) if before.get(p)!=after.get(p)}
        prep._need(changes=={REQUEST_PATH} and REQUEST_PATH not in before and after[REQUEST_PATH][:2]==('blob','100644'),'INVALID_ACTIVATION')
    except (ValueError,TypeError,KeyError): raise ValueError('INVALID_ACTIVATION') from None


def run_preparation(root, request, env):
    out = root / 'output/stage7-builder-preparation' / request['request_id']
    out.mkdir(parents=True, exist_ok=True)
    _need(not (out / 'preparation.json').exists(), 'OUTPUT_EXISTS')
    receipt = {'schema': 'builder-preparation-result-v7', 'status': 'FAILED_OR_INCOMPLETE', 'errors': [],
               'request_id': request['request_id'], 'source_execution_attempted': False, 'target_execution_verified': False,
               'image_preparation_ready': False, 'native_admission': False, 'full_lock_ready': False,
               'official_model_calls': 0, 'transports': []}
    work = Path('/tmp/engine-clock-preparation-' + request['request_id'])
    buildfd = None
    try:
        receipt['context'] = authenticate(root, request, env)
        work.mkdir(mode=0o700, exist_ok=False)
        receipt['host_capacity'] = {}
        prep.check_host_capacity(work, receipt['host_capacity'])
        receipt['host'] = {}
        qualify_host(root, work, env, receipt['host'])
        _need(supported(receipt['host']['qualification']), 'UNSUPPORTED_HOST_NAMESPACE')
        buildfd, receipt['build_mount'] = prep.open_build_mount(REQUEST_ID)
        _need(independent_device(receipt['host']['probe_device'], os.fstat(buildfd).st_dev), 'UNSUPPORTED_HOST_QUOTA')
        store = work / 'inputs';store.mkdir()
        stop = monotonic() + 300
        for row in request['inputs']:receipt['transports'].append(prep.download_input(row, store, stop))
        sources, payloads = make_sources(root, request)
        plan = staging.compile_plan(sources)
        verify_plan(plan,request)
        (out / 'root-files.json').write_bytes(canonical(plan))
        receipt['staging'] = staging.stage_tree(work / 'root', plan, prep.input_members(sources, request, store, payloads), deadline=perf_counter() + 180)
        _need(receipt['staging']['status'] == 'STAGED_CONTENT_MATCH', 'STAGING_FAILED')
        receipt['verification'] = staging.verify_tree(work / 'root', plan, deadline=perf_counter() + 180)
        _need(receipt['verification']['status'] == 'STAGED_CONTENT_MATCH', 'ROOT_VERIFICATION_FAILED')
        fd = os.open(work / 'root', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            receipt['open_root_verification'] = staging.verify_open_tree(fd, plan, deadline=perf_counter() + 180)
            _need(receipt['open_root_verification']['status'] == 'STAGED_CONTENT_MATCH', 'ROOT_VERIFICATION_FAILED')
            receipt['source_execution_attempted'] = True
            receipt['execution'], raw = sandbox.capture(private_launch_argv(fd, buildfd), timeout=180, pass_fds=(fd, buildfd))
        finally:os.close(fd)
        receipt['namespace'],core_raw=decode_envelope(raw)
        receipt['core_wire']={'nbytes':len(core_raw),'sha256':hashlib.sha256(core_raw).hexdigest()}
        if receipt['execution']['status'] == 'EXITED' and receipt['execution']['returncode'] != 0:
            receipt['driver_failure'] = decode_failure(core_raw)
            receipt['driver_failure_claim'] = receipt['driver_failure']['code']
        _need(receipt['execution']['status'] == 'EXITED' and receipt['execution']['returncode'] == 0, 'BUILDER_EXECUTION_FAILED')
        namespace.validate(receipt['namespace'])
        driver_result, wheel = sandbox.decode_wire(core_raw)
        source_rows = [{'path': r['path'].split('/', 1)[1], 'sha256': r['sha256']}
                       for r in _json((root / prep.SOURCE_INSPECTION).read_bytes())['source_members'] if r['kind'] == 'file']
        driver_logic.validate_snapshots(driver_result['source_snapshots'], source_rows)
        policy = _json((root / prep.POLICY).read_bytes())['output_policy']
        pins = {**policy['runtime_files'], 'progressbar-2.5.dist-info/licenses/LICENSE.txt': policy['license_bytes_sha256']}
        receipt['wheel'] = wheel_check.validate_wheel(wheel, pins)
        _need(receipt['wheel']['status'] == 'WHEEL_BYTES_MATCH', 'WHEEL_REJECTED')
        receipt['driver'] = driver_result
        (out / policy['expected_filename']).write_bytes(wheel)
        receipt.update(status='BUILT_WHEEL_VERIFIED', target_execution_verified=True)
    except ValueError as exc:
        allowed = {'UNSUPPORTED_HOST_TOOL', 'UNSUPPORTED_HOST_OPTIONS', 'UNSUPPORTED_HOST_NAMESPACE', 'UNSUPPORTED_HOST_QUOTA', 'HOST_CAPACITY_INSUFFICIENT',
                   'DOWNLOAD_URL_REJECTED', 'DOWNLOAD_REDIRECT_REJECTED', 'DOWNLOAD_HTTP_REJECTED',
                   'DOWNLOAD_DEADLINE', 'DOWNLOAD_SIZE_MISMATCH', 'DOWNLOAD_CONTENT_MISMATCH',
                   'STAGING_FAILED', 'ROOT_VERIFICATION_FAILED', 'BUILDER_EXECUTION_FAILED',
                   'WHEEL_REJECTED', 'INVALID_DRIVER_WIRE', 'INVALID_RUN_CONTEXT', 'INVALID_REMOTE_ENVIRONMENT',
                   'SOURCE_CLOSURE_MISMATCH', 'WORKFLOW_MISMATCH', 'INPUT_REGISTRATION_MISMATCH', 'INVALID_SUPPORT', 'INVALID_ACTIVATION', 'ROOT_PLAN_CHANGED','UNSUPPORTED_PYTHON','UNSUPPORTED_NAMESPACE','UNSUPPORTED_QUOTA','UNSUPPORTED_CAPABILITIES','UNSUPPORTED_NETWORK','INVALID_NAMESPACE_FACTS'}
        receipt['errors'] = [{'code': str(exc) if str(exc) in allowed else 'PREPARATION_FAILED'}]
    except Exception:
        receipt['errors'] = [{'code': 'PREPARATION_FAILED'}]
    finally:
        if buildfd is not None:os.close(buildfd)
        (out / 'source-closure.json').write_bytes(canonical(request))
        (out / 'preparation.json').write_bytes(canonical(receipt))
    return receipt


def retention_roots():
    return {'workspace':Path('/tmp/engine-clock-preparation-'+REQUEST_ID),'build':Path('/tmp/engine-clock-build-'+REQUEST_ID),
            'probe-build':Path('/tmp/engine-clock-build-'+REQUEST_ID+'-probe'),'host-helper':Path('/tmp/engine-clock-profile-host-helper')}


def retain(root,env):
    prep.require_remote_environment(env)
    _need(env.get('GITHUB_REF')=='refs/heads/'+BRANCH and env.get('GITHUB_WORKFLOW_REF')==prep.REPOSITORY+'/'+WORKFLOW+'@refs/heads/'+BRANCH
          and Path(env.get('GITHUB_WORKSPACE','')).resolve()==root.resolve(),'INVALID_REMOTE_ENVIRONMENT')
    out=root/'output/stage7-builder-preparation'/REQUEST_ID;out.mkdir(parents=True,exist_ok=True)
    return retention.preserve_workspaces(retention_roots(),out,deadline=perf_counter()+180)


def main():
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group();mode.add_argument('--guard-only',action='store_true');mode.add_argument('--retain',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parent.parent;env=dict(os.environ)
    try:
        if args.retain:
            result=retain(root,env);print(result['status']);return 0 if result['status']=='PRESERVED_AVAILABLE_WORKSPACES' else 1
        request=validate_request(_json((root/REQUEST_PATH).read_bytes()))
        if args.guard_only:authenticate(root,request,env);print('REGISTERED_SCOPED_CONTEXT_VALID');return 0
        result=run_preparation(root,request,env);print(result['status']);return 0 if result['status']=='BUILT_WHEEL_VERIFIED' else 1
    except Exception:
        print('SCOPED_BUILDER_CONTEXT_REJECTED');return 1

if __name__=='__main__':raise SystemExit(main())
