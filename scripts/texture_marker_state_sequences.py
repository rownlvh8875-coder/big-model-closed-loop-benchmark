"""CPU-only state histories from the two already accepted Texture marker ZIPs."""
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
from scripts import texture_generation_markers as marker

PINS = {
    'canary': dict(source='0a98918e746fe7df9d5502e21db91c3e5cd15396',run_id=43177564313,
        artifact_id=13925041858,archive_bytes=14605800,
        archive_sha256='6a8c7a2e3495a5115938d17aee1da8c4e27f4e2ebc1b6350001e0f1090ee1994',
        members=33,uncompressed_bytes=15795803),
    'abba': dict(source='4814794243ca61a96264ebe04f4fb1b82f0eeecf',run_id=43178394897,
        artifact_id=13925716196,archive_bytes=58403425,
        archive_sha256='e6017f302e6879709bf089aaeca97fde9ca8828764b645c8e4bde473db6f16ce',
        members=129,uncompressed_bytes=63162078),
}
REPORT_CAP=2*1024*1024
RAW_RETENTION_CAP=128*1024*1024
LIMITATION=('Image state IDs are SHA-sorted RGB byte classes within a pose/camera group, not '
    'renderer frames, physical phase or GPU state. Capture ordinal and virtual pose time do not '
    'supply engine frame/time snapshots. OFF retains raw and has no observed markers. Cross-process '
    'absolute counters are not globally unique image identities or fences. No new native, GPU, '
    'ORT or model work, live API authentication, observer-neutrality, binary-equality or strict-PASS proof.')


def _images(images):
    if not isinstance(images,(list,tuple)) or not 1<=len(images)<=32:
        raise ValueError('bounded nonempty image cohort required')
    shape=None
    for image in images:
        if (not isinstance(image,np.ndarray) or image.dtype!=np.uint8 or image.ndim!=3 or
            image.shape[2]!=3 or min(image.shape[:2])<=0 or (shape is not None and image.shape!=shape)):
            raise ValueError('matching nonempty HWC uint8 RGB images required')
        shape=image.shape


def state_catalog(images):
    """Full-image equality classes; includes broad first-capture states."""
    _images(images)
    hashes=[sha256(image.tobytes(order='C')).hexdigest() for image in images]
    unique=sorted(set(hashes));ids={value:index for index,value in enumerate(unique)}
    return dict(states=[dict(id=ids[h],rgb_sha256=h,indices=[i for i,v in enumerate(hashes) if v==h],
                             representative_index=hashes.index(h)) for h in unique],
                sequence=[ids[h] for h in hashes])


def sparse_locations(images,limit=64):
    """Export a bounded union within ONE registered capture ordinal cohort."""
    _images(images)
    if type(limit) is not int or not 0<=limit<=64:raise ValueError('invalid sparse cap')
    mask=np.zeros(images[0].shape[:2],bool)
    for image in images[1:]:mask|=np.any(image!=images[0],axis=2)
    if np.count_nonzero(mask)>limit:raise ValueError('sparse union exceeds cap')
    result=[]
    for y,x in np.argwhere(mask):
        values=[image[y,x].astype(np.int16) for image in images]
        result.append(dict(xy=[int(x),int(y)],rgb=[v.tolist() for v in values],
                           delta_from_first=[(v-values[0]).tolist() for v in values]))
    return result


def compare_markers(left,right):
    """Keep unobserved OFF nulls distinct from equal measured counters."""
    if not left or len(left)!=len(right) or len(left)>64:raise ValueError('matching marker traces required')
    on=[]
    for rows in (left,right):
        modes=[]
        for row in rows:
            values=[row['before'],row['after']]
            if row['camera'] not in marker.CAMERAS:raise ValueError('invalid camera')
            if values==[None,None]:modes.append(False)
            elif all(type(v) is int and -(2**31)<=v<2**31 for v in values):modes.append(True)
            else:raise ValueError('typed signed32 marker pair or OFF nulls required')
        if len(set(modes))!=1:raise ValueError('mixed observed/unobserved trace')
        on.append(modes[0])
    if [r['camera'] for r in left]!=[r['camera'] for r in right]:raise ValueError('camera order mismatch')
    observed=all(on)
    examples=None
    if observed:
        examples=[dict(row=i+1,camera=a['camera'],before=a['before'],after=a['after'])
                  for i,(a,b) in enumerate(zip(left,right))
                  if (a['before'],a['after'])==(b['before'],b['after']) and a['raw_sha256']!=b['raw_sha256']]
    return dict(observed=observed,
        values_equal=([(r['before'],r['after']) for r in left]==[(r['before'],r['after']) for r in right]) if observed else None,
        patterns_equal=([r['before']==r['after'] for r in left]==[r['before']==r['after'] for r in right]) if observed else None,
        raw_trace_equal=[r['raw_sha256'] for r in left]==[r['raw_sha256'] for r in right],
        same_values_different_raw=examples)


