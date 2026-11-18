"""Pinned original ORT wheels and bounded mounted-byte descriptors (stdlib only)."""
from pathlib import Path
import hashlib
import json
import stat
from urllib.parse import urlsplit
from .full_s_recorded_worker import need,_receipt_bytes,_read_receipt
from . import recorded_official_execution as c

VERSIONS={'onnxruntime':'1.20.1','flatbuffers':'24.3.25','coloredlogs':'15.0.1','humanfriendly':'10.0',
    'packaging':'24.2','protobuf':'5.29.5','sympy':'1.13.3','mpmath':'1.3.0'}
DECLARATION_SHA='c6791df27ca89e17f813fc45ce2b294dea55f3148a4e6e28c1594501857b5ffe'
MAX_FILES=10000
MAX_MEMBER=128*1024**2
MAX_TOTAL=256*1024**2


def declaration():
    raw=_receipt_bytes(c.ROOT/c.RUNTIME,65536)
    need(hashlib.sha256(raw).hexdigest()==DECLARATION_SHA,'pinned wheel declaration bytes required')
    return json.loads(raw)


def validate_declaration(value):
    need(value==declaration(),'exact reviewed wheel declarations required')
    return value


def installed_versions(root):
    from importlib.metadata import distributions
    found=[]
    for value in distributions(path=[str(root)]):
        need(len(found)<8,'bounded installed distribution count required');found.append(value)
    names=[d.metadata['Name'].lower().replace('_','-') for d in found]
    need(len(names)==len(set(names)),'unique installed distributions required')
    return dict(zip(names,[d.version for d in found]))


def file_map(root):
    root=Path(root).absolute()
    need(root.is_dir() and not root.is_symlink() and all(not p.is_symlink() for p in root.parents),'regular dependency directory required')
    mapping={};total=0
    import os
    stack=[root];entries=0
    while stack:
        directory=stack.pop()
        with os.scandir(directory) as scan:
            children=[]
            for entry in scan:
                entries+=1;need(entries<=MAX_FILES,'bounded dependency namespace before allocation/metadata required')
                children.append(Path(entry.path))
        for path in children:
            info=path.lstat();need(not path.is_symlink(),'dependency symlink forbidden')
            if stat.S_ISDIR(info.st_mode):
                stack.append(path);continue
            need(stat.S_ISREG(info.st_mode) and len(mapping)<MAX_FILES and info.st_size<=MAX_MEMBER,'bounded regular dependency member required')
            name=path.relative_to(root).as_posix()
            need(not name.endswith(('.pth','.pyc')) and '__pycache__' not in path.parts,'dependency startup hooks/compiled cache forbidden')
            total+=info.st_size;need(total<=MAX_TOTAL,'bounded total dependency bytes required')
            if path.parent.name.endswith('.dist-info'):
                need(info.st_size<=1024**2,'bounded distribution metadata before parse required')
            h=hashlib.sha256()
            with path.open('rb') as stream:
                for data in iter(lambda:stream.read(1024**2),b''):h.update(data)
            need(path.stat().st_size==info.st_size,'stable dependency extent required')
            mapping[name]=dict(nbytes=info.st_size,sha256=h.hexdigest())
    need(mapping,'nonempty dependency namespace required')
    return mapping


def describe(root):
    mapping=file_map(root)  # Bound the namespace and metadata BEFORE discovery.
    versions=installed_versions(root);need(versions==VERSIONS,'exact eight original dependency versions required')
    result=dict(protocol='recorded-official-installed-dependencies-v1',declaration_sha256=DECLARATION_SHA,
        versions=versions,files=mapping,removed_inert_hook=dict(path='coloredlogs.pth',nbytes=147,sha256='dda83a855986efa5cd87f0248b0199c0086eb0e8e7fece7d6741959c5ce39536',site_processing_used=False))
    need(len(json.dumps(result).encode())<=4*1024**2,'bounded dependency descriptor required')
    return result


def verify(root,descriptor):
    need(isinstance(descriptor,dict) and descriptor==describe(root),'all mounted dependency versions/bytes/namespace must match descriptor')
    return dict(versions=VERSIONS,declaration_sha256=DECLARATION_SHA,file_count=len(descriptor['files']))


def remove_inert_hook(root):
    path=Path(root)/'coloredlogs.pth'
    raw=_receipt_bytes(path,147)
    need(len(raw)==147 and hashlib.sha256(raw).hexdigest()=='dda83a855986efa5cd87f0248b0199c0086eb0e8e7fece7d6741959c5ce39536',
         'exact original inert coloredlogs hook bytes required before removal')
    path.unlink()
    return dict(path='coloredlogs.pth',nbytes=147,sha256=hashlib.sha256(raw).hexdigest(),site_processing_used=False)


def stage(work):
    """CI-only caller supplies authenticated admission before invoking this."""
    import subprocess
    import sys
    import urllib.request
    need(sys.platform=='linux','ephemeral Linux dependency staging required')
    work=Path(work);wheels=work/'wheels';target=work/'model-deps'
    need(not wheels.exists() and not target.exists(),'fresh wheel/dependency staging required')
    wheels.mkdir();files=[]
    for name,entry in declaration()['packages'].items():
        url=entry['url'];parts=urlsplit(url)
        need(parts.scheme=='https' and parts.netloc=='files.pythonhosted.org' and parts.path.endswith('/'+entry['filename']), 'pinned PyPI wheel origin required')
        path=wheels/entry['filename'];size=0;digest=hashlib.sha256()
        with urllib.request.urlopen(url,timeout=120) as response,path.open('xb') as stream:
            need(response.geturl()==url,'wheel redirect forbidden')
            while True:
                data=response.read(min(1024**2,entry['nbytes']+1-size))
                if not data:break
                size+=len(data);need(size<=entry['nbytes'],'wheel extent exceeded');digest.update(data);stream.write(data)
        need(size==entry['nbytes'] and digest.hexdigest()==entry['sha256'],'exact pinned wheel bytes required')
        files.append(str(path))
    subprocess.run([sys.executable,'-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(target),*files],check=True,timeout=300)
    hook=remove_inert_hook(target)
    descriptor=describe(target);descriptor['removed_inert_hook']=hook
    return target,descriptor
