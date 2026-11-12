"""Pinned saved-byte CPU interventions; never native or model execution."""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import stat
import subprocess
import sys
import zipfile

import numpy as np

from bigbench import first_divergence as capture
from bigbench.image_adapter import camera_pair_to_model
from bigbench.optical_calibration import PinholeIntrinsics, PinholeRectifier

SOURCE = '582cc594d127e9cde5ff3525e50c143f60285f75'
RUN_ID = 43149053427
ARTIFACT_ID = 13912454399
ARCHIVE_BYTES = 27428724
ARCHIVE_SHA = '370ef36862e3da5bf39064acc732ff1728b0a0a549b6fba77045ce7380a8c748'
REPORT_CAP = 1024 * 1024
CAMERAS = ('road', 'wide')
LIMITATION = ('CPU transform interventions on copied saved RGB only; no native/GPU/ORT/model '
              'execution or altered real graph feed. Pixel neighborhoods do not identify scene '
              'semantics or a unique GPU cause. State/fixed-feed snapshots are source-reconstructed. '
              'Pinned offline archive provenance is not live API authentication.')


def _image_pair(a, b):
    if (not isinstance(a,np.ndarray) or not isinstance(b,np.ndarray) or
        a.dtype!=np.uint8 or b.dtype!=np.uint8 or a.shape!=b.shape or
        a.ndim!=3 or a.shape[2]!=3 or min(a.shape[:2])<=0):
        raise ValueError('matching nonempty HWC uint8 RGB images required')


def pixel_locations(lhs, rhs):
    _image_pair(lhs,rhs)
    changed=np.any(lhs!=rhs,axis=2)
    if np.count_nonzero(changed)>4:raise ValueError('at most four changed raw pixels admitted')
    points=[]
    for y,x in np.argwhere(changed):
        x,y=int(x),int(y)
        x0,y0=max(0,x-2),max(0,y-2)
        x1,y1=min(lhs.shape[1]-1,x+2),min(lhs.shape[0]-1,y+2)
        points.append(dict(xy=[x,y],rgb_a=lhs[y,x].tolist(),rgb_b=rhs[y,x].tolist(),
            delta_rgb=(rhs[y,x].astype(np.int16)-lhs[y,x].astype(np.int16)).tolist(),
            patch_bounds_xyxy=[x0,y0,x1,y1],patch_a=lhs[y0:y1+1,x0:x1+1].tolist(),
            patch_b=rhs[y0:y1+1,x0:x1+1].tolist()))
    return points


def _transform(raw, intrinsics):
    pair,_=PinholeRectifier().rectify_pair(raw['road'],raw['wide'],
        road_intrinsics=intrinsics['road'],wide_intrinsics=intrinsics['wide'])
    return pair,camera_pair_to_model(pair.road,pair.wide)


def analyze_pair(raw_a, raw_b, intrinsics):
    for raw in (raw_a,raw_b):
        if not isinstance(raw,dict) or set(raw)!=set(CAMERAS):
            raise ValueError('exact Road/Wide pair required')
    if not isinstance(intrinsics,dict) or set(intrinsics)!=set(CAMERAS):
        raise ValueError('both retained intrinsics required')
    count=0
    for camera in CAMERAS:
        _image_pair(raw_a[camera],raw_b[camera])
        if raw_a[camera].shape!=(604,964,3):raise ValueError('registered raw shape required')
        count+=int(np.count_nonzero(np.any(raw_a[camera]!=raw_b[camera],axis=2)))
    if count>4:raise ValueError('at most four changed raw pixels admitted')
    points=[]
    for camera in CAMERAS:
        for point in pixel_locations(raw_a[camera],raw_b[camera]):
            points.append(dict(point,camera=camera,pixel_id=len(points)))
    _,baseline=_transform(raw_a,intrinsics)
    _,target=_transform(raw_b,intrinsics)
    rows=[];matching=[];single_sum=np.zeros_like(baseline,dtype=np.int64)
    joint=None
    for mask in range(1<<count):
        raw={camera:raw_a[camera].copy() for camera in CAMERAS}
        selected=[]
        for index,point in enumerate(points):
            if mask&(1<<index):
                camera=point['camera'];x,y=point['xy']
                raw[camera][y,x]=raw_b[camera][y,x];selected.append(index)
        _,packed=_transform(raw,intrinsics)
        delta=packed.astype(np.int64)-baseline.astype(np.int64)
        if mask and mask&(mask-1)==0:single_sum+=delta
        if mask==(1<<count)-1:joint=delta
        changed=np.argwhere(delta!=0)
        entries=[dict(index=c.tolist(),a=int(baseline[tuple(c)]),b=int(packed[tuple(c)]),
                      delta=int(delta[tuple(c)])) for c in changed]
        matches=bool(np.array_equal(packed,target))
        if matches:matching.append(mask)
        rows.append(dict(mask=mask,selected_pixel_ids=selected,packed_sha256=sha256(packed.tobytes()).hexdigest(),
            packed_checksum=int(packed.sum(dtype=np.uint64)),changed_packed_values=len(entries),
            camera_changed_values={name:int(np.count_nonzero(delta[i])) for i,name in enumerate(CAMERAS)},
            max_abs_packed_delta=int(np.abs(delta).max()),packed_deltas=entries,
            equals_observed_b_packed=matches,observed_endpoint=mask in (0,(1<<count)-1)))
    minimal=[m for m in matching if not any(k!=m and k&m==k for k in matching)]
    return dict(pixels=points,subsets=rows,minimal_exact_subsets=minimal,
        baseline_packed_sha256=sha256(baseline.tobytes()).hexdigest(),
        target_packed_sha256=sha256(target.tobytes()).hexdigest(),
        joint_delta_equals_sum_of_singles=bool(np.array_equal(joint,single_sum)),
        intervention_scope='IN_MEMORY_CPU_WARP_I420_ONLY_NO_MODEL_COUNTERFACTUAL')


