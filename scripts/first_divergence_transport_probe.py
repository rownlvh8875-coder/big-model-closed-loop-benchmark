"""Two-case CI transport association probe; no native/model acceptance claim.

The fixed receiver and module import are stdlib-only. The production launcher is
imported lazily by the parent; the only command substitutions live at Popen.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import select
import shutil
import stat
import subprocess
import sys
import time
import uuid

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO/'scripts/first_divergence_transport_probe.py'
WORKFLOW = '.github/workflows/stage7-first-divergence-transport.yml'
BRANCH = 'fix/first-divergence-launch-transport'
REPOSITORY = 'rownlvh8875-coder/big-model-closed-loop-benchmark'
SCHEMA = 'first-divergence-transport-v1'
LOG_CAP = 65536
ARTIFACT_CAP = 2097152
MANIFEST_CAP = ARTIFACT_CAP-2*LOG_CAP
CASE_CAP = 120
CLEANUP_RESERVE = 6
TOTAL_CAP = 300
EARLY_MARKER = 'FIRST_DIVERGENCE_PROBE_EARLY_EXIT_73'
SUBSTITUTIONS = ['fixed-stdlib-receiver-for-native-policy-cli', 'probe-only-omit-xvfb-auto-servernum']
CLAIMS = dict(official_model_calls=0, ort_sessions=0, metadrive_providers=0,
              original_strict_pass=False, historical_cause_proven=False,
              physical_fidelity_proven=False, installed_binary_equality_proven=False,
              full_native_model_test=False)
FORBIDDEN = ('onnxruntime', 'panda3d', 'direct', 'metadrive')


def _fail(message):
    raise ValueError(message)


def _modules_absent():
    if any(n == p or n.startswith(p+'.') for n in sys.modules for p in FORBIDDEN):
        _fail('native/model runtime module already imported')
    return True


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _hash(value, length=64):
    return type(value) is str and len(value)==length and all(c in '0123456789abcdef' for c in value)


def _fields(value, keys):
    if type(value) is not dict or set(value)!=set(keys):_fail('unexpected object fields')


def _equal(value, expected):
    if type(value) is not type(expected):return False
    if type(expected) is dict:
        return value.keys()==expected.keys() and all(_equal(value[k],v) for k,v in expected.items())
    if type(expected) is list:
        return len(value)==len(expected) and all(_equal(a,b) for a,b in zip(value,expected))
    return value==expected


def _json(data):
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:_fail('duplicate JSON key')
            result[k]=v
        return result
    def constant(value):_fail('nonfinite JSON number')
    try:return json.loads(data,object_pairs_hook=unique,parse_constant=constant)
    except (UnicodeError,json.JSONDecodeError) as exc:raise ValueError('invalid JSON') from exc


def _positive(value):
    return type(value) is int and value>0


def _finite(value, limit):
    return type(value) in (int,float) and 0<=value<=limit and math.isfinite(value)


def _safe(root):
    root=Path(root).absolute()
    if any(p.is_symlink() for p in (root,*root.parents)):_fail('symlink path prohibited')
    if '..' in root.parts:_fail('path traversal prohibited')
    return root


def _production():
    # Direct script execution places scripts/, rather than the checkout, on sys.path.
    if str(REPO) not in sys.path:sys.path.insert(0,str(REPO))
    from bigbench import first_divergence_model
    return first_divergence_model


def _remaining(deadline, cap):
    remaining=deadline-time.monotonic()
    if remaining<=0:raise subprocess.TimeoutExpired('probe deadline',cap)
    return min(cap,remaining)


def _git(*args, timeout=10):
    result=subprocess.run(['git',*args],cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
    if result.returncode:_fail('required local Git blob unavailable')
    return result.stdout


def _verify_sources(head, snapshot, *, deadline=None):
    if deadline is None:deadline=time.monotonic()+TOTAL_CAP
    capture=_production().capture
    if not _equal(snapshot,capture.source_snapshot()):_fail('current source map mismatch')
    for name,digest in snapshot.items():
        if _sha(_git('show',head+':'+name,timeout=_remaining(deadline,10)))!=digest:_fail('actual commit source blob mismatch: '+name)


def _context():
    expected_ref=REPOSITORY+'/'+WORKFLOW+'@refs/heads/'+BRANCH
    if (os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REPOSITORY')!=REPOSITORY or
        os.environ.get('GITHUB_EVENT_NAME')!='push' or os.environ.get('GITHUB_REF_NAME')!=BRANCH or
        os.environ.get('GITHUB_RUN_ATTEMPT')!='1' or os.environ.get('GITHUB_WORKFLOW_REF')!=expected_ref):
        _fail('actual registered GitHub push/branch/workflow/attempt required')
    head=os.environ.get('GITHUB_SHA')
    if not _hash(head,40) or _git('rev-parse','HEAD').decode().strip()!=head:_fail('actual checkout head mismatch')
    run=os.environ.get('GITHUB_RUN_ID','')
    if not run.isdecimal() or int(run)<=0:_fail('invalid actual run id')
    if any(not os.environ.get(n) for n in ('ImageOS','ImageVersion')):_fail('missing runner image identity')
    return dict(repository=REPOSITORY,workflow_path=WORKFLOW,workflow_ref=expected_ref,
                head_sha=head,run_id=int(run),attempt=1,event='push',branch=BRANCH)


def _tool_output(argv, *, deadline):
    # A bounded sink avoids retaining unbounded tool version output in memory.
    timeout=_remaining(deadline,5)
    process=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
    data=bytearray();deadline=min(deadline,time.monotonic()+timeout)
    try:
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise subprocess.TimeoutExpired(argv,5)
            ready,_,_=select.select([process.stdout],[],[],remaining)
            if not ready:raise subprocess.TimeoutExpired(argv,5)
            block=os.read(process.stdout.fileno(),4096)
            if not block:break
            if len(data)+len(block)>4096:_fail('tool metadata output cap')
            data.extend(block)
        if process.wait(timeout=max(.001,deadline-time.monotonic()))!=0:_fail('tool metadata command failed')
        value=data.decode('utf-8').strip()
        if not value:_fail('empty tool version')
        return value
    finally:
        if process.poll() is None:
            import signal
            os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=2)
        process.stdout.close()


def _tools(*, deadline):
    wrapper=shutil.which('xvfb-run');xauth=shutil.which('xauth')
    if not wrapper or not xauth:_fail('xvfb-run and xauth are required')
    return dict(wrapper_path=str(Path(wrapper).resolve()),wrapper_sha256=_sha(Path(wrapper).read_bytes()),
                wrapper_version=_tool_output(['dpkg-query','-W','-f=${Version}','xvfb'],deadline=deadline),
                xauth_path=str(Path(xauth).resolve()),xauth_version=_tool_output([xauth,'-V'],deadline=deadline))


def _record(tag, value):
    data=tag.encode()+b' '+_canonical(value)+b'\n'
    if len(data)>4096:_fail('receiver record cap')
    if os.write(1,data)!=len(data):_fail('short receiver output write')


def _receive(args):
    """Fixed stdlib receiver. No production imports or native admission call."""
    _modules_absent()
    if args.case not in ('normal','early_exit') or not _hash(args.nonce) or not _hash(args.parent_uuid,32):
        _fail('invalid fixed receiver association')
    fdtext=os.environ.pop('FIRST_DIVERGENCE_TRIAL_FD',None)
    if not fdtext or not fdtext.isdecimal() or int(fdtext)<10:_fail('high inherited descriptor required')
    fd=int(fdtext)
    try:
        if not stat.S_ISFIFO(os.fstat(fd).st_mode):_fail('authorization descriptor is not FIFO')
        if args.parent_pid<=0 or args.parent_pid==os.getpid():_fail('invalid live parent')
        os.kill(args.parent_pid,0)
        if 'FIRST_DIVERGENCE_ACCEPTANCE' in os.environ:_fail('model acceptance must be absent')
        if Path(args.model).exists():_fail('dummy model must be absent')
        identity=dict(case=args.case,pid=os.getpid(),pgid=os.getpgid(0),fd=fd,
                      parent_pid=args.parent_pid,parent_uuid=args.parent_uuid,nonce=args.nonce,
                      source_sha256=args.source_sha256,runtime_sha256=args.runtime_sha256,
                      modules_absent=_modules_absent(),model_path_absent=True,pipe_fifo=True)
        _record('PROBE_RECEIVER_START',identity)
        if args.case=='early_exit':
            os.write(2,(EARLY_MARKER+'\n').encode())
            return 73
        deadline=time.monotonic()+args.timeout
        data=bytearray()
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0:_fail('receiver read deadline')
            readable,_,_=select.select([fd],[],[],remaining)
            if not readable:_fail('receiver read deadline')
            block=os.read(fd,65536)
            if not block:break
            data.extend(block)
            if len(data)>8*1024*1024:_fail('permit byte cap')
        permit=_json(bytes(data))
        _fields(permit,{'parent_pid','parent_uuid','process_group','nonce','arm','repeat','source_snapshot',
                        'runtime','schedule_index','storage_limits'})
        for key,want in dict(parent_pid=args.parent_pid,parent_uuid=args.parent_uuid,
                             process_group=os.getpgid(0),nonce=args.nonce,arm='original',repeat=0,schedule_index=0).items():
            if not _equal(permit[key],want):_fail('permit association mismatch')
        if not _equal(permit['storage_limits'],dict(payload_limit_bytes=0,trial_ledger_limit_bytes=4096,log_limit_bytes=LOG_CAP)):
            _fail('permit storage allocation mismatch')
        sources=permit['source_snapshot']
        if type(sources) is not dict or not sources or any(type(k) is not str or not _hash(v) for k,v in sources.items()):
            _fail('invalid permit source map')
        if type(permit['runtime']) is not dict or not permit['runtime']:_fail('invalid permit runtime')
        if _sha(_canonical(sources))!=args.source_sha256 or _sha(_canonical(permit['runtime']))!=args.runtime_sha256:
            _fail('permit source/runtime association mismatch')
        os.kill(args.parent_pid,0)
        closing,fd=fd,None;os.close(closing)
        try:os.fstat(closing)
        except OSError as exc:
            import errno
            if exc.errno!=errno.EBADF:raise
        else:_fail('authorization descriptor remains open')
        _record('PROBE_PERMIT_RECEIVED',dict(identity,received_bytes=len(data),eof=True,fd_closed=True,
                                           permit_validated=True,modules_absent=_modules_absent()))
        return 0
    finally:
        if fd is not None:os.close(fd)


@contextmanager
def _without_acceptance():
    original=os.environ.pop('FIRST_DIVERGENCE_ACCEPTANCE',None)
    try:yield
    finally:
        if original is not None:os.environ['FIRST_DIVERGENCE_ACCEPTANCE']=original


def _group_gone(pid):
    try:os.killpg(pid,0)
    except ProcessLookupError:return True
    return False


def _case(out, case, parent_uuid, source_hash, runtime_hash, total_deadline):
    model=_production();started=time.monotonic()
    execution_deadline=min(started+CASE_CAP,total_deadline)-CLEANUP_RESERVE
    nonce=secrets.token_hex(32)
    dummy=out.parent/'NO_MODEL_FOR_TRANSPORT_PROBE.onnx'
    if dummy.exists():_fail('dummy model path exists')
    spec=REPO/'model_specs/md-v3.json'
    row=dict(launched=False,launcher_pid=None,process_group=None,exit_code=None,cleanup_errors=[],
             storage=dict(payload_limit_bytes=0,trial_ledger_limit_bytes=model.MIN_LEDGER_BYTES,
                          log_limit_bytes=LOG_CAP,log_bytes=0,limit_error=None))
    result=dict(case=case,nonce=nonce,launcher_pid=None,process_group=None,receiver=None,
                receipt=None,exit_code=None,delivery_error=None,launch_timeout_s=None,wait_timeout_s=None,
                elapsed_s=0.,cleanup_errors=[],group_gone=False,reaped=False,log=None,
                wrapper_waited_before_delivery=False,storage=row['storage'])
    raw=[];child=None;real_popen=subprocess.Popen
    original_env=dict(os.environ)
    failure=None

    def adapter(command, **kwargs):
        expected=['xvfb-run','-a',sys.executable,'-m','scripts.first_divergence_audit','native-trial',
                  '--model',str(dummy.resolve()),'--spec',str(spec.resolve()),'--out',str(out),
                  '--arm','original','--repeat','0','--nonce',nonce]
        fdtext=kwargs.get('env',{}).get('FIRST_DIVERGENCE_TRIAL_FD','')
        if not fdtext.isdecimal() or int(fdtext)<10:_fail('unexpected production read descriptor')
        expected_kwargs=dict(cwd=model.capture.REPO_ROOT,env=dict(original_env,FIRST_DIVERGENCE_TRIAL_FD=fdtext),
                             stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(int(fdtext),))
        if command!=expected or kwargs!=expected_kwargs:_fail('unexpected production command/kwargs')
        if raw:_fail('wrapper retry prohibited')
        remaining=execution_deadline-time.monotonic()
        if remaining<=0:raise subprocess.TimeoutExpired('probe adapter',0)
        receiver=[sys.executable,str(SCRIPT),'_receive','--case',case,'--parent-pid',str(os.getpid()),
                  '--parent-uuid',parent_uuid,'--nonce',nonce,'--source-sha256',source_hash,
                  '--runtime-sha256',runtime_hash,'--model',str(dummy),'--timeout',str(remaining)]
        process=real_popen(['xvfb-run',*receiver],**kwargs);raw.append(process)
        if case=='early_exit':
            try:
                process.wait(timeout=max(.001,execution_deadline-time.monotonic()))
                result['wrapper_waited_before_delivery']=True
            except BaseException:
                # Ownership has not reached the production launcher yet.
                result['cleanup_errors'].extend(model._terminate_group(process))
                if process.stdout is not None:process.stdout.close()
                raise
        return process

    try:
        result['launch_timeout_s']=execution_deadline-time.monotonic()
        if result['launch_timeout_s']<=0:raise subprocess.TimeoutExpired('probe case',0)
        subprocess.Popen=adapter
        try:
            child=model._launch_trial(dummy,spec,out,'original',0,nonce,parent_uuid,0,row,
                                      timeout=result['launch_timeout_s'])
        finally:subprocess.Popen=real_popen
        result['wait_timeout_s']=execution_deadline-time.monotonic()
        if result['wait_timeout_s']<=0:raise subprocess.TimeoutExpired('probe wait',0)
        result['exit_code']=child.wait(timeout=result['wait_timeout_s'])
        if case!='normal' or result['exit_code']!=0:_fail('unexpected receiver completion')
    except BrokenPipeError as exc:
        result['delivery_error']='BrokenPipeError'
        if case!='early_exit':failure=exc
    except BaseException as exc:
        failure=exc
    finally:
        subprocess.Popen=real_popen
        if child is not None:
            # Raw handle is essential: output draining may itself have failed.
            result['cleanup_errors'].extend(model._terminate_group(child.process))
            try:child.drain_available()
            except Exception as exc:result['cleanup_errors'].append('output drain: '+type(exc).__name__)
            child.close_output();result['cleanup_errors'].extend(child.output_cleanup_errors)
        result['cleanup_errors'].extend(row['cleanup_errors'])
        if raw:
            process=raw[0]
            result.update(launcher_pid=process.pid,process_group=process.pid,exit_code=process.returncode,
                          group_gone=_group_gone(process.pid),reaped=process.poll() is not None)
        path=out/'process.log'
        if path.is_file():
            data=path.read_bytes()
            result['log']=dict(path=case+'/process.log',bytes=len(data),sha256=_sha(data))
            try:
                result['receiver'],result['receipt']=_parse_log(data,case)
            except ValueError as exc:
                if failure is None:failure=exc
        result['elapsed_s']=time.monotonic()-started
        if result['elapsed_s']>CASE_CAP or not result['group_gone'] or not result['reaped'] or result['cleanup_errors']:
            if failure is None:failure=ValueError('case time/cleanup unconfirmed')
    if failure is not None:result['error']=type(failure).__name__+': '+str(failure)[:1000]
    return result


def _parse_log(data,case):
    starts=[];receipts=[]
    for line in data.splitlines():
        if line.startswith(b'PROBE_RECEIVER_START '):starts.append(_json(line.split(b' ',1)[1]))
        if line.startswith(b'PROBE_PERMIT_RECEIVED '):receipts.append(_json(line.split(b' ',1)[1]))
    if len(starts)!=1 or len(receipts)!=(1 if case=='normal' else 0):_fail('missing/duplicate actual receiver evidence')
    if case=='early_exit' and data.splitlines().count(EARLY_MARKER.encode())!=1:_fail('missing early stderr marker')
    return starts[0],receipts[0] if receipts else None


def _encode(value):
    return (json.dumps(value,indent=2,allow_nan=False)+'\n').encode()


def _publish(out, manifest):
    payload=_encode(manifest)
    if len(payload)>MANIFEST_CAP:_fail('probe manifest cap')
    existing=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    if existing+len(payload)>ARTIFACT_CAP:_fail('probe artifact cap')
    with (out/'probe.json').open('xb') as stream:stream.write(payload)


def run_probe(out: Path) -> dict:
    started=time.monotonic();total_deadline=started+TOTAL_CAP
    _modules_absent();context=_context()
    temptext=os.environ.get('RUNNER_TEMP')
    if not temptext:_fail('RUNNER_TEMP required')
    temp=_safe(Path(temptext));out=_safe(Path(out))
    if temp==out or temp not in out.parents or out.exists():_fail('fresh output strictly below RUNNER_TEMP required')
    model=_production();_modules_absent()
    snapshot=model.capture.source_snapshot();_verify_sources(context['head_sha'],snapshot,deadline=total_deadline-CLEANUP_RESERVE)
    runtime=model._runtime_identity();tools=_tools(deadline=total_deadline-CLEANUP_RESERVE)
    _remaining(total_deadline-CLEANUP_RESERVE,TOTAL_CAP)
    manifest=dict(schema=SCHEMA,status='FAILED_OR_INCOMPLETE',context=context,source_snapshot=snapshot,
                  source_sha256=_sha(_canonical(snapshot)),runtime=runtime,runtime_sha256=_sha(_canonical(runtime)),
                  tools=tools,parent_pid=os.getpid(),parent_uuid=uuid.uuid4().hex,claims=dict(CLAIMS),
                  substitutions=list(SUBSTITUTIONS),limits=dict(case_s=CASE_CAP,cleanup_reserve_s=CLEANUP_RESERVE,
                  total_s=TOTAL_CAP,log_bytes=LOG_CAP,artifact_bytes=ARTIFACT_CAP,manifest_bytes=MANIFEST_CAP,
                  max_wrappers=2,max_servers=2),cases=[],elapsed_s=0.,parent_modules_absent=True,
                  model_path_absent=True,wrapper_launches=0)
    out.mkdir(parents=True)
    try:
        model._enable_subreaper()
        with _without_acceptance():
            for case in ('normal','early_exit'):
                result=_case(out/case,case,manifest['parent_uuid'],manifest['source_sha256'],
                             manifest['runtime_sha256'],total_deadline)
                manifest['cases'].append(result)
                manifest['wrapper_launches']+=int(result['launcher_pid'] is not None)
                if 'error' in result:_fail(result['error'])
        manifest['elapsed_s']=time.monotonic()-started
        manifest['parent_modules_absent']=_modules_absent()
        manifest['status']='TRANSPORT_ASSOCIATION_VALIDATED'
        _validate(out,manifest,manifest_present=False,deadline=total_deadline-CLEANUP_RESERVE)
        manifest['elapsed_s']=time.monotonic()-started
        _remaining(total_deadline-CLEANUP_RESERVE,TOTAL_CAP)
        _publish(out,manifest)
        return manifest
    except BaseException as primary:
        manifest.update(status='FAILED_OR_INCOMPLETE',error=type(primary).__name__+': '+str(primary)[:1200],
                        elapsed_s=time.monotonic()-started)
        try:_publish(out,manifest)
        except BaseException as publication:
            # Independent minimal serializer preserves the initiating error even
            # if the ordinary JSON publication path fails. Never overwrite logs.
            compact=dict(schema=SCHEMA,status='FAILED_OR_INCOMPLETE',error=manifest['error'],
                         publication_error=type(publication).__name__+': '+str(publication)[:500],
                         wrapper_launches=manifest['wrapper_launches'],cases=manifest['cases'])
            data=(json.dumps(compact,allow_nan=False)+'\n').encode()
            if len(data)>MANIFEST_CAP:
                compact['cases']=[{k:r.get(k) for k in ('case','launcher_pid','process_group','exit_code','error','log','cleanup_errors')} for r in manifest['cases']]
                data=(json.dumps(compact,allow_nan=False)+'\n').encode()
            path=out/'probe.json'
            if path.exists():path.unlink()
            with path.open('xb') as stream:stream.write(data)
            return compact
        return manifest


def _validate(root, value, *, manifest_present, deadline=None):
    root=_safe(root)
    _fields(value,{'schema','status','context','source_snapshot','source_sha256','runtime','runtime_sha256','tools',
                   'parent_pid','parent_uuid','claims','substitutions','limits','cases','elapsed_s',
                   'parent_modules_absent','model_path_absent','wrapper_launches'})
    if value['schema']!=SCHEMA or value['status']!='TRANSPORT_ASSOCIATION_VALIDATED':_fail('probe incomplete')
    if not _equal(value['claims'],CLAIMS) or not _equal(value['substitutions'],SUBSTITUTIONS):_fail('unsupported claims/substitutions')
    if value['parent_modules_absent'] is not True or value['model_path_absent'] is not True:_fail('zero-model evidence absent')
    if not _positive(value['parent_pid']) or not _hash(value['parent_uuid'],32):_fail('invalid parent identity')
    context=value['context']
    _fields(context,{'repository','workflow_path','workflow_ref','head_sha','run_id','attempt','event','branch'})
    expected=dict(repository=REPOSITORY,workflow_path=WORKFLOW,workflow_ref=REPOSITORY+'/'+WORKFLOW+'@refs/heads/'+BRANCH,
                  head_sha=context['head_sha'],run_id=context['run_id'],attempt=1,event='push',branch=BRANCH)
    if not _equal(context,expected) or not _hash(context['head_sha'],40) or not _positive(context['run_id']):_fail('invalid run context')
    _verify_sources(context['head_sha'],value['source_snapshot'],deadline=deadline)
    if not _hash(value['source_sha256']) or value['source_sha256']!=_sha(_canonical(value['source_snapshot'])):_fail('source digest mismatch')
    runtime=value['runtime']
    _fields(runtime,{'python','executable','numpy','opencv-python-headless','panda3d','metadrive-simulator','onnxruntime','ImageOS','ImageVersion'})
    if any(type(runtime[n]) is not str or not runtime[n] for n in ('python','executable','ImageOS','ImageVersion','numpy','opencv-python-headless')):
        _fail('missing Python/image/dependency runtime metadata')
    if any(runtime[n] is not None and (type(runtime[n]) is not str or not runtime[n]) for n in ('panda3d','metadrive-simulator','onnxruntime')):
        _fail('invalid distribution metadata')
    if value['runtime_sha256']!=_sha(_canonical(runtime)):_fail('runtime digest mismatch')
    tools=value['tools'];_fields(tools,{'wrapper_path','wrapper_sha256','wrapper_version','xauth_path','xauth_version'})
    if not _hash(tools['wrapper_sha256']) or any(type(tools[n]) is not str or not tools[n] or len(tools[n])>4096 for n in tools if n!='wrapper_sha256'):
        _fail('missing wrapper/xauth identity')
    if any(not Path(tools[n]).is_absolute() for n in ('wrapper_path','xauth_path')):_fail('invalid executable path')
    limits=dict(case_s=120,cleanup_reserve_s=6,total_s=300,log_bytes=65536,artifact_bytes=2097152,
                manifest_bytes=1966080,max_wrappers=2,max_servers=2)
    if not _equal(value['limits'],limits) or type(value['wrapper_launches']) is not int or value['wrapper_launches']!=2:_fail('probe limit mismatch')
    if not _finite(value['elapsed_s'],TOTAL_CAP):_fail('probe total deadline exceeded')
    if type(value['cases']) is not list or len(value['cases'])!=2:_fail('exactly two cases required')
    members={'normal/process.log','early_exit/process.log'}|({'probe.json'} if manifest_present else set())
    actual=set();total=0
    for p in root.rglob('*'):
        if p.is_symlink():_fail('symlink artifact member')
        name=p.relative_to(root).as_posix()
        if p.is_dir():
            if name not in ('normal','early_exit'):_fail('extra artifact directory')
        elif p.is_file():
            if name not in members:_fail('extra artifact member')
            actual.add(name);total+=p.stat().st_size
        else:_fail('unsafe artifact member type')
    if actual!=members or total>ARTIFACT_CAP:_fail('missing member/artifact cap')
    wrapper_ids=[];receiver_ids=[];nonces=[];elapsed=0
    for case,row in zip(('normal','early_exit'),value['cases']):
        _fields(row,{'case','nonce','launcher_pid','process_group','receiver','receipt','exit_code','delivery_error',
                     'launch_timeout_s','wait_timeout_s','elapsed_s','cleanup_errors','group_gone','reaped','log',
                     'wrapper_waited_before_delivery','storage'})
        if row['case']!=case or not _hash(row['nonce']):_fail('case/nonce mismatch')
        if not _positive(row['launcher_pid']) or row['process_group']!=row['launcher_pid'] or type(row['process_group']) is not int:
            _fail('invalid actual wrapper group')
        if row['launcher_pid']==value['parent_pid']:_fail('wrapper must differ from parent')
        wrapper_ids.append(row['launcher_pid']);nonces.append(row['nonce'])
        if row['cleanup_errors']!=[] or type(row['cleanup_errors']) is not list or row['group_gone'] is not True or row['reaped'] is not True:_fail('group cleanup unconfirmed')
        if not _finite(row['elapsed_s'],CASE_CAP):_fail('case deadline exceeded')
        elapsed+=row['elapsed_s']
        if not _finite(row['launch_timeout_s'],CASE_CAP-CLEANUP_RESERVE) or row['launch_timeout_s']<=0:_fail('invalid launch deadline')
        if case=='normal':
            if not _finite(row['wait_timeout_s'],row['launch_timeout_s']) or row['wait_timeout_s']<=0:_fail('invalid remaining wait budget')
        elif row['wait_timeout_s'] is not None:_fail('early-exit must fail during delivery')
        if not _equal(row['exit_code'],0 if case=='normal' else 73):_fail('unexpected case exit')
        if row['delivery_error']!=(None if case=='normal' else 'BrokenPipeError'):_fail('unexpected pipe delivery outcome')
        if row['wrapper_waited_before_delivery'] is not (case=='early_exit'):_fail('early synchronization absent')
        log=row['log'];_fields(log,{'path','bytes','sha256'})
        if log['path']!=case+'/process.log' or type(log['bytes']) is not int or not 0<log['bytes']<=LOG_CAP or not _hash(log['sha256']):_fail('invalid log descriptor')
        path=root/log['path'];data=path.read_bytes()
        if len(data)!=log['bytes'] or _sha(data)!=log['sha256']:_fail('log bytes/hash mismatch')
        start,receipt=_parse_log(data,case)
        if not _equal(start,row['receiver']) or not _equal(receipt,row['receipt']):_fail('receiver evidence mismatch')
        _fields(start,{'case','pid','pgid','fd','parent_pid','parent_uuid','nonce','source_sha256','runtime_sha256',
                       'modules_absent','model_path_absent','pipe_fifo'})
        if not _positive(start['pid']) or start['pid'] in (row['launcher_pid'],value['parent_pid']):_fail('invalid distinct receiver PID')
        receiver_ids.append(start['pid'])
        want=dict(case=case,pid=start['pid'],pgid=row['process_group'],fd=start['fd'],parent_pid=value['parent_pid'],
                  parent_uuid=value['parent_uuid'],nonce=row['nonce'],source_sha256=value['source_sha256'],
                  runtime_sha256=value['runtime_sha256'],modules_absent=True,model_path_absent=True,pipe_fifo=True)
        if not _equal(start,want) or type(start['fd']) is not int or start['fd']<10:_fail('receiver association mismatch')
        lines=data.splitlines()
        if lines.count(f'authorization_fd={start["fd"]} phase=prepared'.encode())!=1 or lines.count(f'phase=permit launcher_pid={row["launcher_pid"]}'.encode())!=1:
            _fail('missing actual launcher phase/descriptor evidence')
        sent=lines.count(b'phase=permit_sent')
        if sent!=(1 if case=='normal' else 0):_fail('unexpected permit phase')
        if case=='normal':
            _fields(receipt,set(start)|{'received_bytes','eof','fd_closed','permit_validated'})
            if not _positive(receipt['received_bytes']) or receipt['received_bytes']>8*1024*1024:_fail('invalid permit receipt size')
            if not _equal(receipt,dict(start,received_bytes=receipt['received_bytes'],eof=True,fd_closed=True,permit_validated=True)):_fail('normal permit receipt invalid')
        storage=row['storage']
        if not _equal(storage,dict(payload_limit_bytes=0,trial_ledger_limit_bytes=4096,log_limit_bytes=65536,log_bytes=len(data),limit_error=None)):
            _fail('actual storage count mismatch')
    if len(set(wrapper_ids+receiver_ids))!=4 or len(set(nonces))!=2:_fail('distinct real cases required')
    if elapsed>value['elapsed_s']:_fail('incoherent elapsed times')
    return value


def validate_probe(root: Path) -> dict:
    root=_safe(root);path=root/'probe.json'
    if not path.is_file() or path.is_symlink() or path.stat().st_size>MANIFEST_CAP:_fail('missing/oversize/unsafe probe manifest')
    return _validate(root,_json(path.read_bytes()),manifest_present=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run');run.add_argument('--out',type=Path,required=True)
    validate=sub.add_parser('validate');validate.add_argument('--root',type=Path,required=True)
    receiver=sub.add_parser('_receive')
    for name in ('case','parent-uuid','nonce','source-sha256','runtime-sha256','model'):receiver.add_argument('--'+name,required=True)
    receiver.add_argument('--parent-pid',type=int,required=True);receiver.add_argument('--timeout',type=float,required=True)
    args=parser.parse_args(argv)
    try:
        # This dispatch must precede all production/NumPy/OpenCV imports.
        if args.command=='_receive':return _receive(args)
        value=run_probe(args.out) if args.command=='run' else validate_probe(args.root)
        print(json.dumps({'schema':value['schema'],'status':value['status']}))
        return 0 if value['status']=='TRANSPORT_ASSOCIATION_VALIDATED' else 1
    except Exception as exc:
        print(type(exc).__name__+': '+str(exc)[:1200],file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
