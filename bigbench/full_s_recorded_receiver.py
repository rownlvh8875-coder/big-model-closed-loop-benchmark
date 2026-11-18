"""CPU-only complete/partial receipt consistency, never native authentication."""
from pathlib import Path
import hashlib
import struct
import sys
from .full_s_recorded_worker import need,_read_receipt,_receipt_bytes,_source_snapshot,_error

FALSE_FLAGS=('origin_authenticated','native_execution_authenticated','model_camera_qualified',
    'hardware_gpu_qualified','physical_optics_validated','carla_validated','all_four_validation_tracks_passed')
REAL_SESSION='onnxruntime.capi.onnxruntime_inference_collection.InferenceSession'
MODEL_SHA='35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199'
FINAL={'RECORDED','FAILED_OR_INCOMPLETE'}
EARLY={'PRE_POLICY','DEPENDENCIES_LOADING','POLICY_LOADING','WORLD_LOADING'}
CHECKPOINTS=EARLY|{'EPISODE_READY','INFERENCE_PENDING','STEP_COMMITTED','TRIAL_RECORDED'}


def plan():
    from .full_s_failure_capture import recording_plan
    return dict(protocol='recorded-official-diagnostic-receiver-plan-v1',private_task_state='UNKNOWN',
        execution_activated=False,model_execution_command_available=False,new_model_processes=0,new_inferences=0,
        new_native_render_calls=0,recording=recording_plan(),intended_single_trial_max_steps=600,
        minimum_model_ram_bytes=8*1024**3,archive_cap_bytes=384*1024**2,expanded_cap_bytes=512*1024**2,
        heavy_modules_loaded=sorted(n for n in sys.modules if n.split('.')[0] in
            ('numpy','cv2','panda3d','direct','metadrive','onnxruntime','carla')),**{k:False for k in FALSE_FLAGS})


def _optional(path,limit=65536):
    try:path.lstat()
    except FileNotFoundError:return None
    return _read_receipt(path,limit)


def _hex(value,size):
    return isinstance(value,str) and len(value)==size and value!='0'*size and all(c in '0123456789abcdef' for c in value)


def _bounds(value):
    need(isinstance(value,list) and len(value)==2 and all(type(v) is int for v in value) and
         0<=value[0]<=value[1]<=600 and value[1]-value[0]<=1,'conservative typed inference bounds required')
    return list(value)


def _identity(value,protocol):
    need(value.get('protocol')==protocol and all(type(value.get(k)) is int and value[k]>0 for k in ('pid','parent_pid')) and
         value['pid']!=value['parent_pid'] and _hex(value.get('nonce'),32) and type(value.get('seed')) is int and
         value['seed'] in (20261109,20261110) and value.get('scenario') in ('s_curve_left_right','s_curve_right_left'),
         'registered typed worker/case/nonce identity required')
    need(value.get('mode') is None and all(value.get(k) is None for k in
        ('fixture_policy_audit_bounds','counter_scope','official_inference_bounds','official_model_processes','policy_data','graph_feed_attested')),
        'synthetic canary metadata cannot certify official-body receipts')


def _errors(value,*,required):
    need(not required or all(k in value for k in ('primary_error','secondary_errors')),'explicit final error fields required')
    p=value.get('primary_error');s=value.get('secondary_errors')
    need(p is None or isinstance(p,str) and 0<len(p)<=4096,'bounded primary error required')
    need(s is None and not required or isinstance(s,list) and len(s)<=64 and
         all(isinstance(e,str) and len(e)<=4096 for e in s),'bounded secondary errors required')
    return p,s


