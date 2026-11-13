"""Pure wheel bytes, publisher metadata and target dependency graph checks.

Never imports, installs or extracts wheel contents. Packaging is from the trusted tool pip.
"""
import base64
import csv
from email import policy
from email.parser import BytesParser
import hashlib
import io
import os
from pathlib import Path
import re
import stat
from time import perf_counter
import tokenize
import urllib.parse
import zipfile
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.tags import compatible_tags,cpython_tags,parse_tag
from pip._vendor.packaging.utils import canonicalize_name,parse_wheel_filename
from pip._vendor.packaging.version import Version

MIB=1024*1024
MAX_ARCHIVE=256*MIB
MAX_DECODED=3*1024*MIB
MAX_MEMBER=512*MIB
MAX_MEMBERS=100000
TARGET_PYTHON='3.11.18'
PLATFORMS=tuple('manylinux_2_'+str(n)+'_x86_64' for n in range(28,4,-1))+('manylinux2014_x86_64','manylinux2010_x86_64','manylinux1_x86_64')
TARGET_TAGS=set(cpython_tags((3,11),['cp311'],PLATFORMS))|set(compatible_tags((3,11),'cp311',PLATFORMS))
CV2_PROVIDERS={'opencv-python','opencv-python-headless','opencv-contrib-python','opencv-contrib-python-headless'}


def _need(ok,code):
    if not ok:raise ValueError(code)


def _safe(p):
    return type(p) is str and 0<len(p.encode())<=4096 and not p.startswith('/') and '\\' not in p and all(ord(c)>=32 and ord(c)!=127 for c in p) and len(p.split('/'))<=64 and all(v not in ('','.','..') and len(v.encode())<=255 for v in p.split('/'))


def _time(stop):_need(perf_counter()<=stop,'WHEEL_AUDIT_DEADLINE')

def _signature(st):return (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns,st.st_nlink)


def target_environment():
    return {'implementation_name':'cpython','implementation_version':TARGET_PYTHON,'os_name':'posix','platform_machine':'x86_64',
            'platform_python_implementation':'CPython','platform_release':'UNBOUND_UNSUPPORTED','platform_system':'Linux',
            'platform_version':'UNBOUND_UNSUPPORTED','python_full_version':TARGET_PYTHON,'python_version':'3.11','sys_platform':'linux','extra':''}


def _message(raw):
    _need(len(raw)<=4*MIB,'INVALID_WHEEL_INPUT')
    value=BytesParser(policy=policy.default).parsebytes(raw)
    _need(not value.defects and not value.is_multipart(),'INVALID_WHEEL_INPUT');return value


