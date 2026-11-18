"""Pinned real canary versus historical first graph-input bytes; no native run."""
from pathlib import Path
from types import FunctionType
import hashlib
import json
import subprocess
import sys
from .full_s_recorded_worker import need,_fresh,_read_receipt,_receipt_bytes,_write_receipt

ROOT=Path(__file__).resolve().parents[1]
CANARY_SOURCE='d05d971290a46e403c635b6efc798aca28a48794'
CANARY_ACTIVATION='c38b8d23c2361fc2a9db23839b57e77030291cf9'
CANARY_RUN=44262872996
CANARY_ARTIFACT=14408877649
CANARY_BYTES=5012494
CANARY_SHA='e66820ded0ab60e2fc488d00350fbe6003f19a13c31b7056a5bb81d6a1a52b49'
MODEL_SHA='35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199'
CASE=(20261109,'s_curve_left_right')
FIELDS=('source_road_rgb_sha256','source_wide_rgb_sha256','road_frame_sha256','wide_frame_sha256','new_img_sha256')


def compare_first_step(recording,reports):
    from .full_s_failure_capture import verify_recording
    verified=verify_recording(recording)
    canary=_read_receipt(Path(recording)/'report.json',16*1024**2)
    need((canary.get('seed'),canary.get('scenario'))==CASE and canary.get('max_steps')==2 and
         canary.get('model_test_double') is True and canary.get('injected_session') is True and
         verified['recording_status']=='COMPLETE' and verified['completed_steps']==2,'complete two-step synthetic-policy canary recording required')
    need(isinstance(reports,list) and len(reports)==2 and
         len({r.get('process_uuid') for r in reports})==2 and len({r.get('process_id') for r in reports})==2,
         'two independent original graph audit identities required')
    rows=[]
    for index,original in enumerate(reports):
        need(original.get('protocol')=='full-s-closed-loop-v1' and original.get('max_steps')==600 and
             (original.get('seed'),original.get('scenario'))==CASE and original.get('initial_state')==canary['initial_state'] and
             original.get('geometry')==canary['geometry'] and original.get('model_sha256')==MODEL_SHA and
             original.get('real_ort_session') is True and original.get('model_test_double') is False and original.get('injected_session') is False,
             'original real-model same-case/initial-pose/geometry metadata required')
        frames=original.get('frames');audits=original.get('inference_audit_rows')
        need(isinstance(frames,list) and frames and isinstance(audits,list) and audits and
             frames[0].get('step')==1 and frames[0].get('new_img_sha256')==audits[0].get('new_img_sha256'),
             'original first graph feed audit/frame binding required')
        for field in FIELDS:
            value=frames[0].get(field)
            need(isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value),
                 'original first input requires every valid source/canvas/I420 digest')
        matches={field:canary['frames'][0][field]==frames[0][field] for field in FIELDS}
        rows.append(dict(original_trial=index,process_id=original['process_id'],process_uuid=original['process_uuid'],matches=matches,
            first_input_matches=all(matches.values()),original_graph_feed_sha256=audits[0]['new_img_sha256']))
    return dict(protocol='recorded-canary-first-input-continuity-v1',seed=CASE[0],scenario=CASE[1],
        first_input_continuity_confirmed=all(row['first_input_matches'] for row in rows),
        original_first_graph_inputs_matched=sum(row['first_input_matches'] for row in rows),comparisons=rows,
        actual_canary_camera_pairs=2,first_packed_input_sha256=canary['frames'][0]['new_img_sha256'],
        canary_actual_graph_feed_attested=False,later_model_pixels_verified=False,
        new_model_processes=0,new_inferences=0,new_native_render_calls=0,origin_authenticated=False,
        model_camera_qualified=False,hardware_gpu_qualified=False,physical_optics_validated=False,
        carla_validated=False,all_four_validation_tracks_passed=False,
        scope='First input bytes only. Canary policy/state/action are synthetic. Historical graph-feed matches require separate immutable artifact origins; no repeatability/quality/native qualification.')


def export_canary_source(out):
    """Export local trusted Git bytes for hashing only; never import/exported code."""
    from scripts.run_recorded_worker_canary import source_manifest
    from .recorded_worker_canary import check_source_map
    mapping=source_manifest(CANARY_SOURCE)
    # Current frozen Python reader dependencies must still equal reviewed bytes.
    for name,digest in mapping.items():
        if name.endswith('.py'):
            need(hashlib.sha256(_receipt_bytes(ROOT/name,16*1024**2)).hexdigest()==digest,
                 'current existing Python reader must equal approved canary source: '+name)
    out=_fresh(out)
    for name,digest in mapping.items():
        raw=subprocess.check_output(['git','show',CANARY_SOURCE+':'+name],cwd=ROOT,timeout=30)
        need(hashlib.sha256(raw).hexdigest()==digest,'trusted Git source export must match approved full map')
        path=out/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
        path.chmod(0o444)
    return out,check_source_map(out,mapping)


