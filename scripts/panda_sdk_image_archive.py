"""Versioned COPY-image Docker-save DATA verifier; original v2 remains unchanged.

Reads data only. No network, Docker, filesystem payload extraction or package
imports. Dictionary proofs alone never authenticate their external origin.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import posixpath
import re
import stat
import tarfile
from time import perf_counter
import zlib

MAX_ARCHIVE_BYTES=2*1024**3
MAX_LAYER_BYTES=3*1024**3
MAX_LAYER_MEMBERS=100000
MAX_FILE_BYTES=512*1024**2
MAX_JSON_BYTES=4*1024**2
MAX_METADATA_BYTES=16*1024**2
CHUNK=1024**2
MAX_EXTENSION_BYTES=1024**2
MAX_EXTENSION_RECORD_BYTES=65536
RENDER_ENV={'LIBGL_ALWAYS_SOFTWARE':'1','PYOPENGL_PLATFORM':'glx','OMP_NUM_THREADS':'2'}
IMAGE_ENV={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',**RENDER_ENV}


def _need(value,code='IMAGE_ARCHIVE_REJECTED'):
    if not value:raise ValueError(code)


def _pairs(values):
    result={}
    for key,value in values:_need(key not in result);result[key]=value
    return result


def _json(raw):
    _need(len(raw)<=MAX_JSON_BYTES)
    return json.loads(raw,object_pairs_hook=_pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('IMAGE_ARCHIVE_REJECTED')))


def _sha(data):return hashlib.sha256(data).hexdigest()

def _hex(value,n=64):return type(value) is str and re.fullmatch('[0-9a-f]{'+str(n)+'}',value) is not None

def _digest(value):return type(value) is str and value.startswith('sha256:') and _hex(value[7:])


def _path(name,root=False):
    _need(type(name) is str)
    if name.startswith('./'):name=name[2:]
    name=name.rstrip('/')
    if root and name in ('','.'):return '.'
    _need(0<len(name.encode('utf-8'))<=4096 and not name.startswith('/') and '\\' not in name and len(name.split('/'))<=256)
    _need(all(v not in ('','.','..') for v in name.split('/')) and all(ord(c)>=32 and ord(c)!=127 for c in name))
    return name


def _link(path,target,hard=False):
    _need(type(target) is str and 0<len(target.encode())<=4096 and '\\' not in target and '\0' not in target)
    if hard:return _path(target)
    parts=[] if target.startswith('/') else path.split('/')[:-1]
    for part in target.split('/'):
        if part in ('','.'):continue
        if part=='..':_need(bool(parts));parts.pop()
        else:parts.append(part)
    return '/'.join(parts)


def _signature(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)


def tar_bounds():
    return dict(metadata=MAX_METADATA_BYTES,extensions=MAX_EXTENSION_BYTES,extension_records=1024,headers=MAX_LAYER_MEMBERS)


def bounded_tarinfo(bounds,check,file_limit):
    """Check raw headers BEFORE stdlib consumes hidden extension payloads.

    The same bounds object covers the outer object and all decoded layers.
    GNU sparse forms are excluded before their internal parsing as well.
    """
    class BoundedTarInfo(tarfile.TarInfo):
        def _reject_sparse(self,*args):
            raise ValueError('GNU sparse payload/map parsing is unsupported')
        _proc_gnusparse_00=_reject_sparse
        _proc_gnusparse_01=_reject_sparse
        _proc_gnusparse_10=_reject_sparse
        def _proc_member(self,container):
            check();bounds['headers']-=1;_need(bounds['headers']>=0)
            _need(0<=self.size<=file_limit)
            if self.type in (tarfile.XHDTYPE,tarfile.XGLTYPE,tarfile.SOLARIS_XHDTYPE,tarfile.GNUTYPE_LONGNAME,tarfile.GNUTYPE_LONGLINK):
                limit=4097 if self.type in (tarfile.GNUTYPE_LONGNAME,tarfile.GNUTYPE_LONGLINK) else MAX_EXTENSION_RECORD_BYTES
                _need(self.size<=limit);bounds['metadata']-=self.size;bounds['extensions']-=self.size;bounds['extension_records']-=1
                _need(bounds['metadata']>=0 and bounds['extensions']>=0 and bounds['extension_records']>=0)
            else:
                _need(self.type in (tarfile.REGTYPE,tarfile.AREGTYPE,tarfile.CONTTYPE,tarfile.DIRTYPE,tarfile.SYMTYPE,tarfile.LNKTYPE))
            return super()._proc_member(container)
    return BoundedTarInfo


class _LayerReader:
    def __init__(self,stream,budget,check):
        self.stream=stream;self.budget=budget;self.check=check;self.pending=stream.read(2);self.gzip=self.pending==b'\x1f\x8b';self.decoder=zlib.decompressobj(31) if self.gzip else None;self.done=False;self.nbytes=0;self.hasher=hashlib.sha256();self.tail=b''
    def read(self,n=-1):
        self.check();n=min(CHUNK,n if n>=0 else CHUNK);result=bytearray()
        if n==0:return b''
        if self.done:return b''
        if self.gzip:
            while len(result)<n and not self.done:
                self.check()
                if not self.pending:self.pending=self.stream.read(CHUNK)
                _need(self.pending or self.decoder.eof)
                if self.decoder.eof:self.done=True;break
                limit=min(n-len(result),self.budget[0]-len(result)+1);_need(limit>0)
                result.extend(self.decoder.decompress(self.pending,limit));self.pending=self.decoder.unconsumed_tail
                _need(not self.decoder.unused_data and len(result)<=self.budget[0])
                if self.decoder.eof:_need(not self.pending and not self.stream.read(1));self.done=True
        else:
            take=min(n,len(self.pending));result.extend(self.pending[:take]);self.pending=self.pending[take:]
            if len(result)<n:result.extend(self.stream.read(min(n-len(result),self.budget[0]-len(result)+1)))
            if not result:self.done=True
        _need(len(result)<=self.budget[0]);raw=bytes(result);self.budget[0]-=len(raw);self.nbytes+=len(raw);self.hasher.update(raw);self.tail=(self.tail+raw)[-CHUNK:];return raw


def _layer(stream,remaining,member_budget,check,bounds):
    reader=_LayerReader(stream,remaining,check);seen=set();last_end=0;regular=0
    with tarfile.open(fileobj=reader,mode='r|',tarinfo=bounded_tarinfo(bounds,check,MAX_FILE_BYTES)) as archive:
        for member in archive:
            check();_need(member_budget[0]>0);member_budget[0]-=1;name=_path(member.name,True);_need(name not in seen);seen.add(name)
            _need(member.isfile() or member.isdir() or member.issym() or member.islnk());_need(0<=member.size<=MAX_FILE_BYTES)
            if name=='.':_need(member.isdir())
            if member.issym() or member.islnk():_link(name,member.linkname,member.islnk())
            if member.isfile():regular+=member.size
            last_end=member.offset_data+((member.size+511)//512)*512
    while reader.read(CHUNK):pass
    tail=reader.nbytes-last_end;_need(1024<=tail<=CHUNK and not any(reader.tail[-tail:]))
    return {'diff_id':'sha256:'+reader.hasher.hexdigest(),'decoded_bytes':reader.nbytes,'members':len(seen),'regular_bytes':regular,'gzip':reader.gzip}


EMPTY_COMPAT_CONTAINER={'Hostname':'','Domainname':'','User':'','AttachStdin':False,'AttachStdout':False,'AttachStderr':False,'Tty':False,'OpenStdin':False,'StdinOnce':False,'Env':None,'Cmd':None,'Image':'','Volumes':None,'WorkingDir':'','Entrypoint':None,'OnBuild':None,'Labels':None}


def _same_json(left,right):
    return json.dumps(left,sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(right,sort_keys=True,separators=(',',':'),allow_nan=False)


def _canonical_reference(tag):
    if '/' not in tag:return 'docker.io/library/'+tag
    first=tag.split('/',1)[0]
    return tag if '.' in first or ':' in first or first=='localhost' else 'docker.io/'+tag


def _compatibility_metadata(files,metadata,extras,config,layers):
    """Recognize bounded non-authoritative Docker v1 JSON compatibility metadata."""
    if not extras:return 0
    _need(len(extras)==len(layers)<=32);nodes={}
    for name in extras:
        _need(name=='blobs/sha256/'+files[name]['sha256'] and name in metadata and files[name]['nbytes']<=65536)
        row=_json(metadata[name]);_need(type(row) is dict and _hex(row.get('id')) and row['id'] not in nodes and row.get('os')=='linux' and type(row.get('container_config')) is dict)
        _need(type(row.get('created')) is str and len(row['created'])<=64)
        if 'parent' in row:_need(_hex(row['parent']) and row['parent']!=row['id'])
        nodes[row['id']]=row
    parents={row['parent'] for row in nodes.values() if 'parent' in row}
    _need(parents<=set(nodes));heads=set(nodes)-parents;_need(len(heads)==1 and sum('parent' not in row for row in nodes.values())==1)
    head=next(iter(heads));visited=set();current=head
    while current is not None:
        _need(current in nodes and current not in visited);visited.add(current);row=nodes[current];current=row.get('parent')
    _need(visited==set(nodes))
    for node,row in nodes.items():
        required={'id','created','container_config','os'}|({'parent'} if 'parent' in row else set())
        if node==head:
            if 'docker_version' in config:
                _need(type(config['docker_version']) is str and re.fullmatch('[0-9A-Za-z.+_-]{1,64}',config['docker_version']) is not None and row.get('docker_version')==config['docker_version'])
                required.add('docker_version')
            _need(set(row)==required|{'architecture','config'} and row['architecture']=='amd64' and row['created']==config.get('created') and type(config.get('config')) is dict and _same_json({**row['config'],'OnBuild':row['config'].get('OnBuild')},{**EMPTY_COMPAT_CONTAINER,**config['config']}))
            _need(_same_json(row['container_config'],config.get('container_config',EMPTY_COMPAT_CONTAINER)))
        else:
            _need(set(row)==required and row['created']=='1970-01-01T00:00:00Z')
            _need(set(row['container_config']) in (set(EMPTY_COMPAT_CONTAINER),set(EMPTY_COMPAT_CONTAINER)-{'OnBuild'}) and _same_json({**row['container_config'],'OnBuild':row['container_config'].get('OnBuild')},EMPTY_COMPAT_CONTAINER))
    return len(extras)


def inspect_save_archive(path:Path,*,expected_tag:str,deadline:float,environment_profile="renderer")->dict:
    """Verify one closed Docker-save object; establish no installed/native admission."""
    try:
        _need(type(deadline) in (int,float) and math.isfinite(deadline));stop=min(deadline,perf_counter()+180)
        def check():_need(perf_counter()<stop)
        check();fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            before=os.fstat(stream.fileno());_need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=MAX_ARCHIVE_BYTES and before.st_size%512==0)
            full=hashlib.sha256()
            for block in iter(lambda:stream.read(CHUNK),b''):check();full.update(block)
            stream.seek(0);files={};metadata={};kinds={};bounds=tar_bounds();outer_end=0
            with tarfile.open(fileobj=stream,mode='r:',tarinfo=bounded_tarinfo(bounds,check,MAX_ARCHIVE_BYTES)) as outer:
                for member in outer:
                    check();outer_end=member.offset_data+((member.size+511)//512)*512;name=_path(member.name,True);_need(name not in kinds and len(kinds)<1024 and (member.isfile() or member.isdir()));kinds[name]='directory' if member.isdir() else 'file'
                    if member.isdir():_need(member.size==0);continue
                    _need(0<=member.size<=MAX_ARCHIVE_BYTES);hasher=hashlib.sha256();raw=bytearray();keep=name in ('manifest.json','index.json','oci-layout','repositories') or name.endswith('.json') or (name.startswith('blobs/sha256/') and member.size<=MAX_JSON_BYTES)
                    _need(not keep or member.size<=MAX_JSON_BYTES)
                    with outer.extractfile(member) as payload:
                        count=0
                        for block in iter(lambda:payload.read(CHUNK),b''):
                            check();count+=len(block);hasher.update(block)
                            if keep:raw.extend(block);_need(len(raw)<=MAX_JSON_BYTES)
                    _need(count==member.size);files[name]={'nbytes':count,'sha256':hasher.hexdigest()}
                    if keep and (not name.startswith('blobs/sha256/') or raw.startswith(b'{')):bounds['metadata']-=len(raw);_need(bounds['metadata']>=0);metadata[name]=bytes(raw)
            tail=before.st_size-outer_end;_need(1024<=tail<=CHUNK);stream.seek(outer_end);_need(not any(stream.read(tail)))
            _need('manifest.json' in metadata or 'index.json' in metadata)
            for name in kinds:
                parts=name.split('/')
                for n in range(1,len(parts)):_need(kinds.get('/'.join(parts[:n]))!='file')
            allowed=set();oci=None;layout='docker-save-legacy'
            if 'index.json' in metadata:
                _need(_json(metadata['oci-layout'])=={'imageLayoutVersion':'1.0.0'});index=_json(metadata['index.json']);_need(index['schemaVersion']==2 and len(index['manifests'])==1);desc=index['manifests'][0]
                if 'platform' in desc:_need(desc['platform'].get('os')=='linux' and desc['platform'].get('architecture')=='amd64' and desc['platform'].get('variant') in (None,''))
                annotations=desc.get('annotations',{});annotation=annotations.get('org.opencontainers.image.ref.name');image_name=annotations.get('io.containerd.image.name')
                if image_name is not None:_need(image_name==_canonical_reference(expected_tag))
                _need(annotation in (None,expected_tag) or (annotation==expected_tag.rsplit(':',1)[-1] and image_name==_canonical_reference(expected_tag)))
                def referenced(d):
                    _need(_digest(d['digest']) and type(d['size']) is int);name='blobs/sha256/'+d['digest'][7:];_need(name in files and files[name]['sha256']==d['digest'][7:] and files[name]['nbytes']==d['size']);allowed.add(name);return name
                oci=_json(metadata[referenced(desc)]);_need(oci['schemaVersion']==2);oc=referenced(oci['config']);ol=[referenced(d) for d in oci['layers']];allowed.update(('index.json','oci-layout'));layout='docker-save-oci-layout'
            if 'manifest.json' in metadata:
                manifest=_json(metadata['manifest.json']);_need(type(manifest) is list and len(manifest)==1);record=manifest[0];_need(set(record) in ({'Config','RepoTags','Layers'},{'Config','RepoTags','Layers','LayerSources'}));_need(record['RepoTags']==[expected_tag]);allowed.add('manifest.json')
                cp=_path(record['Config']);layers=[_path(p) for p in record['Layers']]
                if oci is not None:_need(cp==oc and layers==ol)
                if 'LayerSources' in record:
                    _need(type(record['LayerSources']) is dict and len(record['LayerSources'])<=len(layers))
                    for d in record['LayerSources'].values():_need(type(d) is dict and _digest(d['digest']) and not d.get('urls') and d['digest'][7:] in {files[p]['sha256'] for p in layers})
            else:_need(oci is not None);cp,layers=oc,ol
            _need(cp in metadata and 0<len(layers)<=32 and len(set(layers))==len(layers) and all(p in files for p in layers));allowed.update((cp,*layers));config=_json(metadata[cp]);_need(config['architecture']=='amd64' and config['os']=='linux' and config['rootfs']['type']=='layers')
            diffids=config['rootfs']['diff_ids'];_need(type(diffids) is list and len(diffids)==len(layers) and all(_digest(v) for v in diffids))
            for p in layers:
                if p.endswith('/layer.tar'):
                    for suffix in ('VERSION','json'):
                        q=p.rsplit('/',1)[0]+'/'+suffix
                        if q in files:allowed.add(q);_need(files[q]['nbytes']<=MAX_JSON_BYTES)
            if 'repositories' in metadata:
                repo,tag=expected_tag.rsplit(':',1);pointer=layers[-1].rsplit('/',1)[-1] if layers[-1].startswith('blobs/sha256/') else layers[-1].split('/')[0];_need(_json(metadata['repositories'])=={repo:{tag:pointer}});allowed.add('repositories')
            extras=set(files)-allowed;compatibility_files=0
            if extras:
                _need(oci is not None and 'manifest.json' in metadata)
                compatibility_files=_compatibility_metadata(files,metadata,extras,config,layers);allowed.update(extras)
            _need(set(files)==allowed)
            environment={}
            for value in config.get('config',{}).get('Env',[]):
                name,sep,v=value.partition('=');_need(sep and name not in environment);environment[name]=v
            _need(environment_profile in ("renderer","base") and environment==(IMAGE_ENV if environment_profile=="renderer" else {"PATH":IMAGE_ENV["PATH"]}))
            stream.seek(0);remaining=[MAX_LAYER_BYTES];member_budget=[MAX_LAYER_MEMBERS];audits={}
            # The outer bytes are read twice, but count their extension metadata
            # once against the cross-layer total; also bound the replay itself.
            with tarfile.open(fileobj=stream,mode='r:',tarinfo=bounded_tarinfo(tar_bounds(),check,MAX_ARCHIVE_BYTES)) as outer:
                for member in outer:
                    check();name=_path(member.name,True)
                    if name not in layers:continue
                    with outer.extractfile(member) as payload:audits[name]=_layer(payload,remaining,member_budget,check,bounds)
            _need([audits[p]['diff_id'] for p in layers]==diffids and _signature(os.fstat(stream.fileno()))==_signature(before))
        return {'schema':'engine-clock-save-archive-check-v1','status':'DOCKER_SAVE_STRUCTURE_VERIFIED','image_tar_sha256':full.hexdigest(),'image_tar_nbytes':before.st_size,'config_digest':'sha256:'+files[cp]['sha256'],'rootfs_diff_ids':diffids,'platform':'linux/amd64','archive_layout':layout,'compatibility_metadata_files':compatibility_files,'compatibility_metadata_authoritative':False,'layers':[{'path':p,**files[p],**audits[p]} for p in layers],'decoded_layer_bytes':MAX_LAYER_BYTES-remaining[0],'layer_member_count':MAX_LAYER_MEMBERS-member_budget[0],'config_environment':environment,'native_admission':False,'installed_runtime_verified':False}
    except Exception:raise ValueError('IMAGE_ARCHIVE_REJECTED') from None

