"""Authenticated, bounded draw observation. GPU instrumentation changes timing."""
from pathlib import Path
import argparse,hashlib,json,math,os,secrets,shutil,subprocess,sys,struct
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk3_runtime as p,sdk3_draw_trace as t,sdk3_draw_trace_native as native,sdk3_pixel_geometry_budget_runtime as runtime,run_sdk3_pixel_geometry as geometry
from scripts.continue_panda_sdk3_models import PROFILE,unpack_prior
from scripts.compare_native_mdv3_rgb_pixels import read_verified_pixels
from scripts.sdk3_capture_progress import read_journal
ROOT=Path(__file__).resolve().parents[1];BASE='ae836ad09f410dd38f2503ac250863e889974c27';REQUEST='docs/requests/sdk3-draw-trace-20261117-03.json';ENTRY='/work/repo/scripts/sdk3_draw_trace_native.py'

def native_command(name,repo,sdk,out,args,*,reference,owner=None,library=None):
    command=runtime.native_command(name,repo,sdk,out,args,reference=reference,owner=owner);command[command.index(runtime.ENTRY)]=ENTRY
    if library is not None:
        i=command.index(p.IMAGE);command[i:i]=['--mount',f'type=bind,src={Path(library).resolve()},dst=/drawtrace.so,readonly','--env','LD_PRELOAD=/drawtrace.so']
    return command

def validate_command(command,spec):
    expected=native_command(spec['name'],Path(spec['repo']),Path(spec['sdk']),Path(spec['out']),spec['args'],reference=Path(spec['reference']),owner=spec['owner'],library=None if spec['library'] is None else Path(spec['library']))
    p.need(command==expected,'exact draw-trace isolation, mounts, environment and native entry')

def validate_source_delta(delta):p.need(delta and all(v.startswith('A\t') for v in delta),'only added files; historical producers and evidence preserved')

def validate_report(r,nonce,mode,sha):
    p.need(r.get('protocol')=='sdk3-draw-trace-native-v1' and r.get('nonce')==nonce and r.get('mode')==mode and type(r.get('pid')) is int and r['pid']>0,'draw identity/mode')
    p.need(r.get('sdk_sha256')==p.SDK_SHA and r.get('core_sha256')==p.CORE_SHA and r.get('panda_version')=='1.10.13' and r.get('driver',{}).get('renderer','').strip().lower()=='softpipe','pinned actual core/SDK/software renderer')
    p.need(all(type(r.get(k)) is int and r[k]==0 for k in ('official_model_processes','onnx_inferences')) and all(r.get(k) is False for k in ('model_weights_used','repair_proven','stage7_complete')),'zero-model diagnostic scope only')
    p.need(all(r.get(k)==dict.fromkeys(p.STATS_FIELDS,0) for k in ('source_stats_before','source_stats_after')),'original SDK observer stays default OFF')
    p.need(r.get('intentional_target_depth_mutation') is (mode=='depth-probe'),'explicit original-world depth mutation classification')
    p.need(r.get('observer_is_intervention') is (mode!='off') and r.get('trace_library_sha256')==sha,'explicit diagnostic intervention/library')
    s=r.get('trace_stats',{});p.need(set(s)=={'version','error','active','restored','lookups','forwards','draws','queries','readbacks','blits'} and all(type(v) is int and v>=0 for v in s.values()),'typed actual trace counters')
    p.need(s['version']==1 and s['active']==0 and s['restored']==1 and s['draws']<=512 and s['queries']<=100000 and s['readbacks']<=2048 and s['blits']<=1024,'trace resource and restoration bounds')
    if mode=='off':p.need(all(s[k]==0 for k in ('error','lookups','forwards','draws','queries','readbacks','blits')),'unloaded OFF has no trace activity')
    return dict(s,complete=s['error']==0 and (mode=='off' or s['draws']>0))

