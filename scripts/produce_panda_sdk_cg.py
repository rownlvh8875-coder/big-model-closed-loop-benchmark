"""One new source-bound compile-only Cg SDK job. Never load/run target code."""
import argparse,base64,io,json,os,shutil,sys,tarfile,time
from pathlib import Path
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk_cg_build_policy as a
from scripts import panda_sdk_cg_inputs as inputs
from scripts import build_panda_sdk_cg as builder
from scripts import panda_sdk_cg_static_gate as gate
from scripts import panda_sdk_cg_carrier as carrier
from scripts import panda_sdk_image_carrier as image_carrier
from scripts import panda_sdk_image_archive as image_archive
from scripts import panda_sdk_link_image as image
from scripts import panda_sdk_routes_stage as source
from scripts.engine_clock_image_transport import Client
from scripts import build_panda_adapter_sdk as archive_headers
OUT='output/stage7-panda-sdk-cg-candidate-01/producer'
class BuildClient(Client):
 def _url(self,url,kind):
  if kind=='cg-header':
   import urllib.parse
   a.need(url==inputs.contract()['cg_archive']['url'],'pinned NVIDIA URL');return urllib.parse.urlsplit(url)
  return super()._url(url,kind)

def authenticate_context(client,request,ctx,raw,completed=False):
 head=ctx['head_sha'];commit=client.get_json('git/commits/'+head,'activation-commit.json');delta=client.get_json('compare/'+request['source_sha']+'...'+head,'activation-compare.json');files=delta['files'];a.need(len(files)==1,'request-only delta');blob=client.get_json('git/blobs/'+files[0]['sha'],'request-blob.json');a.need(blob['encoding']=='base64' and base64.b64decode(blob['content'],validate=False)==raw and blob['sha']==files[0]['sha'],'exact live request blob')
 # Resolve the request's actual Git mode through its three tree components.
 tree=commit['tree']['sha'];mode=None
 for index,part in enumerate(a.REQUEST.split('/')):
  rows=client.get_json('git/trees/'+tree,'request-tree-'+str(index)+'.json');a.need(not rows.get('truncated'),'request tree closure');hits=[x for x in rows['tree'] if x['path']==part];a.need(len(hits)==1,'request tree member');row=hits[0];tree=row['sha'];mode=row['mode']
 a.need(tree==blob['sha'],'request tree/blob binding');a.validate_activation(request,head,commit,delta,mode);proofs=[]
 for reg in request['source_ci']:
  rid=str(reg['run_id']);proofs.append({k:client.get_json('actions/runs/'+rid+suffix,'source-'+reg['event']+'-'+k+'.json') for k,suffix in [('run',''),('jobs','/jobs'),('artifacts','/artifacts')]})
 a.validate_ci(request,proofs);run=client.get_json('actions/runs/'+str(ctx['run_id']),'live-run.json');workflow=client.get_json('actions/workflows/'+str(run['workflow_id']),'live-workflow.json');listing=client.get_json('actions/workflows/'+str(run['workflow_id'])+'/runs?per_page=100','unique-build-runs.json');a.validate_run(ctx,run,workflow,listing,completed);return run

