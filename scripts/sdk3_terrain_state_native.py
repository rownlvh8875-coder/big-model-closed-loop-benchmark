"""Observe CPU-cached procedural terrain after the original Road7 read."""
from contextlib import contextmanager
from pathlib import Path
import argparse,hashlib,json,os,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import sdk3_shader_cache_native as cached,sdk3_shader_path_native as previous,panda_sdk3_runtime as p,sdk3_terrain_state as terrain
from scripts.sdk3_pssm_matrix import matrix_rows
from scripts.sdk3_capture_progress import stack_watchdog

class TextStore:
    def __init__(self,out):self.out=Path(out);self.used=0;self.sequence=0
    def save(self,text):
        raw=text.encode('utf-8');p.need(0<len(raw)<=262144 and self.used+len(raw)<=2097152,'bounded terrain source/cache bytes');self.sequence+=1;name=f'terrain-text-{self.sequence:03}.txt';(self.out/name).write_bytes(raw);self.used+=len(raw);return dict(file=name,nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def snapshot_terrain(core,engine,sensor,geometry,out,nonce,journal):
    from scripts.run_sdk3_terrain_state import TERRAIN_SOURCE_PINS
    from scripts.sdk3_pixel_material_native import _sampler
    out=Path(out);started=time.monotonic();store=TextStore(out);prior=json.loads((out/'shader.json').read_text());shaders=[];lookup={}
    x=dict(protocol='sdk3-terrain-state-v1',pid=os.getpid(),nonce=nonce,status='TERRAIN_PARTIAL',limits=dict(terrain.LIMITS),clock='journal_elapsed_monotonic_seconds',terrain_enter_elapsed_s=started-journal.started,terrain_exit_elapsed_s=None,elapsed_wall_seconds=None,target_read_sha256=prior['target_read_sha256'],geometry_archive_sha256=prior['geometry_archive_sha256'],shader_sha256=p.digest(out/'shader.json'),borrowed_parent_is_origin=sensor.cam.getParent()==engine.origin,observer_finalized=False,selection_complete=False,truncation_reasons=[],sources=[],bytes_captured=0,terrain_present=False,owner=dict(available=False),node=None,camera=None,states=[],shaders=shaders,textures=[],samples=[],known_input_scope='KNOWN_TWENTY_FOUR_NAMES_ONLY',all_inputs_enumerated=False,cpu_candidates_are_terrain_intersections=False,states_are_actual_cull_state=False,gpu_program_execution_proven=False,hardware_uniform_values_proven=False,gpu_pixel_owner_proven=False,depth_tie_proven=False,unique_cause_proven=False,repair_proven=False,stage7_complete=False)
    p.write(out/'terrain.json',x)
    def guard():p.need(time.monotonic()-started<=20,'terrain CPU inspection time budget')
    def shader_id(attrib):
        shader=None if attrib is None else attrib.getShader()
        if shader is None:return None
        pointer=int(shader.this)
        if pointer in lookup:return lookup[pointer]
        p.need(len(shaders)<4,'bounded terrain shaders');index=len(shaders);stages={};shaders.append(dict(shader_id=index,pointer=pointer,language=int(shader.getLanguage()),error_flag=bool(shader.getErrorFlag()),stages=stages));lookup[pointer]=index
        for name,kind in [('vertex',core.Shader.ST_vertex),('fragment',core.Shader.ST_fragment)]:
            guard();text=shader.getText(kind);stages[name]=dict(filename=str(shader.getFilename(kind)),text=store.save(text) if text else None)
        return index
    try:
        root=(Path(p.SITE)/'metadrive').resolve()
        for name,pin in TERRAIN_SOURCE_PINS.items():
            guard();path=(root/name).resolve();p.need(path.is_relative_to(root) and path.is_file() and path.stat().st_size==pin['nbytes']<=262144,'bounded immutable terrain source');raw=path.read_bytes();p.need(hashlib.sha256(raw).hexdigest()==pin['sha256'],'same pinned terrain source');x['sources'].append(dict(name=name,**store.save(raw.decode('utf-8'))))
        owner=getattr(engine,'terrain',None);path=None if owner is None else getattr(owner,'_mesh_terrain',None)
        if owner is not None:x['owner']=dict(available=True,render=bool(owner.render),use_mesh_terrain=bool(owner.use_mesh_terrain),terrain_size=int(owner._terrain_size),height_scale=float(owner._height_scale),elevation_ratio=float(owner._elevation_texture_ratio))
        if path is not None and not path.isEmpty():
            camera=sensor.cam.node();key=str(camera.getTagStateKey());value=str(path.getNetTag(key));node=path.node();net=path.getNetState();initial=camera.getInitialState();tag=camera.getTagState(value);combined=net.compose(tag);slot=core.ShaderAttrib.getClassSlot()
            x.update(terrain_present=True,camera=dict(tag_state_key=key,tag_value=value,has_tag_state=bool(camera.hasTagState(value))),node=dict(path=str(path),name=str(node.getName()),node_type=str(node.getType().getName()),pointer=int(node.this),is_geom_node=bool(node.isOfType(core.GeomNode.getClassType())),direct_tag=str(path.getTag(key)),cpu_hidden=bool(path.isHidden(camera.getCameraMask())),local_to_world=matrix_rows(core,path.getMat(engine.render)),heightfield_pointer=int(node.getHeightfield().this)))
            for role,state in [('node_net',net),('camera_initial',initial),('camera_tag',tag),('cpu_net_then_tag',combined)]:
                guard();attrib=state.getAttrib(slot);x['states'].append(dict(role=role,pointer=int(state.this),shader_override=int(state.getOverride(slot)),shader_attrib_pointer=None if attrib is None else int(attrib.this),shader_id=shader_id(attrib),text=str(state)[:16384],known_inputs=[previous.input_info(core,attrib,name) for name in terrain.INPUT_NAMES]))
            x['samples']=terrain.candidate_samples(geometry['hits'],x['node']['local_to_world'],x['owner']['elevation_ratio'])
            for role,texture,uv_key in [('attribute',owner.semantic_tex,'attribute_uv'),('heightfield',owner.heightfield_tex,'heightfield_uv'),('yellow',owner.yellow_lane_line,'yellow_uv')]:
                guard();x['textures'].append(dict(role=role,texture=previous.texture_info(texture),default_sampler=_sampler(texture.getDefaultSampler()),windows=[dict(sample_index=i,window=terrain.resident_window(texture,sample[uv_key],core)) for i,sample in enumerate(x['samples'])]))
        guard();x.update(status='TERRAIN_RECORDED',selection_complete=True)
    except BaseException as error:x.update(failure=type(error).__name__+': '+str(error)[:256],truncation_reasons=['inspection_error'])
    stopped=time.monotonic();x.update(terrain_exit_elapsed_s=stopped-journal.started,elapsed_wall_seconds=stopped-started,bytes_captured=store.used);p.write(out/'terrain.json',x);return x

def material_shader_terrain(core,engine,sensor,geometry,out,nonce,journal):
    result=cached.material_and_shader(core,engine,sensor,geometry,out,nonce,journal);snapshot_terrain(core,engine,sensor,geometry,out,nonce,journal);return result

@contextmanager
def terrain_observe(camera,journal,out,nonce):
    observer=contextmanager(previous.clone(previous.shader_observe.__wrapped__,material_and_shader=material_shader_terrain))
    try:
        with observer(camera,journal,out,nonce):yield
    finally:
        path=Path(out)/'terrain.json';parent=Path(out)/'shader.json'
        if path.exists() and parent.exists():
            x=json.loads(path.read_text())
            if 'shader_sha256' in x:x.update(observer_finalized=json.loads(parent.read_text()).get('observer_finalized') is True,shader_sha256=p.digest(parent));p.write(path,x)

def run_native(args):
    p.write(Path(args.out)/'terrain.json',dict(protocol='sdk3-terrain-state-v1',pid=os.getpid(),nonce=args.nonce,status='OWNED_BOOT'));return previous.clone(previous.run_native,shader_observe=terrain_observe)(args)

def owned_child_command(args,parent_pid):return [sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--owned-child','--server-owner',str(parent_pid),'--out',args.out,'--repeat','0','--nonce',args.nonce]
def run_with_server(args):return previous.clone(previous.budget.run_with_server,owned_child_command=owned_child_command)(args)
def main():
    import faulthandler;faulthandler.enable();parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--nonce',required=True);parser.add_argument('--repeat',type=int,choices=(0,),required=True);parser.add_argument('--owned-child',action='store_true');parser.add_argument('--server-owner',type=int);args=parser.parse_args();args.model_trial=False
    if args.owned_child:
        with stack_watchdog(Path(args.out)/'stacks.log'):run_native(args)
        return 0
    return 0 if run_with_server(args)==0 else 1
if __name__=='__main__':raise SystemExit(main())
