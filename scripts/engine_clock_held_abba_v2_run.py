"""Authenticated one-use outer controller. No action occurs on import."""
import datetime
import time
import os
from pathlib import Path
import secrets
import shutil
import re
import subprocess
import sys
from time import perf_counter

if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import engine_clock_held_abba_v2 as n
from scripts import engine_clock_held_abba_v2_lifecycle as life
from scripts import engine_clock_held_abba_v2_archive as authority
from scripts.engine_clock_image_backend_v2 import Docker as BaseDocker
from scripts.engine_clock_image_staging_v3 import RetainedClient


def host_memory_profile(raw):
    n.need(type(raw) is bytes and len(raw)<=65536)
    values=re.findall(rb'^MemTotal:\s+([0-9]+) kB$',raw,re.M);n.need(len(values)==1)
    total=int(values[0])*1024;n.need(n.BUDGET['minimum_host_memory_bytes']<=total<2**63)
    return dict(total_bytes=total,minimum_bytes=n.BUDGET['minimum_host_memory_bytes'],container_memory_bytes=n.BUDGET['memory_bytes'])


def state_projection(value):
    n.need(type(value) is dict and type(value.get('Running')) is bool and type(value.get('OOMKilled')) is bool
           and type(value.get('ExitCode')) is int and -1<=value['ExitCode']<=255
           and value.get('Status') in ('created','running','paused','restarting','removing','exited','dead'))
    return {key:value[key] for key in ('Running','Status','ExitCode','OOMKilled')}


class Docker(BaseDocker):
    """Observe already-issued State calls without consuming cleanup allowance."""
    def json(self,args,*,cleanup=False):
        result=super().json(args,cleanup=cleanup)
        if len(args)==5 and args[:4]==['container','inspect','--format','{{json .State}}']:
            try:
                safe=state_projection(result)
                (self.out/('state-observation-%03d.json'%self.counter)).write_bytes(n.canonical(safe))
            except Exception:pass
        return result


def prepare_routes(work,root):
    work=Path(work).resolve();n.need(work.is_dir())
    routes={'repo':str(Path(root).resolve())}
    for name in ('binding','output','cache'):
        path=work.parent/'native-cache' if name=='cache' else work/name
        mode=0o755 if name=='binding' else 0o777
        path.mkdir(mode=mode);path.chmod(mode)
        n.need(path.stat().st_mode&0o777==mode)
        routes[name]=str(path.resolve())
    n.need(not Path(routes['cache']).is_relative_to(work))
    return routes


def failure_summary(work,context,environment):
    result=dict(status='UNAVAILABLE_OR_UNBOUND',accepted=False,provider_bounds=[0,4])
    try:
        phase=n.image.parse(n.image.read_regular(Path(work)/'output/phase.json',2*n.MIB))
        n.need(n.exact(phase['context'],context))
        result.update(status='BOUND_PHASE_DIAGNOSTIC_ONLY',phase_status=phase['status'],
            launches_retained=len(phase['launches']),provider_bounds=[0,len(n.schedule(phase['mode']))])
    except Exception:pass
    return result


def identity_gate(accepted,current,path):
    differences=n.identity_difference(accepted,current)
    report=dict(schema='sealed-abba-identity-comparison-v1',equal=not differences,differences=differences)
    Path(path).write_bytes(n.canonical(report))
    n.need(not differences)
    return report