def acquire_image(client,work,stop):
 c=inputs.contract();meta=client.get_json('actions/artifacts/'+str(a.IMAGE_ARTIFACT['id']),'image-artifact.json');pin=a.IMAGE_ARTIFACT;w=meta['workflow_run'];a.need(meta['id']==pin['id'] and meta['name']==pin['name'] and meta['size_in_bytes']==pin['size_in_bytes'] and meta['digest']=='sha256:'+pin['sha256'] and not meta['expired'] and w['id']==pin['run_id'] and w['head_sha']==pin['head_sha'] and w['repository_id']==w['head_repository_id']==a.REPO_ID,'frozen image artifact');client.download('https://api.github.com/repos/'+a.REPO+'/actions/artifacts/'+str(meta['id'])+'/zip',work/'image.zip',nbytes=pin['size_in_bytes'],sha256=pin['sha256'],kind='artifact');image_carrier.extract_carrier(work/'image.zip',work/'image',deadline=stop)
 check=image_archive.inspect_save_archive(work/'image/image.tar',expected_tag='stage7-panda-sdk:actions-20261115-03',deadline=time.perf_counter()+180);a.need(check['image_tar_sha256']==c['current_image_sha256'] and check['config_digest']==c['current_config_digest'],'current image archive');_,auth,rows=inputs.image_authority(a.ROOT/c['current_image_acceptance_path']);a.need(a.sha(a.read(work/'image/installed-files.json',16*1024**2))==auth['installed_manifest_sha256'],'downloaded image manifest');inventory=inputs.parse(a.read(a.ROOT/inputs.INVENTORY,16*1024**2));wanted=set(auth['installed_root_static_audit']['root_symbol_availability']['provider_records'])|{p['image_path'] for p in c['image_cg_providers'].values()};reader=image.SelectedImage(work/'image/image.tar',image.Inventory(inventory),check,work/'provider-data',deadline=stop);records=reader.collect(sorted(wanted));return {p:Path(r['data_path']) for p,r in records.items()},reader.inventory

def populate_headers(private):
 folder=a.ROOT/'docs/evidence/panda-sdk-cg-candidate-01/debs';manifest=inputs.parse(a.read(folder/'manifest.json',1024**2));original=a.read(a.ROOT/'docs/evidence/panda-source-dispatch-01/before-review/dependency-inputs.json',1024**2);a.need(a.sha(original)==manifest['source_profile_sha256']==archive_headers.DEPS_SHA,'original dependency profile');expected={r['sha256']:r['nbytes'] for r in inputs.parse(original)['dev_packages']};a.need(len(manifest['packages'])==len(expected) and {r['sha256']:r['nbytes'] for r in manifest['packages']}==expected and all(r['path']==r['sha256']+'.deb.data' for r in manifest['packages']),'exact original development packages');records={};private=Path(private)
 for row in manifest['packages']:
  raw=a.read(folder/row['path'],8*1024**2);a.need(len(raw)==row['nbytes'] and a.sha(raw)==row['sha256'],'pinned Debian header package');a.need(raw.startswith(b'!<arch>\n'),'Debian ar');at=8;payload=None
  while at<len(raw):
   h=raw[at:at+60];a.need(len(h)==60 and h[-2:]==b'`\n','ar header');name=h[:16].decode().strip().rstrip('/');n=int(h[48:58]);at+=60;a.need(n>=0 and at+n<=len(raw),'ar extent')
   if name.startswith('data.tar'):a.need(payload is None,'unique package data');payload=raw[at:at+n]
   at+=n+n%2
  a.need(payload is not None,'Debian data tar');total=0;count=0
  with tarfile.open(fileobj=io.BytesIO(payload),mode='r|*',tarinfo=image_archive.bounded_tarinfo(image_archive.tar_bounds(),lambda:None,64*1024**2)) as tf:
   for m in tf:
    count+=1;total+=m.size;a.need(count<=30000 and total<=256*1024**2,'package budget');name=image_archive._path(m.name,True)
    if not name.startswith('usr/include/') or m.isdir():continue
    dest=private/name;dest.parent.mkdir(parents=True,exist_ok=True)
    if m.issym() or m.islnk():
     target=image_archive._link(name,m.linkname,m.islnk());relative=os.path.relpath(private/target,dest.parent)
     if dest.exists() or dest.is_symlink():a.need(dest.is_symlink() and os.readlink(dest)==relative,'header alias collision')
     else:dest.symlink_to(relative)
     records[name]=dict(kind='symlink',target=relative,package_sha256=row['sha256'])
    else:
     a.need(m.isfile(),'regular package header');f=tf.extractfile(m);data=f.read(64*1024**2+1);a.need(len(data)==m.size<=64*1024**2,'header size')
     if dest.exists():a.need(a.read(dest,64*1024**2)==data,'header collision')
     else:dest.write_bytes(data);dest.chmod(0o644)
     records[name]=dict(kind='file',nbytes=len(data),sha256=a.sha(data),package_sha256=row['sha256'])
 return records

