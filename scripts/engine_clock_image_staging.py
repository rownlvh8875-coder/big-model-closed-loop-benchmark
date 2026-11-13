"""Fresh component transfers and data-only closed offline context composition."""
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
    from scripts import engine_clock_image_preparation as p
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
    for r in full['os']['packages']:fetch(r,ctx/'debs'/Path(r['filename']).name)
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
