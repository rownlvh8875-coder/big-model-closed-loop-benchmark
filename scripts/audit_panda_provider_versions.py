"""Authenticate retained SDK3 DATA and explain strict version misses, never load it."""
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
    global w, prior
    from scripts import panda_provider_version_witness as w
    from scripts import accept_panda_sdk_cg_runpath_json as prior
    prior._dependencies()


def _write_json(path, value):
    raw = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode('utf-8')
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.audit-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            if stream.write(raw) != len(raw):
                raise OSError('short audit write')
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
    c = w.contract()
    previous = prior.frozen_state()
    raw = w.read(w.ROOT / c['prior_acceptance_path'], 1024**2)
    w.need(w.sha(raw) == c['prior_acceptance_sha256'], 'prior selected-static receipt unchanged')
    receipt = w.parse(raw)
    w.need(receipt['status'] == 'AUTHENTICATED_CG_RUNPATH_JSON_SELECTED_STATIC_ACCEPTED_NOT_RUNTIME'
           and receipt['audit_source_sha'] == c['prior_audit_source_sha'] and
           receipt['actions_output_origin_authenticated'] is True and
           receipt['selected_static_accepted'] is True and receipt['source_count'] == 314 and
           receipt['producer'] == prior.j.contract()['producer'] and
           all(receipt[k] is False for k in w.FORBIDDEN), 'prior selected-static authority boundary')
    return dict(source_closure=w.source_closure(), prior_acceptance_sha256=w.sha(raw),
                old_failure_sha256=previous['old_failure_sha256'])


def verify_source(source):
    _dependencies()
    old = prior.verify_audit_source(source)
    state = frozen_state()
    w.need({p: state['source_closure'][p] for p in old['source_closure']} == old['source_closure'],
           'source314 prefix unchanged')
    for name in set(state['source_closure']) - set(old['source_closure']):
        raw = subprocess.check_output(['git', 'show', source + ':' + name], cwd=w.ROOT, timeout=10)
        w.need(w.sha(raw) == state['source_closure'][name], 'witness source/Git bytes: ' + name)
    return dict(audit_source_sha=source, **state)


def read_prior_gate(path, expected_sha):
    _dependencies()
    path = prior._canonical(path)
    w.need(prior._hash_file(path, 16*1024**2)['sha256'] == expected_sha, 'prior gate hash')
    raw = w.read(path, 16*1024**2)
    w.need(w.sha(raw) == expected_sha, 'prior gate bytes recheck')
    gate = w.parse(raw)
    w.need(type(gate) is dict and gate['schema'] == 'panda-sdk-cg-runpath-static-gate-v3' and
           gate['status'] == prior.gate.SUCCESS and
           all(gate[k] is False for k in w.FORBIDDEN) and
           type(gate['loader_metadata']) is dict and type(gate['provider_audit']) is dict,
           'prior gate selected-static boundary')
    return gate


def make_client(out, stop):
    token = subprocess.check_output(['gh', 'auth', 'token'], stderr=subprocess.PIPE,
                                    text=True, timeout=10).strip()
    return prior.host.BuildClient(out / 'api', repository=w.REPO, token=token, deadline=stop,
                                  max_requests=96, max_payload_bytes=64*1024**2)


def _ci(client, source, registrations):
    w.need(type(registrations) is list and len(registrations) == 2 and
           all(type(r) is dict and set(r) == {'event', 'run_id'} and
               prior.a.positive(r['run_id']) for r in registrations) and
           [r['event'] for r in registrations] == ['push', 'pull_request'], 'witness CI registrations')
    proofs = []
    for registration in registrations:
        rid, event = str(registration['run_id']), registration['event']
        proofs.append({key: client.get_json('actions/runs/' + rid + suffix,
                      'witness-' + event + '-' + key + '.json')
                      for key, suffix in [('run', ''), ('jobs', '/jobs'), ('artifacts', '/artifacts')]})
    w.validate_ci(source, registrations, proofs)


