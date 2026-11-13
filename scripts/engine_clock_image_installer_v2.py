"""Owned isolated offline renderer installer; no operation occurs at import.

Library callers supply explicit owned roots and tool callbacks. The real CLI is
reserved for a source-qualified image build and never imports renderer packages.
"""
from email import policy
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import zipfile

CHUNK=1024**2
MAX_FILE=512*1024**2
MAX_ZIP=256*1024**2
MAX_ASSET_BYTES=1024**3
FORBIDDEN={'numpy','cv2','panda3d','metadrive','onnxruntime'}
PIP_CODE="""import runpy,sys
sys.path.insert(0,sys.argv.pop(1));sys.argv[0]='pip'
import pip
assert pip.__version__=='26.2.2' and sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode
code=0
try:runpy.run_module('pip',run_name='__main__')
except SystemExit as exc:code=exc.code
forbidden={'numpy','cv2','panda3d','metadrive','onnxruntime'}
bad=any(n.split('.',1)[0] in forbidden for n in sys.modules)
if bad or type(code) is not int:code=2
print('PIP_OFFLINE_WHEELS_INSTALLED_NO_PAYLOAD_IMPORTS' if code==0 else 'PIP_OFFLINE_INSTALL_FAILED')
raise SystemExit(code)
"""


def _need(value):
    if not value:raise ValueError('IMAGE_INSTALL_REJECTED')


def _name(value):
    _need(type(value) is str and re.fullmatch('[A-Za-z0-9_.+!\\-]{1,240}',value) is not None)
    return value


def _normal(value):
    _need(type(value) is str)
    name=re.sub('[-_.]+','-',value).lower();_need(re.fullmatch('[a-z0-9][a-z0-9-]*',name) is not None);return name


def _signature(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)


def _file_hash(path,limit=MAX_FILE):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as f:
        before=os.fstat(f.fileno());_need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<=before.st_size<=limit);h=hashlib.sha256();count=0
        for block in iter(lambda:f.read(CHUNK),b''):count+=len(block);_need(count<=before.st_size);h.update(block)
        _need(count==before.st_size and _signature(os.fstat(f.fileno()))==_signature(before));return count,h.hexdigest()


def _pairs(rows):
    result={}
    for k,v in rows:_need(k not in result);result[k]=v
    return result


def _plan(context,pins):
    path=context/'renderer-wheels.lock.json';n,digest=_file_hash(path,4*CHUNK);_need(digest==pins['plan_sha256']);raw=path.read_bytes();_need(len(raw)==n and hashlib.sha256(raw).hexdigest()==digest)
    plan=json.loads(raw,object_pairs_hook=_pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('IMAGE_INSTALL_REJECTED')))
    _need(plan['schema']=='engine-clock-model-free-renderer-wheel-lock-v1' and plan['renderer_input_graph_closed'] is True and plan['forbidden_distribution_prefix']=='onnxruntime')
    rows=plan['wheels'];_need(type(rows) is list and 0<len(rows)<=96);seen=set();filenames=set()
    for row in rows:
        name=_normal(row['name']);_need(name==row['name'] and name not in seen and not name.startswith('onnxruntime'));seen.add(name)
        filename=_name(row['filename']);_need(filename.endswith('.whl') and filename not in filenames);filenames.add(filename)
        _need(type(row['nbytes']) is int and row['nbytes']>0 and _file_hash(context/'wheels'/filename,MAX_ZIP)==(row['nbytes'],row['sha256']))
    _need({p.name for p in (context/'wheels').iterdir()}==filenames)
    for key in ('tool','assets'):
        pin=pins[key];_need(_file_hash(context/_name(pin['path']),MAX_ZIP)==(pin['nbytes'],pin['sha256']))
    return plan


def pip_command(root:Path,tool:Path,wheels:list[Path])->list[str]:
    return [str(root/'opt/venv/bin/python'),'-I','-S','-B','-c',PIP_CODE,str(tool),'--isolated','--disable-pip-version-check','--no-input','--no-cache-dir','--keyring-provider','disabled','install','--no-index','--no-deps','--no-compile','--only-binary=:all:','--prefix',str(root/'opt/venv'),*[str(p) for p in wheels]]