def stage_sources(work,commands,env):
 git=builder.TOOLS['git'];upstream=work/'upstream';source_dir=work/'source';common=[git,'-c','credential.helper=','-c','core.hooksPath=/dev/null','-c','http.sslVerify=true','-c','core.fsmonitor=false']
 for index,cmd in enumerate([common+['clone','--filter=blob:none','--no-checkout','--depth=1','https://github.com/panda3d/panda3d.git',str(upstream)],common+['-C',str(upstream),'fetch','--depth=1','origin',source.old.REVISION],common+['-C',str(upstream),'checkout','--detach',source.old.REVISION]]):
  r=builder.run_owned(cmd,work,env,work/('source-command-'+str(index)),180,stream_limit=1024**2);commands.append(r);a.need(r['status']=='EXITED' and r['returncode']==0 and r['streams_complete'] and r['owned_group_reaped'],'pinned upstream transfer failed')
 code='import sys,json;sys.path.insert(0,sys.argv[1]);from scripts import panda_sdk_routes_stage as s;m=s.stage(sys.argv[2],sys.argv[3]);print(json.dumps(dict(source_files=m["source_tree_files"])))'
 cmd=[builder.TOOLS['python'],'-I','-S','-B','-c',code,str(a.ROOT),str(upstream),str(source_dir)];r=builder.run_owned(cmd,work,env,work/'source-stage',300,stream_limit=1024**2);commands.append(r);a.need(r['status']=='EXITED' and r['returncode']==0 and r['streams_complete'] and r['owned_group_reaped'],'verified source staging failed');return source_dir

def stage_provider_links(private,paths,inventory):
 target=Path(private)/'usr/lib/x86_64-linux-gnu';target.mkdir(parents=True,exist_ok=True)
 for image_path,data_path in paths.items():
  name=Path(image_path).name;dest=target/name;raw=a.read(data_path,64*1024**2)
  if dest.exists():a.need(a.read(dest,64*1024**2)==raw,'provider filename collision')
  else:dest.write_bytes(raw);dest.chmod(0o644)
 aliases={}
 for name,path in [('libGL.so','/usr/lib/x86_64-linux-gnu/libGL.so.1'),('libX11.so','/usr/lib/x86_64-linux-gnu/libX11.so.6')]:
  resolved=inventory.resolve(path);a.need(resolved in paths,'qualified linker provider missing');base=Path(resolved).name;dest=target/name;a.need(not dest.exists() and not dest.is_symlink(),'linker alias collision');dest.symlink_to(base);aliases[name]=dict(target=base,image_path=resolved)
 return aliases

def _copy(source,destination,limit):
 raw=a.read(source,limit);Path(destination).parent.mkdir(parents=True,exist_ok=True);Path(destination).write_bytes(raw);Path(destination).chmod(0o600)
