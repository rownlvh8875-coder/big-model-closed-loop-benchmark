"""Complete-only corrected-world expansion; failed ORT call totals can be unknown."""
from __future__ import annotations

import argparse
from dataclasses import asdict,is_dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import os
import subprocess
import sys
from time import time_ns
import uuid

from bigbench.curved_lane_scenarios import SCENARIOS,select_native_curve_lanes
from bigbench.kinematics import step_ideal
from bigbench.native_model_campaign import CampaignSpec,run_target_lane_episode
from bigbench.native_route import NativeRouteProgress,forward_contiguous_chain
from scripts import native_mdv3_world_frame as frame
from scripts import native_mdv3_renderer_candidate as base
from scripts import native_mdv3_candidate_expansion as legacy
from scripts.compare_fresh_native_mdv3 import compare_fresh_trials
from scripts.native_opaque_order_matrix import CPU_RECEIPT,opaque_bin_policy
from scripts.native_shadow_sampler_probe import configure_sampler

PROTOCOL='stage7-mdv3-world-frame-expansion-v1'
EVIDENCE='CANDIDATE_BOTH_UNSORTED_WORLD_FRAME_OFFICIAL_MDV3_EXPANSION'
SEEDS=frame.SEEDS
GROUPS={'camera028':dict(scenes=frame.SCENES,fraction=.28,steps=12),
        'native_ramps':dict(scenes=('in_ramp','out_ramp'),fraction=.12,steps=12),
        'longer160':dict(scenes=frame.SCENES,fraction=.12,steps=160)}
CASES=tuple((group,seed,scene) for group,config in GROUPS.items() for seed in SEEDS for scene in config['scenes'])
SOURCE_BINDINGS=dict(frame.SOURCE_BINDINGS,**{
    'bigbench/model_world_frame.py':'275f5359a975d9e152f61df74cd57803e1322e1f9618784f0993e780516ec092',
    'scripts/native_mdv3_world_frame.py':'cd57c4d407e96459921ca61c78eb81ef55851cd4fafa92ca917bbc7f494a3e38'})
CLAIMS=dict(frame.CLAIMS)
_new_provider=frame._new_provider
_new_camera=frame._new_camera
_runtime=frame._runtime


def _require(condition,message):
    if not condition:raise ValueError(message)


def verify_source_bindings(root=None):
    root=Path(__file__).resolve().parents[1] if root is None else Path(root);actual={}
    for name,expected in SOURCE_BINDINGS.items():
        path=root/name;_require(path.is_file(),'reviewed dependency missing: '+name)
        actual[name]=sha256(path.read_bytes()).hexdigest();_require(actual[name]==expected,'reviewed dependency changed: '+name)
    return actual


def _new_policy(model,spec):
    verify_source_bindings()
    return frame._new_policy(model,spec)  # ALREADY wrapped; never apply the body rotation twice.


def campaign_spec(group,seed,scene,repeat=0):
    config=GROUPS.get(group)
    _require(config is not None and type(seed) is int and seed in SEEDS and scene in config['scenes']
        and type(repeat) is int and repeat in (0,1),'unknown actual corrected expansion case/repeat')
    return CampaignSpec(scenario=scene,seed=seed,steps=config['steps'],initial_fraction=config['fraction'])


def _committed_trace_count(d):
    trace=d.get('committed_parent_trace');count=d.get('parent_onnx_step_count')
    _require(isinstance(trace,list) and type(count) is int and 0<=count<=d['requested_steps'] and len(trace)==count,
             'committed parent trace/count inconsistent')
    fields={'step_index','elapsed_ms','raw_lateral_accel_mps2','raw_longitudinal_accel_mps2','curvature_1pm','image_checksum'}
    for index,row in enumerate(trace):
        _require(isinstance(row,dict) and set(row)==fields and type(row['step_index']) is int and row['step_index']==index
            and type(row['image_checksum']) is int and 0<=row['image_checksum']<2**32
            and all(type(row[k]) in (int,float) and math.isfinite(row[k]) for k in fields-{'step_index','image_checksum'})
            and row['elapsed_ms']>=0 and row['curvature_1pm']==row['raw_lateral_accel_mps2']/64.,'committed parent trace schema/action invalid')
    return count