def read_trace(folder,pid):
    path=Path(folder)/'draw-trace.jsonl';p.need(0<path.stat().st_size<=t.LIMITS['max_trace_bytes'],'bounded nonempty raw trace');raw=path.read_bytes();p.need(raw.endswith(b'\n'),'complete trace lines');rows=[json.loads(v) for v in raw.splitlines()]
    p.need(rows[0]==dict(event='configured',pid=pid,max_draws=512) and len(rows)<=521,'trace configuration/identity/row budget');draws=[];programs={}
    for row in rows[1:]:
        if row.get('event')=='program':
            ident=row['program'];p.need(ident not in programs and len(programs)<8,'unique bounded program source table');programs[ident]=row
            for source in row.get('sources',[]):
                name=source['file'];p.need(Path(name).name==name and name.startswith('gpu-shader-') and name.endswith('.txt'),'owned shader basename');q=Path(folder)/name;p.need(q.stat().st_size==source['nbytes']<=262144,'bounded retained actual shader bytes')
        else:
            p.need(row.get('event')=='draw' and row.get('pid')==pid and row.get('sequence')==len(draws)+1 and row.get('phase') in (0,1,2),'ordered original draw identities');draws.append(row)
    p.need(0<len(draws)<=512,'draw observation required');p.need(sum((Path(folder)/s['file']).stat().st_size for v in programs.values() for s in v.get('sources',[]))<=4194304,'total shader bound')
    return draws,programs

def validate_trace_details(draws,mode,pixel):
    rows=expected=clears=total=matrix_bytes=0;complete=True;exposed=False
    for draw in draws:
        uniforms=draw.get('uniforms') or {};sampler=uniforms.get('terrain_data_texture');expected+=int(sampler is not None);row=draw.get('terrain_data_row')
        if row is not None:
            rows+=1;p.need(rows<=2 and isinstance(row,dict),'two bounded terrain rows')
            if row.get('status')!='ROW_RECORDED':p.need(row.get('status') in ('UNAVAILABLE_LIMIT','UNAVAILABLE_UNIT','UNAVAILABLE_LAYOUT','ROW_PARTIAL'),'explicit partial terrain row');complete=False
            else:
                width=row.get('width');values=row.get('values');bits=row.get('float_bits');p.need(isinstance(sampler,dict) and sampler.get('restored') is True and type(width) is int and width==draw.get('instances') and 1<=width<=64 and row.get('nbytes')==width*16 and row['nbytes']<=1024,'row bound to original instance width and byte cap');p.need(row.get('texture')==sampler.get('texture') and row.get('unit')==sampler.get('unit') and row.get('texture_size')==[sampler.get('width'),sampler.get('height')] and row.get('internal_format')==sampler.get('internal_format')==34836 and row.get('view_index')==uniforms.get('terrain_view_index') and type(row['view_index']) is int and 0<=row['view_index']<sampler['height'] and width<=sampler['width'],'actual sampler/texture/view binding');p.need(row.get('restored') is True and row.get('gl_error_before')==row.get('gl_error_after')==0,'row query state and errors');p.need(isinstance(values,list) and isinstance(bits,list) and len(values)==len(bits)==4*width and all(type(v) in (int,float) and math.isfinite(v) for v in values) and all(type(v) is int and 0<=v<2**32 for v in bits),'finite typed row floats/bits');p.need(list(struct.unpack('<'+str(len(values))+'I',struct.pack('<'+str(len(values))+'f',*values)))==bits,'retained row float bit identity');total+=row['nbytes'];p.need(total<=2048,'total GPUrow byte cap')
        table=draw.get('transform_table')
        if table is not None:
            p.need(isinstance(table,dict) and table.get('status') in ('MATRICES_RECORDED','MATRICES_PARTIAL'),'explicit matrix array outcome');count=table.get('count');bits=table.get('float_bits');p.need(table.get('uniform')=='p3d_TransformTable' and type(count) is int and 1<=count<=100 and type(table.get('nbytes')) is int and table['nbytes']==count*64<=6400 and isinstance(bits,list) and len(bits)==count*16 and all(type(v) is int and 0<=v<2**32 for v in bits),'bounded indexed matrix bits/extent')
            if table['status']=='MATRICES_RECORDED':p.need(table.get('gl_error_before')==table.get('gl_error_after')==0 and all(math.isfinite(v) for v in struct.unpack('<'+str(len(bits))+'f',struct.pack('<'+str(len(bits))+'I',*bits))),'finite exact uniform matrices')
            matrix_bytes+=table['nbytes']
        probe=draw.get('depth_probe')
        if probe is not None:
            p.need(mode in ('depth-probe','canary') and draw.get('phase')==1 and draw.get('pixel_gl')==list(pixel),'explicit scoped target-only depth mutation');clears+=1;p.need(clears<=1 and set(probe)=={'cleared_pixels','state_restored','original_depth_bits32'} and type(probe.get('cleared_pixels')) is int and probe['cleared_pixels']==1 and probe.get('state_restored') is True,'exact one restored depth clear');before,after=draw['before'],draw['after'];p.need(before.get('valid') is True and after.get('valid') is True and probe['original_depth_bits32']==before.get('depth_bits32') and len(probe['original_depth_bits32'])==1,'original pre-clear depth binding');p.need(all(before.get(k)==after.get(k)==v for k,v in [('depth_func',513),('depth_test',1),('depth_write',1)]) and before.get('scissor')==after.get('scissor') and before.get('scissor_test')==after.get('scissor_test'),'original LESS/depth/scissor state preserved');exposed=after['depth_bits32'][0]>=before['depth_bits32'][0] and after['color_bits']!=before['color_bits']
    if mode=='depth-probe':p.need(clears==1,'depth probe performed exactly once')
    return dict(transform_matrix_bytes=matrix_bytes,terrain_row_count=rows,terrain_row_bytes=total,terrain_rows_complete=complete and rows==expected and rows>0,depth_clear_pixels=clears,occluded_terrain_exposed=exposed)

