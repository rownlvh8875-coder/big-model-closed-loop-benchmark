"""Narrow version-library/export DATA witnesses; never change legacy verdicts."""
import hashlib
import json
from pathlib import Path
from scripts import panda_sdk_cg_runpath_json as prior
from scripts import panda_sdk_link_elf as elf
from scripts import panda_sdk_link_image as image

ROOT, REPO = prior.ROOT, prior.REPO
BRANCH = 'feature/panda-provider-version-witness-v1'
CONTRACT = 'docs/evidence/panda-provider-version-01/contract.json'
CONTRACT_SHA = '88172397264dcd75cd99a4c9d32308280f05aba59fe1242448e416bf83ade608'
FORBIDDEN = prior.FORBIDDEN
need, read, parse, sha = prior.need, prior.read, prior.parse, prior.sha


def contract(root=ROOT):
    raw = read(Path(root) / CONTRACT, 1024**2)
    need(sha(raw) == CONTRACT_SHA, 'version witness contract identity')
    return parse(raw)


def source_closure(root=ROOT):
    root, c = Path(root), contract(root)
    raw = read(root / c['frozen_source_path'], 1024**2)
    need(sha(raw) == c['frozen_source_sha256'], 'frozen314 map identity')
    frozen = parse(raw)
    need(len(frozen) == 314 and prior.source_closure(root) == frozen, 'prior source314 unchanged')
    names = set(frozen) | set(c['new_source_paths'])
    need(len(names) == c['source_count'] == 318, 'exact witness source318')
    return {name: sha(read(root / name, 16*1024**2)) for name in sorted(names)}


def validate_ci(source, registrations, proofs):
    need(prior.old.hexstr(source, 40) and type(registrations) is list and len(registrations) == 2
         and all(type(r) is dict and set(r) == {'event', 'run_id'} and
                 prior.old.positive(r['run_id']) for r in registrations)
         and [r['event'] for r in registrations] == ['push', 'pull_request']
         and registrations[0]['run_id'] != registrations[1]['run_id'], 'two witness source CI identities')
    need(type(proofs) is list and len(proofs) == 2, 'two witness source CI proofs')
    for registration, proof in zip(registrations, proofs):
        run = proof['run']
        need(run['id'] == registration['run_id'] and run['head_sha'] == source and
             run['head_branch'] == BRANCH and run['event'] == registration['event'] and
             run['workflow_id'] == 411705464 and run['path'] == '.github/workflows/ci.yml' and
             type(run['run_attempt']) is int and run['run_attempt'] == 1 and
             run['status'] == 'completed' and run['conclusion'] == 'success' and
             all(run[k]['full_name'] == REPO and run[k]['id'] == 1447652055
                 for k in ('repository', 'head_repository')), 'exact witness source CI')
        jobs = proof['jobs']
        need(type(jobs['total_count']) is int and jobs['total_count'] == len(jobs['jobs']) == 2
             and {r['name'] for r in jobs['jobs']} == {'synthetic-unit', 'onnx-interface-test'}
             and len({r['id'] for r in jobs['jobs']}) == 2
             and all(prior.old.positive(r['id']) and r['run_id'] == run['id'] and
                     r['head_sha'] == source and r['head_branch'] == BRANCH and
                     type(r['run_attempt']) is int and r['run_attempt'] == 1 and
                     r['status'] == 'completed' and r['conclusion'] == 'success' for r in jobs['jobs'])
             and proof['artifacts'] == dict(total_count=0, artifacts=[]), 'witness CI jobs/artifact closure')


def _library(value, optional=False):
    need(optional and value is None or type(value) is str and value and
         '/' not in value and '\\' not in value and '\0' not in value and value not in ('.', '..'),
         'loader library basename')


