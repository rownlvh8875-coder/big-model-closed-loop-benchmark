"""Bounded owned process-group capture, including memory-only private metadata.

The caller chooses commands, environment and limits. No process runs at import.
Observed digests/counts can include one bounded read beyond a limit; saved streams
never exceed the registered limit. Incomplete streams are never called complete.
"""
import hashlib
import json
import math
import os
import resource
from pathlib import Path
import selectors
import signal
import subprocess
from time import monotonic


def public_receipt(result):
    return {k:v for k,v in result.items() if not k.startswith('_')}


def capture(command,out:Path,*,timeout,stdout_limit,stderr_limit,stdin=None,env=None,
            keep_stdout=True,keep_stderr=True,redact=None,file_size_limit=None):
    if (type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=1800
            or any(type(v) is not int or not 0<=v<=2*1024**3 for v in (stdout_limit,stderr_limit))):
        raise ValueError('IMAGE_PROCESS_CONTEXT_REJECTED')
    if file_size_limit is not None and (type(file_size_limit) is not int or not 0<file_size_limit<=2*1024**3):raise ValueError('IMAGE_PROCESS_CONTEXT_REJECTED')
    def limits():resource.setrlimit(resource.RLIMIT_FSIZE,(file_size_limit,file_size_limit))
    out=Path(out);out.mkdir(parents=True,mode=0o700,exist_ok=False);started=monotonic();deadline=started+timeout
    result={'schema':'image-owned-process-capture-v1','status':'CAPTURE_FAILED','returncode':None,'streams_complete':False,'termination_attempted':False,'cleanup_failed':False,'argv_sha256':hashlib.sha256(json.dumps(command,separators=(',',':')).encode()).hexdigest()}
    streams={};process=None;selector=selectors.DefaultSelector();reason=None
    for name,limit,keep in [('stdout',stdout_limit,keep_stdout),('stderr',stderr_limit,keep_stderr)]:
        streams[name]={'limit':limit,'keep':keep,'hash':hashlib.sha256(),'count':0,'chunks':[],'file':None,'saved':0,'redacted':False,'truncated':False}
        if keep and redact is None:streams[name]['file']=(out/(name+'.bin')).open('xb')
    def stop():
        result['termination_attempted']=True
        try:os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        try:process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            try:process.wait(timeout=2)
            except subprocess.TimeoutExpired:result['cleanup_failed']=True
        # A parent can exit before a descendant with inherited output descriptors.
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    try:
        process=subprocess.Popen(command,stdin=subprocess.DEVNULL if stdin is None else stdin,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,start_new_session=True,preexec_fn=limits if file_size_limit is not None else None)
        for name,pipe in [('stdout',process.stdout),('stderr',process.stderr)]:
            os.set_blocking(pipe.fileno(),False);selector.register(pipe,selectors.EVENT_READ,name)
        while selector.get_map() and reason is None:
            left=deadline-monotonic()
            if left<=0:reason='TIMEOUT';break
            for key,_ in selector.select(min(.1,left)):
                try:block=os.read(key.fileobj.fileno(),65536)
                except BlockingIOError:continue
                if not block:selector.unregister(key.fileobj);key.fileobj.close();continue
                entry=streams[key.data];remaining=max(0,entry['limit']-entry['count']);entry['count']+=len(block);entry['hash'].update(block);admitted=block[:remaining]
                if entry['file'] is not None:entry['file'].write(admitted);entry['saved']+=len(admitted)
                else:entry['chunks'].append(admitted)
                if entry['count']>entry['limit']:reason='OUTPUT_LIMIT';break
        if reason is not None:stop()
        else:
            try:process.wait(timeout=max(.001,deadline-monotonic()))
            except subprocess.TimeoutExpired:reason='TIMEOUT';stop()
        result.update(status=reason or 'EXITED',returncode=process.returncode,streams_complete=reason is None)
    except Exception:
        reason='CAPTURE_FAILED'
        if process is not None:stop();result['returncode']=process.returncode
        result['status']='CAPTURE_FAILED'
    finally:
        selector.close()
        if process is not None:
            for pipe in (process.stdout,process.stderr):
                if pipe is not None and not pipe.closed:pipe.close()
        for name,entry in streams.items():
            if entry['file'] is not None:entry['file'].close()
            body=b''.join(entry['chunks'])
            if entry['keep'] and redact is not None:
                safe=redact(body)
                if type(safe) is not bytes:raise ValueError('IMAGE_PROCESS_REDACTOR_REJECTED')
                entry['redacted']=safe!=body;entry['truncated']=len(safe)>entry['limit'];safe=safe[:entry['limit']]
                with (out/(name+'.bin')).open('xb') as f:f.write(safe)
                entry['saved']=len(safe)
            if not entry['keep']:result['_'+name]=body
            result.update({name+'_observed_bytes':entry['count'],name+'_sha256':entry['hash'].hexdigest(),name+'_saved_bytes':entry['saved'],name+'_redacted':entry['redacted'],name+'_saved_truncated':entry['truncated']})
        result['elapsed_seconds']=monotonic()-started
        if result['cleanup_failed']:result.update(status='CLEANUP_FAILED',streams_complete=False)
        with (out/'receipt.json').open('x') as f:json.dump(public_receipt(result),f,sort_keys=True,indent=2);f.write('\n')
    return result
