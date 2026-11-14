"""CPU call boundaries and submitted source locals, never GPU state or admission."""
from contextlib import contextmanager
from copy import deepcopy
import json
import sys
import threading
from types import MethodType
from scripts import renderer_task_callbacks as cb

SCHEMA='renderer-pipeline-calls-v1'
TRACE_CAP=512*1024
PY=('PSSM.update','MainCamera._chase_task','igLoop','road_ram','wide_ram')
C=('shader_inputs','render_frame','road_image_as','wide_image_as')
COUNTS=('step_attempts','step_returns','ram_attempts','ram_returns','rig_attempts','rig_returns',
        'submission_attempts','submission_returns','profile_installs')
_ACTIVE=None

class PipelineError(RuntimeError):pass

def _remember(t,exc):
    if t['error'] is None:
        try:message=str(exc)
        except BaseException:message='<unprintable>'
        t['error']=type(exc).__name__+': '+message[:256]
    t['status']='FAILED_OR_INCOMPLETE'

def matrix_state(raw):
    if type(raw) is not dict or set(raw)!={'matrices'}:raise PipelineError('submitted matrix fields required')
    try:s=cb._state(dict(pose=dict(xyz_m=[0.,0.,0.],hpr_deg=[0.,0.,0.]),matrices=raw['matrices'],chase_run_task=False))
    except cb.CallbackBoundaryError as exc:raise PipelineError(str(exc)) from exc
    return dict(matrices=s['matrices'],mvp_sha256=s['mvp_sha256'])

def _state_valid(e):
    state=e['state'];name=e['callback']
    if name in cb.CALLBACKS:
        try:expected=cb._state({k:state[k] for k in ('pose','matrices','chase_run_task')})
        except (TypeError,KeyError,cb.CallbackBoundaryError) as exc:raise PipelineError('invalid callback state') from exc
        if expected!=state:raise PipelineError('callback digest mismatch')
    elif name=='shader_inputs':
        if type(state) is not dict or set(state)!={'matrices','mvp_sha256'} or matrix_state(dict(matrices=state['matrices']))!=state:
            raise PipelineError('submitted matrix digest mismatch')
    elif state is not None:raise PipelineError('unmeasured state must be null')

def _validate_events(events,ram=False):
    if type(events) is not list or len(events)!=(4 if ram else 10):raise PipelineError('complete bounded events required')
    for i,e in enumerate(events,1):
        if (type(e) is not dict or set(e)!={'index','event','callback','state','return_value','lineno','local_identity_matched'} or
            type(e['index']) is not int or e['index']!=i or type(e['lineno']) is not int or e['lineno']<=0):
            raise PipelineError('typed event association required')
        _state_valid(e)
        if e['callback']=='shader_inputs':
            if e['local_identity_matched'] is not True:raise PipelineError('submitted local identity required')
        elif e['local_identity_matched'] is not None:raise PipelineError('unobserved local identity must be null')
        if e['event']=='return':
            want='NON_NULL_OBJECT' if e['callback']=='RAM.method' else 1
            if type(e['return_value']) is not type(want) or e['return_value']!=want:raise PipelineError('normal Python return required')
        elif e['return_value'] is not None:raise PipelineError('C profile events do not expose result values')
    actual=[(e['event'],e['callback']) for e in events]
    if ram:
        if actual!=[('call','RAM.method'),('c_call','RAM.image_as'),('c_return','RAM.image_as'),('return','RAM.method')]:
            raise PipelineError('original RAM call nesting required')
    else:
        sections={'PSSM.update':[('call','PSSM.update'),('c_call','shader_inputs'),('c_return','shader_inputs'),('return','PSSM.update')],
            'MainCamera._chase_task':[('call','MainCamera._chase_task'),('return','MainCamera._chase_task')],
            'igLoop':[('call','igLoop'),('c_call','render_frame'),('c_return','render_frame'),('return','igLoop')]}
        pos=0;seen=set()
        while pos<len(actual):
            kind=actual[pos][1]
            if kind not in sections or kind in seen:raise PipelineError('distinct nonoverlapping Python callbacks required')
            seq=sections[kind]
            if actual[pos:pos+len(seq)]!=seq:raise PipelineError('original C call nesting incomplete')
            seen.add(kind);pos+=len(seq)
        if seen!=set(sections):raise PipelineError('missing Python callback')

