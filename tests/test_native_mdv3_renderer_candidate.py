"""Synthetic/unit candidate contracts; no official weights, ORT or Panda runs."""
import copy
from contextlib import contextmanager
from hashlib import sha256
import importlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

import numpy as np

from bigbench.kinematics import AgentState, ModelAction, step_ideal
from scripts.native_mdv3_repeat_trial import AuditedOfficialOnnx, recurrent_receipt
from test_native_shadow_feedback_matrix import fixture as feedback_fixture
from test_native_opaque_order_matrix import snapshot

SEEDS=(20261109,20261110)
SCENES=('s_curve_left_right','s_curve_right_left')
STATE_SCHEMA={'state_img_q':('uint8',[2,5,6,128,256],1966080),
              'state_desire_q':('float32',[132,1,8],4224),
              'state_feat_q':('float32',[128,1,16384],8388608)}
MODEL_SHA='35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199'
SPEC_SHA='689f4d80082070b08ff35920e37d7070e811dfb42a279909751f79e900c735e2'


def module(test):
    test.assertIsNotNone(importlib.util.find_spec('scripts.native_mdv3_renderer_candidate'),
                         'candidate module not implemented')
    return importlib.import_module('scripts.native_mdv3_renderer_candidate')


def states():return {k:np.zeros(shape,dtype=dtype) for k,(dtype,shape,_) in STATE_SCHEMA.items()}
INITIAL={k:dict(name=k,dtype=dtype,shape=shape,nbytes=nbytes,sha256=sha256(bytes(nbytes)).hexdigest())
         for k,(dtype,shape,nbytes) in STATE_SCHEMA.items()}
INITIAL_AGG=recurrent_receipt(states())


