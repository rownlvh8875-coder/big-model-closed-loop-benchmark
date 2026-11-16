"""CPU material snapshot inside unchanged measured-budget Road7 observer."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from types import FunctionType
import argparse,json,os,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk3_runtime as p,sdk3_pixel_geometry_budget_native as budget
from scripts.sdk3_capture_progress import stack_watchdog

LIMITS=dict(max_hits_per_ray=8,max_triangles=40,max_stages=8,max_textures=16,max_file_bytes=8388608,max_total_bytes=16777216,max_cpu_seconds=20)


def _matrix(matrix):return [[float(matrix.getCell(r,c)) for c in range(4)] for r in range(4)]


def _sampler(s):
    return dict(wrap_u=int(s.getWrapU()),wrap_v=int(s.getWrapV()),wrap_w=int(s.getWrapW()),minfilter=int(s.getMinfilter()),magfilter=int(s.getMagfilter()),effective_minfilter=int(s.getEffectiveMinfilter()),effective_magfilter=int(s.getEffectiveMagfilter()),anisotropic_degree=int(s.getAnisotropicDegree()),effective_anisotropic_degree=int(s.getEffectiveAnisotropicDegree()),border_color=[float(v) for v in s.getBorderColor()],min_lod=float(s.getMinLod()),max_lod=float(s.getMaxLod()),lod_bias=float(s.getLodBias()),text=str(s)[:4096])


def _material(core,state):
    attrib=state.getAttrib(core.MaterialAttrib.getClassSlot())
    if attrib is None or attrib.getMaterial() is None:return dict(available=False,text=str(attrib))
    material=attrib.getMaterial();result=dict(available=True,text=str(material)[:4096],name=material.getName(),shininess=float(material.getShininess()))
    for name in ('Ambient','Diffuse','Emission','Specular','BaseColor'):
        has=getattr(material,'has'+name,None);get=getattr(material,'get'+name,None)
        result[name.lower()]=dict(api_available=has is not None and get is not None,defined=bool(has()) if has is not None else None,value=[float(v) for v in get()] if has is not None and get is not None and has() else None)
    return result


def _attribute(core,data,column,vertices,required=None):
    reader=core.GeomVertexReader(data,column)
    if not reader.hasColumn():return dict(status='UNAVAILABLE_COLUMN',components=None,values=None)
    count=int(reader.getColumn().getNumComponents())
    if count not in (2,3,4) or (required is not None and count!=required):return dict(status='UNSUPPORTED_COMPONENT_COUNT',components=count,values=None)
    getter={2:reader.getData2f,3:reader.getData3f,4:reader.getData4f}[count];values=[]
    for vertex in vertices:reader.setRow(vertex);values.append([float(v) for v in getter()])
    return dict(status='CAPTURED',components=count,values=values)


def snapshot_material(core,engine,sensor,geometry,out,nonce,journal):
    import numpy as np
    from scripts import sdk3_pixel_geometry as g,sdk3_pixel_material as m
    out=Path(out);parent=json.loads((out/'geometry-observer.json').read_text());started=time.monotonic();entered=started-journal.started;reasons=set();store=m.BoundedStore(out);textures=[];texture_ids={};meshes=[];mesh_map={};triangles=[]
    result=dict(protocol='sdk3-pixel-material-v1',pid=os.getpid(),nonce=nonce,status='MATERIAL_PARTIAL',target_read_sha256=parent['target_read_sha256'],geometry_archive_sha256=geometry['triangle_archive']['sha256'],borrowed_parent_is_origin=sensor.cam.getParent()==engine.origin,clock='journal_elapsed_monotonic_seconds',material_enter_elapsed_s=entered,limits=dict(LIMITS),selected_triangle_indices=[],meshes=meshes,triangles=triangles,textures=textures,samples=[],shader_inputs_unenumerated=True,hardware_sampler_state_unobserved=True,gpu_material_result_proven=False,gpu_pixel_owner_proven=False,unique_cause_proven=False,repair_proven=False,stage7_complete=False)
    p.write(out/'material.json',result)
    wanted=[]
    for ray in geometry['rays']:
        hits=geometry['hits'][ray['name']]
        if len(hits)>8:reasons.add('hit_budget')
        for hit in hits[:8]:
            if hit['triangle_index'] not in wanted:wanted.append(hit['triangle_index'])
    if len(wanted)>40:reasons.add('triangle_budget');wanted=wanted[:40]
    packed,ids=g.load_geometry_archive(out/'geometry.npz',geometry['triangle_archive']);paths=engine.render.findAllMatches('**/+GeomNode');roots=[Path(p.SITE)/'metadrive/assets']
    def expired():
        if time.monotonic()-started>=20:reasons.add('time_budget');return True
        return False
    def texture_record(texture):
        pointer=int(texture.this)
        if pointer in texture_ids:return texture_ids[pointer]
        if len(textures)>=16:reasons.add('texture_budget');return None
        index=len(textures);fullpath=str(texture.getFullpath());row=dict(texture_id=index,pointer=pointer,name=texture.getName(),filename=str(texture.getFilename()),fullpath=fullpath,x_size=int(texture.getXSize()),y_size=int(texture.getYSize()),z_size=int(texture.getZSize()),num_components=int(texture.getNumComponents()),component_width=int(texture.getComponentWidth()),component_type=int(texture.getComponentType()),format=int(texture.getFormat()),texture_type=int(texture.getTextureType()))
        row['ram']=m.capture_cached_ram(texture,store);row['asset']=store.copy_asset(fullpath,roots);textures.append(row);texture_ids[pointer]=index;return index
    try:
        for index in wanted:
            if expired():break
            source=ids[index].tolist();mesh_id,primitive_index,decomposed_index,*vertices=source;original=geometry['meshes'][mesh_id];path=paths[original['node_ordinal']];p.need(str(path)==original['path'],'same CPU scene path');node=path.node();geom=node.getGeom(original['geom_index']);data=geom.getVertexData()
            p.need(int(geom.this)==original['geom_pointer'] and int(data.this)==original['vertex_data_pointer'],'same source Geom/vertex data')
            primitive=geom.getPrimitive(primitive_index).decompose();begin=primitive.getPrimitiveStart(decomposed_index);end=primitive.getPrimitiveEnd(decomposed_index);p.need(end-begin==3 and [int(primitive.getVertex(v)) for v in range(begin,end)]==vertices,'same source primitive vertex triple')
            if mesh_id not in mesh_map:
                state=path.getNetState().compose(node.getGeomState(original['geom_index']));text=str(state);p.need(text[:4096]==original['net_state_text'] and (len(text)>4096)==original['net_state_text_truncated'],'same cached net-state text');matrix=_matrix(path.getMat(engine.render));p.need(matrix==original['local_to_world'],'same source world transform')
                row=dict(mesh_id=mesh_id,node_ordinal=original['node_ordinal'],path=str(path),geom_index=original['geom_index'],geom_pointer=int(geom.this),vertex_data_pointer=int(data.this),local_to_world=matrix,net_state_text=text[:4096],net_state_text_truncated=len(text)>4096,net_state_pointer=int(state.this),stages=[],source_stage_count=0,material=_material(core,state))
                attrib=state.getAttrib(core.TextureAttrib.getClassSlot());texmatrix=state.getAttrib(core.TexMatrixAttrib.getClassSlot());count=0 if attrib is None else int(attrib.getNumOnStages());row['source_stage_count']=count
                if count>8:reasons.add('stage_budget')
                for stage_id in range(min(count,8)):
                    if expired():break
                    stage=attrib.getOnStage(stage_id);texture=attrib.getOnTexture(stage);tid=texture_record(texture)
                    if tid is None:break
                    effective=_sampler(attrib.getOnSampler(stage));default=_sampler(texture.getDefaultSampler());transform=np.eye(4).tolist() if texmatrix is None else _matrix(texmatrix.getTransform(stage).getMat())
                    row['stages'].append(dict(stage_id=stage_id,name=stage.getName(),sort=int(stage.getSort()),mode=int(stage.getMode()),texcoord_column=str(stage.getTexcoordName()),texture_id=tid,texture_matrix=transform,effective_sampler=effective,texture_default_sampler=default,differs_from_texture_default={k:v for k,v in effective.items() if k!='text'}!={k:v for k,v in default.items() if k!='text'}))
                meshes.append(row);mesh_map[mesh_id]=row
            position=_attribute(core,data,'vertex',vertices,required=3);p.need(position['status']=='CAPTURED' and np.allclose(g.transform_points(position['values'],original['local_to_world']),packed[index],rtol=1e-12,atol=1e-9),'retained source positions match geometry archive')
            columns={stage['texcoord_column'] for stage in mesh_map[mesh_id]['stages']};attributes={column:_attribute(core,data,core.InternalName.make(column),vertices) for column in sorted(columns)}
            triangles.append(dict(triangle_index=index,source_id=source,positions_local=position['values'],normals=_attribute(core,data,'normal',vertices,required=3),texcoords=attributes));result['selected_triangle_indices'].append(index)
        triangle_map={t['triangle_index']:t for t in triangles}
        for ray in geometry['rays']:
            for hit in geometry['hits'][ray['name']][:8]:
                index=hit['triangle_index']
                if index not in triangle_map:continue
                triangle=triangle_map[index];sample=dict(ray=ray['name'],triangle_index=index,barycentric=hit['barycentric'],stages=[])
                for stage in mesh_map[triangle['source_id'][0]]['stages']:
                    column=stage['texcoord_column'];attribute=triangle['texcoords'][column];row=dict(stage_id=stage['stage_id'],texture_id=stage['texture_id'],column=column,status=attribute['status'],uv=None,transformed4=None)
                    if attribute['status']=='CAPTURED' and attribute['components']==2:row.update(status='CAPTURED',uv=m.interpolate_uv(attribute['values'],hit['barycentric']));row['transformed4']=m.transform_uv(row['uv'],stage['texture_matrix'])
                    else:row['status']='UNAVAILABLE_2D_UV'
                    sample['stages'].append(row)
                result['samples'].append(sample)
        expired();result.update(status='MATERIAL_RECORDED' if not reasons else 'MATERIAL_PARTIAL',selection_complete=not reasons,truncation_reasons=sorted(reasons),bytes_captured=store.used,material_exit_elapsed_s=time.monotonic()-journal.started,cpu_seconds=time.monotonic()-started);p.write(out/'material.json',result);return result
    except BaseException as error:
        result.update(failure=type(error).__name__+': '+str(error),selection_complete=False,truncation_reasons=sorted(reasons|{'inspection_error'}),bytes_captured=store.used,material_exit_elapsed_s=time.monotonic()-journal.started,cpu_seconds=time.monotonic()-started);p.write(out/'material.json',result);raise


@contextmanager
def material_observe(camera,journal,out,nonce):
    def snapshot(engine,sensor,folder):
        import panda3d.core as core
        from scripts.sdk3_pixel_geometry_native import snapshot_geometry
        geometry=snapshot_geometry(core,engine,sensor,folder);lens=sensor.get_lens();inverse=lens.getProjectionMatInv();geometry.update(lens_projection_inverse=_matrix(inverse),lens_inverse_dtype='float32',lens_far_limit=float(core.ConfigVariableDouble('lens-far-limit').getValue()));snapshot_material(core,engine,sensor,geometry,folder,nonce,journal);return geometry
    try:
        with budget.geometry_observe(camera,journal,out,nonce,snapshot=snapshot):yield
    finally:
        path=Path(out)/'material.json'
        if path.exists():
            result=json.loads(path.read_text());parent=json.loads((Path(out)/'geometry-observer.json').read_text());result['observer_finalized']=parent.get('observers_restored') is True;p.write(path,result)


def run_native(args):
    p.need(args.server_owner==os.getppid(),'owned material observer child');p.write(Path(args.out)/'material.json',dict(protocol='sdk3-pixel-material-v1',pid=os.getpid(),nonce=args.nonce,status='OWNED_BOOT'))
    original=budget.run_native;fn=FunctionType(original.__code__,dict(original.__globals__,geometry_observe=material_observe),original.__name__,original.__defaults__,original.__closure__);fn.__kwdefaults__=dict(original.__kwdefaults__ or {});return fn(args)


def owned_child_command(args,parent_pid):return [sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--owned-child','--server-owner',str(parent_pid),'--out',args.out,'--repeat','0','--nonce',args.nonce]


def run_with_server(args):
    original=budget.run_with_server;fn=FunctionType(original.__code__,dict(original.__globals__,owned_child_command=owned_child_command),original.__name__,original.__defaults__,original.__closure__);fn.__kwdefaults__=dict(original.__kwdefaults__ or {});return fn(args)


def main():
    import faulthandler;faulthandler.enable();parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--nonce',required=True);parser.add_argument('--repeat',type=int,choices=(0,),required=True);parser.add_argument('--owned-child',action='store_true');parser.add_argument('--server-owner',type=int);args=parser.parse_args();args.model_trial=False
    if args.owned_child:
        with stack_watchdog(Path(args.out)/'stacks.log'):run_native(args)
        return 0
    return 0 if run_with_server(args)==0 else 1
if __name__=='__main__':raise SystemExit(main())
