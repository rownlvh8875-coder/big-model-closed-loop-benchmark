"""Structural callback binding and pinned wheel source audit, no native imports."""
import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

from scripts.renderer_task_callbacks import _state, CallbackBoundaryError

WHEEL_SHA='f949e89ff4bc32b72c8d09f5c61446bbc2b1f9b415b99a077c02b8df77c217f7'
WHEEL_BYTES=72968610
MANIFEST_SHA='f81fa5be38bc9853b6eff1d0ea524be97f3d1e92f5c1f0f9e1449a11b4c4b59f'
TARGETS=(('metadrive/engine/core/pssm.py','PSSM','update'),
         ('metadrive/engine/core/main_camera.py','MainCamera','_chase_task'),
         ('metadrive/component/sensors/base_camera.py','BaseCamera','perceive'),
         ('metadrive/engine/base_engine.py','BaseEngine','setup_main_camera'))


def bind_engine(engine,*,pssm_class,chase_class,matrix_class,task_continue,max_snapshots=48):
    """Bind supplied already-admitted classes. Structural checks are not admission.

    Named getters exclude Python/C++ vector/array indexing and private value-copy
    operations, which are counted separately. No GPU/clock getters are added.
    """
    if type(max_snapshots) is not int or not 1<=max_snapshots<=48 or type(task_continue) is not int:
        raise ValueError('bounded snapshots and explicit task.cont required')
    pssm=getattr(engine,'pssm',None);chase=getattr(engine,'main_camera',None)
    camera=getattr(engine,'camera',None);render=getattr(engine,'render',None)
    def owners():
        if (type(pssm) is not pssm_class or type(chase) is not chase_class or
            engine.pssm is not pssm or engine.main_camera is not chase or
            getattr(pssm,'engine',None) is not engine or getattr(chase,'engine',None) is not engine or
            camera is None or render is None or engine.camera is not camera or engine.render is not render or
            getattr(chase,'camera',None) is not camera or type(pssm.num_splits) is not int or pssm.num_splits!=2 or
            type(chase.run_task) is not bool):raise ValueError('exact engine/callback/camera ownership required')
    owners();rig=pssm.camera_rig
    if not callable(matrix_class):raise ValueError('private aligned matrix constructor required')
    counts=dict(snapshots_attempted=0,snapshots_returned=0,named_getter_attempts=0,named_getter_returns=0,
        private_matrix_allocations=0,private_matrix_assignments=0,vector_component_reads=0,matrix_array_reads=0)
    attempts=0
    def get(method,*args):
        counts['named_getter_attempts']+=1;result=method(*args);counts['named_getter_returns']+=1
        return result
    def snapshot():
        nonlocal attempts
        owners()
        if pssm.camera_rig is not rig:raise ValueError('camera rig owner changed')
        if attempts>=max_snapshots:raise ValueError('snapshot cap exhausted before getters')
        attempts+=1;counts['snapshots_attempted']+=1
        xyz=get(camera.getPos,render);hpr=get(camera.getHpr,render)
        position=[];rotation=[]
        for vector,target in ((xyz,position),(hpr,rotation)):
            for i in range(3):
                counts['vector_component_reads']+=1;target.append(float(vector[i]))
        raw=get(rig.get_mvp_array)
        if len(raw)!=2:raise ValueError('exact two-split MVP layout required')
        matrices=[]
        for i in range(2):
            counts['matrix_array_reads']+=1;source=raw[i]
            aligned=matrix_class();counts['private_matrix_allocations']+=1
            aligned.assign(source);counts['private_matrix_assignments']+=1
            matrices.append([[float(get(aligned.getCell,r,c)) for c in range(4)] for r in range(4)])
        result=dict(pose=dict(xyz_m=position,hpr_deg=rotation),matrices=matrices,chase_run_task=chase.run_task)
        try:_state(result)
        except CallbackBoundaryError as exc:raise ValueError(str(exc)) from exc
        counts['snapshots_returned']+=1
        return result
    return dict(targets={'PSSM.update':pssm.update,'MainCamera._chase_task':chase._chase_task},
                snapshot=snapshot,task_continue=task_continue,reader_counts=counts,native_admission_proven=False)