def finalize_bundle(out,receipt,build_out,qualified,tools,gate_result):
 bundle=out/'bundle';reports=bundle/'reports';reports.mkdir(parents=True,exist_ok=True);(bundle/'logs').mkdir(exist_ok=True);build_out=Path(build_out)
 mapping={'host-before':'host-before.json','used-inputs':'used-inputs.json','compile-dependencies':'compile-dependencies.json','sdk-output-manifest':'sdk-output-manifest.json','source-manifest':'source-manifest.json','configuration':'configuration.json','tools-before':'tools-before.json','tools-after':'tools-after.json'}
 for dst,src in mapping.items():
  if (build_out/src).is_file():_copy(build_out/src,reports/(dst+'.json'),16*1024**2)
 if qualified:
  q=dict(qualified)
  if (build_out/'private-before.json').is_file():q['private_before']=inputs.parse(a.read(build_out/'private-before.json',16*1024**2))
  a.write(reports/'inputs.json',q)
 if (out/'work/tool-profile.json').is_file() and not (reports/'tools-before.json').exists():_copy(out/'work/tool-profile.json',reports/'tools-before.json',16*1024**2)
 if gate_result:
  a.write(reports/'gate.json',gate_result)
  if 'layout' in gate_result:a.write(reports/'layout.json',gate_result['layout'])
  if 'provider_audit' in gate_result:a.write(reports/'provider-audit.json',gate_result['provider_audit'])
  if 'loader_metadata' in gate_result:a.write(reports/'loader-metadata.json',gate_result['loader_metadata'])
 candidates={'candidate/libpandagl.so.data':build_out/'sdk/lib/libpandagl.so','candidate/build-libpanda.so.data':build_out/'sdk/lib/libpanda.so.1.10','candidate/layout-contract.o.data':build_out/'layout-build/layout-contract.o'}
 for name,path in candidates.items():
  if path.is_file():_copy(path,bundle/name,carrier.FILE_LIMITS[name])
 # Keep exact selected compiler output; other owned command diagnostics in host log.
 make=build_out/'makepanda/stdout.log';_copy(make,bundle/'logs/makepanda.log',16*1024**2) if make.is_file() else (bundle/'logs/makepanda.log').write_bytes(b'')
 collected=[]
 for p in sorted((out/'work').rglob('*.log')):
  if p==make or p.is_symlink():continue
  data=a.read(p,16*1024**2);collected.append(str(p.relative_to(out)).encode()+b'\n'+data+b'\n')
 host=b''.join(collected);a.need(len(host)+(bundle/'logs/makepanda.log').stat().st_size<=32*1024**2,'combined build logs');(bundle/'logs/host.log').write_bytes(host)
 regular={str(p.relative_to(bundle)):dict(nbytes=p.stat().st_size,sha256=a.sha(a.read(p,carrier.FILE_LIMITS[str(p.relative_to(bundle))]))) for p in bundle.rglob('*') if p.is_file() and str(p.relative_to(bundle))!='reports/receipt.json'}
 receipt['files']=regular;receipt['omissions']=sorted(carrier.FILES-set(regular)-{'reports/receipt.json'});a.need(sum(x['nbytes'] for x in regular.values())<=240*1024**2,'carrier total bytes')
 if receipt['status']=='CG_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME' and receipt['omissions']:receipt.update(status='FAILED',failure='incomplete success carrier')
 a.write(reports/'receipt.json',receipt)

def record_failure(receipt,error):
 receipt.update(status='FAILED' if receipt.get('build_start_attempts') else 'BLOCKED',failure=type(error).__name__+': '+str(error))

def seal_failure_bundle(out,receipt):
 out=Path(out);bundle=out/'bundle';(bundle/'reports').mkdir(parents=True,exist_ok=True);quarantine=out/'work/rejected-bundle';regular={};total=0
 for p in sorted(bundle.rglob('*')):
  if not p.is_file():continue
  name=str(p.relative_to(bundle))
  if name=='reports/receipt.json':continue
  if p.is_symlink() or name not in carrier.FILES or p.stat().st_size>carrier.FILE_LIMITS.get(name,0) or total+p.stat().st_size>240*1024**2:
   quarantine.mkdir(parents=True,exist_ok=True);p.rename(quarantine/(name.replace('/','__')));continue
  data=a.read(p,carrier.FILE_LIMITS[name]);regular[name]=dict(nbytes=len(data),sha256=a.sha(data));total+=len(data)
 receipt.update(files=regular,omissions=sorted(carrier.FILES-set(regular)-{'reports/receipt.json'}));a.write(bundle/'reports/receipt.json',receipt)

