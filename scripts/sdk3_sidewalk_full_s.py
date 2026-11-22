"""Explicit local Cloud cohort. Use the original owned SDK3 and full-S paths."""

import argparse
from contextlib import ExitStack
from dataclasses import asdict
from importlib.metadata import distributions
from pathlib import Path
from time import perf_counter_ns
import json
import math
import signal
import os
import secrets
import subprocess
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import panda_sdk3_diagnostic as owner, panda_sdk3_runtime as pins
from scripts.sdk3_four_validation_native import bootstrap
from scripts.sdk3_four_validation_trial import _world, atomic_json, driver_info, rate_admission
from bigbench.recorded_official_execution import clone

DEPS = {'onnxruntime':'1.20.1','flatbuffers':'24.3.25','coloredlogs':'15.0.1',
        'humanfriendly':'10.0','packaging':'24.2','protobuf':'5.29.5','sympy':'1.13.3','mpmath':'1.3.0'}
INPUT_VARIANT = 'source_yuv_nearest_even'


def retained_file(folder, filename, data):
    with (folder / filename).open('xb') as stream:
        stream.write(zlib.compress(data,1))
    return dict(name=filename, extent=len(data))


def cull_order(engine, ordering):
    from panda3d.core import GeomNode, NodePath
    from bigbench.sdk3_sidewalk_order import _index_digest

    sensor=engine.sensors['bigbench_wide']
    regions=[r for b in sensor.manager.buffers for r in b.getDisplayRegions()
             if r.isActive() and r.getCamera()==sensor.cam]
    assert len(regions)==1
    tree=NodePath(regions[0].make_cull_result_graph())
    bins=[b for b in tree.get_children() if b.get_name()==ordering['bin']]
    if not bins:
        return []
    assert len(bins)==1
    expected={(row['count'],row['index_fingerprint']):row['priority'] for row in ordering['targets']}
    priorities=[]
    for path in sorted(bins[0].find_all_matches('**/+GeomNode'),
                       key=lambda p:int(p.get_name().rsplit('_',1)[1])):
        node=path.node()
        assert isinstance(node,GeomNode) and node.get_num_geoms()==1
        geom=node.get_geom(0)
        assert geom.get_num_primitives()==1
        primitive=geom.get_primitive(0)
        priorities.append(expected[(primitive.get_num_vertices(),_index_digest(primitive))])
    assert priorities==sorted(set(priorities))
    return priorities


def local_memory():
    host=next(int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines()
              if line.startswith('MemAvailable:'))
    limit,current=(int(Path('/sys/fs/cgroup',name).read_text())
                   for name in ('memory.max','memory.current'))
    effective=min(host,limit-current)
    values=dict(host_available_bytes=host,cgroup_limit_bytes=limit,cgroup_current_bytes=current,
                effective_available_bytes=effective,host_minimum_bytes=12*1024**3,
                effective_minimum_bytes=8*1024**3)
    return dict(**values,admitted=host>=values['host_minimum_bytes'] and effective>=values['effective_minimum_bytes'])


