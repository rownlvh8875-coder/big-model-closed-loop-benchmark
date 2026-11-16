"""Authenticate CPU material state without relaxing inherited image/geometry gates."""
from __future__ import annotations
import argparse,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path,PurePosixPath
from types import FunctionType
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from scripts import panda_sdk3_runtime as p,sdk3_pixel_geometry as g,sdk3_pixel_material as material,run_sdk3_pixel_geometry_budget as budget,sdk3_pixel_geometry_budget_runtime as runtime
from scripts.continue_panda_sdk3_models import unpack_prior
ROOT=Path(__file__).resolve().parents[1];BASE='288fc0a80a11c28630239d031e61ffaf0d381e51';REQUEST='docs/requests/sdk3-pixel-material-20261117-01.json';ENTRY='/work/repo/scripts/sdk3_pixel_material_native.py'
LIMITS=dict(max_hits_per_ray=8,max_triangles=40,max_stages=8,max_textures=16,max_file_bytes=8388608,max_total_bytes=16777216,max_cpu_seconds=20)
observation_summary=budget.observation_summary


def _clone(function,**globals):
    fn=FunctionType(function.__code__,dict(function.__globals__,**globals),function.__name__,function.__defaults__,function.__closure__);fn.__kwdefaults__=dict(function.__kwdefaults__ or {});return fn


def native_command(*args,**kwargs):
    cmd=runtime.native_command(*args,**kwargs);cmd[cmd.index(runtime.ENTRY)]=ENTRY;return cmd


def run_renderer(name,sdk,out,args,reference):return _clone(runtime.run_renderer,native_command=native_command)(name,sdk,out,args,reference)


def _finite(value,shape):
    array=np.asarray(value,float);p.need(array.shape==shape and np.isfinite(array).all(),'finite material attribute extent');return array


def _sampler(value):
    integer=('wrap_u','wrap_v','wrap_w','minfilter','magfilter','effective_minfilter','effective_magfilter','anisotropic_degree','effective_anisotropic_degree');p.need(isinstance(value,dict) and all(type(value.get(k)) is int for k in integer),'integer CPU sampler fields')
    p.need(all(0<=value[k]<=4 for k in integer[:3]) and all(0<=value[k]<=7 for k in integer[3:7]) and all(-1<=value[k]<=65536 for k in integer[7:]),'pinned sampler enum/range')
    _finite(value['border_color'],(4,));p.need(all(type(value.get(k)) in (int,float) and np.isfinite(value[k]) for k in ('min_lod','max_lod','lod_bias')) and isinstance(value.get('text'),str) and len(value['text'])<=4096,'finite bounded sampler values')
    return {k:v for k,v in value.items() if k!='text'}


def _attribute(value,required=None):
    p.need(isinstance(value,dict) and value.get('status') in ('CAPTURED','UNAVAILABLE_COLUMN','UNSUPPORTED_COMPONENT_COUNT'),'explicit vertex attribute availability')
    if value['status']=='CAPTURED':
        count=value.get('components');p.need(type(count) is int and count in (2,3,4) and (required is None or count==required),'vertex attribute components');return _finite(value['values'],(3,count))
    p.need(value.get('values') is None,'unavailable attribute has no invented values');return None