def _safe(path):
    path=Path(path).absolute()
    if '..' in path.parts:raise ValueError('parent traversal prohibited')
    return marker.capture._safe_path(path.parent,path.name)


def _hash(path):
    result=sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(65536),b''):result.update(block)
    return result.hexdigest()


def verify_archive(root,archive,pin):
    root,archive=_safe(root),_safe(archive)
    if not root.is_dir() or not archive.is_file():raise ValueError('existing original ZIP/extraction required')
    if archive.stat().st_size!=pin['archive_bytes'] or _hash(archive)!=pin['archive_sha256']:
        raise ValueError('original ZIP size/hash mismatch')
    with zipfile.ZipFile(archive) as z:
        records=z.infolist();members=set()
        if len(records)!=pin['members'] or sum(r.file_size for r in records)!=pin['uncompressed_bytes']:
            raise ValueError('original ZIP member count/bytes mismatch')
        if sum(r.file_size for r in records)>marker.DATASET_CAP:raise ValueError('original dataset cap')
        for r in records:
            mode=stat.S_IFMT(r.external_attr>>16)
            if r.filename in members or r.is_dir() or mode not in (0,stat.S_IFREG) or r.flag_bits&1:
                raise ValueError('unsafe/duplicate ZIP member')
            path=marker.capture._safe_path(root,r.filename);members.add(r.filename)
            if not path.is_file() or path.stat().st_size!=r.file_size:raise ValueError('extracted size mismatch')
            digest=sha256()
            with z.open(r) as source:
                for block in iter(lambda:source.read(65536),b''):digest.update(block)
            if _hash(path)!=digest.hexdigest():raise ValueError('extracted bytes differ from original ZIP')
        actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() or p.is_symlink()}
        if actual!=members:raise ValueError('extra/missing extracted member')
    return dict(pin)


def _no_native_imports():
    if any(k.split('.')[0] in ('panda3d','metadrive','onnxruntime') for k in sys.modules):
        raise ValueError('fresh CPU-only process required')


def require_cpu_runtime():
    for name,version in (('numpy','2.4.6'),('opencv-python-headless','5.0.0.93')):
        if importlib.metadata.version(name)!=version:raise ValueError('recorded CPU runtime required')
    _no_native_imports()


def _difference(a,b):
    diff=a.astype(np.int16)-b.astype(np.int16);mask=np.any(diff!=0,axis=2);where=np.argwhere(mask)
    return dict(changed_pixels=int(np.count_nonzero(mask)),changed_values=int(np.count_nonzero(diff)),
                max_abs=int(np.abs(diff).max()),first_xy=where[0][::-1].tolist() if where.size else None)


