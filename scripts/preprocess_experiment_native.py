"""Admitted ephemeral-CI-only experimental input arm; never selected-host execution."""
from pathlib import Path
import argparse,hashlib,os,secrets,socket,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigbench import preprocess_experiment_protocol as c
from bigbench.full_s_recorded_worker import need,_read_receipt,_write_receipt
from bigbench import worker_ownership as ownership
from scripts import panda_sdk3_runtime as pins,panda_sdk3_diagnostic as owner
from scripts.recorded_official_native import model_memory


def owned_child_command(args,parent_pid):
    _write_receipt(Path(args.out)/'launch.json',dict(parent_pid=parent_pid,nonce=args.nonce,
        seed=args.seed,scenario=args.scenario,variant=args.variant,mode=c.MODE,limits=c.LIMITS,
        source=args.source,activation=args.activation,run_id=args.run_id,approval=args.approval,
        dependencies_sha256=args.dependencies_sha256))
    return [sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--owned-child',
        '--server-owner',str(parent_pid),'--out',args.out,'--nonce',args.nonce,
        '--source',args.source,'--activation',args.activation,'--run-id',args.run_id,'--approval',args.approval,
        '--dependencies-sha256',args.dependencies_sha256,'--seed',str(args.seed),'--scenario',args.scenario,'--variant',args.variant]


