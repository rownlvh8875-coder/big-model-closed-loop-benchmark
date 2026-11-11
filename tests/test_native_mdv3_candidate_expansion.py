"""Pure/unit expansion contracts; no official weights, Panda or ORT execution."""
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

import numpy as np

from bigbench.kinematics import AgentState, ModelAction, step_ideal
from test_native_mdv3_renderer_candidate import fixture as base_fixture

GROUPS={'camera028':(('s_curve_left_right','s_curve_right_left'),.28,12),
        'native_ramps':(('in_ramp','out_ramp'),.12,12),
        'longer160':(('s_curve_left_right','s_curve_right_left'),.12,160)}
SEEDS=(20261109,20261110)
POLICY_KEYS=('new_img_sha256','raw_model_action','raw_action_sha256','state_after_step_sha256',
             'named_state_receipts','raw_action_receipt','parent_converted_action','named_state_audit_wall_s')
HASH_KEYS=('source_road_rgb_sha256','source_wide_rgb_sha256','road_frame_sha256','wide_frame_sha256')


def module(test):
    test.assertIsNotNone(importlib.util.find_spec('scripts.native_mdv3_candidate_expansion'),
                         'expansion implementation is missing')
    return importlib.import_module('scripts.native_mdv3_candidate_expansion')


def fixture(group='camera028',seed=SEEDS[0],scene=None,repeat=0,partial=None):
    scenes,fraction,planned=GROUPS[group];scene=scene or scenes[0]
    d=base_fixture(seed,repeat=repeat);template=copy.deepcopy(d['frames'][0])
    name=f'{group}-{seed}-{scene}-{repeat}'
    d.update(protocol='stage7-mdv3-candidate-expansion-v1',scenario=scene,initial_fraction=fraction,
        requested_steps=planned,trial_evidence='CANDIDATE_BOTH_UNSORTED_OFFICIAL_MDV3_EXPANSION',
        process_uuid=uuid.uuid5(uuid.NAMESPACE_DNS,name).hex,
        expansion_trial=dict(group=group,seed=seed,scenario=scene,repeat=repeat,
                             request_uuid=uuid.uuid5(uuid.NAMESPACE_URL,name).hex),
        campaign_spec=dict(scenario=scene,seed=seed,steps=planned,speed_mps=8.,dt_s=.05,
                           fixed_speed=True,initial_fraction=fraction),
        full_s_route_requested=group=='longer160',full_s_traversal_proven=False)
    d.pop('candidate_trial');d.pop('partial_policy_audit_rows');d.pop('partial_capture_audit_rows')
    d['registered_tasks_before']=sorted(d['registered_tasks_before'])
    d['registered_tasks_after']=d['registered_tasks_before'].copy()
    n=planned if partial is None else partial+1;m=planned if partial is None else partial
    rows=[];caps=[];audits=[];pose=AgentState(0.,0.,0.,0.,8.)
    for index in range(n):
        row=copy.deepcopy(template);after=step_ideal(pose,ModelAction(0.,0.),.05,speed_override=8.)
        row.update(step=index+1,time_s=after.t,world_x_m=after.x,world_y_m=after.y,
                   heading_rad=after.heading,speed_mps=after.speed)
        cap=row['capture_audit'];cap['entry_pose']=asdict(pose)
        cap['before']=dict(frame_count=10+2*index,frame_time_s=index*.1,real_time_s=index*.2,dt_s=.05)
        cap['after']=dict(frame_count=12+2*index,frame_time_s=(index+1)*.1,real_time_s=index*.2+.15,dt_s=.05)
        cap['global_clock_time_delta_s']=cap['after']['frame_time_s']-cap['before']['frame_time_s']
        cap['real_time_delta_s']=cap['after']['real_time_s']-cap['before']['real_time_s']
        cap.update({key:row[key] for key in HASH_KEYS})
        cap.update(warped_bytes_hashed=786432,warped_hash_audit_wall_s=.001)
        caps.append(copy.deepcopy(cap));audits.append({k:copy.deepcopy(row[k]) for k in POLICY_KEYS})
        if index<m:rows.append(row)
        pose=after
    error=None if partial is None else 'LaneTruthError: ego longitudinal coordinate outside lane segment'
    status='DIAGNOSTIC_EXECUTED' if partial is None else 'FAILED_OR_INCOMPLETE'
    d.update(status=status,error=error,frames=rows,completed_steps=m,parent_onnx_step_count=n,
        capture_audit_rows=caps,inference_audit_rows=audits,
        episode_provenance=dict(public_episode_returned=True,returned_status=status,returned_error=error,
                                outer_lifecycle_error=None))
    d['audit_scope'].update(capture_delegate_calls=n,warped_bytes_hashed_per_capture=786432)
    lane=dict(index='lane0',type='UNIT_NATIVE_LANE',length=200.,radius=55.,direction=1.)
    selected=[lane] if group=='native_ramps' else [lane,dict(lane,index='lane1',direction=-1.)]
    route=copy.deepcopy(selected) if group=='longer160' else [copy.deepcopy(lane)]
    blocks=[dict(id='I',direction=None)]
    blocks+=([dict(id='r' if scene=='in_ramp' else 'R',direction=None)] if group=='native_ramps'
             else [dict(id='C',direction=x) for x in ((0,1) if scene.endswith('left_right') else (1,0))])
    d.update(explicit_route_lane_ids=[z['index'] for z in route],route_active_index_after_episode=0,
        visited_target_lane_ids=['lane0'] if rows else [],
        native_geometry=dict(blocks=blocks,selected_lanes=selected,route_lanes=route,
                             initial_pose=asdict(AgentState(0.,0.,0.,0.,8.))))
    return d


