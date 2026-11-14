"""Read relocation-backed ELF imports from loader tables, without loading code.

No section headers, symbol execution, resolver calls, memory writes or runtime
admission. An import spelling/slot does not establish which calls execute.
"""
import hashlib
import struct

from scripts.readback_process_mapping import elf_ranges


def _need(ok, message):
    if not ok:
        raise ValueError(message)


def inspect_imports(blob):
    loads = elf_ranges(blob)  # bounded ELF64LE/amd64, PHDRs and file spans
    ordered = sorted(loads, key=lambda p: p['vaddr'])
    for a, b in zip(ordered, ordered[1:]):
        _need(a['vaddr'] + a['memsz'] <= b['vaddr'], 'overlapping ELF load spans')

    def location(va, size):
        _need(type(va) is int and type(size) is int and 0 <= va < 2**64 and 0 <= size < 2**64-va, 'virtual span overflow')
        matches = [p for p in loads if p['vaddr'] <= va and va+size <= p['vaddr']+p['filesz']]
        _need(len(matches) == 1, 'unique file-backed loader span required')
        return matches[0]['offset'] + va - matches[0]['vaddr']

    def virtual(va, size):
        offset = location(va, size)
        return blob[offset:offset+size]

    header = struct.unpack_from('<16sHHIQQQIHHHHHH', blob)
    dynamics = []
    for i in range(header[10]):
        p = struct.unpack_from('<IIQQQQQQ', blob, header[5]+56*i)
        if p[0] == 2:
            dynamics.append(p)
    _need(len(dynamics) == 1, 'unique PT_DYNAMIC required')
    dynamic = dynamics[0]
    _, _, offset, va, _, size, memsize, _ = dynamic
    _need(16 <= size <= 1024*1024 and size % 16 == 0 and size <= memsize and offset+size <= len(blob), 'dynamic table extent')
    _need(location(va, size) == offset, 'dynamic file/virtual association')
    tags, needed, terminated = {}, [], False
    for pos in range(offset, offset+size, 16):
        tag, value = struct.unpack_from('<qQ', blob, pos)
        if tag == 0:
            terminated = True
            break
        if tag == 1:
            needed.append(value)
        else:
            _need(tag not in tags, 'duplicate dynamic tag')
            tags[tag] = value
    _need(terminated, 'unterminated dynamic table')
    _need(all(tag in tags for tag in (5, 6, 10, 11)) and tags[11] == 24, 'dynamic string/symbol metadata')
    _need(1 <= tags[10] <= 4*1024*1024, 'dynamic string budget')
    strings = virtual(tags[5], tags[10])
    _need(strings[:1] == b'\0' and strings[-1:] == b'\0', 'terminated dynamic string table')

    def name_at(index):
        _need(0 <= index < len(strings), 'dynamic string index')
        end = strings.find(b'\0', index, min(len(strings), index+513))
        _need(end >= index, 'bounded terminated symbol name')
        try:
            return strings[index:end].decode('ascii')
        except UnicodeError as exc:
            raise ValueError('ASCII loader name required') from exc

    _need(len(needed) <= 256, 'needed-library budget')
    libraries = [name_at(index) for index in needed]
    _need(all(libraries), 'empty needed library')
    tables = []
    # DT_RELA/RELASZ/RELAENT and DT_JMPREL/PLTRELSZ/PLTREL are actual loader inputs.
    if 7 in tags or 8 in tags:
        _need(all(tag in tags for tag in (7, 8, 9)) and tags[9] == 24, 'RELA table metadata')
        tables.append((tags[7], tags[8]))
    if 23 in tags or 2 in tags:
        _need(all(tag in tags for tag in (23, 2, 20)) and tags[20] == 7, 'RELA PLT metadata')
        tables.append((tags[23], tags[2]))
    _need(not tags.get(17, 0) and not tags.get(18, 0), 'REL imports unsupported in amd64 profile')
    count = 0
    spans = []
    for address, nbytes in tables:
        _need(nbytes % 24 == 0 and nbytes // 24 <= 262144, 'relocation table extent')
        count += nbytes // 24
        _need(count <= 262144, 'relocation count budget')
        if nbytes:
            location(address, nbytes)
            for previous, old_size in spans:
                _need(max(previous, address) >= min(previous+old_size, address+nbytes), 'overlapping loader relocation tables')
            spans.append((address, nbytes))
    imports, targets = [], set()
    for address, nbytes in tables:
        raw = virtual(address, nbytes) if nbytes else b''
        for at in range(0, nbytes, 24):
            target, info, addend = struct.unpack_from('<QQq', raw, at)
            kind, index = info & 0xffffffff, info >> 32
            if kind not in (6, 7):
                continue
            _need(index < 65536, 'dynamic symbol budget')
            symbol = struct.unpack('<IBBHQQ', virtual(tags[6]+24*index, 24))
            string_index, attributes, visibility, section, _, _ = symbol
            symbol_type, binding = attributes & 15, attributes >> 4
            if section != 0 or symbol_type not in (0, 2, 10):
                continue
            _need(binding in (1, 2) and visibility == 0 and addend == 0, 'unsupported import binding')
            _need(target % 8 == 0 and target not in targets, 'duplicate or unaligned import slot')
            location(target, 8)
            targets.add(target)
            name = name_at(string_index)
            _need(bool(name), 'empty import name')
            imports.append(dict(name=name, symbol_index=index, symbol_type=symbol_type,
                                binding=binding, slot_vaddr=target, relocation_type=kind))
    return dict(schema='readback-loader-imports-v1', elf_sha256=hashlib.sha256(blob).hexdigest(),
                imports=sorted(imports, key=lambda r: (r['name'], r['slot_vaddr'])),
                needed_libraries=libraries, loader_relocations=count, section_headers_used=False,
                runtime_admission_ready=False, native_admitted=False)
