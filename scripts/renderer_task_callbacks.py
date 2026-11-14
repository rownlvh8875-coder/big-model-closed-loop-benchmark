"""Bounded CPU callback metadata. No native admission, renderer imports or I/O."""
from contextlib import contextmanager
from hashlib import sha256
import json
import math
import struct
import sys
import threading
from types import MethodType

CALLBACKS=('PSSM.update','MainCamera._chase_task')
TRACE_CAP=256*1024
_ACTIVE=None


class CallbackBoundaryError(RuntimeError):pass


def _remember(trace,exc):
    if trace['error'] is None:
        try:detail=str(exc)
        except BaseException:detail='<unprintable>'
        trace['error']=type(exc).__name__+': '+detail[:256]
    trace['status']='FAILED_OR_INCOMPLETE'


def _state(raw):
    if type(raw) is not dict or set(raw)!={'pose','matrices','chase_run_task'}:
        raise CallbackBoundaryError('exact snapshot fields required')
    p=raw['pose'];m=raw['matrices']
    if (type(p) is not dict or set(p)!={'xyz_m','hpr_deg'} or
        any(type(p[k]) is not list or len(p[k])!=3 for k in p) or
        type(m) is not list or len(m)!=2 or
        any(type(a) is not list or len(a)!=4 or
            any(type(r) is not list or len(r)!=4 for r in a) for a in m) or
        type(raw['chase_run_task']) is not bool):
        raise CallbackBoundaryError('two-split matrix/WORLD pose/boolean flag required')
    values=p['xyz_m']+p['hpr_deg']+[v for a in m for r in a for v in r]
    if any(type(v) is not float or not math.isfinite(v) for v in values):
        raise CallbackBoundaryError('finite float observations required')
    copied=dict(pose={k:list(p[k]) for k in p},matrices=[[list(r) for r in a] for a in m],
                chase_run_task=raw['chase_run_task'])
    copied['mvp_sha256']=sha256(b''.join(struct.pack('!d',v) for v in values[6:])).hexdigest()
    return copied


def _events(events,task_continue):
    if type(events) is not list or len(events)!=4:raise CallbackBoundaryError('four callback boundaries required')
    names=[]
    for i,e in enumerate(events):
        if (type(e) is not dict or set(e)!={'index','callback','event','state','return_value'} or
            type(e['index']) is not int or e['index']!=i+1 or e['callback'] not in CALLBACKS or
            e['event']!=('call' if i%2==0 else 'return')):
            raise CallbackBoundaryError('nonoverlapping callback call/return sequence required')
        state=e['state']
        if type(state) is not dict or set(state)!={'pose','matrices','chase_run_task','mvp_sha256'}:
            raise CallbackBoundaryError('complete state receipt required')
        if _state({k:state[k] for k in ('pose','matrices','chase_run_task')})!=state:
            raise CallbackBoundaryError('numeric MVP digest mismatch')
        if i%2==0:
            names.append(e['callback'])
            if e['return_value'] is not None:raise CallbackBoundaryError('call has no return observation')
        elif (e['callback']!=events[i-1]['callback'] or
              type(e['return_value']) is not int or e['return_value']!=task_continue):
            raise CallbackBoundaryError('normal task.cont return required')
    if set(names)!=set(CALLBACKS):raise CallbackBoundaryError('both exact callbacks required')


