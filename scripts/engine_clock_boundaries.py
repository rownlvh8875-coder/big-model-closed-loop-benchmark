"""CPU method-boundary observer, not native admission or a GPU frame probe.

No graphics imports, clock construction/setters, extra steps/copies, or I/O.
The future caller must bind this trace to its independently admitted provider.
"""
from contextlib import contextmanager
import json
import math
import threading

SCHEMA='engine-clock-boundaries-v1'
TRACE_CAP=64*1024
CAMERAS=('road','wide')
BOUNDARIES=('before_perceive','before_ram_method','after_ram_method','after_perceive')
EVENTS=('perceive_enter','task_step_enter','task_step_return','ram_enter','ram_return','perceive_return')
KINDS=('perceive','task_step','ram','clock_snapshot','frame_count','frame_time')
_ACTIVE=None


class ClockObserverError(RuntimeError):
    pass


def _detail(exc):
    try:message=str(exc)
    except BaseException:message='<unprintable exception>'
    return type(exc).__name__+': '+message[:256]


def _remember(trace,exc):
    if trace['error'] is None:trace['error']=_detail(exc)
    trace['status']='FAILED_OR_INCOMPLETE'


def _fields(value,keys):
    if type(value) is not dict or set(value)!=set(keys):raise ClockObserverError('trace schema mismatch')


def _clock_values(count,time):
    if type(count) is not int or not -(2**63)<=count<2**63:
        raise ClockObserverError('frame count must be a signed64 integer')
    if type(time) is not float or not math.isfinite(time):
        raise ClockObserverError('frame time must be a finite float')


def validate_clock_trace(trace):
    """Validate complete CPU metadata only; a synthetic provider can also pass."""
    _fields(trace,{'schema','status','enabled','max_pairs','clock_owner','clock_binding_observed',
        'owner_thread','calls','events','counts','restoration_complete','restoration_errors','error','body_error'})
    if (trace['schema']!=SCHEMA or trace['status']!='CLOCK_BOUNDARY_TRACE_RECORDED' or
        type(trace['enabled']) is not bool or type(trace['max_pairs']) is not int or
        not 1<=trace['max_pairs']<=6 or type(trace['owner_thread']) is not int or trace['owner_thread']<=0 or
        trace['clock_owner']!='engine.taskMgr.globalClock' or
        type(trace['clock_binding_observed']) is not bool or trace['clock_binding_observed']!=trace['enabled'] or
        trace['restoration_complete'] is not True or trace['restoration_errors']!=[] or
        trace['error'] is not None or trace['body_error'] is not None):
        raise ClockObserverError('complete restored trace required')
    count=2*trace['max_pairs'];reads=4*count if trace['enabled'] else 0
    expected={kind+'_'+state:(count if kind in ('perceive','task_step','ram') else reads)
              for kind in KINDS for state in ('attempts','returns')}
    _fields(trace['counts'],expected)
    if any(type(trace['counts'][k]) is not int or trace['counts'][k]!=v for k,v in expected.items()):
        raise ClockObserverError('exact observer attempt/return counters required')
    calls,events=trace['calls'],trace['events']
    if type(calls) is not list or len(calls)!=count or type(events) is not list or len(events)!=6*count:
        raise ClockObserverError('complete bounded call/event sequence required')
    for i,row in enumerate(calls):
        flags={kind+'_'+state for kind in ('perceive','task_step','ram') for state in ('attempted','returned')}
        _fields(row,{'call','camera','status','snapshots'}|flags)
        if (type(row['call']) is not int or row['call']!=i+1 or row['camera']!=CAMERAS[i%2] or
            row['status']!='RETURNED' or any(row[k] is not True for k in flags)):
            raise ClockObserverError('original method association incomplete')
        _fields(row['snapshots'],BOUNDARIES)
        for offset,event in enumerate(EVENTS):
            actual=events[6*i+offset]
            _fields(actual,{'index','event','call','camera'})
            expected_event=dict(index=6*i+offset+1,event=event,call=i+1,camera=CAMERAS[i%2])
            if actual!=expected_event or type(actual['index']) is not int or type(actual['call']) is not int:
                raise ClockObserverError('original method event order mismatch')
        for boundary,offset in zip(BOUNDARIES,(1,4,5,6)):
            snap=row['snapshots'][boundary]
            if not trace['enabled']:
                if snap is not None:raise ClockObserverError('OFF clock snapshot is unobserved/null')
                continue
            _fields(snap,{'event_index','frame_count','frame_time_s','frame_count_attempted','frame_count_returned',
                          'frame_time_attempted','frame_time_returned','error'})
            if (type(snap['event_index']) is not int or snap['event_index']!=6*i+offset or snap['error'] is not None or
                any(snap[k] is not True for k in ('frame_count_attempted','frame_count_returned','frame_time_attempted','frame_time_returned'))):
                raise ClockObserverError('snapshot boundary/read association mismatch')
            _clock_values(snap['frame_count'],snap['frame_time_s'])
    try:encoded=json.dumps(trace,allow_nan=False).encode()
    except (ValueError,TypeError) as exc:raise ClockObserverError('trace must be finite JSON metadata') from exc
    if len(encoded)>TRACE_CAP:raise ClockObserverError('trace byte cap')
    return dict(status='CPU_BOUNDARY_TRACE_VALIDATED',pairs=trace['max_pairs'],perceive_calls=count,
                task_step_calls=count,ram_calls=count,clock_snapshots=reads,
                observer_clock_getter_invocations=2*reads,clock_pairs_atomic=False,gpu_frame_identity_proven=False)


