"""Prepare one final empty source leaf through owned same-device nofollow FDs."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

STAGES={'LOCATION','BUILD','TMP','PARENT','CREATE','LEAF','BINDING','EMPTY','READY'}


def _need(ok):
    if not ok:raise ValueError('SOURCE_DIRECTORY_REJECTED')


def empty():
    return {'schema':'source-directory-v1','status':'REJECTED','stage':'LOCATION','location_sha256':None,'created':False,
            'build_device':None,'tmp_device':None,'parent_device':None,'target_device':None,'target_inode':None,
            'target_uid':None,'target_mode':None,'parent_named_inode_matches':None,'target_named_inode_matches':None,'empty':None,'errno':None}


def validate(f):
    try:
        if type(f) is not dict or set(f)!=set(empty()) or f['schema']!='source-directory-v1':raise ValueError()
        if f['status'] not in ('REJECTED','EMPTY_SOURCE_DIRECTORY_READY') or f['stage'] not in STAGES or type(f['created']) is not bool:raise ValueError()
        if f['location_sha256'] is not None and (type(f['location_sha256']) is not str or re.fullmatch('[0-9a-f]{64}',f['location_sha256']) is None):raise ValueError()
        for k,maximum in [('build_device',2**64-1),('tmp_device',2**64-1),('parent_device',2**64-1),('target_device',2**64-1),('target_inode',2**64-1),('target_uid',2**32-1),('target_mode',0o7777),('errno',4095)]:
            if f[k] is not None and (type(f[k]) is not int or not 0<=f[k]<=maximum):raise ValueError()
        for k in ('parent_named_inode_matches','target_named_inode_matches','empty'):
            if f[k] is not None and type(f[k]) is not bool:raise ValueError()
        if f['status']=='EMPTY_SOURCE_DIRECTORY_READY':
            if not (f['stage']=='READY' and f['location_sha256'] is not None and all(f[k] is True for k in ('parent_named_inode_matches','target_named_inode_matches','empty')) and
                    type(f['build_device']) is int and f['build_device']>0 and all(f[k]==f['build_device'] for k in ('tmp_device','parent_device','target_device')) and
                    type(f['target_inode']) is int and f['target_inode']>0 and type(f['target_uid']) is int and type(f['target_mode']) is int and not f['target_mode']&0o022 and f['errno'] is None):raise ValueError()
        return f
    except (TypeError,ValueError,KeyError):raise ValueError('INVALID_SOURCE_DIRECTORY_FACTS') from None


def prepare_directory(location,*,tmp_root=Path('/build/tmp'),build_root=Path('/build'),facts=None):
    f={} if facts is None else facts;f.clear();f.update(empty());fds=[]
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
    def opened(name,**kwargs):
        fd=os.open(name,flags,**kwargs);fds.append(fd);return fd
    def owned(info):_need(stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid() and not stat.S_IMODE(info.st_mode)&0o022)
    try:
        _need(type(location) is str and len(location)<=4096 and Path(location).is_absolute() and str(Path(location))==location)
        _need(tmp_root.is_absolute() and build_root.is_absolute() and tmp_root==build_root/'tmp')
        f['location_sha256']=hashlib.sha256(location.encode()).hexdigest()
        relative=Path(location).relative_to(tmp_root).as_posix()
        _need(re.fullmatch(r'pip-wheel-[a-z0-9_-]{1,64}/progressbar_[0-9a-f]{32}',relative) is not None)
        parent,leaf=relative.split('/')
        f['stage']='BUILD';bfd=opened(build_root);build=os.fstat(bfd);owned(build);f['build_device']=build.st_dev
        f['stage']='TMP';tfd=opened('tmp',dir_fd=bfd);tmp=os.fstat(tfd);owned(tmp);f['tmp_device']=tmp.st_dev;_need(tmp.st_dev==build.st_dev)
        f['stage']='PARENT';pfd=opened(parent,dir_fd=tfd);pinfo=os.fstat(pfd);owned(pinfo);f['parent_device']=pinfo.st_dev;_need(pinfo.st_dev==build.st_dev)
        named=os.stat(parent,dir_fd=tfd,follow_symlinks=False);f['parent_named_inode_matches']=(named.st_dev,named.st_ino)==(pinfo.st_dev,pinfo.st_ino);_need(f['parent_named_inode_matches'])
        f['stage']='CREATE'
        try:os.mkdir(leaf,mode=0o700,dir_fd=pfd);f['created']=True
        except FileExistsError:pass
        f['stage']='LEAF';lfd=opened(leaf,dir_fd=pfd);info=os.fstat(lfd)
        f.update(target_device=info.st_dev,target_inode=info.st_ino,target_uid=info.st_uid,target_mode=stat.S_IMODE(info.st_mode));owned(info);_need(info.st_dev==build.st_dev)
        f['stage']='BINDING'
        named=os.stat(parent,dir_fd=tfd,follow_symlinks=False);f['parent_named_inode_matches']=(named.st_dev,named.st_ino)==(pinfo.st_dev,pinfo.st_ino)
        named=os.stat(leaf,dir_fd=pfd,follow_symlinks=False);f['target_named_inode_matches']=(named.st_dev,named.st_ino)==(info.st_dev,info.st_ino)
        _need(f['parent_named_inode_matches'] and f['target_named_inode_matches'])
        f['stage']='EMPTY'
        with os.scandir(lfd) as entries:f['empty']=next(entries,None) is None
        _need(f['empty']);f.update(status='EMPTY_SOURCE_DIRECTORY_READY',stage='READY');validate(f);return f
    except (OSError,ValueError,TypeError) as exc:
        f['status']='REJECTED'
        if isinstance(exc,OSError) and type(exc.errno) is int and 0<=exc.errno<=4095:f['errno']=exc.errno
        raise ValueError('SOURCE_DIRECTORY_REJECTED') from None
    finally:
        for fd in reversed(fds):os.close(fd)


def persist(facts,*,path=Path('/build/source-directory.json')):
    validate(facts);raw=(json.dumps(facts,sort_keys=True,separators=(',',':'))+'\n').encode()
    _need(len(raw)<=4096)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(raw)


class PrepareProxy:
    def __init__(self,real,*,tmp_root=Path('/build/tmp'),build_root=Path('/build'),emit=persist):
        self.real,self.tmp_root,self.build_root,self.emit=real,tmp_root,build_root,emit;self.original=real.unpack_url;self.calls=0
    @property
    def unpack_url(self):return self.real.unpack_url
    @unpack_url.setter
    def unpack_url(self,hook):
        if hook is self.original:self.real.unpack_url=hook;return
        def prepared(*args,**kwargs):
            if self.calls:raise ValueError('SOURCE_DIRECTORY_REUSED')
            self.calls+=1;facts={};location=args[1] if len(args)>1 else kwargs.get('location')
            try:prepare_directory(location,tmp_root=self.tmp_root,build_root=self.build_root,facts=facts)
            finally:self.emit(facts)
            return hook(*args,**kwargs)
        self.real.unpack_url=prepared
