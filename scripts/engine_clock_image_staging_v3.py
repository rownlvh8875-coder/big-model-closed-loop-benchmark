"""Closed complete-payload artifact transport and source-fresh image context."""
import hashlib
import json
import os
from pathlib import Path
import stat
import time
import zipfile
from scripts import engine_clock_image_archive as archive
from scripts.engine_clock_image_staging import verify_python_archive
from scripts.engine_clock_image_staging_v2 import RetainedClient

PAYLOAD_LOCK='docs/locks/engine-clock-retained-image-payloads-02.lock.json'
PAYLOAD_SHA='fd0483be76c1682081c50c3d02708e6a0af8b30a5947aa9324bfd3ed9720e3ee'
BASE_TAR_SHA='9d6eb992b55a035e58a8ef6321de6163043ee586e3eb78ed1f91da05caa9616c'


def need(value):
    if not value:raise ValueError('IMAGE_PAYLOADS_REJECTED')


def expected_payloads(full,renderer):
    result={}
    def add(name,row):
        need(name not in result);result[name]={'nbytes':row['nbytes'],'sha256':row['sha256']}
    for r in full['os']['packages']:add('context/debs/'+Path(r['filename']).name,r)
    for r in renderer['wheels']:add('context/wheels/'+r['filename'],r)
    for key,name in [('python','python.tar.gz'),('assets','assets.zip'),('wheel_install_tool','pip-tool.whl')]:add('context/'+name,full[key])
    add('base-save.tar',{'nbytes':80721920,'sha256':BASE_TAR_SHA})
    return result


def copy_bundle(path,work,descriptor,expected,*,deadline):
    """Authenticate whole carrier and copy only source-registered regular inputs."""
    try:
        rows={r['path']:r for r in descriptor['members']};need(len(rows)==len(descriptor['members'])==descriptor['member_count'] and set(rows)==set(expected))
        for name,row in rows.items():
            need(archive._path(name)==name and row['nbytes']==expected[name]['nbytes'] and row['sha256']==expected[name]['sha256'])
        need(sum(r['nbytes'] for r in rows.values())==descriptor['member_bytes'])
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            before=os.fstat(stream.fileno());need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size==descriptor['artifact_zip_nbytes']<=2*1024**3)
            h=hashlib.sha256()
            for block in iter(lambda:stream.read(1024**2),b''):need(time.perf_counter()<deadline);h.update(block)
            need(h.hexdigest()==descriptor['artifact_zip_sha256']);stream.seek(0);selected=set();names=set();decoded=0
            with zipfile.ZipFile(stream) as z:
                infos=z.infolist();need(len(infos)<=100000)
                for info in infos:
                    need(time.perf_counter()<deadline);name=info.filename
                    need(archive._path(name,True)==name.rstrip('/') and name not in names and not info.flag_bits&1);names.add(name);need(0<=info.file_size<=512*1024**2);decoded+=info.file_size;need(decoded<=2*1024**3)
                    if name not in rows:continue
                    row=rows[name];need(not info.is_dir() and stat.S_IFMT(info.external_attr>>16) in (0,stat.S_IFREG) and info.file_size==row['nbytes'])
                    target=Path(work)/name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700);digest=hashlib.sha256();count=0
                    with z.open(info) as source,target.open('xb') as dest:
                        for block in iter(lambda:source.read(1024**2),b''):
                            need(time.perf_counter()<deadline);count+=len(block);need(count<=row['nbytes']);dest.write(block);digest.update(block)
                    need(count==row['nbytes'] and digest.hexdigest()==row['sha256']);target.chmod(0o644);selected.add(name)
            need(selected==set(rows) and archive._signature(before)==archive._signature(os.fstat(stream.fileno())))
        return {'status':'COMPLETE_REGISTERED_PAYLOADS_MATCH','member_count':len(selected),'member_bytes':descriptor['member_bytes'],'root_filesystem_extracted':False,'native_admission':False}
    except Exception:raise ValueError('IMAGE_PAYLOADS_REJECTED') from None


def acquire_bundle(client,rawdir,descriptor):
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
    return path


