"""Closed nostdlib CPU loader fixtures. No SDK payload can enter this graph."""
import copy
import json
import os
import re
import shutil
import stat
import struct
import tempfile
from pathlib import Path
from scripts import panda_provider_version_witness as previous
from scripts import build_panda_sdk_cg as owned
from scripts.panda_sdk_link_elf import inspect_elf
from scripts.readback_process_mapping import elf_ranges

ROOT, REPO = previous.ROOT, previous.REPO
BRANCH = 'feature/panda-loader-cpu-profile-v1'
CONTRACT = 'docs/evidence/panda-loader-cpu-01/contract.json'
CONTRACT_SHA = '061386a6a5893f15bac0828577a085670dd4d6b5bdf650049eebc43f16d81feb'
need, read, sha, parse = previous.need, previous.read, previous.sha, previous.parse
run_owned = owned.run_owned
LEGACY, MERGED = 'libstage7_cpu_legacy.so', 'libstage7_cpu_merged.so'
SYMBOL, V1, V2 = 'cpu_probe_value', 'CPU_ABI_1', 'CPU_ABI_2'
CASES = ('same_library', 'merged_nondefault', 'missing_library_version', 'wrong_symbol_version')
SOURCES = {
    'legacy.c': 'int cpu_probe_value(void){return 7;}\n',
    'target1.c': 'int impl(void){return 7;} __asm__(".symver impl,cpu_probe_value@CPU_ABI_1");\n',
    'target2.c': 'int impl(void){return 9;} __asm__(".symver impl,cpu_probe_value@CPU_ABI_2");\n',
    'stub.c': 'int cpu_probe_placeholder(void){return 0;}\n',
    'root.S': '.text\n.global _start\n.type _start,@function\n_start:\n andq $-16,%rsp\n call cpu_probe_value@PLT\n movl %eax,%edi\n movl $60,%eax\n syscall\n.size _start,.-_start\n.section .note.GNU-stack,"",@progbits\n',
    'value1.map': 'CPU_ABI_1 { global: cpu_probe_value; local: *; };\n',
    'value2.map': 'CPU_ABI_2 { global: cpu_probe_value; local: *; };\n',
    'stub1.map': 'CPU_ABI_1 { global: cpu_probe_placeholder; local: *; };\n',
    'stub2.map': 'CPU_ABI_2 { global: cpu_probe_placeholder; local: *; };\n',
}
LAYOUT = {
    'same_library': {'root.so': 'root.so', LEGACY: 'legacy.so'},
    'merged_nondefault': {'root.so': 'root.so', LEGACY: 'stub1.so', MERGED: 'target1.so'},
    'missing_library_version': {'root.so': 'root.so', LEGACY: 'stub2.so', MERGED: 'target1.so'},
    'wrong_symbol_version': {'root.so': 'root.so', LEGACY: 'stub1.so', MERGED: 'target2.so'},
}


def contract(root=ROOT):
    raw = read(Path(root) / CONTRACT, 1024**2)
    need(sha(raw) == CONTRACT_SHA, 'CPU loader contract identity')
    return parse(raw)


def source_closure(root=ROOT):
    root, c = Path(root), contract(root)
    raw = read(root / c['frozen_source_path'], 1024**2)
    need(sha(raw) == c['frozen_source_sha256'], 'frozen318 map identity')
    frozen = parse(raw)
    need(len(frozen) == 318 and previous.source_closure(root) == frozen, 'old source318 unchanged')
    names = set(frozen) | set(c['new_source_paths'])
    need(len(names) == c['source_count'] == 322, 'exact CPU loader source322')
    return {p: sha(read(root / p, 16*1024**2)) for p in sorted(names)}


