"""Experimental both+unsorted official MD-V3 repeatability, never a default fix.

The original camera, episode loop, image adapter, policy step and kinematics are
delegated unchanged. Extra named-state/capture/clock audits are CPU overhead.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from functools import lru_cache
from hashlib import sha256
import importlib.metadata
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
from bigbench.native_model_campaign import CampaignSpec, NativeWorldCamera, run_target_lane_episode
from bigbench.onnx_contract import ModelContract
from scripts.compare_fresh_native_mdv3 import compare_fresh_trials
from scripts.compare_native_shadow_sampler import SHADER_SHA256
from scripts.native_mdv3_repeat_trial import AuditedOfficialOnnx, recurrent_receipt
from scripts.native_opaque_order_matrix import opaque_bin_policy, CPU_RECEIPT
from scripts.native_shadow_sampler_probe import configure_sampler

SEEDS=(20261109,20261110)
SCENES=('s_curve_left_right','s_curve_right_left')
MODEL_SHA='35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199'
MODEL_BYTES=768750198
SPEC_SHA='689f4d80082070b08ff35920e37d7070e811dfb42a279909751f79e900c735e2'
EVIDENCE='CANDIDATE_BOTH_UNSORTED_OFFICIAL_MDV3'
STATE_SCHEMA={'state_img_q':('uint8',[2,5,6,128,256],1966080),
              'state_desire_q':('float32',[132,1,8],4224),
              'state_feat_q':('float32',[128,1,16384],8388608)}
STATE_BYTES=10358912
CLAIMS=dict(original_mdv3_gate_passed=False,default_renderer_promoted=False,
            full_renderer_equivalence_proven=False,unique_renderer_microcause_proven=False,
            model_scoring_allowed=False,real_vehicle_testing=False,cd210_fallback=False,carrot_tuning_used=False)


def _configuration(seed,scene,repeat):
    if seed not in SEEDS or scene not in SCENES or type(repeat) is not int or repeat not in (0,1):
        raise ValueError('unknown bounded candidate case/repeat')


def _hash(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def _uuid(value):return isinstance(value,str) and len(value)==32 and all(c in '0123456789abcdef' for c in value)
def _duration(value):return type(value) in (int,float) and math.isfinite(value) and value>=0


def _exact(value,expected):
    if type(value) is not type(expected):return False
    if isinstance(expected,dict):return value.keys()==expected.keys() and all(_exact(value[k],v) for k,v in expected.items())
    if isinstance(expected,list):return len(value)==len(expected) and all(_exact(a,b) for a,b in zip(value,expected))
    return value==expected


def named_state_receipts(states):
    if not isinstance(states,dict) or set(states)!=set(STATE_SCHEMA):raise ValueError('all three exact named states required')
    result={}
    for name,(dtype,shape,nbytes) in STATE_SCHEMA.items():
        value=np.asarray(states[name])
        if str(value.dtype)!=dtype or list(value.shape)!=shape or value.nbytes!=nbytes or not np.isfinite(value).all():
            raise ValueError('incorrect recurrent state schema or values: '+name)
        result[name]=dict(name=name,dtype=dtype,shape=shape.copy(),nbytes=nbytes,sha256=sha256(value.tobytes(order='C')).hexdigest())
    return result


@lru_cache(maxsize=1)
def _initial_receipts():
    states={k:np.zeros(shape,dtype=dtype) for k,(dtype,shape,_) in STATE_SCHEMA.items()}
    return named_state_receipts(states),recurrent_receipt(states)


class CandidateAuditedOnnx(AuditedOfficialOnnx):
    def reset(self):
        super().reset()
        self.policy_reset_count=getattr(self,'policy_reset_count',0)+1
        self.initial_state_receipts=named_state_receipts(self.state)
        self.initial_state_sha256=recurrent_receipt(self.state)

    def step(self,observation):
        action=super().step(observation)  # Actual parent inference exactly once.
        started=perf_counter()
        raw=self.last_model_outputs['action']
        if not isinstance(raw,np.ndarray) or raw.dtype!=np.float32 or raw.shape!=(4,) or not np.isfinite(raw).all():
            raise ValueError('official raw action must be four finite float32 values')
        self.audit_rows[-1].update(named_state_receipts=named_state_receipts(self.state),
            raw_action_receipt=dict(name='action',dtype=str(raw.dtype),shape=list(raw.shape),nbytes=int(raw.nbytes),
                                    sha256=sha256(raw.tobytes(order='C')).hexdigest()),
            parent_converted_action=asdict(action),named_state_audit_wall_s=perf_counter()-started)
        return action


def _new_policy(model,spec):
    # No public test-model bypass. Verify actual pinned file BEFORE ORT creation.
    if sha256(Path(spec).read_bytes()).hexdigest()!=SPEC_SHA:raise ValueError('official MD-V3 spec bytes changed')
    contract=ModelContract.load(Path(spec))
    if contract.sha256!=MODEL_SHA or contract.nbytes!=MODEL_BYTES:raise ValueError('wrong official MD-V3 contract')
    contract.check_file(Path(model))
    return CandidateAuditedOnnx(Path(model),Path(spec))


def _new_provider(seed,scene):
    from bigbench.metadrive_camera import NativeMetaDriveProvider
    return NativeMetaDriveProvider(seed=seed,map_config=SCENARIOS[scene].map_config())


def _new_camera(provider):return NativeWorldCamera(provider)


def clock_sample():
    from scripts.native_raw_pixel_clock import clock_receipt
    return clock_receipt()


class CandidateCaptureAudit:
    def __init__(self,delegate):self.delegate=delegate;self.rows=[];self.delegate_calls=0
    @property
    def last_source_rgb_sha256(self):return self.delegate.last_source_rgb_sha256
    def capture(self,pose):
        before=clock_sample();started=perf_counter();row=dict(entry_pose=asdict(pose),before=before,delegate_calls=1)
        self.delegate_calls+=1
        try:return self.delegate.capture(pose)
        except Exception as exc:
            row['error']=f'{type(exc).__name__}: {exc}';raise
        finally:
            after=clock_sample()
            row.update(after=after,global_clock_frame_count_delta=after['frame_count']-before['frame_count'],
                global_clock_time_delta_s=after['frame_time_s']-before['frame_time_s'],
                real_time_delta_s=after['real_time_s']-before['real_time_s'],capture_wall_s=perf_counter()-started)
            self.rows.append(row)


def _tasks(engine):return sorted(task.getName() for task in engine.taskMgr.getTasks())


def _runtime(policy):
    return dict(ort_version=importlib.metadata.version('onnxruntime'),providers=policy.session.get_providers(),
                optimization_level=int(policy.session.get_session_options().graph_optimization_level),
                injected_session=policy._injected_session)


def native_trial(*,model,spec,seed,scene,repeat,request_uuid):
    _configuration(seed,scene,repeat)
    if not _uuid(request_uuid):raise ValueError('fresh candidate request UUID required')
    campaign=CampaignSpec(scenario=scene,seed=seed,steps=12,speed_mps=8.,dt_s=.05,initial_fraction=.12)
    report=dict(status='ERROR',error=None,frames=[]);policy=None;camera=None;provider=None;bins=None;sampler=None
    before_tasks=None;after_tasks=None;closed=False;runtime=None;lane_ids=[]
    try:
        policy=_new_policy(Path(model),Path(spec));runtime=_runtime(policy)
        with opaque_bin_policy(1) as bins:
            try:
                provider=_new_provider(seed,scene)
                sampler=configure_sampler(provider.env.engine,'feedback_both')
                lanes=select_native_curve_lanes(provider.env.current_map,SCENARIOS[scene])
                if not lanes:raise ValueError('scene does not contain the original native curve')
                lane_ids=[str(lanes[0].index)]
                camera=CandidateCaptureAudit(_new_camera(provider))
                before_tasks=_tasks(provider.env.engine)
                report=run_target_lane_episode(policy,camera,lanes[0],campaign,route=None)
            finally:
                if provider is not None:
                    try:after_tasks=_tasks(provider.env.engine)
                    finally:provider.close();closed=True
    except Exception as exc:
        report['status']='FAILED_OR_INCOMPLETE';report['error']=f'{type(exc).__name__}: {exc}'
    audit_rows=getattr(policy,'audit_rows',[]);capture_rows=getattr(camera,'rows',[])
    if report.get('status')=='DIAGNOSTIC_EXECUTED' and any(count!=12 for count in
            (len(report.get('frames',[])),len(audit_rows),len(capture_rows),len(getattr(policy,'trace',[])))):
        report['status']='FAILED_OR_INCOMPLETE';report['error']='native capture/inference/audit step counts differ'
    for index,row in enumerate(report.get('frames',[])):
        if index<len(audit_rows):row.update(audit_rows[index])
        if index<len(capture_rows):row['capture_audit']=capture_rows[index]
    official=(policy is not None and getattr(policy,'is_mock',True) is False
              and not getattr(policy,'_injected_session',True) and len(getattr(policy,'trace',[]))>0)
    report.update(model_sha256=getattr(getattr(policy,'contract',None),'sha256',None),model_nbytes=MODEL_BYTES,
        model_spec_sha256=SPEC_SHA,scenario=scene,seed=seed,requested_steps=12,initial_fraction=.12,
        completed_steps=len(report.get('frames',[])),process_id=os.getpid(),process_uuid=uuid.uuid4().hex,
        candidate_trial=dict(seed=seed,scenario=scene,repeat=repeat,request_uuid=request_uuid),
        trial_evidence=EVIDENCE if official else 'UNIT_TEST_DOUBLE_OR_FAILED_SETUP_NOT_OFFICIAL_EXECUTION',
        official_model_execution=official,camera_capture_mode='native_MetaDrive_perceive_sequential_per_step',
        camera_convergence_attempts=0,camera_pixel_tolerance=0,camera_image_interpolation_or_replay=False,
        gpu_hdr_extraction=False,gpu_texture_extract_calls=0,gpu_queries_used=False,rgb_retention_observer=False,
        pssm_update_preserved=True,raw_action_and_recurrent_sha_captured_per_step=True,
        actual_onnx_image_feed_sha_captured_per_step=True,native_source_964x604_rgb_sha_captured_per_step=True,
        historical_original_gate=dict(passed=0,total=4,status='FAIL'),campaign_spec=asdict(campaign),
        parent_onnx_step_count=len(getattr(policy,'trace',[])),
        initial_state_receipts=getattr(policy,'initial_state_receipts',None),initial_state_sha256=getattr(policy,'initial_state_sha256',None),
        policy_reset_count=getattr(policy,'policy_reset_count',None),explicit_route_lane_ids=lane_ids,full_s_route_requested=False,
        sampler_configuration=sampler,opaque_bin_diagnostic=bins,registered_tasks_before=before_tasks,
        registered_tasks_after=after_tasks,provider_closed=closed,runtime=runtime,
        audit_scope=dict(cpu_only=True,state_bytes_hashed_per_step=STATE_BYTES,extra_audit_overhead_free=False,
            original_camera_class='bigbench.native_model_campaign.NativeWorldCamera',capture_delegate_calls=getattr(camera,'delegate_calls',0)),
        raw_sensor_rgb_dims=[964,604],model_rgb_dims=[512,256],actual_i420_shape=[2,6,128,256],actual_i420_dtype='uint8',
        partial_policy_audit_rows=audit_rows if report.get('status')!='DIAGNOSTIC_EXECUTED' else [],
        partial_capture_audit_rows=capture_rows if report.get('status')!='DIAGNOSTIC_EXECUTED' else [],**CLAIMS)
    return report


def _validate_states(receipts):
    if not isinstance(receipts,dict) or set(receipts)!=set(STATE_SCHEMA):raise ValueError('all named state receipts required')
    for name,(dtype,shape,nbytes) in STATE_SCHEMA.items():
        value=receipts[name]
        if (not isinstance(value,dict) or set(value)!={'name','dtype','shape','nbytes','sha256'}
            or not _exact({k:value[k] for k in ('name','dtype','shape','nbytes')},dict(name=name,dtype=dtype,shape=shape,nbytes=nbytes))
            or not _hash(value['sha256'])):raise ValueError('named state receipt schema/hash invalid: '+name)


def _pose(value):
    if (not isinstance(value,dict) or set(value)!={'t','x','y','heading','speed'}
        or any(type(x) not in (int,float) or not math.isfinite(x) for x in value.values())):
        raise ValueError('finite exact virtual capture pose required')
    return AgentState(**value)


def validate_trial(d,seed,scene,repeat):
    _configuration(seed,scene,repeat)
    expected=dict(status='DIAGNOSTIC_EXECUTED',model_sha256=MODEL_SHA,model_nbytes=MODEL_BYTES,model_spec_sha256=SPEC_SHA,
        scenario=scene,seed=seed,requested_steps=12,completed_steps=12,initial_fraction=.12,
        trial_evidence=EVIDENCE,official_model_execution=True,camera_capture_mode='native_MetaDrive_perceive_sequential_per_step',
        camera_convergence_attempts=0,camera_pixel_tolerance=0,camera_image_interpolation_or_replay=False,
        gpu_hdr_extraction=False,gpu_texture_extract_calls=0,gpu_queries_used=False,rgb_retention_observer=False,
        pssm_update_preserved=True,raw_action_and_recurrent_sha_captured_per_step=True,
        actual_onnx_image_feed_sha_captured_per_step=True,native_source_964x604_rgb_sha_captured_per_step=True,
        historical_original_gate=dict(passed=0,total=4,status='FAIL'),policy_reset_count=2,parent_onnx_step_count=12,provider_closed=True,
        full_s_route_requested=False,raw_sensor_rgb_dims=[964,604],model_rgb_dims=[512,256],
        actual_i420_shape=[2,6,128,256],actual_i420_dtype='uint8',**CLAIMS)
    if any(not _exact(d.get(k),v) for k,v in expected.items()) or d.get('error') is not None:
        raise ValueError('candidate identity, official model, capture or non-promotion controls invalid')
    if type(d.get('process_id')) is not int or d['process_id']<=0 or not _uuid(d.get('process_uuid')):
        raise ValueError('fresh native process identity required')
    request=d.get('candidate_trial',{})
    if (not _uuid(request.get('request_uuid')) or not _exact(request,dict(seed=seed,scenario=scene,repeat=repeat,request_uuid=request.get('request_uuid')))):
        raise ValueError('candidate request/case/repeat protocol invalid')
    if not _exact(d.get('campaign_spec'),asdict(CampaignSpec(scenario=scene,seed=seed,steps=12,speed_mps=8.,initial_fraction=.12))):
        raise ValueError('original kinematic/campaign protocol changed')
    initial,aggregate=_initial_receipts();_validate_states(d.get('initial_state_receipts'))
    if d['initial_state_receipts']!=initial or d.get('initial_state_sha256')!=aggregate:
        raise ValueError('initial recurrent state is not the exact parent reset zeros')
    tasks=d.get('registered_tasks_before');after_tasks=d.get('registered_tasks_after')
    if (not isinstance(tasks,list) or not isinstance(after_tasks,list) or any(not isinstance(x,str) for x in tasks+after_tasks)
        or sorted(tasks)!=sorted(after_tasks) or any(tasks.count(k)!=1 for k in ('igLoop','PSSM.update','update main chase camera'))):
        raise ValueError('original task registry not preserved')
    guard=dict(enabled=True,original_camera_states_empty=[True,True],camera_count=2,shader_replaced=False,
        input_priority=1000000,inputs=['use_pssm','PSSMShadowAtlas'],
        placeholder=dict(dimensions=[1,1],format='RGBA8',rgba=[255]*4,filters=[1,1]))
    sampler=dict(mode='feedback_both',filters_before=[6,6],filters_after=[1,1],metadrive_version='0.4.3',
        loaded_fragment_shader_sha256=SHADER_SHA256,shader_edited=False,manual_pcf_sampler2d_confirmed=True,
        renderer_semantics_experimental=True,shadow_guard=guard)
    if not _exact(d.get('sampler_configuration'),sampler):raise ValueError('sampler/guard candidate treatment invalid')
    bins=d.get('opaque_bin_diagnostic',{});before=bins.get('before')
    if (not isinstance(before,dict) or set(before)!={'index','name','type','sort','active'}
        or type(before.get('index')) is not int or before['index']<0 or before.get('name')!='opaque'
        or type(before.get('type')) is not int or before['type']!=2 or type(before.get('sort')) is not int or type(before.get('active')) is not bool
        or not _exact(bins,dict(CPU_RECEIPT,before=before,requested_type=1,configured=dict(before,type=1),after_capture=dict(before,type=1),restored=before))):
        raise ValueError('opaque bin policy receipt invalid')
    runtime=d.get('runtime',{})
    if (not isinstance(runtime,dict) or set(runtime)!={'ort_version','providers','optimization_level','injected_session'}
        or not isinstance(runtime.get('ort_version'),str) or not runtime['ort_version']
        or not _exact(runtime.get('providers'),['CPUExecutionProvider'])
        or type(runtime.get('optimization_level')) is not int or runtime['optimization_level']!=1 or runtime.get('injected_session') is not False):
        raise ValueError('actual parent ORT CPU/basic session settings invalid')
    if not _exact(d.get('audit_scope'),dict(cpu_only=True,state_bytes_hashed_per_step=STATE_BYTES,extra_audit_overhead_free=False,
        original_camera_class='bigbench.native_model_campaign.NativeWorldCamera',capture_delegate_calls=12)):
        raise ValueError('delegating CPU audit scope invalid')
    lane_ids=d.get('explicit_route_lane_ids')
    if not isinstance(lane_ids,list) or len(lane_ids)!=1 or not isinstance(lane_ids[0],str) or not lane_ids[0]:raise ValueError('original target lane ID missing')
    rows=d.get('frames');previous_pose=None;previous_clock=None
    if not isinstance(rows,list) or len(rows)!=12:raise ValueError('twelve complete native capture/inference rows required')
    for index,row in enumerate(rows):
        if type(row.get('step')) is not int or row['step']!=index+1:raise ValueError('nonsequential candidate step')
        for key in ('source_road_rgb_sha256','source_wide_rgb_sha256','road_frame_sha256','wide_frame_sha256','new_img_sha256','raw_action_sha256','state_after_step_sha256'):
            if not _hash(row.get(key)):raise ValueError('missing actual frame/feed/action/state SHA: '+key)
        _validate_states(row.get('named_state_receipts'))
        raw=row.get('raw_model_action')
        if not isinstance(raw,list) or len(raw)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) for x in raw):raise ValueError('four finite raw action values required')
        value=np.asarray(raw,dtype=np.float32)
        if not np.isfinite(value).all() or raw!=value.tolist() or sha256(value.tobytes(order='C')).hexdigest()!=row['raw_action_sha256']:
            raise ValueError('raw float32 action values do not match recorded bytes')
        if not _exact(row.get('raw_action_receipt'),dict(name='action',dtype='float32',shape=[4],nbytes=16,sha256=row['raw_action_sha256'])):
            raise ValueError('raw action dtype/shape/byte receipt invalid')
        action=ModelAction(float(value[0])/64.,float(value[1]))
        if (not _exact(row.get('parent_converted_action'),asdict(action))
            or row.get('desired_curvature_1pm')!=action.curvature_1pm or row.get('desired_acceleration_mps2')!=action.acceleration_mps2
            or not _duration(row.get('named_state_audit_wall_s'))):raise ValueError('parent action conversion or audit timing changed')
        capture=row.get('capture_audit',{});pose=_pose(capture.get('entry_pose'))
        if (pose.speed!=8. or (index==0 and pose.t!=0.) or previous_pose is not None and pose!=previous_pose
            or capture.get('delegate_calls')!=1 or not _duration(capture.get('capture_wall_s')) or 'error' in capture):
            raise ValueError('capture-entry virtual state or single delegation invalid')
        expected_pose=step_ideal(pose,action,.05,speed_override=8.)
        if (any(type(row.get(k)) not in (int,float) or not math.isfinite(row[k]) for k in ('time_s','world_x_m','world_y_m','heading_rad','speed_mps'))
            or [row[k] for k in ('time_s','world_x_m','world_y_m','heading_rad','speed_mps')]!=[expected_pose.t,expected_pose.x,expected_pose.y,expected_pose.heading,expected_pose.speed]
            or row.get('target_lane_id')!=lane_ids[0]):raise ValueError('post-action virtual pose/time differs from unchanged kinematics')
        previous_pose=expected_pose
        a,b=capture.get('before',{}),capture.get('after',{})
        if (any(type(c.get('frame_count')) is not int for c in (a,b))
            or b['frame_count']-a['frame_count']!=2 or type(capture.get('global_clock_frame_count_delta')) is not int or capture['global_clock_frame_count_delta']!=2
            or any(not _duration(c.get(k)) for c in (a,b) for k in ('frame_time_s','real_time_s','dt_s'))
            or any(not _duration(capture.get(k)) for k in ('global_clock_time_delta_s','real_time_delta_s'))
            or b['frame_time_s']-a['frame_time_s']!=capture['global_clock_time_delta_s'] or b['real_time_s']-a['real_time_s']!=capture['real_time_delta_s']
            or previous_clock is not None and (a['frame_count']!=previous_clock['frame_count'] or a['frame_time_s']!=previous_clock['frame_time_s'] or a['real_time_s']<previous_clock['real_time_s'])):
            raise ValueError('finite raw two-tick Panda clock evidence inconsistent')
        previous_clock=b


def compare_trials(a,b,seed,scene):
    for repeat,d in enumerate((a,b)):validate_trial(d,seed,scene,repeat)
    if a['candidate_trial']['request_uuid']==b['candidate_trial']['request_uuid']:raise ValueError('independent request nonces required')
    common=compare_fresh_trials(a,b)
    top=('campaign_spec','initial_state_receipts','initial_state_sha256','runtime','sampler_configuration','opaque_bin_diagnostic','registered_tasks_before','registered_tasks_after','explicit_route_lane_ids')
    if any(a[k]!=b[k] for k in top):raise ValueError('candidate repeat configuration/initial state differs')
    extra=[]
    for index,(x,y) in enumerate(zip(a['frames'],b['frames']),1):
        keys=('named_state_receipts','raw_action_receipt','parent_converted_action','target_lane_id')
        differing=[key for key in keys if x[key]!=y[key]]
        if x['capture_audit']['entry_pose']!=y['capture_audit']['entry_pose']:differing.append('capture_entry_pose')
        if any(x['capture_audit'][boundary]['frame_count']!=y['capture_audit'][boundary]['frame_count'] for boundary in ('before','after')):
            differing.append('capture_panda_frame_counts')
        if differing:extra.append(dict(step=index,differing_fields=differing))
    first=[x for x in (common['first_diverging_step'],extra[0]['step'] if extra else None) if x is not None]
    passed=common['exact_repeated_execution_gate_passed'] and not extra
    return dict(status='CANDIDATE_MDV3_REPEAT_MATCH' if passed else 'CANDIDATE_MDV3_REPEAT_MISMATCH',seed=seed,scenario=scene,
        candidate_exact_gate_passed=passed,first_diverging_step=min(first) if first else None,common_strict_comparison=common,
        extra_mismatches=extra,trial_evidence=EVIDENCE,process_uuids=[a['process_uuid'],b['process_uuid']],**CLAIMS)


def _folder(root,seed,scene):
    _configuration(seed,scene,0);return Path(root)/f'seed-{seed}'/scene


def _write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def launch_trial(*,model,spec,seed,scene,repeat,out,request_uuid=None,status_receipt=None):
    _configuration(seed,scene,repeat);request_uuid=uuid.uuid4().hex if request_uuid is None else request_uuid
    if not _uuid(request_uuid):raise ValueError('invalid launch nonce')
    out=Path(out);log=out.with_suffix('.log')
    if out.exists() or log.exists():raise ValueError('fresh candidate JSON/log required')
    out.parent.mkdir(parents=True,exist_ok=True)
    command=['xvfb-run','-a',sys.executable,'-m','scripts.native_mdv3_renderer_candidate','--mode','native',
        '--model',str(model),'--spec',str(spec),'--seed',str(seed),'--scene',scene,'--repeat',str(repeat),
        '--request-uuid',request_uuid,'--out',str(out)]
    with log.open('x') as stream:status=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT).returncode
    if status_receipt is not None:status_receipt.append(status)
    if status not in (0,5):return status
    d=json.loads(out.read_text());validate_trial(d,seed,scene,repeat)
    if d['candidate_trial']['request_uuid']!=request_uuid:raise ValueError('fresh candidate receipt has wrong nonce')
    if status==5:print('XVFB_CLEANUP_5_WITH_VALIDATED_FRESH_CANDIDATE_RECEIPT',out,flush=True)
    return 0


def run_case(*,root,model,spec,seed,scene):
    folder=_folder(root,seed,scene)
    if folder.exists():raise ValueError('candidate case directory must be fresh')
    folder.mkdir(parents=True);ledger=dict(seed=seed,scenario=scene,entries=[])
    for repeat in (0,1):
        nonce=uuid.uuid4().hex;entry=dict(repeat=repeat,filename=f'run_{repeat}.json',request_uuid=nonce,
            started_ns=time_ns(),finished_ns=None,native_exit_status=None,accepted_exit_status=None)
        ledger['entries'].append(entry);_write(folder/'execution_ledger.json',ledger);statuses=[]
        try:
            status=launch_trial(model=model,spec=spec,seed=seed,scene=scene,repeat=repeat,out=folder/entry['filename'],request_uuid=nonce,status_receipt=statuses)
            entry['accepted_exit_status']=status
            if status==0:
                d=json.loads((folder/entry['filename']).read_text());entry.update(process_id=d['process_id'],process_uuid=d['process_uuid'])
        except Exception as exc:entry['error']=f'{type(exc).__name__}: {exc}';raise
        finally:
            entry['finished_ns']=time_ns();entry['native_exit_status']=statuses[0] if statuses else None;_write(folder/'execution_ledger.json',ledger)
        if status!=0:return status
    _write(folder/'case_comparison.json',compare_case(root,seed,scene));return 0


def compare_case(root,seed,scene):
    folder=_folder(root,seed,scene);ledger=json.loads((folder/'execution_ledger.json').read_text())
    entries=ledger.get('entries')
    if ledger.get('seed')!=seed or ledger.get('scenario')!=scene or not isinstance(entries,list) or len(entries)!=2:
        raise ValueError('complete two-process candidate ledger required')
    trials=[];previous_end=0
    for repeat,entry in enumerate(entries):
        if (type(entry.get('repeat')) is not int or entry['repeat']!=repeat or entry.get('filename')!=f'run_{repeat}.json'
            or type(entry.get('native_exit_status')) is not int or entry['native_exit_status'] not in (0,5)
            or type(entry.get('accepted_exit_status')) is not int or entry['accepted_exit_status']!=0
            or type(entry.get('started_ns')) is not int or type(entry.get('finished_ns')) is not int
            or entry['started_ns']<=0 or entry['started_ns']<previous_end or entry['finished_ns']<entry['started_ns'] or 'error' in entry):
            raise ValueError('candidate ledger order/timing/status invalid')
        previous_end=entry['finished_ns'];d=json.loads((folder/entry['filename']).read_text());validate_trial(d,seed,scene,repeat)
        if (entry.get('request_uuid')!=d['candidate_trial']['request_uuid'] or entry.get('process_uuid')!=d['process_uuid']
            or entry.get('process_id')!=d['process_id']):raise ValueError('candidate ledger identity/nonce mismatch')
        trials.append(d)
    return dict(compare_trials(*trials,seed,scene),execution_ledger=ledger,independent_process_count=2)


def aggregate_cases(root):
    cases=[];ids=set();nonces=set();runtimes=[]
    for seed in SEEDS:
        for scene in SCENES:
            case=compare_case(root,seed,scene);folder=_folder(root,seed,scene)
            if json.loads((folder/'case_comparison.json').read_text())!=case:raise ValueError('stale or modified candidate case summary')
            for repeat in (0,1):
                d=json.loads((folder/f'run_{repeat}.json').read_text());uid=d['process_uuid'];nonce=d['candidate_trial']['request_uuid']
                if uid in ids or nonce in nonces:raise ValueError('native UUID/nonce reused across candidate cases')
                ids.add(uid);nonces.add(nonce);runtimes.append(d['runtime'])
            cases.append(case)
    if any(runtime!=runtimes[0] for runtime in runtimes):raise ValueError('mixed ORT runtime configurations across cohort')
    passed=sum(case['candidate_exact_gate_passed'] for case in cases)
    result=dict(status='CANDIDATE_MDV3_4_CASES_PASS' if passed==4 else 'CANDIDATE_MDV3_GATE_NOT_PASSED',
        candidate_gate_pass_count=passed,candidate_gate_total=4,candidate_all_four_cases_passed=passed==4,
        independent_process_count=len(ids),actual_onnx_steps=96,per_scene=cases,trial_evidence=EVIDENCE,
        historical_original_gate=dict(passed=0,total=4,status='FAIL'),**CLAIMS)
    stored=Path(root)/'aggregate_summary.json'
    if stored.exists() and json.loads(stored.read_text())!=result:raise ValueError('stale or modified candidate final summary')
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('native','run-case','case','aggregate'),required=True)
    p.add_argument('--model',type=Path);p.add_argument('--spec',type=Path)
    p.add_argument('--root',type=Path);p.add_argument('--out',type=Path)
    p.add_argument('--seed',type=int,choices=SEEDS);p.add_argument('--scene',choices=SCENES)
    p.add_argument('--repeat',type=int,choices=(0,1));p.add_argument('--request-uuid')
    a=p.parse_args(argv)
    if a.mode=='run-case':
        if None in (a.root,a.model,a.spec,a.seed,a.scene):p.error('run-case requires root/model/spec/seed/scene')
        return run_case(root=a.root,model=a.model,spec=a.spec,seed=a.seed,scene=a.scene)
    if a.out is None:p.error('--out required')
    if a.mode=='native':
        if None in (a.model,a.spec,a.seed,a.scene,a.repeat,a.request_uuid):p.error('native requires model/spec/seed/scene/repeat/nonce')
        if a.out.exists():raise ValueError('native output must be fresh')
        try:result=native_trial(model=a.model,spec=a.spec,seed=a.seed,scene=a.scene,repeat=a.repeat,request_uuid=a.request_uuid)
        except Exception as exc:result=dict(status='ERROR',error=f'{type(exc).__name__}: {exc}',**CLAIMS)
        _write(a.out,result)  # Full raw/partial JSON FIRST; strict wire validation only after reload.
        try:
            wire=json.loads(a.out.read_text());validate_trial(wire,a.seed,a.scene,a.repeat)
            if wire['candidate_trial']['request_uuid']!=a.request_uuid:raise ValueError('native nonce differs from launch request')
        except Exception as exc:print('CANDIDATE_NATIVE_INVALID',f'{type(exc).__name__}: {exc}',file=sys.stderr,flush=True);return 2
        print('CANDIDATE_NATIVE_RECEIPT_VALID',a.seed,a.scene,a.repeat,flush=True);return 0
    if a.root is None or a.mode=='case' and None in (a.seed,a.scene):p.error('comparison requires root; case also seed/scene')
    result=compare_case(a.root,a.seed,a.scene) if a.mode=='case' else aggregate_cases(a.root)
    _write(a.out,result);print(result['status'],flush=True);return 0


if __name__=='__main__':raise SystemExit(main())