def _validate_nodes(nodes):
    c = contract()
    need(type(nodes) is dict and 1 <= len(nodes) <= c['maximum_nodes'], 'bounded loader nodes')
    nodes = prior.canonical_metadata(nodes)
    symbols = 0
    for path, meta in nodes.items():
        image.canonical(path)
        need(meta['path'] == path and prior.old.hexstr(meta['elf_sha256']) and
             type(meta['nbytes']) is int and 0 < meta['nbytes'] <= 64*1024**2 and
             meta['native_admitted'] is False and meta['runtime_mapping_qualified'] is False,
             'loader node identity/authority')
        _library(meta['soname'], optional=True)
        needed = meta['needed']
        need(type(needed) is list and len(needed) <= 256 and len(set(needed)) == len(needed),
             'unique needed libraries')
        for name in needed:
            _library(name)
        need(type(meta['unsupported_features']) is list and
             all(type(s) is str for s in meta['unsupported_features']), 'unsupported feature list')
        definitions, requirements = meta['version_definitions'], meta['version_needs']
        for key, value in definitions.items():
            need(int(key) >= 1 and type(value) is str and value, 'version definition')
        for key, value in requirements.items():
            need(int(key) >= 2 and type(value) is dict and set(value) == {'name', 'library'}
                 and type(value['name']) is str and value['name'] and value['library'] in needed,
                 'version requirement')
        need(type(meta['dynamic_symbol_count']) is int and 1 <= meta['dynamic_symbol_count'] <= 65536,
             'dynamic symbol extent')
        seen = set()
        for kind in ('imports', 'exports'):
            rows = meta[kind]
            need(type(rows) is list, 'loader symbol list')
            symbols += len(rows)
            need(symbols <= c['maximum_symbols'], 'aggregate loader symbol budget')
            for row in rows:
                need(type(row) is dict and type(row['name']) is str and row['name'] and
                     type(row['symbol_index']) is int and 0 < row['symbol_index'] < meta['dynamic_symbol_count']
                     and row['symbol_index'] not in seen and type(row['binding']) is int and
                     row['binding'] in ((1, 2) if kind == 'imports' else (1, 2, 10)) and
                     type(row['symbol_type']) is int and 0 <= row['symbol_type'] <= 15 and
                     type(row['default_version']) is bool and
                     all(type(row[k]) is int and 0 <= row[k] < 2**64 for k in ('value', 'nbytes')),
                     'typed loader symbol identity')
                seen.add(row['symbol_index'])
                version = row['version']
                need(version is None or type(version) is str and version, 'symbol version name')
                if kind == 'imports' and version is not None:
                    need(any(v == dict(name=version, library=row['version_library'])
                             for v in requirements.values()), 'import/version-library association')
                else:
                    need(row['version_library'] is None and
                         (version is None or version in definitions.values()), 'export/version definition association')
    return nodes


def _pin(pin, nodes, alias=False):
    fields = {'path', 'soname', 'sha256', 'nbytes'} | ({'versions'} if alias else set())
    need(type(pin) is dict and set(pin) == fields, 'closed model pin')
    path = image.canonical(pin['path'])
    need(path in nodes and prior.old.hexstr(pin['sha256']) and type(pin['nbytes']) is int and
         pin['nbytes'] > 0, 'present pinned loader node')
    node = nodes[path]
    need(node['soname'] == pin['soname'] and node['elf_sha256'] == pin['sha256'] and
         node['nbytes'] == pin['nbytes'], 'pinned node bytes/SONAME')
    if alias:
        need(type(pin['versions']) is list and pin['versions'] and
             all(type(v) is str and v for v in pin['versions']) and
             len(set(pin['versions'])) == len(pin['versions']), 'explicit model versions')
    return node


def _graph(nodes, edges, root):
    need(type(edges) is list and len(edges) <= contract()['maximum_edges'], 'bounded needed edges')
    selected = {}
    for row in edges:
        need(type(row) is dict and set(row) == {'requester', 'needed', 'selected'}, 'closed needed edge')
        key = (row['requester'], row['needed'])
        need(key not in selected and row['requester'] in nodes and row['selected'] in nodes and
             row['needed'] in nodes[row['requester']]['needed'] and
             nodes[row['selected']]['soname'] == row['needed'], 'unique exact needed edge')
        selected[key] = row['selected']
    need(set(selected) == {(p, n) for p, m in nodes.items() for n in m['needed']}, 'complete needed edges')
    reached, todo = set(), [root]
    while todo:
        path = todo.pop()
        if path in reached:
            continue
        reached.add(path)
        todo.extend(selected[path, name] for name in nodes[path]['needed'])
    need(reached == set(nodes), 'no disconnected providers')
    return selected


def _definition(meta, name):
    matches = [int(k) for k, v in meta['version_definitions'].items() if int(k) > 1 and v == name]
    return matches[0] if len(matches) == 1 else None