def attempt_accounting(d):
    """Count committed steps separately; a failed uncommitted policy call may have run ORT."""
    result=dict(known_committed_parent_steps=None,total_executed_ort_calls=None,
                completed_frame_rows=len(d['frames']) if isinstance(d,dict) and isinstance(d.get('frames'),list) else None,
                successful_capture_returns=None,reason='MALFORMED_ACCOUNTING_EVIDENCE',errors=[])
    try:
        _require(isinstance(d,dict),'raw attempt must be an object')
        n=_committed_trace_count(d);result['known_committed_parent_steps']=n
        captures=d.get('capture_audit_rows');audits=d.get('inference_audit_rows');bridges=d.get('bridge_receipts')
        _require(all(isinstance(x,list) for x in (captures,audits,bridges)),'retained accounting arrays missing')
        _require(isinstance(d.get('frames'),list) and len(d['frames'])<=len(bridges)<=len(audits)<=n,
                 'frozen completed-row/bridge/audit/committed-trace cardinality violated')
        _require(len(captures)<=d['requested_steps'],'capture attempts exceed the requested episode horizon')
        provenance=d.get('episode_provenance',{})
        _require(isinstance(provenance,dict),'public phase provenance must be an object')
        if provenance.get('public_episode_started') is False:
            _require(n==0 and not captures and not audits and not bridges,'setup phase conflicts with retained policy/capture work')
            result.update(total_executed_ort_calls=0,successful_capture_returns=0,reason='SETUP_BEFORE_POLICY_STEP')
            return result
        _require(provenance.get('public_episode_started') is True,'public episode phase marker required')
        pose=base._pose(d['native_geometry']['initial_pose']);clock=None;success=0
        for index,capture in enumerate(captures):
            _require(isinstance(capture,dict),'capture accounting record must be an object')
            error=capture.get('error') or capture.get('hash_audit_error')
            if error is not None:
                _require(index==len(captures)-1 and type(error) is str and bool(error)
                    and error in (provenance.get('returned_error'),provenance.get('outer_lifecycle_error'))
                    and base._pose(capture.get('entry_pose'))==pose,'unproven failed capture phase')
                break  # Frozen public loop cannot invoke policy after capture raises.
            entry,clock=legacy._validate_capture(capture,pose,clock);success+=1
            if index<len(audits) and index<len(bridges):
                parent=legacy._validate_action(audits[index]);applied=frame._bridge_action(bridges[index],parent,index+1)
                pose=step_ideal(entry,applied,.05,speed_override=8.)
            else:_require(index==len(captures)-1,'capture order cannot be established after a missing policy/bridge receipt')
        result['successful_capture_returns']=success
        _require(n<=success,'committed trace exceeds proved successful captures')
        if n==success:
            result.update(total_executed_ort_calls=n,reason='CAPTURE_POLICY_ORDER_PROVES_TOTAL')
        else:result['reason']='POSSIBLE_UNCOMMITTED_POLICY_ATTEMPT'
    except Exception as exc:
        result['errors'].append(f'{type(exc).__name__}: {exc}')
    return result


