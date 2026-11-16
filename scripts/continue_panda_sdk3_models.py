"""Complete only the interrupted condition; native f3 producer files stay unchanged."""
from __future__ import annotations
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path,PurePosixPath
from zipfile import ZipFile
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk3_runtime as p
from scripts.compare_fresh_native_mdv3 import compare_fresh_trials
from scripts.aggregate_original_mdv3_current_recheck import aggregate_original_mdv3,MODEL_SHA256

ROOT=Path(__file__).resolve().parents[1]
BASE='f3bb85b6e692ecfd1efb54e2af3aabb93beb3c3e'
REQUEST='docs/requests/panda-sdk3-final-condition-20261116-04.json'
PRIOR_CASES=((20261109,'s_curve_left_right'),(20261109,'s_curve_right_left'),(20261110,'s_curve_left_right'))
MISSING=(20261110,'s_curve_right_left')
PROFILE=dict(Memory=10737418240,MemorySwap=10737418240,NanoCpus=2000000000,PidsLimit=128,ReadonlyRootfs=True,NetworkMode='none',IpcMode='private')


def validate_source_delta(rows):
    p.need(bool(rows) and all(row.startswith('A\t') for row in rows),'all f3 files must remain byte/mode unchanged')


def validate_case(folder,seed,scene):
    folder=Path(folder);pair=folder/'pair';execution=json.loads((pair/'execution.json').read_text());container=json.loads((pair/'container.json').read_text())
    p.need(execution['returncode']==0 and execution['failure'] is None and execution['owned_container_removed'] is True,'complete owned pair exit')
    state=execution['stopped_state'];p.need(state['Running'] is False and state['Pid']==0 and state['OOMKilled'] is False,'clean non-OOM pair')
    p.need(container['image']==p.IMAGE and container['id']==execution['container_id'] and container['effective_limits']==PROFILE,'identical actual model resource/image profile')
    rows=[]
    for index in (0,1):
        raw=(pair/f'run-{index}'/'run.json').read_bytes();p.need(raw==(folder/f'run_{index}.json').read_bytes(),'unchanged duplicate raw report bytes')
        value=json.loads(raw);native=json.loads((pair/f'run-{index}'/'native-child.json').read_text())
        p.need(value['model_sha256']==MODEL_SHA256 and value['selected_sdk_sha256']==p.SDK_SHA and value['sdk_load_order']=='core-first','same actual model/SDK/load order')
        p.need(value['seed']==seed and value['scenario']==scene and value['requested_steps']==value['completed_steps']==12 and value['initial_fraction']==.12,'registered complete condition')
        p.need(value['trial_evidence']=='UNMODIFIED_METADRIVE_NEW_FRAME_OFFICIAL_ONNX_DIAGNOSTIC','unmodified native trial only')
        p.need(native['spawn_attempted'] is True and type(native['pid']) is int and native['pid']>0 and native['pid']==value['process_id'] and native['returncode']==0 and native['server_returncode']==0,'actual completed native child/display')
        rows.append(value)
    verdict=compare_fresh_trials(*rows)
    p.need(json.loads((folder/'strict_native_repeat_verdict.json').read_text())==verdict,'raw independent verdict coherence')
    return dict(seed=seed,scenario=scene,container_id=execution['container_id'],verdict=verdict)


def copy_completed_cases(prior,target):
    prior=Path(prior);target=Path(target);summary=json.loads((prior/'summary.json').read_text())
    p.need(summary['source_sha']==BASE and summary['image']==p.IMAGE and summary['sdk_sha256']==p.SDK_SHA,'fixed prior native context')
    validated=[validate_case(prior/'models'/f'seed-{seed}'/scene,seed,scene) for seed,scene in PRIOR_CASES]
    p.need(len({v['container_id'] for v in validated})==3,'distinct prior case containers')
    p.need(not target.exists(),'fresh selected matrix');target.mkdir(parents=True)
    for row in validated:
        relative=Path(f"seed-{row['seed']}")/row['scenario'];shutil.copytree(prior/'models'/relative,target/relative)
    return validated