def _witness(path, row, nodes, selected, policy):
    alias = policy['aliases'].get(row['version_library'])
    if not alias or row['symbol_type'] != 2 or row['version'] not in alias['versions']:
        return None, 'outside pinned ordinary-FUNC/version profile'
    stub, target = nodes[alias['path']], nodes[policy['target']['path']]
    requirement_indices = [int(k) for k, v in nodes[path]['version_needs'].items()
                           if v == dict(name=row['version'], library=row['version_library'])]
    declared_index, target_index = _definition(stub, row['version']), _definition(target, row['version'])
    if (len(requirement_indices) != 1 or selected.get((path, row['version_library'])) != alias['path']
            or declared_index is None or target_index is None or
            selected.get((alias['path'], target['soname'])) != policy['target']['path']):
        return None, 'declared-library/version/target-edge obligation absent or ambiguous'
    exports = [s['symbol_index'] for s in target['exports'] if s['name'] == row['name'] and
               s['version'] == row['version'] and s['symbol_type'] == 2 and s['binding'] in (1, 2)]
    if not exports:
        return None, 'ordinary target name/type/version export absent'
    return dict(import_=row, requirement_index=requirement_indices[0],
                declared_library=dict(path=alias['path'], soname=stub['soname'], sha256=stub['elf_sha256'],
                                      version_definition_index=declared_index),
                target=dict(path=policy['target']['path'], soname=target['soname'], sha256=target['elf_sha256'],
                            version_definition_index=target_index, symbol_indices=sorted(exports))), None


def audit_graph(nodes, edges, policy):
    nodes = _validate_nodes(nodes)
    need(type(policy) is dict and set(policy) == {'root', 'target', 'aliases',
         'expected_legacy_missing', 'expected_legacy_blocks'}, 'closed witness model')
    need(type(policy['aliases']) is dict and 1 <= len(policy['aliases']) <= 2, 'bounded model aliases')
    for key in ('expected_legacy_missing', 'expected_legacy_blocks'):
        need(type(policy[key]) is int and 0 <= policy[key] <= 200000, 'expected residual population')
    _pin(policy['root'], nodes)
    target = _pin(policy['target'], nodes)
    _library(target['soname'])
    for name, pin in policy['aliases'].items():
        _library(name)
        need(pin['soname'] == name and pin['path'] != policy['target']['path'], 'declared library model identity')
        _pin(pin, nodes, alias=True)
    selected = _graph(nodes, edges, policy['root']['path'])
    result = dict(schema='panda-provider-version-witness-v1', provider_audits={}, legacy_missing_count=0,
                  legacy_block_count=0, witness_count=0, unexplained_count=0,
                  legacy_provider_blocks_removed=False, actions_output_origin_authenticated=False,
                  target_execution=False, scientific_native_runs=0)
    unsupported = set()
    for path, meta in sorted(nodes.items()):
        strict = elf.available_imports(meta, list(nodes.values()))
        unsupported.update(strict['unsupported_features'])
        witnesses, unexplained = [], []
        for row in strict['missing']:
            witness, reason = _witness(path, row, nodes, selected, policy)
            if witness:
                witness['import'] = witness.pop('import_')
                witnesses.append(witness)
            else:
                unexplained.append(dict(import_=row, reason=reason))
        result['provider_audits'][path] = dict(missing=strict['missing'], weak_unresolved=strict['weak_unresolved'],
            resolved_count=len(strict['resolved']), root_strong_symbols_available=strict['root_strong_symbols_available'],
            legacy_audit_sha256=hashlib.sha256(json.dumps(strict, sort_keys=True).encode()).hexdigest(),
            witnesses=witnesses, unexplained=unexplained)
        result['legacy_missing_count'] += len(strict['missing'])
        result['legacy_block_count'] += bool(strict['missing'])
        result['witness_count'] += len(witnesses)
        result['unexplained_count'] += len(unexplained)
    need(result['legacy_missing_count'] == policy['expected_legacy_missing'] and
         result['legacy_block_count'] == policy['expected_legacy_blocks'], 'fixed legacy residual population')
    result['unsupported_features'] = sorted(unsupported)
    complete = not unsupported and result['unexplained_count'] == 0
    result.update(diagnostic_witnesses_complete=complete,
                  status='LEGACY_PROVIDER_VERSION_WITNESSES_' + ('COMPLETE' if complete else 'INCOMPLETE') + '_NOT_RUNTIME')
    for flag in FORBIDDEN:
        result[flag] = False
    return result
