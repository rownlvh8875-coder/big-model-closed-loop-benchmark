"""Observe prepared texture CPU caches without preparing or querying the GPU."""
from contextlib import contextmanager
from pathlib import Path
import json,os,resource,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import sdk3_terrain_attribute_native as previous,sdk3_terrain_attribute as sparse,sdk3_prepared_texture as h
p=previous.p

def snapshot_prepared(core,engine,sensor,out,nonce,journal):
    out=Path(out);started=time.monotonic();rss_before=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;terrain=json.loads((out/'terrain.json').read_text())
    x=dict(protocol='sdk3-prepared-texture-v1',pid=os.getpid(),nonce=nonce,status='PREPARED_PARTIAL',policy=dict(h.POLICY),reference_index_sha256=h.REFERENCE_SHA256,clock='journal_elapsed_monotonic_seconds',prepared_enter_elapsed_s=started-journal.started,prepared_exit_elapsed_s=None,elapsed_wall_seconds=None,target_read_sha256=terrain['target_read_sha256'],geometry_archive_sha256=terrain['geometry_archive_sha256'],terrain_sha256=p.digest(out/'terrain.json'),material_sha256=p.digest(out/'material.json'),borrowed_parent_is_origin=sensor.cam.getParent()==engine.origin,observer_finalized=False,selection_complete=False,truncation_reasons=[],outputs=[],contexts=[],textures=[],mip1_sample_bytes_captured=0,reported_state_is_cpu_cache=True,**{k:False for k in h.FALSE_FLAGS})
    p.write(out/'prepared.json',x);objects=[];lookup={}
    def guard():p.need(time.monotonic()-started<=20,'prepared CPU time budget')
    try:
        buffers=getattr(getattr(sensor,'manager',None),'buffers',[]);p.need(isinstance(buffers,(list,tuple)) and len(buffers)<=4,'at most four existing filter buffers')
        outputs=[('engine_output',getattr(engine,'win',None)),('road_output',getattr(sensor,'buffer',None))]+[('filter_buffer_'+str(i),b) for i,b in enumerate(buffers)]
        for role,output in outputs:
            guard();gsg=None if output is None else output.getGsg()
            if gsg is None:x['outputs'].append(dict(role=role,available=False));x['truncation_reasons'].append('missing_'+role);continue
            pointer=int(gsg.this)
            if pointer not in lookup:
                pgo=gsg.getPreparedObjects();p.need(pgo is not None,'existing prepared objects');index=len(objects);p.need(index<6,'six cached GSGs');row=dict(context_index=index,gsg_pointer=pointer,pgo_pointer=int(pgo.this),max_texture_dimension=int(gsg.getMaxTextureDimension()),supports_tex_non_pow2=bool(gsg.getSupportsTexNonPow2()),max_texture_stages=int(gsg.getMaxTextureStages()));objects.append(pgo);x['contexts'].append(row);lookup[pointer]=index
            x['outputs'].append(dict(role=role,available=True,context_index=lookup[pointer]))
        if terrain['terrain_present']:
            owner=engine.terrain
            for role,texture in [('attribute',owner.semantic_tex),('heightfield',owner.heightfield_tex),('yellow',owner.yellow_lane_line)]:
                guard();mips=h.mip_metadata(texture);p.need(1<=mips['num_views']<=8,'eight cached texture views');metadata=next(r['texture'] for r in terrain['textures'] if r['role']==role);row=dict(role=role,pointer=int(texture.this),mips=mips,minimum_bias_by_context=[h.minimum_bias([metadata['x_size'],metadata['y_size']],c['max_texture_dimension']) for c in x['contexts']],cache=[],mip1_windows=[])
                for i,pgo in enumerate(objects):guard();row['cache'].append(dict(context_index=i,**h.texture_cache(texture,pgo)))
                if role=='attribute':
                    for i,sample in enumerate(terrain['samples']):
                        guard();window=h.mip1_window(texture,sample['attribute_uv'],core);row['mip1_windows'].append(dict(sample_index=i,window=window))
                x['textures'].append(row)
        guard()
        if not x['contexts']:x['truncation_reasons'].append('no_existing_gsg')
    except BaseException as error:x.update(failure=type(error).__name__+': '+str(error)[:256]);x['truncation_reasons'].append('inspection_error')
    total=sum(v['nbytes'] for t in x['textures'] for item in t['mip1_windows'] for v in item['window'].get('texels',[]));p.need(total<=80,'80byte mip1 observation budget');x['mip1_sample_bytes_captured']=total
    rss_after=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;x['rss_peak_kib']=[rss_before,rss_after]
    if rss_after-rss_before>32768:x['truncation_reasons'].append('rss_delta_budget')
    stopped=time.monotonic();x.update(prepared_exit_elapsed_s=stopped-journal.started,elapsed_wall_seconds=stopped-started)
    if stopped-started>20:x['truncation_reasons'].append('time_budget')
    x['truncation_reasons']=sorted(set(x['truncation_reasons']));x['selection_complete']=not x['truncation_reasons'];x['status']='PREPARED_RECORDED' if x['selection_complete'] else 'PREPARED_PARTIAL';p.write(out/'prepared.json',x);return x

def snapshot_terrain(core,engine,sensor,geometry,out,nonce,journal):
    result=previous.snapshot_terrain(core,engine,sensor,geometry,out,nonce,journal);snapshot_prepared(core,engine,sensor,out,nonce,journal);return result

def material_shader_terrain(*args,**kwargs):return sparse.clone(previous.previous.material_shader_terrain,snapshot_terrain=snapshot_terrain)(*args,**kwargs)

@contextmanager
def terrain_observe(camera,journal,out,nonce):
    observer=contextmanager(sparse.clone(previous.terrain_observe.__wrapped__,material_shader_terrain=material_shader_terrain))
    try:
        with observer(camera,journal,out,nonce):yield
    finally:
        q=Path(out)/'prepared.json';terrain=Path(out)/'terrain.json';material=Path(out)/'material.json'
        if q.exists() and terrain.exists() and material.exists():
            x=json.loads(q.read_text())
            if 'terrain_sha256' in x:x.update(observer_finalized=json.loads(terrain.read_text()).get('observer_finalized') is True,terrain_sha256=p.digest(terrain),material_sha256=p.digest(material));p.write(q,x)

def run_native(args):
    p.write(Path(args.out)/'prepared.json',dict(protocol='sdk3-prepared-texture-v1',pid=os.getpid(),nonce=args.nonce,status='OWNED_BOOT'));return sparse.clone(previous.run_native,terrain_observe=terrain_observe)(args)
def owned_child_command(args,parent_pid):return sparse.clone(previous.owned_child_command,__file__=__file__)(args,parent_pid)
def run_with_server(args):return sparse.clone(previous.run_with_server,owned_child_command=owned_child_command)(args)
def main():return sparse.clone(previous.main,run_native=run_native,run_with_server=run_with_server)()
if __name__=='__main__':raise SystemExit(main())
