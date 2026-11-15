"""COPY-only local SDK image, verified as bytes; never start a container."""
import argparse,hashlib,json,math,os,re,shutil,stat,subprocess,tarfile,time,uuid
from datetime import datetime,timezone,timedelta
from pathlib import Path,PurePosixPath
from scripts import panda_sdk_routes_stage as stage
from scripts import panda_sdk_routes_inputs as inputs
from scripts import panda_sdk_image_binding as retained
from scripts import panda_sdk_routes_archive as archive
from scripts.engine_clock_runtime_inventory import validate_inventory
from scripts.panda_dispatch_coverage import read_input
from scripts.build_panda_source_dispatch import stop_build_group

ROOT=stage.ROOT;need=stage.need
SDK_PATH='/opt/venv/lib/python3.11/site-packages/panda3d/libpandagl.so'
DOCKER='/usr/local/bin/docker';ENDPOINT='--host=unix:///var/run/docker.sock'
GiB=1024**3

def _check(deadline):need(time.perf_counter()<deadline,'image deadline exceeded')
def _signature(s):return s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink
def _name(name):
    while name.startswith('./'):name=name[2:]
    need(name and len(name)<=4096 and '\0' not in name and not name.startswith('/') and len(name.split('/'))<=256 and all(x not in ('','..','.') for x in name.split('/')),'unsafe archive path')
    return '/'+name

class _BoundedReader:
    def __init__(self,stream,deadline):self.stream=stream;self.deadline=deadline;self.total=0
    def read(self,size=-1):
        _check(self.deadline);need(0<=size<=16*1024**2,'archive metadata allocation budget');self.total+=size;need(self.total<=4*GiB,'archive read budget');return self.stream.read(size)
    def seek(self,*a):_check(self.deadline);return self.stream.seek(*a)
    def tell(self):return self.stream.tell()

def inspect_export(path,manifest,deadline):
    """Compare scoped file/link inventory without extracting or following links.

    Directory metadata, ownership and xattrs are outside the inherited inventory.
    """
    need(type(deadline) in (int,float) and math.isfinite(deadline),'finite deadline');deadline=min(deadline,time.perf_counter()+180);_check(deadline)
    expected=validate_inventory(manifest);path=Path(path)
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        with os.fdopen(fd,'rb') as stream:
            before=os.fstat(stream.fileno());need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=4*GiB,'regular bounded export required')
            full=hashlib.sha256()
            for block in iter(lambda:stream.read(1024**2),b''):_check(deadline);full.update(block)
            stream.seek(0);seen=set();rows={};pending={};total=0
            with tarfile.open(fileobj=_BoundedReader(stream,deadline),mode='r:',tarinfo=archive.bounded_tarinfo(archive.tar_bounds(),lambda:_check(deadline),4*GiB)) as t:
                for member in t:
                    _check(deadline)
                    raw=member.name.rstrip('/') if member.isdir() else member.name
                    if raw in ('.','./','') and member.isdir():continue
                    name=_name(raw);need(name not in seen and len(seen)<100000,'duplicate or too many export entries');seen.add(name)
                    inside=any(name==r or name.startswith(r+'/') for r in expected['roots']) and not any(name==r or name.startswith(r+'/') for r in expected['runtime_exclusions'])
                    if not inside:continue
                    need(member.size==0 or member.isfile(),'non-file export payload')
                    if member.isdir():continue
                    if member.issym():rows[name]=dict(path=name,kind='symlink',target=member.linkname)
                    elif member.islnk():pending[name]=(_name(member.linkname),member.mode)
                    elif member.isfile():
                        need(0<=member.size<=512*1024**2,'export file budget');total+=member.size;need(total<=3*GiB,'installed bytes budget');h=hashlib.sha256();count=0
                        with t.extractfile(member) as payload:
                            for block in iter(lambda:payload.read(1024**2),b''):_check(deadline);h.update(block);count+=len(block)
                        need(count==member.size,'truncated exported file');rows[name]=dict(path=name,kind='file',mode=member.mode,nbytes=count,sha256=h.hexdigest())
                    else:raise ValueError('special exported entry')
            def resolve(name,trail=()):
                _check(deadline);need(name not in trail and len(trail)<256,'hardlink cycle/depth')
                if name in pending:
                    target,mode=pending[name];r=resolve(target,trail+(name,));need(mode==r['mode'],'hardlink mode mismatch');rows[name]=dict(r,path=name);del pending[name]
                need(name in rows and rows[name]['kind']=='file','hardlink requires scoped regular target');return rows[name]
            for name in list(pending):resolve(name)
            need(set(expected['roots'])<=seen,'export roots missing');need([rows[n] for n in sorted(rows)]==expected['entries'],'installed files differ from expected inventory')
            need(_signature(os.fstat(stream.fileno()))==_signature(before)==_signature(path.lstat()),'export changed during inspection')
            return dict(schema='panda-sdk-routes-export-v2',matched_entries=len(rows),export_sha256=full.hexdigest(),export_nbytes=before.st_size,roots=expected['roots'],directory_metadata_attested=False,ownership_xattrs_attested=False,native_admitted=False)
    except (tarfile.TarError,OverflowError,RecursionError) as e:raise ValueError('invalid bounded export') from e

