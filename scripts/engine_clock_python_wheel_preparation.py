"""One-use local binary-only Python wheel input preparation; never installs/imports payloads."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import signal
import ssl
import stat
import subprocess
import sys
import time
import tomllib
import urllib.parse
import urllib.error
import urllib.request
import pip

if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from scripts import engine_clock_python_wheel_closure as wheel

REQUEST_ID='python-lock-20261114-02'
REPOSITORY='rownlvh8875-coder/big-model-closed-loop-benchmark'
SOURCE_BRANCH='prepare/engine-clock-python-wheel-closure'
BRANCH='prepare/engine-clock-'+REQUEST_ID
REQUEST_PATH='docs/requests/engine-clock-'+REQUEST_ID+'.json'
OUTPUT='output/stage7-python-wheel-closure/'+REQUEST_ID
PREFLIGHT='output/stage7-python-wheel-closure-preflight/'+REQUEST_ID
TOOL={'python':'/workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python','version':'3.11.17','pip':'26.2.2'}
TARGET={'python':'3.11.18','implementation':'cp','abi':'cp311','platform':'linux/amd64','platform_tags':list(wheel.PLATFORMS)}
MIB=1024*1024
BUDGET={'pip_downloads':1,'metadata_requests':96,'max_wheels':96,'max_archive_bytes':256*MIB,'max_total_archive_bytes':1024*MIB,
        'max_decoded_bytes':3072*MIB,'max_member_bytes':512*MIB,'max_members':100000,'max_json_bytes':4*MIB,'max_json_total_bytes':128*MIB,
        'pip_timeout_seconds':300,'total_timeout_seconds':900,'log_limit_bytes':MIB,'operation_tree_limit_bytes':2048*MIB,'minimum_free_bytes':16384*MIB}
PERMISSIONS={'wheel_downloads':True,'package_installs':False,'source_execution':False,'native_calls':False,'model_calls':False,'docker_calls':False}
META_RECEIPT='docs/evidence/STAGE7_ENGINE_CLOCK_REAL_WHEEL_RECEIPT.json'
META_CHECK='docs/evidence/STAGE7_ENGINE_CLOCK_REAL_WHEEL_ROOT_VERIFICATION.json'
BUILD_RECEIPT='docs/evidence/STAGE7_ENGINE_CLOCK_BUILDER_SOURCE_DIRECTORY_RESULT.json'
LOCAL_INPUTS=[{'id':'metadrive-headless','name':'metadrive-simulator','version':'0.4.3','path':'output/stage7-real-wheel-preparation/wheel-input-20261113-e369b2c18129/metadrive_simulator-0.4.3-1headless-py3-none-any.whl','nbytes':72968610,'sha256':'f949e89ff4bc32b72c8d09f5c61446bbc2b1f9b415b99a077c02b8df77c217f7'},
 {'id':'progressbar','name':'progressbar','version':'2.5','path':'output/stage7-builder-directory-evidence/builder-20261113-07/progressbar-2.5-py3-none-any.whl','nbytes':12144,'sha256':'6d700c40ef5826211c7fa03701fc0bd9131a93f40e170963cff507c622ee3dd1'}]
CLOSURE=frozenset(['scripts/__init__.py','pyproject.toml',META_RECEIPT,META_CHECK,BUILD_RECEIPT,
 'scripts/engine_clock_python_wheel_closure.py','scripts/engine_clock_python_wheel_preparation.py','scripts/engine_clock_binary_pip_download.py',
 'tests/test_engine_clock_python_wheel_closure.py','tests/test_engine_clock_python_wheel_preparation.py','tests/test_engine_clock_binary_pip_download.py',
 'docs/superpowers/specs/2026-11-14-engine-clock-python-wheel-closure-design.md','docs/superpowers/plans/2026-11-14-engine-clock-python-wheel-closure.md'])


def _need(ok,code):
    if not ok:raise ValueError(code)


def canonical(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def _pairs(rows):
    d={}
    for k,v in rows:
        _need(k not in d,'INVALID_JSON');d[k]=v
    return d

def parse(raw):
    _need(type(raw) is bytes and len(raw)<=16*MIB,'INVALID_JSON')
    return json.loads(raw,object_pairs_hook=_pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('INVALID_JSON')))

def _digest(v,n=64):return type(v) is str and re.fullmatch('[0-9a-f]{'+str(n)+'}',v) is not None

def read_regular(path,limit=16*MIB):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno());_need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<=before.st_size<=limit,'UNSAFE_INPUT_FILE')
        data=stream.read(limit+1);after=os.fstat(stream.fileno())
        _need(len(data)==before.st_size and (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'INPUT_CHANGED')
        return data


def expected_roots(root):
    project=tomllib.loads((root/'pyproject.toml').read_text())['project']
    _need(wheel.SpecifierSet(project['requires-python']).contains('3.11.18'),'INVALID_PROJECT_TARGET')
    return ['metadrive-simulator==0.4.3','progressbar==2.5','numpy==2.4.6','opencv-python-headless==5.0.0.93','panda3d==1.10.13',*project['optional-dependencies']['inference']]


def validate_request(v,root):
    try:
        _need(type(v) is dict and set(v)=={'schema','request_id','repository','branch','reviewed_source_branch','reviewed_source_sha','output_directory','tool','target','budget','permissions','root_requirements','local_inputs','source_closure','source_ci'},'INVALID_REQUEST')
        for k,x in {'schema':'python-wheel-closure-request-v1','request_id':REQUEST_ID,'repository':REPOSITORY,'branch':BRANCH,'reviewed_source_branch':SOURCE_BRANCH,'output_directory':OUTPUT,'tool':TOOL,'target':TARGET,'budget':BUDGET,'permissions':PERMISSIONS,'local_inputs':LOCAL_INPUTS}.items():_need(v[k]==x,'INVALID_REQUEST')
        _need(_digest(v['reviewed_source_sha'],40) and all(type(x) is int for x in v['budget'].values()) and all(type(x) is bool for x in v['permissions'].values()),'INVALID_REQUEST')
        _need(v['root_requirements']==expected_roots(root) and type(v['source_closure']) is dict and set(v['source_closure'])==CLOSURE and all(_digest(x) for x in v['source_closure'].values()),'INVALID_REQUEST')
        _need(type(v['source_ci']) is list and len(v['source_ci'])==2 and [r['event'] for r in v['source_ci']]==['push','pull_request'],'INVALID_REQUEST')
        ids=set()
        for row in v['source_ci']:
            _need(type(row) is dict and set(row)=={'run_id','event','proofs'} and type(row['run_id']) is int and row['run_id']>0 and row['run_id'] not in ids and type(row['proofs']) is dict and set(row['proofs'])=={'run','jobs','artifacts'},'INVALID_REQUEST');ids.add(row['run_id'])
            for kind,spec in row['proofs'].items():
                _need(type(spec) is dict and set(spec)=={'path','nbytes','sha256'} and spec['path']==PREFLIGHT+'/source-'+str(row['run_id'])+'-'+kind+'.json' and type(spec['nbytes']) is int and 0<spec['nbytes']<=4*MIB and _digest(spec['sha256']),'INVALID_REQUEST')
        return v
    except (ValueError,TypeError,KeyError):raise ValueError('INVALID_REQUEST') from None


def validate_activation(request,head,parents,changes,mode):
    _need(_digest(head,40) and parents==[request['reviewed_source_sha']] and head!=request['reviewed_source_sha'] and changes==b'A\0'+REQUEST_PATH.encode()+b'\0' and mode=='100644','INVALID_ACTIVATION')


def validate_ci(request,proofs):
    try:
        _need(len(proofs)==2,'INVALID_SOURCE_CI')
        for registration,data in zip(request['source_ci'],proofs):
            run=data['run'];jobs=data['jobs'];artifacts=data['artifacts'];rid=registration['run_id']
            _need(type(run['id']) is int and run['id']==rid and run['head_sha']==request['reviewed_source_sha'] and run['head_branch']==SOURCE_BRANCH and run['event']==registration['event'] and run['path']=='.github/workflows/ci.yml' and type(run['run_attempt']) is int and run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='success' and run['repository']['full_name']==REPOSITORY,'INVALID_SOURCE_CI')
            _need(type(jobs['total_count']) is int and jobs['total_count']==2 and len(jobs['jobs'])==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(type(j['run_id']) is int and j['run_id']==rid and j['status']=='completed' and j['conclusion']=='success' for j in jobs['jobs']),'INVALID_SOURCE_CI')
            _need(type(artifacts['total_count']) is int and artifacts['total_count']==0 and artifacts['artifacts']==[],'INVALID_SOURCE_CI')
    except (ValueError,TypeError,KeyError):raise ValueError('INVALID_SOURCE_CI') from None


def validate_input_provenance(root):
    meta=parse(read_regular(root/META_RECEIPT));checked=parse(read_regular(root/META_CHECK));built=parse(read_regular(root/BUILD_RECEIPT));m,p=LOCAL_INPUTS
    _need(meta['status']=='LOCAL_WHEEL_DERIVED_PUBLISHED_PINS_MATCH' and meta['derived_file_verified'] is True and meta['derived_sha256']==checked['derived_sha256']==m['sha256'] and meta['derived_nbytes']==m['nbytes'] and checked['status']=='ROOT_MEMBER_BYTES_AND_RECORD_VERIFIED' and checked['operator_receipt_sha256']==hashlib.sha256(read_regular(root/META_RECEIPT)).hexdigest(),'INVALID_LOCAL_PROVENANCE')
    _need(built['status']=='BUILT_WHEEL_VERIFIED' and built['request_id']=='builder-20261113-07' and built['run_id']==43447694201 and built['workflow_id']==417393804 and built['activation_sha']=='3bc04985cc05498f7a8f1686a0c45d186381e3ad' and built['source_sha']=='b8979edf2d592431c85864936bdc04519e932e41' and built['run_attempt']==built['unique_workflow_branch_runs']==1 and built['request_consumed'] is True and built['wheel']['wheel_sha256']==p['sha256'] and built['wheel']['nbytes']==p['nbytes'] and built['target_execution_verified'] is True,'INVALID_LOCAL_PROVENANCE')
    return {r['id']:{'sha256':r['sha256'],'nbytes':r['nbytes'],'source_receipt':META_RECEIPT if r['id']=='metadrive-headless' else BUILD_RECEIPT,'publisher_signature_or_endorsement':False} for r in LOCAL_INPUTS}


def authenticate(root,request):
    validate_request(request,root)
    git=lambda *args:subprocess.check_output(['git',*args],cwd=root,timeout=15)
    _need(parse(read_regular(root/REQUEST_PATH))==request and git('rev-parse','--show-toplevel').decode().strip()==str(root.resolve()) and git('branch','--show-current').decode().strip()==BRANCH and not git('status','--porcelain','--untracked-files=all').strip(),'INVALID_LOCAL_CONTEXT')
    head=git('rev-parse','HEAD').decode().strip();parents=git('rev-list','--parents','-n','1','HEAD').decode().split()[1:];mode=git('ls-tree','HEAD',REQUEST_PATH).decode().split()[0]
    validate_activation(request,head,parents,git('diff-tree','--no-commit-id','--name-status','-r','-z',request['reviewed_source_sha'],head),mode)
    for p,digest in request['source_closure'].items():
        raw=read_regular(root/p);_need(hashlib.sha256(raw).hexdigest()==digest and raw==git('show',request['reviewed_source_sha']+':'+p),'SOURCE_CLOSURE_MISMATCH')
    rows=[];raws={}
    for ci in request['source_ci']:
        row={}
        for kind,spec in ci['proofs'].items():
            raw=read_regular(root/spec['path'],4*MIB);_need(len(raw)==spec['nbytes'] and hashlib.sha256(raw).hexdigest()==spec['sha256'],'INVALID_SOURCE_CI');row[kind]=parse(raw);raws[Path(spec['path']).name]=raw
        rows.append(row)
    validate_ci(request,rows)
    return {'activation_sha':head,'reviewed_source_sha':request['reviewed_source_sha'],'request_sha256':hashlib.sha256(read_regular(root/REQUEST_PATH)).hexdigest(),'source_closure_verified':True,'source_ci_runs':[r['run_id'] for r in request['source_ci']],'ci_files':raws}


def pip_argv(root,request,out):
    args=[TOOL['python'],'-I','-B',str(root/'scripts/engine_clock_binary_pip_download.py'),'--','--isolated','--disable-pip-version-check','--no-input','--no-cache-dir','--keyring-provider','disabled','--retries','0','--timeout','20','download','--only-binary=:all:','--index-url','https://pypi.org/simple','--python-version','3.11.18','--implementation','cp','--abi','cp311','--dest',str(out/'wheels')]
    for tag in wheel.PLATFORMS:args.extend(['--platform',tag])
    args.extend(str(root/r['path']) for r in LOCAL_INPUTS);args.extend(request['root_requirements']);return args


def _tool_facts(cmd):
    _need(sys.executable==TOOL['python'] and platform.python_version()==TOOL['version'] and pip.__version__==TOOL['pip'] and sys.flags.isolated and sys.flags.dont_write_bytecode,'UNSUPPORTED_TOOL')
    from pip._internal.commands import create_command
    arguments=cmd[cmd.index('--')+1:];pivot=arguments.index('download');parsed,_=create_command('download',isolated=True).parse_args(arguments[:pivot]+arguments[pivot+1:])
    _need(parsed.index_url=='https://pypi.org/simple' and parsed.extra_index_urls==[] and parsed.trusted_hosts==[] and parsed.format_control.only_binary=={':all:'} and not parsed.ignore_dependencies,'UNSUPPORTED_PIP_CONFIGURATION')
    return {'python':platform.python_version(),'pip':pip.__version__,'isolated':True,'dont_write_bytecode':True,'public_index_exact':True,'extra_indexes':0,'trusted_hosts':0}


def _tree_bytes(root):
    count=0;total=0
    def visit(fd,depth):
        nonlocal count,total
        _need(depth<=32,'UNSAFE_OPERATION_TREE')
        with os.scandir(fd) as entries:
            for entry in entries:
                try:info=entry.stat(follow_symlinks=False)
                except FileNotFoundError:continue
                count+=1;_need(count<=100000,'OPERATION_TREE_LIMIT')
                if stat.S_ISREG(info.st_mode):total+=info.st_size;_need(info.st_size<=256*MIB,'OPERATION_TREE_LIMIT')
                elif stat.S_ISDIR(info.st_mode):
                    try:child=os.open(entry.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
                    except FileNotFoundError:continue
                    try:visit(child,depth+1)
                    finally:os.close(child)
                else:raise ValueError('UNSAFE_OPERATION_TREE')
    fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:visit(fd,0)
    finally:os.close(fd)
    return total


def _limits():
    for which,value in ((resource.RLIMIT_CORE,0),(resource.RLIMIT_FSIZE,256*MIB),(resource.RLIMIT_AS,2048*MIB),(resource.RLIMIT_CPU,301)):resource.setrlimit(which,(value,value))


def _run_pip(cmd,out,receipt):
    env={k:v for k,v in os.environ.items() if not k.startswith(('PIP_','GH_','GITHUB_','AWS_','AZURE_','OPENAI_','ANTHROPIC_'))}
    env.update(PIP_CONFIG_FILE=os.devnull,PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(out/'tmp'))
    start=time.monotonic();reason=None;peak=0;proc=None
    with (out/'pip.log').open('xb') as log:
        try:
            receipt['pip_invocations']=1;proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True,preexec_fn=_limits)
            while True:
                peak=max(peak,_tree_bytes(out))
                if time.monotonic()-start>BUDGET['pip_timeout_seconds']:reason='PIP_TIMEOUT'
                elif peak>BUDGET['operation_tree_limit_bytes']:reason='OPERATION_TREE_LIMIT'
                elif (out/'pip.log').stat().st_size>BUDGET['log_limit_bytes']:reason='PIP_LOG_LIMIT'
                if reason or proc.poll() is not None:break
                time.sleep(.1)
        finally:
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=2)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=2)
    receipt.update(pip_exit_code=None if proc is None else proc.returncode,pip_seconds=time.monotonic()-start,observed_tree_peak_bytes=peak,pip_limit_failure=reason)
    _need(proc is not None and proc.returncode==0 and reason is None,'BINARY_WHEEL_DOWNLOAD_FAILED')


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('PUBLISHER_REDIRECT_REJECTED')


def _release(name,version,path,deadline):
    url='https://pypi.org/pypi/'+urllib.parse.quote(name,safe='')+'/'+urllib.parse.quote(version,safe='')+'/json'
    _need(time.monotonic()<deadline,'METADATA_DEADLINE');context=ssl.create_default_context();_need(context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED,'INVALID_TLS_CONTEXT')
    opener=urllib.request.build_opener(_NoRedirect(),urllib.request.HTTPSHandler(context=context));request=urllib.request.Request(url,headers={'User-Agent':'engine-clock-wheel-inputs/1','Accept':'application/json'})
    raw=bytearray();start=time.monotonic()
    with opener.open(request,timeout=min(20,max(.1,deadline-time.monotonic()))) as response:
        _need(response.status==200 and response.geturl()==url,'PUBLISHER_HTTP_REJECTED')
        while True:
            _need(time.monotonic()<deadline,'METADATA_DEADLINE');block=response.read(65536)
            if not block:break
            raw.extend(block);_need(len(raw)<=BUDGET['max_json_bytes'],'PUBLISHER_METADATA_LIMIT')
    data=bytes(raw)
    with path.open('xb') as stream:stream.write(data)
    return parse(data),{'url':url,'http_status':200,'nbytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'seconds':time.monotonic()-start,'tls_default_context_verified':True,'redirects':0}


def audit_wheels(paths,*,deadline):
    remaining={'archive_bytes':BUDGET['max_total_archive_bytes'],'decoded_bytes':BUDGET['max_decoded_bytes'],'members':BUDGET['max_members']};rows=[]
    for path in paths:
        row=wheel.inspect_wheel(path,deadline=deadline,remaining=remaining)
        rows.append(row)
        for key,field in (('archive_bytes','nbytes'),('decoded_bytes','decoded_bytes'),('members','member_count')):remaining[key]-=row[field]
    return rows


def _kst():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()

def _write(path,value):
    with path.open('xb') as stream:stream.write(canonical(value))


def run_preparation(root,request):
    context=authenticate(root,request);out=root/OUTPUT
    _need(not out.exists() and not out.is_symlink(),'OUTPUT_EXISTS');out.mkdir(parents=True,mode=0o700,exist_ok=False)
    started=time.monotonic();_write(out/'attempt.json',{'schema':'python-wheel-closure-attempt-v1','request_id':REQUEST_ID,'status':'CONSUMED_STARTED','activation_sha':context.get('activation_sha'),'started_kst':_kst(),'further_execution_authorized':False})
    receipt={'schema':'python-wheel-closure-result-v1','request_id':REQUEST_ID,'status':'FAILED_OR_INCOMPLETE','request_consumed':True,'started_kst':_kst(),'errors':[],
             'context':{k:v for k,v in context.items() if k!='ci_files'},'pip_invocations':0,'publisher_requests':0,'publisher_json_bytes':0,'publisher_transports':[],
             'pip_internal_http_requests':None,'pip_internal_network_bytes':None,'observed_tree_peak_bytes':0,'tree_limit_is_hard_quota':False,
             'python_wheel_inputs_ready':False,'full_runtime_lock_ready':False,'installed_runtime_verified':False,'image_preparation_ready':False,'native_admission':False,'official_model_calls':0,
             'source_executions':0,'package_installs':0,'docker_calls':0,'routing_presence_only':{k:bool(os.environ.get(k)) for k in ('HTTP_PROXY','HTTPS_PROXY','SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE')}}
    try:
        ci=out/'source-ci';ci.mkdir()
        for name,raw in context.get('ci_files',{}).items():(ci/name).write_bytes(raw)
        receipt['local_provenance']=validate_input_provenance(root)
        for row in LOCAL_INPUTS:
            raw=read_regular(root/row['path'],256*MIB);_need(len(raw)==row['nbytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'LOCAL_INPUT_CHANGED')
        receipt['free_bytes_before']=shutil.disk_usage(out).free;_need(receipt['free_bytes_before']>=BUDGET['minimum_free_bytes'],'INSUFFICIENT_DISK')
        for name in ('wheels','tmp','publisher'):(out/name).mkdir(mode=0o700)
        cmd=pip_argv(root,request,out);receipt['tool']=_tool_facts(cmd);receipt['pip_argv']=cmd
        _run_pip(cmd,out,receipt)
        gate=parse(read_regular(out/'binary-gate.json',4096))
        _need(gate['schema']=='binary-pip-gate-v1' and gate['prepare_source_sha256']=='ccb9153120eef5c511d0a9c39b76d9dd0bc879a12b8492abaf5d3d5320cc94a4'
              and gate['gate_installed'] is True and gate['gate_restored'] is True and gate['only_wheel_links_admitted'] is True and gate['only_allowed_origins_admitted'] is True
              and type(gate['requirements_checked']) is int and 0<gate['requirements_checked']<=1024 and gate['rejections']==[],'BINARY_GATE_FAILED')
        receipt['binary_gate']=gate
        paths=sorted((out/'wheels').iterdir());_need(0<len(paths)<=96 and all(p.suffix=='.whl' and not p.is_symlink() for p in paths),'UNSUPPORTED_DOWNLOADED_SET')
        _need(time.monotonic()-started<BUDGET['total_timeout_seconds'],'OPERATION_DEADLINE');audit_stop=time.perf_counter()+min(120,BUDGET['total_timeout_seconds']-(time.monotonic()-started))
        rows=audit_wheels(paths,deadline=audit_stop)
        graph=wheel.validate_graph(rows,request['root_requirements'],deadline=audit_stop);_write(out/'target-graph.json',graph)
        local={Path(v['path']).name:v for v in LOCAL_INPUTS};seen=set();stop=min(started+BUDGET['total_timeout_seconds'],time.monotonic()+300)
        for row in rows:
            if row['filename'] in local:
                pin=local[row['filename']];_need(row['sha256']==pin['sha256'] and row['nbytes']==pin['nbytes'] and row['name']==pin['name'] and row['version']==pin['version'],'LOCAL_INPUT_CHANGED');seen.add(pin['id']);row['origin']={'kind':'registered-local-wheel-v1',**receipt['local_provenance'][pin['id']]}
            else:
                _need(receipt['publisher_requests']<96,'PUBLISHER_METADATA_LIMIT');receipt['publisher_requests']+=1
                data,transport=_release(row['name'],row['version'],out/'publisher'/(row['name']+'-'+row['version']+'.json'),stop);receipt['publisher_transports'].append(transport);receipt['publisher_json_bytes']+=transport['nbytes'];_need(receipt['publisher_json_bytes']<=BUDGET['max_json_total_bytes'],'PUBLISHER_METADATA_LIMIT')
                row['origin']={**wheel.verify_publisher(row,data),'release_url':transport['url'],'release_json_sha256':transport['sha256'],'release_json_nbytes':transport['nbytes']}
            receipt['observed_tree_peak_bytes']=max(receipt['observed_tree_peak_bytes'],_tree_bytes(out));_need(receipt['observed_tree_peak_bytes']<=BUDGET['operation_tree_limit_bytes'],'OPERATION_TREE_LIMIT')
        _need(seen=={r['id'] for r in LOCAL_INPUTS},'LOCAL_INPUT_NOT_SELECTED')
        _need(time.monotonic()-started<=BUDGET['total_timeout_seconds'],'OPERATION_DEADLINE')
        lock={'schema':'python-wheel-input-lock-v1','target':TARGET,'root_requirements':request['root_requirements'],'wheels':sorted(rows,key=lambda r:r['name']),'graph':graph,'python_wheel_inputs_ready':True,'installed_runtime_verified':False,'image_preparation_ready':False,'native_admission':False}
        raw=canonical(lock);_need(len(raw)<=16*MIB,'LOCK_LIMIT');_need(_tree_bytes(out)+len(raw)+MIB<=BUDGET['operation_tree_limit_bytes'],'OPERATION_TREE_LIMIT');(out/'wheels.lock.json').write_bytes(raw)
        receipt.update(status='PYTHON_WHEEL_INPUT_CLOSURE_VERIFIED',python_wheel_inputs_ready=True,wheel_count=len(rows),archive_bytes=sum(r['nbytes'] for r in rows),decoded_bytes=sum(r['decoded_bytes'] for r in rows),members=sum(r['member_count'] for r in rows),lock_sha256=hashlib.sha256(raw).hexdigest(),lock_nbytes=len(raw))
    except Exception as exc:
        allowed={'BINARY_GATE_FAILED','INVALID_LOCAL_PROVENANCE','LOCAL_INPUT_CHANGED','INSUFFICIENT_DISK','UNSUPPORTED_TOOL','UNSUPPORTED_PIP_CONFIGURATION','BINARY_WHEEL_DOWNLOAD_FAILED','UNSUPPORTED_DOWNLOADED_SET','OPERATION_DEADLINE','WHEEL_AUDIT_DEADLINE','WHEEL_SET_LIMIT','UNSUPPORTED_WHEEL_TARGET','UNSUPPORTED_WHEEL_PYTHON','WHEEL_INPUT_CHANGED','INVALID_WHEEL_INPUT','TARGET_GRAPH_REJECTED','TARGET_GRAPH_DEADLINE','DUPLICATE_WHEEL_DISTRIBUTION','MULTIPLE_CV2_PROVIDERS','DIRECT_DEPENDENCY_URL_REJECTED','UNSUPPORTED_TARGET_MARKER','INVALID_TARGET_REQUIREMENT','UNSATISFIED_TARGET_DEPENDENCY','UNDECLARED_TARGET_EXTRA','ORPHAN_WHEEL','PUBLISHER_METADATA_LIMIT','PUBLISHER_WHEEL_MISMATCH','PUBLISHER_REDIRECT_REJECTED','PUBLISHER_HTTP_REJECTED','METADATA_DEADLINE','OPERATION_TREE_LIMIT','UNSAFE_OPERATION_TREE','LOCK_LIMIT'}
        code=exc.args[0] if type(exc) is ValueError and len(exc.args)==1 and type(exc.args[0]) is str and exc.args[0] in allowed else 'PREPARATION_FAILED'
        if isinstance(exc,urllib.error.HTTPError):
            code='PUBLISHER_HTTP_REJECTED'
            if type(exc.code) is int and 100<=exc.code<=599:receipt['publisher_http_status']=exc.code
        elif isinstance(exc,urllib.error.URLError):code='PUBLISHER_TRANSPORT_FAILED'
        receipt['errors']=[{'code':code}]
    finally:
        receipt.update(finished_kst=_kst(),elapsed_seconds=time.monotonic()-started)
        _write(out/'receipt.json',receipt)
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--run',action='store_true');mode.add_argument('--guard-only',action='store_true');args=parser.parse_args();root=Path(__file__).resolve().parent.parent
    try:
        request=validate_request(parse(read_regular(root/REQUEST_PATH)),root)
        if args.guard_only:authenticate(root,request);print('REGISTERED_LOCAL_CONTEXT_VALID');return 0
        result=run_preparation(root,request);print(result['status']);return 0 if result['status']=='PYTHON_WHEEL_INPUT_CLOSURE_VERIFIED' else 1
    except Exception:print('LOCAL_WHEEL_CONTEXT_REJECTED');return 1

if __name__=='__main__':raise SystemExit(main())