def inspect_wheel(path,*,deadline=None,remaining=None):
    stop=perf_counter()+120 if deadline is None else deadline
    remaining={'archive_bytes':MAX_ARCHIVE,'decoded_bytes':MAX_DECODED,'members':MAX_MEMBERS} if remaining is None else remaining
    _need(type(remaining) is dict and set(remaining)=={'archive_bytes','decoded_bytes','members'} and all(type(v) is int and v>=0 for v in remaining.values()),'WHEEL_SET_LIMIT')
    try:
        path=Path(path);_need(re.fullmatch(r'[A-Za-z0-9_.+!\-]{1,240}\.whl',path.name) is not None,'INVALID_WHEEL_INPUT')
        name,version,build,tags=parse_wheel_filename(path.name)
        _need(bool(tags&TARGET_TAGS),'UNSUPPORTED_WHEEL_TARGET')
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            before=os.fstat(stream.fileno());_need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=MAX_ARCHIVE,'INVALID_WHEEL_INPUT')
            _need(before.st_size<=remaining['archive_bytes'],'WHEEL_SET_LIMIT')
            archive_hash=hashlib.sha256();n=0
            for block in iter(lambda:stream.read(MIB),b''):_time(stop);archive_hash.update(block);n+=len(block);_need(n<=MAX_ARCHIVE,'INVALID_WHEEL_INPUT')
            _need(n==before.st_size,'INVALID_WHEEL_INPUT');stream.seek(0)
            kinds,hashes,sizes,headers={}, {}, {}, {};decoded=0
            with zipfile.ZipFile(stream) as archive:
                infos=archive.infolist();_need(0<len(infos)<=MAX_MEMBERS,'INVALID_WHEEL_INPUT')
                _need(len(infos)<=remaining['members'],'WHEEL_SET_LIMIT')
                for info in infos:
                    _time(stop);directory=info.is_dir();p=info.filename[:-1] if directory else info.filename
                    _need(info.orig_filename==info.filename and _safe(p) and p not in kinds and not info.flag_bits&1 and info.compress_type in (0,8),'INVALID_WHEEL_INPUT')
                    mode=info.external_attr>>16;_need(stat.S_IFMT(mode) in ((0,stat.S_IFDIR) if directory else (0,stat.S_IFREG)) and not stat.S_IMODE(mode)&0o7000,'INVALID_WHEEL_INPUT')
                    _need(0<=info.file_size<=MAX_MEMBER and decoded+info.file_size<=MAX_DECODED,'INVALID_WHEEL_INPUT')
                    _need(decoded+info.file_size<=remaining['decoded_bytes'],'WHEEL_SET_LIMIT');kinds[p]='directory' if directory else 'file'
                    if directory:_need(info.file_size==0,'INVALID_WHEEL_INPUT');continue
                    keep=p.count('/')==1 and p.split('/')[0].endswith('.dist-info') and p.rsplit('/',1)[1] in ('METADATA','WHEEL','RECORD')
                    digesters={a:hashlib.new(a) for a in ('sha256','sha384','sha512')};count=0;raw=bytearray()
                    with archive.open(info) as member:
                        for block in iter(lambda:member.read(MIB),b''):
                            _time(stop);count+=len(block);_need(count<=info.file_size and decoded+count<=MAX_DECODED,'INVALID_WHEEL_INPUT')
                            for hasher in digesters.values():hasher.update(block)
                            if keep:_need(len(raw)+len(block)<=4*MIB,'INVALID_WHEEL_INPUT');raw.extend(block)
                    _need(count==info.file_size,'INVALID_WHEEL_INPUT');decoded+=count;sizes[p]=count
                    hashes[p]={a:base64.urlsafe_b64encode(h.digest()).decode().rstrip('=') for a,h in digesters.items()}
                    if keep:headers[p]=bytes(raw)
                for p in kinds:
                    _time(stop);parts=p.split('/')
                    for i in range(1,len(parts)):_need(kinds.get('/'.join(parts[:i]))!='file','INVALID_WHEEL_INPUT')
            _need(_signature(os.fstat(stream.fileno()))==_signature(before),'WHEEL_INPUT_CHANGED')
        metas=[p for p in headers if p.endswith('.dist-info/METADATA')];_need(len(metas)==1,'INVALID_WHEEL_INPUT');prefix=metas[0].rsplit('/',1)[0]+'/'
        _need(set(headers)=={prefix+'METADATA',prefix+'WHEEL',prefix+'RECORD'},'INVALID_WHEEL_INPUT')
        metadata=_message(headers[prefix+'METADATA']);wheel=_message(headers[prefix+'WHEEL'])
        _need(metadata.get_all('Name') is not None and len(metadata.get_all('Name'))==1 and canonicalize_name(str(metadata['Name']))==name,'INVALID_WHEEL_INPUT')
        _need(metadata.get_all('Version') is not None and len(metadata.get_all('Version'))==1 and Version(str(metadata['Version']))==version,'INVALID_WHEEL_INPUT')
        _need(wheel.get_all('Wheel-Version')==['1.0'] and wheel.get_all('Root-Is-Purelib') in (['true'],['false']),'INVALID_WHEEL_INPUT')
        declared=set()
        for tag in wheel.get_all('Tag',[]):declared.update(parse_tag(str(tag)))
        _need(declared==tags,'INVALID_WHEEL_INPUT')
        python=metadata.get_all('Requires-Python',[]);_need(len(python)<=1,'INVALID_WHEEL_INPUT');python=str(python[0]) if python else None
        _need(python is None or SpecifierSet(python).contains(TARGET_PYTHON),'UNSUPPORTED_WHEEL_PYTHON')
        requires=[str(v) for v in metadata.get_all('Requires-Dist',[])];_need(len(requires)<=2048 and all(len(v)<=4096 for v in requires),'INVALID_WHEEL_INPUT')
        for requirement in requires:Requirement(requirement)
        extras=[canonicalize_name(str(v)) for v in metadata.get_all('Provides-Extra',[])];_need(len(extras)<=128 and len(set(extras))==len(extras) and all(re.fullmatch('[a-z0-9][a-z0-9-]{0,127}',v) for v in extras),'INVALID_WHEEL_INPUT')
        records=list(csv.reader(io.StringIO(headers[prefix+'RECORD'].decode('utf-8'),newline=''),strict=True));seen=set()
        for row in records:
            _need(len(row)==3 and row[0] in hashes and row[0] not in seen,'INVALID_WHEEL_INPUT');p,h,n=row;seen.add(p)
            if p==prefix+'RECORD':_need(h==n=='','INVALID_WHEEL_INPUT')
            else:
                algorithm,encoded=h.split('=',1);_need(algorithm in hashes[p] and hashes[p][algorithm]==encoded and n==str(sizes[p]),'INVALID_WHEEL_INPUT')
        _need(seen==set(hashes),'INVALID_WHEEL_INPUT')
        return {'name':str(name),'version':str(version),'filename':path.name,'nbytes':before.st_size,'sha256':archive_hash.hexdigest(),
                'metadata_sha256':hashlib.sha256(headers[prefix+'METADATA']).hexdigest(),'requires_python':python,'requires_dist':requires,
                'provides_extra':sorted(extras),'tags':sorted(str(v) for v in tags),'member_count':len(infos),'decoded_bytes':decoded,
                'startup_hooks':sorted(p for p in hashes if p.endswith('.pth') or p.rsplit('/',1)[-1] in ('sitecustomize.py','usercustomize.py'))}
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,zipfile.BadZipFile,csv.Error) as exc:
        allowed={'WHEEL_SET_LIMIT','WHEEL_AUDIT_DEADLINE','UNSUPPORTED_WHEEL_TARGET','UNSUPPORTED_WHEEL_PYTHON','WHEEL_INPUT_CHANGED'}
        raise ValueError(str(exc) if type(exc) is ValueError and str(exc) in allowed else 'INVALID_WHEEL_INPUT') from None


