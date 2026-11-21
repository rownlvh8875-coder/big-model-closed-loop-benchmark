"""One owned Linux SDK3 process with source-built CPU Add observation."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bigbench import recorded_official_dependencies as deps
from bigbench import sdk3_action_terms as contract
from bigbench.recorded_official_execution import clone
from scripts import sdk3_steering_plan_native as launcher
from scripts import panda_sdk3_runtime as pins
from scripts.recorded_official_native import model_memory
from scripts.sdk3_four_validation_native import bootstrap
from scripts.sdk3_four_validation_trial import atomic_json


def child(args):
    out = Path(args.out)
    report = dict(protocol=contract.REPORT_PROTOCOL, status='FAILED', pid=os.getpid(),
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
        pins.need(request == {'source':args.source, 'limits':contract.LIMITS, 'mode':contract.MODE},
                  'exact mounted native Add request')
        report['effective_resources'] = contract.live_limits()
        dependency_file = out/'model-dependencies.json'
        pins.need(pins.digest(dependency_file)==args.dependencies_sha, 'bound dependency descriptor')
        deps.verify(Path('/model-deps'),json.loads(dependency_file.read_text()))
        model = Path('/model.onnx')
        pins.need(model.stat().st_size==768750198 and pins.digest(model)==pins.MODEL_SHA, 'official weights digest')
        report['model_sha256'] = pins.MODEL_SHA
        core, preload, sdk = bootstrap(report)
        sys.path.insert(0,'/model-deps')
        site = Path('/debug-ort')
        receipt = json.loads((out/'debug-runtime.json').read_bytes())
        libraries = contract.native_libraries(site)
        pins.need(libraries and libraries == receipt['native_libraries'], 'bound read-only native ORT libraries')
        pins.need(all(os.environ.get(key) == value for key, value in contract.DEBUG_FLAGS.items()),
                  'exact native Add dump settings')
        sys.path.insert(0,str(site))
        from dataclasses import asdict
        import onnxruntime as ort
        from bigbench.full_s_validation import run_full_s
        from bigbench.model_world_frame import SOURCE_ACTION_FRAME, WorldFramePolicyAdapter
        from bigbench.native_model_campaign import NativeWorldCamera
        from bigbench.optical_calibration import intrinsics_from_panda_lens
        from bigbench.preprocess_experiment import LiveInput
        from scripts.sdk3_four_validation_trial import _world, driver_info
        from scripts.sdk3_priority_model_native import source_stats_after

        build = ort.get_build_info()
        pins.need(ort.__version__=='1.20.1' and contract.release_build(build)
                  and Path(ort.__file__).is_relative_to(site), 'release-pinned debug ORT')
        report['debug_runtime'] = dict(build=build, module=ort.__file__,
                                       native_libraries=libraries, wheel_sha256=receipt['wheel_sha256'])
        report['source_stats_before'] = source_stats_after()
        report['model_memory'] = model_memory()
        progress({'model_process_bounds':[0,1]})
        inner = contract.capturing_policy(out/'action-terms')(model,Path(__file__).resolve().parents[1]/'model_specs/md-v3.json',None)
        progress({'model_process_bounds':[1,1]})
        report.update(real_session=isinstance(inner.session,ort.InferenceSession), ort_version=ort.__version__,
                      providers=inner.session.get_providers())
        pins.need(report['real_session'] and report['providers']==['CPUExecutionProvider'], 'actual CPU session')
        provider, lanes, terrain = _world(args.seed,args.scenario)
        report.update(driver=driver_info(provider),terrain=terrain)
        intrinsics = {r:intrinsics_from_panda_lens(provider.env.engine.sensors['bigbench_'+r].get_lens(),964,604)
                      for r in ('road','wide')}
        report['intrinsics'] = {r:asdict(lens) for r,lens in intrinsics.items()}
        inputs = LiveInput(NativeWorldCamera(provider),intrinsics,contract.VARIANT,out)
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
        try:
            if provider is not None:
                provider.close()
                report['provider_closed']=True
        finally:
            report['model_process_bounds']=life['model_process_bounds']
            report['inference_bounds']=life['inference_bounds']
            atomic_json(out/'report.json',report)


def main():
    return clone(launcher.main, __file__=__file__, contract=contract, child=child)()


if __name__ == '__main__':
    raise SystemExit(main())
