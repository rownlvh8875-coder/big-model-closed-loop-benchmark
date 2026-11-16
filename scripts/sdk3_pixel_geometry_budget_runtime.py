"""Materialized owned lifecycle from panda_sdk3_runtime, fixed no-model630s attach.

Only signature/entry builder/attach timeout differ; old source/globals untouched.
"""
from pathlib import Path
import secrets,subprocess
from scripts import run_sdk3_capture_progress as baseline
from scripts.panda_sdk3_runtime import write,need,inspect_container,IMAGE,log_limits
ROOT=Path(__file__).resolve().parents[1]
ENTRY='/work/repo/scripts/sdk3_pixel_geometry_budget_native.py'


def native_command(*args,**kwargs):
    command=baseline.native_command(*args,**kwargs);i=command.index(baseline.ENTRY);command[i]=ENTRY;return command


def run_renderer(name,sdk,out,args,reference):
    out.mkdir(parents=True);out.chmod(0o777);owner=secrets.token_hex(16)
    cmd=native_command(name,ROOT,sdk,out,args,reference=reference,owner=owner)
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
            rc=subprocess.run(['docker','start','--attach',cid],stdout=stdout,stderr=stderr,timeout=630,preexec_fn=log_limits).returncode
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
