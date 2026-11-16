"""Authenticated zero-model renderer jobs and independent CPU candidate audit."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
from types import FunctionType
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from scripts import panda_sdk3_runtime as p,sdk3_pixel_geometry as g
from scripts.continue_panda_sdk3_models import PROFILE,unpack_prior
from scripts.compare_native_mdv3_rgb_pixels import read_verified_pixels
ROOT=Path(__file__).resolve().parents[1]
BASE='d02fefd283375be5e020c3fd4923f05f19ac21da'
REQUEST='docs/requests/sdk3-pixel-geometry-20261116-01.json'


def native_command(name,repo,sdk,out,args,*,reference,owner=None,model=None,deps=None):
    p.need(model is None and deps is None,'zero-model resource mode has no model/dependency mount')
    cmd=p.container_command(name,repo,sdk,out,args,owner=owner)
    for key,value in [('--memory','10g'),('--memory-swap','10g'),('--cpus','2'),('--tmpfs','/tmp:rw,nosuid,nodev,size=512m')]:cmd[cmd.index(key)+1]=value
    i=cmd.index('LD_DEBUG=bindings,versions');p.need(cmd[i-1]=='--env','known legacy debug option');del cmd[i-1:i+1]
    i=cmd.index(p.IMAGE);cmd[i:i]=['--mount',f'type=bind,src={Path(reference).resolve()},dst=/reference.json,readonly']
    i=cmd.index('/work/repo/scripts/panda_sdk3_diagnostic.py');cmd[i]='/work/repo/scripts/sdk3_pixel_geometry_native.py'
    return cmd


def run_renderer(name,sdk,out,args,reference):
    def command(*a,**kw):return native_command(*a,reference=reference,**kw)
    original=p.run_container
    function=FunctionType(original.__code__,dict(original.__globals__,container_command=command),original.__name__,original.__defaults__,original.__closure__)
    function.__kwdefaults__=dict(original.__kwdefaults__ or {})
    return function(name,sdk,out,args)


def validate_command(receipt,container,repeat,nonce):
    command=receipt.get('argv');p.need(isinstance(command,list) and all(type(v) is str for v in command) and command[:2]==['docker','create'] and command.count(p.IMAGE)==1,'actual Docker create command')
    split=command.index(p.IMAGE);prefix=command[2:split];options={};flags=[];i=0
    singles={'--network':'none','--user':'65534:65534','--cap-drop':'ALL','--security-opt':'no-new-privileges','--memory':'10g','--memory-swap':'10g','--cpus':'2','--pids-limit':'128','--ipc':'private','--ulimit':'core=0','--tmpfs':'/tmp:rw,nosuid,nodev,size=512m','--workdir':'/work/repo','--entrypoint':'/opt/venv/bin/python'}
    allowed=set(singles)|{'--name','--mount','--env','--label'}
    while i<len(prefix):
        key=prefix[i]
        if key=='--read-only':flags.append(key);i+=1;continue
        p.need(key in allowed and i+1<len(prefix),'no undeclared container options')
        options.setdefault(key,[]).append(prefix[i+1]);i+=2
    p.need(flags==['--read-only'] and set(options)==allowed and all(options.get(k)==[v] for k,v in singles.items()),'fixed actual container isolation/resource options')
    p.need(options['--name']==[container.get('name')] and type(container.get('name')) is str and bool(container['name']),'container command name binding')
    owner=receipt.get('ownership_label');p.need(type(owner) is str and len(owner)==32 and all(c in '0123456789abcdef' for c in owner) and container.get('ownership_label')==owner and options['--label']==['stage7.sdk3.owner='+owner],'actual ownership label binding')
    expected_env={'DISPLAY':':99','HOME':'/tmp','XDG_CACHE_HOME':'/tmp/cache','LIBGL_ALWAYS_SOFTWARE':'1','GALLIUM_DRIVER':'softpipe','LP_NUM_THREADS':'0','MESA_SHADER_CACHE_DISABLE':'true','PYOPENGL_PLATFORM':'glx','OMP_NUM_THREADS':'2'}
    env=[v.split('=',1) for v in options['--env']]
    p.need(all(len(v)==2 for v in env) and len(env)==len(expected_env) and dict(env)==expected_env,'fixed software renderer/runtime environment;no duplicate overrides')
    mounts={}
    for text in options['--mount']:
        entries=[part.split('=',1) for part in text.split(',')];row={parts[0]:parts[1] if len(parts)==2 else True for parts in entries}
        p.need(len(row)==len(entries) and row.get('type')=='bind' and type(row.get('src')) is str and Path(row['src']).is_absolute() and row.get('dst') not in mounts,'actual unique absolute bind mount')
        mounts[row.get('dst')]=row
    expected_mounts={'/work/repo',p.SDK_PATH,'/out','/reference.json'};p.need(set(mounts)==expected_mounts,'exact native source/SDK/output/model/dependency mounts')
    for destination,row in mounts.items():
        p.need(set(row)==({'type','src','dst'} if destination=='/out' else {'type','src','dst','readonly'}) and (destination=='/out' or row.get('readonly') is True),'original payload mounts readonly')
    expected=['-I','-S','-B','/work/repo/scripts/sdk3_pixel_geometry_native.py','--out','/out','--repeat',str(repeat),'--nonce',nonce]
    p.need(command[split+1:]==expected,'fixed native pair entrypoint and diagnostic condition')



def validate_receipt(folder,reference_path,repeat,nonce):
    folder=Path(folder);reference_path=Path(reference_path);reference=json.loads(reference_path.read_text());execution=json.loads((folder/'execution.json').read_text());container=json.loads((folder/'container.json').read_text());native=json.loads((folder/'native-child.json').read_text());report=json.loads((folder/'report.json').read_text())
    identity=container.get('id');p.need(type(identity) is str and len(identity)==64 and all(c in '0123456789abcdef' for c in identity) and execution.get('container_id')==identity,'valid actual renderer container identity')
    p.need(execution.get('returncode')==0 and execution.get('failure') is None and execution.get('owned_container_removed') is True and execution.get('ownership_unresolved') is False,'clean owned renderer container')
    state=execution.get('stopped_state',{});p.need(state.get('Running') is False and state.get('Pid')==0 and state.get('OOMKilled') is False and state.get('ExitCode')==0,'stopped non-OOM renderer')
    p.need(container.get('image')==p.IMAGE and container.get('effective_limits')==PROFILE,'same bounded frozen renderer resource profile');validate_command(json.loads((folder/'command.json').read_text()),container,repeat,nonce)
    p.need(native.get('spawn_attempted') is True and type(native.get('pid')) is int and native['pid']>0 and native['pid']==report.get('pid') and native.get('returncode')==native.get('server_returncode')==0,'actual native/display success')
    p.need(report.get('protocol')=='sdk3-pixel-geometry-v1' and report.get('status')=='ZERO_MODEL_REPLAY_RECORDED' and report.get('repeat')==repeat and report.get('seed')==20261110 and report.get('scenario')=='s_curve_left_right' and report.get('nonce')==nonce and type(report.get('process_uuid')) is str and len(report['process_uuid'])==32,'fresh native replay identity')
    p.need(report.get('core_sha256')==p.CORE_SHA and report.get('sdk_sha256')==p.SDK_SHA and report.get('panda_version')=='1.10.13' and report.get('base_camera_sha256')=='23d90c3d12894f855ae64d4607c03f3bf34e31e28dd7f5ce82bd0ddc7b37faf5' and report.get('reference_sha256')==p.digest(reference_path),'actual pinned native source inputs')
    p.need(all(type(report.get(k)) is int and report[k]==0 for k in ('official_model_processes','onnx_inferences','extra_gpu_queries','extra_render_tasks')) and all(report.get(k) is False for k in ('ort_used','ort_module_loaded','model_weights_used','repair_proven','stage7_complete')),'zero-model diagnostic only,no inferred repair')
    p.need(report.get('provider_closed') is True and report.get('getter_restored') is True and report.get('child_finalized_before_server_stop') is True and report.get('server_returncode')==0,'exact observer/provider/display lifetime')
    p.need(report.get('observer')==dict(read_attempts=7,reads=7,inspection_attempts=1,inspections=1) and report.get('task_frame_count_delta')==14,'original sevenRoad/sevenWide captures without extra task ticks')
    tasks=report.get('tasks_before');p.need(isinstance(tasks,list) and tasks==report.get('tasks_after') and all(tasks.count(k)==1 for k in ('igLoop','PSSM.update','update main chase camera')),'unchanged original task membership')
    p.need('softpipe' in report.get('driver',{}).get('renderer','').lower(),'same software renderer')
    replay=g.qualify_replay(report['captures'],reference);p.need(replay==report.get('replay'),'independently recomputed exact replay membership')
    images=report.get('target_images');p.need(isinstance(images,list) and [r.get('camera') for r in images]==['road','wide'],'both target original RGB images')
    for row in images:
        camera=row['camera'];p.need(row.get('file')=='step7-'+camera+'.rgb.zlib' and row.get('shape')==[604,964,3] and row.get('sha256')==report['captures'][6][camera+'_sha256'],'source-bound target image');pixels=read_verified_pixels(folder,row)
        if camera=='road':p.need(pixels[494,596].tolist()==report.get('target_road_rgb') and row['sha256']==report.get('target_read_sha256'),'actual inspected target pixel')
    geometry=report.get('geometry',{});p.need(geometry.get('stage')=='AFTER_ORIGINAL_ROAD_CPU_READ_BEFORE_CAMERA_RESTORE' and geometry.get('borrowed_parent_is_origin') is True and geometry.get('source_viewport')==[0.,1.,0.,1.] and geometry.get('source_buffer_size')==[964,604],'CPU state from borrowed full-source camera')
    p.need(all(geometry.get(k) is False for k in ('cpu_scene_coverage_proven','gpu_pixel_owner_proven','depth_tie_proven','unique_cause_proven')) and geometry.get('cpu_sample_rays_not_msaa_positions') is True and geometry.get('cpu_net_state_not_actual_cull_draw_state') is True,'no CPU-to-GPU ownership/depth/causality overclaim')
    p.need(type(geometry.get('scan_finished_within_budget')) is bool,'explicit geometry truncation status')
    triangles,ids=g.load_geometry_archive(folder/'geometry.npz',geometry['triangle_archive']);meshes=geometry['meshes'];p.need(geometry.get('counts',{}).get('triangles_tested')==len(triangles),'complete retained tested triangle count')
    cursor=0
    for index,mesh in enumerate(meshes):
        end=mesh['triangle_end'];p.need(mesh['mesh_id']==index and mesh['triangle_start']==cursor and cursor<=end<=len(triangles) and mesh['path'],'ordered mesh/triangle source ranges')
        selected=ids[cursor:end]
        p.need(np.all(selected[:,0]==index) and np.all(selected[:,3:]<mesh['vertex_count']) and all(row[1]<len(mesh['primitive_triangle_counts']) and row[2]<mesh['primitive_triangle_counts'][row[1]] for row in selected),'authentic source-index ranges')
        cursor=end
    p.need(cursor==len(triangles),'every tested triangle has a source mesh')
    rays=geometry['rays'];p.need([dict(name=r['name'],ndc=r['ndc']) for r in rays]==g.pixel_samples(964,604,596,494),'exact top-left center/corner ray labels')
    error=g.ray_projection_error(rays,geometry['camera_to_world'],geometry['lens_projection']);p.need(error<=1e-5,'CPU camera/lens ray reprojection,not an image tolerance')
    hits=g.all_ray_hits(triangles,rays);declared=geometry.get('hits');p.need(isinstance(declared,dict) and set(declared)==set(hits),'complete reported sample hit sets')
    for name,rows in hits.items():
        p.need(len(rows)==len(declared[name]),'independent CPU hit membership')
        for left,right in zip(rows,declared[name]):
            p.need(set(right)==set(left) and left['triangle_index']==right.get('triangle_index'),'independent source triangle identity')
            p.need(np.allclose([left['distance'],*left['barycentric'],*left['position']],[right['distance'],*right['barycentric'],*right['position']],rtol=1e-12,atol=1e-9),'independent CPU numerical intersection')
    return dict(status='ZERO_MODEL_CPU_CANDIDATES_RECOMPUTED',repeat=repeat,process_uuid=report['process_uuid'],pid=native['pid'],container_id=identity,replay=replay,geometry_scan_finished=geometry['scan_finished_within_budget'],triangles_tested=len(triangles),meshes_tested=len(meshes),hits=hits,cpu_reprojection_max_abs_ndc_error=error,cpu_intersection_recompute_tolerance=dict(rtol=1e-12,atol_world_units=1e-9),cpu_ray_reprojection_tolerance_ndc=1e-5,target_road_rgb=report['target_road_rgb'],official_model_processes=0,onnx_inferences=0,original_matrix_passed=3,original_matrix_total=4,original_matrix_gate_passed=False,gpu_pixel_owner_proven=False,depth_tie_proven=False,unique_cause_proven=False,repair_proven=False,stage7_complete=False)


def authenticate_source(bundle):
    request=json.loads((ROOT/REQUEST).read_text());source=request['source_sha'];head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    p.need(os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and head==os.environ.get('GITHUB_SHA'),'fresh single renderer request')
    p.need(request.get('schema')=='sdk3-pixel-geometry-request-v1' and request.get('renderer_processes')==2 and request.get('official_model_processes')==request.get('onnx_inferences')==0 and request.get('target_pixel')==[596,494],'two-renderer zero-model scope')
    p.need(subprocess.check_output(['git','diff','--name-only',source,head],cwd=ROOT,text=True).splitlines()==[REQUEST],'request-only activation')
    delta=subprocess.check_output(['git','diff','--name-status',BASE,source],cwd=ROOT,text=True).splitlines();p.need(delta and all(row.startswith('A\t') for row in delta),'all existing source and verdict bytes/modes unchanged')
    for event,key in [('push','push_ci'),('pull_request','pr_ci')]:
        run=p.api('actions/runs/'+str(request[key]));jobs=p.api('actions/runs/'+str(request[key])+'/jobs');artifacts=p.api('actions/runs/'+str(request[key])+'/artifacts')
        p.need(run['head_sha']==source and run['event']==event and run['workflow_id']==411705464 and run['run_attempt']==1 and run['conclusion']=='success','exact reviewed source canonical CI')
        p.need(jobs['total_count']==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(j['conclusion']=='success' for j in jobs['jobs']) and artifacts['total_count']==0,'four successful source jobs and no artifacts')
        p.write(bundle/('source-ci-'+event+'.json'),dict(run=run,jobs=jobs,artifacts=artifacts))
    p.write(bundle/'request.json',request);return request


def run(repeat):
    p.need(type(repeat) is int and repeat in (0,1),'declared renderer repeat')
    out=ROOT/'output/stage7-sdk3-pixel-geometry-01'/str(repeat)/'producer';p.need(not out.exists(),'fresh renderer output');work=out/'work';bundle=out/'bundle';work.mkdir(parents=True);bundle.mkdir()
    summary=dict(status='FAILED',repeat=repeat,known_renderer_processes=0,renderer_spawn_attempts=0,official_model_processes=0,onnx_inferences=0,repair_proven=False,stage7_complete=False);p.write(bundle/'summary.json',summary)
    try:
        request=authenticate_source(bundle);summary['source_sha']=request['source_sha'];p.write(bundle/'summary.json',summary)
        prior_run=p.api('actions/runs/43854755697');p.need(prior_run['workflow_id']==420027188 and prior_run['head_sha']=='bddd41d9f607a6ba20fc65da4291b76837db4b2f' and prior_run['run_attempt']==1 and prior_run['status']=='completed' and prior_run['conclusion']=='success','prior actual full-RGB observation origin');p.write(bundle/'prior-run.json',prior_run)
        prior_zip=p.artifact(work,bundle,14220249832,43506956,'6136240ea3894d5c90b16fa9c0e6c10e5829c59d7565daa00556084f1789aba1',43854755697,'bddd41d9f607a6ba20fc65da4291b76837db4b2f','prior-full-rgb')
        prior=bundle/'prior-full-rgb';unpack_prior(prior_zip,prior)
        from scripts.run_sdk3_rgb_forensics import validate_observed_pair
        original=validate_observed_pair(prior,'full_rgb');p.need(original['first_raw_source_diff_step']==7 and original['strict_pair_pass'] is False,'preserve original single-pixel failure')
        reports=[json.loads((prior/'pair'/f'run-{i}'/'run.json').read_text()) for i in (0,1)];reference=g.reference_from_reports(*reports);reference_path=bundle/'reference.json';p.write(reference_path,reference)
        p.need(shutil.disk_usage(work).free>=8*1024**3,'8GiB ephemeral staging disk')
        iz=p.artifact(work,bundle,14156262448,1738137175,'47711425a5a48fb2ef0cab140da6e394516f9cbb7f04b294c5f6583d7efbc687',43700449423,'7cf0f0157f8100f0aa0e05b01a815d7395c3383f','image')
        sz=p.artifact(work,bundle,14191115165,61661546,'2a44226962b3175081566918dd55eb845ac8ce1c9f9f5a396f469c8f6eca5d26',43786081196,'40dd7187ce8d3c5de510aa8c7a8ac2a6d37b0f38','sdk3')
        image=p.verify_member(iz,'image.tar',1727678464,'4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698',work/'image.tar');sdk=p.verify_member(sz,'candidate/libpandagl.so.data',1052968,p.SDK_SHA,work/'libpandagl.so')
        subprocess.run(['docker','load','-i',str(image)],check=True,timeout=600);p.need(json.loads(subprocess.check_output(['docker','image','inspect',p.IMAGE],text=True))[0]['Id']==p.IMAGE,'same immutable SDK renderer image')
        mem={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines()) if k in ('MemTotal','MemAvailable')};summary['host_memory']=mem;p.need(mem['MemAvailable']>=12*1024**3,'12GiB host availability')
        import secrets
        nonce=secrets.token_hex(16);summary['nonce']=nonce;p.write(bundle/'summary.json',summary)
        print('ZERO_MODEL_GEOMETRY_RENDERER_START',repeat,flush=True)
        execution=run_renderer('sdk3-geometry-'+os.environ['GITHUB_RUN_ID']+'-'+str(repeat),sdk,bundle/'renderer',['--repeat',str(repeat),'--nonce',nonce],reference_path);summary['execution']=execution
        native_path=bundle/'renderer/native-child.json'
        if native_path.exists():
            native=json.loads(native_path.read_text());summary['known_renderer_processes']=int(type(native.get('pid')) is int and native['pid']>0);summary['renderer_spawn_attempts']=int(native.get('spawn_attempted') is True)
        p.write(bundle/'summary.json',summary);analysis=validate_receipt(bundle/'renderer',reference_path,repeat,nonce);p.write(bundle/'analysis.json',analysis)
        summary.update(status='ZERO_MODEL_CPU_CANDIDATES_RECOMPUTED',source_images_match_reference=analysis['replay']['source_images_match_reference'],geometry_scan_finished=analysis['geometry_scan_finished'],triangles_tested=analysis['triangles_tested'],native_renderer_processes=1)
        p.write(bundle/'summary.json',summary);print(json.dumps(summary),flush=True);return summary
    except BaseException as error:summary['failure']=type(error).__name__+': '+str(error);p.write(bundle/'summary.json',summary);raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true',required=True);parser.add_argument('--repeat',type=int,choices=(0,1),required=True);args=parser.parse_args();run(args.repeat)

if __name__=='__main__':main()
