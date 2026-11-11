"""Synthetic frame-boundary contracts; no controller, official weights or native GL."""
import copy
from contextlib import contextmanager
from dataclasses import asdict
import importlib
import importlib.util
import json
import math
from hashlib import sha256
import struct
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

import numpy as np

from bigbench.kinematics import AgentState,ModelAction,step_ideal
from test_native_mdv3_candidate_expansion import fixture as expansion_fixture


def module(test,name='scripts.native_mdv3_world_frame'):
    test.assertIsNotNone(importlib.util.find_spec(name),'world-frame implementation missing')
    return importlib.import_module(name)


def fixture(seed=20261109,scene='s_curve_left_right',repeat=0):
    m=importlib.import_module('scripts.native_mdv3_world_frame')
    d=expansion_fixture(seed=seed,scene=scene,repeat=repeat)
    d.pop('expansion_trial');d['campaign_spec']['initial_fraction']=.12
    d.update(protocol='stage7-mdv3-world-frame-v1',trial_evidence=m.EVIDENCE,initial_fraction=.12,
        world_frame_trial=dict(seed=seed,scenario=scene,repeat=repeat,
            request_uuid=uuid.uuid5(uuid.NAMESPACE_URL,f'world-{seed}-{scene}-{repeat}').hex),
        source_bindings=dict(m.SOURCE_BINDINGS),action_basis=m.basis_receipt(),adapter_reset_calls=1)
    d['process_uuid']=uuid.uuid5(uuid.NAMESPACE_DNS,f'world-{seed}-{scene}-{repeat}').hex
    d['bridge_receipts']=[]
    for index,row in enumerate(d['frames'],1):
        bridge=dict(step=index,**m.basis_receipt(),parent_model_action=row['parent_converted_action'].copy(),
                    applied_world_action=dict(curvature_1pm=-row['parent_converted_action']['curvature_1pm'],
                        acceleration_mps2=row['parent_converted_action']['acceleration_mps2']),bridge_audit_wall_s=.001)
        d['bridge_receipts'].append(bridge);row['world_frame_bridge']=copy.deepcopy(bridge)
    return d


def build(root,m):
    for seed in m.SEEDS:
        for scene in m.SCENES:
            folder=root/f'seed-{seed}'/scene;folder.mkdir(parents=True);entries=[]
            for repeat in (0,1):
                d=fixture(seed,scene,repeat);filename=f'run_{repeat}.json';(folder/filename).write_text(json.dumps(d))
                entries.append(dict(repeat=repeat,filename=filename,request_uuid=d['world_frame_trial']['request_uuid'],
                    process_id=d['process_id'],process_uuid=d['process_uuid'],started_ns=10+repeat*10,finished_ns=15+repeat*10,
                    native_exit_status=0,accepted_exit_status=0))
            (folder/'execution_ledger.json').write_text(json.dumps(dict(seed=seed,scenario=scene,entries=entries)))
            (folder/'case_comparison.json').write_text(json.dumps(m.compare_case(root,seed,scene)))