def _requirement(text):
    try:
        req=Requirement(text);_need(req.url is None,'DIRECT_DEPENDENCY_URL_REJECTED')
        if req.marker:
            names={t.string for t in tokenize.generate_tokens(io.StringIO(str(req.marker)).readline) if t.type==tokenize.NAME}
            _need(not names&{'platform_release','platform_version','extras','dependency_groups'},'UNSUPPORTED_TARGET_MARKER')
        return req
    except ValueError as exc:
        allowed={'DIRECT_DEPENDENCY_URL_REJECTED','UNSUPPORTED_TARGET_MARKER'}
        raise ValueError(str(exc) if str(exc) in allowed else 'INVALID_TARGET_REQUIREMENT') from None


def validate_graph(wheels,roots,*,deadline=None):
    stop=perf_counter()+120 if deadline is None else deadline
    def check_time():_need(perf_counter()<=stop,'TARGET_GRAPH_DEADLINE')
    check_time()
    _need(type(wheels) is list and 0<len(wheels)<=96 and type(roots) is list and 0<len(roots)<=32,'TARGET_GRAPH_REJECTED')
    nodes={}
    for row in wheels:
        name=canonicalize_name(row['name']);_need(name==row['name'] and name not in nodes,'DUPLICATE_WHEEL_DISTRIBUTION');nodes[name]=row
    _need(len(set(nodes)&CV2_PROVIDERS)<=1,'MULTIPLE_CV2_PROVIDERS')
    requirements={}
    for n,row in nodes.items():
        check_time();requirements[n]=[]
        for text in row['requires_dist']:check_time();requirements[n].append(_requirement(text))
    extras={};queue=[];edges={};environment=target_environment()
    def admit(req,parent):
        name=canonicalize_name(req.name);_need(name in nodes and req.specifier.contains(nodes[name]['version'],prereleases=True),'UNSATISFIED_TARGET_DEPENDENCY')
        wanted={canonicalize_name(v) for v in req.extras};_need(wanted<=set(nodes[name]['provides_extra']),'UNDECLARED_TARGET_EXTRA')
        if name not in extras:extras[name]=set();queue.append(name)
        if not wanted<=extras[name]:extras[name].update(wanted);queue.append(name)
        if parent is not None:edges[(parent,name,str(req))]={'parent':parent,'dependency':name,'requirement':str(req)}
        _need(len(edges)<=10000,'TARGET_GRAPH_REJECTED')
    for text in roots:
        req=_requirement(text)
        if req.marker is None or req.marker.evaluate(environment):admit(req,None)
    processed={}
    while queue:
        check_time();name=queue.pop(0);contexts=frozenset(['',*extras[name]])
        if processed.get(name)==contexts:continue
        processed[name]=contexts
        for req in requirements[name]:
            check_time()
            if req.marker is None or any(req.marker.evaluate({**environment,'extra':context}) for context in contexts):admit(req,name)
    _need(set(extras)==set(nodes),'ORPHAN_WHEEL')
    return {'schema':'target-python-wheel-graph-v1','status':'CLOSED_TARGET_WHEEL_GRAPH','environment':environment,'root_requirements':roots,
            'selected_names':sorted(nodes),'requested_extras':{n:sorted(extras[n]) for n in sorted(extras)},'edges':[edges[k] for k in sorted(edges)],
            'installed_runtime_verified':False,'native_admission':False,'image_preparation_ready':False}