def child(args):
    out=Path(args.out)
    r=dict(protocol=c.TRIAL_PROTOCOL,status='FAILED',mode=c.MODE,pid=os.getpid(),parent_pid=os.getppid(),
        nonce=args.nonce,seed=args.seed,scenario=args.scenario,variant=args.variant,
        source=args.source,activation=args.activation,approval=args.approval,run_id=args.run_id,
        dependencies_sha256=args.dependencies_sha256,container_hostname=socket.gethostname(),
        model_process_bounds=[0,0],inference_bounds=[0,0],provider_closed=False,failure=None,
        secondary_errors=[],**{k:False for k in c.FALSE_FLAGS})
    primary=None;provider=None;inner=None;inputs=None;core=preload=sdk=None
    def progress(row):
        r.update(inference_bounds=row['inference_bounds'],progress=row)
        pins.write(out/'progress.json',r)
    try:
        ack=ownership.await_parent_ack(out,parent=args.server_owner,nonce=args.nonce,
            seed=args.seed,scene=args.scenario,read_owner=c.read_native_ack)
        need(ack.get('variant')==args.variant and all(ack.get(k)==getattr(args,k) for k in
            ('source','activation','approval','run_id','dependencies_sha256')),'exact sealed experimental admission required')
        need(sys.platform=='linux' and sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and
            not os.environ.get('LD_PRELOAD') and Path('/tmp/.X11-unix/X99').exists(),'admitted isolated Linux display required')
        need(not any(n.split('.')[0] in ('panda3d','direct','metadrive','onnxruntime') for n in sys.modules),
            'native admission must precede native imports')
        request=_read_receipt(c.ROOT/c.REQUEST,4*1024**2)
        need(request.get('active') is True and request.get('source')==args.source and
            request.get('approval_sha')==args.approval and request.get('mode')==c.MODE and
            request.get('limits')==c.LIMITS,'mounted exact source/cohort request required')
        r['source_map_sha256']=c.check_source_map(c.ROOT,request['source_map'])
        from bigbench import recorded_official_dependencies as dependencies
        raw=(out/'model-dependencies.json').read_bytes()
        need(len(raw)<=4*1024**2 and hashlib.sha256(raw).hexdigest()==args.dependencies_sha256,
            'bounded byte-bound original runtime descriptor required')
        r['dependencies']=dependencies.verify(Path('/model-deps'),_read_receipt(out/'model-dependencies.json',4*1024**2))
        need(Path('/model.onnx').stat().st_size==768750198 and pins.digest('/model.onnx')==pins.MODEL_SHA,
            'original model extent and SHA required')
        r.update(model_sha256=pins.MODEL_SHA,model_nbytes=768750198)
        from scripts.sdk3_four_validation_native import bootstrap
        core,preload,sdk=bootstrap(r)
        sys.path.insert(0,'/model-deps')
        from scripts.sdk3_priority_model_native import source_stats_after
        r['source_stats_before']=source_stats_after()
        from bigbench.preprocess_experiment import policy_class,LiveInput
        r['model_memory']=model_memory()
        r['model_process_bounds']=[0,1];pins.write(out/'progress.json',r)
        inner=policy_class()(Path('/model.onnx'),c.ROOT/'model_specs/md-v3.json',None)
        r['model_process_bounds']=[1,1]
        import onnxruntime as ort
        r.update(real_session=isinstance(inner.session,ort.InferenceSession),
            injected_session=inner._injected_session,providers=inner.session.get_providers(),ort_version=ort.__version__)
        from scripts.sdk3_four_validation_trial import _world,driver_info
        from bigbench.native_model_campaign import NativeWorldCamera
        from bigbench.optical_calibration import intrinsics_from_panda_lens
        from bigbench.model_world_frame import WorldFramePolicyAdapter,SOURCE_ACTION_FRAME
        from bigbench.full_s_validation import run_full_s
        from dataclasses import asdict
        provider,lanes,terrain=_world(args.seed,args.scenario)
        r.update(driver=driver_info(provider),terrain=terrain)
        intrinsics={role:intrinsics_from_panda_lens(provider.env.engine.sensors['bigbench_'+role].get_lens(),964,604)
            for role in ('road','wide')}
        r['intrinsics']={role:asdict(k) for role,k in intrinsics.items()}
        inputs=LiveInput(NativeWorldCamera(provider),intrinsics,args.variant,out)
        inner.preparer=inputs
        policy=WorldFramePolicyAdapter(inner,source_action_frame=SOURCE_ACTION_FRAME)
        r['trajectory']=run_full_s(policy,inputs,lanes,seed=args.seed,scene=args.scenario,max_steps=600,progress=progress)
        r['initial_recurrent_sha256']=inner.initial_recurrent_sha256
        r['trajectory'].update(experimental_policy_scope=c.POLICY_SCOPE,input_variant=args.variant,
            initial_recurrent_sha256=inner.initial_recurrent_sha256,policy_class=type(inner).__module__+'.'+type(inner).__qualname__)
        r['inference_bounds']=r['trajectory']['actual_inference_bounds']
        need(r['trajectory']['trial_completed'] is True,r['trajectory'].get('error') or 'full original trajectory did not complete')
        r['status']='RETURNED'
        return 0
    except BaseException as exc:
        primary=exc;r['status']='FAILED';r['failure']=type(exc).__name__+': '+str(exc)[:2048]
        raise
    finally:
        def close():
            if provider is not None:provider.close();r['provider_closed']=True
        def audit():
            if inputs is not None:r['input_rows']=inputs.rows
            if inner is not None:
                from scripts.sdk3_priority_model_native import source_stats_after
                r['source_stats_after']=source_stats_after()
        c.finalize_preserving_primary(primary,[close,audit,lambda:pins.write(out/'report.json',r)],r['secondary_errors'])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('out','source','activation','approval','run-id','dependencies-sha256','scenario','variant'):
        p.add_argument('--'+name,required=True)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--nonce',default='0'*32)
    p.add_argument('--owned-child',action='store_true');p.add_argument('--server-owner',type=int)
    a=p.parse_args(argv);c.validate_trial(a.seed,a.scenario,a.variant)
    need(all(len(v)==40 and all(x in '0123456789abcdef' for x in v) for v in (a.source,a.activation,a.approval)) and
         a.run_id.isdecimal(),'typed source/run identity required')
    if a.owned_child:return child(a)
    need(a.nonce=='0'*32 and a.server_owner is None,'fresh parent-only launch required')
    a.nonce=secrets.token_hex(16);a.model_trial=True;code=None;primary=None;secondary=[]
    def wait(child,server,original):return owner.wait_child_then_stop_server(child,server,9000)
    try:
        code=c.clone(owner.run_with_server,owned_child_command=owned_child_command,wait_child_then_stop_server=wait)(a)
        need(code==0,'owned experimental child failed')
        return code
    except BaseException as exc:primary=exc;raise
    finally:
        out=Path(a.out)
        receipt=dict(protocol='preprocess-intervention-parent-v1',returncode=code,parent_pid=os.getpid(),nonce=a.nonce,
            source=a.source,activation=a.activation,run_id=a.run_id,seed=a.seed,scenario=a.scenario,variant=a.variant,
            approval=a.approval,dependencies_sha256=a.dependencies_sha256,failure=None if primary is None else str(primary),secondary_errors=secondary)
        def hashes():
            for name in ('report','native-child'):
                receipt[name.replace('-','_')+'_sha256']=pins.digest(out/(name+'.json'))
        c.finalize_preserving_primary(primary,[hashes,lambda:pins.write(out/'parent-completion.json',receipt)],secondary)


if __name__=='__main__':raise SystemExit(main())