def validate_material(folder,report,nonce,result):
    path=folder/'material.json';p.need(path.stat().st_size<=8*1024**2,'bounded material manifest');m=json.loads(path.read_text());p.need(m.get('protocol')=='sdk3-pixel-material-v1' and type(m.get('pid')) is int and m['pid']==report['pid'] and m.get('nonce')==nonce,'material observer identity')
    result.update(material_recorded=False,material_complete=None,material=None,gpu_material_result_proven=False)
    if not result['geometry_recorded']:p.need(not result['native_completed'],'complete native requires material snapshot');return result
    parent=json.loads((folder/'geometry-observer.json').read_text());geo=parent['geometry'];p.need(m.get('target_read_sha256')==parent['target_read_sha256'] and m.get('geometry_archive_sha256')==geo['triangle_archive']['sha256'] and m.get('borrowed_parent_is_origin') is True,'material bound to inspected Road/geometry/camera')
    p.need(m.get('limits')==LIMITS and type(m.get('selection_complete')) is bool and m.get('status') in ('MATERIAL_RECORDED','MATERIAL_PARTIAL'),'fixed material limits/status')
    p.need(all(m.get(k) is False for k in ('gpu_material_result_proven','gpu_pixel_owner_proven','unique_cause_proven','repair_proven','stage7_complete')) and m.get('shader_inputs_unenumerated') is True and m.get('hardware_sampler_state_unobserved') is True,'CPU state is not actual shader/hardware ownership')
    if result['native_completed']:p.need(m.get('observer_finalized') is True,'material wrapper finalization')
    p.need(m.get('clock')=='journal_elapsed_monotonic_seconds' and all(type(m.get(k)) in (int,float) and np.isfinite(m[k]) for k in ('material_enter_elapsed_s','material_exit_elapsed_s','cpu_seconds')),'material clock binding')
    rows=budget.read_journal(folder/'progress.jsonl');enter=next(r['elapsed_s'] for r in rows if r['event']=='checkpoint' and r['metadata'].get('stage')=='GEOMETRY_ENTER');exit=next(r['elapsed_s'] for r in rows if r['event']=='checkpoint' and r['metadata'].get('stage')=='GEOMETRY_RETURN')
    p.need(enter<=m['material_enter_elapsed_s']<=m['material_exit_elapsed_s']<=exit and 0<=m['cpu_seconds']<=600 and abs(m['material_exit_elapsed_s']-m['material_enter_elapsed_s']-m['cpu_seconds'])<=.01,'material inside borrowed-camera geometry interval')
    reasons=m.get('truncation_reasons');p.need(isinstance(reasons,list) and all(r in ('hit_budget','triangle_budget','stage_budget','texture_budget','time_budget') for r in reasons),'explicit material truncation')
    complete=m['selection_complete'];p.need((not reasons and m['cpu_seconds']<=20) if complete else bool(reasons),'complete material cannot hide budget omissions')
    packed,ids=g.load_geometry_archive(folder/'geometry.npz',geo['triangle_archive']);wanted=[]
    for ray in geo['rays']:
        for hit in result['geometry']['hits'][ray['name']][:8]:
            if hit['triangle_index'] not in wanted:wanted.append(hit['triangle_index'])
    wanted=wanted[:40];selected=m.get('selected_triangle_indices');p.need(isinstance(selected,list) and selected==wanted[:len(selected)] and len(selected)<=40 and (not complete or selected==wanted),'deterministic bounded CPU candidate selection')
    textures=m.get('textures');meshes=m.get('meshes');triangles=m.get('triangles');samples=m.get('samples');p.need(isinstance(textures,list) and len(textures)<=16 and isinstance(meshes,list) and len(meshes)<=40 and isinstance(triangles,list) and [t.get('triangle_index') for t in triangles]==selected and isinstance(samples,list),'bounded material tables')
    files=set();captured=0;without_ram=0
    for index,texture in enumerate(textures):
        p.need(texture.get('texture_id')==index and type(texture.get('pointer')) is int and texture['pointer']>0,'texture identity')
        p.need(all(type(texture.get(k)) is int and 0<=texture[k]<2**63 for k in ('x_size','y_size','z_size','num_components','component_width','component_type','format','texture_type')) and all(isinstance(texture.get(k),str) and len(texture[k])<=4096 for k in ('name','filename','fullpath')),'bounded cached texture properties')
        for kind in ('ram','asset'):
            item=texture.get(kind,{});status=item.get('status');p.need(status in ('CAPTURED','UNAVAILABLE_NOT_RESIDENT','UNAVAILABLE_LIMIT','UNAVAILABLE_NO_PATH','UNAVAILABLE_OUTSIDE_ASSET_ROOT','UNAVAILABLE_FILE_TYPE','UNAVAILABLE_NOT_REGULAR','UNAVAILABLE_READ_ERROR'),'explicit texture byte availability')
            if kind=='ram' and status!='CAPTURED':without_ram+=1
            if status=='CAPTURED':
                name=item.get('file');p.need(type(name) is str and re.fullmatch(r'material-\d{3}-'+kind+r'\.bin',name) is not None and name not in files and type(item.get('nbytes')) is int and 0<item['nbytes']<=8388608,'unique bounded texture byte descriptor');file=folder/name;p.need(file.stat().st_size==item['nbytes'] and p.digest(file)==item.get('sha256'),'actual CPU texture bytes');files.add(name);captured+=item['nbytes']
                if kind=='ram':p.need(item.get('resident_before') is True and type(item.get('expected_nbytes')) is int and 0<item['expected_nbytes']<=8388608 and type(item.get('compression')) is int and (item['compression']!=0 or item['nbytes']==item['expected_nbytes']),'resident RAM extent/compression')
                else:
                    source=PurePosixPath(item.get('source_path',''));root=PurePosixPath('/opt/venv/lib/python3.11/site-packages/metadrive/assets');p.need(source.is_absolute() and source.is_relative_to(root) and '..' not in source.parts and '\\' not in str(source),'readonly asset provenance')
            else:p.need('file' not in item and 'sha256' not in item,'unavailable bytes cannot invent data')
    p.need(type(m.get('bytes_captured')) is int and m['bytes_captured']==captured<=16777216 and {p.name for p in folder.glob('material-*.bin')}==files,'all material byte files accounted within global budget')
    mesh_map={}
    for mesh in meshes:
        mesh_id=mesh.get('mesh_id');p.need(type(mesh_id) is int and mesh_id not in mesh_map and 0<=mesh_id<len(geo['meshes']),'unique actual mesh material');original=geo['meshes'][mesh_id]
        p.need(all(mesh.get(k)==original.get(k) for k in ('node_ordinal','path','geom_index','geom_pointer','vertex_data_pointer','local_to_world','net_state_text','net_state_text_truncated')),'material mesh/state/source transform binding');_finite(mesh['local_to_world'],(4,4));p.need(type(mesh.get('net_state_pointer')) is int and mesh['net_state_pointer']>0 and isinstance(mesh.get('material'),dict),'CPU material state descriptor')
        stages=mesh.get('stages');count=mesh.get('source_stage_count');p.need(type(count) is int and 0<=count<2**31 and isinstance(stages,list) and len(stages)<=min(count,8) and (not complete or len(stages)==count),'bounded complete/partial stage table')
        for stage_id,stage in enumerate(stages):
            p.need(stage.get('stage_id')==stage_id and type(stage.get('texture_id')) is int and 0<=stage['texture_id']<len(textures) and isinstance(stage.get('texcoord_column'),str) and 0<len(stage['texcoord_column'])<=256 and isinstance(stage.get('name'),str) and len(stage['name'])<=256 and type(stage.get('sort')) is int and type(stage.get('mode')) is int,'actual stage/texture/column link');_finite(stage['texture_matrix'],(4,4));effective=_sampler(stage['effective_sampler']);default=_sampler(stage['texture_default_sampler']);p.need(stage.get('differs_from_texture_default') is (effective!=default),'actual stage sampler value override')
        mesh_map[mesh_id]=mesh
    p.need(set(mesh_map)=={int(ids[i,0]) for i in selected},'exact selected mesh set')
    triangle_map={}
    for triangle in triangles:
        index=triangle['triangle_index'];source=ids[index].tolist();p.need(triangle.get('source_id')==source,'actual primitive/vertex IDs');mesh=mesh_map[source[0]];positions=_finite(triangle['positions_local'],(3,3));p.need(np.allclose(g.transform_points(positions,mesh['local_to_world']),packed[index],rtol=1e-12,atol=1e-9),'actual source vertex positions');_attribute(triangle['normals'],required=3);columns={s['texcoord_column'] for s in mesh['stages']};p.need(isinstance(triangle.get('texcoords'),dict) and set(triangle['texcoords'])==columns,'all actual stage UV columns')
        for column in columns:_attribute(triangle['texcoords'][column])
        triangle_map[index]=triangle
    expected=[(ray['name'],hit['triangle_index'],hit) for ray in geo['rays'] for hit in result['geometry']['hits'][ray['name']][:8] if hit['triangle_index'] in triangle_map];p.need([(s.get('ray'),s.get('triangle_index')) for s in samples]==[(name,index) for name,index,_ in expected],'exact sample/candidate set');uv_count=0
    for sample,(name,index,hit) in zip(samples,expected):
        p.need(np.allclose(_finite(sample['barycentric'],(3,)),hit['barycentric'],rtol=1e-12,atol=1e-9),'actual ray triangle barycentric');triangle=triangle_map[index];mesh=mesh_map[triangle['source_id'][0]];p.need(isinstance(sample.get('stages'),list) and len(sample['stages'])==len(mesh['stages']),'all sample stages')
        for row,stage in zip(sample['stages'],mesh['stages']):
            column=stage['texcoord_column'];p.need(row.get('stage_id')==stage['stage_id'] and row.get('texture_id')==stage['texture_id'] and row.get('column')==column,'sample stage binding');attribute=triangle['texcoords'][column]
            if attribute['status']=='CAPTURED' and attribute['components']==2:
                uv=material.interpolate_uv(attribute['values'],hit['barycentric']);transformed=material.transform_uv(uv,stage['texture_matrix']);p.need(row.get('status')=='CAPTURED' and np.allclose(_finite(row['uv'],(2,)),uv,rtol=1e-12,atol=1e-9) and np.allclose(_finite(row['transformed4'],(4,)),transformed,rtol=1e-12,atol=1e-9),'independently recomputed CPU UV/texture transform');uv_count+=1
            else:p.need(row.get('status')=='UNAVAILABLE_2D_UV' and row.get('uv') is None and row.get('transformed4') is None,'unsupported UV remains unavailable')
    result.update(material_recorded=True,material_complete=complete,material=dict(triangles=len(triangles),meshes=len(meshes),textures=len(textures),samples=len(samples),two_d_stage_samples=uv_count,captured_bytes=captured,textures_without_ram=without_ram,cpu_seconds=m['cpu_seconds']),renderer_diagnostic_passed=result['renderer_diagnostic_passed'] and complete)
    result['status']='SOURCE_QUALIFIED_CPU_MATERIAL_RECOMPUTED' if result['renderer_diagnostic_passed'] else 'INCONCLUSIVE_CPU_MATERIAL_RECORDED';return result


