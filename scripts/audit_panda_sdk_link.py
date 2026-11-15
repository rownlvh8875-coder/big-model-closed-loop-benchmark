"""Audit exact SDK bytes against authenticated image providers without loading."""
import argparse,hashlib,json,time
from pathlib import Path
from scripts import panda_sdk_link_image as image
from scripts import panda_sdk_image_archive as archive
from scripts.panda_dispatch_coverage import read_input
ROOT=image.ROOT;need=image.need

def audit(image_path,candidate,out):
 image_path=Path(image_path).absolute();candidate=Path(candidate).absolute();out=Path(out).absolute();need(not out.exists(),'existing audit preserved');raw=read_input(ROOT/image.AUTH,1024**2);need(hashlib.sha256(raw).hexdigest()==image.AUTH_SHA,'authenticated authority pin');authority=json.loads(raw);need(authority['status']=='AUTHENTICATED_ACTIONS_SDK_IMAGE_BYTES_NATIVE_BLOCKED' and authority['actions_output_origin_authenticated'] is True and authority['native_admitted'] is False,'authenticated image scope');manifest_raw=read_input(ROOT/'docs/evidence/panda-sdk-image-auth-01/actual/acceptance/candidate/installed-files.json',16*1024**2);need(hashlib.sha256(manifest_raw).hexdigest()==authority['installed_manifest_sha256'],'installed inventory pin');inventory=image.Inventory(json.loads(manifest_raw));stop=time.monotonic()+900;out.mkdir(parents=True);report=dict(status='FAILED',native_admitted=False,runtime_mapping_qualified=False,stage7_complete=False)
 def save():(out/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
 save()
 try:
  check=archive.inspect_save_archive(image_path,expected_tag='stage7-panda-sdk:actions-20261115-02',deadline=time.perf_counter()+180)
  for k in ('image_tar_sha256','image_tar_nbytes','config_digest','rootfs_diff_ids'):need(check[k]==authority['archive'][k],'authenticated archive drift: '+k)
  data=read_input(candidate,64*1024**2);candidate_sha=hashlib.sha256(data).hexdigest();reader=image.SelectedImage(image_path,inventory,check,out/'providers',deadline=stop);result,nodes=image.provider_graph(reader,data)
  for p,row in reader.cache.items():need(hashlib.sha256(read_input(Path(row['data_path']),64*1024**2)).hexdigest()==row['sha256'],'final provider drift')
  need(hashlib.sha256(read_input(candidate,64*1024**2)).hexdigest()==candidate_sha,'candidate changed');need(time.monotonic()<stop,'audit deadline')
  (out/'loader-metadata.json').write_text(json.dumps(nodes,indent=2)+'\n');report.update(status='STATIC_SYMBOLS_AVAILABLE_NOT_RUNTIME' if result['root_strong_symbols_available'] else 'STATIC_LINK_BLOCKED',candidate_sha256=candidate_sha,candidate_nbytes=len(data),candidate_installed=inventory.rows[image.LIB]['sha256']==candidate_sha,image_sha256=check['image_tar_sha256'],image_nbytes=check['image_tar_nbytes'],authority_sha256=image.AUTH_SHA,installed_inventory_sha256=authority['installed_manifest_sha256'],root_symbol_availability=result,selected_providers=len(reader.cache),actual_loader_invocations=0,actual_native_runs=0,official_model_calls=0);save();return report
 except BaseException as e:report['failure']=type(e).__name__+': '+str(e);save();raise

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--image',default='output/stage7-panda-sdk-image-auth-01/acceptance/candidate/image.tar');p.add_argument('--candidate',required=True);p.add_argument('--out',required=True);a=p.parse_args(argv)
 try:r=audit(a.image,a.candidate,a.out);print(json.dumps(dict(status=r['status'],strong_missing=len(r['root_symbol_availability']['missing']),weak_unresolved=len(r['root_symbol_availability']['weak_unresolved']),providers=r['selected_providers'],candidate_installed=r['candidate_installed'],native_admitted=False)));return 0
 except (ValueError,OSError) as e:print('static link audit rejected: '+str(e));return 2
if __name__=='__main__':raise SystemExit(main())
