"""Separate read-only acceptance of one retained SDK3 DATA carrier. Never run it."""
import argparse
import base64
import hashlib
import json
import os
import stat
import subprocess
import sys
import time
import zipfile
from pathlib import Path

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk_cg_runpath_json as j
from scripts import panda_sdk_cg_runpath_policy as a
from scripts import panda_sdk_cg_runpath_carrier as carrier
from scripts import accept_panda_sdk_cg_runpath as legacy
from scripts import produce_panda_sdk_cg_runpath as host
from scripts import panda_sdk_cg_runpath_evidence as evidence
from scripts import panda_sdk_cg_runpath_gate as gate
from scripts import panda_sdk_cg_inputs as inputs
from scripts import panda_sdk_link_image as image
from scripts.engine_clock_image_transport import _absolute_deadline


def frozen_state():
    c = j.contract()
    closure = j.source_closure()
    raw = j.read(j.ROOT / c['old_failure_path'], 1024**2)
    j.need(j.sha(raw) == c['old_failure_sha256'] and j.parse(raw)['status'] == 'FAILED',
           'original failed receiver receipt unchanged')
    return dict(source_closure=closure, old_failure_sha256=j.sha(raw))


def verify_audit_source(source):
    j.need(a.hexstr(source, 40), 'exact audit source SHA')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=j.ROOT, timeout=10).decode().strip()
    j.need(head == source, 'audit source is current HEAD')
    state = frozen_state()
    for name, digest in state['source_closure'].items():
        raw = subprocess.check_output(['git', 'show', source + ':' + name], cwd=j.ROOT, timeout=10)
        j.need(j.sha(raw) == digest, 'working DATA matches audit source: ' + name)
    return dict(audit_source_sha=source, **state)


def authenticate_producer(client):
    pin = j.contract()['producer']
    meta = client.get_json('contents/' + a.REQUEST + '?ref=' + pin['activation_sha'], 'request-content.json')
    j.need(meta['type'] == 'file' and meta['encoding'] == 'base64', 'original request contents')
    raw = base64.b64decode(meta['content'], validate=False)
    request = a.parse(raw)
    a.validate_request(request, a.ROOT)
    j.need(request['source_sha'] == pin['source_sha'] and j.sha(raw) == pin['request_sha256'],
           'fixed original source/request')
    context = dict(repository=a.REPO, head_sha=pin['activation_sha'], run_id=pin['run_id'],
                   attempt=pin['run_attempt'], event='push', actor=a.OWNER)
    run = host.authenticate_context(client, request, context, raw, completed=True)
    j.need(run['id'] == pin['run_id'] and run['workflow_id'] == pin['workflow_id'] and
           type(run['run_attempt']) is int and run['run_attempt'] == pin['run_attempt'] and
           run['conclusion'] == 'success', 'fixed successful SDK3 run')
    jobs = client.get_json('actions/runs/' + str(pin['run_id']) + '/jobs', 'build-jobs.json')
    j.need(jobs['total_count'] == len(jobs['jobs']) == 1, 'one original build job')
    job = jobs['jobs'][0]
    j.need(job['id'] == pin['job_id'] and job['name'] == 'build' and
           job['run_id'] == pin['run_id'] and job['head_sha'] == pin['activation_sha'] and
           job['head_branch'] == a.BRANCH and type(job['run_attempt']) is int and
           job['run_attempt'] == 1 and job['status'] == 'completed' and
           job['conclusion'] == 'success', 'fixed successful SDK3 job')
    artifact = a.validate_artifact(run, client.get_json(
        'actions/runs/' + str(pin['run_id']) + '/artifacts', 'artifacts.json'))
    j.need(artifact['id'] == pin['artifact_id'] and
           artifact['size_in_bytes'] == pin['artifact_zip_nbytes'] and
           artifact['digest'] == 'sha256:' + pin['artifact_zip_sha256'], 'fixed SDK3 artifact')
    return dict(request=request, raw_request=raw, run=run, job=job, artifact=artifact)


def _canonical(path, directory=False):
    path = Path(os.path.abspath(path))
    j.need(path.resolve() == path and not path.is_symlink(), 'canonical retained DATA path')
    if directory:
        j.need(path.is_dir(), 'retained DATA directory missing')
    return path


def _hash_file(path, limit):
    path = _canonical(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            j.need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
                   0 <= before.st_size <= limit, 'regular bounded retained DATA')
            digest, count = hashlib.sha256(), 0
            for block in iter(lambda: stream.read(1024**2), b''):
                count += len(block)
                j.need(count <= limit, 'retained DATA extent')
                digest.update(block)
            j.need(count == before.st_size and carrier.signature(before) ==
                   carrier.signature(os.fstat(stream.fileno())) == carrier.signature(path.lstat()),
                   'retained DATA changed')
            return dict(nbytes=count, sha256=digest.hexdigest())
    except OSError as error:
        raise ValueError('retained regular DATA unavailable') from error