def _safe(path):
    path=Path(path).absolute()
    if '..' in path.parts:raise ValueError('parent traversal prohibited')
    capture._safe_path(path.parent,path.name)
    return path


def _hash(path):
    result=sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(65536),b''):result.update(block)
    return result.hexdigest()


def verify_archive(root, archive):
    root,archive=_safe(root),_safe(archive)
    if not root.is_dir() or not archive.is_file():raise ValueError('existing archive/extraction required')
    if archive.stat().st_size!=ARCHIVE_BYTES or _hash(archive)!=ARCHIVE_SHA:
        raise ValueError('pinned original archive size/hash mismatch')
    with zipfile.ZipFile(archive) as stream:
        records=stream.infolist();members=set()
        if len(records)!=141 or sum(r.file_size for r in records)!=187115633:
            raise ValueError('original member/byte count mismatch')
        for record in records:
            mode=stat.S_IFMT(record.external_attr>>16)
            if record.filename in members or record.is_dir() or mode not in (0,stat.S_IFREG) or record.flag_bits&1:
                raise ValueError('unsafe/duplicate archive member')
            path=capture._safe_path(root,record.filename);members.add(record.filename)
            if not path.is_file() or path.stat().st_size!=record.file_size:
                raise ValueError('extracted member size mismatch')
            digest=sha256()
            with stream.open(record) as source:
                for block in iter(lambda:source.read(65536),b''):digest.update(block)
            if _hash(path)!=digest.hexdigest():raise ValueError('extracted bytes differ from original ZIP')
        actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() or p.is_symlink()}
        if actual!=members:raise ValueError('extra/missing extracted member')
    return dict(run_id=RUN_ID,artifact_id=ARTIFACT_ID,source_sha=SOURCE,archive_nbytes=ARCHIVE_BYTES,
                archive_sha256=ARCHIVE_SHA,members=141,uncompressed_bytes=187115633)


def _require_runtime():
    for name,version in (('numpy','2.4.6'),('opencv-python-headless','5.0.0.93')):
        if importlib.metadata.version(name)!=version:raise ValueError('recorded CPU runtime required')
    if any(k.split('.')[0] in ('panda3d','metadrive','onnxruntime') for k in sys.modules):
        raise ValueError('archival replay requires a fresh CPU-only process')


def _sources(study):
    sources=capture.source_snapshot()
    if len(sources)!=62 or study['source_snapshot']!=sources:raise ValueError('producer source drift')
    for name,digest in sources.items():
        data=subprocess.check_output(['git','show',SOURCE+':'+name],cwd=capture.REPO_ROOT)
        if sha256(data).hexdigest()!=digest:raise ValueError('recorded producer Git blob mismatch')