def stage_inputs(request,context,work,*,client,root):
    from scripts import engine_clock_image_preparation_v3 as p
    root=Path(root);work=Path(work);ctx=work/'context';ctx.mkdir(mode=0o700);rawdir=work/'component-transports';rawdir.mkdir(mode=0o700)
    def lock(path,sha):
        raw=p.read_regular(root/path);need(hashlib.sha256(raw).hexdigest()==sha);return p.parse(raw)
    full=lock(p.INPUT_PATH,p.INPUT_SHA);renderer=lock(p.RENDERER_PATH,p.RENDERER_SHA);layout=lock(p.LAYOUT_PATH,p.LAYOUT_SHA);lock(p.EFFECTIVE_PATH,p.EFFECTIVE_SHA);descriptor=lock(PAYLOAD_LOCK,PAYLOAD_SHA)
    need(descriptor['full_input_lock_sha256']==p.INPUT_SHA and descriptor['renderer_lock_sha256']==p.RENDERER_SHA)
    for row in full['authority_files'].values():
        raw=p.read_regular(root/row['path']);need(len(raw)==row['nbytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'])
    path=acquire_bundle(client,rawdir,descriptor)
    reused=copy_bundle(path,work,descriptor,expected_payloads(full,renderer),deadline=client.deadline)
    members_raw=p.read_regular(root/layout['source_manifest']['path']);need(hashlib.sha256(members_raw).hexdigest()==layout['source_manifest']['sha256'])
    pycheck=verify_python_archive(ctx/'python.tar.gz',p.parse(members_raw)['entries'],deadline=client.deadline)
    basecheck=archive.inspect_save_archive(work/'base-save.tar',expected_tag=p.BASE_TAG,deadline=min(client.deadline,time.perf_counter()+180),environment_profile='base')
    need(basecheck['config_digest']==full['base']['config_digest'] and basecheck['rootfs_diff_ids']==full['base']['rootfs_diff_ids'] and basecheck['image_tar_sha256']==BASE_TAR_SHA)
    def copy(relative,dest):
        raw=p.read_regular(root/relative);dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(raw)
        dest.chmod(0o644)
    for source,name in [(p.RENDERER_PATH,'renderer-wheels.lock.json'),(p.LAYOUT_PATH,'python-layout.json'),(p.EFFECTIVE_PATH,'effective-inputs.lock.json')]:copy(source,ctx/name)
    copy('scripts/engine_clock_image_installer_v2.py',ctx/'installer.py')
    for name in ['__init__.py','engine_clock_image_process.py']:copy('scripts/'+name,ctx/'scripts'/name)
    for name in ['__init__.py','engine_clock_runtime_inventory.py','engine_clock_image_inventory.py','engine_clock_image_installer.py']:copy('scripts/'+name,ctx/'collector/scripts'/name)
    recipe=p.read_regular(root/'docker/engine-clock-sealed-image.Dockerfile');(ctx/'Dockerfile').write_bytes(recipe);sums=[];total=0
    for f in sorted(ctx.rglob('*')):
        if f.is_file():
            total+=f.stat().st_size;need(total<=request['budget']['context_bytes']);h=hashlib.sha256()
            with f.open('rb') as stream:
                for block in iter(lambda:stream.read(p.MIB),b''):h.update(block)
            sums.append(h.hexdigest()+'  '+f.relative_to(ctx).as_posix())
    (ctx/'checksums.sha256').write_text('\n'.join(sums)+'\n')
    execution=sum(f.stat().st_size for f in work.rglob('*') if f.is_file());need(execution<=request['budget']['execution_bytes'])
    (work/'staging.json').write_bytes(p.canonical({'status':'CLOSED_OFFLINE_CONTEXT_STAGED','context_bytes':total,'execution_bytes_before_build':execution,'retained_payloads':reused,'python_archive':pycheck,'base':basecheck,'http_gets':client.requests,'payload_bytes':client.payload_bytes,'native_admission':False}))
    return {'context':ctx,'base_archive':work/'base-save.tar','base_config_digest':full['base']['config_digest'],'base_diff_ids':full['base']['rootfs_diff_ids'],'recipe_sha256':hashlib.sha256(recipe).hexdigest(),'renderer':renderer}
