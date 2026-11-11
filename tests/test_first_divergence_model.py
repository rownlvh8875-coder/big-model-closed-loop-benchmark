"""CPU contracts for the bounded diagnostic; native/REST/process boundaries only."""
from __future__ import annotations
from dataclasses import asdict
from hashlib import sha256
import importlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import warnings
from unittest.mock import patch
import zipfile
import numpy as np
from bigbench import first_divergence as capture
from bigbench import native_model_campaign as campaign
from bigbench.kinematics import AgentState, ModelAction
from bigbench.policies import ModelObservation
from bigbench.image_adapter import camera_pair_to_model
from test_first_divergence import CopiedBufferCamera, Provider
try:
    model = importlib.import_module('bigbench.first_divergence_model')
except ModuleNotFoundError as exc:
    if exc.name != 'bigbench.first_divergence_model': raise
    model = None


class Parent:
    needs_dual_camera=True
    name='boundary-policy'
    is_mock=False
    def __init__(self):
        self.contract=SimpleNamespace(state_keys=('state_small',),input_shapes={'state_small':(2,),
            'desire':(8,), 'traffic_convention':(1,2),'action_t':(1,2)},
            output_slices={'action':(0,4),'plan':(4,10)})
        self._types={'state_small':np.dtype('float32')}
        self.traffic_convention=np.array([[1,0]],np.float32)
        self.action_t=np.array([[.175,.175]],np.float32)
        self.state={'state_small':np.array([0,1],np.float32)}
        self.trace=[]; self.resets=0; self.observations=[]
        self.last_input_image_sha256=None; self.last_model_outputs=None
    def reset(self): self.resets+=1
    def step(self,observation):
        self.observations.append(observation)
        self.state['state_small']+=2
        self.last_model_outputs={'action':np.array([2,3,4,5],np.float32),
                                 'plan':np.arange(6,dtype=np.float32)}
        self.last_input_image_sha256=sha256(camera_pair_to_model(observation.frame,observation.wide_frame).tobytes()).hexdigest()
        self.trace.append(SimpleNamespace(elapsed_ms=1.25))
        return ModelAction(-.03125,3.)


class ObserverTests(unittest.TestCase):
    def setUp(self): self.assertIsNotNone(model,'Task2 model observer must exist')
    def observation(self,collector):
        with patch.object(campaign,'NativeWorldCamera',CopiedBufferCamera), capture.capture_scope(collector.arm,collector):
            pair=campaign.NativeWorldCamera(Provider()).capture(AgentState(0,0,0,0,8))
        return ModelObservation(pair.road,8.,0.,wide_frame=pair.wide)
    def test_forwarding_preserves_observation_once_and_parent_graph_time(self):
        c=capture.CaptureCollector('proxy',max_captures=24); p=Parent(); wrapper=model.PolicyObserver(p,c)
        wrapper.reset(); o=self.observation(c); action=wrapper.step(o)
        self.assertEqual(p.resets,1); self.assertEqual(len(p.observations),1)
        self.assertIs(p.observations[0],o); self.assertEqual(action,ModelAction(-.03125,3.))
        self.assertEqual(p.trace[0].elapsed_ms,1.25)
        self.assertEqual(c.payload_bytes,0); self.assertEqual(wrapper.arrays,[])
        self.assertEqual(wrapper.rows[0]['actual_input_sha256'],p.last_input_image_sha256)
    def test_retention_prepost_and_outputs_are_independent_readonly_and_budgeted(self):
        c=capture.CaptureCollector('retention',max_captures=24); p=Parent(); w=model.PolicyObserver(p,c)
        o=self.observation(c); w.step(o)
        row=w.arrays[0]
        self.assertEqual(row['pre_state']['state_small'].tolist(),[0,1])
        self.assertEqual(row['post_state']['state_small'].tolist(),[2,3])
        self.assertEqual(row['raw4'].tolist(),[2,3,4,5]); self.assertEqual(row['plan'].shape,(6,))
        p.state['state_small'][:]=99; p.last_model_outputs['action'][:]=99
        self.assertEqual(row['post_state']['state_small'].tolist(),[2,3])
        self.assertEqual(row['raw4'][0],2)
        self.assertFalse(row['raw4'].flags.writeable)
        self.assertGreaterEqual(c.payload_bytes,sum(a.nbytes for group in (row['pre_state'],row['post_state'],row['fixed_inputs']) for a in group.values())+row['raw4'].nbytes+row['plan'].nbytes)
    def test_wrong_selected_objects_rejected_before_parent_call(self):
        from bigbench.camera import RGBFrame
        c=capture.CaptureCollector('retention',max_captures=24); p=Parent(); w=model.PolicyObserver(p,c)
        o=self.observation(c)
        impostor=ModelObservation(RGBFrame(o.frame.width,o.frame.height,o.frame.rgb),8.,0.,wide_frame=o.wide_frame)
        with self.assertRaises(ValueError): w.step(impostor)
        self.assertEqual(p.observations,[])
    def test_missing_outputs_preserves_failed_prefix_and_unknown_count(self):
        c=capture.CaptureCollector('retention',max_captures=24); p=Parent(); w=model.PolicyObserver(p,c)
        original=p.step
        def broken(o):
            result=original(o); p.last_model_outputs=None; return result
        p.step=broken
        with self.assertRaises(ValueError): w.step(self.observation(c))
        self.assertEqual(len(p.observations),1); self.assertEqual(w.rows[0]['status'],'FAILED_OR_INCOMPLETE')
        self.assertEqual(w.rows[0]['graph_calls'],None)
    def test_state_copy_cap_prevents_parent_and_copy(self):
        c=capture.CaptureCollector('retention',payload_cap_bytes=10_000_000,max_captures=24)
        p=Parent(); w=model.PolicyObserver(p,c); o=self.observation(c)
        c.reserve_payload(c.payload_cap_bytes-c.payload_bytes)
        with self.assertRaises(ValueError): w.step(o)
        self.assertEqual(p.observations,[])
    def test_preflight_includes_full_declared_state_and_transients(self):
        estimate=model.retention_preflight(Path('model_specs/md-v3.json'))
        self.assertEqual(estimate['state_snapshot_bytes'],10358912)
        self.assertEqual(estimate['pre_post_state_bytes'],82871296)
        self.assertGreater(estimate['payload_bytes'],105844000)
        self.assertLess(estimate['payload_bytes'],268435456)




class GateTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(model,'verify_accepted_canary',None)), 'API-bound gate required')
        versions=capture.runtime_versions()
        versions.update({k:'cpu-fixture-1' for k in ('panda3d','metadrive-simulator','onnxruntime')})
        self.enterContext(patch.object(capture,'runtime_versions',return_value=versions))
    def fixture(self,temp):
        from test_first_divergence import FirstDivergenceTests
        root=Path(temp)/'evidence'; data=root/'dataset'
        helper=FirstDivergenceTests(); helper.setUp(); helper.dataset(data)
        manifest=json.loads((data/'manifest.json').read_text())
        manifest['metadata'].update(process_id=os.getpid(),process_uuid='d'*32,runtime_versions=capture.runtime_versions(),
            source_binding='CHECKOUT_BYTES_ONLY_GITHUB_API_BINDING_REQUIRED_BY_TASK2')
        (data/'manifest.json').write_text(json.dumps(manifest))
        repo='rownlvh8875-coder/big-model-closed-loop-benchmark'
        accepted='a'*40; current='b'*40
        context=dict(repository=repo,workflow_path='.github/workflows/stage7-first-divergence.yml',
            workflow_id=77,head_sha=accepted,run_id=101,attempt=1,event='push',branch='fix/public-onnx-action-frame')
        runtime=dict(capture.runtime_versions(),ImageOS='ubuntu24',ImageVersion='20261101.1')
        receipt=dict(schema='first-divergence-source-receipt-v1',context=context,
            source_snapshot=capture.source_snapshot(),runtime=runtime,installed_binary_equality_proven=False)
        (root/'receipt.json').write_text(json.dumps(receipt))
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
            for p in root.rglob('*'):
                if p.is_file(): archive.write(p,p.relative_to(root).as_posix())
        archive=stream.getvalue()
        request=dict(schema='first-divergence-request-v1',mode='model-study',acceptance=dict(
            repository=repo,workflow_id=77,source_sha=accepted,run_id=101,run_attempt=1,
            artifact_id=501,artifact_name='stage7-first-divergence-canary',artifact_nbytes=len(archive),
            artifact_sha256=sha256(archive).hexdigest(),root_raw_accepted=True,fresh_raw_review_accepted=True))
        requestpath=Path(temp)/'request.json'; requestpath.write_text(json.dumps(request))
        def run(number,head,conclusion):
            return dict(id=number,run_attempt=1,event='push',head_sha=head,head_branch=context['branch'],
                path=context['workflow_path'],workflow_id=77,repository={'full_name':repo},
                status='completed' if conclusion else 'in_progress',conclusion=conclusion)
        payloads={f'/repos/{repo}/actions/runs/101':run(101,accepted,'success'),
            f'/repos/{repo}/actions/runs/102':run(102,current,None),
            f'/repos/{repo}/actions/workflows/77':dict(id=77,path=context['workflow_path'],state='active'),
            f'/repos/{repo}/actions/artifacts/501':dict(id=501,name='stage7-first-divergence-canary',expired=False,
                size_in_bytes=len(archive),digest='sha256:'+sha256(archive).hexdigest(),
                workflow_run=dict(id=101,head_sha=accepted,head_branch=context['branch'])),
            f'/repos/{repo}/commits/{current}':dict(sha=current,parents=[{'sha':accepted}],
                files=[{'filename':'.github/stage7-first-divergence-request.json','status':'modified'}])}
        payloads[f'/repos/{repo}/actions/workflows/77/runs?event=push&head_sha={current}&per_page=100']=dict(total_count=1,workflow_runs=[payloads[f'/repos/{repo}/actions/runs/102']])
        class API:
            def json(self,path): return json.loads(json.dumps(payloads[path]))
            def download(self,path,limit):
                if path!=f'/repos/{repo}/actions/artifacts/501/zip': raise AssertionError(path)
                if len(archive)>limit: raise ValueError('archive cap')
                return archive
        def git(*args):
            if args==('rev-parse','HEAD'): return current.encode()+b'\n'
            if args==('rev-list','--parents','-n','1','HEAD'): return f'{current} {accepted}\n'.encode()
            if args==('diff-tree','--no-commit-id','--name-only','-r',current): return b'.github/stage7-first-divergence-request.json\n'
            if args[0]=='show':
                head,path=args[1].split(':',1)
                if path=='.github/stage7-first-divergence-request.json':
                    return requestpath.read_bytes() if head==current else b'{"schema":"first-divergence-request-v1","mode":"capture-canary","acceptance":null}'
                return (capture.REPO_ROOT/path).read_bytes()
            raise AssertionError(args)
        env=dict(GITHUB_ACTIONS='true',RUNNER_TEMP=temp,GITHUB_REPOSITORY=repo,GITHUB_SHA=current,
            GITHUB_RUN_ID='102',GITHUB_RUN_ATTEMPT='1',GITHUB_EVENT_NAME='push',GITHUB_REF_NAME=context['branch'],
            ImageOS='ubuntu24',ImageVersion='20261101.1')
        return SimpleNamespace(request=request,requestpath=requestpath,payloads=payloads,api=API(),git=git,env=env,
            archive=archive,accepted=accepted,current=current,repo=repo)
    def gate(self,f,out):
        with patch.dict(os.environ,f.env), patch.object(model,'_github',return_value=f.api), patch.object(model,'_git',side_effect=f.git):
            return model.verify_accepted_canary(f.requestpath,out)
    def test_api_bound_real_archive_is_validated_without_model_work(self):
        with tempfile.TemporaryDirectory() as temp:
            f=self.fixture(temp); result=self.gate(f,Path(temp)/'gate')
            self.assertEqual(result['status'],'CANARY_ACCEPTED_FOR_BOUNDED_STUDY')
            self.assertEqual(result['current_context']['run_id'],102)
            self.assertEqual(result['accepted_context']['run_id'],101)
            self.assertFalse(result['installed_binary_equality_proven'])
    def test_api_identity_attempt_artifact_and_runtime_tamper_fail_closed(self):
        mutations=[('run',lambda r:r.update(run_attempt=2)),('run',lambda r:r.update(head_sha='c'*40)),
            ('run',lambda r:r.update(event='workflow_dispatch')),('accepted',lambda r:r.update(conclusion='failure')),
            ('artifact',lambda r:r.update(size_in_bytes=1)),('artifact',lambda r:r.update(digest='sha256:'+'0'*64)),
            ('artifact',lambda r:r.update(name='other')),('commit',lambda r:r.update(parents=[{'sha':'c'*40}]))]
        with tempfile.TemporaryDirectory() as temp:
            f=self.fixture(temp)
            keys=dict(run=f'/repos/{f.repo}/actions/runs/102',accepted=f'/repos/{f.repo}/actions/runs/101',
                artifact=f'/repos/{f.repo}/actions/artifacts/501',commit=f'/repos/{f.repo}/commits/{f.current}')
            original=json.loads(json.dumps(f.payloads))
            for index,(key,change) in enumerate(mutations):
                f.payloads.clear(); f.payloads.update(json.loads(json.dumps(original))); change(f.payloads[keys[key]])
                with self.subTest(index=index),self.assertRaises(ValueError): self.gate(f,Path(temp)/f'gate-{index}')
            f.payloads.clear();f.payloads.update(original); f.env['ImageVersion']='changed'
            with self.assertRaises(ValueError):self.gate(f,Path(temp)/'runtime')
    def test_activation_requires_parent_capture_mode_and_only_registered_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            f=self.fixture(temp); original=f.git
            def git(*args):
                if args==('show',f.accepted+':.github/stage7-first-divergence-request.json'):
                    return f.requestpath.read_bytes()
                return original(*args)
            f.git=git
            with self.assertRaises(ValueError): self.gate(f,Path(temp)/'repeat')
            f.git=original
            f.payloads[f'/repos/{f.repo}/commits/{f.current}']['files'].append({'filename':'bigbench/onnx_policy.py','status':'modified'})
            with self.assertRaises(ValueError): self.gate(f,Path(temp)/'drift')
    def test_source_blobs_are_verified_against_actual_parent_not_receipt_only(self):
        with tempfile.TemporaryDirectory() as temp:
            f=self.fixture(temp); original=f.git
            def git(*args):
                if args==('show',f.accepted+':bigbench/onnx_policy.py'): return b'tampered'
                return original(*args)
            f.git=git
            with self.assertRaises(ValueError): self.gate(f,Path(temp)/'drift')
    def test_archive_rejects_traversal_symlinks_duplicates_and_bombs(self):
        self.assertTrue(callable(getattr(model,'safe_extract',None)),'safe extraction required')
        for kind in ('traversal','symlink','duplicate','over-budget'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                stream=io.BytesIO()
                with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
                    if kind=='traversal':archive.writestr('../escape',b'a')
                    elif kind=='symlink':
                        z=zipfile.ZipInfo('link');z.create_system=3;z.external_attr=(0o120777<<16);archive.writestr(z,b'outside')
                    elif kind=='duplicate':
                        with warnings.catch_warnings():
                            warnings.simplefilter('ignore',UserWarning)
                            archive.writestr('same',b'a');archive.writestr('same',b'b')
                    else:archive.writestr('large',b'x'*1025)
                with self.assertRaises(ValueError):model.safe_extract(stream.getvalue(),Path(temp)/'out',byte_limit=1024)




class TrialTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(model,'run_trial',None)),'bounded trials required')
        self.enterContext(patch.dict(os.environ,dict(GITHUB_ACTIONS='true',RUNNER_TEMP='/tmp')))
    def fixture(self,temp,arm='proxy',fail=False):
        from bigbench.public_action_frame import PublicActionFrameBinding,ModelIdentity,_resolve_action_frame,_bind_policy
        p=Parent()
        identity=ModelIdentity('/temp/official.onnx','model_specs/md-v3.json',model.MODEL_SHA,768750198,model.SPEC_SHA)
        resolution=_resolve_action_frame(identity,'auto')
        binding=PublicActionFrameBinding(_bind_policy(p,resolution),resolution)
        out=Path(temp)/arm
        seen=[]
        def episode(policy,spec,**kwargs):
            self.assertEqual(spec.steps,4);self.assertEqual(spec.seed,20261109)
            self.assertEqual(kwargs,dict(full_s_route=False,camera_convergence=6,camera_pixel_tolerance=16,camera_rgb_delta=10))
            seen.append(policy)
            if arm=='original':self.assertIs(policy,binding.policy)
            else:self.assertIsInstance(policy,model.PolicyObserver)
            if fail:raise RuntimeError('episode or close failed')
            return dict(status='FAILED_OR_INCOMPLETE',completed_steps=0,requested_steps=4,error='empty prefix')
        authorization=dict(parent_pid=os.getpid(),parent_uuid='c'*32,process_group=os.getpgid(0),
            nonce='a'*64,arm=arm,repeat=0,source_snapshot=capture.source_snapshot(),runtime=model._runtime_identity())
        return SimpleNamespace(p=p,binding=binding,out=out,episode=episode,seen=seen,authorization=authorization)
    def run_fixture(self,f):
        with patch.object(model,'_consume_trial_authorization',return_value=f.authorization), \
             patch.object(model,'_require_official_model'), \
             patch('bigbench.public_action_frame.create_public_onnx_policy',return_value=f.binding), \
             patch.object(campaign,'run_native_episode',side_effect=f.episode):
            return model.run_trial(Path('/temp/official.onnx'),Path('model_specs/md-v3.json'),f.authorization['arm'],0,'a'*64,f.out)
    def test_original_passes_public_binding_directly_and_records_unknown_observations(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,dict(ImageOS='ubuntu24',ImageVersion='20261101.1')):
            f=self.fixture(temp,'original');r=self.run_fixture(f)
            self.assertIsNone(r['observed']);self.assertEqual(r['status'],'FAILED_OR_INCOMPLETE')
            self.assertIsNone(r['model_calls']);self.assertTrue(r['provider_closed'])
            self.assertEqual(r['binding'],f.binding.receipt())
    def test_unconfirmed_close_writes_no_bulk_arrays_and_keeps_primary_error(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,dict(ImageOS='ubuntu24',ImageVersion='20261101.1')):
            f=self.fixture(temp,'retention',fail=True);r=self.run_fixture(f)
            self.assertFalse(r['provider_closed']);self.assertIn('episode or close failed',r['error'])
            self.assertEqual({p.name for p in f.out.iterdir()},{'trial.json'})
            self.assertIsNone(r['model_calls']);self.assertEqual(r['model_calls_upper_bound'],4)
    def test_direct_trial_cannot_bypass_parent_capability(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ,{},clear=True),self.assertRaises(ValueError):
                model.run_trial('unused','model_specs/md-v3.json','original',0,'a'*64,Path(temp)/'trial')


class StudyTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(model,'run_study',None)),'fresh-child study required')
        self.enterContext(patch.dict(os.environ,dict(ImageOS='ubuntu24',ImageVersion='20261101.1',GITHUB_ACTIONS='true',RUNNER_TEMP='/tmp')))
    def test_schedule_aborts_on_invalid_zero_exit_child_and_does_not_retry(self):
        launched=[]
        class Process:
            def __init__(self):self.pid=1200+len(launched);self.returncode=0
            def wait(self,timeout):return 0
        def launch(*args):launched.append(args);return Process()
        with tempfile.TemporaryDirectory() as temp,patch.object(model,'_require_model_acceptance',return_value={}), \
             patch.object(model,'_require_official_model'),patch.object(model,'_enable_subreaper'), \
             patch.object(model,'_launch_trial',side_effect=launch),patch.object(model,'_terminate_group',return_value=[]), \
             patch.object(model,'_validate_trial',side_effect=ValueError('missing child members')):
            result=model.run_study('unused','model_specs/md-v3.json',Path(temp)/'study')
            self.assertEqual(len(launched),1);self.assertEqual(result['status'],'FAILED_OR_INCOMPLETE')
            self.assertIsNone(result['model_calls']);self.assertEqual(result['model_calls_upper_bound'],4)
            self.assertIn('missing child members',result['error'])
            self.assertEqual(result['launch_ledger'][0]['exit_code'],0)
    def test_timeout_uses_remaining_deadline_and_cleans_whole_group(self):
        waits=[];cleaned=[]
        class Process:
            pid=321
            returncode=-9
            def wait(self,timeout):waits.append(timeout);raise __import__('subprocess').TimeoutExpired('trial',timeout)
        with tempfile.TemporaryDirectory() as temp,patch.object(model,'_require_model_acceptance',return_value={}), \
             patch.object(model,'_require_official_model'),patch.object(model,'_enable_subreaper'), \
             patch.object(model,'_launch_trial',return_value=Process()), \
             patch.object(model,'_terminate_group',side_effect=lambda p:cleaned.append(p.pid) or []), \
             patch.object(model,'perf_counter',side_effect=[0.,2395.,2395.,2395.,2400.,2400.,2400.,2400.]):
            result=model.run_study('unused','model_specs/md-v3.json',Path(temp)/'study')
            self.assertEqual(waits,[5.]);self.assertEqual(cleaned,[321])
            self.assertIsNone(result['model_calls']);self.assertTrue(result['launch_ledger'][0]['timed_out'])
    def test_group_cleanup_sends_signals_and_reaps(self):
        events=[]
        class Process:
            pid=432
            def wait(self,timeout):events.append(('wait',timeout));return -15
        with patch.object(model.os,'killpg',side_effect=lambda pg,sig:events.append((pg,sig))), \
             patch.object(model.os,'waitpid',side_effect=ChildProcessError):
            self.assertEqual(model._terminate_group(Process()),[])
        self.assertEqual(events[0],(432,__import__('signal').SIGTERM))
        self.assertIn((432,__import__('signal').SIGKILL),events)