def launch_phase(engine,image,request,context,receipt,manifest_raw,work,root,accepted=None,*,producer,lease):
    """Stopped-container proof precedes the only native start; finite cleanup owns it."""
    work=Path(work);root=Path(root);nonce=secrets.token_hex(16)
    routes=prepare_routes(work,root)
    identity=n.make_identity(receipt,request['image_evidence']['expected'],engine.host,engine.profile)
    if request['mode']=='abba':
        n.need(accepted is not None)
        shutil.copytree(work.parent/'accepted-inputs/accepted-canary',work/'binding/accepted-canary')
    binding=dict(schema='engine-clock-held-abba-binding-v2',request=request,producer_request=producer,
                 host_lease=lease,context=context,accepted_canary=accepted,
                 receipt=receipt,identity=identity,host=engine.host,engine=engine.profile,
                 outer_provenance={k:os.environ.get(k) for k in ('ImageOS','ImageVersion')})
    (work/'binding'/'binding.json').write_bytes(n.canonical(binding))
    (work/'binding'/'installed-files.json').write_bytes(manifest_raw)
    for name in ('binding.json','installed-files.json'):(work/'binding'/name).chmod(0o644)
    engine.once('native-container')
    args=['create','--read-only','--network=none','--cap-drop=ALL','--security-opt=no-new-privileges',
          '--ipc=private','--cgroupns=private','--pids-limit=128','--memory=4294967296','--cpus=2','--tmpfs','/tmp:'+n.TMPFS,
          '--user=0:0','--workdir=/work/repo','--hostname=stage7-sealed-native','--entrypoint=/opt/venv/bin/python']
    for key,value in n.environment_profile().items():args+=['--env',key+'='+value]
    for key,value in {'stage7.request':n.ID,'stage7.nonce':nonce,'stage7.source':request['reviewed_source_sha']}.items():args+=['--label',key+'='+value]
    for key,source in routes.items():
        n.need(source.startswith('/') and ',' not in source and '\n' not in source)
        args+=['--mount','type=bind,src='+source+',dst=/work/'+key+(',readonly' if key in ('repo','binding') else '')]
    cid=engine.call([*args,image['config_digest'],*n.CONTAINER_COMMAND])['_stdout'].decode().strip()
    n.need(n.image._hex(cid));copied=[]
    original_deadline=engine.deadline
    try:
        engine.deadline=min(original_deadline,perf_counter()+n.BUDGET['prestart_seconds'])
        # Prove the executable/stdlib and collector code without starting the image.
        names=['__init__.py','engine_clock_runtime_inventory.py','engine_clock_image_inventory.py','engine_clock_image_installer.py']
        entries=[]
        for name in names:
            raw=n.image.read_regular(root/'scripts'/name)
            entries.append(dict(path='scripts/'+name,kind='file',mode=0o644,nbytes=len(raw),sha256=n.sha(raw)))
        copied.append(engine.copied_tree(cid,'/usr/local/libexec/stage7','stage7',entries,'copied-code'))
        members=n.image.parse(n.image.read_regular(root/'docs/evidence/engine-clock-python-bootstrap/archive-members.json'))['entries']
        copied.append(engine.copied_tree(cid,'/opt/python','python',members,'copied-python'))
        layout=n.image.parse(n.image.read_regular(root/n.image.LAYOUT_PATH))
        copied.append(engine.copied_tree(cid,'/opt/venv/bin/python','python',layout['expected_members']['bin/python3.11'],'copied-executable'))
        engine.deadline=original_deadline
        raw=engine.json(['container','inspect',cid]);n.need(len(raw)==1)
        expected=dict(config_digest=image['config_digest'],nonce=nonce,source_sha=request['reviewed_source_sha'])
        (work/'launch-diagnostics.json').write_bytes(n.canonical(n.launch_diagnostics(raw[0],routes,expected)))
        launch=n.validate_launch(raw[0],routes,expected)
        (work/'launch.json').write_bytes(n.canonical(dict(launch,copied_trees=copied)))
        engine.once('native-start')
        engine.call(['start','--attach',cid],timeout=n.BUDGET['container_seconds'],stdout_limit=n.MIB)
        state=engine.json(['container','inspect','--format','{{json .State}}',cid])
        n.need(state['Status']=='exited' and state['Running'] is False and state['ExitCode']==0 and state['OOMKilled'] is False)
        phase=n.image.parse(n.image.read_regular(work/'output'/'phase.json'))
        n.need(phase['status']==n.recorded_status(request['mode']) and phase['identity']==identity
               and phase['context']==context and phase['official_model_calls']==0 and phase['ort_sessions']==0)
        result=dict(schema='engine-clock-sealed-native-controller-v1',status=n.recorded_status(request['mode']),
                    context=context,identity=identity,launch=launch,copied_trees=copied,state=state,
                    phase_sha256=n.sha(n.image.read_regular(work/'output'/'phase.json')),
                    official_model_calls=0,ort_sessions=0,scientific_result_promoted=False)
        (work/'controller.json').write_bytes(n.canonical(result))
        return result
    except BaseException:
        engine.deadline=original_deadline
        engine.terminate(cid)
        raise