def verify_installed_metadata(root:Path,expected:list[dict])->dict:
    try:
        site=root/'opt/venv/lib/python3.11/site-packages';_need(site.is_dir() and not site.is_symlink());wanted={r['name']:r['version'] for r in expected};_need(len(wanted)==len(expected));found={};hashes={}
        for global_site in (site,root/'opt/python/lib/python3.11/site-packages',root/'usr/lib/python3/dist-packages'):
            if global_site.exists():
                _need(global_site.is_dir() and not global_site.is_symlink())
                for p in global_site.iterdir():_need(not re.sub('[-_.]+','-',p.name).lower().lstrip('-').startswith('onnxruntime'))
        for path in sorted(site.glob('*.dist-info')):
            _need(path.is_dir() and not path.is_symlink());meta=path/'METADATA';n,digest=_file_hash(meta,4*CHUNK);raw=meta.read_bytes();_need(len(raw)==n and hashlib.sha256(raw).hexdigest()==digest);message=BytesParser(policy=policy.default).parsebytes(raw);_need(not message.defects and len(message.get_all('Name',[]))==len(message.get_all('Version',[]))==1)
            name=_normal(str(message['Name']));version=str(message['Version']);_need(name not in found and not name.startswith('onnxruntime'));found[name]=version;hashes[name]=digest
        _need(found==wanted)
        return {'installed_distributions':found,'metadata_sha256':hashes,'payload_imports':False,'native_admission':False,'abi_verified':False}
    except Exception:raise ValueError('IMAGE_INSTALL_REJECTED') from None


def _asset_path(name,directory=False):
    _need(type(name) is str and len(name.encode())<=4096 and '\\' not in name and not name.startswith('/') and all(ord(c)>=32 and ord(c)!=127 for c in name))
    path=name[:-1] if directory and name.endswith('/') else name;parts=path.split('/');_need(len(parts)<=64 and all(p not in ('','.','..') and len(p.encode())<=255 for p in parts) and parts[0]=='assets');return path


def replace_assets(package:Path,archive_path:Path,backup:Path,*,expected_sha256:str)->dict:
    try:
        _need(package.is_dir() and not package.is_symlink() and not backup.exists() and not backup.is_symlink())
        fd=os.open(archive_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as raw:
            before=os.fstat(raw.fileno());_need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=MAX_ZIP);h=hashlib.sha256()
            for block in iter(lambda:raw.read(CHUNK),b''):h.update(block)
            _need(h.hexdigest()==expected_sha256);raw.seek(0)
            with zipfile.ZipFile(raw) as archive:
                infos=archive.infolist();_need(0<len(infos)<=20000);seen={};rows={};total=0;version=None
                for info in infos:
                    directory=info.is_dir();name=_asset_path(info.filename,directory);_need(info.orig_filename==info.filename and name not in seen and not info.flag_bits&1 and info.compress_type in (0,8));mode=info.external_attr>>16;_need(stat.S_IFMT(mode) in ((0,stat.S_IFDIR) if directory else (0,stat.S_IFREG)) and not mode&0o7000);seen[name]='directory' if directory else 'file'
                    _need(0<=info.file_size<=MAX_FILE and total+info.file_size<=MAX_ASSET_BYTES)
                    if directory:_need(info.file_size==0);continue
                    digest=hashlib.sha256();count=0;small=bytearray()
                    with archive.open(info) as source:
                        for block in iter(lambda:source.read(CHUNK),b''):
                            count+=len(block);_need(count<=info.file_size);digest.update(block)
                            if name=='assets/version.txt':_need(len(small)+len(block)<=1024);small.extend(block)
                    _need(count==info.file_size);total+=count;rows[name]=(count,digest.hexdigest())
                    if name=='assets/version.txt':version=small.decode().strip()
                for name in seen:
                    parts=name.split('/')
                    for i in range(1,len(parts)):_need(seen.get('/'.join(parts[:i]))!='file')
                _need(version=='0.4.3');old=package/'assets';_need(not old.is_symlink());original_present=old.exists()
                if original_present:_need(old.is_dir());os.rename(old,backup)
                old.mkdir(mode=0o755)
                for info in infos:
                    name=_asset_path(info.filename,info.is_dir());target=package/name
                    if info.is_dir():target.mkdir(parents=True,exist_ok=True,mode=0o755);continue
                    target.parent.mkdir(parents=True,exist_ok=True,mode=0o755);outfd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644);digest=hashlib.sha256();count=0
                    with os.fdopen(outfd,'wb') as output,archive.open(info) as source:
                        for block in iter(lambda:source.read(CHUNK),b''):count+=len(block);_need(count<=rows[name][0]);output.write(block);digest.update(block)
                    _need((count,digest.hexdigest())==rows[name])
                _need(_signature(os.fstat(raw.fileno()))==_signature(before))
        return {'version':version,'members':len(infos),'decoded_bytes':total,'sha256':expected_sha256,'original_assets_present':original_present,'original_assets_preserved':original_present,'payload_execution':False,'native_admission':False}
    except Exception:raise ValueError('IMAGE_INSTALL_REJECTED') from None


