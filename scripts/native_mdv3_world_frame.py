"""Complete-only experimental official MD-V3 model-to-world basis diagnostic."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from time import time_ns
import uuid

from bigbench.curved_lane_scenarios import SCENARIOS,select_native_curve_lanes
from bigbench.kinematics import ModelAction,step_ideal
from bigbench.model_world_frame import WorldFramePolicyAdapter,SOURCE_ACTION_FRAME,APPLIED_ACTION_FRAME,basis_receipt
from bigbench.native_model_campaign import CampaignSpec,run_target_lane_episode
from scripts import native_mdv3_renderer_candidate as base
from scripts import native_mdv3_candidate_expansion as legacy
from scripts.compare_fresh_native_mdv3 import compare_fresh_trials
from scripts.native_opaque_order_matrix import CPU_RECEIPT,opaque_bin_policy
from scripts.native_shadow_sampler_probe import configure_sampler

PROTOCOL='stage7-mdv3-world-frame-v1'
EVIDENCE='CANDIDATE_BOTH_UNSORTED_WORLD_FRAME_OFFICIAL_MDV3'
SEEDS=base.SEEDS
SCENES=base.SCENES
CLAIMS=dict(base.CLAIMS,full_s_traversal_proven=False)
SOURCE_BINDINGS={
    'bigbench/onnx_policy.py':'d983d5950296620a6ae89c88993829b4d2cebd35a6fd0e9046a980f75c9142da',
    'scripts/native_mdv3_repeat_trial.py':'ddaf0510a775c3a44c908bb4dedf4879ae88bfcb80e1f2d022a8b513a4f42427',
    'scripts/native_mdv3_renderer_candidate.py':'5a9058102004e2f5eaa4c9dcab4c24d97a9d42702b7a9e7c248c4f576a30d22e',
    'scripts/native_mdv3_candidate_expansion.py':'d86b3be67c8ac3dee31f0bf9928014d3880c8c55a6cd829bb3c46c464d16b42c',
    'bigbench/kinematics.py':'58c92e9a5b584932cfe73ebbf7de888f2595e88ceacdabe9a457a78fa77bb70a',
    'bigbench/native_model_campaign.py':'0bcb4ca73e1404a7164be1c879a200eeff5ca41e47e3035301d40fd173000bad',
    'bigbench/metadrive_camera.py':'1c5661e6c9eea6445ebe55cb246e6b48d3384dd5a731353ba3f1a45599e338f9'}
_new_provider=base._new_provider
_new_camera=base._new_camera
_runtime=base._runtime


def _require(condition,message):
    if not condition:raise ValueError(message)


def verify_source_bindings(root=None):
    root=Path(__file__).resolve().parents[1] if root is None else Path(root)
    actual={}
    for name,expected in SOURCE_BINDINGS.items():
        path=root/name
        _require(path.is_file(),'reviewed source binding missing: '+name)
        actual[name]=sha256(path.read_bytes()).hexdigest()
        _require(actual[name]==expected,'reviewed source binding changed: '+name)
    return actual


def _new_policy(model,spec):
    verify_source_bindings()  # Must precede factory/ORT, including future parent sign changes.
    inner=base._new_policy(model,spec)
    _require(type(inner) is base.CandidateAuditedOnnx and inner.is_mock is False and inner._injected_session is False,
             'exact official noninjected audited inner policy required')
    return WorldFramePolicyAdapter(inner,source_action_frame=SOURCE_ACTION_FRAME)


def _configuration(seed,scene,repeat):
    _require(type(seed) is int and seed in SEEDS and scene in SCENES and type(repeat) is int and repeat in (0,1),
             'unknown first corrected-world gate case/repeat')
    return CampaignSpec(scenario=scene,seed=seed,steps=12,initial_fraction=.12)


def native_trial(*,model,spec,seed,scene,repeat,request_uuid):
    campaign=_configuration(seed,scene,repeat);_require(base._uuid(request_uuid),'fresh world-frame request nonce required')
    report=dict(status='ERROR',error=None,frames=[])
    policy=camera=provider=bins=sampler=runtime=geometry=bindings=None;before=after=None;closed=False
    provenance=dict(public_episode_returned=False,returned_status=None,returned_error=None,outer_lifecycle_error=None)
    try:
        bindings=verify_source_bindings();policy=_new_policy(Path(model),Path(spec));runtime=_runtime(policy)
        with opaque_bin_policy(1) as bins:
            try:
                provider=_new_provider(seed,scene);engine=provider.env.engine;world=provider.env.current_map
                sampler=configure_sampler(engine,'feedback_both')
                selected=select_native_curve_lanes(world,SCENARIOS[scene])
                _require(len(selected)==2,'two actual native S bends required')
                geometry=legacy._geometry(world,selected,None,campaign)
                camera=legacy.ExpansionCaptureAudit(_new_camera(provider));before=base._tasks(engine)
                report=run_target_lane_episode(policy,camera,selected[0],campaign,route=None)
                provenance.update(public_episode_returned=True,returned_status=report.get('status'),returned_error=report.get('error'))
            finally:
                if provider is not None:
                    try:after=base._tasks(provider.env.engine)
                    finally:provider.close();closed=True
    except Exception as exc:
        error=f'{type(exc).__name__}: {exc}';provenance['outer_lifecycle_error']=error
        report.update(status='FAILED_OR_INCOMPLETE',error=error)
    audits=getattr(policy,'audit_rows',[]);captures=getattr(camera,'rows',[]);bridges=getattr(policy,'bridge_receipts',[])
    trace=getattr(policy,'trace',[]);rows=report.get('frames',[])
    for index,row in enumerate(rows):
        if index<len(audits):row.update(audits[index])
        if index<len(captures):row['capture_audit']=captures[index]
        if index<len(bridges):row['world_frame_bridge']=bridges[index]
    official=(policy is not None and getattr(policy,'is_mock',True) is False
              and not getattr(policy,'_injected_session',True) and len(trace)>0)
    report.update(protocol=PROTOCOL,trial_evidence=EVIDENCE if official else 'UNIT_TEST_DOUBLE_OR_FAILED_SETUP_NOT_OFFICIAL_EXECUTION',
        official_model_execution=official,model_sha256=getattr(getattr(policy,'contract',None),'sha256',None),model_nbytes=base.MODEL_BYTES,
        model_spec_sha256=base.SPEC_SHA,scenario=scene,seed=seed,requested_steps=12,completed_steps=len(rows),initial_fraction=.12,
        campaign_spec=asdict(campaign),source_bindings=bindings,action_basis=basis_receipt(),
        world_frame_trial=dict(seed=seed,scenario=scene,repeat=repeat,request_uuid=request_uuid),
        process_id=os.getpid(),process_uuid=uuid.uuid4().hex,episode_provenance=provenance,
        camera_capture_mode='native_MetaDrive_perceive_sequential_per_step',camera_convergence_attempts=0,camera_pixel_tolerance=0,
        camera_image_interpolation_or_replay=False,gpu_hdr_extraction=False,gpu_texture_extract_calls=0,gpu_queries_used=False,
        rgb_retention_observer=False,pssm_update_preserved=True,raw_action_and_recurrent_sha_captured_per_step=True,
        actual_onnx_image_feed_sha_captured_per_step=True,native_source_964x604_rgb_sha_captured_per_step=True,
        historical_original_gate=dict(passed=0,total=4,status='FAIL'),
        initial_state_receipts=getattr(policy,'initial_state_receipts',None),initial_state_sha256=getattr(policy,'initial_state_sha256',None),
        policy_reset_count=getattr(policy,'policy_reset_count',None),adapter_reset_calls=getattr(policy,'adapter_reset_calls',None),
        parent_onnx_step_count=len(trace),inference_audit_rows=audits,capture_audit_rows=captures,bridge_receipts=bridges,
        native_geometry=geometry,explicit_route_lane_ids=[geometry['selected_lanes'][0]['index']] if geometry else [],
        full_s_route_requested=False,route_active_index_after_episode=0,visited_target_lane_ids=legacy._visited(rows),
        sampler_configuration=sampler,opaque_bin_diagnostic=bins,registered_tasks_before=before,registered_tasks_after=after,
        provider_closed=closed,runtime=runtime,
        audit_scope=dict(cpu_only=True,state_bytes_hashed_per_step=base.STATE_BYTES,extra_audit_overhead_free=False,
            original_camera_class='bigbench.native_model_campaign.NativeWorldCamera',capture_delegate_calls=getattr(camera,'delegate_calls',0),
            warped_bytes_hashed_per_capture=legacy.WARP_HASH_BYTES),
        raw_sensor_rgb_dims=[964,604],model_rgb_dims=[512,256],actual_i420_shape=[2,6,128,256],actual_i420_dtype='uint8',**CLAIMS)
    return report


def _controls(d,seed,scene,repeat):
    campaign=_configuration(seed,scene,repeat)
    expected=dict(protocol=PROTOCOL,status='DIAGNOSTIC_EXECUTED',error=None,trial_evidence=EVIDENCE,official_model_execution=True,
        model_sha256=base.MODEL_SHA,model_nbytes=base.MODEL_BYTES,model_spec_sha256=base.SPEC_SHA,
        scenario=scene,seed=seed,requested_steps=12,completed_steps=12,initial_fraction=.12,campaign_spec=asdict(campaign),
        source_bindings=SOURCE_BINDINGS,action_basis=basis_receipt(),policy_reset_count=2,adapter_reset_calls=1,parent_onnx_step_count=12,
        provider_closed=True,full_s_route_requested=False,route_active_index_after_episode=0,
        camera_capture_mode='native_MetaDrive_perceive_sequential_per_step',camera_convergence_attempts=0,camera_pixel_tolerance=0,
        camera_image_interpolation_or_replay=False,gpu_hdr_extraction=False,gpu_texture_extract_calls=0,gpu_queries_used=False,
        rgb_retention_observer=False,pssm_update_preserved=True,raw_action_and_recurrent_sha_captured_per_step=True,
        actual_onnx_image_feed_sha_captured_per_step=True,native_source_964x604_rgb_sha_captured_per_step=True,
        historical_original_gate=dict(passed=0,total=4,status='FAIL'),raw_sensor_rgb_dims=[964,604],model_rgb_dims=[512,256],
        actual_i420_shape=[2,6,128,256],actual_i420_dtype='uint8',
        episode_provenance=dict(public_episode_returned=True,returned_status='DIAGNOSTIC_EXECUTED',returned_error=None,outer_lifecycle_error=None),
        audit_scope=dict(cpu_only=True,state_bytes_hashed_per_step=base.STATE_BYTES,extra_audit_overhead_free=False,
            original_camera_class='bigbench.native_model_campaign.NativeWorldCamera',capture_delegate_calls=12,
            warped_bytes_hashed_per_capture=legacy.WARP_HASH_BYTES),**CLAIMS)
    _require(all(base._exact(d.get(k),v) for k,v in expected.items()),'new world-frame identity/model/complete controls invalid')
    request=d.get('world_frame_trial',{})
    _require(base._uuid(request.get('request_uuid')) and base._exact(request,dict(seed=seed,scenario=scene,repeat=repeat,
        request_uuid=request.get('request_uuid'))),'fresh corrected-frame case/repeat nonce required')
    _require(type(d.get('process_id')) is int and d['process_id']>0 and base._uuid(d.get('process_uuid')),'native process identity invalid')
    initial,aggregate=base._initial_receipts();base._validate_states(d.get('initial_state_receipts'))
    _require(base._exact(d['initial_state_receipts'],initial) and d.get('initial_state_sha256')==aggregate,'exact parent zero reset required')
    tasks=d.get('registered_tasks_before');after=d.get('registered_tasks_after')
    _require(isinstance(tasks,list) and isinstance(after,list) and all(type(x) is str for x in tasks+after)
        and tasks==sorted(tasks) and tasks==after and all(tasks.count(k)==1 for k in ('igLoop','PSSM.update','update main chase camera')),
        'unchanged task registry required')
    guard=dict(enabled=True,original_camera_states_empty=[True,True],camera_count=2,shader_replaced=False,
        input_priority=1000000,inputs=['use_pssm','PSSMShadowAtlas'],placeholder=dict(dimensions=[1,1],format='RGBA8',rgba=[255]*4,filters=[1,1]))
    sampler=dict(mode='feedback_both',filters_before=[6,6],filters_after=[1,1],metadrive_version='0.4.3',
        loaded_fragment_shader_sha256=base.SHADER_SHA256,shader_edited=False,manual_pcf_sampler2d_confirmed=True,
        renderer_semantics_experimental=True,shadow_guard=guard)
    _require(base._exact(d.get('sampler_configuration'),sampler),'opt-in renderer sampler/guard invalid')
    bins=d.get('opaque_bin_diagnostic',{});before=bins.get('before')
    _require(isinstance(before,dict) and set(before)=={'index','name','type','sort','active'}
        and type(before.get('index')) is int and before['index']>=0 and before.get('name')=='opaque'
        and type(before.get('type')) is int and before['type']==2 and type(before.get('sort')) is int and type(before.get('active')) is bool
        and base._exact(bins,dict(CPU_RECEIPT,before=before,requested_type=1,configured=dict(before,type=1),after_capture=dict(before,type=1),restored=before)),
        'opaque type-only treatment/restoration invalid')
    runtime=d.get('runtime',{})
    _require(isinstance(runtime,dict) and set(runtime)=={'ort_version','providers','optimization_level','injected_session'}
        and type(runtime.get('ort_version')) is str and bool(runtime['ort_version']) and base._exact(runtime.get('providers'),['CPUExecutionProvider'])
        and type(runtime.get('optimization_level')) is int and runtime['optimization_level']==1 and runtime.get('injected_session') is False,
        'actual forwarded official CPU/basic runtime invalid')


def _geometry_check(d,scene):
    geometry=d.get('native_geometry')
    _require(isinstance(geometry,dict) and set(geometry)=={'blocks','selected_lanes','route_lanes','initial_pose'},'actual native geometry required')
    blocks=geometry['blocks'];_require(isinstance(blocks,list) and all(isinstance(x,dict) and set(x)=={'id','direction'}
        and type(x['id']) is str and (x['direction'] is None or type(x['direction']) is int) for x in blocks),'native block fields invalid')
    _require([x['id'] for x in blocks]==['I','C','C'],'original native I/C/C map blocks required')
    curves=[x for x in blocks if x['id']=='C']
    _require(tuple(x['direction'] for x in curves)==SCENARIOS[scene].expected_curve_directions,'actual native S directions invalid')
    selected=geometry['selected_lanes'];_require(isinstance(selected,list) and len(selected)==2,'two selected circular lanes required')
    for lane in selected:
        _require(isinstance(lane,dict) and set(lane)=={'index','type','length','radius','direction'}
            and all(type(lane.get(k)) is str and bool(lane[k]) for k in ('index','type'))
            and all(type(lane.get(k)) in (int,float) and math.isfinite(lane[k]) for k in ('length','radius','direction'))
            and lane['length']>0 and lane['radius']>0 and lane['direction']!=0,'native circular-lane fields invalid')
    _require(selected[0]['index']!=selected[1]['index'] and len({math.copysign(1.,x['direction']) for x in selected})==2
        and base._exact(geometry['route_lanes'],[selected[0]]) and base._exact(d.get('explicit_route_lane_ids'),[selected[0]['index']])
        and base._exact(d.get('visited_target_lane_ids'),[selected[0]['index']]),'original first target lane changed')
    pose=base._pose(geometry['initial_pose']);_require(pose.t==0. and pose.speed==8.,'initial native pose invalid')
    return selected[0]['index'],pose


def _bridge_action(receipt,parent,index):
    expected=dict(step=index,**basis_receipt(),parent_model_action=asdict(parent),
                  applied_world_action=asdict(ModelAction(-parent.curvature_1pm,parent.acceleration_mps2)))
    _require(isinstance(receipt,dict) and set(receipt)==set(expected)|{'bridge_audit_wall_s'}
        and all(base._exact(receipt.get(k),v) for k,v in expected.items()) and base._duration(receipt.get('bridge_audit_wall_s')),
        'separate exact FRD-to-FLU bridge receipt invalid')
    return ModelAction(**receipt['applied_world_action'])


def validate_trial(d,seed,scene,repeat):
    _controls(d,seed,scene,repeat);lane,pose=_geometry_check(d,scene)
    rows=d.get('frames');audits=d.get('inference_audit_rows');captures=d.get('capture_audit_rows');bridges=d.get('bridge_receipts')
    _require(all(isinstance(x,list) and len(x)==12 for x in (rows,audits,captures,bridges)),'twelve FULL capture/parent/bridge/frame records required')
    clock=None
    for index in range(12):
        parent=legacy._validate_action(audits[index])  # Generic parent FRD fields; never apply it directly to world motion.
        applied=_bridge_action(bridges[index],parent,index+1)
        entry,clock=legacy._validate_capture(captures[index],pose,clock)
        pose=step_ideal(entry,applied,.05,speed_override=8.);row=rows[index]
        _require(isinstance(row,dict) and type(row.get('step')) is int and row['step']==index+1
            and all(base._exact(row.get(k),audits[index][k]) for k in legacy.POLICY_KEYS)
            and base._exact(row.get('capture_audit'),captures[index]) and base._exact(row.get('world_frame_bridge'),bridges[index])
            and all(base._exact(row.get(k),captures[index][k]) for k in legacy.HASH_KEYS),'completed row differs from original parent/capture/bridge audits')
        keys=('time_s','world_x_m','world_y_m','heading_rad','speed_mps','desired_curvature_1pm','desired_acceleration_mps2')
        values=[row.get(k) for k in keys]
        _require(all(type(x) in (int,float) and math.isfinite(x) for x in values)
            and values==[pose.t,pose.x,pose.y,pose.heading,pose.speed,applied.curvature_1pm,applied.acceleration_mps2]
            and row.get('target_lane_id')==lane,'row kinematics must use applied WORLD action, not parent FRD')
        _require(all(type(row.get(k)) in (int,float) and math.isfinite(row[k]) for k in ('lateral_right_m','lane_intrusion_m'))
            and row['lane_intrusion_m']>=0 and (row.get('inside_turn_offset_m') is None
                or type(row['inside_turn_offset_m']) in (int,float) and math.isfinite(row['inside_turn_offset_m'])),'native truth fields invalid')


def compare_trials(a,b,seed,scene):
    for repeat,d in enumerate((a,b)):validate_trial(d,seed,scene,repeat)
    _require(a['world_frame_trial']['request_uuid']!=b['world_frame_trial']['request_uuid'],'independent request nonces required')
    common=compare_fresh_trials(a,b)
    top=('campaign_spec','source_bindings','action_basis','initial_state_receipts','initial_state_sha256','runtime','native_geometry',
         'sampler_configuration','opaque_bin_diagnostic','registered_tasks_before','registered_tasks_after','explicit_route_lane_ids')
    _require(all(base._exact(a[k],b[k]) for k in top),'corrected repeat initial configuration differs')
    extra=[]
    for index,(x,y) in enumerate(zip(a['frames'],b['frames']),1):
        keys=('named_state_receipts','raw_action_receipt','parent_converted_action','target_lane_id',
              'lateral_right_m','inside_turn_offset_m','lane_intrusion_m')
        differing=[k for k in keys if not base._exact(x[k],y[k])]
        for key in ('source_action_frame','applied_action_frame','body_rotation','raw_outputs_rewritten','parent_model_action','applied_world_action'):
            if not base._exact(x['world_frame_bridge'][key],y['world_frame_bridge'][key]):differing.append('bridge_'+key)
        if not base._exact(x['capture_audit']['entry_pose'],y['capture_audit']['entry_pose']):differing.append('capture_entry_pose')
        if any(x['capture_audit'][p]['frame_count']!=y['capture_audit'][p]['frame_count'] for p in ('before','after')):
            differing.append('capture_panda_frame_counts')
        if differing:extra.append(dict(step=index,differing_fields=differing))
    first=[x for x in (common['first_diverging_step'],extra[0]['step'] if extra else None) if x is not None]
    passed=common['exact_repeated_execution_gate_passed'] and not extra
    return dict(protocol=PROTOCOL,trial_evidence=EVIDENCE,seed=seed,scenario=scene,world_frame_exact_gate_passed=passed,
        status='WORLD_FRAME_REPEAT_MATCH' if passed else 'WORLD_FRAME_REPEAT_MISMATCH',first_diverging_step=min(first) if first else None,
        common_strict_comparison=common,extra_mismatches=extra,actual_onnx_steps=sum(d['parent_onnx_step_count'] for d in (a,b)),
        process_uuids=[a['process_uuid'],b['process_uuid']],**CLAIMS)


def _folder(root,seed,scene):
    _configuration(seed,scene,0);return Path(root)/f'seed-{seed}'/scene


def _write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def launch_trial(*,model,spec,seed,scene,repeat,out,request_uuid=None,status_receipt=None):
    _configuration(seed,scene,repeat);nonce=uuid.uuid4().hex if request_uuid is None else request_uuid
    _require(base._uuid(nonce),'fresh launch nonce required');out=Path(out);log=out.with_suffix('.log')
    _require(not out.exists() and not log.exists(),'fresh raw output/log required');out.parent.mkdir(parents=True,exist_ok=True)
    command=['xvfb-run','-a',sys.executable,'-m','scripts.native_mdv3_world_frame','--mode','native',
        '--model',str(model),'--spec',str(spec),'--seed',str(seed),'--scene',scene,'--repeat',str(repeat),'--request-uuid',nonce,'--out',str(out)]
    with log.open('x') as stream:status=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT).returncode
    if status_receipt is not None:status_receipt.append(status)
    if status not in (0,5):return status
    wire=json.loads(out.read_text());validate_trial(wire,seed,scene,repeat)
    _require(wire['world_frame_trial']['request_uuid']==nonce,'fresh corrected receipt nonce differs from launch')
    return 0


def run_case(*,root,model,spec,seed,scene):
    folder=_folder(root,seed,scene);_require(not folder.exists(),'fresh corrected case directory required');folder.mkdir(parents=True)
    ledger=dict(seed=seed,scenario=scene,entries=[])
    for repeat in (0,1):
        nonce=uuid.uuid4().hex;statuses=[];entry=dict(repeat=repeat,filename=f'run_{repeat}.json',request_uuid=nonce,
            started_ns=time_ns(),finished_ns=None,native_exit_status=None,accepted_exit_status=None)
        ledger['entries'].append(entry);_write(folder/'execution_ledger.json',ledger)
        try:
            status=launch_trial(model=model,spec=spec,seed=seed,scene=scene,repeat=repeat,out=folder/entry['filename'],request_uuid=nonce,status_receipt=statuses)
            entry['accepted_exit_status']=status
            if status==0:
                wire=json.loads((folder/entry['filename']).read_text());entry.update(process_id=wire['process_id'],process_uuid=wire['process_uuid'])
        except Exception as exc:entry['error']=f'{type(exc).__name__}: {exc}';raise
        finally:
            entry['finished_ns']=time_ns();entry['native_exit_status']=statuses[0] if statuses else None;_write(folder/'execution_ledger.json',ledger)
        if status!=0:return status
    _write(folder/'case_comparison.json',compare_case(root,seed,scene));return 0


def compare_case(root,seed,scene):
    folder=_folder(root,seed,scene);ledger=json.loads((folder/'execution_ledger.json').read_text());entries=ledger.get('entries')
    _require(base._exact(ledger.get('seed'),seed) and ledger.get('scenario')==scene and isinstance(entries,list) and len(entries)==2,'complete corrected two-process ledger required')
    trials=[];end=0
    for repeat,entry in enumerate(entries):
        _require(type(entry.get('repeat')) is int and entry['repeat']==repeat and entry.get('filename')==f'run_{repeat}.json'
            and type(entry.get('native_exit_status')) is int and entry['native_exit_status'] in (0,5)
            and type(entry.get('accepted_exit_status')) is int and entry['accepted_exit_status']==0
            and type(entry.get('started_ns')) is int and type(entry.get('finished_ns')) is int
            and entry['started_ns']>0 and entry['started_ns']>=end and entry['finished_ns']>=entry['started_ns'] and 'error' not in entry,
            'corrected ledger actual status/order/timing invalid')
        end=entry['finished_ns'];wire=json.loads((folder/entry['filename']).read_text());validate_trial(wire,seed,scene,repeat)
        _require(entry.get('request_uuid')==wire['world_frame_trial']['request_uuid'] and entry.get('process_uuid')==wire['process_uuid']
            and entry.get('process_id')==wire['process_id'],'corrected ledger nonce/process identity mismatch');trials.append(wire)
    return dict(compare_trials(*trials,seed,scene),execution_ledger=ledger,independent_process_count=2)


def aggregate_cases(root):
    cases=[];identities=set();nonces=set();runtimes=[]
    for seed in SEEDS:
        for scene in SCENES:
            folder=_folder(root,seed,scene);case=compare_case(root,seed,scene)
            _require(base._exact(json.loads((folder/'case_comparison.json').read_text()),case),'stale corrected case summary')
            for repeat in (0,1):
                wire=json.loads((folder/f'run_{repeat}.json').read_text());identity=wire['process_uuid'];nonce=wire['world_frame_trial']['request_uuid']
                _require(identity not in identities and nonce not in nonces,'corrected UUID/nonce reused across cases')
                identities.add(identity);nonces.add(nonce);runtimes.append(wire['runtime'])
            cases.append(case)
    _require(all(base._exact(x,runtimes[0]) for x in runtimes),'mixed actual ORT runtimes')
    passed=sum(x['world_frame_exact_gate_passed'] for x in cases)
    result=dict(protocol=PROTOCOL,trial_evidence=EVIDENCE,world_frame_gate_pass_count=passed,world_frame_gate_total=4,
        world_frame_all_four_cases_passed=passed==4,independent_process_count=len(identities),
        actual_onnx_steps=sum(x['actual_onnx_steps'] for x in cases),per_case=cases,
        historical_original_gate=dict(passed=0,total=4,status='FAIL'),**CLAIMS)
    stored=Path(root)/'aggregate_summary.json'
    if stored.exists():_require(base._exact(json.loads(stored.read_text()),result),'stale corrected final summary')
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('native','run-case','case','aggregate'),required=True)
    parser.add_argument('--model',type=Path);parser.add_argument('--spec',type=Path);parser.add_argument('--root',type=Path);parser.add_argument('--out',type=Path)
    parser.add_argument('--seed',type=int,choices=SEEDS);parser.add_argument('--scene',choices=SCENES)
    parser.add_argument('--repeat',type=int,choices=(0,1));parser.add_argument('--request-uuid');args=parser.parse_args(argv)
    if args.mode=='aggregate':
        if args.root is None or args.out is None:parser.error('aggregate requires root/out')
        _write(args.out,aggregate_cases(args.root));return 0
    if None in (args.seed,args.scene):parser.error('case identity required')
    if args.mode=='run-case':
        if None in (args.root,args.model,args.spec):parser.error('run-case requires root/model/spec')
        return run_case(root=args.root,model=args.model,spec=args.spec,seed=args.seed,scene=args.scene)
    if args.out is None:parser.error('out required')
    if args.mode=='case':
        if args.root is None:parser.error('case requires root')
        _write(args.out,compare_case(args.root,args.seed,args.scene));return 0
    if None in (args.model,args.spec,args.repeat,args.request_uuid):parser.error('native requires model/spec/repeat/nonce')
    _require(not args.out.exists(),'fresh native raw output required')
    try:result=native_trial(model=args.model,spec=args.spec,seed=args.seed,scene=args.scene,repeat=args.repeat,request_uuid=args.request_uuid)
    except Exception as exc:result=dict(status='ERROR',error=f'{type(exc).__name__}: {exc}',**CLAIMS)
    _write(args.out,result)  # Preserve ALL raw/failed/dangling evidence before strict wire validation.
    try:
        wire=json.loads(args.out.read_text());validate_trial(wire,args.seed,args.scene,args.repeat)
        _require(wire['world_frame_trial']['request_uuid']==args.request_uuid,'native nonce differs from request')
    except (ValueError,KeyError,TypeError) as exc:
        print(f'WORLD_FRAME_RECEIPT_INVALID: {exc}',file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