def native_trial(*,model,spec,group,seed,scene,repeat,request_uuid):
    campaign=campaign_spec(group,seed,scene,repeat);_require(base._uuid(request_uuid),'fresh expansion nonce required')
    report=dict(status='ERROR',error=None,frames=[])
    policy=camera=provider=bins=sampler=runtime=geometry=route=bindings=None;before=after=None;closed=False
    provenance=dict(public_episode_started=False,public_episode_returned=False,returned_status=None,returned_error=None,outer_lifecycle_error=None)
    try:
        bindings=verify_source_bindings();policy=_new_policy(Path(model),Path(spec));runtime=_runtime(policy)
        with opaque_bin_policy(1) as bins:
            try:
                provider=_new_provider(seed,scene);engine=provider.env.engine;world=provider.env.current_map
                sampler=configure_sampler(engine,'feedback_both');selected=select_native_curve_lanes(world,SCENARIOS[scene])
                _require(bool(selected),'actual native curve/ramp lane required')
                if group=='longer160':
                    _require(len(selected)==2,'two admitted bends required for explicit longer route')
                    route=NativeRouteProgress(forward_contiguous_chain(world.road_network,selected[0],str(selected[1].index)))
                geometry=legacy._geometry(world,selected,route,campaign)
                camera=legacy.ExpansionCaptureAudit(_new_camera(provider));before=base._tasks(engine)
                provenance['public_episode_started']=True
                report=run_target_lane_episode(policy,camera,selected[0],campaign,route=route)
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
    official=(policy is not None and getattr(policy,'is_mock',True) is False and not getattr(policy,'_injected_session',True))
    report.update(protocol=PROTOCOL,trial_evidence=EVIDENCE if official and len(trace)>0 else 'UNIT_TEST_DOUBLE_OR_FAILED_ATTEMPT_NOT_PROVEN_OFFICIAL_EXECUTION',
        model_sha256=getattr(getattr(policy,'contract',None),'sha256',None),model_nbytes=base.MODEL_BYTES,model_spec_sha256=base.SPEC_SHA,
        scenario=scene,seed=seed,requested_steps=campaign.steps,completed_steps=len(rows),initial_fraction=campaign.initial_fraction,campaign_spec=asdict(campaign),
        source_bindings=bindings,action_basis=frame.basis_receipt(),world_frame_expansion_trial=dict(group=group,seed=seed,scenario=scene,repeat=repeat,request_uuid=request_uuid),
        process_id=os.getpid(),process_uuid=uuid.uuid4().hex,episode_provenance=provenance,
        camera_capture_mode='native_MetaDrive_perceive_sequential_per_step',camera_convergence_attempts=0,camera_pixel_tolerance=0,
        camera_image_interpolation_or_replay=False,gpu_hdr_extraction=False,gpu_texture_extract_calls=0,gpu_queries_used=False,rgb_retention_observer=False,
        pssm_update_preserved=True,raw_action_and_recurrent_sha_captured_per_step=True,actual_onnx_image_feed_sha_captured_per_step=True,
        native_source_964x604_rgb_sha_captured_per_step=True,historical_original_gate=dict(passed=0,total=4,status='FAIL'),
        initial_state_receipts=getattr(policy,'initial_state_receipts',None),initial_state_sha256=getattr(policy,'initial_state_sha256',None),
        policy_reset_count=getattr(policy,'policy_reset_count',None),adapter_reset_calls=getattr(policy,'adapter_reset_calls',None),parent_onnx_step_count=len(trace),
        committed_parent_trace=[asdict(x) if is_dataclass(x) else dict(invalid_trace_type=type(x).__name__,representation=str(x)) for x in trace],
        inference_audit_rows=audits,capture_audit_rows=captures,bridge_receipts=bridges,native_geometry=geometry,
        explicit_route_lane_ids=[x['index'] for x in geometry['route_lanes']] if geometry else [],full_s_route_requested=group=='longer160',
        route_active_index_after_episode=route.active_index if route else 0,visited_target_lane_ids=legacy._visited(rows),
        sampler_configuration=sampler,opaque_bin_diagnostic=bins,registered_tasks_before=before,registered_tasks_after=after,provider_closed=closed,runtime=runtime,
        audit_scope=dict(cpu_only=True,state_bytes_hashed_per_step=base.STATE_BYTES,extra_audit_overhead_free=False,
            original_camera_class='bigbench.native_model_campaign.NativeWorldCamera',capture_delegate_calls=getattr(camera,'delegate_calls',0),
            warped_bytes_hashed_per_capture=legacy.WARP_HASH_BYTES),raw_sensor_rgb_dims=[964,604],model_rgb_dims=[512,256],actual_i420_shape=[2,6,128,256],actual_i420_dtype='uint8',**CLAIMS)
    accounting=attempt_accounting(report);report['execution_accounting']=accounting
    report['official_model_execution']=(bool(trace) if accounting['total_executed_ort_calls'] is not None or trace else None) if official else False
    return report


