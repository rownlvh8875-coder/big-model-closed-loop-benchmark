"""Authenticate cached shader source and bindings; preserve original failure gates."""
from pathlib import Path
from types import FunctionType
import argparse,hashlib,json,os,re,shutil,subprocess,sys
import numpy as np
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import run_sdk3_pixel_material as material,run_sdk3_pixel_geometry_budget as budget,panda_sdk3_runtime as p,sdk3_pixel_geometry as g,sdk3_pixel_geometry_budget_runtime as runtime,sdk3_shader_path as s
from scripts.continue_panda_sdk3_models import unpack_prior
ROOT=Path(__file__).resolve().parents[1];BASE='dacce23588e45dfd986f69f1ec00f23e0be051ed';REQUEST='docs/requests/sdk3-shader-path-20261117-01.json';ENTRY='/work/repo/scripts/sdk3_shader_path_native.py'
LIMITS=dict(max_shader_objects=8,max_file_bytes=262144,max_total_bytes=2097152,max_meshes=40,max_cpu_seconds=20)
SOURCE_PINS=json.loads((ROOT/'docs/evidence/sdk3-shader-path-01/frozen-source-index.json').read_text())['files']
observation_summary=budget.observation_summary
_clone=material._clone

def native_command(*args,**kwargs):
    cmd=runtime.native_command(*args,**kwargs);cmd[cmd.index(runtime.ENTRY)]=ENTRY;return cmd

def run_renderer(name,sdk,out,args,reference):return _clone(runtime.run_renderer,native_command=native_command)(name,sdk,out,args,reference)

def _texture(value):
    p.need(isinstance(value,dict) and type(value.get('pointer')) is int and value['pointer']>0 and isinstance(value.get('name'),str) and len(value['name'])<=4096,'cached texture identity')
    p.need(all(type(value.get(k)) is int and 0<=value[k]<2**31 for k in ('x_size','y_size','z_size','num_components','component_width','component_type','format','texture_type')),'cached texture dimensions/type')

def _input(row,name):
    p.need(isinstance(row,dict) and row.get('name')==name,'source-known input identity');status=row.get('status')
    if status=='MISSING':p.need(set(row)=={'name','status'},'missing input has no invented values');return
    base={'name','status','value_type','priority'};p.need(type(row.get('value_type')) is int and 1<=row['value_type']<=8 and type(row.get('priority')) is int,'input type/priority')
    if status=='AVAILABLE_TEXTURE':p.need(set(row)==base|{'texture'} and row['value_type'] in (1,5),'typed texture input');_texture(row['texture'])
    elif status=='AVAILABLE_VECTOR':p.need(set(row)==base|{'vector'} and row['value_type']==3,'typed vector input');material._finite(row['vector'],(4,))
    elif status=='UNAVAILABLE_NUMERIC_ARRAY':p.need(set(row)==base and row['value_type']==4,'numeric arrays stay unavailable')
    else:p.need(status=='UNAVAILABLE_TYPE' and set(row)==base and row['value_type'] not in (1,3,4,5),'unsupported input remains explicit')

