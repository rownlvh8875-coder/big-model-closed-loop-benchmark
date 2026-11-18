"""Complete/partial recorded official-body evidence. CPU readers only.

Session and inference metadata are reported by the producer. This reader never
authenticates a native run or turns local structure into scientific qualification.
"""
from pathlib import Path
import hashlib
import json
import sys
from .full_s_recorded_worker import need,_read_receipt,_receipt_bytes,_source_snapshot

FALSE_FLAGS=('origin_authenticated','native_execution_authenticated','model_camera_qualified',
    'hardware_gpu_qualified','physical_optics_validated','carla_validated','all_four_validation_tracks_passed')
REAL_SESSION='onnxruntime.capi.onnxruntime_inference_collection.InferenceSession'


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


def _identity(life):
    need(life.get('protocol')=='recorded-full-s-worker-lifecycle-v1','known worker lifecycle required')
    need(all(type(life.get(k)) is int and life[k]>0 for k in ('pid','parent_pid')) and life['pid']!=life['parent_pid'] and
         isinstance(life.get('nonce'),str) and len(life['nonce'])==32 and life['nonce']!='0'*32 and
         all(c in '0123456789abcdef' for c in life['nonce']) and type(life.get('seed')) is int and
         life['seed'] in (20261109,20261110) and life.get('scenario') in ('s_curve_left_right','s_curve_right_left'),
         'registered case and typed worker/PID/nonce identity required')
    bounds=life.get('inference_bounds')
    need(isinstance(bounds,list) and len(bounds)==2 and all(type(v) is int for v in bounds) and
         0<=bounds[0]<=bounds[1]<=600 and bounds[1]-bounds[0]<=1,'conservative bounded reported calls required')
    need(life.get('mode') is None and life.get('fixture_policy_audit_bounds') is None and
         life.get('counter_scope') is None and life.get('official_inference_bounds') is None,
         'synthetic canary lifecycle is not official model evidence')
    return bounds


def _errors(value,*,required):
    need(not required or all(k in value for k in ('primary_error','secondary_errors')),'explicit final error fields required')
    primary=value.get('primary_error');secondary=value.get('secondary_errors')
    need(primary is None or isinstance(primary,str) and 0<len(primary)<=4096,'bounded explicit primary error required')
    need(secondary is None and not required or isinstance(secondary,list) and len(secondary)<=64 and
         all(isinstance(e,str) and len(e)<=4096 for e in secondary),'bounded secondary errors required')
    return primary,secondary


