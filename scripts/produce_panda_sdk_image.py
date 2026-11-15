"""One-use Actions producer: COPY-only Docker operations, never start payloads."""
import argparse,base64,hashlib,json,os,shutil,stat,subprocess,sys,time,uuid
from pathlib import Path
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk_image_auth as a
from scripts import panda_sdk_routes_image as image
from scripts import panda_sdk_image_archive as archive
from scripts import panda_sdk_image_carrier as carrier
from scripts import engine_clock_image_process as process
from scripts.engine_clock_image_transport import Client
from scripts.panda_dispatch_coverage import read_input
OUT='output/stage7-panda-sdk-image-auth-01/producer'
def inspection_deadline(stop):return time.perf_counter()+min(180,max(0,stop-time.monotonic()))
def file_hash(path,limit,stop):
 path=Path(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 with os.fdopen(fd,'rb') as f:
  before=os.fstat(f.fileno());a.need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=limit,'regular bounded file required');h=hashlib.sha256()
  for b in iter(lambda:f.read(1024**2),b''):a.need(time.monotonic()<stop,'file deadline');h.update(b)
  a.need(image._signature(before)==image._signature(os.fstat(f.fileno()))==image._signature(path.lstat()),'file changed');return dict(nbytes=before.st_size,sha256=h.hexdigest())
