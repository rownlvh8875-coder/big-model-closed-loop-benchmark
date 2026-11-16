"""Bounded CPU-only progress observers; no renderer/model imports."""
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
import faulthandler,json,math,subprocess,time

MAX_EVENTS=256
MAX_LINE=4096
MAX_BYTES=1024*1024

class Journal:
    def __init__(self,folder,identity):
        self.file=(Path(folder)/'progress.jsonl').open('xb',buffering=0);self.identity=dict(identity);self.seq=0;self.written=0;self.started=time.monotonic();self.cpu_started=time.process_time();self.step=0;self.camera=None
    def emit(self,event,step=None,camera=None,**metadata):
        row=dict(seq=self.seq+1,elapsed_s=time.monotonic()-self.started,cpu_s=time.process_time()-self.cpu_started,identity=self.identity,event=event,step=self.step if step is None else step,camera=self.camera if camera is None else camera,metadata=metadata)
        raw=(json.dumps(row,separators=(',',':'),allow_nan=False)+'\n').encode()
        if self.seq>=MAX_EVENTS or len(raw)>MAX_LINE or self.written+len(raw)>MAX_BYTES:raise ValueError('bounded progress journal exhausted')
        if self.file.write(raw)!=len(raw):raise OSError('short progress write')
        self.seq+=1;self.written+=len(raw);return row
    def close(self):self.file.close()


def read_journal(path):
    with Path(path).open('rb') as f:raw=f.read(MAX_BYTES+1)
    if not raw or len(raw)>MAX_BYTES or not raw.endswith(b'\n'):raise ValueError('missing/truncated/oversized progress journal')
    lines=raw.splitlines();rows=[];stack=[];identity=None;last_wall=last_cpu=0.;last_capture=0;terminal_error=False
    if len(lines)>MAX_EVENTS:raise ValueError('too many progress records')
    for seq,line in enumerate(lines,1):
        if len(line)+1>MAX_LINE:raise ValueError('oversized progress line')
        row=json.loads(line)
        if set(row)!={'seq','elapsed_s','cpu_s','identity','event','step','camera','metadata'} or type(row['seq']) is not int or row['seq']!=seq:raise ValueError('progress sequence/schema')
        for key,last in [('elapsed_s',last_wall),('cpu_s',last_cpu)]:
            value=row[key]
            if type(value) not in (int,float) or not math.isfinite(value) or value<last:raise ValueError('nonmonotonic progress time')
        last_wall,last_cpu=row['elapsed_s'],row['cpu_s']
        if not isinstance(row['identity'],dict) or (identity is not None and row['identity']!=identity):raise ValueError('progress identity changed')
        identity=row['identity']
        if type(row['step']) is not int or not 0<=row['step']<=7 or row['camera'] not in (None,'road','wide') or not isinstance(row['metadata'],dict):raise ValueError('progress scope')
        event=row['event']
        if event!='checkpoint':
            if type(event) is not str or '.' not in event:raise ValueError('progress event')
            operation,phase=event.split('.',1)
            if operation not in ('capture','perceive','get_rgb','task_step') or phase not in ('enter','return','error'):raise ValueError('progress boundary')
            key=(operation,row['step'],row['camera'])
            if phase=='enter':
                if operation=='capture':
                    if terminal_error or stack or row['step']!=last_capture+1 or row['camera'] is not None:raise ValueError('capture order')
                    last_capture=row['step']
                else:
                    if not stack or row['step']!=last_capture:raise ValueError('boundary outside capture')
                    parent=stack[-1]
                    if parent['failed'] or parent['next']>=len(parent['expected']) or parent['expected'][parent['next']]!=(operation,row['camera']):raise ValueError('missing/reordered/duplicated original operation')
                expected=([('perceive','road'),('perceive','wide')] if operation=='capture' else [('task_step',row['camera']),('get_rgb',row['camera'])] if operation=='perceive' else [])
                stack.append(dict(key=key,expected=expected,next=0,failed=False))
            else:
                if not stack or stack[-1]['key']!=key:raise ValueError('unbalanced progress boundary')
                frame=stack.pop()
                if phase=='return' and (frame['failed'] or frame['next']!=len(frame['expected'])):raise ValueError('successful return omitted operations or swallowed an error')
                if stack:
                    if phase=='error':stack[-1]['failed']=True
                    else:stack[-1]['next']+=1
                elif phase=='error':terminal_error=True
        rows.append(row)
    return rows


@contextmanager
def observe(camera,journal):
    restorations=[]
    def install(obj,name,operation,kind=None):
        original=getattr(obj,name);owned=name in vars(obj);owned_value=vars(obj).get(name)
        @wraps(original)
        def wrapped(*args,**kwargs):
            previous=journal.camera
            if operation=='capture':journal.step+=1;journal.camera=None
            elif kind is not None:journal.camera=kind
            try:
                journal.emit(operation+'.enter')
                try:value=original(*args,**kwargs)
                except BaseException as error:
                    try:journal.emit(operation+'.error',error_type=type(error).__name__)
                    except BaseException:pass
                    raise
                journal.emit(operation+'.return');return value
            finally:journal.camera=previous
        setattr(obj,name,wrapped);restorations.append((obj,name,owned,owned_value))
    try:
        install(camera,'capture','capture');engine=camera.provider.env.engine
        for kind in ('road','wide'):
            sensor=engine.sensors['bigbench_'+kind];install(sensor,'perceive','perceive',kind);install(sensor,'get_rgb_array_cpu','get_rgb',kind)
        install(engine.taskMgr,'step','task_step');yield
    finally:
        for obj,name,owned,value in reversed(restorations):
            if owned:setattr(obj,name,value)
            else:delattr(obj,name)


@contextmanager
def stack_watchdog(path,seconds=30):
    with Path(path).open('xb',buffering=0) as log:
        faulthandler.dump_traceback_later(seconds,repeat=True,file=log,exit=False)
        try:yield
        finally:faulthandler.cancel_dump_traceback_later()


def wait_observed(child,server,timeout,out):
    started=time.monotonic();receipt=dict(pid=child.pid,timeout_seconds=timeout,timed_out=False,child_returncode=None,server_returncode=None,proc_before_kill={})
    try:
        try:return child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            receipt['timed_out']=True
            for name in ('stat','status','wchan'):
                try:
                    with Path(f'/proc/{child.pid}/{name}').open('r') as f:receipt['proc_before_kill'][name]=f.read(16384)
                except OSError as error:receipt['proc_before_kill'][name+'_error']=type(error).__name__
            child.kill();return child.wait(timeout=10)
    finally:
        if child.poll() is None:child.kill();child.wait(timeout=10)
        if server.poll() is None:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
        receipt.update(child_returncode=child.returncode,server_returncode=server.returncode,elapsed_s=time.monotonic()-started)
        target=Path(out)/'watchdog.json';temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(receipt,indent=2)+'\n');temporary.replace(target)