def validate_receipt(folder,reference_path,nonce):
    def qualified(path,report,identity,result):return validate_material(path,report,identity,budget.qualify_geometry(path,report,identity,result))
    return _clone(budget.validate_receipt,ENTRY=ENTRY,qualify_geometry=qualified)(folder,reference_path,nonce)


def authenticate_source(bundle):
    request=json.loads((ROOT/REQUEST).read_text());source=request['source_sha'];head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    p.need(os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and head==os.environ.get('GITHUB_SHA'),'fresh request attempt1')
    p.need(request.get('schema')=='sdk3-pixel-material-request-v1' and request.get('renderer_processes')==1 and request.get('official_model_processes')==request.get('onnx_inferences')==0,'one renderer/zero models scope')
    p.need(request.get('child_timeout_seconds')==600 and request.get('container_timeout_seconds')==630 and request.get('target_pixel')==[596,494],'measured geometry envelope and target')
    p.need(request.get('material_limits')==LIMITS,'fixed bounded material observation')
    p.need(subprocess.check_output(['git','diff','--name-only',source,head],cwd=ROOT,text=True).splitlines()==[REQUEST],'request-only activation')
    delta=subprocess.check_output(['git','diff','--name-status',BASE,source],cwd=ROOT,text=True).splitlines();p.need(delta and all(x.startswith('A\t') for x in delta),'all old source/verdict bytes preserved')
    for event,key in [('push','push_ci'),('pull_request','pr_ci')]:
        run=p.api('actions/runs/'+str(request[key]));jobs=p.api('actions/runs/'+str(request[key])+'/jobs');artifacts=p.api('actions/runs/'+str(request[key])+'/artifacts')
        p.need(run['head_sha']==source and run['event']==event and run['workflow_id']==411705464 and run['run_attempt']==1 and run['conclusion']=='success' and jobs['total_count']==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(j['conclusion']=='success' for j in jobs['jobs']) and artifacts['total_count']==0,'four exact source CI jobs')
        p.write(bundle/('source-ci-'+event+'.json'),dict(run=run,jobs=jobs,artifacts=artifacts))
    p.write(bundle/'request.json',request);return request

