"""Actions-only host for the separate, one-shot steering-plan diagnostic."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bigbench import recorded_official_dependencies as deps
from bigbench import sdk3_steering_contract as c
from bigbench.full_s_receipts import bind_case_geometry, validate_trajectory
from bigbench.model_inventory import download_checked
from bigbench.recorded_official_execution import clone
from scripts import panda_sdk3_runtime as p, sdk3_four_validation_runtime as runtime
from scripts import run_sdk3_four_validation as review
from scripts.run_recorded_worker_canary import handoff_evidence

ROOT = Path(__file__).resolve().parents[1]
REPO = 'rownlvh8875-coder/big-model-closed-loop-benchmark'


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True,timeout=20).strip()


def authenticate():
    e = os.environ
    activation = git('rev-parse','HEAD')
    run_id = e['GITHUB_RUN_ID']
    p.need(e['GITHUB_ACTIONS']=='true' and e['RUNNER_ENVIRONMENT']=='github-hosted'
           and e['GITHUB_REPOSITORY']==REPO and e['GITHUB_EVENT_NAME']=='push'
           and e['GITHUB_RUN_ATTEMPT']=='1' and e['GITHUB_REF']=='refs/heads/'+c.BRANCH
           and e['GITHUB_SHA']==activation, 'fresh exact hosted Actions identity')
    run = p.api('actions/runs/'+run_id)
    p.need(str(run['id'])==run_id and run['head_sha']==activation and run['head_branch']==c.BRANCH
           and run['path']==c.WORKFLOW and run['run_attempt']==1 and run['event']=='push',
           'GitHub API confirms the immutable run identity')
    approval_commit = git('show','-s','--format=%P',activation)
    source = git('show','-s','--format=%P',approval_commit)
    p.need(git('show','-s','--format=%P',source)==c.BASE, 'fixed registered source base')
    p.need(git('diff','--name-status',source,approval_commit)=='A\t'+c.APPROVAL
           and git('diff','--name-status',approval_commit,activation)=='A\t'+c.REQUEST,
           'separate reviewed-source seal and request-only activation')
    request = json.loads((ROOT/c.REQUEST).read_text())
    approval = json.loads((ROOT/c.APPROVAL).read_text())
    p.need(request==dict(source=source,limits=c.LIMITS,mode=c.MODE)
           and approval==dict(source=source,limits=c.LIMITS,mode=c.MODE,review='OFFLINE_CONTRACT_TESTED'),
           'exact bounded request and source seal')
    context = dict(source=source,activation=activation,run_id=run_id)
    return context,run


def probe(work,bundle,identity,summary):
    sdk = review.stage_runtime(work,bundle)
    rows = []
    for seed,scene in c.PROBE_CASES:
        dest = bundle/f'{seed}-{scene}'
        runtime.run_container(f'steering-probe-{identity["run_id"]}-{seed}-{scene}',sdk,dest,
                              ['--probe','--seed',str(seed),'--scenario',scene])
        review.validate_container(dest,seed,scene,model=False)
        review.validate_child(dest,seed,scene,model=False)
        rows.append(review.validate_virtual_probe(dest,seed,scene))
    p.need(all(row['rate']['admitted'] for row in rows)
           and all(row['driver']==rows[0]['driver'] for row in rows), 'four native camera, geometry and rate gates')
    proof = dict(identity=identity,cases=rows)
    p.write(bundle/'verified-probes.json',proof)
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as out:
        out.write('qualified='+json.dumps(proof,separators=(',',':'))+'\n')
    summary.update(status='PROBE_ADMITTED',cases=4)


class Deadline:
    @staticmethod
    def run(argv,**kwargs):
        if argv[:3]==['docker','start','--attach']:
            kwargs['timeout']=9030
        return subprocess.run(argv,**kwargs)


def plan_case(work,bundle,identity,seed,scene,summary):
    gate = json.loads(os.environ['STEERING_PROBE_GATE'])
    p.need(gate['identity']==identity and [(r['seed'],r['scenario']) for r in gate['cases']]==list(c.PROBE_CASES)
           and all(r['rate']['admitted'] for r in gate['cases']), 'fresh four-case prerequisite')
    qualification = next(r for r in gate['cases'] if (r['seed'],r['scenario'])==(seed,scene))
    p.write(bundle/'qualified-case.json',qualification)
    sdk = review.stage_runtime(work,bundle)
    installed, descriptor = deps.stage(work)
    depfile = bundle/'model-dependencies.json'
    p.write(depfile,descriptor)
    model = download_checked(path=p.MODEL_ID,sha256=p.MODEL_SHA,
                             output_dir=work/'models',max_bytes=900000000)
    p.need(model.stat().st_size==768750198, 'official model extent')
    native = bundle/'native'

    def command(name,repo,sdk_path,out,args,**kwargs):
        shutil.copyfile(depfile,out/depfile.name)
        argv = runtime.native_command(name,repo,sdk_path,out,args,**kwargs)
        argv[argv.index(runtime.ENTRY)]='/work/repo/scripts/sdk3_steering_plan_native.py'
        return argv

    args = ['--seed',str(seed),'--scenario',scene,'--source',identity['source'],
            '--activation',identity['activation'],'--run-id',identity['run_id'],
            '--dependencies-sha',p.digest(depfile)]
    summary.update(model_process_bounds=[0,1],inference_bounds=[0,600])
    execution = clone(runtime.run_container,container_command=command,subprocess=Deadline)(
        f'steering-plan-{identity["run_id"]}-{seed}-{scene}',sdk,native,args,model=model,deps=installed)
    summary.update(execution=execution,**c.modeled_activity(native,execution))
    if execution['owned_container_removed']:
        p.write(bundle/'handoff.json',handoff_evidence(native,execution))
    p.need(execution['returncode']==0 and not execution['failure'] and execution['owned_container_removed'],
           'owned runtime exited cleanly; see retained logs')
    report = review.read(native/'report.json')
    child = review.read(native/'native-child.json')
    p.need(all(report[k]==v for k,v in identity.items()) and report['pid']==child['pid']
           and report['child_finalized_before_server_stop'] and report['server_returncode']==0,
           'bound model child provenance and cleanup')
    trajectory = report['trajectory']
    bind_case_geometry(trajectory,qualification)
    review.same_driver(report['driver'],qualification['driver'])
    verdict = validate_trajectory(trajectory,seed,scene)
    summary.update(traversal_passed=verdict['traversal_passed'],outcome=verdict['outcome'])
    from bigbench.sdk3_steering_collector import seal_capture_manifest
    from bigbench.sdk3_steering_receiver import receive
    selected = seal_capture_manifest(native/'report.json',native/'steering-evidence',review.read(native/'capture-ledger.json'))
    p.write(bundle/'verified-plan.json',receive(native/'report.json',native/'steering-evidence'))
    summary.update(status='CAPTURE_VERIFIED',captured_steps=len(selected))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('probe','model'))
    parser.add_argument('--seed',type=int)
    parser.add_argument('--scenario')
    args=parser.parse_args()
    p.need(args.phase=='probe' or (args.seed,args.scenario) in c.CASES,'registered phase/case')
    output=ROOT/'output'/c.OUTPUT
    output=output/('probe' if args.phase=='probe' else f'{args.seed}-{args.scenario}')
    bundle=output/'bundle'
    bundle.mkdir(parents=True)
    work=output/'work'
    work.mkdir()
    summary=dict(status='FAILED',phase=args.phase,model_process_bounds=[0,0],inference_bounds=[0,0],
                 traversal_passed=None,strict_repeat_passed=None)
    try:
        identity,run=authenticate()
        p.write(bundle/'actions-run.json',run)
        summary.update(identity)
        cgroup=subprocess.check_output(['docker','info','--format','{{.CgroupDriver}} {{.CgroupVersion}}'],text=True).strip()
        summary['docker_cgroup']=cgroup
        p.need(cgroup in ('systemd 2','cgroupfs 2'),'cgroup-v2 controller required')
        if args.phase=='probe':
            probe(work,bundle,identity,summary)
        else:
            plan_case(work,bundle,identity,args.seed,args.scenario,summary)
    except BaseException as exc:
        summary['failure']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        p.write(bundle/'summary.json',summary)


if __name__=='__main__':
    main()
