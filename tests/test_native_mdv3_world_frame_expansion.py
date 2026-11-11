"""Synthetic complete-only expansion/accounting tests; no official inference or graphics."""
import copy
from contextlib import contextmanager
from dataclasses import asdict
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

from bigbench.kinematics import AgentState,ModelAction,step_ideal
from test_native_mdv3_candidate_expansion import fixture as legacy_fixture,GROUPS,SEEDS


def module(test):
    test.assertIsNotNone(importlib.util.find_spec('scripts.native_mdv3_world_frame_expansion'),
                         'corrected expansion implementation missing')
    return importlib.import_module('scripts.native_mdv3_world_frame_expansion')


def fixture(group='camera028',seed=SEEDS[0],scene=None,repeat=0,failed=None,committed=4):
    m=importlib.import_module('scripts.native_mdv3_world_frame_expansion')
    d=legacy_fixture(group,seed,scene,repeat,partial=committed if failed else None)
    request=d.pop('expansion_trial');request['request_uuid']=uuid.uuid5(uuid.NAMESPACE_URL,'world-expanded-'+str(request)).hex
    d.update(protocol=m.PROTOCOL,trial_evidence=m.EVIDENCE,world_frame_expansion_trial=request,
        source_bindings=dict(m.SOURCE_BINDINGS),action_basis=m.frame.basis_receipt(),adapter_reset_calls=1)
    d['episode_provenance']['public_episode_started']=True
    if failed=='policy':
        d['inference_audit_rows'].pop();d['parent_onnx_step_count']-=1
        d['error']='ModelContractError: unit output validation AFTER possible session.run'
        d['episode_provenance']['returned_error']=d['error']
    d['bridge_receipts']=[];d['committed_parent_trace']=[]
    for index,audit in enumerate(d['inference_audit_rows']):
        d['committed_parent_trace'].append(dict(step_index=index,elapsed_ms=1.,raw_lateral_accel_mps2=audit['raw_model_action'][0],
            raw_longitudinal_accel_mps2=audit['raw_model_action'][1],curvature_1pm=audit['parent_converted_action']['curvature_1pm'],image_checksum=123))
        bridge=dict(step=index+1,**m.frame.basis_receipt(),parent_model_action=copy.deepcopy(audit['parent_converted_action']),
            applied_world_action=dict(curvature_1pm=-audit['parent_converted_action']['curvature_1pm'],
                acceleration_mps2=audit['parent_converted_action']['acceleration_mps2']),bridge_audit_wall_s=.001)
        d['bridge_receipts'].append(bridge)
        if index<len(d['frames']):d['frames'][index]['world_frame_bridge']=copy.deepcopy(bridge)
    d['execution_accounting']=m.attempt_accounting(d)
    return d


def build(root,m,failed=None):
    for group,config in m.GROUPS.items():
        for seed in m.SEEDS:
            for scene in config['scenes']:
                folder=root/group/f'seed-{seed}'/scene;folder.mkdir(parents=True);entries=[]
                failure=failed if (group,seed,scene)==('longer160',SEEDS[0],'s_curve_left_right') else None
                for repeat in ((0,) if failure else (0,1)):
                    d=fixture(group,seed,scene,repeat,failed=failure);filename=f'run_{repeat}.json'
                    (folder/filename).write_text(json.dumps(d));entries.append(dict(repeat=repeat,filename=filename,
                        request_uuid=d['world_frame_expansion_trial']['request_uuid'],process_uuid=d['process_uuid'],process_id=d['process_id'],
                        started_ns=10+repeat*10,finished_ns=15+repeat*10,native_exit_status=2 if failure else 0,accepted_exit_status=2 if failure else 0))
                ledger=dict(group=group,seed=seed,scenario=scene,planned_repeats=[0,1],unattempted_repeats=[1] if failure else [],entries=entries)
                (folder/'execution_ledger.json').write_text(json.dumps(ledger))
                if not failure:(folder/'case_comparison.json').write_text(json.dumps(m.compare_case(root,group,seed,scene)))


