"""One authenticated SDK3 control or full12 CPU-retention pair per hosted job."""
from __future__ import annotations
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk3_runtime as p
from scripts.sdk3_rgb_forensics import analyze_pair,SEED,SCENE
from scripts.continue_panda_sdk3_models import PROFILE,unpack_prior

ROOT=Path(__file__).resolve().parents[1]
BASE='46b750e6ad8d311b903c1104f12160779ce5806e'
REQUEST='docs/requests/sdk3-rgb-forensics-20261116-01.json'
MODIFIED={'scripts/native_mdv3_repeat_trial.py','scripts/panda_sdk3_diagnostic.py'}


def validate_source_delta(rows):
    p.need(bool(rows) and all(row.startswith('A\t') or row.startswith('M\t') and row[2:] in MODIFIED for row in rows),'only declared optional observer dispatch extensions')


def validate_observed_pair(folder,arm):
    pair=Path(folder)/'pair';execution=json.loads((pair/'execution.json').read_text());container=json.loads((pair/'container.json').read_text())
    p.need(execution.get('returncode')==0 and execution.get('failure') is None and execution.get('owned_container_removed') is True and execution.get('ownership_unresolved') is False,'complete owned diagnostic pair')
    state=execution.get('stopped_state',{});p.need(state.get('Running') is False and state.get('Pid')==0 and state.get('OOMKilled') is False and state.get('ExitCode')==0,'clean non-OOM diagnostic exit')
    p.need(container.get('image')==p.IMAGE and container.get('id')==execution.get('container_id') and container.get('effective_limits')==PROFILE,'same authenticated image/resource profile')
    command=json.loads((pair/'command.json').read_text())['argv'];p.need(('--full-rgb' in command)==(arm=='full_rgb'),'actual command/probe arm binding')
    ledger=json.loads((pair/'pair-ledger.json').read_text());p.need(len(ledger)==2 and [row.get('index') for row in ledger]==[0,1] and p.observed_model_processes(ledger)==dict(known=2,upper=2,spawn_attempts=2) and all(row.get('returncode')==0 for row in ledger),'two actual completed model launches')
    for index in (0,1):
        native=json.loads((pair/f'run-{index}'/'native-child.json').read_text());trial=json.loads((pair/f'run-{index}'/'run.json').read_text())
        p.need(native.get('spawn_attempted') is True and type(native.get('pid')) is int and native['pid']>0 and native['pid']==ledger[index]['pid']==trial.get('process_id') and native.get('returncode')==native.get('server_returncode')==0,'actual clean native/display completion')
    return analyze_pair(Path(folder),arm)


def authenticate_source(bundle):
    request=json.loads((ROOT/REQUEST).read_text());source=request['source_sha'];head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    p.need(os.environ.get('GITHUB_RUN_ATTEMPT')=='1' and os.environ.get('GITHUB_SHA')==head,'fresh single diagnostic activation')
    p.need(request.get('schema')=='sdk3-rgb-forensics-request-v1' and request.get('arms')==['control','full_rgb'] and request.get('native_models_max')==4 and request.get('seed')==SEED and request.get('scenario')==SCENE,'fixed four-child/two-arm scope')
    p.need(subprocess.check_output(['git','diff','--name-only',source,head],cwd=ROOT,text=True).splitlines()==[REQUEST],'request-only diagnostic activation')
    validate_source_delta(subprocess.check_output(['git','diff','--name-status',BASE,source],cwd=ROOT,text=True).splitlines())
    for event,key in [('push','push_ci'),('pull_request','pr_ci')]:
        run=p.api('actions/runs/'+str(request[key]));jobs=p.api('actions/runs/'+str(request[key])+'/jobs');artifacts=p.api('actions/runs/'+str(request[key])+'/artifacts')
        p.need(run['head_sha']==source and run['event']==event and run['workflow_id']==411705464 and run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='success','exact source canonical CI')
        p.need(jobs['total_count']==2 and {j['name'] for j in jobs['jobs']}=={'synthetic-unit','onnx-interface-test'} and all(j['conclusion']=='success' for j in jobs['jobs']) and artifacts['total_count']==0,'four canonical source jobs;no artifacts')
        p.write(bundle/('source-ci-'+event+'.json'),dict(run=run,jobs=jobs,artifacts=artifacts))
    p.write(bundle/'request.json',request);return request


