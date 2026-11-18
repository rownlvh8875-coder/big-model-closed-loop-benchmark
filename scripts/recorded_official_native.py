"""Admitted ephemeral-CI-only native official-model recorded diagnostic; ONE fixed original case."""
from pathlib import Path
import argparse
import hashlib
import os
import secrets
import socket
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigbench import recorded_official_execution as c
from bigbench import full_s_recorded_worker as worker
from bigbench import worker_ownership as ownership
from scripts import panda_sdk3_runtime as pins, panda_sdk3_diagnostic as owner
from bigbench.recorded_official_execution import clone


def owned_child_command(args,parent_pid):
    worker._write_receipt(Path(args.out)/'launch.json',dict(parent_pid=parent_pid,
        nonce=args.nonce,seed=c.CASE[0],scenario=c.CASE[1],mode=c.MODE,
        source=args.source,activation=args.activation,run_id=args.run_id,approval=args.approval,limits=c.LIMITS,dependencies_sha256=args.dependencies_sha256))
    return [sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--owned-child',
        '--server-owner',str(parent_pid),'--out',args.out,'--nonce',args.nonce,
        '--source',args.source,'--activation',args.activation,'--run-id',args.run_id,'--approval',args.approval,'--dependencies-sha256',args.dependencies_sha256]


def invoke_body(args):
    return worker.run_recorded_trial(argparse.Namespace(out=Path(args.out)/'observed-trial',
        nonce=args.nonce,seed=c.CASE[0],scenario=c.CASE[1]))


def model_memory():
    rows={k:int(v.split()[0])*1024 for k,v in (row.split(':',1) for row in Path('/proc/meminfo').read_text().splitlines()) if k=='MemAvailable'}
    maximum=Path('/sys/fs/cgroup/memory.max').read_text().strip()
    current=Path('/sys/fs/cgroup/memory.current').read_text().strip()
    worker.need(maximum.isdecimal() and current.isdecimal(),'observed bounded cgroup-v2 memory required')
    return c.model_memory_gate(rows['MemAvailable'],int(maximum),int(current))


def finalize_child(out,report,primary):
    secondary=report.setdefault('secondary_errors',[])
    def lifecycle():
        try:life=worker._read_receipt(out/'observed-trial/recorded-trial-lifecycle.json')
        except FileNotFoundError:return
        worker.need(all(life.get(k)==report[k] for k in ('pid','parent_pid','nonce','seed','scenario')),'original lifecycle identity required')
        from bigbench.full_s_recorded_receiver import _lifecycle
        _lifecycle(life);report.update(c.activity_bounds(life))
    def trial_digest():
        try:report['recorded_trial_sha256']=pins.digest(out/'observed-trial/recorded-trial.json')
        except FileNotFoundError:report['recorded_trial_sha256']=None
    c.finalize_preserving_primary(primary,[lifecycle,trial_digest,lambda:pins.write(out/'report.json',report)],secondary)