def method_receipt(raw,classname,method):
    """Parse source as data; list syntactic calls, not actual runtime execution."""
    if type(raw) is not bytes or len(raw)>256*1024:raise ValueError('bounded source bytes required')
    try:tree=ast.parse(raw)
    except (SyntaxError,UnicodeError) as exc:raise ValueError('invalid target source') from exc
    classes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==classname]
    if len(classes)!=1:raise ValueError('one exact target class required')
    methods=[n for n in classes[0].body if isinstance(n,ast.FunctionDef) and n.name==method]
    if len(methods)!=1:raise ValueError('one exact target method required')
    node=methods[0]
    calls=sorted((n for n in ast.walk(node) if isinstance(n,ast.Call)),key=lambda n:(n.lineno,n.col_offset))
    return dict(classname=classname,method=method,lineno=node.lineno,end_lineno=node.end_lineno,
                syntactic_calls=[ast.unparse(n.func) for n in calls],code_executed=False,
                source_nbytes=len(raw),source_sha256=sha256(raw).hexdigest())


def _safe(path):
    path=Path(path).absolute()
    if '..' in path.parts or any(p.is_symlink() for p in (path,*path.parents)):
        raise ValueError('no traversal/symlink input or output')
    return path


def _hash(path):
    result=sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()


def audit_sources(wheel,manifest,out):
    wheel,manifest,out=map(_safe,(wheel,manifest,out))
    if out.exists():raise ValueError('fresh output required')
    if (not wheel.is_file() or wheel.stat().st_size!=WHEEL_BYTES or _hash(wheel)!=WHEEL_SHA or
        not manifest.is_file() or manifest.stat().st_size>16*1024*1024 or _hash(manifest)!=MANIFEST_SHA):
        raise ValueError('pinned wheel/installed manifest mismatch')
    installed=json.loads(manifest.read_bytes());entries={e['path']:e for e in installed['entries']}
    if len(entries)!=44232:raise ValueError('accepted installed manifest entries required')
    files=[]
    with zipfile.ZipFile(wheel) as z:
        members=z.infolist();seen=set()
        for m in members:
            p=PurePosixPath(m.filename);mode=stat.S_IFMT(m.external_attr>>16)
            if (m.filename in seen or p.is_absolute() or '..' in p.parts or '\\' in m.filename or
                m.flag_bits&1 or mode not in (0,stat.S_IFREG,stat.S_IFDIR)):
                raise ValueError('unsafe pinned wheel member')
            seen.add(m.filename)
        for name,cls,method in TARGETS:
            info=z.getinfo(name)
            if info.is_dir() or info.file_size>256*1024:raise ValueError('bounded regular target source required')
            raw=z.read(info);receipt=method_receipt(raw,cls,method)
            installed_path='/opt/venv/lib/python3.11/site-packages/'+name
            entry=entries[installed_path]
            if (entry['kind']!='file' or entry['nbytes']!=len(raw) or entry['sha256']!=receipt['source_sha256']):
                raise ValueError('wheel target differs from accepted installed image source')
            files.append(dict(path=name,installed_path=installed_path,**receipt))
    report=dict(schema='renderer-task-boundary-source-audit-v1',status='PINNED_TARGET_SOURCE_MATCH',
        wheel_sha256=WHEEL_SHA,wheel_nbytes=WHEEL_BYTES,installed_manifest_sha256=MANIFEST_SHA,
        installed_entries=44232,files=files,split_count=2,max_task_steps=12,max_callback_snapshots=48,
        named_getters_per_snapshot=35,named_getter_bound_per_observed_process=1680,
        private_matrix_copy_bound_per_observed_process=96,
        getter_accounting='Named methods only: getPos/getHpr/get_mvp_array/getCell; vector/array indexing and private matrix allocations/assignments separate.',
        native_admission_proven=False,native_execution_status='NOT_RUN',new_native_calls=0,new_model_calls=0,new_ort_sessions=0,
        downloaded_code_executed=False,original_strict_pass=False,stage7_complete=False,
        limitation='Static byte/AST and structural binding only, not actual callback/camera/MVP observations, physical binary identity, GPU cause or observer neutrality.')
    raw=(json.dumps(report,indent=2,allow_nan=False)+'\n').encode()
    if len(raw)>64*1024:raise ValueError('audit report cap')
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('xb') as stream:stream.write(raw)
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('wheel','manifest','out'):parser.add_argument('--'+flag,type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        r=audit_sources(args.wheel,args.manifest,args.out)
        print(json.dumps(dict(status=r['status'],files=len(r['files']),native_execution_status='NOT_RUN')))
    except (ValueError,OSError,KeyError,zipfile.BadZipFile) as exc:
        print(json.dumps(dict(status='FAILED_OR_INCOMPLETE',error=str(exc))));return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