def run(arm):
    p.need(arm in ('control','full_rgb'),'registered hosted diagnostic arm')
    out=ROOT/'output/stage7-sdk3-rgb-forensics-01'/arm/'producer';p.need(not out.exists(),'fresh diagnostic output')
    work=out/'work';bundle=out/'bundle';work.mkdir(parents=True);bundle.mkdir()
    summary=dict(status='FAILED',arm=arm,known_native_model_processes=0,repair_proven=False,stage7_complete=False,original_matrix_passed=3,original_matrix_total=4,original_matrix_gate_passed=False)
    p.write(bundle/'summary.json',summary)
    try:
        request=authenticate_source(bundle);summary['source_sha']=request['source_sha'];p.write(bundle/'summary.json',summary)
        prior_run=p.api('actions/runs/43845729539');p.need(prior_run['workflow_id']==419974420 and prior_run['head_sha']=='1573e07218dc5153f168f504592f1f87e4922579' and prior_run['run_attempt']==1 and prior_run['status']=='completed' and prior_run['conclusion']=='success','actual04carrier origin')
        p.write(bundle/'prior-run.json',prior_run)
        zip_path=p.artifact(work,bundle,14216386095,291036,'657c03078b4670a892ae8f52e81fec9067e625cb7003a4d725c9cb72f08f193c',43845729539,'1573e07218dc5153f168f504592f1f87e4922579','prior04')
        prior=bundle/'prior04';unpack_prior(zip_path,prior);summary['selected_glx']=p.validate_prior_glx(prior/'prior-models'/'prior-glx')
        gate=json.loads((prior/'independent-model-aggregate.json').read_text());p.need(gate['strict_gate_pass_count']==3 and gate['all_four_cases_strict_native_gate_passed'] is False,'preserve failed original matrix')
        p.need(shutil.disk_usage(work).free>=8*1024**3,'8GiB ephemeral staging disk')
        iz=p.artifact(work,bundle,14156262448,1738137175,'47711425a5a48fb2ef0cab140da6e394516f9cbb7f04b294c5f6583d7efbc687',43700449423,'7cf0f0157f8100f0aa0e05b01a815d7395c3383f','image')
        sz=p.artifact(work,bundle,14191115165,61661546,'2a44226962b3175081566918dd55eb845ac8ce1c9f9f5a396f469c8f6eca5d26',43786081196,'40dd7187ce8d3c5de510aa8c7a8ac2a6d37b0f38','sdk3')
        image=p.verify_member(iz,'image.tar',1727678464,'4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698',work/'image.tar')
        sdk=p.verify_member(sz,'candidate/libpandagl.so.data',1052968,p.SDK_SHA,work/'libpandagl.so')
        subprocess.run(['docker','load','-i',str(image)],check=True,timeout=600)
        p.need(json.loads(subprocess.check_output(['docker','image','inspect',p.IMAGE],text=True))[0]['Id']==p.IMAGE,'same immutable image config')
        mem={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines()) if k in ('MemTotal','MemAvailable')}
        summary['host_memory_before_model']=mem;p.write(bundle/'summary.json',summary);p.need(mem['MemAvailable']>=12*1024**3,'12GiB host memory available')
        from bigbench.model_inventory import download_checked
        model=download_checked(path=p.MODEL_ID,sha256=p.MODEL_SHA,output_dir=work/'models',max_bytes=900000000);p.need(model.stat().st_size==768750198,'official model extent')
        deps=Path(os.environ['SDK3_MODEL_DEPS']);p.need(deps.is_dir(),'pinned ORT dependency mount')
        args=['--model-pair','--seed',str(SEED),'--scenario',SCENE]+(['--full-rgb'] if arm=='full_rgb' else [])
        print('SDK3_RGB_DIAGNOSTIC_PAIR_START',arm,SEED,SCENE,flush=True)
        execution=p.run_container('sdk3-rgb-'+os.environ['GITHUB_RUN_ID']+'-'+arm,sdk,bundle/'pair',args,model=model,deps=deps)
        native_files=list((bundle/'pair').glob('run-*/native-child.json'));summary['known_native_model_processes']=sum(type(json.loads(path.read_text()).get('pid')) is int for path in native_files);summary['execution']=execution;p.write(bundle/'summary.json',summary)
        analysis=validate_observed_pair(bundle,arm);p.write(bundle/'analysis.json',analysis)
        summary.update(status='DIAGNOSTIC_PAIR_RECOMPUTED',strict_pair_pass=analysis['strict_pair_pass'],first_raw_source_diff_step=analysis['first_raw_source_diff_step'],new_native_model_processes=2)
        p.write(bundle/'summary.json',summary);print(json.dumps(summary),flush=True);return summary
    except BaseException as error:
        summary['failure']=type(error).__name__+': '+str(error);p.write(bundle/'summary.json',summary);raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true',required=True);parser.add_argument('--arm',choices=('control','full_rgb'),required=True);args=parser.parse_args();run(args.arm)

if __name__=='__main__':main()
