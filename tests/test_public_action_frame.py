"""CPU-only public binding tests; synthetic identities are not official weight evidence."""
from contextlib import ExitStack, redirect_stdout
import ast
from dataclasses import FrozenInstanceError, asdict
from hashlib import sha256
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
import weakref
from unittest.mock import patch

from bigbench.kinematics import AgentState, ModelAction, step_ideal
from bigbench.onnx_policy import ModelTiming

ROOT=Path(__file__).resolve().parents[1]
PINS={
    'bigbench/onnx_policy.py':'d983d5950296620a6ae89c88993829b4d2cebd35a6fd0e9046a980f75c9142da',
    'scripts/native_mdv3_repeat_trial.py':'ddaf0510a775c3a44c908bb4dedf4879ae88bfcb80e1f2d022a8b513a4f42427',
    'scripts/native_mdv3_renderer_candidate.py':'5a9058102004e2f5eaa4c9dcab4c24d97a9d42702b7a9e7c248c4f576a30d22e',
    'scripts/native_mdv3_candidate_expansion.py':'d86b3be67c8ac3dee31f0bf9928014d3880c8c55a6cd829bb3c46c464d16b42c',
    'bigbench/kinematics.py':'58c92e9a5b584932cfe73ebbf7de888f2595e88ceacdabe9a457a78fa77bb70a',
    'bigbench/native_model_campaign.py':'0bcb4ca73e1404a7164be1c879a200eeff5ca41e47e3035301d40fd173000bad',
    'bigbench/metadrive_camera.py':'1c5661e6c9eea6445ebe55cb246e6b48d3384dd5a731353ba3f1a45599e338f9',
    'bigbench/model_world_frame.py':'275f5359a975d9e152f61df74cd57803e1322e1f9618784f0993e780516ec092',
    'scripts/native_mdv3_world_frame.py':'cd57c4d407e96459921ca61c78eb81ef55851cd4fafa92ca917bbc7f494a3e38'}


def api():return importlib.import_module('bigbench.public_action_frame')


def files(folder):
    model=folder/'unit.onnx';model.write_bytes(b'CPU fake constructor fixture, not ONNX')
    spec=json.loads((ROOT/'model_specs/md-v3.json').read_text())
    spec.update(sha256=sha256(model.read_bytes()).hexdigest(),nbytes=model.stat().st_size)
    manifest=folder/'unit.json';manifest.write_text(json.dumps(spec))
    return model,manifest


class Parent:
    is_mock=False
    needs_dual_camera=True
    _injected_session=True
    evidence_class='UNIT_PARENT_NOT_OFFICIAL_INFERENCE'
    name='unit-parent'
    def __init__(self):
        self.reset_calls=0;self.step_calls=[];self.trace=[];self.state={'unchanged':object()}
        self.last_model_outputs={'action':[1.,-.2,3.,4.]};self.session=object()
        self.contract=SimpleNamespace(sha256='a'*64)
    def reset(self):self.reset_calls+=1;self.trace.clear()
    def step(self,observation):
        self.step_calls.append(observation)
        action=ModelAction(getattr(observation,'curvature',.02),-.2)
        self.trace.append(ModelTiming(len(self.trace),1.,action.curvature_1pm*64.,-.2,action.curvature_1pm,123))
        return action


