"""Closed small mapping-proof carrier with pre-allocation bounds and deadlines."""
import hashlib,os,stat,struct,time,zipfile
from pathlib import Path
from scripts import panda_sdk_cg_eigen_policy as a
from scripts.engine_clock_image_transport import _absolute_deadline
MAX_ZIP=256*1024**2;MAX_DIRECTORY=65536
CONTRACT=a.eigen.contract()
FILE_LIMITS=dict(CONTRACT['success_carrier_file_limits']);FILES=set(FILE_LIMITS)
DIRS=set(CONTRACT['carrier_optional_directories']);NAMES=FILES|DIRS
FILE_LIMITS.update({name:0 for name in DIRS})
def signature(s):return s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink
def _preflight(f,size):
 f.seek(max(0,size-65557));tail=f.read(65557);at=tail.rfind(b'PK\x05\x06');a.need(at>=0 and len(tail)-at>=22,'ZIP end record');e=struct.unpack_from('<4s4H2LH',tail,at);end=size-len(tail)+at
 a.need(e[1]==e[2]==0 and e[7]<=1024 and at+22+e[7]==len(tail),'ZIP disks/comment/trailing bytes');count,cdsize,offset=e[4],e[5],e[6];directory_end=end
 if end>=20:
  f.seek(end-20);locator=f.read(20)
  if locator[:4]==b'PK\x06\x07':
   _,disk,where,disks=struct.unpack('<4sLQL',locator);a.need(disk==0 and disks==1 and 0<=where<=end-76,'ZIP64 locator');f.seek(where);raw=f.read(56);z=struct.unpack('<4sQ2H2L4Q',raw);a.need(z[0]==b'PK\x06\x06' and z[1]==44 and z[4]==z[5]==0 and where+56==end-20 and z[6]==z[7],'ZIP64 record')
   for old,new,sentinel in ((e[3],z[6],65535),(count,z[7],65535),(cdsize,z[8],0xffffffff),(offset,z[9],0xffffffff)):a.need(old in (sentinel,new),'ZIP64 cross binding')
   count,cdsize,offset=z[7],z[8],z[9];directory_end=where
 a.need(1<=count<=len(NAMES) and e[3] in (count,65535) and 0<cdsize<=MAX_DIRECTORY and 0<=offset and offset+cdsize==directory_end,'closed bounded ZIP directory');f.seek(offset);raw=f.read(cdsize);a.need(len(raw)==cdsize,'ZIP directory read');pos=0;seen=set();total=0
 for _ in range(count):
  a.need(pos+46<=len(raw) and raw[pos:pos+4]==b'PK\x01\x02','ZIP directory header');flags,method=struct.unpack_from('<HH',raw,pos+8);compressed,nbytes=struct.unpack_from('<LL',raw,pos+20);namelen,extra,comment,disk=struct.unpack_from('<4H',raw,pos+28);attr,local=struct.unpack_from('<LL',raw,pos+38);endpos=pos+46+namelen+extra+comment
  a.need(0<namelen<=128 and extra<=4096 and comment<=1024 and endpos<=len(raw) and not flags&1 and method in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED),'ZIP member metadata/decoder');name=raw[pos+46:pos+46+namelen].decode('ascii');a.need(name in NAMES and name not in seen and ((name in DIRS and stat.S_IFMT(attr>>16) in (0,stat.S_IFDIR)) or (name in FILES and stat.S_IFMT(attr>>16) in (0,stat.S_IFREG))),'ZIP closed regular member');seen.add(name)
  extension=raw[pos+46+namelen:pos+46+namelen+extra];cursor=0;z64=None
  while cursor<len(extension):
   a.need(cursor+4<=len(extension),'ZIP extra header');tag,length=struct.unpack_from('<HH',extension,cursor);cursor+=4;a.need(cursor+length<=len(extension),'ZIP extra data')
   if tag==1:a.need(z64 is None,'duplicate ZIP64 data');z64=extension[cursor:cursor+length]
   cursor+=length
  values=[nbytes,compressed,local,disk];cursor=0
  for index in range(4):
   sentinel=65535 if index==3 else 0xffffffff
   if values[index]==sentinel:
    width=4 if index==3 else 8;a.need(z64 is not None and cursor+width<=len(z64),'ZIP64 member data');values[index]=int.from_bytes(z64[cursor:cursor+width],'little');cursor+=width
  nbytes,compressed,local,disk=values;a.need(name!='candidate/layout-descriptor.data' or nbytes==128,'exact raw descriptor extent');a.need(disk==0 and 0<=nbytes<=FILE_LIMITS[name] and (nbytes>0 or name in DIRS or name.startswith('logs/')) and 0<=compressed<=MAX_ZIP and 0<=local<offset,'ZIP member bounds');total+=nbytes;a.need(total<=MAX_ZIP,'ZIP extracted byte budget');pos=endpos
 a.need(pos==len(raw) and 'reports/receipt.json' in seen,'ZIP directory closure');return seen
def extract_carrier(path,destination,deadline=None):
 stop=min(time.monotonic()+180,deadline if deadline is not None else time.monotonic()+180);a.need(time.monotonic()<stop,'ZIP deadline');path=Path(os.path.abspath(path));destination=Path(os.path.abspath(destination));a.need(path.resolve()==path and destination.resolve()==destination and not destination.exists(),'canonical fresh ZIP paths')
 try:
  with _absolute_deadline(stop):
   fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
   with os.fdopen(fd,'rb') as f:
    before=os.fstat(f.fileno());a.need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=MAX_ZIP,'regular bounded ZIP');expected=_preflight(f,before.st_size);f.seek(0)
    with zipfile.ZipFile(f) as z:
     rows=z.infolist();a.need(1<=len(rows)<=len(NAMES) and {r.filename for r in rows}==expected,'ZIP members');destination.mkdir(parents=True,mode=0o700,exist_ok=False);files={}
     for row in rows:
      if row.filename in DIRS:
       a.need(row.is_dir() and row.file_size==0,'closed empty directory');(destination/row.filename).mkdir(parents=True,exist_ok=True);continue
      a.need(not row.flag_bits&1 and row.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED) and not row.is_dir() and stat.S_IFMT(row.external_attr>>16) in (0,stat.S_IFREG),'ZIP regular data');count=0;h=hashlib.sha256()
      (destination/row.filename).parent.mkdir(parents=True,exist_ok=True)
      with z.open(row) as source,(destination/row.filename).open('xb') as out:
       for block in iter(lambda:source.read(1024**2),b''):
        a.need(time.monotonic()<stop,'ZIP deadline');count+=len(block);a.need(count<=row.file_size,'ZIP file size');out.write(block);h.update(block)
      a.need(count==row.file_size,'ZIP full member');files[row.filename]=dict(nbytes=count,sha256=h.hexdigest())
    a.need(sum(v['nbytes'] for k,v in files.items() if k.startswith('logs/'))<=32*1024**2,'combined log bound')
    a.need(signature(before)==signature(os.fstat(f.fileno()))==signature(path.lstat()) and time.monotonic()<stop,'ZIP changed/deadline')
   return dict(status='CLOSED_BOUNDED_CG_EIGEN_BUILD_CARRIER_EXTRACTED',files=files,root_filesystem_extracted=False,native_admitted=False)
 except Exception as e:raise ValueError('CG_BUILD_CARRIER_REJECTED') from e
