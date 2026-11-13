"""Candidate installed manifest and explicit caller-root prefix verification.

No automatic scan, native package import, Docker or network operation. A candidate
is not independent image acceptance. The immutable core collector stays unchanged.
"""
from contextlib import ExitStack
import hashlib
import math
import os
from pathlib import Path
import stat
import sys
from time import perf_counter
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from scripts import engine_clock_runtime_inventory as core


class _Candidate(core._Collector):
    def __init__(self,deadline,result):
        super().__init__(deadline,result)
        self.declared_bytes=0
        self.seen=set()
    def regular(self,parent,name,path,before):
        if self.read_payload:
            if not 0<=before.st_size<=core.MAX_FILE_BYTES:raise ValueError('IMAGE_INVENTORY_REJECTED')
            if self.declared_bytes+before.st_size>core.MAX_INSTALLED_BYTES:raise ValueError('IMAGE_INVENTORY_REJECTED')
            self.declared_bytes+=before.st_size
            self.expected[path]={'kind':'file','nbytes':before.st_size,'mode':stat.S_IMODE(before.st_mode)}
        super().regular(parent,name,path,before)
    def matched(self,value):
        if self.read_payload:
            if value['path'] in self.seen:raise ValueError('IMAGE_INVENTORY_REJECTED')
            self.seen.add(value['path'])
            self.expected[value['path']]=dict(value)
            self.observed.append(value)
            self.result['candidate_entries']+=1
        elif value!=self.expected.get(value['path']):raise ValueError('IMAGE_INVENTORY_REJECTED')


def create_inventory(root:Path,*,deadline:float)->dict:
    """Hash only a caller-supplied tree; return candidate data, never admission."""
    started=perf_counter();result={'schema':'engine-clock-image-inventory-candidate-v1','status':'FAILED_OR_INCOMPLETE','complete':False,'inventory':None,'canonical_manifest_sha256':None,'bytes_read':0,'visited_nodes':0,'matched_entries':0,'matched_prefix':[],'candidate_entries':0,'failure_stage':'arguments','failure_path':None,'error_code':None,'installed_runtime_verified':False,'native_admission':False}
    try:
        if type(deadline) not in (int,float) or not math.isfinite(deadline):raise ValueError('IMAGE_INVENTORY_REJECTED')
        stop=min(deadline,started+core.MAX_SECONDS);collector=_Candidate(stop,result);collector.check()
        with core._absolute_deadline(stop):
            flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC
            with core._opened(root,flags) as rootfd:
                stub={'roots':list(core.BASE_ROOTS)}
                first=collector.scan(rootfd,stub,True)
                roots=sorted(set(core.BASE_ROOTS)|{core._resolve(p,first,collector.check,require_existing=True) for p in core.BASE_ROOTS})
                candidate={'schema':'installed-files-v1','roots':roots,'runtime_exclusions':list(core.RUNTIME_EXCLUSIONS),'entries':sorted(collector.observed,key=lambda v:v['path'])}
                candidate,raw=core._validate(candidate,collector.check)
                second=collector.scan(rootfd,candidate,False)
                if first!=second:raise ValueError('IMAGE_INVENTORY_REJECTED')
            collector.check()
            result.update(status='CANDIDATE_INSTALLED_MANIFEST_COLLECTED',complete=True,inventory=candidate,canonical_manifest_sha256=hashlib.sha256(raw).hexdigest(),failure_stage=None,failure_path=None)
    except Exception:result.update(status='FAILED_OR_INCOMPLETE',complete=False,inventory=None,canonical_manifest_sha256=None,error_code='IMAGE_INVENTORY_REJECTED',failure_path=None)
    finally:result['elapsed_s']=perf_counter()-started
    return result


def verify_inventory(root:Path,expected:dict,*,deadline:float)->dict:
    """Verify saved expected bytes via the immutable existing public collector."""
    return core.collect_inventory(root,expected,deadline=deadline)


def _need(value):
    if not value:raise ValueError('IMAGE_PREFIX_REJECTED')


