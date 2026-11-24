"""Run one owned benchmark case in the locally loaded frozen SDK3 image."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from bigbench.benchmark_results import LONGITUDINAL_CASES, SDK_SHA, read, verify_input_files
from bigbench.sdk3_radius45 import TIGHT_FULL_S_CASE
from bigbench.full_s_validation import registered_case
from scripts.panda_sdk3_runtime import digest
from scripts.sdk3_sidewalk_full_s import OFFICIAL_MODELS, local_memory

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'sha256:b9d673de93f1857e4dfa5ed6a48330d568ef96fce7f3cc975f0c688877e6e26e'
DOCKER = ('docker','--host=unix:///var/run/docker.sock')


def require(condition, why):
    if not condition:
        raise ValueError(why)


def write_json(path, value):
    with path.open('x') as output:
        json.dump(value,output,indent=2,allow_nan=False)
        output.write('\n')


def camera_gate(track, paths, seed, scene):
    require(len(paths)==2 and paths[0].resolve()!=paths[1].resolve(),'two distinct probe outputs required')
    parents = []
    nonces = set()
    containers = set()
    for path in paths:
        doc = read(path/'report.json')
        owner = read(path/'native-child.json')
        require((doc['seed'],doc['scenario'])==(seed,scene) and doc['status']=='RETURNED'
                and doc['provider_closed'] and doc['official_model_process_bounds']==[0,0]
                and doc['official_inference_bounds']==[0,0] and not doc['ort_imported']
                and doc['sdk_sha256']==SDK_SHA and doc['child_finalized_before_server_stop']
                and owner['pid']==doc['pid'] and owner['returncode']==0,
                'need a successful, reaped model-free probe for the registered case')
        nonces.add(doc['nonce'])
        containers.add((path/'container-id.txt').read_text().strip())
        if track=='lateral':
            require(doc['rate']['admitted'] and doc['ordering']['state_restored']
                    and doc['ordering']['original_active_bins_restored'],'restored admitted lateral camera')
            rows = [row['hashes'] for row in doc['probe_rows']]
            require(len(rows)==4,'expected the full four-pose lateral camera probe')
        else:
            require(doc['admission']['admitted'] and doc['actor_closed'],'closed admitted longitudinal camera')
            rows = read(path/'input-rows.json')
            require(len(rows)==2,'expected two native lead camera poses')
        verify_input_files(path, rows[0])
        parents.append(dict(geometry=doc['geometry'],intrinsics=doc['intrinsics'],driver=doc['driver'],
                            input_variant=doc['input_variant'], rows=rows))
    require(len(nonces)==len(containers)==2 and '' not in containers,'distinct owned native probes required')
    require(parents[0]==parents[1],'camera admission found a real difference across independent probes')
    return parents[0]


def mount(path, destination, *, readonly=True):
    path = str(path.resolve())
    require(',' not in path,'container bind paths cannot contain a comma')
    return ['--mount',f'type=bind,src={path},dst={destination}'+(',readonly' if readonly else '')]


def invoke(args):
    out = args.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    owned = False
    name = f'sdk3-benchmark-{out.stat().st_ino}-{args.track}-{args.mode}'
    rc = 2
    try:
        geometry_track = 'lateral' if args.track == 'integrated' else args.track
        case = (args.seed, args.scenario)
        integrated = args.track == 'integrated'
        admitted = (registered_case(*case, integrated=integrated) if geometry_track == 'lateral'
                    else args.scenario in LONGITUDINAL_CASES)
        require(admitted, 'unregistered benchmark scenario')
        require(digest(args.sdk)==SDK_SHA,'unexpected frozen SDK bytes')
        source = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        require(not subprocess.check_output(['git','status','--porcelain=v1'],cwd=ROOT,text=True).strip(),
                'runner requires a clean committed source checkout')
        affinity = sorted(os.sched_getaffinity(0))[:4]
        require(len(affinity)==4,'need the same four-CPU affinity as the measured SDK3 cohort')
        cpus = ','.join(map(str,affinity))
        (out/'cpu-affinity.txt').write_text(cpus+'\n')
        options = ['--read-only','--network','none','--user',f'{os.getuid()}:{os.getgid()}',
                   '--cap-drop','ALL','--security-opt','no-new-privileges','--ipc','private',
                   '--tmpfs','/tmp:rw,nosuid,nodev,size=512m','--cidfile',str(out/'container-id.txt'),
                   '--name',name,'--entrypoint','/usr/bin/taskset']
        env = dict(HOME='/tmp',XDG_CACHE_HOME='/tmp/cache',DISPLAY=':99',LIBGL_ALWAYS_SOFTWARE='1',
                   GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',MESA_SHADER_CACHE_DISABLE='true',
                   PYOPENGL_PLATFORM='glx',OMP_NUM_THREADS='2',SDK3_CANDIDATE_SHA=source)
        for key,value in env.items():
            options += ['--env',f'{key}={value}']
        options += mount(ROOT,'/work/repo')+mount(out,'/out',readonly=False)
        options += mount(args.sdk,'/opt/venv/lib/python3.11/site-packages/panda3d/libpandagl.so')
        if args.mode=='model':
            require(args.model_file is not None and args.deps is not None,'model weights and pinned ORT directory required')
            require(not subprocess.check_output([*DOCKER,'ps','-q','--filter','name=sdk3-'],text=True).strip(),
                    'a previous SDK3 container still owns the model slot')
            memory = local_memory()
            write_json(out/'host-memory.json',memory)
            require(memory['admitted'] and shutil.disk_usage(out).free>=8*1024**3,
                    'host/effective RAM or disk did not meet SDK3 prerequisites')
            _,expected_sha,expected_size = OFFICIAL_MODELS[args.model_id]
            require(args.model_file.stat().st_size==expected_size and digest(args.model_file)==expected_sha,
                    'official weight size or SHA-256 mismatch')
            if case == TIGHT_FULL_S_CASE:
                # The identity check filled the host read cache. Release those pages before
                # Docker creates its VFS copy. The native worker still checks the original RAM gate.
                with args.model_file.open('rb') as weights:
                    os.posix_fadvise(weights.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
            admission = camera_gate(geometry_track,args.probe,args.seed,args.scenario)
            write_json(out/'camera-admission.json',admission)
            options += mount(args.model_file,'/model.onnx')+mount(args.deps,'/model-deps')
        launch = 'sdk3_sidewalk_full_s.py' if geometry_track=='lateral' else 'sdk3_longitudinal_campaign.py'
        mode = 'pair' if geometry_track=='lateral' and args.mode=='model' else args.mode
        seconds = 18120 if mode=='pair' else (9050 if mode=='model' else 280)
        command = ['timeout',str(seconds),*DOCKER,'run',*options,IMAGE,'--cpu-list',cpus,
                   '/opt/venv/bin/python','-I','-S','-B',f'/work/repo/scripts/{launch}',mode,
                   '--out','/out','--seed',str(args.seed),'--scenario',args.scenario,'--model-id',args.model_id]
        if integrated and (args.mode == 'model' or case == TIGHT_FULL_S_CASE):
            command.append('--integrated')
        write_json(out/'command.json',command)
        with (out/'stdout.log').open('xb') as stdout,(out/'stderr.log').open('xb') as stderr:
            rc = subprocess.run(command,stdout=stdout,stderr=stderr,check=False).returncode
        owned = (out/'container-id.txt').is_file()
    except (OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError) as error:
        write_json(out/'error.json',dict(type=type(error).__name__,message=str(error)))
    finally:
        (out/'returncode.txt').write_text(str(rc)+'\n')
        if owned:
            container = (out/'container-id.txt').read_text().strip()
            if rc==124:
                with (out/'stop.log').open('xb') as output:
                    subprocess.run([*DOCKER,'stop','--time','5',container],stdout=output,stderr=output,check=False)
            with (out/'container-state.json').open('xb') as stdout,(out/'inspect.stderr.log').open('xb') as stderr:
                subprocess.run([*DOCKER,'inspect','--format','{{json .State}}',container],
                               stdout=stdout,stderr=stderr,check=False)
            with (out/'remove.log').open('xb') as output:
                subprocess.run([*DOCKER,'rm',container],stdout=output,stderr=output,check=False)
    return rc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('track',choices=('lateral','longitudinal','integrated'))
    parser.add_argument('mode',choices=('probe','model'))
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--seed',choices=(20261109,20261110),required=True,type=int)
    parser.add_argument('--scenario',required=True)
    parser.add_argument('--sdk',required=True,type=Path)
    parser.add_argument('--model-file',type=Path)
    parser.add_argument('--model-id',choices=OFFICIAL_MODELS,default='md-v3')
    parser.add_argument('--deps',type=Path)
    parser.add_argument('--probe',type=Path,action='append',default=[])
    return invoke(parser.parse_args(argv))


if __name__=='__main__':
    raise SystemExit(main())
