"""Four explicitly scoped image-loader CPU cases, never an SDK/Panda target."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _dependencies():
    global f, previous
    from scripts import panda_loader_cpu_fixture as f
    from scripts import audit_panda_provider_versions as previous
    previous._dependencies()


def _write_json(path, value):
    raw = (json.dumps(value, indent=2, allow_nan=False)+'\n').encode()
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.cpu-receipt-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            if stream.write(raw) != len(raw):
                raise OSError('short CPU receipt write')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def frozen_state():
    _dependencies()
    old, c = previous.frozen_state(), f.contract()
    raw = f.read(f.ROOT/c['prior_receipt_path'], 1024**2)
    f.need(f.sha(raw) == c['prior_receipt_sha256'], 'prior witness receipt unchanged')
    r = f.parse(raw)
    f.need(r['status'] == 'AUTHENTICATED_PROVIDER_VERSION_WITNESSES_NOT_RUNTIME' and
           r['audit_source_sha'] == c['prior_audit_source_sha'] and r['source_count'] == 318 and
           r['actions_output_origin_authenticated'] is True and r['diagnostic_witnesses_complete'] is True
           and (r['legacy_missing_count'], r['legacy_block_count'], r['witness_count'], r['unexplained_count'])
           == (110, 6, 110, 0) and r['legacy_provider_blocks_removed'] is False and
           all(r[k] is False for k in f.previous.FORBIDDEN), 'prior witness authority boundary')
    return dict(source_closure=f.source_closure(), prior_witness_sha256=f.sha(raw),
                prior_acceptance_sha256=old['prior_acceptance_sha256'], old_failure_sha256=old['old_failure_sha256'])


def verify_source(source):
    _dependencies()
    old = previous.verify_source(source)
    state = frozen_state()
    f.need({p:state['source_closure'][p] for p in old['source_closure']} == old['source_closure'],
           'source318 prefix unchanged')
    for name in set(state['source_closure'])-set(old['source_closure']):
        raw = subprocess.check_output(['git', 'show', source+':'+name], cwd=f.ROOT, timeout=10)
        f.need(f.sha(raw) == state['source_closure'][name], 'CPU source/Git bytes: '+name)
    return dict(audit_source_sha=source, **state)


def stage_loader(source, destination, pin):
    _dependencies()
    source, destination = f._canonical(source), f._canonical(destination)
    f.need(not destination.exists(), 'fresh private loader tool')
    before = source.stat()
    observed = f._loader_record(source)
    f.need(observed == dict(nbytes=pin['nbytes'], sha256=pin['sha256']), 'fixed loader bytes')
    raw = f.read(source, 1024**2)
    f.need(f.sha(raw) == pin['sha256'], 'loader bytes before private copy')
    destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    with destination.open('xb') as stream:
        f.need(stream.write(raw) == len(raw), 'full private loader copy')
        stream.flush()
        os.fsync(stream.fileno())
    destination.chmod(0o500)
    after = source.stat()
    f.need(f._loader_record(destination) == observed and
           (before.st_dev, before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
           == (after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
           'private copy/original DATA unchanged')
    return dict(observed, source_mode=before.st_mode & 0o777, private_mode=0o500)


def merge_execution_facts(result, report):
    _dependencies()
    fields = ('loader_start_attempts', 'loader_invocations_lower_bound', 'loader_invocations_upper_bound',
              'verified_fixture_entries', 'controlled_loader_failures')
    f.need(all(type(report[k]) is int and 0 <= report[k] <= 4 for k in fields), 'bounded CPU execution facts')
    attempts, lo, hi = report['loader_start_attempts'], report['loader_invocations_lower_bound'], report['loader_invocations_upper_bound']
    actual = report['loader_invocations']
    f.need(0 <= lo <= hi <= attempts <= 4 and
           (actual is None or type(actual) is int and actual == lo == hi) and
           report['verified_fixture_entries']+report['controlled_loader_failures'] <= lo and
           report['sdk_target_execution'] is False and type(report['scientific_native_runs']) is int and
           report['scientific_native_runs'] == 0, 'consistent CPU invocation bounds/no SDK authority')
    result.update({k:report[k] for k in fields})
    result['loader_invocations'] = actual


def _client(out, stop):
    token = subprocess.check_output(['gh', 'auth', 'token'], stderr=subprocess.PIPE, text=True, timeout=10).strip()
    return previous.prior.host.BuildClient(out/'api', repository=f.REPO, token=token,
        deadline=stop, max_requests=96, max_payload_bytes=64*1024**2)


def _ci(client, source, registrations):
    positive = previous.prior.a.positive
    f.need(type(registrations) is list and len(registrations) == 2 and
           all(type(r) is dict and set(r) == {'event', 'run_id'} and positive(r['run_id']) for r in registrations)
           and [r['event'] for r in registrations] == ['push', 'pull_request'], 'CPU source CI registrations')
    proofs = []
    for r in registrations:
        proofs.append({key:client.get_json('actions/runs/'+str(r['run_id'])+suffix,
                      'cpu-profile-'+r['event']+'-'+key+'.json') for key, suffix in
                      [('run', ''), ('jobs', '/jobs'), ('artifacts', '/artifacts')]})
    f.validate_ci(source, registrations, proofs)


def _image_loader_authority(client):
    cg = previous.prior.inputs
    c = cg.contract()
    _, authority, rows = cg.image_authority(f.ROOT/c['current_image_acceptance_path'])
    pin = f.contract()['loader']
    row = rows[pin['image_path']]
    f.need(row['kind'] == 'file' and row['sha256'] == pin['sha256'] and row['nbytes'] == pin['nbytes'],
           'fixed loader membership in authenticated image inventory')
    artifact_pin = previous.prior.a.IMAGE_ARTIFACT
    meta = client.get_json('actions/artifacts/'+str(artifact_pin['id']), 'image-artifact.json')
    run = meta['workflow_run']
    f.need(meta['id'] == artifact_pin['id'] and meta['name'] == artifact_pin['name'] and
           meta['size_in_bytes'] == artifact_pin['size_in_bytes'] and
           meta['digest'] == 'sha256:'+artifact_pin['sha256'] and meta['expired'] is False and
           run['id'] == artifact_pin['run_id'] and run['head_sha'] == artifact_pin['head_sha'] and
           run['repository_id'] == run['head_repository_id'] == 1447652055, 'frozen live image artifact')
    return dict(image_sha256=c['current_image_sha256'], inventory_sha256=authority['installed_manifest_sha256'],
                image_artifact_id=artifact_pin['id'], loader=pin)


def _unknown_counts(result):
    result.update(loader_start_attempts=None, loader_invocations=None, loader_invocations_lower_bound=0,
                  loader_invocations_upper_bound=4, verified_fixture_entries=None, controlled_loader_failures=None)


def _zero_counts(result):
    result.update(loader_start_attempts=0, loader_invocations=0, loader_invocations_lower_bound=0,
                  loader_invocations_upper_bound=0, verified_fixture_entries=0, controlled_loader_failures=0)


def probe(source, registrations, out, run_cpu_fixtures=False):
    out = Path(os.path.abspath(out))
    if out.resolve() != out or out.exists():
        raise ValueError('fresh canonical fixed-image CPU output')
    out.mkdir(parents=True)
    result = dict(schema='panda-loader-cpu-profile-v1', status='FAILED', audit_source_sha=source,
                  actions_output_origin_authenticated=False, fixed_image_cpu_profile_observed=False,
                  cpu_fixture_execution_requested=run_cpu_fixtures, sdk_target_execution=False,
                  scientific_native_runs=0, new_sdk_builds=0, new_workflow_activations=0,
                  artifact_downloads=0, archive_extractions=0, new_images=0,
                  execution_ledger_path='cases/ledger.json', strict_current_result='0/4 FAIL')
    for flag in ('native_admitted', 'stage7_complete', 'full_object_abi_qualified',
                 'full_dependency_closure_qualified', 'previous_abort_fixed', 'candidate_installed',
                 'runtime_mapping_qualified', 'external_build_origin_authenticated'):
        result[flag] = False
    _unknown_counts(result)
    _write_json(out/'acceptance.json', result)
    initial = dict(result)
    runner_entered, report = False, None
    try:
        _dependencies()
        f.need(run_cpu_fixtures is True, 'explicit CPU fixture execution flag required')
        stop = time.monotonic()+f.contract()['whole_seconds']
        with previous.prior._absolute_deadline(stop):
            state = verify_source(source)
            c = f.contract()
            f.need(out == f.ROOT/c['actual_output_path'], 'one fixed actual output; no alternate-path retry')
            _write_json(out/'source-closure.json', state)
            client = _client(out, stop)
            _ci(client, source, registrations)
            previous.prior.authenticate_producer(client)
            image = _image_loader_authority(client)
            original = f.ROOT/c['loader']['retained_path']
            private = out/'work/image-loader'
            staged = stage_loader(original, private, c['loader'])
            _write_json(out/'loader-authority.json', dict(image=image, copy=staged))
            fixture = out/'work/fixture'
            manifest = f.build_fixture(fixture)
            _write_json(out/'fixture-manifest.json', manifest)
            runner_entered = True
            report = f.run_cases(private, fixture, manifest, out/'cases')
            merge_execution_facts(result, report)
            f.need(report['status'] == 'FOUR_CPU_LOADER_VERSION_CASES_OBSERVED_NOT_SDK_RUNTIME' and
                   report['loader_start_attempts'] == report['loader_invocations'] == 4 and
                   report['verified_fixture_entries'] == report['controlled_loader_failures'] == 2 and
                   [r['case'] for r in report['cases']] == list(f.CASES), 'four exact CPU case observations')
            f.need(verify_source(source) == state and f._record(original) == f._record(private) ==
                   dict(nbytes=c['loader']['nbytes'], sha256=c['loader']['sha256']), 'final source/receipts/loader DATA bytes')
            f.validate_fixture(fixture, manifest)
            result.update(status='FOUR_CPU_LOADER_VERSION_CASES_OBSERVED_NOT_SDK_RUNTIME',
                actions_output_origin_authenticated=True, fixed_image_cpu_profile_observed=True,
                source_count=322, image=image, loader_copy=staged, audit_ci=registrations,
                prior_witness_sha256=state['prior_witness_sha256'], prior_acceptance_sha256=state['prior_acceptance_sha256'],
                old_failure_sha256=state['old_failure_sha256'])
    except BaseException as error:
        result.update(status='FAILED', actions_output_origin_authenticated=False, fixed_image_cpu_profile_observed=False,
                      failure=(type(error).__name__+': '+str(error))[:4096])
        if not runner_entered:
            _zero_counts(result)
        else:
            try:
                if report is None:
                    report = f.parse(f.read(out/'cases/ledger.json', 1024**2))
                merge_execution_facts(result, report)
            except BaseException:
                _unknown_counts(result)
    try:
        _write_json(out/'acceptance.json', result)
    except BaseException:
        return initial
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--push-ci', type=int, required=True)
    parser.add_argument('--pr-ci', type=int, required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--run-cpu-fixtures', action='store_true')
    args = parser.parse_args()
    result = probe(args.source, [dict(event='push', run_id=args.push_ci),
                   dict(event='pull_request', run_id=args.pr_ci)], args.out, args.run_cpu_fixtures)
    print(json.dumps({k:result[k] for k in ('status', 'loader_invocations', 'sdk_target_execution')}))
    return 0 if result['fixed_image_cpu_profile_observed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
