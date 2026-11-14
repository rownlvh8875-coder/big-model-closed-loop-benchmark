"""Offline pinned campaign03 clock/RGB evidence and copied-array I420 subsets."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from hashlib import sha256
import importlib.metadata
from itertools import combinations
import json
import math
from pathlib import Path, PurePosixPath
import stat
import subprocess
import zipfile

import cv2
import numpy as np

from bigbench.optical_calibration import PinholeIntrinsics
from scripts import engine_clock_boundaries as clock
from scripts import first_divergence_pixel_forensics as pixels
from scripts import texture_marker_state_sequences as states

REPO=Path(__file__).resolve().parents[1]
SOURCE='60f6d7fbadf9c0cdbeb087f6452d7b07ea77abd5'
PRODUCER='fd57f5efab90c7b410b699250a47603f364aace5'
CONTROL='498647977af799ba0b765440d44985565eee7d13'
IDENTITY='6563f6af12ed20dafbe5ff7a67e960f0878bb0ac40c1731b4d45ad1c92a03f2c'
PINS={
    'canary':dict(artifact_id=14104039420,archive_bytes=339057032,
        archive_sha256='1484ea8be64763afa10b6cce1053f09790390ce3580adf1bfa90525b279606e7',
        members=102,uncompressed_bytes=339041286,
        request_sha256='03936937f07a814d07e16eaea138df3119826c0deb675c03df2da4f73ce21dc5'),
    'abba':dict(artifact_id=14103669668,archive_bytes=405545950,
        archive_sha256='cf1a03b478e15bc9c0533ef4bc2e8e644cb2a16df20ad3f6f341c409b6ea7505',
        members=374,uncompressed_bytes=405483168,
        request_sha256='13dd5753f6b5a9b593be615bc68a52151276d182c3df2ed200fa228584d97d85'),
}
CAMERAS=('road','wide')
REPORT_CAP=2*1024*1024
RAW_CAP=128*1024*1024
LIMITATION=('Offline exact pinned ZIP authentication, not new live API or physical-host '
    'attestation. Numeric engine counts and Texture values are per-process, non-atomic '
    'observations, not global frame IDs, GPU fences or proof of observer neutrality. '
    'Different times do not identify a cause. Full RGB classes are local to pose/camera. '
    'Subset replacements affect private CPU arrays only: derived I420, no real graph '
    'feed, native intervention or model counterfactual. No unique shadow/task/GPU cause, '
    'physical optics/geometry/full-S or original strict-PASS proof. Raw cap is logical '
    'retained array bytes, not RSS. No new native/model/ORT/GPU/getter calls.')


def _hash_file(path):
    result=sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()


def _safe(path):
    path=Path(path).absolute()
    if '..' in path.parts:raise ValueError('parent traversal prohibited')
    pixels.capture._safe_path(path.parent,path.name)
    return path


def _member_name(name):
    path=PurePosixPath(name)
    if (not name or '\\' in name or path.is_absolute() or '..' in path.parts or
        str(path)!=name or name.endswith('/')):raise ValueError('unsafe ZIP member')


@contextmanager
def open_archive(path,pin):
    """Validate a complete immutable ZIP before reading bounded selected members."""
    path=_safe(path)
    if (not path.is_file() or path.stat().st_size!=pin['archive_bytes'] or
        _hash_file(path)!=pin['archive_sha256']):raise ValueError('pinned ZIP size/hash mismatch')
    with zipfile.ZipFile(path) as z:
        info=z.infolist();names=set()
        if (len(info)!=pin['members'] or sum(r.file_size for r in info)!=pin['uncompressed_bytes']):
            raise ValueError('pinned ZIP member/byte mismatch')
        for row in info:
            _member_name(row.filename)
            mode=stat.S_IFMT(row.external_attr>>16)
            if row.filename in names or mode not in (0,stat.S_IFREG) or row.flag_bits&1:
                raise ValueError('duplicate/encrypted/nonregular ZIP member')
            names.add(row.filename)
        yield z


def read_member(z,name,cap):
    _member_name(name)
    try:info=z.getinfo(name)
    except KeyError as exc:raise ValueError('missing selected original member') from exc
    if info.file_size>cap:raise ValueError('selected member byte cap')
    with z.open(info) as stream:
        raw=stream.read(cap+1)
    if len(raw)!=info.file_size or len(raw)>cap:raise ValueError('selected member byte cap')
    return raw


def _json_member(z,name):
    return json.loads(read_member(z,name,1024*1024))


def _observations(rows):
    if type(rows) is not list or not 1<=len(rows)<=12:raise ValueError('bounded observations required')
    enabled=[]
    for i,row in enumerate(rows):
        if (type(row) is not dict or set(row)!={'capture','camera','raw_sha256','counts','times','markers'} or
            type(row['capture']) is not int or row['capture']!=i//2+1 or
            row['camera']!=CAMERAS[i%2] or type(row['raw_sha256']) is not str or
            len(row['raw_sha256'])!=64 or any(c not in '0123456789abcdef' for c in row['raw_sha256'])):
            raise ValueError('capture/camera/RGB association mismatch')
        if (type(row['markers']) is not list or len(row['markers'])!=2 or
            any(type(v) is not int or not -(2**31)<=v<2**31 for v in row['markers'])):
            raise ValueError('observed signed32 Texture pair required')
        on=row['counts'] is not None;enabled.append(on)
        if not on:
            if row['times'] is not None:raise ValueError('OFF clock is unobserved/null')
        elif (type(row['counts']) is not list or len(row['counts'])!=4 or
              any(type(v) is not int or not -(2**63)<=v<2**63 for v in row['counts']) or
              type(row['times']) is not list or len(row['times'])!=4 or
              any(type(v) is not float or not math.isfinite(v) for v in row['times'])):
            raise ValueError('complete typed clock boundary observations required')
    if len(set(enabled))!=1:raise ValueError('mixed observed/unobserved clock trace')
    return enabled[0]


def compare_observations(left,right):
    a,b=_observations(left),_observations(right)
    if len(left)!=len(right):raise ValueError('matching observation lengths required')
    observed=a and b;rows=[]
    for i,(l,r) in enumerate(zip(left,right),1):
        rows.append(dict(call=i,capture=l['capture'],camera=l['camera'],
            raw_equal=l['raw_sha256']==r['raw_sha256'],markers_equal=l['markers']==r['markers'],
            counts_equal=l['counts']==r['counts'] if observed else None,
            times_equal=l['times']==r['times'] if observed else None,
            left=l,right=r))
    return dict(clock_observed=observed,rows=rows,
        same_counts=[r['call'] for r in rows if r['counts_equal']] if observed else None,
        same_counts_and_markers_different_rgb=[r['call'] for r in rows
            if r['counts_equal'] and r['markers_equal'] and not r['raw_equal']] if observed else None,
        same_rgb_different_times=[r['call'] for r in rows
            if r['raw_equal'] and not r['times_equal']] if observed else None)


def _read_image(z,prefix,desc,path,width,height):
    if desc['path']!=path:raise ValueError('registered capture member path required')
    raw=read_member(z,prefix+path,4*1024*1024)
    if len(raw)!=desc['nbytes'] or sha256(raw).hexdigest()!=desc['sha256']:
        raise ValueError('original PNG descriptor mismatch')
    if (raw[:8]!=b'\x89PNG\r\n\x1a\n' or raw[12:16]!=b'IHDR' or
        int.from_bytes(raw[16:20],'big')!=width or int.from_bytes(raw[20:24],'big')!=height):
        raise ValueError('registered PNG dimensions required before decode')
    image=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
    if image is None or image.shape!=(height,width,3) or image.dtype!=np.uint8:
        raise ValueError('decoded PNG shape/type mismatch')
    image=cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
    if sha256(image.tobytes()).hexdigest()!=desc['rgb_sha256']:raise ValueError('decoded RGB hash mismatch')
    image.setflags(write=False)
    return image


def load_capture(z,prefix,row,index):
    """Verify both saved transform endpoints; model association must remain absent."""
    raw={};canvas={}
    for cam in CAMERAS:
        raw[cam]=_read_image(z,prefix,row['raw'][cam],f'capture_{index:02d}/raw_{cam}.png',964,604)
        canvas[cam]=_read_image(z,prefix,row['canvas'][cam],f'capture_{index:02d}/canvas_{cam}.png',512,256)
    desc=row['packed'];path=f'capture_{index:02d}/packed_i420.bin'
    if (desc['path']!=path or desc['actual_input_sha256'] is not None or
        desc['association']!='DERIVED_ONLY_NO_MODEL_CALL'):raise ValueError('derived-only packed association required')
    saved=read_member(z,prefix+path,393216)
    if len(saved)!=393216 or len(saved)!=desc['nbytes'] or sha256(saved).hexdigest()!=desc['sha256']:
        raise ValueError('original packed descriptor mismatch')
    intrinsics={cam:PinholeIntrinsics(**row['intrinsics'][cam]) for cam in CAMERAS}
    pair,packed=pixels._transform(raw,intrinsics)
    for cam in CAMERAS:
        if getattr(pair,cam).rgb!=canvas[cam].tobytes():raise ValueError('raw/intrinsics do not reconstruct saved canvas')
    if packed.tobytes()!=saved:raise ValueError('raw/intrinsics do not reconstruct saved I420')
    return raw,intrinsics,packed


def catalog_group(images,samples):
    if len(images)!=len(samples):raise ValueError('catalog sample association mismatch')
    catalog=states.state_catalog(images);edges=[]
    for l,r in combinations(catalog['states'],2):
        a,b=(images[s['representative_index']] for s in (l,r))
        mask=np.any(a!=b,axis=2);coords=np.argwhere(mask)
        edges.append(dict(left=l['id'],right=r['id'],changed_pixels=int(np.count_nonzero(mask)),
            max_abs=int(np.abs(a.astype(np.int16)-b.astype(np.int16)).max()),
            first_xy=coords[0][::-1].tolist() if coords.size else None))
    return dict(samples=samples,**catalog,differences=edges)


def _sources(snapshot):
    if type(snapshot) is not dict or len(snapshot)!=261:raise ValueError('261 producer pins required')
    for name,digest in snapshot.items():
        _member_name(name);path=pixels.capture._safe_path(REPO,name)
        original=subprocess.check_output(['git','show',SOURCE+':'+name],cwd=REPO)
        if sha256(original).hexdigest()!=digest or _hash_file(path)!=digest:
            raise ValueError('frozen producer source mismatch: '+name)


def _case_observations(data):
    clock.validate_clock_trace(data['clock_trace'])
    rows=[]
    if len(data['markers'])!=12 or len(data['clock_trace']['calls'])!=12:
        raise ValueError('exact twelve camera calls required')
    for i,(call,marker) in enumerate(zip(data['clock_trace']['calls'],data['markers'])):
        cam=CAMERAS[i%2];capture=i//2+1
        if (marker['call']!=i+1 or marker['camera']!=cam or
            marker['raw_sha256']!=data['accepted'][capture-1]['raw'][cam]['rgb_sha256'] or
            marker['raw_sha256']!=data['capture_rows'][capture-1]['raw_sha256'][cam]):
            raise ValueError('original marker/raw/capture association mismatch')
        snaps=call['snapshots'];on=data['clock_enabled']
        rows.append(dict(capture=capture,camera=cam,raw_sha256=marker['raw_sha256'],
            markers=[marker['before'],marker['after']],
            counts=[snaps[k]['frame_count'] for k in clock.BOUNDARIES] if on else None,
            times=[snaps[k]['frame_time_s'] for k in clock.BOUNDARIES] if on else None))
    if _observations(rows)!=data['clock_enabled'] or data['clock_trace']['enabled']!=data['clock_enabled']:
        raise ValueError('clock ON/OFF association mismatch')
    return rows


def run(canary_archive,abba_archive,out):
    archives=[_safe(p) for p in (canary_archive,abba_archive)];out=_safe(out)
    if out.exists() or any(p.parent==out or p.parent in out.parents for p in archives):
        raise ValueError('fresh output outside original archive directories required')
    states.require_cpu_runtime();cases=[];provenance=[];retained=0;snapshot=None;endpoints=[]
    for mode,path in zip(('canary','abba'),archives):
        pin=PINS[mode]
        with open_archive(path,pin) as z:
            phase=_json_member(z,'output/phase.json')
            if (phase['mode']!=mode or phase['identity_verified'] is not True or phase['error'] is not None or
                phase['status']!=('HELD_CANARY_NATIVE_RECORDED' if mode=='canary' else 'HELD_ABBA_DATASET_RECORDED') or
                phase['official_model_calls']!=0 or phase['ort_sessions']!=0 or phase['scientific_result_promoted'] is not False):
                raise ValueError('accepted original phase required')
            for index in range(1 if mode=='canary' else 4):
                prefix=f'output/case_{index:02d}/';data=_json_member(z,prefix+'case.json');ctx=data['context']
                if (ctx['source_sha']!=SOURCE or ctx['head_sha']!=PRODUCER or ctx['producer_head_sha']!=PRODUCER or
                    ctx['control_head_sha']!=(PRODUCER if mode=='canary' else CONTROL) or
                    ctx['run_id']!=43571004531 or ctx['workflow_id']!=418107188 or ctx['attempt']!=1 or
                    ctx['job_id']!=132375169212 or ctx['request_sha256']!=pin['request_sha256'] or
                    data['request_sha256']!=pin['request_sha256'] or data['phase']!=mode or data['index']!=index or
                    data['status']!='CLOCK_CAMERA_REPLAY_RECORDED' or data['provider_closed'] is not True or
                    data['capture_count']!=6 or len(data['accepted'])!=6 or len(data['capture_rows'])!=6 or
                    data['clock_enabled']!=(mode=='canary' or index in (1,2)) or
                    data['runtime']!=phase['identity'] or data['runtime']['core_sha256']!=IDENTITY):
                    raise ValueError('pinned source/process/phase association mismatch')
                if snapshot is None:snapshot=data['source_snapshot'];_sources(snapshot)
                if data['source_snapshot']!=snapshot:raise ValueError('producer snapshot differs')
                if cases and data['runtime']!=cases[0]['data']['runtime']:raise ValueError('recorded runtime differs')
                label='C_ON' if mode=='canary' else ('OFF0','ON0','ON1','OFF1')[index]
                images=[];lenses=[]
                for i,row in enumerate(data['accepted'],1):
                    if row['capture_index']!=i or row['accepted_index']!=i:raise ValueError('capture ordinal mismatch')
                    if cases and (row['intrinsics']!=cases[0]['data']['accepted'][i-1]['intrinsics'] or
                        data['capture_rows'][i-1]['pose']!=cases[0]['data']['capture_rows'][i-1]['pose']):
                        raise ValueError('recorded pose/intrinsics differ')
                    raw,intrinsics,packed=load_capture(z,prefix,row,i)
                    retained+=sum(a.nbytes for a in raw.values())
                    if retained>RAW_CAP:raise ValueError('logical retained raw array cap')
                    images.append(raw);lenses.append(intrinsics)
                    endpoints.append(dict(case=label,capture=i,packed_sha256=sha256(packed.tobytes()).hexdigest(),
                        raw_rgb_sha256={c:row['raw'][c]['rgb_sha256'] for c in CAMERAS},
                        canvas_rgb_sha256={c:row['canvas'][c]['rgb_sha256'] for c in CAMERAS}))
                cases.append(dict(id=label,data=data,images=images,lenses=lenses,observations=_case_observations(data)))
            provenance.append(dict(phase=mode,run_id=43571004531,source_sha=SOURCE,producer_head_sha=PRODUCER,**pin))
    if len({c['data']['process_uuid'] for c in cases})!=5:raise ValueError('five distinct process UUIDs required')
    catalogs=[]
    for pose,indices in ((0,range(4)),(1,range(4,6))):
        for cam in CAMERAS:
            recorded=[c['data']['capture_rows'][i]['pose'] for c in cases for i in indices]
            if any(p!=recorded[0] for p in recorded):raise ValueError('catalog pose group mismatch')
            samples=[dict(case=c['id'],capture=i+1) for c in cases for i in indices]
            images=[c['images'][i][cam] for c in cases for i in indices]
            catalogs.append(dict(pose=recorded[0],camera=cam,**catalog_group(images,samples)))
    sparse=[dict(capture=i+1,camera=cam,cases=[c['id'] for c in cases],
                 points=states.sparse_locations([c['images'][i][cam] for c in cases]))
            for i in range(6) for cam in CAMERAS]
    comparisons=[dict(left=l['id'],right=r['id'],**compare_observations(l['observations'],r['observations']))
                 for l,r in combinations(cases,2)]
    interventions=[]
    for i in range(6):
        l,r=cases[1],cases[2]
        result=pixels.analyze_pair(l['images'][i],r['images'][i],l['lenses'][i])
        if (result['baseline_packed_sha256']!=l['data']['accepted'][i]['packed']['sha256'] or
            result['target_packed_sha256']!=r['data']['accepted'][i]['packed']['sha256']):
            raise ValueError('subset endpoint association mismatch')
        interventions.append(dict(capture=i+1,left='OFF0',right='ON0',**result))
    states.require_cpu_runtime();_sources(snapshot)
    report=dict(schema='engine-clock-pixel-forensics-03-v1',status='SAVED_CLOCK_PIXEL_ANALYSIS_VALIDATED',
        provenance=provenance,source_pins=len(snapshot),source_snapshot=snapshot,
        analyzer_sha256=_hash_file(Path(__file__)),cpu_runtime={k:importlib.metadata.version(k)
            for k in ('numpy','opencv-python-headless')},
        cases=[dict(id=c['id'],process_uuid=c['data']['process_uuid'],clock_enabled=c['data']['clock_enabled']) for c in cases],
        reconstructed_pairs=len(endpoints),raw_frames=60,retained_raw_bytes=retained,logical_raw_cap=RAW_CAP,
        endpoints=endpoints,catalogs=catalogs,ordinal_sparse_differences=sparse,
        cross_process_clock_and_texture=comparisons,copied_array_interventions=interventions,
        new_native_calls=0,new_official_model_calls=0,new_ort_sessions=0,new_gpu_reads=0,new_clock_getters=0,
        original_strict_pass=False,stage7_complete=False,limitation=LIMITATION)
    payload=(json.dumps(report,indent=2,allow_nan=False)+'\n').encode()
    if len(payload)>REPORT_CAP:raise ValueError('report byte cap')
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('xb') as stream:stream.write(payload)
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('canary-archive','abba-archive','out'):parser.add_argument('--'+flag,type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        report=run(args.canary_archive,args.abba_archive,args.out)
        print(json.dumps(dict(status=report['status'],reconstructed_pairs=report['reconstructed_pairs'],
                              raw_frames=report['raw_frames'],new_native_calls=0)))
    except (ValueError,OSError,KeyError,zipfile.BadZipFile,clock.ClockObserverError,
            subprocess.CalledProcessError,importlib.metadata.PackageNotFoundError) as exc:
        print(json.dumps(dict(status='FAILED_OR_INCOMPLETE',error=str(exc))));return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
