"""Registered CI camera replay with common Texture and optional clock observers.

The old model launcher is reused solely as a bounded pipe/process transport.
This module never invokes its official-model authorization or model factory.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import secrets
import select
import signal
import stat
import subprocess
import sys
import tempfile
import threading
from time import perf_counter
import uuid

import numpy as np
from bigbench import first_divergence as capture
from bigbench import first_divergence_model as oldmodel
from scripts import texture_generation_markers as marker
from scripts import engine_clock_boundaries as clock

REPO = Path(__file__).resolve().parents[1]
SCRIPT_PATH = 'scripts/engine_clock_native.py'
TEST_PATH = 'tests/test_engine_clock_native.py'
WORKFLOW = '.github/workflows/stage7-engine-clock-boundaries.yml'
REQUEST = '.github/stage7-engine-clock-request.json'
BRANCH = 'diagnostic/engine-clock-boundaries'
REPOSITORY = oldmodel.REPOSITORY
REQUEST_SCHEMA = 'engine-clock-request-v1'
SCHEMA = 'engine-clock-phase-v1'
CASE_SCHEMA = 'engine-clock-case-v1'
CAMERAS = ('road', 'wide')
JSON_CAP = 2*1024*1024
LOG_CAP = 1024*1024
RETENTION_CAP = 32*1024*1024
PAYLOAD_CAP = 40*1024*1024
DATASET_CAP = 192*1024*1024
CACHE_CAP = 64*1024*1024
CACHE_FILES = 1024
CHILD_S = 270
CASE_S = 300
PHASE_S = 1320
POSE0 = dict(t=0.,x=65.4052721645879,y=.26625325426066837,heading=.09843656981248028,speed=8.)
POSE1 = dict(t=.05,x=65.80328679516661,y=.30605719684545585,heading=.10091307127732403,speed=8.)
POSES = [POSE0]*4+[POSE1]*2
SCHEDULES = {'canary':[(True,0)],'abba':[(False,0),(True,0),(True,1),(False,1)]}
LIMITS = dict(payload_limit_bytes=PAYLOAD_CAP,trial_ledger_limit_bytes=JSON_CAP,log_limit_bytes=LOG_CAP)
PROTOCOL = dict(texture_markers_enabled=True,clock_max_pairs=6,clock_trace_bytes=65536,
                seed=20261109,scenario='s_curve_left_right',poses=POSES,
                schedule={k:[[a,b] for a,b in v] for k,v in SCHEDULES.items()},
                child_s=CHILD_S,case_s=CASE_S,phase_s=PHASE_S,storage=LIMITS,retention_bytes=RETENTION_CAP,dataset_bytes=DATASET_CAP,
                cache_bytes=CACHE_CAP,cache_files=CACHE_FILES)
CLAIMS = dict(official_model_calls=0,ort_sessions=0,extra_gpu_reads=0,original_strict_pass=False,
              installed_binary_equality_proven=False,markers_are_fences=False,observer_effects_absent=False)
LIMITATION = ('Fixed camera-only 4+2 replay with common raw retention, Texture markers and clock method wrappers; CPU clock pairs are non-atomic, absolute counts/times descriptive only, and do not prove GPU frame identity or callback ordering. Startup sensor '
              'activity is outside observed read counts. CPU signed generation equality is not freshness '
              'or GPU completion. Retention, hashing, wrapper overhead, fresh processes and cold Mesa '
              'compilation change wall timing. Cache inventory verifies routing/population, not individual '
              'hits. Derived I420 is not a graph feed; no scientific PASS or binary equality claim.')
PINNED = {'numpy':'2.4.6','opencv-python-headless':'5.0.0.93','panda3d':'1.10.13','metadrive-simulator':'0.4.3'}
ACCEPTANCE_KEYS = {'source_sha','run_id','run_attempt','workflow_id','artifact_id','artifact_name',
                   'artifact_size_bytes','artifact_sha256','root_raw_accepted','fresh_raw_review_accepted'}


_fail = marker._fail
_sha = marker._sha
_fields = marker._fields
_same = marker._same
_positive = marker._positive
_hex = marker._hex
_duration = marker._duration
_json = marker._json
_read = marker._read
_write = marker._write
_detail = marker._detail
_remaining = marker._remaining


def source_snapshot():
    result=marker.source_snapshot()
    for name in ('scripts/engine_clock_boundaries.py','tests/test_engine_clock_boundaries.py',SCRIPT_PATH,TEST_PATH,WORKFLOW):
        path=capture._safe_path(REPO,name)
        if not path.is_file():_fail('required source missing: '+name)
        result[name]=_sha(path.read_bytes())
    if len(result)!=70:_fail('source closure must contain exactly 70 paths')
    return dict(sorted(result.items()))


marker_scope = marker.marker_scope


def _runtime():
    result=capture.runtime_versions()
    import cv2
    result['cv2']=cv2.__version__
    for key in ('ImageOS','ImageVersion'):result[key]=os.environ.get(key)
    _check_runtime(result)
    if any(k=='onnxruntime' or k.startswith('onnxruntime.') for k in sys.modules):_fail('imported ORT prohibited in native harness')
    return result


def _check_runtime(value):
    _fields(value,set(PINNED)|{'python','executable','onnxruntime','cv2','ImageOS','ImageVersion'})
    if any(value[k]!=v for k,v in PINNED.items()) or value['onnxruntime'] is not None or value['cv2']!='5.0.0' or value['ImageOS']!='ubuntu24':_fail('native runtime pins or installed ORT mismatch')
    if not isinstance(value['python'],str) or not value['python'].startswith('3.11.'):_fail('Python3.11 required')
    if any(type(value[k]) is not str or not value[k] for k in ('executable','cv2','ImageOS','ImageVersion')):_fail('native runtime/image identity missing')


def _request_data(value):
    _fields(value,{'schema','mode','acceptance'})
    if value['schema']!=REQUEST_SCHEMA or value['mode'] not in SCHEDULES:_fail('unregistered request')
    a=value['acceptance']
    if value['mode']=='canary':
        if a is not None:_fail('canary cannot carry acceptance')
    else:
        _fields(a,ACCEPTANCE_KEYS)
        if (not _hex(a['source_sha'],40) or not _hex(a['artifact_sha256'],64) or
            any(not _positive(a[k]) for k in ('run_id','workflow_id','artifact_id','artifact_size_bytes')) or
            type(a['run_attempt']) is not int or a['run_attempt']!=1 or a['artifact_size_bytes']>DATASET_CAP or
            a['artifact_name']!='stage7-engine-clock-canary' or
            a['root_raw_accepted'] is not True or a['fresh_raw_review_accepted'] is not True):_fail('invalid actual canary acceptance')
    return value


def _request_bytes(raw):
    if len(raw)>65536:_fail('request byte cap; failure-ledger reserve required')
    return _request_data(_json(raw))


class _DeadlineAPI:
    """Keep frozen read-only HTTP transport, adding an absolute call deadline.

    Its socket timeout alone cannot bound a slowly streaming response. Linux
    SIGALRM bounds the entire synchronous transport including redirects/reads.
    """
    def __init__(self,api,deadline):self.api=api;self.deadline=deadline
    def _call(self,method,*args):
        if _remaining(self.deadline)<60.:_fail('API call cannot reserve its 60s deadline')
        handler=signal.getsignal(signal.SIGALRM)
        previous=signal.getitimer(signal.ITIMER_REAL)
        if previous!=(0.,0.):_fail('concurrent API alarm prohibited')
        def expired(signum,frame):raise TimeoutError('absolute API call deadline')
        signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,60.)
        try:return getattr(self.api,method)(*args)
        finally:
            signal.setitimer(signal.ITIMER_REAL,0.);signal.signal(signal.SIGALRM,handler)
    def json(self,path):return self._call('json',path)
    def download(self,path,limit):return self._call('download',path,limit)


def _git(*args,deadline=None):
    result=subprocess.run(['git',*args],cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          timeout=min(10.,_remaining(deadline)) if deadline else 10.,check=False)
    if result.returncode:_fail('required Git source unavailable')
    return result.stdout


def _run_context(run):
    if (type(run) is not dict or run.get('event')!='push' or run.get('head_branch')!=BRANCH or
        run.get('path')!=WORKFLOW or run.get('repository',{}).get('full_name')!=REPOSITORY or
        any(not _positive(run.get(k)) for k in ('id','workflow_id')) or
        type(run.get('run_attempt')) is not int or run['run_attempt']!=1 or not _hex(run.get('head_sha'),40)):
        _fail('API run identity mismatch')
    return dict(repository=REPOSITORY,workflow_path=WORKFLOW,workflow_id=run['workflow_id'],
                head_sha=run['head_sha'],run_id=run['id'],attempt=1,event='push',branch=BRANCH)


def _context(api,deadline):
    expected=dict(repository=os.environ.get('GITHUB_REPOSITORY'),head_sha=os.environ.get('GITHUB_SHA'),
                  event=os.environ.get('GITHUB_EVENT_NAME'),branch=os.environ.get('GITHUB_REF_NAME'))
    if (os.environ.get('GITHUB_ACTIONS')!='true' or expected['repository']!=REPOSITORY or expected['event']!='push' or
        expected['branch']!=BRANCH or os.environ.get('GITHUB_RUN_ATTEMPT')!='1' or not _hex(expected['head_sha'],40)):
        _fail('actual registered CI context required')
    runid=os.environ.get('GITHUB_RUN_ID','')
    if not runid.isdecimal() or int(runid)<=0:_fail('invalid run id')
    _remaining(deadline)
    run=api.json(f'/repos/{REPOSITORY}/actions/runs/{runid}');context=_run_context(run)
    if run.get('status')!='in_progress' or any(context[k]!=v for k,v in expected.items()) or context['run_id']!=int(runid):_fail('current API run binding/status mismatch')
    workflow=api.json(f'/repos/{REPOSITORY}/actions/workflows/{context["workflow_id"]}')
    if workflow.get('id')!=context['workflow_id'] or workflow.get('path')!=WORKFLOW or workflow.get('state')!='active':_fail('API workflow identity mismatch')
    if _git('rev-parse','HEAD',deadline=deadline).decode().strip()!=context['head_sha']:_fail('actual checkout HEAD mismatch')
    snapshot=source_snapshot()
    for name,digest in snapshot.items():
        if _sha(_git('show',context['head_sha']+':'+name,deadline=deadline))!=digest:_fail('Git source70 blob mismatch: '+name)
    raw=(REPO/REQUEST).read_bytes();request=_request_bytes(raw)
    if raw!=_git('show',context['head_sha']+':'+REQUEST,deadline=deadline):_fail('request differs from actual Git blob')
    if _git('status','--porcelain','--untracked-files=no',deadline=deadline).strip():_fail('tracked source checkout dirty')
    return context,snapshot,request,_sha(raw)


def _output(out,phase):
    if phase not in SCHEDULES:_fail('unknown phase')
    capture._require_ephemeral_ci(Path(out));capture._safe_path(Path(out),'phase.json')
    expected=Path(os.environ['RUNNER_TEMP']).resolve()/('engine-clock-'+phase)
    if Path(out).absolute()!=expected or Path(out).exists():_fail('fixed phase output must be fresh')
    return expected


_cache_inventory = marker._cache_inventory


_group_gone = marker._group_gone


def _consume(phase,index,nonce,out):
    fdtext=os.environ.pop('FIRST_DIVERGENCE_TRIAL_FD',None)
    if not fdtext or not fdtext.isdecimal() or int(fdtext)<10:_fail('one-use inherited FD>=10 required')
    fd=int(fdtext);deadline=perf_counter()+10.;blocks=[];size=0
    try:
        if not stat.S_ISFIFO(os.fstat(fd).st_mode):_fail('authorization must be FIFO')
        os.set_blocking(fd,False)
        while True:
            ready,_,_=select.select([fd],[],[],_remaining(deadline))
            if not ready:_fail('authorization EOF deadline')
            block=os.read(fd,min(65536,JSON_CAP+1-size))
            if not block:break
            size+=len(block)
            if size>JSON_CAP:_fail('authorization size cap')
            blocks.append(block)
    finally:os.close(fd)
    permit=_json(b''.join(blocks))
    _fields(permit,{'parent_pid','parent_uuid','process_group','nonce','arm','repeat','source_snapshot','runtime','schedule_index','storage_limits'})
    if phase not in SCHEDULES or type(index) is not int or not 0<=index<len(SCHEDULES[phase]) or not _hex(nonce,64):_fail('child schedule/nonce invalid')
    enabled,_=SCHEDULES[phase][index]
    _same((permit['arm'],permit['repeat'],permit['nonce'],permit['schedule_index']),('retention' if enabled else 'original',0,nonce,index))
    _same(permit['storage_limits'],LIMITS)
    if not _positive(permit['parent_pid']) or permit['parent_pid']==os.getpid() or not _hex(permit['parent_uuid'],32):_fail('parent identity invalid')
    if not _positive(permit['process_group']) or permit['process_group']!=os.getpgid(0):_fail('fresh launcher process group mismatch')
    os.kill(permit['parent_pid'],0)
    # The live root must also be an actual ancestor of the Xvfb/Python child.
    current=os.getpid();ancestors=[]
    for _ in range(32):
        try:parent=int(Path(f'/proc/{current}/status').read_text().split('PPid:\t',1)[1].splitlines()[0])
        except (OSError,ValueError,IndexError):_fail('live root ancestry unavailable')
        ancestors.append(parent)
        if parent in (0,1) or parent==permit['parent_pid']:break
        current=parent
    if permit['parent_pid'] not in ancestors:_fail('permit parent is not live root ancestor')
    _same(permit['source_snapshot'],capture.source_snapshot())
    _same(permit['runtime'],oldmodel._runtime_identity())
    binding=_json(os.environ.get('ENGINE_CLOCK_BINDING','').encode())
    _fields(binding,{'phase','parent_pid','parent_uuid','root','context','source_snapshot','runtime','request_sha256'})
    if binding['phase']!=phase or binding['parent_pid']!=permit['parent_pid'] or binding['parent_uuid']!=permit['parent_uuid']:_fail('own parent/phase association mismatch')
    root=Path(binding['root']);capture._require_ephemeral_ci(root)
    expected=Path(os.environ['RUNNER_TEMP']).resolve()/('engine-clock-'+phase)
    if root!=expected or Path(out)!=root/f'case_{index:02d}' or not root.is_dir():_fail('child output is not parent phase member')
    capture._safe_path(root,f'case_{index:02d}/case.json')
    if (Path(out)/'case.json').exists():_fail('child evidence must be fresh')
    if 'FIRST_DIVERGENCE_ACCEPTANCE' in os.environ:_fail('model acceptance must be cleared')
    admission_deadline=perf_counter()+120.
    api=_DeadlineAPI(oldmodel._github(),admission_deadline)
    context,snapshot,request,request_sha=_context(api,admission_deadline)
    _unique_run(api,context)
    _same(binding['context'],context);_same(binding['source_snapshot'],snapshot)
    _same(binding['runtime'],_runtime())
    if request['mode']!=phase or request_sha!=binding['request_sha256']:_fail('child Git-bound request mismatch')
    cache=Path(os.environ.get('MESA_SHADER_CACHE_DIR',''))
    if ('MESA_SHADER_CACHE_DISABLE' in os.environ or not cache.is_absolute() or
        Path(os.environ['RUNNER_TEMP']).resolve() not in cache.parents or root in cache.parents or not cache.is_dir() or
        _cache_inventory(cache)['files']!=0):_fail('fresh external Mesa cache required')
    return permit,binding


_persist_unclosed_snapshots = marker._persist_unclosed_snapshots


def _failure_prefix(collector,out,data):
    """Describe CPU records separately from files which reached durable storage.

    Never retry serialization, copy arrays, derive I420 or hash payloads here.
    Existing raw hashes and bounded file metadata retain the partial association.
    """
    if len(collector.records)>6:_fail('failure CPU-record cap')
    data['accepted_cpu_records_before_serialization']=[
        dict(accepted_index=i,capture_index=r.capture_index,raw_sha256=dict(r.raw_sha256),observation=dict(r.observation))
        for i,r in enumerate(collector.records,1)]
    data['bulk_serialization_attempted']=collector._serialization_started
    data['persisted_payload_prefix']=[]
    try:
        members,_=_members(out,PAYLOAD_CAP+LOG_CAP)
        total=0
        for name in sorted(members-{'process.log','case.json'}):
            if len(data['persisted_payload_prefix'])>=30:_fail('failure payload member cap')
            path=capture._safe_path(out,name);size=path.stat().st_size;total+=size
            if total>PAYLOAD_CAP:_fail('failure payload byte cap')
            data['persisted_payload_prefix'].append(dict(path=name,nbytes=size))
    except BaseException as exc:data['cleanup_errors'].append('failure prefix inventory: '+_detail(exc))


def run_child(out,phase,index,nonce):
    out=Path(out)
    if threading.current_thread() is not threading.main_thread():_fail('actual Python main thread required before constructor')
    permit,binding=_consume(phase,index,nonce,out)
    from bigbench import native_model_campaign as campaign
    from bigbench.curved_lane_scenarios import SCENARIOS
    from bigbench.kinematics import AgentState
    from bigbench.metadrive_camera import NativeMetaDriveProvider
    from bigbench.policies import ModelObservation
    enabled,repeat=SCHEDULES[phase][index]
    collector=capture.CaptureCollector('retention',payload_cap_bytes=RETENTION_CAP,max_captures=6)
    if capture.capture_payload_estimate(6,extra_retained_bytes=65536)>RETENTION_CAP:_fail('retention preflight exceeds payload cap')
    data=dict(schema=CASE_SCHEMA,status='FAILED_OR_INCOMPLETE',phase=phase,index=index,clock_enabled=enabled,repeat=repeat,
              nonce=nonce,parent_pid=permit['parent_pid'],parent_uuid=permit['parent_uuid'],
              process_id=os.getpid(),process_uuid=uuid.uuid4().hex,process_group=os.getpgid(0),
              context=binding['context'],source_snapshot=binding['source_snapshot'],runtime=binding['runtime'],
              request_sha256=binding['request_sha256'],protocol=PROTOCOL,claims=CLAIMS,limitation=LIMITATION,
              provider_attempted=False,provider_constructed=False,provider_closed=False,
              provider_lower_bound=0,provider_upper_bound=1,texture_markers_enabled=True,
              main_thread_id=threading.get_ident(),clock_trace={},markers=[],capture_rows=[],accepted=[],
              capture_count=0,observed_reads=0,marker_reads=0,retained_payload_bytes=0,
              payload_charged_bytes=0,error=None,cleanup_errors=[])
    provider=None;disk=oldmodel._StorageBudget(PAYLOAD_CAP)
    try:
        data['provider_attempted']=True
        provider=NativeMetaDriveProvider(seed=20261109,map_config=SCENARIOS['s_curve_left_right'].map_config())
        data['provider_constructed']=True;data['provider_lower_bound']=1
        with marker_scope(provider,True,data['markers']),clock.camera_clock_scope(provider,enabled,data['clock_trace'],max_pairs=6),capture.capture_scope('retention',collector):
            camera=campaign.NativeWorldCamera(provider)
            for pose in POSES:
                pair=camera.capture(AgentState(**pose))
                collector.accept_observation(ModelObservation(pair.road,8.,pose['t'],wide_frame=pair.wide))
    except BaseException as exc:data['error']=_detail(exc)
    finally:
        if provider is not None:
            try:provider.close();data['provider_closed']=True;collector.mark_closed()
            except BaseException as exc:
                if data['error'] is None:data['error']=_detail(exc)
                else:data['cleanup_errors'].append(_detail(exc))
        data['capture_count']=collector.capture_count;data['capture_rows']=collector.capture_rows
        data['observed_reads']=len(data['markers'])
        data['marker_reads']=sum((r['before'] is not None)+(r['after'] is not None) for r in data['markers'])
        data['retained_payload_bytes']=collector.payload_bytes
        if data['provider_closed']:
            try:data['accepted']=collector.serialize_captures(out,write_budget=disk)
            except BaseException as exc:
                if data['error'] is None:data['error']=_detail(exc)
                else:data['cleanup_errors'].append(_detail(exc))
        elif collector.records:
            evidence=dict(schema='texture-marker-closure-unconfirmed-v1',
                          status='CLOSURE_UNCONFIRMED_CPU_SNAPSHOTS',provider_closed=False,
                          association='ALREADY_ACCEPTED_CPU_RAW_AND_ACTUAL_CANVAS_CLOSURE_UNCONFIRMED',
                          complete=False,rows=[],error=None)
            data['closure_unconfirmed_snapshots']=evidence
            try:_persist_unclosed_snapshots(collector,out,disk,evidence)
            except BaseException as exc:
                evidence['error']=_detail(exc);data['cleanup_errors'].append(evidence['error'])
        data['payload_charged_bytes']=disk.charged
    if data['error'] is None and not data['cleanup_errors']:data['status']='CLOCK_CAMERA_REPLAY_RECORDED'
    else:
        data['observed_reads']=None;data['marker_reads']=None
        _failure_prefix(collector,out,data)
    _write(out/'case.json',data)
    return data


def _case(out,phase,index,parent_uuid,binding,deadline):
    started=perf_counter();execution_deadline=min(started+CHILD_S,deadline-30.)
    enabled,_=SCHEDULES[phase][index];nonce=secrets.token_hex(32)
    cache=Path(os.environ['RUNNER_TEMP'])/('engine-clock-cache-'+parent_uuid+f'-{index:02d}')
    row=dict(index=index,clock_enabled=enabled,nonce=nonce,attempted=True,launched=False,launcher_pid=None,
             process_group=None,exit_code=None,cleanup_errors=[],error=None,group_gone=False,reaped=False,
             provider_lower_bound=0,provider_upper_bound=1,provider_attempted=None,provider_constructed=None,provider_closed=None,
             storage=dict(LIMITS,log_bytes=0,limit_error=None),cache_path=str(cache),cache_before=None,
             cache_after=None,launch_s=0.,wait_s=0.,elapsed_s=0.,log=None)
    dummy=out.parent/'NO_MODEL_ENGINE_CLOCK.onnx';spec=REPO/'model_specs/md-v3.json'
    real_popen=subprocess.Popen;original_env=dict(os.environ);raw=[];child=None
    childenv=dict(original_env,MESA_SHADER_CACHE_DIR=str(cache),ENGINE_CLOCK_BINDING=json.dumps(binding,allow_nan=False))
    childenv.pop('FIRST_DIVERGENCE_ACCEPTANCE',None);childenv.pop('MESA_SHADER_CACHE_DISABLE',None)
    def adapter(command,**kwargs):
        expected=['xvfb-run','-a',sys.executable,'-m','scripts.first_divergence_audit','native-trial',
                  '--model',str(dummy.resolve()),'--spec',str(spec.resolve()),'--out',str(out),
                  '--arm','retention' if enabled else 'original','--repeat','0','--nonce',nonce]
        env=kwargs.get('env',{});fdtext=env.get('FIRST_DIVERGENCE_TRIAL_FD','')
        expected_kwargs=dict(cwd=REPO,env=dict(childenv,FIRST_DIVERGENCE_TRIAL_FD=fdtext),stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(int(fdtext),) if fdtext.isdecimal() else ())
        if command!=expected or kwargs!=expected_kwargs or not fdtext.isdecimal() or int(fdtext)<10 or raw:_fail('fixed launcher substitution mismatch/retry')
        _remaining(execution_deadline)
        process=real_popen(['xvfb-run',sys.executable,'-m','scripts.engine_clock_native','child',
                           '--out',str(out),'--phase',phase,'--index',str(index),'--nonce',nonce],**kwargs)
        raw.append(process);return process
    try:
        if cache.exists():_fail('case cache must be fresh')
        cache.mkdir();row['cache_before']=_cache_inventory(cache)
        if dummy.exists():_fail('dummy model path exists')
        os.environ.clear();os.environ.update(childenv)
        subprocess.Popen=adapter
        try:child=oldmodel._launch_trial(dummy,spec,out,'retention' if enabled else 'original',0,nonce,parent_uuid,index,row,timeout=min(CHILD_S,_remaining(execution_deadline)))
        finally:subprocess.Popen=real_popen;os.environ.clear();os.environ.update(original_env)
        row['launch_s']=perf_counter()-started
        wait_start=perf_counter()
        try:row['exit_code']=child.wait(timeout=_remaining(execution_deadline))
        finally:row['wait_s']=perf_counter()-wait_start
        if row['exit_code']!=0:_fail('child exit failed')
    except BaseException as exc:row['error']=_detail(exc)
    finally:
        subprocess.Popen=real_popen;os.environ.clear();os.environ.update(original_env)
        if child is not None:
            try:row['cleanup_errors'].extend(oldmodel._terminate_group(child.process))
            except BaseException as exc:row['cleanup_errors'].append('group cleanup: '+_detail(exc))
            try:child.drain_available()
            except BaseException as exc:row['cleanup_errors'].append('output drain: '+_detail(exc))
            try:child.close_output();row['cleanup_errors'].extend(child.output_cleanup_errors)
            except BaseException as exc:row['cleanup_errors'].append('output close: '+_detail(exc))
        # _launch_trial owns its own error cleanup, including failures before return.
        if raw:
            process=raw[0];row.update(launcher_pid=process.pid,process_group=process.pid,exit_code=process.returncode,
                                    group_gone=_group_gone(process.pid),reaped=process.poll() is not None)
        log=out/'process.log'
        if log.is_file():
            size=log.stat().st_size
            if size<=LOG_CAP:row['log']=dict(path='process.log',nbytes=size,sha256=_sha(log.read_bytes()))
        try:
            if cache.is_dir():row['cache_after']=_cache_inventory(cache)
        except BaseException as exc:row['cleanup_errors'].append('cache inventory: '+_detail(exc))
        row['elapsed_s']=perf_counter()-started
    # A missing child ledger never establishes zero constructor attempts.
    # A bound partial ledger can narrow the initially unknown [0,1] bounds.
    path=out/'case.json'
    if path.is_file():
        try:
            partial=_read(path)
            if (partial.get('nonce')==nonce and partial.get('parent_uuid')==parent_uuid and
                partial.get('index')==index and partial.get('phase')==phase):
                for key in ('provider_attempted','provider_constructed','provider_closed','provider_lower_bound','provider_upper_bound'):
                    if key in partial:row[key]=partial[key]
        except (OSError,ValueError):pass
    try:
        if row['error'] or row['cleanup_errors'] or not row['group_gone'] or not row['reaped']:_fail('child execution/cleanup unconfirmed')
        if row['elapsed_s']>CASE_S or not row['cache_after']['files']:_fail('case deadline/cache route unconfirmed')
        data=_read(out/'case.json')
        _validate_case(out,data,row,binding)
        for key in ('provider_attempted','provider_constructed','provider_closed','provider_lower_bound','provider_upper_bound'):row[key]=data[key]
    except BaseException as exc:
        if row['error'] is None:row['error']=_detail(exc)
    row['elapsed_s']=perf_counter()-started
    if row['elapsed_s']>CASE_S and row['error'] is None:row['error']='case deadline exhausted during validation'
    return row


_members = marker._members


_cache_record = marker._cache_record


def _validate_case(root,data,launch,binding):
    _fields(data,{'schema','status','phase','index','clock_enabled','repeat','nonce','parent_pid','parent_uuid',
        'process_id','process_uuid','process_group','context','source_snapshot','runtime','request_sha256',
        'protocol','claims','limitation','provider_attempted','provider_constructed','provider_closed',
        'provider_lower_bound','provider_upper_bound','texture_markers_enabled','main_thread_id','clock_trace','markers','capture_rows','accepted','capture_count',
        'observed_reads','marker_reads','retained_payload_bytes','payload_charged_bytes','error','cleanup_errors'})
    phase=binding['phase'];index=launch['index'];enabled,repeat=SCHEDULES[phase][index]
    expected=dict(schema=CASE_SCHEMA,status='CLOCK_CAMERA_REPLAY_RECORDED',phase=phase,index=index,clock_enabled=enabled,repeat=repeat,
                  nonce=launch['nonce'],parent_pid=binding['parent_pid'],parent_uuid=binding['parent_uuid'],
                  process_group=launch['process_group'],context=binding['context'],source_snapshot=binding['source_snapshot'],
                  runtime=binding['runtime'],request_sha256=binding['request_sha256'],protocol=PROTOCOL,claims=CLAIMS,
                  limitation=LIMITATION,provider_attempted=True,provider_constructed=True,provider_closed=True,
                  provider_lower_bound=1,provider_upper_bound=1,capture_count=6,observed_reads=12,
                  marker_reads=24,texture_markers_enabled=True,error=None,cleanup_errors=[])
    for key,value in expected.items():_same(data[key],value)
    if not _positive(data['process_id']) or data['process_id'] in (data['parent_pid'],launch['launcher_pid']) or not _hex(data['process_uuid'],32):_fail('child identity invalid')
    if (type(data['retained_payload_bytes']) is not int or data['retained_payload_bytes']!=6*(capture.RAW_PAIR_BYTES+capture.CANVAS_PAIR_BYTES+capture.PACKED_BYTES) or
        type(data['payload_charged_bytes']) is not int or not 0<data['payload_charged_bytes']<=PAYLOAD_CAP):_fail('retention/storage bounds invalid')
    trace=data['clock_trace']
    try:clock.validate_clock_trace(trace)
    except clock.ClockObserverError as exc:raise ValueError('invalid bound clock trace') from exc
    _same(trace['max_pairs'],6);_same(trace['enabled'],enabled)
    if type(data['main_thread_id']) is not int or data['main_thread_id']<=0 or trace['owner_thread']!=data['main_thread_id']:_fail('clock/main-thread association mismatch')
    markers=data['markers'];attempts=data['capture_rows'];accepted=data['accepted']
    if any(type(v) is not list for v in (markers,attempts,accepted)) or (len(markers),len(attempts),len(accepted))!=(12,6,6):_fail('exact replay counts required')
    for i,row in enumerate(markers):
        _fields(row,{'call','camera','before','after','equal','raw_sha256','status','copy_attempted','copy_returned','copy_wall_s','wrapper_wall_s'})
        _same(row['call'],i+1);_same(row['camera'],CAMERAS[i%2]);_same(row['status'],'RETURNED')
        _same(row['copy_attempted'],True);_same(row['copy_returned'],True)
        _same((trace['calls'][i]['call'],trace['calls'][i]['camera']),(row['call'],row['camera']))
        if not _hex(row['raw_sha256'],64):_fail('marker raw SHA invalid')
        for key in ('copy_wall_s','wrapper_wall_s'):_duration(row[key],CHILD_S)
        if row['copy_wall_s']>row['wrapper_wall_s']:_fail('copy duration exceeds wrapper')
        if any(type(row[k]) is not int or not -(2**31)<=row[k]<2**31 for k in ('before','after')):_fail('signed generation integers required')
        _same(row['equal'],row['before']==row['after'])
    registered={'case.json','process.log'};payload_bytes=0
    def member(desc,name,image):
        nonlocal payload_bytes
        _fields(desc,{'path','nbytes','sha256','rgb_sha256'} if image else {'path','nbytes','sha256','actual_input_sha256','association'})
        if desc['path']!=name or name in registered or not _hex(desc['sha256'],64) or not _positive(desc['nbytes']):_fail('invalid payload descriptor/path')
        path=capture._safe_path(root,name)
        if not path.is_file() or path.stat().st_size!=desc['nbytes'] or desc['nbytes']>8*1024*1024:_fail('payload size mismatch')
        payload_bytes+=desc['nbytes']
        if payload_bytes>PAYLOAD_CAP:_fail('payload byte cap')
        raw=path.read_bytes()
        if _sha(raw)!=desc['sha256']:_fail('payload SHA mismatch')
        registered.add(name)
        return path
    for i,(attempt,row,pose) in enumerate(zip(attempts,accepted,POSES),1):
        _fields(attempt,{'capture_index','status','pose','raw_sha256','canvas_sha256','capture_wrapper_wall_s',
                        'capture_inclusive_wall_s','wrapper_observer_arithmetic_wall_s','raw_callback_nested_wall_s','accept_observation_wall_s'})
        _same(attempt['capture_index'],i);_same(attempt['status'],'RETURNED');_same(attempt['pose'],pose)
        for key in ('raw_sha256','canvas_sha256'):capture._hash_pair(attempt[key])
        for key in ('capture_wrapper_wall_s','capture_inclusive_wall_s','wrapper_observer_arithmetic_wall_s','raw_callback_nested_wall_s','accept_observation_wall_s'):_duration(attempt[key],CHILD_S)
        if (attempt['raw_callback_nested_wall_s']>attempt['capture_inclusive_wall_s'] or
            attempt['capture_inclusive_wall_s']>attempt['capture_wrapper_wall_s'] or
            not math.isclose(attempt['wrapper_observer_arithmetic_wall_s'],attempt['capture_wrapper_wall_s']-attempt['capture_inclusive_wall_s'],rel_tol=1e-9,abs_tol=1e-12)):_fail('capture wall association mismatch')
        _fields(row,{'accepted_index','capture_index','observation','intrinsics','raw','canvas','packed'})
        _same(row['accepted_index'],i);_same(row['capture_index'],i)
        _same(row['observation'],dict(speed_mps=8.,time_s=pose['t']))
        for key in ('raw','canvas','intrinsics'):_fields(row[key],CAMERAS)
        raw={};canvas={};intrinsics={}
        for j,kind in enumerate(CAMERAS):
            _fields(row['intrinsics'][kind],{'width','height','fx','fy','cx','cy'})
            iv=row['intrinsics'][kind]
            if (type(iv['width']) is not int or type(iv['height']) is not int or
                any(not capture._number(iv[k]) for k in ('fx','fy','cx','cy'))):_fail('typed finite intrinsics required')
            intrinsics[kind]=capture.PinholeIntrinsics(**iv)
            for boundary,w,h,target in (('raw',964,604,raw),('canvas',512,256,canvas)):
                desc=row[boundary][kind]
                frame=capture._read_png(member(desc,f'capture_{i:02d}/{boundary}_{kind}.png',True),w,h)
                if frame.sha256!=desc['rgb_sha256']:_fail('decoded RGB SHA mismatch')
                target[kind]=frame
            if (raw[kind].sha256!=attempt['raw_sha256'][kind] or raw[kind].sha256!=markers[2*(i-1)+j]['raw_sha256'] or
                canvas[kind].sha256!=attempt['canvas_sha256'][kind]):_fail('wrapper/capture/accepted raw association mismatch')
        reproduced,_=capture.PinholeRectifier().rectify_pair(
            np.frombuffer(raw['road'].rgb,np.uint8).reshape(capture.RAW_SHAPE),
            np.frombuffer(raw['wide'].rgb,np.uint8).reshape(capture.RAW_SHAPE),
            road_intrinsics=intrinsics['road'],wide_intrinsics=intrinsics['wide'])
        if any(getattr(reproduced,k).rgb!=canvas[k].rgb for k in CAMERAS):_fail('offline raw-to-canvas reconstruction mismatch')
        packed=row['packed'];path=member(packed,f'capture_{i:02d}/packed_i420.bin',False)
        if (packed['actual_input_sha256'] is not None or packed['association']!='DERIVED_ONLY_NO_MODEL_CALL' or
            packed['nbytes']!=capture.PACKED_BYTES or path.read_bytes()!=capture.camera_pair_to_model(canvas['road'],canvas['wide']).tobytes()):_fail('offline I420 reconstruction/association mismatch')
    if data['payload_charged_bytes']<payload_bytes:_fail('payload reservation below written bytes')
    members,_=_members(root,PAYLOAD_CAP+JSON_CAP+LOG_CAP)
    if members!=registered:_fail('unregistered/missing case members')
    return data


def _clock_patterns(trace):
    # Python integers retain signed differences, including signed64 endpoints.
    return [[row['snapshots'][key]['frame_count']-row['snapshots']['before_perceive']['frame_count']
             for key in clock.BOUNDARIES] for row in trace['calls']]


def _comparisons(cases):
    result=[]
    for left in range(len(cases)):
        for right in range(left+1,len(cases)):
            a,b=cases[left],cases[right]
            enabled=a['clock_enabled'] and b['clock_enabled']
            kind=('ON/ON' if enabled else 'OFF/OFF') if a['clock_enabled']==b['clock_enabled'] else 'OFF/ON'
            row=dict(left=left,right=right,kind=kind,first_raw_difference=None,first_canvas_difference=None,
                first_i420_difference=None,marker_patterns_equal=None,marker_values_equal=None,
                source_capture_hashes_equal=None,clock_count_patterns_equal=None,
                clock_absolute_counts_equal=None,clock_absolute_times_equal=None)
            for i,(ar,br) in enumerate(zip(a['accepted'],b['accepted']),1):
                for boundary in ('raw','canvas'):
                    key='first_'+boundary+'_difference'
                    for camera in CAMERAS:
                        if row[key] is None and ar[boundary][camera]['rgb_sha256']!=br[boundary][camera]['rgb_sha256']:row[key]=dict(capture=i,camera=camera)
                if row['first_i420_difference'] is None and ar['packed']['sha256']!=br['packed']['sha256']:row['first_i420_difference']=dict(capture=i)
            row['marker_patterns_equal']=[r['equal'] for r in a['markers']]==[r['equal'] for r in b['markers']]
            row['marker_values_equal']=[(r['before'],r['after']) for r in a['markers']]==[(r['before'],r['after']) for r in b['markers']]
            row['source_capture_hashes_equal']=[(r['raw_sha256'],r['canvas_sha256']) for r in a['capture_rows']]==[(r['raw_sha256'],r['canvas_sha256']) for r in b['capture_rows']]
            if enabled:
                row['clock_count_patterns_equal']=_clock_patterns(a['clock_trace'])==_clock_patterns(b['clock_trace'])
                for field,key in (('frame_count','clock_absolute_counts_equal'),('frame_time_s','clock_absolute_times_equal')):
                    row[key]=[[r['snapshots'][k][field] for k in clock.BOUNDARIES] for r in a['clock_trace']['calls']]==[[r['snapshots'][k][field] for k in clock.BOUNDARIES] for r in b['clock_trace']['calls']]
            result.append(row)
    return result


def _phase_counts(phase):
    count=len(SCHEDULES[phase]);on=sum(enabled for enabled,_ in SCHEDULES[phase])
    return dict(providers=count,accepted_pairs=6*count,observed_reads=12*count,marker_reads=24*count,
                task_step_calls=12*count,clock_snapshots=48*on,clock_getter_invocations=96*on)


def _unique_run(api,context):
    runs=api.json(f'/repos/{REPOSITORY}/actions/workflows/{context["workflow_id"]}/runs?event=push&head_sha={context["head_sha"]}&per_page=100')
    if type(runs.get('total_count')) is not int or runs['total_count']!=1 or type(runs.get('workflow_runs')) is not list or len(runs['workflow_runs'])!=1 or _run_context(runs['workflow_runs'][0])!=context:_fail('head already has another workflow run')


_extract = marker._extract


def _gate(api,context,snapshot,runtime,request,deadline):
    a=request['acceptance'];_request_data(request)
    _unique_run(api,context);_remaining(deadline)
    run=api.json(f'/repos/{REPOSITORY}/actions/runs/{a["run_id"]}');accepted=_run_context(run)
    if (run.get('status')!='completed' or run.get('conclusion')!='success' or accepted['head_sha']!=a['source_sha'] or
        accepted['run_id']!=a['run_id'] or accepted['workflow_id']!=a['workflow_id'] or accepted['workflow_id']!=context['workflow_id']):_fail('accepted API run mismatch')
    commit=api.json(f'/repos/{REPOSITORY}/commits/{context["head_sha"]}')
    parents=commit.get('parents');files=commit.get('files')
    if (commit.get('sha')!=context['head_sha'] or type(parents) is not list or len(parents)!=1 or parents[0].get('sha')!=a['source_sha'] or
        _git('rev-list','--parents','-n','1','HEAD',deadline=deadline).decode().split()!=[context['head_sha'],a['source_sha']]):_fail('activation must be direct child of accepted source')
    _same(_request_data(_json(_git('show',a['source_sha']+':'+REQUEST,deadline=deadline))),dict(schema=REQUEST_SCHEMA,mode='canary',acceptance=None))
    if type(files) is not list or not files or len(files)>=300:_fail('activation changed-path list missing/truncated')
    changed={r.get('filename') for r in files}
    actual=set(_git('diff-tree','--no-commit-id','--name-only','-r',context['head_sha'],deadline=deadline).decode().splitlines())
    allowed={REQUEST,'.github/stage7-engine-clock-acceptance.json'}
    if (changed!=actual or REQUEST not in changed or any(type(name) is not str or (name not in allowed and not name.startswith('docs/')) for name in changed) or
        any(r.get('status') not in ('added','modified') or r.get('previous_filename') for r in files)):_fail('activation edited producer/runtime paths')
    for name,digest in snapshot.items():
        if _sha(_git('show',a['source_sha']+':'+name,deadline=deadline))!=digest:_fail('accepted source70 bytes differ')
    artifact=api.json(f'/repos/{REPOSITORY}/actions/artifacts/{a["artifact_id"]}')
    wr=artifact.get('workflow_run',{})
    if (artifact.get('id')!=a['artifact_id'] or artifact.get('name')!=a['artifact_name'] or artifact.get('expired') is not False or
        artifact.get('size_in_bytes')!=a['artifact_size_bytes'] or artifact.get('digest')!='sha256:'+a['artifact_sha256'] or
        wr.get('id')!=a['run_id'] or wr.get('head_sha')!=a['source_sha'] or wr.get('head_branch')!=BRANCH or
        (wr.get('repository_id') is not None and wr.get('repository_id')!=run.get('repository',{}).get('id'))):_fail('actual artifact API association/size/digest mismatch')
    _remaining(deadline)
    archive=api.download(f'/repos/{REPOSITORY}/actions/artifacts/{a["artifact_id"]}/zip',a['artifact_size_bytes'])
    if len(archive)!=a['artifact_size_bytes'] or _sha(archive)!=a['artifact_sha256']:_fail('original artifact ZIP size/digest mismatch')
    with tempfile.TemporaryDirectory(prefix='engine-clock-acceptance-',dir=os.environ['RUNNER_TEMP']) as temp:
        extracted=Path(temp)/'canary';_extract(archive,extracted)
        result=validate_dataset(extracted)
        data=_read(extracted/'phase.json')
        if data['phase']!='canary' or data['context']!=accepted or data['source_snapshot']!=snapshot or data['runtime']!=runtime:_fail('accepted raw dataset context/source/runtime mismatch')
        _remaining(deadline)
    return dict(schema='engine-clock-acceptance-v1',accepted_context=accepted,acceptance=a,
                accepted_dataset_status=result['status'],source_snapshot=snapshot,runtime=runtime)


def _context_record(value):
    _fields(value,{'repository','workflow_path','workflow_id','head_sha','run_id','attempt','event','branch'})
    expected=dict(repository=REPOSITORY,workflow_path=WORKFLOW,event='push',branch=BRANCH,attempt=1)
    for key,exp in expected.items():_same(value[key],exp)
    if not _hex(value['head_sha'],40) or not _positive(value['workflow_id']) or not _positive(value['run_id']):_fail('context counters/head invalid')


def _validate_dataset(root,data,*,manifest_present):
    root=Path(root);members,_=_members(root)
    if not manifest_present:members.add('phase.json')
    _fields(data,{'schema','status','phase','parent_pid','parent_uuid','context','source_snapshot','runtime',
        'request_blob','request_sha256','protocol','claims','limitation','acceptance','launches','comparisons',
        'providers','accepted_pairs','observed_reads','marker_reads','task_step_calls','clock_snapshots','clock_getter_invocations','elapsed_s','error','cleanup_errors'})
    if data['schema']!=SCHEMA or data['status']!='CLOCK_DATASET_VALIDATED' or data['phase'] not in SCHEDULES:_fail('unknown/incomplete marker dataset')
    phase=data['phase'];_context_record(data['context']);_check_runtime(data['runtime'])
    _same(data['source_snapshot'],source_snapshot());_same(data['protocol'],PROTOCOL);_same(data['claims'],CLAIMS)
    _same(data['limitation'],LIMITATION)
    if not _positive(data['parent_pid']) or not _hex(data['parent_uuid'],32):_fail('root process identity invalid')
    request=_request_data(_json(data['request_blob'].encode()))
    if request['mode']!=phase or _sha(data['request_blob'].encode())!=data['request_sha256']:_fail('request provenance mismatch')
    if phase=='canary':
        if data['acceptance'] is not None:_fail('canary acceptance must be null')
    else:
        gate=data['acceptance'];_fields(gate,{'schema','accepted_context','acceptance','accepted_dataset_status','source_snapshot','runtime'})
        _context_record(gate['accepted_context'])
        if (gate['schema']!='engine-clock-acceptance-v1' or gate['acceptance']!=request['acceptance'] or gate['accepted_dataset_status']!='CLOCK_DATASET_VALIDATED' or
            gate['source_snapshot']!=data['source_snapshot'] or gate['runtime']!=data['runtime'] or
            gate['accepted_context']!={**data['context'],'head_sha':request['acceptance']['source_sha'],'run_id':request['acceptance']['run_id']} or
            gate['accepted_context']['workflow_id']!=request['acceptance']['workflow_id']):_fail('ABBA acceptance receipt mismatch')
    _same(data['error'],None);_same(data['cleanup_errors'],[]);_duration(data['elapsed_s'],PHASE_S)
    count=len(SCHEDULES[phase])
    for key,expected in _phase_counts(phase).items():_same(data[key],expected)
    launches=data['launches']
    if type(launches) is not list or len(launches)!=count:_fail('exact phase case count required')
    binding={k:data[k] for k in ('phase','parent_pid','parent_uuid','context','source_snapshot','runtime','request_sha256')}
    cases=[];pids={data['parent_pid']};uuids={data['parent_uuid']};nonces=set();caches=set();registered={'phase.json'}
    for index,launch in enumerate(launches):
        _fields(launch,{'index','clock_enabled','nonce','attempted','launched','launcher_pid','process_group','exit_code','cleanup_errors','error',
            'group_gone','reaped','provider_lower_bound','provider_upper_bound','provider_attempted','provider_constructed','provider_closed',
            'storage','cache_path','cache_before','cache_after','launch_s','wait_s','elapsed_s','log'})
        for key,expected in dict(index=index,clock_enabled=SCHEDULES[phase][index][0],attempted=True,launched=True,exit_code=0,
            cleanup_errors=[],error=None,group_gone=True,reaped=True,provider_lower_bound=1,provider_upper_bound=1,
            provider_attempted=True,provider_constructed=True,provider_closed=True).items():_same(launch[key],expected)
        if not _hex(launch['nonce'],64) or launch['nonce'] in nonces:_fail('duplicated/invalid nonce')
        nonces.add(launch['nonce'])
        if not _positive(launch['launcher_pid']) or launch['launcher_pid'] in pids or launch['process_group']!=launch['launcher_pid']:_fail('duplicated/invalid launcher identity')
        pids.add(launch['launcher_pid'])
        for key,limit in (('launch_s',CHILD_S),('wait_s',CHILD_S),('elapsed_s',CASE_S)):_duration(launch[key],limit)
        if launch['launch_s']+launch['wait_s']>CHILD_S or launch['launch_s']+launch['wait_s']>launch['elapsed_s']+1e-9:_fail('launch/wait deadline accounting mismatch')
        storage=launch['storage'];_fields(storage,set(LIMITS)|{'log_bytes','limit_error'})
        for key,value in LIMITS.items():_same(storage[key],value)
        _same(storage['limit_error'],None)
        if type(storage['log_bytes']) is not int or not 0<storage['log_bytes']<=LOG_CAP:_fail('invalid bounded process log bytes')
        _cache_record(launch['cache_before'],empty=True);_cache_record(launch['cache_after'],empty=False)
        cache=Path(launch['cache_path'])
        if not cache.is_absolute() or cache.name!='engine-clock-cache-'+data['parent_uuid']+f'-{index:02d}' or str(cache) in caches or root==cache or root in cache.parents:_fail('cache path/freshness invalid')
        caches.add(str(cache))
        case_root=root/f'case_{index:02d}';case=_read(capture._safe_path(case_root,'case.json'))
        _validate_case(case_root,case,launch,binding)
        if case['process_id'] in pids or case['process_uuid'] in uuids:_fail('duplicate child identity')
        pids.add(case['process_id']);uuids.add(case['process_uuid']);cases.append(case)
        log=launch['log'];_fields(log,{'path','nbytes','sha256'})
        _same(log['path'],'process.log');_same(log['nbytes'],storage['log_bytes'])
        path=case_root/'process.log'
        if path.stat().st_size!=log['nbytes'] or _sha(path.read_bytes())!=log['sha256']:_fail('bounded log descriptor mismatch')
        text=path.read_bytes()
        if not text.startswith(b'authorization_fd=') or b' phase=prepared\n' not in text or f'phase=permit launcher_pid={launch["launcher_pid"]}\n'.encode() not in text or b'phase=permit_sent\n' not in text:_fail('launcher log association missing')
        names,_=_members(case_root);registered.update(f'case_{index:02d}/'+name for name in names)
    if members!=registered or len(members)!=1+32*count:_fail('exact phase allowed members mismatch')
    comparisons=_comparisons(cases);_same(data['comparisons'],comparisons)
    return dict(status='CLOCK_DATASET_VALIDATED',phase=phase,**_phase_counts(phase),comparisons=comparisons,claims=CLAIMS)


def validate_dataset(root):
    """Pure CPU/disk validation; never constructs a provider or queries GitHub."""
    root=Path(root)
    return _validate_dataset(root,_read(capture._safe_path(root,'phase.json')),manifest_present=True)


def run_phase(out):
    started=perf_counter();deadline=started+PHASE_S
    # A syntactically registered phase is sufficient only to name its failure
    # evidence. Context/source/runtime remain unconfirmed until all gates pass.
    raw=(REPO/REQUEST).read_bytes();request=_request_bytes(raw)
    phase=request['mode'];out=_output(Path(out),phase);out.mkdir(parents=True)
    data=dict(schema=SCHEMA,status='FAILED_OR_INCOMPLETE',phase=phase,parent_pid=os.getpid(),parent_uuid=uuid.uuid4().hex,
              context=None,source_snapshot=None,runtime=None,request_blob=raw.decode(),
              request_sha256=_sha(raw),protocol=PROTOCOL,claims=CLAIMS,limitation=LIMITATION,acceptance=None,
              launches=[],comparisons=[],**dict.fromkeys(_phase_counts(phase)),
              elapsed_s=0.,error=None,cleanup_errors=[],failure_stage='context')
    stage='context'
    try:
        api=_DeadlineAPI(oldmodel._github(),deadline-30.)
        context,snapshot,request,request_sha=_context(api,deadline-30.)
        if request['mode']!=phase:_fail('registered phase changed during admission')
        data.update(context=context,source_snapshot=snapshot,request_sha256=request_sha)
        stage='runtime';runtime=_runtime();data['runtime']=runtime
        stage='unique_run';_unique_run(api,context)
        binding={k:data[k] for k in ('phase','parent_pid','parent_uuid','context','source_snapshot','runtime','request_sha256')};binding['root']=str(out)
        stage='subreaper';oldmodel._enable_subreaper()
        stage='acceptance'
        if phase=='abba':data['acceptance']=_gate(api,context,snapshot,runtime,request,deadline)
        for index in range(len(SCHEDULES[phase])):
            stage=f'case_{index:02d}';_remaining(deadline)
            row=_case(out/f'case_{index:02d}',phase,index,data['parent_uuid'],binding,deadline)
            data['launches'].append(row)
            if row['error']:_fail(row['error'])
            _members(out)
        stage='dataset_validation'
        cases=[_read(out/f'case_{index:02d}'/'case.json') for index in range(len(SCHEDULES[phase]))]
        data.update(_phase_counts(phase));data['comparisons']=_comparisons(cases)
        data['status']='CLOCK_DATASET_VALIDATED';data.pop('failure_stage')
        data['elapsed_s']=perf_counter()-started
        _validate_dataset(out,data,manifest_present=False)
    except BaseException as exc:
        data['error']=_detail(exc);data['status']='FAILED_OR_INCOMPLETE';data['failure_stage']=stage
        for key in _phase_counts(phase):data[key]=None
    data['elapsed_s']=perf_counter()-started
    if data['elapsed_s']>PHASE_S:
        data['status']='FAILED_OR_INCOMPLETE';data['error']=data['error'] or 'phase deadline exhausted';data['failure_stage']=stage
        for key in _phase_counts(phase):data[key]=None
    _write(out/'phase.json',data)
    return data


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    for name in ('run','child','validate'):
        command=commands.add_parser(name);command.add_argument('--out' if name!='validate' else '--root',type=Path,required=True)
        if name=='child':
            command.add_argument('--phase',choices=SCHEDULES,required=True);command.add_argument('--index',type=int,required=True);command.add_argument('--nonce',required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='validate':result=validate_dataset(args.root)
        elif args.command=='run':result=run_phase(args.out)
        else:result=run_child(args.out,args.phase,args.index,args.nonce)
    except Exception as exc:
        print(json.dumps(dict(status='FAILED_OR_INCOMPLETE',error=_detail(exc),claims=CLAIMS),allow_nan=False))
        return 1
    print(json.dumps(dict(status=result['status'],claims=CLAIMS),allow_nan=False))
    return 0 if result['status'] in ('CLOCK_DATASET_VALIDATED','CLOCK_CAMERA_REPLAY_RECORDED') else 1


if __name__=='__main__':raise SystemExit(main())
