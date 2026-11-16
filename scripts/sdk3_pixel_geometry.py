"""Finite CPU ray candidates, never a GPU ownership or renderer-repair test."""
from __future__ import annotations
from contextlib import contextmanager
import math
import numpy as np

SOLVER_EPSILON=1e-12
MAX_TRIANGLES=500_000


def need(condition,message):
    if not condition:raise ValueError(message)


def pixel_samples(width,height,x,y):
    need(all(type(v) is int for v in (width,height,x,y)) and width>0 and height>0 and 0<=x<width and 0<=y<height,'valid top-left pixel coordinates')
    locations=[('center',2*x+1,2*y+1),('top_left',2*x,2*y),('top_right',2*x+2,2*y),('bottom_right',2*x+2,2*y+2),('bottom_left',2*x,2*y+2)]
    return [dict(name=name,ndc=[(u-width)/width,(height-v)/height]) for name,u,v in locations]


def _ray(origin,direction,max_distance):
    origin=np.asarray(origin,dtype=np.float64);direction=np.asarray(direction,dtype=np.float64)
    need(origin.shape==direction.shape==(3,) and np.isfinite(origin).all() and np.isfinite(direction).all() and math.isfinite(max_distance) and max_distance>0,'finite bounded CPU ray')
    length=float(np.linalg.norm(direction));need(math.isfinite(length) and length>0,'nonzero finite ray direction')
    return origin,direction/length


def intersect_triangles(origin,direction,triangles,max_distance):
    origin,direction=_ray(origin,direction,max_distance);triangles=np.asarray(triangles,dtype=np.float64)
    need(triangles.ndim==3 and triangles.shape[1:]==(3,3) and len(triangles)<=MAX_TRIANGLES and np.isfinite(triangles).all(),'bounded finite Nx3x3 CPU triangles')
    edge1=triangles[:,1]-triangles[:,0];edge2=triangles[:,2]-triangles[:,0];cross=np.cross(direction,edge2);det=np.einsum('ij,ij->i',edge1,cross)
    valid=np.abs(det)>SOLVER_EPSILON;inverse=np.zeros_like(det);np.divide(1.,det,out=inverse,where=valid)
    delta=origin-triangles[:,0];u=np.einsum('ij,ij->i',delta,cross)*inverse;other=np.cross(delta,edge1);v=np.einsum('j,ij->i',direction,other)*inverse;distance=np.einsum('ij,ij->i',edge2,other)*inverse
    indices=np.nonzero(valid&(u>=0)&(v>=0)&(u+v<=1)&(distance>=0)&(distance<=max_distance))[0]
    return [dict(triangle_index=int(i),distance=float(distance[i]),barycentric=[float(1-u[i]-v[i]),float(u[i]),float(v[i])],position=(origin+direction*distance[i]).tolist()) for i in sorted(indices,key=lambda i:distance[i])]


def ray_box(origin,direction,minimum,maximum,max_distance):
    origin,direction=_ray(origin,direction,max_distance);minimum=np.asarray(minimum,dtype=float);maximum=np.asarray(maximum,dtype=float)
    need(minimum.shape==maximum.shape==(3,) and np.isfinite(minimum).all() and np.isfinite(maximum).all() and np.all(minimum<=maximum),'finite ordered CPU bounds')
    low=0.;high=float(max_distance)
    for axis in range(3):
        if direction[axis]==0:
            if not minimum[axis]<=origin[axis]<=maximum[axis]:return False
        else:
            a,b=sorted(((minimum[axis]-origin[axis])/direction[axis],(maximum[axis]-origin[axis])/direction[axis]));low=max(low,a);high=min(high,b)
            if low>high:return False
    return True


@contextmanager
def post_read_observer(sensor,callback,target_call=7):
    need(type(target_call) is int and 1<=target_call<=32 and callable(callback),'bounded CPU observation callback')
    name='get_rgb_array_cpu';original=getattr(sensor,name);owned=name in vars(sensor);prior=vars(sensor).get(name)
    state=dict(read_attempts=0,reads=0,inspection_attempts=0,inspections=0)
    def observed(*args,**kwargs):
        state['read_attempts']+=1;value=original(*args,**kwargs);state['reads']+=1
        if state['reads']==target_call:
            state['inspection_attempts']+=1;callback(value);state['inspections']+=1
        return value
    setattr(sensor,name,observed)
    try:yield state
    finally:
        if owned:setattr(sensor,name,prior)
        else:delattr(sensor,name)


def all_ray_hits(triangles,rays):
    need(len(rays)==5 and [r.get('name') for r in rays]==['center','top_left','top_right','bottom_right','bottom_left'],'five declared CPU samples,not GPU/MSAA positions')
    return {ray['name']:intersect_triangles(ray['origin'],ray['direction'],triangles,ray['max_distance']) for ray in rays}