def validate_shader(folder,nonce,result):
    path=folder/'shader.json';p.need(path.stat().st_size<=2097152,'bounded shader manifest');x=json.loads(path.read_text());result.update(shader_recorded=False,shader_complete=None,shader_variants_matched=None,shader=None,gpu_program_execution_proven=False,hardware_uniform_values_proven=False)
    p.need(x.get('protocol')=='sdk3-shader-path-v1' and x.get('pid')==result['pid'] and x.get('nonce')==nonce,'actual shader observer identity')
    if not result.get('material_recorded'):p.need(not result['native_completed'],'completed native requires material/shader boundary');return result
    m=json.loads((folder/'material.json').read_text());p.need(x.get('target_read_sha256')==m['target_read_sha256'] and x.get('geometry_archive_sha256')==m['geometry_archive_sha256'] and x.get('material_sha256')==p.digest(folder/'material.json'),'shader target/geometry/final material binding')
    p.need(x.get('borrowed_parent_is_origin') is True and x.get('observer_finalized') is True and x.get('clock')=='journal_elapsed_monotonic_seconds' and x.get('limits')==LIMITS,'shader borrowed boundary/restoration/budgets')
    rows=[json.loads(line) for line in (folder/'progress.jsonl').read_text().splitlines()];end=next(r['elapsed_s'] for r in rows if r['event']=='checkpoint' and r['metadata'].get('stage')=='GEOMETRY_RETURN')
    start,stop=x.get('shader_enter_elapsed_s'),x.get('shader_exit_elapsed_s');p.need(all(type(v) in (int,float) and np.isfinite(v) for v in (start,stop,x.get('elapsed_wall_seconds'))) and m['material_exit_elapsed_s']<=start<=stop<=end and abs(stop-start-x['elapsed_wall_seconds'])<=1e-6,'shader interval follows material inside geometry boundary')
    complete=x.get('selection_complete');reasons=x.get('truncation_reasons');p.need(type(complete) is bool and isinstance(reasons,list) and all(isinstance(v,str) and len(v)<=128 for v in reasons) and complete==(not reasons) and x.get('status')==('SHADER_RECORDED' if complete else 'SHADER_PARTIAL') and (not complete or x['elapsed_wall_seconds']<=20),'explicit complete/partial shader capture')
    p.need(x.get('known_input_scope')=='KNOWN_EIGHT_PSSM_NAMES_ONLY' and all(x.get(k) is False for k in ('all_inputs_enumerated','gpu_program_execution_proven','hardware_uniform_values_proven','gpu_pixel_owner_proven','unique_cause_proven','repair_proven','stage7_complete')),'CPU shader evidence never promotes GPU/cause gates')
    files=set();total=0
    def text(desc):
        nonlocal total
        p.need(isinstance(desc,dict) and isinstance(desc.get('file'),str) and re.fullmatch(r'shader-text-\d{3}-[a-z0-9-]+\.txt',desc['file']) is not None and desc['file'] not in files and type(desc.get('nbytes')) is int and 0<desc['nbytes']<=262144,'unique bounded source/shader descriptor');q=folder/desc['file'];p.need(q.stat().st_size==desc['nbytes'] and p.digest(q)==desc.get('sha256'),'actual shader source bytes');files.add(desc['file']);total+=desc['nbytes'];p.need(total<=2097152,'global shader byte budget');return q.read_bytes().decode('utf-8')
    sources=x.get('sources');p.need(isinstance(sources,list) and [v.get('name') for v in sources]==list(SOURCE_PINS)[:len(sources)] and (not complete or len(sources)==len(SOURCE_PINS)),'exact pinned frozen source set');raw={}
    for row in sources:
        pin=SOURCE_PINS[row['name']];raw[row['name']]=text(row);p.need(row['sha256']==pin['sha256'] and row['nbytes']==pin['nbytes'],'frozen file SHA/size match immutable image')
    shaders=x.get('shaders');meshes=x.get('meshes');p.need(isinstance(shaders,list) and len(shaders)<=8 and isinstance(meshes,list) and len(meshes)<=40,'bounded shader/mesh tables');shader_map={}
    for i,shader in enumerate(shaders):
        p.need(shader.get('shader_id')==i and type(shader.get('pointer')) is int and shader['pointer']>0 and type(shader.get('language')) is int and 0<=shader['language']<=4 and type(shader.get('error_flag')) is bool and set(shader.get('stages',{}))=={'vertex','fragment'},'actual cached shader identity and stages');texts={}
        for stage,row in shader['stages'].items():
            p.need(isinstance(row.get('filename'),str) and len(row['filename'])<=4096,'bounded shader filename');texts[stage]=text(row['text']) if row.get('text') is not None else None
        shader_map[i]=dict(texts=texts,language=shader['language'],error_flag=shader['error_flag'])
    p.need(len({row['pointer'] for row in shaders})==len(shaders),'deduplicated actual shader objects')
    config=x.get('pipeline');defines=s.pipeline_defines(config) if config is not None else None
    if config is not None:p.need(type(config.get('exposure')) in (int,float) and np.isfinite(config['exposure']) and config['exposure']>=0,'finite pipeline exposure')
    def matches(shader_id,role):
        if shader_id is None or defines is None:return False
        p.need(type(shader_id) is int and shader_id in shader_map,'bound shader ID');row=shader_map[shader_id];expected={}
        for stage,base in zip(('vertex','fragment'),('simplepbr.vert','simplepbr.frag') if role=='pipeline' else ('post.vert','tonemap.frag') if role=='tonemap' else ('skybox.vert','skybox.frag')):
            name=('assets/shaders/' if role=='skybox' else 'third_party/simplepbr/shaders/')+base+'.glsl'
            if name not in raw:return False
            expected[stage]=raw[name] if role=='skybox' else s.variant(raw[name],defines if role=='pipeline' else {},stage)
        return row['texts']==expected and row['language']==2 and not row['error_flag']
    expected_meshes=m['meshes'];p.need([v.get('mesh_id') for v in meshes]==[v['mesh_id'] for v in expected_meshes[:len(meshes)]] and (not complete or len(meshes)==len(expected_meshes)),'exact material mesh shader bindings');matched=[];input_count=0
    for row,prior in zip(meshes,expected_meshes):
        p.need(row.get('net_state_pointer')==prior['net_state_pointer'] and type(row.get('shader_attrib_pointer')) is int and row['shader_attrib_pointer']>0,'exact cached material RenderState/ShaderAttrib identity')
        inputs=row.get('known_inputs');p.need(isinstance(inputs,list) and [v.get('name') for v in inputs]==list(s.INPUT_NAMES),'known eight PSSM input set')
        for value,name in zip(inputs,s.INPUT_NAMES):_input(value,name);input_count+=1
        matched.append(matches(row.get('shader_id'),'skybox' if prior['path'].endswith('/SkyboxMesh') else 'pipeline'))
    camera=x.get('camera');p.need(isinstance(camera,dict) and all(isinstance(camera.get(k),str) and len(camera[k])<=16384 for k in ('initial_state_text','tag_state_key')),'bounded camera state/tag context')
    owner=x.get('pssm_owner');p.need(isinstance(owner,dict) and type(owner.get('available')) is bool and owner.get('input_values_bound_to_shader') is False,'owner arrays are not effective shader uniform proof')
    if owner['available']:
        p.need(type(owner.get('num_splits')) is int and owner['num_splits']==2,'bounded PSSM split count');material._finite(owner['mvp_array'],(2,4,4));material._finite(owner['nearfar_array'],(2,2))
        p.need(all(type(owner.get(k)) is bool for k in ('use_pssm','fog','freeze_pssm')) and type(owner.get('border_bias')) in (int,float) and np.isfinite(owner['border_bias']),'finite PSSM owner fields')
    tone=x.get('tonemap');tone_match=False
    if tone is not None:
        p.need(all(type(tone.get(k)) is int and tone[k]>0 for k in ('net_state_pointer','shader_attrib_pointer','copy_texture_pointer')) and isinstance(tone.get('quad_path'),str) and len(tone['quad_path'])<=4096,'actual tonemap state/quad');_texture(tone['scene_texture']);_input(tone['tex_input'],'tex');_input(tone['exposure_input'],'exposure');p.need(tone['tex_input']['status']=='AVAILABLE_TEXTURE' and tone['tex_input']['texture']==tone['scene_texture'] and tone['copy_texture_pointer']!=tone['scene_texture']['pointer'],'tonemap input uses actual HDR scene texture distinct from copy texture');tone_match=matches(tone.get('shader_id'),'tonemap')
    p.need(not complete or config is not None and tone is not None,'complete capture has pipeline and tonemap');p.need(type(x.get('bytes_captured')) is int and x['bytes_captured']==total and {v.name for v in folder.glob('shader-text-*.txt')}==files,'all shader byte files accounted')
    variants=complete and bool(matched) and all(matched) and tone_match;result.update(shader_recorded=True,shader_complete=complete,shader_variants_matched=variants,shader=dict(shader_objects=len(shaders),meshes=len(meshes),known_inputs=input_count,source_files=len(sources),captured_bytes=total,elapsed_wall_seconds=x['elapsed_wall_seconds'],mesh_variant_matches=matched,tonemap_variant_matches=tone_match),renderer_diagnostic_passed=result['renderer_diagnostic_passed'] and variants);result['status']='SOURCE_QUALIFIED_CACHED_SHADER_PATH' if result['renderer_diagnostic_passed'] else 'INCONCLUSIVE_CACHED_SHADER_PATH_RECORDED';return result