def audit(source, registrations, out):
    out = Path(os.path.abspath(out))
    if out.resolve() != out or out.exists():
        raise ValueError('fresh canonical provider audit output')
    out.mkdir(parents=True)
    result = dict(schema='panda-provider-version-audit-v1', status='FAILED', audit_source_sha=source,
                  actions_output_origin_authenticated=False, diagnostic_witnesses_complete=False,
                  legacy_provider_blocks_removed=False, old_verdicts_changed=False,
                  new_sdk_builds=0, new_workflow_activations=0, artifact_downloads=0,
                  image_operations=0, target_execution=False, scientific_native_runs=0,
                  native_admitted=False, stage7_complete=False,
                  source_observer_default_off_observed=None, strict_current_result='0/4 FAIL')
    for key in ('full_object_abi_qualified', 'full_dependency_closure_qualified',
                'runtime_mapping_qualified', 'previous_abort_fixed', 'candidate_installed',
                'external_build_origin_authenticated'):
        result[key] = False
    _write_json(out / 'acceptance.json', result)
    initial = dict(result)
    try:
        _dependencies()
        stop = time.monotonic() + w.contract()['audit_seconds']
        with prior._absolute_deadline(stop):
            state = verify_source(source)
            _write_json(out / 'source-closure.json', state)
            client = make_client(out, stop)
            _ci(client, source, registrations)
            producer = prior.authenticate_producer(client)
            c, pc = w.contract(), prior.j.contract()
            previous_gate = read_prior_gate(w.ROOT / c['prior_gate_path'], c['prior_gate_sha256'])
            zip_path, candidate = w.ROOT / pc['retained_zip'], w.ROOT / pc['retained_candidate']
            carrier = prior.verify_cached_carrier(zip_path, candidate)
            receipt = w.parse(w.read(candidate / 'reports/receipt.json', 16*1024**2))
            pin = pc['producer']
            semantics = prior.legacy.validate_receipt(receipt, carrier['files'], pin['source_sha'],
                pin['activation_sha'], pin['run_id'], pin['request_sha256'])
            w.need(semantics['static_passed'], 'same successful SDK3 DATA carrier')
            coherence = prior.evidence.validate_build_evidence(receipt, candidate)
            _write_json(out / 'independent-build-evidence.json', coherence)
            ic = prior.inputs.contract()
            prior.inputs.image_authority(w.ROOT / ic['current_image_acceptance_path'])
            inventory = w.parse(w.read(w.ROOT / prior.inputs.INVENTORY, 16*1024**2))
            providers = prior.provider_paths(inventory, w.ROOT / pc['retained_providers'])
            recomputed = prior.gate.audit_candidate(candidate / 'candidate/libpandagl.so.data',
                candidate / 'candidate/layout-contract.o.data', candidate / 'candidate/layout-descriptor.data',
                candidate / 'candidate/build-libpanda.so.data', receipt['compiler_build'], providers)
            prior._independent_reports(candidate, receipt, recomputed)
            prior.j.validate_reported_gate(previous_gate, recomputed, previous_gate['provider_audit'],
                                           previous_gate['loader_metadata'])
            report = w.audit_graph(recomputed['loader_metadata'], recomputed['provider_audit']['edges'], c['model'])
            _write_json(out / 'witness-report.json', report)
            w.need(report['diagnostic_witnesses_complete'] is True and
                   report['legacy_provider_blocks_removed'] is False and
                   all(report[k] is False for k in w.FORBIDDEN), 'complete narrow witnesses without authority')
            w.need(prior.verify_cached_carrier(zip_path, candidate) == carrier and
                   prior.provider_paths(inventory, w.ROOT / pc['retained_providers']) == providers and
                   verify_source(source) == state, 'final source/cache/prior-verdict recheck')
            read_prior_gate(w.ROOT / c['prior_gate_path'], c['prior_gate_sha256'])
            result.update(status='AUTHENTICATED_PROVIDER_VERSION_WITNESSES_NOT_RUNTIME',
                actions_output_origin_authenticated=True, diagnostic_witnesses_complete=True,
                producer=pin, audit_ci=registrations, source_count=318,
                prior_acceptance_sha256=state['prior_acceptance_sha256'],
                old_failure_sha256=state['old_failure_sha256'], prior_gate_sha256=c['prior_gate_sha256'],
                legacy_missing_count=report['legacy_missing_count'], legacy_block_count=report['legacy_block_count'],
                witness_count=report['witness_count'], unexplained_count=report['unexplained_count'],
                witness_report_sha256=w.sha(w.read(out / 'witness-report.json', 16*1024**2)),
                legacy_blocks={p: len(v['missing']) for p, v in report['provider_audits'].items() if v['missing']},
                root_sha256=recomputed['candidate_sha256'], carrier=carrier)
    except BaseException as error:
        result.update(status='FAILED', actions_output_origin_authenticated=False,
                      diagnostic_witnesses_complete=False,
                      failure=(type(error).__name__ + ': ' + str(error))[:4096])
    try:
        _write_json(out / 'acceptance.json', result)
    except BaseException:
        return initial
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
    print(json.dumps({k: result[k] for k in ('status', 'diagnostic_witnesses_complete', 'native_admitted')}))
    return 0 if result['diagnostic_witnesses_complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