def fixture(seed=SEEDS[0],scene=SCENES[0],repeat=0):
    name=f'{seed}-{scene}-{repeat}';nonce=uuid.uuid5(uuid.NAMESPACE_URL,name).hex
    old=feedback_fixture(seed,scene,'both',False,repeat)
    bin=dict(before=snapshot(),configured=snapshot(1),after_capture=snapshot(1),restored=snapshot(),
        requested_type=1,setup_cpu_checks=True,before_provider=True,type_only_policy=True,
        type_change_may_apply_next_frame=True,extra_render_ticks=0,observer_enabled=False,
        gpu_queries_used=False,actual_draw_trace=False,setup_overhead_free=False)
    rows=[];pose=AgentState(0.,0.,0.,0.,8.)
    for i in range(12):
        after=step_ideal(pose,ModelAction(0.,0.),.05,speed_override=8.)
        before_clock=dict(frame_count=10+2*i,frame_time_s=i*.1,real_time_s=i*.2,dt_s=.05)
        after_clock=dict(frame_count=12+2*i,frame_time_s=(i+1)*.1,real_time_s=i*.2+.15,dt_s=.05)
        capture=dict(entry_pose=vars(pose),before=before_clock,after=after_clock,
            global_clock_frame_count_delta=2,global_clock_time_delta_s=after_clock['frame_time_s']-before_clock['frame_time_s'],
            real_time_delta_s=after_clock['real_time_s']-before_clock['real_time_s'],delegate_calls=1,capture_wall_s=.1)
        rows.append(dict(step=i+1,time_s=after.t,world_x_m=after.x,world_y_m=after.y,heading_rad=after.heading,speed_mps=after.speed,
            desired_curvature_1pm=0.,desired_acceleration_mps2=0.,target_lane_id='lane0',
            lateral_right_m=0.,inside_turn_offset_m=0.,lane_intrusion_m=0.,
            source_road_rgb_sha256='a'*64,source_wide_rgb_sha256='b'*64,road_frame_sha256='c'*64,
            wide_frame_sha256='d'*64,new_img_sha256='e'*64,raw_model_action=[0.,0.,0.,0.],
            raw_action_sha256=sha256(bytes(16)).hexdigest(),state_after_step_sha256=INITIAL_AGG,
            named_state_receipts=copy.deepcopy(INITIAL),
            raw_action_receipt=dict(name='action',dtype='float32',shape=[4],nbytes=16,sha256=sha256(bytes(16)).hexdigest()),
            parent_converted_action=dict(curvature_1pm=0.,acceleration_mps2=0.),named_state_audit_wall_s=.001,capture_audit=capture))
        pose=after
    tasks=['igLoop','PSSM.update','update main chase camera']
    return dict(status='DIAGNOSTIC_EXECUTED',error=None,model_label='big-onnx-'+MODEL_SHA[:12],
        model_sha256=MODEL_SHA,model_nbytes=768750198,model_spec_sha256=SPEC_SHA,
        scenario=scene,seed=seed,requested_steps=12,completed_steps=12,initial_fraction=.12,
        process_id=60000+repeat,process_uuid=uuid.uuid5(uuid.NAMESPACE_DNS,name).hex,
        candidate_trial=dict(request_uuid=nonce,repeat=repeat,seed=seed,scenario=scene),
        trial_evidence='CANDIDATE_BOTH_UNSORTED_OFFICIAL_MDV3',official_model_execution=True,
        camera_capture_mode='native_MetaDrive_perceive_sequential_per_step',camera_convergence_attempts=0,
        camera_pixel_tolerance=0,camera_image_interpolation_or_replay=False,gpu_hdr_extraction=False,
        gpu_texture_extract_calls=0,gpu_queries_used=False,rgb_retention_observer=False,pssm_update_preserved=True,
        raw_action_and_recurrent_sha_captured_per_step=True,actual_onnx_image_feed_sha_captured_per_step=True,
        native_source_964x604_rgb_sha_captured_per_step=True,
        original_mdv3_gate_passed=False,default_renderer_promoted=False,full_renderer_equivalence_proven=False,
        unique_renderer_microcause_proven=False,model_scoring_allowed=False,real_vehicle_testing=False,
        cd210_fallback=False,carrot_tuning_used=False,
        historical_original_gate=dict(passed=0,total=4,status='FAIL'),parent_onnx_step_count=12,
        campaign_spec=dict(scenario=scene,seed=seed,steps=12,speed_mps=8.,dt_s=.05,fixed_speed=True,initial_fraction=.12),
        initial_state_receipts=copy.deepcopy(INITIAL),initial_state_sha256=INITIAL_AGG,policy_reset_count=2,
        explicit_route_lane_ids=['lane0'],full_s_route_requested=False,
        sampler_configuration=old['shadow_sampler_diagnostic']['configuration'],opaque_bin_diagnostic=bin,
        registered_tasks_before=tasks,registered_tasks_after=tasks.copy(),provider_closed=True,
        runtime=dict(ort_version='UNIT_FIXTURE',providers=['CPUExecutionProvider'],optimization_level=1,injected_session=False),
        audit_scope=dict(cpu_only=True,state_bytes_hashed_per_step=10358912,extra_audit_overhead_free=False,
                         original_camera_class='bigbench.native_model_campaign.NativeWorldCamera',capture_delegate_calls=12),
        raw_sensor_rgb_dims=[964,604],model_rgb_dims=[512,256],actual_i420_shape=[2,6,128,256],actual_i420_dtype='uint8',
        frames=rows,partial_policy_audit_rows=[],partial_capture_audit_rows=[])


def build(root,m):
    for seed in SEEDS:
        for scene in SCENES:
            folder=root/f'seed-{seed}'/scene;folder.mkdir(parents=True)
            entries=[]
            for repeat in (0,1):
                d=fixture(seed,scene,repeat);filename=f'run_{repeat}.json'
                (folder/filename).write_text(json.dumps(d))
                entries.append(dict(repeat=repeat,filename=filename,request_uuid=d['candidate_trial']['request_uuid'],
                    process_uuid=d['process_uuid'],process_id=d['process_id'],started_ns=100+repeat*10,
                    finished_ns=105+repeat*10,native_exit_status=0,accepted_exit_status=0))
            (folder/'execution_ledger.json').write_text(json.dumps(dict(seed=seed,scenario=scene,entries=entries)))
            (folder/'case_comparison.json').write_text(json.dumps(m.compare_case(root,seed,scene)))


