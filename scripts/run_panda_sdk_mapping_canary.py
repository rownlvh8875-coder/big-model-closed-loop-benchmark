"""Fresh qualified one-use Actions mapping canary; no scientific campaign."""
import argparse,base64,hashlib,json,os,secrets,shutil,stat,sys,time
from pathlib import Path
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk_mapping_policy as a
from scripts import panda_sdk_mapping_runtime as runtime
from scripts import produce_panda_sdk_abi0_image as old
from scripts import panda_sdk_abi0_image_policy as image_policy
from scripts import panda_sdk_image_archive as archive
from scripts import panda_sdk_image_carrier as image_carrier
from scripts import panda_sdk_routes_image as image
from scripts import engine_clock_image_process as process
from scripts.engine_clock_image_transport import Client
from scripts.panda_dispatch_coverage import read_input
OUT='output/stage7-panda-sdk-mapping-01/producer'
def save_json(path,value,limit):
 raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode();a.need(len(raw)<=limit,'bounded proof JSON');Path(path).write_bytes(raw)
def preserve_failed_start(docker,bundle):
 """Retain captured bytes even when attach/verification never returns a wire."""
 capture=getattr(docker,'last_start_capture',None)
 if capture is None:return
 def payload(name,limit):
  p=Path(capture['prefix'])/(name+'.bin');a.need(p.stat().st_size<=limit,'failed start output budget');raw=p.read_bytes();return dict(nbytes=len(raw),sha256=a.sha(raw),base64=base64.b64encode(raw).decode())
 envelope=dict(schema='panda-sdk-failed-start-capture-v1',status='UNVALIDATED_FAILED_START_OUTPUT',capture=capture['process'],captured_stdout=payload('stdout',a.BUDGET['runtime_bytes']),captured_stderr=payload('stderr',128*1024),runtime_semantics_validated=False,native_admitted=False,external_origin_authenticated=False,stage7_complete=False)
 save_json(Path(bundle)/'runtime.json',envelope,a.BUDGET['runtime_proof_bytes'])