def finalize_matrix(models):
    return aggregate_original_mdv3(Path(models))


def authenticate_source(bundle):
    request=json.loads((ROOT/REQUEST).read_text());source=request['source_sha'];head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    p.need(os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and os.environ.get('GITHUB_SHA')==head,'one fresh actual activation')
    p.need(request['schema']=='sdk3-final-condition-request-v1' and request['prior_run_id']==43830776012 and request['new_model_processes']==2,'fixed continuation scope')
    p.need(subprocess.check_output(['git','diff','--name-only',source,head],cwd=ROOT,text=True).splitlines()==[REQUEST],'request-only activation')
    validate_source_delta(subprocess.check_output(['git','diff','--name-status',BASE,source],cwd=ROOT,text=True).splitlines())
    for event,key in [('push','push_ci'),('pull_request','pr_ci')]:
        run=p.api('actions/runs/'+str(request[key]));jobs=p.api('actions/runs/'+str(request[key])+'/jobs')
        p.need(run['head_sha']==source and run['event']==event and run['workflow_id']==411705464 and run['run_attempt']==1 and run['conclusion']=='success','exact new source CI')
        p.need(jobs['total_count']==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(j['conclusion']=='success' for j in jobs['jobs']),'four exact canonical jobs')
        p.write(bundle/('source-ci-'+event+'.json'),dict(run=run,jobs=jobs))
    p.write(bundle/'request.json',request);return request


def unpack_prior(archive,target):
    with ZipFile(archive) as z:
        p.need(len(z.namelist())==len(set(z.namelist())) and sum(i.file_size for i in z.infolist())<128*1024**2,'bounded unique prior carrier')
        for info in z.infolist():
            import stat
            name=PurePosixPath(info.filename);p.need(not name.is_absolute() and '..' not in name.parts and '\\' not in info.filename and not stat.S_ISLNK(info.external_attr>>16) and info.file_size<16*1024**2,'safe prior member')
        z.extractall(target)