def validate_ci(source, registrations, proofs):
    need(previous.prior.old.hexstr(source, 40) and type(registrations) is list and
         len(registrations) == 2 and all(type(r) is dict and set(r) == {'event', 'run_id'} and
         previous.prior.old.positive(r['run_id']) for r in registrations) and
         [r['event'] for r in registrations] == ['push', 'pull_request'] and
         registrations[0]['run_id'] != registrations[1]['run_id'], 'two CPU source CI identities')
    need(type(proofs) is list and len(proofs) == 2, 'two CPU source CI proofs')
    for registration, proof in zip(registrations, proofs):
        r = proof['run']
        need(r['id'] == registration['run_id'] and r['head_sha'] == source and r['head_branch'] == BRANCH
             and r['event'] == registration['event'] and r['workflow_id'] == 411705464 and
             r['path'] == '.github/workflows/ci.yml' and type(r['run_attempt']) is int and
             r['run_attempt'] == 1 and r['status'] == 'completed' and r['conclusion'] == 'success'
             and all(r[k]['full_name'] == REPO and r[k]['id'] == 1447652055
                     for k in ('repository', 'head_repository')), 'exact CPU source CI')
        jobs = proof['jobs']
        need(type(jobs['total_count']) is int and jobs['total_count'] == len(jobs['jobs']) == 2 and
             {j['name'] for j in jobs['jobs']} == {'synthetic-unit', 'onnx-interface-test'} and
             len({j['id'] for j in jobs['jobs']}) == 2 and all(previous.prior.old.positive(j['id'])
             and j['run_id'] == r['id'] and j['head_sha'] == source and j['head_branch'] == BRANCH
             and type(j['run_attempt']) is int and j['run_attempt'] == 1 and
             j['status'] == 'completed' and j['conclusion'] == 'success' for j in jobs['jobs']) and
             type(proof['artifacts']['total_count']) is int and
             proof['artifacts'] == dict(total_count=0, artifacts=[]), 'CPU source CI jobs/artifact closure')


def _canonical(path):
    path = Path(os.path.abspath(path))
    need(path.resolve() == path and not path.is_symlink(), 'canonical CPU fixture path')
    return path


def _record(path, limit=1024**2):
    path = _canonical(path)
    s = path.lstat()
    need(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'regular CPU fixture/tool file')
    raw = read(path, limit)
    return dict(nbytes=len(raw), sha256=sha(raw))


def _write(path, value):
    raw = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.cpu-json-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            if stream.write(raw) != len(raw):
                raise OSError('short CPU ledger write')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def _environment(debug=False):
    result = dict(PATH='/usr/bin:/bin', LANG='C', LC_ALL='C')
    if debug:
        result.update(LD_DEBUG='versions,bindings', LD_BIND_NOW='1')
    return result


def _tools():
    return {p: owned.record(p) for p in ('/usr/bin/gcc', '/usr/bin/as', '/usr/bin/ld')}


def _compile_commands():
    base = ['/usr/bin/gcc', '-nostdlib', '-shared', '-fPIC', '-O2', '-fno-stack-protector',
            '-fcf-protection=none', '-fno-asynchronous-unwind-tables', '-fno-unwind-tables',
            '-Wl,-z,noexecstack', '-Wl,--hash-style=both']
    variants = [
        ['legacy.c', '-Wl,--version-script=value1.map', '-Wl,-soname='+LEGACY, '-o', 'legacy.so'],
        ['target1.c', '-Wl,--version-script=value1.map', '-Wl,-soname='+MERGED, '-o', 'target1.so'],
        ['target2.c', '-Wl,--version-script=value2.map', '-Wl,-soname='+MERGED, '-o', 'target2.so'],
        ['stub.c', '-Wl,--version-script=stub1.map', '-L.', '-Wl,--no-as-needed', '-l:target1.so', '-Wl,-soname='+LEGACY, '-o', 'stub1.so'],
        ['stub.c', '-Wl,--version-script=stub2.map', '-L.', '-Wl,--no-as-needed', '-l:target1.so', '-Wl,-soname='+LEGACY, '-o', 'stub2.so'],
        ['root.S', '-L.', '-Wl,--no-as-needed', '-l:legacy.so', '-Wl,-e,_start', '-o', 'root.so'],
    ]
    return [base + v for v in variants]