def verify_zip_files(zip_path, candidate, pin):
    """Verify transport bytes without extracting, executing or granting origin."""
    zip_path, candidate = _canonical(zip_path), _canonical(candidate, directory=True)
    expected = dict(nbytes=pin['artifact_zip_nbytes'], sha256=pin['artifact_zip_sha256'])
    j.need(_hash_file(zip_path, carrier.MAX_ZIP) == expected, 'retained ZIP identity')
    actual = set()
    parents = {str(Path(name).parent) for name in carrier.FILES}
    for path in candidate.rglob('*'):
        j.need(not path.is_symlink() and path.resolve() == path, 'retained member alias')
        name = str(path.relative_to(candidate))
        if path.is_dir():
            j.need(name in parents, 'extra retained directory')
        else:
            j.need(name in carrier.FILES, 'extra retained file')
            actual.add(name)
    j.need(actual == carrier.FILES, 'exact retained 23 files')
    files = {}
    with zip_path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        names = carrier._preflight(stream, before.st_size)
        j.need(names - carrier.DIRS == carrier.FILES, 'exact ZIP 23 files')
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            rows = archive.infolist()
            j.need(len(rows) == len(names) and {row.filename for row in rows} == names,
                   'ZIP directory binding')
            for row in rows:
                if row.filename in carrier.DIRS:
                    j.need(row.is_dir() and row.file_size == 0, 'empty ZIP directory')
                    continue
                digest, count = hashlib.sha256(), 0
                with archive.open(row) as member:
                    for block in iter(lambda: member.read(1024**2), b''):
                        count += len(block)
                        j.need(count <= row.file_size <= carrier.FILE_LIMITS[row.filename],
                               'bounded ZIP member')
                        digest.update(block)
                observed = dict(nbytes=count, sha256=digest.hexdigest())
                j.need(count == row.file_size and observed == _hash_file(
                    candidate / row.filename, carrier.FILE_LIMITS[row.filename]),
                    'ZIP/retained member bytes: ' + row.filename)
                files[row.filename] = observed
        j.need(carrier.signature(before) == carrier.signature(os.fstat(stream.fileno())) ==
               carrier.signature(zip_path.lstat()), 'ZIP changed during verification')
    j.need(_hash_file(zip_path, carrier.MAX_ZIP) == expected, 'ZIP identity recheck')
    j.need(sum(v['nbytes'] for k, v in files.items() if k.startswith('logs/')) <= 32*1024**2,
           'combined log bound')
    return dict(files=files, **expected, native_admitted=False, extracted_files=0)


def verify_cached_carrier(zip_path, candidate):
    return verify_zip_files(zip_path, candidate, j.contract()['producer'])


def provider_paths(inventory_document, cache):
    cache = _canonical(cache, directory=True)
    inventory = image.Inventory(inventory_document)
    paths, checked = {}, {}
    for logical, row in inventory.rows.items():
        if row['kind'] != 'file':
            continue
        path = cache / (row['sha256'] + '.elf.data')
        if not path.exists() and not path.is_symlink():
            continue
        if row['sha256'] not in checked:
            checked[row['sha256']] = _hash_file(path, 64*1024**2)
        j.need(checked[row['sha256']] == dict(nbytes=row['nbytes'], sha256=row['sha256']),
               'provider bytes/immutable inventory')
        paths[logical] = path
    j.need(paths, 'retained provider cache missing')
    return paths


def _independent_reports(candidate, receipt, recomputed):
    def report(name):
        return j.parse(j.read(candidate / ('reports/' + name + '.json'), 16*1024**2))
    j.validate_reported_gate(report('gate'), recomputed, report('provider-audit'),
                             report('loader-metadata'))
    configuration = report('configuration')
    j.need(configuration == receipt['compiler_build']['configuration'], 'configuration binding')
    j.need(report('effective-configuration') == receipt['compiler_build']['effective_configuration'],
           'effective configuration binding')
    j.need(report('configuration-delta') == host.builder.configuration_delta(configuration),
           'independent macro delta')
    extraction = gate.previous.literal.extract_literal(j.read(
        candidate / 'candidate/layout-contract.o.data', 1024**2))
    extraction.pop('raw')
    j.need(extraction == report('layout-extraction'), 'independent descriptor extraction')


