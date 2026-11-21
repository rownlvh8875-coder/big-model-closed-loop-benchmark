"""One owned Linux SDK3 process for observing the registered steering window."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bigbench import recorded_official_dependencies as deps
from bigbench import sdk3_steering_contract as contract
from bigbench.recorded_official_execution import clone
from scripts import panda_sdk3_diagnostic as owner
from scripts import panda_sdk3_runtime as pins
from scripts.recorded_official_native import model_memory
from scripts.sdk3_four_validation_native import bootstrap
from scripts.sdk3_four_validation_trial import atomic_json


def child(args):
    out = Path(args.out)
    report = dict(protocol='sdk3-steering-plan-v1', status='FAILED', pid=os.getpid(),
                  nonce=args.nonce, seed=args.seed, scenario=args.scenario, variant=contract.VARIANT,
                  source=args.source, activation=args.activation, run_id=args.run_id, provider_closed=False)
    life = dict(pid=os.getpid(), nonce=args.nonce, model_process_bounds=[0,0], inference_bounds=[0,0])
    lifecycle_path = out/'model-lifecycle.json'
    atomic_json(lifecycle_path,life)

    def progress(update):
        life.update(update)
        atomic_json(lifecycle_path,life)

    provider = inputs = None
    try:
        pins.need(args.server_owner == os.getppid() and Path('/tmp/.X11-unix/X99').exists(), 'owned display required')
        pins.need(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and not os.environ.get('LD_PRELOAD'),
                  'original isolated worker settings')
        request = json.loads((Path(__file__).resolve().parents[1]/contract.REQUEST).read_text())
        pins.need(request == {'source':args.source, 'limits':contract.LIMITS, 'mode':'STEERING_PLAN_RETENTION'},
                  'exact mounted steering request')
        report['effective_resources'] = contract.live_limits()
        dependency_file = out/'model-dependencies.json'
        pins.need(pins.digest(dependency_file)==args.dependencies_sha, 'bound dependency descriptor')
        deps.verify(Path('/model-deps'),json.loads(dependency_file.read_text()))
        model = Path('/model.onnx')
        pins.need(model.stat().st_size==768750198 and pins.digest(model)==pins.MODEL_SHA, 'official weights digest')
        report['model_sha256'] = pins.MODEL_SHA
        core, preload, sdk = bootstrap(report)
        sys.path.insert(0,'/model-deps')
        from dataclasses import asdict
        import onnxruntime as ort
        from bigbench.full_s_validation import run_full_s
        from bigbench.model_world_frame import SOURCE_ACTION_FRAME, WorldFramePolicyAdapter
        from bigbench.native_model_campaign import NativeWorldCamera
        from bigbench.optical_calibration import intrinsics_from_panda_lens
        from bigbench.sdk3_steering_collector import CaptureInput, capturing_policy_class
        from scripts.sdk3_four_validation_trial import _world, driver_info
        from scripts.sdk3_priority_model_native import source_stats_after

        pins.need(ort.__version__=='1.20.1', 'original ORT version')
        report['source_stats_before'] = source_stats_after()
        report['model_memory'] = model_memory()
        progress({'model_process_bounds':[0,1]})
        inner = capturing_policy_class()(model,Path(__file__).resolve().parents[1]/'model_specs/md-v3.json',None)
        progress({'model_process_bounds':[1,1]})
        report.update(real_session=isinstance(inner.session,ort.InferenceSession), ort_version=ort.__version__,
                      providers=inner.session.get_providers())
        pins.need(report['real_session'] and report['providers']==['CPUExecutionProvider'], 'actual CPU session')
        provider, lanes, terrain = _world(args.seed,args.scenario)
        report.update(driver=driver_info(provider),terrain=terrain)
        intrinsics = {r:intrinsics_from_panda_lens(provider.env.engine.sensors['bigbench_'+r].get_lens(),964,604)
                      for r in ('road','wide')}
        report['intrinsics'] = {r:asdict(lens) for r,lens in intrinsics.items()}
        inputs = CaptureInput(NativeWorldCamera(provider),intrinsics,contract.VARIANT,out,lanes)
        inner.preparer = inputs
        policy = WorldFramePolicyAdapter(inner,source_action_frame=SOURCE_ACTION_FRAME)
        trajectory = run_full_s(policy,inputs,lanes,seed=args.seed,scene=args.scenario,
                                max_steps=contract.LIMITS['steps'],progress=progress)
        report.update(trajectory=trajectory,initial_recurrent_sha256=inner.initial_recurrent_sha256,
                      input_rows=inputs.rows,inference_bounds=trajectory['actual_inference_bounds'])
        progress({'inference_bounds':trajectory['actual_inference_bounds']})
        pins.need(trajectory['trial_completed'],trajectory['error'] or 'trial incomplete')
        report['status']='RETURNED'
        return 0
    except BaseException as exc:
        report['failure']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        if inputs is not None:
            report['input_rows']=inputs.rows
            atomic_json(out/'capture-ledger.json',inputs.records)
        try:
            if provider is not None:
                provider.close()
                report['provider_closed']=True
        finally:
            report['model_process_bounds']=life['model_process_bounds']
            report['inference_bounds']=life['inference_bounds']
            atomic_json(out/'report.json',report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--scenario',required=True)
    for name in ('source','activation','run-id','dependencies-sha'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--owner',type=int,dest='server_owner')
    parser.add_argument('--nonce')
    args=parser.parse_args()
    pins.need((args.seed,args.scenario) in contract.CASES and args.run_id.isdecimal(), 'registered case and run')
    pins.need(all(len(v)==40 and all(x in '0123456789abcdef' for x in v) for v in (args.source,args.activation)),
              'valid source and activation commit')
    if args.nonce is not None:
        pins.need(len(args.nonce)==32 and args.server_owner is not None,'owned child identity')
        return child(args)
    args.nonce=secrets.token_hex(16)
    args.model_trial=True

    def command(params,parent_pid):
        return [sys.executable,'-I','-S','-B',str(Path(__file__).resolve()), *sys.argv[1:],
                '--owner',str(parent_pid),'--nonce',params.nonce]

    def wait(worker, server, _):
        return owner.wait_child_then_stop_server(worker,server,contract.LIMITS['seconds'])

    return clone(owner.run_with_server,owned_child_command=command,wait_child_then_stop_server=wait)(args)


if __name__=='__main__':
    raise SystemExit(main())