def validate_canary(folder,r,stats):
    p.need(r.get('status')=='TINY_GPU_CANARY_RECORDED' and r.get('canary_render_calls')==(11 if r.get('depth_probe_canary') else 8) and stats['complete'],'actual tiny GPU completed');draws,programs=read_trace(folder,r['pid']);p.need(len(draws)==stats['draws'],'actual draw counter binding');cases=r.get('canary_cases');p.need(isinstance(cases,list) and [c.get('requested_samples') for c in cases]==[0,4],'single/MSAA challenged cases')
    import numpy as np
    for phase,case in enumerate(cases):
        receipt=case['callback_receipt'];p.need(receipt['trace_complete'] is True and receipt['target_region_returns']==4 and receipt['callbacks_restored'] is True and not receipt['errors'],'canary original callbacks/restoration')
        first=[1.,float(int(r['nonce'][0],16)&1),0.];p.need(len(case['challenges'])==2 and [v['color'] for v in case['challenges']]==[first,[1.-v for v in first]],'nonce-bound distinct GPU challenges')
        for challenge in case['challenges']:
            name=challenge['raw_file'];p.need(Path(name).name==name,'canary raw basename');raw=(Path(folder)/name).read_bytes();w=challenge['component_width'];typ=challenge['component_type'];dtype=np.dtype('float32') if typ==2 and w==4 else np.dtype('float16') if typ==7 and w==2 else np.dtype('uint8') if typ==0 and w==1 else None
            p.need(dtype is not None and len(raw)==challenge['nbytes']==256*w<=8192 and hashlib.sha256(raw).hexdigest()==challenge['sha256'],'actual tiny raw bytes and layout');pixels=np.frombuffer(raw,dtype=dtype).reshape((64,4));expected=np.asarray([*challenge['color'],1.])*(255 if w==1 else 1);p.need(np.array_equal(pixels,np.broadcast_to(expected,pixels.shape)),'independently decoded all64 challenge pixels')
            start,stop=challenge['draw_range'];selected=draws[start-1:stop];p.need(start>=1 and stop>=start and len(selected)==stop-start+1,'bounded complete challenge draw range')
            p.need(any(d['kind'] in ((1,2,3) if phase==0 else (4,5)) for d in selected),'actual noninstanced and instanced interception')
            for d in selected:
                p.need(d['phase']==phase and d['restored'] is True and d['pixel_gl']==[3,3] and all(d[k]['valid'] is True and d[k]['restored'] is True and d[k]['gl_error_before']==d[k]['gl_error_after']==0 for k in ('before','after')),'actual challenged readback/state restoration')
                p.need((d['after']['samples']==0 and d['after']['sample_buffers']==0 if phase==0 else 1<=d['after']['samples']<=16 and d['after']['sample_buffers']==1) and d['after']['depth_bits']>=16,'observed single/MSAA depth attachment');p.need(np.array_equal(np.asarray(d['after']['color']),np.asarray([*challenge['color'],1.])),'draw boundary reaches challenged color')
    details=validate_trace_details(draws,'canary',[3,3]);qualified=False;probe=r.get('depth_probe_canary')
    if probe is not None:
        first=[1.,float(int(r['nonce'][0],16)&1),0.];back=[1.-v for v in first];p.need(probe.get('front')==first and probe.get('back')==back and probe.get('expected_terrain_data_row')==[*back,1.],'fresh depth canary colors/row');name=probe['raw_file'];before_name=probe['raw_before'];p.need(Path(name).name==name and Path(before_name).name==before_name,'owned depth raw names');raw=(Path(folder)/name).read_bytes();before_raw=(Path(folder)/before_name).read_bytes();w=probe['component_width'];typ=probe['component_type'];p.need(hashlib.sha256(before_raw).hexdigest()==probe['raw_before_sha256'],'original foreground raw SHA');dtype=np.dtype('float32') if typ==2 and w==4 else np.dtype('float16') if typ==7 and w==2 else None;p.need(dtype is not None and len(before_raw)==256*w and np.array_equal(np.frombuffer(before_raw,dtype=dtype).reshape(64,4),np.broadcast_to(np.asarray([*first,1.]),(64,4))),'all64original foreground pixels');verified=t.verify_depth_canary_pixels(raw,w,typ,first,back);p.need(all(probe.get(k)==v for k,v in verified.items()),'independently verified one-pixel canary metadata');start,stop=probe['draw_range'];selected=draws[start-1:stop];p.need(start>=1 and stop>=start and len(selected)==stop-start+1 and probe['callback_receipt']['trace_complete'] is True and probe['callback_receipt']['target_region_returns']==1 and probe['callback_receipt']['callbacks_restored'] is True,'owned one-frame depth canary');selected_details=validate_trace_details(selected,'depth-probe',[3,3]);p.need(selected_details['occluded_terrain_exposed'] and selected_details['terrain_rows_complete'] and selected_details['terrain_row_count']==1 and [d['terrain_data_row']['values'] for d in selected if d.get('terrain_data_row')]==[[*back,1.]],'actual farther-fragment depth and GPUrow qualification');qualified=True
    p.need(stats['blits']>0 and stats['readbacks']==4*stats['draws']+details['terrain_row_count'],'actual multisample/row read path');return dict(one_pixel_depth_probe_qualified=qualified,terrain_row_read_qualified=qualified,status='QUALIFIED_TINY_GPU_CANARY',draws=len(draws),queries=stats['queries'],max_effective_samples_observed=max(d['after']['samples'] for d in draws),multiple_effective_samples_qualified=any(d['after']['samples']>1 for d in draws),scope='single-sample and observed multisample-storage resolve only',stage7_complete=False)

