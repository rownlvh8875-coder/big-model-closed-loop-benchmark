"""Bounded, CI-only accepted-buffer diagnostic. Imports start no processes/sessions.

The model phase is available only after API-bound camera/source acceptance. All
results are descriptive and never replace the original failed strict gate.
"""
from __future__ import annotations
from dataclasses import asdict
from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path
import secrets
import signal
import stat
import subprocess
import sys
import tempfile
from time import perf_counter
import uuid
import zipfile

import numpy as np
from . import first_divergence as capture

SCHEDULE = (('original',0),('proxy',0),('retention',0),('retention',1),('proxy',1),('original',1))
STEPS = 4
CHILD_LIMIT_S = 480
STUDY_LIMIT_S = 2400
PROCESS_LOG_CAP_BYTES = 1024 * 1024
MIN_LEDGER_BYTES = 4096
WORKFLOW_PATH = '.github/workflows/stage7-first-divergence.yml'
REQUEST_PATH = '.github/stage7-first-divergence-request.json'
ARTIFACT_NAME = 'stage7-first-divergence-canary'
BRANCH = 'fix/public-onnx-action-frame'
REQUEST_SCHEMA = 'first-divergence-request-v1'
TRIAL_SCHEMA = 'first-divergence-trial-v1'
STUDY_SCHEMA = 'first-divergence-study-v1'
RECEIPT_SCHEMA = 'first-divergence-source-receipt-v1'
GATE_SCHEMA = 'first-divergence-acceptance-v1'
MODEL_SHA = '35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199'
MODEL_BYTES = 768750198
SPEC_SHA = '689f4d80082070b08ff35920e37d7070e811dfb42a279909751f79e900c735e2'
STATE_DTYPES = {'state_img_q':'uint8','state_desire_q':'float32','state_feat_q':'float32'}
PROTOCOL = dict(capture.CANARY_PROTOCOL,steps=STEPS,schedule=[list(x) for x in SCHEDULE])
LIMITATION = capture.LIMITATION + ' Other feeds are source-reconstructed, not intercepted tensors; installed binaries/system equality is unproven.'


def _fail(message):
    raise ValueError(message)


def _json_write(path, value, *, byte_limit=None):
    path=Path(path); capture._safe_path(path.parent,path.name)
    path.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(value,indent=2,allow_nan=False)+'\n'
    if len(payload.encode())>min(capture.MANIFEST_CAP_BYTES,byte_limit if byte_limit is not None else capture.MANIFEST_CAP_BYTES): _fail('JSON byte cap')
    with path.open('x',encoding='utf-8') as stream: stream.write(payload)



class _StorageBudget:
    """Conservative disk reservation; rejected writes never touch a member."""
    def __init__(self,limit):
        if type(limit) is not int or limit<0:_fail('invalid storage budget')
        self.limit=limit;self.charged=0
    def reserve(self,nbytes):
        if type(nbytes) is not int or nbytes<0 or self.charged+nbytes>self.limit:
            _fail('payload storage budget exhausted before write')
        self.charged+=nbytes