class CandidateAuditTests(unittest.TestCase):
    def test_noninjected_policy_setup_failure_with_zero_steps_never_claims_execution(self):
        m=module(self)
        constructed=SimpleNamespace(is_mock=False,_injected_session=False,trace=[],audit_rows=[],
            contract=SimpleNamespace(sha256=MODEL_SHA))
        with patch.object(m,'_new_policy',return_value=constructed), \
             patch.object(m,'_runtime',side_effect=RuntimeError('UNIT runtime metadata setup failure')), \
             patch.object(m,'_new_provider',side_effect=AssertionError('provider must not be created')):
            d=m.native_trial(model=Path('UNIT_NOT_WEIGHTS.onnx'),spec=Path('model_specs/md-v3.json'),
                seed=SEEDS[0],scene=SCENES[0],repeat=0,request_uuid='a'*32)
        self.assertEqual(d['status'],'FAILED_OR_INCOMPLETE')
        self.assertEqual(d['parent_onnx_step_count'],0)
        self.assertFalse(d['official_model_execution'])
        self.assertNotEqual(d['trial_evidence'],'CANDIDATE_BOTH_UNSORTED_OFFICIAL_MDV3')
        self.assertIn('FAILED_SETUP',d['trial_evidence'])

    def test_unit_only_native_lifecycle_keeps_visibility_closes_and_counts_parent_steps(self):
        m=module(self)
        from test_native_model_campaign import StraightTarget, FakePairCamera
        for fail in (False,True,'extra_audit'):
            interrupted=fail is True
            events=[];base=fixture();bin=copy.deepcopy(base['opaque_bin_diagnostic'])
            class UnitPolicy:
                is_mock=True;_injected_session=True;name='UNIT_FAKE_NOT_OFFICIAL'
                contract=SimpleNamespace(sha256=MODEL_SHA)
                def __init__(self):
                    self.policy_reset_count=1;self.audit_rows=[];self.trace=[]
                    self.initial_state_receipts=copy.deepcopy(INITIAL);self.initial_state_sha256=INITIAL_AGG
                def reset(self):
                    self.policy_reset_count+=1;self.audit_rows=[];self.trace=[];events.append('reset')
                def step(self,observation):
                    if interrupted and len(self.trace)==4:raise RuntimeError('UNIT partial model failure')
                    row=base['frames'][len(self.trace)]
                    self.audit_rows.append({k:copy.deepcopy(row[k]) for k in ('new_img_sha256','raw_model_action','raw_action_sha256',
                        'state_after_step_sha256','named_state_receipts','raw_action_receipt','parent_converted_action','named_state_audit_wall_s')})
                    self.trace.append('UNIT_STEP')
                    if fail=='extra_audit' and len(self.trace)==12:self.audit_rows.append({'UNIT_EXTRA_AUDIT':True})
                    return ModelAction(0.,0.)
            policy=UnitPolicy()
            class UnitCamera(FakePairCamera):
                last_source_rgb_sha256={'road':'a'*64,'wide':'b'*64}
                def capture(self,pose):events.append('capture');return super().capture(pose)
            def forbidden_hide(*args):raise AssertionError('original visual ego visibility must remain unchanged')
            engine=SimpleNamespace(taskMgr=SimpleNamespace(getTasks=lambda:[SimpleNamespace(getName=lambda name=name:name)
                for name in ('igLoop','PSSM.update','update main chase camera')]))
            provider=SimpleNamespace(env=SimpleNamespace(engine=engine,current_map=object(),
                vehicle=SimpleNamespace(origin=SimpleNamespace(hide=forbidden_hide))),close=lambda:events.append('close'))
            @contextmanager
            def bins(typ):
                self.assertEqual(typ,1);events.append('bin_enter')
                try:yield bin
                finally:events.append('bin_exit')
            clock_index=iter(range(24))
            def clock():
                i=next(clock_index);return dict(frame_count=10+2*i,frame_time_s=i*.1,real_time_s=i*.2,dt_s=.05)
            with patch.object(m,'_new_policy',return_value=policy),patch.object(m,'_runtime',return_value=base['runtime']), \
                 patch.object(m,'opaque_bin_policy',side_effect=bins), \
                 patch.object(m,'_new_provider',side_effect=lambda *args:events.append('provider') or provider), \
                 patch.object(m,'configure_sampler',side_effect=lambda *args:events.append('configure') or base['sampler_configuration']), \
                 patch.object(m,'select_native_curve_lanes',return_value=[StraightTarget()]), \
                 patch.object(m,'_new_camera',side_effect=lambda p:events.append('camera') or UnitCamera()), \
                 patch.object(m,'clock_sample',side_effect=clock):
                d=m.native_trial(model=Path('UNIT_NOT_WEIGHTS.onnx'),spec=Path('model_specs/md-v3.json'),
                    seed=SEEDS[0],scene=SCENES[0],repeat=0,request_uuid='a'*32)
            self.assertEqual(d.get('parent_onnx_step_count'),4 if interrupted else 12)
            self.assertEqual(d['completed_steps'],4 if interrupted else 12)
            self.assertEqual(d['policy_reset_count'],2)
            self.assertEqual(events.count('capture'),5 if interrupted else 12)
            self.assertLess(events.index('bin_enter'),events.index('provider'))
            self.assertLess(events.index('provider'),events.index('configure'))
            self.assertLess(events.index('configure'),events.index('camera'))
            self.assertLess(events.index('close'),events.index('bin_exit'))
            self.assertTrue(d['provider_closed']);self.assertFalse(d['official_model_execution'])
            self.assertTrue(d['trial_evidence'].startswith('UNIT_'))
            if interrupted:self.assertEqual(len(d['partial_capture_audit_rows']),5)
            if fail=='extra_audit':
                self.assertEqual(d['status'],'FAILED_OR_INCOMPLETE')
                self.assertEqual(d['partial_policy_audit_rows'][-1],{'UNIT_EXTRA_AUDIT':True})

    def test_task_membership_receipt_is_canonical_without_changing_tasks(self):
        m=module(self);names=['update main chase camera','igLoop','PSSM.update']
        tasks=[SimpleNamespace(getName=lambda name=name:name) for name in names]
        engine=SimpleNamespace(taskMgr=SimpleNamespace(getTasks=lambda:tasks))
        self.assertEqual(m._tasks(engine),['PSSM.update','igLoop','update main chase camera'])
        self.assertEqual([task.getName() for task in tasks],names)

    def test_named_states_preserve_uint8_shape_dtype_bytes_and_reject_wrong_schema(self):
        m=module(self);data=states()
        self.assertEqual(m.named_state_receipts(data),INITIAL)
        for mutation in ('name','shape','dtype','nonfinite'):
            bad=data.copy()
            if mutation=='name':del bad['state_desire_q']
            elif mutation=='shape':bad['state_desire_q']=np.zeros((1,132,8),np.float32)
            elif mutation=='dtype':bad['state_img_q']=np.zeros((2,5,6,128,256),np.float32)
            else:bad['state_desire_q']=np.full((132,1,8),np.nan,np.float32)
            with self.assertRaises(ValueError):m.named_state_receipts(bad)

    def test_policy_parent_step_once_no_perstep_reset_and_exact_converted_action(self):
        m=module(self);calls=[]
        def reset(policy):policy.state=states();policy.audit_rows=[];calls.append('reset')
        action=ModelAction(.125,-.25)
        def step(policy,observation):
            calls.append('step');policy.last_model_outputs=dict(action=np.array([8.,-.25,2.,3.],np.float32))
            policy.audit_rows.append(dict(raw_model_action=[8.,-.25,2.,3.],raw_action_sha256=sha256(policy.last_model_outputs['action'].tobytes()).hexdigest(),state_after_step_sha256=recurrent_receipt(policy.state)))
            return action
        with patch.object(AuditedOfficialOnnx,'reset',new=reset),patch.object(AuditedOfficialOnnx,'step',new=step):
            policy=m.CandidateAuditedOnnx.__new__(m.CandidateAuditedOnnx);policy.reset()
            self.assertIs(policy.step(object()),action);self.assertIs(policy.step(object()),action)
        self.assertEqual(calls,['reset','step','step'])
        self.assertEqual(policy.audit_rows[0]['raw_action_receipt']['dtype'],'float32')
        self.assertEqual(policy.audit_rows[0]['named_state_receipts']['state_img_q']['dtype'],'uint8')
        self.assertEqual(policy.audit_rows[0]['parent_converted_action'],dict(curvature_1pm=.125,acceleration_mps2=-.25))

    def test_capture_calls_original_once_forwards_source_hashes_and_pose_unchanged(self):
        m=module(self);seen=[];pair=object();pose=AgentState(0.,1.,2.,.1,8.)
        delegate=SimpleNamespace(last_source_rgb_sha256={'road':'a'*64,'wide':'b'*64},capture=lambda p:seen.append(p) or pair)
        clocks=iter([dict(frame_count=10,frame_time_s=1.,real_time_s=2.,dt_s=.05),dict(frame_count=12,frame_time_s=1.1,real_time_s=2.2,dt_s=.05)])
        with patch.object(m,'clock_sample',side_effect=lambda:next(clocks)):
            camera=m.CandidateCaptureAudit(delegate);self.assertIs(camera.capture(pose),pair)
        self.assertEqual(seen,[pose]);self.assertEqual(camera.last_source_rgb_sha256,delegate.last_source_rgb_sha256)
        self.assertEqual(camera.rows[0]['entry_pose'],vars(pose))
        self.assertEqual(camera.rows[0]['global_clock_frame_count_delta'],2)

    def test_wrong_actual_model_or_changed_spec_fail_before_policy_ort_construction(self):
        m=module(self)
        with TemporaryDirectory() as tmp:
            model=Path(tmp)/'unit-not-weights.onnx';model.write_bytes(b'UNIT_NOT_OFFICIAL_WEIGHTS')
            spec=Path('model_specs/md-v3.json')
            with patch.object(m,'CandidateAuditedOnnx',side_effect=AssertionError('ORT must not construct')):
                with self.assertRaises(ValueError):m._new_policy(model,spec)
                changed=Path(tmp)/'changed.json';d=json.loads(spec.read_text());d['input_shapes']['state_img_q']=[1];changed.write_text(json.dumps(d))
                with self.assertRaises(ValueError):m._new_policy(model,changed)


