"""Authenticate sparse selector windows without relaxing inherited verdicts."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,sys
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import run_sdk3_terrain_state as previous,sdk3_terrain_attribute as sparse
from scripts.run_sdk3_terrain_state import p,g,cache,unpack_prior,observation_summary,LIMITS,runtime
ROOT=Path(__file__).resolve().parents[1];BASE='279ab9d6881a4924bb27aca6de198fd8e9ee1d04';REQUEST='docs/requests/sdk3-terrain-attribute-20261117-01.json';ENTRY='/work/repo/scripts/sdk3_terrain_attribute_native.py';TERRAIN_LIMITS=sparse.LIMITS
_window=sparse.clone(previous._window,terrain=sparse.proxy())

def native_command(*args,**kwargs):
    command=runtime.native_command(*args,**kwargs);command[command.index(runtime.ENTRY)]=ENTRY;return command

def run_renderer(name,sdk,out,args,reference):return sparse.clone(runtime.run_renderer,native_command=native_command)(name,sdk,out,args,reference)

def validate_terrain(folder,nonce,result):
    result=sparse.clone(previous.validate_terrain,terrain=sparse.proxy(),TERRAIN_LIMITS=TERRAIN_LIMITS,_window=_window)(folder,nonce,result)
    result.update(attribute_window_count=0,attribute_collection_complete=False,sparse_sample_bytes_captured=0,sparse_rss_delta_kib=None)
    if not result['terrain_recorded']:return result
    x=json.loads((Path(folder)/'terrain.json').read_text());p.need(x.get('sparse_policy')==sparse.SPARSE_POLICY,'exact sparse extent and copied-byte policy');total=sparse.sample_bytes(x);p.need(type(x.get('sparse_sample_bytes_captured')) is int and x['sparse_sample_bytes_captured']==total,'recomputed sparse texel byte count')
    rss=x.get('sparse_rss_peak_kib');p.need(isinstance(rss,list) and len(rss)==2 and all(type(v) is int and v>=0 for v in rss) and rss[1]>=rss[0],'typed sparse RSS highwater measurements');delta=rss[1]-rss[0];p.need(delta<=sparse.SPARSE_POLICY['max_rss_delta_kib'] or not x['selection_complete'] and 'rss_delta_budget' in x['truncation_reasons'],'RSS overrun cannot claim complete collection')
    attribute=next((row for row in x['textures'] if row['role']=='attribute'),None);count=0 if attribute is None else sum(item['window']['status']=='CAPTURED' for item in attribute['windows']);complete=bool(x['samples']) and result['terrain_complete'] and result['terrain_present'] and count==len(x['samples'])
    result.update(attribute_window_count=count,attribute_collection_complete=bool(complete),sparse_sample_bytes_captured=total,sparse_rss_delta_kib=delta,renderer_diagnostic_passed=result['renderer_diagnostic_passed'] and complete);result['status']='SOURCE_QUALIFIED_TERRAIN_ATTRIBUTE' if result['renderer_diagnostic_passed'] else 'INCONCLUSIVE_TERRAIN_ATTRIBUTE_RECORDED';return result

def validate_receipt(folder,reference_path,nonce):return sparse.clone(previous.validate_receipt,ENTRY=ENTRY,validate_terrain=validate_terrain)(folder,reference_path,nonce)

def authenticate_source(bundle):
    request=json.loads((ROOT/REQUEST).read_text());source=request['source_sha'];head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    p.need(os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and head==os.environ.get('GITHUB_SHA'),'fresh request attempt1')
    p.need(request.get('schema')=='sdk3-terrain-attribute-request-v1' and request.get('renderer_processes')==1 and request.get('official_model_processes')==request.get('onnx_inferences')==0,'one renderer/zero models scope')
    p.need(request.get('child_timeout_seconds')==600 and request.get('container_timeout_seconds')==630 and request.get('target_pixel')==[596,494],'measured geometry envelope and target')
    p.need(request.get('shader_limits')==LIMITS and request.get('terrain_limits')==TERRAIN_LIMITS,'fixed bounded shader and terrain observation')
    p.need(request.get('cache_policy_id')==cache.POLICY_ID and request.get('panda_shader_cxx_sha256')==cache.PANDA_SHADER_CXX_SHA256,'pinned expected-cache preprocessing policy')
    p.need(subprocess.check_output(['git','diff','--name-only',source,head],cwd=ROOT,text=True).splitlines()==[REQUEST],'request-only activation')
    delta=subprocess.check_output(['git','diff','--name-status',BASE,source],cwd=ROOT,text=True).splitlines();p.need(delta and all(x.startswith('A\t') for x in delta),'all old source/verdict bytes preserved')
    for event,key in [('push','push_ci'),('pull_request','pr_ci')]:
        run=p.api('actions/runs/'+str(request[key]));jobs=p.api('actions/runs/'+str(request[key])+'/jobs');artifacts=p.api('actions/runs/'+str(request[key])+'/artifacts')
        p.need(run['head_sha']==source and run['event']==event and run['workflow_id']==411705464 and run['run_attempt']==1 and run['conclusion']=='success' and jobs['total_count']==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(j['conclusion']=='success' for j in jobs['jobs']) and artifacts['total_count']==0,'four exact source CI jobs')
        p.write(bundle/('source-ci-'+event+'.json'),dict(run=run,jobs=jobs,artifacts=artifacts))
    p.need(request.get('sparse_policy')==sparse.SPARSE_POLICY,'bounded sparse read policy');p.write(bundle/'request.json',request);return request

def run():
    out=ROOT/'output/stage7-sdk3-terrain-attribute-01/producer';p.need(not out.exists(),'fresh output');work=out/'work';bundle=out/'bundle';work.mkdir(parents=True);bundle.mkdir();summary=dict(status='FAILED',known_renderer_processes=0,renderer_spawn_attempts=0,official_model_processes=0,onnx_inferences=0,repair_proven=False,stage7_complete=False);p.write(bundle/'summary.json',summary)
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
        summary['execution']=run_renderer('sdk3-terrain-attribute-'+os.environ['GITHUB_RUN_ID'],sdk,bundle/'renderer',['--repeat','0','--nonce',nonce],reference_path)
        path=bundle/'renderer/native-child.json'
        if path.exists():n=json.loads(path.read_text());summary.update(known_renderer_processes=int(type(n.get('pid')) is int and n['pid']>0),renderer_spawn_attempts=int(n.get('spawn_attempted') is True))
        p.write(bundle/'summary.json',summary);analysis=validate_receipt(bundle/'renderer',reference_path,nonce);p.write(bundle/'analysis.json',analysis);summary=observation_summary(summary,analysis);p.write(bundle/'summary.json',summary);print(json.dumps(summary));return summary
    except BaseException as error:summary['failure']=type(error).__name__+': '+str(error);p.write(bundle/'summary.json',summary);raise

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true',required=True);parser.parse_args();run()

if __name__=='__main__':main()