def _load_capture(root, row):
    raw={};canvas={}
    for camera in CAMERAS:
        raw_frame=capture._read_png(capture._safe_path(root,row['raw'][camera]['path']),964,604)
        canvas[camera]=capture._read_png(capture._safe_path(root,row['canvas'][camera]['path']),512,256)
        if raw_frame.sha256!=row['raw'][camera]['rgb_sha256'] or canvas[camera].sha256!=row['canvas'][camera]['rgb_sha256']:
            raise ValueError('decoded RGB hash mismatch')
        raw[camera]=np.frombuffer(raw_frame.rgb,np.uint8).reshape(604,964,3)
    intrinsics={k:PinholeIntrinsics(**row['intrinsics'][k]) for k in CAMERAS}
    pair,packed=_transform(raw,intrinsics)
    if pair.road!=canvas['road'] or pair.wide!=canvas['wide']:
        raise ValueError('saved raw/intrinsics do not reconstruct saved canvas')
    saved=capture._safe_path(root,row['packed']['path']).read_bytes()
    if saved!=packed.tobytes() or sha256(saved).hexdigest()!=row['packed']['sha256'] or row['packed']['actual_input_sha256']!=row['packed']['sha256']:
        raise ValueError('saved packed bytes/actual NEW_IMG SHA mismatch')
    return raw,intrinsics


def run(root, archive, out):
    root,archive,out=_safe(root),_safe(archive),_safe(out)
    if out.exists() or out==root or root in out.parents:
        raise ValueError('fresh output outside original input root required')
    _require_runtime()
    provenance=verify_archive(root,archive)
    study=capture._read_json(root/'study.json')
    if study['status']!='STUDY_ASSOCIATION_VALIDATED' or study['model_calls']!=24:
        raise ValueError('accepted complete study required')
    _sources(study)
    roots=[root/'trial_02',root/'trial_03']
    trials=[capture._read_json(p/'trial.json') for p in roots]
    for repeat,trial in enumerate(trials):
        if (trial['status']!='TRIAL_ASSOCIATION_VALIDATED' or trial['arm']!='retention' or
            trial['repeat']!=repeat or trial['provider_closed'] is not True or trial['model_calls']!=4 or
            trial['source_snapshot']!=study['source_snapshot'] or trial['runtime']!=study['runtime']):
            raise ValueError('wrong retained trial binding')
    steps=[]
    for index in (0,1):
        rows=[t['observed']['captures'][index] for t in trials]
        values=[_load_capture(r,row) for r,row in zip(roots,rows)]
        poses=[t['observed']['capture_rows'][row['capture_index']-1]['pose'] for t,row in zip(trials,rows)]
        if poses[0]!=poses[1] or rows[0]['intrinsics']!=rows[1]['intrinsics']:
            raise ValueError('accepted pose/intrinsics differ before intervention')
        state_equal={}
        for section in ('pre_state','fixed_inputs'):
            arrays=[t['observed']['arrays'][index][section] for t in trials]
            if arrays[0].keys()!=arrays[1].keys():raise ValueError('recorded snapshot keys differ')
            state_equal[section]={key:bool(np.array_equal(*[np.load(capture._safe_path(r,a[key]['path']),allow_pickle=False) for r,a in zip(roots,arrays)])) for key in arrays[0]}
        if not all(v for values_by_key in state_equal.values() for v in values_by_key.values()):
            raise ValueError('saved pre-state/fixed feeds differ')
        analysis=analyze_pair(values[0][0],values[1][0],values[0][1])
        steps.append(dict(step=index+1,accepted_pose=poses[0],intrinsics=rows[0]['intrinsics'],
                          source_reconstructed_snapshot_equality=state_equal,analysis=analysis))
    _require_runtime()
    report=dict(schema='first-divergence-pixel-forensics-v1',status='CPU_ARCHIVE_INTERVENTIONS_VALIDATED',
        provenance=provenance,producer_paths=62,cpu_runtime={k:importlib.metadata.version(k) for k in ('numpy','opencv-python-headless')},
        steps=steps,new_native_calls=0,new_official_model_calls=0,new_ort_sessions=0,new_gpu_reads=0,
        original_strict_pass=False,stage7_complete=False,limitation=LIMITATION)
    payload=json.dumps(report,indent=2,allow_nan=False)+'\n'
    if len(payload.encode())>REPORT_CAP:raise ValueError('CPU report byte cap')
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as stream:stream.write(payload)
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('root','archive','out'):parser.add_argument('--'+flag,type=Path,required=True)
    args=parser.parse_args(argv)
    try:report=run(args.root,args.archive,args.out)
    except (ValueError,OSError,zipfile.BadZipFile,subprocess.CalledProcessError,importlib.metadata.PackageNotFoundError) as exc:
        print(json.dumps(dict(status='FAILED_OR_INCOMPLETE',error=str(exc))));return 1
    print(json.dumps(dict(status=report['status'],steps=len(report['steps']),new_official_model_calls=0)));return 0


if __name__=='__main__':raise SystemExit(main())
