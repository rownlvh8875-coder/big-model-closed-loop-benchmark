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
