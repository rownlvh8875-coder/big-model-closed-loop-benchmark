"""Isolated same-namespace parent/child for the new sealed native canary."""
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import re
import secrets
import select
import stat
import subprocess
import sys
import threading
from time import perf_counter
import uuid

if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import engine_clock_sealed_native_v5 as n
from scripts import engine_clock_image_inventory as inventory

ROOT=Path('/work/repo')
BINDING=Path('/work/binding')
OUT=Path('/work/output')


def memory_snapshot(root=Path('/sys/fs/cgroup')):
    """Non-atomic cgroup-v2 charge/counter metadata; never an RSS measurement."""
    root=Path(root);n.need(not root.is_symlink() and root.is_dir())
    def read(name):
        try:fd=os.open(root/name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
        except OSError:raise ValueError('CGROUP_READ_REJECTED') from None
        try:
            n.need(stat.S_ISREG(os.fstat(fd).st_mode));raw=bytearray()
            while True:
                block=os.read(fd,min(4096,8193-len(raw)))
                if not block:break
                raw.extend(block);n.need(len(raw)<=8192)
            return raw.decode('ascii')
        finally:os.close(fd)
    def number(text):
        value=text.strip();n.need(re.fullmatch('[0-9]{1,19}',value) is not None)
        result=int(value);n.need(0<=result<2**63);return result
    maximum=number(read('memory.max'));n.need(maximum==n.BUDGET['memory_bytes'])
    current=number(read('memory.current'));peak=number(read('memory.peak'));events={}
    for line in read('memory.events').splitlines():
        parts=line.split();n.need(len(parts)==2 and re.fullmatch('[a-z_]{1,64}',parts[0]) is not None and parts[0] not in events)
        events[parts[0]]=number(parts[1]);n.need(len(events)<=32)
    n.need({'oom','oom_kill'}<=set(events))
    return dict(schema='native-cgroup-memory-v1',max_bytes=maximum,current_bytes=current,peak_bytes=peak,
                events=events,cgroup_inode=root.stat().st_ino,non_atomic=True,peak_is_rss=False)


def require_no_oom(before,after):
    n.need(before['max_bytes']==after['max_bytes']==n.BUDGET['memory_bytes']
           and before['cgroup_inode']==after['cgroup_inode']
           and all(before['events'][key]==after['events'][key]==0 for key in ('oom','oom_kill')))


def write(path,value):
    raw=n.canonical(value);n.need(len(raw)<=n.BUDGET['ledger_bytes'])
    with Path(path).open('xb') as f:f.write(raw)


def maps_snapshot():
    raw=Path('/proc/self/maps').read_bytes();n.need(len(raw)<=n.MIB)
    paths=set()
    for line in raw.decode().splitlines():
        parts=line.split(None,5)
        if len(parts)==6 and parts[5].startswith('/'):
            path=parts[5];n.need(not path.endswith(' (deleted)'))
            actual=os.path.realpath(path)
            n.need(actual.startswith(('/opt/python/','/opt/venv/','/usr/lib/','/usr/local/lib/')))
            paths.add(actual)
    return sorted(paths)


def module_origins():
    origins={}
    for name,module in list(sys.modules.items()):
        path=getattr(module,'__file__',None)
        if path is not None:
            actual=os.path.realpath(path)
            n.need(actual.startswith(('/work/repo/','/opt/python/','/opt/venv/')))
            origins[name]=actual
    n.need(not any(k.split('.',1)[0]=='onnxruntime' for k in sys.modules))
    return origins


def compact_inventory(result,expected_raw):
    """Keep actual verification evidence without duplicating its 8MiB manifest."""
    n.need(result['complete'] is True and result['status']=='INSTALLED_FILES_MATCH'
           and result['canonical_manifest_sha256']==n.sha(expected_raw)
           and inventory.core._canonical(result['inventory'])==expected_raw)
    summary={key:value for key,value in result.items() if key!='inventory'}
    summary['inventory_manifest']=dict(path='/work/binding/installed-files.json',
        nbytes=len(expected_raw),sha256=n.sha(expected_raw))
    n.need(len(n.canonical(summary))<n.BUDGET['ledger_bytes']//2)
    return summary


def preflight(role):
    started=perf_counter()
    n.need(sys.executable=='/opt/venv/bin/python' and sys.version_info[:3]==(3,11,18)
           and sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode
           and os.geteuid()==0 and threading.current_thread() is threading.main_thread())
    n.check_environment(os.environ,role)
    launch_environment=dict(os.environ)
    n.need(not any(k.split('.',1)[0] in {'numpy','cv2','panda3d','metadrive','onnxruntime'} for k in sys.modules))
    raw=n.image.read_regular(BINDING/'binding.json');binding=n.image.parse(raw)
    request=n.validate_request(binding['request'],ROOT)
    n.verify_sources(ROOT,request['source_closure'])
    n.need(n.sha(n.image.read_regular(ROOT/n.REQUEST))==binding['context']['request_sha256'])
    n.need(n.image.parse(n.image.read_regular(ROOT/n.REQUEST))==request)
    expected_raw=n.image.read_regular(BINDING/'installed-files.json')
    n.need(n.sha(expected_raw)==binding['receipt']['installed_files_sha256'])
    expected=inventory.core.validate_inventory(n.image.parse(expected_raw))
    maps=maps_snapshot()
    observation=dict(python_version='.'.join(str(v) for v in sys.version_info[:3]),executable=sys.executable,
        executable_realpath=os.path.realpath(sys.executable),stdlib_realpath=os.path.realpath(os.__file__),
        loaded_libpython_realpaths=[p for p in maps if '/libpython3.11.so' in p],
        isolated=True,no_site=True,dont_write_bytecode=True,imported_forbidden=[])
    layout=n.image.parse(n.image.read_regular(ROOT/n.image.LAYOUT_PATH))
    prefix=inventory.verify_prefix(Path('/'),observation,expected_members=layout['expected_members'])
    result=inventory.verify_inventory(Path('/'),expected,deadline=started+n.BUDGET['inventory_seconds'])
    n.need(result['complete'] is True and result['canonical_manifest_sha256']==n.sha(expected_raw))
    result=compact_inventory(result,expected_raw)
    host=inventory.collect_host_profile();n.need(host==binding['host'])
    # Explicit isolated path selection, no site/.pth execution.
    package='/opt/venv/lib/python3.11/site-packages'
    n.need(package not in sys.path);sys.path.append(package)
    import cv2
    wanted={'numpy':'2.4.6','opencv-python-headless':'5.0.0.93','panda3d':'1.10.13','metadrive-simulator':'0.4.3'}
    n.need(all(importlib.metadata.version(k)==v for k,v in wanted.items()) and cv2.__version__=='5.0.0')
    n.need(not any(d.metadata.get('Name','').lower()=='onnxruntime' for d in importlib.metadata.distributions()))
    n.check_post_import_environment(os.environ,role)
    identity=n.make_identity(binding['receipt'],request['image_evidence']['expected'],host,binding['engine'])
    n.need(identity==binding['identity'])
    # Also enforce immutable old protected-source pins, without invoking its gates.
    from bigbench import first_divergence as capture
    capture.source_snapshot()
    memory=memory_snapshot();require_no_oom(memory,memory)
    return binding,n.sha(raw),identity,dict(inventory=result,prefix=prefix,maps_before_native=maps,memory_before=memory,
           elapsed_seconds=perf_counter()-started,launch_environment=launch_environment,environment=dict(os.environ))


def consume_fd(nonce,binding_sha,identity_sha):
    text=os.environ.pop('FIRST_DIVERGENCE_TRIAL_FD',None)
    n.need(text is not None and text.isdecimal() and int(text)>=10)
    fd=int(text);stop=perf_counter()+10.;raw=bytearray()
    try:
        n.need(stat.S_ISFIFO(os.fstat(fd).st_mode));os.set_blocking(fd,False)
        while True:
            left=stop-perf_counter();n.need(left>0)
            ready,_,_=select.select([fd],[],[],left);n.need(ready)
            block=os.read(fd,4097-len(raw))
            if not block:break
            raw.extend(block);n.need(len(raw)<=4096)
    finally:os.close(fd)
    p=n.image.parse(raw);current=os.getpid();ancestors=[]
    for _ in range(32):
        status=Path('/proc/'+str(current)+'/status').read_text()
        current=int(status.split('PPid:\t',1)[1].splitlines()[0]);ancestors.append(current)
        if current in (0,1,p['parent_pid']):break
    os.kill(p['parent_pid'],0)
    return n.validate_permit(p,ancestors=ancestors,group=os.getpgid(0),nonce=nonce,
                             binding_sha=binding_sha,identity_sha=identity_sha)


def capture_case(permit,binding):
    from scripts import engine_clock_native as old
    from bigbench import native_model_campaign as campaign
    from bigbench.curved_lane_scenarios import SCENARIOS
    from bigbench.kinematics import AgentState
    from bigbench.metadrive_camera import NativeMetaDriveProvider
    from bigbench.policies import ModelObservation
    capture=old.capture;out=OUT/'case_00'
    collector=capture.CaptureCollector('retention',payload_cap_bytes=old.RETENTION_CAP,max_captures=6)
    n.need(capture.capture_payload_estimate(6,extra_retained_bytes=65536)<=old.RETENTION_CAP)
    data=dict(schema=old.CASE_SCHEMA,status='FAILED_OR_INCOMPLETE',phase='canary',index=0,clock_enabled=True,repeat=0,
              nonce=permit['nonce'],parent_pid=permit['parent_pid'],parent_uuid=permit['parent_uuid'],
              process_id=os.getpid(),process_uuid=uuid.uuid4().hex,process_group=os.getpgid(0),
              context=binding['context'],source_snapshot=binding['request']['source_closure'],runtime=binding['identity'],
              request_sha256=binding['context']['request_sha256'],protocol=old.PROTOCOL,claims=old.CLAIMS,limitation=old.LIMITATION,
              provider_attempted=False,provider_constructed=False,provider_closed=False,provider_lower_bound=0,provider_upper_bound=1,
              texture_markers_enabled=True,main_thread_id=threading.get_ident(),clock_trace={},markers=[],capture_rows=[],accepted=[],
              capture_count=0,observed_reads=0,marker_reads=0,retained_payload_bytes=0,payload_charged_bytes=0,error=None,cleanup_errors=[])
    disk=old.oldmodel._StorageBudget(old.PAYLOAD_CAP);provider=None
    resource.setrlimit(resource.RLIMIT_FSIZE,(old.PAYLOAD_CAP,old.PAYLOAD_CAP))
    try:
        with inventory.core._absolute_deadline(perf_counter()+n.BUDGET['native_seconds']):
            data['provider_attempted']=True
            provider=NativeMetaDriveProvider(seed=20261109,map_config=SCENARIOS['s_curve_left_right'].map_config())
            data['provider_constructed']=True;data['provider_lower_bound']=1
            with old.marker_scope(provider,True,data['markers']),old.clock.camera_clock_scope(provider,True,data['clock_trace'],max_pairs=6),capture.capture_scope('retention',collector):
                camera=campaign.NativeWorldCamera(provider)
                for pose in old.POSES:
                    pair=camera.capture(AgentState(**pose))
                    collector.accept_observation(ModelObservation(pair.road,8.,pose['t'],wide_frame=pair.wide))
    except BaseException as exc:data['error']=old._detail(exc)
    finally:
        if provider is not None:
            try:provider.close();data['provider_closed']=True;collector.mark_closed()
            except BaseException as exc:data['cleanup_errors'].append(old._detail(exc))
        data.update(capture_count=collector.capture_count,capture_rows=collector.capture_rows,
                    observed_reads=len(data['markers']),marker_reads=sum((r['before'] is not None)+(r['after'] is not None) for r in data['markers']),
                    retained_payload_bytes=collector.payload_bytes)
        if data['provider_closed']:
            try:data['accepted']=collector.serialize_captures(out,write_budget=disk)
            except BaseException as exc:data['cleanup_errors'].append(old._detail(exc))
        elif collector.records:
            evidence=dict(schema='texture-marker-closure-unconfirmed-v1',status='CLOSURE_UNCONFIRMED_CPU_SNAPSHOTS',provider_closed=False,
                association='ALREADY_ACCEPTED_CPU_RAW_AND_ACTUAL_CANVAS_CLOSURE_UNCONFIRMED',complete=False,rows=[],error=None)
            data['closure_unconfirmed_snapshots']=evidence
            try:old._persist_unclosed_snapshots(collector,out,disk,evidence)
            except BaseException as exc:data['cleanup_errors'].append(old._detail(exc))
        data['payload_charged_bytes']=disk.charged
    if data['error'] is None and not data['cleanup_errors']:data['status']='CLOCK_CAMERA_REPLAY_RECORDED'
    else:old._failure_prefix(collector,out,data)
    old._write(out/'case.json',data)
    return data


def child(nonce):
    # Check exact environment before consuming its only FD.
    n.check_environment(os.environ,'child');n.need('DISPLAY' in os.environ and 'XAUTHORITY' in os.environ)
    fdtext=os.environ['FIRST_DIVERGENCE_TRIAL_FD']
    binding,bsha,identity,proof=preflight('child')
    permit=consume_fd(nonce,bsha,identity['core_sha256'])
    # Record consumed route without restoring the authorization environment.
    proof.update(permit=permit,authorization_fd=int(fdtext),binding_sha256=bsha,identity=identity)
    write(OUT/'child-admission.json',proof)
    data=capture_case(permit,binding)
    memory_after=memory_snapshot();write(OUT/'child-memory-after.json',memory_after)
    require_no_oom(proof['memory_before'],memory_after)
    write(OUT/'child-loaded-files.json',dict(maps=maps_snapshot(),modules=module_origins()))
    return 0 if data['status']=='CLOCK_CAMERA_REPLAY_RECORDED' else 1


def build_child_environment(proof,fd):
    """Fresh exec uses the validated snapshot, never mutated parent globals."""
    n.need(type(fd) is int and fd>=10)
    launch=dict(proof['launch_environment']);n.check_environment(launch,'parent')
    result=dict(launch,FIRST_DIVERGENCE_TRIAL_FD=str(fd),MESA_SHADER_CACHE_DIR='/work/cache/case_00')
    n.check_environment(result,'child')
    return result


def parent():
    started=perf_counter();binding,bsha,identity,proof=preflight('parent')
    write(OUT/'parent-admission.json',dict(proof,identity=identity,binding_sha256=bsha))
    from scripts import engine_clock_native as old
    old.oldmodel._enable_subreaper()
    parent_uuid=uuid.uuid4().hex;nonce=secrets.token_hex(32)
    case=OUT/'case_00';case.mkdir();cache=Path('/work/cache/case_00');cache.mkdir()
    row=dict(index=0,clock_enabled=True,nonce=nonce,launcher_pid=None,process_group=None,exit_code=None,
             reaped=False,group_gone=False,error=None,cleanup_errors=[],provider_lower_bound=0,provider_upper_bound=1,
             storage=dict(old.LIMITS,log_bytes=0,limit_error=None),cache_before=old._cache_inventory(cache),cache_after=None)
    readfd=writefd=lowfd=None;process=bounded=None;sink=None
    try:
        sink=old.oldmodel._LogSink(case/'process.log',n.BUDGET['log_bytes'])
        lowfd,writefd=os.pipe();readfd=fcntl.fcntl(lowfd,fcntl.F_DUPFD_CLOEXEC,10);os.close(lowfd);lowfd=None
        environment=build_child_environment(proof,readfd)
        command=['/usr/bin/xvfb-run','-a',sys.executable,'-I','-S','-B',str(ROOT/'scripts/engine_clock_sealed_native_container_v5.py'),'child',nonce]
        process=subprocess.Popen(command,cwd=ROOT,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(readfd,))
        row.update(launcher_pid=process.pid,process_group=process.pid)
        bounded=old.oldmodel._BoundedChild(process,sink,row['storage']);os.close(readfd);readfd=None
        permit=dict(schema='engine-clock-sealed-native-permit-v1',parent_pid=os.getpid(),parent_uuid=parent_uuid,
                    process_group=process.pid,nonce=nonce,binding_sha256=bsha,identity_sha256=identity['core_sha256'])
        raw=n.canonical(permit);n.need(len(raw)<=4096);n.need(os.write(writefd,raw)==len(raw));os.close(writefd);writefd=None
        row['exit_code']=bounded.wait(timeout=n.BUDGET['child_seconds'])
        n.need(row['exit_code']==0)
    except BaseException as exc:row['error']=old._detail(exc)
    finally:
        for fd in (lowfd,readfd,writefd):
            if fd is not None:os.close(fd)
        if process is not None:
            row['cleanup_errors'].extend(old.oldmodel._terminate_group(process))
            row.update(reaped=process.poll() is not None,group_gone=old._group_gone(process.pid))
        if bounded is not None:
            try:bounded.drain_available()
            except BaseException as exc:row['cleanup_errors'].append(old._detail(exc))
            bounded.close_output();row['cleanup_errors'].extend(bounded.output_cleanup_errors)
        elif sink is not None:sink.close()
    memory_after=memory_snapshot();write(OUT/'parent-memory-after.json',memory_after)
    try:
        require_no_oom(proof['memory_before'],memory_after)
        row['cache_after']=old._cache_inventory(cache)
        n.need(row['cache_after']['files']>0 and row['error'] is None and not row['cleanup_errors'] and row['reaped'] and row['group_gone'])
        admission=n.image.parse(n.image.read_regular(OUT/'child-admission.json'))
        n.need(admission['identity']==identity and admission['binding_sha256']==bsha and admission['permit']==permit)
        case_binding=dict(phase='canary',parent_pid=os.getpid(),parent_uuid=parent_uuid,
            context=binding['context'],source_snapshot=binding['request']['source_closure'],runtime=identity,
            request_sha256=binding['context']['request_sha256'])
        data=old._read(case/'case.json');old._validate_case(case,data,row,case_binding)
        for key in ('provider_lower_bound','provider_upper_bound'):row[key]=data[key]
    except BaseException as exc:
        if row['error'] is None:row['error']=old._detail(exc)
    write(OUT/'parent-loaded-files.json',dict(maps=maps_snapshot(),modules=module_origins()))
    report=dict(schema='engine-clock-sealed-native-phase-v1',status='SEALED_NATIVE_CANARY_RECORDED' if row['error'] is None else 'FAILED_OR_INCOMPLETE',
                context=binding['context'],identity=identity,parent_pid=os.getpid(),parent_uuid=parent_uuid,
                binding_sha256=bsha,launch=row,elapsed_seconds=perf_counter()-started,budget=n.BUDGET,native_budget=n.NATIVE_BUDGET,
                official_model_calls=0,ort_sessions=0,scientific_result_promoted=False)
    write(OUT/'phase.json',report)
    return 0 if report['status']=='SEALED_NATIVE_CANARY_RECORDED' else 1


def main():
    try:
        n.need(Path(__file__)==ROOT/'scripts/engine_clock_sealed_native_container_v5.py' and sys.executable=='/opt/venv/bin/python')
        n.need(len(sys.argv) in (2,3))
        if sys.argv[1]=='parent' and len(sys.argv)==2:return parent()
        if sys.argv[1]=='child' and len(sys.argv)==3 and n.image._hex(sys.argv[2]):return child(sys.argv[2])
        n.need(False)
    except BaseException as exc:
        # Preserve bounded errors even before a case/phase ledger exists.
        if OUT.is_dir():
            try:write(OUT/('failure-'+str(os.getpid())+'.json'),dict(status='FAILED_OR_INCOMPLETE',error_type=type(exc).__name__,detail=str(exc)[:1500]))
            except Exception:pass
        print('SEALED_NATIVE_REJECTED');return 1


if __name__=='__main__':raise SystemExit(main())