def public_wheel_url(url,filename):
    try:
        p=urllib.parse.urlsplit(url)
        return type(url) is str and p.scheme=='https' and p.hostname=='files.pythonhosted.org' and p.port in (None,443) and p.username is None and p.password is None and not p.query and not p.fragment and urllib.parse.unquote(p.path.rsplit('/',1)[-1])==filename
    except (TypeError,ValueError):return False


def verify_publisher(wheel,data):
    try:
        _need(canonicalize_name(data['info']['name'])==wheel['name'] and Version(data['info']['version'])==Version(wheel['version']),'PUBLISHER_WHEEL_MISMATCH')
        rows=[v for v in data['urls'] if v['filename']==wheel['filename']];_need(len(rows)==1,'PUBLISHER_WHEEL_MISMATCH');r=rows[0]
        _need(r['packagetype']=='bdist_wheel' and type(r['size']) is int and r['size']==wheel['nbytes'] and r['digests']['sha256']==wheel['sha256'] and r['yanked'] is False and public_wheel_url(r['url'],wheel['filename']),'PUBLISHER_WHEEL_MISMATCH')
        _need(r.get('requires_python') is None or SpecifierSet(r['requires_python']).contains(TARGET_PYTHON),'PUBLISHER_WHEEL_MISMATCH')
        return {'kind':'pypi-release-file-v1','url':r['url'],'published_sha256':r['digests']['sha256'],'published_nbytes':r['size'],'yanked':False}
    except (ValueError,TypeError,KeyError):raise ValueError('PUBLISHER_WHEEL_MISMATCH') from None
