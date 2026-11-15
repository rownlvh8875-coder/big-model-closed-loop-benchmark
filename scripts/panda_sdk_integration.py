"""Run SDK coverage, retained-image binding and inactive execution assessments."""
import argparse,json,subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
from pathlib import Path
from scripts import panda_sdk_coverage as coverage
from scripts import panda_sdk_image_binding as image
LIVE_GATES=('MAPPED_NEW_ABI_NOT_QUALIFIED','EARLY_INSTALL_BEFORE_FIRST_CONTEXT_NOT_QUALIFIED','TEXTURE_GSG_ALLOCATION_LIFETIMES_NOT_QUALIFIED','FRESH_CACHE_IDENTITY_HANDOFF_NOT_QUALIFIED','DRIVER_AND_GPU_WRITE_READ_FRESHNESS_NOT_QUALIFIED','AUTHENTICATED_PROCESS_WINDOW_SINK_RECEIPTS_MISSING','FRESH_REVIEWED_BOUNDED_CANARY_CONTRACT_MISSING')

def assess_execution(selected,binding):
    for value,schema in ((selected,'panda-selected-sdk-coverage-v1'),(binding,'panda-sdk-image-binding-assessment-v1')):
        coverage.need(type(value) is dict and value.get('schema')==schema and value.get('candidate_sha256')==coverage.CANDIDATE,'matching exact candidate assessments required')
        coverage.need(value.get('native_admitted') is False and type(value.get('new_native_runs')) is int and value['new_native_runs']==0,'data-only assessment required')
        coverage.need(type(value.get('blockers')) is list and all(type(x) is str and x for x in value['blockers']),'explicit assessment blockers required')
    blockers=['coverage:'+x for x in selected['blockers']]+['image:'+x for x in binding['blockers']]+list(LIVE_GATES)
    # These reports cannot supply actual mapped/runtime/driver/process evidence.
    # Even caller-supplied ready flags cannot fill those independently missing gates.
    return dict(schema='panda-sdk-native-execution-assessment-v1',status='BLOCKED_NOT_EXECUTED',candidate_sha256=coverage.CANDIDATE,blockers=blockers,execution_request_active=False,native_allowance=0,actual_native_processes=0,new_native_runs=0,official_model_calls=0,official_ort_sessions=0,new_gl_calls=0,planned_official_cohort=dict(seeds=[20261109,20261110],scenes=['s_curve_left_right','s_curve_right_left'],steps=12,hz=20,speed_mps=8,independent_runs_per_condition=2,conditions=4,independent_processes=8),official_model=dict(id='1365126a-e71e-4778-be00-8ab92dc82c09/12864/big_driving_supercombo.onnx',sha256='35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199'),inherited_strict_result='0/4 FAIL',new_official_result='NOT_RUN',runtime_binding_qualified=False,native_admitted=False,stage7_complete=False)

def run(out):
    out=coverage.stage.canonical(out);coverage.need(not out.exists(),'existing joint assessment preserved');out.mkdir(parents=True)
    now=lambda:datetime.now(timezone(timedelta(hours=9))).isoformat()
    result=dict(schema='panda-sdk-joint-assessment-v1',checked_at_kst=now(),status='FAILED_OR_INCOMPLETE',candidate_sha256=coverage.CANDIDATE,native_admitted=False,new_native_runs=0,stage7_complete=False)
    path=out/'result.json'
    def save():path.write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(coverage.audit_sdk,out/'coverage');b=pool.submit(image.inspect_retained_image,out/'image')
            selected=a.result();binding=b.result()
        execution=assess_execution(selected,binding);(out/'native-assessment.json').write_text(json.dumps(execution,indent=2)+'\n')
        paths=('coverage/coverage.json','image/image-binding.json','native-assessment.json')
        result.update(status='ASSESSMENTS_COMPLETE_CANDIDATE_BLOCKED_NATIVE_NOT_RUN',checked_at_kst=now(),assessments={name:dict(path=name,sha256=coverage.digest((out/name).read_bytes()),nbytes=(out/name).stat().st_size) for name in paths},coverage_blockers=selected['blockers'],image_blockers=binding['blockers'],execution_blockers=execution['blockers'],actual_native_processes=0,official_model_calls=0,inherited_strict_result='0/4 FAIL',new_official_result='NOT_RUN')
        save();return result
    except BaseException as exc:result.update(failure=type(exc).__name__+': '+str(exc),checked_at_kst=now());save();raise

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args(argv)
    try:r=run(args.out);print(json.dumps(r));return 0
    except (ValueError,OSError,subprocess.SubprocessError) as exc:print('joint assessment failed: '+str(exc));return 2
if __name__=='__main__':raise SystemExit(main())
