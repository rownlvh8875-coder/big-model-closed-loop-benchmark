"""Read CPU-cached shader objects after original Road7 read, before restoration."""
from contextlib import contextmanager
from pathlib import Path
import argparse,json,os,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import sdk3_pixel_material_native as material,sdk3_pixel_geometry_budget_native as budget,panda_sdk3_runtime as p
from scripts.sdk3_capture_progress import stack_watchdog
_clone=None

def clone(function,**changes):
    from types import FunctionType
    fn=FunctionType(function.__code__,dict(function.__globals__,**changes),function.__name__,function.__defaults__,function.__closure__);fn.__kwdefaults__=dict(function.__kwdefaults__ or {});return fn

def texture_info(texture):
    return dict(pointer=int(texture.this),name=texture.getName(),**{key:int(getattr(texture,method)()) for key,method in [('x_size','getXSize'),('y_size','getYSize'),('z_size','getZSize'),('num_components','getNumComponents'),('component_width','getComponentWidth'),('component_type','getComponentType'),('format','getFormat'),('texture_type','getTextureType')]})

def input_info(core,attrib,name):
    if attrib is None or not attrib.hasShaderInput(core.InternalName.make(name)):return dict(name=name,status='MISSING')
    value=attrib.getShaderInput(name);kind=int(value.getValueType());row=dict(name=name,value_type=kind,priority=int(value.getPriority()))
    if kind in (1,5):row.update(status='AVAILABLE_TEXTURE',texture=texture_info(value.getTexture()))
    elif kind==3:row.update(status='AVAILABLE_VECTOR',vector=[float(v) for v in value.getVector()])
    elif kind==4:row['status']='UNAVAILABLE_NUMERIC_ARRAY'
    else:row['status']='UNAVAILABLE_TYPE'
    return row

def snapshot_shader(core,engine,sensor,geometry,out,nonce,journal):
    from scripts import sdk3_shader_path as s,run_sdk3_shader_path as h
    out=Path(out);m=json.loads((out/'material.json').read_text());started=time.monotonic();store=s.TextStore(out);shaders=[];lookup={};sources=[];meshes=[]
    x=dict(protocol='sdk3-shader-path-v1',pid=os.getpid(),nonce=nonce,status='SHADER_PARTIAL',limits=dict(h.LIMITS),clock='journal_elapsed_monotonic_seconds',shader_enter_elapsed_s=started-journal.started,shader_exit_elapsed_s=None,elapsed_wall_seconds=None,target_read_sha256=m['target_read_sha256'],geometry_archive_sha256=m['geometry_archive_sha256'],material_sha256=p.digest(out/'material.json'),borrowed_parent_is_origin=sensor.cam.getParent()==engine.origin,observer_finalized=False,selection_complete=False,truncation_reasons=[],sources=sources,bytes_captured=0,pipeline=None,shaders=shaders,meshes=meshes,camera=dict(initial_state_text=str(sensor.cam.node().getInitialState())[:16384],tag_state_key=str(sensor.cam.node().getTagStateKey())),tonemap=None,pssm_owner=dict(available=False,input_values_bound_to_shader=False),known_input_scope='KNOWN_EIGHT_PSSM_NAMES_ONLY',all_inputs_enumerated=False,gpu_program_execution_proven=False,hardware_uniform_values_proven=False,gpu_pixel_owner_proven=False,unique_cause_proven=False,repair_proven=False,stage7_complete=False)
    p.write(out/'shader.json',x)
    def guard():
        if time.monotonic()-started>=20:raise TimeoutError('shader cooperative CPU inspection budget')
    def shader_id(attrib):
        shader=None if attrib is None else attrib.getShader()
        if shader is None:return None
        pointer=int(shader.this)
        if pointer in lookup:return lookup[pointer]
        p.need(len(shaders)<8,'shader object limit');stages={}
        for name,kind in [('vertex',core.Shader.ST_vertex),('fragment',core.Shader.ST_fragment)]:
            guard();text=shader.getText(kind);stages[name]=dict(filename=str(shader.getFilename(kind)),text=store.save(text,name) if text else None)
        index=len(shaders);shaders.append(dict(shader_id=index,pointer=pointer,language=int(shader.getLanguage()),error_flag=bool(shader.getErrorFlag()),stages=stages));lookup[pointer]=index;return index
    try:
        pipeline=engine.pbrpipe;p.need(pipeline is not None,'existing simplepbr pipeline');x['pipeline']=dict(max_lights=int(pipeline.max_lights),exposure=float(pipeline.exposure),**{key:bool(getattr(pipeline,key)) for key in s.CONFIG_FLAGS})
        root=(Path(p.SITE)/'metadrive').resolve()
        for name,pin in h.SOURCE_PINS.items():
            guard();path=(root/name).resolve();p.need(path.is_relative_to(root) and path.is_file() and path.stat().st_size==pin['nbytes']<=262144,'bounded immutable shader source');raw=path.read_bytes();p.need(__import__('hashlib').sha256(raw).hexdigest()==pin['sha256'],'same frozen source bytes');sources.append(dict(name=name,**store.save(raw.decode('utf-8'),'source')))
        paths=engine.render.findAllMatches('**/+GeomNode')
        for prior in m['meshes']:
            guard();path=paths[prior['node_ordinal']];p.need(str(path)==prior['path'],'same cached material scene path');state=path.getNetState().compose(path.node().getGeomState(prior['geom_index']));p.need(int(state.this)==prior['net_state_pointer'],'same material RenderState identity');attrib=state.getAttrib(core.ShaderAttrib.getClassSlot());p.need(attrib is not None,'cached mesh shader attrib');meshes.append(dict(mesh_id=prior['mesh_id'],net_state_pointer=int(state.this),shader_attrib_pointer=int(attrib.this),shader_id=shader_id(attrib),known_inputs=[input_info(core,attrib,name) for name in s.INPUT_NAMES]))
        guard();quad=sensor.tonemap_quad;state=quad.getNetState();attrib=state.getAttrib(core.ShaderAttrib.getClassSlot());p.need(attrib is not None,'existing Road tonemap shader');x['tonemap']=dict(shader_id=shader_id(attrib),net_state_pointer=int(state.this),shader_attrib_pointer=int(attrib.this),quad_path=str(quad),scene_texture=texture_info(sensor.scene_tex),copy_texture_pointer=int(sensor.copy_texture.this),tex_input=input_info(core,attrib,'tex'),exposure_input=input_info(core,attrib,'exposure'))
        shadow=engine.pssm;rig=shadow.camera_rig;x['pssm_owner']=dict(available=True,input_values_bound_to_shader=False,num_splits=int(shadow.num_splits),use_pssm=bool(shadow.use_pssm),fog=bool(shadow.fog),freeze_pssm=bool(shadow.freeze_pssm),border_bias=float(shadow.border_bias),mvp_array=[material._matrix(matrix) for matrix in rig.get_mvp_array()],nearfar_array=[[float(v) for v in row] for row in rig.get_nearfar_array()]);guard();x.update(status='SHADER_RECORDED',selection_complete=True)
    except BaseException as error:x.update(failure=type(error).__name__+': '+str(error)[:256],truncation_reasons=['time_budget' if isinstance(error,TimeoutError) else 'inspection_error'])
    stopped=time.monotonic();x.update(shader_exit_elapsed_s=stopped-journal.started,elapsed_wall_seconds=stopped-started,bytes_captured=store.used);p.write(out/'shader.json',x);return x

