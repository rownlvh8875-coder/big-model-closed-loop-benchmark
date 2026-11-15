"""Compare the new SDK to authenticated retained renderer image bytes, as data."""
import argparse,hashlib,json,re,time
from pathlib import Path,PurePosixPath
from scripts import panda_sdk_coverage as coverage
from scripts import engine_clock_image_archive_v2 as archive
from scripts.panda_dispatch_coverage import read_input
ROOT=coverage.ROOT
RESULT='docs/evidence/STAGE7_ENGINE_CLOCK_SEALED_IMAGE_06_RESULT.json'
RESULT_SHA='f01f98ee86f7e1fc9eea175c844687f24901360385c42caa492845a73a62b8aa'
IMAGE='output/stage7-image-root-authentication/image-20261114-06/accepted-carrier/image.tar'
TAG='stage7-engine-clock:image-20261114-01'
need=coverage.need

def compare_installed(entries,candidate_sha):
    need(type(candidate_sha) is str and re.fullmatch('[a-f0-9]{64}',candidate_sha),'candidate digest required')
    need(type(entries) is list and 0<len(entries)<=100000,'closed inventory budget')
    seen=set();files=[]
    for row in entries:
        need(type(row) is dict and type(row.get('path')) is str,'inventory row')
        p=row['path'];need(p.startswith('/') and str(PurePosixPath(p))==p and '..' not in PurePosixPath(p).parts and p not in seen,'canonical unique inventory path');seen.add(p)
        need(row.get('kind') in ('file','directory','symlink'),'inventory kind')
        if row['kind']=='file':need(type(row.get('sha256')) is str and re.fullmatch('[a-f0-9]{64}',row['sha256']),'inventory file digest');files.append(row)
    panda=[dict(path=r['path'],sha256=r['sha256']) for r in files if re.fullmatch(r'/opt/(?:venv|python)/lib/python3\.11/site-packages/panda3d/libpandagl\.so(?:\.1\.10)?',r['path'])]
    need(len(panda)<=1,'multiple Panda GL library candidates')
    installed=len(panda)==1 and panda[0]['sha256']==candidate_sha
    python=any(r['path']=='/opt/python/lib/libpython3.11.so.1.0' for r in files)
    metadrive=any(re.fullmatch(r'/opt/(?:venv|python)/lib/python3\.11/site-packages/metadrive/__init__\.py',r['path']) for r in files)
    blockers=[]
    if not installed:blockers.append('CANDIDATE_SDK_NOT_INSTALLED')
    if not python:blockers.append('PYTHON_RUNTIME_NOT_IN_INVENTORY')
    if not metadrive:blockers.append('METADRIVE_NOT_IN_INVENTORY')
    return dict(schema='panda-sdk-installed-membership-v1',candidate_sha256=candidate_sha,candidate_sdk_installed=installed,panda_gl_files=panda,python_runtime_present=python,metadrive_present=metadrive,installed_entries=len(entries),blockers=blockers,runtime_binding_qualified=False,native_admitted=False)

def inspect_retained_image(out):
    out=coverage.stage.canonical(out);need(not out.exists(),'existing image assessment preserved');out.mkdir(parents=True)
    raw=read_input(ROOT/RESULT,1024**2);need(coverage.digest(raw)==RESULT_SHA,'retained image authority pin');authority=json.loads(raw)
    need(authority['status']=='AUTHENTICATED_PROVIDER_FREE_IMAGE_AND_INSTALLED_BYTES_MATCH' and authority['native_admission'] is False,'retained authority scope')
    for row in authority['authority_files'].values():
        p=ROOT/row['path'];need(p.is_relative_to(ROOT/'docs/evidence/engine-clock-sealed-image-06'),'authority path scope')
        data=read_input(p,16*1024**2);need(len(data)==row['nbytes'] and coverage.digest(data)==row['sha256'],'retained authority file drift')
    data=read_input(ROOT/'docs/evidence/engine-clock-sealed-image-06/installed-files.json',16*1024**2)
    need(len(data)==authority['installed_files_nbytes'] and coverage.digest(data)==authority['installed_files_sha256'],'closed installed inventory drift')
    inventory=json.loads(data);need(inventory['schema']=='installed-files-v1' and len(inventory['entries'])==authority['installed_entries'],'complete installed inventory required')
    start=time.perf_counter();check=archive.inspect_save_archive(ROOT/IMAGE,expected_tag=TAG,deadline=start+180)
    for key in ('image_tar_sha256','image_tar_nbytes','config_digest','rootfs_diff_ids'):need(check[key]==authority[key],'retained archive identity mismatch: '+key)
    membership=compare_installed(inventory['entries'],coverage.CANDIDATE)
    result=dict(schema='panda-sdk-image-binding-assessment-v1',kind='AUTHENTICATED_RETAINED_IMAGE_DATA_ONLY',candidate_sha256=coverage.CANDIDATE,authority_path=RESULT,authority_sha256=RESULT_SHA,archive_path=IMAGE,archive_check=check,archive_wall_seconds=time.perf_counter()-start,installed_files_sha256=authority['installed_files_sha256'],membership=membership,blockers=membership['blockers']+['NEW_SDK_MAPPED_ABI_AND_DISPATCH_NOT_QUALIFIED','EARLY_INSTALL_AND_IDENTITY_HANDOFF_NOT_QUALIFIED'],candidate_image_ready=False,runtime_binding_qualified=False,actual_image_loaded=False,new_native_runs=0,new_model_runs=0,native_admitted=False,stage7_complete=False)
    (out/'image-binding.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args(argv)
    try:r=inspect_retained_image(args.out);print(json.dumps(dict(candidate_sdk_installed=r['membership']['candidate_sdk_installed'],image_tar_sha256=r['archive_check']['image_tar_sha256'],blockers=r['blockers'],native_admitted=False)));return 0
    except (ValueError,OSError) as exc:print('image assessment rejected: '+str(exc));return 2
if __name__=='__main__':raise SystemExit(main())