def child(args):
    out=Path(args.out)
    report=dict(protocol='recorded-official-native-v1',status='FAILED',mode=c.MODE,
        pid=os.getpid(),parent_pid=os.getppid(),nonce=args.nonce,seed=c.CASE[0],scenario=c.CASE[1],
        source=args.source,activation=args.activation,run_id=args.run_id,approval=args.approval,limits=c.LIMITS,
        official_model_process_bounds=[0,1],official_inference_bounds=[0,600],failure=None,
        container_hostname=socket.gethostname(),dependencies_sha256=args.dependencies_sha256,**{k:False for k in c.FALSE_FLAGS})
    primary=None
    try:
        ack=ownership.await_parent_ack(out,parent=args.server_owner,nonce=args.nonce,
            seed=c.CASE[0],scene=c.CASE[1],read_owner=c.read_native_ack)
        worker.need(ack.get('mode')==c.MODE and all(ack.get(k)==getattr(args,k) for k in
            ('source','activation','run_id','approval','dependencies_sha256')) and ack.get('limits')==c.LIMITS,'exact parent canary admission required')
        worker.need(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and
            not os.environ.get('LD_PRELOAD') and Path('/tmp/.X11-unix/X99').exists(), 'isolated admitted owned display required')
        worker.need(not any(n.split('.')[0] in ('panda3d','direct','metadrive','onnxruntime') for n in sys.modules),
            'admission must precede native imports')
        request=worker._read_receipt(worker.ROOT/c.REQUEST,4*1024**2)
        worker.need(request.get('active') is True and request.get('source')==args.source and
            request.get('mode')==c.MODE and request.get('limits')==c.LIMITS and
            request.get('approval_sha')==args.approval,'sealed mounted request required')
        report['source_map_sha256']=c.check_source_map(worker.ROOT,request['source_map'])
        from bigbench import recorded_official_dependencies as dependencies
        descriptor_raw=worker._receipt_bytes(out/'model-dependencies.json',4*1024**2)
        worker.need(hashlib.sha256(descriptor_raw).hexdigest()==args.dependencies_sha256,'exact admitted dependency descriptor required')
        descriptor=worker._read_receipt(out/'model-dependencies.json',4*1024**2)
        report['dependencies']=dependencies.verify(Path('/model-deps'),descriptor)
        worker.need(Path('/model.onnx').stat().st_size==768750198 and pins.digest('/model.onnx')==pins.MODEL_SHA,'original official model bytes required')
        report['model_sha256']=pins.MODEL_SHA
        report['model_nbytes']=768750198
        report['parent_admission_checked']=True
        from scripts.sdk3_four_validation_native import bootstrap
        from scripts.sdk3_priority_model_native import source_stats_after
        core,preload,sdk=bootstrap(report)  # Retain all handles through teardown.
        sys.path.insert(0,'/model-deps')  # No site hooks; only after admission/byte checks.
        report['source_stats_before']=source_stats_after()
        report['model_memory']=model_memory()
        invoke_body(args)  # Frozen worker constructs the original real policy ONCE.
        report['source_stats_after']=source_stats_after()
        report.update(status='OFFICIAL_RECORDED_DIAGNOSTIC_RETURNED')
        return 0
    except BaseException as exc:
        primary=exc
        report['status']='FAILED'
        report['failure']=worker._error(exc)
        raise
    finally:
        finalize_child(out,report,primary)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    parser.add_argument('--source',required=True)
    parser.add_argument('--activation',required=True)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--approval',required=True)
    parser.add_argument('--dependencies-sha256',required=True)
    parser.add_argument('--nonce',default='0'*32)
    parser.add_argument('--owned-child',action='store_true')
    parser.add_argument('--server-owner',type=int)
    args=parser.parse_args(argv)
    worker.need(all(len(v)==40 and all(x in '0123456789abcdef' for x in v) for v in
        (args.source,args.activation,args.approval)) and args.run_id.isdecimal(),'exact source/activation/run identity required')
    if args.owned_child:return child(args)
    worker.need(args.nonce=='0'*32 and args.server_owner is None,'fresh parent-only official launch required')
    args.nonce=secrets.token_hex(16)
    args.model_trial=True
    def bounded_wait(child,server,original_limit):
        return owner.wait_child_then_stop_server(child,server,c.LIMITS['child_seconds'])
    code=None;failure=None
    try:
        code=clone(owner.run_with_server,owned_child_command=owned_child_command,
            wait_child_then_stop_server=bounded_wait)(args)
        return code
    except BaseException as exc:
        failure=worker._error(exc)
        raise
    finally:
        out=Path(args.out)
        final=dict(protocol='recorded-official-parent-completion-v1',
            status='NATIVE_CHILD_REAPED' if code is not None and failure is None else 'FAILED',failure=failure,
            returncode=code,parent_pid=os.getpid(),pid=None,nonce=args.nonce,source=args.source,
            activation=args.activation,run_id=args.run_id,approval=args.approval,mode=c.MODE,
            container_hostname=socket.gethostname(),native_child_sha256=None,report_sha256=None)
        secondary=final.setdefault('secondary_errors',[])
        def hashes():
            for name,key in (('native-child.json','native_child_sha256'),('report.json','report_sha256')):
                try:
                    raw=worker._receipt_bytes(out/name)
                    final[key]=hashlib.sha256(raw).hexdigest()
                    if name=='native-child.json':final['pid']=worker._read_receipt(out/name).get('pid')
                except FileNotFoundError:pass
        primary=RuntimeError(failure or ('native child returned '+str(code))) if failure is not None or code!=0 else None
        c.finalize_preserving_primary(primary,[hashes,lambda:pins.write(out/'parent-completion.json',final)],secondary)



if __name__=='__main__':raise SystemExit(main())
