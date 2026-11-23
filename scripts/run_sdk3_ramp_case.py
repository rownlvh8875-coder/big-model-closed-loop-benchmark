"""Run a single frozen Linux SDK3 ramp worker in its own Docker namespace."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from bigbench.sdk3_native_ramp import CHILD_LIMIT_S, SCENES, SEEDS
from scripts.panda_sdk3_runtime import digest
from scripts.run_sdk3_benchmark_case import DOCKER, IMAGE, ROOT, SDK_SHA, mount, require, write_json
from scripts.sdk3_sidewalk_full_s import OFFICIAL_MODELS, local_memory

SEALED_SOURCES = ('bigbench/sdk3_native_ramp.py', 'scripts/sdk3_native_ramp.py',
                  'scripts/run_sdk3_ramp_case.py', 'scripts/verify_sdk3_ramps.py')


def invoke(args):
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    name = f'sdk3-ramp-{out.stat().st_ino}-{args.mode}'
    cid = out / 'container-id.txt'
    returncode = 2
    try:
        require(digest(args.sdk) == SDK_SHA, 'unexpected frozen SDK bytes')
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        require(not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT, text=True).strip(),
                'tracked benchmark source differs from the baseline')
        sources = {path: digest(ROOT / path) for path in SEALED_SOURCES}
        write_json(out / 'source.json', dict(baseline_sha=source, ramp_source_sha256=sources))
        affinity = sorted(os.sched_getaffinity(0))[:4]
        require(len(affinity) == 4, 'the measured Linux SDK3 cohort requires four available CPUs')
        cpus = ','.join(map(str, affinity))
        options = ['--read-only', '--network', 'none', '--user', f'{os.getuid()}:{os.getgid()}',
                   '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--ipc', 'private',
                   '--tmpfs', '/tmp:rw,nosuid,nodev,size=512m', '--cidfile', str(cid),
                   '--name', name, '--entrypoint', '/usr/bin/taskset']
        env = dict(HOME='/tmp', XDG_CACHE_HOME='/tmp/cache', DISPLAY=':99', LIBGL_ALWAYS_SOFTWARE='1',
                   GALLIUM_DRIVER='llvmpipe', LP_NUM_THREADS='2', MESA_SHADER_CACHE_DISABLE='true',
                   PYOPENGL_PLATFORM='glx', OMP_NUM_THREADS='2', SDK3_CANDIDATE_SHA=source)
        for key, value in env.items():
            options += ['--env', f'{key}={value}']
        options += mount(ROOT, '/work/repo') + mount(out, '/out', readonly=False)
        options += mount(args.sdk, '/opt/venv/lib/python3.11/site-packages/panda3d/libpandagl.so')
        if args.mode == 'model':
            require(args.model_file is not None and args.deps is not None and args.gate is not None,
                    'original weights, pinned ORT and full camera gate required')
            require(not subprocess.check_output([*DOCKER, 'ps', '-q', '--filter', 'name=sdk3-'], text=True).strip(),
                    'a previous SDK3 worker is still active')
            gate = json.loads(args.gate.read_bytes())
            probe_source = sources
            if gate['ramp_source_sha256'] != sources:
                archived = args.gate.parent / 'probe-source'
                probe_source = {path: digest(archived / path) for path in SEALED_SOURCES}
                unaffected = ('bigbench/sdk3_native_ramp.py', 'scripts/verify_sdk3_ramps.py')
                require(all(probe_source[key] == sources[key] for key in unaffected),
                        'ramp geometry, evaluation and camera verifier must remain identical')
            require(gate['all_cases_admitted'] is True and gate['candidate_sha'] == source
                    and gate['ramp_source_sha256'] == probe_source
                    and len(gate['cases']) == 4 and all(row['admitted'] for row in gate['cases']),
                    'all four registered ramp camera pairs must be admitted against these exact sources')
            memory = local_memory()
            write_json(out / 'host-memory.json', memory)
            require(memory['admitted'] and shutil.disk_usage(out).free >= 8 * 1024**3,
                    'host/effective RAM or disk did not meet Linux SDK3 prerequisites')
            _, expected_sha, expected_size = OFFICIAL_MODELS[args.model_id]
            require(args.model_file.stat().st_size == expected_size and digest(args.model_file) == expected_sha,
                    'official weight size or SHA-256 mismatch')
            write_json(out / 'admission.json', dict(gate_sha256=digest(args.gate), seed=args.seed,
                                                   scenario=args.scenario, weight_sha256=expected_sha,
                                                   probe_source_sha256=probe_source,
                                                   model_source_sha256=sources))
            options += mount(args.model_file, '/model.onnx') + mount(args.deps, '/model-deps')
        timeout = CHILD_LIMIT_S + 50 if args.mode == 'model' else 285
        command = ['timeout', str(timeout), *DOCKER, 'run', *options, IMAGE, '--cpu-list', cpus,
                   '/opt/venv/bin/python', '-I', '-S', '-B', '/work/repo/scripts/sdk3_native_ramp.py',
                   args.mode, '--out', '/out', '--seed', str(args.seed), '--scenario', args.scenario,
                   '--model-id', args.model_id]
        write_json(out / 'command.json', command)
        with (out / 'stdout.log').open('xb') as stdout, (out / 'stderr.log').open('xb') as stderr:
            returncode = subprocess.run(command, stdout=stdout, stderr=stderr, check=False).returncode
    except (OSError, TypeError, KeyError, ValueError, subprocess.SubprocessError) as exc:
        write_json(out / 'error.json', dict(type=type(exc).__name__, message=str(exc)))
    finally:
        if cid.is_file():
            container = cid.read_text().strip()
            if returncode in (124, 137):
                with (out / 'stop.log').open('xb') as output:
                    subprocess.run([*DOCKER, 'stop', '--time', '5', container],
                                   stdout=output, stderr=output, check=False, timeout=30)
            with (out / 'container-state.json').open('xb') as stdout, (out / 'inspect.stderr.log').open('xb') as stderr:
                subprocess.run([*DOCKER, 'inspect', '--format', '{{json .State}}', container],
                               stdout=stdout, stderr=stderr, check=False, timeout=30)
            with (out / 'remove.log').open('xb') as output:
                subprocess.run([*DOCKER, 'rm', container], stdout=output, stderr=output, check=False, timeout=30)
        (out / 'returncode.txt').write_text(f'{returncode}\n')
    return returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('probe', 'model'))
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--seed', required=True, type=int, choices=SEEDS)
    parser.add_argument('--scenario', required=True, choices=SCENES)
    parser.add_argument('--sdk', required=True, type=Path)
    parser.add_argument('--model-id', choices=OFFICIAL_MODELS, default='md-v3')
    parser.add_argument('--model-file', type=Path)
    parser.add_argument('--deps', type=Path)
    parser.add_argument('--gate', type=Path)
    return invoke(parser.parse_args())


if __name__ == '__main__':
    raise SystemExit(main())