def build(root,m,partial_case=None):
    for group,(scenes,_,_) in GROUPS.items():
        for seed in SEEDS:
            for scene in scenes:
                folder=root/group/f'seed-{seed}'/scene;folder.mkdir(parents=True)
                entries=[]
                for repeat in (0,1):
                    d=fixture(group,seed,scene,repeat,partial=3 if (group,seed,scene)==partial_case else None)
                    filename=f'run_{repeat}.json';(folder/filename).write_text(json.dumps(d))
                    entries.append(dict(repeat=repeat,filename=filename,request_uuid=d['expansion_trial']['request_uuid'],
                        process_uuid=d['process_uuid'],process_id=d['process_id'],started_ns=100+repeat*10,
                        finished_ns=105+repeat*10,native_exit_status=2 if d['error'] else 0,
                        diagnostic_classification='VALID_FAILED_DIAGNOSTIC' if d['error'] else 'COMPLETE'))
                ledger=dict(group=group,seed=seed,scenario=scene,entries=entries)
                (folder/'execution_ledger.json').write_text(json.dumps(ledger))
                (folder/'case_comparison.json').write_text(json.dumps(m.compare_case(root,group,seed,scene)))


class ExpansionContracts(unittest.TestCase):
    def test_native_straight_vector_and_circular_scalar_directions_remain_distinct(self):
        m=module(self)
        if importlib.util.find_spec('metadrive') is not None:
            from metadrive.component.lane.straight_lane import StraightLane
            from metadrive.component.lane.circular_lane import CircularLane
            lane=StraightLane([0.,0.],[10.,0.]);lane.index=('A','B',0)
            circle=CircularLane([0.,0.],55.,0.,.5,clockwise=True);circle.index=('B','C',0)
        else:
            lane=SimpleNamespace(index=('A','B',0),length=10.,radius=0.,direction=np.array([1.,0.]))
            circle=SimpleNamespace(index=('B','C',0),length=27.5,radius=55.,direction=-1)
        try:receipt=m._lane_receipt(lane)
        except TypeError as exc:self.fail(f'native StraightLane direction vector must serialize: {exc}')
        self.assertEqual(receipt['direction'],[1.,0.]);self.assertEqual(receipt['radius'],0.)
        circular=m._lane_receipt(circle)
        self.assertEqual(circular['direction'],-1.)
        d=fixture('longer160');d['native_geometry']['route_lanes'].insert(1,receipt)
        d['explicit_route_lane_ids'].insert(1,receipt['index'])
        self.assertEqual(m.validate_trial(d,'longer160',SEEDS[0],d['scenario'],0),'COMPLETE')

    def test_all_twelve_actual_configs_and_twenty_four_repeats_are_bounded(self):
        m=module(self);count=budget=0
        for group,(scenes,fraction,steps) in GROUPS.items():
            for seed in SEEDS:
                for scene in scenes:
                    for repeat in (0,1):
                        spec=m.campaign_spec(group,seed,scene,repeat)
                        self.assertEqual((spec.scenario,spec.initial_fraction,spec.steps),(scene,fraction,steps))
                        count+=1;budget+=spec.steps
        self.assertEqual((count,budget),(24,1472))
        for args in (('camera028',SEEDS[0],'in_ramp',0),('native_ramps',SEEDS[0],'s_curve_left_right',0),
                     ('longer160',SEEDS[0],'s_curve_left_right',2)):
            with self.assertRaises(ValueError):m.campaign_spec(*args)

    def test_actual_ramps_and_160_validate_without_fixed_base_validator(self):
        m=module(self)
        with patch.object(m.base,'validate_trial',side_effect=AssertionError('fixed base validator forbidden')):
            for group,(scenes,_,_) in GROUPS.items():
                for scene in scenes:
                    d=fixture(group,scene=scene)
                    self.assertEqual(m.validate_trial(d,group,SEEDS[0],scene,0,native_exit_status=0),'COMPLETE')

    def test_partial_retains_dangling_capture_and_states_but_never_passes(self):
        m=module(self);a,b=(fixture('longer160',repeat=r,partial=159) for r in (0,1))
        # Progress may advance before failed truth; this does not add a successful visit.
        a['route_active_index_after_episode']=b['route_active_index_after_episode']=1
        self.assertEqual(m.validate_trial(a,'longer160',SEEDS[0],a['scenario'],0,native_exit_status=2),'VALID_FAILED_DIAGNOSTIC')
        with patch.object(m,'compare_fresh_trials',side_effect=AssertionError('partial common comparison forbidden')):
            result=m.compare_trials(a,b,'longer160',SEEDS[0],a['scenario'])
        self.assertFalse(result['candidate_expansion_gate_passed'])
        self.assertEqual(result['reason'],'INCOMPLETE_REQUESTED_EPISODE')
        self.assertEqual(result['first_incomplete_step'],160)
        self.assertEqual(result['actual_onnx_steps'],320)
        self.assertEqual(result['completed_frame_rows'],318)

    def test_wrong_status_provenance_counts_and_dangling_hashes_reject(self):
        m=module(self);scene='s_curve_left_right'
        for mutation in ('zero','outer','not_returned','returned_error','other_error','missing_capture_hash',
                         'missing_state','capture_error','extra_count','wrong_prefix','hash_audit_error'):
            d=fixture('longer160',partial=0 if mutation=='zero' else 3)
            if mutation=='outer':d['episode_provenance']['outer_lifecycle_error']='RuntimeError: close'
            elif mutation=='not_returned':d['episode_provenance']['public_episode_returned']=False
            elif mutation=='returned_error':d['episode_provenance']['returned_error']='LaneTruthError: forged'
            elif mutation=='other_error':d['error']='RuntimeError: not route failure';d['episode_provenance']['returned_error']=d['error']
            elif mutation=='missing_capture_hash':del d['capture_audit_rows'][-1]['source_wide_rgb_sha256']
            elif mutation=='missing_state':del d['inference_audit_rows'][-1]['named_state_receipts']['state_feat_q']
            elif mutation=='capture_error':d['capture_audit_rows'][-1]['error']='LaneTruthError: camera failure'
            elif mutation=='extra_count':d['parent_onnx_step_count']+=1
            elif mutation=='wrong_prefix':d['error']='LaneTruthError:simulated';d['episode_provenance']['returned_error']=d['error']
            elif mutation=='hash_audit_error':d['capture_audit_rows'][-1]['hash_audit_error']='RuntimeError: digest'
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):m.validate_trial(d,'longer160',SEEDS[0],scene,0,native_exit_status=2)
        for partial,status in ((3,0),(3,5),(None,2),(3,7)):
            with self.assertRaises(ValueError):m.validate_trial(fixture('longer160',partial=partial),'longer160',SEEDS[0],scene,0,native_exit_status=status)

    def test_late_159_160_fields_and_route_identity_are_actually_checked(self):
        m=module(self);scene='s_curve_left_right'
        for field in ('state','clock','pose','capture_hash','route','ramp','claim','initial'):
            d=fixture('longer160');row=d['frames'][159]
            if field=='state':del d['inference_audit_rows'][158]['named_state_receipts']['state_img_q']
            elif field=='clock':d['capture_audit_rows'][159]['global_clock_frame_count_delta']=1
            elif field=='pose':row['time_s']+=.001
            elif field=='capture_hash':row['road_frame_sha256']='f'*64
            elif field=='route':d['explicit_route_lane_ids']=['not-native']
            elif field=='ramp':d=fixture('native_ramps');d['native_geometry']['blocks'][1]['id']='C'
            elif field=='claim':d['original_mdv3_gate_passed']=True
            else:d['native_geometry']['initial_pose']['x']+=1
            group=d['expansion_trial']['group'];scene=d['scenario']
            with self.subTest(field=field):
                with self.assertRaises(ValueError):m.validate_trial(d,group,SEEDS[0],scene,0)
        a,b=fixture('longer160',repeat=0),fixture('longer160',repeat=1)
        b['frames'][158]['named_state_receipts']['state_feat_q']['sha256']='f'*64
        b['inference_audit_rows'][158]['named_state_receipts']['state_feat_q']['sha256']='f'*64
        result=m.compare_trials(a,b,'longer160',SEEDS[0],a['scenario'])
        self.assertFalse(result['candidate_expansion_gate_passed']);self.assertEqual(result['first_diverging_step'],159)

    def test_actual_direction_and_finite_typed_state_action_clock_controls_reject(self):
        m=module(self)
        for change in ('directions','bool_action','state_dtype','action_shape','action_bytes','nonfinite_clock','runtime','tasks','sampler','bin'):
            d=fixture('longer160')
            if change=='directions':d['native_geometry']['selected_lanes'][1]['direction']=1.;d['native_geometry']['route_lanes'][1]['direction']=1.
            elif change=='bool_action':d['frames'][159]['desired_curvature_1pm']=False
            elif change=='state_dtype':d['inference_audit_rows'][159]['named_state_receipts']['state_img_q']['dtype']='float32'
            elif change=='action_shape':d['inference_audit_rows'][159]['raw_action_receipt']['shape']=[2,2]
            elif change=='action_bytes':d['inference_audit_rows'][159]['raw_model_action'][3]=1e-50
            elif change=='nonfinite_clock':d['capture_audit_rows'][159]['after']['dt_s']=float('nan')
            elif change=='runtime':d['runtime']['injected_session']=True
            elif change=='tasks':d['registered_tasks_after'].remove('PSSM.update')
            elif change=='sampler':d['sampler_configuration']['shadow_guard']['enabled']=False
            else:d['opaque_bin_diagnostic']['restored']['type']=1
            with self.subTest(change=change):
                with self.assertRaises(ValueError):m.validate_trial(d,'longer160',SEEDS[0],d['scenario'],0)

    def test_uuid_nonce_and_pid_reuse_are_rejected(self):
        m=module(self)
        a,b=fixture(repeat=0),fixture(repeat=1);b['process_id']=a['process_id']
        with self.assertRaises(ValueError):m.compare_trials(a,b,'camera028',SEEDS[0],a['scenario'])
        for key in ('process_uuid','request_uuid'):
            with TemporaryDirectory() as tmp:
                root=Path(tmp);build(root,m);group='native_ramps';scene='out_ramp';seed=SEEDS[1]
                folder=root/group/f'seed-{seed}'/scene;path=folder/'run_0.json';d=json.loads(path.read_text());other=fixture()
                value=other['process_uuid'] if key=='process_uuid' else other['expansion_trial']['request_uuid']
                if key=='process_uuid':d[key]=value
                else:d['expansion_trial'][key]=value
                path.write_text(json.dumps(d));path=folder/'execution_ledger.json';ledger=json.loads(path.read_text())
                ledger['entries'][0][key]=value;path.write_text(json.dumps(ledger))
                (folder/'case_comparison.json').write_text(json.dumps(m.compare_case(root,group,seed,scene)))
                with self.assertRaises(ValueError):m.aggregate_cases(root)

    def test_global_aggregation_counts_partial_actual_inferences_and_stale_results(self):
        m=module(self)
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root,m,partial_case=('longer160',SEEDS[0],'s_curve_left_right'))
            result=m.aggregate_cases(root)
            self.assertEqual(result['independent_process_count'],24)
            self.assertEqual(result['planned_onnx_steps'],1472)
            self.assertEqual(result['actual_onnx_steps'],1160)
            self.assertEqual(result['completed_frame_rows'],1158)
            self.assertEqual(result['candidate_expansion_gate_pass_count'],11)
            self.assertFalse(result['candidate_expansion_all_cases_passed'])
            self.assertFalse(result['original_mdv3_gate_passed'])
            bad=copy.deepcopy(result);bad['actual_onnx_steps']=1472
            (root/'aggregate_summary.json').write_text(json.dumps(bad))
            with self.assertRaises(ValueError):m.aggregate_cases(root)