def reference_from_reports(a,b):
    from scripts import panda_sdk3_runtime as p
    from scripts.aggregate_original_mdv3_current_recheck import MODEL_SHA256
    for row in (a,b):
        need(row.get('status')=='DIAGNOSTIC_EXECUTED' and row.get('seed')==20261110 and row.get('scenario')=='s_curve_left_right' and row.get('completed_steps')==row.get('requested_steps')==12 and len(row.get('frames',[]))==12,'complete fixed reference trials')
        need(row.get('model_sha256')==MODEL_SHA256 and row.get('selected_sdk_sha256')==p.SDK_SHA and row.get('pssm_update_preserved') is True and row.get('gpu_hdr_extraction') is False,'pinned original reference context')
    need(a['frames'][:6]==b['frames'][:6],'identical first6closed-loop reference history')
    road=[r['frames'][6]['source_road_rgb_sha256'] for r in (a,b)];wide=a['frames'][6]['source_wide_rgb_sha256']
    need(road[0]!=road[1] and wide==b['frames'][6]['source_wide_rgb_sha256'],'known step7Road-only branches')
    previous=[dict(t=r['time_s'],x=r['world_x_m'],y=r['world_y_m'],heading=r['heading_rad'],speed=r['speed_mps']) for r in a['frames'][:6]]
    need(all(math.isfinite(v) for r in previous for v in r.values()),'finite replay history')
    return dict(schema='sdk3-seven-pose-reference-v1',seed=20261110,scenario='s_curve_left_right',initial_fraction=.12,previous_states=previous,prefix_sha256=[dict(road=r['source_road_rgb_sha256'],wide=r['source_wide_rgb_sha256']) for r in a['frames'][:6]],target_road_sha256=road,target_wide_sha256=wide,original_matrix_passed=3,original_matrix_total=4)


def qualify_replay(captures,reference):
    need(reference.get('schema')=='sdk3-seven-pose-reference-v1','registered source-image reference')
    complete=len(captures)==7 and [r.get('step') for r in captures]==list(range(1,8))
    count=sum(r.get(camera+'_sha256')==reference['prefix_sha256'][i][camera] for i,r in enumerate(captures[:6]) for camera in ('road','wide'))
    poses=complete and all(captures[i]['pose']==reference['previous_states'][i-1] for i in range(1,7))
    branch=None;wide=False
    if complete:
        source=captures[6].get('road_sha256');branch=reference['target_road_sha256'].index(source) if source in reference['target_road_sha256'] else None;wide=captures[6].get('wide_sha256')==reference['target_wide_sha256']
    matched=bool(complete and count==12 and poses and branch is not None and wide)
    return dict(source_images_match_reference=matched,complete_seven_pose_replay=complete,prefix_hashes_matched=count,prefix_hashes_total=12,recorded_poststep_poses_matched=poses,known_target_branch=branch,target_wide_matches=wide,original_closed_loop_episode=False,original_matrix_gate_passed=False,gpu_pixel_owner_proven=False,unique_cause_proven=False,repair_proven=False,stage7_complete=False)


def _arrays(triangles,ids):
    triangles=np.asarray(triangles,dtype='<f8');ids=np.asarray(ids,dtype='<i8')
    need(triangles.ndim==3 and triangles.shape[1:]==(3,3) and len(triangles)<=MAX_TRIANGLES and ids.shape==(len(triangles),6) and np.isfinite(triangles).all() and np.all(ids>=0),'bounded finite geometry arrays and nonnegative source indices')
    return triangles,ids


def save_geometry_archive(path,triangles,ids):
    import hashlib
    from pathlib import Path
    path=Path(path);need(path.suffix=='.npz','explicit geometry archive extension');triangles,ids=_arrays(triangles,ids)
    np.savez_compressed(path,triangles=triangles,ids=ids)
    return dict(nbytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),triangles_shape=list(triangles.shape),ids_shape=list(ids.shape),triangles_sha256=hashlib.sha256(triangles.tobytes()).hexdigest(),ids_sha256=hashlib.sha256(ids.tobytes()).hexdigest())


def load_geometry_archive(path,receipt):
    import hashlib
    from zipfile import ZipFile
    from pathlib import Path
    path=Path(path);need(0<path.stat().st_size==receipt.get('nbytes')<=64*1024**2,'bounded geometry archive bytes');need(hashlib.sha256(path.read_bytes()).hexdigest()==receipt.get('sha256'),'authentic geometry archive')
    with ZipFile(path) as archive:
        need(archive.namelist()==['triangles.npy','ids.npy'] and sum(i.file_size for i in archive.infolist())<=MAX_TRIANGLES*120+2048,'bounded unique numeric array members')
    with np.load(path,allow_pickle=False) as arrays:
        need(arrays['triangles'].dtype==np.dtype('<f8') and arrays['ids'].dtype==np.dtype('<i8'),'numeric-only geometry archive')
        triangles,ids=_arrays(arrays['triangles'],arrays['ids'])
    need(list(triangles.shape)==receipt.get('triangles_shape') and list(ids.shape)==receipt.get('ids_shape') and hashlib.sha256(triangles.tobytes()).hexdigest()==receipt.get('triangles_sha256') and hashlib.sha256(ids.tobytes()).hexdigest()==receipt.get('ids_sha256'),'geometry array identity')
    return triangles,ids