class MappingDocker(old.DockerData):
 def __init__(self,tool,out,stop,binding,binding_sha,nonce,cache_image):
  super().__init__(tool,out,stop);self.binding=Path(binding).absolute();self.binding_sha=binding_sha;self.nonce=nonce;self.cache_image=Path(cache_image).absolute();self.cid=None;self.consumed=False;self.on_consume=lambda:None
 def bind(self,cid):a.need(a.hexstr(cid),'owned container ID');self.cid=cid
 def create_argv(self):
  for p in [a.ROOT,self.binding]:a.need(p.resolve()==p and ',' not in str(p),'canonical readonly bind')
  args=['create','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user','65534:65534','--memory','805306368','--memory-swap','805306368','--pids-limit','32','--cpus','1','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=16777216','--entrypoint','/opt/venv/bin/python','--name','panda-map-'+self.nonce,'--label','stage7.mapping='+self.nonce,'--mount','type=bind,src='+str(a.ROOT)+',dst=/work/repo,readonly','--mount','type=bind,src='+str(self.binding)+',dst=/work/binding,readonly','--workdir','/work/repo']
  for k,v in runtime.CLEAN_ENV.items():args+=['--env',k+'='+v]
  return args+[a.CONFIG,'-I','-S','-B','/work/repo/scripts/panda_sdk_mapping_runtime.py','--binding-sha',self.binding_sha]
 def validate_args(self,args):
  a.need(type(args) is list and args,'fixed Docker argv');valid=args==['version','--format','{{json .Server}}'] or args==['image','inspect','--format','{{json .}}',a.CONFIG] or args==['load','--input',str(self.cache_image)] or args==self.create_argv()
  if self.cid:valid=valid or args in [['container','inspect','--format','{{json .}}',self.cid],['rm',self.cid],['kill',self.cid]] or args==['start','--attach',self.cid] and not self.consumed
  a.need(valid,'unqualified/foreign Docker argv')
 def call(self,args,timeout=180,cleanup=False,missing=False):
  self.validate_args(args);stop=time.monotonic()+12 if cleanup else min(self.stop,time.monotonic()+timeout);self.verify(stop);start=args[0]=='start'
  if start:
   a.need(not self.consumed,'one start only');marker=self.out.parent/'mapping-window-consumed.json'
   with marker.open('xb') as f:f.write(b'{"mapping_window_consumed":true}\n')
   self.consumed=True;self.on_consume()
  remaining=a.BUDGET['log_bytes']-self.log_bytes;a.need(remaining>0,'Docker log budget');prefix=self.out/('command-'+str(self.index));self.index+=1;command=[str(self.tool),'--host=unix:///var/run/docker.sock',*args];r=process.capture(command,prefix,timeout=max(.001,stop-time.monotonic()),stdout_limit=a.BUDGET['runtime_bytes'] if start else min(128*1024,remaining//2),stderr_limit=min(128*1024,remaining//2),env=self.env,file_size_limit=2*1024**3)
  if start:self.last_start_capture=dict(prefix=str(prefix),process=process.public_receipt(r))
  self.log_bytes+=r['stderr_saved_bytes']+(0 if start else r['stdout_saved_bytes']);self.records.append(dict(command=command,process=process.public_receipt(r)));a.write(self.out/'commands.json',self.records)
  self.verify(time.monotonic()+12 if cleanup else stop)
  stdout=(prefix/'stdout.bin').read_text();stderr=(prefix/'stderr.bin').read_text();a.need(r['status']=='EXITED' and r['streams_complete'] and not r['cleanup_failed'],'Docker boundary failure')
  if missing and r['returncode']==1 and args[0]=='image' and 'No such image:' in stderr:return None
  a.need(start or r['returncode']==0,'Docker command failed');return stdout
 def inspect(self,kind,value,missing=False,cleanup=False):
  raw=self.call([kind,'inspect','--format','{{json .}}',value],timeout=12 if cleanup else 30,cleanup=cleanup,missing=missing);return None if raw is None else a.parse(raw)
def owned(docker,cleanup=False):
 c=docker.inspect('container',docker.cid,cleanup=cleanup);h=c['HostConfig'];a.need(c['Id']==docker.cid and c['Image']==a.CONFIG and c['Name']=='/panda-map-'+docker.nonce and c['Config']['Labels'].get('stage7.mapping')==docker.nonce,'owned image/container');a.need(h['ReadonlyRootfs'] is True and h['NetworkMode']=='none' and h['Privileged'] is False and h['CapDrop']==['ALL'] and not h['CapAdd'] and not h['Devices'] and not h.get('DeviceRequests') and h['Memory']==h['MemorySwap']==a.BUDGET['memory_bytes'] and h['PidsLimit']==32 and h['NanoCpus']==1000000000 and h['SecurityOpt']==['no-new-privileges'] and c['Config']['User']=='65534:65534' and c['RestartCount']==0,'container resource/isolation policy');binds={(m['Source'],m['Destination'],m['RW']) for m in c['Mounts'] if m['Type']=='bind'};a.need(binds=={(str(a.ROOT),'/work/repo',False),(str(docker.binding),'/work/binding',False)},'readonly source/binding mounts');return c
def tree_request_mode(client,commit,prefix='activation'):
 tree=commit['commit']['tree']['sha']
 for i,name in enumerate(a.REQUEST.split('/')):
  row=client.get_json('git/trees/'+tree,prefix+'-tree-'+str(i)+'.json');hits=[x for x in row['tree'] if x['path']==name];a.need(len(hits)==1,'activation tree path');entry=hits[0]
  if i==len(a.REQUEST.split('/'))-1:return entry
  a.need(entry['type']=='tree','activation tree directory');tree=entry['sha']
def authenticate_context(client,r,ctx,raw,completed=False):
 a.validate_request(r,a.ROOT);head=ctx['head_sha'];commit=client.get_json('commits/'+head,'activation-commit.json');delta=client.get_json('compare/'+r['source_sha']+'...'+head,'activation-compare.json');entry=tree_request_mode(client,commit);a.validate_activation(r,head,commit,delta,entry['mode']);blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();a.need(entry['sha']==delta['files'][0]['sha']==blob,'activation request bytes');proof=[]
 for reg in r['source_ci']:
  rid=reg['run_id'];proof.append({k:client.get_json('actions/runs/'+str(rid)+suffix,'source-'+reg['event']+'-'+k+'.json') for k,suffix in [('run',''),('jobs','/jobs'),('artifacts','/artifacts')]})
 a.validate_ci(r,proof);run=client.get_json('actions/runs/'+str(ctx['run_id']),'live-run.json');workflow=client.get_json('actions/workflows/'+str(run['workflow_id']),'live-workflow.json');listing=client.get_json('actions/workflows/'+str(run['workflow_id'])+'/runs?branch='+a.BRANCH+'&per_page=100','unique-runs.json');a.validate_run(r,ctx,run,workflow,listing,completed);return run
def image_input(client,work,stop):
 pin=a.IMAGE_ARTIFACT;run=client.get_json('actions/runs/'+str(pin['run_id']),'image-run.json');jobs=client.get_json('actions/runs/'+str(pin['run_id'])+'/jobs','image-jobs.json');a.need(run['head_sha']==pin['head_sha'] and run['workflow_id']==419021681 and run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='success' and run['path']==image_policy.WORKFLOW and run['actor']['login']==a.OWNER,'authenticated image source run');a.need(image_policy.validate_production_job(run,jobs)==132770205181,'image source job');listing=client.get_json('actions/runs/'+str(pin['run_id'])+'/artifacts','image-artifacts.json');row=image_policy.validate_artifacts(run,listing)[pin['name']];a.need(row['id']==pin['id'] and row['size_in_bytes']==pin['size_in_bytes'] and row['digest']=='sha256:'+pin['sha256'],'exact current image artifact');client.download('https://api.github.com/repos/'+a.REPO+'/actions/artifacts/'+str(row['id'])+'/zip',work/'image.zip',nbytes=row['size_in_bytes'],sha256=pin['sha256'],kind='artifact');image_carrier.extract_carrier(work/'image.zip',work/'image',deadline=stop);path=work/'image/image.tar';check=archive.inspect_save_archive(path,expected_tag=image_policy.TAG,deadline=old.inspection_deadline(stop));auth=a.image_authority(a.ROOT)
 for k in ['image_tar_sha256','image_tar_nbytes','config_digest','rootfs_diff_ids']:a.need(check[k]==auth['archive'][k],'current saved image identity')
 a.need(a.parse(read_input(work/'image/installed-files.json',16*1024**2))==a.expected_inventory(a.ROOT),'current image manifest');image._copy_layer(path,check,a.SDK_SHA,a.SDK_SIZE,old.inspection_deadline(stop));return path,check
def run_canary():
 a.need(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_REPOSITORY')==a.REPO and os.environ.get('GITHUB_REF_NAME')==a.BRANCH and os.environ.get('GITHUB_EVENT_NAME')=='push' and os.environ.get('GITHUB_RUN_ATTEMPT')=='1','exact registered Actions context');out=a.ROOT/OUT;a.need(not out.exists(),'old canary output preserved');out.mkdir(parents=True);bundle=out/'bundle';bundle.mkdir();execution=out/'execution';execution.mkdir();work=out/'work';work.mkdir();r=dict(schema='panda-sdk-mapping-canary-v1',status='MAPPING_ONLY_CANARY_FAILED',source_sha=None,activation_sha=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),mapping_window_consumed=False,start_attempts=0,sdk_sha256=a.SDK_SHA,image_sha256=a.IMAGE_SHA,native_admitted=False,scientific_native_runs=0,stage7_complete=False,owned_container_removed=False);runtime_raw=b'{"status":"NOT_STARTED","native_admitted":false}\n';docker=None;runtime_written=False;stop=time.monotonic()+1800
 def save():save_json(bundle/'canary.json',r,1024**2)
 save();(bundle/'runtime.json').write_bytes(runtime_raw);save_json(bundle/'execution.json',{},4*1024**2)
 try:
  a.need(shutil.disk_usage(out).free>=a.BUDGET['minimum_free'],'16GiB runner free required');raw=read_input(a.ROOT/a.REQUEST,1024**2);request=a.parse(raw);a.validate_request(request,a.ROOT);ctx=dict(repository=a.REPO,head_sha=os.environ['GITHUB_SHA'],run_id=r['run_id'],attempt=1,event='push',actor=os.environ['GITHUB_ACTOR']);client=Client(execution/'api',repository=a.REPO,token=os.environ['GH_TOKEN'],deadline=stop,max_requests=96,max_payload_bytes=2*1024**3);run=authenticate_context(client,request,ctx,raw);r.update(source_sha=request['source_sha'],request_sha256=a.sha(raw),workflow_id=run['workflow_id']);save();path,check=image_input(client,work,stop);nonce=secrets.token_hex(16);binding=work/'binding';binding.mkdir();binding.chmod(0o755);b=dict(request=request,nonce=nonce,window_max=1,image_sha256=a.IMAGE_SHA,host_namespaces={k:os.readlink('/proc/self/ns/'+k) for k in ['pid','mnt','net']});a.write(binding/'binding.json',b);(binding/'binding.json').chmod(0o644);binding_sha=a.sha(read_input(binding/'binding.json',1024**2));tool=shutil.which('docker',path='/usr/bin:/usr/local/bin:/bin');a.need(tool,'Docker client');docker=MappingDocker(tool,execution/'docker',stop,binding,binding_sha,nonce,path)
  docker.call(['version','--format','{{json .Server}}']);docker.call(['load','--input',str(path)]);loaded=docker.inspect('image',a.CONFIG);a.need(loaded['RootFS']['Layers']==check['rootfs_diff_ids'],'loaded immutable image');cid=docker.call(docker.create_argv(),90).strip();docker.bind(cid);before=owned(docker);a.need(before['State']['Status']=='created' and before['State']['Pid']==0 and before['State']['Running'] is False,'fresh stopped container');r.update(container_id=cid,nonce=nonce,binding_sha256=binding_sha,container_before=before['State'],host_namespaces=b['host_namespaces']);save()
  def consume():r.update(mapping_window_consumed=True,start_attempts=1);save()
  docker.on_consume=consume;runtime_raw=docker.call(['start','--attach',cid],90).encode();a.need(len(runtime_raw)<=8*1024**2,'runtime wire budget');(bundle/'runtime.json').write_bytes(runtime_raw);runtime_written=True;result=a.parse(runtime_raw);a.need(result['status']=='SELECTED_MAPPING_ABI_OBSERVED' and result['fixture'] is False and result['image_membership_verified'] is True and result['binding_sha256']==binding_sha and result['nonce']==nonce,'actual mapping-only result');runtime.validate_window(a.mapping_profile(a.ROOT),result);after=owned(docker);r['container_after']=after['State'];a.need(after['State']['Status']=='exited' and after['State']['Running'] is False and after['State']['Pid']==0 and after['State']['ExitCode']==0 and not after['State']['OOMKilled'],'clean bounded exit');r.update(status='MAPPING_ONLY_CANARY_PASSED',selected_sdk_code_mapping_verified=True,selected_c_abi_calls_verified=5);save()
 except BaseException as e:r.update(status='MAPPING_ONLY_CANARY_FAILED',failure=type(e).__name__+': '+str(e));save()
 finally:
  if docker:
   if docker.cid:
    try:
     c=owned(docker,cleanup=True)
     if c['State']['Running']:docker.call(['kill',docker.cid],12,cleanup=True);c=owned(docker,cleanup=True)
     a.need(c['State']['Running'] is False and c['State']['Pid']==0,'owned stopped cleanup');docker.call(['rm',docker.cid],12,cleanup=True);r['owned_container_removed']=True
    except BaseException as e:r.update(status='MAPPING_ONLY_CANARY_FAILED',cleanup_failure=type(e).__name__+': '+str(e))
   if not runtime_written:preserve_failed_start(docker,bundle)
   logs=[]
   for i,record in enumerate(docker.records):
    row=dict(record)
    if record['command'][2]!='start':row['stdout']=(docker.out/('command-'+str(i))/'stdout.bin').read_text(errors='replace')
    row['stderr']=(docker.out/('command-'+str(i))/'stderr.bin').read_text(errors='replace');logs.append(row)
   try:docker.verify(time.monotonic()+12);verified=True
   except BaseException as e:verified=False;r.update(status='MAPPING_ONLY_CANARY_FAILED',tool_failure=type(e).__name__+': '+str(e))
   save_json(bundle/'execution.json',dict(commands=logs,tools_before=docker.profile,tools_after=docker.profile,tools_after_verified=verified,http_events=client.events),4*1024**2)
  save()
 return r
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true',required=True);p.parse_args()
 try:r=run_canary();print(json.dumps(dict(status=r['status'],mapping_window_consumed=r['mapping_window_consumed'],native_admitted=False)));return 0 if r['status']=='MAPPING_ONLY_CANARY_PASSED' and r['owned_container_removed'] else 2
 except Exception as e:print('mapping canary rejected: '+type(e).__name__+': '+str(e));return 2
if __name__=='__main__':raise SystemExit(main())