def material_and_shader(core,engine,sensor,geometry,out,nonce,journal):
    result=material.snapshot_material(core,engine,sensor,geometry,out,nonce,journal);snapshot_shader(core,engine,sensor,geometry,out,nonce,journal);return result

@contextmanager
def shader_observe(camera,journal,out,nonce):
    observer=contextmanager(clone(material.material_observe.__wrapped__,snapshot_material=material_and_shader))
    try:
        with observer(camera,journal,out,nonce):yield
    finally:
        path=Path(out)/'shader.json';parent=Path(out)/'material.json'
        if path.exists() and parent.exists():
            x=json.loads(path.read_text())
            if 'material_sha256' in x:x['observer_finalized']=json.loads(parent.read_text()).get('observer_finalized') is True;x['material_sha256']=p.digest(parent);p.write(path,x)

def run_native(args):
    p.need(args.server_owner==os.getppid(),'owned cached shader observer child');p.write(Path(args.out)/'shader.json',dict(protocol='sdk3-shader-path-v1',pid=os.getpid(),nonce=args.nonce,status='OWNED_BOOT'));return clone(material.run_native,material_observe=shader_observe)(args)

def owned_child_command(args,parent_pid):return [sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--owned-child','--server-owner',str(parent_pid),'--out',args.out,'--repeat','0','--nonce',args.nonce]

def run_with_server(args):return clone(budget.run_with_server,owned_child_command=owned_child_command)(args)

def main():
    import faulthandler;faulthandler.enable();parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--nonce',required=True);parser.add_argument('--repeat',type=int,choices=(0,),required=True);parser.add_argument('--owned-child',action='store_true');parser.add_argument('--server-owner',type=int);args=parser.parse_args();args.model_trial=False
    if args.owned_child:
        with stack_watchdog(Path(args.out)/'stacks.log'):run_native(args)
        return 0
    return 0 if run_with_server(args)==0 else 1
if __name__=='__main__':raise SystemExit(main())