def verify_prefix(root:Path,observation:dict,*,expected_members:dict)->dict:
    """Check a supplied caller root and source-bound expected Python member hashes.

    Runtime observations and container origin require independent controller proof.
    Absolute in-image links are checked lexically, never followed on the host.
    """
    try:
        required={'bin/python3.11','lib/libpython3.11.so.1.0','lib/python3.11/os.py'}
        _need(type(expected_members) is dict and set(expected_members)==required)
        literals={'python_version':'3.11.18','executable':'/opt/venv/bin/python','executable_realpath':'/opt/venv/bin/python','stdlib_realpath':'/opt/python/lib/python3.11/os.py','loaded_libpython_realpaths':['/opt/python/lib/libpython3.11.so.1.0'],'isolated':True,'no_site':True,'dont_write_bytecode':True,'imported_forbidden':[]}
        _need(type(observation) is dict and all(observation.get(k)==v and (type(observation[k]) is bool if type(v) is bool else True) for k,v in literals.items()))
        flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC
        with ExitStack() as stack:
            fd=os.open(root,flags);stack.callback(os.close,fd);anchor=os.fstat(fd);owner=anchor.st_uid;device=anchor.st_dev
            def directory(path):
                current=fd
                for component in path.split('/'):
                    child=os.open(component,flags,dir_fd=current);stack.callback(os.close,child);info=os.fstat(child)
                    _need(info.st_dev==device and info.st_uid==owner and not stat.S_IMODE(info.st_mode)&0o022);current=child
                return current
            parent=directory('opt/hostedtoolcache/Python/3.11.18');alias=os.stat('x64',dir_fd=parent,follow_symlinks=False)
            _need(stat.S_ISLNK(alias.st_mode) and alias.st_uid==owner and alias.st_dev==device and os.readlink('x64',dir_fd=parent)=='/opt/python')
            directory('opt/python');directory('opt/venv')
            measured={}
            for path,key in [('opt/venv/bin/python','bin/python3.11'),('opt/python/lib/libpython3.11.so.1.0','lib/libpython3.11.so.1.0'),('opt/python/lib/python3.11/os.py','lib/python3.11/os.py')]:
                d,name=path.rsplit('/',1);parentfd=directory(d);rawfd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,dir_fd=parentfd);stack.callback(os.close,rawfd);before=os.fstat(rawfd);pin=expected_members[key]
                _need(stat.S_ISREG(before.st_mode) and before.st_dev==device and before.st_uid==owner and type(pin['nbytes']) is int and 0<=before.st_size==pin['nbytes']<=core.MAX_FILE_BYTES)
                if path.endswith('/bin/python'):_need(bool(stat.S_IMODE(before.st_mode)&0o111))
                digest=hashlib.sha256();count=0
                while True:
                    block=os.read(rawfd,core.READ_CHUNK)
                    if not block:break
                    count+=len(block);_need(count<=before.st_size);digest.update(block)
                _need(count==before.st_size and digest.hexdigest()==pin['sha256'] and core._signature(os.fstat(rawfd))==core._signature(before) and core._signature(os.stat(name,dir_fd=parentfd,follow_symlinks=False))==core._signature(before));measured['/'+path]={'nbytes':count,'sha256':digest.hexdigest()}
            _need(core._signature(os.stat('x64',dir_fd=parent,follow_symlinks=False))==core._signature(alias))
        return {'status':'PREFIX_LAYOUT_AND_OBSERVATION_MATCH','compiled_prefix':'/opt/hostedtoolcache/Python/3.11.18/x64','canonical_prefix':'/opt/python','alias_target':'/opt/python','root_uid':owner,'measured':measured,'external_container_origin_authenticated':False,'native_admission':False,'installed_runtime_verified':False}
    except Exception:raise ValueError('IMAGE_PREFIX_REJECTED') from None


def _static_data(path,digest):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as f:
        before=os.fstat(f.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0<=before.st_size<=core.MAX_JSON_BYTES:raise ValueError('IMAGE_INVENTORY_REJECTED')
        raw=f.read(core.MAX_JSON_BYTES+1)
        if len(raw)!=before.st_size or hashlib.sha256(raw).hexdigest()!=digest or core._signature(os.fstat(f.fileno()))!=core._signature(before):raise ValueError('IMAGE_INVENTORY_REJECTED')
    import json
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('IMAGE_INVENTORY_REJECTED')
            result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('IMAGE_INVENTORY_REJECTED')))


