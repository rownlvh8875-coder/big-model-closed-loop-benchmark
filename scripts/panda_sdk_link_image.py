"""Image-bound selected ELF payloads as nonexecutable DATA, not a rootfs extract."""
import hashlib,json,os,posixpath,stat,tarfile,time
from pathlib import Path
from scripts import panda_sdk_image_archive as archive
from scripts.engine_clock_runtime_inventory import validate_inventory
from scripts.produce_panda_sdk_image import file_hash
from scripts.panda_dispatch_coverage import read_input
from scripts.panda_sdk_link_elf import inspect_elf,available_imports
ROOT=Path(__file__).resolve().parents[1]
AUTH='docs/evidence/panda-sdk-image-auth-01/actual/acceptance/acceptance.json'
AUTH_SHA='f5ac58f63d6a0d2b8f1205b456df6e8e8855f714f086274e122ec0fab516c5b8'
PANDA='/opt/venv/lib/python3.11/site-packages/panda3d';LIB=PANDA+'/libpandagl.so'
DEFAULTS=('/usr/lib/x86_64-linux-gnu','/usr/lib64')
def need(v,msg='SDK_LINK_IMAGE_REJECTED'):
 if not v:raise ValueError(msg)
def canonical(path):
 need(type(path) is str and path.startswith('/') and len(path)<=4096 and '\0' not in path and '\\' not in path and all(x not in ('','.','..') for x in path[1:].split('/')),'canonical image path');return path
class Inventory:
 def __init__(self,document):
  self.document=validate_inventory(document);self.rows={r['path']:r for r in self.document['entries']}
 def resolve(self,path):
  path=canonical(path);seen=set()
  for _ in range(64):
   need(path not in seen,'inventory alias cycle');seen.add(path);parts=path.strip('/').split('/');changed=False
   for n in range(1,len(parts)+1):
    prefix='/'+('/'.join(parts[:n]));row=self.rows.get(prefix)
    if row and row['kind']=='symlink':
     target=row['target'];stack=[] if target.startswith('/') else parts[:n-1]
     for token in target.split('/')+parts[n:]:
      if token in ('','.'):continue
      if token=='..':need(stack,'alias escapes root');stack.pop()
      else:stack.append(token)
     path=canonical('/'+'/'.join(stack));changed=True;break
    if row and row['kind']=='file' and n<len(parts):raise ValueError('alias traverses regular file')
   if not changed:
    need(path in self.rows and self.rows[path]['kind']=='file','inventory regular target missing');return path
  raise ValueError('inventory alias depth')
 def select(self,requester,name,metadata):
  need(type(name) is str and name and '/' not in name and '\\' not in name and name not in ('.','..'),'needed basename')
  directories=[]
  if requester==LIB and name in ('libpanda.so.1.10','libpandaexpress.so.1.10','libp3dtool.so.1.10','libp3dtoolconfig.so.1.10'):directories.append(PANDA)
  configured=metadata.get('runpath') if metadata.get('runpath') is not None else metadata.get('rpath')
  if configured:
   for value in configured.split(':'):
    need(value and ('$' not in value.replace('${ORIGIN}','').replace('$ORIGIN','')),'unsupported RPATH token');value=value.replace('${ORIGIN}',posixpath.dirname(requester)).replace('$ORIGIN',posixpath.dirname(requester));need(value.startswith('/'),'relative RPATH unsupported');directories.append(posixpath.normpath(value))
  directories.extend(DEFAULTS)
  for directory in dict.fromkeys(directories):
   path=canonical(directory+'/'+name)
   try:return self.resolve(path)
   except ValueError:
    # Missing alternatives may be skipped; a present alias must not silently
    # fall through a malformed/cyclic target to a different provider.
    if path in self.rows:raise
  raise ValueError('needed provider absent: '+name+' requested by '+requester)
