"""Admitted ephemeral-CI-only native camera/recorder canary. NO graph mode."""
from pathlib import Path
import argparse
import os
import secrets
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigbench import recorded_worker_canary as c
from bigbench import full_s_recorded_worker as worker
from bigbench import worker_ownership as ownership
from scripts import panda_sdk3_runtime as pins, panda_sdk3_diagnostic as owner
from scripts.sdk3_priority_model_trial import clone


def owned_child_command(args,parent_pid):
    worker._write_receipt(Path(args.out)/'launch.json',dict(parent_pid=parent_pid,
        nonce=args.nonce,seed=c.CASE[0],scenario=c.CASE[1],mode=c.MODE,
        source=args.source,activation=args.activation,run_id=args.run_id,limits=c.LIMITS))
    return [sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--owned-child',
        '--server-owner',str(parent_pid),'--out',args.out,'--nonce',args.nonce,
        '--source',args.source,'--activation',args.activation,'--run-id',args.run_id]


def child(args):
    out=Path(args.out)
    audit=c.ZeroModelAudit()
    report=dict(protocol='recorded-camera-canary-native-v1',status='FAILED',mode=c.MODE,
        pid=os.getpid(),parent_pid=os.getppid(),nonce=args.nonce,seed=c.CASE[0],scenario=c.CASE[1],
        source=args.source,activation=args.activation,run_id=args.run_id,limits=c.LIMITS,
        official_model_processes=0,official_inferences=0,capture_count_bounds=[0,2],
        sensor_perceive_bounds=[0,4],policy_data='SYNTHETIC_STATE_AND_ZERO_ACTION_NO_GRAPH',
        graph_feed_attested=False,**{k:False for k in c.FALSE_FLAGS})
    try:
        ack=ownership.await_parent_ack(out,parent=args.server_owner,nonce=args.nonce,
            seed=c.CASE[0],scene=c.CASE[1],read_owner=c.read_native_ack)
        worker.need(ack.get('mode')==c.MODE and all(ack.get(k)==getattr(args,k) for k in
            ('source','activation','run_id')) and ack.get('limits')==c.LIMITS,'exact parent canary admission required')
        worker.need(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and
            not os.environ.get('LD_PRELOAD') and Path('/tmp/.X11-unix/X99').exists(), 'isolated admitted owned display required')
        worker.need(not any(n.split('.')[0] in ('panda3d','direct','metadrive','onnxruntime') for n in sys.modules),
            'admission must precede native imports')
        worker.need(not Path('/model.onnx').exists() and not Path('/model-deps').exists(), 'no model/dependency mounts permitted')
        sys.addaudithook(audit)
        request=worker._read_receipt(worker.ROOT/c.REQUEST,4*1024**2)
        worker.need(request.get('active') is True and request.get('source')==args.source and
            request.get('mode')==c.MODE and request.get('limits')==c.LIMITS,'sealed mounted request required')
        report['source_map_sha256']=c.check_source_map(worker.ROOT,request['source_map'])
        report['parent_admission_checked']=True
        from scripts.sdk3_four_validation_native import bootstrap
        from scripts.sdk3_priority_model_native import source_stats_after
        core,preload,sdk=bootstrap(report)  # Keep all handles alive until teardown.
        report['source_stats_before']=source_stats_after()
        trial=worker.run_camera_canary_trial(argparse.Namespace(out=out/'observed-trial',
            nonce=args.nonce,seed=c.CASE[0],scenario=c.CASE[1]))
        report['source_stats_after']=source_stats_after()
        report.update(status='CAMERA_RECORDER_CANARY_RECORDED',capture_count_bounds=[2,2],
            sensor_perceive_bounds=[4,4],fixture_policy_audit_bounds=trial['fixture_policy_audit_bounds'])
        worker.need(audit.snapshot()==dict(weight_open_attempts=0,ort_import_attempts=0) and
            'onnxruntime' not in sys.modules,'zero official model activity required')
        return 0
    except BaseException as exc:
        report['failure']=worker._error(exc)
        raise
    finally:
        report.update(zero_model_audit=audit.snapshot(),onnxruntime_loaded='onnxruntime' in sys.modules)
        pins.write(out/'report.json',report)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    parser.add_argument('--source',required=True)
    parser.add_argument('--activation',required=True)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--nonce',default='0'*32)
    parser.add_argument('--owned-child',action='store_true')
    parser.add_argument('--server-owner',type=int)
    args=parser.parse_args(argv)
    worker.need(all(len(v)==40 and all(x in '0123456789abcdef' for x in v) for v in
        (args.source,args.activation)) and args.run_id.isdecimal(),'exact source/activation/run identity required')
    if args.owned_child:return child(args)
    worker.need(args.nonce=='0'*32 and args.server_owner is None,'fresh parent-only canary launch required')
    args.nonce=secrets.token_hex(16)
    args.model_trial=False
    def bounded_wait(child,server,original_limit):
        return owner.wait_child_then_stop_server(child,server,c.LIMITS['child_seconds'])
    return clone(owner.run_with_server,owned_child_command=owned_child_command,
        wait_child_then_stop_server=bounded_wait)(args)


if __name__=='__main__':raise SystemExit(main())