def recipe(base_tag):
    need(type(base_tag) is str and re.fullmatch('[a-z0-9][a-z0-9:._/-]{1,127}',base_tag),'owned base tag required')
    return 'FROM '+base_tag+'\nCOPY libpandagl.so '+SDK_PATH+'\n'

def validate_context(context,base_tag,sdk_sha,nbytes):
    context=Path(context);need(not context.is_symlink() and context.is_dir(),'regular context')
    need({p.name for p in context.iterdir()}=={'Dockerfile','libpandagl.so'},'two-file context required')
    for p in context.iterdir():need(stat.S_ISREG(p.lstat().st_mode) and p.stat().st_nlink==1,'regular unaliased context files required')
    need(read_input(context/'Dockerfile',4096).decode()==recipe(base_tag),'COPY-only recipe required')
    p=context/'libpandagl.so';data=read_input(p,64*1024**2);need(len(data)==nbytes and inputs.sha(data)==sdk_sha and stat.S_IMODE(p.stat().st_mode)==0o755,'context SDK mismatch')

def validate_docker_arguments(args):
    need(type(args) is list and args and all(type(a) is str and '\0' not in a for a in args),'Docker argument vector')
    need(args[0] in {'version','info','load','tag','build','create','export','save','rm','image','container'},'activation/publication forbidden')
    if args[0] in ('image','container'):need(len(args)>1 and args[1]=='inspect','inspect-only namespace')
    if args[0]=='rm':need(len(args)==2 and not args[1].startswith('-'),'only one owned stopped container removal')

def _json(path,limit=16*1024**2):return json.loads(read_input(path,limit))
def _write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

class _Docker:
    def __init__(self,out,deadline):
        self.out=out;self.deadline=deadline;self.records=[];self.env=os.environ.copy()
        for key in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'):self.env.pop(key,None)
        self.env['DOCKER_BUILDKIT']='0'
    def call(self,args,timeout=180,cleanup=False):
        validate_docker_arguments(args);stop=time.perf_counter()+timeout if cleanup else min(self.deadline,time.perf_counter()+timeout);_check(stop)
        inputs.verify_tool_files(inputs.tool_profile());prefix=self.out/('docker-'+str(len(self.records)));stdout=prefix.with_suffix('.stdout');stderr=prefix.with_suffix('.stderr');command=[DOCKER,ENDPOINT,*args];start=time.perf_counter()
        record=dict(command=command,status='failed');self.records.append(record)
        with stdout.open('xb') as o,stderr.open('xb') as e:
            p=subprocess.Popen(command,cwd=ROOT,env=self.env,stdout=o,stderr=e,start_new_session=True)
            try:
                while p.poll() is None:
                    _check(stop);need(sum(x.stat().st_size for x in self.out.glob('docker-*') if x.is_file())<=1024**2,'Docker log budget');need(sum(x.stat().st_size for x in self.out.rglob('*') if x.is_file())<=6*GiB,'image output budget');time.sleep(.05)
            finally:stop_build_group(p)
        _check(stop);need(stdout.stat().st_size+stderr.stat().st_size<=1024**2,'Docker output budget');record.update(returncode=p.returncode,wall_seconds=time.perf_counter()-start,stdout_path=str(stdout),stderr_path=str(stderr));_write(self.out/'commands.json',self.records)
        inputs.verify_tool_files(inputs.tool_profile());need(p.returncode==0,'Docker command failed; raw output retained');record['status']='success';_write(self.out/'commands.json',self.records);return stdout.read_text()
    def inspect(self,kind,identity,cleanup=False):return json.loads(self.call([kind,'inspect','--format','{{json .}}',identity],12 if cleanup else 30,cleanup=cleanup))

