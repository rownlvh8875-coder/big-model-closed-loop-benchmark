"""Owned frozen-SDK3 longitudinal camera admission and official model runs."""

import argparse
from dataclasses import asdict
import os
from pathlib import Path
import secrets
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bigbench.recorded_official_execution import clone
from scripts import panda_sdk3_diagnostic as owner
from scripts.sdk3_four_validation_native import bootstrap
from scripts.sdk3_four_validation_trial import atomic_json, driver_info
from scripts.sdk3_sidewalk_full_s import INPUT_VARIANT, OFFICIAL_MODELS, open_official_policy

SCENARIO_STEPS = {'lead_brake': 240, 'stop_go': 240, 'cut_in': 200}
SEEDS = (20261109, 20261110)
ORIGIN_M = 10.


def open_straight_world(seed):
    from bigbench.metadrive_camera import NativeMetaDriveProvider
    from bigbench.sdk3_terrain_priority import install_rgb_terrain_priority
    from metadrive.component.lane.straight_lane import StraightLane
    from metadrive.component.pgblock.first_block import FirstPGBlock
    from metadrive.constants import CameraTagStateKey, Semantics

    provider = NativeMetaDriveProvider(seed=seed, map_config={
        'type': 'block_sequence', 'config': 'S', 'lane_width': 3.5,
        'lane_num': 2, 'exit_length': 400,
    })
    try:
        start, end = FirstPGBlock.NODE_2, FirstPGBlock.NODE_3
        roads = provider.env.current_map.road_network.graph[start][end]
        if len(roads) != 2 or not all(type(lane) is StraightLane for lane in roads):
            raise ValueError('expected two actual straight lanes in the approach block')
        geometry = []
        for lane in roads:
            if not (lane.length >= 380. and lane.heading_theta_at(ORIGIN_M) == 0.
                    and lane.width_at(ORIGIN_M) == 3.5):
                raise ValueError('native straight geometry differs from the registered corridor')
            geometry.append(dict(id=list(lane.index), length_m=float(lane.length),
                                 origin=[float(v) for v in lane.position(ORIGIN_M,0.)],
                                 heading_rad=0., width_m=3.5))
        if (geometry[0]['origin'][0] != geometry[1]['origin'][0]
                or abs(geometry[0]['origin'][1]-geometry[1]['origin'][1]) != 3.5):
            raise ValueError('parallel lead and adjacent lane centerlines required')
        terrain = install_rgb_terrain_priority(provider.env.engine, terrain_label=Semantics.TERRAIN.label,
                                               tag_key=CameraTagStateKey.RGB)
        return provider, roads, geometry, terrain
    except BaseException:
        provider.close()
        raise


def model_free_probe(camera, inputs, scene, step_limit):
    from bigbench.kinematics import AgentState
    from bigbench.native_longitudinal import DeterministicLeadTimeline

    initial = AgentState(0.,0.,0.,0.,scene.ego_speed_mps)
    lead = DeterministicLeadTimeline(scene)
    elapsed = []
    for index in range(2):
        pose = AgentState(index*.05,index*.05*initial.speed,0.,0.,initial.speed)
        before = perf_counter()
        pair = camera.capture(pose, lead.state, in_lane=scene.merge_at_s is None)
        if pair.road.sha256 == pair.wide.sha256:
            raise ValueError('expected separate native road and wide views')
        inputs.prepare(pair.road,pair.wide)
        elapsed.append(perf_counter()-before)
        lead.step(pose.t,.05)
    estimate = 2*max(elapsed)*step_limit+600.
    if estimate>9000 or any(inputs.rows[0]['source_sha256'][role]==inputs.rows[1]['source_sha256'][role]
                            for role in ('road','wide')):
        raise ValueError('camera pose response or native runtime admission failed')
    return dict(admitted=True, camera_pairs=2, capture_seconds=elapsed, estimated_max_seconds=estimate)