class CandidateReceiptTests(unittest.TestCase):
    def test_all_four_cases_recompute_eight_processes_without_original_gate_promotion(self):
        m=module(self)
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root,m);d=m.aggregate_cases(root)
            self.assertEqual(d['independent_process_count'],8)
            self.assertEqual(d['actual_onnx_steps'],96)
            self.assertTrue(d['candidate_all_four_cases_passed'])
            self.assertFalse(d['original_mdv3_gate_passed']);self.assertFalse(d['default_renderer_promoted'])

    def test_malformed_controls_fail_and_each_valid_one_field_difference_fails_exact_gate(self):
        m=module(self);base=fixture()
        mutations=('model','spec','missing_state','state_dtype','action_shape','action_hash','action_noncanonical','entry_pose','virtual_time',
                   'clock','clock_finite','ticks','tasks','sampler','guard','bin','gpu','observer','label','nonce','claim')
        for mutation in mutations:
            d=copy.deepcopy(base);row=d['frames'][2]
            if mutation=='model':d['model_sha256']='a'*64
            elif mutation=='spec':d['model_spec_sha256']='a'*64
            elif mutation=='missing_state':del row['named_state_receipts']['state_feat_q']
            elif mutation=='state_dtype':row['named_state_receipts']['state_img_q']['dtype']='float32'
            elif mutation=='action_shape':row['raw_action_receipt']['shape']=[2]
            elif mutation=='action_hash':row['raw_action_sha256']='a'*64
            elif mutation=='action_noncanonical':row['raw_model_action'][3]=1e-50
            elif mutation=='entry_pose':row['capture_audit']['entry_pose']['x']+=1
            elif mutation=='virtual_time':row['time_s']+=.001
            elif mutation=='clock':row['capture_audit']['before']['frame_count']+=1
            elif mutation=='clock_finite':row['capture_audit']['after']['dt_s']=float('nan')
            elif mutation=='ticks':row['capture_audit']['global_clock_frame_count_delta']=1
            elif mutation=='tasks':d['registered_tasks_after'].remove('PSSM.update')
            elif mutation=='sampler':d['sampler_configuration']['filters_after']=[6,6]
            elif mutation=='guard':d['sampler_configuration']['shadow_guard']['enabled']=False
            elif mutation=='bin':d['opaque_bin_diagnostic']['after_capture']['type']=2
            elif mutation=='gpu':d['gpu_texture_extract_calls']=1
            elif mutation=='observer':d['rgb_retention_observer']=True
            elif mutation=='label':d['trial_evidence']='UNMODIFIED_METADRIVE_NEW_FRAME_OFFICIAL_ONNX_DIAGNOSTIC'
            elif mutation=='nonce':d['candidate_trial']['request_uuid']='bad'
            else:d['original_mdv3_gate_passed']=True
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):m.validate_trial(d,SEEDS[0],SCENES[0],0)
        for field in ('source_road_rgb_sha256','new_img_sha256','state_after_step_sha256','named_state_receipts'):
            a,b=fixture(repeat=0),fixture(repeat=1)
            if field=='named_state_receipts':b['frames'][6][field]['state_feat_q']['sha256']='f'*64
            else:b['frames'][6][field]='f'*64
            result=m.compare_trials(a,b,SEEDS[0],SCENES[0])
            self.assertFalse(result['candidate_exact_gate_passed']);self.assertEqual(result['first_diverging_step'],7)
        a,b=fixture(repeat=0),fixture(repeat=1);row=b['frames'][6];row['raw_model_action'][3]=1.
        row['raw_action_sha256']=sha256(np.asarray(row['raw_model_action'],np.float32).tobytes()).hexdigest()
        row['raw_action_receipt']['sha256']=row['raw_action_sha256']
        self.assertFalse(m.compare_trials(a,b,SEEDS[0],SCENES[0])['candidate_exact_gate_passed'])

    def test_global_uuid_and_nonce_reuse_are_rejected_after_case_regeneration(self):
        m=module(self)
        for key in ('process_uuid','request_uuid'):
            with TemporaryDirectory() as tmp:
                root=Path(tmp);build(root,m);folder=root/f'seed-{SEEDS[1]}'/SCENES[1]
                p=folder/'run_0.json';d=json.loads(p.read_text());other=fixture(SEEDS[0],SCENES[0],0)
                if key=='process_uuid':d[key]=other[key]
                else:d['candidate_trial'][key]=other['candidate_trial'][key]
                p.write_text(json.dumps(d));ledgerpath=folder/'execution_ledger.json';ledger=json.loads(ledgerpath.read_text())
                ledger['entries'][0][key]=d[key] if key=='process_uuid' else d['candidate_trial'][key]
                ledgerpath.write_text(json.dumps(ledger));(folder/'case_comparison.json').write_text(json.dumps(m.compare_case(root,SEEDS[1],SCENES[1])))
                with self.assertRaises(ValueError):m.aggregate_cases(root)

    def test_stale_case_final_summary_and_reused_processes_rejected(self):
        m=module(self)
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root,m);summary=m.aggregate_cases(root)
            p=root/'aggregate_summary.json';summary['candidate_all_four_cases_passed']=False;p.write_text(json.dumps(summary))
            with self.assertRaises(ValueError):m.aggregate_cases(root)
            p.unlink();folder=root/f'seed-{SEEDS[0]}'/SCENES[0];p=folder/'case_comparison.json';d=json.loads(p.read_text());d['candidate_exact_gate_passed']=False;p.write_text(json.dumps(d))
            with self.assertRaises(ValueError):m.aggregate_cases(root)
            q=folder/'run_1.json';d=json.loads(q.read_text());d['process_id']=60000;q.write_text(json.dumps(d))
            with self.assertRaises(ValueError):m.compare_case(root,SEEDS[0],SCENES[0])

    def test_raw_json_keeps_partial_rows_and_tuple_pose_before_wire_validation(self):
        m=module(self)
        for invalid in (False,True):
            d=fixture();d['frames'][0]['capture_audit']['entry_pose']=dict(d['frames'][0]['capture_audit']['entry_pose'])
            d['initial_state_receipts']['state_img_q']['shape']=tuple(d['initial_state_receipts']['state_img_q']['shape'])
            if invalid:d['frames'].pop();d['status']='FAILED_OR_INCOMPLETE';d['partial_capture_audit_rows']=[{'error':'unit failure'}]
            with TemporaryDirectory() as tmp:
                out=Path(tmp)/'raw.json'
                with patch.object(m,'native_trial',return_value=d):
                    status=m.main(['--mode','native','--model','UNIT_NOT_WEIGHTS.onnx','--spec','model_specs/md-v3.json',
                        '--seed',str(SEEDS[0]),'--scene',SCENES[0],'--repeat','0','--request-uuid',d['candidate_trial']['request_uuid'],'--out',str(out)])
                self.assertEqual(status,2 if invalid else 0)
                self.assertEqual(json.loads(out.read_text())['frames'],json.loads(json.dumps(d['frames'])))


