"""Stdlib process identity/admission; never imports a simulator or model."""
from pathlib import Path
import errno,json,math,os,platform,sys,time
_NATIVE_ENV_ENABLED=False

def confirmed_spawn_failure(exc):
    return isinstance(exc,OSError) and exc.errno in (errno.ENOENT,errno.EACCES,errno.ENOEXEC,errno.ENOTDIR)

def logical_prefix():
    executable=Path(sys.executable).absolute()
    for cfg in (executable.parent/'pyvenv.cfg',executable.parent.parent/'pyvenv.cfg'):
        if cfg.is_file():return str(cfg.parent.resolve())
    return sys.prefix

def prepare_interpreter(*,paths_only=False,native=False):
    """Resolve a 3.11 -S venv without hooks; native hooks require prior admission."""
    global _NATIVE_ENV_ENABLED
    if not sys.flags.no_site:raise ValueError('owned worker must start with -I -S before admission')
    prefix=logical_prefix();sys.prefix=sys.exec_prefix=prefix
    if paths_only or native:
        import site
        if native:
            _NATIVE_ENV_ENABLED=True;site.main()
        else:
            prefixes=[prefix];cfg=Path(prefix)/'pyvenv.cfg'
            if cfg.is_file():
                settings=dict(line.split('=',1) for line in cfg.read_text(encoding='utf-8').splitlines() if '=' in line)
                if any(k.strip().lower()=='include-system-site-packages' and v.strip().lower()=='true' for k,v in settings.items()):prefixes.append(sys.base_prefix)
            for path in site.getsitepackages(prefixes):
                if Path(path).is_dir() and path not in sys.path:sys.path.append(path)
    return prefix

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
    prepare_interpreter()
    loaded=any(n.split('.')[0] in ('panda3d','direct','metadrive','carla','onnxruntime') for n in sys.modules)
    if loaded or _NATIVE_ENV_ENABLED:raise ValueError('ownership-only worker must remain stdlib-only')
    return dict(protocol='owned-worker-process-check-v1',ownership_check_complete=True,process_id=os.getpid(),parent_process_id=os.getppid(),nonce=owner['nonce'],seed=owner['seed'],scenario=owner['scenario'],backend=backend,python_executable=sys.executable,prefix=sys.prefix,base_prefix=sys.base_prefix,system=platform.system(),site_hooks_disabled=True,native_modules_loaded=False,model_loaded=False,server_connection_attempted=False,official_model_processes=0,inferences=0,scope='stdlib process/PID/parent/venv only; no camera, model or CARLA qualification')

class OwnershipUnresolved(RuntimeError):pass
