"""Offline pinned Panda dispatch inventory and installation planning gate.

Source branches are a conservative union, not observed execution. Loader import
slots and matching spellings do not establish compiled paths or runtime coverage.
No renderer loading, lookup, patching, driver query or native admission occurs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

from scripts.panda_readback_abi import qualify_elf
from scripts.readback_elf_imports import inspect_imports

ROOT = Path(__file__).resolve().parents[1]
REVISION = '470e352ab87ceae6e30429720e4690c8371f5a55'
DELIVERY_SHA = '04955473d5747c483a115a6d30695a36041421df46764b796d95a229f96a02f2'
SOURCE_PINS = {
    'glGraphicsStateGuardian_src.cxx': (491575, 'a7ee480dbafa47f652bbab8b525606421cde6d9a15507422c423fe62128f2d6a'),
    'glGraphicsBuffer_src.cxx': (69373, 'fef28d07e0d9b0e5276769fb08a5c5710eebd0cac2c8c445c64ba3a75705cb3f'),
    'glxGraphicsStateGuardian.cxx': (28440, '1525687bc32339493bf3655872089c9d83d41ac3830f8070433f8e703170cc20'),
    'posixGraphicsStateGuardian.cxx': (2492, '3d7f0a0d8b05a8c585a353ff5d4e0680e07441c02afbf5f87344ee4628b61ed1'),
}
_NAME = re.compile(r'gl[A-Z][A-Za-z_0-9]*\Z')
_IDENT = re.compile(r'[A-Za-z_][A-Za-z_0-9]*')
_LOOKUPS = {'get_extension_func', 'do_get_extension_func', 'get_system_func'}
_UNSAFE = ('glPixelStore', 'glBindBuffer', 'glDeleteBuffers', 'glBindFramebuffer', 'glDeleteFramebuffers',
           'glReadBuffer', 'glNamedFramebufferReadBuffer', 'glFramebufferReadBuffer', 'glPushClientAttrib',
           'glPopClientAttrib', 'glXCreate', 'glXMake', 'glXDestroy', 'glXCopyContext', 'glReadPixels', 'glGetError')


def _need(ok, message):
    if not ok:
        raise ValueError(message)


def _tokens(data):
    _need(type(data) is bytes and len(data) <= 1024*1024, 'source byte budget')
    try:
        text = data.decode('utf-8')
    except UnicodeError as exc:
        raise ValueError('source UTF8 required') from exc
    result, i, line = [], 0, 1
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            line += ch == '\n'
            i += 1
            continue
        if text.startswith('//', i):
            end = text.find('\n', i+2)
            i = len(text) if end < 0 else end
            continue
        if text.startswith('/*', i):
            end = text.find('*/', i+2)
            _need(end >= 0, 'unterminated source comment')
            line += text.count('\n', i, end+2)
            i = end+2
            continue
        if text.startswith('\\\n', i):
            # Do not silently miss an identifier manufactured by phase-two splicing.
            _need(not (i and text[i-1].isalnum() and i+2 < len(text) and text[i+2].isalnum()), 'spliced source token unsupported')
            line += 1
            i += 2
            continue
        _need(not text.startswith('R"', i), 'raw source strings unsupported')
        if ch in ('"', "'"):
            quote, start, startline = ch, i+1, line
            i += 1
            while i < len(text) and text[i] != quote:
                _need(text[i] != '\n', 'newline in ordinary source literal')
                if text[i] == '\\':
                    _need(i+1 < len(text), 'unterminated source escape')
                    line += text[i+1] == '\n'
                    i += 2
                else:
                    i += 1
            _need(i < len(text), 'unterminated source literal')
            result.append(('string' if quote == '"' else 'char', text[start:i], startline))
            i += 1
        else:
            match = _IDENT.match(text, i)
            if match:
                result.append(('id', match[0], line))
                i = match.end()
            else:
                punctuation = text[i:i+2] if text[i:i+2] in ('::', '->') else ch
                result.append(('punct', punctuation, line))
                i += len(punctuation)
        _need(len(result) <= 500000, 'source token budget')
    return result


def _closing(tokens, opening):
    depth = 0
    for index in range(opening, len(tokens)):
        if tokens[index][1] == '(':
            depth += 1
            _need(depth <= 64, 'source nesting budget')
        elif tokens[index][1] == ')':
            depth -= 1
            if depth == 0:
                return index
    raise ValueError('unclosed source call')


def _string(raw):
    result, i = [], 0
    escapes = {'n': '\n', 'r': '\r', 't': '\t', '\\': '\\', '"': '"', "'": "'", 'a': '\a', 'b': '\b', 'f': '\f', 'v': '\v'}
    while i < len(raw):
        if raw[i] != '\\':
            result.append(raw[i]); i += 1
            continue
        i += 1
        _need(i < len(raw), 'incomplete string escape')
        if raw[i] == '\n':
            i += 1
        elif raw[i] in escapes:
            result.append(escapes[raw[i]]); i += 1
        elif raw[i] in '01234567':
            match = re.match('[0-7]{1,3}', raw[i:])
            result.append(chr(int(match[0], 8))); i += len(match[0])
        elif raw[i] == 'x':
            match = re.match('[0-9a-fA-F]+', raw[i+1:])
            _need(match is not None and len(match[0]) <= 2, 'bounded byte hex escape')
            result.append(chr(int(match[0], 16))); i += 1+len(match[0])
        else:
            raise ValueError('unsupported lookup string escape')
    return ''.join(result)


def _declared(tokens, index, close):
    following = tokens[close+1][1] if close+1 < len(tokens) else ''
    if following == '{':
        return True
    if index >= 2 and tokens[index-2][1] == '#' and tokens[index-1][1] == 'define':
        return True
    if following != ';':
        return False
    previous = []
    for token in reversed(tokens[max(0, index-12):index]):
        if token[1] in (';', '{', '}'):
            break
        previous.append(token[1])
    # A conservative ordinary declaration check; assignments/return/casts remain calls.
    return bool(set(previous) & {'void', 'char', 'int', 'unsigned', 'auto', 'GLXContext'}) and not set(previous) & {'=', 'return', '(', ')', '->', '.'}


def scan_source(data, filename):
    _need(type(filename) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', filename), 'source filename')
    tokens = _tokens(data)
    groups = dict(literal_lookups=[], computed_lookups=[], direct_calls=[], member_calls=[])
    for index, (kind, name, line) in enumerate(tokens):
        member = name.startswith('_') and _NAME.fullmatch(name[1:])
        direct = _NAME.fullmatch(name)
        if kind != 'id' or not (member or direct or name in _LOOKUPS):
            continue
        if index+1 >= len(tokens) or tokens[index+1][1] != '(':
            continue
        close = _closing(tokens, index+1)
        if _declared(tokens, index, close):
            continue
        if name in _LOOKUPS:
            arguments = tokens[index+2:close]
            if arguments and all(t[0] == 'string' for t in arguments):
                value = ''.join(_string(t[1]) for t in arguments)
                _need(len(value) <= 63 and _NAME.fullmatch(value), 'literal lookup name')
                groups['literal_lookups'].append(dict(name=value, line=line))
            else:
                groups['computed_lookups'].append(dict(callee=name, line=line))
        else:
            groups['member_calls' if member else 'direct_calls'].append(dict(name=name, line=line))
        _need(sum(len(v) for v in groups.values()) <= 20000, 'source observation budget')
    return dict(file=filename, sha256=hashlib.sha256(data).hexdigest(), nbytes=len(data),
                **groups, active_compiled_paths_proven=False, preprocessor_branches_selected=False)


def delivery_routes(data):
    tokens = _tokens(data)
    names = []
    for index, token in enumerate(tokens):
        if token[:2] != ('id', 'ROUTE') or index+2 >= len(tokens) or tokens[index+1][1] != '(' or tokens[index+2][0] != 'string':
            continue
        close = _closing(tokens, index+1)
        args = tokens[index+2:close]
        _need(len(args) == 5 and args[1][1] == args[3][1] == ',' and args[2][0] == args[4][0] == 'id', 'typed ROUTE declaration')
        name = _string(args[0][1])
        _need(len(name) <= 63 and _NAME.fullmatch(name) and name not in names, 'duplicate or invalid delivery route')
        names.append(name)
    _need(0 < len(names) <= 256, 'delivery route budget')
    return tuple(names)


def qualify_sources(sources):
    _need(type(sources) is dict and set(sources) == set(SOURCE_PINS), 'exact pinned source set required')
    result = []
    for name, (size, sha) in SOURCE_PINS.items():
        data = sources[name]
        _need(type(data) is bytes and len(data) == size and hashlib.sha256(data).hexdigest() == sha, 'pinned source identity: '+name)
        result.append(scan_source(data, name))
    _need(sum(len(s[k]) for s in result for k in ('literal_lookups', 'computed_lookups', 'direct_calls', 'member_calls')) <= 20000, 'combined observation budget')
    return result


def _names(values, cap):
    _need(type(values) in (tuple, list) and len(values) <= cap, 'bounded explicit names required')
    _need(all(type(n) is str and len(n) <= 63 and _NAME.fullmatch(n) for n in values), 'GL name required')
    _need(len(set(values)) == len(values), 'duplicate explicit name')
    return set(values)


def assess_coverage(imports, sources, routes, safe_names=(), mechanism='got-only'):
    _need(type(imports) is dict and imports.get('schema') == 'readback-loader-imports-v1' and type(imports.get('imports')) is list, 'loader inventory required')
    _need(type(sources) is list and 1 <= len(sources) <= 4 and mechanism in ('got-only', 'source-integrated'), 'source set and planning mechanism required')
    routed, safe = _names(routes, 256), _names(safe_names, 256)
    _need(not routed & safe and not any(n.startswith(_UNSAFE) for n in safe), 'known mutation or routed name cannot be safe')
    imported = {r['name'] for r in imports['imports'] if _NAME.fullmatch(r['name'])}
    literal = {r['name'] for source in sources for r in source['literal_lookups']}
    direct = {r['name'] for source in sources for r in source['direct_calls']}
    required = imported | literal | direct
    unclassified = required-routed-safe
    missing = {n for n in unclassified if n.startswith(_UNSAFE)}
    blockers = ['INSTALLATION_UNQUALIFIED', 'ACTIVE_COMPILED_PATHS_UNBOUND', 'NATIVE_LIFETIMES_UNBOUND',
                'ENVIRONMENT_PROFILE_NOT_REQUALIFIED', 'FRESH_CANARY_ALLOWANCE_MISSING']
    if mechanism == 'got-only' and (literal or any(s['computed_lookups'] or s['member_calls'] for s in sources)):
        blockers.append('GOT_CANNOT_COVER_PRIVATE_OR_FALLBACK_RESOLVERS')
    if missing:
        blockers.append('MISSING_CAPTURE_STATE_ROUTES')
    if unclassified:
        blockers.append('UNCLASSIFIED_ROUTE_NAMES')
    if len(required-routed) > 256:
        blockers.append('CONSERVATIVE_NAME_UNION_EXCEEDS_SAFE_CAP')
    return dict(schema='panda-dispatch-coverage-plan-v1', mechanism=mechanism, imported_gl_names=sorted(imported),
                source_literal_names=sorted(literal), direct_source_names=sorted(direct),
                potential_name_union=sorted(required), available_routes=sorted(routed), safe_names=sorted(safe),
                safe_names_count=len(safe), missing_required_routes=sorted(missing), unclassified_names=sorted(unclassified),
                name_classification_complete=not unclassified, blockers=blockers, installation_qualified=False,
                active_compiled_paths_proven=False, runtime_admission_ready=False, native_admitted=False,
                driver_state_proven=False, original_gpu_bytes_observed=False, planning_only=True)


def qualify(image, sources, delivery, safe_names=(), mechanism='got-only'):
    abi = qualify_elf(image)
    source_reports = qualify_sources(sources)
    _need(type(delivery) is bytes and hashlib.sha256(delivery).hexdigest() == DELIVERY_SHA, 'pinned existing delivery source identity')
    routes = delivery_routes(delivery)
    _need(len(routes) == 17, 'existing delivery route count')
    imports = inspect_imports(image)
    assessment = assess_coverage(imports, source_reports, routes, safe_names, mechanism)
    spellings = {name: image.find(name.encode()+b'\0') >= 0 for name in assessment['source_literal_names']}
    from scripts.audit_readback_return_source import probe_environment
    return dict(schema='pinned-panda-dispatch-coverage-v1', kind='STATIC_DATA_ONLY_NO_ELF_LOAD',
                upstream_revision=REVISION, image_sha256=hashlib.sha256(image).hexdigest(),
                delivery_sha256=DELIVERY_SHA, read_abi=abi, imports=imports, sources=source_reports,
                source_literal_nul_spellings_present=spellings, assessment=assessment,
                preferred_future_strategy='source-integrated-dispatch',
                required_future_hooks=[
                    'Before first temporary-context creation: preserve legacy/New/Attribs/SGIX returns and bootstrap lifecycle.',
                    'At unified extension return: cover compiled table, GLX private resolver and POSIX dlsym fallback; preserve NULL/alias.',
                    'At direct capture-state originals: qualify complete mutation/error coverage, including buffer deletion.',
                    'Qualify new build/image/ABI/runtime/camera lifetimes/sink transport and fresh bounded ON/OFF canary contract.'],
                environment_guard=probe_environment(), static_image_identity_matched=True,
                source_to_compiled_paths_proven=False, installation_qualified=False, runtime_admission_ready=False,
                native_admitted=False, driver_state_proven=False, original_gpu_bytes_observed=False,
                new_native_runs=0, new_gl_calls=0, new_provider_runs=0, new_model_runs=0, new_official_ort_runs=0,
                strict_score='0/4 FAIL (inherited original cohort)', stage7_complete=False)


def read_input(path, limit):
    path = os.path.abspath(os.fspath(path))
    _need(os.path.realpath(path) == path, 'canonical nonsymlink input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        _need(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit, 'bounded regular input required')
        data = os.pread(fd, before.st_size, 0)
        after = os.fstat(fd)
        key = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        _need(len(data) == before.st_size and key(before) == key(after) == key(os.stat(path, follow_symlinks=False)), 'input changed or short read')
        return data
    finally:
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--source-dir', required=True)
    parser.add_argument('--delivery', default=str(ROOT/'native/readback_call_delivery.c'))
    parser.add_argument('--safe-names')
    parser.add_argument('--mechanism', choices=('got-only', 'source-integrated'), default='got-only')
    parser.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    try:
        source_dir = Path(args.source_dir)
        sources = {name: read_input(source_dir/name, 1024*1024) for name in SOURCE_PINS}
        safe = json.loads(read_input(args.safe_names, 16384)) if args.safe_names else ()
        report = qualify(read_input(args.image, 64*1024*1024), sources,
                         read_input(args.delivery, 1024*1024), safe, args.mechanism)
        output = Path(os.path.abspath(args.out))
        _need(str(output) == os.path.realpath(output), 'canonical nonsymlink output required')
        output.mkdir(parents=True, exist_ok=False)
        written = []
        try:
            for name, value in (('report.json', report), ('imports.json', report['imports']), ('coverage.json', report['assessment'])):
                path = output/name
                with path.open('x') as stream:
                    written.append(path)
                    stream.write(json.dumps(value, indent=2)+'\n')
        except OSError:
            for path in written:
                path.unlink()
            output.rmdir()
            raise
        print(json.dumps(dict(out=str(output), static_image_identity_matched=True,
                              potential_names=len(report['assessment']['potential_name_union']),
                              missing_routes=report['assessment']['missing_required_routes'], runtime_admission_ready=False)))
        return 0
    except (ValueError, OSError, TypeError) as exc:
        print('dispatch coverage rejected: '+str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
