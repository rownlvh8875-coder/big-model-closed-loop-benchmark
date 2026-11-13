"""Typed candidate namespace facts and a single real additional-userns assertion.

Importing this module performs no namespace, file or package operations.
"""
import ctypes
import errno
import os
from pathlib import Path
import sys

RO_PATHS=('/', '/proc', '/dev', '/dev/pts')
CAPS=('CapEff','CapPrm','CapInh','CapAmb','CapBnd')
PHASES=('python','identity','readonly','build','limit','capabilities','network','collection','assertion')


def _need(ok,code='INVALID_NAMESPACE_FACTS'):
    if not ok:raise ValueError(code)


def empty():
    return {'schema':'builder-namespace-proof-v1',
            'python':{'version':None,'isolated':None,'no_site':None,'dont_write_bytecode':None},
            'uid':None,'gid':None,'readonly':{p:None for p in RO_PATHS},
            'build':{'bytes':None,'readonly':None,'tmpfs':None},'visible_userns_limit':None,
            'capabilities':{p:None for p in CAPS},
            'network':{'interfaces_present':None,'interface_count':None,'only_loopback':None,'route_lines':None},
            'errors':[],'additional_userns':{'status':'NOT_RUN','returncode':None,'errno':None}}


def _integer(value,maximum=2**64-1):return value is None or type(value) is int and 0<=value<=maximum

def _boolean(value):return value is None or type(value) is bool


def validate_shape(f):
    """Accept safe partial failures, never arbitrary strings or unknown fields."""
    try:
        _need(type(f) is dict and set(f)==set(empty()) and f['schema']=='builder-namespace-proof-v1')
        p=f['python'];_need(type(p) is dict and set(p)=={'version','isolated','no_site','dont_write_bytecode'})
        _need(p['version'] is None or type(p['version']) is list and len(p['version'])==3 and all(type(v) is int and 0<=v<=1000 for v in p['version']))
        _need(all(_boolean(p[k]) for k in ('isolated','no_site','dont_write_bytecode')))
        _need(_integer(f['uid'],2**32-1) and _integer(f['gid'],2**32-1) and _integer(f['visible_userns_limit'],2**63-1))
        _need(type(f['readonly']) is dict and set(f['readonly'])==set(RO_PATHS) and all(_boolean(v) for v in f['readonly'].values()))
        q=f['build'];_need(type(q) is dict and set(q)=={'bytes','readonly','tmpfs'} and _integer(q['bytes']) and _boolean(q['readonly']) and _boolean(q['tmpfs']))
        c=f['capabilities'];_need(type(c) is dict and set(c)==set(CAPS) and all(_integer(v) for v in c.values()))
        net=f['network'];_need(type(net) is dict and set(net)=={'interfaces_present','interface_count','only_loopback','route_lines'})
        _need(_boolean(net['interfaces_present']) and _boolean(net['only_loopback']) and _integer(net['interface_count'],100000) and _integer(net['route_lines'],100000))
        _need(type(f['errors']) is list and len(f['errors'])<=len(PHASES) and len(set(f['errors']))==len(f['errors']) and all(type(v) is str and v in PHASES for v in f['errors']))
        a=f['additional_userns'];_need(type(a) is dict and set(a)=={'status','returncode','errno'} and a['status'] in ('NOT_RUN','RETURNED','ERROR'))
        _need(a['returncode'] is None or type(a['returncode']) is int and -2**31<=a['returncode']<2**31)
        _need(_integer(a['errno'],4095))
        _need((a['status']=='RETURNED')==(a['returncode'] is not None and a['errno'] is not None))
        if a['status']!='RETURNED':_need(a['returncode'] is None and a['errno'] is None)
        return f
    except (KeyError,TypeError,ValueError,OverflowError):raise ValueError('INVALID_NAMESPACE_FACTS') from None


