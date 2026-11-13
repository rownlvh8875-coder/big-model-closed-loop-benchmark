"""Bounded Docker-save bytes and externally acquired API/launch proof semantics.

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


def _layer(stream,remaining,member_budget,check):
    reader=_LayerReader(stream,remaining,check);seen=set();last_end=0;regular=0
    with tarfile.open(fileobj=reader,mode='r|') as archive:
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
            stream.seek(0);files={};metadata={};kinds={};metadata_bytes=0;outer_end=0
            with tarfile.open(fileobj=stream,mode='r:') as outer:
                for member in outer:
                    check();outer_end=member.offset_data+((member.size+511)//512)*512;name=_path(member.name,True);_need(name not in kinds and len(kinds)<1024 and (member.isfile() or member.isdir()));kinds[name]='directory' if member.isdir() else 'file'
                    if member.isdir():_need(member.size==0);continue
                    _need(0<=member.size<=MAX_ARCHIVE_BYTES);hasher=hashlib.sha256();raw=bytearray();keep=name in ('manifest.json','index.json','oci-layout','repositories') or name.endswith('.json') or (name.startswith('blobs/sha256/') and member.size<=MAX_JSON_BYTES)
                    with outer.extractfile(member) as payload:
                        count=0
                        for block in iter(lambda:payload.read(CHUNK),b''):
                            check();count+=len(block);hasher.update(block)
                            if keep:raw.extend(block);_need(len(raw)<=MAX_JSON_BYTES)
                    _need(count==member.size);files[name]={'nbytes':count,'sha256':hasher.hexdigest()}
                    if keep and (not name.startswith('blobs/sha256/') or raw.startswith(b'{')):metadata_bytes+=len(raw);_need(metadata_bytes<=MAX_METADATA_BYTES);metadata[name]=bytes(raw)
            tail=before.st_size-outer_end;_need(1024<=tail<=CHUNK);stream.seek(outer_end);_need(not any(stream.read(tail)))
            _need('manifest.json' in metadata or 'index.json' in metadata)
            for name in kinds:
                parts=name.split('/')
                for n in range(1,len(parts)):_need(kinds.get('/'.join(parts[:n]))!='file')
            allowed=set();oci=None;layout='docker-save-legacy'
            if 'index.json' in metadata:
                _need(_json(metadata['oci-layout'])=={'imageLayoutVersion':'1.0.0'});index=_json(metadata['index.json']);_need(index['schemaVersion']==2 and len(index['manifests'])==1);desc=index['manifests'][0]
                if 'platform' in desc:_need(desc['platform'].get('os')=='linux' and desc['platform'].get('architecture')=='amd64' and desc['platform'].get('variant') in (None,''))
                annotation=desc.get('annotations',{}).get('org.opencontainers.image.ref.name');_need(annotation in (None,expected_tag))
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
                repo,tag=expected_tag.rsplit(':',1);_need(_json(metadata['repositories'])=={repo:{tag:layers[-1].split('/')[0]}});allowed.add('repositories')
            _need(set(files)==allowed)
            environment={}
            for value in config.get('config',{}).get('Env',[]):
                name,sep,v=value.partition('=');_need(sep and name not in environment);environment[name]=v
            _need(environment_profile in ("renderer","base") and environment==(IMAGE_ENV if environment_profile=="renderer" else {"PATH":IMAGE_ENV["PATH"]}))
            stream.seek(0);remaining=[MAX_LAYER_BYTES];member_budget=[MAX_LAYER_MEMBERS];audits={}
            with tarfile.open(fileobj=stream,mode='r:') as outer:
                for member in outer:
                    check();name=_path(member.name,True)
                    if name not in layers:continue
                    with outer.extractfile(member) as payload:audits[name]=_layer(payload,remaining,member_budget,check)
            _need([audits[p]['diff_id'] for p in layers]==diffids and _signature(os.fstat(stream.fileno()))==_signature(before))
        return {'schema':'engine-clock-save-archive-check-v1','status':'DOCKER_SAVE_STRUCTURE_VERIFIED','image_tar_sha256':full.hexdigest(),'image_tar_nbytes':before.st_size,'config_digest':'sha256:'+files[cp]['sha256'],'rootfs_diff_ids':diffids,'platform':'linux/amd64','archive_layout':layout,'layers':[{'path':p,**files[p],**audits[p]} for p in layers],'decoded_layer_bytes':MAX_LAYER_BYTES-remaining[0],'layer_member_count':MAX_LAYER_MEMBERS-member_budget[0],'config_environment':environment,'native_admission':False,'installed_runtime_verified':False}
    except Exception:raise ValueError('IMAGE_ARCHIVE_REJECTED') from None


def validate_preparation(receipt:dict,api_evidence:dict,archive:Path,*,expected:dict)->dict:
    try:
        def need(value):_need(value,'IMAGE_PREPARATION_REJECTED')
        need(all(type(expected[k]) is int and expected[k]>0 for k in ('run_id','workflow_id','artifact_id','artifact_zip_nbytes')) and expected['artifact_zip_nbytes']<=MAX_ARCHIVE_BYTES)
        need(all(_hex(expected[k],40) for k in ('activation_sha','source_sha')) and all(_hex(expected[k]) for k in ('artifact_zip_sha256','lock_sha256','recipe_sha256','installed_files_sha256')))
        run=api_evidence['run'];wf=api_evidence['workflow'];jobs=api_evidence['jobs'];arts=api_evidence['artifacts'];unique=api_evidence['unique_runs']
        need(run['id']==expected['run_id'] and run['workflow_id']==expected['workflow_id'] and run['path']==expected['workflow_path'] and run['head_sha']==expected['activation_sha'] and run['head_branch']==expected['branch'] and run['event']=='push' and type(run['run_attempt']) is int and run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='success' and run['repository']['full_name']==expected['repository'])
        need(wf['id']==expected['workflow_id'] and wf['path']==expected['workflow_path'] and wf['state']=='active')
        need(type(jobs['total_count']) is int and jobs['total_count']==1 and len(jobs['jobs'])==1 and all(j['run_id']==expected['run_id'] and j['name']=='prepare' and j['status']=='completed' and j['conclusion']=='success' for j in jobs['jobs']))
        need(type(unique['total_count']) is int and unique['total_count']==1 and len(unique['workflow_runs'])==1 and unique['workflow_runs'][0]['id']==expected['run_id'] and unique['workflow_runs'][0]['head_sha']==expected['activation_sha'] and unique['workflow_runs'][0]['head_branch']==expected['branch'] and type(unique['workflow_runs'][0]['run_attempt']) is int and unique['workflow_runs'][0]['run_attempt']==1)
        need(type(arts['total_count']) is int and arts['total_count']==2 and len(arts['artifacts'])==2 and {v['name'] for v in arts['artifacts']}=={expected['artifact_name'],expected['execution_artifact_name']} and all(v['expired'] is False and v['workflow_run']['id']==expected['run_id'] and v['workflow_run']['head_sha']==expected['activation_sha'] for v in arts['artifacts']))
        selected=[v for v in arts['artifacts'] if v['name']==expected['artifact_name']];need(len(selected)==1);artifact=selected[0];need(artifact['id']==expected['artifact_id'] and artifact['digest']=='sha256:'+expected['artifact_zip_sha256'] and artifact['size_in_bytes']==expected['artifact_zip_nbytes'])
        need(receipt['schema']=='engine-clock-image-candidate-v1' and receipt['status']=='IMAGE_CANDIDATE_PREPARED' and receipt['request_id']==expected['request_id'] and receipt['activation_sha']==expected['activation_sha'] and receipt['source_sha']==expected['source_sha'] and receipt['lock_sha256']==expected['lock_sha256'] and receipt['recipe_sha256']==expected['recipe_sha256'] and receipt['installed_files_sha256']==expected['installed_files_sha256'] and receipt['native_admission'] is False and type(receipt['official_model_calls']) is int and receipt['official_model_calls']==0)
        inspected=inspect_save_archive(archive,expected_tag=expected['image_tag'],deadline=perf_counter()+180)
        for key in ('image_tar_sha256','image_tar_nbytes','config_digest','rootfs_diff_ids','platform'):need(receipt[key]==inspected[key])
        return {'status':'PREPARATION_METADATA_AND_ARCHIVE_MATCH','archive':inspected,'artifact_id':artifact['id'],'external_api_origin_authenticated':False,'native_admission':False,'installed_runtime_verified':False}
    except Exception:raise ValueError('IMAGE_PREPARATION_REJECTED') from None


def validate_launch(actual:dict,expected:dict,nonce:str)->dict:
    try:
        def need(v):_need(v,'IMAGE_LAUNCH_REJECTED')
        need(_hex(nonce,32) and _hex(actual['container_id'],64) and actual['image_id']==expected['config_digest'])
        need(actual['read_only_rootfs'] is True and actual['privileged'] is False and actual['network_mode']=='none' and actual['cap_drop']==['ALL'] and actual['security_opt']==['no-new-privileges'] and actual['pid_mode']=='' and actual['ipc_mode']=='private')
        need(actual['pids_limit']==128 and actual['memory_bytes']==2147483648 and actual['nano_cpus']==2000000000 and actual['devices']==[] and actual['device_requests']==[] and actual['binds']==[])
        need(actual['tmpfs']=={'/tmp':'rw,nosuid,nodev,noexec,size=67108864,mode=0700'})
        need(type(actual['mounts']) is list and (actual['mounts']==[] or actual['mounts']==[{'type':'tmpfs','destination':'/tmp','rw':True}]))
        need(actual['entrypoint']==['/opt/venv/bin/python'] and actual['command']==expected['command'] and actual['user']=='0:0' and actual['working_dir']=='/' and actual['env']==IMAGE_ENV and type(actual['unknown_env_count']) is int and actual['unknown_env_count']==0)
        need(actual['labels']['stage7.request']==expected['request_id'] and actual['labels']['stage7.nonce']==nonce)
        if 'source_sha' in expected:need(actual['labels']['stage7.source']==expected['source_sha'])
        return {'status':'CLOSED_IMAGE_LAUNCH_METADATA_MATCH','container_id':actual['container_id'],'image_id':actual['image_id'],'nonce':nonce,'native_admission':False,'installed_runtime_verified':False}
    except Exception:raise ValueError('IMAGE_LAUNCH_REJECTED') from None


def verify_tree_archive(path:Path,expected_entries:list[dict],*,prefix:str,deadline:float)->dict:
    """Compare a stopped container's closed copied tree as data, without extraction."""
    try:
        _need(type(deadline) in (int,float) and math.isfinite(deadline));stop=min(deadline,perf_counter()+180)
        def check():_need(perf_counter()<stop)
        check();prefix=_path(prefix);_need('/' not in prefix and type(expected_entries) is list and len(expected_entries)<=MAX_LAYER_MEMBERS)
        expected={};expected_bytes=0
        for row in expected_entries:
            name=_path(row['path'],True);_need(name not in expected and row['kind'] in ('file','directory','symlink'))
            if name=='.':_need(row['kind']=='directory');continue
            if row['kind']=='file':_need(type(row['nbytes']) is int and 0<=row['nbytes']<=MAX_FILE_BYTES and _hex(row['sha256']));expected_bytes+=row['nbytes']
            elif row['kind']=='symlink':_link(name,row['target'])
            expected[name]=row
        _need(expected_bytes<=MAX_FILE_BYTES);observed={};outer_end=0
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            before=os.fstat(stream.fileno());_need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=MAX_FILE_BYTES and before.st_size%512==0);archive_hash=hashlib.sha256()
            for block in iter(lambda:stream.read(CHUNK),b''):check();archive_hash.update(block)
            stream.seek(0)
            with tarfile.open(fileobj=stream,mode='r:') as tar:
                for member in tar:
                    check();outer_end=member.offset_data+((member.size+511)//512)*512;name=_path(member.name,True)
                    if name in ('.',prefix):_need(member.isdir());continue
                    _need(name.startswith(prefix+'/'));name=name[len(prefix)+1:];_need(name not in observed and len(observed)<MAX_LAYER_MEMBERS and (member.isfile() or member.isdir() or member.issym() or member.islnk()))
                    if member.isdir() and name not in expected:
                        _need(any(p.startswith(name+'/') for p in expected));continue
                    _need(name in expected);row={'kind':'file' if member.isfile() else 'directory' if member.isdir() else 'symlink' if member.issym() else 'hardlink','mode':member.mode,'nbytes':member.size}
                    if member.isfile():
                        _need(0<=member.size<=MAX_FILE_BYTES);digest=hashlib.sha256();count=0
                        with tar.extractfile(member) as data:
                            for block in iter(lambda:data.read(CHUNK),b''):check();count+=len(block);_need(count<=member.size);digest.update(block)
                        _need(count==member.size);row['sha256']=digest.hexdigest()
                    elif member.issym():_link(name,member.linkname);row['target']=member.linkname
                    elif member.islnk():
                        target=_path(member.linkname);_need(target.startswith(prefix+'/'));row['target']=target[len(prefix)+1:]
                    observed[name]=row
            tail=before.st_size-outer_end;_need(1024<=tail<=CHUNK);stream.seek(outer_end);_need(not any(stream.read(tail)) and _signature(os.fstat(stream.fileno()))==_signature(before))
        def resolve(name,seen):
            _need(name in observed and name not in seen and len(seen)<40);row=observed[name]
            if row['kind']!='hardlink':return row
            target=resolve(row['target'],seen|{name});_need(target['kind']=='file');return {**target,'mode':row['mode']}
        _need(set(observed)==set(expected))
        for name,row in expected.items():
            actual=resolve(name,set());_need(actual['kind']==row['kind'] and actual['mode']==row['mode'])
            if row['kind']=='file':_need(actual['nbytes']==row['nbytes'] and actual['sha256']==row['sha256'])
            elif row['kind']=='symlink':_need(actual['target']==row['target'])
        return {'status':'CLOSED_COPIED_TREE_MATCH','archive_sha256':archive_hash.hexdigest(),'archive_nbytes':before.st_size,'prefix':prefix,'entries':len(observed),'file_bytes':expected_bytes,'payload_extracted':False,'native_admission':False,'external_container_origin_authenticated':False}
    except Exception:raise ValueError('IMAGE_TREE_REJECTED') from None


def extract_image_bundle(path:Path,destination:Path)->dict:
    """Extract only three authenticated carrier files, never a root filesystem."""
    import zipfile
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            before=os.fstat(stream.fileno());_need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=MAX_ARCHIVE_BYTES)
            with zipfile.ZipFile(stream) as z:
                rows=z.infolist();_need(len(rows)==3 and {r.filename for r in rows}=={'image.tar','preparation.json','installed-files.json'})
                _need(sum(r.file_size for r in rows)<=MAX_ARCHIVE_BYTES)
                for r in rows:_need(not r.flag_bits&1 and not r.is_dir() and (r.external_attr>>16)&0o170000 in (0,0o100000) and 0<r.file_size<=(MAX_ARCHIVE_BYTES if r.filename=='image.tar' else 16*1024**2))
                destination=Path(destination);destination.mkdir(mode=0o700,exist_ok=False);files={}
                for r in rows:
                    digest=hashlib.sha256();count=0
                    with z.open(r) as src,(destination/r.filename).open('xb') as out:
                        for block in iter(lambda:src.read(CHUNK),b''):
                            count+=len(block);_need(count<=r.file_size);out.write(block);digest.update(block)
                    _need(count==r.file_size);files[r.filename]={'nbytes':count,'sha256':digest.hexdigest()}
                _need(_signature(before)==_signature(os.fstat(stream.fileno())))
        return {'status':'CLOSED_IMAGE_BUNDLE_EXTRACTED','files':files,'root_filesystem_extracted':False}
    except Exception:raise ValueError('IMAGE_BUNDLE_REJECTED') from None