class ExpansionCaptureContracts(unittest.TestCase):
    def test_noninjected_setup_failure_with_zero_parent_steps_never_claims_execution(self):
        m=module(self)
        policy=SimpleNamespace(is_mock=False,_injected_session=False,trace=[],audit_rows=[],
                               contract=SimpleNamespace(sha256=base_fixture()['model_sha256']))
        with patch.object(m,'_new_policy',return_value=policy),patch.object(m,'_runtime',side_effect=RuntimeError('UNIT setup')), \
             patch.object(m,'_new_provider',side_effect=AssertionError('provider must not start')):
            d=m.native_trial(model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),
                group='camera028',seed=SEEDS[0],scene='s_curve_left_right',repeat=0,request_uuid='a'*32)
        self.assertFalse(d['official_model_execution']);self.assertFalse(d['episode_provenance']['public_episode_returned'])
        self.assertEqual(d['parent_onnx_step_count'],0);self.assertEqual(d['completed_steps'],0)
        self.assertIn('RuntimeError: UNIT setup',d['episode_provenance']['outer_lifecycle_error'])

    def test_public_loop_lifecycle_uses_real_route_and_preserves_truth_failed_extra_step(self):
        m=module(self)
        from test_native_route import Straight
        from test_native_model_campaign import FakePairCamera
        for group,close_failure in [(name,False) for name in GROUPS]+[('native_ramps',True)]:
            scene=GROUPS[group][0][0];events=[];ticks=[0];template=base_fixture()['frames'][0]
            class UnitPolicy:
                is_mock=True;_injected_session=True;name='UNIT_NOT_OFFICIAL'
                contract=SimpleNamespace(sha256=base_fixture()['model_sha256'])
                def __init__(self):
                    self.policy_reset_count=1;self.audit_rows=[];self.trace=[]
                    self.initial_state_receipts=base_fixture()['initial_state_receipts']
                    self.initial_state_sha256=base_fixture()['initial_state_sha256']
                def reset(self):self.policy_reset_count+=1;self.audit_rows=[];self.trace=[];events.append('reset')
                def step(self,observation):
                    events.append('inference');self.trace.append('UNIT_PARENT_STEP')
                    self.audit_rows.append({k:copy.deepcopy(template[k]) for k in POLICY_KEYS})
                    return ModelAction(0.,0.)
            class UnitCamera(FakePairCamera):
                last_source_rgb_sha256={'road':'a'*64,'wide':'b'*64}
                def capture(self,pose):ticks[0]+=2;events.append('capture');return super().capture(pose)
            first=Straight(0,3 if group=='native_ramps' else 20,('A','B',0))
            connector=Straight(20,40,('B','C',0));last=Straight(40,200,('C','D',0))
            for lane in (first,connector,last):lane.radius=55.;lane.direction=1.
            blocks=([SimpleNamespace(ID='r',get_config=lambda:{})] if group=='native_ramps' else
                    [SimpleNamespace(ID='C',get_config=lambda d=d:{'dir':d}) for d in (0,1)])
            world=SimpleNamespace(blocks=blocks,road_network=SimpleNamespace(graph={
                'A':{'B':[first]},'B':{'C':[connector]},'C':{'D':[last]}}))
            engine=SimpleNamespace(taskMgr=SimpleNamespace(getTasks=lambda:[SimpleNamespace(getName=lambda name=name:name)
                for name in ('igLoop','PSSM.update','update main chase camera')]))
            def forbidden_hide(*args):raise AssertionError('ego visibility must remain original')
            def close():
                events.append('close')
                if close_failure:raise RuntimeError('UNIT close failure after public return')
            provider=SimpleNamespace(env=SimpleNamespace(current_map=world,engine=engine,
                vehicle=SimpleNamespace(origin=SimpleNamespace(hide=forbidden_hide))),close=close)
            @contextmanager
            def bins(typ):
                self.assertEqual(typ,1);events.append('bin_enter')
                try:yield copy.deepcopy(base_fixture()['opaque_bin_diagnostic'])
                finally:events.append('bin_exit')
            def clock():return dict(frame_count=10+ticks[0],frame_time_s=ticks[0]*.05,real_time_s=ticks[0]*.1,dt_s=.05)
            with patch.object(m,'_new_policy',side_effect=lambda *a:UnitPolicy()), \
                 patch.object(m,'_runtime',return_value=base_fixture()['runtime']), \
                 patch.object(m,'opaque_bin_policy',side_effect=bins), \
                 patch.object(m,'_new_provider',side_effect=lambda *a:events.append('provider') or provider), \
                 patch.object(m,'configure_sampler',side_effect=lambda *a:events.append('sampler') or base_fixture()['sampler_configuration']), \
                 patch.object(m,'select_native_curve_lanes',return_value=[first] if group=='native_ramps' else [first,last]), \
                 patch.object(m,'_new_camera',return_value=UnitCamera()),patch.object(m.base,'clock_sample',side_effect=clock):
                d=m.native_trial(model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),
                    group=group,seed=SEEDS[0],scene=scene,repeat=0,request_uuid='a'*32)
            expected=7 if group=='native_ramps' else GROUPS[group][2]
            self.assertEqual(events.count('inference'),expected);self.assertEqual(events.count('capture'),expected)
            self.assertEqual(d['completed_steps'],6 if group=='native_ramps' else expected)
            self.assertEqual(len(d['inference_audit_rows']),expected);self.assertEqual(len(d['capture_audit_rows']),expected)
            self.assertTrue(d['episode_provenance']['public_episode_returned'])
            self.assertEqual(d['policy_reset_count'],2);self.assertEqual(d['provider_closed'],not close_failure)
            if close_failure:
                self.assertIn('UNIT close failure',d['episode_provenance']['outer_lifecycle_error'])
                self.assertTrue(d['episode_provenance']['returned_error'].startswith('LaneTruthError: '))
            else:self.assertIsNone(d['episode_provenance']['outer_lifecycle_error'])
            self.assertLess(events.index('bin_enter'),events.index('provider'));self.assertLess(events.index('provider'),events.index('sampler'))
            self.assertLess(events.index('close'),events.index('bin_exit'));self.assertFalse(d['official_model_execution'])
            if group=='native_ramps' and not close_failure:self.assertTrue(d['error'].startswith('LaneTruthError: '))
            if group=='longer160':
                self.assertEqual(d['route_active_index_after_episode'],2)
                self.assertEqual(d['visited_target_lane_ids'],[str(first.index),str(connector.index),str(last.index)])

    def test_capture_parent_once_keeps_only_hashes_and_discloses_cpu_overhead(self):
        m=module(self);pose=AgentState(0.,1.,2.,.2,8.);calls=[]
        pair=SimpleNamespace(road=SimpleNamespace(sha256='c'*64),wide=SimpleNamespace(sha256='d'*64))
        delegate=SimpleNamespace(last_source_rgb_sha256={'road':'a'*64,'wide':'b'*64},capture=lambda p:calls.append(p) or pair)
        clocks=iter([dict(frame_count=10,frame_time_s=1.,real_time_s=2.,dt_s=.05),dict(frame_count=12,frame_time_s=1.1,real_time_s=2.2,dt_s=.05)])
        with patch.object(m.base,'clock_sample',side_effect=lambda:next(clocks)):
            audit=m.ExpansionCaptureAudit(delegate);self.assertIs(audit.capture(pose),pair)
        self.assertEqual(calls,[pose]);self.assertEqual(audit.rows[0]['warped_bytes_hashed'],786432)
        self.assertEqual(audit.rows[0]['source_road_rgb_sha256'],'a'*64)
        self.assertEqual(audit.rows[0]['wide_frame_sha256'],'d'*64)
        self.assertGreaterEqual(audit.rows[0]['warped_hash_audit_wall_s'],0)
        self.assertEqual(set(vars(audit)),{'delegate','rows','delegate_calls'})

    def test_hash_failure_is_retained_and_never_looks_like_truth_partial(self):
        m=module(self)
        class BadFrame:
            @property
            def sha256(self):raise RuntimeError('UNIT digest failure')
        delegate=SimpleNamespace(last_source_rgb_sha256={'road':'a'*64,'wide':'b'*64},
            capture=lambda p:SimpleNamespace(road=BadFrame(),wide=BadFrame()))
        clocks=iter([dict(frame_count=x,frame_time_s=float(x),real_time_s=float(x),dt_s=.05) for x in (10,12)])
        with patch.object(m.base,'clock_sample',side_effect=lambda:next(clocks)):
            audit=m.ExpansionCaptureAudit(delegate)
            with self.assertRaises(RuntimeError):audit.capture(AgentState(0.,0.,0.,0.,8.))
        self.assertIn('UNIT digest failure',audit.rows[0]['hash_audit_error'])


