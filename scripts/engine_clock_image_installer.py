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
                _need(version=='0.4.3');old=package/'assets';_need(old.is_dir() and not old.is_symlink());os.rename(old,backup);old.mkdir(mode=0o755)
                for info in infos:
                    name=_asset_path(info.filename,info.is_dir());target=package/name
                    if info.is_dir():target.mkdir(parents=True,exist_ok=True,mode=0o755);continue
                    target.parent.mkdir(parents=True,exist_ok=True,mode=0o755);outfd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644);digest=hashlib.sha256();count=0
                    with os.fdopen(outfd,'wb') as output,archive.open(info) as source:
                        for block in iter(lambda:source.read(CHUNK),b''):count+=len(block);_need(count<=rows[name][0]);output.write(block);digest.update(block)
                    _need((count,digest.hexdigest())==rows[name])
                _need(_signature(os.fstat(raw.fileno()))==_signature(before))
        return {'version':version,'members':len(infos),'decoded_bytes':total,'sha256':expected_sha256,'original_assets_preserved':True,'payload_execution':False,'native_admission':False}
    except Exception:raise ValueError('IMAGE_INSTALL_REJECTED') from None


def install_renderer(root:Path,context:Path,pins:dict,*,create_venv,run_pip)->dict:
    try:
        plan=_plan(context,pins);prefix=root/'opt/venv';_need(not prefix.exists() and not prefix.is_symlink());_need(callable(create_venv) and callable(run_pip));create_venv(prefix)
        command=pip_command(root,context/pins['tool']['path'],[context/'wheels'/r['filename'] for r in plan['wheels']]);result=run_pip(command);_need(type(result) is dict and type(result['returncode']) is int and result['returncode']==0 and result['payload_imports'] is False)
        metadata=verify_installed_metadata(root,plan['wheels']);assets=replace_assets(prefix/'lib/python3.11/site-packages/metadrive',context/pins['assets']['path'],context/'original-metadrive-assets',expected_sha256=pins['assets']['sha256'])
        return {'status':'OFFLINE_RENDERER_INSTALL_RECORDED','pip_invocations':1,'venv_creations':1,'metadata':metadata,'assets':assets,'native_admission':False,'installed_abi_verified':False,'official_model_calls':0}
    except Exception:raise ValueError('IMAGE_INSTALL_REJECTED') from None
