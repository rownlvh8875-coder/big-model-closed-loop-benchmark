"""Stdlib process identity/admission; never imports a simulator or model."""
from pathlib import Path
import json,math,os,platform,sys,time

def worker_launch():
    executable=sys.executable
    environment=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
    base=getattr(sys,'_base_executable',executable)
    if sys.platform=='win32' and os.path.normcase(base)!=os.path.normcase(executable):
        environment['__PYVENV_LAUNCHER__']=executable
        executable=base
    return executable,environment

def await_parent_ack(out,*,parent,nonce,seed,scene,timeout=5):
    if type(parent) is not int or parent<=0 or parent!=os.getppid() or not isinstance(nonce,str) or len(nonce)!=32 or any(c not in '0123456789abcdef' for c in nonce):raise ValueError('live owned parent/nonce required before native imports')
    if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<=timeout<=5:raise ValueError('bounded parent acknowledgement required')
    deadline=time.monotonic()+timeout
    while True:
        owner=json.loads((Path(out)/'owner.json').read_text())
        if owner.get('parent_pid')!=parent or owner.get('nonce')!=nonce or (owner.get('seed'),owner.get('scenario'))!=(seed,scene):raise ValueError('parent-assigned worker case/nonce mismatch')
        if owner.get('spawn_succeeded') is True:
            if owner.get('pid')!=os.getpid() or owner.get('returncode') is not None or owner.get('child_reaped') is not False:raise ValueError('parent must acknowledge this actual live worker PID')
            return owner
        if owner.get('spawn_succeeded') is False or time.monotonic()>=deadline:raise ValueError('parent admission unresolved; native imports forbidden')
        time.sleep(.02)

def ownership_snapshot(owner,backend):
    loaded=any(n.split('.')[0] in ('panda3d','direct','metadrive','carla','onnxruntime') for n in sys.modules)
    if loaded:raise ValueError('ownership-only worker must remain stdlib-only')
    return dict(protocol='owned-worker-process-check-v1',ownership_check_complete=True,process_id=os.getpid(),parent_process_id=os.getppid(),nonce=owner['nonce'],seed=owner['seed'],scenario=owner['scenario'],backend=backend,python_executable=sys.executable,prefix=sys.prefix,base_prefix=sys.base_prefix,system=platform.system(),native_modules_loaded=False,model_loaded=False,server_connection_attempted=False,official_model_processes=0,inferences=0,scope='stdlib process/PID/parent/venv only; no camera, model or CARLA qualification')

class OwnershipUnresolved(RuntimeError):pass