def _ledger_reserve(cap):
    if cap<2*MIN_LEDGER_BYTES:_fail('dataset cap cannot reserve bounded failure ledgers')
    return min(capture.MANIFEST_CAP_BYTES,cap//2)


def _child_storage_limits(available):
    if available<MIN_LEDGER_BYTES:_fail('dataset budget cannot reserve next child ledger')
    ledger=min(capture.MANIFEST_CAP_BYTES,max(MIN_LEDGER_BYTES,available//2))
    log=min(PROCESS_LOG_CAP_BYTES,(available-ledger)//4)
    return dict(payload_limit_bytes=available-ledger-log,trial_ledger_limit_bytes=ledger,log_limit_bytes=log)


def _storage_limits(value):
    capture._fields(value,{'payload_limit_bytes','trial_ledger_limit_bytes','log_limit_bytes'})
    if (any(type(v) is not int or v<0 for v in value.values()) or value['trial_ledger_limit_bytes']<MIN_LEDGER_BYTES or
        value['trial_ledger_limit_bytes']>capture.MANIFEST_CAP_BYTES or value['log_limit_bytes']>PROCESS_LOG_CAP_BYTES or
        sum(value.values())>capture.DATASET_CAP_BYTES):_fail('invalid child disk allocation')
    return value


class _LogSink:
    """Keep an explicit byte prefix, then stop the child rather than grow disk."""
    def __init__(self,path,limit):
        self.limit=limit;self.nbytes=0
        path=Path(path);capture._safe_path(path.parent,path.name)
        self.stream=path.open('xb')
    def write(self,data):
        keep=min(len(data),max(0,self.limit-self.nbytes))
        if keep:self.stream.write(data[:keep]);self.stream.flush();self.nbytes+=keep
        if keep!=len(data):_fail('process log storage budget exhausted; bounded prefix retained')
    def close(self):self.stream.close()


class _BoundedChild:
    """Drain the actual stdout/stderr pipe through the bounded sink while waiting."""
    def __init__(self,process,sink,storage):
        self.process=process;self.sink=sink;self.storage=storage;self.output_closed=False;self.output_cleanup_errors=[]
    @property
    def pid(self):return self.process.pid
    @property
    def returncode(self):return self.process.returncode
    def close_output(self):
        if not self.output_closed:
            self.output_closed=True
            for close in (self.process.stdout.close,self.sink.close):
                try:close()
                except OSError as exc:self.output_cleanup_errors.append(f'output close: {type(exc).__name__}: {exc}')
        self.storage['log_bytes']=self.sink.nbytes
    def wait(self,timeout):
        deadline=perf_counter()+timeout
        if not self.output_closed:
            import select
            try:
                while True:
                    remaining=deadline-perf_counter()
                    if remaining<=0:raise subprocess.TimeoutExpired('bounded child output',timeout)
                    ready,_,_=select.select([self.process.stdout],[],[],remaining)
                    if not ready:raise subprocess.TimeoutExpired('bounded child output',timeout)
                    block=os.read(self.process.stdout.fileno(),65536)
                    if not block:break
                    self.sink.write(block)
            except ValueError as exc:
                self.storage['limit_error']=str(exc);self.close_output();raise
            else:
                self.close_output()
                if self.output_cleanup_errors:_fail('process output close unconfirmed')
        return self.process.wait(timeout=max(0.,deadline-perf_counter()))


def _publish_ledger(path,data,limit):
    """Metadata overflow is explicit failed evidence, never deletion of raw files."""
    payload=json.dumps(data,indent=2,allow_nan=False)+'\n'
    if len(payload.encode())>limit:
        keep={'schema','error','error_chain','cleanup_errors','model_calls_lower_bound','model_calls_upper_bound',
              'parent_pid','parent_uuid','process_id','process_uuid','arm','repeat','nonce','provider_closed','launch_ledger','storage'}
        compact={k:v for k,v in data.items() if k in keep}
        compact.update(status='FAILED_OR_INCOMPLETE',model_calls=None,metadata_omitted={})
        if not compact.get('error'):compact['error']='ledger storage budget exhausted; metadata explicitly omitted'
        for k,v in data.items():
            if k not in keep and k not in ('status','model_calls'):
                encoded=json.dumps(v,allow_nan=False).encode()
                compact['metadata_omitted'][k]=dict(nbytes=len(encoded),sha256=sha256(encoded).hexdigest())
        for k in ('error','error_chain','cleanup_errors'):
            if k in compact:
                value=compact[k]
                if isinstance(value,str):compact[k]=value[:512]+(' [TRUNCATED]' if len(value)>512 else '')
                elif isinstance(value,list):compact[k]=[str(x)[:256] for x in value[:4]]
        if len((json.dumps(compact,indent=2,allow_nan=False)+'\n').encode())>limit:
            value=compact.pop('launch_ledger',None)
            if value is not None:
                encoded=json.dumps(value,allow_nan=False).encode()
                compact['metadata_omitted']['launch_ledger']=dict(nbytes=len(encoded),sha256=sha256(encoded).hexdigest())
        data=compact
    _json_write(path,data,byte_limit=limit)
    return data


def _hash_file(path):
    h=sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def _array(value, shape, dtype):
    if not isinstance(value,np.ndarray) or value.shape!=tuple(shape) or value.dtype!=np.dtype(dtype) or not np.all(np.isfinite(value)):
        _fail('typed finite array contract mismatch')
    return value


def _copy(value):
    result=np.array(value,copy=True,order='C'); result.setflags(write=False); return result


def _descriptor(value):
    return dict(shape=list(value.shape),dtype=value.dtype.name,nbytes=value.nbytes,
                sha256=sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest())


def retention_preflight(spec):
    """Declared official typed payload, including post-close and live overlap."""
    from .onnx_contract import ModelContract
    spec=Path(spec)
    if _hash_file(spec)!=SPEC_SHA: _fail('official spec required')
    contract=ModelContract.load(spec)
    state=sum(math.prod(contract.input_shapes[k])*np.dtype(v).itemsize for k,v in STATE_DTYPES.items())
    fixed=(8+2+2)*4
    output=(4+contract.output_slices['plan'][1]-contract.output_slices['plan'][0])*4
    # 8 state snapshots, each step's fixed feeds/raw4/plan, and one temporary
    # post-close serialization/hash buffer as large as the largest named state.
    transient=max(math.prod(contract.input_shapes[k])*np.dtype(v).itemsize for k,v in STATE_DTYPES.items())
    extra=STEPS*(2*state+fixed+output)+transient+capture.PACKED_BYTES
    total=capture.capture_payload_estimate(STEPS,extra_retained_bytes=extra)
    if total>capture.PAYLOAD_CAP_BYTES: _fail('retention preflight payload cap')
    return dict(state_snapshot_bytes=state,pre_post_state_bytes=2*STEPS*state,
                fixed_and_outputs_bytes=STEPS*(fixed+output),transient_bytes=transient+capture.PACKED_BYTES,
                payload_bytes=total,payload_cap_bytes=capture.PAYLOAD_CAP_BYTES)


class PolicyObserver:
    """Forward the public binding exactly once. No render/session interception."""
    def __init__(self,parent,collector):
        if collector.arm not in ('proxy','retention'): _fail('observer arm')
        self.parent=parent; self.collector=collector; self.rows=[]; self.arrays=[]
        self.reset_calls=0

    def __getattr__(self,name): return getattr(self.parent,name)

    def reset(self):
        if self.reset_calls or self.rows: _fail('episode may reset once')
        self.reset_calls+=1
        return self.parent.reset()

    def _state(self):
        contract=self.parent.contract
        if set(self.parent.state)!=set(contract.state_keys): _fail('named state mapping mismatch')
        return {k:_array(self.parent.state[k],contract.input_shapes[k],self.parent._types[k]) for k in contract.state_keys}

    def step(self,observation):
        if len(self.rows)>=STEPS: _fail('four-step prefix exhausted')
        start=perf_counter(); selected=self.collector.accept_observation(observation)
        row=dict(step=len(self.rows)+1,status='FAILED_OR_INCOMPLETE',graph_calls=None,
                 graph_calls_upper_bound=1,actual_input_sha256=None,policy_inclusive_wall_s=0.,
                 observer_before_wall_s=0.,parent_inclusive_wall_s=0.,observer_after_wall_s=0.,
                 capture_index=selected.capture_index,observation=dict(selected.observation),error=None)
        self.rows.append(row)
        arrays=None
        try:
            if self.collector.arm=='retention':
                state=self._state()
                fixed={'traffic_convention':_array(self.parent.traffic_convention,(1,2),'float32'),
                       'action_t':_array(self.parent.action_t,(1,2),'float32')}
                plan_width=self.parent.contract.output_slices['plan'][1]-self.parent.contract.output_slices['plan'][0]
                # Reserve all retained payload before any copies, including post-state.
                self.collector.reserve_payload(2*sum(v.nbytes for v in state.values())+
                    sum(v.nbytes for v in fixed.values())+8*4+(4+plan_width)*4)
                arrays=dict(pre_state={k:_copy(v) for k,v in state.items()},post_state={},
                    fixed_inputs={k:_copy(v) for k,v in fixed.items()})
                arrays['fixed_inputs']['desire']=_copy(np.zeros((8,),np.float32))
                self.arrays.append(arrays)
            row['observer_before_wall_s']=perf_counter()-start
            parent_start=perf_counter()
            try: action=self.parent.step(observation)
            finally: row['parent_inclusive_wall_s']=perf_counter()-parent_start
            after=perf_counter()
            selected.bind_actual_input(self.parent.last_input_image_sha256)
            row['actual_input_sha256']=selected.actual_input_sha256
            if arrays is not None:
                outputs=self.parent.last_model_outputs
                if type(outputs) is not dict or set(outputs)!= {'action','plan'}: _fail('missing actual parent outputs')
                raw=_array(outputs['action'],(4,),'float32')
                plan=_array(outputs['plan'],(plan_width,),'float32')
                arrays['post_state']={k:_copy(v) for k,v in self._state().items()}
                arrays['raw4']=_copy(raw); arrays['plan']=_copy(plan)
            row.update(status='RETURNED',graph_calls=1,action=asdict(action),
                observer_after_wall_s=perf_counter()-after)
            return action
        except BaseException as exc:
            row['error']=f'{type(exc).__name__}: {exc}'
            raise
        finally: row['policy_inclusive_wall_s']=perf_counter()-start

REPOSITORY = 'rownlvh8875-coder/big-model-closed-loop-benchmark'
ACTIVATION_METADATA = {REQUEST_PATH,'.github/stage7-first-divergence-acceptance.json'}


def _git(*args):
    """Read-only local Git plumbing. Never mutate/fetch repository state."""
    result=subprocess.run(['git',*args],cwd=capture.REPO_ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    if result.returncode: _fail('required local Git blob unavailable')
    return result.stdout


def _github():
    """Authenticated standard-library REST transport; tokens never enter output."""
    import urllib.request
    import urllib.parse
    token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token: _fail('inherited GitHub token required')
    class Redirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            if urllib.parse.urlsplit(newurl).scheme!='https': _fail('non-HTTPS API redirect')
            new=super().redirect_request(req,fp,code,msg,headers,newurl)
            if new is not None and urllib.parse.urlsplit(newurl).netloc!='api.github.com':
                new.remove_header('Authorization')
            return new
    opener=urllib.request.build_opener(Redirect())
    class API:
        def download(self,path,limit):
            if not path.startswith('/repos/'+REPOSITORY+'/'): _fail('unregistered API repository')
            request=urllib.request.Request('https://api.github.com'+path,headers={
                'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
                'X-GitHub-Api-Version':'2022-11-28','User-Agent':'first-divergence-audit'})
            try:
                with opener.open(request,timeout=60) as stream:
                    content_length=stream.headers.get('Content-Length')
                    if content_length is not None and int(content_length)>limit: _fail('API response byte cap')
                    data=stream.read(limit+1)
            except (OSError,ValueError) as exc:
                raise ValueError('GitHub API transport failed') from None
            if len(data)>limit: _fail('API response byte cap')
            return data
        def json(self,path):
            return _json_bytes(self.download(path,capture.MANIFEST_CAP_BYTES))
    return API()


def _json_bytes(data):
    if len(data)>capture.MANIFEST_CAP_BYTES: _fail('JSON byte cap')
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result: _fail('duplicate JSON key')
            result[k]=v
        return result
    try: return json.loads(data,object_pairs_hook=unique,parse_constant=lambda _: _fail('nonfinite JSON'))
    except (UnicodeError,json.JSONDecodeError): raise ValueError('invalid JSON') from None


def _runtime_identity():
    result=capture.runtime_versions()
    for name in ('ImageOS','ImageVersion'):
        value=os.environ.get(name)
        if not value: _fail('missing runner image identity')
        result[name]=value
    return result


def _require_native_runtime(runtime):
    if any(not isinstance(v,str) or not v for v in runtime.values()): _fail('required native/inference runtime distribution unavailable')


def _context(api):
    keys=('GITHUB_REPOSITORY','GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_EVENT_NAME','GITHUB_REF_NAME')
    values={k:os.environ.get(k) for k in keys}
    if os.environ.get('GITHUB_ACTIONS')!='true' or any(not v for v in values.values()): _fail('actual GitHub CI context required')
    if (values['GITHUB_REPOSITORY']!=REPOSITORY or values['GITHUB_EVENT_NAME']!='push' or
        values['GITHUB_REF_NAME']!=BRANCH or values['GITHUB_RUN_ATTEMPT']!='1'): _fail('unregistered run/branch/event/attempt')
    head=values['GITHUB_SHA']
    if len(head)!=40 or any(c not in '0123456789abcdef' for c in head): _fail('invalid actual source head')
    if _git('rev-parse','HEAD').decode().strip()!=head: _fail('actual checkout head mismatch')
    try: run_id=int(values['GITHUB_RUN_ID'])
    except ValueError: _fail('invalid run id')
    if run_id<=0: _fail('invalid run id')
    run=api.json(f'/repos/{REPOSITORY}/actions/runs/{run_id}')
    context=_run_context(run)
    if (context['run_id']!=run_id or context['head_sha']!=head or context['attempt']!=1): _fail('current API run binding mismatch')
    workflow=api.json(f'/repos/{REPOSITORY}/actions/workflows/{context["workflow_id"]}')
    if workflow.get('id')!=context['workflow_id'] or workflow.get('path')!=WORKFLOW_PATH or workflow.get('state')!='active':
        _fail('API workflow identity mismatch')
    return context


def _run_context(run):
    if (type(run) is not dict or run.get('event')!='push' or run.get('head_branch')!=BRANCH or
        run.get('path')!=WORKFLOW_PATH or run.get('repository',{}).get('full_name')!=REPOSITORY or
        type(run.get('id')) is not int or run['id']<=0 or type(run.get('run_attempt')) is not int or
        run['run_attempt']!=1 or type(run.get('workflow_id')) is not int or run['workflow_id']<=0): _fail('API run identity mismatch')
    head=run.get('head_sha')
    if not isinstance(head,str) or len(head)!=40 or any(c not in '0123456789abcdef' for c in head): _fail('API source head')
    return dict(repository=REPOSITORY,workflow_path=WORKFLOW_PATH,workflow_id=run['workflow_id'],
                head_sha=head,run_id=run['id'],attempt=run['run_attempt'],event='push',branch=BRANCH)


def _source_blobs(head,snapshot):
    if snapshot!=capture.source_snapshot(): _fail('current source map mismatch')
    for name,digest in snapshot.items():
        if sha256(_git('show',head+':'+name)).hexdigest()!=digest: _fail('actual commit source blob mismatch: '+name)


def safe_extract(data,out,*,byte_limit=capture.DATASET_CAP_BYTES):
    """Bound both archive and declared decompressed bytes before writing members."""
    out=Path(out)
    if len(data)>capture.PAYLOAD_CAP_BYTES: _fail('archive byte cap')
    capture._safe_path(out,'member')
    if out.exists(): _fail('extraction destination must be fresh')
    try:
        archive=zipfile.ZipFile(io.BytesIO(data))
        members=archive.infolist()
        if not members or len(members)>100 or sum(x.file_size for x in members)>byte_limit: _fail('archive member/byte cap')
        seen=set()
        for member in members:
            path=capture._safe_path(out,member.filename.rstrip('/') if member.is_dir() else member.filename)
            mode=(member.external_attr>>16)&0xffff
            if member.filename in seen or (mode and stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR)) or member.flag_bits&1:
                _fail('unsafe/duplicate/encrypted archive member')
            seen.add(member.filename)
            if member.file_size<0 or member.compress_size<0 or member.file_size>byte_limit: _fail('archive size cap')
        out.mkdir(parents=True)
        for member in members:
            path=capture._safe_path(out,member.filename.rstrip('/') if member.is_dir() else member.filename)
            if member.is_dir(): path.mkdir(parents=True,exist_ok=True); continue
            path.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(member) as stream,path.open('xb') as target:
                left=member.file_size
                while left:
                    block=stream.read(min(left,1024*1024))
                    if not block: _fail('truncated archive member')
                    target.write(block);left-=len(block)
                if stream.read(1): _fail('archive expanded size mismatch')
    except (zipfile.BadZipFile,RuntimeError,OSError) as exc:
        raise ValueError('unsafe or incomplete artifact archive') from exc


def _request(request):
    path=Path(request); capture._safe_path(path.parent,path.name)
    data=capture._read_json(path)
    capture._fields(data,{'schema','mode','acceptance'})
    if data['schema']!=REQUEST_SCHEMA or data['mode'] not in ('capture-canary','model-study'): _fail('unregistered request')
    if data['mode']=='capture-canary' and data['acceptance'] is not None: _fail('canary request cannot activate model')
    return data,path.read_bytes()


def run_canary(out):
    """API/source receipt lives OUTSIDE the strictly registered canary dataset."""
    out=Path(out);capture._require_ephemeral_ci(out)
    request,requestbytes=_request(capture.REPO_ROOT/REQUEST_PATH)
    if request['mode']!='capture-canary': _fail('capture mode required')
    api=_github(); context=_context(api); sources=capture.source_snapshot()
    _source_blobs(context['head_sha'],sources)
    if _git('show',context['head_sha']+':'+REQUEST_PATH)!=requestbytes: _fail('request differs from source commit')
    runtime=_runtime_identity();_require_native_runtime(runtime)
    _json_write(out/'receipt.json',dict(schema=RECEIPT_SCHEMA,context=context,source_snapshot=sources,
        runtime=runtime,installed_binary_equality_proven=False))
    return capture.capture_canary(out/'dataset')


def verify_accepted_canary(request,out):
    """Authenticate one-shot activation and accepted camera artifact BEFORE weights."""
    out=Path(out);capture._require_ephemeral_ci(out)
    config,requestbytes=_request(request)
    if config['mode']!='model-study': _fail('model activation required')
    a=config['acceptance']
    capture._fields(a,{'repository','workflow_id','source_sha','run_id','run_attempt','artifact_id',
        'artifact_name','artifact_nbytes','artifact_sha256','root_raw_accepted','fresh_raw_review_accepted'})
    if (a['repository']!=REPOSITORY or a['artifact_name']!=ARTIFACT_NAME or a['run_attempt']!=1 or
        a['root_raw_accepted'] is not True or a['fresh_raw_review_accepted'] is not True or not capture._is_hash(a['artifact_sha256'])):
        _fail('raw/source acceptance identity missing')
    if any(type(a[k]) is not int or a[k]<=0 for k in ('workflow_id','run_id','run_attempt','artifact_id','artifact_nbytes')):
        _fail('invalid acceptance counters')
    if not 0<a['artifact_nbytes']<=capture.PAYLOAD_CAP_BYTES: _fail('artifact compressed byte cap')
    api=_github();current=_context(api)
    activations=api.json(f'/repos/{REPOSITORY}/actions/workflows/{current["workflow_id"]}/runs?event=push&head_sha={current["head_sha"]}&per_page=100')
    if (type(activations.get('total_count')) is not int or activations['total_count']!=1 or
        type(activations.get('workflow_runs')) is not list or len(activations['workflow_runs'])!=1 or
        _run_context(activations['workflow_runs'][0])!=current):
        _fail('activation commit already has another workflow run')
    if _git('show',current['head_sha']+':'+REQUEST_PATH)!=requestbytes: _fail('request bytes differ from actual current commit')
    run=api.json(f'/repos/{REPOSITORY}/actions/runs/{a["run_id"]}')
    accepted=_run_context(run)
    if (run.get('status')!='completed' or run.get('conclusion')!='success' or accepted['head_sha']!=a['source_sha'] or
        accepted['workflow_id']!=a['workflow_id'] or accepted['workflow_id']!=current['workflow_id'] or accepted['run_id']!=a['run_id']):
        _fail('accepted run was not exact successful canary')
    commit=api.json(f'/repos/{REPOSITORY}/commits/{current["head_sha"]}')
    if (commit.get('sha')!=current['head_sha'] or commit.get('parents')!=[{'sha':a['source_sha']}]):
        # Real GitHub parent objects have extra URL fields.
        parents=commit.get('parents')
        if (commit.get('sha')!=current['head_sha'] or not isinstance(parents,list) or len(parents)!=1 or parents[0].get('sha')!=a['source_sha']):
            _fail('activation must be single direct child of accepted canary')
    if _git('rev-list','--parents','-n','1','HEAD').decode().split()!=[current['head_sha'],a['source_sha']]: _fail('actual activation parent mismatch')
    parent=_json_bytes(_git('show',a['source_sha']+':'+REQUEST_PATH))
    if parent!={'schema':REQUEST_SCHEMA,'mode':'capture-canary','acceptance':None}: _fail('activation parent already requested models')
    files=commit.get('files')
    if type(files) is not list or not files or len(files)>=300: _fail('activation changed-path list missing/truncated')
    changed={r.get('filename') for r in files}
    actual_changed=set(_git('diff-tree','--no-commit-id','--name-only','-r',current['head_sha']).decode().splitlines())
    if changed!=actual_changed or REQUEST_PATH not in changed or any(
        not isinstance(name,str) or (name not in ACTIVATION_METADATA and not name.startswith('docs/')) for name in changed): _fail('activation edited producer/runtime paths')
    if any(r.get('status') not in ('modified','added') or r.get('previous_filename') for r in files): _fail('activation rename/delete prohibited')
    sources=capture.source_snapshot()
    _source_blobs(a['source_sha'],sources);_source_blobs(current['head_sha'],sources)
    runtime=_runtime_identity();_require_native_runtime(runtime)
    artifact=api.json(f'/repos/{REPOSITORY}/actions/artifacts/{a["artifact_id"]}')
    if (artifact.get('id')!=a['artifact_id'] or artifact.get('name')!=ARTIFACT_NAME or artifact.get('expired') is not False or
        artifact.get('size_in_bytes')!=a['artifact_nbytes'] or artifact.get('digest')!='sha256:'+a['artifact_sha256'] or
        artifact.get('workflow_run',{}).get('id')!=a['run_id'] or artifact.get('workflow_run',{}).get('head_sha')!=a['source_sha'] or
        artifact.get('workflow_run',{}).get('head_branch')!=BRANCH): _fail('artifact API identity/size/digest mismatch')
    archive=api.download(f'/repos/{REPOSITORY}/actions/artifacts/{a["artifact_id"]}/zip',a['artifact_nbytes'])
    if len(archive)!=a['artifact_nbytes'] or sha256(archive).hexdigest()!=a['artifact_sha256']: _fail('archive bytes differ from API/request digest')
    safe_extract(archive,out/'accepted-canary')
    extracted=out/'accepted-canary'
    if {p.name for p in extracted.iterdir()}!={'receipt.json','dataset'}: _fail('unregistered artifact root members')
    receipt=capture._read_json(capture._safe_path(extracted,'receipt.json'))
    capture._fields(receipt,{'schema','context','source_snapshot','runtime','installed_binary_equality_proven'})
    if (receipt['schema']!=RECEIPT_SCHEMA or receipt['context']!=accepted or receipt['source_snapshot']!=sources or
        receipt['runtime']!=runtime or receipt['installed_binary_equality_proven'] is not False): _fail('source/run/runtime receipt mismatch')
    capture.validate_capture_dataset(extracted/'dataset')
    manifest=capture._read_json(extracted/'dataset'/'manifest.json')
    # The canary distribution receipt and external source receipt must agree.
    metadata=manifest['metadata']
    if metadata.get('runtime_versions')!={k:v for k,v in runtime.items() if k not in ('ImageOS','ImageVersion')}: _fail('missing/mismatched canary runtime')
    if type(metadata.get('process_id')) is not int or metadata['process_id']<=0 or type(metadata.get('process_uuid')) is not str or len(metadata['process_uuid'])!=32:
        _fail('missing canary process identity')
    if metadata.get('source_binding')!='CHECKOUT_BYTES_ONLY_GITHUB_API_BINDING_REQUIRED_BY_TASK2': _fail('missing canary source binding')
    result=dict(schema=GATE_SCHEMA,status='CANARY_ACCEPTED_FOR_BOUNDED_STUDY',
        current_context=current,accepted_context=accepted,source_snapshot=sources,runtime=runtime,
        request_sha256=sha256(requestbytes).hexdigest(),acceptance=a,protocol=PROTOCOL,
        installed_binary_equality_proven=False,original_strict_pass=False)
    _json_write(out/'acceptance.json',result)
    return result


def _require_official_model(model,spec):
    capture._require_ephemeral_ci(Path(model))
    from .public_action_frame import preflight_public_onnx_policy
    resolution=preflight_public_onnx_policy(Path(model),Path(spec),model_action_frame='auto')
    identity=resolution.identity
    if (identity.model_sha256,identity.model_nbytes,identity.spec_sha256)!=(MODEL_SHA,MODEL_BYTES,SPEC_SHA): _fail('exact official MD-V3 triplet required')
    return resolution


def _require_model_acceptance():
    """Re-authenticate receipt at the executable boundary, before session creation.

    An editable JSON receipt alone is insufficient authorization. Re-run the API,
    commit, source, archive, protocol and runtime gate and compare its result.
    """
    receiptpath=os.environ.get('FIRST_DIVERGENCE_ACCEPTANCE')
    if not receiptpath: _fail('validated current acceptance receipt required')
    receiptpath=Path(receiptpath);capture._require_ephemeral_ci(receiptpath)
    receipt=capture._read_json(capture._safe_path(receiptpath.parent,receiptpath.name))
    runner_temp=Path(os.environ['RUNNER_TEMP'])
    with tempfile.TemporaryDirectory(prefix='first-divergence-recheck-',dir=runner_temp) as temp:
        actual=verify_accepted_canary(capture.REPO_ROOT/REQUEST_PATH,Path(temp)/'gate')
    if receipt!=actual: _fail('acceptance receipt altered or bound to different current source/run/request')
    return actual


def _consume_trial_authorization(arm,repeat,nonce):
    """One-use inherited pipe capability from the currently live study parent."""
    if arm not in capture.ARMS or type(repeat) is not int or repeat not in (0,1) or not capture._is_hash(nonce): _fail('trial arm/repeat/nonce')
    fdtext=os.environ.pop('FIRST_DIVERGENCE_TRIAL_FD',None)
    if not fdtext or not fdtext.isdecimal(): _fail('study parent pipe authorization required')
    fd=int(fdtext)
    try:
        if not stat.S_ISFIFO(os.fstat(fd).st_mode): _fail('trial authorization is not inherited pipe')
        with os.fdopen(fd,'rb') as stream: data=stream.read(capture.MANIFEST_CAP_BYTES+1)
    except OSError: raise ValueError('missing one-use trial capability') from None
    permit=_json_bytes(data)
    capture._fields(permit,{'parent_pid','parent_uuid','process_group','nonce','arm','repeat','source_snapshot','runtime','schedule_index','storage_limits'})
    if (permit['arm'],permit['repeat'],permit['nonce'])!=(arm,repeat,nonce): _fail('trial capability association mismatch')
    _storage_limits(permit['storage_limits'])
    index=permit['schedule_index']
    if type(index) is not int or not 0<=index<len(SCHEDULE) or SCHEDULE[index]!=(arm,repeat): _fail('unauthorized trial schedule')
    if type(permit['parent_pid']) is not int or permit['parent_pid']<=0 or permit['parent_pid']==os.getpid(): _fail('trial parent identity')
    if type(permit['parent_uuid']) is not str or len(permit['parent_uuid'])!=32 or any(c not in '0123456789abcdef' for c in permit['parent_uuid']): _fail('trial parent UUID')
    if permit['process_group']!=os.getpgid(0): _fail('fresh child process group mismatch')
    try: os.kill(permit['parent_pid'],0)
    except OSError: raise ValueError('study parent is no longer live') from None
    if permit['source_snapshot']!=capture.source_snapshot() or permit['runtime']!=_runtime_identity(): _fail('child source/runtime drift')
    # The receipt is re-authenticated by the parent; child verifies current bytes
    # and actual environment binding without creating another acceptance session.
    path=os.environ.get('FIRST_DIVERGENCE_ACCEPTANCE')
    if not path: _fail('child requires study acceptance receipt')
    receipt=capture._read_json(Path(path))
    _receipt_current_binding(receipt)
    return permit


def _receipt_current_binding(receipt):
    capture._fields(receipt,{'schema','status','current_context','accepted_context','source_snapshot','runtime',
        'request_sha256','acceptance','protocol','installed_binary_equality_proven','original_strict_pass'})
    context_keys={'repository','workflow_path','workflow_id','head_sha','run_id','attempt','event','branch'}
    for key in ('current_context','accepted_context'):capture._fields(receipt[key],context_keys)
    config,requestbytes=_request(capture.REPO_ROOT/REQUEST_PATH)
    if (receipt['schema']!=GATE_SCHEMA or receipt['status']!='CANARY_ACCEPTED_FOR_BOUNDED_STUDY' or
        receipt['installed_binary_equality_proven'] is not False or receipt['original_strict_pass'] is not False or
        receipt['source_snapshot']!=capture.source_snapshot() or receipt['runtime']!=_runtime_identity() or
        not capture._exact(receipt['protocol'],PROTOCOL) or receipt['request_sha256']!=sha256(requestbytes).hexdigest() or
        config['mode']!='model-study' or config['acceptance']!=receipt['acceptance']):
        _fail('receipt source/runtime/request/protocol/claims mismatch')
    context=receipt['current_context'];accepted=receipt['accepted_context'];a=receipt['acceptance']
    expected=dict(repository=os.environ.get('GITHUB_REPOSITORY'),head_sha=os.environ.get('GITHUB_SHA'),
        run_id=int(os.environ.get('GITHUB_RUN_ID','0')),attempt=int(os.environ.get('GITHUB_RUN_ATTEMPT','0')),
        event=os.environ.get('GITHUB_EVENT_NAME'),branch=os.environ.get('GITHUB_REF_NAME'))
    if (any(context.get(k)!=v for k,v in expected.items()) or context['workflow_path']!=WORKFLOW_PATH or
        expected['attempt']!=1 or expected['repository']!=REPOSITORY or expected['event']!='push' or expected['branch']!=BRANCH):
        _fail('receipt current actual run mismatch')
    if (accepted!={**context,'head_sha':a['source_sha'],'run_id':a['run_id'],'attempt':a['run_attempt']} or
        context['workflow_id']!=a['workflow_id'] or a['root_raw_accepted'] is not True or a['fresh_raw_review_accepted'] is not True):
        _fail('receipt accepted source/run binding mismatch')
    if _git('rev-parse','HEAD').decode().strip()!=expected['head_sha']: _fail('child actual source head mismatch')


def _save_array(root,name,value,*,write_budget=None):
    path=capture._safe_path(root,name)
    if write_budget is not None:write_budget.reserve(value.nbytes+4096)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream: np.save(stream,value,allow_pickle=False)
    return dict(path=name,nbytes=path.stat().st_size,sha256=_hash_file(path),array=_descriptor(value))


def _serialize_arrays(root,rows,write_budget=None):
    result=[]
    for index,row in enumerate(rows,1):
        saved={}
        for group in ('pre_state','post_state','fixed_inputs'):
            saved[group]={name:_save_array(root,f'step_{index:02d}/{group}_{name}.npy',value,write_budget=write_budget) for name,value in row.get(group,{}).items()}
        for name in ('raw4','plan'):
            if name in row: saved[name]=_save_array(root,f'step_{index:02d}/{name}.npy',row[name],write_budget=write_budget)
        result.append(saved)
    return result


def _exception_record(exc):
    """Keep the complete chain; identify only the frozen owner's known close site."""
    import traceback
    chain=[];current=exc;seen=set()
    while current is not None and id(current) not in seen:
        seen.add(id(current));chain.append(f'{type(current).__name__}: {current}')
        current=current.__cause__ if current.__cause__ is not None else current.__context__
    close_override=exc.__context__ is not None and any(
        entry.filename.endswith('/bigbench/native_model_campaign.py') and entry.line and entry.line.strip()=='provider.close()'
        for entry in traceback.extract_tb(exc.__traceback__))
    if close_override:return chain[1],chain,[chain[0]]
    return chain[0],chain,[]


def run_trial(model,spec,arm,repeat,nonce,out):
    """One authorized fresh-process four-step prefix. Native owner closes provider."""
    permit=_consume_trial_authorization(arm,repeat,nonce)
    out=Path(out);capture._require_ephemeral_ci(out)
    limits=_storage_limits(permit.get('storage_limits') or _child_storage_limits(capture.DATASET_CAP_BYTES-_ledger_reserve(capture.DATASET_CAP_BYTES)))
    disk=_StorageBudget(limits['payload_limit_bytes'])
    budget=retention_preflight(spec)  # before native provider or ORT session
    _require_official_model(model,spec)
    from .public_action_frame import create_public_onnx_policy
    from .native_model_campaign import CampaignSpec,run_native_episode
    sources=capture.source_snapshot();runtime=_runtime_identity()
    collector=capture.CaptureCollector(arm,max_captures=24)
    # Reserve the largest serialization/hash transient before retaining anything.
    if arm=='retention': collector.reserve_payload(budget['transient_bytes'])
    binding=observer=None; report=None;error=None;error_chain=[];cleanup_errors=[];closed=False
    try:
        binding=create_public_onnx_policy(Path(model),Path(spec),model_action_frame='auto')
        policy=binding.policy
        if arm!='original': observer=PolicyObserver(policy,collector);policy=observer
        with capture.capture_scope(arm,collector):
            report=run_native_episode(policy,CampaignSpec('s_curve_left_right',seed=20261109,steps=4,
                speed_mps=8.,dt_s=.05,initial_fraction=.12),full_s_route=False,
                camera_convergence=6,camera_pixel_tolerance=16,camera_rgb_delta=10)
        # Successful return attests the frozen owner's finally-close returned,
        # even if report itself describes an incomplete prefix.
        closed=True;collector.mark_closed()
    except BaseException as exc:
        error,error_chain,cleanup_errors=_exception_record(exc)
    if error is None and (not isinstance(report,dict) or report.get('status')!='DIAGNOSTIC_EXECUTED'):
        error=(report.get('error') if isinstance(report,dict) else None) or 'incomplete native report'
        error_chain=[error]
    data=dict(schema=TRIAL_SCHEMA,status='FAILED_OR_INCOMPLETE',protocol=PROTOCOL,arm=arm,repeat=repeat,
        nonce=nonce,process_id=os.getpid(),process_uuid=uuid.uuid4().hex,
        parent_pid=permit['parent_pid'],parent_uuid=permit['parent_uuid'],process_group=os.getpgid(0),
        source_snapshot=sources,runtime=runtime,provider_closed=closed,error=error,error_chain=error_chain,cleanup_errors=cleanup_errors,
        storage=dict(limits=limits,payload_charged_bytes=0,limit_error=None),preflight=budget,binding=binding.receipt() if binding else None,report=report,observed=None,
        model_calls=None,model_calls_lower_bound=len(binding.policy.trace) if binding else 0,
        model_calls_upper_bound=4,claims=dict(capture.CLAIMS),limitation=LIMITATION)
    if observer is not None:
        data['observed']=dict(reset_calls=observer.reset_calls,steps=observer.rows,capture_count=collector.capture_count,
            capture_rows=collector.capture_rows,retained_payload_bytes=collector.payload_bytes,captures=[],arrays=[],
            actual_image_scope='ACTUAL_PARENT_NEW_IMG_SHA_ONLY',other_feed_scope='SOURCE_RECONSTRUCTED_NOT_INTERCEPTED')
        if closed and arm=='retention':
            try:
                data['observed']['captures']=collector.serialize_captures(out,write_budget=disk)
                data['observed']['arrays']=_serialize_arrays(out,observer.arrays,write_budget=disk)
            except BaseException as exc:
                detail=f'{type(exc).__name__}: {exc}'
                if 'budget' in str(exc):data['storage']['limit_error']=detail
                if data['error'] is None:
                    data['error']=detail;data['error_chain']=[detail]
                else:cleanup_errors.append(detail)
    data['storage']['payload_charged_bytes']=disk.charged
    if data['error'] is None and report is not None and report.get('status')=='DIAGNOSTIC_EXECUTED' and not cleanup_errors:
        data['status']='TRIAL_ASSOCIATION_VALIDATED';data['model_calls']=4
        try: _validate_trial(out,manifest=data)
        except BaseException as exc:
            data['status']='FAILED_OR_INCOMPLETE';data['model_calls']=None
            data['error']=f'{type(exc).__name__}: {exc}';data['error_chain']=[data['error']]
    elif data['error'] is None:
        data['error']=report.get('error','incomplete native report') if isinstance(report,dict) else 'no complete native report'
    if _dataset_bytes(out)+limits['trial_ledger_limit_bytes']>sum(limits.values()):_fail('trial exceeded its reserved storage allocation')
    return _publish_ledger(out/'trial.json',data,limits['trial_ledger_limit_bytes'])


def _enable_subreaper():
    # Reparent orphaned Xvfb/helper grandchildren here so timeout cleanup can
    # reap the full process group rather than merely killing its shell leader.
    import ctypes
    if not sys.platform.startswith('linux') or ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0)!=0:
        _fail('Linux child-subreaper required for complete group cleanup')


def _launch_trial(model,spec,out,arm,repeat,nonce,parent_uuid,index,launch_row):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    readfd,writefd=os.pipe();process=None
    limits={k:v for k,v in launch_row.get('storage',_child_storage_limits(capture.DATASET_CAP_BYTES-_ledger_reserve(capture.DATASET_CAP_BYTES))).items() if k in ('payload_limit_bytes','trial_ledger_limit_bytes','log_limit_bytes')}
    _storage_limits(limits)
    storage=launch_row.setdefault('storage',dict(limits,log_bytes=0,limit_error=None))
    try:
        env=dict(os.environ,FIRST_DIVERGENCE_TRIAL_FD=str(readfd))
        command=['xvfb-run','-a',sys.executable,'-m','scripts.first_divergence_audit','native-trial',
            '--model',str(Path(model).resolve()),'--spec',str(Path(spec).resolve()),'--out',str(out),
            '--arm',arm,'--repeat',str(repeat),'--nonce',nonce]
        process=subprocess.Popen(command,cwd=capture.REPO_ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            start_new_session=True,pass_fds=(readfd,))
        launch_row.update(launched=True,launcher_pid=process.pid,process_group=process.pid)
        os.close(readfd);readfd=None
        permit=dict(parent_pid=os.getpid(),parent_uuid=parent_uuid,process_group=process.pid,
            nonce=nonce,arm=arm,repeat=repeat,schedule_index=index,
            source_snapshot=capture.source_snapshot(),runtime=_runtime_identity(),storage_limits=limits)
        with os.fdopen(writefd,'wb') as stream: stream.write(json.dumps(permit,allow_nan=False).encode())
        writefd=None
        return _BoundedChild(process,_LogSink(out/'process.log',limits['log_limit_bytes']),storage)
    except BaseException:
        if process is not None:
            launch_row['cleanup_errors']=_terminate_group(process)
            launch_row['exit_code']=process.returncode
            if getattr(process,'stdout',None) is not None:process.stdout.close()
        raise
    finally:
        for fd in (readfd,writefd):
            if fd is not None:
                try:os.close(fd)
                except OSError:pass


def _terminate_group(process):
    errors=[]
    for sig in (signal.SIGTERM,signal.SIGKILL):
        try: os.killpg(process.pid,sig)
        except ProcessLookupError: pass
        except OSError as exc: errors.append(f'group signal {sig}: {type(exc).__name__}: {exc}')
        if sig==signal.SIGTERM:
            try:process.wait(timeout=2.)
            except subprocess.TimeoutExpired:pass
            except OSError as exc:errors.append(f'leader reap: {exc}')
    try:process.wait(timeout=2.)
    except (OSError,subprocess.TimeoutExpired) as exc:errors.append(f'final leader reap: {exc}')
    # With subreaper enabled these are our actual adopted group children.
    deadline=perf_counter()+2.
    while True:
        try: pid,status=os.waitpid(-process.pid,os.WNOHANG)
        except ChildProcessError:break
        except OSError as exc:errors.append(f'group reap: {exc}');break
        if pid:continue
        if perf_counter()>=deadline:errors.append('group descendants not reaped before cleanup deadline');break
        # A short bounded scheduling yield, never a study retry.
        import time
        time.sleep(.01)
    return errors


def _dataset_bytes(root):
    total=0
    for p in Path(root).rglob('*'):
        if p.is_symlink() or not (p.is_dir() or p.is_file()): _fail('unsafe study member')
        if p.is_file():total+=p.stat().st_size
        if total>capture.DATASET_CAP_BYTES: _fail('study dataset cap')
    return total


def run_study(model,spec,out):
    start=perf_counter()
    receipt=_require_model_acceptance()
    retention_preflight(spec);_require_official_model(model,spec)
    out=Path(out);capture._require_ephemeral_ci(out);capture._safe_path(out,'study.json')
    if out.exists(): _fail('study output must be fresh; no retry/extension')
    ledger_limit=_ledger_reserve(capture.DATASET_CAP_BYTES)
    out.mkdir(parents=True);_enable_subreaper()
    parent_uuid=uuid.uuid4().hex;ledger=[];trials=[];error=None;cleanup=[]
    for index,(arm,repeat) in enumerate(SCHEDULE):
        remaining=STUDY_LIMIT_S-(perf_counter()-start)
        if remaining<=0:error='whole-study deadline exhausted';break
        try:limits=_child_storage_limits(capture.DATASET_CAP_BYTES-ledger_limit-_dataset_bytes(out))
        except ValueError as exc:error=str(exc);break
        nonce=secrets.token_hex(32);childout=out/f'trial_{index:02d}'
        row=dict(schedule_index=index,arm=arm,repeat=repeat,nonce=nonce,launched=False,
            launcher_pid=None,process_group=None,launch_elapsed_s=perf_counter()-start,
            exit_elapsed_s=None,exit_code=None,timed_out=False,child_pid=None,child_uuid=None,
            validation_error=None,cleanup_errors=[],storage=dict(limits,log_bytes=0,limit_error=None))
        ledger.append(row);process=None
        try:
            process=_launch_trial(model,spec,childout,arm,repeat,nonce,parent_uuid,index,row)
            row.update(launched=True,launcher_pid=process.pid,process_group=process.pid)
            try:
                timeout=min(float(CHILD_LIMIT_S),max(0.,STUDY_LIMIT_S-(perf_counter()-start)))
                if timeout<=0:raise subprocess.TimeoutExpired('whole-study',0)
                row['exit_code']=process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                row['timed_out']=True
                raise ValueError('child/study deadline exceeded') from None
            if row['exit_code']!=0: _fail('child process returned nonzero exit')
            trial=_validate_trial(childout,expected=dict(arm=arm,repeat=repeat,nonce=nonce,
                parent_pid=os.getpid(),parent_uuid=parent_uuid,process_group=process.pid))
            row['child_pid']=trial['process_id'];row['child_uuid']=trial['process_uuid']
            if any(t['process_id']==trial['process_id'] or t['process_uuid']==trial['process_uuid'] for t in trials): _fail('child process identity reused')
            trials.append(trial)
            _dataset_bytes(out)
        except BaseException as exc:
            error=f'{type(exc).__name__}: {exc}';row['validation_error']=error
        finally:
            if process is not None:
                output_errors=[]
                if isinstance(process,_BoundedChild):
                    process.close_output();output_errors=process.output_cleanup_errors
                row['cleanup_errors']=output_errors+_terminate_group(process)
                row['exit_code']=process.returncode
                cleanup.extend(row['cleanup_errors'])
                if row['cleanup_errors'] and error is None:error='child group cleanup unconfirmed'
            if process is None and row['cleanup_errors']:
                cleanup.extend(row['cleanup_errors'])
            try:
                if _dataset_bytes(out)>capture.DATASET_CAP_BYTES-ledger_limit:_fail('dataset budget consumed reserved study ledger')
            except ValueError as exc:
                row['storage']['limit_error']=str(exc)
                if error is None:error=str(exc)
            row['exit_elapsed_s']=perf_counter()-start
        if error is not None:break
    complete=len(trials)==6 and error is None and perf_counter()-start<=STUDY_LIMIT_S
    result=dict(schema=STUDY_SCHEMA,status='STUDY_ASSOCIATION_VALIDATED' if complete else 'FAILED_OR_INCOMPLETE',
        protocol=PROTOCOL,source_snapshot=capture.source_snapshot(),runtime=_runtime_identity(),
        parent_pid=os.getpid(),parent_uuid=parent_uuid,acceptance=receipt,
        launch_ledger=ledger,error=error,cleanup_errors=cleanup,storage=dict(dataset_cap_bytes=capture.DATASET_CAP_BYTES,ledger_limit_bytes=ledger_limit),elapsed_wall_s=perf_counter()-start,
        model_calls=24 if complete else None,model_calls_lower_bound=4*len(trials),
        model_calls_upper_bound=4*sum(r['launched'] for r in ledger),
        claims=dict(capture.CLAIMS),limitation=LIMITATION,
        comparisons=_comparisons(trials) if complete else [])
    if complete:
        try:_validate_study(out,manifest=result)
        except BaseException as exc:
            result.update(status='FAILED_OR_INCOMPLETE',model_calls=None,error=f'{type(exc).__name__}: {exc}')
    if _dataset_bytes(out)+ledger_limit>capture.DATASET_CAP_BYTES:_fail('unmanaged output exceeded reserved dataset storage; evidence preserved')
    return _publish_ledger(out/'study.json',result,ledger_limit)


def _file_member(root,desc,registered,*,limit=32*1024*1024):
    if type(desc) is not dict or type(desc.get('nbytes')) is not int or not 0<desc['nbytes']<=limit or not capture._is_hash(desc.get('sha256')):
        _fail('invalid bounded member descriptor')
    name=desc.get('path');path=capture._safe_path(root,name)
    if name in registered or not path.is_file() or path.stat().st_size!=desc['nbytes']: _fail('duplicate/missing/member byte mismatch')
    registered.add(name)
    if _hash_file(path)!=desc['sha256']: _fail('member SHA mismatch')
    return path


def _load_array(root,desc,shape,dtype,registered=None):
    capture._fields(desc,{'path','nbytes','sha256','array'})
    capture._fields(desc['array'],{'shape','dtype','nbytes','sha256'})
    a=desc['array'];dtype=np.dtype(dtype);size=math.prod(shape)*dtype.itemsize
    if size>16*1024*1024 or a['shape']!=list(shape) or a['dtype']!=dtype.name or type(a['nbytes']) is not int or a['nbytes']!=size or not capture._is_hash(a['sha256']): _fail('declared array layout mismatch')
    path=_file_member(root,desc,registered if registered is not None else set(),limit=size+4096)
    try:
        with path.open('rb') as stream:
            version=np.lib.format.read_magic(stream)
            if version==(1,0): layout=np.lib.format.read_array_header_1_0(stream,max_header_size=4096)
            elif version==(2,0): layout=np.lib.format.read_array_header_2_0(stream,max_header_size=4096)
            else:_fail('unsupported NPY version')
            actual_shape,fortran,actual_dtype=layout
            if actual_shape!=tuple(shape) or actual_dtype!=dtype or actual_dtype.hasobject or fortran or stream.tell()+size!=desc['nbytes']:
                _fail('NPY header/payload contract mismatch')
        value=np.load(path,allow_pickle=False,max_header_size=4096)
    except (OSError,EOFError,TypeError) as exc:raise ValueError('invalid typed NPY') from exc
    _array(value,shape,dtype)
    if _descriptor(value)!=a: _fail('decoded array SHA mismatch')
    return value


def _validate_binding_report(data):
    b=data['binding'];report=data['report']
    capture._fields(b,{'protocol','identity','requested_frame','parent_action_frame','applied_action_frame','provenance',
        'rotation_applied','parent_trace','parent_trace_count','bridge_receipts','bridge_receipt_count',
        'total_executed_model_calls','execution_count_scope','episode_completion_inferred','parent_trace_values_rewritten',
        'raw_outputs_rewritten','renderer_selected','source_basis_verified'})
    if (b['protocol']!='public-onnx-action-frame-v1' or b['requested_frame']!='auto' or b['parent_action_frame']!='MODEL_BODY_FRD' or
        b['applied_action_frame']!='INTEGRATOR_BODY_FLU_WORLD_CCW' or b['provenance']!='VERIFIED_OFFICIAL_IDENTITY' or
        b['rotation_applied'] is not True or b['source_basis_verified'] is not True or
        any(b[k] is not False for k in ('episode_completion_inferred','parent_trace_values_rewritten','raw_outputs_rewritten','renderer_selected')) or
        b['total_executed_model_calls'] is not None or b['execution_count_scope']!='committed parent trace and completed bridges only; total execution unknown'):
        _fail('public auto FRD binding changed')
    identity=b['identity'];capture._fields(identity,{'model_path','spec_path','model_sha256','model_nbytes','spec_sha256'})
    if identity['model_sha256']!=MODEL_SHA or type(identity['model_nbytes']) is not int or identity['model_nbytes']!=MODEL_BYTES or identity['spec_sha256']!=SPEC_SHA:
        _fail('official identity mismatch')
    if any(type(identity[k]) is not str or not identity[k] for k in ('model_path','spec_path')): _fail('missing model/spec identity paths')
    if (type(report) is not dict or report.get('status')!='DIAGNOSTIC_EXECUTED' or report.get('error') is not None or
        report.get('scenario')!='s_curve_left_right' or type(report.get('seed')) is not int or report['seed']!=20261109 or
        any(type(report.get(k)) is not int or report[k]!=4 for k in ('requested_steps','completed_steps')) or
        report.get('model_sha256')!=MODEL_SHA or report.get('full_s_route_requested') is not False or
        report.get('model_scoring_allowed') is not False or report.get('real_vehicle_testing') is not False): _fail('failed/incomplete/changed native report')
    convergence=report.get('strict_same_pose_convergence',{})
    fixed=dict(enabled=True,max_captures=6,sample_count=4,failed_samples=0,pixel_tolerance_count=16,pixel_channel_delta_tolerance=10)
    if any(not capture._exact(convergence.get(k),v) for k,v in fixed.items()): _fail('native convergence contract mismatch')
    for count in ('parent_trace_count','bridge_receipt_count'):
        if type(b[count]) is not int or b[count]!=4:_fail('binding committed counts incomplete')
    frames=report.get('frames');trace=b['parent_trace'];bridges=b['bridge_receipts']
    if any(type(x) is not list or len(x)!=4 for x in (frames,trace,bridges)): _fail('four complete associated rows required')
    from .model_world_frame import basis_receipt
    for i,(frame,parent,bridge) in enumerate(zip(frames,trace,bridges),1):
        capture._fields(parent,{'step_index','elapsed_ms','raw_lateral_accel_mps2','raw_longitudinal_accel_mps2','curvature_1pm','image_checksum'})
        capture._fields(bridge,{'step','source_action_frame','applied_action_frame','body_rotation','raw_outputs_rewritten',
            'parent_model_action','applied_world_action','bridge_audit_wall_s'})
        if type(frame.get('step')) is not int or frame['step']!=i or type(parent['step_index']) is not int or parent['step_index']!=i-1 or type(bridge['step']) is not int or bridge['step']!=i:_fail('step association mismatch')
        if any(bridge[k]!=v for k,v in basis_receipt().items()):_fail('body rotation receipt mismatch')
        if any(not capture._number(parent[k]) for k in ('elapsed_ms','raw_lateral_accel_mps2','raw_longitudinal_accel_mps2','curvature_1pm')) or parent['elapsed_ms']<0:
            _fail('graph-only parent trace must be finite')
        if not capture._number(bridge['bridge_audit_wall_s']) or bridge['bridge_audit_wall_s']<0:_fail('bridge wall time')
        if type(parent['image_checksum']) is not int or not 0<=parent['image_checksum']<2**32:_fail('parent checksum')
        expected_parent=dict(curvature_1pm=parent['raw_lateral_accel_mps2']/64.,acceleration_mps2=parent['raw_longitudinal_accel_mps2'])
        expected_applied=dict(curvature_1pm=-expected_parent['curvature_1pm'],acceleration_mps2=expected_parent['acceleration_mps2'])
        if parent['curvature_1pm']!=expected_parent['curvature_1pm'] or bridge['parent_model_action']!=expected_parent or bridge['applied_world_action']!=expected_applied:
            _fail('raw parent/world action association mismatch')
        if frame.get('desired_curvature_1pm')!=expected_applied['curvature_1pm'] or frame.get('desired_acceleration_mps2')!=expected_applied['acceleration_mps2']:
            _fail('native report applied another action')
        if not capture._number(frame.get('time_s')) or not math.isclose(frame['time_s'],i*.05,abs_tol=1e-12) or frame.get('speed_mps')!=8.:
            _fail('report fixed clock/speed mismatch')
        if any(not capture._number(frame.get(k)) for k in ('world_x_m','world_y_m','heading_rad')):_fail('nonfinite report pose')
        if any(not capture._is_hash(frame.get(k)) for k in ('road_frame_sha256','wide_frame_sha256')):_fail('missing actual canvas hashes')
        if frame['road_frame_sha256']==frame['wide_frame_sha256']:_fail('duplicated camera frames')
        # Preserve the frozen convergence wrapper's generic null source fields.
        if any(k not in frame or frame[k] is not None for k in ('source_road_rgb_sha256','source_wide_rgb_sha256')):_fail('generic report source fields rewritten')


def _validate_capture_rows(observed,frames,steps):
    rows=observed['capture_rows'];count=observed['capture_count']
    if type(count) is not int or not 8<=count<=24 or type(rows) is not list or len(rows)!=count:_fail('bounded complete capture attempts required')
    selected=[];previous=0
    from .kinematics import AgentState,ModelAction,step_ideal
    previous_state=None
    for i,step in enumerate(steps):
        index=step['capture_index']
        if type(index) is not int or not previous+2<=index<=min(previous+6,count):_fail('selected capture ordering/convergence bound')
        group=rows[previous:index];pose=group[0].get('pose')
        capture._fields(pose,{'t','x','y','heading','speed'})
        if any(not capture._number(v) for v in pose.values()):_fail('capture finite pose required')
        state=AgentState(**pose)
        if not math.isclose(state.t,i*.05,abs_tol=1e-12) or state.speed!=8.:_fail('capture observation clock/speed')
        if previous_state is not None:
            expected=step_ideal(previous_state,ModelAction(frames[i-1]['desired_curvature_1pm'],frames[i-1]['desired_acceleration_mps2']),.05,speed_override=8.)
            if state!=expected:_fail('capture feedback pose chain mismatch')
        after=step_ideal(state,ModelAction(frames[i]['desired_curvature_1pm'],frames[i]['desired_acceleration_mps2']),.05,speed_override=8.)
        if any(frames[i][key]!=value for key,value in (('world_x_m',after.x),('world_y_m',after.y),('heading_rad',after.heading))):_fail('capture pose/report transition mismatch')
        for ordinal,row in enumerate(group,previous+1):
            capture._fields(row,{'capture_index','status','pose','raw_sha256','canvas_sha256','capture_wrapper_wall_s',
                'capture_inclusive_wall_s','wrapper_observer_arithmetic_wall_s','raw_callback_nested_wall_s'}, {'accept_observation_wall_s'})
            if type(row['capture_index']) is not int or row['capture_index']!=ordinal or row['status']!='RETURNED' or row['pose']!=pose:_fail('capture attempt order/pose/status')
            capture._hash_pair(row['raw_sha256']);capture._hash_pair(row['canvas_sha256'])
            inclusive,nested,wrapper,arithmetic=(row[k] for k in ('capture_inclusive_wall_s','raw_callback_nested_wall_s','capture_wrapper_wall_s','wrapper_observer_arithmetic_wall_s'))
            if any(not capture._number(x) or x<0 for x in (inclusive,nested,wrapper,arithmetic)) or not nested<=inclusive<=wrapper or not math.isclose(wrapper-inclusive,arithmetic,rel_tol=1e-9,abs_tol=1e-12):_fail('capture nested wall timing mismatch')
            if ('accept_observation_wall_s' in row)!=(ordinal==index):_fail('acceptance timing association')
            if ordinal==index and (not capture._number(row['accept_observation_wall_s']) or row['accept_observation_wall_s']<0):_fail('invalid acceptance wall timing')
        last=rows[index-1]
        if last['canvas_sha256']!={'road':frames[i]['road_frame_sha256'],'wide':frames[i]['wide_frame_sha256']}:_fail('selected capture/report frame hashes mismatch')
        selected.append(last);previous=index;previous_state=state
    if previous!=count:_fail('trailing unselected captures')
    return selected


def _validate_retention(root,observed,frames,steps,selected,registered,binding):
    from .optical_calibration import PinholeIntrinsics,PinholeRectifier
    from .image_adapter import camera_pair_to_model
    captures=observed['captures'];arrays=observed['arrays']
    if type(captures) is not list or len(captures)!=4 or type(arrays) is not list or len(arrays)!=4:_fail('four retained capture/state associations required')
    previous_post=None;decoded_total=0
    from .onnx_contract import ModelContract
    contract=ModelContract.load(capture.REPO_ROOT/'model_specs/md-v3.json')
    for i,(row,state_row,step,attempt,frame) in enumerate(zip(captures,arrays,steps,selected,frames),1):
        capture._fields(row,{'accepted_index','capture_index','observation','intrinsics','raw','canvas','packed'})
        if type(row['accepted_index']) is not int or row['accepted_index']!=i or row['capture_index']!=step['capture_index'] or row['observation']!=step['observation']:_fail('retained capture/step association')
        raw={};canvas={};lenses={}
        for group in ('raw','canvas','intrinsics'):capture._fields(row[group],{'road','wide'})
        for kind in ('road','wide'):
            lens=row['intrinsics'][kind];capture._fields(lens,{'width','height','fx','fy','cx','cy'})
            if type(lens['width']) is not int or type(lens['height']) is not int or any(not capture._number(lens[k]) for k in ('fx','fy','cx','cy')):_fail('invalid lens descriptor')
            lenses[kind]=PinholeIntrinsics(**lens)
            for group,width,height,target in (('raw',964,604,raw),('canvas',512,256,canvas)):
                desc=row[group][kind];capture._fields(desc,{'path','nbytes','sha256','rgb_sha256'})
                if not capture._is_hash(desc['rgb_sha256']):_fail('missing decoded RGB SHA')
                image=capture._read_png(_file_member(root,desc,registered,limit=8*1024*1024),width,height)
                if image.sha256!=desc['rgb_sha256']:_fail('decoded RGB SHA mismatch')
                target[kind]=image
                decoded_total+=width*height*3
        if {k:raw[k].sha256 for k in raw}!=attempt['raw_sha256'] or {k:canvas[k].sha256 for k in canvas}!=attempt['canvas_sha256']:_fail('retained raw/canvas/selected attempt mismatch')
        pair,_=PinholeRectifier().rectify_pair(np.frombuffer(raw['road'].rgb,np.uint8).reshape(capture.RAW_SHAPE),
            np.frombuffer(raw['wide'].rgb,np.uint8).reshape(capture.RAW_SHAPE),road_intrinsics=lenses['road'],wide_intrinsics=lenses['wide'])
        if pair.road.rgb!=canvas['road'].rgb or pair.wide.rgb!=canvas['wide'].rgb:_fail('raw/lens warp differs from accepted canvas')
        packed=row['packed'];capture._fields(packed,{'path','nbytes','sha256','actual_input_sha256','association'})
        if packed['association']!='ACTUAL_INPUT_SHA_EQUIVALENT' or packed['actual_input_sha256']!=step['actual_input_sha256'] or packed['sha256']!=step['actual_input_sha256'] or packed['nbytes']!=capture.PACKED_BYTES:_fail('actual graph new_img SHA mismatch')
        actual=camera_pair_to_model(canvas['road'],canvas['wide'])
        if _file_member(root,packed,registered,limit=capture.PACKED_BYTES).read_bytes()!=actual.tobytes():_fail('packed I420 differs from derived actual accepted pair')
        if int(np.sum(actual,dtype=np.uint64)%(2**32))!=binding['parent_trace'][i-1]['image_checksum']:_fail('actual packed checksum/parent trace mismatch')
        capture._fields(state_row,{'pre_state','post_state','fixed_inputs','raw4','plan'})
        states={}
        for group in ('pre_state','post_state'):
            capture._fields(state_row[group],set(STATE_DTYPES))
            states[group]={k:_load_array(root,state_row[group][k],contract.input_shapes[k],dtype,registered) for k,dtype in STATE_DTYPES.items()}
            decoded_total+=sum(v.nbytes for v in states[group].values())
        if previous_post is None:
            if any(np.any(v) for v in states['pre_state'].values()):_fail('initial recurrent state is not reset zeros')
        elif any(not np.array_equal(previous_post[k],states['pre_state'][k]) for k in STATE_DTYPES):_fail('step-to-step recurrent chain mismatch')
        previous_post=states['post_state']
        fixed=state_row['fixed_inputs'];capture._fields(fixed,{'desire','traffic_convention','action_t'})
        for name,shape,expected in (('desire',(8,),np.zeros((8,),np.float32)),('traffic_convention',(1,2),np.array([[1,0]],np.float32)),('action_t',(1,2),np.array([[.175,.175]],np.float32))):
            value=_load_array(root,fixed[name],shape,'float32',registered);decoded_total+=value.nbytes
            if not np.array_equal(value,expected):_fail('source-reconstructed fixed feed changed')
        raw4=_load_array(root,state_row['raw4'],(4,),'float32',registered)
        plan=_load_array(root,state_row['plan'],(990,),'float32',registered)
        decoded_total+=raw4.nbytes+plan.nbytes+capture.PACKED_BYTES
        trace=binding['parent_trace'][i-1]
        if float(raw4[0])!=trace['raw_lateral_accel_mps2'] or float(raw4[1])!=trace['raw_longitudinal_accel_mps2']:_fail('actual raw4/trace/action association mismatch')
    if decoded_total>observed['retained_payload_bytes'] or decoded_total>capture.PAYLOAD_CAP_BYTES:_fail('retained array/image byte budget mismatch')


def _validate_trial(root,expected=None,manifest=None):
    root=Path(root)
    data=capture._read_json(capture._safe_path(root,'trial.json')) if manifest is None else manifest
    capture._fields(data,{'schema','status','protocol','arm','repeat','nonce','process_id','process_uuid','parent_pid','parent_uuid',
        'process_group','source_snapshot','runtime','provider_closed','error','error_chain','cleanup_errors','storage','preflight','binding','report','observed',
        'model_calls','model_calls_lower_bound','model_calls_upper_bound','claims','limitation'})
    if data['schema']!=TRIAL_SCHEMA or data['status']!='TRIAL_ASSOCIATION_VALIDATED' or data['provider_closed'] is not True or data['error'] is not None or data['error_chain']!=[] or data['cleanup_errors']!=[]:_fail('failed/incomplete child')
    if not capture._exact(data['protocol'],PROTOCOL) or not capture._exact(data['claims'],capture.CLAIMS) or data['limitation']!=LIMITATION:_fail('trial protocol/claims changed')
    if data['source_snapshot']!=capture.source_snapshot() or data['runtime']!=_runtime_identity():_fail('child source/runtime identity mismatch')
    if data['preflight']!=retention_preflight(capture.REPO_ROOT/'model_specs/md-v3.json'):_fail('payload preflight changed')
    if any(type(data[k]) is not int or data[k]!=4 for k in ('model_calls','model_calls_lower_bound','model_calls_upper_bound')):_fail('complete child call accounting mismatch')
    if data['arm'] not in capture.ARMS or type(data['repeat']) is not int or data['repeat'] not in (0,1) or not capture._is_hash(data['nonce']):_fail('child schedule/nonce invalid')
    for key in ('process_id','parent_pid','process_group'):
        if type(data[key]) is not int or data[key]<=0:_fail('actual positive process identities required')
    if data['process_id']==data['parent_pid']:_fail('child is not fresh parent process')
    for key in ('process_uuid','parent_uuid'):
        value=data[key]
        if type(value) is not str or len(value)!=32 or any(c not in '0123456789abcdef' for c in value):_fail('process UUID invalid')
    if expected is not None and any(data.get(k)!=v for k,v in expected.items()):_fail('child differs from actual parent launch ledger')
    capture._fields(data['storage'],{'limits','payload_charged_bytes','limit_error'})
    limits=_storage_limits(data['storage']['limits'])
    if type(data['storage']['payload_charged_bytes']) is not int or not 0<=data['storage']['payload_charged_bytes']<=limits['payload_limit_bytes'] or data['storage']['limit_error'] is not None:_fail('trial disk budget invalid')
    _validate_binding_report(data)
    registered={'trial.json'} if manifest is None else set()
    if (root/'process.log').is_file():registered.add('process.log')
    if data['arm']=='original':
        if data['observed'] is not None:_fail('unobserved original must keep intermediate payload unknown')
    else:
        observed=data['observed'];capture._fields(observed,{'reset_calls','steps','capture_count','capture_rows','retained_payload_bytes','captures','arrays','actual_image_scope','other_feed_scope'})
        if observed['actual_image_scope']!='ACTUAL_PARENT_NEW_IMG_SHA_ONLY' or observed['other_feed_scope']!='SOURCE_RECONSTRUCTED_NOT_INTERCEPTED':_fail('feed provenance changed')
        if type(observed['reset_calls']) is not int or observed['reset_calls']!=1:_fail('observer reset forwarding mismatch')
        steps=observed['steps']
        if type(steps) is not list or len(steps)!=4:_fail('complete observed step prefix required')
        for i,row in enumerate(steps,1):
            capture._fields(row,{'step','status','graph_calls','graph_calls_upper_bound','actual_input_sha256','policy_inclusive_wall_s',
                'observer_before_wall_s','parent_inclusive_wall_s','observer_after_wall_s','capture_index','observation','error','action'})
            if type(row['step']) is not int or row['step']!=i or row['status']!='RETURNED' or row['error'] is not None or any(type(row[k]) is not int or row[k]!=1 for k in ('graph_calls','graph_calls_upper_bound')) or not capture._is_hash(row['actual_input_sha256']):_fail('invalid observed parent step')
            if row['observation']!={'speed_mps':8.,'time_s':(i-1)*.05} and not (row['observation'].get('speed_mps')==8. and math.isclose(row['observation'].get('time_s',-1),(i-1)*.05,abs_tol=1e-12)):_fail('observed clock/speed mismatch')
            capture._fields(row['observation'],{'speed_mps','time_s'})
            if any(not capture._number(row[k]) or row[k]<0 for k in ('policy_inclusive_wall_s','observer_before_wall_s','parent_inclusive_wall_s','observer_after_wall_s')):_fail('observer wall timing invalid')
            if row['policy_inclusive_wall_s']+1e-12<sum(row[k] for k in ('observer_before_wall_s','parent_inclusive_wall_s','observer_after_wall_s')):_fail('observer timing double counted')
            if row['action']!=data['binding']['bridge_receipts'][i-1]['applied_world_action']:_fail('observer returned another action')
        selected=_validate_capture_rows(observed,data['report']['frames'],steps)
        if type(observed['retained_payload_bytes']) is not int or not 0<=observed['retained_payload_bytes']<=capture.PAYLOAD_CAP_BYTES:_fail('observer payload cap')
        if data['arm']=='proxy':
            if observed['retained_payload_bytes']!=0 or observed['captures']!=[] or observed['arrays']!=[]:_fail('proxy fabricated or retained payload')
        else:_validate_retention(root,observed,data['report']['frames'],steps,selected,registered,data['binding'])
    total=_dataset_bytes(root)
    payload=sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and p.name not in ('trial.json','process.log'))
    if payload>data['storage']['payload_charged_bytes']:_fail('payload bytes exceed pre-write storage reservation')
    if manifest is not None and total+len((json.dumps(manifest,indent=2,allow_nan=False)+'\n').encode())>capture.DATASET_CAP_BYTES:_fail('candidate dataset byte cap')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual!=registered:_fail('missing or unregistered trial member')
    return data


def _comparisons(trials):
    result=[]
    by={(t['arm'],t['repeat']):t for t in trials}
    pairs=[((arm,0),(arm,1)) for arm in capture.ARMS]
    pairs += [((a,r),(b,r)) for r in (0,1) for a,b in (('original','proxy'),('proxy','retention'),('original','retention'))]
    for a,b in pairs:
        if a not in by or b not in by:continue
        first,second=by[a],by[b];differences={};availability={}
        for name in ('road_frame_sha256','wide_frame_sha256','desired_curvature_1pm','desired_acceleration_mps2','world_x_m','world_y_m','heading_rad'):
            availability[name]='generic-report-observed'
            differences[name]=next((i+1 for i,(x,y) in enumerate(zip(first['report']['frames'],second['report']['frames'])) if x[name]!=y[name]),None)
        for name in ('actual_input_sha256','pre_state','post_state','raw4','plan','raw_rgb'):
            available=(name=='actual_input_sha256' and first['observed'] is not None and second['observed'] is not None) or (name!='actual_input_sha256' and a[0]==b[0]=='retention')
            availability[name]='observed' if available else 'unknown-unobserved-control'
            differences[name]=None
            if available:
                for index in range(4):
                    x=first['observed'];y=second['observed']
                    if name=='actual_input_sha256':vx=x['steps'][index][name];vy=y['steps'][index][name]
                    elif name=='raw_rgb':vx={k:v['rgb_sha256'] for k,v in x['captures'][index]['raw'].items()};vy={k:v['rgb_sha256'] for k,v in y['captures'][index]['raw'].items()}
                    elif name in ('raw4','plan'):vx=x['arrays'][index][name]['array'];vy=y['arrays'][index][name]['array']
                    else:vx={k:v['array'] for k,v in x['arrays'][index][name].items()};vy={k:v['array'] for k,v in y['arrays'][index][name].items()}
                    if vx!=vy:differences[name]=index+1;break
        result.append(dict(pair=[list(a),list(b)],availability=availability,first_differences=differences,
            interpretation='DESCRIPTIVE_ONLY_NO_DIFFERENCE_WITHIN_FOUR_STEPS_IS_INCONCLUSIVE',
            graph_elapsed_ms=[[t['elapsed_ms'] for t in trial['binding']['parent_trace']] for trial in (first,second)],
            observer_wall_s=[([s['policy_inclusive_wall_s']-s['parent_inclusive_wall_s'] for s in trial['observed']['steps']] if trial['observed'] is not None else None) for trial in (first,second)],
            capture_wall_s=[({key:sum(row[key] for row in trial['observed']['capture_rows']) for key in
                ('capture_inclusive_wall_s','raw_callback_nested_wall_s','wrapper_observer_arithmetic_wall_s')} if trial['observed'] is not None else None) for trial in (first,second)],
            capture_timing_scope='raw callback nested within inclusive capture; never add the two; wall durations, not CPU execution time'))
    return result


def validate_study(root):
    return _validate_study(Path(root))


def _validate_study(root,manifest=None):
    root=Path(root)
    data=capture._read_json(capture._safe_path(root,'study.json')) if manifest is None else manifest
    capture._fields(data,{'schema','status','protocol','source_snapshot','runtime','parent_pid','parent_uuid','acceptance','launch_ledger',
        'error','cleanup_errors','storage','elapsed_wall_s','model_calls','model_calls_lower_bound','model_calls_upper_bound','claims','limitation','comparisons'})
    if data['schema']!=STUDY_SCHEMA or data['status']!='STUDY_ASSOCIATION_VALIDATED' or data['error'] is not None or data['cleanup_errors']!=[]:_fail('failed/incomplete study')
    if not capture._exact(data['protocol'],PROTOCOL) or not capture._exact(data['claims'],capture.CLAIMS) or data['limitation']!=LIMITATION:_fail('study claims/protocol changed')
    if data['source_snapshot']!=capture.source_snapshot() or data['runtime']!=_runtime_identity():_fail('study source/runtime mismatch')
    if any(type(data[k]) is not int or data[k]!=24 for k in ('model_calls','model_calls_lower_bound','model_calls_upper_bound')):_fail('study call bounds')
    if not capture._number(data['elapsed_wall_s']) or not 0<=data['elapsed_wall_s']<=STUDY_LIMIT_S:_fail('study wall cap')
    capture._fields(data['storage'],{'dataset_cap_bytes','ledger_limit_bytes'})
    if data['storage']!={'dataset_cap_bytes':capture.DATASET_CAP_BYTES,'ledger_limit_bytes':_ledger_reserve(capture.DATASET_CAP_BYTES)}:_fail('study storage allocation changed')
    receipt=data['acceptance'];_receipt_current_binding(receipt)
    if receipt.get('current_context',{}).get('repository')!=REPOSITORY:_fail('study acceptance repository')
    ledger=data['launch_ledger']
    if type(ledger) is not list or len(ledger)!=6:_fail('six real child launch records required')
    trials=[];pids=set();uuids=set();nonces=set();last_exit=0.;prefix_bytes=0
    for i,(row,(arm,repeat)) in enumerate(zip(ledger,SCHEDULE)):
        capture._fields(row,{'schedule_index','arm','repeat','nonce','launched','launcher_pid','process_group','launch_elapsed_s',
            'exit_elapsed_s','exit_code','timed_out','child_pid','child_uuid','validation_error','cleanup_errors','storage'})
        if type(row['schedule_index']) is not int or row['schedule_index']!=i or (row['arm'],row['repeat'])!=(arm,repeat) or row['launched'] is not True or row['exit_code']!=0 or row['timed_out'] is not False or row['validation_error'] is not None or row['cleanup_errors']!=[]:_fail('child launch/exit schedule invalid')
        storage=row['storage'];capture._fields(storage,{'payload_limit_bytes','trial_ledger_limit_bytes','log_limit_bytes','log_bytes','limit_error'})
        limits=_storage_limits({k:storage[k] for k in ('payload_limit_bytes','trial_ledger_limit_bytes','log_limit_bytes')})
        if limits!=_child_storage_limits(capture.DATASET_CAP_BYTES-data['storage']['ledger_limit_bytes']-prefix_bytes):_fail('child allocation differs from remaining dataset budget')
        logfile=root/f'trial_{i:02d}'/'process.log'
        if storage['limit_error'] is not None or type(storage['log_bytes']) is not int or not 0<=storage['log_bytes']<=limits['log_limit_bytes'] or storage['log_bytes']!=(logfile.stat().st_size if logfile.is_file() else 0):_fail('child log budget invalid')
        if type(row['launcher_pid']) is not int or row['launcher_pid']<=0 or row['process_group']!=row['launcher_pid']:_fail('launcher/group identity invalid')
        launch,exit=row['launch_elapsed_s'],row['exit_elapsed_s']
        if not capture._number(launch) or not capture._number(exit) or not last_exit<=launch<=exit<=data['elapsed_wall_s'] or exit-launch>CHILD_LIMIT_S+10.:_fail('child sequential wall bounds invalid')
        trial=_validate_trial(root/f'trial_{i:02d}',expected=dict(arm=arm,repeat=repeat,nonce=row['nonce'],
            parent_pid=data['parent_pid'],parent_uuid=data['parent_uuid'],process_group=row['process_group']))
        if trial['storage']['limits']!=limits:_fail('child disk allocation differs from parent authorization')
        prefix_bytes+=_dataset_bytes(root/f'trial_{i:02d}')
        if trial['process_id']!=row['child_pid'] or trial['process_uuid']!=row['child_uuid'] or trial['process_id'] in pids or trial['process_uuid'] in uuids or row['nonce'] in nonces:_fail('fresh child/process/nonce ledger association invalid')
        pids.add(trial['process_id']);uuids.add(trial['process_uuid']);nonces.add(row['nonce']);trials.append(trial);last_exit=exit
    if data['comparisons']!=_comparisons(trials):_fail('descriptive differences were not derived from actual trials')
    allowed={f'trial_{i:02d}' for i in range(6)}
    if manifest is None:allowed.add('study.json')
    if {p.name for p in root.iterdir()}!=allowed:_fail('unregistered study root member')
    total=_dataset_bytes(root)
    if manifest is not None and total+len((json.dumps(manifest,indent=2,allow_nan=False)+'\n').encode())>capture.DATASET_CAP_BYTES:_fail('candidate study byte cap')
    return data