def stage_historical_metadata(evidence,out):
    """Only the verified byte snapshots enter this private replay namespace."""
    from scripts.verify_saved_camera_inputs import CASES
    names=['artifacts.json','independent-receiver.json']+[str(s)+'-'+c+'/probe.json' for s,c in CASES]
    evidence=Path(evidence);snapshots={};hashes={}
    for name in names:
        path=evidence/name;relative=path.relative_to(ROOT).as_posix()
        expected=subprocess.check_output(['git','show',CANARY_SOURCE+':'+relative],cwd=ROOT,timeout=30)
        actual=_receipt_bytes(path,4*1024**2)
        need(actual==expected,'historical metadata must equal the pinned trusted Git bytes: '+relative)
        snapshots[name]=actual;hashes[relative]=hashlib.sha256(actual).hexdigest()
    out=_fresh(out)
    for name,raw in snapshots.items():
        path=out/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
        path.chmod(0o444)
    return out,hashes


def scoped_historical_reader(evidence):
    from scripts import verify_saved_camera_inputs as historical
    return _scoped(historical.run,EVIDENCE=Path(evidence),
        replay_case=_scoped(historical.replay_case,EVIDENCE=Path(evidence)))


def _scoped(function,**changes):
    value=FunctionType(function.__code__,dict(function.__globals__,**changes),function.__name__,
        function.__defaults__,function.__closure__)
    value.__kwdefaults__=dict(function.__kwdefaults__ or {})
    return value


def run(canary_zip,historical_cohort,out):
    """Authenticate known immutable archives and compare without network/model calls."""
    from . import recorded_worker_canary as canary
    from scripts import verify_saved_camera_inputs as historical
    need(sys.platform=='linux','pinned native Cloud receipt replay requires Linux; trial/archive readers are portable')
    canary_zip=Path(canary_zip);historical_cohort=Path(historical_cohort)
    need(canary_zip.is_file() and not canary_zip.is_symlink() and canary_zip.stat().st_size==CANARY_BYTES,
         'exact pinned real canary artifact extent required')
    # Neither input tree may contain output, even through normalized path aliases.
    out=Path(out).absolute()
    for source in (canary_zip.resolve().parent,historical_cohort.resolve()):
        need(not out.resolve().is_relative_to(source) and not source.is_relative_to(out.resolve()),
             'continuity output must be outside immutable input trees')
    out=_fresh(out)
    exported,map_sha=export_canary_source(out/'pinned-reader-source')
    bundle=canary.extract_archive(canary_zip,out/'canary-bundle',expected_sha256=CANARY_SHA)
    # Scoped function globals: only the source map's byte-root changes. Imported
    # producer/reader Python is the current, independently hash-checked code.
    verdict=_scoped(canary.validate_native_bundle,ROOT=exported)(bundle)
    need(verdict['source']==CANARY_SOURCE and verdict['activation']==CANARY_ACTIVATION and
         verdict['run_id']==str(CANARY_RUN) and verdict['source_map_sha256']==map_sha,
         'actual pinned camera canary identity/source required')
    staged,metadata_hashes=stage_historical_metadata(historical.EVIDENCE,out/'pinned-historical-metadata')
    replay=scoped_historical_reader(staged)(historical_cohort)
    inventory=_read_receipt(staged/'artifacts.json',4*1024**2)
    name='sdk3-four-validation-full-s-20261118-02-'+str(CASE[0])+'-'+CASE[1]
    meta=[row for row in inventory['artifacts'] if row['name']==name]
    need(len(meta)==1,'exact historical case artifact required')
    origin,snapshot=historical.authenticate_archive(historical_cohort/(name+'.zip'),meta[0])
    import io,zipfile
    with zipfile.ZipFile(io.BytesIO(snapshot)) as archive:
        from .full_s_failure_capture import _decode
        originals=[_decode(historical.read_member(archive,f'pair/run-{i}/run.json',8*1024**2)) for i in (0,1)]
    result=compare_first_step(bundle/'native/observed-trial/recording',originals)
    result.update(canary_origin=dict(run_id=CANARY_RUN,artifact_id=CANARY_ARTIFACT,source=CANARY_SOURCE,
        activation=CANARY_ACTIVATION,archive_sha256=CANARY_SHA,archive_bytes=CANARY_BYTES),
        historical_origin=origin,pinned_archive_origins_verified=True,historical_metadata_sha256=metadata_hashes,
        canary_source_map_sha256=map_sha,
        prior_all_cases_first_inputs_bound=replay['first_model_inputs_bound'],
        prior_full_s_passed_cases=replay['original_full_s_passed_cases'],
        prior_strict_repeat_passed_cases=replay['original_strict_repeat_passed_cases'],private_task_state='UNKNOWN')
    need(not any(n.split('.')[0] in ('panda3d','direct','metadrive','onnxruntime','carla') for n in sys.modules),
         'continuity verification must remain CPU readers only')
    _write_receipt(out/'continuity.json',result)
    _write_receipt(out/'historical-replay.json',replay)
    return result
