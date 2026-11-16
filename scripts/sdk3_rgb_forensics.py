"""Post-episode full-RGB diagnosis; equality never repairs the original gate."""
from __future__ import annotations
import json
from pathlib import Path
from scripts import panda_sdk3_runtime as p
from scripts.native_mdv3_rgb_pixel_capture import BoundedNativeRGBCapture,SHAPE,RAW_NBYTES,CAMERAS
from scripts.compare_native_mdv3_rgb_pixels import read_verified_pixels,summarize_pixel_difference,MAX_COMPRESSED_BYTES
from scripts.compare_fresh_native_mdv3 import compare_fresh_trials
from scripts.aggregate_original_mdv3_current_recheck import MODEL_SHA256,first_divergence_timeline

PRODUCER_SHA='ddaf0510a775c3a44c908bb4dedf4879ae88bfcb80e1f2d022a8b513a4f42427'
SEED=20261110
SCENE='s_curve_left_right'


class FullEpisodeRGBCapture(BoundedNativeRGBCapture):
    """Same reference-only observer; legacy constructor/default remain untouched."""
    def __init__(self):
        super().__init__()
        self.max_steps=12


def run_full_rgb_trial(*,raw_rgb_dir,**kwargs):
    """Run frozen producer bytecode in private globals with one observer factory.

    No original module/function global is patched. This is an instrumented
    diagnostic and retains the original source pin and default execution.
    """
    from types import FunctionType
    from scripts import native_mdv3_repeat_trial as native
    p.need(raw_rgb_dir is not None,'explicit full-RGB output required')
    p.need(p.digest(Path(native.__file__))==PRODUCER_SHA,'frozen original trial source')
    original=native.run_trial
    namespace=dict(original.__globals__,BoundedNativeRGBCapture=FullEpisodeRGBCapture)
    observed=FunctionType(original.__code__,namespace,original.__name__,original.__defaults__,original.__closure__)
    observed.__kwdefaults__=dict(original.__kwdefaults__ or {})
    return observed(raw_rgb_dir=raw_rgb_dir,**kwargs)


def _manifest(folder,report):
    value=json.loads((folder/'manifest.json').read_text())
    p.need(value.get('status')=='CPU_ONLY_NATIVE_RGB_FIRST_STEPS_RETAINED' and value.get('probe_is_not_uninstrumented_original_strict_gate') is True and value.get('additional_gpu_readback_or_render_tasks') is False and value.get('original_pssm_chase_tasks_preserved') is True and value.get('camera_capture_semantics')=='original_perceive_sequential','original CPU-only observer contract')
    p.need(value.get('seed')==SEED and value.get('scenario')==SCENE and value.get('model_sha256')==MODEL_SHA256 and value.get('process_uuid')==report['process_uuid'],'raw capture identity')
    p.need(value.get('original_native_image_shape_hwc')==list(SHAPE) and value.get('total_native_onnx_steps')==12 and value.get('captured_step_count')==12,'complete full12 manifest')
    rows=value.get('images');expected=[(step,camera) for step in range(1,13) for camera in CAMERAS]
    p.need(isinstance(rows,list) and [(r.get('step'),r.get('camera')) for r in rows]==expected,'ordered complete unique24 images')
    for row,(step,camera) in zip(rows,expected):
        p.need(row.get('file')==f'step-{step:02d}-{camera}.rgb.zlib' and row.get('sha256')==report['frames'][step-1][f'source_{camera}_rgb_sha256'] and row.get('raw_bytes')==RAW_NBYTES and type(row.get('compressed_bytes')) is int and 0<row['compressed_bytes']<=MAX_COMPRESSED_BYTES,'source-bound bounded RGB member')
    return rows


