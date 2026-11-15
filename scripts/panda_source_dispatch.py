"""Stage exact pinned Panda source hooks; never load or execute Panda/GL."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

from scripts.panda_dispatch_coverage import SOURCE_PINS, REVISION, qualify_sources, scan_source

ROOT=Path(__file__).resolve().parents[1]
MEMBERS={
 'glGraphicsStateGuardian_src.cxx':'panda/src/glstuff/glGraphicsStateGuardian_src.cxx',
 'glGraphicsBuffer_src.cxx':'panda/src/glstuff/glGraphicsBuffer_src.cxx',
 'glxGraphicsStateGuardian.cxx':'panda/src/glxdisplay/glxGraphicsStateGuardian.cxx',
 'posixGraphicsStateGuardian.cxx':'panda/src/glxdisplay/posixGraphicsStateGuardian.cxx',
}
DIRECT={'glPixelStorei':'PSD_PIXEL_STORE','glBindBuffer':'PSD_BIND_BUFFER','glBindBufferARB':'PSD_BIND_BUFFER',
 'glBindFramebuffer':'PSD_BIND_FRAMEBUFFER','glBindFramebufferEXT':'PSD_BIND_FRAMEBUFFER',
 'glReadBuffer':'PSD_READ_BUFFER','glDeleteFramebuffers':'PSD_DELETE_FRAMEBUFFER',
 'glDeleteBuffers':'PSD_DELETE_BUFFER','glDeleteBuffersARB':'PSD_DELETE_BUFFER',
 'glXCreateContext':'PSD_CREATE_LEGACY','glXCreateNewContext':'PSD_CREATE_NEW',
 'glXCreateContextAttribsARB':'PSD_CREATE_ATTRIBS','glXMakeCurrent':'PSD_MAKE_CURRENT',
 'glXMakeContextCurrent':'PSD_MAKE_CONTEXT_CURRENT','glXDestroyContext':'PSD_DESTROY_CONTEXT',
 'glGetError':'PSD_GET_ERROR','glReadPixels':'TAIL'}
_LEX=re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\[\s\S]|[^"\\])*"|\'(?:\\[\s\S]|[^\'\\])*\'|\b(?P<call>'+ '|'.join(DIRECT)+r')(?P<space>\s*)\(')

def need(ok,message):
    if not ok:raise ValueError(message)

def rewrite_calls(data):
    inventory=scan_source(data,'source.cxx')
    expected={}
    for row in inventory['direct_calls']:
        if row['name'] in DIRECT:expected[row['name']]=expected.get(row['name'],0)+1
    counts={};text=data.decode()
    def replace(match):
        name=match['call']
        if name is None:return match[0]
        counts[name]=counts.get(name,0)+1
        if name=='glReadPixels':return 'psd_read_pixels'+match['space']+'('
        return 'psd::call<'+DIRECT[name]+'>'+match['space']+'('+name+('' if name=='glGetError' else ', ')
    changed=_LEX.sub(replace,text)
    need(counts==expected,'unrewritable/declaration/ambiguous direct source spelling')
    return changed.encode(),counts

def once(text,old,new):
    need(text.count(old)==1,'exact source anchor missing or ambiguous: '+old[:60])
    return text.replace(old,new,1)

def transform_sources(sources):
    qualify_sources(sources)
    changed={};total={};files={}
    for name,data in sources.items():
        rewritten,counts=rewrite_calls(data)
        for key,count in counts.items():total[key]=total.get(key,0)+count
        text=rewritten.decode()
        include=re.search(r'^#include "[^"\n]+"',text,re.M)
        need(include is not None,'source include anchor')
        text=text[:include.end()]+'\n#include "panda_source_dispatch.h"'+text[include.end():]
        if name=='glGraphicsStateGuardian_src.cxx':
            text=once(text,'get_extension_func(const char *name) {','get_extension_func(const char *name) {\n  psd_lookup psd_request(name);')
            text=once(text,'return compiled_function_table[i].fptr;','return psd_resolved(&psd_request, compiled_function_table[i].fptr, PSD_SOURCE_COMPILED);')
            text=once(text,'return do_get_extension_func(name);','return psd_resolved(&psd_request, do_get_extension_func(name), PSD_SOURCE_RUNTIME);')
            text+='\n// Source-dispatch candidate: one implementation, original-only read tail.\n#define PSD_PANDA_BUILD 1\n#define PSD_ORIGINAL_READ glReadPixels\n#include "panda_source_dispatch.cxx"\n'
        elif name=='glxGraphicsStateGuardian.cxx':
            for expression,origin in (('(void *)glXGetProcAddress((const GLubyte *)name)','PSD_PATH_GLX_CORE'),
                                      ('(void *)glXGetProcAddressARB((const GLubyte *)name)','PSD_PATH_GLX_ARB'),
                                      ('(void *)_glXGetProcAddress((const GLubyte *)name)','PSD_PATH_GLX_PRIVATE')):
                text=once(text,'return '+expression+';','return psd_path('+origin+', '+expression+');')
        elif name=='posixGraphicsStateGuardian.cxx':
            text=once(text,'return dlsym(_libgl_handle, name);','return psd_path(PSD_PATH_POSIX, dlsym(_libgl_handle, name));')
        changed[name]=text.encode()
        files[name]=dict(member=MEMBERS[name],original_sha256=hashlib.sha256(data).hexdigest(),candidate_sha256=hashlib.sha256(changed[name]).hexdigest(),
                         original_nbytes=len(data),candidate_nbytes=len(changed[name]))
    return changed,dict(schema='panda-source-dispatch-transform-v1',upstream_revision=REVISION,files=files,
                        direct_replacements=total,unified_returns=2,glx_path_returns=3,posix_path_returns=1,
                        configured_by_default=False,capture_arming_available=False,runtime_admission_ready=False,native_admitted=False)

def canonical(path):
    path=Path(os.path.abspath(os.fspath(path)))
    need(str(path)==os.path.realpath(path) and re.fullmatch(r'[A-Za-z0-9_./-]+',str(path)),'canonical shell-safe path required')
    return path

def tree_records(root):
    result=[];size=0
    for path in sorted(root.rglob('*')):
        relative=str(path.relative_to(root))
        if path.is_symlink():
            need(path.resolve().is_relative_to(root),'source symlink escapes staging')
            result.append(dict(path=relative,kind='symlink',target=os.readlink(path)))
        elif path.is_file():
            n=path.stat().st_size;size+=n;need(size<=1024**3,'source stage byte budget')
            result.append(dict(path=relative,kind='file',nbytes=n,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        else:need(path.is_dir(),'unsupported source member')
        need(len(result)<=30000,'source stage member budget')
    return result

def stage(upstream,dest):
    upstream,dest=canonical(upstream),canonical(dest)
    need(not dest.exists(),'existing source output is preserved')
    def git(*args):return subprocess.check_output(['git','-C',str(upstream),*args],stderr=subprocess.PIPE,timeout=30)
    need(git('rev-parse','HEAD').decode().strip()==REVISION,'exact upstream Git revision required')
    need(git('status','--porcelain','--untracked-files=all')==b'','clean pinned upstream required')
    sources={name:(upstream/member).read_bytes() for name,member in MEMBERS.items()}
    changed,manifest=transform_sources(sources)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryFile() as archive:
        p=subprocess.run(['git','-C',str(upstream),'archive','--format=tar',REVISION],stdout=archive,stderr=subprocess.PIPE,timeout=60)
        need(p.returncode==0,'source archive failed')
        need(archive.tell()<=1024**3,'source archive byte budget');archive.seek(0)
        dest.mkdir()
        try:
            with tarfile.open(fileobj=archive,mode='r:') as tar:
                members=tar.getmembers();need(len(members)<=30000 and sum(m.size for m in members)<=1024**3,'archive member budget')
                tar.extractall(dest,filter='data')
            for name,data in changed.items():(dest/MEMBERS[name]).write_bytes(data)
            for name in ('panda_source_dispatch.h','panda_source_dispatch.cxx'):
                target=dest/'panda/src/glstuff'/name;need(not target.exists(),'runtime output collision')
                shutil.copy2(ROOT/'native'/name,target)
            manifest['source_tree']=tree_records(dest)
            manifest['source_tree_files']=len(manifest['source_tree'])
            (dest/'source-dispatch-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        except BaseException:
            # Preserve this task's partial stage for diagnosis, never present success.
            raise
    return manifest

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--upstream',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args(argv)
    try:
        result=stage(args.upstream,args.out)
        print(json.dumps(dict(out=args.out,files=result['source_tree_files'],direct_replacements=result['direct_replacements'],runtime_admission_ready=False)))
        return 0
    except (ValueError,OSError,subprocess.SubprocessError,tarfile.TarError) as exc:
        print('source stage rejected: '+str(exc),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
