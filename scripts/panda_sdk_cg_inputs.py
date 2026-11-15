"""Pinned Cg headers and existing image providers, inspected/copied only as DATA."""
import hashlib,io,json,os,stat,tarfile,time
from pathlib import Path
from scripts import panda_sdk_image_archive as bounded
ROOT=Path(__file__).resolve().parents[1]
CONTRACT='docs/evidence/panda-sdk-cg-design-01/contract.json'
CONTRACT_SHA='b11e85da328bd4f68627fdd957b14f1aa4e2f0c898282404402405dd1f4d3630'
INVENTORY='docs/evidence/panda-sdk-abi0-image-01/actual/acceptance/candidate/installed-files.json'

def need(ok,message='CG_INPUTS_REJECTED'):
 if not ok:raise ValueError(message)
def sha(data):return hashlib.sha256(data).hexdigest()
def pairs(rows):
 out={}
 for k,v in rows:need(k not in out,'duplicate JSON key');out[k]=v
 return out
def parse(data):return json.loads(data,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
def read(path,limit):
 path=Path(path)
 try:fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 except OSError as e:raise ValueError('regular DATA input required') from e
 try:
  before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and 0<=before.st_size<=limit,'bounded regular DATA input');raw=b''
  with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(limit+1)
  after=os.fstat(fd);need(len(raw)==before.st_size<=limit and (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'input changed');return raw
 finally:os.close(fd)
def contract(root=ROOT):
 raw=read(root/CONTRACT,1024**2);need(sha(raw)==CONTRACT_SHA,'design contract changed');return parse(raw)
def extract_headers(data,pins):
 need(type(data) is bytes and 0<len(data)<=32*1024**2,'archive bound');need(set(pins)=={'usr/include/Cg/cg.h','usr/include/Cg/cgGL.h'},'exact header names');need(all(type(x['nbytes']) is int and 0<x['nbytes']<=1024**2 for x in pins.values()),'header extent')
 stop=time.monotonic()+30
 def check():need(time.monotonic()<stop,'archive deadline')
 bounds=bounded.tar_bounds();bounds['headers']=20000;remaining=[512*1024**2];reader=bounded._LayerReader(io.BytesIO(data),remaining,check);seen=set();result={}
 try:
  with tarfile.open(fileobj=reader,mode='r|',tarinfo=bounded.bounded_tarinfo(bounds,check,128*1024**2)) as tf:
   for member in tf:
    check();name=bounded._path(member.name,True);need(name not in seen,'duplicate archive member');seen.add(name)
    if name=='.':need(member.isdir(),'root directory')
    if member.issym() or member.islnk():bounded._link(name,member.linkname,member.islnk())
    if name in pins:
     need(member.isfile() and not member.issym() and not member.islnk(),'real header required');need(member.size==pins[name]['nbytes'],'header size');stream=tf.extractfile(member);need(stream is not None,'header stream');raw=stream.read(1024**2+1);need(len(raw)==member.size and sha(raw)==pins[name]['sha256'],'header digest');result[name]=raw
  while reader.read(1024**2):pass
 except (tarfile.TarError,EOFError,OSError) as e:raise ValueError('invalid Cg archive') from e
 need(set(result)==set(pins),'missing Cg headers');return result

def verify_providers(paths,expected):
 need(set(paths)==set(expected),'exact image provider set');records={}
 for name,path in paths.items():
  need('/' not in name and name in ('libCg.so','libCgGL.so'),'Cg provider name');raw=read(path,64*1024**2);m=expected[name];need(len(raw)==m['nbytes'] and sha(raw)==m['sha256'],'current image provider bytes');records[name]=dict(nbytes=len(raw),sha256=sha(raw),source_path=str(Path(path).absolute()))
 return records

def image_authority(path,root=ROOT):
 c=contract(root);need(Path(path).absolute()==root/c['current_image_acceptance_path'],'exact image authority path');raw=read(path,4*1024**2);need(sha(raw)==c['current_image_acceptance_sha256'],'image authority digest');a=parse(raw)
 need(a['actions_output_origin_authenticated'] is True and a['native_admitted'] is False and a['sdk_sha256']==c['current_sdk_sha256'] and a['archive']['image_tar_sha256']==c['current_image_sha256'],'authenticated frozen image');raw=read(root/INVENTORY,16*1024**2);need(sha(raw)==a['installed_manifest_sha256'],'image inventory digest');m=parse(raw);rows={r['path']:r for r in m['entries']};need(len(rows)==len(m['entries']),'duplicate inventory path')
 for name,p in c['image_cg_providers'].items():
  r=rows[p['image_path']];need(r['kind']=='file' and r['sha256']==p['sha256'] and r['nbytes']==p['nbytes'],'current image Cg membership')
 return c,a,rows

def qualify_inputs(archive,image_authority_path,provider_data,out):
 out=Path(out).absolute();need(not out.exists() and not out.is_symlink(),'existing output preserved');c,a,rows=image_authority(image_authority_path);raw=read(archive,32*1024**2);pin=c['cg_archive'];need(len(raw)==pin['nbytes'] and sha(raw)==pin['sha256'],'Cg archive pin');headers=extract_headers(raw,pin['headers']);providers=verify_providers(provider_data,c['image_cg_providers']);out.mkdir(parents=True);files={}
 for source,raw in headers.items():
  dest=out/source;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw);dest.chmod(0o644);files[source]=dict(nbytes=len(raw),sha256=sha(raw),origin='pinned-nvidia-header')
 for name,row in providers.items():
  dest=out/'usr/lib/x86_64-linux-gnu'/name;dest.parent.mkdir(parents=True,exist_ok=True);raw=read(provider_data[name],64*1024**2);need(len(raw)==row['nbytes'] and sha(raw)==row['sha256'],'provider copy drift');dest.write_bytes(raw);dest.chmod(0o644);files[str(dest.relative_to(out))]=dict(nbytes=len(raw),sha256=sha(raw),origin='authenticated-current-image',image_path=c['image_cg_providers'][name]['image_path'])
 result=dict(schema='panda-sdk-cg-inputs-v1',status='CURRENT_IMAGE_CG_INPUTS_QUALIFIED_DATA_ONLY',root=str(out),contract_sha256=CONTRACT_SHA,archive_sha256=pin['sha256'],image_authority_sha256=c['current_image_acceptance_sha256'],inventory_sha256=a['installed_manifest_sha256'],files=files,providers=providers,target_execution=False,native_admitted=False,external_build_origin_authenticated=False)
 (out/'inputs.json').write_text(json.dumps(result,indent=2)+'\n');return result