def validate_receipt(folder,reference_path,nonce):
    folder=Path(folder);result=_clone(material.validate_receipt,ENTRY=ENTRY)(folder,reference_path,nonce);return validate_shader(folder,nonce,result)


def authenticate_source(bundle):
    request=json.loads((ROOT/REQUEST).read_text());source=request['source_sha'];head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    p.need(os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and head==os.environ.get('GITHUB_SHA'),'fresh request attempt1')
    p.need(request.get('schema')=='sdk3-shader-path-request-v1' and request.get('renderer_processes')==1 and request.get('official_model_processes')==request.get('onnx_inferences')==0,'one renderer/zero models scope')
    p.need(request.get('child_timeout_seconds')==600 and request.get('container_timeout_seconds')==630 and request.get('target_pixel')==[596,494],'measured geometry envelope and target')
    p.need(request.get('shader_limits')==LIMITS,'fixed bounded material observation')
    p.need(subprocess.check_output(['git','diff','--name-only',source,head],cwd=ROOT,text=True).splitlines()==[REQUEST],'request-only activation')
    delta=subprocess.check_output(['git','diff','--name-status',BASE,source],cwd=ROOT,text=True).splitlines();p.need(delta and all(x.startswith('A\t') for x in delta),'all old source/verdict bytes preserved')
    for event,key in [('push','push_ci'),('pull_request','pr_ci')]:
        run=p.api('actions/runs/'+str(request[key]));jobs=p.api('actions/runs/'+str(request[key])+'/jobs');artifacts=p.api('actions/runs/'+str(request[key])+'/artifacts')
        p.need(run['head_sha']==source and run['event']==event and run['workflow_id']==411705464 and run['run_attempt']==1 and run['conclusion']=='success' and jobs['total_count']==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(j['conclusion']=='success' for j in jobs['jobs']) and artifacts['total_count']==0,'four exact source CI jobs')
        p.write(bundle/('source-ci-'+event+'.json'),dict(run=run,jobs=jobs,artifacts=artifacts))
    p.write(bundle/'request.json',request);return request