class ExpansionLaunchContracts(unittest.TestCase):
    def test_launcher_status_table_nonce_and_stale_proofs(self):
        m=module(self)
        for status,partial in ((0,None),(5,None),(2,3),(0,3),(5,3),(2,None),(7,None)):
            with TemporaryDirectory() as tmp:
                out=Path(tmp)/'raw.json';statuses=[]
                def child(command,**kwargs):
                    d=fixture(partial=partial);d['expansion_trial']['request_uuid']=command[command.index('--request-uuid')+1]
                    out.write_text(json.dumps(d));return SimpleNamespace(returncode=status)
                valid=(status,partial) in ((0,None),(5,None),(2,3),(7,None))
                with patch.object(m.subprocess,'run',side_effect=child):
                    kwargs=dict(model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),group='camera028',
                                seed=SEEDS[0],scene='s_curve_left_right',repeat=0,out=out,status_receipt=statuses)
                    if valid:
                        receipt=m.launch_trial(**kwargs);self.assertEqual(receipt['native_exit_status'],status)
                    else:
                        with self.assertRaises(ValueError):m.launch_trial(**kwargs)
                self.assertEqual(statuses,[status])
                with self.assertRaises(ValueError):m.launch_trial(**kwargs)
        for mode in ('missing','nonce','malformed'):
            with TemporaryDirectory() as tmp:
                out=Path(tmp)/'raw.json'
                def child(command,**kwargs):
                    if mode!='missing':
                        d=fixture();d['expansion_trial']['request_uuid']='f'*32
                        if mode=='malformed':d['frames'].pop()
                        out.write_text(json.dumps(d))
                    return SimpleNamespace(returncode=5)
                with patch.object(m.subprocess,'run',side_effect=child):
                    with self.assertRaises((ValueError,FileNotFoundError)):
                        m.launch_trial(model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),group='camera028',
                                       seed=SEEDS[0],scene='s_curve_left_right',repeat=0,out=out)

    def test_native_raw_first_wire_validation_and_partial_exit_two(self):
        m=module(self)
        for partial in (None,3):
            d=fixture(partial=partial);d['initial_state_receipts']['state_img_q']['shape']=tuple(d['initial_state_receipts']['state_img_q']['shape'])
            with TemporaryDirectory() as tmp:
                out=Path(tmp)/'raw.json'
                with patch.object(m,'native_trial',return_value=d):
                    result=m.main(['--mode','native','--group','camera028','--seed',str(SEEDS[0]),
                        '--scene',d['scenario'],'--repeat','0','--request-uuid',d['expansion_trial']['request_uuid'],
                        '--model','UNIT_NOT_WEIGHTS','--spec','model_specs/md-v3.json','--out',str(out)])
                self.assertEqual(result,0 if partial is None else 2)
                wire=json.loads(out.read_text());self.assertEqual(wire['capture_audit_rows'],d['capture_audit_rows'])
                self.assertEqual(wire['requested_steps'],12)

    def test_two_valid_failed_children_keep_status_two_while_case_collection_succeeds(self):
        m=module(self)
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/'matrix';calls=[]
            def child(command,**kwargs):
                calls.append(command);arg=lambda k:command[command.index(k)+1]
                d=fixture('native_ramps',repeat=int(arg('--repeat')),partial=3)
                d['expansion_trial']['request_uuid']=arg('--request-uuid')
                Path(arg('--out')).write_text(json.dumps(d));return SimpleNamespace(returncode=2)
            with patch.object(m.subprocess,'run',side_effect=child):
                code=m.run_case(root=root,model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),
                    group='native_ramps',seed=SEEDS[0],scene='in_ramp')
            self.assertEqual(code,0);self.assertEqual(len(calls),2)
            folder=root/'native_ramps'/f'seed-{SEEDS[0]}'/'in_ramp'
            ledger=json.loads((folder/'execution_ledger.json').read_text())
            self.assertEqual([x['native_exit_status'] for x in ledger['entries']],[2,2])
            verdict=json.loads((folder/'case_comparison.json').read_text())
            self.assertFalse(verdict['candidate_expansion_gate_passed'])


if __name__=='__main__':unittest.main()