def analyze_pair(folder:Path,arm:str)->dict:
    folder=Path(folder);p.need(arm in ('control','full_rgb'),'registered diagnostic arm')
    reports=[json.loads((folder/'pair'/f'run-{i}'/'run.json').read_text()) for i in (0,1)]
    for row in reports:
        p.need(row.get('status')=='DIAGNOSTIC_EXECUTED' and row.get('model_sha256')==MODEL_SHA256 and row.get('selected_sdk_sha256')==p.SDK_SHA and row.get('sdk_load_order')=='core-first','actual pinned SDK/model trial')
        p.need(row.get('seed')==SEED and row.get('scenario')==SCENE and row.get('initial_fraction')==.12 and row.get('requested_steps')==row.get('completed_steps')==12 and len(row.get('frames',[]))==12,'complete registered diagnostic condition')
        p.need(row.get('camera_capture_mode')=='native_MetaDrive_perceive_sequential_per_step','original sequential native capture mode')
        p.need(row.get('pssm_update_preserved') is True and row.get('gpu_hdr_extraction') is False and row.get('camera_convergence_attempts')==0 and row.get('camera_pixel_tolerance')==0 and row.get('camera_image_interpolation_or_replay') is False and row.get('model_scoring_allowed') is False and row.get('real_vehicle_testing') is False,'unchanged original rendering controls')
        evidence='ORIGINAL_PSSM_WITH_OPT_IN_CPU_RGB_RETENTION_PROBE' if arm=='full_rgb' else 'UNMODIFIED_METADRIVE_NEW_FRAME_OFFICIAL_ONNX_DIAGNOSTIC'
        p.need(row.get('trial_evidence')==evidence,'control/probe evidence separation')
        audit=row.get('raw_rgb_pixel_audit')
        if arm=='full_rgb':p.need(isinstance(audit,dict) and audit.get('enabled') is True and audit.get('captured_step_count')==12 and audit.get('total_steps')==12 and audit.get('is_uninstrumented_strict_repeatability_gate') is False,'full12 opt-in trial receipt')
        else:p.need(audit is None,'uninstrumented control has no observer')
    strict=compare_fresh_trials(*reports);timeline=first_divergence_timeline(*reports)
    first=timeline['first_native_road_or_wide_rgb_mismatch_step'];prior_equal=None
    if first and first>1:
        keys=('time_s','world_x_m','world_y_m','heading_rad','raw_action_sha256','state_after_step_sha256')
        prior_equal=all(reports[0]['frames'][first-2][k]==reports[1]['frames'][first-2][k] for k in keys)
    metrics=None
    if arm=='full_rgb':
        roots=[folder/'pair'/f'run-{i}'/'rgb' for i in (0,1)];manifests=[_manifest(root,row) for root,row in zip(roots,reports)];metrics={camera:[] for camera in CAMERAS}
        measured=[]
        for step in range(1,13):
            for offset,camera in enumerate(CAMERAS):
                index=(step-1)*2+offset
                pixels=[read_verified_pixels(root,manifest[index]) for root,manifest in zip(roots,manifests)]
                result=summarize_pixel_difference(*pixels)
                same_sha=reports[0]['frames'][step-1][f'source_{camera}_rgb_sha256']==reports[1]['frames'][step-1][f'source_{camera}_rgb_sha256']
                p.need(result['bit_exact']==same_sha,'exact pixels/source digest coherence')
                metrics[camera].append(dict(step=step,**result))
                if not result['bit_exact']:measured.append(step)
        p.need(min(measured,default=None)==first,'first raw pixels/source mismatch coherence')
    else:
        p.need(all(not (folder/'pair'/f'run-{i}'/'rgb').exists() for i in (0,1)),'control cannot contain retained RGB')
    return dict(status='DIAGNOSTIC_PAIR_RECOMPUTED',arm=arm,seed=SEED,scenario=SCENE,strict_pair_pass=strict['exact_repeated_execution_gate_passed'],strict_verdict=strict,first_raw_source_diff_step=first,timeline=timeline,prior_step_pose_action_state_equal=prior_equal,pixel_metrics=metrics,original_matrix_passed=3,original_matrix_total=4,original_matrix_gate_passed=False,repair_proven=False,unique_renderer_cause_proven=False,stage7_complete=False,model_scoring_allowed=False,real_vehicle_testing=False,observer_may_perturb_timing=arm=='full_rgb')
