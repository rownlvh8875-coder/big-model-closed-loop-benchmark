"""Fresh component transfers and data-only closed offline context composition."""
import json
import stat
import urllib.parse
from scripts import engine_clock_image_transport as transport
import gzip
import hashlib
import io
import os
from pathlib import Path
import shutil
import tarfile
import time
import zipfile
from scripts import engine_clock_image_archive as archive


def need(v):
    if not v:raise ValueError('IMAGE_STAGING_REJECTED')


RETAINED_LOCK='docs/locks/engine-clock-retained-image-debs-01.lock.json'
RETAINED_SHA='5110e40b8bc3009783ec9d40c771c8ff7c958af4a1be4d6c42d4b4352ceee920'


class RetainedClient(transport.Client):
    """Keep safe failure facts that the v1 client otherwise held only in memory."""
    def _failure(self,operation,url,path=None):
        parsed=urllib.parse.urlsplit(url);public=urllib.parse.urlunsplit((parsed.scheme,parsed.hostname or '',parsed.path,'',''))
        latest=self.errors[-1] if self.errors else {}
        row={'operation':operation,'public_url':public,'http_status':latest.get('http_status'),'error_code':'IMAGE_TRANSPORT_REJECTED','partial_nbytes':None,'token_or_exception_text_preserved':False}
        if path is not None:
            partial=Path(path).with_name(Path(path).name+'.partial')
            try:
                info=partial.lstat()
                if stat.S_ISREG(info.st_mode):row['partial_nbytes']=info.st_size
            except FileNotFoundError:pass
        with (self.out/'failure-events.jsonl').open('a') as f:f.write(json.dumps(row,sort_keys=True)+'\n')
    def download(self,url,path,**kwargs):
        try:return super().download(url,path,**kwargs)
        except Exception:self._failure('download',url,path);raise
    def get_json(self,endpoint,name):
        try:return super().get_json(endpoint,name)
        except Exception:self._failure('api','https://api.github.com/repos/'+self.repository+'/'+endpoint);raise
    def registry_authenticate(self):
        try:return super().registry_authenticate()
        except Exception:self._failure('anonymous-registry-token','https://auth.docker.io/token');raise


def extract_retained_debs(path,dest,descriptor,registered_packages):
    """Copy exactly registered, pinned component members, never an input rootfs."""
    try:
        packages={Path(r['filename']).name:r for r in registered_packages};need(len(packages)==len(registered_packages))
        expected={}
        for row in descriptor['members']:
            name=row['filename'];member=row['member'];need(Path(name).name==name and member=='context/debs/'+name and member not in expected and name in packages)
            pin=packages[name];need(type(row['nbytes']) is int and row['nbytes']>0 and row['nbytes']==pin['nbytes'] and row['sha256']==pin['sha256']);expected[member]=row
        need(len(expected)==descriptor['member_count'] and sum(r['nbytes'] for r in expected.values())==descriptor['member_bytes'])
        total=0;selected={}
        with zipfile.ZipFile(path) as z:
            infos=z.infolist();need(len(infos)<=100000);names=set();decoded=0
            for info in infos:
                name=info.filename;need(name not in names and name and not name.startswith('/') and '..' not in name.split('/') and '\\' not in name and not info.flag_bits&1);names.add(name)
                need(0<=info.file_size<=512*1024**2);decoded+=info.file_size;need(decoded<=2*1024**3)
                if name not in expected:continue
                row=expected[name];need(not info.is_dir() and stat.S_IFMT(info.external_attr>>16) in (0,stat.S_IFREG) and info.file_size==row['nbytes']);digest=hashlib.sha256();count=0
                target=Path(dest)/row['filename'];fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
                with z.open(info) as source,os.fdopen(fd,'wb') as out:
                    for block in iter(lambda:source.read(1024**2),b''):
                        count+=len(block);need(count<=row['nbytes']);digest.update(block);out.write(block)
                need(count==row['nbytes'] and digest.hexdigest()==row['sha256']);total+=count;selected[name]=row
        need(set(selected)==set(expected));return {'status':'AUTHENTICATED_COMPONENT_MEMBERS_MATCH','member_count':len(selected),'member_bytes':total,'filenames':sorted(r['filename'] for r in selected.values()),'root_filesystem_extracted':False,'native_admission':False}
    except Exception:raise ValueError('IMAGE_RETAINED_INPUTS_REJECTED') from None