def validate_receipt(folder,reference,nonce,mode,sha,spec):
    folder=Path(folder);read=lambda n:json.loads((folder/n).read_text());r=read('report.json');n=read('native-child.json');c=read('container.json');e=read('execution.json');w=read('watchdog.json');cmd=read('command.json');validate_command(cmd['argv'],dict(spec,owner=cmd['ownership_label']))
    cid=c['id'];p.need(type(cid) is str and len(cid)==64 and e.get('container_id')==cid and c.get('image')==p.IMAGE and c.get('effective_limits')==PROFILE and c.get('ownership_label')==cmd['ownership_label'],'frozen isolated owned container');p.need(e.get('failure') is None and e.get('returncode')==0 and e.get('owned_container_removed') is True and e.get('ownership_unresolved') is False,'complete owned container cleanup')
    state=e['stopped_state'];p.need(state.get('Running') is False and state.get('Pid')==0 and state.get('OOMKilled') is False and state.get('ExitCode')==0,'stopped non-OOM child');p.need(n.get('spawn_attempted') is True and n.get('pid')==w.get('pid')==r.get('pid') and n.get('returncode')==w.get('child_returncode')==0 and n.get('server_returncode')==w.get('server_returncode')==0 and r.get('child_finalized_before_server_stop') is True,'owned native/display lifetime')
    p.need(w.get('timed_out') is False and w.get('timeout_seconds')==(90 if mode=='canary' else 600) and r.get('provider_closed') is True,'complete bounded native outcome');stats=validate_report(r,nonce,mode,sha)
    if mode=='canary':return validate_canary(folder,r,stats)
    p.need(r.get('status')=='DRAW_TRACE_REPLAY_RECORDED' and r.get('base_camera_sha256')==native.BASE_CAMERA_SHA and r.get('reference_sha256')==p.digest(reference) and r.get('observers_restored') is True and r.get('ort_module_loaded') is False and r.get('extra_render_tasks')==0 and r.get('extra_gpu_queries')==stats['queries'] and r.get('terminal_sync_calls')==(1 if mode!='off' else 0),'declared original replay/observation operations')
    p.need(r.get('task_frame_count_delta')==14 and r.get('tasks_before')==r.get('tasks_after') and len(r.get('captures',[]))==7,'original14ticks/sevenpairs');rows=read_journal(folder/'progress.jsonl');p.need(all(row['identity']==dict(pid=r['pid'],nonce=nonce,protocol='sdk3-draw-trace-native-v1') for row in rows) and [row['step'] for row in rows if row['event']=='capture.return']==list(range(1,8)),'original complete progress boundaries')
    ref=json.loads(Path(reference).read_text());matches=[];target=None
    for i,cap in enumerate(r['captures'],1):
        p.need(cap['step']==i and (i==1 or cap['pose']==ref['previous_states'][i-2]),'frozen original camera poses');p.need([v['camera'] for v in cap['images']]==['road','wide'],'original ordered camera pair')
        for image in cap['images']:
            p.need(image['file']==f"step{i}-{image['camera']}.rgb.zlib" and image['shape']==[604,964,3] and image['sha256']==cap[image['camera']+'_sha256'],'source image binding');pixels=read_verified_pixels(folder,image)
            if i==7 and image['camera']=='road':target=pixels[494,596].tolist()
        matches.append(all(cap[c+'_sha256']==ref['prefix_sha256'][i-1][c] for c in ('road','wide')) if i<=6 else cap['road_sha256'] in ref['target_road_sha256'] and cap['wide_sha256']==ref['target_wide_sha256'])
    result=dict(status='REPLAY_RECORDED',source_image_equivalence=all(matches),capture_matches_reference=matches,target_road_rgb=target,verified_images=14,trace_complete=stats['complete'],trace_stats=stats,gpu_pixel_owner_proven=False,unique_cause_proven=False,repair_proven=False,stage7_complete=False)
    if mode in ('trace','depth-probe'):
        draws,programs=read_trace(folder,r['pid']);p.need(len(draws)==stats['draws'] and all(d['pixel_gl']==[596,109] and d['phase'] in (1,2) for d in draws),'actual target-pixel draw counter/scope');receipt=r['callback_receipt'];result.update(callback_receipt=receipt,trace_complete=stats['complete'] and receipt['trace_complete'],draw_count=len(draws),program_count=len(programs));post=[d for d in draws if d['phase']==2];result['final_post_float_rgba']=post[-1]['after']['color'] if post else None;result.update(validate_trace_details(draws,mode,[596,109]));result['intentional_depth_pixel_mutation']=mode=='depth-probe'
    return result