class CandidateLauncherTests(unittest.TestCase):
    def test_case_launcher_preserves_success_failure_and_invalid_receipt_ledgers(self):
        m=module(self)
        for outcome in ('success','failure','invalid'):
            with TemporaryDirectory() as tmp:
                root=Path(tmp)/'matrix';calls=[]
                def child(command,**kwargs):
                    calls.append(command);arg=lambda key:command[command.index(key)+1]
                    d=fixture(int(arg('--seed')),arg('--scene'),int(arg('--repeat')))
                    d['candidate_trial']['request_uuid']=arg('--request-uuid')
                    if outcome=='invalid':d['frames'].pop()
                    Path(arg('--out')).write_text(json.dumps(d))
                    return SimpleNamespace(returncode=7 if outcome=='failure' else 5 if len(calls)==1 else 0)
                with patch.object(m.subprocess,'run',side_effect=child):
                    if outcome=='invalid':
                        with self.assertRaises(ValueError):m.run_case(root=root,model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),seed=SEEDS[0],scene=SCENES[0])
                    else:self.assertEqual(m.run_case(root=root,model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),seed=SEEDS[0],scene=SCENES[0]),7 if outcome=='failure' else 0)
                folder=root/f'seed-{SEEDS[0]}'/SCENES[0];ledger=json.loads((folder/'execution_ledger.json').read_text())
                self.assertEqual(len(calls),2 if outcome=='success' else 1)
                entry=ledger['entries'][0];self.assertEqual(entry['native_exit_status'],7 if outcome=='failure' else 5)
                self.assertEqual(entry['accepted_exit_status'],0 if outcome=='success' else 7 if outcome=='failure' else None)
                self.assertEqual('error' in entry,outcome=='invalid')
                self.assertTrue((folder/entry['filename']).exists());self.assertEqual((folder/'case_comparison.json').exists(),outcome=='success')
                with self.assertRaises(ValueError):m.run_case(root=root,model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),seed=SEEDS[0],scene=SCENES[0])

    def invoke(self,status,*,write=True,invalid=False,nonce=False,stale=False):
        m=module(self)
        with TemporaryDirectory() as tmp:
            out=Path(tmp)/'raw.json'
            if stale:out.write_text('{}')
            def child(command,**kwargs):
                self.assertEqual(command[:2],['xvfb-run','-a'])
                if write:
                    d=fixture();d['candidate_trial']['request_uuid']='f'*32 if nonce else command[command.index('--request-uuid')+1]
                    if invalid:d['frames'].pop()
                    out.write_text(json.dumps(d))
                return SimpleNamespace(returncode=status)
            with patch.object(m.subprocess,'run',side_effect=child):
                return m.launch_trial(model=Path('UNIT_NOT_WEIGHTS.onnx'),spec=Path('model_specs/md-v3.json'),seed=SEEDS[0],scene=SCENES[0],repeat=0,out=out)
    def test_fresh_complete_nonce_proof_required_for_zero_and_cleanup_five(self):
        for status in (0,5):
            self.assertEqual(self.invoke(status),0)
            with self.assertRaises(ValueError):self.invoke(status,invalid=True)
            with self.assertRaises(ValueError):self.invoke(status,nonce=True)
            with self.assertRaises(FileNotFoundError):self.invoke(status,write=False)
        with self.assertRaises(ValueError):self.invoke(5,stale=True)
    def test_other_native_statuses_preserved_even_with_valid_receipt(self):
        for status in (1,2,7,-9):self.assertEqual(self.invoke(status),status)
