"""Original policy/camera instances, with only an explicit RGB tag-state repair."""
from pathlib import Path
from types import FunctionType
import hashlib,inspect,os,sys
from bigbench import sdk3_terrain_priority as repair
from scripts import panda_sdk3_runtime as pins
CANDIDATE_EVIDENCE='MODIFIED_RGB_TERRAIN_PRIORITY_OFFICIAL_ONNX_DIAGNOSTIC'

def clone(function,**changes):
    value=FunctionType(function.__code__,dict(function.__globals__,**changes),function.__name__,function.__defaults__,function.__closure__);value.__kwdefaults__=dict(function.__kwdefaults__ or {});return value

def function_sha(function):return hashlib.sha256(inspect.getsource(function).encode()).hexdigest()

def make_trial(original_trial,original_episode,original_policy,original_camera,*,install_policy,out,source_stats_after,identity):
    out=Path(out);policies=[];cameras=[];receipts=[];life=dict(protocol='sdk3-priority-model-lifecycle-v1',pid=os.getpid(),**identity,status='PRE_POLICY',policy_constructor_entered=False,policy_created=False,completed=False,inferences_completed_lower_bound=0,inferences_completed_upper_bound=0)
    def persist():pins.write(out/'model-trial-lifecycle.json',life)
    context=dict(original_episode_implementation_sha256=function_sha(original_episode),original_trial_implementation_sha256=function_sha(original_trial),policy_step_implementation_sha256=function_sha(original_policy.step),camera_capture_implementation_sha256=function_sha(original_camera.capture),candidate_wrapper_sha256=pins.digest(__file__),policy_class_preserved=True,policy_step_implementation_preserved=True,camera_class_preserved=True,camera_capture_implementation_preserved=True)
    def construct_policy(*args,**kwargs):
        life.update(status='POLICY_LOADING',policy_constructor_entered=True);persist();value=original_policy(*args,**kwargs);pins.need(type(value) is original_policy,'exact original policy class');policies.append(value);life.update(status='EPISODE_PENDING',policy_created=True,inferences_completed_upper_bound=12);persist();return value
    def construct_camera(provider,raw_rgb_observer=None):
        pins.need(raw_rgb_observer is None,'no raw RGB observer in official cohort');receipt=install_policy(provider);value=original_camera(provider,raw_rgb_observer=None);pins.need(type(value) is original_camera and value.raw_rgb_observer is None,'exact original unobserved camera instance');receipts.append(receipt);cameras.append(value);return value
    episode=clone(original_episode,NativeWorldCamera=construct_camera);trial=clone(original_trial,AuditedOfficialOnnx=construct_policy,run_native_episode=episode)
    def invoke(**kwargs):
        pins.need(kwargs.get('raw_rgb_dir') is None and kwargs.get('steps')==12 and kwargs.get('speed')==8. and kwargs.get('initial_fraction')==.12,'fixed unobserved12step official cohort');pins.need(not policies and not cameras and not receipts,'one original model/camera lifetime per trial callable');life.update(seed=kwargs['seed'],scenario=kwargs['scenario']);persist();result=None;failure=None
        try:
            result=trial(**kwargs);pins.need(len(policies)==len(cameras)==len(receipts)==1,'one original model and native camera');result.update(trial_evidence=CANDIDATE_EVIDENCE,renderer_candidate_id=repair.REPAIR_ID,renderer_policy_modified=True,renderer_candidate=receipts[0],original_unmodified_pipeline=False,source_context=context,raw_rgb_observer_used=False,extra_gpu_queries=0,extra_render_tasks=0,diagnostic_depth_clear_pixels=0,draw_trace_modules_loaded=any(k in sys.modules for k in ('scripts.sdk3_draw_trace','scripts.sdk3_draw_trace_native','scripts.sdk3_priority_canary')),ld_preload_present=bool(os.environ.get('LD_PRELOAD')))
            ort=sys.modules.get('onnxruntime');session=getattr(policies[0],'session',None);result.update(onnxruntime_version=getattr(ort,'__version__',None),onnxruntime_providers=session.get_providers() if session is not None else None,injected_session=getattr(policies[0],'_injected_session',None),real_ort_session=ort is not None and session is not None and isinstance(session,getattr(ort,'InferenceSession',())))
            try:maps=Path('/proc/self/maps').read_text();result['draw_trace_library_mapped']=any(name in maps for name in ('/drawtrace.so','/libtrace.so'))
            except OSError:result['draw_trace_library_mapped']=None
            return result
        except BaseException as exc:failure=type(exc).__name__+': '+str(exc);raise
        finally:
            known=len(policies[0].audit_rows) if policies else 0;complete=result is not None and result.get('status')=='DIAGNOSTIC_EXECUTED' and result.get('completed_steps')==12 and known==12;upper=known if complete else min(12,known+1) if policies else 0;life.update(status='COMPLETED' if complete else 'FAILED_OR_INCOMPLETE',completed=complete,inferences_completed_lower_bound=known,inferences_completed_upper_bound=upper,failure=failure)
            try:life['source_stats_after']=source_stats_after()
            except BaseException as exc:life['source_stats_after']=None;life['source_stats_after_error']=type(exc).__name__+': '+str(exc)
            if result is not None:result.update(actual_onnx_inferences_completed=known if complete else None,actual_onnx_inference_bounds=[known,upper],source_stats_after=life['source_stats_after'])
            persist()
    return invoke