def authenticate_source(bundle):
    request=json.loads((ROOT/REQUEST).read_text());source=request['source_sha'];head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();p.need(os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and head==os.environ.get('GITHUB_SHA'),'fresh request attempt1');p.need(request.get('schema')=='sdk3-depth-mechanism-request-v1' and request.get('arms')==['canary','trace','depth-probe'] and request.get('renderer_processes')==3 and request.get('official_model_processes')==request.get('onnx_inferences')==0 and request.get('limits')==t.LIMITS and request.get('target_pixel')==[596,494],'exact canary/control/depth-probe scope and limits')
    p.need(subprocess.check_output(['git','diff','--name-only',source,head],cwd=ROOT,text=True).splitlines()==[REQUEST],'request-only activation');validate_source_delta(subprocess.check_output(['git','diff','--name-status',BASE,source],cwd=ROOT,text=True).splitlines())
    for event,key in [('push','push_ci'),('pull_request','pr_ci')]:
        run=p.api('actions/runs/'+str(request[key]));jobs=p.api('actions/runs/'+str(request[key])+'/jobs');artifacts=p.api('actions/runs/'+str(request[key])+'/artifacts');p.need(run['head_sha']==source and run['event']==event and run['workflow_id']==411705464 and run['run_attempt']==1 and run['conclusion']=='success' and jobs['total_count']==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(j['conclusion']=='success' for j in jobs['jobs']) and artifacts['total_count']==0,'four exact source CI jobs');p.write(bundle/('source-ci-'+event+'.json'),dict(run=run,jobs=jobs,artifacts=artifacts))
    p.write(bundle/'request.json',request);return request