class DockerData:
 def __init__(self,tool,out,stop):
  self.tool=Path(tool).resolve();self.out=Path(out);self.out.mkdir(parents=True,exist_ok=False);self.stop=stop;self.index=0;self.log_bytes=0;self.records=[]
  allowed={'PATH','HOME','USER','LANG','LC_ALL','LC_CTYPE','TMPDIR','XDG_RUNTIME_DIR','XDG_CONFIG_HOME','DOCKER_CONFIG','SSL_CERT_FILE','SSL_CERT_DIR','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy'}
  self.env={k:v for k,v in os.environ.items() if k in allowed}
  for k in ('GH_TOKEN','GITHUB_TOKEN','ACTIONS_RUNTIME_TOKEN','ACTIONS_ID_TOKEN_REQUEST_TOKEN','LD_PRELOAD','LD_AUDIT','LD_LIBRARY_PATH','DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'):self.env.pop(k,None)
  self.env['DOCKER_BUILDKIT']='0';self.profile={str(p):file_hash(p,64*1024**2,stop) for p in (self.tool,Path(sys.executable).resolve())};a.write(self.out/'tools-before.json',self.profile)
 def verify(self,stop):
  a.need(all(file_hash(Path(p),64*1024**2,stop)==r for p,r in self.profile.items()),'producer tool drift')
 def call(self,args,timeout=180,cleanup=False,missing=False):
  image.validate_docker_arguments(args);stop=time.monotonic()+min(timeout,12) if cleanup else min(self.stop,time.monotonic()+timeout);self.verify(stop);remaining=a.BUDGET['log_bytes']-self.log_bytes;a.need(remaining>0,'Docker log budget')
  prefix=self.out/('command-'+str(self.index));self.index+=1;command=[str(self.tool),'--host=unix:///var/run/docker.sock',*args]
  r=process.capture(command,prefix,timeout=max(.001,stop-time.monotonic()),stdout_limit=min(128*1024,remaining//2),stderr_limit=min(128*1024,remaining//2),env=self.env,file_size_limit=2*1024**3)
  self.log_bytes+=r['stdout_saved_bytes']+r['stderr_saved_bytes'];self.records.append(dict(command=command,process=process.public_receipt(r)));a.write(self.out/'commands.json',self.records);self.verify(stop if not cleanup else time.monotonic()+12)
  stdout=(prefix/'stdout.bin').read_text();stderr=(prefix/'stderr.bin').read_text();a.need(r['status']=='EXITED' and r['streams_complete'] and not r['cleanup_failed'],'Docker process boundary')
  if missing and r['returncode']==1 and args[:2]==['image','inspect'] and 'No such image:' in stderr:return None
  a.need(r['returncode']==0,'Docker command failed; outputs preserved');return stdout
 def inspect(self,kind,value,missing=False,cleanup=False):
  raw=self.call([kind,'inspect','--format','{{json .}}',value],timeout=12 if cleanup else 30,missing=missing,cleanup=cleanup);return None if raw is None else a.parse(raw)

def tree_request_mode(client,commit,prefix='activation'):
 tree=commit['commit']['tree']['sha']
 for index,name in enumerate(a.REQUEST.split('/')):
  row=client.get_json('git/trees/'+tree,prefix+'-tree-'+str(index)+'.json');hits=[x for x in row['tree'] if x['path']==name];a.need(len(hits)==1,'activation tree path');entry=hits[0]
  if index==len(a.REQUEST.split('/'))-1:return entry
  a.need(entry['type']=='tree','activation tree directory');tree=entry['sha']
def unique_runs(client,wid):
 for i in range(6):
  row=client.get_json('actions/workflows/'+str(wid)+'/runs?branch='+a.BRANCH+'&per_page=100','unique-'+str(i)+'.json')
  if row.get('total_count')!=0 or row.get('workflow_runs')!=[]:return row
  a.need(i<5,'workflow visibility empty');time.sleep(5)
 raise ValueError('workflow visibility rejected')
def authenticate_context(client,r,ctx,raw_request,completed=False):
 a.validate_request(r,a.ROOT);head=ctx['head_sha'];commit=client.get_json('commits/'+head,'activation-commit.json');delta=client.get_json('compare/'+r['source_sha']+'...'+head,'activation-compare.json');entry=tree_request_mode(client,commit)
 a.validate_activation(r,head,commit,delta,entry['mode']);blob=hashlib.sha1(b'blob '+str(len(raw_request)).encode()+b'\0'+raw_request).hexdigest();a.need(entry['type']=='blob' and entry['sha']==delta['files'][0]['sha']==blob,'activation request bytes')
 proofs=[]
 for reg in r['source_ci']:
  rid=reg['run_id'];proofs.append({k:client.get_json('actions/runs/'+str(rid)+suffix,'source-'+reg['event']+'-'+k+'.json') for k,suffix in [('run',''),('jobs','/jobs'),('artifacts','/artifacts')]})
 a.validate_ci(r,proofs);run=client.get_json('actions/runs/'+str(ctx['run_id']),'live-run.json');workflow=client.get_json('actions/workflows/'+str(run['workflow_id']),'live-workflow.json');listing=unique_runs(client,run['workflow_id']);a.validate_run(r,ctx,run,workflow,listing,completed);return run

def check_base_artifact(row):
 pin=a.BASE_ARTIFACT;w=row['workflow_run'];a.need(row['id']==pin['id'] and row['name']==pin['name'] and row['size_in_bytes']==pin['size_in_bytes'] and row['digest']=='sha256:'+pin['sha256'] and row['expired'] is False and w['id']==pin['run_id'] and w['head_sha']==pin['head_sha'] and w['repository_id']==w['head_repository_id']==a.REPO_ID,'base artifact identity')
def stopped(docker,cid,iid,nonce,cleanup=False):
 c=docker.inspect('container',cid,cleanup=cleanup);a.need(c['Id']==cid and c['Image']==iid and c['Name']=='/panda-sdk-'+nonce and c['Config']['Labels'].get('stage7.sdk.image')==nonce and c['State']['Status']=='created' and c['State']['Running'] is False and c['State']['Pid']==0 and c['HostConfig']['ReadonlyRootfs'] is True and c['HostConfig']['NetworkMode']=='none','owned stopped container');return dict(Status='created',Running=False,Pid=0)

def run_production():
 a.need(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_REPOSITORY')==a.REPO and os.environ.get('GITHUB_REF_NAME')==a.BRANCH and os.environ.get('GITHUB_EVENT_NAME')=='push' and os.environ.get('GITHUB_RUN_ATTEMPT')=='1','exact Actions entry required')
 ctx=dict(repository=a.REPO,head_sha=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),attempt=1,event='push',actor=os.environ['GITHUB_ACTOR']);raw=read_input(a.ROOT/a.REQUEST,4*1024**2);r=a.parse(raw);a.validate_request(r,a.ROOT);out=a.ROOT/OUT;a.need(not out.exists(),'existing producer output preserved');a.need(shutil.disk_usage(a.ROOT).free>=a.BUDGET['minimum_free'],'16GiB free required');out.mkdir(parents=True);bundle=out/'bundle';execution=out/'execution';work=out/'work'
 for p in (bundle,execution,work):p.mkdir()
 stop=time.monotonic()+a.BUDGET['total_seconds'];client=Client(execution/'api',repository=a.REPO,token=os.environ['GH_TOKEN'],deadline=stop,max_requests=96,max_payload_bytes=a.BUDGET['producer_payload']);result=dict(schema='panda-sdk-actions-image-production-v1',status='FAILED',request_id=a.ID,source_sha=r['source_sha'],activation_sha=ctx['head_sha'],run_id=ctx['run_id'],request_sha256=a.sha(raw),sdk_sha256=a.SDK_SHA,sdk_nbytes=a.SDK_SIZE,containers_started=0,new_native_runs=0,official_model_calls=0,native_admitted=False,stage7_complete=False,owned_stopped_container_removed=False);docker=None;cid=None;iid=None;nonce=uuid.uuid4().hex
 def save():a.write(bundle/'preparation.json',result)
 save()
 try:
  run=authenticate_context(client,r,ctx,raw);result['workflow_id']=run['workflow_id'];save();meta=client.get_json('actions/artifacts/'+str(a.BASE_ARTIFACT['id']),'base-artifact.json');check_base_artifact(meta)
  client.download('https://api.github.com/repos/'+a.REPO+'/actions/artifacts/'+str(meta['id'])+'/zip',work/'base.zip',nbytes=meta['size_in_bytes'],sha256=meta['digest'][7:],kind='artifact');extracted=carrier.extract_carrier(work/'base.zip',work/'base',deadline=stop);auth=a.authority(a.ROOT)
  for name,key in [('image.tar','image_tar_sha256'),('installed-files.json','installed_files_sha256')]:a.need(extracted['files'][name]['sha256']==auth[key],'base carrier bytes')
  a.need(extracted['files']['preparation.json']['sha256']==auth['authority_files']['preparation.json']['sha256'],'base preparation bytes');base_check=archive.inspect_save_archive(work/'base/image.tar',expected_tag=a.base.TAG,deadline=inspection_deadline(stop));a.need(all(base_check[k]==auth[k] for k in ('config_digest','rootfs_diff_ids','image_tar_sha256','image_tar_nbytes')),'base image bytes');result['base_archive']=base_check;save()
  tool=shutil.which('docker',path='/usr/bin:/usr/local/bin:/bin');a.need(tool,'Docker client missing');docker=DockerData(tool,execution/'docker',stop);result['docker_server']=a.parse(docker.call(['version','--format','{{json .Server}}'],30));save()
  old=docker.inspect('image',a.base.TAG,missing=True);a.need(old is None or old['Id']==auth['config_digest'],'existing base tag collision');docker.call(['load','--input',str(work/'base/image.tar')]);loaded=docker.inspect('image',auth['config_digest']);a.need(loaded['RootFS']['Layers']==auth['rootfs_diff_ids'],'loaded base identity')
  base_tag='stage7-panda-sdk-base:'+auth['config_digest'][7:19];a.need(docker.inspect('image',base_tag,missing=True) is None and docker.inspect('image',a.TAG,missing=True) is None,'owned tag collision');docker.call(['tag',auth['config_digest'],base_tag]);context=work/'context';context.mkdir();data=read_input(a.ROOT/a.SDK,2*1024**2);a.need(len(data)==a.SDK_SIZE and a.sha(data)==a.SDK_SHA,'SDK drift');(context/'libpandagl.so').write_bytes(data);(context/'libpandagl.so').chmod(0o755);(context/'Dockerfile').write_text(image.recipe(base_tag));image.validate_context(context,base_tag,a.SDK_SHA,a.SDK_SIZE)
  docker.call(['build','--network=none','--pull=false','--no-cache','--tag',a.TAG,'--file',str(context/'Dockerfile'),str(context)]);image.validate_context(context,base_tag,a.SDK_SHA,a.SDK_SIZE);new=docker.inspect('image',a.TAG);iid=new['Id'];a.need(new['RootFS']['Layers'][:-1]==auth['rootfs_diff_ids'] and len(new['RootFS']['Layers'])==11,'exact base plus single COPY layer')
  cid=docker.call(['create','--network=none','--read-only','--entrypoint','/bin/false','--name','panda-sdk-'+nonce,'--label','stage7.sdk.image='+nonce,iid],30).strip();a.need(a.hexstr(cid),'owned container ID');result['container_before']=stopped(docker,cid,iid,nonce);save();docker.call(['export','--output',str(work/'rootfs.tar'),cid]);result['container_after']=stopped(docker,cid,iid,nonce);expected=a.expected_inventory(a.ROOT);a.write(bundle/'installed-files.json',expected);result['installed_manifest_sha256']=a.sha(read_input(bundle/'installed-files.json',16*1024**2));result['export']=image.inspect_export(work/'rootfs.tar',expected,inspection_deadline(stop));result['installed_entries']=result['export']['matched_entries'];save()
  docker.call(['save','--output',str(bundle/'image.tar'),a.TAG]);result['archive']=archive.inspect_save_archive(bundle/'image.tar',expected_tag=a.TAG,deadline=inspection_deadline(stop));a.need(result['archive']['config_digest']==iid and result['archive']['rootfs_diff_ids']==new['RootFS']['Layers'],'saved image identity');result['copy_layer']=image._copy_layer(bundle/'image.tar',result['archive'],a.SDK_SHA,a.SDK_SIZE,inspection_deadline(stop));a.validate_request(r,a.ROOT);docker.verify(stop);a.write(execution/'tools-after.json',docker.profile);a.need(sum(p.stat().st_size for p in out.rglob('*') if p.is_file())<=a.BUDGET['producer_output'],'producer output budget');save()
 except BaseException as e:result['failure']=type(e).__name__+': '+str(e);save();raise
 finally:
  if cid and docker:
   try:stopped(docker,cid,iid,nonce,cleanup=True);docker.call(['rm',cid],12,cleanup=True);result['owned_stopped_container_removed']=True;save()
   except BaseException as e:result['cleanup_failure']=type(e).__name__;save()
 a.need(result['owned_stopped_container_removed'] is True and time.monotonic()<stop,'producer completion/cleanup');result['status']='COPY_ONLY_SDK_IMAGE_BYTES_VERIFIED_NATIVE_BLOCKED';save();return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true',required=True);p.parse_args()
 try:r=run_production();print(json.dumps(dict(status=r['status'],image_sha256=r['archive']['image_tar_sha256'],native_admitted=False)));return 0
 except Exception as e:print('SDK image production rejected: '+type(e).__name__+': '+str(e));return 2
if __name__=='__main__':raise SystemExit(main())