def probe(provider, lanes, inputs, out, receipt):
    from bigbench.full_s_validation import route_state
    from bigbench.kinematics import AgentState
    from scripts.sdk3_wide_capture_native import CameraTiming
    from scripts.verify_sdk3_wide_capture import verify_timing

    initial = float(lanes[0].length) * .12
    length = sum(float(l.length) for l in lanes)
    minimum = math.ceil((length - initial) / .4)
    receipt['probe_rows'] = []
    with ExitStack() as stack:
        timing = CameraTiming(provider, stack)
        last = 0
        for index in range(4):
            s = initial + index * .4
            x, y = map(float, lanes[0].position(s,0.))
            pose = AgentState(index*.05,x,y,float(lanes[0].heading_theta_at(s)),8.)
            assert route_state(lanes,0,pose)['intrusion_m'] == 0
            timing.events = []
            receipt['camera_attempts'] += 1
            begin = perf_counter_ns()
            pair = inputs.capture(pose)
            end = perf_counter_ns()
            rgb,_ = inputs.pending
            tensor = inputs.prepare(pair.road,pair.wide)
            assert pair.road.sha256 != pair.wide.sha256
            prepared = perf_counter_ns()
            pixels = {}
            for role in ('road','wide'):
                pixels[role] = dict(source=retained_file(out,f'{index+1:02d}-{role}-source.rgb.zlib',rgb[role].tobytes()),
                                    canvas=retained_file(out,f'{index+1:02d}-{role}-canvas.rgb.zlib',getattr(pair,role).rgb))
            pixels['tensor'] = retained_file(out,f'{index+1:02d}-input.bin.zlib',tensor.tobytes())
            ledger=dict(step=index+1,pose=asdict(pose),events=timing.events,wait_begin_ns=begin,
                        capture_begin_ns=begin,capture_end_ns=end,preprocessing_end_ns=prepared,
                        evidence_write_end_ns=perf_counter_ns())
            verify_timing(ledger,last,0)
            last=ledger['evidence_write_end_ns']
            receipt['probe_rows'].append(dict(**ledger,pixels=pixels,hashes=inputs.rows[-1],
                                             wide_target_order=cull_order(provider.env.engine,receipt['ordering'])))
            atomic_json(out/'report.json',receipt)
        second=receipt['probe_rows'][1]
        receipt['rate']=rate_admission(minimum,(second['capture_end_ns']-second['capture_begin_ns'])/1e9)


def child(args):
    out=Path(args.out)
    life=out/'lifecycle.json'
    receipt=dict(status='FAILED',runtime='cloud-local',candidate_sha=os.environ['SDK3_CANDIDATE_SHA'],
                 seed=args.seed,scenario=args.scenario,mode=args.mode,pid=os.getpid(),nonce=args.nonce,
                 official_inference_bounds=[0,0],official_model_process_bounds=[0,0],
                 provider_closed=False,policy_created=False,camera_attempts=0)
    def progress(message):
        receipt['official_inference_bounds']=message['inference_bounds']
        receipt['progress']=message
        atomic_json(life,receipt)

    provider=None
    try:
        atomic_json(life,receipt)
        assert os.getppid()==args.server_owner and Path('/tmp/.X11-unix/X99').exists()
        assert not os.environ.get('LD_PRELOAD')
        bootstrap(receipt)
        from bigbench.full_s_validation import run_full_s, validate_route
        from bigbench.model_world_frame import SOURCE_ACTION_FRAME, WorldFramePolicyAdapter, basis_receipt
        from bigbench.native_model_campaign import NativeWorldCamera
        from bigbench.optical_calibration import (assert_intrinsics_match,intrinsics_from_panda_lens,
                                                 reference_source)
        from bigbench.preprocess_experiment import LiveInput,policy_class
        from bigbench.sdk3_sidewalk_order import ordered_sidewalks

        if args.mode=='model':
            actual={d.metadata['Name'].lower():d.version for d in distributions(path=['/model-deps'])}
            assert actual==DEPS
            receipt['dependencies']=actual
            assert Path('/model.onnx').stat().st_size==768750198 and pins.digest('/model.onnx')==pins.MODEL_SHA
            receipt['model_memory']=local_memory()
            assert receipt['model_memory']['admitted'], 'local SDK3 model memory prerequisite unmet'
            sys.path.insert(0,'/model-deps')
            receipt['official_model_process_bounds']=[0,1]
            receipt['model_sha256']=pins.MODEL_SHA
            atomic_json(life,receipt)
            inner=policy_class()(Path('/model.onnx'),ROOT/'model_specs/md-v3.json',None)
            import onnxruntime as ort
            assert ort.__version__=='1.20.1' and inner.session.get_providers()==['CPUExecutionProvider']
            assert isinstance(inner.session,ort.InferenceSession) and not inner._injected_session
            receipt.update(official_model_process_bounds=[1,1],policy_created=True,ort=ort.__version__,
                           providers=inner.session.get_providers(),action_basis=basis_receipt())
            atomic_json(life,receipt)

        provider,lanes,terrain=_world(args.seed,args.scenario)
        lenses={role:intrinsics_from_panda_lens(
            provider.env.engine.sensors['bigbench_'+role].get_lens(),964,604) for role in ('road','wide')}
        for role,lens in lenses.items():
            assert_intrinsics_match(lens,reference_source(role))
        receipt.update(geometry=validate_route(lanes),intrinsics={k:asdict(v) for k,v in lenses.items()},
                       driver=driver_info(provider),terrain=terrain,input_variant=INPUT_VARIANT)
        assert 'llvmpipe' in receipt['driver']['renderer']
        camera=NativeWorldCamera(provider)
        with ordered_sidewalks(provider,args.scenario) as ordering:
            receipt['ordering']=ordering
            inputs=LiveInput(camera,lenses,INPUT_VARIANT,out)
            if args.mode=='probe':
                probe(provider,lanes,inputs,out,receipt)
            else:
                inner.preparer=inputs
                policy=WorldFramePolicyAdapter(inner,source_action_frame=SOURCE_ACTION_FRAME)
                result=run_full_s(policy,inputs,lanes,seed=args.seed,scene=args.scenario,
                                  max_steps=600,progress=progress)
                receipt['official_inference_bounds']=result['actual_inference_bounds']
                atomic_json(out/'run.json',result)
                atomic_json(out/'input-rows.json',inputs.rows)
                if not result['trial_completed']:
                    raise RuntimeError(result['error'] or 'official trajectory did not complete')
        receipt['status']='RETURNED'
    except BaseException as exc:
        receipt['failure']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        try:
            if provider is not None:
                provider.close()
                receipt['provider_closed']=True
        finally:
            receipt['ort_imported']=any(k=='onnxruntime' or k.startswith('onnxruntime.') for k in sys.modules)
            atomic_json(out/'report.json',receipt)
            atomic_json(life,receipt)
    return 0