def _copy_layer(path,check,sdk_sha,nbytes,deadline):
    """Require the single added layer to contain only SDK bytes and ancestors."""
    layer=check['layers'][-1]['path'];seen=set();files=[]
    with tarfile.open(path,'r:') as outer:
        member=outer.getmember(layer)
        with outer.extractfile(member) as payload,tarfile.open(fileobj=payload,mode='r|*') as t:
            for m in t:
                _check(deadline);name=_name(m.name.rstrip('/') if m.isdir() else m.name);need(name not in seen and len(seen)<32,'COPY layer duplicate/budget');seen.add(name)
                if m.isdir():need(SDK_PATH.startswith(name+'/'),'unexpected added directory');continue
                need(name==SDK_PATH and m.isfile() and m.size==nbytes and m.mode==0o755,'unexpected COPY layer payload');h=hashlib.sha256()
                with t.extractfile(m) as stream:
                    for block in iter(lambda:stream.read(1024**2),b''):_check(deadline);h.update(block)
                need(h.hexdigest()==sdk_sha,'COPY layer SDK hash');files.append(name)
    need(files==[SDK_PATH],'one SDK payload required');return dict(files=files,directory_metadata_attested=False)

def assemble_image(build_dir,coverage_dir,out):
    build_dir,coverage_dir,out=map(stage.canonical,(build_dir,coverage_dir,out));need(not out.exists(),'existing output preserved')
    build_raw=read_input(build_dir/'receipt.json',4*1024**2);r=json.loads(build_raw);cov=_json(coverage_dir/'coverage.json');library=build_dir/'sdk/lib/libpandagl.so'
    need(r.get('status')=='NEW_SDK_COMPILE_LINK_STATIC_VERIFIED_NOT_LOADED' and r.get('native_admitted') is False and r.get('new_native_runs')==0 and r.get('native_sha256')==stage.NATIVE_PINS,'qualified SDK build required')
    need(r['output']==str(build_dir) and r['candidate_library']==str(library),'owned SDK output binding');data=read_input(library,64*1024**2);sha=inputs.sha(data);nbytes=len(data);need(sha==r['candidate_sha256'] and nbytes==r['candidate_nbytes'],'SDK bytes changed')
    need(cov.get('build_receipt_sha256')==inputs.sha(build_raw) and cov.get('candidate_sha256')==sha and cov.get('all_selected_names_classified') is True and cov.get('computed_names_statically_closed') is True and cov.get('safe_name_count')==252 and cov.get('safe_cap')==256 and cov.get('native_admitted') is False,'SDK coverage binding')
    need(shutil.disk_usage(ROOT).free>=16*GiB,'16GiB free space required');out.mkdir(parents=True);deadline=time.perf_counter()+900;docker=_Docker(out,deadline);container=None;nonce=uuid.uuid4().hex;start=time.perf_counter()
    result=dict(schema='panda-sdk-routes-local-image-v2',status='failed',checked_at_kst=datetime.now(timezone(timedelta(hours=9))).isoformat(),candidate_sha256=sha,candidate_nbytes=nbytes,build_receipt_sha256=inputs.sha(build_raw),coverage_sha256=inputs.sha(read_input(coverage_dir/'coverage.json',4*1024**2)),producer_local=True,output_actions_authenticated=False,containers_started=0,new_native_runs=0,official_model_calls=0,native_admitted=False,runtime_binding_qualified=False,stage7_complete=False)
    def save():_write(out/'receipt.json',result)
    save()
    try:
        base=retained.inspect_retained_image(out/'base-verification');authority=_json(ROOT/retained.RESULT);result['base_verification']=base;save();base_id=authority['config_digest']
        version=json.loads(docker.call(['version','--format','{{json .Server}}'],30));result['docker_server']={k:version.get(k) for k in ('Version','ApiVersion','Os','Arch')};save()
        # Inspect all local IDs without changing shared references. A missing base
        # is established through the read-only API, not a failed mutation.
        try:base_info=docker.inspect('image',base_id)
        except ValueError:
            try:tag_info=docker.inspect('image',retained.TAG)
            except ValueError:tag_info=None
            need(tag_info is None or tag_info['Id']==base_id,'shared base tag collision');docker.call(['load','--input',str(ROOT/retained.IMAGE)]);base_info=docker.inspect('image',base_id)
        need(base_info['Id']==base_id and base_info['RootFS']['Layers']==authority['rootfs_diff_ids'],'loaded base differs')
        base_tag='stage7-panda-routes-base:'+base_id[7:19]
        try:tag_info=docker.inspect('image',base_tag)
        except ValueError:tag_info=None
        need(tag_info is None or tag_info['Id']==base_id,'owned base tag collision')
        if tag_info is None:docker.call(['tag',base_id,base_tag],30)
        tag='stage7-panda-routes:sdk-'+sha[:12]+'-'+nonce[:8];context=out/'context';context.mkdir();(context/'libpandagl.so').write_bytes(data);(context/'libpandagl.so').chmod(0o755);(context/'Dockerfile').write_text(recipe(base_tag));validate_context(context,base_tag,sha,nbytes)
        result.update(tag=tag,base_tag=base_tag,nonce=nonce);save();docker.call(['build','--network=none','--pull=false','--no-cache','--tag',tag,'--file',str(context/'Dockerfile'),str(context)]);validate_context(context,base_tag,sha,nbytes);new=docker.inspect('image',tag)
        need(new['RootFS']['Layers'][:-1]==authority['rootfs_diff_ids'] and len(new['RootFS']['Layers'])==len(authority['rootfs_diff_ids'])+1,'one COPY layer over exact base required');result['image_id']=new['Id'];save()
        container=docker.call(['create','--network=none','--read-only','--entrypoint','/bin/false','--name','panda-routes-'+nonce,'--label','stage7.panda.routes='+nonce,new['Id']],30).strip();need(re.fullmatch('[a-f0-9]{64}',container),'owned container ID')
        def stopped():
            c=docker.inspect('container',container);need(c['Id']==container and c['Image']==new['Id'] and c['Name']=='/panda-routes-'+nonce and c['Config']['Labels'].get('stage7.panda.routes')==nonce and c['State']['Status']=='created' and c['State']['Running'] is False and c['State']['Pid']==0,'owned never-started container required');return {k:c['State'][k] for k in ('Status','Running','Pid')}
        result['container_before']=stopped();save();docker.call(['export','--output',str(out/'rootfs.tar'),container]);result['container_after']=stopped();save()
        expected=_json(ROOT/'docs/evidence/engine-clock-sealed-image-06/installed-files.json');hits=[row for row in expected['entries'] if row['path']==SDK_PATH];need(len(hits)==1 and hits[0]['kind']=='file','old SDK manifest membership');hits[0].update(mode=0o755,nbytes=nbytes,sha256=sha);validate_inventory(expected);_write(out/'installed-files.json',expected)
        result['installed_inventory']=inspect_export(out/'rootfs.tar',expected,min(deadline,time.perf_counter()+180));save();docker.call(['save','--output',str(out/'image.tar'),tag]);check=archive.inspect_save_archive(out/'image.tar',expected_tag=tag,deadline=min(deadline,time.perf_counter()+180));need(check['config_digest']==new['Id'] and check['rootfs_diff_ids']==new['RootFS']['Layers'],'saved image binding');result['saved_image']=check;result['copy_layer']=_copy_layer(out/'image.tar',check,sha,nbytes,deadline);result['candidate_sdk_installed']=True;save()
    except BaseException as e:result['failure']=type(e).__name__+': '+str(e);save();raise
    finally:
        if container:
            try:
                c=docker.inspect('container',container,cleanup=True);need(c['Id']==container and c['Image']==new['Id'] and c['Name']=='/panda-routes-'+nonce and c['State']['Status']=='created' and c['State']['Running'] is False and c['State']['Pid']==0 and c['Config']['Labels'].get('stage7.panda.routes')==nonce,'cleanup ownership/stopped check');docker.call(['rm',container],12,cleanup=True);result['owned_stopped_container_removed']=True;save()
            except BaseException as e:result['cleanup_failure']=str(e);save()
    need(result.get('owned_stopped_container_removed') is True,'owned stopped-container cleanup failed');need(inputs.sha(read_input(library,64*1024**2))==sha,'SDK changed during assembly');need(sum(p.stat().st_size for p in out.rglob('*') if p.is_file())<=6*GiB,'image final output budget');_check(deadline);result.update(status='LOCAL_CANDIDATE_IMAGE_BUILT_BYTES_VERIFIED_NATIVE_BLOCKED',wall_seconds=time.perf_counter()-start);save();return result

