"""Bounded experimental MD-V3 expansion; diagnostic collection is not gate PASS."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter, time_ns
import uuid

import numpy as np

from bigbench.curved_lane_scenarios import SCENARIOS, select_native_curve_lanes
from bigbench.kinematics import AgentState, ModelAction, step_ideal
from bigbench.native_model_campaign import CampaignSpec, run_target_lane_episode
from bigbench.native_route import NativeRouteProgress, forward_contiguous_chain
from scripts import native_mdv3_renderer_candidate as base
from scripts.compare_fresh_native_mdv3 import compare_fresh_trials
from scripts.native_opaque_order_matrix import CPU_RECEIPT, opaque_bin_policy
from scripts.native_shadow_sampler_probe import configure_sampler

PROTOCOL='stage7-mdv3-candidate-expansion-v1'
EVIDENCE='CANDIDATE_BOTH_UNSORTED_OFFICIAL_MDV3_EXPANSION'
SEEDS=base.SEEDS
GROUPS={'camera028':dict(scenes=base.SCENES,fraction=.28,steps=12),
        'native_ramps':dict(scenes=('in_ramp','out_ramp'),fraction=.12,steps=12),
        'longer160':dict(scenes=base.SCENES,fraction=.12,steps=160)}
CASES=tuple((group,seed,scene) for group,config in GROUPS.items()
            for seed in SEEDS for scene in config['scenes'])
CLAIMS=dict(base.CLAIMS,full_s_traversal_proven=False)
WARP_HASH_BYTES=2*512*256*3
POLICY_KEYS=('new_img_sha256','raw_model_action','raw_action_sha256','state_after_step_sha256',
             'named_state_receipts','raw_action_receipt','parent_converted_action','named_state_audit_wall_s')
HASH_KEYS=('source_road_rgb_sha256','source_wide_rgb_sha256','road_frame_sha256','wide_frame_sha256')
_new_policy=base._new_policy  # Reuse the unchanged official-file checks BEFORE ORT.
_new_provider=base._new_provider
_new_camera=base._new_camera
_runtime=base._runtime


def campaign_spec(group,seed,scene,repeat=0):
    config=GROUPS.get(group)
    if (config is None or type(seed) is not int or seed not in SEEDS or scene not in config['scenes']
            or type(repeat) is not int or repeat not in (0,1)):
        raise ValueError('unknown prespecified expansion case/repeat')
    return CampaignSpec(scenario=scene,seed=seed,steps=config['steps'],initial_fraction=config['fraction'])


class ExpansionCaptureAudit(base.CandidateCaptureAudit):
    """Delegate once; preserve existing source and actual warped hashes, no RGB retention."""
    def capture(self,pose):
        pair=super().capture(pose)
        row=self.rows[-1];started=perf_counter()
        try:
            source=self.last_source_rgb_sha256
            row.update(source_road_rgb_sha256=source['road'],source_wide_rgb_sha256=source['wide'],
                       road_frame_sha256=pair.road.sha256,wide_frame_sha256=pair.wide.sha256,
                       warped_bytes_hashed=WARP_HASH_BYTES)
            return pair
        except Exception as exc:
            row['hash_audit_error']=f'{type(exc).__name__}: {exc}'
            raise
        finally:
            row['warped_hash_audit_wall_s']=perf_counter()-started


def _lane_receipt(lane):
    direction=getattr(lane,'direction',None)
    if direction is not None:
        value=np.asarray(direction)
        if value.shape==():direction=float(value)
        elif value.shape==(2,):direction=[float(x) for x in value]
        else:raise ValueError('native lane direction must be a scalar or 2D vector')
    return dict(index=str(lane.index),type=f'{type(lane).__module__}.{type(lane).__qualname__}',
                length=float(lane.length),radius=float(lane.radius) if hasattr(lane,'radius') else None,
                direction=direction)


def _geometry(world,selected,route,campaign):
    blocks=[]
    for block in world.blocks:
        config=block.get_config()
        direction=config.get('dir')
        blocks.append(dict(id=str(block.ID),direction=int(direction) if direction is not None else None))
    first=selected[0];xy=first.position(float(first.length)*campaign.initial_fraction,0.)
    pose=AgentState(0.,float(xy[0]),float(xy[1]),float(first.heading_theta_at(float(first.length)*campaign.initial_fraction)),8.)
    return dict(blocks=blocks,selected_lanes=[_lane_receipt(x) for x in selected],
                route_lanes=[_lane_receipt(x) for x in (route.lanes if route else (first,))],initial_pose=asdict(pose))


def _visited(rows):
    values=[]
    for row in rows:
        value=row.get('target_lane_id')
        if not values or values[-1]!=value:values.append(value)
    return values


def native_trial(*,model,spec,group,seed,scene,repeat,request_uuid):
    campaign=campaign_spec(group,seed,scene,repeat)
    if not base._uuid(request_uuid):raise ValueError('fresh expansion nonce required')
    report=dict(status='ERROR',error=None,frames=[])
    policy=camera=provider=bins=sampler=runtime=geometry=route=None
    tasks_before=tasks_after=None;closed=False
    provenance=dict(public_episode_returned=False,returned_status=None,returned_error=None,outer_lifecycle_error=None)
    try:
        policy=_new_policy(Path(model),Path(spec));runtime=_runtime(policy)
        with opaque_bin_policy(1) as bins:
            try:
                provider=_new_provider(seed,scene);engine=provider.env.engine;world=provider.env.current_map
                sampler=configure_sampler(engine,'feedback_both')
                selected=select_native_curve_lanes(world,SCENARIOS[scene])
                if not selected:raise ValueError('actual native curve/ramp lane required')
                if group=='longer160':
                    if len(selected)!=2:raise ValueError('explicit longer prefix requires both native bends')
                    route=NativeRouteProgress(forward_contiguous_chain(world.road_network,selected[0],str(selected[1].index)))
                geometry=_geometry(world,selected,route,campaign)
                camera=ExpansionCaptureAudit(_new_camera(provider));tasks_before=base._tasks(engine)
                report=run_target_lane_episode(policy,camera,selected[0],campaign,route=route)
                provenance.update(public_episode_returned=True,returned_status=report.get('status'),returned_error=report.get('error'))
            finally:
                if provider is not None:
                    try:tasks_after=base._tasks(provider.env.engine)
                    finally:provider.close();closed=True
    except Exception as exc:
        error=f'{type(exc).__name__}: {exc}'
        provenance['outer_lifecycle_error']=error
        report.update(status='FAILED_OR_INCOMPLETE',error=error)
    audits=getattr(policy,'audit_rows',[]);captures=getattr(camera,'rows',[]);trace=getattr(policy,'trace',[])
    rows=report.get('frames',[])
    for index,row in enumerate(rows):
        if index<len(audits):row.update(audits[index])
        if index<len(captures):row['capture_audit']=captures[index]
    official=(policy is not None and getattr(policy,'is_mock',True) is False
              and not getattr(policy,'_injected_session',True) and len(trace)>0)
    report.update(protocol=PROTOCOL,trial_evidence=EVIDENCE if official else 'UNIT_TEST_DOUBLE_OR_FAILED_SETUP_NOT_OFFICIAL_EXECUTION',
        official_model_execution=official,model_sha256=getattr(getattr(policy,'contract',None),'sha256',None),
        model_nbytes=base.MODEL_BYTES,model_spec_sha256=base.SPEC_SHA,scenario=scene,seed=seed,
        requested_steps=campaign.steps,completed_steps=len(rows),initial_fraction=campaign.initial_fraction,
        process_id=os.getpid(),process_uuid=uuid.uuid4().hex,
        expansion_trial=dict(group=group,seed=seed,scenario=scene,repeat=repeat,request_uuid=request_uuid),
        campaign_spec=asdict(campaign),episode_provenance=provenance,
        camera_capture_mode='native_MetaDrive_perceive_sequential_per_step',camera_convergence_attempts=0,
        camera_pixel_tolerance=0,camera_image_interpolation_or_replay=False,gpu_hdr_extraction=False,
        gpu_texture_extract_calls=0,gpu_queries_used=False,rgb_retention_observer=False,pssm_update_preserved=True,
        raw_action_and_recurrent_sha_captured_per_step=True,actual_onnx_image_feed_sha_captured_per_step=True,
        native_source_964x604_rgb_sha_captured_per_step=True,historical_original_gate=dict(passed=0,total=4,status='FAIL'),
        initial_state_receipts=getattr(policy,'initial_state_receipts',None),initial_state_sha256=getattr(policy,'initial_state_sha256',None),
        policy_reset_count=getattr(policy,'policy_reset_count',None),parent_onnx_step_count=len(trace),
        inference_audit_rows=audits,capture_audit_rows=captures,native_geometry=geometry,
        explicit_route_lane_ids=[x['index'] for x in geometry['route_lanes']] if geometry else [],
        full_s_route_requested=group=='longer160',route_active_index_after_episode=route.active_index if route else 0,
        visited_target_lane_ids=_visited(rows),sampler_configuration=sampler,opaque_bin_diagnostic=bins,
        registered_tasks_before=tasks_before,registered_tasks_after=tasks_after,provider_closed=closed,runtime=runtime,
        audit_scope=dict(cpu_only=True,state_bytes_hashed_per_step=base.STATE_BYTES,extra_audit_overhead_free=False,
            original_camera_class='bigbench.native_model_campaign.NativeWorldCamera',capture_delegate_calls=getattr(camera,'delegate_calls',0),
            warped_bytes_hashed_per_capture=WARP_HASH_BYTES),
        raw_sensor_rgb_dims=[964,604],model_rgb_dims=[512,256],actual_i420_shape=[2,6,128,256],actual_i420_dtype='uint8',**CLAIMS)
    return report


def _require(condition,message):
    if not condition:raise ValueError(message)


def _controls(d,campaign,group,seed,scene,repeat):
    expected=dict(protocol=PROTOCOL,trial_evidence=EVIDENCE,official_model_execution=True,
        model_sha256=base.MODEL_SHA,model_nbytes=base.MODEL_BYTES,model_spec_sha256=base.SPEC_SHA,
        scenario=scene,seed=seed,requested_steps=campaign.steps,initial_fraction=campaign.initial_fraction,
        campaign_spec=asdict(campaign),camera_capture_mode='native_MetaDrive_perceive_sequential_per_step',
        camera_convergence_attempts=0,camera_pixel_tolerance=0,camera_image_interpolation_or_replay=False,
        gpu_hdr_extraction=False,gpu_texture_extract_calls=0,gpu_queries_used=False,rgb_retention_observer=False,
        pssm_update_preserved=True,raw_action_and_recurrent_sha_captured_per_step=True,
        actual_onnx_image_feed_sha_captured_per_step=True,native_source_964x604_rgb_sha_captured_per_step=True,
        historical_original_gate=dict(passed=0,total=4,status='FAIL'),policy_reset_count=2,provider_closed=True,
        full_s_route_requested=group=='longer160',raw_sensor_rgb_dims=[964,604],model_rgb_dims=[512,256],
        actual_i420_shape=[2,6,128,256],actual_i420_dtype='uint8',**CLAIMS)
    _require(all(base._exact(d.get(k),v) for k,v in expected.items()),'expansion identity/model/capture/non-promotion controls invalid')
    request=d.get('expansion_trial',{})
    _require(base._uuid(request.get('request_uuid')) and base._exact(request,dict(group=group,seed=seed,scenario=scene,repeat=repeat,
        request_uuid=request.get('request_uuid'))),'expansion nonce/case/repeat invalid')
    _require(type(d.get('process_id')) is int and d['process_id']>0 and base._uuid(d.get('process_uuid')),'fresh native identity required')
    initial,aggregate=base._initial_receipts();base._validate_states(d.get('initial_state_receipts'))
    _require(base._exact(d['initial_state_receipts'],initial) and d.get('initial_state_sha256')==aggregate,'exact parent reset state required')
    tasks=d.get('registered_tasks_before');after=d.get('registered_tasks_after')
    _require(isinstance(tasks,list) and isinstance(after,list) and all(type(x) is str for x in tasks+after)
        and tasks==sorted(tasks) and tasks==after and all(tasks.count(k)==1 for k in ('igLoop','PSSM.update','update main chase camera')),
        'original task registry not preserved')
    guard=dict(enabled=True,original_camera_states_empty=[True,True],camera_count=2,shader_replaced=False,
        input_priority=1000000,inputs=['use_pssm','PSSMShadowAtlas'],placeholder=dict(dimensions=[1,1],format='RGBA8',rgba=[255]*4,filters=[1,1]))
    sampler=dict(mode='feedback_both',filters_before=[6,6],filters_after=[1,1],metadrive_version='0.4.3',
        loaded_fragment_shader_sha256=base.SHADER_SHA256,shader_edited=False,manual_pcf_sampler2d_confirmed=True,
        renderer_semantics_experimental=True,shadow_guard=guard)
    _require(base._exact(d.get('sampler_configuration'),sampler),'candidate sampler/guard invalid')
    bins=d.get('opaque_bin_diagnostic',{});before=bins.get('before')
    _require(isinstance(before,dict) and set(before)=={'index','name','type','sort','active'}
        and type(before.get('index')) is int and before['index']>=0 and before.get('name')=='opaque'
        and type(before.get('type')) is int and before['type']==2 and type(before.get('sort')) is int and type(before.get('active')) is bool
        and base._exact(bins,dict(CPU_RECEIPT,before=before,requested_type=1,configured=dict(before,type=1),after_capture=dict(before,type=1),restored=before)),
        'opaque configuration/restore invalid')
    runtime=d.get('runtime',{})
    _require(isinstance(runtime,dict) and set(runtime)=={'ort_version','providers','optimization_level','injected_session'}
        and type(runtime.get('ort_version')) is str and bool(runtime['ort_version'])
        and base._exact(runtime.get('providers'),['CPUExecutionProvider']) and type(runtime.get('optimization_level')) is int
        and runtime['optimization_level']==1 and runtime.get('injected_session') is False,'actual CPU/basic parent runtime invalid')


def _validate_geometry(d,group,scene):
    geometry=d.get('native_geometry')
    _require(isinstance(geometry,dict) and set(geometry)=={'blocks','selected_lanes','route_lanes','initial_pose'},'actual native geometry receipt required')
    blocks=geometry['blocks'];case=SCENARIOS[scene]
    _require(isinstance(blocks,list) and bool(blocks),'actual native blocks required')
    for block in blocks:
        _require(isinstance(block,dict) and set(block)=={'id','direction'} and type(block['id']) is str and bool(block['id'])
            and (block['direction'] is None or type(block['direction']) is int),'native block metadata invalid')
    chosen=[x for x in blocks if x['id'] in case.block_ids]
    _require(tuple(x['id'] for x in chosen)==case.block_ids,'actual curve/ramp block identities invalid')
    if case.expected_curve_directions:
        _require(tuple(x['direction'] for x in chosen)==case.expected_curve_directions,'actual S bend directions invalid')
    selected=geometry['selected_lanes'];route=geometry['route_lanes']
    _require(isinstance(selected,list) and bool(selected) and isinstance(route,list) and bool(route),'native lane/route receipts required')
    for lane in selected+route:
        direction=lane.get('direction') if isinstance(lane,dict) else None
        valid_direction=(direction is None or type(direction) in (int,float) and math.isfinite(direction)
            or isinstance(direction,list) and len(direction)==2
            and all(type(x) in (int,float) and math.isfinite(x) for x in direction) and any(x!=0 for x in direction))
        _require(isinstance(lane,dict) and set(lane)=={'index','type','length','radius','direction'}
            and all(type(lane[k]) is str and bool(lane[k]) for k in ('index','type'))
            and type(lane['length']) in (int,float) and math.isfinite(lane['length']) and lane['length']>0
            and (lane['radius'] is None or type(lane['radius']) in (int,float) and math.isfinite(lane['radius'])) and valid_direction,
            'actual native lane fields invalid')
    _require(all(type(x['radius']) in (int,float) and x['radius']>0 for x in selected),'selected native circular lane required')
    _require(len(selected)<=2 if group=='native_ramps' else len(selected)==2,'native selected lane count invalid')
    if group!='native_ramps':
        _require(all(type(x['direction']) in (int,float) and x['direction']!=0 for x in selected)
            and len({math.copysign(1.,x['direction']) for x in selected})==2,'native forward bends must reverse curvature sign')
    _require(len({x['index'] for x in selected})==len(selected),'selected native lane identities repeated')
    ids=[x['index'] for x in route]
    _require(len(set(ids))==len(ids) and base._exact(d.get('explicit_route_lane_ids'),ids)
        and base._exact(route[0],selected[0]),'explicit route identities/start invalid')
    if group=='longer160':
        _require(len(route)>=2 and base._exact(route[-1],selected[1]),'explicit second-bend route endpoint required')
    else:_require(len(route)==1,'short scene must preserve original selected lane')
    index=d.get('route_active_index_after_episode')
    _require(type(index) is int and 0<=index<len(route),'actual route active index invalid')
    initial=base._pose(geometry['initial_pose'])
    _require(initial.t==0. and initial.speed==8.,'native initial virtual pose invalid')
    return ids,initial


def _validate_action(audit):
    _require(isinstance(audit,dict) and set(audit)==set(POLICY_KEYS),'all parent inference audit fields required')
    for key in ('new_img_sha256','raw_action_sha256','state_after_step_sha256'):
        _require(base._hash(audit.get(key)),'missing actual inference SHA: '+key)
    base._validate_states(audit.get('named_state_receipts'))
    raw=audit.get('raw_model_action')
    _require(isinstance(raw,list) and len(raw)==4 and all(type(x) in (int,float) and math.isfinite(x) for x in raw),'four finite raw action values required')
    values=np.asarray(raw,dtype=np.float32)
    from hashlib import sha256
    _require(np.isfinite(values).all() and raw==values.tolist() and sha256(values.tobytes(order='C')).hexdigest()==audit['raw_action_sha256'],
             'raw float32 action bytes do not match values')
    _require(base._exact(audit.get('raw_action_receipt'),dict(name='action',dtype='float32',shape=[4],nbytes=16,sha256=audit['raw_action_sha256'])),
             'actual action schema invalid')
    action=ModelAction(float(values[0])/64.,float(values[1]))
    _require(base._exact(audit.get('parent_converted_action'),asdict(action)) and base._duration(audit.get('named_state_audit_wall_s')),
             'unchanged parent action conversion/audit time required')
    return action


def _validate_capture(capture,previous_pose,previous_clock):
    keys={'entry_pose','before','after','delegate_calls','global_clock_frame_count_delta','global_clock_time_delta_s',
          'real_time_delta_s','capture_wall_s','warped_bytes_hashed','warped_hash_audit_wall_s',*HASH_KEYS}
    _require(isinstance(capture,dict) and set(capture)==keys,'successful complete capture/hash audit required')
    pose=base._pose(capture['entry_pose'])
    _require(pose==previous_pose and type(capture['delegate_calls']) is int and capture['delegate_calls']==1
        and type(capture['warped_bytes_hashed']) is int and capture['warped_bytes_hashed']==WARP_HASH_BYTES
        and all(base._duration(capture.get(k)) for k in ('capture_wall_s','warped_hash_audit_wall_s')),'capture virtual pose/delegation/hash scope invalid')
    _require(all(base._hash(capture.get(k)) for k in HASH_KEYS),'native source/warped capture SHA missing')
    a,b=capture['before'],capture['after']
    _require(all(isinstance(c,dict) and set(c)=={'frame_count','frame_time_s','real_time_s','dt_s'}
        and type(c['frame_count']) is int and c['frame_count']>=0 and all(base._duration(c[k]) for k in ('frame_time_s','real_time_s','dt_s')) for c in (a,b)),
        'finite actual Panda clock receipt required')
    _require(b['frame_count']-a['frame_count']==2 and type(capture['global_clock_frame_count_delta']) is int
        and capture['global_clock_frame_count_delta']==2 and all(base._duration(capture[k]) for k in ('global_clock_time_delta_s','real_time_delta_s'))
        and b['frame_time_s']-a['frame_time_s']==capture['global_clock_time_delta_s']
        and b['real_time_s']-a['real_time_s']==capture['real_time_delta_s']
        and (previous_clock is None or a['frame_count']==previous_clock['frame_count']
             and a['frame_time_s']==previous_clock['frame_time_s'] and a['real_time_s']>=previous_clock['real_time_s']),
        'original contiguous two-tick clock contract invalid')
    return pose,b


def validate_trial(d,group,seed,scene,repeat,*,native_exit_status=None):
    campaign=campaign_spec(group,seed,scene,repeat);_controls(d,campaign,group,seed,scene,repeat)
    ids,expected_pose=_validate_geometry(d,group,scene)
    rows=d.get('frames');audits=d.get('inference_audit_rows');captures=d.get('capture_audit_rows')
    _require(all(isinstance(x,list) for x in (rows,audits,captures)),'all raw frame/capture/inference arrays required')
    m=len(rows);n=len(audits);provenance=d.get('episode_provenance')
    _require(base._exact(provenance,dict(public_episode_returned=True,returned_status=d.get('status'),returned_error=d.get('error'),
                                      outer_lifecycle_error=None)),'actual public episode return and clean outer lifecycle required')
    complete=(m==campaign.steps and d.get('status')=='DIAGNOSTIC_EXECUTED' and d.get('error') is None and n==m)
    error=d.get('error')
    partial=(0<m<campaign.steps and d.get('status')=='FAILED_OR_INCOMPLETE' and type(error) is str
        and any(error.startswith(prefix) and len(error)>len(prefix) for prefix in ('LaneTruthError: ','RouteContractError: ')) and n==m+1)
    _require(complete or partial,'episode is neither complete nor a prespecified post-inference truth failure')
    classification='COMPLETE' if complete else 'VALID_FAILED_DIAGNOSTIC'
    if native_exit_status is not None:
        _require(type(native_exit_status) is int and native_exit_status in ((0,5) if complete else (2,)),
                 'actual native exit status conflicts with complete/failed diagnostic receipt')
    _require(len(captures)==n and type(d.get('parent_onnx_step_count')) is int and d['parent_onnx_step_count']==n
        and type(d.get('completed_steps')) is int and d['completed_steps']==m,'actual parent/capture/frame counts inconsistent')
    _require(base._exact(d.get('audit_scope'),dict(cpu_only=True,state_bytes_hashed_per_step=base.STATE_BYTES,
        extra_audit_overhead_free=False,original_camera_class='bigbench.native_model_campaign.NativeWorldCamera',
        capture_delegate_calls=n,warped_bytes_hashed_per_capture=WARP_HASH_BYTES)),'actual CPU audit/delegation scope invalid')
    previous_clock=None;last_lane_index=0
    for index in range(n):
        action=_validate_action(audits[index]);pose,previous_clock=_validate_capture(captures[index],expected_pose,previous_clock)
        expected_pose=step_ideal(pose,action,.05,speed_override=8.)
        if index>=m:continue  # Retained failed-truth audit is not fabricated into a completed row.
        row=rows[index]
        _require(isinstance(row,dict) and type(row.get('step')) is int and row['step']==index+1,'sequential completed frame row required')
        _require(all(base._exact(row.get(k),audits[index][k]) for k in POLICY_KEYS)
            and base._exact(row.get('capture_audit'),captures[index])
            and all(base._exact(row.get(k),captures[index][k]) for k in HASH_KEYS),'frame differs from actual capture/inference receipts')
        values=[row.get(k) for k in ('time_s','world_x_m','world_y_m','heading_rad','speed_mps')]
        _require(all(type(x) in (int,float) and math.isfinite(x) for x in values)
            and values==[expected_pose.t,expected_pose.x,expected_pose.y,expected_pose.heading,expected_pose.speed]
            and all(type(row.get(k)) in (int,float) and math.isfinite(row[k])
                    for k in ('desired_curvature_1pm','desired_acceleration_mps2'))
            and row.get('desired_curvature_1pm')==action.curvature_1pm and row.get('desired_acceleration_mps2')==action.acceleration_mps2,
            'actual post-action state/time or unchanged action differs')
        lane=row.get('target_lane_id');_require(lane in ids,'completed truth lane outside explicit native route')
        current=ids.index(lane);_require(current>=last_lane_index,'native truth route moved backwards');last_lane_index=current
        _require(all(type(row.get(k)) in (int,float) and math.isfinite(row[k]) for k in ('lateral_right_m','lane_intrusion_m'))
            and row['lane_intrusion_m']>=0 and (row.get('inside_turn_offset_m') is None
                or type(row.get('inside_turn_offset_m')) in (int,float) and math.isfinite(row['inside_turn_offset_m'])),
            'finite native lane truth fields required')
    _require(base._exact(d.get('visited_target_lane_ids'),_visited(rows)) and d['route_active_index_after_episode']>=last_lane_index,
             'observed successful truth visits/actual active index inconsistent')
    if complete:_require(d['route_active_index_after_episode']==last_lane_index,'complete final route index differs from final truth')
    return classification


def compare_trials(a,b,group,seed,scene):
    classes=[validate_trial(d,group,seed,scene,repeat) for repeat,d in enumerate((a,b))]
    _require(a['process_uuid']!=b['process_uuid'] and a['process_id']!=b['process_id']
        and a['expansion_trial']['request_uuid']!=b['expansion_trial']['request_uuid'],'independent native processes/nonces required')
    top=('campaign_spec','initial_state_receipts','initial_state_sha256','runtime','sampler_configuration','opaque_bin_diagnostic',
         'registered_tasks_before','registered_tasks_after','native_geometry','explicit_route_lane_ids')
    _require(all(base._exact(a[k],b[k]) for k in top),'repeat initial native/model/runtime/configuration differs')
    complete=all(x=='COMPLETE' for x in classes);common=None;extra=[]
    if complete:
        common=compare_fresh_trials(a,b)
        for index,(x,y) in enumerate(zip(a['frames'],b['frames']),1):
            differing=[k for k in ('named_state_receipts','raw_action_receipt','parent_converted_action','target_lane_id',
                                  'lateral_right_m','inside_turn_offset_m','lane_intrusion_m') if not base._exact(x[k],y[k])]
            if x['capture_audit']['entry_pose']!=y['capture_audit']['entry_pose']:differing.append('capture_entry_pose')
            if any(x['capture_audit'][p]['frame_count']!=y['capture_audit'][p]['frame_count'] for p in ('before','after')):
                differing.append('capture_panda_frame_counts')
            if differing:extra.append(dict(step=index,differing_fields=differing))
    firsts=[x for x in (common['first_diverging_step'] if common else None,extra[0]['step'] if extra else None) if x is not None]
    passed=complete and common['exact_repeated_execution_gate_passed'] and not extra
    incomplete=[d['completed_steps']+1 for d,c in zip((a,b),classes) if c!='COMPLETE']
    return dict(protocol=PROTOCOL,group=group,seed=seed,scenario=scene,trial_evidence=EVIDENCE,
        status='EXPANSION_REPEAT_MATCH' if passed else 'EXPANSION_GATE_NOT_PASSED',candidate_expansion_gate_passed=passed,
        reason=None if passed else 'INCOMPLETE_REQUESTED_EPISODE' if incomplete else 'EXACT_REPEAT_MISMATCH',
        first_incomplete_step=min(incomplete) if incomplete else None,first_diverging_step=min(firsts) if firsts else None,
        diagnostic_classifications=classes,common_strict_comparison=common,extra_mismatches=extra,
        actual_onnx_steps=sum(d['parent_onnx_step_count'] for d in (a,b)),completed_frame_rows=sum(d['completed_steps'] for d in (a,b)),
        process_uuids=[a['process_uuid'],b['process_uuid']],**CLAIMS)


def _folder(root,group,seed,scene):
    campaign_spec(group,seed,scene)
    return Path(root)/group/f'seed-{seed}'/scene


def _write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def launch_trial(*,model,spec,group,seed,scene,repeat,out,request_uuid=None,status_receipt=None):
    campaign_spec(group,seed,scene,repeat);nonce=uuid.uuid4().hex if request_uuid is None else request_uuid
    _require(base._uuid(nonce),'fresh launch nonce required')
    out=Path(out);log=out.with_suffix('.log')
    _require(not out.exists() and not log.exists(),'fresh output/log required');out.parent.mkdir(parents=True,exist_ok=True)
    command=['xvfb-run','-a',sys.executable,'-m','scripts.native_mdv3_candidate_expansion','--mode','native',
        '--model',str(model),'--spec',str(spec),'--group',group,'--seed',str(seed),'--scene',scene,'--repeat',str(repeat),
        '--request-uuid',nonce,'--out',str(out)]
    with log.open('x') as stream:status=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT).returncode
    if status_receipt is not None:status_receipt.append(status)
    if status not in (0,2,5):return dict(native_exit_status=status,diagnostic_classification=None)
    wire=json.loads(out.read_text());classification=validate_trial(wire,group,seed,scene,repeat,native_exit_status=status)
    _require(wire['expansion_trial']['request_uuid']==nonce,'fresh receipt nonce differs from launch request')
    return dict(native_exit_status=status,diagnostic_classification=classification,process_id=wire['process_id'],process_uuid=wire['process_uuid'])


def run_case(*,root,model,spec,group,seed,scene):
    folder=_folder(root,group,seed,scene);_require(not folder.exists(),'fresh case directory required');folder.mkdir(parents=True)
    ledger=dict(group=group,seed=seed,scenario=scene,entries=[])
    for repeat in (0,1):
        nonce=uuid.uuid4().hex;statuses=[]
        entry=dict(repeat=repeat,filename=f'run_{repeat}.json',request_uuid=nonce,started_ns=time_ns(),finished_ns=None,
                   native_exit_status=None,diagnostic_classification=None)
        ledger['entries'].append(entry);_write(folder/'execution_ledger.json',ledger)
        try:
            receipt=launch_trial(model=model,spec=spec,group=group,seed=seed,scene=scene,repeat=repeat,
                out=folder/entry['filename'],request_uuid=nonce,status_receipt=statuses)
            entry.update(receipt)
            if receipt['diagnostic_classification'] is None:return receipt['native_exit_status']
        except Exception as exc:
            entry['error']=f'{type(exc).__name__}: {exc}'
            raise
        finally:
            entry['finished_ns']=time_ns();entry['native_exit_status']=statuses[0] if statuses else None
            _write(folder/'execution_ledger.json',ledger)
    _write(folder/'case_comparison.json',compare_case(root,group,seed,scene))
    return 0  # Receipt collection succeeded; native 2 remains 2 and the full gate remains false.


def compare_case(root,group,seed,scene):
    folder=_folder(root,group,seed,scene);ledger=json.loads((folder/'execution_ledger.json').read_text())
    _require(all(base._exact(ledger.get(k),v) for k,v in dict(group=group,seed=seed,scenario=scene).items()),'ledger case identity invalid')
    entries=ledger.get('entries');_require(isinstance(entries,list) and len(entries)==2,'two native child ledger entries required')
    trials=[];previous_end=0
    for repeat,entry in enumerate(entries):
        _require(type(entry.get('repeat')) is int and entry['repeat']==repeat and entry.get('filename')==f'run_{repeat}.json'
            and type(entry.get('native_exit_status')) is int and entry['native_exit_status'] in (0,2,5)
            and type(entry.get('started_ns')) is int and type(entry.get('finished_ns')) is int
            and entry['started_ns']>0 and entry['started_ns']>=previous_end and entry['finished_ns']>=entry['started_ns'] and 'error' not in entry,
            'native ledger order/timing/status invalid')
        previous_end=entry['finished_ns'];wire=json.loads((folder/entry['filename']).read_text())
        classification=validate_trial(wire,group,seed,scene,repeat,native_exit_status=entry['native_exit_status'])
        _require(entry.get('diagnostic_classification')==classification and entry.get('request_uuid')==wire['expansion_trial']['request_uuid']
            and entry.get('process_uuid')==wire['process_uuid'] and entry.get('process_id')==wire['process_id'],'ledger receipt identity/classification mismatch')
        trials.append(wire)
    return dict(compare_trials(*trials,group,seed,scene),execution_ledger=ledger,independent_process_count=2)


def aggregate_cases(root):
    cases=[];ids=set();nonces=set();runtimes=[]
    for group,seed,scene in CASES:
        case=compare_case(root,group,seed,scene);folder=_folder(root,group,seed,scene)
        _require(base._exact(json.loads((folder/'case_comparison.json').read_text()),case),'stale or changed expansion case summary')
        for repeat in (0,1):
            wire=json.loads((folder/f'run_{repeat}.json').read_text());identity=wire['process_uuid'];nonce=wire['expansion_trial']['request_uuid']
            _require(identity not in ids and nonce not in nonces,'native UUID/nonce reused across expansion cohort')
            ids.add(identity);nonces.add(nonce);runtimes.append(wire['runtime'])
        cases.append(case)
    _require(all(base._exact(x,runtimes[0]) for x in runtimes),'mixed ORT runtimes across expansion cohort')
    groups=[]
    for group,config in GROUPS.items():
        subset=[case for case in cases if case['group']==group];passed=sum(case['candidate_expansion_gate_passed'] for case in subset)
        groups.append(dict(group=group,case_count=len(subset),gate_pass_count=passed,all_cases_passed=passed==4,
            planned_onnx_steps=8*config['steps'],actual_onnx_steps=sum(x['actual_onnx_steps'] for x in subset),
            completed_frame_rows=sum(x['completed_frame_rows'] for x in subset)))
    passed=sum(x['candidate_expansion_gate_passed'] for x in cases)
    result=dict(protocol=PROTOCOL,trial_evidence=EVIDENCE,status='EXPANSION_ALL_CASES_PASS' if passed==12 else 'EXPANSION_GATE_NOT_PASSED',
        candidate_expansion_gate_pass_count=passed,candidate_expansion_gate_total=12,candidate_expansion_all_cases_passed=passed==12,
        planned_process_count=24,independent_process_count=len(ids),planned_onnx_steps=sum(8*x['steps'] for x in GROUPS.values()),
        actual_onnx_steps=sum(x['actual_onnx_steps'] for x in cases),completed_frame_rows=sum(x['completed_frame_rows'] for x in cases),
        per_group=groups,per_case=cases,historical_original_gate=dict(passed=0,total=4,status='FAIL'),**CLAIMS)
    stored=Path(root)/'aggregate_summary.json'
    if stored.exists():_require(base._exact(json.loads(stored.read_text()),result),'stale or changed expansion final summary')
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('native','run-case','case','aggregate'),required=True)
    parser.add_argument('--group',choices=tuple(GROUPS));parser.add_argument('--seed',type=int,choices=SEEDS)
    parser.add_argument('--scene',choices=tuple(SCENARIOS));parser.add_argument('--repeat',type=int,choices=(0,1))
    parser.add_argument('--request-uuid');parser.add_argument('--model',type=Path);parser.add_argument('--spec',type=Path)
    parser.add_argument('--root',type=Path);parser.add_argument('--out',type=Path);args=parser.parse_args(argv)
    if args.mode=='aggregate':
        if args.root is None or args.out is None:parser.error('aggregate requires root/out')
        _write(args.out,aggregate_cases(args.root));return 0
    if None in (args.group,args.seed,args.scene):parser.error('case identity required')
    if args.mode=='run-case':
        if None in (args.root,args.model,args.spec):parser.error('run-case requires root/model/spec')
        return run_case(root=args.root,model=args.model,spec=args.spec,group=args.group,seed=args.seed,scene=args.scene)
    if args.out is None:parser.error('out required')
    if args.mode=='case':_write(args.out,compare_case(args.root,args.group,args.seed,args.scene));return 0
    if None in (args.model,args.spec,args.repeat,args.request_uuid):parser.error('native requires model/spec/repeat/nonce')
    _require(not args.out.exists(),'fresh native output required')
    try:
        result=native_trial(model=args.model,spec=args.spec,group=args.group,seed=args.seed,scene=args.scene,
                            repeat=args.repeat,request_uuid=args.request_uuid)
    except Exception as exc:result=dict(status='ERROR',error=f'{type(exc).__name__}: {exc}',**CLAIMS)
    _write(args.out,result)  # Preserve complete raw/partial evidence BEFORE wire validation.
    try:
        wire=json.loads(args.out.read_text());classification=validate_trial(wire,args.group,args.seed,args.scene,args.repeat)
        _require(wire['expansion_trial']['request_uuid']==args.request_uuid,'native nonce differs from requested nonce')
    except (ValueError,KeyError,TypeError) as exc:
        print(f'EXPANSION_RECEIPT_INVALID: {exc}',file=sys.stderr);return 2
    return 0 if classification=='COMPLETE' else 2


if __name__=='__main__':raise SystemExit(main())