def download_retained_debs(client,rawdir,dest,descriptor,packages):
    rid=descriptor['run_id'];head=descriptor['activation_sha'];wid=descriptor['workflow_id']
    run=client.get_json('actions/runs/'+str(rid),'retained-run.json')
    need(run['id']==rid and run['head_sha']==head and run['head_branch']==descriptor['branch'] and run['event']=='push' and type(run['run_attempt']) is int and run['run_attempt']==1 and run['workflow_id']==wid and run['path']==descriptor['workflow_path'] and run['status']=='completed' and run['conclusion']==descriptor['run_conclusion']=='failure' and run['repository']['full_name']==descriptor['repository'])
    jobs=client.get_json('actions/runs/'+str(rid)+'/jobs?per_page=100','retained-jobs.json')
    need(jobs['total_count']==1 and len(jobs['jobs'])==1 and jobs['jobs'][0]['run_id']==rid and jobs['jobs'][0]['name']==descriptor['job_name'] and jobs['jobs'][0]['status']=='completed' and jobs['jobs'][0]['conclusion']=='failure')
    unique=client.get_json('actions/workflows/'+str(wid)+'/runs?branch='+descriptor['branch']+'&event=push&per_page=100','retained-unique.json')
    need(unique['total_count']==1 and len(unique['workflow_runs'])==1 and unique['workflow_runs'][0]['id']==rid and unique['workflow_runs'][0]['head_sha']==head and unique['workflow_runs'][0]['run_attempt']==1)
    art=client.get_json('actions/artifacts/'+str(descriptor['artifact_id']),'retained-artifact.json')
    need(art['id']==descriptor['artifact_id'] and art['name']==descriptor['artifact_name'] and art['expired'] is False and art['workflow_run']['id']==rid and art['workflow_run']['head_sha']==head and art['digest']=='sha256:'+descriptor['artifact_zip_sha256'] and art['size_in_bytes']==descriptor['artifact_zip_nbytes'])
    path=Path(rawdir)/'retained-original-execution.zip'
    client.download('https://api.github.com/repos/'+descriptor['repository']+'/actions/artifacts/'+str(descriptor['artifact_id'])+'/zip',path,nbytes=descriptor['artifact_zip_nbytes'],sha256=descriptor['artifact_zip_sha256'],kind='artifact')
    return extract_retained_debs(path,dest,descriptor,packages)


def verify_python_archive(path,entries,*,deadline):
    expected={r['path']:r for r in entries};need(len(expected)==len(entries) and len(entries)<=20000)
    seen=set();decoded=0;stop=min(deadline,time.perf_counter()+180)
    with tarfile.open(path,'r|gz') as t:
        for m in t:
            need(time.perf_counter()<stop);name=archive._path(m.name,True);need(name in expected and name not in seen);seen.add(name);r=expected[name]
            kind='file' if m.isfile() else 'directory' if m.isdir() else 'symlink' if m.issym() else None
            need(kind==r['kind'] and m.mode==r['mode'] and m.size==r['nbytes'])
            if kind=='file':
                need(0<=m.size<=512*1024**2);decoded+=m.size;need(decoded<=512*1024**2);h=hashlib.sha256();n=0
                with t.extractfile(m) as f:
                    for block in iter(lambda:f.read(1024**2),b''):need(time.perf_counter()<stop);n+=len(block);h.update(block)
                need(n==m.size and h.hexdigest()==r['sha256'])
            elif kind=='symlink':need(not m.linkname.startswith('/') and m.linkname==r['target']);archive._link(name,m.linkname)
    need(seen==set(expected));return {'status':'PYTHON_ARCHIVE_MEMBERS_MATCH','entries':len(seen),'decoded_bytes':decoded,'extracted':False}