def run():
    out=ROOT/'output/stage7-sdk3-shader-path-01/producer';p.need(not out.exists(),'fresh output');work=out/'work';bundle=out/'bundle';work.mkdir(parents=True);bundle.mkdir();summary=dict(status='FAILED',known_renderer_processes=0,renderer_spawn_attempts=0,official_model_processes=0,onnx_inferences=0,repair_proven=False,stage7_complete=False);p.write(bundle/'summary.json',summary)
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
        summary['execution']=run_renderer('sdk3-shader-'+os.environ['GITHUB_RUN_ID'],sdk,bundle/'renderer',['--repeat','0','--nonce',nonce],reference_path)
        path=bundle/'renderer/native-child.json'
        if path.exists():n=json.loads(path.read_text());summary.update(known_renderer_processes=int(type(n.get('pid')) is int and n['pid']>0),renderer_spawn_attempts=int(n.get('spawn_attempted') is True))
        p.write(bundle/'summary.json',summary);analysis=validate_receipt(bundle/'renderer',reference_path,nonce);p.write(bundle/'analysis.json',analysis);summary=observation_summary(summary,analysis);p.write(bundle/'summary.json',summary);print(json.dumps(summary));return summary
    except BaseException as error:summary['failure']=type(error).__name__+': '+str(error);p.write(bundle/'summary.json',summary);raise

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true',required=True);parser.parse_args();run()
if __name__=='__main__':main()