def _controls(d,group,seed,scene,repeat):
    campaign=campaign_spec(group,seed,scene,repeat);n=campaign.steps
    expected=dict(protocol=PROTOCOL,status='DIAGNOSTIC_EXECUTED',error=None,trial_evidence=EVIDENCE,official_model_execution=True,
        model_sha256=base.MODEL_SHA,model_nbytes=base.MODEL_BYTES,model_spec_sha256=base.SPEC_SHA,scenario=scene,seed=seed,
        requested_steps=n,completed_steps=n,initial_fraction=campaign.initial_fraction,campaign_spec=asdict(campaign),source_bindings=SOURCE_BINDINGS,
        action_basis=frame.basis_receipt(),policy_reset_count=2,adapter_reset_calls=1,parent_onnx_step_count=n,provider_closed=True,full_s_route_requested=group=='longer160',
        camera_capture_mode='native_MetaDrive_perceive_sequential_per_step',camera_convergence_attempts=0,camera_pixel_tolerance=0,
        camera_image_interpolation_or_replay=False,gpu_hdr_extraction=False,gpu_texture_extract_calls=0,gpu_queries_used=False,rgb_retention_observer=False,
        pssm_update_preserved=True,raw_action_and_recurrent_sha_captured_per_step=True,actual_onnx_image_feed_sha_captured_per_step=True,
        native_source_964x604_rgb_sha_captured_per_step=True,historical_original_gate=dict(passed=0,total=4,status='FAIL'),
        raw_sensor_rgb_dims=[964,604],model_rgb_dims=[512,256],actual_i420_shape=[2,6,128,256],actual_i420_dtype='uint8',
        episode_provenance=dict(public_episode_started=True,public_episode_returned=True,returned_status='DIAGNOSTIC_EXECUTED',returned_error=None,outer_lifecycle_error=None),
        audit_scope=dict(cpu_only=True,state_bytes_hashed_per_step=base.STATE_BYTES,extra_audit_overhead_free=False,
            original_camera_class='bigbench.native_model_campaign.NativeWorldCamera',capture_delegate_calls=n,warped_bytes_hashed_per_capture=legacy.WARP_HASH_BYTES),**CLAIMS)
    _require(all(base._exact(d.get(k),v) for k,v in expected.items()),'actual corrected expansion identity/model/complete controls invalid')
    request=d.get('world_frame_expansion_trial',{})
    _require(isinstance(request,dict),'request identity must be an object')
    _require(base._uuid(request.get('request_uuid')) and base._exact(request,dict(group=group,seed=seed,scenario=scene,repeat=repeat,
        request_uuid=request.get('request_uuid'))),'corrected expansion nonce/case/repeat invalid')
    _require(type(d.get('process_id')) is int and d['process_id']>0 and base._uuid(d.get('process_uuid')),'fresh native identity required')
    initial,aggregate=base._initial_receipts();base._validate_states(d.get('initial_state_receipts'))
    _require(base._exact(d['initial_state_receipts'],initial) and d.get('initial_state_sha256')==aggregate,'exact zero parent reset required')
    tasks=d.get('registered_tasks_before');after=d.get('registered_tasks_after')
    _require(isinstance(tasks,list) and isinstance(after,list) and all(type(x) is str for x in tasks+after)
        and tasks==sorted(tasks) and tasks==after and all(tasks.count(k)==1 for k in ('igLoop','PSSM.update','update main chase camera')),'original tasks changed')
    guard=dict(enabled=True,original_camera_states_empty=[True,True],camera_count=2,shader_replaced=False,input_priority=1000000,
        inputs=['use_pssm','PSSMShadowAtlas'],placeholder=dict(dimensions=[1,1],format='RGBA8',rgba=[255]*4,filters=[1,1]))
    sampler=dict(mode='feedback_both',filters_before=[6,6],filters_after=[1,1],metadrive_version='0.4.3',loaded_fragment_shader_sha256=base.SHADER_SHA256,
        shader_edited=False,manual_pcf_sampler2d_confirmed=True,renderer_semantics_experimental=True,shadow_guard=guard)
    _require(base._exact(d.get('sampler_configuration'),sampler),'candidate sampler/guard invalid')
    bins=d.get('opaque_bin_diagnostic',{});_require(isinstance(bins,dict),'opaque receipt must be an object');before=bins.get('before')
    _require(isinstance(before,dict) and set(before)=={'index','name','type','sort','active'} and type(before.get('index')) is int and before['index']>=0
        and before.get('name')=='opaque' and type(before.get('type')) is int and before['type']==2 and type(before.get('sort')) is int and type(before.get('active')) is bool
        and base._exact(bins,dict(CPU_RECEIPT,before=before,requested_type=1,configured=dict(before,type=1),after_capture=dict(before,type=1),restored=before)),
        'opaque setup/capture/restore invalid')
    runtime=d.get('runtime',{})
    _require(isinstance(runtime,dict) and set(runtime)=={'ort_version','providers','optimization_level','injected_session'}
        and type(runtime.get('ort_version')) is str and bool(runtime['ort_version']) and base._exact(runtime.get('providers'),['CPUExecutionProvider'])
        and type(runtime.get('optimization_level')) is int and runtime['optimization_level']==1 and runtime.get('injected_session') is False,'actual CPU/basic noninjected runtime required')