class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(model,'_validate_trial',None)),'full model association validator required')
        self.enterContext(patch.dict(os.environ,dict(ImageOS='ubuntu24',ImageVersion='20261101.1',GITHUB_ACTIONS='true',RUNNER_TEMP='/tmp')))
    def complete_trial(self,temp,arm='original',out_override=None,expect_status='TRIAL_ASSOCIATION_VALIDATED',storage_limits=None):
        from bigbench.public_action_frame import PublicActionFrameBinding,ModelIdentity,_resolve_action_frame,_bind_policy
        from bigbench.onnx_contract import ModelContract
        from bigbench.onnx_policy import ModelTiming
        from bigbench.kinematics import step_ideal
        p=Parent();p.contract=ModelContract.load(Path('model_specs/md-v3.json'))
        p._types={k:np.dtype(v) for k,v in dict(state_img_q='uint8',state_desire_q='float32',state_feat_q='float32').items()}
        p.state={k:np.zeros(p.contract.input_shapes[k],dtype=v) for k,v in p._types.items()}
        def step(o):
            p.observations.append(o)
            p.state={k:np.full_like(v,len(p.observations)) for k,v in p.state.items()}
            p.last_model_outputs={'action':np.array([2,3,4,5],np.float32),'plan':np.arange(990,dtype=np.float32)}
            p.last_input_image_sha256=sha256(camera_pair_to_model(o.frame,o.wide_frame).tobytes()).hexdigest()
            p.trace.append(ModelTiming(len(p.trace),1.25,2.,3.,.03125,int(np.sum(camera_pair_to_model(o.frame,o.wide_frame),dtype=np.uint64)%(2**32))))
            return ModelAction(.03125,3.)
        p.step=step
        identity=ModelIdentity('/temp/official.onnx','model_specs/md-v3.json',model.MODEL_SHA,768750198,model.SPEC_SHA)
        r=_resolve_action_frame(identity,'auto');binding=PublicActionFrameBinding(_bind_policy(p,r),r)
        out=Path(temp)/arm if out_override is None else Path(out_override)
        def episode(policy,spec,**kwargs):
            from bigbench.camera_convergence import StrictConsecutiveCamera
            # Double only native readback: use the real collector/camera wrapper,
            # convergence loop, observer, action bridge, serializer and validators.
            from bigbench.first_divergence import _ObservedCamera
            collector=policy.collector if isinstance(policy,model.PolicyObserver) else None
            camera=CopiedBufferCamera(Provider(),raw_rgb_observer=collector)
            if collector is not None:camera=_ObservedCamera(camera,collector)
            else:
                class RawIgnore:
                    def record_native_rgb(self,*args):pass
                camera.observer=RawIgnore()
            camera=StrictConsecutiveCamera(camera,max_captures=6,max_changed_pixels=16,max_rgb_delta=10)
            policy.reset();state=AgentState(0.,1.2,0.,0.,8.);frames=[]
            for i in range(4):
                pair=camera.capture(state);action=policy.step(ModelObservation(pair.road,8.,state.t,wide_frame=pair.wide))
                state=step_ideal(state,action,.05,speed_override=8.)
                frames.append(dict(step=i+1,time_s=state.t,world_x_m=state.x,world_y_m=state.y,heading_rad=state.heading,speed_mps=8.,
                    desired_curvature_1pm=action.curvature_1pm,desired_acceleration_mps2=action.acceleration_mps2,
                    road_frame_sha256=pair.road.sha256,wide_frame_sha256=pair.wide.sha256,
                    source_road_rgb_sha256=None,source_wide_rgb_sha256=None))
            return dict(status='DIAGNOSTIC_EXECUTED',error=None,scenario='s_curve_left_right',seed=20261109,
                requested_steps=4,completed_steps=4,model_sha256=model.MODEL_SHA,frames=frames,
                model_scoring_allowed=False,real_vehicle_testing=False,full_s_route_requested=False,
                strict_same_pose_convergence=dict(enabled=True,max_captures=6,sample_count=4,failed_samples=0,
                    pixel_tolerance_count=16,pixel_channel_delta_tolerance=10))
        permit=dict(parent_pid=os.getppid(),parent_uuid='c'*32,process_group=os.getpgid(0),nonce='a'*64,arm=arm,repeat=0)
        if storage_limits is not None:permit['storage_limits']=storage_limits
        with patch.object(model,'_consume_trial_authorization',return_value=permit),patch.object(model,'_require_official_model'), \
             patch('bigbench.public_action_frame.create_public_onnx_policy',return_value=binding), \
             patch.object(campaign,'run_native_episode',side_effect=episode):
            data=model.run_trial('/temp/official.onnx','model_specs/md-v3.json',arm,0,'a'*64,out)
        self.assertEqual(data['status'],expect_status,data.get('error'))
        return out,data
    def test_original_validates_with_unknown_intermediate_payloads(self):
        with tempfile.TemporaryDirectory() as temp:
            out,data=self.complete_trial(temp)
            self.assertIsNone(model._validate_trial(out)['observed'])
            self.assertEqual(data['model_calls'],4)
            self.assertEqual({p.name for p in out.iterdir()},{'trial.json'})
    def test_retention_replays_raw_warp_i420_and_recurrent_chain(self):
        with tempfile.TemporaryDirectory() as temp:
            out,data=self.complete_trial(temp,'retention')
            self.assertEqual(len(model._validate_trial(out)['observed']['arrays']),4)
            path=out/'trial.json'
            data['observed']['arrays'][1]['pre_state']['state_feat_q']['array']['sha256']='0'*64
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):model._validate_trial(out)
    def test_parent_action_report_and_process_associations_are_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            out,data=self.complete_trial(temp);original=json.loads(json.dumps(data))
            mutations=[lambda d:d['binding']['bridge_receipts'][0]['applied_world_action'].update(curvature_1pm=.2),
                lambda d:d['report']['frames'][0].update(step=2),lambda d:d.update(provider_closed=False),
                lambda d:d.update(model_calls=3),lambda d:d.update(nonce='no'),lambda d:d.update(process_uuid='no')]
            for change in mutations:
                data=json.loads(json.dumps(original));change(data);(out/'trial.json').write_text(json.dumps(data))
                with self.assertRaises(ValueError):model._validate_trial(out)
    def test_numpy_loader_rejects_forged_dimensions_pickle_symlink_and_file_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a=np.arange(4,dtype=np.float32)
            desc=model._save_array(root,'state.npy',a)
            self.assertEqual(model._load_array(root,desc,(4,),'float32').tolist(),[0,1,2,3])
            with self.assertRaises(ValueError):model._load_array(root,desc,(100000000,),'float32')
            (root/'link.npy').symlink_to(root/'state.npy');bad=dict(desc,path='link.npy')
            with self.assertRaises(ValueError):model._load_array(root,bad,(4,),'float32')
            (root/'state.npy').write_bytes(b'wrong')
            with self.assertRaises(ValueError):model._load_array(root,desc,(4,),'float32')