def owned_child_command(args,parent_pid):
    return [sys.executable,'-I','-S','-B',__file__,args.mode,'--out',args.out,'--seed',str(args.seed),
            '--scenario',args.scenario,'--nonce',args.nonce,'--server-owner',str(parent_pid)]


def pair(args):
    out=Path(args.out)
    rows=[]
    for i in range(2):
        folder=out/f'run-{i}'
        folder.mkdir()
        nonce=secrets.token_hex(16)
        row=dict(index=i,nonce=nonce,launcher_spawned=False,pid=None,returncode=None)
        rows.append(row)
        atomic_json(out/'pair-ledger.json',rows)
        home=Path('/tmp')/f'home-{nonce}'
        home.mkdir()
        env=dict(os.environ,HOME=str(home),XDG_CACHE_HOME=str(home/'cache'))
        with (folder/'stdout.log').open('xb') as stdout,(folder/'stderr.log').open('xb') as stderr:
            command=[sys.executable,'-I','-S','-B',__file__,'model','--out',str(folder),'--nonce',nonce,
                     '--seed',str(args.seed),'--scenario',args.scenario]
            process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,
                                     env=env,start_new_session=True)
            row.update(launcher_spawned=True,pid=process.pid)
            atomic_json(out/'pair-ledger.json',rows)
            try:
                row['returncode']=process.wait(timeout=9040)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL)
                row.update(timeout=True,returncode=process.wait(timeout=10))
            finally:
                atomic_json(out/'pair-ledger.json',rows)
    return int(any(r['returncode']!=0 for r in rows))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('probe','model','pair'))
    parser.add_argument('--out',required=True)
    parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--scenario',required=True)
    parser.add_argument('--nonce')
    parser.add_argument('--server-owner',type=int)
    args=parser.parse_args()
    assert (args.seed,args.scenario) in pins.CASES
    if args.mode=='pair':
        assert args.server_owner is None
        return pair(args)
    args.model_trial=args.mode=='model'
    if args.server_owner is not None:
        assert args.nonce is not None and len(args.nonce)==32
        return child(args)
    if args.nonce is None:
        args.nonce=secrets.token_hex(16)
    def wait(worker,server,_):
        return owner.wait_child_then_stop_server(worker,server,9000 if args.model_trial else 240)
    return clone(owner.run_with_server,owned_child_command=owned_child_command,wait_child_then_stop_server=wait)(args)


if __name__=='__main__':
    raise SystemExit(main())