def audit(source, registrations, out):
    out = Path(os.path.abspath(out))
    j.need(out.resolve() == out and not out.exists(), 'fresh canonical JSON audit output')
    out.mkdir(parents=True)
    result = dict(schema='panda-sdk-cg-runpath-json-acceptance-v1', status='FAILED',
                  audit_source_sha=source, actions_output_origin_authenticated=False,
                  selected_static_accepted=False, old_receiver_verdict_changed=False,
                  new_sdk_builds=0, new_workflow_activations=0, artifact_downloads=0,
                  image_operations=0, target_execution=False, scientific_native_runs=0,
                  native_admitted=False, stage7_complete=False,
                  source_observer_default_off_observed=None, strict_current_result='0/4 FAIL')
    for key in j.FORBIDDEN:
        result[key] = False
    a.write(out / 'acceptance.json', result)
    try:
        stop = time.monotonic() + j.contract()['audit_seconds']
        with _absolute_deadline(stop):
            state = verify_audit_source(source)
            a.write(out / 'source-closure.json', state)
            token = subprocess.check_output(['gh', 'auth', 'token'], stderr=subprocess.PIPE,
                                            text=True, timeout=10).strip()
            client = host.BuildClient(out / 'api', repository=j.REPO, token=token, deadline=stop,
                                      max_requests=96, max_payload_bytes=64*1024**2)
            proofs = []
            j.need(type(registrations) is list and len(registrations) == 2, 'audit CI registrations')
            for registration in registrations:
                rid = registration['run_id']
                j.need(a.positive(rid), 'positive audit CI run')
                proofs.append({key: client.get_json('actions/runs/' + str(rid) + suffix,
                    'audit-' + registration['event'] + '-' + key + '.json')
                    for key, suffix in [('run', ''), ('jobs', '/jobs'), ('artifacts', '/artifacts')]})
            j.validate_audit_ci(source, registrations, proofs)
            producer = authenticate_producer(client)
            c, pin = j.contract(), j.contract()['producer']
            zip_path, candidate = j.ROOT / c['retained_zip'], j.ROOT / c['retained_candidate']
            transport = verify_cached_carrier(zip_path, candidate)
            receipt = j.parse(j.read(candidate / 'reports/receipt.json', 16*1024**2))
            semantics = legacy.validate_receipt(receipt, transport['files'], pin['source_sha'],
                pin['activation_sha'], pin['run_id'], pin['request_sha256'])
            j.need(semantics['static_passed'], 'original selected static carrier')
            coherence = evidence.validate_build_evidence(receipt, candidate)
            a.write(out / 'independent-build-evidence.json', coherence)
            ic = inputs.contract()
            inputs.image_authority(j.ROOT / ic['current_image_acceptance_path'])
            inventory = j.parse(j.read(j.ROOT / inputs.INVENTORY, 16*1024**2))
            paths = provider_paths(inventory, j.ROOT / c['retained_providers'])
            recomputed = gate.audit_candidate(candidate / 'candidate/libpandagl.so.data',
                candidate / 'candidate/layout-contract.o.data', candidate / 'candidate/layout-descriptor.data',
                candidate / 'candidate/build-libpanda.so.data', receipt['compiler_build'], paths)
            _independent_reports(candidate, receipt, recomputed)
            j.need(verify_cached_carrier(zip_path, candidate) == transport and
                   verify_audit_source(source) == state, 'final DATA/source/failure recheck')
            a.write(out / 'independent-static-gate.json', recomputed)
            result.update(status='AUTHENTICATED_CG_RUNPATH_JSON_SELECTED_STATIC_ACCEPTED_NOT_RUNTIME',
                          selected_static_accepted=True, actions_output_origin_authenticated=True,
                          producer=pin, audit_ci=registrations, source_count=len(state['source_closure']),
                          old_failure_sha256=state['old_failure_sha256'], carrier=transport,
                          build_start_attempts=receipt['build_start_attempts'],
                          static_gate_status=recomputed['status'])
    except BaseException as error:
        result.update(status='FAILED', actions_output_origin_authenticated=False,
                      selected_static_accepted=False, failure=(type(error).__name__ + ': ' + str(error))[:4096])
    a.write(out / 'acceptance.json', result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--push-ci', required=True, type=int)
    parser.add_argument('--pr-ci', required=True, type=int)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    result = audit(args.source, [dict(event='push', run_id=args.push_ci),
                   dict(event='pull_request', run_id=args.pr_ci)], args.out)
    print(json.dumps({key: result[key] for key in ('status', 'selected_static_accepted', 'native_admitted')}))
    return 0 if result['selected_static_accepted'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