def validate_trial(d,group,seed,scene,repeat):
    _require(isinstance(d,dict),'raw trial must be an object')
    _controls(d,group,seed,scene,repeat);n=campaign_spec(group,seed,scene,repeat).steps
    ids,pose=legacy._validate_geometry(d,group,scene)  # ACTUAL group; geometry only, never legacy identity/partial validation.
    expected_blocks=['I',('r' if scene=='in_ramp' else 'R')] if group=='native_ramps' else ['I','C','C']
    _require([x['id'] for x in d['native_geometry']['blocks']]==expected_blocks,'actual native map block IDs changed')
    rows=d.get('frames');audits=d.get('inference_audit_rows');captures=d.get('capture_audit_rows');bridges=d.get('bridge_receipts')
    _require(all(isinstance(x,list) and len(x)==n for x in (rows,audits,captures,bridges)),'ALL actual planned frame/capture/parent/bridge rows required')
    _require(_committed_trace_count(d)==n,'all planned committed parent traces required')
    clock=None;lane_index=0
    for index in range(n):
        parent=legacy._validate_action(audits[index]);applied=frame._bridge_action(bridges[index],parent,index+1)
        entry,clock=legacy._validate_capture(captures[index],pose,clock);pose=step_ideal(entry,applied,.05,speed_override=8.)
        row=rows[index];trace=d['committed_parent_trace'][index]
        _require(trace['raw_lateral_accel_mps2']==audits[index]['raw_model_action'][0]
            and trace['raw_longitudinal_accel_mps2']==audits[index]['raw_model_action'][1] and trace['curvature_1pm']==parent.curvature_1pm,
            'committed trace differs from actual parent FRD action')
        _require(isinstance(row,dict) and type(row.get('step')) is int and row['step']==index+1
            and all(base._exact(row.get(k),audits[index][k]) for k in legacy.POLICY_KEYS)
            and base._exact(row.get('capture_audit'),captures[index]) and base._exact(row.get('world_frame_bridge'),bridges[index])
            and all(base._exact(row.get(k),captures[index][k]) for k in legacy.HASH_KEYS),'completed row differs from capture/parent/bridge receipts')
        keys=('time_s','world_x_m','world_y_m','heading_rad','speed_mps','desired_curvature_1pm','desired_acceleration_mps2')
        values=[row.get(k) for k in keys]
        _require(all(type(x) in (int,float) and math.isfinite(x) for x in values)
            and values==[pose.t,pose.x,pose.y,pose.heading,pose.speed,applied.curvature_1pm,applied.acceleration_mps2],
            'post-action state must use unchanged APPLIED WORLD kinematics')
        lane=row.get('target_lane_id');_require(lane in ids and ids.index(lane)>=lane_index,'native truth outside forward explicit route')
        lane_index=ids.index(lane)
        _require(all(type(row.get(k)) in (int,float) and math.isfinite(row[k]) for k in ('lateral_right_m','lane_intrusion_m'))
            and row['lane_intrusion_m']>=0 and (row.get('inside_turn_offset_m') is None
                or type(row['inside_turn_offset_m']) in (int,float) and math.isfinite(row['inside_turn_offset_m'])),'native truth fields invalid')
    _require(base._exact(d.get('visited_target_lane_ids'),legacy._visited(rows))
        and d['route_active_index_after_episode']==lane_index,'successful route visits/final active index inconsistent')
    accounting=attempt_accounting(d)
    _require(base._exact(d.get('execution_accounting'),accounting) and accounting['known_committed_parent_steps']==n
        and accounting['total_executed_ort_calls']==n and not accounting['errors'],'complete exact execution accounting required')


def compare_trials(a,b,group,seed,scene):
    for repeat,d in enumerate((a,b)):validate_trial(d,group,seed,scene,repeat)
    _require(a['world_frame_expansion_trial']['request_uuid']!=b['world_frame_expansion_trial']['request_uuid'],'independent request nonces required')
    common=compare_fresh_trials(a,b)
    top=('campaign_spec','source_bindings','action_basis','initial_state_receipts','initial_state_sha256','runtime','native_geometry',
         'sampler_configuration','opaque_bin_diagnostic','registered_tasks_before','registered_tasks_after','explicit_route_lane_ids')
    _require(all(base._exact(a[k],b[k]) for k in top),'repeat initial model/native/renderer configuration differs')
    extra=[]
    for index,(x,y) in enumerate(zip(a['frames'],b['frames']),1):
        keys=('named_state_receipts','raw_action_receipt','parent_converted_action','target_lane_id','lateral_right_m','inside_turn_offset_m','lane_intrusion_m')
        differing=[k for k in keys if not base._exact(x[k],y[k])]
        bridge_keys=set(x['world_frame_bridge'])-{'bridge_audit_wall_s'}
        if any(not base._exact(x['world_frame_bridge'][k],y['world_frame_bridge'][k]) for k in bridge_keys):differing.append('world_frame_bridge')
        if not base._exact(x['capture_audit']['entry_pose'],y['capture_audit']['entry_pose']):differing.append('capture_entry_pose')
        if any(x['capture_audit'][p]['frame_count']!=y['capture_audit'][p]['frame_count'] for p in ('before','after')):differing.append('capture_panda_frame_counts')
        if any(not base._exact(a['committed_parent_trace'][index-1][k],b['committed_parent_trace'][index-1][k])
               for k in set(a['committed_parent_trace'][index-1])-{'elapsed_ms'}):differing.append('committed_parent_trace')
        if differing:extra.append(dict(step=index,differing_fields=differing))
    first=[x for x in (common['first_diverging_step'],extra[0]['step'] if extra else None) if x is not None]
    passed=common['exact_repeated_execution_gate_passed'] and not extra
    return dict(protocol=PROTOCOL,trial_evidence=EVIDENCE,group=group,seed=seed,scenario=scene,world_frame_expansion_gate_passed=passed,
        status='WORLD_FRAME_EXPANSION_MATCH' if passed else 'WORLD_FRAME_EXPANSION_MISMATCH',first_diverging_step=min(first) if first else None,
        first_incomplete_step=None,common_strict_comparison=common,extra_mismatches=extra,
        process_uuids=[a['process_uuid'],b['process_uuid']],**CLAIMS)


