"""Bound current compiler selection and dependency bytes; no runtime admission."""
import hashlib,json,os,shlex,stat
from pathlib import Path
from scripts.panda_dispatch_coverage import read_input
from scripts import panda_sdk_routes_stage as stage
from scripts import panda_cache_adapter_cpu as cpu
ROOT=stage.ROOT;need=stage.need
TOOL_SHA='b6b3c42f8a882eb38fce83218e1fb173efde6aaa6d1b17263068e29d9414d1e4'
HOST_ROOTS=(Path('/usr/include'),Path('/usr/lib/gcc/x86_64-linux-gnu/14/include'),Path('/usr/lib/linux/uapi'))
def sha(data):return hashlib.sha256(data).hexdigest()
def tool_profile():
    data=read_input(ROOT/'docs/evidence/panda-sdk-routes-02/tool-profile.json',1024**2);need(sha(data)==TOOL_SHA,'tool profile pin');return json.loads(data)
def verify_tool_files(profile):
    for row in list(profile['tools'].values())+list(profile['link_inputs'].values()):
        p=Path(row['path']);need(str(p.resolve())==row['resolved_path'],'tool selected path changed');data=read_input(p.resolve(),64*1024**2);need(len(data)==row['nbytes'] and sha(data)==row['sha256'],'tool input changed')
    for name in profile['selection_absent']:need(not Path(name).exists() and not Path(name).is_symlink(),'compiler selection changed')
def verify_tools(env,out):
    profile=tool_profile();verify_tool_files(profile);out.mkdir(exist_ok=False);records=[]
    for i,row in enumerate(profile['queries']):
        r=cpu.run_command(row['command'],ROOT,env,out/('query-'+str(i)),5);need(r['returncode']==0 and not r['stderr'] and sha(r['stdout'].encode())==row['stdout_sha256'],'compiler selection query mismatch');records.append(r)
    verify_tool_files(profile);return dict(profile_sha256=TOOL_SHA,queries=records)
def parse_dependencies(data):
    need(type(data) is bytes and 0<len(data)<=4*1024**2 and b'\0' not in data,'dependency input budget')
    try:text=data.decode('utf-8').replace('\\\n','')
    except UnicodeError as e:raise ValueError('dependency UTF8') from e
    need(text.count(':')==1,'one dependency rule required');target,body=text.split(':');need(target.strip() and not body.strip().startswith('#'),'dependency rule')
    names=shlex.split(body,comments=False,posix=True);need(names and len(names)<=30000 and all('$' not in n and '\n' not in n and len(n)<=4096 for n in names),'dependency name budget');return list(dict.fromkeys(names))
def file_record(path):
    observed=path.stat();need(stat.S_ISREG(observed.st_mode),'regular input file required');size=observed.st_size;need(size<=64*1024**2,'input file budget');data=read_input(path,64*1024**2) if size else b'';return dict(kind='file',nbytes=size,sha256=sha(data),mode=stat.S_IMODE(observed.st_mode))
def capture_host_inputs(roots=HOST_ROOTS):
    result={};total=0
    for root in roots:
        root=Path(root).resolve();need(root.is_dir(),'host header root missing')
        for p in [root,*sorted(root.rglob('*'))]:
            need(len(result)<30000,'host header node budget');key=str(p)
            if p.is_symlink():result[key]=dict(kind='symlink',target=os.readlink(p))
            elif p.is_dir():result[key]=dict(kind='directory',mode=stat.S_IMODE(p.stat().st_mode))
            else:r=file_record(p);total+=r['nbytes'];need(total<=1024**3,'host header byte budget');result[key]=r
    return result
def qualify_dependencies(paths,source,sdk,sysroot,host_before):
    roots=[(Path(p).resolve(),n) for p,n in [(source,'source'),(sdk,'generated'),(sysroot,'private')]];rows={}
    for name in paths:
        p=Path(name)
        try:p=(p if p.is_absolute() else Path(source)/p).resolve()
        except (OSError,RuntimeError) as e:raise ValueError('dependency path unresolved') from e
        need(p.is_file(),'dependency file missing');record=file_record(p)
        matches=[n for root,n in roots if p.is_relative_to(root)]
        if matches:need(len(matches)==1,'dependency roots overlap');origin=matches[0]
        else:need(str(p) in host_before and host_before[str(p)]==record,'host input changed or unregistered dependency');origin='host'
        rows[str(p)]=dict(path=str(p),origin=origin,**record)
    return [rows[n] for n in sorted(rows)]