def normalize_pager(root:Path,backup:Path)->dict:
    """Record the known Ubuntu usrmerge pager alias using approved physical paths."""
    from contextlib import ExitStack
    try:
        _need(not backup.exists() and not backup.is_symlink() and backup.parent.is_dir() and not backup.parent.is_symlink())
        with ExitStack() as stack:
            flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC
            rootfd=os.open(root,flags);stack.callback(os.close,rootfd);anchor=os.fstat(rootfd)
            def directory(parts):
                fd=rootfd
                for part in parts:
                    fd=os.open(part,flags,dir_fd=fd);stack.callback(os.close,fd);s=os.fstat(fd)
                    _need(s.st_dev==anchor.st_dev and s.st_uid==anchor.st_uid and not s.st_mode&0o022)
                return fd
            usrbin=directory(('usr','bin'));alternatives=directory(('etc','alternatives'))
            link=os.stat('bin',dir_fd=rootfd,follow_symlinks=False)
            _need(stat.S_ISLNK(link.st_mode) and link.st_uid==anchor.st_uid and link.st_dev==anchor.st_dev and os.readlink('bin',dir_fd=rootfd)=='usr/bin')
            more=os.open('more',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=usrbin);stack.callback(os.close,more);physical=os.fstat(more)
            alias=os.open('bin/more',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=rootfd);stack.callback(os.close,alias);logical=os.fstat(alias)
            _need(stat.S_ISREG(physical.st_mode) and physical.st_uid==anchor.st_uid and physical.st_dev==anchor.st_dev and (physical.st_dev,physical.st_ino)==(logical.st_dev,logical.st_ino))
            before=os.stat('pager',dir_fd=alternatives,follow_symlinks=False);_need(stat.S_ISLNK(before.st_mode) and before.st_uid==anchor.st_uid and before.st_dev==anchor.st_dev)
            target=os.readlink('pager',dir_fd=alternatives);_need(target in ('/bin/more','/usr/bin/more'))
            _need(_signature(link)==_signature(os.stat('bin',dir_fd=rootfd,follow_symlinks=False)) and _signature(before)==_signature(os.stat('pager',dir_fd=alternatives,follow_symlinks=False)))
            changed=target=='/bin/more'
            if changed:
                _need(backup.parent.stat().st_dev==anchor.st_dev)
                os.rename('pager',backup,src_dir_fd=alternatives)
                os.symlink('/usr/bin/more','pager',dir_fd=alternatives)
                _need(os.readlink(backup)==target)
            _need(os.readlink('pager',dir_fd=alternatives)=='/usr/bin/more')
        return {'status':'CANONICAL_BASE_PAGER_ALIAS_RECORDED','previous_target':target,'canonical_target':'/usr/bin/more','bin_alias':'usr/bin','changed':changed,'original_link_preserved_outside_final_image':changed,'same_regular_target_observed':True,'payload_bytes_modified':False,'native_admission':False}
    except Exception:raise ValueError('IMAGE_INSTALL_REJECTED') from None


