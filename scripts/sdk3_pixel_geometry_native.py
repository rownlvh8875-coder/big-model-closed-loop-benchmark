"""Owned zero-model native scene replay; SDK bootstrap occurs only in owned child."""
from __future__ import annotations
import argparse,os,sys
from pathlib import Path
from types import FunctionType
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk3_diagnostic as owner


def owned_child_command(args,parent_pid):
    return [sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--owned-child','--server-owner',str(parent_pid),'--out',args.out,'--nonce',args.nonce,'--repeat',str(args.repeat)]


def run_with_server(args):
    original=owner.run_with_server
    function=FunctionType(original.__code__,dict(original.__globals__,owned_child_command=owned_child_command),original.__name__,original.__defaults__,original.__closure__)
    function.__kwdefaults__=dict(original.__kwdefaults__ or {})
    return function(args)


def _matrix(value):
    return [[float(value.getCell(r,c)) for c in range(4)] for r in range(4)]


def snapshot_geometry(core,engine,sensor,out):
    import time,numpy as np
    from scripts import sdk3_pixel_geometry as g
    camera=sensor.cam;lens=sensor.get_lens();world=engine.render;camera_matrix=camera.getMat(world);camera_rows=_matrix(camera_matrix);rays=[]
    region=camera.node().getDisplayRegion(0);viewport=[float(region.getLeft()),float(region.getRight()),float(region.getBottom()),float(region.getTop())]
    g.need(viewport==[0.,1.,0.,1.] and sensor.buffer.getXSize()==964 and sensor.buffer.getYSize()==604,'full964x604source display region')
    for sample in g.pixel_samples(964,604,596,494):
        near=core.LPoint3f();far=core.LPoint3f();g.need(lens.extrude(core.LPoint2f(*sample['ndc']),near,far),'finite lens extrusion')
        a,b=g.transform_points([list(near),list(far)],camera_rows);direction=b-a;distance=float(np.linalg.norm(direction));g.need(np.isfinite(a).all() and np.isfinite(direction).all() and distance>0,'valid borrowed CPU ray')
        rays.append(dict(**sample,origin=a.tolist(),direction=(direction/distance).tolist(),max_distance=distance))
    fb=sensor.buffer.getFbProperties();counts=dict(nodes_seen=0,hidden=0,bounds_missed=0,geoms_tested=0,triangles_tested=0,oversize_skipped=0,nontriangle_primitives=0);truncated=False;truncation_reasons=[];meshes=[];triangles=[];ids=[];started=time.monotonic();vertices_total=0
    paths=world.findAllMatches('**/+GeomNode');camera_mask=camera.node().getCameraMask()
    for ordinal,path in enumerate(paths):
        if ordinal>=20_000 or len(meshes)>=512 or time.monotonic()-started>45:
            truncated=True;truncation_reasons.append('node_mesh_or_time_budget');break
        counts['nodes_seen']+=1
        if path.isHidden(camera_mask):counts['hidden']+=1;continue
        bounds=path.getTightBounds(world)
        if bounds is None:counts['bounds_missed']+=1;continue
        minimum,maximum=[list(v) for v in bounds]
        padded_min=(np.asarray(minimum)-1e-4).tolist();padded_max=(np.asarray(maximum)+1e-4).tolist()
        if not any(g.ray_box(r['origin'],r['direction'],padded_min,padded_max,r['max_distance']) for r in rays):counts['bounds_missed']+=1;continue
        node=path.node();matrix=path.getMat(world);matrix_rows=np.array(_matrix(matrix),float)
        for geom_index in range(node.getNumGeoms()):
            geom=node.getGeom(geom_index);data=geom.getVertexData();n=data.getNumRows()
            if n+vertices_total>500_000:counts['oversize_skipped']+=1;truncated=True;truncation_reasons.append('vertex_budget');continue
            reader=core.GeomVertexReader(data,'vertex');vertices=np.array([list(reader.getData3f()) for _ in range(n)],float).reshape((n,3));vertices_total+=n
            homogeneous=np.column_stack((vertices,np.ones(n)))@matrix_rows
            g.need(np.isfinite(homogeneous).all() and np.all(homogeneous[:,3]!=0),'finite CPU world vertices');vertices=homogeneous[:,:3]/homogeneous[:,3,None]
            mesh_id=len(meshes);primitive_counts=[];state=path.getNetState().compose(node.getGeomState(geom_index));begin=len(triangles)
            for primitive_index in range(geom.getNumPrimitives()):
                primitive=geom.getPrimitive(primitive_index).decompose();primitive_counts.append(primitive.getNumPrimitives())
                for index in range(primitive.getNumPrimitives()):
                    first,last=primitive.getPrimitiveStart(index),primitive.getPrimitiveEnd(index)
                    if last-first!=3:counts['nontriangle_primitives']+=1;continue
                    if len(triangles)>=g.MAX_TRIANGLES:truncated=True;truncation_reasons.append('triangle_budget');break
                    indices=[int(primitive.getVertex(v)) for v in range(first,last)];triangles.append(vertices[indices]);ids.append([mesh_id,primitive_index,index,*indices])
                if len(triangles)>=g.MAX_TRIANGLES:break
            meshes.append(dict(mesh_id=mesh_id,node_ordinal=ordinal,path=str(path),node_name=node.getName(),geom_index=geom_index,vertex_count=n,source_primitive_count=geom.getNumPrimitives(),primitive_triangle_counts=primitive_counts,triangle_start=begin,triangle_end=len(triangles),local_to_world=_matrix(matrix),bounds_min=minimum,bounds_max=maximum,net_state_text=str(state)[:4096],net_state_text_truncated=len(str(state))>4096,net_state_pointer=int(state.this),vertex_data_pointer=int(data.this),transform_pointer=int(path.getNetTransform().this),geom_pointer=int(geom.this),vertex_format=str(data.getFormat())[:1024]))
            counts['geoms_tested']+=1
        if len(triangles)>=g.MAX_TRIANGLES:break
    packed=np.asarray(triangles,dtype='<f8').reshape((-1,3,3));sources=np.asarray(ids,dtype='<i8').reshape((-1,6));archive=g.save_geometry_archive(out/'geometry.npz',packed,sources);counts['triangles_tested']=len(packed)
    return dict(stage='AFTER_ORIGINAL_ROAD_CPU_READ_BEFORE_CAMERA_RESTORE',borrowed_parent_is_origin=camera.getParent()==engine.origin,source_viewport=viewport,source_buffer_size=[964,604],camera_node_path=str(camera),camera_to_world=_matrix(camera_matrix),lens_projection=_matrix(lens.getProjectionMat()),lens_near=float(lens.getNear()),lens_far=float(lens.getFar()),framebuffer_reported_depth_bits=int(fb.getDepthBits()),framebuffer_reported_multisamples=int(fb.getMultisamples()),framebuffer_properties=str(fb),camera_mask=str(camera_mask),camera_initial_state=str(camera.node().getInitialState())[:16_384],rays=rays,meshes=meshes,counts=counts,triangle_archive=archive,hits=g.all_ray_hits(packed,rays),scan_finished_within_budget=not truncated,truncation_reasons=sorted(set(truncation_reasons)),budgets=dict(max_nodes=20_000,max_meshes=512,max_vertices=500_000,max_triangles=g.MAX_TRIANGLES,max_cpu_seconds=45),cpu_scan_seconds=time.monotonic()-started,cpu_solver_epsilon=g.SOLVER_EPSILON,cpu_bounds_padding_world_units=1e-4,cpu_ray_reprojection_max_abs_ndc_error=g.ray_projection_error(rays,camera_rows,_matrix(lens.getProjectionMat())),cpu_sample_rays_not_msaa_positions=True,cpu_net_state_not_actual_cull_draw_state=True,cpu_scene_coverage_proven=False,gpu_pixel_owner_proven=False,depth_tie_proven=False,unique_cause_proven=False)


def run_native(args):
    import ctypes,hashlib,json,math,uuid,zlib,numpy as np
    from scripts import panda_sdk3_runtime as p
    from scripts import sdk3_pixel_geometry as g
    out=Path(args.out);provider=None;report=dict(protocol='sdk3-pixel-geometry-v1',status='FAILED',pid=os.getpid(),process_uuid=uuid.uuid4().hex,nonce=args.nonce,repeat=args.repeat,seed=20261110,scenario='s_curve_left_right',official_model_processes=0,onnx_inferences=0,ort_used=False,model_weights_used=False,repair_proven=False,stage7_complete=False,provider_closed=False,captures=[])
    try:
        p.need(args.server_owner==os.getppid(),'owned zero-model renderer child');report['checkpoint']='OWNED_BOOT';p.write(out/'report.json',report);sys.path.insert(0,p.SITE);import panda3d.core as core
        report['core_sha256']=p.digest(Path(core.__file__));report['panda_version']=core.PandaSystem.getVersionString()
        preload=ctypes.CDLL(p.SITE+'/panda3d/libpanda.so.1.10',mode=os.RTLD_NOW|os.RTLD_GLOBAL);sdk=ctypes.CDLL(p.SDK_PATH,mode=os.RTLD_NOW|os.RTLD_LOCAL)
        report['sdk_sha256']=p.digest(Path(p.SDK_PATH));p.need(report['core_sha256']==p.CORE_SHA and report['sdk_sha256']==p.SDK_SHA,'actual frozen core/SDK bytes');report['checkpoint']='SDK_VERIFIED';p.write(out/'report.json',report)
        raw=Path('/reference.json').read_bytes();reference=json.loads(raw);report['reference_sha256']=hashlib.sha256(raw).hexdigest()
        from bigbench.metadrive_camera import NativeMetaDriveProvider
        from bigbench.native_model_campaign import NativeWorldCamera
        from bigbench.curved_lane_scenarios import SCENARIOS,select_native_curve_lanes
        from bigbench.kinematics import AgentState
        import metadrive.component.sensors.base_camera as camera_module
        report['base_camera_sha256']=p.digest(Path(camera_module.__file__))
        provider=NativeMetaDriveProvider(seed=20261110,map_config=SCENARIOS['s_curve_left_right'].map_config());engine=provider.env.engine;sensor=engine.sensors['bigbench_road'];lane=select_native_curve_lanes(provider.env.current_map,SCENARIOS['s_curve_left_right'])[0]
        s=float(lane.length)*.12;xy=lane.position(s,0.);initial=dict(t=0.,x=float(xy[0]),y=float(xy[1]),heading=float(lane.heading_theta_at(s)),speed=8.)
        poses=[initial,*reference['previous_states']];target={}
        class TargetRGB:
            def __init__(self):self.count=0
            def record_native_rgb(self,rgb,hashes):
                self.count+=1
                if self.count==7:target.update(rgb=rgb,hashes=hashes)
        capture=NativeWorldCamera(provider,raw_rgb_observer=TargetRGB());clock=core.ClockObject.getGlobalClock();frame_before=clock.getFrameCount();tasks=lambda:sorted(t.getName() for t in engine.taskMgr.getTasks());before=tasks()
        report['tasks_before']=before;report['checkpoint']='WORLD_READY';p.write(out/'report.json',report)
        original_getter=sensor.get_rgb_array_cpu;original_owned_getter='get_rgb_array_cpu' in vars(sensor)
        def inspect(rgb):
            report['target_read_sha256']=hashlib.sha256(rgb.tobytes(order='C')).hexdigest();report['checkpoint']='TARGET_ROAD_READ';p.write(out/'report.json',report);report['geometry']=snapshot_geometry(core,engine,sensor,out)
        with g.post_read_observer(sensor,inspect,target_call=7) as observer:
            for step,pose in enumerate(poses,1):
                capture.capture(AgentState(**pose));hashes=capture.last_source_rgb_sha256;report['captures'].append(dict(step=step,pose=pose,road_sha256=hashes['road'],wide_sha256=hashes['wide']))
        report['observer']=observer;report['tasks_after']=tasks();report['task_frame_count_delta']=clock.getFrameCount()-frame_before
        report['getter_restored']=sensor.get_rgb_array_cpu==original_getter and ('get_rgb_array_cpu' in vars(sensor))==original_owned_getter
        p.need(target and report['target_read_sha256']==target['hashes']['road'],'target pixels unchanged by CPU inspection')
        images=[]
        for camera in ('road','wide'):
            pixels=target['rgb'][camera].tobytes(order='C');name='step7-'+camera+'.rgb.zlib';compressed=zlib.compress(pixels,6);(out/name).write_bytes(compressed);images.append(dict(camera=camera,file=name,shape=[604,964,3],sha256=hashlib.sha256(pixels).hexdigest(),raw_bytes=len(pixels),compressed_bytes=len(compressed)))
        report['target_images']=images;report['target_road_rgb']=target['rgb']['road'][494,596].tolist();report['replay']=g.qualify_replay(report['captures'],reference);report['status']='ZERO_MODEL_REPLAY_RECORDED'
        gsg=sensor.buffer.getGsg();report['driver']=dict(vendor=gsg.getDriverVendor(),renderer=gsg.getDriverRenderer(),version=gsg.getDriverVersion());report['extra_gpu_queries']=0;report['extra_render_tasks']=0;report['ort_module_loaded']=any(k=='onnxruntime' or k.startswith('onnxruntime.') for k in sys.modules)
        return report
    except BaseException as error:report['failure']=type(error).__name__+': '+str(error);raise
    finally:
        if provider is not None:
            try:provider.close();report['provider_closed']=True
            except BaseException as error:report['close_failure']=type(error).__name__+': '+str(error)
        p.write(out/'report.json',report)


def main():
    import faulthandler;faulthandler.enable()
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--nonce',required=True);parser.add_argument('--repeat',type=int,choices=(0,1),required=True);parser.add_argument('--owned-child',action='store_true');parser.add_argument('--server-owner',type=int);args=parser.parse_args();args.model_trial=False
    if args.owned_child:run_native(args);return 0
    return run_with_server(args)

if __name__=='__main__':raise SystemExit(main())