def run(canary_root,canary_archive,abba_root,abba_archive,out):
    roots=[_safe(canary_root),_safe(abba_root)];archives=[_safe(canary_archive),_safe(abba_archive)];out=_safe(out)
    if out.exists() or any(out==r or r in out.parents for r in roots):raise ValueError('fresh output outside original input roots required')
    require_cpu_runtime()
    provenance=[];cases=[];snapshot=marker.source_snapshot()
    for mode,root,archive in zip(('canary','abba'),roots,archives):
        pin=PINS[mode];provenance.append(verify_archive(root,archive,pin))
        validated=marker.validate_dataset(root);phase=marker._read(root/'phase.json')
        if (validated['phase']!=mode or phase['context']['head_sha']!=pin['source'] or
            phase['context']['run_id']!=pin['run_id'] or phase['context']['workflow_id']!=415702769):
            raise ValueError('accepted phase context mismatch')
        for name,digest in snapshot.items():
            raw=subprocess.check_output(['git','show',pin['source']+':'+name],cwd=marker.REPO)
            if sha256(raw).hexdigest()!=digest:raise ValueError('producer Git source drift')
        for index in range(validated['providers']):
            case_root=root/f'case_{index:02d}';data=marker._read(case_root/'case.json')
            label='canary_ON' if mode=='canary' else ('OFF0','ON0','ON1','OFF1')[index]
            cases.append(dict(id=label,mode=mode,index=index,enabled=data['enabled'],root=case_root,data=data))
    retained=0
    for case in cases:
        images=[]
        for row in case['data']['accepted']:
            pair={}
            for camera in marker.CAMERAS:
                f=marker.capture._read_png(case['root']/row['raw'][camera]['path'],964,604)
                image=np.frombuffer(f.rgb,np.uint8).reshape(604,964,3);retained+=image.nbytes
                if retained>RAW_RETENTION_CAP:raise ValueError('CPU retained raw cap')
                pair[camera]=image
            images.append(pair)
        case['images']=images
    catalogs=[]
    for pose,indices in ((0,range(4)),(1,range(4,6))):
        for camera in marker.CAMERAS:
            samples=[dict(case=c['id'],capture=i+1) for c in cases for i in indices]
            images=[c['images'][i][camera] for c in cases for i in indices]
            catalog=state_catalog(images)
            for state in catalog['states']:
                canvases={c['data']['accepted'][i]['canvas'][camera]['rgb_sha256']
                          for c in cases for i in indices
                          if c['data']['accepted'][i]['raw'][camera]['rgb_sha256']==state['rgb_sha256']}
                if len(canvases)!=1:raise ValueError('same raw/lens with different recorded canvas')
                state['canvas_rgb_sha256']=next(iter(canvases))
            edges=[]
            for l in range(len(catalog['states'])):
                for r in range(l+1,len(catalog['states'])):
                    a=images[catalog['states'][l]['representative_index']]
                    b=images[catalog['states'][r]['representative_index']]
                    edges.append(dict(left=l,right=r,**_difference(a,b)))
            catalogs.append(dict(pose=pose,camera=camera,samples=samples,**catalog,differences=edges))
    sparse=[];union={(pose,camera):set() for pose in (0,1) for camera in marker.CAMERAS}
    for i in range(6):
        for camera in marker.CAMERAS:
            points=sparse_locations([c['images'][i][camera] for c in cases]);pose=0 if i<4 else 1
            union[(pose,camera)].update(tuple(p['xy']) for p in points)
            sparse.append(dict(capture=i+1,pose=pose,camera=camera,cases=[c['id'] for c in cases],points=points))
    support=[]
    for (pose,camera),coordinates in union.items():
        indices=range(4) if pose==0 else range(4,6)
        for x,y in sorted(coordinates,key=lambda p:(p[1],p[0])):
            support.append(dict(pose=pose,camera=camera,xy=[x,y],
                case_values=[dict(case=c['id'],captures=[i+1 for i in indices],
                                  rgb=[c['images'][i][camera][y,x].tolist() for i in indices]) for c in cases]))
    comparisons=[];within=[]
    for l in range(len(cases)):
        for r in range(l+1,len(cases)):
            comparisons.append(dict(left=cases[l]['id'],right=cases[r]['id'],
                **compare_markers(cases[l]['data']['markers'],cases[r]['data']['markers'])))
    for c in cases:
        if not c['enabled']:continue
        for i in (0,1,2,4):
            for j,camera in enumerate(marker.CAMERAS):
                a,b=c['data']['markers'][2*i+j],c['data']['markers'][2*(i+1)+j]
                if a['raw_sha256']==b['raw_sha256'] and (a['before'],a['after'])!=(b['before'],b['after']):
                    within.append(dict(case=c['id'],camera=camera,left_capture=i+1,right_capture=i+2,
                        left_values=[a['before'],a['after']],right_values=[b['before'],b['after']],raw_sha256=a['raw_sha256']))
    report=dict(schema='texture-marker-state-sequences-v1',status='CPU_TEXTURE_STATE_SEQUENCES_VALIDATED',
        provenance=provenance,producer_paths=65,cpu_runtime={k:importlib.metadata.version(k) for k in ('numpy','opencv-python-headless')},
        cases=[dict(id=c['id'],phase=c['mode'],index=c['index'],enabled=c['enabled'],
                    source_sha=c['data']['context']['head_sha'],process_id=c['data']['process_id']) for c in cases],
        raw_frames=60,accepted_pairs=30,retained_raw_bytes=retained,raw_retention_cap=RAW_RETENTION_CAP,
        catalogs=catalogs,ordinal_sparse_differences=sparse,support_union=support,
        cross_process_markers=comparisons,within_process_same_rgb_different_markers=within,
        new_native_calls=0,new_official_model_calls=0,new_ort_sessions=0,new_gpu_reads=0,
        original_strict_pass=False,stage7_complete=False,limitation=LIMITATION)
    require_cpu_runtime()
    payload=json.dumps(report,indent=2,allow_nan=False)+'\n'
    if len(payload.encode())>REPORT_CAP:raise ValueError('report byte cap')
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f:f.write(payload)
    return report