def run(mode):
    root=Path(__file__).resolve().parents[1];started=time.monotonic();operation_started=started
    base=root/n.OUTPUT;out=base/mode;out.mkdir(parents=True,mode=0o700,exist_ok=False)
    work=out/'execution';work.mkdir(mode=0o700)
    stage='producer-authentication';status='FAILED_OR_INCOMPLETE';error_type=None;detail=None
    context=None;control_elapsed=0.;lease=None;stop=started+n.BUDGET['total_seconds']
    try:
        if mode=='canary':
            client=RetainedClient(work/'api',repository=n.REPOSITORY,token=os.environ['GH_TOKEN'],
                deadline=min(stop-12,started+n.BUDGET['download_seconds']),max_requests=n.BUDGET['http_gets'],max_payload_bytes=n.BUDGET['payload_bytes'])
            producer,producer_raw,context=life.authenticate_producer(client,root,os.environ,'native-host')
            lease=life.create_lease(context,life.boot_identity(),started)
            life.write_lease(base/'host-lease.json',lease)
            request=producer;request_raw=producer_raw
            context['lease_sha256']=n.sha(n.canonical(lease))
            life.validate_lease(lease,context,life.boot_identity(),time.monotonic())
        else:
            stage='held-lease-and-control'
            lease=life.read_lease(base/'host-lease.json')
            control_stop=min(started+n.LIFECYCLE['control_seconds'],lease['deadline_monotonic']-12)
            control_client=RetainedClient(work/'control-api',repository=n.REPOSITORY,token=os.environ['GH_TOKEN'],
                deadline=control_stop,max_requests=n.LIFECYCLE['control_http_gets'],max_payload_bytes=n.LIFECYCLE['control_json_bytes'])
            producer,producer_raw,context=life.authenticate_producer(control_client,root,os.environ,'native-host')
            life.validate_lease(lease,context,life.boot_identity(),time.monotonic())
            context['lease_sha256']=n.sha(n.canonical(lease))
            control_head,request,request_raw=life.observe_control(control_client,producer,context,lease,work)
            life.validate_lease(lease,context,life.boot_identity(),time.monotonic())
            context=dict(context,mode='abba',control_head_sha=control_head,request_sha256=n.sha(request_raw))
            control_elapsed=time.monotonic()-started;operation_started=time.monotonic()
            stop=min(lease['deadline_monotonic'],operation_started+n.BUDGET['total_seconds'])
            client=RetainedClient(work/'api',repository=n.REPOSITORY,token=os.environ['GH_TOKEN'],
                deadline=min(stop-12,operation_started+n.BUDGET['download_seconds']),max_requests=n.BUDGET['http_gets'],max_payload_bytes=n.BUDGET['payload_bytes'])
        (work/'consumed-request.json').write_bytes(request_raw)
        (work/'producer-request.json').write_bytes(producer_raw)
        (work/'host-lease.json').write_bytes(n.canonical(lease))
        (work/'source-authentication.json').write_bytes(n.canonical(context))
        with n.image.inventory.core._absolute_deadline(stop-12):
            accepted=None
            if mode=='abba':
                stage='completed-canary-attestor-root-authority'
                input_work=out/'accepted-inputs';input_work.mkdir(mode=0o700)
                accepted=authority.authenticate_canary(client,request,context,input_work)
                n.need(accepted['lease_sha256']==context['lease_sha256'])
            stage='image-authentication'
            old_request=n.image.parse(n.image.read_regular(root/(n.AUTH+'preflight-request.json')))
            directory,receipt,manifest,checked=n.image.authenticate_image(client,old_request,work,root)
            stage='host-memory-qualification'
            with open('/proc/meminfo','rb') as f:memory=host_memory_profile(f.read(65537))
            (work/'host-memory.json').write_bytes(n.canonical(memory))
            stage='engine-qualification';engine=Docker(work/'docker',deadline=stop,source_root=root);engine.qualify(out)
            life.validate_lease(lease,context,life.boot_identity(),time.monotonic())
            if mode=='abba':
                stage='exact-held-host-identity'
                identity_gate(accepted['identity'],n.make_identity(receipt,request['image_evidence']['expected'],engine.host,engine.profile),work/'acceptance-identity.json')
            stage='one-image-load';image=engine.load(directory/'image.tar',receipt['config_digest'],receipt['rootfs_diff_ids'])
            stage='one-native-phase'
            result=launch_phase(engine,image,request,context,receipt,manifest,work,root,accepted,producer=producer,lease=lease)
            status=result['status'];return 0
    except Exception as exc:
        error_type=type(exc).__name__;detail=str(exc)[:512];return 1
    finally:
        report=dict(schema='engine-clock-held-abba-operation-v2',status=status,last_stage=stage,error_type=error_type,
            error_detail=detail,elapsed_seconds=time.monotonic()-started,control_elapsed_seconds=control_elapsed,
            phase_operation_seconds=time.monotonic()-operation_started,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            request_id=n.ID,mode=mode,producer_head_sha=os.environ.get('GITHUB_SHA'),
            control_head_sha=context.get('control_head_sha') if context else None,
            workflow_completion_not_claimed=True,official_model_calls=0,ort_sessions=0,scientific_result_promoted=False)
        if status!=n.recorded_status(mode):report['native_failure_summary']=failure_summary(work,context,os.environ)
        (work/'result.json').write_bytes(n.canonical(report));print(n.canonical(report).decode())


def main():
    try:
        n.need(len(sys.argv)==2 and sys.argv[1] in ('--canary','--abba') and os.environ.get('GITHUB_ACTIONS')=='true'
            and os.environ.get('GITHUB_REPOSITORY')==n.REPOSITORY and os.environ.get('GITHUB_EVENT_NAME')=='push'
            and os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and os.environ.get('GITHUB_REF_NAME')==n.BRANCH
            and os.environ.get('GITHUB_JOB')=='native-host')
        return run('canary' if sys.argv[1]=='--canary' else 'abba')
    except Exception:print('HELD_ABBA_REJECTED');return 1


if __name__=='__main__':raise SystemExit(main())