class AdapterTests(unittest.TestCase):
    def test_signed_model_actions_turn_correct_world_direction_at_multiple_headings(self):
        m=module(self,'bigbench.model_world_frame')
        for heading in (0.,math.pi/2,-.7):
            for curvature in (.125,-.125,0.,-0.):
                parent=ModelAction(curvature,-.25)
                inner=SimpleNamespace(step=lambda observation:parent)
                adapter=m.WorldFramePolicyAdapter(inner,source_action_frame=m.SOURCE_ACTION_FRAME)
                action=adapter.step(object());self.assertEqual(action.acceleration_mps2,-.25)
                self.assertEqual(action.curvature_1pm,-curvature)
                self.assertEqual(math.copysign(1.,action.curvature_1pm),math.copysign(1.,-curvature))
                before=AgentState(0.,0.,0.,heading,8.);after=step_ideal(before,action,.05,speed_override=8.)
                right_displacement=math.sin(heading)*after.x-math.cos(heading)*after.y
                if curvature:self.assertGreater(right_displacement*curvature,0.)
                self.assertEqual(after.heading,heading-curvature*.4)
                self.assertEqual(math.degrees(after.heading)-90.,math.degrees(heading-curvature*.4)-90.)

    def test_no_constructor_reset_same_observation_once_and_inner_evidence_untouched(self):
        m=module(self,'bigbench.model_world_frame');calls=[];observation=object()
        raw=bytearray(b'ACTUAL_RAW_UNIT_BYTES');audit=[{'parent_converted_action':{'curvature_1pm':.125,'acceleration_mps2':-.25}}]
        state={'unit':bytearray(b'ACTUAL_STATE')};trace=[];session=object();contract=object()
        def reset():calls.append('reset')
        def step(obs):self.assertIs(obs,observation);calls.append('step');trace.append('actual_parent');return ModelAction(.125,-.25)
        inner=SimpleNamespace(reset=reset,step=step,state=state,trace=trace,session=session,contract=contract,
            audit_rows=audit,last_model_outputs={'action':raw},is_mock=True,_injected_session=True)
        before=copy.deepcopy((state,audit,raw));adapter=m.WorldFramePolicyAdapter(inner,source_action_frame=m.SOURCE_ACTION_FRAME)
        self.assertEqual(calls,[]);adapter.reset();result=adapter.step(observation)
        self.assertEqual(calls,['reset','step']);self.assertEqual(result,ModelAction(-.125,-.25))
        self.assertIs(adapter.state,state);self.assertIs(adapter.trace,trace);self.assertIs(adapter.session,session)
        self.assertIs(adapter.contract,contract);self.assertIs(adapter.audit_rows,audit);self.assertIs(adapter.last_model_outputs['action'],raw)
        self.assertTrue(adapter.is_mock);self.assertTrue(adapter._injected_session)
        inner.is_mock=False;inner._injected_session=False
        self.assertFalse(adapter.is_mock);self.assertFalse(adapter._injected_session)
        self.assertEqual((state,audit,raw),before);self.assertEqual(len(adapter.bridge_receipts),1)
        self.assertEqual(adapter.bridge_receipts[0]['parent_model_action'],audit[0]['parent_converted_action'])
        adapter.reset();self.assertEqual(adapter.bridge_receipts,[]);self.assertEqual(adapter.adapter_reset_calls,2)

    def test_wrong_declarations_double_wrap_and_already_world_output_reject(self):
        m=module(self,'bigbench.model_world_frame');inner=SimpleNamespace()
        for source in ('WORLD_FLU','unknown',None):
            with self.assertRaises(ValueError):m.WorldFramePolicyAdapter(inner,source_action_frame=source)
        adapter=m.WorldFramePolicyAdapter(inner,source_action_frame=m.SOURCE_ACTION_FRAME)
        for wrapped in (adapter,SimpleNamespace(world_frame_adapter_applied=True),
                        SimpleNamespace(applied_action_frame=m.APPLIED_ACTION_FRAME)):
            with self.assertRaises(ValueError):m.WorldFramePolicyAdapter(wrapped,source_action_frame=m.SOURCE_ACTION_FRAME)