def build_fixture(out):
    out = _canonical(out)
    need(not out.exists(), 'fresh CPU fixture output')
    c = contract()
    out.mkdir(parents=True, mode=0o700)
    build = out / 'build'
    build.mkdir()
    for name, text in SOURCES.items():
        (build / name).write_text(text)
    tools, commands = _tools(), []
    for index, argv in enumerate(_compile_commands()):
        r = run_owned(argv, build, _environment(), out / 'commands' / str(index),
                      c['compile_seconds'], stream_limit=c['stream_limit_bytes'],
                      disk_root=out, disk_limit=c['maximum_fixture_disk_bytes'])
        commands.append(r)
        need(r['status'] == 'EXITED' and r['returncode'] == 0 and r['streams_complete'] is True and
             r['owned_group_reaped'] is True, 'CPU fixture compilation failed')
    need(_tools() == tools, 'CPU compiler tool drift')
    cases = {}
    for case, files in LAYOUT.items():
        folder = out / 'cases' / case
        folder.mkdir(parents=True)
        for name, source in files.items():
            shutil.copyfile(build / source, folder / name)
        cases[case] = dict(files={name: _record(folder / name) for name in files},
                           target_default_version=False if MERGED in files else None)
    files = {str(p.relative_to(out)): _record(p) for p in out.rglob('*') if p.is_file()}
    manifest = dict(schema='panda-loader-cpu-fixture-v1', root=str(out), tools=tools,
                    compile_commands=commands, files=files, cases=cases,
                    sdk_target_execution=False, scientific_native_runs=0)
    _write(out / 'manifest.json', manifest)
    validate_fixture(out, manifest)
    return manifest


def _headers(raw):
    h = struct.unpack_from('<16sHHIQQQIHHHHHH', raw)
    ph = [struct.unpack_from('<IIQQQQQQ', raw, h[5]+56*i) for i in range(h[10])]
    dynamics = [p for p in ph if p[0] == 2]
    need(len(dynamics) == 1 and not any(p[0] == 7 for p in ph), 'one dynamic/no TLS fixture')
    need(all(not p[1] & 1 for p in ph if p[0] == 0x6474e551), 'nonexecutable fixture stack')
    page = 4096
    need(os.sysconf('SC_PAGE_SIZE') == page, '4KiB CPU mapping profile')
    loads = [p for p in ph if p[0] == 1]
    need([p[3] for p in loads] == sorted(p[3] for p in loads) and
         all(p[7] >= page and p[7] & (p[7]-1) == 0 and p[2] % page == p[3] % page
             for p in loads), 'ordered page-congruent CPU LOAD mappings')
    rounded = [(p[3] & -page, (p[3]+p[6]+page-1) & -page) for p in loads if p[6]]
    need(all(a[1] <= b[0] for a, b in zip(rounded, rounded[1:])), 'disjoint rounded CPU LOAD pages')
    d, tags = dynamics[0], {}
    for at in range(d[2], d[2]+d[5], 16):
        tag, value = struct.unpack_from('<qQ', raw, at)
        if tag == 0:
            break
        tags[tag] = value
    need(not any(tags.get(t, 0) for t in (12, 13, 25, 26, 27, 28, 32, 33)), 'no fixture constructors/destructors')
    need(not any(t in tags for t in (17, 18, 19, 35, 36, 37, 0x6000000f, 0x60000010,
                                    0x60000011, 0x60000012)), 'no unparsed/packed CPU relocations')
    need(22 not in tags and not tags.get(30, 0) & 4, 'no CPU text relocations')
    allowed = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 20, 23, 30, 0x6ffffef5,
               0x6ffffff0, 0x6ffffffb, 0x6ffffffc, 0x6ffffffd, 0x6ffffffe, 0x6fffffff}
    need(set(tags) <= allowed and not tags.get(30, 0) & ~8 and
         not tags.get(0x6ffffffb, 0) & ~1, 'closed CPU dynamic tags/flags')
    return tags