def run_child(args):
    out = Path(args.out)
    life = out/'lifecycle.json'
    receipt = dict(protocol='sdk3-longitudinal-v1', status='FAILED', runtime='cloud-local',
                   source_sha=os.environ['SDK3_CANDIDATE_SHA'], seed=args.seed, scenario=args.scenario,
                   pid=os.getpid(), nonce=args.nonce, mode=args.mode, provider_closed=False, actor_closed=False,
                   official_model_process_bounds=[0,0], official_inference_bounds=[0,0], policy_created=False)
    provider = camera = inputs = None
    try:
        atomic_json(life,receipt)
        if os.getppid()!=args.server_owner or not Path('/tmp/.X11-unix/X99').exists() or os.environ.get('LD_PRELOAD'):
            raise RuntimeError('live owned display and uninstrumented SDK required')
        bootstrap(receipt)
        from bigbench.longitudinal_world import scenario
        from bigbench.native_longitudinal import NativeLeadVisualRenderer, run_longitudinal_native
        from bigbench.optical_calibration import assert_intrinsics_match, intrinsics_from_panda_lens, reference_source
        from bigbench.preprocess_experiment import LiveInput

        scene = scenario(args.scenario)
        limit = SCENARIO_STEPS[scene.name]
        if args.mode=='model':
            policy = open_official_policy(args.model_id,Path('/model.onnx'),receipt,life)
        provider, lanes, geometry, terrain = open_straight_world(args.seed)
        lenses = {role:intrinsics_from_panda_lens(
            provider.env.engine.sensors['bigbench_'+role].get_lens(),964,604) for role in ('road','wide')}
        for role,lens in lenses.items():
            assert_intrinsics_match(lens,reference_source(role))
        camera = NativeLeadVisualRenderer(provider,target_lane=lanes[0],adjacent_lane=lanes[1],
                                          origin_station_m=ORIGIN_M)
        inputs = LiveInput(camera.world_camera,lenses,INPUT_VARIANT,out)
        camera.capture_world = inputs.capture
        receipt.update(geometry=geometry, terrain=terrain, input_variant=INPUT_VARIANT, driver=driver_info(provider),
                       intrinsics={role:asdict(lens) for role,lens in lenses.items()}, step_limit=limit)
        if 'llvmpipe' not in receipt['driver']['renderer']:
            raise RuntimeError('expected the frozen cloud software renderer')
        if args.mode=='probe':
            receipt['admission'] = model_free_probe(camera,inputs,scene,limit)
        else:
            policy.preparer = inputs

            def progress(event):
                known = len(policy.audit_rows)
                upper = min(known+1,limit) if event['status']=='INFERENCE_PENDING' else known
                receipt.update(progress=event,official_inference_bounds=[known,upper])
                atomic_json(life,receipt)

            result = run_longitudinal_native(policy,scene,camera,steps=limit,stop_at_collision=True,progress=progress)
            known = len(policy.audit_rows)
            _,upper = receipt['official_inference_bounds']
            receipt['official_inference_bounds'] = [known,max(known,upper)]
            result.update(model_id=args.model_id, seed=args.seed, initial_scene=asdict(scene), dt_s=.05,
                          actual_inference_bounds=receipt['official_inference_bounds'],
                          audit_rows=policy.audit_rows, model_test_double=policy.is_mock,
                          injected_session=policy._injected_session)
            atomic_json(out/'run.json',result)
            if result['error']:
                raise RuntimeError(result['error'])
        receipt['status'] = 'RETURNED'
    except BaseException as exc:
        receipt['failure'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        try:
            if camera is not None:
                camera.close()
                receipt['actor_closed'] = True
        finally:
            try:
                if provider is not None:
                    provider.close()
                    receipt['provider_closed'] = True
            finally:
                if inputs is not None:
                    atomic_json(out/'input-rows.json',inputs.rows)
                receipt['ort_imported'] = 'onnxruntime' in sys.modules
                atomic_json(out/'report.json',receipt)
                atomic_json(life,receipt)
    return 0


def child_command(args, parent_pid):
    return [sys.executable,'-I','-S','-B',__file__,args.mode,'--out',args.out,'--seed',str(args.seed),
            '--scenario',args.scenario,'--model-id',args.model_id,'--nonce',args.nonce,'--server-owner',str(parent_pid)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('probe','model'))
    parser.add_argument('--out',required=True)
    parser.add_argument('--seed',type=int,choices=SEEDS,required=True)
    parser.add_argument('--scenario',choices=SCENARIO_STEPS,required=True)
    parser.add_argument('--model-id',choices=OFFICIAL_MODELS,default='md-v3')
    parser.add_argument('--nonce')
    parser.add_argument('--server-owner',type=int)
    args = parser.parse_args()
    if args.server_owner is not None:
        if args.nonce is None or len(args.nonce)!=32:
            parser.error('owned child needs launcher nonce')
        return run_child(args)
    args.nonce = secrets.token_hex(16)
    args.model_trial = args.mode=='model'

    def wait(child, server, _):
        return owner.wait_child_then_stop_server(child,server,9000 if args.model_trial else 240)

    return clone(owner.run_with_server,owned_child_command=child_command,wait_child_then_stop_server=wait)(args)


if __name__=='__main__':
    raise SystemExit(main())
