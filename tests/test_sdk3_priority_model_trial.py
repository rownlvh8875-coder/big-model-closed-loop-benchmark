from pathlib import Path
from types import SimpleNamespace
import copy,json,tempfile,unittest
try:from scripts import sdk3_priority_model_trial as h
except ImportError:h=None
from bigbench import sdk3_terrain_priority as policy
from tests.test_sdk3_terrain_priority import fixture
class OriginalPolicy:
    made=[]
    def __init__(self,*args,**kwargs):self.audit_rows=[];OriginalPolicy.made.append(self)
    def step(self,observation):self.audit_rows.append(dict(step=len(self.audit_rows)+1));return 1.
class OriginalCamera:
    made=[]
    def __init__(self,provider,raw_rgb_observer=None):self.provider=provider;self.raw_rgb_observer=raw_rgb_observer;OriginalCamera.made.append(self)
    def capture(self,pose):return 'original-frame'
AuditedOfficialOnnx=OriginalPolicy
NativeWorldCamera=OriginalCamera
PROVIDERS=[]
FAIL_AT=None

def original_episode(policy,spec,*,raw_rgb_observer=None,**kwargs):
    engine,core=fixture();provider=SimpleNamespace(env=SimpleNamespace(engine=engine),core=core,closed=False);PROVIDERS.append(provider)
    try:
        camera=NativeWorldCamera(provider,raw_rgb_observer=raw_rgb_observer);frames=[]
        for step in range(spec.steps):
            camera.capture(step)
            if FAIL_AT==step:raise RuntimeError('measured episode failure')
            policy.step('original-observation');frames.append(dict(step=step+1))
        return dict(status='DIAGNOSTIC_EXECUTED',completed_steps=spec.steps,frames=frames)
    finally:provider.closed=True
run_native_episode=original_episode

def original_trial(*,model,spec,scenario,seed,steps,speed,initial_fraction,raw_rgb_dir=None):
    instance=AuditedOfficialOnnx(model,spec);result=run_native_episode(instance,SimpleNamespace(steps=steps),raw_rgb_observer=None if raw_rgb_dir is None else object());result.update(trial_evidence='UNMODIFIED_METADRIVE_NEW_FRAME_OFFICIAL_ONNX_DIAGNOSTIC',requested_steps=steps,seed=seed,scenario=scenario);return result
class CandidateTrialContracts(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(h,'candidate trial wrapper missing');OriginalPolicy.made=[];OriginalCamera.made=[];PROVIDERS.clear()
    def make(self,folder):
        def install(provider):return policy.install_rgb_terrain_priority(provider.env.engine,terrain_label='terrain',tag_key='rgb',core=provider.core)
        def stats():self.assertTrue(PROVIDERS[-1].closed);return dict(returned=0,guards_ok=True,values=dict.fromkeys(('configured','closed','error','forwarded','resolutions','paths','events'),0))
        return h.make_trial(original_trial,original_episode,OriginalPolicy,OriginalCamera,install_policy=install,out=Path(folder),source_stats_after=stats,identity=dict(nonce='a'*32))
    def call(self,trial,**kw):return trial(model=Path('/model.onnx'),spec=Path('/spec.json'),scenario='s_curve_left_right',seed=20261110,steps=12,speed=8.,initial_fraction=.12,**kw)
    def test_exact_original_policy_camera_and_globals_are_preserved(self):
        before=(original_trial.__globals__['AuditedOfficialOnnx'],original_trial.__globals__['run_native_episode'],original_episode.__globals__['NativeWorldCamera'])
        with tempfile.TemporaryDirectory() as d:
            result=self.call(self.make(d));self.assertIs(type(OriginalPolicy.made[0]),OriginalPolicy);self.assertIs(type(OriginalCamera.made[0]),OriginalCamera);self.assertIs(OriginalPolicy.made[0].step.__func__,OriginalPolicy.step);self.assertIs(OriginalCamera.made[0].capture.__func__,OriginalCamera.capture);self.assertIsNone(OriginalCamera.made[0].raw_rgb_observer);self.assertEqual(result['completed_steps'],12);self.assertEqual(result['trial_evidence'],h.CANDIDATE_EVIDENCE);self.assertEqual(result['renderer_candidate_id'],policy.REPAIR_ID)
        self.assertEqual(before,(original_trial.__globals__['AuditedOfficialOnnx'],original_trial.__globals__['run_native_episode'],original_episode.__globals__['NativeWorldCamera']))
    def test_complete_lifecycle_counts_twelve_actual_original_audit_steps(self):
        with tempfile.TemporaryDirectory() as d:
            result=self.call(self.make(d));life=json.loads((Path(d)/'model-trial-lifecycle.json').read_text());self.assertEqual(life['inferences_completed_lower_bound'],12);self.assertEqual(life['inferences_completed_upper_bound'],12);self.assertTrue(life['completed']);self.assertEqual(result['actual_onnx_inferences_completed'],12)
    def test_episode_error_keeps_original_exception_and_nonzero_inference_bounds(self):
        global FAIL_AT;FAIL_AT=3
        try:
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaisesRegex(RuntimeError,'measured episode failure'):self.call(self.make(d))
                life=json.loads((Path(d)/'model-trial-lifecycle.json').read_text());self.assertFalse(life['completed']);self.assertEqual(life['inferences_completed_lower_bound'],3);self.assertGreaterEqual(life['inferences_completed_upper_bound'],3)
        finally:FAIL_AT=None
    def test_raw_rgb_retention_is_rejected_before_any_model_constructor(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):self.call(self.make(d),raw_rgb_dir=Path('/forbidden'))
            self.assertEqual(OriginalPolicy.made,[])
    def test_trial_clones_never_share_policy_or_camera_instances(self):
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:self.call(self.make(a));self.call(self.make(b))
        self.assertEqual(len(OriginalPolicy.made),2);self.assertIsNot(OriginalPolicy.made[0],OriginalPolicy.made[1]);self.assertIsNot(OriginalCamera.made[0],OriginalCamera.made[1])
if __name__=='__main__':unittest.main()
