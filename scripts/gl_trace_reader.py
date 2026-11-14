"""Pinned apitrace CPU decoding only. No trace capture, replay or GL context."""
from contextlib import contextmanager
from hashlib import sha256
import io
import os
from pathlib import Path
import pickle
import re
import signal
import subprocess
import tarfile
import threading

from scripts.gl_read_provenance import Pointer

TOOL_SHA='b41db446641250045e94645a94b507345bfcec6e5a2d7e7224348a5a80544274'
DEB_SHA='0b7212fd6a0fa9ce488abec7358cdfe99aba50817eca02aa5c493e686bcec3aa'
TRACE_PINS={'on_0.trace':(209757595,'9665413782cbe05d0f5460c8983643b5cdf8e6d8415ad88f2a2e85f135136e9a'),
            'on_1.trace':(209758897,'6ddef5fc8a2c29d6f296e991fe32322b22d73a38dfd86f8764e78990622d3192')}

class Limited:
    def __init__(self,stream,limit):self.stream=stream;self.limit=limit;self.count=0
    def read(self,n):
        if not 0<=n<=512*1024*1024:raise ValueError('pickle read request cap')
        data=self.stream.read(min(n,self.limit-self.count+1));self.count+=len(data)
        if self.count>self.limit:raise ValueError('pickle total byte cap')
        return data
    def readline(self,n=-1):
        if n<0:n=1024*1024+1
        if n>1024*1024+1:raise ValueError('pickle line request cap')
        data=self.stream.readline(min(n,self.limit-self.count+1));self.count+=len(data)
        if self.count>self.limit or len(data)>1024*1024:raise ValueError('pickle line/byte cap')
        return data

class Restricted(pickle.Unpickler):
    def find_class(self,module,name):
        if (module,name)==('unpickle','Pointer'):return Pointer
        raise ValueError('forbidden pickle global: '+module+'.'+name)

def read_pickles(stream,*,max_bytes=2*1024**3,stats=None):
    if type(max_bytes) is not int or not 1<=max_bytes<=2*1024**3:raise ValueError('bounded pickle bytes required')
    bounded=Limited(stream,max_bytes);count=0
    try:
        while True:
            before=bounded.count
            try:value=Restricted(bounded).load()
            except EOFError:
                if bounded.count!=before:raise ValueError('truncated pickle record') from None
                break
            except (pickle.UnpicklingError,OverflowError,TypeError,AttributeError,ImportError) as exc:
                raise ValueError('malformed pickle record') from exc
            count+=1
            if count>120000:raise ValueError('pickle call cap')
            yield value
    finally:
        if stats is not None:stats.update(decoded_pickle_bytes=bounded.count,decoded_calls=count)

def scan_threads(lines,*,max_calls=120000,max_bytes=128*1024**2,max_line=1024**2):
    if any(type(x) is not int or not 1<=x<=cap for x,cap in ((max_calls,120000),(max_bytes,128*1024**2),(max_line,1024**2))):
        raise ValueError('bounded thread scan required')
    threads=set();count=0;total=0;last=-1;digest=sha256()
    for line in lines:
        if type(line) is not bytes or len(line)>max_line:raise ValueError('metadata line cap')
        total+=len(line);digest.update(line)
        if total>max_bytes:raise ValueError('metadata byte cap')
        if not line.strip() or line.startswith(b'//'):continue
        m=re.match(rb'^([0-9]+) @([0-9]+) (gl[A-Za-z0-9_]+)\(',line)
        if m is None:raise ValueError('complete thread-id metadata required')
        no,thread=map(int,m.group(1,2))
        if no<=last:raise ValueError('ordered metadata calls required')
        last=no;threads.add(thread);count+=1
        if len(threads)>1 or count>max_calls:raise ValueError('single GL thread/call cap required')
    if count==0 or len(threads)!=1:raise ValueError('one observed GL thread required')
    return dict(thread_id=next(iter(threads)),calls=count,text_bytes=total,text_sha256=digest.hexdigest())

def decoder_command(tool,mode,trace):
    tool,trace=Path(tool),Path(trace)
    if not tool.is_absolute() or not trace.is_absolute():raise ValueError('absolute data/tool paths required')
    if mode=='pickle':return [str(tool),'pickle',str(trace)]
    if mode=='dump':return [str(tool),'dump','--verbose','--color=never','--thread-ids','--multiline=no',str(trace)]
    raise ValueError('only offline dump/pickle permitted')