def run():
    out=ROOT/'output/stage7-sdk3-pixel-material-01/producer';p.need(not out.exists(),'fresh output');work=out/'work';bundle=out/'bundle';work.mkdir(parents=True);bundle.mkdir();summary=dict(status='FAILED',known_renderer_processes=0,renderer_spawn_attempts=0,official_model_processes=0,onnx_inferences=0,repair_proven=False,stage7_complete=False);p.write(bundle/'summary.json',summary)
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
        summary['execution']=run_renderer('sdk3-material-'+os.environ['GITHUB_RUN_ID'],sdk,bundle/'renderer',['--repeat','0','--nonce',nonce],reference_path)
        path=bundle/'renderer/native-child.json'
        if path.exists():n=json.loads(path.read_text());summary.update(known_renderer_processes=int(type(n.get('pid')) is int and n['pid']>0),renderer_spawn_attempts=int(n.get('spawn_attempted') is True))
        p.write(bundle/'summary.json',summary);analysis=validate_receipt(bundle/'renderer',reference_path,nonce);p.write(bundle/'analysis.json',analysis);summary=observation_summary(summary,analysis);p.write(bundle/'summary.json',summary);print(json.dumps(summary));return summary
    except BaseException as error:summary['failure']=type(error).__name__+': '+str(error);p.write(bundle/'summary.json',summary);raise

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true',required=True);parser.parse_args();run()
if __name__=='__main__':main()