def validate_trace(trace):
    fields={'schema','status','enabled','max_pairs','owner_thread','task_continue','steps',
            'step_attempts','step_returns','snapshot_attempts','snapshot_returns',
            'restoration_complete','restoration_errors','error','body_error'}
    if type(trace) is not dict or set(trace)!=fields:raise CallbackBoundaryError('exact trace schema required')
    if (trace['schema']!='renderer-task-callbacks-v1' or trace['status']!='CPU_CALLBACK_TRACE_COMPLETE' or
        type(trace['enabled']) is not bool or type(trace['max_pairs']) is not int or not 1<=trace['max_pairs']<=6 or
        type(trace['owner_thread']) is not int or trace['owner_thread']<=0 or
        type(trace['task_continue']) is not int or trace['restoration_complete'] is not True or
        trace['restoration_errors']!=[] or trace['error'] is not None or trace['body_error'] is not None):
        raise CallbackBoundaryError('complete restored CPU trace required')
    steps=2*trace['max_pairs'];reads=4*steps if trace['enabled'] else 0
    for key,want in (('step_attempts',steps),('step_returns',steps),('snapshot_attempts',reads),('snapshot_returns',reads)):
        if type(trace[key]) is not int or trace[key]!=want:raise CallbackBoundaryError('exact observer budgets required')
    if type(trace['steps']) is not list or len(trace['steps'])!=steps:raise CallbackBoundaryError('complete step ledger required')
    for i,row in enumerate(trace['steps']):
        if (type(row) is not dict or set(row)!={'call','camera','status','original_returned','events'} or
            type(row['call']) is not int or row['call']!=i+1 or row['camera']!=('road','wide')[i%2] or
            row['status']!='RETURNED' or row['original_returned'] is not True):
            raise CallbackBoundaryError('explicit camera/step association required')
        if trace['enabled']:_events(row['events'],trace['task_continue'])
        elif row['events'] is not None:raise CallbackBoundaryError('OFF callbacks are unobserved/null')
    if len(json.dumps(trace,allow_nan=False).encode())>TRACE_CAP:raise CallbackBoundaryError('trace byte cap')
    return dict(status='CPU_CALLBACK_METADATA_VALIDATED',steps=steps,
                observed_callback_events=reads if trace['enabled'] else None,
                native_execution_proven=False,gpu_causality_proven=False,snapshots_atomic=False)