def inspect_trial(root):
    root=Path(root).absolute()
    need(root.is_dir() and not root.is_symlink() and all(not p.is_symlink() for p in root.parents),
         'nonsymlink recorded trial directory required')
    life=_read_receipt(root/'recorded-trial-lifecycle.json')
    bounds=_identity(life)
    primary,secondary=_errors(life,required=False)
    result=dict(protocol='recorded-official-diagnostic-receiver-v1',status='INCOMPLETE_EVIDENCE',
        seed=life['seed'],scenario=life['scenario'],pid=life['pid'],parent_pid=life['parent_pid'],nonce=life['nonce'],
        reported_inference_bounds=bounds,verified_recording_inference_bounds=None,
        recording_structure_valid=False,body_execution_succeeded=False,completed_frames=None,
        provider_closed=life.get('provider_closed'),primary_error=primary,secondary_errors=secondary,
        recording_verification=None,unavailable_evidence=[],new_model_processes=0,new_inferences=0,
        new_native_render_calls=0,private_task_state='UNKNOWN',**{k:False for k in FALSE_FLAGS},
        scope='Local receipts/bytes only. Producer session/call metadata is not external run authentication or scientific qualification. No new model/native calls.')
    trial=_optional(root/'recorded-trial.json',4*1024**2)
    if trial is None:
        result['unavailable_evidence'].append('recorded-trial.json')
        return result
    need(trial.get('protocol')=='recorded-full-s-worker-trial-v1' and
         all(trial.get(k)==life[k] for k in ('pid','parent_pid','nonce','seed','scenario')) and
         type(trial.get('max_steps')) is int and trial['max_steps']==600 and trial.get('actual_inference_bounds')==bounds,
         'same official-body identity/max600/reported inference bounds required')
    need(all(trial.get(k) is None for k in ('mode','fixture_policy_audit_bounds','official_inference_bounds',
         'official_model_processes','policy_data','graph_feed_attested')),'synthetic policy metadata cannot certify an official diagnostic')
    primary,secondary=_errors(trial,required=True)
    need(_errors(life,required=True)==(primary,secondary),'lifecycle and worker must preserve the same primary/secondary failures')
    need(life.get('status') in ('RECORDED','FAILED_OR_INCOMPLETE') and
         (life['status']=='RECORDED')==(primary is None) and (primary is not None or not secondary),
         'honest final lifecycle/error state required')
    need(trial.get('provider_closed') is life.get('provider_closed') and
         type(life.get('policy_created')) is bool and type(life.get('provider_received')) is bool and
         all(trial.get(k) is False for k in ('origin_authenticated','model_camera_qualified','hardware_gpu_qualified',
             'physical_optics_validated','carla_validated','all_four_validation_tracks_passed')),
         'consistent provider and scoped qualification flags required')
    need(trial.get('source_context')==_source_snapshot() and
         trial.get('fingerprint_scope')=='SELECTED_SOURCE_FILES_NOT_FULL_CLOSURE' and
         trial.get('parent_admission_checked_by_body') is False,'known selected source context and external parent admission scope required')
    if life['policy_created']:
        need(trial.get('model_test_double') is False and trial.get('injected_session') is False and
             trial.get('onnxruntime')==dict(version='1.20.1',real_session=True,providers=['CPUExecutionProvider'],session_class=REAL_SESSION),
             'explicit official-session metadata required; test double/injected sessions rejected')
    else:
        need(bounds==[0,0] and trial.get('model_test_double') is None and trial.get('injected_session') is None and
             trial.get('onnxruntime')==dict(version=None,real_session=False,providers=None,session_class=None) and primary is not None,
             'uncreated policy must retain known zero reported calls without inventing a session')
    if life['provider_received']:
        need(life.get('provider_created') is True and life.get('provider_close_attempted') is True and
             life.get('body_provider_close_attempted') is True and type(life.get('provider_closed')) is bool and
             (life['provider_closed'] or primary is not None),'received provider must have honest body cleanup')
    else:
        need(life.get('body_provider_close_attempted') is False and life.get('provider_closed') in (False,None) and primary is not None,
             'unreceived provider cleanup must remain unavailable or unattempted')
    result.update(primary_error=primary,secondary_errors=secondary)
    report=_optional(root/'recording/report.json',16*1024**2)
    manifest=_optional(root/'recording/manifest.json',4*1024**2)
    for name,value in (('recording/report.json',report),('recording/manifest.json',manifest)):
        if value is None:result['unavailable_evidence'].append(name)
    if report is None or manifest is None:
        need(life['status']=='FAILED_OR_INCOMPLETE' and primary is not None,'successful body cannot omit original report/manifest')
        need(trial.get('recording_verification') is None and trial.get('recording_binding') is None and
             trial.get('original_report_file') in (None,'recording/report.json'),'missing recording must not invent verification/binding')
        return result
    from .full_s_failure_capture import verify_recording
    from .full_s_receipts import validate_trajectory
    verified=verify_recording(root/'recording')
    need(report.get('process_id')==life['pid'] and (report.get('seed'),report.get('scenario'),report.get('max_steps'))==
         (life['seed'],life['scenario'],600) and report.get('actual_inference_bounds')==bounds and
         report.get('model_test_double') is False and report.get('injected_session') is False,
         'original official-report worker/case/audit binding required')
    expected=dict(manifest_sha256=hashlib.sha256(_receipt_bytes(root/'recording/manifest.json',4*1024**2)).hexdigest(),
        report_sha256=hashlib.sha256(_receipt_bytes(root/'recording/report.json',16*1024**2)).hexdigest(),process_uuid=report['process_uuid'])
    need(trial.get('recording_binding')==expected and trial.get('recording_verification')==verified and
         trial.get('original_report_file')=='recording/report.json','exact report/manifest/UUID worker binding required')
    evidence=any('source/road' in p['blobs'] or 'source/wide' in p['blobs'] for p in manifest['packages'].values())
    requested=trial.get('raw_rgb_observer_requested')
    need(type(requested) is bool and trial.get('raw_rgb_source_evidence_present') is evidence and
         trial.get('raw_rgb_observer_used') is (True if evidence else None if requested else False),
         'raw callback request/evidence/unknown must stay distinct')
    validate_trajectory(report,life['seed'],life['scenario'])
    if report.get('trial_completed') is False:
        need(primary is not None and report.get('error') and report['error'] in primary,'original scientific error must remain primary')
    successful=life['status']=='RECORDED'
    if successful:
        need(report.get('trial_completed') is True and verified['recording_status']=='COMPLETE' and
             life.get('provider_closed') is True and requested is True and evidence,
             'completed diagnostic requires complete bytes, original result and provider cleanup')
    result.update(status='COMPLETE_DIAGNOSTIC' if successful else 'PARTIAL_DIAGNOSTIC',
        recording_structure_valid=True,body_execution_succeeded=successful,
        verified_recording_inference_bounds=verified['actual_inference_bounds'],completed_frames=report['completed_steps'],
        recording_verification=verified,reported_scientific_outcome=report['outcome'],recording_binding=expected)
    return result
