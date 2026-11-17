"""Owned immutable runtime, explicitly versioned software-driver and deadline changes."""
from pathlib import Path
import json,secrets,subprocess
from scripts import panda_sdk3_runtime as p
from scripts.panda_sdk3_runtime import write,need,inspect_container,IMAGE,log_limits
ROOT=Path(__file__).resolve().parents[1]
ENTRY='/work/repo/scripts/sdk3_four_validation_native.py'

def native_command(*args,**kwargs):
 command=p.container_command(*args,**kwargs);command[command.index('/work/repo/scripts/panda_sdk3_diagnostic.py')]=ENTRY
 for option,value in [('--memory','10g'),('--memory-swap','10g'),('--cpus','2'),('--tmpfs','/tmp:rw,nosuid,nodev,size=512m')]:command[command.index(option)+1]=value
 command=[{'GALLIUM_DRIVER=softpipe':'GALLIUM_DRIVER=llvmpipe','LP_NUM_THREADS=0':'LP_NUM_THREADS=2'}.get(x,x) for x in command]
 if 'LD_DEBUG=bindings,versions' in command:
  index=command.index('LD_DEBUG=bindings,versions');need(command[index-1]=='--env','exact old debug environment');del command[index-1:index+1]
 return command
container_command=native_command

def run_container(name,sdk,out,args,*,model=None,deps=None):
    out.mkdir(parents=True);out.chmod(0o777);owner=secrets.token_hex(16)
    cmd=container_command(name,ROOT,sdk,out,args,model=model,deps=deps,owner=owner)
    write(out/'command.json',dict(argv=cmd,ownership_label=owner))
    cid=None;rc=None;failure=None;state=None;create_attempted=False;start_attempted=False;removed=False;cleanup_failure=None
    write(out/'execution.json',dict(status='PREPARING',create_attempted=False,start_attempted=False,owned_container_removed=False))
    try:
        need(inspect_container(name) is None,'fresh owned container name')
        create_attempted=True
        write(out/'execution.json',dict(status='CREATE_IN_FLIGHT',create_attempted=True,start_attempted=False,ownership_label=owner,owned_container_removed=False))
        with (out/'create.stdout.log').open('wb') as stdout,(out/'create.stderr.log').open('wb') as stderr:
            creation=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=90)
        need(creation.returncode==0,'Docker create failed; see retained creation logs')
        actual=inspect_container(name)
        need(actual is not None and actual['Config']['Labels'].get('stage7.sdk3.owner')==owner,'created ownership label')
        cid=actual['Id'];write(out/'container.json',dict(id=cid,name=name,image=IMAGE,ownership_label=owner,effective_limits={k:actual.get('HostConfig',{}).get(k) for k in ('Memory','MemorySwap','NanoCpus','PidsLimit','ReadonlyRootfs','NetworkMode','IpcMode')}))
        start_attempted=True
        with (out/'stdout.log').open('wb') as stdout,(out/'stderr.log').open('wb') as stderr:
            rc=subprocess.run(['docker','start','--attach',cid],stdout=stdout,stderr=stderr,timeout=18180 if model else 300,preexec_fn=log_limits).returncode
        actual=inspect_container(cid);need(actual is not None,'retained stopped container');state=actual['State']
        need(not state['Running'] and state['Pid']==0 and not state['OOMKilled'],'stopped non-OOM child')
        need(all((out/n).stat().st_size<=16*1024**2 for n in ['stdout.log','stderr.log']),'complete bounded logs')
    except BaseException as e:failure=type(e).__name__+': '+str(e)
    finally:
        # A create timeout can follow daemon-side creation. Recover only our exact label.
        if create_attempted and cid is None:
            try:
                actual=inspect_container(name)
                if actual is not None and actual['Config']['Labels'].get('stage7.sdk3.owner')==owner:cid=actual['Id'];state=actual['State']
            except BaseException as e:cleanup_failure='ownership recovery '+type(e).__name__+': '+str(e)
        if cid is not None:
            try:
                with (out/'remove.stdout.log').open('wb') as stdout,(out/'remove.stderr.log').open('wb') as stderr:
                    removal=subprocess.run(['docker','rm','--force',cid],stdout=stdout,stderr=stderr,timeout=30)
                removed=removal.returncode==0
                if not removed:cleanup_failure='owned removal returned '+str(removal.returncode)
            except BaseException as e:cleanup_failure='owned removal '+type(e).__name__+': '+str(e)
        if cleanup_failure:failure=((failure+'; ') if failure else '')+cleanup_failure
        execution=dict(status='FAILED' if failure else 'EXIT_OBSERVED',returncode=rc,failure=failure,stopped_state=state,
            create_attempted=create_attempted,start_attempted=start_attempted,container_id=cid,
            ownership_unresolved=create_attempted and cid is None,owned_container_removed=removed,cleanup_failure=cleanup_failure)
        write(out/'execution.json',execution)
    return execution