@contextmanager
def task_callback_scope(manager,enabled,trace,*,clock_trace,targets=None,snapshot=None,task_continue=1,max_pairs=6):
    """Install BEFORE camera_clock_scope; profile only each original step.

    targets are exact already-admitted bound Python methods. OFF must not bind
    targets or a state reader. This function neither imports nor admits a renderer.
    Python unwind also produces profile return; require the caller's task.cont
    contract instead of inferring normal completion from that event alone.
    """
    global _ACTIVE
    if _ACTIVE is not None:
        exc=CallbackBoundaryError('nested callback observers prohibited');_remember(_ACTIVE,exc);raise exc
    if (type(trace) is not dict or trace or type(clock_trace) is not dict or type(enabled) is not bool or
        type(max_pairs) is not int or not 1<=max_pairs<=6 or type(task_continue) is not int):
        raise CallbackBoundaryError('fresh trace and bounded typed configuration required')
    if sys.getprofile() is not None:raise CallbackBoundaryError('existing profile hook must be preserved')
    if enabled:
        if (type(targets) is not dict or set(targets)!=set(CALLBACKS) or not callable(snapshot) or
            any(type(v) is not MethodType for v in targets.values())):
            raise CallbackBoundaryError('two exact bound methods and state reader required')
        bindings={v.__func__.__code__:(k,v.__self__) for k,v in targets.items()}
        if len(bindings)!=2:raise CallbackBoundaryError('distinct callback code objects required')
    elif targets is not None or snapshot is not None:raise CallbackBoundaryError('OFF must not bind callback owners/readers')
    trace.update(schema='renderer-task-callbacks-v1',status='FAILED_OR_INCOMPLETE',enabled=enabled,
        max_pairs=max_pairs,owner_thread=threading.get_ident(),task_continue=task_continue,steps=[],
        step_attempts=0,step_returns=0,snapshot_attempts=0,snapshot_returns=0,
        restoration_complete=False,restoration_errors=[],error=None,body_error=None)
    original=manager.step;own='step' in vars(manager);saved=vars(manager).get('step')
    if not callable(original):raise CallbackBoundaryError('original step unavailable')
    _ACTIVE=trace;active=None;callback_frame=None;callback_name=None;primary=None;installed=False

    def reject(message):
        exc=CallbackBoundaryError(message);_remember(trace,exc);raise exc

    def guard():
        if threading.get_ident()!=trace['owner_thread']:reject('one owner thread required')
        if trace['error'] is not None:reject('observer already failed')

    def profile(frame,event,arg):
        nonlocal callback_frame,callback_name
        if event not in ('call','return') or frame.f_code not in bindings:return
        # A profile exception would mask an original callback exception and
        # disable the hook. Keep the first failure sticky, let original engine
        # control flow finish/unwind, then reject at the step boundary.
        if trace['error'] is not None:return
        try:
            guard();name,owner=bindings[frame.f_code]
            if frame.f_locals.get('self') is not owner:reject('foreign callback self identity')
            if active is None:reject('callback outside associated original step')
            events=active['events']
            if len(events)>=4:reject('callback boundary budget exhausted')
            if event=='call':
                if callback_frame is not None:reject('nested callback execution')
                if any(e['callback']==name for e in events):reject('duplicate callback execution')
                callback_frame,callback_name=frame,name
            elif callback_frame is not frame or callback_name!=name:reject('unpaired callback exit')
            elif type(arg) is not int or arg!=task_continue:reject('exception unwind or unexpected callback return')
            if trace['snapshot_attempts']>=8*max_pairs:reject('snapshot budget exhausted')
            trace['snapshot_attempts']+=1;state=_state(snapshot());trace['snapshot_returns']+=1
            events.append(dict(index=len(events)+1,callback=name,event=event,state=state,
                               return_value=arg if event=='return' else None))
            if event=='return':callback_frame=callback_name=None
        except (KeyboardInterrupt,SystemExit,TimeoutError) as exc:
            _remember(trace,exc);raise
        except BaseException as exc:_remember(trace,exc)

    def step(*args,**kwargs):
        nonlocal active,callback_frame,callback_name
        guard()
        if active is not None:reject('nested step execution')
        if len(trace['steps'])>=2*max_pairs:reject('step budget exhausted')
        calls=clock_trace.get('calls')
        if type(calls) is not list or not calls:reject('missing active clock camera binding')
        bound=calls[-1];index=len(trace['steps'])
        if (bound.get('call')!=index+1 or type(bound.get('call')) is not int or
            bound.get('camera')!=('road','wide')[index%2] or
            bound.get('task_step_attempted') is not True or bound.get('task_step_returned') is not False or
            bound.get('ram_attempted') is not False):reject('wrong active camera step binding')
        if sys.getprofile() is not None:reject('profile hook changed before original step')
        row=dict(call=index+1,camera=bound['camera'],status='FAILED_OR_INCOMPLETE',
                 original_returned=False,events=[] if enabled else None)
        trace['steps'].append(row);active=row;callback_frame=callback_name=None
        try:
            if enabled:sys.setprofile(profile)
            trace['step_attempts']+=1
            result=original(*args,**kwargs)
            row['original_returned']=True;trace['step_returns']+=1
            if enabled and sys.getprofile() is not profile:reject('profile hook disappeared/replaced')
            guard()
            if enabled:_events(row['events'],task_continue)
            row['status']='RETURNED';return result
        except BaseException as exc:_remember(trace,exc);raise
        finally:
            if enabled:sys.setprofile(None)
            active=callback_frame=callback_name=None

    try:
        installed=True;setattr(manager,'step',step)
        try:yield trace
        except BaseException as exc:trace['body_error']=type(exc).__name__;raise
    except BaseException as exc:primary=exc;_remember(trace,exc);raise
    finally:
        if installed:
            try:
                if own:
                    if vars(manager).get('step') is not saved:setattr(manager,'step',saved)
                    if vars(manager).get('step') is not saved:raise CallbackBoundaryError('own step not restored')
                else:
                    if 'step' in vars(manager):delattr(manager,'step')
                    if 'step' in vars(manager):raise CallbackBoundaryError('inherited step not restored')
            except BaseException as exc:trace['restoration_errors'].append(type(exc).__name__)
        trace['restoration_complete']=not trace['restoration_errors'];_ACTIVE=None
        if primary is None:
            if trace['error'] is not None or trace['restoration_errors']:
                reject('observer failed or attribute restoration incomplete')
            trace['status']='CPU_CALLBACK_TRACE_COMPLETE'
            try:validate_trace(trace)
            except BaseException as exc:_remember(trace,exc);raise
        elif trace['restoration_errors']:primary.add_note('callback step restoration incomplete')