class PublicBindingTests(unittest.TestCase):
    def test_unknown_identity_with_official_byte_count_is_still_a_user_declaration(self):
        m=api();identity=m.ModelIdentity('synthetic.onnx','synthetic.json','1'*64,m.OFFICIAL_MODEL_NBYTES,'2'*64)
        for declaration in ('model-frd','world-flu'):
            resolution=m._resolve_action_frame(identity,declaration)
            self.assertEqual(resolution.provenance,'USER_DECLARATION')
            self.assertEqual(resolution.rotation_applied,declaration=='model-frd')
        with self.assertRaisesRegex(ValueError,'declaration'):m._resolve_action_frame(identity,'auto')

    def test_synthetic_identity_resolution_table_and_partial_anchors_fail_closed(self):
        m=api()
        identity=m.ModelIdentity('synthetic.onnx','synthetic.json',m.OFFICIAL_MODEL_SHA256,m.OFFICIAL_MODEL_NBYTES,m.OFFICIAL_SPEC_SHA256)
        for declaration in ('auto','model-frd'):
            resolved=m._resolve_action_frame(identity,declaration)
            self.assertEqual(resolved.parent_action_frame,'MODEL_BODY_FRD');self.assertTrue(resolved.rotation_applied)
            self.assertEqual(resolved.provenance,'VERIFIED_OFFICIAL_IDENTITY')
            with self.assertRaises(FrozenInstanceError):resolved.provenance='changed'
        with self.assertRaisesRegex(ValueError,'conflict'):m._resolve_action_frame(identity,'world-flu')
        for mask in range(1,7):
            if mask==2:continue  # A coincident byte count alone is not an official identity anchor.
            partial=m.ModelIdentity('unit.onnx','unit.json',m.OFFICIAL_MODEL_SHA256 if mask&1 else '1'*64,
                m.OFFICIAL_MODEL_NBYTES if mask&2 else 8,m.OFFICIAL_SPEC_SHA256 if mask&4 else '2'*64)
            for declaration in ('auto','model-frd','world-flu'):
                with self.subTest(mask=mask,declaration=declaration):
                    with self.assertRaisesRegex(ValueError,'identity conflict'):m._resolve_action_frame(partial,declaration)

    def test_unknown_auto_and_invalid_declarations_fail_before_constructor(self):
        m=api()
        with TemporaryDirectory() as tmp:
            model,spec=files(Path(tmp))
            with patch.object(m,'_construct_policy') as constructor:
                for declaration in ('auto','legacy',None,[],1):
                    with self.subTest(declaration=declaration):
                        with self.assertRaises(ValueError):m.create_public_onnx_policy(model,spec,model_action_frame=declaration)
                constructor.assert_not_called()

    def test_actual_file_manifest_and_spec_bytes_rechecked_after_preflight(self):
        m=api()
        with TemporaryDirectory() as tmp:
            model,spec=files(Path(tmp));resolved=m.preflight_public_onnx_policy(model,spec,model_action_frame='model-frd')
            self.assertEqual(resolved.identity.model_sha256,sha256(model.read_bytes()).hexdigest())
            self.assertEqual(resolved.identity.spec_sha256,sha256(spec.read_bytes()).hexdigest())
            model.write_bytes(b'X'*model.stat().st_size)
            with patch.object(m,'_construct_policy') as constructor:
                with self.assertRaisesRegex(ValueError,'SHA256'):m.create_public_onnx_policy(model,spec,model_action_frame='model-frd')
                constructor.assert_not_called()

    def test_invalid_model_or_contract_fails_before_constructor(self):
        m=api()
        for fault in ('size','manifest-sha','shape','json'):
            with self.subTest(fault=fault),TemporaryDirectory() as tmp:
                model,spec=files(Path(tmp));data=json.loads(spec.read_text())
                if fault=='size':model.write_bytes(b'too short')
                elif fault=='manifest-sha':data['sha256']='f'*64;spec.write_text(json.dumps(data))
                elif fault=='shape':data['input_shapes']['new_img']=[1,2];spec.write_text(json.dumps(data))
                else:spec.write_text('{')
                with patch.object(m,'_construct_policy') as constructor:
                    with self.assertRaises(ValueError):m.create_public_onnx_policy(model,spec,model_action_frame='world-flu')
                    constructor.assert_not_called()

    def test_composition_once_preserves_observation_raw_state_trace_and_runtime_flags(self):
        m=api()
        with TemporaryDirectory() as tmp:
            model,spec=files(Path(tmp));inner=Parent()
            with patch.object(m,'_construct_policy',return_value=inner) as constructor:
                binding=m.create_public_onnx_policy(model,spec,model_action_frame='model-frd',traffic_is_rhd=True,
                    lat_action_t_s=.2,long_action_t_s=.3)
            constructor.assert_called_once_with(model,spec,traffic_is_rhd=True,lat_action_t_s=.2,long_action_t_s=.3)
            policy=binding.policy;self.assertEqual(inner.reset_calls,0)
            self.assertIs(policy.state,inner.state);self.assertIs(policy.last_model_outputs,inner.last_model_outputs)
            self.assertIs(policy.session,inner.session);self.assertTrue(policy._injected_session)
            self.assertFalse(policy.is_mock);self.assertEqual(policy.evidence_class,inner.evidence_class)
            policy.reset();self.assertEqual(inner.reset_calls,1)
            for curvature in (-.02,0.,.02):
                obs=SimpleNamespace(curvature=curvature,frame=object(),wide_frame=object())
                action=policy.step(obs);self.assertIs(inner.step_calls[-1],obs)
                self.assertEqual(action,ModelAction(-curvature,-.2));self.assertEqual(inner.trace[-1].curvature_1pm,curvature)
                for heading in (0.,.7):
                    after=step_ideal(AgentState(0.,0.,0.,heading,8.),action,.05,speed_override=8.)
                    self.assertAlmostEqual(after.heading,heading-.05*8.*curvature)
            receipt=binding.receipt();self.assertEqual(len(receipt['bridge_receipts']),3)
            self.assertEqual(receipt['parent_trace'],[asdict(row) for row in inner.trace])
            self.assertEqual(receipt['parent_trace_count'],3);self.assertIsNone(receipt['total_executed_model_calls'])
            self.assertEqual(receipt['provenance'],'USER_DECLARATION');json.dumps(receipt,allow_nan=False)

    def test_declared_world_passes_same_parent_action_and_double_binding_rejects(self):
        m=api()
        with TemporaryDirectory() as tmp:
            model,spec=files(Path(tmp));inner=Parent()
            with patch.object(m,'_construct_policy',return_value=inner):
                binding=m.create_public_onnx_policy(model,spec,model_action_frame='world-flu')
            self.assertIs(binding.policy,inner);self.assertEqual(binding.policy.step(object()),ModelAction(.02,-.2))
            self.assertEqual(binding.receipt()['bridge_receipts'],[]);self.assertFalse(binding.receipt()['rotation_applied'])
            for marker,value in (('world_frame_adapter_applied',True),('applied_action_frame','INTEGRATOR_BODY_FLU_WORLD_CCW')):
                inner=Parent();setattr(inner,marker,value)
                with patch.object(m,'_construct_policy',return_value=inner):
                    for declaration in ('model-frd','world-flu'):
                        with self.assertRaisesRegex(ValueError,'already|repeated'):m.create_public_onnx_policy(model,spec,model_action_frame=declaration)

    def test_failed_parent_validation_retains_dangling_trace_without_invented_execution_count(self):
        m=api();inner=Parent()
        with TemporaryDirectory() as tmp:
            model,spec=files(Path(tmp))
            with patch.object(m,'_construct_policy',return_value=inner):binding=m.create_public_onnx_policy(model,spec,model_action_frame='model-frd')
            def invalid_return(observation):Parent.step(inner,observation);return object()
            with patch.object(inner,'step',side_effect=invalid_return):
                with self.assertRaises(ValueError):binding.policy.step(object())
            receipt=binding.receipt()
            self.assertEqual(receipt['parent_trace_count'],1);self.assertEqual(receipt['bridge_receipts'],[])
            self.assertIsNone(receipt['total_executed_model_calls']);json.dumps(receipt,allow_nan=False)

    def test_public_import_is_light_and_exposes_no_constructor_bypass(self):
        import inspect
        m=api();params=inspect.signature(m.create_public_onnx_policy).parameters
        self.assertEqual(set(params),{'model_path','spec_path','model_action_frame','traffic_is_rhd','lat_action_t_s','long_action_t_s'})
        code='import sys;import bigbench.public_action_frame;assert not any(x in sys.modules for x in ("numpy","onnxruntime","panda3d.core","bigbench.onnx_policy","bigbench.runner","bigbench.metadrive_camera"))'
        subprocess.run([sys.executable,'-c',code],cwd=ROOT,check=True,capture_output=True,text=True,timeout=20)

    def test_nine_pins_and_static_diagnostic_import_closure_stay_isolated(self):
        queue=[name[:-3].replace('/','.') for name in PINS];seen=set()
        while queue:
            name=queue.pop()
            if name in seen:continue
            path=ROOT/(name.replace('.','/')+'.py')
            if not path.is_file():continue
            seen.add(name)
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node,ast.Import):queue.extend(alias.name for alias in node.names)
                elif isinstance(node,ast.ImportFrom):
                    parent='.'.join(name.split('.')[:-node.level]) if node.level else ''
                    target='.'.join(x for x in (parent,node.module) if x)
                    queue.append(target)
                    queue.extend(target+'.'+alias.name for alias in node.names)
        self.assertNotIn('bigbench.public_action_frame',seen)
        for name,expected in PINS.items():self.assertEqual(sha256((ROOT/name).read_bytes()).hexdigest(),expected,name)
        code='''
import importlib.abc,sys
class Forbidden(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname in ('bigbench.public_action_frame','onnxruntime','panda3d.core'):
   raise AssertionError('forbidden eager import '+fullname)
sys.meta_path.insert(0,Forbidden())
from bigbench.onnx_policy import OnnxBigModelPolicy
from bigbench.metadrive_camera import NativeMetaDriveProvider
def forbidden(*args,**kwargs):raise AssertionError('constructor during pure diagnostic import')
OnnxBigModelPolicy.__init__=forbidden
NativeMetaDriveProvider.__init__=forbidden
import scripts.native_mdv3_world_frame
import scripts.native_mdv3_world_frame_expansion
assert 'bigbench.public_action_frame' not in sys.modules
'''
        subprocess.run([sys.executable,'-c',code],cwd=ROOT,check=True,capture_output=True,text=True,timeout=20)