def run():
    out=ROOT/'output/stage7-panda-sdk3-final-condition-04/producer';p.need(not out.exists(),'fresh04output')
    work=out/'work';bundle=out/'bundle';work.mkdir(parents=True);bundle.mkdir()
    summary=dict(status='FAILED',new_model_processes=0,selected_matrix_processes=0,stage7_complete=False)
    p.write(bundle/'summary.json',summary)
    try:
        request=authenticate_source(bundle);summary['source_sha']=request['source_sha']
        prior_run=p.api('actions/runs/43830776012');p.need(prior_run['workflow_id']==419847763 and prior_run['head_sha']=='1b9888f1b42b18b3b10ed66131a5c7a0b15fc00d' and prior_run['run_attempt']==1 and prior_run['status']=='completed' and prior_run['conclusion']=='cancelled','fixed interrupted03origin')
        p.write(bundle/'prior-run.json',prior_run)
        priorzip=p.artifact(work,bundle,14212471670,135298,'aed730fb9e709756c48b73d82fe88c15245306427ad526291deb3caa9344dc85',43830776012,'1b9888f1b42b18b3b10ed66131a5c7a0b15fc00d','prior-models')
        prior=bundle/'prior-models';unpack_prior(priorzip,prior)
        summary['prior_glx']=p.validate_prior_glx(prior/'prior-glx')
        rows=copy_completed_cases(prior,bundle/'models');summary['carried_cases']=[dict(seed=r['seed'],scenario=r['scenario'],strict_pass=r['verdict']['exact_repeated_execution_gate_passed'],origin_run=43830776012,origin_artifact=14212471670,origin_source=BASE) for r in rows]
        p.write(bundle/'summary.json',summary)
        print('PRIOR_THREE_CASES_VALIDATED_WITHOUT_OUTCOME_FILTERING',json.dumps(summary['carried_cases']),flush=True)
        p.need(shutil.disk_usage(work).free>=8*1024**3,'8GiB ephemeral disk required')
        imagezip=p.artifact(work,bundle,14156262448,1738137175,'47711425a5a48fb2ef0cab140da6e394516f9cbb7f04b294c5f6583d7efbc687',43700449423,'7cf0f0157f8100f0aa0e05b01a815d7395c3383f','image')
        sdkzip=p.artifact(work,bundle,14191115165,61661546,'2a44226962b3175081566918dd55eb845ac8ce1c9f9f5a396f469c8f6eca5d26',43786081196,'40dd7187ce8d3c5de510aa8c7a8ac2a6d37b0f38','sdk3')
        image=p.verify_member(imagezip,'image.tar',1727678464,'4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698',work/'image.tar')
        sdk=p.verify_member(sdkzip,'candidate/libpandagl.so.data',1052968,p.SDK_SHA,work/'libpandagl.so')
        subprocess.run(['docker','load','-i',str(image)],check=True,timeout=600)
        p.need(json.loads(subprocess.check_output(['docker','image','inspect',p.IMAGE],text=True))[0]['Id']==p.IMAGE,'same loaded image')
        mem={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines()) if k in ('MemTotal','MemAvailable')}
        summary['host_memory_before_model']=mem;p.write(bundle/'summary.json',summary);p.need(mem['MemAvailable']>=12*1024**3,'12GiB host availability required')
        from bigbench.model_inventory import download_checked
        model=download_checked(path=p.MODEL_ID,sha256=p.MODEL_SHA,output_dir=work/'models',max_bytes=900000000);p.need(model.stat().st_size==768750198,'model extent')
        deps=Path(os.environ['SDK3_MODEL_DEPS']);p.need(deps.is_dir(),'unchanged ORT dependency mount')
        seed,scene=MISSING;folder=bundle/'models'/f'seed-{seed}'/scene;dest=folder/'pair'
        print('MISSING_CONDITION_START',seed,scene,flush=True)
        execution=p.run_container('sdk3-final-'+os.environ['GITHUB_RUN_ID'],sdk,dest,['--model-pair','--seed',str(seed),'--scenario',scene],model=model,deps=deps)
        ledger=json.loads((dest/'pair-ledger.json').read_text()) if (dest/'pair-ledger.json').exists() else []
        counts=p.observed_model_processes(ledger);summary['new_model_processes']=counts['known'];summary['new_pair_execution']=execution;p.write(bundle/'summary.json',summary)
        p.need(counts==dict(known=2,upper=2,spawn_attempts=2) and execution['returncode']==0 and execution['failure'] is None,'two complete new native model children')
        raw=[json.loads((dest/f'run-{i}'/'run.json').read_text()) for i in (0,1)];verdict=compare_fresh_trials(*raw)
        for i in (0,1):(folder/f'run_{i}.json').write_bytes((dest/f'run-{i}'/'run.json').read_bytes())
        p.write(folder/'strict_native_repeat_verdict.json',verdict);validate_case(folder,seed,scene)
        aggregate=finalize_matrix(bundle/'models');p.write(bundle/'independent-model-aggregate.json',aggregate)
        summary.update(status='FOUR_CONDITION_CONTINUATION_RECOMPUTED',selected_matrix_processes=8,strict_pass_count=aggregate['strict_gate_pass_count'],strict_total=4,strict_pass=aggregate['all_four_cases_strict_native_gate_passed'],new_condition=dict(seed=seed,scenario=scene,origin_run=int(os.environ['GITHUB_RUN_ID']),origin_source=request['source_sha']),expansion_admitted=aggregate['all_four_cases_strict_native_gate_passed'])
        p.write(bundle/'summary.json',summary);print(json.dumps(summary),flush=True);return summary
    except BaseException as e:
        summary['failure']=type(e).__name__+': '+str(e);p.write(bundle/'summary.json',summary);raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true',required=True);parser.parse_args();run()

if __name__=='__main__':main()