def run_production(out=None):
 builder.action_context();raw=a.read(a.ROOT/a.REQUEST,4*1024**2);request=a.parse(raw);a.validate_request(request,a.ROOT);out=Path(out or a.ROOT/OUT);a.need(not out.exists(),'fresh producer output');out.mkdir(parents=True);(out/'bundle/reports').mkdir(parents=True);work=out/'work';work.mkdir();stop=time.monotonic()+2400;ctx=dict(repository=os.environ['GITHUB_REPOSITORY'],head_sha=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),attempt=int(os.environ['GITHUB_RUN_ATTEMPT']),event=os.environ['GITHUB_EVENT_NAME'],actor=os.environ['GITHUB_ACTOR']);client=BuildClient(out/'api',repository=a.REPO,token=os.environ['GH_TOKEN'],deadline=stop,max_requests=96,max_payload_bytes=4*1024**3)
 receipt=dict(schema='panda-sdk-cg-production-v1',status='BLOCKED',source_sha=request['source_sha'],activation_sha=ctx['head_sha'],run_id=ctx['run_id'],request_sha256=a.sha(raw),build_start_attempts=0,native_admitted=False,stage7_complete=False,target_execution=False,scientific_native_runs=0,contract_sha256=inputs.CONTRACT_SHA,image_sha256=inputs.contract()['current_image_sha256'],files={},omissions=[],staging=[]);qualified=None;tools=None;result=None;build_out=work/'build'
 try:
  from scripts.engine_clock_image_transport import _absolute_deadline
  with _absolute_deadline(stop):
   run=authenticate_context(client,request,ctx,raw);receipt['workflow_id']=run['workflow_id'];a.need(shutil.disk_usage(out).free>=16*1024**3,'16GiB initial free required');tools=builder.measure_tools(out=work/'tool-profile.json');receipt['host_resources']=dict(initial_free_bytes=shutil.disk_usage(out).free,memory_capacity=Path('/proc/meminfo').read_text().splitlines()[0],aggregate_cgroup_memory_limit_claimed=False)
   paths,inventory=acquire_image(client,work,stop);c=inputs.contract();pin=c['cg_archive'];client.download(pin['url'],work/'cg.tgz',nbytes=pin['nbytes'],sha256=pin['sha256'],kind='cg-header');qualified=inputs.qualify_inputs(work/'cg.tgz',a.ROOT/c['current_image_acceptance_path'],{n:paths[x['image_path']] for n,x in c['image_cg_providers'].items()},work/'private');qualified['header_packages']=populate_headers(qualified['root']);qualified['linker_aliases']=stage_provider_links(qualified['root'],paths,inventory)
   env=dict(PATH='/usr/bin:/bin',LANG='C',LC_ALL='C',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_TERMINAL_PROMPT='0');stage=stage_sources(work,receipt['staging'],env);a.need(time.monotonic()<stop and sum(p.stat().st_size for p in work.rglob('*') if p.is_file() and not p.is_symlink())<=4*1024**3,'staged input/time budget');compiled=builder.build(stage,qualified,build_out,tools);receipt['compiler_build']=compiled;receipt['build_start_attempts']=compiled['build_start_attempts'];result=gate.audit_candidate(compiled['candidate'],compiled['layout_object'],compiled,a.ROOT/c['audit_path'],paths);receipt['status']=result['status'] if result['status']=='CG_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME' else 'FAILED';a.validate_request(request,a.ROOT);a.need(time.monotonic()<stop,'whole producer deadline')
 except BaseException as e:record_failure(receipt,e)
 finally:
  if (build_out/'receipt.json').is_file():receipt['compiler_build']=a.parse(a.read(build_out/'receipt.json',16*1024**2));receipt['build_start_attempts']=receipt['compiler_build']['build_start_attempts']
  if receipt['status']=='BLOCKED' and receipt['build_start_attempts']:receipt['status']='FAILED'
  try:finalize_bundle(out,receipt,build_out,qualified,tools,result)
  except BaseException as e:
   receipt.update(status='FAILED',bundle_failure=type(e).__name__+': '+str(e));seal_failure_bundle(out,receipt)
 return receipt

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true',required=True);p.parse_args()
 try:r=run_production();print(json.dumps({k:r[k] for k in ['status','build_start_attempts','target_execution']}));return 0 if r['status']=='CG_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME' else 2
 except Exception as e:print('CG build rejected: '+type(e).__name__+': '+str(e));return 2
if __name__=='__main__':raise SystemExit(main())