@contextmanager
def camera_clock_scope(provider,enabled,trace,*,max_pairs=6):
    """One original perceive/step/RAM path; exact attribute restoration on exits.

    OFF suppresses only this observer's owner/getter access. Original engine
    methods may perform their own clock operations; those remain untouched.
    """
    global _ACTIVE
    if type(trace) is not dict or trace or type(enabled) is not bool or type(max_pairs) is not int or not 1<=max_pairs<=6:
        raise ClockObserverError('fresh trace, boolean arm and bounded pair count required')
    if _ACTIVE is not None:
        exc=ClockObserverError('nested clock observers prohibited');_remember(_ACTIVE,exc);raise exc
    trace.update(schema=SCHEMA,status='FAILED_OR_INCOMPLETE',enabled=enabled,max_pairs=max_pairs,
        clock_owner='engine.taskMgr.globalClock',clock_binding_observed=False,owner_thread=threading.get_ident(),
        calls=[],events=[],counts={kind+'_'+state:0 for kind in KINDS for state in ('attempts','returns')},
        restoration_complete=False,restoration_errors=[],error=None,body_error=None)
    _ACTIVE=trace;originals=[];active=None;primary=None

    def reject(message):
        exc=ClockObserverError(message);_remember(trace,exc);raise exc

    def guard():
        if threading.get_ident()!=trace['owner_thread']:reject('observer belongs to one Python thread')
        if trace['error'] is not None:reject('observer already recorded a failed operation')

    def event(row,name):
        if len(trace['events'])>=12*max_pairs:reject('event budget exhausted')
        trace['events'].append(dict(index=len(trace['events'])+1,event=name,call=row['call'],camera=row['camera']))

    def invoke(row,kind,bound,args,kwargs):
        row[kind+'_attempted']=True;trace['counts'][kind+'_attempts']+=1
        result=bound(*args,**kwargs)
        row[kind+'_returned']=True;trace['counts'][kind+'_returns']+=1
        return result

    def install(obj,name,wrapper):
        own=name in vars(obj);saved=vars(obj).get(name)
        originals.append((obj,name,own,saved))
        setattr(obj,name,wrapper)

    try:
        engine=provider.env.engine;manager=engine.taskMgr
        clock=None;get_count=None;get_time=None
        if enabled:
            clock=manager.globalClock;get_count=clock.getFrameCount;get_time=clock.getFrameTime
            if not callable(get_count) or not callable(get_time):reject('clock getter unavailable')

        def snapshot(row,boundary):
            if not enabled:return
            snap=dict(event_index=len(trace['events']),frame_count=None,frame_time_s=None,
                frame_count_attempted=False,frame_count_returned=False,
                frame_time_attempted=False,frame_time_returned=False,error=None)
            row['snapshots'][boundary]=snap;trace['counts']['clock_snapshot_attempts']+=1
            try:
                if manager.globalClock is not clock:reject('TaskManager clock owner changed')
                trace['clock_binding_observed']=True
                snap['frame_count_attempted']=True;trace['counts']['frame_count_attempts']+=1
                value=get_count();snap['frame_count_returned']=True;trace['counts']['frame_count_returns']+=1
                if type(value) is not int or not -(2**63)<=value<2**63:reject('frame count must be a signed64 integer')
                snap['frame_count']=value
                snap['frame_time_attempted']=True;trace['counts']['frame_time_attempts']+=1
                value=get_time();snap['frame_time_returned']=True;trace['counts']['frame_time_returns']+=1
                if type(value) is not float or not math.isfinite(value):reject('frame time must be a finite float')
                snap['frame_time_s']=value;trace['counts']['clock_snapshot_returns']+=1
            except BaseException as exc:snap['error']=_detail(exc);_remember(trace,exc);raise

        original_step=manager.step
        if not callable(original_step):reject('TaskManager step unavailable')
        def step(*args,**kwargs):
            guard()
            if active is None:reject('orphan TaskManager step')
            row=active
            if row['task_step_attempted']:reject('duplicate TaskManager step')
            try:
                event(row,'task_step_enter');result=invoke(row,'task_step',original_step,args,kwargs)
                event(row,'task_step_return');return result
            except BaseException as exc:_remember(trace,exc);row['status']='FAILED_OR_INCOMPLETE';raise
        install(manager,'step',step)
        def camera_wrappers(kind,bound_perceive,bound_ram):
            # Factory closure avoids reserving any keyword accepted by the original methods.
            def perceive(*args,**kwargs):
                nonlocal active
                guard()
                if active is not None:reject('nested perceive call')
                index=len(trace['calls'])
                if index>=2*max_pairs:reject('perceive budget exhausted')
                if kind!=CAMERAS[index%2]:reject('registered Road/Wide order required')
                row=dict(call=index+1,camera=kind,status='FAILED_OR_INCOMPLETE',
                    **{k+'_'+s:False for k in ('perceive','task_step','ram') for s in ('attempted','returned')},
                    snapshots={k:None for k in BOUNDARIES})
                trace['calls'].append(row);active=row
                try:
                    event(row,'perceive_enter');snapshot(row,'before_perceive')
                    result=invoke(row,'perceive',bound_perceive,args,kwargs)
                    event(row,'perceive_return');snapshot(row,'after_perceive')
                    if not row['task_step_returned'] or not row['ram_returned']:reject('perceive missing step/RAM return')
                    if trace['error'] is None:row['status']='RETURNED'
                    return result
                except BaseException as exc:_remember(trace,exc);raise
                finally:active=None
            def ram(*args,**kwargs):
                guard()
                if active is None or active['camera']!=kind:reject('orphan/wrong-camera RAM call')
                row=active
                if row['ram_attempted']:reject('duplicate RAM call')
                if not row['task_step_returned']:reject('RAM call before observed task step return')
                try:
                    event(row,'ram_enter');snapshot(row,'before_ram_method')
                    result=invoke(row,'ram',bound_ram,args,kwargs)
                    event(row,'ram_return');snapshot(row,'after_ram_method');return result
                except BaseException as exc:_remember(trace,exc);row['status']='FAILED_OR_INCOMPLETE';raise
            return perceive,ram
        for kind in CAMERAS:
            camera=engine.sensors['bigbench_'+kind]
            original_perceive=camera.perceive;original_ram=camera.get_rgb_array_cpu
            if not callable(original_perceive) or not callable(original_ram):reject('camera method unavailable')
            perceive,ram=camera_wrappers(kind,original_perceive,original_ram)
            install(camera,'perceive',perceive);install(camera,'get_rgb_array_cpu',ram)
        try:yield trace
        except BaseException as exc:trace['body_error']=_detail(exc);raise
    except BaseException as exc:
        primary=exc;_remember(trace,exc);raise
    finally:
        for obj,name,own,saved in reversed(originals):
            try:
                if own:
                    if vars(obj).get(name) is not saved:setattr(obj,name,saved)
                    if name not in vars(obj) or vars(obj)[name] is not saved:raise ClockObserverError('own attribute not restored')
                else:
                    if name in vars(obj):delattr(obj,name)
                    if name in vars(obj):raise ClockObserverError('inherited attribute ownership not restored')
            except BaseException as exc:trace['restoration_errors'].append(name+': '+_detail(exc))
        trace['restoration_complete']=not trace['restoration_errors'];_ACTIVE=None
        if trace['restoration_errors']:
            trace['status']='FAILED_OR_INCOMPLETE'
            note='Clock observer attribute restoration: '+'; '.join(trace['restoration_errors'])
            if primary is not None:primary.add_note(note)
            else:
                exc=ClockObserverError(note);_remember(trace,exc);raise exc
        if primary is None:
            if trace['error'] is not None:
                trace['status']='FAILED_OR_INCOMPLETE';raise ClockObserverError('observer recorded a failed operation')
            trace['status']='CLOCK_BOUNDARY_TRACE_RECORDED'
            try:validate_clock_trace(trace)
            except BaseException as exc:_remember(trace,exc);raise