class SelectedImage:
 def __init__(self,path,inventory,check,out,deadline):
  self.path=Path(path).absolute();self.inventory=inventory;self.check=check;self.out=Path(out).absolute();self.stop=min(deadline,time.monotonic()+900);need(not self.out.exists() and self.out.resolve()==self.out,'fresh canonical extraction output');need(self.path.resolve()==self.path,'canonical image archive');need(file_hash(self.path,2*1024**3,self.stop)==dict(nbytes=check['image_tar_nbytes'],sha256=check['image_tar_sha256']),'image archive identity');self.key=archive._signature(self.path.stat());self.cache={};self.blobs=set();self.out.mkdir(parents=True)
 def collect(self,paths):
  paths=sorted(set(canonical(p) for p in paths));need(0<len(paths)<=64,'selected file count');need(all(self.inventory.resolve(p)==p for p in paths),'select resolved regular paths only');new=set(paths)-set(self.cache)
  if not new:return {p:self.cache[p] for p in paths}
  wanted=set(self.cache)|new;need(len(wanted)<=64 and sum(self.inventory.rows[p]['nbytes'] for p in wanted)<=256*1024**2,'selected total byte budget');need(archive._signature(self.path.stat())==self.key,'archive drift');found={};stop=min(self.stop,time.monotonic()+180);bounds=archive.tar_bounds();remaining=[3*1024**3]
  def check():need(time.monotonic()<stop,'selected image deadline')
  fd=os.open(self.path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  with os.fdopen(fd,'rb') as source,tarfile.open(fileobj=source,mode='r:',tarinfo=archive.bounded_tarinfo(bounds,check,2*1024**3)) as outer:
   need(archive._signature(os.fstat(source.fileno()))==self.key,'opened archive drift')
   for layer in self.check['layers']:
    changes={};deleted=set();seen=set()
    with outer.extractfile(layer['path']) as raw:
     reader=archive._LayerReader(raw,remaining,check)
     with tarfile.open(fileobj=reader,mode='r|',tarinfo=archive.bounded_tarinfo(bounds,check,512*1024**2)) as t:
      for member in t:
       check();name=archive._path(member.name,True);need(name not in seen,'duplicate layer path');seen.add(name)
       if name=='.':continue
       name='/'+name;parent,leaf=posixpath.split(name)
       if leaf=='.wh..wh..opq':deleted.update(p for p in wanted if p.startswith(parent+'/'));continue
       if leaf.startswith('.wh.'):
        target=parent+'/'+leaf[4:];deleted.update(p for p in wanted if p==target or p.startswith(target+'/'));continue
       if not member.isdir():deleted.update(p for p in wanted if p==name or p.startswith(name+'/'))
       elif name in wanted:deleted.add(name)
       if name not in wanted:continue
       if not member.isfile():changes[name]=None;continue
       need(0<member.size<=64*1024**2,'selected ELF size');payload=t.extractfile(member);data=bytearray()
       for block in iter(lambda:payload.read(1024**2),b''):check();data.extend(block);need(len(data)<=member.size,'selected file extent')
       need(len(data)==member.size and sum(len(x[0]) for x in changes.values() if x is not None)+len(data)<=256*1024**2,'selected layer bytes');changes[name]=(bytes(data),member.mode)
     while reader.read(1024**2):check()
    for p in deleted:found.pop(p,None)
    for p,value in changes.items():
     if value is None:found.pop(p,None)
     else:found[p]=value
   need(archive._signature(os.fstat(source.fileno()))==self.key==archive._signature(self.path.stat()),'archive changed during selection')
  for p in wanted:
   need(p in found,'selected final payload missing/unsupported link: '+p);data,mode=found[p];expected=self.inventory.rows[p];digest=hashlib.sha256(data).hexdigest();need(len(data)==expected['nbytes'] and digest==expected['sha256'] and mode==expected['mode'],'selected final bytes/mode mismatch: '+p)
  for p in new:
   data,mode=found[p];digest=hashlib.sha256(data).hexdigest();dest=self.out/(digest+'.elf.data')
   if digest not in self.blobs:
    with dest.open('xb') as f:f.write(data)
    dest.chmod(0o600);self.blobs.add(digest)
   self.cache[p]=dict(path=p,sha256=digest,nbytes=len(data),image_mode=mode,data_path=str(dest),native_admitted=False)
  return {p:self.cache[p] for p in paths}

def provider_graph(reader,candidate):
 root=inspect_elf(candidate);root['path']=LIB;nodes={LIB:root};todo=[LIB];edges=[];records={}
 while todo:
  request=todo;todo=[];wanted=set()
  for p in request:
   for name in nodes[p]['needed']:
    selected=reader.inventory.select(p,name,nodes[p]);edges.append(dict(requester=p,needed=name,selected=selected))
    if selected not in nodes:wanted.add(selected)
  if wanted:
   fetched=reader.collect(sorted(wanted));records.update(fetched)
   for p,row in fetched.items():
    raw=read_input(Path(row['data_path']),64*1024**2);need(hashlib.sha256(raw).hexdigest()==row['sha256'],'provider DATA drift');meta=inspect_elf(raw);meta['path']=p;nodes[p]=meta;todo.append(p)
  need(len(nodes)<=64,'provider graph count')
 result=available_imports(root,list(nodes.values()));result.update(provider_count=len(nodes)-1,edges=edges,provider_records=records,root_sha256=root['elf_sha256'],root_needed=root['needed'],provider_policy='explicit root Panda package; object-local ORIGIN; fixed system directories; no glibc namespace/cache/interposition emulation',provider_audits={p:available_imports(m,list(nodes.values())) for p,m in nodes.items() if p!=LIB})
 return result,nodes