def install_renderer(root:Path,context:Path,pins:dict,*,create_venv,run_pip)->dict:
    try:
        plan=_plan(context,pins);print('INSTALLER_PLAN_VERIFIED');pager=normalize_pager(root,context/'original-pager-link');print('INSTALLER_PAGER_ALIAS_RECORDED');prefix=root/'opt/venv';_need(not prefix.exists() and not prefix.is_symlink());_need(callable(create_venv) and callable(run_pip));create_venv(prefix);print('INSTALLER_VENV_CREATED')
        command=pip_command(root,context/pins['tool']['path'],[context/'wheels'/r['filename'] for r in plan['wheels']]);result=run_pip(command);_need(type(result) is dict and type(result['returncode']) is int and result['returncode']==0 and result['payload_imports'] is False)
        print('INSTALLER_PIP_FINISHED');metadata=verify_installed_metadata(root,plan['wheels']);print('INSTALLER_METADATA_VERIFIED');assets=replace_assets(prefix/'lib/python3.11/site-packages/metadrive',context/pins['assets']['path'],context/'original-metadrive-assets',expected_sha256=pins['assets']['sha256'])
        print('INSTALLER_ASSETS_WRITTEN')
        return {'status':'OFFLINE_RENDERER_INSTALL_RECORDED','pip_invocations':1,'venv_creations':1,'metadata':metadata,'assets':assets,'pager_alias':pager,'native_admission':False,'installed_abi_verified':False,'official_model_calls':0}
    except Exception:raise ValueError('IMAGE_INSTALL_REJECTED') from None


def main(argv=None):
    """Only the explicit isolated target-interpreter build-stage invocation runs."""
    import argparse
    import subprocess
    import sys
    import venv
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-owned-image-stage',action='store_true',required=True)
    parser.parse_args(argv)
    try:
        _need(sys.executable=='/opt/python/bin/python3.11' and sys.version_info[:3]==(3,11,18) and sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and os.geteuid()==0)
        context=Path('/sealed')
        pins={'plan_sha256':'052b6dd97b126bb2b79ea1b0573b6bf6dc70a800d587dec7316cb3e5fe99d51c','tool':{'path':'pip-tool.whl','nbytes':1819850,'sha256':'fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70'},'assets':{'path':'assets.zip','nbytes':134074203,'sha256':'4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9'}}
        def create(prefix):venv.create(prefix,with_pip=False,symlinks=False)
        sys.path.insert(0,str(context))
        from scripts.engine_clock_image_process import capture
        def run(command):
            result=capture(command,context/'pip-capture',timeout=300,stdout_limit=CHUNK//2,stderr_limit=CHUNK//2,file_size_limit=MAX_FILE)
            stdout=(context/'pip-capture/stdout.bin').read_bytes();stderr=(context/'pip-capture/stderr.bin').read_bytes()
            sys.stdout.buffer.write(stdout);sys.stdout.buffer.flush();sys.stderr.buffer.write(stderr);sys.stderr.buffer.flush()
            good=result['status']=='EXITED' and result['returncode']==0 and result['streams_complete'] is True and stdout.splitlines()[-1:]==[b'PIP_OFFLINE_WHEELS_INSTALLED_NO_PAYLOAD_IMPORTS']
            return {'returncode':0 if good else 1,'payload_imports':False if good else None}
        receipt=install_renderer(Path('/'),context,pins,create_venv=create,run_pip=run)
        fd=os.open(context/'install-receipt.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as f:json.dump(receipt,f,sort_keys=True,indent=2);f.write('\n')
        print('OFFLINE_RENDERER_INSTALL_RECORDED');return 0
    except Exception:print('IMAGE_INSTALL_REJECTED');return 1


if __name__=='__main__':raise SystemExit(main())
