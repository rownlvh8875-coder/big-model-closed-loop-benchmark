"""Closed Eigen header DATA qualification; no package installation or target execution."""
import io,json,lzma,os,re,tarfile,time
from pathlib import Path
from scripts import panda_sdk_cg_inputs as cg
from scripts import panda_sdk_image_archive as bounded
ROOT=cg.ROOT;need=cg.need;read=cg.read;sha=cg.sha;parse=cg.parse
CONTRACT='docs/evidence/panda-sdk-cg-residual-01/contract.json'
CONTRACT_SHA='89bcc8e4372670aa80d535a45969aaec820cd57e0a6549549cf7fd6d030af509'
def contract(root=ROOT):
 raw=read(root/CONTRACT,1024**2);need(sha(raw)==CONTRACT_SHA,'Eigen design authority changed');return parse(raw)
def parse_package(raw,pins):
 need(type(raw) is bytes and 8<len(raw)<=4*1024**2 and raw[:8]==b'!<arch>\n','bounded Debian ar');at=8;members={}
 try:
  while at<len(raw):
   h=raw[at:at+60];need(len(h)==60 and h[-2:]==b'`\n','ar header');name=h[:16].decode('ascii').strip().rstrip('/');digits=h[48:58].strip();need(digits.isdigit(),'ar size');n=int(digits);at+=60;need(name not in members and name in ('debian-binary','control.tar.xz','data.tar.xz') and at+n<=len(raw),'closed ar members');members[name]=raw[at:at+n];at+=n
   if n%2:need(raw[at:at+1]==b'\n','ar alignment');at+=1
  need(at==len(raw) and set(members)=={'debian-binary','control.tar.xz','data.tar.xz'} and members['debian-binary']==b'2.0\n','Debian package version');d=lzma.LZMADecompressor();data=d.decompress(members['data.tar.xz'],max_length=32*1024**2+1);need(len(data)<=32*1024**2 and d.eof and not d.unused_data,'bounded single xz stream')
  seen=set();headers={};bounds=bounded.tar_bounds();bounds['headers']=2048;stop=time.monotonic()+30
  def check():need(time.monotonic()<stop,'Eigen parser deadline')
  with tarfile.open(fileobj=io.BytesIO(data),mode='r:',tarinfo=bounded.bounded_tarinfo(bounds,check,32*1024**2)) as t:
   for m in t:
    check();name=bounded._path(m.name,True);need(name not in seen,'duplicate package path');seen.add(name)
    if name=='.':need(m.isdir(),'package root')
    if name.startswith('usr/include/eigen3/') and not m.isdir():
     need(m.isfile() and not m.issym() and not m.islnk() and name in pins and 0<m.size<=2*1024**2,'closed regular Eigen header');row=pins[name];need(type(row['nbytes']) is int and m.size==row['nbytes'],'Eigen header extent');stream=t.extractfile(m);need(stream is not None,'header stream');body=stream.read(2*1024**2+1);need(len(body)==m.size and sha(body)==row['sha256'],'Eigen header bytes');headers[name]=body
  need(set(headers)==set(pins),'exact Eigen header membership');return headers
 except (OSError,UnicodeError,lzma.LZMAError,tarfile.TarError,EOFError) as error:raise ValueError('invalid Eigen package') from error

def qualify_eigen(package,private_root):
 c=contract();raw=read(package,4*1024**2);pin=c['eigen'];need(len(raw)==pin['nbytes'] and sha(raw)==pin['sha256'],'Eigen package pin');manifest_raw=read(ROOT/c['eigen_headers_path'],1024**2);need(sha(manifest_raw)==c['eigen_headers_sha256'],'Eigen header manifest pin');manifest=parse(manifest_raw);need(manifest['selected_header_files']==530 and manifest['selected_header_nbytes']==8669561 and manifest['package_sha256']==pin['sha256'],'Eigen manifest facts');headers=parse_package(raw,manifest['files']);text=headers['usr/include/eigen3/Eigen/src/Core/util/Macros.h'].decode('ascii');version={k:re.findall(r'^#define\s+EIGEN_'+k+r'_VERSION\s+(\d+)\s*$',text,re.M) for k in ('WORLD','MAJOR','MINOR')};need(version==dict(WORLD=['3'],MAJOR=['4'],MINOR=['0']),'exact Eigen version')
 root=Path(private_root).absolute();need(root.is_dir() and root.resolve()==root,'canonical fresh private root');destination=root/'usr/include/eigen3';need(not destination.exists() and not destination.is_symlink() and destination.parent.resolve()==destination.parent,'new owned Eigen subtree');need(not (root/'eigen-inputs.json').exists(),'no repeated qualification')
 for name,body in headers.items():
  path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('xb') as f:f.write(body)
  path.chmod(0o644)
 result=dict(schema='panda-sdk-cg-eigen-inputs-v2',status='EIGEN_HEADERS_QUALIFIED_DATA_ONLY',root=str(root),contract_sha256=CONTRACT_SHA,package_sha256=pin['sha256'],header_files=len(headers),header_nbytes=sum(map(len,headers.values())),version='3.4.0',files=manifest['files'],target_execution=False,native_admitted=False,external_build_origin_authenticated=False)
 (root/'eigen-inputs.json').write_text(json.dumps(result,indent=2)+'\n');return result