def _folder(root,group,seed,scene):
    campaign_spec(group,seed,scene);return Path(root)/group/f'seed-{seed}'/scene


def _write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def launch_trial(*,model,spec,group,seed,scene,repeat,out,request_uuid=None,status_receipt=None):
    campaign_spec(group,seed,scene,repeat);nonce=uuid.uuid4().hex if request_uuid is None else request_uuid
    _require(base._uuid(nonce),'fresh launch nonce required');out=Path(out);log=out.with_suffix('.log')
    _require(not out.exists() and not log.exists(),'fresh raw output/log required');out.parent.mkdir(parents=True,exist_ok=True)
    command=['xvfb-run','-a',sys.executable,'-m','scripts.native_mdv3_world_frame_expansion','--mode','native','--model',str(model),'--spec',str(spec),
        '--group',group,'--seed',str(seed),'--scene',scene,'--repeat',str(repeat),'--request-uuid',nonce,'--out',str(out)]
    with log.open('x') as stream:status=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT).returncode
    if status_receipt is not None:status_receipt.append(status)
    if status not in (0,5):return status
    wire=json.loads(out.read_text());validate_trial(wire,group,seed,scene,repeat)
    _require(wire['world_frame_expansion_trial']['request_uuid']==nonce,'raw receipt nonce differs from launch')
    return 0


def run_case(*,root,model,spec,group,seed,scene):
    folder=_folder(root,group,seed,scene);_require(not folder.exists(),'fresh expansion case directory required');folder.mkdir(parents=True)
    ledger=dict(group=group,seed=seed,scenario=scene,planned_repeats=[0,1],unattempted_repeats=[0,1],entries=[])
    for repeat in (0,1):
        statuses=[];nonce=uuid.uuid4().hex;entry=dict(repeat=repeat,filename=f'run_{repeat}.json',request_uuid=nonce,
            started_ns=time_ns(),finished_ns=None,native_exit_status=None,accepted_exit_status=None)
        ledger['unattempted_repeats'].remove(repeat);ledger['entries'].append(entry);_write(folder/'execution_ledger.json',ledger)
        try:
            status=launch_trial(model=model,spec=spec,group=group,seed=seed,scene=scene,repeat=repeat,out=folder/entry['filename'],
                                request_uuid=nonce,status_receipt=statuses)
            entry['accepted_exit_status']=status
            if status==0:
                wire=json.loads((folder/entry['filename']).read_text());entry.update(process_id=wire['process_id'],process_uuid=wire['process_uuid'])
        except Exception as exc:entry['error']=f'{type(exc).__name__}: {exc}';raise
        finally:
            entry['finished_ns']=time_ns();entry['native_exit_status']=statuses[0] if statuses else None;_write(folder/'execution_ledger.json',ledger)
        if status!=0:return status
    _write(folder/'case_comparison.json',compare_case(root,group,seed,scene));return 0


def _ledger(root,group,seed,scene):
    ledger=json.loads((_folder(root,group,seed,scene)/'execution_ledger.json').read_text())
    _require(isinstance(ledger,dict),'ledger must be an object')
    _require(all(base._exact(ledger.get(k),v) for k,v in dict(group=group,seed=seed,scenario=scene,planned_repeats=[0,1]).items()),'ledger case/planned repeat identity invalid')
    entries=ledger.get('entries');unattempted=ledger.get('unattempted_repeats')
    _require(isinstance(entries,list) and len(entries)<=2 and isinstance(unattempted,list)
        and base._exact(unattempted,list(range(len(entries),2))),'explicit attempted/unattempted repeats inconsistent')
    end=0
    for repeat,entry in enumerate(entries):
        _require(isinstance(entry,dict),'ledger entry must be an object')
        _require(type(entry.get('repeat')) is int and entry['repeat']==repeat and entry.get('filename')==f'run_{repeat}.json'
            and base._uuid(entry.get('request_uuid')) and type(entry.get('started_ns')) is int and type(entry.get('finished_ns')) is int
            and entry['started_ns']>0 and entry['started_ns']>=end and entry['finished_ns']>=entry['started_ns']
            and type(entry.get('native_exit_status')) is int,'ledger timing/order/native status invalid')
        end=entry['finished_ns']
    return ledger


def compare_case(root,group,seed,scene):
    folder=_folder(root,group,seed,scene);ledger=_ledger(root,group,seed,scene)
    _require(len(ledger['entries'])==2 and not ledger['unattempted_repeats'],'both planned complete children required')
    trials=[]
    for repeat,entry in enumerate(ledger['entries']):
        _require(entry['native_exit_status'] in (0,5) and type(entry.get('accepted_exit_status')) is int
            and entry['accepted_exit_status']==0 and 'error' not in entry,'failed/invalid native child cannot pass')
        wire=json.loads((folder/entry['filename']).read_text());validate_trial(wire,group,seed,scene,repeat)
        _require(entry['request_uuid']==wire['world_frame_expansion_trial']['request_uuid'] and entry.get('process_uuid')==wire['process_uuid']
            and entry.get('process_id')==wire['process_id'],'ledger nonce/process proof differs from raw receipt');trials.append(wire)
    return dict(compare_trials(*trials,group,seed,scene),execution_ledger=ledger,independent_process_count=2)