class WorldFrameReceiptTests(unittest.TestCase):
    def test_nonzero_parent_frd_receipts_validate_only_with_opposite_world_kinematics(self):
        m=module(self);d=fixture();pose=AgentState(0.,0.,0.,0.,8.)
        parent=ModelAction(.125,-.25);applied=ModelAction(-.125,-.25)
        digest=sha256(struct.pack('<4f',8.,-.25,2.,3.)).hexdigest()
        for index,row in enumerate(d['frames']):
            audit=d['inference_audit_rows'][index]
            audit.update(raw_model_action=[8.,-.25,2.,3.],raw_action_sha256=digest,parent_converted_action=asdict(parent))
            audit['raw_action_receipt']['sha256']=digest;row.update(copy.deepcopy(audit))
            cap=d['capture_audit_rows'][index];cap['entry_pose']=asdict(pose);row['capture_audit']=copy.deepcopy(cap)
            bridge=d['bridge_receipts'][index];bridge.update(parent_model_action=asdict(parent),applied_world_action=asdict(applied))
            row['world_frame_bridge']=copy.deepcopy(bridge)
            pose=step_ideal(pose,applied,.05,speed_override=8.)
            row.update(time_s=pose.t,world_x_m=pose.x,world_y_m=pose.y,heading_rad=pose.heading,speed_mps=pose.speed,
                       desired_curvature_1pm=applied.curvature_1pm,desired_acceleration_mps2=applied.acceleration_mps2)
        m.validate_trial(d,20261109,'s_curve_left_right',0)
        self.assertLess(d['frames'][-1]['world_y_m'],0.)
        d['frames'][0]['heading_rad']*=-1
        with self.assertRaises(ValueError):m.validate_trial(d,20261109,'s_curve_left_right',0)

    def test_original_camera_pose_rectifier_delegation_and_analytic_body_right(self):
        module(self)
        from bigbench.native_model_campaign import NativeWorldCamera
        from bigbench.optical_calibration import PinholeRectifier
        seen=[];origin=object()
        lens=SimpleNamespace(getFilmSize=lambda:(2.,2.),getFilmOffset=lambda:(0.,0.),getFocalLength=lambda:1.)
        def sensor(kind):
            raw=np.zeros((604,964,3),np.uint8);raw[:,:,0 if kind=='road' else 2]=120
            def perceive(**kwargs):seen.append((kind,kwargs));return raw
            return SimpleNamespace(perceive=perceive,get_lens=lambda:lens)
        provider=SimpleNamespace(source_width=964,source_height=604,height_m=1.22,
            env=SimpleNamespace(engine=SimpleNamespace(origin=origin,sensors={
                'bigbench_road':sensor('road'),'bigbench_wide':sensor('wide')})))
        from bigbench.camera import RGBFrame
        from bigbench.camera_rig import SchematicPair
        camera=NativeWorldCamera(provider);self.assertIsInstance(camera.rectifier,PinholeRectifier)
        unit_pair=SchematicPair(RGBFrame(512,256,bytes((120,0,0))*512*256),RGBFrame(512,256,bytes((0,0,120))*512*256))
        heading=-.4;pose=AgentState(0.,2.,3.,heading,8.)
        with patch.object(camera.rectifier,'rectify_pair',return_value=(unit_pair,{})) as rectify:
            pair=camera.capture(pose)
        self.assertEqual(rectify.call_count,1);self.assertIs(pair,unit_pair)
        self.assertEqual(rectify.call_args.args[0].shape,(604,964,3));self.assertEqual(rectify.call_args.args[1].shape,(604,964,3))
        self.assertEqual([x[0] for x in seen],['road','wide']);self.assertNotEqual(pair.road.sha256,pair.wide.sha256)
        for kind,kwargs in seen:
            self.assertEqual(kwargs['position'],(2.,3.,1.22));self.assertEqual(kwargs['hpr'],(math.degrees(heading)-90.,0.,0.))
            self.assertIs(kwargs['new_parent_node'],origin);self.assertFalse(kwargs['to_float'])
        # Panda camera local +X is image right; H=theta-90 gives world body-right.
        h=math.radians(seen[0][1]['hpr'][0])
        self.assertAlmostEqual(math.cos(h),math.sin(heading));self.assertAlmostEqual(math.sin(h),-math.cos(heading))

    def test_shared_public_episode_applies_bridge_once_keeps_parent_frd_and_visibility(self):
        m=module(self)
        from test_native_route import Straight
        from test_native_model_campaign import FakePairCamera
        events=[];ticks=[0];template=fixture()['inference_audit_rows'][0]
        class UnitPolicy:
            is_mock=True;_injected_session=True;name='UNIT_NOT_OFFICIAL'
            contract=SimpleNamespace(sha256=m.base.MODEL_SHA)
            def __init__(self):
                self.audit_rows=[];self.trace=[];self.policy_reset_count=1
                self.initial_state_receipts=fixture()['initial_state_receipts'];self.initial_state_sha256=fixture()['initial_state_sha256']
            def reset(self):self.policy_reset_count+=1;self.audit_rows=[];self.trace=[]
            def step(self,observation):
                events.append('parent_step');self.trace.append('UNIT_PARENT')
                audit=copy.deepcopy(template);digest=sha256(struct.pack('<4f',8.,-.25,2.,3.)).hexdigest()
                audit.update(raw_model_action=[8.,-.25,2.,3.],raw_action_sha256=digest,
                    parent_converted_action=dict(curvature_1pm=.125,acceleration_mps2=-.25))
                audit['raw_action_receipt']['sha256']=digest;self.audit_rows.append(audit)
                return ModelAction(.125,-.25)
        class Camera(FakePairCamera):
            last_source_rgb_sha256={'road':'a'*64,'wide':'b'*64}
            def capture(self,pose):events.append('capture');ticks[0]+=2;return super().capture(pose)
        lanes=[Straight(0,100,('A','B',0)),Straight(100,200,('B','C',0))]
        for lane,direction in zip(lanes,(1.,-1.)):lane.radius=55.;lane.direction=direction
        blocks=[SimpleNamespace(ID='C',get_config=lambda d=d:{'dir':d}) for d in (0,1)]
        engine=SimpleNamespace(taskMgr=SimpleNamespace(getTasks=lambda:[SimpleNamespace(getName=lambda n=n:n)
            for n in ('igLoop','PSSM.update','update main chase camera')]))
        def no_hide(*args):raise AssertionError('original ego visibility must remain unchanged')
        provider=SimpleNamespace(env=SimpleNamespace(engine=engine,current_map=SimpleNamespace(blocks=blocks),
            vehicle=SimpleNamespace(origin=SimpleNamespace(hide=no_hide))),close=lambda:events.append('close'))
        @contextmanager
        def bins(typ):
            events.append('bin_enter')
            try:yield copy.deepcopy(fixture()['opaque_bin_diagnostic'])
            finally:events.append('bin_exit')
        def clock():return dict(frame_count=10+ticks[0],frame_time_s=ticks[0]*.05,real_time_s=ticks[0]*.1,dt_s=.05)
        policy=m.WorldFramePolicyAdapter(UnitPolicy(),source_action_frame=m.SOURCE_ACTION_FRAME)
        with patch.object(m,'_new_policy',return_value=policy),patch.object(m,'_runtime',return_value=fixture()['runtime']), \
             patch.object(m,'opaque_bin_policy',side_effect=bins),patch.object(m,'_new_provider',side_effect=lambda *a:events.append('provider') or provider), \
             patch.object(m,'configure_sampler',return_value=fixture()['sampler_configuration']),patch.object(m,'select_native_curve_lanes',return_value=lanes), \
             patch.object(m,'_new_camera',return_value=Camera()),patch.object(m.base,'clock_sample',side_effect=clock):
            d=m.native_trial(model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),seed=20261109,
                scene='s_curve_left_right',repeat=0,request_uuid='a'*32)
        self.assertEqual(events.count('capture'),12);self.assertEqual(events.count('parent_step'),12)
        self.assertEqual(d['policy_reset_count'],2);self.assertEqual(d['adapter_reset_calls'],1)
        self.assertEqual(d['frames'][0]['parent_converted_action']['curvature_1pm'],.125)
        self.assertEqual(d['frames'][0]['desired_curvature_1pm'],-.125)
        self.assertLess(d['frames'][-1]['world_y_m'],0.);self.assertFalse(d['official_model_execution'])
        self.assertEqual(len(d['bridge_receipts']),12);self.assertTrue(d['provider_closed'])
        self.assertLess(events.index('bin_enter'),events.index('provider'));self.assertLess(events.index('close'),events.index('bin_exit'))

    def test_source_pins_checked_before_factory_and_exact_inner_class_required(self):
        m=module(self);self.assertEqual(len(m.verify_source_bindings()),7)
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'bigbench/onnx_policy.py';path.parent.mkdir();path.write_text('UNIT_CHANGED_SOURCE')
            with self.assertRaisesRegex(ValueError,'source binding changed'):m.verify_source_bindings(tmp)
        with patch.object(m,'verify_source_bindings',side_effect=ValueError('changed source')), \
             patch.object(m.base,'_new_policy',side_effect=AssertionError('ORT factory forbidden')):
            with self.assertRaisesRegex(ValueError,'changed source'):m._new_policy(Path('UNIT_NOT_WEIGHTS'),Path('model_specs/md-v3.json'))
        with patch.object(m.base,'_new_policy',return_value=object()):
            with self.assertRaises(ValueError):m._new_policy(Path('UNIT_NOT_WEIGHTS'),Path('model_specs/md-v3.json'))

    def test_full_new_protocol_works_without_legacy_validators_and_all_four_regenerate(self):
        m=module(self)
        with patch.object(m.base,'validate_trial',side_effect=AssertionError('legacy validator forbidden')), \
             patch.object(m.legacy,'validate_trial',side_effect=AssertionError('legacy expansion validator forbidden')):
            m.validate_trial(fixture(),20261109,'s_curve_left_right',0)
            with TemporaryDirectory() as tmp:
                root=Path(tmp);build(root,m);d=m.aggregate_cases(root)
                self.assertTrue(d['world_frame_all_four_cases_passed']);self.assertEqual(d['actual_onnx_steps'],96)
                self.assertEqual(d['independent_process_count'],8);self.assertFalse(d['original_mdv3_gate_passed'])
                d['actual_onnx_steps']=95;(root/'aggregate_summary.json').write_text(json.dumps(d))
                with self.assertRaises(ValueError):m.aggregate_cases(root)

    def test_bridge_parent_world_clock_state_source_and_full_counts_fail_closed(self):
        m=module(self)
        for change in ('bridge','parent','world','state','clock','pins','frame','partial','outer','reset','label','capture_hash','geometry'):
            d=fixture();row=d['frames'][11]
            if change=='bridge':d['bridge_receipts'][11]['body_rotation'][1][1]=1.
            elif change=='parent':d['inference_audit_rows'][11]['parent_converted_action']['curvature_1pm']=.2
            elif change=='world':row['desired_curvature_1pm']=.2
            elif change=='state':del d['inference_audit_rows'][11]['named_state_receipts']['state_feat_q']
            elif change=='clock':d['capture_audit_rows'][11]['global_clock_frame_count_delta']=1
            elif change=='pins':d['source_bindings']['bigbench/onnx_policy.py']='a'*64
            elif change=='frame':d['action_basis']['source_action_frame']='WORLD_FLU'
            elif change=='partial':d['frames'].pop();d['completed_steps']=11;d['status']='FAILED_OR_INCOMPLETE';d['error']='LaneTruthError: boundary'
            elif change=='outer':d['episode_provenance']['outer_lifecycle_error']='RuntimeError: close'
            elif change=='reset':d['adapter_reset_calls']=2
            elif change=='label':d['trial_evidence']='UNMODIFIED_METADRIVE_NEW_FRAME_OFFICIAL_ONNX_DIAGNOSTIC'
            elif change=='geometry':d['native_geometry']['blocks'][0]['id']='r'
            else:row['source_road_rgb_sha256']='f'*64
            with self.subTest(change=change):
                with self.assertRaises(ValueError):m.validate_trial(d,20261109,'s_curve_left_right',0)
        a,b=fixture(repeat=0),fixture(repeat=1)
        for location in (b['frames'][6]['named_state_receipts'],b['inference_audit_rows'][6]['named_state_receipts']):
            location['state_feat_q']['sha256']='f'*64
        result=m.compare_trials(a,b,20261109,'s_curve_left_right')
        self.assertFalse(result['world_frame_exact_gate_passed']);self.assertEqual(result['first_diverging_step'],7)

    def test_raw_first_keeps_failed_dangling_records_and_tuple_shapes(self):
        m=module(self)
        for invalid in (False,True):
            d=fixture();d['initial_state_receipts']['state_img_q']['shape']=tuple(d['initial_state_receipts']['state_img_q']['shape'])
            if invalid:d['frames'].pop();d['completed_steps']=11;d['status']='FAILED_OR_INCOMPLETE';d['error']='LaneTruthError: boundary'
            with TemporaryDirectory() as tmp:
                out=Path(tmp)/'raw.json'
                with patch.object(m,'native_trial',return_value=d):
                    status=m.main(['--mode','native','--seed','20261109','--scene','s_curve_left_right','--repeat','0',
                        '--request-uuid',d['world_frame_trial']['request_uuid'],'--model','UNIT_NOT_WEIGHTS','--spec','model_specs/md-v3.json','--out',str(out)])
                self.assertEqual(status,2 if invalid else 0)
                raw=json.loads(out.read_text());self.assertEqual(len(raw['capture_audit_rows']),12);self.assertEqual(len(raw['bridge_receipts']),12)

    def test_launcher_only_accepts_complete_zero_five_nonce_and_keeps_other_status(self):
        m=module(self)
        for status in (0,5,2,7):
            with TemporaryDirectory() as tmp:
                out=Path(tmp)/'raw.json';statuses=[]
                def child(command,**kwargs):
                    d=fixture();d['world_frame_trial']['request_uuid']=command[command.index('--request-uuid')+1]
                    out.write_text(json.dumps(d));return SimpleNamespace(returncode=status)
                with patch.object(m.subprocess,'run',side_effect=child):
                    code=m.launch_trial(model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),seed=20261109,
                        scene='s_curve_left_right',repeat=0,out=out,status_receipt=statuses)
                self.assertEqual(code,0 if status in (0,5) else status);self.assertEqual(statuses,[status])
                with self.assertRaises(ValueError):m.launch_trial(model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),
                    seed=20261109,scene='s_curve_left_right',repeat=0,out=out)

    def test_zero_five_need_full_matching_nonce_and_failed_case_ledger_is_retained(self):
        m=module(self)
        for status in (0,5):
            for defect in ('missing','nonce','partial'):
                with TemporaryDirectory() as tmp:
                    out=Path(tmp)/'raw.json'
                    def child(command,**kwargs):
                        if defect!='missing':
                            d=fixture();d['world_frame_trial']['request_uuid']=('f'*32 if defect=='nonce' else command[command.index('--request-uuid')+1])
                            if defect=='partial':d['frames'].pop()
                            out.write_text(json.dumps(d))
                        return SimpleNamespace(returncode=status)
                    with patch.object(m.subprocess,'run',side_effect=child):
                        with self.assertRaises((ValueError,FileNotFoundError)):
                            m.launch_trial(model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),seed=20261109,
                                           scene='s_curve_left_right',repeat=0,out=out)
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/'matrix';calls=[]
            def child(command,**kwargs):
                calls.append(command);d=fixture();d['frames'].pop();d['completed_steps']=11
                Path(command[command.index('--out')+1]).write_text(json.dumps(d));return SimpleNamespace(returncode=2)
            with patch.object(m.subprocess,'run',side_effect=child):
                status=m.run_case(root=root,model=Path('UNIT_NOT_WEIGHTS'),spec=Path('model_specs/md-v3.json'),seed=20261109,scene='s_curve_left_right')
            self.assertEqual(status,2);self.assertEqual(len(calls),1)
            folder=root/'seed-20261109'/'s_curve_left_right';ledger=json.loads((folder/'execution_ledger.json').read_text())
            self.assertEqual(ledger['entries'][0]['native_exit_status'],2)
            self.assertEqual(ledger['entries'][0]['accepted_exit_status'],2)
            self.assertTrue((folder/'run_0.json').exists());self.assertFalse((folder/'case_comparison.json').exists())

    def test_global_nonce_uuid_pid_and_stale_case_proofs_reject(self):
        m=module(self)
        for key in ('process_uuid','request_uuid','stale'):
            with TemporaryDirectory() as tmp:
                root=Path(tmp);build(root,m);seed=20261110;scene='s_curve_right_left';folder=root/f'seed-{seed}'/scene
                if key=='stale':
                    path=folder/'case_comparison.json';d=json.loads(path.read_text());d['world_frame_exact_gate_passed']=False;path.write_text(json.dumps(d))
                else:
                    path=folder/'run_0.json';d=json.loads(path.read_text());other=fixture()
                    value=other['process_uuid'] if key=='process_uuid' else other['world_frame_trial']['request_uuid']
                    if key=='process_uuid':d[key]=value
                    else:d['world_frame_trial'][key]=value
                    path.write_text(json.dumps(d));path=folder/'execution_ledger.json';ledger=json.loads(path.read_text())
                    ledger['entries'][0][key]=value;path.write_text(json.dumps(ledger))
                    (folder/'case_comparison.json').write_text(json.dumps(m.compare_case(root,seed,scene)))
                with self.assertRaises(ValueError):m.aggregate_cases(root)
        a,b=fixture(repeat=0),fixture(repeat=1);b['process_id']=a['process_id']
        with self.assertRaises(ValueError):m.compare_trials(a,b,20261109,'s_curve_left_right')


if __name__=='__main__':unittest.main()