def collect_host_profile(*,cpuinfo=None,uname=None,logical_cpus=None,affinity_cpus=None):
    """Read actual caller facts explicitly; environment assertions are unused."""
    try:
        uname=os.uname() if uname is None else uname
        if cpuinfo is None:
            with open('/proc/cpuinfo',encoding='utf-8') as source:cpuinfo=source.read(4*1024**2+1)
        if type(cpuinfo) is not str or len(cpuinfo.encode())>4*1024**2:raise ValueError('IMAGE_HOST_REJECTED')
        logical_cpus=os.cpu_count() if logical_cpus is None else logical_cpus
        affinity_cpus=len(os.sched_getaffinity(0)) if affinity_cpus is None else affinity_cpus
        if type(logical_cpus) is not int or type(affinity_cpus) is not int or not 0<affinity_cpus<=logical_cpus:raise ValueError('IMAGE_HOST_REJECTED')
        records=[]
        for block in cpuinfo.split('\n\n'):
            fields={}
            for line in block.splitlines():
                key,sep,value=line.partition(':')
                if sep:fields[key.strip()]=value.strip()
            if 'processor' in fields:
                vendor=fields.get('vendor_id');model=fields.get('model name');flags=sorted(set(fields.get('flags','').split()))
                if not vendor or not model or not flags:raise ValueError('IMAGE_HOST_REJECTED')
                records.append((vendor,model,flags))
        if not records or any(row!=records[0] for row in records) or uname.sysname!='Linux' or uname.machine!='x86_64' or sys.byteorder!='little':raise ValueError('IMAGE_HOST_REJECTED')
        return {'sysname':uname.sysname,'release':uname.release,'version':uname.version,'machine':uname.machine,'byteorder':sys.byteorder,'cpu_vendor':records[0][0],'cpu_model':records[0][1],'cpu_flags':records[0][2],'logical_cpus':logical_cpus,'affinity_cpus':affinity_cpus}
    except Exception:raise ValueError('IMAGE_HOST_REJECTED') from None


