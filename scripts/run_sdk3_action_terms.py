"""Authenticate a fresh Actions attempt and observe one official md-v3 Add per step."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bigbench import recorded_official_dependencies as deps
from bigbench import sdk3_action_terms as contract
from bigbench.full_s_receipts import bind_case_geometry, validate_trajectory
from bigbench.model_inventory import download_checked
from bigbench.recorded_official_execution import clone
from scripts import panda_sdk3_runtime as pins
from scripts import run_sdk3_four_validation as review
from scripts import run_sdk3_steering_plan as steering
from scripts import sdk3_four_validation_runtime as runtime
from scripts.run_recorded_worker_canary import handoff_evidence


authenticate = clone(steering.authenticate, c=contract)
probe = clone(steering.probe, c=contract)


def qualify_in_image(bundle, build, site, identity, seed):
    source = build/'canary'
    stock = review.read(source/'stock/report.json')
    dest = bundle/'frozen-canary'
    dest.mkdir(mode=0o777)
    dest.chmod(0o777)
    debug = dest/'debug'
    debug.mkdir()
    debug.chmod(0o777)
    shutil.copyfile(source/'fixture.onnx', dest/'fixture.onnx')
    (dest/'fixture.onnx').chmod(0o644)
    verifier = dest/'audit.py'
    shutil.copyfile(steering.ROOT/'scripts/verify_ort_node_audit.py', verifier)
    verifier.chmod(0o644)
    name = f'action-terms-canary-{identity["run_id"]}-{seed}'
    cidfile = dest/'container-id.txt'
    command = ['docker', 'run', '--rm', '--name', name, '--cidfile', str(cidfile),
               '--read-only', '--network', 'none', '--user', '65534:65534', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges', '--memory', '2g', '--memory-swap', '2g',
               '--cpus', '2', '--pids-limit', '128', '--entrypoint', '/opt/venv/bin/python']
    mounts = {verifier: '/audit.py', site: '/debug-ort',
              Path(os.environ['ACTION_TERMS_CANARY_DEPS']): '/canary-deps', dest: '/out'}
    for path, target in mounts.items():
        command += ['--mount', f'type=bind,src={path},dst={target}'+('' if path==dest else ',readonly')]
    flags = contract.DEBUG_FLAGS | {'ORT_DEBUG_NODE_IO_NAME_FILTER': 'FixtureSum', 'PYTHONDONTWRITEBYTECODE': '1'}
    for key, value in flags.items():
        command += ['--env', f'{key}={value}']
    command += [pins.IMAGE, '-I', '-S', '-B', '-c',
                "import runpy,sys; sys.path.insert(0,'/canary-deps'); runpy.run_path('/audit.py',run_name='__main__')",
                '/debug-ort', '/debug-ort', '/out', '--child', 'debug', '--site', '/debug-ort',
                '--fixture-sha256', stock['fixture_sha256']]
    pins.need(pins.inspect_container(name) is None, 'fresh canary container')
    try:
        with (dest/'stdout.log').open('xb') as out, (dest/'stderr.log').open('xb') as err:
            subprocess.run(command, stdout=out, stderr=err, timeout=110, check=True)
    finally:
        if cidfile.exists():
            container_id = cidfile.read_text().strip()
            if pins.inspect_container(container_id) is not None:
                with (dest/'remove.stdout.log').open('xb') as out, (dest/'remove.stderr.log').open('xb') as err:
                    subprocess.run(['docker', 'rm', '--force', container_id], stdout=out, stderr=err,
                                   timeout=30, check=True)
    candidate = review.read(debug/'report.json')
    hosted = review.read(source/'debug/report.json')
    pins.need(candidate['rows'] == hosted['rows'] and candidate['build'] == hosted['build']
              and len(candidate['rows']) == len(stock['rows']) == 3
              and [row['public_sha256'] for row in stock['rows']]
              == [row['public_sha256'] for row in candidate['rows']], 'exact stock public and native debug fixture parity')
    pins.write(dest/'qualification.json', dict(status='FROZEN_IMAGE_CANARY_PASSED', image=pins.IMAGE,
                                              exact_public_frames=3, native_tensors=9,
                                              official_model_processes=0, official_inferences=0))


def plan_case(work, bundle, identity, seed, scene, summary):
    gate = json.loads(os.environ['STEERING_PROBE_GATE'])
    pins.need(gate['identity'] == identity
              and [(r['seed'], r['scenario']) for r in gate['cases']] == list(contract.PROBE_CASES)
              and all(r['rate']['admitted'] for r in gate['cases']), 'fresh four-case prerequisite')
    qualification = next(r for r in gate['cases'] if (r['seed'], r['scenario']) == (seed, scene))
    pins.write(bundle/'qualified-case.json', qualification)
    site = Path(os.environ['ACTION_TERMS_DEBUG_SITE']).resolve()
    build = bundle.parent/'build'
    build_receipt = review.read(build/'runtime.json')
    pins.need(build_receipt['ort_release_commit'] == contract.ORT_COMMIT
              and build_receipt['native_libraries'] == contract.native_libraries(site)
              and build_receipt['native_libraries'], 'bound release debug runtime')
    canary = review.read(build/'canary/qualification.json')
    pins.need(canary['source_commit'] == contract.ORT_COMMIT
              and canary['exact_public_output_frames'] == canary['native_fp32_add_frames'] == 3,
              'fresh hosted CPU canary')
    sdk = review.stage_runtime(work, bundle)
    qualify_in_image(bundle, build, site, identity, seed)
    installed, descriptor = deps.stage(work)
    depfile = bundle/'model-dependencies.json'
    pins.write(depfile, descriptor)
    model = download_checked(path=pins.MODEL_ID, sha256=pins.MODEL_SHA,
                             output_dir=work/'models', max_bytes=900000000)
    pins.need(model.stat().st_size == 768750198, 'official model extent')
    native = bundle/'native'

    def command(name, repo, sdk_path, out, args, **kwargs):
        shutil.copyfile(depfile, out/depfile.name)
        shutil.copyfile(build/'runtime.json', out/'debug-runtime.json')
        argv = runtime.native_command(name, repo, sdk_path, out, args, **kwargs)
        argv[argv.index(runtime.ENTRY)] = '/work/repo/scripts/sdk3_action_terms_native.py'
        flags = ['--mount', f'type=bind,src={site},dst=/debug-ort,readonly']
        for key, value in contract.DEBUG_FLAGS.items():
            flags.extend(['--env', f'{key}={value}'])
        index = argv.index('--entrypoint')
        argv[index:index] = flags
        return argv

    args = ['--seed', str(seed), '--scenario', scene, '--source', identity['source'],
            '--activation', identity['activation'], '--run-id', identity['run_id'],
            '--dependencies-sha', pins.digest(depfile)]
    summary.update(model_process_bounds=[0,1], inference_bounds=[0,600])
    execution = clone(runtime.run_container, container_command=command, subprocess=steering.Deadline)(
        f'action-terms-{identity["run_id"]}-{seed}-{scene}', sdk, native, args, model=model, deps=installed)
    summary.update(execution=execution, **contract.modeled_activity(native, execution))
    if execution['owned_container_removed']:
        pins.write(bundle/'handoff.json', handoff_evidence(native, execution))
    pins.need(execution['returncode'] == 0 and not execution['failure'] and execution['owned_container_removed'],
              'owned runtime exited cleanly; see retained logs')
    report = review.read(native/'report.json')
    child = review.read(native/'native-child.json')
    pins.need(all(report[k] == v for k, v in identity.items()) and report['pid'] == child['pid']
              and report['child_finalized_before_server_stop'] and report['server_returncode'] == 0
              and report['provider_closed'] and report['real_session'], 'model child provenance and cleanup')
    pins.need(report['debug_runtime']['native_libraries'] == build_receipt['native_libraries'],
              'exact canary-tested debug library bytes')
    trajectory = report['trajectory']
    bind_case_geometry(trajectory, qualification)
    review.same_driver(report['driver'], qualification['driver'])
    verdict = validate_trajectory(trajectory, seed, scene)
    summary.update(traversal_passed=verdict['traversal_passed'], outcome=verdict['outcome'])
    from scripts.verify_sdk3_action_terms import verify_native
    verified = verify_native(native)
    pins.write(bundle/'verified-action-terms.json', verified)
    summary.update(status=verified['status'], captured_steps=len(verified['rows']))


def main():
    clone(steering.main, c=contract, authenticate=authenticate, probe=probe, plan_case=plan_case)()


if __name__ == '__main__':
    main()