def _lifecycle(value):
    _identity(value,'recorded-full-s-worker-lifecycle-v1')
    bounds=_bounds(value.get('inference_bounds'));status=value.get('status')
    need(status in FINAL|CHECKPOINTS,'recognized final state or earlier lifecycle checkpoint required')
    for key in ('policy_constructor_entered','policy_created','provider_received','body_provider_close_attempted'):
        need(type(value.get(key)) is bool,'typed construction/cleanup milestone required: '+key)
    for key in ('provider_created','provider_close_attempted','provider_closed'):
        need(key in value and (value[key] is None or type(value[key]) is bool),'explicit known/unknown provider milestone required')
    policy=value['policy_created'];received=value['provider_received'];body_close=value['body_provider_close_attempted']
    need(not policy or value['policy_constructor_entered'],'policy cannot exist before construction')
    if not policy:
        need(bounds==[0,0] and not received and not body_close and all(value[k] is False for k in
             ('provider_created','provider_close_attempted','provider_closed')),'uncreated policy cannot have calls or a provider')
    if received:
        need(policy and value['provider_created'] is True,'provider receipt requires completed policy and provider creation')
    else:
        need(bounds==[0,0],'no received provider can have inference calls')
        if policy:need(value['provider_created'] is None,'factory creation before handoff must remain unknown')
    need(not body_close or value['provider_close_attempted'] is True,'body close must be explicitly attempted')
    need(value['provider_closed'] is not True or body_close and value['provider_close_attempted'] is True,
         'closed provider requires observed body cleanup')
    p,s=_errors(value,required=status in FINAL)
    if status in FINAL:
        need((status=='RECORDED')==(p is None) and (p is not None or not s),'final status and errors must agree')
        if received:need(body_close and type(value['provider_closed']) is bool,'final received provider requires attempted cleanup')
        if status=='RECORDED':need(policy and received and value['provider_closed'] is True,'reported completed body must have closed provider')
    else:
        need(p is None and s in (None,[]),'earlier checkpoint cannot claim a final failure')
    rows=value.get('completed_rows')
    if rows is not None:need(type(rows) is int and 0<=rows<=bounds[0],'typed committed progress cannot exceed known audits')
    if status in EARLY:need(bounds==[0,0] and rows in (None,0),'loading checkpoint cannot contain inference progress')
    if status=='EPISODE_READY':need(bounds==[0,0] and rows==0,'ready checkpoint starts with zero progress')
    if status=='INFERENCE_PENDING':need(received and rows==bounds[0] and bounds[1]==bounds[0]+1,'pending checkpoint requires exact uncertain next call')
    if status=='STEP_COMMITTED':need(received and rows==bounds[0]==bounds[1],'committed checkpoint requires exact completed calls')
    return bounds,p,s


def _report(value,who):
    from .full_s_receipts import validate_trajectory
    need(value.get('protocol')=='full-s-closed-loop-v1' and type(value.get('process_id')) is int and
         value['process_id']==who['pid'] and (value.get('seed'),value.get('scenario'))==(who['seed'],who['scenario']) and
         type(value.get('max_steps')) is int and value['max_steps']==600 and value.get('initial_fraction')==.12 and
         _hex(value.get('process_uuid'),32) and value.get('model_sha256')==MODEL_SHA and
         value.get('model_test_double') is False and value.get('injected_session') is False,
         'available original report must bind typed PID/UUID/case/model metadata')
    bounds=_bounds(value.get('actual_inference_bounds'))
    need(type(value.get('completed_steps')) is int and type(value.get('trial_completed')) is bool and
         all(value.get(k) is False for k in ('ground_truth_control_used','model_scoring_allowed','real_vehicle_testing')) and
         type(value.get('pixel_tolerance')) is int and value['pixel_tolerance']==0 and
         type(value.get('extra_render_tasks')) is int and value['extra_render_tasks']==0,'original unmodified protocol required')
    for audit in value.get('inference_audit_rows',[]):
        raw=audit.get('raw_model_action')
        need(isinstance(raw,list) and len(raw)==4 and hashlib.sha256(struct.pack('<4f',*raw)).hexdigest()==audit.get('raw_action_sha256'),
             'available raw action must match its exact FP32 hash')
    validate_trajectory(value,who['seed'],who['scenario'])
    return bounds


