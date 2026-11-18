"""Separate recorded-model ZIP profile; original camera-canary caps stay fixed.

The ordinary ZIP parser mirrors the frozen canary parser with larger total
budgets. Raw-name/extra validation is shared; no archive content is executed.
"""
from pathlib import Path, PurePosixPath
import hashlib
import shutil
import stat
import struct
import tempfile
import zlib
from .full_s_recorded_worker import need
from .recorded_worker_archive import _name, _extra

CAP=384*1024**2
EXPANDED_CAP=512*1024**2


def _members(raw):
    end=raw.rfind(b'PK\x05\x06',max(0,len(raw)-65557))
    need(end>=0 and end+22<=len(raw),'complete ordinary ZIP directory trailer required')
    _,disk,cd_disk,n_disk,n,cd_size,cd_offset,comment=struct.unpack_from('<4s4H2IH',raw,end)
    need(disk==cd_disk==0 and 0<n==n_disk<=512 and cd_size<=1024**2 and
        cd_offset+cd_size==end and end+22+comment==len(raw),'bounded directory metadata before allocation required')
    rows=[];names=set();cursor=cd_offset;total=0
    for _ in range(n):
        need(cursor+46<=end,'complete central entry required')
        fields=struct.unpack_from('<4s6H3I5H2I',raw,cursor)
        sig,made,version,flags,method,mtime,mdate,crc,csize,size,nlen,xlen,clen,start,iattr,eattr,offset=fields
        need(sig==b'PK\x01\x02' and version<=20 and flags&~0x80e==0 and method in (0,8) and
             start==0 and 0<nlen<=512 and xlen<=4096 and clen<=1024 and
             cursor+46+nlen+xlen+clen<=end and size<=16*1024**2 and csize<=CAP and
             (not stat.S_IFMT(eattr>>16) or stat.S_ISREG(eattr>>16)),'bounded supported regular ZIP member required')
        spelling=raw[cursor+46:cursor+46+nlen];name=_name(spelling,flags);key=name.casefold()
        need(key not in names and all(parent.as_posix().casefold() not in names for parent in PurePosixPath(name).parents if str(parent)!='.') and
            not any(v.startswith(key+'/') for v in names),'unique portable ZIP namespace required')
        names.add(key);_extra(raw[cursor+46+nlen:cursor+46+nlen+xlen])
        cursor+=46+nlen+xlen+clen;total+=size
        need(total<=EXPANDED_CAP,'bounded uncompressed ZIP total required')
        need(offset+30<=cd_offset,'bounded local ZIP header required')
        local=struct.unpack_from('<4s5H3I2H',raw,offset)
        lsig,lver,lflags,lmethod,ltime,ldate,lcrc,lcsize,lsize,lnlen,lxlen=local
        data=offset+30+lnlen+lxlen;finish=data+csize
        need(lsig==b'PK\x03\x04' and lver==version and lflags==flags and lmethod==method and
            lnlen==nlen and lxlen<=4096 and finish<=cd_offset and
            raw[offset+30:offset+30+lnlen]==spelling,'exact local/central member association required')
        _extra(raw[offset+30+lnlen:data])
        if flags&8:
            need(lcrc in (0,crc) and lcsize in (0,csize) and lsize in (0,size),'bounded local descriptor fields required')
            descriptor=finish+4 if raw[finish:finish+4]==b'PK\x07\x08' else finish
            need(descriptor+12<=cd_offset and struct.unpack_from('<III',raw,descriptor)==(crc,csize,size),'exact compressed data descriptor required')
            finish=descriptor+12
        else:need((lcrc,lcsize,lsize)==(crc,csize,size),'exact original local sizes/CRC required')
        rows.append(dict(name=name,offset=offset,data=data,finish=finish,csize=csize,size=size,method=method,crc=crc))
    need(cursor==end,'exact bounded central directory required')
    ordered=sorted(rows,key=lambda r:r['offset']);position=0
    for row in ordered:
        need(row['offset']==position,'nonoverlapping complete local ZIP namespace required')
        position=row['finish']
    need(position==cd_offset,'no unregistered local ZIP data required')
    return rows


def extract_archive(archive,out,*,expected_sha256):
    archive=Path(archive)
    need(not archive.is_symlink() and archive.is_file() and archive.stat().st_size<=CAP,'bounded regular archive required')
    with archive.open('rb') as stream:raw=stream.read(CAP+1)
    need(len(raw)<=CAP and hashlib.sha256(raw).hexdigest()==expected_sha256,'immutable archive digest required')
    rows=_members(raw)  # Caps run before any central-directory object allocation.
    out=Path(out).absolute()
    need(not out.exists() and not out.is_symlink() and all(not p.is_symlink() for p in out.parents),'fresh nonsymlink extraction required')
    out.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='.'+out.name+'-partial-',dir=out.parent))
    try:
        for row in rows:
            payload=raw[row['data']:row['data']+row['csize']]
            if row['method']==0:
                need(row['size']==row['csize'],'exact stored member extent required');data=payload
            else:
                decoder=zlib.decompressobj(-15)
                data=decoder.decompress(payload,row['size']+1)
                need(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,'exact complete deflate stream required')
            need(len(data)==row['size'] and zlib.crc32(data)==row['crc'],'exact uncompressed extent/CRC required')
            path=staging/row['name'];path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as stream:stream.write(data)
        need(not out.exists() and not out.is_symlink(),'fresh publication destination required')
        staging.rename(out)
    finally:
        if staging.exists():shutil.rmtree(staging)
    return out