class WorkflowTests(unittest.TestCase):
    def config(self):
        path=capture.REPO_ROOT/'.github/workflows/stage7-first-divergence.yml'
        self.assertTrue(path.is_file(),'new diagnostic workflow required')
        return json.loads(path.read_text())
    def test_parsed_workflow_push_scope_avoids_main_dispatch_and_docs(self):
        workflow=self.config();events=workflow['on']
        self.assertEqual(set(events),{'push'})
        def selected(event,branch,changed):
            trigger=events.get(event)
            return bool(trigger and branch in trigger['branches'] and set(changed)&set(trigger['paths']))
        cases=[('push','fix/public-onnx-action-frame',['bigbench/first_divergence_model.py'],True),
            ('push','fix/public-onnx-action-frame',['.github/stage7-first-divergence-request.json'],True),
            ('push','fix/public-onnx-action-frame',['docs/result.md'],False),
            ('push','main',['bigbench/first_divergence_model.py'],False),
            ('workflow_dispatch','fix/public-onnx-action-frame',['bigbench/first_divergence_model.py'],False),
            ('push','fix/public-onnx-action-frame',['bigbench/onnx_policy.py'],False)]
        for event,branch,changed,want in cases:
            with self.subTest(event=event,branch=branch,changed=changed):self.assertEqual(selected(event,branch,changed),want)
        self.assertEqual(workflow['permissions'],{'contents':'read','actions':'read'})
        self.assertEqual(workflow['jobs']['diagnostic']['steps'][0]['with']['fetch-depth'],2)
    def test_initial_request_and_artifact_layout_keep_canary_camera_only(self):
        workflow=self.config();request=json.loads((capture.REPO_ROOT/'.github/stage7-first-divergence-request.json').read_text())
        self.assertEqual(request['schema'],'first-divergence-request-v1')
        self.assertIn(request['mode'],('capture-canary','model-study'))
        if request['mode']=='capture-canary':self.assertIsNone(request['acceptance'])
        else:self.assertIsInstance(request['acceptance'],dict)
        steps=workflow['jobs']['diagnostic']['steps'];ids={s.get('id'):s for s in steps}
        self.assertLess(steps.index(ids['gate']),steps.index(ids['weights']))
        self.assertEqual(ids['gate']['if'],"steps.mode.outputs.mode == 'model-study'")
        self.assertEqual(ids['weights']['if'],"steps.mode.outputs.mode == 'model-study'")
        uploads=[s for s in steps if s.get('uses','').startswith('actions/upload-artifact@')]
        canary=next(s for s in uploads if s['with']['name']=='stage7-first-divergence-canary')
        self.assertEqual(canary['with']['path'],'${{ runner.temp }}/first-divergence-canary/')
        self.assertEqual(canary['if'],"always() && steps.mode.outputs.mode == 'capture-canary'")
    def test_source_registry_includes_all_new_producers_and_download_closure(self):
        paths=set(capture.required_source_paths())
        self.assertTrue({'bigbench/first_divergence_model.py','tests/test_first_divergence_model.py',
            '.github/workflows/stage7-first-divergence.yml','bigbench/model_inventory.py','scripts/__init__.py'}<=paths)
        self.assertNotIn('.github/stage7-first-divergence-request.json',paths)
    def test_cli_routes_all_explicit_commands_and_failed_trial_is_nonzero(self):
        from scripts.first_divergence_audit import main
        with patch.object(model,'run_trial',return_value={'status':'FAILED_OR_INCOMPLETE'}):
            self.assertEqual(main(['native-trial','--model','m','--spec','s','--arm','original','--repeat','0','--nonce','a'*64,'--out','o']),1)
        with patch.object(model,'validate_study',return_value={'status':'STUDY_ASSOCIATION_VALIDATED'}):
            self.assertEqual(main(['validate-study','--root','r']),0)
        with patch.object(model,'verify_accepted_canary',return_value={'status':'CANARY_ACCEPTED_FOR_BOUNDED_STUDY'}):
            self.assertEqual(main(['verify-accepted-canary','--request','r','--out','o']),0)




