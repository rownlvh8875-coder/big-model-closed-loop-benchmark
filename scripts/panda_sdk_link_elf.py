"""Inspect bounded SDK/provider loader symbols and versions, without execution.

No section headers, symbol execution, resolver calls, memory writes or runtime
admission. An import spelling/slot does not establish which calls execute.
"""
import hashlib
import struct

from scripts.readback_process_mapping import elf_ranges


def _need(ok, message):
    if not ok:
        raise ValueError(message)


def inspect_elf(blob):
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
        end = strings.find(b'\0', index, min(len(strings), index+4097))
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
    relocation_count = 0
    spans = []
    for address, nbytes in tables:
        _need(nbytes % 24 == 0 and nbytes // 24 <= 524288, 'relocation table extent')
        relocation_count += nbytes // 24
        _need(relocation_count <= 524288, 'relocation count budget')
        if nbytes:
            location(address, nbytes)
            for previous, old_size in spans:
                _need(max(previous, address) >= min(previous+old_size, address+nbytes), 'overlapping loader relocation tables')
            spans.append((address, nbytes))
    # A bounded load is not a symbol-table bound. Derive the actual extent from
    # loader hash metadata before interpreting/filtering any relocation symbol.
    counts, hash_spans = [], []
    if 4 in tags:  # DT_HASH: nbucket, nchain, buckets, chains
        buckets, chains = struct.unpack('<II', virtual(tags[4], 8))
        _need(1 <= buckets <= 65536 and 1 <= chains <= 65536, 'SysV hash budget')
        size = 8+4*(buckets+chains)
        raw = virtual(tags[4], size)
        links = struct.unpack_from(f'<{buckets+chains}I', raw, 8)
        _need(all(link < chains for link in links), 'SysV hash symbol index')
        counts.append(chains)
        hash_spans.append((tags[4], size))
    if 0x6ffffef5 in tags:  # DT_GNU_HASH: header, bloom, buckets, terminal chains
        address = tags[0x6ffffef5]
        buckets, first, bloom, shift = struct.unpack('<IIII', virtual(address, 16))
        _need(1 <= buckets <= 65536 and 1 <= first <= 65536 and 1 <= bloom <= 65536 and
              bloom & (bloom-1) == 0 and shift < 64, 'GNU hash budget')
        prefix = 16+8*bloom+4*buckets
        raw = virtual(address, prefix)
        bucket_values = struct.unpack_from(f'<{buckets}I', raw, 16+8*bloom)
        starts = [index for index in bucket_values if index]
        _need(all(first <= index < 65536 for index in starts) and len(set(starts)) == len(starts), 'GNU hash bucket index')
        count = first
        if starts:
            index = max(starts)
            while True:
                _need(index < 65536, 'GNU hash chain budget')
                value = struct.unpack('<I', virtual(address+prefix+4*(index-first), 4))[0]
                index += 1
                if value & 1:
                    break
            count = index
            chains = struct.unpack(f'<{count-first}I', virtual(address+prefix, 4*(count-first)))
            groups = {first} | {first+i+1 for i, value in enumerate(chains[:-1]) if value & 1}
            _need(groups == set(starts), 'GNU hash chain/bucket association')
        counts.append(count)
        hash_spans.append((address, prefix+4*(count-first)))
    _need(counts and len(set(counts)) == 1, 'loader-backed dynamic symbol extent required')
    symbol_count = counts[0]
    _need(tags[6] % 8 == 0 and virtual(tags[6], 24) == b'\0'*24, 'dynamic null symbol')
    metadata = [(dynamic[3], dynamic[5]), (tags[5], tags[10]), (tags[6], 24*symbol_count), *spans, *hash_spans]
    metadata.sort()
    for address, extent in metadata:
        location(address, extent)
    for (a, an), (b, _) in zip(metadata, metadata[1:]):
        _need(a+an <= b, 'overlapping loader metadata tables')
    versions_need, versions_def, version_spans = {}, {}, []
    def vr(address,size):
        for a,n in metadata+version_spans:_need(max(a,address)>=min(a+n,address+size),'overlapping version metadata')
        version_spans.append((address,size));return virtual(address,size)
    def elfhash(name):
        h=0
        for c in name.encode('ascii'):
            h=(h<<4)+c;g=h&0xf0000000
            if g:h^=g>>24
            h&=~g
        return h
    if 0x6ffffffe in tags or 0x6fffffff in tags:
        _need(0x6ffffffe in tags and 1<=tags.get(0x6fffffff,0)<=4096,'versionneed count');at=tags[0x6ffffffe];seen=set()
        for i in range(tags[0x6fffffff]):
            _need(at not in seen,'versionneed cycle');seen.add(at);v,count,file,aux,nxt=struct.unpack('<HHIII',vr(at,16));library=name_at(file);_need(v==1 and 1<=count<=256 and library in libraries and aux>=16,'versionneed header');p=at+aux;used=set()
            for j in range(count):
                _need(p not in used and len(versions_need)<16384,'versionneed auxiliary cycle/budget');used.add(p);h,flags,index,name,nextaux=struct.unpack('<IHHII',vr(p,16));name=name_at(name);index&=0x7fff
                _need(index>1 and index not in versions_need and flags&~3==0 and h==elfhash(name),'versionneed definition');versions_need[index]=dict(name=name,library=library)
                _need((nextaux==0)==(j==count-1),'versionneed auxiliary termination')
                if nextaux:_need(nextaux>=16,'versionneed auxiliary offset');p+=nextaux
            _need((nxt==0)==(i==tags[0x6fffffff]-1),'versionneed termination')
            if nxt:_need(nxt>=16,'versionneed offset');at+=nxt
    if 0x6ffffffc in tags or 0x6ffffffd in tags:
        _need(0x6ffffffc in tags and 1<=tags.get(0x6ffffffd,0)<=4096,'versiondef count');at=tags[0x6ffffffc];seen=set()
        for i in range(tags[0x6ffffffd]):
            _need(at not in seen,'versiondef cycle');seen.add(at);v,flags,index,count,h,aux,nxt=struct.unpack('<HHHHIII',vr(at,20));_need(v==1 and 0<index<32768 and index not in versions_def and index not in versions_need and 1<=count<=64 and flags&~3==0 and aux>=20,'versiondef header');p=at+aux;parents=[]
            for j in range(count):
                name,nextaux=struct.unpack('<II',vr(p,8));parents.append(name_at(name));_need((nextaux==0)==(j==count-1),'versiondef auxiliary termination')
                if nextaux:_need(nextaux>=8,'versiondef auxiliary offset');p+=nextaux
            _need(h==elfhash(parents[0]),'versiondef hash');versions_def[index]=parents[0]
            _need((nxt==0)==(i==tags[0x6ffffffd]-1),'versiondef termination')
            if nxt:_need(nxt>=20,'versiondef offset');at+=nxt
    if 0x6ffffff0 in tags:version_indices=struct.unpack('<'+str(symbol_count)+'H',vr(tags[0x6ffffff0],symbol_count*2))
    else:_need(not versions_need and not versions_def,'missing versym');version_indices=(1,)*symbol_count
    referenced=set();relocation_kinds=set()
    for address,nbytes in tables:
        raw=virtual(address,nbytes) if nbytes else b''
        for off in range(0,nbytes,24):
            target,info,addend=struct.unpack_from('<QQq',raw,off);index,kind=info>>32,info&0xffffffff;_need(index<symbol_count,'relocation symbol bound')
            if index:
                width=16 if kind==36 else 8
                _need(target<2**64-width and any(p['vaddr']<=target and target+width<=p['vaddr']+p['memsz'] for p in loads),'relocation target outside mapped image')
                referenced.add(index);relocation_kinds.add(kind)
    imports=[];exports=[];symbols=[];name_bytes=0
    for i in range(symbol_count):
        name,attr,vis,section,value,size=struct.unpack('<IBBHQQ',virtual(tags[6]+24*i,24));name=name_at(name);name_bytes+=len(name);_need(name_bytes<=16*1024**2,'aggregate symbol name budget');binding,typ=attr>>4,attr&15;version_index=version_indices[i]&0x7fff
        version=None;library=None
        if version_index>1:
            if section==0:
                _need(version_index in versions_need,'undefined version index');version=versions_need[version_index]['name'];library=versions_need[version_index]['library']
            else:_need(version_index in versions_def,'defined version index');version=versions_def[version_index]
        row=dict(name=name,symbol_index=i,binding=binding,symbol_type=typ,version=version,version_library=library,default_version=not bool(version_indices[i]&0x8000),value=value,nbytes=size)
        symbols.append((name,binding,vis&3,section))
        if i in referenced and section==0 and binding in (1,2):
            _need(name and vis&3==0,'invalid required symbol');imports.append(row)
        if section!=0 and binding in (1,2,10) and vis&3 in (0,3) and name:
            if typ in (2,10):
                extent=max(1,size);_need(section!=0xfff1 and value<2**64-extent and any(p['flags']&1 and p['vaddr']<=value and value+extent<=p['vaddr']+p['filesz'] for p in loads),'exported code outside executable file span')
            exports.append(row)
    # Availability is based on real loader-visible names. Check hash membership,
    # terminal chains, name hashes and bloom bits rather than trusting sections.
    visible={i for i,(n,b,v,s) in enumerate(symbols) if n and s and b in (1,2,10) and v in (0,3)}
    if 4 in tags:
        nb,nc=struct.unpack('<II',virtual(tags[4],8));words=struct.unpack('<'+str(nb+nc)+'I',virtual(tags[4]+8,4*(nb+nc)));buckets0=words[:nb];chain=words[nb:];seen={}
        for bucket,start in enumerate(buckets0):
            cursor=start;local=set()
            while cursor:
                _need(cursor not in local and len(local)<symbol_count,'SysV lookup cycle');local.add(cursor)
                if cursor in seen:_need(seen[cursor]==bucket,'SysV cross-bucket chain');break
                seen[cursor]=bucket;_need(elfhash(symbols[cursor][0])%nb==bucket,'SysV name/hash mismatch');cursor=chain[cursor]
        _need(visible<=set(seen),'SysV export missing from lookup')
    if 0x6ffffef5 in tags:
        address=tags[0x6ffffef5];nb,first,nbloom,shift=struct.unpack('<IIII',virtual(address,16));bloomwords=struct.unpack('<'+str(nbloom)+'Q',virtual(address+16,8*nbloom));bs=struct.unpack('<'+str(nb)+'I',virtual(address+16+8*nbloom,4*nb));chain=struct.unpack('<'+str(symbol_count-first)+'I',virtual(address+16+8*nbloom+4*nb,4*(symbol_count-first)))
        _need(visible<=set(range(first,symbol_count)),'GNU export missing from lookup');group=first;cache={}
        for i in range(first,symbol_count):
            name=symbols[i][0]
            if name not in cache:
                h=5381
                for c in name.encode('ascii'):h=((h*33)+c)&0xffffffff
                cache[name]=h
            h=cache[name];_need(bs[h%nb]==group and chain[i-first]&~1==h&~1,'GNU name/bucket/hash mismatch');word=bloomwords[(h//64)&(nbloom-1)];_need(word&(1<<(h%64)) and word&(1<<((h>>shift)%64)),'GNU bloom missing symbol')
            if chain[i-first]&1:group=i+1
    unsupported=[]
    for tag,name in [(0x7ffffffd,'DT_AUXILIARY'),(0x7fffffff,'DT_FILTER'),(0x6ffffefc,'DT_AUDIT'),(0x6ffffefb,'DT_DEPAUDIT')]:
        if tag in tags:unsupported.append(name)
    # COPY looks up an external source although its receiving symbol is defined.
    # This SDK profile does not model that lookup or its object-size semantics.
    if 5 in relocation_kinds:unsupported.append('COPY_RELOCATIONS')
    if relocation_kinds-{1,5,6,7,16,17,18,36}:unsupported.append('OTHER_SYMBOL_RELOCATIONS')
    return dict(schema='panda-sdk-link-loader-metadata-v1',elf_sha256=hashlib.sha256(blob).hexdigest(),nbytes=len(blob),soname=name_at(tags[14]) if 14 in tags else None,needed=libraries,rpath=name_at(tags[15]) if 15 in tags else None,runpath=name_at(tags[29]) if 29 in tags else None,imports=imports,exports=exports,dynamic_symbol_count=symbol_count,relocation_count=relocation_count,relocation_kinds=sorted(relocation_kinds),version_needs=versions_need,version_definitions=versions_def,init_present=bool(tags.get(12) or tags.get(25)),ifunc_exports=sum(x['symbol_type']==10 for x in exports),unsupported_features=unsupported,section_headers_used=False,native_admitted=False,runtime_mapping_qualified=False)

def available_imports(root,providers):
    _need(type(providers) is list and len(providers)<=64,'provider budget');lookup={}
    for index,p in enumerate(providers):
        for s in p['exports']:lookup.setdefault(s['name'],[]).append((p,s,index))
    resolved=[];missing=[];weak=[]
    for r in root['imports']:
        matches=[]
        for p,s,index in lookup.get(r['name'],[]):
            if r['version'] is not None:
                if s['version']!=r['version'] or p['soname']!=r['version_library']:continue
            elif not s['default_version']:continue
            compatible=r['symbol_type']==0 or s['symbol_type']==r['symbol_type'] or r['symbol_type']==2 and s['symbol_type']==10
            if compatible:matches.append(p.get('path',p.get('soname') or 'provider-'+str(index)))
        row=dict(r,provider_candidates=sorted(set(matches)))
        if matches:resolved.append(row)
        elif r['binding']==2:weak.append(row)
        else:missing.append(row)
    unsupported=sorted(set(root.get('unsupported_features',[])+[x for p in providers for x in p.get('unsupported_features',[])]))
    return dict(schema='panda-sdk-symbol-availability-v1',root_strong_symbols_available=not missing and not unsupported,missing=missing,weak_unresolved=weak,resolved=resolved,unsupported_features=unsupported,scope='name/type/version availability in declared providers; no loader namespace/order/cache/interposition/object-layout certification',runtime_mapping_qualified=False,native_admitted=False)