def plot_report(report_path,out):
    """Optional Agg-only view; does not read or transform original image files."""
    _no_native_imports();report_path,out=_safe(report_path),_safe(out);svg=out.with_suffix('.svg')
    if out.suffix!='.png' or out.exists() or svg.exists():raise ValueError('fresh PNG/SVG outputs required')
    if report_path.stat().st_size>REPORT_CAP:raise ValueError('report byte cap')
    report=json.loads(report_path.read_text())
    if report.get('status')!='CPU_TEXTURE_STATE_SEQUENCES_VALIDATED':raise ValueError('validated report required')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt']='texture-marker-state-sequences-v1'
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    for group,ax in zip(report['catalogs'],axes.flat):
        width=4 if group['pose']==0 else 2
        values=np.array(group['sequence']).reshape(5,width)
        ax.imshow(values,cmap='Set2',vmin=0,vmax=7,aspect='auto',interpolation='nearest')
        for y in range(5):
            for x in range(width):ax.text(x,y,f'S{values[y,x]}',ha='center',va='center',color='black')
        ax.set_yticks(range(5),[c['id'] for c in report['cases']])
        ax.set_xticks(range(width),range(1 if width==4 else 5,5 if width==4 else 7))
        ax.set_xlabel('Recorded capture ordinal')
        ax.set_title(f'Pose {group["pose"]} / {group["camera"]}: {len(group["states"])} full RGB states')
    fig.suptitle('Saved RGB state sequences — no new native or model run')
    fig.supxlabel('S IDs are SHA-sorted within each panel; equal IDs across panels have no shared meaning.\nOFF retains raw; CPU counters are not frame identities or GPU fences.',fontsize=9)
    out.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(out,dpi=160,metadata={'Software':'saved Texture state CPU analysis'})
    fig.savefig(svg,metadata={'Date':None});plt.close(fig);_no_native_imports()
    return dict(png_sha256=_hash(out),svg_sha256=_hash(svg),matplotlib=matplotlib.__version__,
                numpy=np.__version__,scope='FIGURE_FROM_REPORT_ONLY_NOT_IMAGE_REPLAY')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    r=sub.add_parser('run')
    for flag in ('canary-root','canary-archive','abba-root','abba-archive','out'):r.add_argument('--'+flag,type=Path,required=True)
    q=sub.add_parser('plot');q.add_argument('--report',type=Path,required=True);q.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        if a.command=='run':
            result=run(a.canary_root,a.canary_archive,a.abba_root,a.abba_archive,a.out)
            print(json.dumps(dict(status=result['status'],raw_frames=result['raw_frames'],support_pixels=len(result['support_union']))))
        else:print(json.dumps(plot_report(a.report,a.out)))
    except (ValueError,OSError,zipfile.BadZipFile,subprocess.CalledProcessError,importlib.metadata.PackageNotFoundError) as exc:
        print(json.dumps(dict(status='FAILED_OR_INCOMPLETE',error=str(exc))));return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