def _virtual(raw, va, size, executable=False):
    rows = [p for p in elf_ranges(raw) if p['vaddr'] <= va and va+size <= p['vaddr']+p['filesz']
            and (not executable or p['flags'] & 1 and not p['flags'] & 2)]
    need(len(rows) == 1, 'unique fixture code/data span')
    p = rows[0]
    return raw[p['offset']+va-p['vaddr']:p['offset']+va-p['vaddr']+size]


def _validate_binary(raw, role):
    meta, tags = inspect_elf(raw), _headers(raw)
    need(meta['init_present'] is False and meta['ifunc_exports'] == 0 and
         not meta['unsupported_features'] and meta['rpath'] is None and meta['runpath'] is None,
         'closed CPU fixture loader features')
    need(set(meta['relocation_kinds']) <= {7}, 'only fixture PLT relocation')
    need(meta['relocation_count'] == (1 if role == 'root.so' else 0), 'exact total CPU relocation count')
    functions = [r for r in meta['exports'] if r['symbol_type'] == 2]
    expected = '_start' if role == 'root.so' else ('cpu_probe_placeholder' if role.startswith('stub') else SYMBOL)
    need(len(functions) == 1 and functions[0]['name'] == expected, 'one closed fixture function')
    fn = functions[0]
    body = _virtual(raw, fn['value'], fn['nbytes'], executable=True)
    if role == 'root.so':
        need(meta['needed'] == [LEGACY] and len(meta['imports']) == 1 and
             meta['imports'][0]['name'] == SYMBOL and meta['imports'][0]['version'] == V1 and
             meta['imports'][0]['version_library'] == LEGACY and meta['imports'][0]['binding'] == 1 and
             meta['imports'][0]['symbol_type'] == 2 and len(body) == 18 and
             body[:5] == bytes.fromhex('4883e4f0e8') and body[9:] == bytes.fromhex('89c7b83c0000000f05'),
             'fixed CPU entry call/exit instructions')
        header = struct.unpack_from('<16sHHIQQQIHHHHHH', raw)
        need(header[4] == fn['value'], 'fixed CPU ELF entry')
        target = fn['value']+9+struct.unpack_from('<i', body, 5)[0]
        stub = _virtual(raw, target, 6, executable=True)
        need(stub[:2] == b'\xff\x25', 'fixed CPU PLT jump')
        got = target+6+struct.unpack_from('<i', stub, 2)[0]
        slots = [p for p in elf_ranges(raw) if p['vaddr'] <= got and got+8 <= p['vaddr']+p['memsz']
                 and p['flags'] & 2 and not p['flags'] & 1]
        need(len(slots) == 1, 'CPU GOT is writable nonexecutable memory')
        need(23 in tags and 2 in tags and tags[2] == 24, 'one CPU PLT relocation')
        slot, info, addend = struct.unpack('<QQq', _virtual(raw, tags[23], 24))
        need(slot == got and info & 0xffffffff == 7 and info >> 32 == meta['imports'][0]['symbol_index']
             and addend == 0, 'CPU entry only calls declared probe import')
    else:
        need(not meta['imports'] and meta['needed'] == ([MERGED] if role.startswith('stub') else []),
             'no external CPU imports/dependencies')
        value = 9 if role == 'target2.so' else 7
        need(body == (bytes.fromhex('31c0c3') if role.startswith('stub') else
                      b'\xb8'+struct.pack('<I', value)+b'\xc3'), 'fixed CPU constant-return instructions')
        need(meta['soname'] == (LEGACY if role == 'legacy.so' or role.startswith('stub') else MERGED),
             'fixed CPU SONAME')
        need(fn['version'] == (V2 if role in ('target2.so', 'stub2.so') else V1) and
             fn['default_version'] is (not role.startswith('target')), 'explicit CPU version/default distinction')
    return meta


