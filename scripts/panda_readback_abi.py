"""Static byte-level qualification of one pinned Linux amd64 Panda call ABI.

No ELF loading, patching, runtime mapping admission or engine imports. Structural
inspection is deliberately separate from exact pinned identity qualification.
"""
import hashlib
import struct

ELF_SHA='f38e0734a5344eda9a11e3024695febf2cea0177aa80985b67ceef5837a088d7'
METHOD_SHA='f2b072cf0eec59f8972329124719f328d442cea81134d6058afba4c4f7b7f90d'
GSG='_ZN23GLGraphicsStateGuardian23framebuffer_copy_to_ramEP7TextureiiPK13DisplayRegionRK12RenderBuffer'
METHOD=0x62c50
METHOD_BYTES=4227
CALL=0x6305c
PLT=0x29aa0
GOT=0xcc550

def need(ok,message):
    if not ok:raise ValueError(message)

def inspect_elf(blob):
    """Bounded structural inspection, never sufficient to qualify foreign bytes."""
    need(type(blob) is bytes and 64<=len(blob)<=2*1024*1024,'ELF size')
    def extent(offset,size):
        need(0<=offset<=len(blob) and 0<=size<=len(blob)-offset,'file extent')
        return blob[offset:offset+size]
    def unpack(fmt,offset):
        s=struct.Struct(fmt);return s.unpack(extent(offset,s.size))
    h=unpack('<16sHHIQQQIHHHHHH',0)
    need(h[0][:7]==b'\x7fELF\x02\x01\x01' and h[1:4]==(3,62,1) and h[8:10]==(64,56) and h[11]==64,'ELF64LE amd64 DYN header')
    need(1<=h[10]<=32 and 1<=h[12]<=128 and h[13]<h[12],'header table counts')
    extent(h[5],h[10]*56);extent(h[6],h[12]*64)
    loads=[]
    for i in range(h[10]):
        p=unpack('<IIQQQQQQ',h[5]+56*i)
        if p[0]!=1:continue
        kind,flags,offset,va,_,size,memsize,alignment=p
        need(size<=memsize and memsize<2**64-va and flags&~7==0,'load extent/flags')
        extent(offset,size)
        need(alignment in (0,1) or alignment&(alignment-1)==0,'load alignment')
        if alignment>1:need((va-offset)%alignment==0,'load congruence')
        for old in loads:need(not (va<old[3]+old[6] and old[3]<va+memsize),'overlapping virtual loads')
        loads.append(p)
    def virtual(va,size,*,executable=False):
        matches=[p for p in loads if p[3]<=va and size<=p[5] and va-p[3]<=p[5]-size]
        need(len(matches)==1,'unique file-backed virtual span')
        p=matches[0]
        if executable:need(p[1]&1 and not p[1]&2,'immutable executable code')
        return extent(p[2]+va-p[3],size)
    code=virtual(METHOD,METHOD_BYTES,executable=True)
    call=virtual(CALL,5,executable=True)
    need(call[0]==0xe8 and CALL+5+struct.unpack('<i',call[1:])[0]==PLT,'direct GL call target')
    plt=virtual(PLT,6,executable=True)
    need(plt[:2]==b'\xff\x25' and PLT+6+struct.unpack('<i',plt[2:])[0]==GOT,'PLT/GOT route')
    virtual(GOT,8)
    sections=[unpack('<IIQQQQIIQQ',h[6]+64*i) for i in range(h[12])]
    for s in sections:
        if s[1]!=8:extent(s[4],s[5])
    dynamics=[i for i,s in enumerate(sections) if s[1]==11]
    need(len(dynamics)==1,'unique dynamic symbol table')
    dynamic_index=dynamics[0];s=sections[dynamic_index]
    need(s[9]==24 and s[5]%24==0 and 1<=s[5]//24<=65536 and s[6]<len(sections),'dynamic symbol extent')
    strings=sections[s[6]];need(strings[1]==3 and strings[5]<=1024*1024,'symbol string table')
    names=extent(strings[4],strings[5]);symbols=[]
    for i in range(s[5]//24):
        sym=unpack('<IBBHQQ',s[4]+24*i);name=sym[0]
        need(name<len(names),'symbol name offset');end=names.find(b'\0',name)
        need(end>=name,'terminated symbol name')
        symbols.append((names[name:end],sym))
    gl=[i for i,(name,sym) in enumerate(symbols) if name==b'glReadPixels']
    gsg=[sym for name,sym in symbols if name==GSG.encode()]
    need(len(gl)==1 and len(gsg)==1,'unique boundary symbols')
    gs=gsg[0];imp=symbols[gl[0]][1]
    need(gs[1]==18 and gs[2]==0 and gs[3]!=0 and gs[4:]==(METHOD,METHOD_BYTES),'GSG function binding')
    need(imp[1]==18 and imp[2]==0 and imp[3:]==(0,0,0),'GL function import')
    got_relocations=[]
    for s in sections:
        if s[1]!=4:continue
        need(s[9]==24 and s[5]%24==0 and s[5]//24<=65536,'relocation extent')
        for i in range(s[5]//24):
            va,info,addend=unpack('<QQq',s[4]+24*i)
            if va==GOT:got_relocations.append((s[6],info>>32,info&0xffffffff,addend))
    need(got_relocations==[(dynamic_index,gl[0],7,0)],'unique GL JUMP_SLOT relocation')
    return dict(method_va=METHOD,method_nbytes=METHOD_BYTES,method_sha256=hashlib.sha256(code).hexdigest(),
        call_va=CALL,return_va=CALL+5,plt_va=PLT,got_va=GOT,elf_sha256=hashlib.sha256(blob).hexdigest(),
        pinned_identity_matched=False,file_call_abi_bound=False,runtime_mapping_bound=False,runtime_admission_ready=False,
        original_gpu_bytes_observed=False,abi='Linux-amd64-SysV',
        registers=dict(texture='rbx',gsg='rbp',capacity='r12',pixel_pointer='r15'),
        original_stack_argument_offset=8,caller_z_offset=28,caller_view_offset=48,
        accepted_view=0,accepted_z=-1,
        caveats=['Structural validity alone never qualifies arbitrary ELF bytes.',
                 'Runtime mapped code/dispatch and actual allocation/cached-state/camera/receipt suppliers remain unqualified.'])

def qualify_elf(blob):
    need(type(blob) is bytes and len(blob)==913073 and hashlib.sha256(blob).hexdigest()==ELF_SHA,'exact pinned libpandagl identity')
    result=inspect_elf(blob)
    need(result['method_sha256']==METHOD_SHA,'pinned method code')
    result.update(pinned_identity_matched=True,file_call_abi_bound=True)
    return result