def stage(work,bundle,summary):
    prior_run=p.api('actions/runs/43854755697');p.need(prior_run['workflow_id']==420027188 and prior_run['head_sha']=='bddd41d9f607a6ba20fc65da4291b76837db4b2f' and prior_run['run_attempt']==1 and prior_run['conclusion']=='success','prior RGB origin');p.write(bundle/'prior-run.json',prior_run)
    archive=p.artifact(work,bundle,14220249832,43506956,'6136240ea3894d5c90b16fa9c0e6c10e5829c59d7565daa00556084f1789aba1',43854755697,'bddd41d9f607a6ba20fc65da4291b76837db4b2f','prior-full-rgb');old=work/'prior-full-rgb';unpack_prior(archive,old)
    from scripts.run_sdk3_rgb_forensics import validate_observed_pair
    prior_analysis=validate_observed_pair(old,'full_rgb');p.need(prior_analysis['first_raw_source_diff_step']==7 and prior_analysis['strict_pair_pass'] is False,'preserve prior failure');p.write(bundle/'prior-validation.json',prior_analysis)
    reports=[json.loads((old/'pair'/f'run-{i}'/'run.json').read_text()) for i in (0,1)];reference_path=bundle/'reference.json';p.write(reference_path,__import__('scripts.sdk3_pixel_geometry',fromlist=['reference_from_reports']).reference_from_reports(*reports))
    for i,r in enumerate(reports):p.write(bundle/'prior-reference'/f'run-{i}.json',r)
    p.need(shutil.disk_usage(work).free>=8*1024**3,'8GiB staging disk')
    iz=p.artifact(work,bundle,14156262448,1738137175,'47711425a5a48fb2ef0cab140da6e394516f9cbb7f04b294c5f6583d7efbc687',43700449423,'7cf0f0157f8100f0aa0e05b01a815d7395c3383f','image');sz=p.artifact(work,bundle,14191115165,61661546,'2a44226962b3175081566918dd55eb845ac8ce1c9f9f5a396f469c8f6eca5d26',43786081196,'40dd7187ce8d3c5de510aa8c7a8ac2a6d37b0f38','sdk3')
    image=p.verify_member(iz,'image.tar',1727678464,'4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698',work/'image.tar');sdk=p.verify_member(sz,'candidate/libpandagl.so.data',1052968,p.SDK_SHA,work/'libpandagl.so')
    subprocess.run(['docker','load','-i',str(image)],check=True,timeout=600);p.need(json.loads(subprocess.check_output(['docker','image','inspect',p.IMAGE],text=True))[0]['Id']==p.IMAGE,'same immutable image')
    mem={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines()) if k in ('MemTotal','MemAvailable')};summary['host_memory']=mem;p.need(mem['MemAvailable']>=12*1024**3,'12GiB host availability')
    return sdk,reference_path

