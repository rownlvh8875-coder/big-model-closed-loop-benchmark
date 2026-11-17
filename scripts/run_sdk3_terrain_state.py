"""Authenticate terrain CPU state while preserving all inherited capture gates."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,sys
import numpy as np
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import run_sdk3_shader_cache as previous,panda_sdk3_runtime as p,sdk3_pixel_geometry as g,sdk3_pixel_geometry_budget_runtime as runtime,sdk3_shader_cache as cache,sdk3_terrain_state as terrain
from scripts.continue_panda_sdk3_models import unpack_prior
ROOT=Path(__file__).resolve().parents[1];BASE='1ddcdc8e3b8a1c0022a07bc9844aeae613ca2b4c';REQUEST='docs/requests/sdk3-terrain-state-20261117-01.json';ENTRY='/work/repo/scripts/sdk3_terrain_state_native.py'
LIMITS=previous.LIMITS;TERRAIN_LIMITS=terrain.LIMITS
_pins=json.loads((ROOT/'docs/evidence/sdk3-terrain-route-01/input-index.json').read_text())['files']
TERRAIN_SOURCE_PINS={name:_pins['docs/evidence/sdk3-terrain-route-01/frozen-source/'+name+'.data'] for name in ('shaders/terrain.vert.glsl','shaders/terrain.frag.glsl')}
observation_summary=previous.observation_summary
_clone=previous._clone


def native_command(*args,**kwargs):
    command=runtime.native_command(*args,**kwargs);command[command.index(runtime.ENTRY)]=ENTRY;return command

def run_renderer(name,sdk,out,args,reference):return _clone(runtime.run_renderer,native_command=native_command)(name,sdk,out,args,reference)

def _window(row,texture,sampler,uv):
    p.need(isinstance(row,dict),'CPU window object');status=row.get('status')
    if status=='UNAVAILABLE_NOT_RESIDENT':p.need(row==dict(status=status,resident_before=False),'absent RAM cannot invent texels');return False
    p.need(row.get('resident_before') is True and type(row.get('expected_nbytes')) is int and 0<=row['expected_nbytes']<2**63 and type(row.get('compression')) is int,'explicit existing CPU RAM extent')
    if status!='CAPTURED':
        p.need(status in ('UNAVAILABLE_EXTENT','UNAVAILABLE_FORMAT','UNAVAILABLE_WRAP','UNAVAILABLE_BUFFER') and set(row)=={'status','resident_before','expected_nbytes','compression'},'unavailable CPU windows contain no invented values');return False
    keys={'status','resident_before','expected_nbytes','compression','size_xy','num_components','component_width','component_type','byte_order','uv','wrap_codes','wrap_modes','texels','sample_sha256'};p.need(set(row)==keys,'captured CPU window fields')
    size=[texture['x_size'],texture['y_size']];components=texture['num_components'];width=texture['component_width'];stride=components*width
    p.need(row['size_xy']==size and type(components) is int and 1<=components<=4 and width in (1,2,4) and row['num_components']==components and row['component_width']==width and row['component_type']==texture['component_type'] and texture['z_size']==texture['texture_type']==1,'window bound to exact 2D texture layout')
    p.need(row['expected_nbytes']==size[0]*size[1]*stride<=terrain.MAX_RESIDENT_BYTES and row['compression']==1 and row['byte_order'] in ('little','big'),'bounded uncompressed resident RAM')
    p.need(np.allclose(previous.material._finite(row['uv'],(2,)),uv,atol=1e-9,rtol=1e-12),'candidate UV binding')
    codes=[sampler['wrap_u'],sampler['wrap_v']];policy={0:'clamp',1:'repeat',2:'mirror'};p.need(all(code in policy for code in codes) and row['wrap_codes']==codes and row['wrap_modes']==[policy[c] for c in codes],'pinned Panda1.10.13 default CPU wrap policy')
    expected=terrain.footprint(size,uv,*row['wrap_modes']);rows=row['texels'];p.need(isinstance(rows,list) and len(rows)==4,'four level0 CPU corners');raw=[]
    for value,xy in zip(rows,expected):
        p.need(isinstance(value,dict) and set(value)=={'xy','offset','nbytes','raw_hex'} and value['xy']==xy and type(value['offset']) is int and value['offset']==(xy[1]*size[0]+xy[0])*stride and value['nbytes']==stride and isinstance(value['raw_hex'],str) and re.fullmatch('[0-9a-f]{'+str(stride*2)+'}',value['raw_hex']) is not None,'exact bounded resident texel offset/extent/rawbytes');raw.append(bytes.fromhex(value['raw_hex']))
    p.need(hashlib.sha256(b''.join(raw)).hexdigest()==row['sample_sha256'],'CPU sample byte integrity');return True


def validate_terrain(folder,nonce,result):
    folder=Path(folder);path=folder/'terrain.json';p.need(path.stat().st_size<=1048576,'bounded terrain manifest');x=json.loads(path.read_text());result.update(terrain_recorded=False,terrain_complete=None,terrain_present=None,terrain_tag_shader_matched=None,cpu_candidate_windows_captured=0)
    p.need(x.get('protocol')=='sdk3-terrain-state-v1' and x.get('pid')==result['pid'] and x.get('nonce')==nonce,'same terrain observer identity')
    if not result.get('shader_recorded') or x.get('status')=='OWNED_BOOT':p.need(not result['native_completed'],'completed native requires terrain boundary');return result
    prior=json.loads((folder/'shader.json').read_text());geometry=json.loads((folder/'geometry-observer.json').read_text())['geometry'];p.need(x.get('target_read_sha256')==prior['target_read_sha256'] and x.get('geometry_archive_sha256')==prior['geometry_archive_sha256']==geometry['triangle_archive']['sha256'] and x.get('shader_sha256')==p.digest(folder/'shader.json'),'terrain target/geometry/final shader binding')
    p.need(x.get('observer_finalized') is True and x.get('borrowed_parent_is_origin') is True and x.get('limits')==TERRAIN_LIMITS and x.get('clock')=='journal_elapsed_monotonic_seconds','terrain bounded borrowed boundary/restoration')
    rows=[json.loads(line) for line in (folder/'progress.jsonl').read_text().splitlines()];end=next(row['elapsed_s'] for row in rows if row['event']=='checkpoint' and row['metadata'].get('stage')=='GEOMETRY_RETURN');start,stop,elapsed=[x.get(k) for k in ('terrain_enter_elapsed_s','terrain_exit_elapsed_s','elapsed_wall_seconds')]
    p.need(all(type(v) in (int,float) and np.isfinite(v) for v in (start,stop,elapsed)) and prior['shader_exit_elapsed_s']<=start<=stop<=end and abs(stop-start-elapsed)<=1e-6,'terrain interval follows shader inside original geometry boundary')
    complete=x.get('selection_complete');reasons=x.get('truncation_reasons');p.need(type(complete) is bool and isinstance(reasons,list) and all(isinstance(v,str) and len(v)<=128 for v in reasons) and complete==(not reasons) and x.get('status')==('TERRAIN_RECORDED' if complete else 'TERRAIN_PARTIAL') and (not complete or elapsed<=20),'explicit terrain complete/partial inspection')
    flags=('all_inputs_enumerated','cpu_candidates_are_terrain_intersections','states_are_actual_cull_state','gpu_program_execution_proven','hardware_uniform_values_proven','gpu_pixel_owner_proven','depth_tie_proven','unique_cause_proven','repair_proven','stage7_complete');p.need(all(x.get(k) is False for k in flags) and x.get('known_input_scope')=='KNOWN_TWENTY_FOUR_NAMES_ONLY','CPU candidate/state evidence never promotes GPU/owner/cause gates')
    files=set();total=0
    def text(desc):
        nonlocal total
        p.need(isinstance(desc,dict) and isinstance(desc.get('file'),str) and re.fullmatch('terrain-text-[0-9]{3}\\.txt',desc['file']) is not None and desc['file'] not in files and type(desc.get('nbytes')) is int and 0<desc['nbytes']<=262144,'unique bounded terrain byte descriptor');q=folder/desc['file'];p.need(q.stat().st_size==desc['nbytes'] and p.digest(q)==desc.get('sha256'),'exact terrain source/cache bytes');files.add(desc['file']);total+=desc['nbytes'];p.need(total<=2097152,'total terrain byte bound');return q.read_bytes().decode('utf-8')
    sources=x.get('sources');p.need(isinstance(sources,list) and [r.get('name') for r in sources]==list(TERRAIN_SOURCE_PINS)[:len(sources)] and (not complete or len(sources)==2),'exact frozen terrain source set');raw={}
    for row in sources:
        pin=TERRAIN_SOURCE_PINS[row['name']];raw[row['name']]=text(row);p.need(row['sha256']==pin['sha256'] and row['nbytes']==pin['nbytes'],'same immutable image terrain sources')
    shaders=x.get('shaders');p.need(isinstance(shaders,list) and len(shaders)<=4,'bounded terrain shader table');shader_map={}
    for i,row in enumerate(shaders):
        p.need(row.get('shader_id')==i and type(row.get('pointer')) is int and row['pointer']>0 and type(row.get('language')) is int and 0<=row['language']<=4 and type(row.get('error_flag')) is bool and isinstance(row.get('stages'),dict) and set(row['stages'])<= {'vertex','fragment'} and (not complete or set(row['stages'])=={'vertex','fragment'}),'cached terrain shader identity')
        shader_map[i]={}
        for stage,desc in row['stages'].items():p.need(isinstance(desc.get('filename'),str) and len(desc['filename'])<=4096,'bounded terrain shader filename');shader_map[i][stage]=None if desc.get('text') is None else text(desc['text'])
    p.need(len({r['pointer'] for r in shaders})==len(shaders),'deduplicated terrain shader identities')
    present=x.get('terrain_present');owner=x.get('owner');p.need(type(present) is bool and isinstance(owner,dict) and type(owner.get('available')) is bool,'explicit terrain owner/node availability')
    if owner['available']:
        p.need(all(type(owner.get(k)) is bool for k in ('render','use_mesh_terrain')) and type(owner.get('terrain_size')) is int and 0<owner['terrain_size']<=65536 and all(type(owner.get(k)) in (int,float) and np.isfinite(owner[k]) and owner[k]>0 for k in ('height_scale','elevation_ratio')),'bounded finite terrain owner configuration')
    else:p.need(owner=={'available':False} and not present,'absent owner has no invented configuration')
    states=x.get('states');textures=x.get('textures');samples=x.get('samples');p.need(isinstance(states,list) and len(states)<=4 and isinstance(textures,list) and len(textures)<=3 and isinstance(samples,list) and len(samples)<=5,'bounded terrain state/texture/candidate tables');matched=False;captured=0
    if not present:p.need(x.get('node') is None and x.get('camera') is None and not states and not textures and not samples,'absent terrain contains no invented live state')
    else:
        p.need(owner['available'],'present terrain owner');node=x.get('node');camera=x.get('camera');p.need(isinstance(node,dict) and isinstance(camera,dict) and all(isinstance(node.get(k),str) and len(node[k])<=4096 for k in ('path','name','node_type','direct_tag')) and all(isinstance(camera.get(k),str) and len(camera[k])<=4096 for k in ('tag_state_key','tag_value')) and type(camera.get('has_tag_state')) is bool,'bounded actual terrain path/tag context')
        p.need(all(type(node.get(k)) is int and node[k]>0 for k in ('pointer','heightfield_pointer')) and all(type(node.get(k)) is bool for k in ('is_geom_node','cpu_hidden')),'typed terrain node/heightfield identity');matrix=previous.material._finite(node['local_to_world'],(4,4));expected_samples=terrain.candidate_samples(geometry['hits'],matrix,owner['elevation_ratio'])
        p.need([r.get('ray') for r in samples]==[r['ray'] for r in expected_samples] and len(samples)==len(expected_samples),'exact existing nearest CPU candidate set')
        for sample,expected in zip(samples,expected_samples):
            p.need(set(sample)==set(expected) and sample['ray']==expected['ray'] and sample['triangle_index']==expected['triangle_index'],'CPU candidate identity')
            for key in ('world_point','local_point','heightfield_uv','attribute_uv','yellow_uv'):p.need(np.allclose(previous.material._finite(sample[key],(len(expected[key]),)),expected[key],atol=1e-9,rtol=1e-12),'recomputed candidate '+key)
        roles=['node_net','camera_initial','camera_tag','cpu_net_then_tag'];p.need([r.get('role') for r in states]==roles[:len(states)] and (not complete or len(states)==4),'exact CPU state observation roles')
        for row in states:
            p.need(type(row.get('pointer')) is int and row['pointer']>0 and type(row.get('shader_override')) is int and -2**31<=row['shader_override']<2**31 and isinstance(row.get('text'),str) and len(row['text'])<=16384,'actual CPU RenderState pointer/override/text');attrib=row.get('shader_attrib_pointer');sid=row.get('shader_id');p.need(attrib is None or type(attrib) is int and attrib>0,'explicit ShaderAttrib identity');p.need(sid is None or type(sid) is int and sid in shader_map and attrib is not None,'bound cached terrain shader ID');inputs=row.get('known_inputs');p.need(isinstance(inputs,list) and [r.get('name') for r in inputs]==list(terrain.INPUT_NAMES),'known24input names only')
            for value,name in zip(inputs,terrain.INPUT_NAMES):previous._input(value,name)
            if attrib is None:p.need(sid is None and all(r['status']=='MISSING' for r in inputs),'absent attrib has no invented shader inputs')
        p.need([r.get('role') for r in textures]==['attribute','heightfield','yellow'][:len(textures)] and (not complete or len(textures)==3),'exact terrain owner texture roles')
        for row in textures:
            previous._texture(row['texture']);previous.material._sampler(row['default_sampler']);windows=row.get('windows');p.need(isinstance(windows,list) and [r.get('sample_index') for r in windows]==list(range(len(samples))),'all candidate windows bound to sample indices');uv_key={'attribute':'attribute_uv','heightfield':'heightfield_uv','yellow':'yellow_uv'}[row['role']]
            for item,sample in zip(windows,samples):captured+=int(_window(item['window'],row['texture'],row['default_sampler'],sample[uv_key]))
        if complete:
            by_role={r['role']:r for r in textures};inputs={r['name']:r for r in states[3]['known_inputs']}
            p.need(by_role['heightfield']['texture']['pointer']==node['heightfield_pointer'],'node heightfield bound to owner texture')
            for role,name in [('attribute','attribute_tex'),('yellow','yellow_tex')]:p.need(inputs[name]['status']=='AVAILABLE_TEXTURE' and inputs[name]['texture']==by_role[role]['texture'],'exact composed input/owner texture binding')
            sid=states[2]['shader_id'];expected={stage:cache.preprocess_cache(raw[name]) for stage,name in zip(('vertex','fragment'),TERRAIN_SOURCE_PINS)};matched=sid is not None and shader_map[sid]==expected and shaders[sid]['language']==2 and not shaders[sid]['error_flag'] and camera['tag_state_key']=='rgb' and camera['tag_value']=='TERRAIN' and camera['has_tag_state']
    p.need(type(x.get('bytes_captured')) is int and x['bytes_captured']==total and {q.name for q in folder.glob('terrain-text-*.txt')}==files,'all terrain byte files accounted')
    qualified=complete and present and matched and not x['node']['cpu_hidden'];result.update(terrain_recorded=True,terrain_complete=complete,terrain_present=present,terrain_tag_shader_matched=bool(matched),cpu_candidate_windows_captured=captured,terrain=dict(states=len(states),shaders=len(shaders),sources=len(sources),textures=len(textures),candidate_points=len(samples),elapsed_wall_seconds=elapsed,captured_bytes=total),renderer_diagnostic_passed=result['renderer_diagnostic_passed'] and qualified);result['status']='SOURCE_QUALIFIED_TERRAIN_STATE' if result['renderer_diagnostic_passed'] else 'INCONCLUSIVE_TERRAIN_STATE_RECORDED';return result


def validate_receipt(folder,reference_path,nonce):
    result=_clone(previous.validate_receipt,ENTRY=ENTRY)(folder,reference_path,nonce);return validate_terrain(folder,nonce,result)


def authenticate_source(bundle):
    request=json.loads((ROOT/REQUEST).read_text());source=request['source_sha'];head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    p.need(os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and head==os.environ.get('GITHUB_SHA'),'fresh request attempt1')
    p.need(request.get('schema')=='sdk3-terrain-state-request-v1' and request.get('renderer_processes')==1 and request.get('official_model_processes')==request.get('onnx_inferences')==0,'one renderer/zero models scope')
    p.need(request.get('child_timeout_seconds')==600 and request.get('container_timeout_seconds')==630 and request.get('target_pixel')==[596,494],'measured geometry envelope and target')
    p.need(request.get('shader_limits')==LIMITS and request.get('terrain_limits')==TERRAIN_LIMITS,'fixed bounded shader and terrain observation')
    p.need(request.get('cache_policy_id')==cache.POLICY_ID and request.get('panda_shader_cxx_sha256')==cache.PANDA_SHADER_CXX_SHA256,'pinned expected-cache preprocessing policy')
    p.need(subprocess.check_output(['git','diff','--name-only',source,head],cwd=ROOT,text=True).splitlines()==[REQUEST],'request-only activation')
    delta=subprocess.check_output(['git','diff','--name-status',BASE,source],cwd=ROOT,text=True).splitlines();p.need(delta and all(x.startswith('A\t') for x in delta),'all old source/verdict bytes preserved')
    for event,key in [('push','push_ci'),('pull_request','pr_ci')]:
        run=p.api('actions/runs/'+str(request[key]));jobs=p.api('actions/runs/'+str(request[key])+'/jobs');artifacts=p.api('actions/runs/'+str(request[key])+'/artifacts')
        p.need(run['head_sha']==source and run['event']==event and run['workflow_id']==411705464 and run['run_attempt']==1 and run['conclusion']=='success' and jobs['total_count']==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(j['conclusion']=='success' for j in jobs['jobs']) and artifacts['total_count']==0,'four exact source CI jobs')
        p.write(bundle/('source-ci-'+event+'.json'),dict(run=run,jobs=jobs,artifacts=artifacts))
    p.write(bundle/'request.json',request);return request


def run():
    out=ROOT/'output/stage7-sdk3-terrain-state-01/producer';p.need(not out.exists(),'fresh output');work=out/'work';bundle=out/'bundle';work.mkdir(parents=True);bundle.mkdir();summary=dict(status='FAILED',known_renderer_processes=0,renderer_spawn_attempts=0,official_model_processes=0,onnx_inferences=0,repair_proven=False,stage7_complete=False);p.write(bundle/'summary.json',summary)
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
        summary['execution']=run_renderer('sdk3-terrain-'+os.environ['GITHUB_RUN_ID'],sdk,bundle/'renderer',['--repeat','0','--nonce',nonce],reference_path)
        path=bundle/'renderer/native-child.json'
        if path.exists():n=json.loads(path.read_text());summary.update(known_renderer_processes=int(type(n.get('pid')) is int and n['pid']>0),renderer_spawn_attempts=int(n.get('spawn_attempted') is True))
        p.write(bundle/'summary.json',summary);analysis=validate_receipt(bundle/'renderer',reference_path,nonce);p.write(bundle/'analysis.json',analysis);summary=observation_summary(summary,analysis);p.write(bundle/'summary.json',summary);print(json.dumps(summary));return summary
    except BaseException as error:summary['failure']=type(error).__name__+': '+str(error);p.write(bundle/'summary.json',summary);raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true',required=True);parser.parse_args();run()

if __name__=='__main__':main()