def validate_fixture(out, manifest):
    out = _canonical(out)
    need(out.is_dir() and type(manifest) is dict and manifest['root'] == str(out) and
         manifest['schema'] == 'panda-loader-cpu-fixture-v1' and
         manifest['sdk_target_execution'] is False and manifest['scientific_native_runs'] == 0,
         'owned CPU fixture identity')
    need(parse(read(out / 'manifest.json', 1024**2)) == manifest, 'CPU manifest/retained binding')
    actual = set()
    for p in out.rglob('*'):
        need(not p.is_symlink() and p.resolve() == p, 'CPU fixture alias')
        if p.is_file() and p.name != 'manifest.json':
            actual.add(str(p.relative_to(out)))
    need(actual == set(manifest['files']), 'exact CPU fixture file closure')
    need(sum(r['nbytes'] for r in manifest['files'].values()) <= contract()['maximum_fixture_disk_bytes'],
         'CPU fixture disk bound')
    for name, row in manifest['files'].items():
        need(_record(out / name) == row, 'CPU fixture bytes changed: ' + name)
    need(_tools() == manifest['tools'] and len(manifest['compile_commands']) == 6,
         'same CPU compiler tools/command count')
    for name, text in SOURCES.items():
        need(read(out / 'build' / name, 65536) == text.encode(), 'closed CPU source bytes')
    need(set(manifest['cases']) == set(CASES), 'four closed CPU cases')
    for case, layout in LAYOUT.items():
        need(set(manifest['cases'][case]['files']) == set(layout), 'closed CPU case files')
        for name, role in layout.items():
            p = out / 'cases' / case / name
            need(_record(p) == manifest['cases'][case]['files'][name] == manifest['files']['build/'+role],
                 'CPU case/build bytes')
            _validate_binary(read(p, 1024**2), role)


def case_paths(fixture, case):
    need(case in CASES, 'closed CPU case name')
    p = Path(fixture) / 'cases' / case
    return dict(root=str(p/'root.so'), legacy=str(p/LEGACY), merged=str(p/MERGED))


def _loader_record(path):
    row = _record(path)
    meta = inspect_elf(read(path, 1024**2))
    need(not meta['needed'] and not meta['imports'] and meta['init_present'] is False and
         not meta['unsupported_features'], 'standalone loader tool only')
    return row


def validate_observation(case, command, trace, paths):
    need(case in CASES and type(trace) is str and command['status'] == 'EXITED' and
         command['streams_complete'] is True and command['owned_group_reaped'] is True and
         type(command['pid']) is int and command['pid'] > 0 and
         type(command['returncode']) is int and 0 <= command['returncode'] <= 255, 'complete owned CPU process')
    raw = trace.encode()
    stderr, stdout = command['streams']['stderr'], command['streams']['stdout']
    need(len(raw) <= contract()['stream_limit_bytes'] and
         stderr == dict(observed_nbytes=len(raw), saved_nbytes=len(raw), sha256=sha(raw)) and
         stdout == dict(observed_nbytes=0, saved_nbytes=0, sha256=sha(b'')), 'complete bound CPU trace/empty stdout')
    quote = "[`']"
    version = re.search(r'checking for version '+quote+V1+quote+r' in file '+re.escape(paths['legacy'])+
                        r' \[0\] required by file '+re.escape(paths['root'])+r' \[0\]', trace)
    need(version is not None, 'observed declared-library version check')
    positive = case in ('same_library', 'merged_nondefault')
    destination = paths['legacy'] if case == 'same_library' else paths['merged']
    binding = re.search(r'binding file '+re.escape(paths['root'])+r' \[0\] to '+re.escape(destination)+
                        r' \[0\]: normal symbol '+quote+SYMBOL+quote+r' \['+V1+r'\]', trace)
    if positive:
        need(command['returncode'] == 7 and binding is not None, 'observed exact CPU version binding and value')
        return dict(fixture_entry_verified=True, declared_version_checked=True,
                    bound_provider=LEGACY if case == 'same_library' else MERGED, failure_kind=None)
    any_binding = re.search(r'binding file '+re.escape(paths['root'])+r'.*normal symbol '+quote+SYMBOL+quote, trace)
    need(command['returncode'] not in (0, 7) and any_binding is None, 'failed before CPU probe binding/entry')
    if case == 'missing_library_version':
        need(re.search(r'version '+quote+V1+quote+r' not found', trace) is not None,
             'observed missing declared-library version')
        kind = 'DECLARED_LIBRARY_VERSION_MISSING'
    else:
        need('undefined symbol: '+SYMBOL+', version '+V1 in trace, 'observed missing explicit symbol version')
        kind = 'EXPLICIT_SYMBOL_VERSION_MISSING'
    return dict(fixture_entry_verified=False, declared_version_checked=True, bound_provider=None, failure_kind=kind)