def run_arm(name,sdk,out,args,reference,library):
    def command(*a,**kw):return native_command(*a,**kw,library=library)
    return native.clone(runtime.run_renderer,native_command=command)(name,sdk,out,args,reference)

def run():
    out=ROOT/'output/stage7-sdk3-draw-trace-03/producer';p.need(not out.exists(),'fresh output');work=out/'work';bundle=out/'bundle';work.mkdir(parents=True);bundle.mkdir();summary=dict(status='FAILED',official_model_processes=0,onnx_inferences=0,repair_proven=False,stage7_complete=False,arms={});p.write(bundle/'summary.json',summary)
    try:
        request=authenticate_source(bundle);summary['source_sha']=request['source_sha'];sdk,reference=stage(work,bundle,summary);library=work/'drawtrace.so';command=['gcc','-std=c11','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror',str(ROOT/'native/sdk3_draw_trace/trace.c'),'-ldl','-o',str(library)];subprocess.run(command,check=True,timeout=60);library.chmod(0o644);sha=p.digest(library);shutil.copyfile(library,bundle/'drawtrace.so.data');p.write(bundle/'build.json',dict(command=command,compiler=subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],sha256=sha))
        for mode in ('canary','trace','depth-probe'):
            nonce=secrets.token_hex(16);name='sdk3-draw-'+mode+'-'+os.environ['GITHUB_RUN_ID'];dest=bundle/mode;args=['--mode',mode,'--nonce',nonce];loaded=library if mode!='off' else None
            if loaded:args+=['--trace-library','/drawtrace.so','--trace-sha256',sha]
            summary['arms'][mode]=dict(nonce=nonce,spawn_attempted=True);p.write(bundle/'summary.json',summary);execution=run_arm(name,sdk,dest,args,reference,loaded);summary['arms'][mode]['execution']=execution;p.write(bundle/'summary.json',summary)
            spec=dict(name=name,repo=str(ROOT),sdk=str(sdk),out=str(dest),args=args,reference=str(reference),library=None if loaded is None else str(loaded));analysis=validate_receipt(dest,reference,nonce,mode,sha if loaded else None,spec);p.write(bundle/(mode+'-analysis.json'),analysis);summary['arms'][mode]['analysis']=analysis;p.write(bundle/'summary.json',summary)
            if mode=='canary':p.need(analysis['status']=='QUALIFIED_TINY_GPU_CANARY' and analysis['one_pixel_depth_probe_qualified'] and analysis['terrain_row_read_qualified'],'tiny GPU gates all original scene execution')
        p.need(sum(f.stat().st_size for f in bundle.rglob('*') if f.is_file() and 'prior-reference' not in f.parts)<=128*1024**2,'128MiB retained carrier');summary['status']='DRAW_OBSERVATION_RECORDED';p.write(bundle/'summary.json',summary);print(json.dumps(summary));return summary
    except BaseException as exc:summary['failure']=type(exc).__name__+': '+str(exc);p.write(bundle/'summary.json',summary);raise

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true',required=True);parser.parse_args();run()
if __name__=='__main__':main()
