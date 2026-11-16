"""Narrow JSON representation comparison for a separate, DATA-only SDK3 audit."""
import math
from pathlib import Path, PurePosixPath
from scripts import panda_sdk_cg_runpath_policy as old

ROOT = old.ROOT
REPO = old.REPO
SOURCE_BRANCH = 'feature/panda-sdk-cg-runpath-json-audit-v1'
CONTRACT = 'docs/evidence/panda-sdk-cg-runpath-json-01/contract.json'
CONTRACT_SHA = '4bfd49267bf96fe3ac2cef4a1222c65b2c309ee9e8c69ccac2b68a2a7398e940'
parse, read, sha, need = old.parse, old.read, old.sha, old.need
FORBIDDEN = ('native_admitted', 'stage7_complete', 'full_object_abi_qualified',
             'full_dependency_closure_qualified', 'previous_abort_fixed',
             'candidate_installed', 'runtime_mapping_qualified',
             'external_build_origin_authenticated')


def contract(root=ROOT):
    raw = read(Path(root) / CONTRACT, 1024**2)
    need(sha(raw) == CONTRACT_SHA, 'JSON audit contract identity')
    return parse(raw)


def _canonical(value, metadata=False):
    limits = contract()
    remaining = limits['maximum_nodes']

    def string(value):
        need(type(value) is str and len(value.encode('utf-8')) <= limits['maximum_string_bytes'],
             'bounded JSON string')

    def walk(item, path, depth):
        nonlocal remaining
        remaining -= 1
        need(remaining >= 0 and depth <= limits['maximum_depth'], 'bounded JSON tree')
        kind = type(item)
        if kind is dict:
            table = metadata and len(path) == 2 and path[1] in limits['version_tables']
            result = {}
            for key, child in item.items():
                remaining -= 1
                need(remaining >= 0, 'bounded JSON keys')
                if table:
                    if type(key) is int:
                        need(0 <= key <= 32767, 'version index range')
                        key = str(key)
                    else:
                        need(type(key) is str and key.isascii() and key.isdecimal()
                             and str(int(key)) == key and 0 <= int(key) <= 32767,
                             'canonical version index')
                string(key)
                need(key not in result, 'JSON key collision')
                result[key] = walk(child, path + (key,), depth + 1)
            return result
        if kind is list:
            return [walk(child, path + ('[]',), depth + 1) for child in item]
        if kind is str:
            string(item)
        elif kind is float:
            need(math.isfinite(item), 'finite JSON number')
        else:
            need(kind in (type(None), bool, int), 'supported JSON value')
        return item

    return walk(value, (), 0)


def canonical_metadata(metadata):
    need(type(metadata) is dict and all(type(value) is dict for value in metadata.values()),
         'loader metadata object map')
    return _canonical(metadata, metadata=True)


def _same(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_same(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _providers(value):
    result = _canonical(value)
    need(type(result) is dict and type(result.get('provider_records')) is dict,
         'declared provider records')
    for record in result['provider_records'].values():
        need(type(record) is dict, 'provider record object')
        path = record.get('data_path')
        need(type(path) is str and '\0' not in path and PurePosixPath(path).is_absolute()
             and str(PurePosixPath(path)) == path and '..' not in PurePosixPath(path).parts,
             'canonical advisory provider location')
        del record['data_path']
    return result


def validate_reported_gate(claimed, recomputed, providers, metadata):
    need(claimed.get('status') == recomputed.get('status') ==
         'CG_EIGEN_RUNPATH_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME', 'selected static status')
    for key in FORBIDDEN:
        need(claimed.get(key) is False and recomputed.get(key) is False,
             'no runtime/full-ABI authority: ' + key)
    fields = ('schema', 'status', 'candidate_sha256', 'candidate_nbytes', 'offsets', 'layout',
              'vtable_nbytes', 'runpath', 'reasons', 'selected_layout_match',
              'unknown_wheel_class_sizes')
    for key in fields:
        need(key in claimed and key in recomputed and
             _same(_canonical(claimed[key]), _canonical(recomputed[key])),
             'reported/independent selected fact: ' + key)
    need(_same(_canonical(providers), _canonical(claimed['provider_audit'])) and
         _same(canonical_metadata(metadata), canonical_metadata(claimed['loader_metadata'])),
         'standalone reports/gate binding')
    need(_same(_providers(providers), _providers(recomputed['provider_audit'])) and
         _same(canonical_metadata(metadata), canonical_metadata(recomputed['loader_metadata'])),
         'independent JSON provider diagnostics')
    if 'interfaces' in claimed or 'interfaces' in recomputed:
        for key in ('required_exports', 'same_image_interfaces_verified', 'source_state_instances',
                    'runtime_binding_qualified', 'native_admitted', 'sha256'):
            need(_same(_canonical(claimed['interfaces'][key]),
                       _canonical(recomputed['interfaces'][key])), 'independent interface fact')


def source_closure(root=ROOT):
    root = Path(root)
    c = contract(root)
    raw = read(root / c['frozen_source_path'], 1024**2)
    need(sha(raw) == c['frozen_source_sha256'], 'frozen source map identity')
    frozen = parse(raw)
    need(len(frozen) == 310 and old.closure(root) == frozen, 'original source310 unchanged')
    names = set(frozen) | set(c['new_source_paths'])
    need(len(names) == c['source_count'] == 314, 'exact audit source314')
    return {name: sha(read(root / name, 16*1024**2)) for name in sorted(names)}


def validate_audit_ci(source, registrations, proofs):
    need(old.hexstr(source, 40) and type(registrations) is list and len(registrations) == 2 and
         [row.get('event') for row in registrations] == ['push', 'pull_request'] and
         all(set(row) == {'event', 'run_id'} and old.positive(row['run_id']) for row in registrations)
         and registrations[0]['run_id'] != registrations[1]['run_id'], 'two audit CI identities')
    need(type(proofs) is list and len(proofs) == 2, 'two audit CI proofs')
    for registration, proof in zip(registrations, proofs):
        run = proof['run']
        need(run['id'] == registration['run_id'] and run['head_sha'] == source and
             run['head_branch'] == SOURCE_BRANCH and run['event'] == registration['event'] and
             run['workflow_id'] == 411705464 and run['path'] == '.github/workflows/ci.yml' and
             type(run['run_attempt']) is int and run['run_attempt'] == 1 and
             run['status'] == 'completed' and run['conclusion'] == 'success' and
             run['repository']['full_name'] == REPO, 'exact audit source CI')
        jobs = proof['jobs']
        need(jobs['total_count'] == len(jobs['jobs']) == 2 and
             {row['name'] for row in jobs['jobs']} == {'synthetic-unit', 'onnx-interface-test'} and
             all(row['run_id'] == run['id'] and row['status'] == 'completed' and
                 row['conclusion'] == 'success' for row in jobs['jobs']) and
             proof['artifacts'] == dict(total_count=0, artifacts=[]), 'audit CI jobs/artifact closure')