def _recount(result):
    lower, unknown = 0, 0
    for row in result['cases']:
        command = row.get('command')
        if command and type(command.get('pid')) is int and command['pid'] > 0:
            lower += 1
        elif command and command.get('status') == 'SPAWN_FAILED' and command.get('pid') is None:
            pass
        else:
            unknown += 1
    result.update(loader_invocations=lower if unknown == 0 else None,
                  loader_invocations_lower_bound=lower, loader_invocations_upper_bound=lower+unknown)


def run_cases(loader, fixture, manifest, out):
    out = _canonical(out)
    need(not out.exists(), 'fresh one-use CPU case output')
    out.mkdir(parents=True, mode=0o700)
    result = dict(schema='panda-loader-cpu-cases-v1', status='FAILED', loader_start_attempts=0,
                  loader_invocations=0, loader_invocations_lower_bound=0, loader_invocations_upper_bound=0,
                  verified_fixture_entries=0, controlled_loader_failures=0, cases=[],
                  sdk_target_execution=False, scientific_native_runs=0, native_admitted=False,
                  stage7_complete=False)
    _write(out/'ledger.json', result)
    try:
        validate_fixture(fixture, manifest)
        loader = _canonical(loader)
        identity = _loader_record(loader)
        preload = Path('/etc/ld.so.preload')
        need(not preload.exists() or read(preload, 65536).strip() == b'', 'no system preload')
        for case in CASES:
            validate_fixture(fixture, manifest)
            need(_loader_record(loader) == identity, 'loader tool drift')
            need(result['loader_start_attempts'] < contract()['maximum_loader_invocations'], 'four CPU slots only')
            paths = case_paths(fixture, case)
            result['loader_start_attempts'] += 1
            row = dict(case=case, status='START_REQUESTED', command=None)
            result['cases'].append(row)
            _recount(result)
            _write(out/'ledger.json', result)
            argv = [str(loader), '--inhibit-cache', '--glibc-hwcaps-mask', '', '--library-path',
                    str(Path(paths['root']).parent), paths['root']]
            row['command'] = run_owned(argv, fixture, _environment(debug=True), out/case,
                contract()['probe_seconds'], stream_limit=contract()['stream_limit_bytes'])
            _recount(result)
            _write(out/'ledger.json', result)
            trace = read(out/case/'stderr.log', contract()['stream_limit_bytes']).decode('utf-8')
            row['observation'] = validate_observation(case, row['command'], trace, paths)
            row['status'] = 'EXPECTED_CPU_CASE_OBSERVED'
            result['verified_fixture_entries'] += int(row['observation']['fixture_entry_verified'])
            result['controlled_loader_failures'] += int(not row['observation']['fixture_entry_verified'])
            _write(out/'ledger.json', result)
        need(_loader_record(loader) == identity, 'final loader bytes')
        validate_fixture(fixture, manifest)
        result.update(status='FOUR_CPU_LOADER_VERSION_CASES_OBSERVED_NOT_SDK_RUNTIME', loader=identity)
    except BaseException as error:
        result.update(status='FAILED', failure=(type(error).__name__+': '+str(error))[:4096])
        _recount(result)
    try:
        _write(out/'ledger.json', result)
    except BaseException as error:
        result.update(status='FAILED', failure=(type(error).__name__+': '+str(error))[:4096])
    return result