def validate_trace(t):
    fields={'schema','status','enabled','max_pairs','task_continue','owner_thread','steps','counts',
            'restoration_complete','restoration_errors','error','body_error'}
    if type(t) is not dict or set(t)!=fields:raise PipelineError('exact trace schema required')
    if (t['schema']!=SCHEMA or t['status']!='CPU_PIPELINE_TRACE_COMPLETE' or type(t['enabled']) is not bool or
        type(t['max_pairs']) is not int or not 1<=t['max_pairs']<=6 or type(t['task_continue']) is not int or t['task_continue']!=1 or
        type(t['owner_thread']) is not int or t['owner_thread']<=0 or t['restoration_complete'] is not True or
        t['restoration_errors']!=[] or t['error'] is not None or t['body_error'] is not None):raise PipelineError('complete restored trace required')
    count=2*t['max_pairs'];on=t['enabled'];reads=count if on else 0
    want=dict(step_attempts=count,step_returns=count,ram_attempts=count,ram_returns=count,
        rig_attempts=4*reads,rig_returns=4*reads,submission_attempts=2*reads,submission_returns=2*reads,profile_installs=2*reads)
    if type(t['counts']) is not dict or set(t['counts'])!=set(want) or any(type(t['counts'][k]) is not int or t['counts'][k]!=v for k,v in want.items()):
        raise PipelineError('exact scoped operation budgets required')
    if type(t['steps']) is not list or len(t['steps'])!=count:raise PipelineError('complete camera steps required')
    for i,s in enumerate(t['steps'],1):
        if (type(s) is not dict or set(s)!={'call','camera','step_returned','ram_returned','result_identity_matched','events','ram_events'} or
            type(s['call']) is not int or s['call']!=i or s['camera']!=('road','wide')[(i-1)%2] or
            s['step_returned'] is not True or s['ram_returned'] is not True or s['result_identity_matched'] is not True):
            raise PipelineError('complete original method returns required')
        if on:_validate_events(s['events']);_validate_events(s['ram_events'],True)
        elif s['events'] is not None or s['ram_events'] is not None:raise PipelineError('OFF evidence is null/unobserved')
    if len(json.dumps(t,allow_nan=False).encode())>TRACE_CAP:raise PipelineError('pipeline trace cap')
    return dict(status='CPU_PIPELINE_METADATA_VALIDATED',original_steps=count,original_ram_methods=count,
        observed_pipeline_events=14*count if on else None,gpu_completion_proven=False,gpu_uniforms_observed=False,
        submitted_cpu_source_locals_only=True,native_execution_proven=False)

def project_callbacks(t):
    rows=[]
    for s in t['steps']:
        events=None
        if t['enabled']:
            events=[]
            for e in s['events']:
                if e['callback'] in cb.CALLBACKS:
                    events.append(dict(index=len(events)+1,callback=e['callback'],event=e['event'],state=deepcopy(e['state']),return_value=e['return_value']))
        rows.append(dict(call=s['call'],camera=s['camera'],status='RETURNED' if s['step_returned'] else 'FAILED_OR_INCOMPLETE',original_returned=s['step_returned'],events=events))
    c=t['counts']
    return dict(schema='renderer-task-callbacks-v1',status='CPU_CALLBACK_TRACE_COMPLETE' if t['status']=='CPU_PIPELINE_TRACE_COMPLETE' else 'FAILED_OR_INCOMPLETE',
        enabled=t['enabled'],max_pairs=t['max_pairs'],owner_thread=t['owner_thread'],task_continue=t['task_continue'],steps=rows,
        step_attempts=c['step_attempts'],step_returns=c['step_returns'],snapshot_attempts=c['rig_attempts'],snapshot_returns=c['rig_returns'],
        restoration_complete=t['restoration_complete'],restoration_errors=list(t['restoration_errors']),error=t['error'],body_error=t['body_error'])