def qualify_existing_assembly(build_dir,coverage_dir,image_dir,out):
    """Recheck retained local bytes after a parser fix; preserve failed receipt.

    No Docker operation occurs. This does not authenticate prior producer logs.
    """
    build_dir,coverage_dir,image_dir,out=map(stage.canonical,(build_dir,coverage_dir,image_dir,out));need(not out.exists(),'existing reinspection preserved');deadline=time.perf_counter()+900
    raw=read_input(image_dir/'receipt.json',4*1024**2);prior=json.loads(raw);build_raw=read_input(build_dir/'receipt.json',4*1024**2);b=json.loads(build_raw);cov_raw=read_input(coverage_dir/'coverage.json',4*1024**2);cov=json.loads(cov_raw)
    need(b.get('status')=='NEW_SDK_COMPILE_LINK_STATIC_VERIFIED_NOT_LOADED' and b.get('native_admitted') is False and b.get('native_sha256')==stage.NATIVE_PINS,'qualified versioned SDK required');need(prior.get('build_receipt_sha256')==inputs.sha(build_raw) and prior.get('coverage_sha256')==inputs.sha(cov_raw),'prior SDK/coverage binding')
    sha=b['candidate_sha256'];size=b['candidate_nbytes'];need(prior.get('candidate_sha256')==sha and prior.get('candidate_nbytes')==size and cov.get('candidate_sha256')==sha and cov.get('build_receipt_sha256')==inputs.sha(build_raw) and cov.get('all_selected_names_classified') is True and cov.get('computed_names_statically_closed') is True and cov.get('safe_name_count')==252 and cov.get('native_admitted') is False,'candidate/coverage qualification')
    lib=read_input(build_dir/'sdk/lib/libpandagl.so',64*1024**2);need(len(lib)==size and inputs.sha(lib)==sha,'retained SDK changed');need(prior.get('owned_stopped_container_removed') is True and prior.get('containers_started')==0 and prior.get('native_admitted') is False,'stopped local assembly required')
    for key in ('container_before','container_after'):need(prior.get(key)==dict(Status='created',Running=False,Pid=0),'never-started local snapshot required')
    authority_raw=read_input(ROOT/retained.RESULT,1024**2);need(inputs.sha(authority_raw)==retained.RESULT_SHA,'base authority pin');authority=json.loads(authority_raw);expected_raw=read_input(ROOT/'docs/evidence/engine-clock-sealed-image-06/installed-files.json',16*1024**2);need(inputs.sha(expected_raw)==authority['installed_files_sha256'],'old installed manifest pin');expected=json.loads(expected_raw);hits=[x for x in expected['entries'] if x['path']==SDK_PATH];need(len(hits)==1 and hits[0]['kind']=='file','one SDK entry');hits[0].update(mode=0o755,nbytes=size,sha256=sha);validate_inventory(expected);need(_json(image_dir/'installed-files.json')==expected,'retained expected inventory changed')
    commands=_json(image_dir/'commands.json');need(type(commands) is list and 0<len(commands)<=64,'bounded local commands')
    for row in commands:need(row['command'][:2]==[DOCKER,ENDPOINT],'managed Docker client binding');validate_docker_arguments(row['command'][2:])
    validate_context(image_dir/'context',prior['base_tag'],sha,size);out.mkdir(parents=True);result=dict(prior);result.update(status='failed',prior_failed_receipt_sha256=inputs.sha(raw),retained_image_dir=str(image_dir),local_producer_logs_authenticated=False,reinspection_only=True,checked_at_kst=datetime.now(timezone(timedelta(hours=9))).isoformat());_write(out/'receipt.json',result)
    try:
        result['installed_inventory']=inspect_export(image_dir/'rootfs.tar',expected,min(deadline,time.perf_counter()+180));check=archive.inspect_save_archive(image_dir/'image.tar',expected_tag=prior['tag'],deadline=min(deadline,time.perf_counter()+180));need(check['config_digest']==prior['image_id'] and check['rootfs_diff_ids'][:-1]==authority['rootfs_diff_ids'] and len(check['rootfs_diff_ids'])==len(authority['rootfs_diff_ids'])+1,'exact base plus COPY image binding');result['saved_image']=check;result['copy_layer']=_copy_layer(image_dir/'image.tar',check,sha,size,deadline);result.update(status='LOCAL_CANDIDATE_IMAGE_BUILT_BYTES_VERIFIED_NATIVE_BLOCKED',candidate_sdk_installed=True);result.pop('failure',None);_write(out/'receipt.json',result);return result
    except BaseException as e:result['failure']=type(e).__name__+': '+str(e);_write(out/'receipt.json',result);raise

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',required=True);p.add_argument('--coverage',required=True);p.add_argument('--out',required=True);p.add_argument('--reinspect',help='retained stopped assembly; data reads only');a=p.parse_args(argv)
    try:r=qualify_existing_assembly(a.build,a.coverage,a.reinspect,a.out) if a.reinspect else assemble_image(a.build,a.coverage,a.out);print(json.dumps({k:r[k] for k in ('status','candidate_sha256','candidate_sdk_installed','image_id','native_admitted')}));return 0
    except (ValueError,OSError) as e:print('local image rejected: '+str(e));return 2
if __name__=='__main__':raise SystemExit(main())