@contextmanager
def process_stdout(command,*,timeout=120):
    if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not 0<timeout<=120:raise ValueError('bounded decoder deadline required')
    env=dict(os.environ)
    for key in ('LD_PRELOAD','LD_LIBRARY_PATH'):env.pop(key,None)
    env['LC_ALL']='C'
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,shell=False,start_new_session=True)
    reason=[];stderr=bytearray();primary=None
    def kill(why):
        reason.append(why)
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    def drain():
        for block in iter(lambda:process.stderr.read(4096),b''):
            if len(stderr)+len(block)>64*1024:kill('stderr cap');return
            stderr.extend(block)
    worker=threading.Thread(target=drain,daemon=True);worker.start()
    timer=threading.Timer(timeout,kill,args=('decoder timeout',));timer.daemon=True;timer.start()
    try:yield process.stdout
    except BaseException as exc:primary=exc;raise
    finally:
        timer.cancel()
        if primary is not None and process.poll() is None:kill('consumer stopped')
        try:code=process.wait(timeout=5)
        except subprocess.TimeoutExpired:kill('exit timeout');code=process.wait(timeout=5)
        worker.join(timeout=1);process.stdout.close();process.stderr.close()
        if primary is None and (reason or code!=0):raise ValueError('offline decoder failed: '+str(reason or code))

def _regular(path,cap):
    path=Path(path).absolute()
    if '..' in path.parts or any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file() or not 0<path.stat().st_size<=cap:
        raise ValueError('bounded regular file required')
    return path

def file_sha(path):
    h=sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def verify_tool(tool,deb):
    tool=_regular(tool,4*1024**2)
    if file_sha(tool)!=TOOL_SHA:raise ValueError('pinned decoder binary mismatch')
    deb=_regular(deb,2*1024**2);raw=deb.read_bytes()
    if len(raw)!=1462376 or sha256(raw).hexdigest()!=DEB_SHA:raise ValueError('pinned decoder package mismatch')
    if raw[:8]!=b'!<arch>\n':raise ValueError('Debian ar header')
    pos=8;payloads=[]
    while pos<len(raw):
        header=raw[pos:pos+60]
        if len(header)!=60 or header[-2:]!=b'`\n':raise ValueError('bounded ar member header')
        size=int(header[48:58]);name=header[:16].decode('ascii').strip().rstrip('/');pos+=60
        if size<0 or pos+size>len(raw):raise ValueError('bounded ar member size')
        if name.startswith('data.tar.'):payloads.append(raw[pos:pos+size])
        pos+=size+(size%2)
    if len(payloads)!=1:raise ValueError('one package data archive required')
    with tarfile.open(fileobj=io.BytesIO(payloads[0]),mode='r:*') as tar:
        matches=[m for m in tar.getmembers() if m.name in ('./usr/bin/apitrace','usr/bin/apitrace')]
        if len(matches)!=1 or not matches[0].isreg() or not 0<matches[0].size<=4*1024**2:raise ValueError('one regular packaged decoder required')
        with tar.extractfile(matches[0]) as f:packaged=f.read(4*1024**2+1)
    if sha256(packaged).hexdigest()!=TOOL_SHA or packaged!=tool.read_bytes():raise ValueError('decoder differs from package payload')
    return dict(tool_sha256=TOOL_SHA,tool_bytes=tool.stat().st_size,package_sha256=DEB_SHA,package_bytes=len(raw),package_payload_matches=True)

def decode(tool,trace,*,deb):
    """Return lazy complete call stream plus mutable decoding receipt (after EOF)."""
    receipt=verify_tool(tool,deb);trace=_regular(trace,256*1024**2)
    expected=TRACE_PINS.get(trace.name)
    if expected is None or (trace.stat().st_size,file_sha(trace))!=expected:raise ValueError('pinned retained trace mismatch')
    with process_stdout(decoder_command(Path(tool), 'dump',trace)) as pipe:
        threads=scan_threads(iter(lambda:pipe.readline(1024**2+1),b''))
    receipt.update(trace_name=trace.name,trace_nbytes=expected[0],trace_sha256=expected[1],threads=threads,
        decoder_modes=['dump','pickle'],replay=False,new_native_calls=0,new_gl_calls=0,decode_complete=False)
    def events():
        with process_stdout(decoder_command(Path(tool),'pickle',trace)) as pipe:
            for value in read_pickles(pipe,stats=receipt):yield value
        if receipt['decoded_calls']!=threads['calls']:raise ValueError('thread/pickle call-count mismatch')
        receipt['decode_complete']=True
    return events(),receipt