class OneShotGateTests(unittest.TestCase):
    setUp=GateTests.setUp
    fixture=GateTests.fixture
    gate=GateTests.gate
    def test_child_receipt_cannot_add_original_pass_or_system_equality_claims(self):
        with tempfile.TemporaryDirectory() as temp:
            f=self.fixture(temp);receipt=self.gate(f,Path(temp)/'gate')
            with patch.dict(os.environ,f.env),patch.object(model,'_git',side_effect=f.git), \
                 patch.object(model,'_request',return_value=(f.request,f.requestpath.read_bytes())), \
                 patch.object(model,'_hash_file',return_value=receipt['request_sha256']):
                model._receipt_current_binding(receipt)
                for key,value in (('original_strict_pass',True),('installed_binary_equality_proven',True),('unknown_claim',True)):
                    changed=dict(receipt);changed[key]=value
                    with self.subTest(key=key),self.assertRaises(ValueError):model._receipt_current_binding(changed)
    def test_duplicate_push_of_same_activation_commit_cannot_spend_calls(self):
        with tempfile.TemporaryDirectory() as temp:
            f=self.fixture(temp)
            f.payloads[f'/repos/{f.repo}/actions/workflows/77/runs?event=push&head_sha={f.current}&per_page=100']['total_count']=2
            with self.assertRaises(ValueError):self.gate(f,Path(temp)/'gate')
    def test_missing_dataset_runtime_is_not_accepted_from_external_receipt_alone(self):
        with tempfile.TemporaryDirectory() as temp:
            f=self.fixture(temp);stream=io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(f.archive)) as original,zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
                for item in original.infolist():
                    content=original.read(item)
                    if item.filename=='dataset/manifest.json':
                        manifest=json.loads(content);manifest['metadata'].pop('runtime_versions');content=json.dumps(manifest).encode()
                    archive.writestr(item.filename,content)
            altered=stream.getvalue();a=f.request['acceptance'];a.update(artifact_nbytes=len(altered),artifact_sha256=sha256(altered).hexdigest())
            f.requestpath.write_text(json.dumps(f.request))
            f.payloads[f'/repos/{f.repo}/actions/artifacts/501'].update(size_in_bytes=len(altered),digest='sha256:'+sha256(altered).hexdigest())
            f.api.download=lambda path,limit:altered
            with self.assertRaises(ValueError):self.gate(f,Path(temp)/'gate')


class FinalizationTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ,dict(ImageOS='ubuntu24',ImageVersion='20261101.1',GITHUB_ACTIONS='true',RUNNER_TEMP='/tmp')))
    def test_post_launch_authorization_error_still_records_unknown_upper_bound(self):
        import inspect
        self.assertIn('launch_row',inspect.signature(model._launch_trial).parameters,'launch must register its actual PID before authorization can fail')
        row={};cleaned=[]
        class Process:pid=6789;returncode=-9
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(model.subprocess,'Popen',return_value=Process()), \
             patch.object(capture,'source_snapshot',side_effect=ValueError('source raced')), \
             patch.object(model,'_terminate_group',side_effect=lambda p:cleaned.append(p.pid) or []):
            with self.assertRaises(ValueError):model._launch_trial('m','s',Path(temp)/'trial','original',0,'a'*64,'b'*32,0,row)
        self.assertTrue(row['launched']);self.assertEqual(row['launcher_pid'],6789);self.assertEqual(cleaned,[6789])
    def test_serialization_mismatch_is_primary_failure_after_confirmed_close(self):
        helper=ValidationTests();helper.setUp();self.addCleanup(helper.doCleanups)
        with tempfile.TemporaryDirectory() as temp,patch.object(capture.CaptureCollector,'serialize_captures',side_effect=ValueError('packed image mismatch')):
            root,data=helper.complete_trial(temp,'retention',expect_status='FAILED_OR_INCOMPLETE')
            self.assertTrue(data['provider_closed']);self.assertIsInstance(data['error'],str)
            self.assertIn('packed image mismatch',data['error'])
            self.assertEqual(data['cleanup_errors'],[]);self.assertIsNone(data['model_calls'])
    def test_candidate_manifest_bytes_are_inside_dataset_cap(self):
        helper=ValidationTests();helper.setUp();self.addCleanup(helper.doCleanups)
        with tempfile.TemporaryDirectory() as temp:
            root,data=helper.complete_trial(temp);(root/'trial.json').unlink()
            with patch.object(capture,'DATASET_CAP_BYTES',1),self.assertRaises(ValueError):model._validate_trial(root,manifest=data)
    def test_frozen_owner_close_error_preserves_raw_primary_and_separate_cleanup(self):
        helper=TrialTests();helper.setUp();self.addCleanup(helper.doCleanups)
        from bigbench import metadrive_camera,curved_lane_scenarios
        real_episode=campaign.run_native_episode
        class NativeBoundaryProvider:
            def __init__(self,**kwargs):self.env=SimpleNamespace(current_map=object())
            def close(self):raise RuntimeError('close failed')
        with tempfile.TemporaryDirectory() as temp:
            f=helper.fixture(temp,'retention')
            f.episode=real_episode
            with patch.object(metadrive_camera,'NativeMetaDriveProvider',NativeBoundaryProvider), \
                 patch.object(curved_lane_scenarios,'select_native_curve_lanes',side_effect=RuntimeError('native raw failure')):
                # The frozen campaign imported its selector directly.
                with patch.object(campaign,'select_native_curve_lanes',side_effect=RuntimeError('native raw failure')):
                    data=helper.run_fixture(f)
            self.assertIn('native raw failure',data['error'])
            self.assertTrue(any('close failed' in e for e in data['cleanup_errors']))
            self.assertFalse(data['provider_closed'])
            self.assertTrue(any('native raw failure' in e for e in data['error_chain']))
    def test_full_six_child_schedule_and_final_publication_validation(self):
        self.assertTrue(callable(getattr(model,'_validate_study',None)),'candidate study must validate before success publication')
        helper=ValidationTests();helper.setUp()
        self.addCleanup(helper.doCleanups)
        with tempfile.TemporaryDirectory() as temp:
            launched=[]
            class Process:
                def __init__(self,pid):self.pid=pid;self.returncode=0
                def wait(self,timeout):return 0
            def launch(m,s,out,arm,repeat,nonce,parent_uuid,index,row):
                path,data=helper.complete_trial(temp,arm,out_override=out,storage_limits={k:row['storage'][k] for k in ('payload_limit_bytes','trial_ledger_limit_bytes','log_limit_bytes')})
                data.update(repeat=repeat,nonce=nonce,parent_pid=os.getpid(),parent_uuid=parent_uuid,
                    process_group=7000+index,process_id=8000+index,process_uuid=f'{index+10:032x}')
                (path/'trial.json').write_text(json.dumps(data))
                launched.append((arm,repeat));return Process(7000+index)
            receipt={'current_context':{'repository':model.REPOSITORY}}
            patches=[patch.object(model,'_require_model_acceptance',return_value=receipt),patch.object(model,'_require_official_model'),
                patch.object(model,'_enable_subreaper'),patch.object(model,'_launch_trial',side_effect=launch),
                patch.object(model,'_terminate_group',return_value=[]),patch.object(model,'_receipt_current_binding')]
            from contextlib import ExitStack
            with ExitStack() as stack:
                for context in patches:stack.enter_context(context)
                result=model.run_study('m','model_specs/md-v3.json',Path(temp)/'study')
                self.assertEqual(launched,[('original',0),('proxy',0),('retention',0),('retention',1),('proxy',1),('original',1)])
                self.assertEqual(result['model_calls'],24);self.assertEqual(len(result['comparisons']),9)
                self.assertEqual(model.validate_study(Path(temp)/'study')['status'],'STUDY_ASSOCIATION_VALIDATED')
                comparison=result['comparisons'][0]
                self.assertEqual(comparison['availability']['pre_state'],'unknown-unobserved-control')
                result['launch_ledger'][0]['storage']['payload_limit_bytes']-=1
                (Path(temp)/'study/study.json').write_text(json.dumps(result))
                with self.assertRaises(ValueError):model.validate_study(Path(temp)/'study')
    def test_array_content_tamper_with_recomputed_file_hash_still_breaks_chain(self):
        helper=ValidationTests();helper.setUp();self.addCleanup(helper.doCleanups)
        with tempfile.TemporaryDirectory() as temp:
            root,data=helper.complete_trial(temp,'retention')
            desc=data['observed']['arrays'][1]['pre_state']['state_feat_q'];p=root/desc['path']
            value=np.load(p,allow_pickle=False);value.reshape(-1)[0]=19
            with p.open('wb') as stream:np.save(stream,value,allow_pickle=False)
            desc.update(nbytes=p.stat().st_size,sha256=sha256(p.read_bytes()).hexdigest(),array=model._descriptor(value))
            (root/'trial.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'recurrent chain'):model._validate_trial(root)


class StorageBudgetTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(model,'_LogSink',None)),'child output needs a bounded real sink')
        self.enterContext(patch.dict(os.environ,dict(ImageOS='review',ImageVersion='review',GITHUB_ACTIONS='true',RUNNER_TEMP='/tmp')))
    def pipe_process(self,data,mode='invalid'):
        import subprocess
        readfd,writefd=os.pipe();os.write(writefd,data);os.close(writefd)
        class Process:
            pid=12345
            returncode=1 if mode=='nonzero' else 0
            stdout=os.fdopen(readfd,'rb',buffering=0)
            def wait(self,timeout):
                if mode=='timeout':raise subprocess.TimeoutExpired('boundary-child',timeout)
                return self.returncode
        return Process()
    def test_output_close_error_cannot_skip_group_reaping_or_failure_ledger(self):
        root_cleanup=[];writefds=[]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'study'
            def launch(m,s,out,arm,repeat,nonce,parent_uuid,index,row):
                out.mkdir();readfd,writefd=os.pipe();writefds.append(writefd)
                class Process:
                    pid=12345;returncode=-9;stdout=os.fdopen(readfd,'rb',buffering=0)
                    def wait(self,timeout):return -9
                sink=model._LogSink(out/'process.log',row['storage']['log_limit_bytes']);close=sink.close
                def broken_close():close();raise OSError('log close failed')
                sink.close=broken_close
                row.update(launched=True,launcher_pid=12345,process_group=12345)
                return model._BoundedChild(Process(),sink,row['storage'])
            with patch.object(capture,'DATASET_CAP_BYTES',32768),patch.object(model,'_require_model_acceptance',return_value={}), \
                 patch.object(model,'_require_official_model'),patch.object(model,'_enable_subreaper'), \
                 patch.object(model,'_launch_trial',side_effect=launch),patch('select.select',return_value=([],[],[])), \
                 patch.object(model,'_terminate_group',side_effect=lambda p:root_cleanup.append(p.pid) or []):
                result=None
                try:result=model.run_study('unused','model_specs/md-v3.json',root)
                except OSError:pass
                finally:
                    for fd in writefds:os.close(fd)
                self.assertEqual(root_cleanup,[12345])
                self.assertIsNotNone(result)
                self.assertTrue(any('log close failed' in e for e in result['cleanup_errors']))
                self.assertLessEqual(sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),32768)
    def test_real_log_sink_keeps_exact_prefix_and_rejects_further_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'process.log';sink=model._LogSink(path,7)
            sink.write(b'abc')
            with self.assertRaises(ValueError):sink.write(b'defghijk')
            sink.close()
            self.assertEqual(path.read_bytes(),b'abcdefg')
            self.assertEqual(sink.nbytes,7)
    def test_all_child_exit_paths_publish_cap_inclusive_failed_evidence(self):
        for mode in ('nonzero','timeout','invalid','overflow'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                root=Path(temp)/'study';launched=[];cleaned=[]
                def launch(m,s,out,arm,repeat,nonce,parent_uuid,index,row):
                    out.mkdir();row.update(launched=True,launcher_pid=12345,process_group=12345)
                    limits=row['storage'];n=min(limits['log_limit_bytes'],4096)
                    data=b'p'*n if mode!='overflow' else b'p'*(min(n,100)+1)
                    if mode=='overflow':limits['log_limit_bytes']=min(n,100)
                    raw=self.pipe_process(data,mode)
                    child=model._BoundedChild(raw,model._LogSink(out/'process.log',limits['log_limit_bytes']),limits)
                    launched.append(child);return child
                with patch.object(capture,'DATASET_CAP_BYTES',32768), \
                     patch.object(model,'_require_model_acceptance',return_value={}),patch.object(model,'_require_official_model'), \
                     patch.object(model,'_enable_subreaper'),patch.object(model,'_launch_trial',side_effect=launch), \
                     patch.object(model,'_terminate_group',side_effect=lambda p:cleaned.append(p.pid) or []):
                    result=model.run_study('unused','model_specs/md-v3.json',root)
                self.assertEqual(len(launched),1);self.assertEqual(cleaned,[12345])
                self.assertEqual(result['status'],'FAILED_OR_INCOMPLETE');self.assertIsNone(result['model_calls'])
                self.assertEqual(result['model_calls_upper_bound'],4)
                self.assertLessEqual(sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),32768)
                self.assertEqual(json.loads((root/'study.json').read_text())['status'],'FAILED_OR_INCOMPLETE')
                if mode=='overflow':
                    self.assertEqual((root/'trial_00/process.log').read_bytes(),b'p'*100)
                    self.assertIn('log',str(result['launch_ledger'][0]['storage']['limit_error']))
    def test_failed_ledger_reservation_keeps_errors_counts_and_explicit_omission(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'study.json'
            data=dict(schema=model.STUDY_SCHEMA,status='FAILED_OR_INCOMPLETE',error='raw failure',cleanup_errors=['cleanup failure'],
                model_calls=None,model_calls_lower_bound=1,model_calls_upper_bound=4,report={'large':'x'*20000})
            result=model._publish_ledger(path,data,4096)
            self.assertLessEqual(path.stat().st_size,4096)
            self.assertEqual(result['error'],'raw failure');self.assertEqual(result['cleanup_errors'],['cleanup failure'])
            self.assertIsNone(result['model_calls']);self.assertEqual(result['model_calls_upper_bound'],4)
            self.assertIn('report',result['metadata_omitted'])
    def test_payload_reservation_prevents_partial_npy_and_preserves_image_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);budget=model._StorageBudget(16)
            with self.assertRaises(ValueError):model._save_array(root,'array.npy',np.arange(4,dtype=np.float32),write_budget=budget)
            self.assertFalse((root/'array.npy').exists())
        helper=ValidationTests();helper.setUp();self.addCleanup(helper.doCleanups)
        with tempfile.TemporaryDirectory() as temp,patch.object(capture,'DATASET_CAP_BYTES',4*1024*1024):
            root,data=helper.complete_trial(temp,'retention',expect_status='FAILED_OR_INCOMPLETE',
                storage_limits=dict(payload_limit_bytes=3000000,trial_ledger_limit_bytes=65536,log_limit_bytes=1024))
            images=list(root.rglob('*.png'))
            self.assertGreater(len(images),0);self.assertLess(len(images),16)
            self.assertTrue(data['provider_closed']);self.assertIn('budget',data['error'])
            self.assertLessEqual(sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),4*1024*1024)
            self.assertIsNone(data['model_calls']);self.assertEqual(data['model_calls_upper_bound'],4)
