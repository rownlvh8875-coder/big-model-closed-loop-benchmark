"""Authenticate prepared cache observations without promoting hardware claims."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,sys,math
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import run_sdk3_terrain_attribute as previous,sdk3_terrain_attribute as sparse,sdk3_prepared_texture as h
from scripts.run_sdk3_terrain_attribute import p,g,cache,unpack_prior,observation_summary,LIMITS,runtime,TERRAIN_LIMITS
ROOT=Path(__file__).resolve().parents[1];BASE='bf71fb9a794506b1fc64f996f4ff062cbb1b98a4';REQUEST='docs/requests/sdk3-prepared-texture-20261117-01.json';ENTRY='/work/repo/scripts/sdk3_prepared_texture_native.py'

def native_command(*args,**kwargs):
    command=runtime.native_command(*args,**kwargs);command[command.index(runtime.ENTRY)]=ENTRY;return command

def run_renderer(name,sdk,out,args,reference):return sparse.clone(runtime.run_renderer,native_command=native_command)(name,sdk,out,args,reference)

def validate_prepared(folder,nonce,result):
    folder=Path(folder);q=folder/'prepared.json';p.need(q.stat().st_size<=1048576,'bounded prepared manifest');x=json.loads(q.read_text());result.update(prepared_recorded=False,prepared_complete=False,mip1_window_count=0,mip1_collection_complete=False,mip1_sample_bytes_captured=0,**{k:False for k in h.FALSE_FLAGS})
    p.need(x.get('protocol')=='sdk3-prepared-texture-v1' and x.get('pid')==result['pid'] and x.get('nonce')==nonce,'same prepared observer identity')
    if not result.get('terrain_recorded') or x.get('status')=='OWNED_BOOT':p.need(not result['native_completed'],'completed native requires prepared boundary');return result
    terrain=json.loads((folder/'terrain.json').read_text());p.need(x.get('target_read_sha256')==terrain['target_read_sha256'] and x.get('geometry_archive_sha256')==terrain['geometry_archive_sha256'] and x.get('terrain_sha256')==p.digest(folder/'terrain.json') and x.get('material_sha256')==p.digest(folder/'material.json'),'prepared final terrain/material/target/archive binding')
    p.need(x.get('observer_finalized') is True and x.get('borrowed_parent_is_origin') is True and x.get('reported_state_is_cpu_cache') is True and all(x.get(k) is False for k in h.FALSE_FLAGS),'cached metadata never proves hardware size, upload bias, pixel or repair')
    p.need(x.get('policy')==h.POLICY and x.get('reference_index_sha256')==h.REFERENCE_SHA256==p.digest(ROOT/'docs/evidence/sdk3-prepared-texture-01/reference-index.json'),'exact prepared observation/reference policy')
    rows=[json.loads(line) for line in (folder/'progress.jsonl').read_text().splitlines()];end=next(r['elapsed_s'] for r in rows if r['event']=='checkpoint' and r['metadata'].get('stage')=='GEOMETRY_RETURN');start,stop,elapsed=[x.get(k) for k in ('prepared_enter_elapsed_s','prepared_exit_elapsed_s','elapsed_wall_seconds')]
    p.need(x.get('clock')=='journal_elapsed_monotonic_seconds' and all(type(v) in (int,float) and math.isfinite(v) for v in (start,stop,elapsed)) and terrain['terrain_exit_elapsed_s']<=start<=stop<=end and abs(stop-start-elapsed)<=1e-6,'prepared interval after terrain inside original geometry boundary')
    complete=x.get('selection_complete');reasons=x.get('truncation_reasons');p.need(type(complete) is bool and isinstance(reasons,list) and len(reasons)<=16 and all(isinstance(v,str) and len(v)<=128 for v in reasons) and complete==(not reasons) and x.get('status')==('PREPARED_RECORDED' if complete else 'PREPARED_PARTIAL') and (elapsed<=20 or not complete and 'time_budget' in reasons),'explicit bounded prepared complete/partial')
    rss=x.get('rss_peak_kib');p.need(isinstance(rss,list) and len(rss)==2 and all(type(v) is int and v>=0 for v in rss) and rss[1]>=rss[0],'typed prepared RSS highwater');delta=rss[1]-rss[0];p.need(delta<=32768 or not complete and 'rss_delta_budget' in reasons,'prepared RSS overrun cannot claim complete')
    outputs=x.get('outputs');contexts=x.get('contexts');textures=x.get('textures');p.need(isinstance(outputs,list) and len(outputs)<=6 and isinstance(contexts,list) and len(contexts)<=6 and isinstance(textures,list) and len(textures)<=3,'bounded prepared tables');roles=['engine_output','road_output']+['filter_buffer_'+str(i) for i in range(4)];p.need([r.get('role') for r in outputs]==roles[:len(outputs)] and (not complete or len(outputs)>=2 and contexts),'ordered prepared output sources')
    for i,c in enumerate(contexts):
        p.need(set(c)=={'context_index','gsg_pointer','pgo_pointer','max_texture_dimension','supports_tex_non_pow2','max_texture_stages'} and c['context_index']==i and all(type(c.get(k)) is int and c[k]>0 for k in ('gsg_pointer','pgo_pointer')) and type(c.get('max_texture_dimension')) is int and -1<=c['max_texture_dimension']<=2**24 and type(c.get('supports_tex_non_pow2')) is bool and type(c.get('max_texture_stages')) is int and 0<=c['max_texture_stages']<=65536,'typed cached GSG limits/identity')
    p.need(len({c['gsg_pointer'] for c in contexts})==len(contexts),'deduplicated GSG pointers');used=set()
    for row in outputs:
        p.need(type(row.get('available')) is bool,'explicit output availability')
        if not row['available']:p.need(set(row)=={'role','available'} and not complete and 'missing_'+row['role'] in reasons,'missing output explicit partial')
        else:p.need(set(row)=={'role','available','context_index'} and type(row['context_index']) is int and 0<=row['context_index']<len(contexts),'source context binding');used.add(row['context_index'])
    p.need(used==set(range(len(contexts))),'all cached contexts source-bound')
    owners=terrain['textures'];p.need([r.get('role') for r in textures]==[r['role'] for r in owners[:len(textures)]] and (not complete or len(textures)==len(owners)),'exact terrain owner texture roles');captured=total=0
    for row,owner in zip(textures,owners):
        info=owner['texture'];p.need(row.get('pointer')==info['pointer'],'same owner texture pointer');m=row.get('mips');p.need(isinstance(m,dict) and set(m)=={'num_views','num_ram_mipmap_images','levels'} and type(m['num_views']) is int and 1<=m['num_views']<=8 and type(m['num_ram_mipmap_images']) is int and 0<=m['num_ram_mipmap_images']<=32 and isinstance(m['levels'],list) and len(m['levels'])==4,'bounded views and RAM mip metadata')
        for n,level in enumerate(m['levels']):
            size=[max(1,info[k]>>n) for k in ('x_size','y_size')];expected=size[0]*size[1]*info['num_components']*info['component_width']*info['z_size']*m['num_views']
            p.need(set(level)=={'level','size_xy','expected_nbytes','resident','cached_nbytes'} and type(level['level']) is int and level['level']==n and level['size_xy']==size and type(level['expected_nbytes']) is int and level['expected_nbytes']==expected and type(level['resident']) is bool and type(level['cached_nbytes']) is int and 0<=level['cached_nbytes']<=2**48 and (level['resident'] or level['cached_nbytes']==0) and (n<m['num_ram_mipmap_images'] or not level['resident'] and level['cached_nbytes']==0),'recomputed bounded existing RAM mip layout')
        p.need(row.get('minimum_bias_by_context')==[h.minimum_bias([info['x_size'],info['y_size']],c['max_texture_dimension']) for c in contexts],'cached-cap minimum bias inference only');stats=row.get('cache');p.need(isinstance(stats,list) and len(stats)==len(contexts),'one cache observation per GSG')
        for i,s in enumerate(stats):p.need(set(s)=={'context_index','queued_or_prepared','reported_graphics_bytes','active_recent_frame','resident_reported','image_modified_or_unprepared'} and type(s['context_index']) is int and s['context_index']==i and all(type(s.get(k)) is bool for k in ('queued_or_prepared','active_recent_frame','resident_reported','image_modified_or_unprepared')) and type(s['reported_graphics_bytes']) is int and 0<=s['reported_graphics_bytes']<=2**48,'cached queue/bytes/recent/resident semantics')
        windows=row.get('mip1_windows');samples=terrain['samples'] if row['role']=='attribute' else [];p.need(isinstance(windows,list) and [r.get('sample_index') for r in windows]==list(range(len(samples))),'mip1 windows bound to existing candidates');level=m['levels'][1];eligible=(m['num_views'],info['z_size'],info['texture_type'],info['num_components'],info['component_width'],info['component_type'],info['format'])==(1,1,1,1,4,2,3)
        for item,sample in zip(windows,samples):
            w=item['window']
            if not level['resident']:p.need(w==dict(status='UNAVAILABLE_NOT_RESIDENT',resident_before=False),'absent mip cannot invent bytes');continue
            if not eligible:p.need(w==dict(status='UNAVAILABLE_LAYOUT'),'unsupported mip layout cannot invent bytes');continue
            p.need(w.get('resident_before') is True and w.get('expected_nbytes')==level['expected_nbytes'],'resident mip expected extent binding');derived=dict(info,x_size=level['size_xy'][0],y_size=level['size_xy'][1]);ok=previous._window(w,derived,owner['default_sampler'],sample['attribute_uv']);captured+=int(ok)
            if ok:
                count=sum(v['nbytes'] for v in w['texels']);p.need(count<=16,'16byte mip1 window cap');total+=count
    p.need(type(x.get('mip1_sample_bytes_captured')) is int and x['mip1_sample_bytes_captured']==total<=80,'recomputed 80byte mip1 budget');mip_complete=bool(terrain['samples']) and complete and result['terrain_complete'] and captured==len(terrain['samples']);result.update(prepared_recorded=True,prepared_complete=complete,prepared_contexts=len(contexts),prepared_textures=len(textures),prepared_rss_delta_kib=delta,mip1_window_count=captured,mip1_collection_complete=bool(mip_complete),mip1_sample_bytes_captured=total,renderer_diagnostic_passed=result['renderer_diagnostic_passed'] and complete);result['status']='SOURCE_QUALIFIED_PREPARED_TEXTURE' if result['renderer_diagnostic_passed'] else 'INCONCLUSIVE_PREPARED_TEXTURE_RECORDED';return result

def validate_receipt(folder,reference_path,nonce):return validate_prepared(folder,nonce,sparse.clone(previous.validate_receipt,ENTRY=ENTRY)(folder,reference_path,nonce))

def authenticate_source(bundle):
    request=json.loads((ROOT/REQUEST).read_text());source=request['source_sha'];head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    p.need(os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and head==os.environ.get('GITHUB_SHA'),'fresh request attempt1')
    p.need(request.get('schema')=='sdk3-prepared-texture-request-v1' and request.get('renderer_processes')==1 and request.get('official_model_processes')==request.get('onnx_inferences')==0,'one renderer/zero models scope')
    p.need(request.get('child_timeout_seconds')==600 and request.get('container_timeout_seconds')==630 and request.get('target_pixel')==[596,494],'measured geometry envelope and target')
    p.need(request.get('shader_limits')==LIMITS and request.get('terrain_limits')==TERRAIN_LIMITS,'fixed bounded shader and terrain observation')
    p.need(request.get('cache_policy_id')==cache.POLICY_ID and request.get('panda_shader_cxx_sha256')==cache.PANDA_SHADER_CXX_SHA256,'pinned expected-cache preprocessing policy')
    p.need(subprocess.check_output(['git','diff','--name-only',source,head],cwd=ROOT,text=True).splitlines()==[REQUEST],'request-only activation')
    delta=subprocess.check_output(['git','diff','--name-status',BASE,source],cwd=ROOT,text=True).splitlines();p.need(delta and all(x.startswith('A\t') for x in delta),'all old source/verdict bytes preserved')
    for event,key in [('push','push_ci'),('pull_request','pr_ci')]:
        run=p.api('actions/runs/'+str(request[key]));jobs=p.api('actions/runs/'+str(request[key])+'/jobs');artifacts=p.api('actions/runs/'+str(request[key])+'/artifacts')
        p.need(run['head_sha']==source and run['event']==event and run['workflow_id']==411705464 and run['run_attempt']==1 and run['conclusion']=='success' and jobs['total_count']==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(j['conclusion']=='success' for j in jobs['jobs']) and artifacts['total_count']==0,'four exact source CI jobs')
        p.write(bundle/('source-ci-'+event+'.json'),dict(run=run,jobs=jobs,artifacts=artifacts))
    p.need(request.get('sparse_policy')==sparse.SPARSE_POLICY,'bounded sparse read policy');p.need(request.get('prepared_policy')==h.POLICY and request.get('reference_index_sha256')==h.REFERENCE_SHA256,'bounded prepared cache policy');p.write(bundle/'request.json',request);return request

def run():
    out=ROOT/'output/stage7-sdk3-prepared-texture-01/producer';p.need(not out.exists(),'fresh output');work=out/'work';bundle=out/'bundle';work.mkdir(parents=True);bundle.mkdir();summary=dict(status='FAILED',known_renderer_processes=0,renderer_spawn_attempts=0,official_model_processes=0,onnx_inferences=0,repair_proven=False,stage7_complete=False);p.write(bundle/'summary.json',summary)
    try:
        request=authenticate_source(bundle);summary['source_sha']=request['source_sha'];p.write(bundle/'summary.json',summary)
        prior_run=p.api('actions/runs/43854755697');p.need(prior_run['workflow_id']==420027188 and prior_run['head_sha']=='bddd41d9f607a6ba20fc65da4291b76837db4b2f' and prior_run['run_attempt']==1 and prior_run['conclusion']=='success','prior RGB origin');p.write(bundle/'prior-run.json',prior_run)
        archive=p.artifact(work,bundle,14220249832,43506956,'6136240ea3894d5c90b16fa9c0e6c10e5829c59d7565daa00556084f1789aba1',43854755697,'bddd41d9f607a6ba20fc65da4291b76837db4b2f','prior-full-rgb');old=work/'prior-full-rgb';unpack_prior(archive,old)
        from scripts.run_sdk3_rgb_forensics import validate_observed_pair
        prior_analysis=validate_observed_pair(old,'full_rgb');p.need(prior_analysis['first_raw_source_diff_step']==7 and prior_analysis['strict_pair_pass'] is False,'preserve prior failure');p.write(bundle/'prior-validation.json',prior_analysis)
        reports=[json.loads((old/'pair'/f'run-{i}'/'run.json').read_text()) for i in (0,1)];reference_path=bundle/'reference.json';p.write(reference_path,g.reference_from_reports(*reports))
        for i,r in enumerate(reports):p.write(bundle/'prior-reference'/f'run-{i}.json',r)
        p.need(shutil.disk_usage(work).free>=8*1024**3,'8GiB staging disk')
        iz=p.artifact(work,bundle,14156262448,1738137175,'47711425a5a48fb2ef0cab140da6e394516f9cbb7f04b294c5f6583d7efbc687',43700449423,'7cf0f0157f8100f0aa0e05b01a815d7395c3383f','image');sz=p.artifact(work,bundle,14191115165,61661546,'2a44226962b3175081566918dd55eb845ac8ce1c9f9f5a396f469c8f6eca5d26',43786081196,'40dd7187ce8d3c5de510aa8c7a8ac2a6d37b0f38','sdk3')
        image=p.verify_member(iz,'image.tar',1727678464,'4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698',work/'image.tar');sdk=p.verify_member(sz,'candidate/libpandagl.so.data',1052968,p.SDK_SHA,work/'libpandagl.so')
        subprocess.run(['docker','load','-i',str(image)],check=True,timeout=600);p.need(json.loads(subprocess.check_output(['docker','image','inspect',p.IMAGE],text=True))[0]['Id']==p.IMAGE,'same immutable image')
        mem={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines()) if k in ('MemTotal','MemAvailable')};summary['host_memory']=mem;p.need(mem['MemAvailable']>=12*1024**3,'12GiB host availability')
        import secrets
        nonce=secrets.token_hex(16);summary['nonce']=nonce;p.write(bundle/'summary.json',summary)
        summary['execution']=run_renderer('sdk3-prepared-texture-'+os.environ['GITHUB_RUN_ID'],sdk,bundle/'renderer',['--repeat','0','--nonce',nonce],reference_path)
        path=bundle/'renderer/native-child.json'
        if path.exists():n=json.loads(path.read_text());summary.update(known_renderer_processes=int(type(n.get('pid')) is int and n['pid']>0),renderer_spawn_attempts=int(n.get('spawn_attempted') is True))
        p.write(bundle/'summary.json',summary);analysis=validate_receipt(bundle/'renderer',reference_path,nonce);p.write(bundle/'analysis.json',analysis);summary=observation_summary(summary,analysis);p.write(bundle/'summary.json',summary);print(json.dumps(summary));return summary
    except BaseException as error:summary['failure']=type(error).__name__+': '+str(error);p.write(bundle/'summary.json',summary);raise

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true',required=True);parser.parse_args();run()

if __name__=='__main__':main()