class PublicEntrypointTests(unittest.TestCase):
    def test_repeat_commands_release_previous_policy_before_next_constructor(self):
        m=api()
        for name in ('scripts.compare_native_onnx','scripts.run_same_model_repeat'):
            entry=importlib.import_module(name);previous=[];constructed=[0]
            def constructor(*args,**kwargs):
                self.assertTrue(all(ref() is None for ref in previous),
                    'previous binding must release its policy before constructing the next session')
                inner=Parent();previous.append(weakref.ref(inner));constructed[0]+=1;return inner
            def episode(policy,spec,**kwargs):
                policy.reset();policy.step(object())
                return dict(status='DIAGNOSTIC_EXECUTED',model_sha256=policy.contract.sha256,completed_steps=1)
            with self.subTest(command=name),TemporaryDirectory() as tmp:
                root=Path(tmp);model,spec=files(root)
                with ExitStack() as stack:
                    # Plain functions avoid Mock.call_args retaining the policy under test.
                    stack.enter_context(patch.object(m,'_construct_policy',new=constructor))
                    stack.enter_context(patch.object(entry,'run_native_episode',new=episode))
                    stack.enter_context(patch('bigbench.reproducibility.compare_repeat_receipts',return_value=dict(
                        status='SYNTHETIC_REPEATED_DIAGNOSTIC_MATCH',max_pose_disagreement_m=0.,frame_hashes_identical=True)))
                    stack.enter_context(redirect_stdout(io.StringIO()))
                    if name.endswith('compare_native_onnx'):
                        stack.enter_context(patch.object(entry,'compare_episode_receipts',return_value={'first_camera_sha_equal':True}))
                        stack.enter_context(patch('bigbench.dashboard.save_diagnostic_dashboard'))
                        argv=['--first-model',str(model),'--first-spec',str(spec),'--first-model-action-frame','model-frd',
                            '--second-model',str(model),'--second-spec',str(spec),'--second-model-action-frame','world-flu','--repeat-first']
                    else:
                        stack.enter_context(patch.object(entry,'compare_repeat_receipts',return_value=dict(
                            status='SYNTHETIC_REPEATED_DIAGNOSTIC_MATCH',max_pose_disagreement_m=0.,frame_hashes_identical=True)))
                        argv=['--model',str(model),'--spec',str(spec),'--model-action-frame','model-frd']
                    self.assertEqual(entry.main(argv+['--out',str(root/'out')]),0)
                self.assertEqual(constructed[0],3 if name.endswith('compare_native_onnx') else 2)
                self.assertTrue(all(ref() is None for ref in previous),'final policy/binding must also be released')

    def test_cli_and_repeat_default_auto_reject_unknown_before_episode(self):
        m=api()
        with TemporaryDirectory() as tmp:
            root=Path(tmp);model,spec=files(root)
            for name,options,loop in (
                ('bigbench.cli',['run-onnx','--accept-uncalibrated-vision'],'run_episode'),
                ('scripts.run_same_model_repeat',[],'run_native_episode')):
                entry=importlib.import_module(name)
                with patch.object(m,'_construct_policy') as constructor,patch.object(entry,loop) as episode:
                    with self.assertRaisesRegex(ValueError,'declaration'):
                        entry.main(options+['--model',str(model),'--spec',str(spec),'--out',str(root/name)])
                    constructor.assert_not_called();episode.assert_not_called()

    def test_cli_episode_exception_retains_error_parent_trace_and_bridge(self):
        m=api();entry=importlib.import_module('bigbench.cli')
        def failure(scenario,policy,**kwargs):policy.reset();policy.step(object());raise RuntimeError('UNIT after parent inference')
        with TemporaryDirectory() as tmp:
            root=Path(tmp);model,spec=files(root);out=root/'out'
            with patch.object(m,'_construct_policy',return_value=Parent()),patch.object(entry,'run_episode',side_effect=failure):
                with self.assertRaisesRegex(RuntimeError,'UNIT after parent inference'):
                    entry.main(['run-onnx','--model',str(model),'--spec',str(spec),'--model-action-frame','model-frd',
                        '--accept-uncalibrated-vision','--out',str(out)])
            receipt=json.loads((out/'action_frame_binding.json').read_text())
            self.assertEqual(receipt['parent_trace_count'],1);self.assertEqual(receipt['bridge_receipt_count'],1)
            self.assertIn('UNIT after parent inference',receipt['episode_error'])
            self.assertIsNone(receipt['total_executed_model_calls'])

    def test_optical_default_no_model_keeps_two_existing_pose_captures(self):
        entry=importlib.import_module('scripts.metadrive_optical_check');m=api()
        from bigbench.camera import RGBFrame
        import numpy as np
        frames=[SimpleNamespace(pair=SimpleNamespace(road=RGBFrame(2,2,bytes([v])*12),wide=RGBFrame(2,2,bytes([v+1])*12)),audit={}) for v in (1,3)]
        rig=SimpleNamespace(capture=unittest.mock.Mock(side_effect=frames),close=unittest.mock.Mock())
        packed=[np.zeros((2,6,128,256),np.uint8),np.ones((2,6,128,256),np.uint8)];packed[0][1]=2
        with TemporaryDirectory() as tmp,patch.object(entry,'NativeMetaDriveProvider') as provider, \
                patch.object(entry,'MetaDriveOpticalRig',return_value=rig),patch.object(entry,'camera_pair_to_model',side_effect=packed), \
                patch.object(m,'_construct_policy') as constructor,redirect_stdout(io.StringIO()):
            self.assertEqual(entry.main(['--out',tmp]),0);constructor.assert_not_called()
            provider.assert_called_once_with(seed=20261109,source_width=964,source_height=604)
            self.assertEqual([call.args[0] for call in rig.capture.call_args_list],[AgentState(0,0,0,0,0),AgentState(.05,3,.5,.01,0)])
            rig.close.assert_called_once();self.assertFalse((Path(tmp)/'action_frame_binding.json').exists())

    def test_optical_model_failure_preserves_dangling_evidence_and_closes(self):
        entry=importlib.import_module('scripts.metadrive_optical_check');m=api();rig=SimpleNamespace(close=unittest.mock.Mock())
        def failed_probe(policy,actual_rig,**kwargs):
            self.assertIs(actual_rig,rig);policy.reset();self.assertEqual(policy.step(object()).curvature_1pm,-.02)
            raise RuntimeError('UNIT optical post-inference failure')
        with TemporaryDirectory() as tmp:
            root=Path(tmp);model,spec=files(root);out=root/'out'
            with patch.object(m,'_construct_policy',return_value=Parent()),patch.object(entry,'NativeMetaDriveProvider'), \
                    patch.object(entry,'MetaDriveOpticalRig',return_value=rig),patch.object(entry,'probe_model_with_metadrive',side_effect=failed_probe):
                with self.assertRaisesRegex(RuntimeError,'UNIT optical post-inference'):
                    entry.main(['--model',str(model),'--spec',str(spec),'--model-action-frame','model-frd','--out',str(out)])
            receipt=json.loads((out/'action_frame_binding.json').read_text())
            self.assertEqual(receipt['parent_trace_count'],1);self.assertEqual(receipt['bridge_receipt_count'],1)
            self.assertIn('UNIT optical post-inference',receipt['episode_error']);rig.close.assert_called_once()

    def test_cli_real_schematic_loop_preserves_parent_csv_and_applies_world_action(self):
        m=api();entry=importlib.import_module('bigbench.cli');inner=Parent()
        with TemporaryDirectory() as tmp:
            root=Path(tmp);model,spec=files(root);out=root/'out'
            with patch.object(m,'_construct_policy',return_value=inner) as constructor,redirect_stdout(io.StringIO()):
                self.assertEqual(entry.main(['run-onnx','--model',str(model),'--spec',str(spec),
                    '--model-action-frame','model-frd','--accept-uncalibrated-vision','--rhd','--lat-action-t','.2',
                    '--long-action-t','.3','--integrated','--steps','2','--out',str(out)]),0)
            constructor.assert_called_once_with(model,spec,traffic_is_rhd=True,lat_action_t_s=.2,long_action_t_s=.3)
            import csv
            with (out/'model_inference.csv').open() as stream:
                reader=csv.DictReader(stream);rows=list(reader)
                self.assertEqual(reader.fieldnames,list(asdict(inner.trace[0])))
            self.assertEqual([float(row['curvature_1pm']) for row in rows],[.02,.02])
            with (out/'frames.csv').open() as stream:frames=list(csv.DictReader(stream))
            self.assertEqual([float(row['desired_curvature_1pm']) for row in frames],[-.02,-.02])
            report=json.loads((out/'summary.json').read_text())
            self.assertEqual(report['public_action_frame']['provenance'],'USER_DECLARATION')
            self.assertEqual(inner.reset_calls,1);self.assertEqual(len(inner.step_calls),2)

    def test_compare_sequential_construction_distinct_declarations_and_repeat_first(self):
        m=api();entry=importlib.import_module('scripts.compare_native_onnx');events=[];parents=[];actions=[]
        real_preflight=entry.preflight_public_onnx_policy
        def preflight(model,spec,**kwargs):events.append('preflight');return real_preflight(model,spec,**kwargs)
        def constructor(*args,**kwargs):events.append('construct');inner=Parent();parents.append(inner);return inner
        def episode(policy,spec,**kwargs):
            events.append('episode');policy.reset();actions.append(policy.step(object()).curvature_1pm)
            return dict(status='DIAGNOSTIC_EXECUTED',model_sha256=policy.contract.sha256,completed_steps=1)
        with TemporaryDirectory() as tmp:
            root=Path(tmp);model,spec=files(root);out=root/'out'
            with ExitStack() as stack:
                stack.enter_context(patch.object(entry,'preflight_public_onnx_policy',side_effect=preflight))
                stack.enter_context(patch.object(m,'_construct_policy',side_effect=constructor))
                stack.enter_context(patch.object(entry,'run_native_episode',side_effect=episode))
                stack.enter_context(patch.object(entry,'compare_episode_receipts',return_value={'first_camera_sha_equal':True}))
                stack.enter_context(patch('bigbench.dashboard.save_diagnostic_dashboard'))
                stack.enter_context(patch('bigbench.reproducibility.compare_repeat_receipts',return_value={'status':'UNIT_ONLY'}))
                stack.enter_context(redirect_stdout(io.StringIO()))
                entry.main(['--first-model',str(model),'--first-spec',str(spec),'--first-model-action-frame','model-frd',
                    '--second-model',str(model),'--second-spec',str(spec),'--second-model-action-frame','world-flu',
                    '--repeat-first','--out',str(out)])
            self.assertEqual(events,['preflight','preflight','construct','episode','construct','episode','construct','episode'])
            self.assertEqual(actions,[-.02,.02,-.02]);self.assertEqual(len({id(x) for x in parents}),3)
            receipts=[json.loads((out/name).read_text())['public_action_frame'] for name in ('model_a.json','model_b.json','repeat_model_a.json')]
            self.assertEqual([r['rotation_applied'] for r in receipts],[True,False,True])

    def test_compare_factory_rechecks_file_changed_after_both_preflights(self):
        m=api();entry=importlib.import_module('scripts.compare_native_onnx');calls=[];real=entry.preflight_public_onnx_policy
        with TemporaryDirectory() as tmp:
            root=Path(tmp);model,spec=files(root)
            def preflight(*args,**kwargs):
                result=real(*args,**kwargs);calls.append(result)
                if len(calls)==2:model.write_bytes(b'X'*model.stat().st_size)
                return result
            with patch.object(entry,'preflight_public_onnx_policy',side_effect=preflight), \
                    patch.object(m,'_construct_policy') as constructor,patch.object(entry,'run_native_episode') as episode:
                with self.assertRaisesRegex(ValueError,'SHA256'):
                    entry.main(['--first-model',str(model),'--first-spec',str(spec),'--first-model-action-frame','model-frd',
                        '--second-model',str(model),'--second-spec',str(spec),'--second-model-action-frame','world-flu','--out',str(root/'out')])
                self.assertEqual(len(calls),2);constructor.assert_not_called();episode.assert_not_called()

    def test_repeat_fresh_bindings_preserve_camera_options_and_failed_dangling_receipt(self):
        m=api();entry=importlib.import_module('scripts.run_same_model_repeat');parents=[];options=[]
        def constructor(*args,**kwargs):inner=Parent();parents.append(inner);return inner
        def episode(policy,spec,**kwargs):
            options.append(kwargs);policy.reset();policy.step(object())
            return dict(status='FAILED_OR_INCOMPLETE',completed_steps=0,error='UNIT truth failure')
        with TemporaryDirectory() as tmp:
            root=Path(tmp);model,spec=files(root);out=root/'out'
            with patch.object(m,'_construct_policy',side_effect=constructor),patch.object(entry,'run_native_episode',side_effect=episode),redirect_stdout(io.StringIO()):
                status=entry.main(['--model',str(model),'--spec',str(spec),'--model-action-frame','model-frd',
                    '--camera-convergence','4','--camera-pixel-tolerance','2','--camera-channel-delta','3','--out',str(out)])
            self.assertEqual(status,2);self.assertEqual(len({id(x) for x in parents}),2)
            self.assertEqual(options,[dict(camera_convergence=4,camera_pixel_tolerance=2,camera_rgb_delta=3)]*2)
            for index in (0,1):
                report=json.loads((out/f'run_{index}.json').read_text());binding=report['public_action_frame']
                self.assertEqual(report['completed_steps'],0);self.assertEqual(binding['parent_trace_count'],1)
                self.assertEqual(binding['bridge_receipt_count'],1);self.assertIsNone(binding['total_executed_model_calls'])

    def test_optical_provider_setup_failure_still_exports_frame_receipt(self):
        m=api();entry=importlib.import_module('scripts.metadrive_optical_check')
        with TemporaryDirectory() as tmp:
            root=Path(tmp);model,spec=files(root);out=root/'out'
            with patch.object(m,'_construct_policy',return_value=Parent()), \
                    patch.object(entry,'NativeMetaDriveProvider',side_effect=RuntimeError('UNIT provider setup')):
                with self.assertRaisesRegex(RuntimeError,'UNIT provider setup'):
                    entry.main(['--model',str(model),'--spec',str(spec),'--model-action-frame','model-frd','--out',str(out)])
            receipt=json.loads((out/'action_frame_binding.json').read_text())
            self.assertEqual(receipt['parent_trace_count'],0);self.assertIsNone(receipt['total_executed_model_calls'])

    def test_compare_preflights_both_before_any_constructor_or_episode(self):
        m=api();entry=importlib.import_module('scripts.compare_native_onnx')
        with TemporaryDirectory() as tmp:
            root=Path(tmp);model,spec=files(root)
            argv=['--first-model',str(model),'--first-spec',str(spec),'--first-model-action-frame','model-frd',
                '--second-model',str(model),'--second-spec',str(spec),'--out',str(root/'out')]
            with patch.object(m,'_construct_policy') as constructor,patch.object(entry,'run_native_episode') as episode:
                with self.assertRaisesRegex(ValueError,'declaration'):entry.main(argv)
                constructor.assert_not_called();episode.assert_not_called()

    def test_optical_unknown_auto_or_model_less_declaration_precedes_provider(self):
        m=api();entry=importlib.import_module('scripts.metadrive_optical_check')
        with TemporaryDirectory() as tmp:
            model,spec=files(Path(tmp))
            with patch.object(m,'_construct_policy') as constructor,patch.object(entry,'NativeMetaDriveProvider') as provider, \
                    patch('bigbench.onnx_policy.OnnxBigModelPolicy',side_effect=AssertionError('bare constructor reached before frame preflight')):
                with self.assertRaisesRegex(ValueError,'declaration'):entry.main(['--model',str(model),'--spec',str(spec)])
                with self.assertRaises(SystemExit):entry.main(['--model-action-frame','world-flu'])
                constructor.assert_not_called();provider.assert_not_called()


if __name__=='__main__':unittest.main()
