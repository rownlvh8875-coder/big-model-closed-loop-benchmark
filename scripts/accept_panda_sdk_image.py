"""Authenticate actual Actions output over TLS, then inspect image bytes as DATA."""
import argparse,base64,json,os,subprocess,sys,time
from pathlib import Path
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import panda_sdk_image_auth as a
from scripts import produce_panda_sdk_image as producer
from scripts import panda_sdk_image_archive as archive
from scripts import panda_sdk_routes_image as image
from scripts.engine_clock_image_transport import Client
from scripts.panda_sdk_image_carrier import extract_carrier
from scripts.panda_dispatch_coverage import read_input

def validate_receipt(r,source,activation,run_id,request_sha,manifest_sha):
 for k,v in dict(schema='panda-sdk-actions-image-production-v1',status='COPY_ONLY_SDK_IMAGE_BYTES_VERIFIED_NATIVE_BLOCKED',request_id=a.ID,source_sha=source,activation_sha=activation,run_id=run_id,request_sha256=request_sha,sdk_sha256=a.SDK_SHA,sdk_nbytes=a.SDK_SIZE,installed_entries=44232,installed_manifest_sha256=manifest_sha).items():a.need(r.get(k)==v,'producer receipt field: '+k)
 for k in ('containers_started','new_native_runs','official_model_calls'):a.need(type(r.get(k)) is int and r[k]==0,'zero actual runs')
 for k in ('native_admitted','stage7_complete'):a.need(r.get(k) is False,'no native readiness')
 a.need(r.get('owned_stopped_container_removed') is True,'owned cleanup required');ar=r['archive'];a.need(a.hexstr(ar['image_tar_sha256']) and a.positive(ar['image_tar_nbytes'],2*1024**3) and type(ar['config_digest']) is str and ar['config_digest'].startswith('sha256:') and a.hexstr(ar['config_digest'][7:]),'receipt archive identity')
 return dict(status='PRODUCER_RECEIPT_SEMANTICS_MATCH',external_origin_authenticated=False,native_admitted=False)
def accept_image(source_sha,activation_sha,run_id,out):
 out=Path(os.path.abspath(out));a.need(not out.exists() and not out.is_symlink(),'existing acceptance preserved');a.need(a.hexstr(source_sha,40) and a.hexstr(activation_sha,40) and a.positive(run_id),'expected caller identities');out.mkdir(parents=True);stop=time.monotonic()+1800
 token=os.environ.get('GH_TOKEN') or subprocess.check_output(['gh','auth','token'],stderr=subprocess.PIPE,text=True,timeout=10).strip();a.need(token,'GitHub credential required');client=Client(out/'api',repository=a.REPO,token=token,deadline=stop,max_requests=96,max_payload_bytes=a.BUDGET['consumer_payload']);result=dict(schema='panda-sdk-image-authenticated-output-v1',status='FAILED',source_sha=source_sha,activation_sha=activation_sha,run_id=run_id,actions_output_origin_authenticated=False,native_admitted=False,containers_started=0,new_native_runs=0,official_model_calls=0,stage7_complete=False)
 def save():a.write(out/'acceptance.json',result)
 save()
 try:
  commit=client.get_json('commits/'+activation_sha,'request-commit.json');entry=producer.tree_request_mode(client,commit,prefix='request');blob=client.get_json('git/blobs/'+entry['sha'],'request-blob.json');a.need(blob['encoding']=='base64' and a.positive(blob['size'],4*1024**2),'request blob');raw=base64.b64decode(blob['content'],validate=False);a.need(len(raw)==blob['size'],'request bytes');r=a.parse(raw);a.need(r.get('source_sha')==source_sha,'caller reviewed source binding');ctx=dict(repository=a.REPO,head_sha=activation_sha,run_id=run_id,attempt=1,event='push',actor=a.OWNER);run=producer.authenticate_context(client,r,ctx,raw,completed=True);listing=client.get_json('actions/runs/'+str(run_id)+'/artifacts','output-artifacts.json');artifacts=a.validate_artifacts(run,listing);meta=artifacts[a.ARTIFACT];client.download('https://api.github.com/repos/'+a.REPO+'/actions/artifacts/'+str(meta['id'])+'/zip',out/'image.zip',nbytes=meta['size_in_bytes'],sha256=meta['digest'][7:],kind='artifact');carrier=extract_carrier(out/'image.zip',out/'candidate',deadline=stop);bundle=out/'candidate';expected=a.expected_inventory(a.ROOT);manifest_raw=read_input(bundle/'installed-files.json',16*1024**2);a.need(a.parse(manifest_raw)==expected,'expected installed inventory');receipt_raw=read_input(bundle/'preparation.json',4*1024**2);receipt=a.parse(receipt_raw);result['receipt_semantics']=validate_receipt(receipt,source_sha,activation_sha,run_id,a.sha(raw),a.sha(manifest_raw));check=archive.inspect_save_archive(bundle/'image.tar',expected_tag=a.TAG,deadline=producer.inspection_deadline(stop));auth=a.authority(a.ROOT);a.need(check['rootfs_diff_ids'][:-1]==auth['rootfs_diff_ids'] and len(check['rootfs_diff_ids'])==11,'base plus SDK layer');a.need(all(check[k]==receipt['archive'][k] for k in ('image_tar_sha256','image_tar_nbytes','config_digest','rootfs_diff_ids')),'producer/archive bytes');layer=image._copy_layer(bundle/'image.tar',check,a.SDK_SHA,a.SDK_SIZE,producer.inspection_deadline(stop));a.need(layer==receipt['copy_layer'],'SDK payload proof');a.need(receipt['container_before']==receipt['container_after']==dict(Status='created',Running=False,Pid=0),'producer stopped snapshots')
  ex=artifacts[a.ARTIFACT+'-execution'];client.download('https://api.github.com/repos/'+a.REPO+'/actions/artifacts/'+str(ex['id'])+'/zip',out/'execution.zip',nbytes=ex['size_in_bytes'],sha256=ex['digest'][7:],kind='artifact')
  result.update(status='AUTHENTICATED_ACTIONS_SDK_IMAGE_BYTES_NATIVE_BLOCKED',authentication='TLS-authenticated GitHub API source/run/artifact-digest lineage; no signature attestation',actions_output_origin_authenticated=True,artifact_id=meta['id'],artifact_zip_sha256=meta['digest'][7:],artifact_zip_nbytes=meta['size_in_bytes'],execution_artifact_id=ex['id'],request_sha256=a.sha(raw),producer_receipt_sha256=a.sha(receipt_raw),archive=check,copy_layer=layer,installed_entries=44232,installed_manifest_sha256=a.sha(manifest_raw),sdk_sha256=a.SDK_SHA,sdk_nbytes=a.SDK_SIZE,candidate_sdk_installed=True,producer_export_authenticated=True,independent_local_export=False,directory_metadata_attested=False,producer_consumer_runtime_equivalence=False);save();return result
 except BaseException as e:result['failure']=type(e).__name__+': '+str(e);save();raise

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--activation',required=True);p.add_argument('--run-id',required=True,type=int);p.add_argument('--out',required=True);x=p.parse_args()
 try:r=accept_image(x.source,x.activation,x.run_id,x.out);print(json.dumps(dict(status=r['status'],artifact_id=r['artifact_id'],image_sha256=r['archive']['image_tar_sha256'],native_admitted=False)));return 0
 except Exception as e:print('SDK image acceptance rejected: '+type(e).__name__+': '+str(e));return 2
if __name__=='__main__':raise SystemExit(main())
