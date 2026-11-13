"""One-use namespace identity observation; no network or policy configuration."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.parse

if __name__ == '__main__': sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from scripts import engine_clock_builder_preparation as prep
from scripts import engine_clock_builder_sandbox as sandbox
REQUEST_ID='namespace-diagnostic-20261113-02'
BRANCH='diagnose/engine-clock-namespace-20261113-02'
WORKFLOW='.github/workflows/engine-clock-namespace-identity.yml'
REQUEST_PATH='docs/requests/engine-clock-'+REQUEST_ID+'.json'
CLOSURE=frozenset([WORKFLOW,'scripts/__init__.py',
    *['scripts/engine_clock_builder_'+x+'.py' for x in ('preparation','staging','sandbox','wheel','driver')],
    'scripts/engine_clock_namespace_identity.py',
    'tests/test_engine_clock_namespace_identity.py',
    'docs/superpowers/specs/2026-11-13-engine-clock-namespace-identity-design.md',
    'docs/superpowers/plans/2026-11-13-engine-clock-namespace-identity.md'])


def namespace_detail(path,name):
    value={'readlink':None,'readlink_errno':None,'readlink_sha256':None,
           'stat':None,'stat_errno':None,'open':None,'open_errno':None}
    try:
        raw=os.fsencode(os.readlink(path))
        value['readlink_sha256']=hashlib.sha256(raw).hexdigest()
        if re.fullmatch(name.encode()+rb':\[[0-9]{1,20}\]',raw): value['readlink']=raw.decode('ascii')
    except OSError as exc: value['readlink_errno']=exc.errno
    try:
        st=path.stat();value['stat']=[st.st_dev,st.st_ino]
    except OSError as exc: value['stat_errno']=exc.errno
    fd=None
    try:
        fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC);st=os.fstat(fd);value['open']=[st.st_dev,st.st_ino]
    except OSError as exc: value['open_errno']=exc.errno
    finally:
        if fd is not None: os.close(fd)
    return value


def read_fact(path,limit=16384):
    receipt={'success':False,'errno':None,'nbytes':0,'sha256':hashlib.sha256(b'').hexdigest(),'truncated':False}
    try:
        with path.open('rb') as f: raw=f.read(limit+1)
        receipt.update(success=True,nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),truncated=len(raw)>limit)
        return raw[:limit],receipt
    except OSError as exc:
        receipt['errno']=exc.errno
        return b'',receipt


def snapshot(proc=Path('/proc')):
    value={'pid':os.getpid(),'uid':os.getuid(),'gid':os.getgid(),
           'facts':{'effective_uid':os.geteuid(),'effective_gid':os.getegid(),'namespaces':{},'status':{},'sysctls':{}},
           'namespace_details':{},'maps':{},'proc_reads':{}}
    def read(name,limit=16384):
        raw,receipt=read_fact(proc/name,limit);value['proc_reads'][name]=receipt
        return raw
    for base in ('self','thread-self'):
        for name in ('user','net'):
            value['namespace_details'][base+'/'+name]=namespace_detail(proc/base/'ns'/name,name)
    for name in ('user','net'): value['facts']['namespaces'][name]=value['namespace_details']['self/'+name]['stat']
    for line in read('self/status').decode('ascii','ignore').splitlines():
        key,sep,text=line.partition(':');text=text.strip()
        if key in ('CapInh','CapPrm','CapEff','CapBnd','CapAmb') and re.fullmatch('[0-9a-f]{16}',text): value['facts']['status'][key]=text
        elif key in ('NoNewPrivs','Seccomp','Seccomp_filters') and text.isdigit(): value['facts']['status'][key]=int(text)
    for name in ('user/max_user_namespaces','kernel/unprivileged_userns_clone','kernel/apparmor_restrict_unprivileged_userns','kernel/cap_last_cap'):
        raw=read('sys/'+name,32).strip();value['facts']['sysctls'][name]=int(raw) if raw.isdigit() else None
    raw=read('self/attr/current')
    label=raw.strip()
    allowed=(b'unconfined',b'unprivileged_userns',b'unprivileged_userns (enforce)',b'bwrap (enforce)',b'docker-default (enforce)')
    value['facts']['profile']={'known':label.decode('ascii') if label in allowed else None,
                              'nbytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    for name in ('uid_map','gid_map'):
        rows=[]
        for line in read('self/'+name,4096).splitlines():
            words=line.split()
            if len(words)==3 and all(x.isdigit() and len(x)<=10 for x in words): rows.append([int(x) for x in words])
        value['maps'][name]=rows[:16]
    return value


def typed_unshare(libc,flags):
    libc.unshare.argtypes=[ctypes.c_int]
    libc.unshare.restype=ctypes.c_int
    ctypes.set_errno(0)
    result=libc.unshare(flags)
    error=ctypes.get_errno()
    return {'flags':flags,'returncode':int(result),'errno':error}


class Linux:
    def snapshot(self): return snapshot()
    def invoke(self,flags): return typed_unshare(ctypes.CDLL(None,use_errno=True),flags)


def worker(case,backend=None):
    if case not in ('NOOP','RAW_USER_NET','SNAPSHOT'): raise ValueError('INVALID_CASE')
    backend=backend or Linux()
    value={'case':case,'pid':os.getpid(),'before':backend.snapshot(),'syscall':None,'admission':False}
    try:
        if case!='SNAPSHOT': value['syscall']=backend.invoke(0 if case=='NOOP' else 0x50000000)
    finally: value['after']=backend.snapshot()
    return value


def parse_journal(raw,pids):
    value={'availability':'UNKNOWN','usable_records':0,'observations':[]}
    for line in raw.splitlines():
        try:
            message=json.loads(line).get('MESSAGE')
            if type(message) is not str: continue
            value['usable_records']+=1
            op=re.search(r'\boperation="(userns_create|capable)"',message)
            decision=re.search(r'\bapparmor="(DENIED|AUDIT|ALLOWED)"',message)
            pid=re.search(r'\bpid=([0-9]{1,12})\b',message)
            if not (op and decision and pid and int(pid[1]) in pids): continue
            cap=re.search(r'\bcapname="(net_admin|setpcap|sys_admin)"',message)
            if op[1]=='capable' and not cap: continue
            label=re.search(r'\bprofile="([^"]*)"',message)
            value['observations'].append({'pid':int(pid[1]),'operation':op[1],'decision':decision[1],
                'capname':cap[1] if cap else None,'profile_sha256':hashlib.sha256(label[1].encode() if label else b'').hexdigest(),
                'message_sha256':hashlib.sha256(message.encode()).hexdigest()})
            if len(value['observations'])>=32: break
        except (ValueError,TypeError,AttributeError): continue
    if value['observations']: value['availability']='READ_COMPLETE_WITH_RECORDS'
    return value


def commands(root):
    base=['/usr/bin/python3','-I','-S','-B',str(root/'scripts/engine_clock_namespace_identity.py'),'--worker']
    return [('NOOP',base+['NOOP']),('RAW_USER_NET',base+['RAW_USER_NET']),
            ('UTIL_MAPPED_USER_NET',base[:-1]+['--launcher'])]


def util_argv(root):
    return ['/usr/bin/unshare','--user','--map-root-user','--net','--',
            '/usr/bin/python3','-I','-S','-B',str(root/'scripts/engine_clock_namespace_identity.py'),'--worker','SNAPSHOT']


def launch_util(root):
    header={'schema':'namespace-identity-launcher-v1','pid':os.getpid(),'before':snapshot()}
    sys.stdout.buffer.write(json.dumps(header,sort_keys=True,separators=(',',':')).encode()+b'\n')
    sys.stdout.buffer.flush()
    os.execve('/usr/bin/unshare',util_argv(root),sandbox.HOST_ENV)


def validate_request(value):
    try:
        prep._need(type(value) is dict and set(value)=={'schema','request_id','repository','branch','workflow_path','reviewed_source_sha','budget','source_closure'},'INVALID_REQUEST')
        expected={'schema':'namespace-identity-request-v1','request_id':REQUEST_ID,'repository':prep.REPOSITORY,'branch':BRANCH,'workflow_path':WORKFLOW}
        prep._need(all(value[k]==v for k,v in expected.items()) and prep._digest(value['reviewed_source_sha'],40),'INVALID_REQUEST')
        b=value['budget']
        prep._need(type(b) is dict and b=={'runs':1,'attempts':1,'workers':3} and all(type(v) is int for v in b.values()),'INVALID_REQUEST')
        prep._need(type(value['source_closure']) is dict and set(value['source_closure'])==CLOSURE and all(prep._digest(d) for d in value['source_closure'].values()),'INVALID_REQUEST')
        return value
    except (ValueError,TypeError,KeyError): raise ValueError('INVALID_REQUEST') from None


def validate_activation(request,head,current,reviewed,commit):
    try:
        prep._need(commit['sha']==head and len(commit['parents'])==1 and commit['parents'][0]['sha']==request['reviewed_source_sha'] and commit['tree']['sha']==current['sha'],'INVALID_ACTIVATION')
        def leaves(tree):
            prep._need(tree['truncated'] is False,'INVALID_ACTIVATION')
            result={}
            for row in tree['tree']:
                prep._need(row['type'] in ('tree','blob','commit'),'INVALID_ACTIVATION')
                if row['type']=='tree': continue
                prep._need(row['path'] not in result,'INVALID_ACTIVATION')
                result[row['path']]=(row['type'],row['mode'],row['sha'])
            return result
        before,after=leaves(reviewed),leaves(current)
        changes={p for p in set(before)|set(after) if before.get(p)!=after.get(p)}
        prep._need(changes=={REQUEST_PATH} and REQUEST_PATH not in before and after[REQUEST_PATH][:2]==('blob','100644'),'INVALID_ACTIVATION')
    except (ValueError,TypeError,KeyError): raise ValueError('INVALID_ACTIVATION') from None


def authenticate(root,env):
    prep.require_remote_environment(env)
    request=validate_request(prep._json((root/REQUEST_PATH).read_bytes()))
    prep._need(env.get('GITHUB_REF')=='refs/heads/'+BRANCH and env.get('GITHUB_WORKFLOW_REF')==prep.REPOSITORY+'/'+WORKFLOW+'@refs/heads/'+BRANCH and Path(env.get('GITHUB_WORKSPACE','')).resolve()==root.resolve(),'INVALID_REMOTE_ENVIRONMENT')
    api=lambda suffix:prep.api_json('/repos/'+prep.REPOSITORY+suffix,env['GH_TOKEN'])
    run=api('/actions/runs/'+env['GITHUB_RUN_ID'])
    listing=api('/actions/workflows/engine-clock-namespace-identity.yml/runs?branch='+urllib.parse.quote(BRANCH,safe='')+'&per_page=2')
    prep.validate_context(request,run,listing,run_id=int(env['GITHUB_RUN_ID']),head=env['GITHUB_SHA'])
    commit=api('/git/commits/'+env['GITHUB_SHA'])
    prior=api('/git/commits/'+request['reviewed_source_sha'])
    prep._need(prior['sha']==request['reviewed_source_sha'],'INVALID_ACTIVATION')
    current=api('/git/trees/'+commit['tree']['sha']+'?recursive=1')
    reviewed=api('/git/trees/'+prior['tree']['sha']+'?recursive=1')
    prep.verify_source_closure(root,request,current);prep.verify_source_closure(root,request,reviewed)
    validate_activation(request,env['GITHUB_SHA'],current,reviewed,commit)
    blobs={r['path']:r['sha'] for r in current['tree'] if r['type']=='blob'}
    prep._need(blobs.get(REQUEST_PATH)==prep.git_blob_sha((root/REQUEST_PATH).read_bytes()),'SOURCE_CLOSURE_MISMATCH')
    return {'request':request,'run_id':int(env['GITHUB_RUN_ID']),'head_sha':env['GITHUB_SHA'],'run_attempt':1,
            'request_sha256':hashlib.sha256((root/REQUEST_PATH).read_bytes()).hexdigest()}


def run(root,env):
    binding=authenticate(root,env)
    result={'schema':'namespace-identity-result-v1','binding':binding,'host':snapshot(),
            'kernel':os.uname().release,'cases':[],'admission':False,'network_execution':False,
            'model_execution':False,'build_execution':False,'status':'OBSERVATION_INCOMPLETE'}
    image=env.get('ImageVersion','');result['image_version']=image if re.fullmatch(r'[0-9.\-]{1,64}',image) else None
    start=int(time.time());pids=set()
    for name,argv in commands(root):
        receipt,raw=sandbox.capture(argv,timeout=20,stdout_limit=32768,stderr_limit=8192)
        item={'case':name,'transport':receipt,'launcher':None,'observation':None}
        if name=='UTIL_MAPPED_USER_NET' and raw:
            line,separator,raw=raw.partition(b'\n')
            header=prep._json(line)
            prep._need(separator and type(header) is dict and set(header)=={'schema','pid','before'}
                       and header['schema']=='namespace-identity-launcher-v1' and type(header['pid']) is int
                       and header['pid']>0 and type(header['before']) is dict,'INVALID_LAUNCHER_RESULT')
            item['launcher']=header;pids.add(header['pid'])
        if receipt['status']=='EXITED' and receipt['returncode']==0:
            value=prep._json(raw)
            expected='SNAPSHOT' if name=='UTIL_MAPPED_USER_NET' else name
            prep._need(type(value) is dict and value.get('case')==expected and type(value.get('pid')) is int and value['pid']>0 and value.get('admission') is False,'INVALID_WORKER_RESULT')
            item['observation']=value;pids.add(value['pid'])
        result['cases'].append(item)
    receipt,raw=sandbox.capture(['/usr/bin/sudo','-n','/usr/bin/journalctl','-k','--since','@'+str(start),'--until','@'+str(int(time.time())+1),'--no-pager','-o','json'],timeout=10,stdout_limit=1048576,stderr_limit=8192)
    result['kernel_log']={'transport':receipt,**(parse_journal(raw,pids) if receipt['status']=='EXITED' and receipt['returncode']==0 else {'availability':'UNKNOWN','usable_records':0,'observations':[]})}
    if all(r['observation'] is not None for r in result['cases']): result['status']='OBSERVATION_COMPLETE_NOT_BUILD_READY'
    output=root/'output/stage7-namespace-identity'/REQUEST_ID
    output.mkdir(parents=True,exist_ok=False)
    raw=prep.canonical(result);prep._need(len(raw)<=131072,'RESULT_TOO_LARGE')
    (output/'identity.json').write_bytes(raw)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--worker',choices=('NOOP','RAW_USER_NET','SNAPSHOT'))
    modes.add_argument('--launcher',action='store_true')
    args=parser.parse_args()
    try:
        if args.launcher: launch_util(Path(__file__).resolve().parent.parent)
        elif args.worker: sys.stdout.buffer.write(prep.canonical(worker(args.worker)))
        else: run(Path(__file__).resolve().parent.parent,dict(os.environ))
    except Exception:
        print('NAMESPACE_IDENTITY_FAILED',file=sys.stderr);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