def _accounted_attempt(wire,entry,group,seed,scene,repeat):
    _require(isinstance(wire,dict),'failed raw attempt must be an object')
    request=wire.get('world_frame_expansion_trial',{})
    _require(base._exact(request,dict(group=group,seed=seed,scenario=scene,repeat=repeat,request_uuid=entry['request_uuid']))
        and base._uuid(wire.get('process_uuid')) and type(wire.get('process_id')) is int and wire['process_id']>0,'failed raw request/process proof invalid')
    _require(wire.get('protocol')==PROTOCOL and type(wire.get('requested_steps')) is int
        and wire['requested_steps']==campaign_spec(group,seed,scene,repeat).steps,'failed raw actual protocol/horizon invalid')
    if wire.get('episode_provenance',{}).get('public_episode_started') is True:
        _require(base._exact(wire.get('source_bindings'),SOURCE_BINDINGS) and wire.get('model_sha256')==base.MODEL_SHA
            and wire.get('runtime',{}).get('injected_session') is False,'failed episode source/model/runtime provenance invalid')
    accounting=attempt_accounting(wire)
    _require(base._exact(wire.get('execution_accounting'),accounting),'stored failed accounting differs from raw receipts')
    return accounting


def aggregate_cases(root):
    cases=[];seen_ids=set();seen_nonces=set();runtimes=[];global_errors=[]
    for group,seed,scene in CASES:
        folder=_folder(root,group,seed,scene);errors=[];accounts=[];attempted=0;unattempted=None;first_incomplete=[]
        try:ledger=_ledger(root,group,seed,scene);unattempted=ledger['unattempted_repeats']
        except Exception as exc:
            ledger=None;errors.append(f'ledger: {type(exc).__name__}: {exc}')
        if ledger is not None:
            for repeat,entry in enumerate(ledger['entries']):
                attempted+=1
                try:
                    wire=json.loads((folder/entry['filename']).read_text());account=_accounted_attempt(wire,entry,group,seed,scene,repeat)
                    identity=wire['process_uuid'];nonce=entry['request_uuid']
                    _require(identity not in seen_ids and nonce not in seen_nonces,'UUID/nonce reused across cohort')
                    seen_ids.add(identity);seen_nonces.add(nonce);accounts.append(account)
                    if isinstance(wire.get('frames'),list) and len(wire['frames'])<campaign_spec(group,seed,scene).steps:
                        first_incomplete.append(len(wire['frames'])+1)
                    if account['errors']:errors.extend(account['errors'])
                    if wire.get('status')=='DIAGNOSTIC_EXECUTED':runtimes.append(wire.get('runtime'))
                except Exception as exc:
                    accounts.append(dict(known_committed_parent_steps=None,total_executed_ort_calls=None,completed_frame_rows=None))
                    errors.append(f'run_{repeat}: {type(exc).__name__}: {exc}')
        try:
            case=compare_case(root,group,seed,scene)
            _require(base._exact(json.loads((folder/'case_comparison.json').read_text()),case),'stale or changed case summary')
        except Exception as exc:
            errors.append(f'complete comparison: {type(exc).__name__}: {exc}')
            case=dict(group=group,seed=seed,scenario=scene,world_frame_expansion_gate_passed=False,
                first_diverging_step=None,first_incomplete_step=min(first_incomplete) if first_incomplete else None)
        if errors:case['world_frame_expansion_gate_passed']=False
        unknown=(ledger is None or any(x['total_executed_ort_calls'] is None for x in accounts))
        known=sum(x['known_committed_parent_steps'] for x in accounts if x['known_committed_parent_steps'] is not None)
        total=None if unknown else sum(x['total_executed_ort_calls'] for x in accounts)
        case.update(aggregation_succeeded=not errors,errors=errors,attempted_process_count=attempted,unattempted_repeats=unattempted,
            known_committed_parent_steps_lower_bound=known,total_executed_ort_calls=total,
            completed_frame_rows=sum(x['completed_frame_rows'] for x in accounts if x['completed_frame_rows'] is not None),
            inference_total_unknown=unknown)
        cases.append(case)
    if runtimes and any(not base._exact(x,runtimes[0]) for x in runtimes):global_errors.append('mixed actual ORT runtimes')
    groups=[]
    for group,config in GROUPS.items():
        subset=[x for x in cases if x['group']==group];unknown=sum(x['inference_total_unknown'] for x in subset)
        groups.append(dict(group=group,gate_pass_count=sum(x['world_frame_expansion_gate_passed'] for x in subset),gate_total=4,
            planned_onnx_steps=8*config['steps'],known_committed_parent_steps_lower_bound=sum(x['known_committed_parent_steps_lower_bound'] for x in subset),
            total_executed_ort_calls=None if unknown else sum(x['total_executed_ort_calls'] for x in subset),unknown_case_count=unknown,
            completed_frame_rows=sum(x['completed_frame_rows'] for x in subset)))
    unknown=sum(x['inference_total_unknown'] for x in cases);passed=sum(x['world_frame_expansion_gate_passed'] for x in cases)
    success=not global_errors and all(x['aggregation_succeeded'] for x in cases)
    result=dict(protocol=PROTOCOL,trial_evidence=EVIDENCE,aggregation_succeeded=success,errors=global_errors,
        world_frame_expansion_gate_pass_count=passed,world_frame_expansion_gate_total=12,world_frame_expansion_all_cases_passed=success and passed==12,
        planned_process_count=24,attempted_process_count=sum(x['attempted_process_count'] for x in cases),independent_process_count=len(seen_ids),planned_onnx_steps=1472,
        known_committed_parent_steps_lower_bound=sum(x['known_committed_parent_steps_lower_bound'] for x in cases),
        total_executed_ort_calls=None if unknown else sum(x['total_executed_ort_calls'] for x in cases),unknown_case_count=unknown,
        completed_frame_rows=sum(x['completed_frame_rows'] for x in cases),per_group=groups,per_case=cases,
        historical_original_gate=dict(passed=0,total=4,status='FAIL'),**CLAIMS)
    stored=Path(root)/'aggregate_summary.json'
    if stored.exists():
        try:
            prior=json.loads(stored.read_text())
            if not base._exact(prior,result):
                original=prior.get('stored_summary_before_revalidation',prior) if isinstance(prior,dict) else prior
                result.update(aggregation_succeeded=False,world_frame_expansion_all_cases_passed=False,stored_summary_before_revalidation=original)
                result['errors'].append('stale or changed final summary; original parsed summary retained')
        except (OSError,ValueError,TypeError) as exc:
            result.update(aggregation_succeeded=False,world_frame_expansion_all_cases_passed=False)
            result['errors'].append(f'invalid stored final summary: {exc}')
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('native','run-case','case','aggregate'),required=True)
    parser.add_argument('--group',choices=tuple(GROUPS));parser.add_argument('--seed',type=int,choices=SEEDS);parser.add_argument('--scene',choices=tuple(SCENARIOS))
    parser.add_argument('--repeat',type=int,choices=(0,1));parser.add_argument('--request-uuid');parser.add_argument('--model',type=Path);parser.add_argument('--spec',type=Path)
    parser.add_argument('--root',type=Path);parser.add_argument('--out',type=Path);args=parser.parse_args(argv)
    if args.mode=='aggregate':
        if args.root is None or args.out is None:parser.error('aggregate requires root/out')
        summary=aggregate_cases(args.root);_write(args.out,summary);return 0 if summary['aggregation_succeeded'] else 2
    if None in (args.group,args.seed,args.scene):parser.error('actual group/seed/scene required')
    if args.mode=='run-case':
        if None in (args.root,args.model,args.spec):parser.error('run-case requires root/model/spec')
        return run_case(root=args.root,model=args.model,spec=args.spec,group=args.group,seed=args.seed,scene=args.scene)
    if args.out is None:parser.error('out required')
    if args.mode=='case':
        if args.root is None:parser.error('case requires root')
        _write(args.out,compare_case(args.root,args.group,args.seed,args.scene));return 0
    if None in (args.model,args.spec,args.repeat,args.request_uuid):parser.error('native requires model/spec/repeat/nonce')
    _require(not args.out.exists(),'fresh raw output required')
    try:result=native_trial(model=args.model,spec=args.spec,group=args.group,seed=args.seed,scene=args.scene,repeat=args.repeat,request_uuid=args.request_uuid)
    except Exception as exc:result=dict(status='ERROR',error=f'{type(exc).__name__}: {exc}',**CLAIMS)
    _write(args.out,result)  # ALL raw failures/dangling records before strict wire validation.
    try:
        wire=json.loads(args.out.read_text());validate_trial(wire,args.group,args.seed,args.scene,args.repeat)
        _require(wire['world_frame_expansion_trial']['request_uuid']==args.request_uuid,'native nonce differs from request')
    except (ValueError,KeyError,TypeError,IndexError) as exc:
        print(f'WORLD_FRAME_EXPANSION_INVALID: {exc}',file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