def compose_base(config,compressed,output,base):
    from scripts.engine_clock_image_preparation import BASE_TAG,canonical
    layer=output.parent/'base-layer.tar';digest=hashlib.sha256();count=0
    with gzip.open(compressed,'rb') as src,layer.open('xb') as target:
        for block in iter(lambda:src.read(1024**2),b''):
            count+=len(block);need(count<=base['actual_base_tar_bytes']);digest.update(block);target.write(block)
    need(count==base['actual_base_tar_bytes'] and 'sha256:'+digest.hexdigest()==base['rootfs_diff_ids'][0])
    cfg=config.read_bytes();need(len(cfg)==base['config_nbytes'] and 'sha256:'+hashlib.sha256(cfg).hexdigest()==base['config_digest'])
    cp=base['config_digest'][7:]+'.json';lp=digest.hexdigest()+'/layer.tar'
    with tarfile.open(output,'w',format=tarfile.PAX_FORMAT) as t:
        for name,raw in [(cp,cfg),('manifest.json',canonical([{'Config':cp,'RepoTags':[BASE_TAG],'Layers':[lp]}]))]:
            m=tarfile.TarInfo(name);m.mode=0o644;m.size=len(raw);t.addfile(m,io.BytesIO(raw))
        m=tarfile.TarInfo(lp);m.mode=0o644;m.size=count
        with layer.open('rb') as f:t.addfile(m,f)
    checked=archive.inspect_save_archive(output,expected_tag=BASE_TAG,deadline=time.perf_counter()+180,environment_profile='base')
    need(checked['config_digest']==base['config_digest'] and checked['rootfs_diff_ids']==base['rootfs_diff_ids'])
    return checked