class CorrectedExpansionContracts(unittest.TestCase):
    def test_impossible_surplus_audits_bridges_or_captures_make_total_unknown(self):
        m=module(self)
        for extra in ('inference_audit_rows','bridge_receipts','capture_audit_rows','frames'):
            d=fixture();d[extra].append(copy.deepcopy(d[extra][-1]))
            if extra=='capture_audit_rows':
                row=d['frames'][-1];cap=d[extra][-1]
                cap['entry_pose']=dict(zip(('t','x','y','heading','speed'),[row[k] for k in ('time_s','world_x_m','world_y_m','heading_rad','speed_mps')]))
                cap['before']=copy.deepcopy(d[extra][-2]['after']);cap['after']=dict(cap['before'],frame_count=cap['before']['frame_count']+2,
                    frame_time_s=cap['before']['frame_time_s']+.1,real_time_s=cap['before']['real_time_s']+.2)
                cap['global_clock_time_delta_s']=cap['after']['frame_time_s']-cap['before']['frame_time_s']
                cap['real_time_delta_s']=cap['after']['real_time_s']-cap['before']['real_time_s']
            if extra=='frames':d[extra][-1]['step']=13;d['completed_steps']=13
            original=copy.deepcopy(d[extra])
            accounting=m.attempt_accounting(d)
            with self.subTest(extra=extra):
                self.assertEqual(accounting['known_committed_parent_steps'],12)
                self.assertIsNone(accounting['total_executed_ort_calls'])
                self.assertTrue(accounting['errors'])
                self.assertEqual(d[extra],original)
        # Inner trace commits before either audited wrapper/bridge: no surplus here.
        d=fixture();d['inference_audit_rows'].pop();d['bridge_receipts'].pop()
        d['frames'].pop();d['completed_steps']=11;d['status']='FAILED_OR_INCOMPLETE'
        d['error']='RuntimeError: audit failure after parent trace commit'
        d['episode_provenance'].update(returned_status=d['status'],returned_error=d['error'])
        accounting=m.attempt_accounting(d)
        self.assertEqual(accounting['known_committed_parent_steps'],12)
        self.assertEqual(accounting['total_executed_ort_calls'],12);self.assertFalse(accounting['errors'])

    def test_failed_aggregate_with_surplus_audit_cannot_report_exact_total(self):
        m=module(self)
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root,m);path=root/'camera028'/f'seed-{SEEDS[0]}'/'s_curve_left_right'/'run_0.json'
            d=json.loads(path.read_text());d['inference_audit_rows'].append(copy.deepcopy(d['inference_audit_rows'][-1]))
            d['execution_accounting']=m.attempt_accounting(d);path.write_text(json.dumps(d))
            result=m.aggregate_cases(root)
            self.assertFalse(result['aggregation_succeeded']);self.assertEqual(result['unknown_case_count'],1)
            self.assertEqual(result['known_committed_parent_steps_lower_bound'],1472)
            self.assertIsNone(result['total_executed_ort_calls'])

    def test_late159_valid_state_difference_fails_but_measured_times_are_not_compared(self):
        m=module(self);a,b=fixture('longer160',repeat=0),fixture('longer160',repeat=1)
        for value in (b['frames'][158]['named_state_receipts'],b['inference_audit_rows'][158]['named_state_receipts']):
            value['state_feat_q']['sha256']='f'*64
        result=m.compare_trials(a,b,'longer160',SEEDS[0],a['scenario'])
        self.assertFalse(result['world_frame_expansion_gate_passed']);self.assertEqual(result['first_diverging_step'],159)
        b=fixture('longer160',repeat=1)
        b['capture_audit_rows'][158]['capture_wall_s']+=1.;b['frames'][158]['capture_audit']=copy.deepcopy(b['capture_audit_rows'][158])
        b['inference_audit_rows'][158]['named_state_audit_wall_s']+=1.;b['frames'][158]['named_state_audit_wall_s']=b['inference_audit_rows'][158]['named_state_audit_wall_s']
        b['bridge_receipts'][158]['bridge_audit_wall_s']+=1.;b['frames'][158]['world_frame_bridge']=copy.deepcopy(b['bridge_receipts'][158])
        b['committed_parent_trace'][158]['elapsed_ms']+=10.
        self.assertTrue(m.compare_trials(a,b,'longer160',SEEDS[0],a['scenario'])['world_frame_expansion_gate_passed'])

    def test_launcher_zero_five_full_wire_nonce_and_other_statuses(self):
        m=module(self)
        for status,defect in ((0,None),(5,None),(0,'nonce'),(5,'partial'),(2,None),(7,'missing')):
            with TemporaryDirectory() as tmp:
                out=Path(tmp)/'raw.json';statuses=[]
                def child(command,**kwargs):
                    if defect!='missing':
                        d=fixture();d['world_frame_expansion_trial']['request_uuid']='f'*32 if defect=='nonce' else command[command.index('--request-uuid')+1]
                        if defect=='partial':d['frames'].pop()
                        out.write_text(json.dumps(d))
                    return SimpleNamespace(returncode=status)
                args=dict(model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),group='camera028',seed=SEEDS[0],scene='s_curve_left_right',repeat=0,out=out,status_receipt=statuses)
                with patch.object(m.subprocess,'run',side_effect=child):
                    if defect in ('nonce','partial'):
                        with self.assertRaises(ValueError):m.launch_trial(**args)
                    else:self.assertEqual(m.launch_trial(**args),0 if status in (0,5) else status)
                self.assertEqual(statuses,[status])
                with self.assertRaises(ValueError):m.launch_trial(**args)

    def test_empty_failed_cohort_writes_summary_and_never_claims_zero_total(self):
        m=module(self)
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/'missing';out=root/'aggregate_summary.json'
            self.assertEqual(m.main(['--mode','aggregate','--root',str(root),'--out',str(out)]),2)
            summary=json.loads(out.read_text());self.assertEqual(summary['unknown_case_count'],12)
            self.assertEqual(summary['known_committed_parent_steps_lower_bound'],0)
            self.assertIsNone(summary['total_executed_ort_calls']);self.assertFalse(summary['world_frame_expansion_all_cases_passed'])

    def test_accounting_setup_capture_failure_close_and_first_uncommitted_attempt(self):
        m=module(self);d=fixture('longer160',failed='policy',committed=0)
        self.assertEqual(m.attempt_accounting(d)['known_committed_parent_steps'],0)
        self.assertIsNone(m.attempt_accounting(d)['total_executed_ort_calls'])
        setup=copy.deepcopy(d);setup['capture_audit_rows']=[]
        setup['episode_provenance'].update(public_episode_started=False,public_episode_returned=False,returned_status=None,returned_error=None,
            outer_lifecycle_error='RuntimeError: setup before public loop')
        self.assertEqual(m.attempt_accounting(setup)['total_executed_ort_calls'],0)
        camera=fixture('longer160',failed='policy');camera['error']='RuntimeError: capture before policy'
        camera['episode_provenance']['returned_error']=camera['error'];camera['capture_audit_rows'][-1]['error']=camera['error']
        for key in m.legacy.HASH_KEYS:camera['capture_audit_rows'][-1].pop(key)
        self.assertEqual(m.attempt_accounting(camera)['total_executed_ort_calls'],4)
        close=fixture();close['status']='FAILED_OR_INCOMPLETE';close['error']='RuntimeError: close';close['provider_closed']=False
        close['episode_provenance']['outer_lifecycle_error']=close['error']
        self.assertEqual(m.attempt_accounting(close)['total_executed_ort_calls'],12)
        with self.assertRaises(ValueError):m.validate_trial(close,'camera028',SEEDS[0],close['scenario'],0)

    def test_malformed_failed_evidence_always_returns_unknown_and_summary(self):
        m=module(self);d=fixture('longer160',failed='policy');d['capture_audit_rows'][-1]=None
        try:account=m.attempt_accounting(d)
        except Exception as exc:self.fail(f'malformed failed accounting must return unknown/error: {exc}')
        self.assertIsNone(account['total_executed_ort_calls']);self.assertTrue(account['errors'])
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root,m,failed='policy')
            path=root/'longer160'/f'seed-{SEEDS[0]}'/'s_curve_left_right'/'run_0.json';path.write_text('[]')
            try:summary=m.aggregate_cases(root)
            except Exception as exc:self.fail(f'malformed raw must preserve a failed aggregate summary: {exc}')
            self.assertFalse(summary['aggregation_succeeded']);self.assertIsNone(summary['total_executed_ort_calls'])

    def test_identity_reuse_cannot_leave_case_pass_count_at12(self):
        m=module(self)
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root,m);group='native_ramps';seed=SEEDS[1];scene='out_ramp'
            folder=root/group/f'seed-{seed}'/scene;path=folder/'run_0.json';d=json.loads(path.read_text());d['process_uuid']=fixture()['process_uuid']
            path.write_text(json.dumps(d));path=folder/'execution_ledger.json';ledger=json.loads(path.read_text())
            ledger['entries'][0]['process_uuid']=d['process_uuid'];path.write_text(json.dumps(ledger))
            (folder/'case_comparison.json').write_text(json.dumps(m.compare_case(root,group,seed,scene)))
            summary=m.aggregate_cases(root);self.assertFalse(summary['aggregation_succeeded'])
            self.assertLess(summary['world_frame_expansion_gate_pass_count'],12)

    def test_stale_final_failure_snapshot_is_preserved_without_recursive_growth(self):
        m=module(self)
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root,m);old=m.aggregate_cases(root);old['total_executed_ort_calls']=1473
            path=root/'aggregate_summary.json';path.write_text(json.dumps(old));first=m.aggregate_cases(root)
            self.assertFalse(first['aggregation_succeeded']);self.assertEqual(first['stored_summary_before_revalidation'],old)
            path.write_text(json.dumps(first));second=m.aggregate_cases(root)
            self.assertEqual(first,second)

    def test_nonzero_parent_frd_and_applied_world_validate_through_step160(self):
        m=module(self);d=fixture('longer160');pose=AgentState(0.,0.,0.,0.,8.)
        import struct
        digest=sha256(struct.pack('<4f',8.,0.,2.,3.)).hexdigest()
        for index,row in enumerate(d['frames']):
            audit=d['inference_audit_rows'][index];audit.update(raw_model_action=[8.,0.,2.,3.],raw_action_sha256=digest,
                parent_converted_action=dict(curvature_1pm=.125,acceleration_mps2=0.))
            audit['raw_action_receipt']['sha256']=digest;row.update(copy.deepcopy(audit))
            trace=d['committed_parent_trace'][index];trace.update(raw_lateral_accel_mps2=8.,curvature_1pm=.125)
            cap=d['capture_audit_rows'][index];cap['entry_pose']=asdict(pose);row['capture_audit']=copy.deepcopy(cap)
            bridge=d['bridge_receipts'][index];bridge.update(parent_model_action=copy.deepcopy(audit['parent_converted_action']),
                applied_world_action=dict(curvature_1pm=-.125,acceleration_mps2=0.));row['world_frame_bridge']=copy.deepcopy(bridge)
            pose=step_ideal(pose,ModelAction(-.125,0.),.05,speed_override=8.)
            row.update(time_s=pose.t,world_x_m=pose.x,world_y_m=pose.y,heading_rad=pose.heading,speed_mps=pose.speed,desired_curvature_1pm=-.125)
        d['execution_accounting']=m.attempt_accounting(d);m.validate_trial(d,'longer160',SEEDS[0],d['scenario'],0)
        d['frames'][159]['desired_curvature_1pm']=.125
        with self.assertRaises(ValueError):m.validate_trial(d,'longer160',SEEDS[0],d['scenario'],0)

    def test_shared_loop_actual_groups_route_and_uncommitted_unit_session_failure(self):
        m=module(self)
        from bigbench.model_world_frame import WorldFramePolicyAdapter,SOURCE_ACTION_FRAME
        from bigbench.onnx_policy import ModelTiming
        from test_native_route import Straight
        from test_native_model_campaign import FakePairCamera
        from test_native_mdv3_renderer_candidate import fixture as base_fixture
        for group,fail in [('camera028',False),('native_ramps',False),('longer160',False),('longer160',True)]:
            events=[];ticks=[0];session_calls=[0];base=base_fixture();template=base['frames'][0]
            class Inner:
                is_mock=True;_injected_session=True;name='UNIT_NOT_OFFICIAL'
                contract=SimpleNamespace(sha256=m.base.MODEL_SHA)
                def __init__(self):
                    self.trace=[];self.audit_rows=[];self.policy_reset_count=1
                    self.initial_state_receipts=base['initial_state_receipts'];self.initial_state_sha256=base['initial_state_sha256']
                def reset(self):self.policy_reset_count+=1;self.trace=[];self.audit_rows=[]
                def step(self,observation):
                    session_calls[0]+=1
                    if fail and len(self.trace)==4:raise RuntimeError('UNIT possible uncommitted session.run')
                    self.trace.append(ModelTiming(len(self.trace),1.,0.,0.,0.,123))
                    self.audit_rows.append({key:copy.deepcopy(template[key]) for key in m.legacy.POLICY_KEYS})
                    return ModelAction(0.,0.)
            class Camera(FakePairCamera):
                last_source_rgb_sha256={'road':'a'*64,'wide':'b'*64}
                def capture(self,pose):ticks[0]+=2;events.append('capture');return super().capture(pose)
            first=Straight(0,3 if group=='native_ramps' else 20,('A','B',0))
            connector=Straight(20,40,('B','C',0));last=Straight(40,200,('C','D',0))
            for lane,direction in ((first,1.),(connector,1.),(last,-1.)):lane.radius=55.;lane.direction=direction
            blocks=[SimpleNamespace(ID='I',get_config=lambda:{})]
            blocks+=([SimpleNamespace(ID='r',get_config=lambda:{})] if group=='native_ramps' else
                     [SimpleNamespace(ID='C',get_config=lambda d=d:{'dir':d}) for d in (0,1)])
            world=SimpleNamespace(blocks=blocks,road_network=SimpleNamespace(graph={
                'A':{'B':[first]},'B':{'C':[connector]},'C':{'D':[last]}}))
            engine=SimpleNamespace(taskMgr=SimpleNamespace(getTasks=lambda:[SimpleNamespace(getName=lambda n=n:n)
                for n in ('igLoop','PSSM.update','update main chase camera')]))
            def no_hide(*args):raise AssertionError('must preserve original ego visibility')
            provider=SimpleNamespace(env=SimpleNamespace(engine=engine,current_map=world,
                vehicle=SimpleNamespace(origin=SimpleNamespace(hide=no_hide))),close=lambda:events.append('close'))
            @contextmanager
            def bins(typ):
                events.append('bin_enter')
                try:yield copy.deepcopy(base['opaque_bin_diagnostic'])
                finally:events.append('bin_exit')
            policy=WorldFramePolicyAdapter(Inner(),source_action_frame=SOURCE_ACTION_FRAME)
            def clock():return dict(frame_count=10+ticks[0],frame_time_s=ticks[0]*.05,real_time_s=ticks[0]*.1,dt_s=.05)
            with patch.object(m.frame,'_new_policy',return_value=policy) as factory,patch.object(m,'_runtime',return_value=base['runtime']), \
                 patch.object(m,'_new_provider',side_effect=lambda *a:events.append('provider') or provider), \
                 patch.object(m,'opaque_bin_policy',side_effect=bins),patch.object(m,'configure_sampler',return_value=base['sampler_configuration']), \
                 patch.object(m,'select_native_curve_lanes',return_value=[first] if group=='native_ramps' else [first,last]), \
                 patch.object(m,'_new_camera',return_value=Camera()),patch.object(m.base,'clock_sample',side_effect=clock):
                d=m.native_trial(model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),group=group,seed=SEEDS[0],
                    scene=GROUPS[group][0][0],repeat=0,request_uuid='a'*32)
            self.assertEqual(factory.call_count,1);self.assertEqual(d['adapter_reset_calls'],1);self.assertEqual(d['policy_reset_count'],2)
            self.assertTrue(d['provider_closed']);self.assertFalse(d['official_model_execution'])
            self.assertLess(events.index('bin_enter'),events.index('provider'));self.assertLess(events.index('close'),events.index('bin_exit'))
            self.assertEqual(events.count('capture'),session_calls[0])
            if fail:
                self.assertEqual(session_calls[0],5);self.assertEqual(d['execution_accounting']['known_committed_parent_steps'],4)
                self.assertIsNone(d['execution_accounting']['total_executed_ort_calls'])
            elif group=='native_ramps':
                self.assertEqual(d['completed_steps'],6);self.assertEqual(d['execution_accounting']['total_executed_ort_calls'],7)
            elif group=='longer160':
                self.assertEqual(d['completed_steps'],160);self.assertEqual(d['route_active_index_after_episode'],2)

    def test_all_actual_configs_and_factory_pins_precede_no_second_adapter(self):
        m=module(self);count=budget=0
        for group,(scenes,fraction,steps) in GROUPS.items():
            for seed in SEEDS:
                for scene in scenes:
                    for repeat in (0,1):
                        spec=m.campaign_spec(group,seed,scene,repeat);self.assertEqual((spec.scenario,spec.initial_fraction,spec.steps),(scene,fraction,steps))
                        count+=1;budget+=spec.steps
        self.assertEqual((count,budget),(24,1472));self.assertEqual(len(m.verify_source_bindings()),9)
        with self.assertRaises(ValueError):m.campaign_spec('native_ramps',SEEDS[0],'s_curve_left_right')
        with patch.object(m,'verify_source_bindings',side_effect=ValueError('changed source')), \
             patch.object(m.frame,'_new_policy',side_effect=AssertionError('factory must not run')):
            with self.assertRaises(ValueError):m._new_policy(Path('UNIT_NOT_WEIGHTS'),Path('model_specs/md-v3.json'))

    def test_uncommitted_policy_attempt_is_unknown_not_committed_prefix_total(self):
        m=module(self);d=fixture('longer160',failed='policy',committed=4)
        value=m.attempt_accounting(d)
        self.assertEqual(value['known_committed_parent_steps'],4)
        self.assertIsNone(value['total_executed_ort_calls']);self.assertIn('UNCOMMITTED',value['reason'])
        self.assertEqual(value['completed_frame_rows'],4)
        with self.assertRaises(ValueError):m.validate_trial(d,'longer160',SEEDS[0],d['scenario'],0)

    def test_last_truth_failure_consumes160_but159_rows_never_pass(self):
        m=module(self);d=fixture('longer160',failed='truth',committed=159)
        accounting=m.attempt_accounting(d)
        self.assertEqual(accounting['known_committed_parent_steps'],160)
        self.assertEqual(accounting['total_executed_ort_calls'],160)
        self.assertEqual(accounting['completed_frame_rows'],159)
        self.assertEqual(len(d['bridge_receipts']),160)
        with patch.object(m,'compare_fresh_trials',side_effect=AssertionError('no partial comparison')):
            with self.assertRaises(ValueError):m.compare_trials(d,fixture('longer160',repeat=1),'longer160',SEEDS[0],d['scenario'])

    def test_complete_actual_ramps_and160_never_call_fixed_validators(self):
        m=module(self)
        with patch.object(m.frame,'validate_trial',side_effect=AssertionError('fixed12 forbidden')), \
             patch.object(m.legacy,'validate_trial',side_effect=AssertionError('legacy partial forbidden')):
            for group,(scenes,_,_) in GROUPS.items():
                for scene in scenes:m.validate_trial(fixture(group,scene=scene),group,SEEDS[0],scene,0)

    def test_late159160_corruptions_and_runtime_geometry_controls_fail(self):
        m=module(self)
        for fault in ('state','bridge','clock','pose','capture','source','block','accounting','trace','runtime','tasks','guard','bin'):
            d=fixture('longer160')
            if fault=='state':del d['inference_audit_rows'][158]['named_state_receipts']['state_feat_q']
            elif fault=='bridge':d['bridge_receipts'][159]['body_rotation'][1][1]=1.
            elif fault=='clock':d['capture_audit_rows'][159]['global_clock_frame_count_delta']=1
            elif fault=='pose':d['frames'][159]['heading_rad']+=.01
            elif fault=='capture':d['frames'][159]['source_road_rgb_sha256']='f'*64
            elif fault=='source':d['source_bindings']['bigbench/model_world_frame.py']='f'*64
            elif fault=='block':d['native_geometry']['blocks'][0]['id']='r'
            elif fault=='accounting':d['execution_accounting']['total_executed_ort_calls']=159
            elif fault=='trace':d['committed_parent_trace'][159]['step_index']=0
            elif fault=='runtime':d['runtime']['injected_session']=True
            elif fault=='tasks':d['registered_tasks_after'].remove('PSSM.update')
            elif fault=='guard':d['sampler_configuration']['shadow_guard']['enabled']=False
            else:d['opaque_bin_diagnostic']['restored']['type']=1
            with self.subTest(fault=fault):
                with self.assertRaises(ValueError):m.validate_trial(d,'longer160',SEEDS[0],d['scenario'],0)

    def test_complete_cohort_and_failed_unknown_totals_are_separate(self):
        m=module(self)
        for failed in (None,'policy'):
            with TemporaryDirectory() as tmp:
                root=Path(tmp);build(root,m,failed);result=m.aggregate_cases(root)
                self.assertEqual(result['planned_onnx_steps'],1472)
                self.assertEqual(result['known_committed_parent_steps_lower_bound'],1472 if failed is None else 1156)
                self.assertEqual(result['total_executed_ort_calls'],1472 if failed is None else None)
                self.assertEqual(result['unknown_case_count'],0 if failed is None else 1)
                self.assertEqual(result['aggregation_succeeded'],failed is None)
                self.assertEqual(result['world_frame_expansion_all_cases_passed'],failed is None)
                out=root/'aggregate_summary.json';status=m.main(['--mode','aggregate','--root',str(root),'--out',str(out)])
                self.assertEqual(status,0 if failed is None else 2);self.assertTrue(out.exists())

    def test_native_raw_first_and_actual_status_two_preserve_dangling_unknown(self):
        m=module(self);d=fixture('longer160',failed='policy')
        with TemporaryDirectory() as tmp:
            out=Path(tmp)/'raw.json'
            with patch.object(m,'native_trial',return_value=d):
                status=m.main(['--mode','native','--model','UNIT_NOT_WEIGHTS','--spec','model_specs/md-v3.json',
                    '--group','longer160','--seed',str(SEEDS[0]),'--scene',d['scenario'],'--repeat','0',
                    '--request-uuid',d['world_frame_expansion_trial']['request_uuid'],'--out',str(out)])
            self.assertEqual(status,2);raw=json.loads(out.read_text())
            self.assertEqual(len(raw['capture_audit_rows']),5);self.assertIsNone(raw['execution_accounting']['total_executed_ort_calls'])

    def test_failed_child_stops_case_and_records_unattempted_repeat(self):
        m=module(self)
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/'matrix';calls=[]
            def child(command,**kwargs):
                calls.append(command);d=fixture('longer160',failed='policy')
                d['world_frame_expansion_trial']['request_uuid']=command[command.index('--request-uuid')+1]
                Path(command[command.index('--out')+1]).write_text(json.dumps(d));return SimpleNamespace(returncode=2)
            with patch.object(m.subprocess,'run',side_effect=child):
                status=m.run_case(root=root,model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),
                    group='longer160',seed=SEEDS[0],scene='s_curve_left_right')
            self.assertEqual(status,2);self.assertEqual(len(calls),1)
            ledger=json.loads((root/'longer160'/f'seed-{SEEDS[0]}'/'s_curve_left_right'/'execution_ledger.json').read_text())
            self.assertEqual(ledger['unattempted_repeats'],[1]);self.assertEqual(ledger['entries'][0]['native_exit_status'],2)


if __name__=='__main__':unittest.main()