def main(argv=None):
    """Explicit actual-image CLI only; plain imports/library callers never scan /."""
    import argparse
    import json
    import re
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group(required=True);modes.add_argument('--candidate',action='store_true');modes.add_argument('--verify',action='store_true')
    parser.add_argument('--nonce',required=True);parser.add_argument('--expected-sha');parser.add_argument('--expected-bytes',type=int);args=parser.parse_args(argv)
    started=perf_counter()
    try:
        if not (sys.executable=='/opt/venv/bin/python' and sys.version_info[:3]==(3,11,18) and sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and os.geteuid()==0 and re.fullmatch('[0-9a-f]{32}',args.nonce)):raise ValueError('IMAGE_INVENTORY_REJECTED')
        forbidden={'numpy','cv2','panda3d','metadrive','onnxruntime'}
        if any(name.split('.',1)[0] in forbidden for name in sys.modules):raise ValueError('IMAGE_INVENTORY_REJECTED')
        for path in sys.path:
            real=os.path.realpath(path)
            if not (real=='/usr/local/libexec/stage7' or real.startswith('/opt/python/lib/')) or 'site-packages' in real.split('/'):raise ValueError('IMAGE_INVENTORY_REJECTED')
        layout=_static_data(Path('/usr/local/share/stage7/python-layout.json'),'701e4d9754700b96b2b9daaf18602bc69dd34d98bf4fbe1d7608a54831e7cc79')
        renderer=_static_data(Path('/usr/local/share/stage7/renderer-wheels.lock.json'),'052b6dd97b126bb2b79ea1b0573b6bf6dc70a800d587dec7316cb3e5fe99d51c')
        loaded=set()
        with open('/proc/self/maps',encoding='utf-8') as maps:
            for line in maps:
                parts=line.split(None,5)
                if len(parts)==6 and 'libpython3.11.so' in parts[5]:
                    value=parts[5].rstrip('\n')
                    if not value.startswith('/') or value.endswith(' (deleted)'):raise ValueError('IMAGE_INVENTORY_REJECTED')
                    loaded.add(os.path.realpath(value))
        observation={'python_version':'.'.join(str(v) for v in sys.version_info[:3]),'executable':sys.executable,'executable_realpath':os.path.realpath(sys.executable),'stdlib_realpath':os.path.realpath(os.__file__),'loaded_libpython_realpaths':sorted(loaded),'isolated':bool(sys.flags.isolated),'no_site':bool(sys.flags.no_site),'dont_write_bytecode':bool(sys.flags.dont_write_bytecode),'imported_forbidden':[]}
        prefix=verify_prefix(Path('/'),observation,expected_members=layout['expected_members'])
        from scripts.engine_clock_image_installer import verify_installed_metadata
        metadata=verify_installed_metadata(Path('/'),renderer['wheels'])
        cfg=Path('/opt/venv/pyvenv.cfg').read_text();settings={}
        for line in cfg.splitlines():
            key,sep,value=line.partition('=')
            if sep:
                key=key.strip()
                if key in settings:raise ValueError('IMAGE_INVENTORY_REJECTED')
                settings[key]=value.strip()
        if settings.get('include-system-site-packages','').lower()!='false' or settings.get('home') not in ('/opt/python/bin','/opt/hostedtoolcache/Python/3.11.18/x64/bin'):raise ValueError('IMAGE_INVENTORY_REJECTED')
        prefix_reads=sum(v['nbytes'] for v in prefix['measured'].values())
        if core.MAX_INSTALLED_BYTES+prefix_reads>core.MAX_READ_BYTES:raise ValueError('IMAGE_INVENTORY_REJECTED')
        stop=started+core.MAX_SECONDS
        if args.candidate:
            result=create_inventory(Path('/'),deadline=stop)
            if not result['complete']:raise ValueError('IMAGE_INVENTORY_REJECTED')
            output=core._canonical(result['inventory']);sys.stdout.buffer.write(output);sys.stdout.buffer.flush()
        else:
            if not (type(args.expected_bytes) is int and 0<args.expected_bytes<=core.MAX_JSON_BYTES and type(args.expected_sha) is str and re.fullmatch('[0-9a-f]{64}',args.expected_sha)):raise ValueError('IMAGE_INVENTORY_REJECTED')
            raw=sys.stdin.buffer.read(args.expected_bytes)
            if len(raw)!=args.expected_bytes or hashlib.sha256(raw).hexdigest()!=args.expected_sha:raise ValueError('IMAGE_INVENTORY_REJECTED')
            expected=json.loads(raw);expected=core.validate_inventory(expected)
            if core._canonical(expected)!=raw:raise ValueError('IMAGE_INVENTORY_REJECTED')
            result=verify_inventory(Path('/'),expected,deadline=stop)
            if not result['complete'] or result['canonical_manifest_sha256']!=args.expected_sha:raise ValueError('IMAGE_INVENTORY_REJECTED')
            sys.stdout.buffer.write(json.dumps({'status':'INSTALLED_FILES_MATCH','canonical_manifest_sha256':args.expected_sha,'bytes_read':result['bytes_read'],'native_admission':False},sort_keys=True).encode()+b'\n');sys.stdout.buffer.flush()
        summary={'status':result['status'],'complete':True,'nonce':args.nonce,'canonical_manifest_sha256':result['canonical_manifest_sha256'],'bytes_read':result['bytes_read'],'prefix_bytes_read':prefix_reads,'total_file_read_bytes':result['bytes_read']+prefix_reads,'visited_nodes':result['visited_nodes'],'prefix':prefix,'host':collect_host_profile(),'version_evidence':{'python':observation['python_version'],'installed_distributions':metadata['installed_distributions'],'cv2_contract_expected':'5.0.0','cv2_imported':False,'renderer_packages_imported':False,'ort_installed':False},'elapsed_seconds':perf_counter()-started,'native_admission':False,'official_model_calls':0}
        sys.stderr.write(json.dumps(summary,sort_keys=True)+'\n');return 0
    except Exception:
        sys.stderr.write(json.dumps({'status':'FAILED_OR_INCOMPLETE','error_code':'IMAGE_INVENTORY_REJECTED','native_admission':False,'official_model_calls':0})+'\n');return 1


if __name__=='__main__':raise SystemExit(main())