def stage_inputs(request,context,work,*,client,root):
    from scripts import engine_clock_image_preparation_v2 as p
    from scripts.engine_clock_wheel_derivative import derive_wheel
    root=Path(root);work=Path(work);ctx=work/'context';ctx.mkdir(mode=0o700);rawdir=work/'component-transports';rawdir.mkdir(mode=0o700)
    def lock(path,sha):
        raw=p.read_regular(root/path);need(hashlib.sha256(raw).hexdigest()==sha);return p.parse(raw)
    full=lock(p.INPUT_PATH,p.INPUT_SHA);renderer=lock(p.RENDERER_PATH,p.RENDERER_SHA);layout=lock(p.LAYOUT_PATH,p.LAYOUT_SHA);lock(p.EFFECTIVE_PATH,p.EFFECTIVE_SHA)
    for row in full['authority_files'].values():
        raw=p.read_regular(root/row['path']);need(len(raw)==row['nbytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'])
    def fetch(row,path,kind='public'):
        client.download(row['url'],path,nbytes=row['nbytes'],sha256=row['sha256'],kind=kind);return path
    (ctx/'debs').mkdir();(ctx/'wheels').mkdir()
    retained=lock(RETAINED_LOCK,RETAINED_SHA)
    need(retained['full_input_lock_sha256']==p.INPUT_SHA)
    reused=download_retained_debs(client,rawdir,ctx/'debs',retained,full['os']['packages'])
    reused_names=set(reused['filenames'])
    for r in full['os']['packages']:
        if Path(r['filename']).name not in reused_names:fetch(r,ctx/'debs'/Path(r['filename']).name)
    (work/'retained-components.json').write_bytes(p.canonical(reused))
    fetch(full['python'],ctx/'python.tar.gz','asset');fetch(full['assets'],ctx/'assets.zip','asset');fetch(full['wheel_install_tool'],ctx/'pip-tool.whl')
    members=p.parse(p.read_regular(root/layout['source_manifest']['path']))['entries']
    need(hashlib.sha256(p.read_regular(root/layout['source_manifest']['path'])).hexdigest()==layout['source_manifest']['sha256'])
    pycheck=verify_python_archive(ctx/'python.tar.gz',members,deadline=client.deadline)
    for row in renderer['wheels']:
        if row['origin']['kind']=='pypi-release-file-v1':fetch({**row,'url':row['origin']['url']},ctx/'wheels'/row['filename'])
    meta=full['local_wheel_remote_transports']['metadrive-headless'];src=fetch(meta['upstream'],rawdir/meta['upstream']['filename'])
    need(hashlib.sha256(p.read_regular(root/meta['transform_source']['path'])).hexdigest()==meta['transform_source']['sha256'])
    result,receipt=derive_wheel(p.read_regular(src,64*p.MIB),expected_source_sha256=meta['upstream']['sha256'],expected_metadata_sha256=meta['upstream']['metadata_sha256'],deadline=min(client.deadline,time.perf_counter()+180))
    need(type(result) is bytes and len(result)==meta['result']['nbytes'] and hashlib.sha256(result).hexdigest()==meta['result']['sha256'])
    (ctx/'wheels'/meta['result']['filename']).write_bytes(result);(rawdir/'derivation.json').write_bytes(p.canonical(receipt))
    bar=full['local_wheel_remote_transports']['progressbar'];rid=bar['run_id']
    run=client.get_json('actions/runs/'+str(rid),'progressbar-run.json')
    need(run['id']==rid and run['workflow_id']==bar['workflow_id'] and run['head_sha']==bar['activation_sha'] and run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='success' and run['repository']['full_name']==p.REPOSITORY)
    art=client.get_json('actions/artifacts/'+str(bar['artifact_id']),'progressbar-artifact.json')
    need(art['id']==bar['artifact_id'] and art['name']==bar['artifact_name'] and art['expired'] is False and art['workflow_run']['id']==rid and art['workflow_run']['head_sha']==bar['activation_sha'] and art['digest']=='sha256:'+bar['artifact_zip_sha256'] and art['size_in_bytes']==bar['artifact_zip_nbytes'])
    zpath=rawdir/'progressbar-original-artifact.zip'
    client.download(bar['archive_url'],zpath,nbytes=bar['artifact_zip_nbytes'],sha256=bar['artifact_zip_sha256'],kind='artifact')
    with zipfile.ZipFile(zpath) as z:
        rows=[r for r in z.infolist() if r.filename==bar['member']];need(len(rows)==1 and rows[0].file_size==bar['nbytes'] and not rows[0].flag_bits&1)
        with z.open(rows[0]) as f:raw=f.read(bar['nbytes']+1)
        need(len(raw)==bar['nbytes'] and hashlib.sha256(raw).hexdigest()==bar['sha256'])
    (ctx/'wheels'/bar['member']).write_bytes(raw)
    need({f.name for f in (ctx/'wheels').iterdir()}=={r['filename'] for r in renderer['wheels']})
    client.registry_authenticate();base=full['base'];config=rawdir/'base-config.json';compressed=rawdir/'base-layer.tar.gz'
    for desc,path in [({'digest':base['config_digest'],'size':base['config_nbytes']},config),(base['layers'][0],compressed)]:
        client.download('https://registry-1.docker.io/v2/library/ubuntu/blobs/'+desc['digest'],path,nbytes=desc['size'],sha256=desc['digest'][7:],kind='registry')
    base_archive=work/'base-save.tar';basecheck=compose_base(config,compressed,base_archive,base)
    def copy(relative,dest):
        raw=p.read_regular(root/relative);dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(raw)
        dest.chmod(0o644)
    copy(p.RENDERER_PATH,ctx/'renderer-wheels.lock.json');copy(p.LAYOUT_PATH,ctx/'python-layout.json');copy(p.EFFECTIVE_PATH,ctx/'effective-inputs.lock.json')
    copy('scripts/engine_clock_image_installer.py',ctx/'installer.py')
    for name in ['__init__.py','engine_clock_image_process.py']:copy('scripts/'+name,ctx/'scripts'/name)
    for name in ['__init__.py','engine_clock_runtime_inventory.py','engine_clock_image_inventory.py','engine_clock_image_installer.py']:copy('scripts/'+name,ctx/'collector/scripts'/name)
    recipe=p.read_regular(root/'docker/engine-clock-sealed-image.Dockerfile');(ctx/'Dockerfile').write_bytes(recipe)
    sums=[];total=0
    for f in sorted(ctx.rglob('*')):
        if f.is_file():
            total+=f.stat().st_size;need(total<=request['budget']['context_bytes'])
            h=hashlib.sha256()
            with f.open('rb') as stream:
                for block in iter(lambda:stream.read(p.MIB),b''):h.update(block)
            sums.append(h.hexdigest()+'  '+f.relative_to(ctx).as_posix())
    (ctx/'checksums.sha256').write_text('\n'.join(sums)+'\n')
    total=sum(f.stat().st_size for f in work.rglob('*') if f.is_file());need(total<=request['budget']['execution_bytes'])
    receipt={'status':'CLOSED_OFFLINE_CONTEXT_STAGED','context_bytes':sum(f.stat().st_size for f in ctx.rglob('*') if f.is_file()),'execution_bytes_before_build':total,'python_archive':pycheck,'base':basecheck,'http_gets':client.requests,'payload_bytes':client.payload_bytes,'native_admission':False}
    (work/'staging.json').write_bytes(p.canonical(receipt))
    return {'context':ctx,'base_archive':base_archive,'base_config_digest':base['config_digest'],'base_diff_ids':base['rootfs_diff_ids'],'recipe_sha256':hashlib.sha256(recipe).hexdigest(),'renderer':renderer}
