"""Authenticate new bounded mapping proof over TLS; never load SDK locally."""
import argparse,base64,json,os,subprocess,sys,time
from pathlib import Path
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk_mapping_policy as a
from scripts import run_panda_sdk_mapping_canary as host
from scripts import panda_sdk_mapping_runtime as runtime
from scripts.panda_sdk_mapping_carrier import extract_carrier
from scripts.engine_clock_image_transport import Client
from scripts.panda_dispatch_coverage import read_input
def validate_result(c,r,e,source,activation,run_id,request_sha):
 for k,v in dict(schema='panda-sdk-mapping-canary-v1',source_sha=source,activation_sha=activation,run_id=run_id,request_sha256=request_sha,sdk_sha256=a.SDK_SHA,image_sha256=a.IMAGE_SHA).items():a.need(c.get(k)==v,'canary identity: '+k)
 a.need(c['native_admitted'] is False and c['stage7_complete'] is False and type(c['scientific_native_runs']) is int and c['scientific_native_runs']==0 and type(c['start_attempts']) is int and c['start_attempts'] in (0,1) and type(c['mapping_window_consumed']) is bool and c['mapping_window_consumed']==bool(c['start_attempts']),'canary bounded flags')
 passed=c['status']=='MAPPING_ONLY_CANARY_PASSED'
 if passed:
  a.need(c['mapping_window_consumed'] and c['start_attempts']==1 and c['owned_container_removed'] is True and c['selected_sdk_code_mapping_verified'] is True and type(c['selected_c_abi_calls_verified']) is int and c['selected_c_abi_calls_verified']==5 and r['fixture'] is False and r['image_membership_verified'] is True and r['nonce']==c['nonce'] and r['binding_sha256']==c['binding_sha256'],'successful owned mapping context');runtime.validate_window(a.mapping_profile(a.ROOT),r);runtime.check_context(r['context'],c['host_namespaces']);a.need(e['tools_before']==e['tools_after'] and e['tools_after_verified'] is True,'tool profiles')
  for point in ['memory_before','memory_after']:a.need(r[point]['max_bytes']==a.BUDGET['memory_bytes'] and all(r[point]['events'][k]==0 for k in ['oom','oom_kill']),'actual memory bound')
  starts=[x for x in e['commands'] if x['command'][2]=='start'];a.need(len(starts)==1 and starts[0]['command'][3:]==['--attach',c['container_id']],'one exact start command')
 else:
  a.need(c['status']=='MAPPING_ONLY_CANARY_FAILED','known canary outcome')
  if r.get('schema')=='panda-sdk-failed-start-capture-v1':
   a.need(r['runtime_semantics_validated'] is False and r['native_admitted'] is False and r['external_origin_authenticated'] is False,'failed wire cannot grant semantics')
   for name,limit in [('stdout',8*1024**2),('stderr',128*1024)]:
    value=r['captured_'+name];raw=base64.b64decode(value['base64'],validate=True);a.need(len(raw)==value['nbytes']<=limit and a.sha(raw)==value['sha256'],'failed wire byte identity')
 return dict(status='CANARY_RECEIPT_SEMANTICS_MATCH',canary_passed=passed,external_origin_authenticated=False,native_admitted=False,stage7_complete=False)
def accept_canary(source,activation,run_id,out):
 out=Path(os.path.abspath(out));a.need(not out.exists() and not out.is_symlink(),'existing acceptance preserved');a.need(a.hexstr(source,40) and a.hexstr(activation,40) and a.positive(run_id),'expected caller identity');out.mkdir(parents=True);result=dict(schema='panda-sdk-mapping-accepted-v1',status='FAILED',actions_output_origin_authenticated=False,native_admitted=False,stage7_complete=False)
 def save():host.save_json(out/'acceptance.json',result,1024**2)
 save()
 try:
  stop=time.monotonic()+600;token=os.environ.get('GH_TOKEN') or subprocess.check_output(['gh','auth','token'],text=True,stderr=subprocess.PIPE,timeout=10).strip();client=Client(out/'api',repository=a.REPO,token=token,deadline=stop,max_requests=96,max_payload_bytes=32*1024**2);commit=client.get_json('commits/'+activation,'request-commit.json');entry=host.tree_request_mode(client,commit,prefix='request');blob=client.get_json('git/blobs/'+entry['sha'],'request-blob.json');a.need(blob['encoding']=='base64' and a.positive(blob['size'],1024**2),'request blob');raw=base64.b64decode(blob['content']);a.need(len(raw)==blob['size'],'request bytes');request=a.parse(raw);a.need(request['source_sha']==source,'caller source');ctx=dict(repository=a.REPO,head_sha=activation,run_id=run_id,attempt=1,event='push',actor=a.OWNER);run=host.authenticate_context(client,request,ctx,raw,completed=True);jobs=client.get_json('actions/runs/'+str(run_id)+'/jobs','canary-jobs.json');job=a.validate_production_job(run,jobs);listing=client.get_json('actions/runs/'+str(run_id)+'/artifacts','artifacts.json');artifact=a.validate_artifacts(run,listing);client.download('https://api.github.com/repos/'+a.REPO+'/actions/artifacts/'+str(artifact['id'])+'/zip',out/'proof.zip',nbytes=artifact['size_in_bytes'],sha256=artifact['digest'][7:],kind='artifact');carrier=extract_carrier(out/'proof.zip',out/'candidate',deadline=stop);c=a.parse(read_input(out/'candidate/canary.json',1024**2));r=a.parse(read_input(out/'candidate/runtime.json',12*1024**2));e=a.parse(read_input(out/'candidate/execution.json',4*1024**2));semantics=validate_result(c,r,e,source,activation,run_id,a.sha(raw));a.need(not semantics['canary_passed'] or run['conclusion']=='success','failed job cannot grant successful canary');result.update(status='AUTHENTICATED_MAPPING_ONLY_CANARY_PASSED' if semantics['canary_passed'] else 'AUTHENTICATED_MAPPING_ONLY_CANARY_FAILED',actions_output_origin_authenticated=True,source_sha=source,activation_sha=activation,run_id=run_id,workflow_id=run['workflow_id'],job_id=job,artifact_id=artifact['id'],artifact_zip_sha256=artifact['digest'][7:],artifact_zip_nbytes=artifact['size_in_bytes'],request_sha256=a.sha(raw),carrier=carrier,receipt_semantics=semantics,mapping_window_consumed=c['mapping_window_consumed'],start_attempts=c['start_attempts'],canary_passed=semantics['canary_passed'],sdk_sha256=a.SDK_SHA,image_sha256=a.IMAGE_SHA,selected_c_abi_calls_verified=5 if semantics['canary_passed'] else None,full_object_abi_qualified=False,runtime_admission_ready=False,scientific_native_runs=0,strict_current_result='0/4 FAIL');save();return result
 except BaseException as error:result.update(status='FAILED',actions_output_origin_authenticated=False,failure=type(error).__name__+': '+str(error));save();raise
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--activation',required=True);p.add_argument('--run-id',type=int,required=True);p.add_argument('--out',required=True);c=p.parse_args()
 try:r=accept_canary(c.source,c.activation,c.run_id,c.out);print(json.dumps({k:r[k] for k in ['status','canary_passed','mapping_window_consumed','native_admitted']}));return 0
 except Exception as e:print('mapping acceptance rejected: '+type(e).__name__+': '+str(e));return 2
if __name__=='__main__':raise SystemExit(main())