@contextmanager
def pipeline_scope(manager,sensors,enabled,trace,*,clock_trace,binding=None,max_pairs=6):
    global _ACTIVE
    if _ACTIVE is not None:
        exc=PipelineError('nested pipeline scope');_remember(_ACTIVE,exc);raise exc
    if (type(enabled) is not bool or type(trace) is not dict or trace or type(clock_trace) is not dict or
        type(max_pairs) is not int or not 1<=max_pairs<=6):raise PipelineError('fresh typed bounded configuration required')
    if sys.getprofile() is not None:raise PipelineError('existing profile must be preserved')
    if enabled:
        if (type(binding) is not dict or set(binding.get('python',{}))!=set(PY) or set(binding.get('c',{}))!=set(C) or
            any(type(v) is not MethodType for v in binding['python'].values()) or
            any(not callable(v) or getattr(v,'__self__',None) is None or type(getattr(v,'__name__',None)) is not str for v in binding['c'].values()) or
            not callable(binding.get('snapshot')) or not callable(binding.get('submission'))):raise PipelineError('exact bound Python/C targets and readers required')
        py=[(name,v.__func__.__code__,v.__self__) for name,v in binding['python'].items()]
        known={code for _,code,_ in py};ctargets=dict(binding['c'])
    elif binding is not None:raise PipelineError('OFF must not bind owners/readers')
    trace.update(schema=SCHEMA,status='FAILED_OR_INCOMPLETE',enabled=enabled,max_pairs=max_pairs,task_continue=1,
        owner_thread=threading.get_ident(),steps=[],counts={k:0 for k in COUNTS},restoration_complete=False,restoration_errors=[],error=None,body_error=None)
    _ACTIVE=trace;originals=[];active=None;stage=None;pyframe=None;pyname=None;cframe=None;cname=None;local=None;ram_result=None;primary=None
    def reject(message):
        exc=PipelineError(message);_remember(trace,exc);raise exc
    def guard():
        if threading.get_ident()!=trace['owner_thread']:reject('one profile owner thread required')
        if trace['error'] is not None:reject('pipeline observer already failed')
    def append(event,name,state,frame,ret=None,identity=None):
        events=active['ram_events'] if stage=='ram' else active['events'];cap=4 if stage=='ram' else 10
        if len(events)>=cap:reject('event budget exhausted')
        events.append(dict(index=len(events)+1,event=event,callback=name,state=state,return_value=ret,lineno=frame.f_lineno,local_identity_matched=identity))
    def profile(frame,event,arg):
        nonlocal pyframe,pyname,cframe,cname,local,ram_result
        if frame.f_code not in known or trace['error'] is not None:return
        if event not in ('call','return','c_call','c_return','c_exception'):return
        try:
            guard();matches=[name for name,code,owner in py if frame.f_code is code and frame.f_locals.get('self') is owner]
            if len(matches)!=1:reject('foreign or ambiguous Python owner')
            name=matches[0]
            expected=('road_ram' if active['camera']=='road' else 'wide_ram') if stage=='ram' else None
            if (stage=='ram' and name!=expected) or (stage=='step' and name not in PY[:3]):reject('wrong method/camera stage')
            label='RAM.method' if stage=='ram' else name
            if event in ('call','return'):
                if event=='call':
                    if pyframe is not None:reject('nested Python target')
                    pyframe,pyname=frame,name
                elif pyframe is not frame or pyname!=name or cframe is not None:reject('unpaired Python return')
                if event=='return':
                    if stage=='ram':
                        if arg is None:reject('RAM unwind or null result')
                        ram_result=arg;ret='NON_NULL_OBJECT'
                    else:
                        if type(arg) is not int or arg!=1:reject('unwind or non-task.cont return')
                        ret=arg
                else:ret=None
                s=None
                if name in cb.CALLBACKS:
                    if trace['counts']['rig_attempts']>=8*max_pairs:reject('rig snapshot budget')
                    trace['counts']['rig_attempts']+=1;s=cb._state(binding['snapshot']());trace['counts']['rig_returns']+=1
                append(event,label,s,frame,ret)
                if event=='return':pyframe=pyname=None
                return
            key='shader_inputs' if name=='PSSM.update' else 'render_frame' if name=='igLoop' else active['camera']+'_image_as' if stage=='ram' else None
            if key is None:return
            target=ctargets[key]
            if getattr(arg,'__name__',None)!=target.__name__ or getattr(arg,'__self__',None) is not target.__self__:return
            if pyframe is not frame or pyname!=name:reject('C target outside original Python frame')
            expected_line=binding.get('lines',{}).get(key)
            if expected_line is not None and frame.f_lineno!=expected_line:reject('pinned C-call source line changed')
            label='RAM.image_as' if stage=='ram' else key
            if event=='c_call':
                if cframe is not None:reject('nested targeted C call')
                cframe,cname=frame,key
                if key=='shader_inputs':
                    if 'mvp_array' not in frame.f_locals:reject('missing submitted source local')
                    local=frame.f_locals['mvp_array']
            elif cframe is not frame or cname!=key:reject('unpaired C return')
            if event=='c_exception':
                append(event,label,None,frame)
                reject('original C call raised')
            s=None;ident=None
            if key=='shader_inputs':
                if frame.f_locals.get('mvp_array') is not local:reject('source local identity changed across C call')
                if trace['counts']['submission_attempts']>=4*max_pairs:reject('submitted snapshot budget')
                trace['counts']['submission_attempts']+=1;s=matrix_state(binding['submission'](local));trace['counts']['submission_returns']+=1;ident=True
            append(event,label,s,frame,identity=ident)
            if event=='c_return':cframe=cname=local=None
        except (KeyboardInterrupt,SystemExit,TimeoutError) as exc:_remember(trace,exc);raise
        except BaseException as exc:_remember(trace,exc)
    def bound_row(kind):
        calls=clock_trace.get('calls')
        if type(calls) is not list or not calls or type(calls[-1]) is not dict:reject('typed active clock call required')
        b=calls[-1];number=len(trace['steps'])+1 if kind=='step' else len(trace['steps'])
        if (type(b.get('call')) is not int or b['call']!=number or type(b.get('camera')) is not str or
            b['camera']!=('road','wide')[(number-1)%2]):reject('active camera association mismatch')
        if kind=='step':
            if b.get('task_step_attempted') is not True or b.get('task_step_returned') is not False or b.get('ram_attempted') is not False:reject('wrong step entry boundary')
        elif b.get('task_step_returned') is not True or b.get('ram_attempted') is not True or b.get('ram_returned') is not False:reject('wrong RAM entry boundary')
        return b
    def invoke(kind,original,args,kwargs,camera=None):
        nonlocal active,stage,pyframe,pyname,cframe,cname,local,ram_result
        guard()
        if active is not None:reject('nested original method')
        b=bound_row(kind)
        if kind=='step':
            if len(trace['steps'])>=2*max_pairs or (trace['steps'] and not trace['steps'][-1]['ram_returned']):reject('step budget or missing prior RAM')
            row=dict(call=b['call'],camera=b['camera'],step_returned=False,ram_returned=False,result_identity_matched=False,events=[] if enabled else None,ram_events=[] if enabled else None);trace['steps'].append(row)
        else:
            if not trace['steps']:reject('orphan RAM')
            row=trace['steps'][-1]
            if row['camera']!=camera or row['ram_returned']:reject('wrong or duplicate RAM')
        if sys.getprofile() is not None:reject('profile hook changed before original call')
        active=row;stage=kind;pyframe=pyname=cframe=cname=local=ram_result=None
        try:
            if enabled:sys.setprofile(profile);trace['counts']['profile_installs']+=1
            trace['counts'][kind+'_attempts']+=1;result=original(*args,**kwargs)
            row[kind+'_returned']=True;trace['counts'][kind+'_returns']+=1
            if enabled and sys.getprofile() is not profile:reject('profile hook disappeared/replaced')
            guard()
            if enabled:_validate_events(row['ram_events'] if kind=='ram' else row['events'],kind=='ram')
            if kind=='ram':
                if enabled and result is not ram_result:reject('RAM Python return identity changed')
                row['result_identity_matched']=True
            return result
        except BaseException as exc:_remember(trace,exc);raise
        finally:
            if enabled:sys.setprofile(None)
            active=stage=pyframe=pyname=cframe=cname=local=ram_result=None
    def install(obj,name,value):
        originals.append((obj,name,name in vars(obj),vars(obj).get(name)));setattr(obj,name,value)
    try:
        original_step=manager.step
        def step(*args,**kwargs):return invoke('step',original_step,args,kwargs)
        install(manager,'step',step)
        def ram_wrapper(camera,original):
            def ram(*args,**kwargs):return invoke('ram',original,args,kwargs,camera)
            return ram
        for camera in ('road','wide'):
            sensor=sensors['bigbench_'+camera];install(sensor,'get_rgb_array_cpu',ram_wrapper(camera,sensor.get_rgb_array_cpu))
        try:yield trace
        except BaseException as exc:trace['body_error']=type(exc).__name__;raise
    except BaseException as exc:primary=exc;_remember(trace,exc);raise
    finally:
        for obj,name,own,saved in reversed(originals):
            try:
                if own:
                    if vars(obj).get(name) is not saved:setattr(obj,name,saved)
                    if vars(obj).get(name) is not saved:raise PipelineError('own attribute not restored')
                else:
                    if name in vars(obj):delattr(obj,name)
                    if name in vars(obj):raise PipelineError('inherited attribute not restored')
            except BaseException as exc:trace['restoration_errors'].append(name+':'+type(exc).__name__)
        trace['restoration_complete']=not trace['restoration_errors'];_ACTIVE=None
        if primary is None:
            if trace['error'] is not None or trace['restoration_errors']:reject('pipeline failure or incomplete restoration')
            trace['status']='CPU_PIPELINE_TRACE_COMPLETE'
            try:validate_trace(trace)
            except BaseException as exc:_remember(trace,exc);raise
        elif trace['restoration_errors']:primary.add_note('pipeline attribute restoration incomplete')