def validate_initial(f):
    validate_shape(f)
    _need(not f['errors'],'UNSUPPORTED_NAMESPACE')
    _need(f['python']=={'version':[3,11,18],'isolated':True,'no_site':True,'dont_write_bytecode':True},'UNSUPPORTED_PYTHON')
    _need(f['uid']==f['gid']==0 and all(v is True for v in f['readonly'].values()) and f['visible_userns_limit'] is not None,'UNSUPPORTED_NAMESPACE')
    q=f['build'];_need(q['bytes'] is not None and 0<q['bytes']<=268435456 and q['readonly'] is False and q['tmpfs'] is True,'UNSUPPORTED_QUOTA')
    _need(all(type(v) is int and v==0 for v in f['capabilities'].values()),'UNSUPPORTED_CAPABILITIES')
    net=f['network']
    _need(net['route_lines']==1 and (net['interfaces_present'] is False and net['interface_count'] is None and net['only_loopback'] is None or
          net['interfaces_present'] is True and type(net['interface_count']) is int and net['interface_count']<=1 and net['only_loopback'] is True),'UNSUPPORTED_NETWORK')
    return f


def validate(f):
    validate_initial(f)
    a=f['additional_userns']
    _need(a['status']=='RETURNED' and a['returncode']==-1 and a['errno'] in (errno.EPERM,errno.ENOSPC),'UNSUPPORTED_NAMESPACE')
    return f


def _read(path,limit=1048576):
    with open(path,'rb') as stream:raw=stream.read(limit+1)
    _need(len(raw)<=limit)
    return raw.decode('ascii')


class LiveBackend:
    def collect_initial(self,f):
        def phase(name,fn):
            try:fn()
            except Exception:f['errors'].append(name)
        def python():f['python'].update(version=list(sys.version_info[:3]),isolated=bool(sys.flags.isolated),no_site=bool(sys.flags.no_site),dont_write_bytecode=bool(sys.flags.dont_write_bytecode))
        def identity():f.update(uid=os.getuid(),gid=os.getgid())
        def readonly():
            for p in RO_PATHS:f['readonly'][p]=bool(os.statvfs(p).f_flag & os.ST_RDONLY)
        def build():
            fs=os.statvfs('/build');f['build'].update(bytes=fs.f_blocks*fs.f_frsize,readonly=bool(fs.f_flag & os.ST_RDONLY))
            lines=_read('/proc/self/mountinfo').splitlines()
            f['build']['tmpfs']=any(len(line.split())>=10 and line.split()[4]=='/build' and ' - tmpfs ' in line for line in lines)
        def limit():f['visible_userns_limit']=int(_read('/proc/sys/user/max_user_namespaces',128).strip())
        def caps():
            rows={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in _read('/proc/self/status',65536).splitlines() if ':' in line}
            for p in CAPS:f['capabilities'][p]=int(rows[p],16)
        def network():
            present=Path('/sys/class/net').exists();f['network']['interfaces_present']=present
            if present:
                names=os.listdir('/sys/class/net');f['network'].update(interface_count=len(names),only_loopback=set(names)<={'lo'})
            f['network']['route_lines']=len(_read('/proc/net/route',65536).splitlines())
        for name,fn in (('python',python),('identity',identity),('readonly',readonly),('build',build),('limit',limit),('capabilities',caps),('network',network)):phase(name,fn)

    def unshare(self):
        lib=ctypes.CDLL(None,use_errno=True)
        lib.unshare.argtypes=[ctypes.c_int];lib.unshare.restype=ctypes.c_int
        ctypes.set_errno(0)
        rc=lib.unshare(0x10000000)
        return rc,ctypes.get_errno()


def collect(facts,backend=None):
    """Populate caller-owned facts before validation; never retry the assertion."""
    facts.clear();facts.update(empty());backend=backend or LiveBackend()
    try:backend.collect_initial(facts)
    except Exception:facts['errors'].append('collection')
    try:validate_initial(facts)
    except ValueError:return facts
    try:
        rc,err=backend.unshare()
        _need(type(rc) is int and -2**31<=rc<2**31 and type(err) is int and 0<=err<=4095)
        facts['additional_userns'].update(status='RETURNED',returncode=rc,errno=err)
    except Exception:
        facts['additional_userns'].update(status='ERROR',returncode=None,errno=None);facts['errors'].append('assertion')
    return facts