def inspect_trial(root):
    root=Path(root).absolute()
    need(root.is_dir() and not root.is_symlink() and all(not p.is_symlink() for p in root.parents),'nonsymlink trial root required')
    life=_optional(root/'recorded-trial-lifecycle.json');trial=_optional(root/'recorded-trial.json',4*1024**2)
    need(life is not None or trial is not None,'at least one worker identity receipt required')
    lb=lp=ls=None
    if life is not None:lb,lp,ls=_lifecycle(life)
    who=trial if trial is not None else life
    unavailable=[];tb=None;p=lp;s=ls;reported=None;final=life is not None and life['status'] in FINAL
    if final:reported=life['status']=='RECORDED'
    if life is None:unavailable.append('recorded-trial-lifecycle.json')
    elif not final:unavailable.append('recorded-trial-lifecycle.json:finalization')
    if trial is None:unavailable.append('recorded-trial.json')
    else:
        _identity(trial,'recorded-full-s-worker-trial-v1');tb=_bounds(trial.get('actual_inference_bounds'));p,s=_errors(trial,required=True)
        need(type(trial.get('max_steps')) is int and trial['max_steps']==600,'exact model trial max600 required')
        need(all(trial.get(k) is False for k in FALSE_FLAGS if k!='native_execution_authenticated') and
             trial.get('fingerprint_scope')=='SELECTED_SOURCE_FILES_NOT_FULL_CLOSURE' and
             trial.get('parent_admission_checked_by_body') is False,'known local-only qualification scope required')
        if life is not None:
            need(all(trial[k]==life[k] for k in ('pid','parent_pid','nonce','seed','scenario')),'worker/lifecycle identities must agree')
            if final:
                need(tb==lb and (p,s)==(lp,ls) and trial.get('provider_closed') is life['provider_closed'],'final receipts must agree')
            else:
                need(lb[0]<=tb[0] and lb[1]<=tb[1] and
                     (life['provider_closed'] is not True or trial.get('provider_closed') is True),'later trial cannot regress earlier progress/cleanup')
        if p is not None:reported=False
        if trial.get('source_context') is None:
            need(p is not None or bool(s),'missing source fingerprint requires a reported failure')
            unavailable.append('recorded-trial.json:source_context')
        else:need(trial['source_context']==_source_snapshot(),'present conflicting source fingerprint rejected')
        created=life['policy_created'] if life is not None else trial.get('model_test_double') is not None
        runtime=trial.get('onnxruntime')
        if created:
            need(trial.get('model_test_double') is False and trial.get('injected_session') is False,'test-double/injected policy rejected')
            if runtime is None:
                need(p is not None or bool(s),'missing runtime metadata requires a producer failure')
                unavailable.append('recorded-trial.json:onnxruntime')
            else:need(runtime==dict(version='1.20.1',real_session=True,providers=['CPUExecutionProvider'],session_class=REAL_SESSION),'present conflicting session metadata rejected')
        else:
            need(tb==[0,0] and trial.get('model_test_double') is None and trial.get('injected_session') is None and p is not None and
                 isinstance(runtime,dict) and set(runtime)=={'version','real_session','providers','session_class'} and
                 runtime['version'] in (None,'1.20.1') and runtime['real_session'] is False and
                 runtime['providers'] is None and runtime['session_class'] is None,'uncreated session retains reported zero without invented runtime')
        need(trial.get('provider_closed') is None or type(trial['provider_closed']) is bool,'typed known/unknown trial cleanup required')
        if life is not None and life['provider_received']:need(type(trial.get('provider_closed')) is bool,'received provider cleanup cannot become unknown')
    result=dict(protocol='recorded-official-diagnostic-receiver-v1',status='INCOMPLETE_EVIDENCE',
        **{k:who[k] for k in ('pid','parent_pid','nonce','seed','scenario')},
        reported_inference_bounds=tb if tb is not None else lb,lifecycle_reported_inference_bounds=lb,
        trial_reported_inference_bounds=tb,verified_recording_inference_bounds=None,recording_structure_valid=False,
        producer_reported_body_success=reported,completed_frames=None,provider_closed=trial.get('provider_closed') if trial else life['provider_closed'],
        primary_error=p,secondary_errors=s,recording_verification=None,unavailable_evidence=unavailable,
        raw_rgb_observer_requested=trial.get('raw_rgb_observer_requested') if trial else None,
        reported_raw_rgb_observer_used=trial.get('raw_rgb_observer_used') if trial else None,
        raw_rgb_source_evidence_present=None,abort_metadata_available=False,abort_reported_completed_rows=None,
        private_task_state='UNKNOWN',new_model_processes=0,new_inferences=0,new_native_render_calls=0,
        **{k:False for k in FALSE_FLAGS},scope='Local receipt/byte consistency only. Success fields describe producer reports; native execution/session/calls require independent authentication. No scientific qualification or new model/native calls.')
    report=_optional(root/'recording/report.json',16*1024**2);manifest=_optional(root/'recording/manifest.json',4*1024**2)
    abort=_optional(root/'recording/abort.json',16*1024**2)
    for name,value in (('recording/report.json',report),('recording/manifest.json',manifest)):
        if value is None:unavailable.append(name)
    need(not (report is not None and abort is not None),'original and unavailable-report alternatives cannot coexist')
    active_bounds=tb if tb is not None else lb
    def correlate(bounds,rows):
        if tb is not None:need(bounds==tb,'available report/abort must match later trial inference bounds')
        if lb is not None:
            need(bounds==lb if final else lb[0]<=bounds[0] and lb[1]<=bounds[1],'report/abort cannot contradict available lifecycle progress')
            old_rows=life.get('completed_rows')
            if old_rows is not None:
                need(old_rows<=rows,'lifecycle cannot contain more committed rows than the original result')
                if final and old_rows<rows:
                    errors=manifest.get('recording_errors',[]) if manifest else []
                    need(any(e.startswith('observer STEP_COMMITTED:') for e in errors) or 'observer STEP_COMMITTED:' in (p or ''),
                         'final committed-row lag requires an explicit observer checkpoint failure')
    if report is not None:
        rb=_report(report,who);correlate(rb,report['completed_steps'])
        result.update(reported_inference_bounds=rb,completed_frames=report['completed_steps'],reported_scientific_outcome=report['outcome'])
        if trial is not None:
            need(trial.get('raw_rgb_observer_requested') is True and type(trial.get('provider_closed')) is bool,'persisted capture requires requested observer and received-provider cleanup')
            if report['trial_completed'] is False:need(p==_error(RuntimeError(report['error'])),'primary error must equal frozen bounded original-error serialization')
    if abort is not None:
        ab=_bounds(abort.get('actual_inference_bounds'));rows=abort.get('completed_rows')
        need(abort.get('protocol')=='original-full-s-report-unavailable-v1' and abort.get('original_report_available') is False and
             type(rows) is int and 0<=rows<=ab[0] and isinstance(abort.get('error'),str) and abort['error'], 'known bounded abort metadata required')
        correlate(ab,rows)
        result.update(abort_metadata_available=True,abort_reported_completed_rows=rows,reported_inference_bounds=ab)
    if manifest is not None:
        need((manifest.get('seed'),manifest.get('scene'),manifest.get('max_steps'))==(who['seed'],who['scenario'],600), 'available manifest must bind registered case/max600')
        from .full_s_failure_capture import _context
        need(manifest.get('source_context')==_context(),'available manifest source context required')
        if abort is not None:
            need(manifest.get('protocol')=='full-s-aborted-failure-recording-v1' and manifest.get('original_report_available') is False and
                 manifest.get('report_sha256')==hashlib.sha256(_receipt_bytes(root/'recording/abort.json',16*1024**2)).hexdigest(),'abort/manifest byte binding required')
        else:need(manifest.get('protocol')=='full-s-failure-recording-v1' and manifest.get('original_report_available') is True,'known original-report manifest required')
    if trial is not None and (report is not None or abort is not None or manifest is not None):
        need(trial.get('raw_rgb_observer_requested') is True,'surviving recording cannot claim no observer request')
    binding=trial.get('recording_binding') if trial else None
    if binding is not None:
        need(isinstance(binding,dict) and set(binding)=={'manifest_sha256','report_sha256','process_uuid'} and
             _hex(binding['manifest_sha256'],64) and _hex(binding['report_sha256'],64) and _hex(binding['process_uuid'],32),'typed report/manifest/UUID binding required')
        if report is not None:need(binding['process_uuid']==report['process_uuid'] and binding['report_sha256']==hashlib.sha256(_receipt_bytes(root/'recording/report.json',16*1024**2)).hexdigest(),'available original report binding required')
        if manifest is not None:need(binding['manifest_sha256']==hashlib.sha256(_receipt_bytes(root/'recording/manifest.json',4*1024**2)).hexdigest(),'available manifest binding required')
    if report is None or manifest is None:
        if reported is True:result['producer_reported_body_success']=True  # Reported only; missing data stays incomplete.
        return result
    from .full_s_failure_capture import verify_recording
    verified=verify_recording(root/'recording')
    if trial is None:return result
    need(binding is not None,'worker must bind exact original report/manifest/UUID')
    if trial.get('recording_verification') is None:
        need(p is not None or bool(s),'missing verification receipt requires producer failure')
        unavailable.append('recorded-trial.json:recording_verification')
    else:need(trial['recording_verification']==verified,'present original byte verification must match')
    if trial.get('original_report_file') is None:
        need(p is not None or bool(s),'missing report pointer requires producer failure')
        unavailable.append('recorded-trial.json:original_report_file')
    else:need(trial['original_report_file']=='recording/report.json','canonical original report pointer required')
    evidence=any('source/road' in package['blobs'] or 'source/wide' in package['blobs'] for package in manifest['packages'].values())
    need(trial.get('raw_rgb_source_evidence_present') is evidence and trial.get('raw_rgb_observer_used') is (True if evidence else None),
         'observer request, verified source bytes and callback outcome must agree')
    result.update(recording_structure_valid=True,verified_recording_inference_bounds=verified['actual_inference_bounds'],
        recording_verification=verified,recording_binding=binding,raw_rgb_source_evidence_present=evidence)
    if not unavailable:
        if reported is True:need(verified['recording_status']=='COMPLETE' and report['trial_completed'] is True and trial['provider_closed'] is True,'reported completed diagnostic needs full recording/cleanup')
        result['status']='COMPLETE_DIAGNOSTIC' if reported is True else 'PARTIAL_DIAGNOSTIC'
    return result
