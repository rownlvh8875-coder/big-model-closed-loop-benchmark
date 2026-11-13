"""One-use dedicated trusted bwrap profile preflight; no candidate/model execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse

if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from scripts import engine_clock_builder_preparation as prep
from scripts import engine_clock_builder_sandbox as sandbox
REQUEST_ID='namespace-diagnostic-20261113-03'
BRANCH='diagnose/engine-clock-namespace-20261113-03'
WORKFLOW='.github/workflows/engine-clock-bwrap-profile-preflight.yml'
REQUEST_PATH='docs/requests/engine-clock-'+REQUEST_ID+'.json'
PROFILE='docs/proposals/stage7-bwrap.apparmor'
HELPER='/usr/local/libexec/stage7-bwrap'
CLOSURE=frozenset([WORKFLOW,PROFILE,'scripts/__init__.py',
    *['scripts/engine_clock_builder_'+x+'.py' for x in ('preparation','staging','sandbox','wheel','driver')],
    'scripts/engine_clock_bwrap_profile_preflight.py','tests/test_engine_clock_bwrap_profile_preflight.py',
    'docs/superpowers/specs/2026-11-13-engine-clock-bwrap-profile-preflight-design.md',
    'docs/superpowers/plans/2026-11-13-engine-clock-bwrap-profile-preflight.md'])
NAMES=('user','net','mnt','pid','ipc','uts')
CAPS=('CapEff','CapPrm','CapInh','CapAmb','CapBnd')
KNOWN_FAILURES={'ed3471f7900377f86150471417911309833a36d664cb5af7409e139103f67ddf':61}
# Fixed trusted-host observer. It receives no source input or credentials.
OBSERVER="""import errno,hashlib,json,os
v={'namespaces':{n:os.readlink('/proc/self/ns/'+n) for n in ('user','net','mnt','pid','ipc','uts')},'uid':os.getuid(),'gid':os.getgid(),'caps':{},'env_keys':sorted(os.environ),'root_write_errno':None,'build_write':False,'profile':None}
for line in open('/proc/self/status'):
 k,_,x=line.partition(':')
 if k in ('CapEff','CapPrm','CapInh','CapAmb','CapBnd'):v['caps'][k]=x.strip()
r=open('/proc/self/attr/current','rb').read(256).strip()
v['profile']=r.decode('ascii') if r in (b'unconfined',b'stage7-bwrap (unconfined)') else None
try:
 f=os.open('/probe-root-write-forbidden',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(f)
except OSError as e:v['root_write_errno']=e.errno
f=os.open('/build/probe-marker',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
v['build_write']=os.write(f,b'stage7-trusted-probe\\n')==21
os.close(f)
print(json.dumps(v,sort_keys=True))
"""


def validate_observation(value,host,after=False):
    try:
        prep._need(type(value) is dict and set(value)=={'namespaces','uid','gid','caps','env_keys','root_write_errno','build_write','profile'},'INVALID_PROBE_OBSERVATION')
        prep._need(type(value['namespaces']) is dict and set(value['namespaces'])==set(NAMES) and set(host)==set(NAMES),'INVALID_PROBE_OBSERVATION')
        for n in NAMES:
            prep._need(type(value['namespaces'][n]) is str and re.fullmatch(n+r':\[[0-9]{1,20}\]',value['namespaces'][n]) and value['namespaces'][n]!=host[n],'INVALID_PROBE_OBSERVATION')
        prep._need(type(value['uid']) is int and value['uid']==0 and type(value['gid']) is int and value['gid']==0,'INVALID_PROBE_OBSERVATION')
        prep._need(type(value['caps']) is dict and set(value['caps'])==set(CAPS) and all(x=='0000000000000000' for x in value['caps'].values()),'INVALID_PROBE_OBSERVATION')
        prep._need(value['env_keys']==sorted(sandbox.CHILD_ENV) and type(value['root_write_errno']) is int and value['root_write_errno']==30 and value['build_write'] is True,'INVALID_PROBE_OBSERVATION')
        prep._need(value['profile'] in (None,'unconfined','stage7-bwrap (unconfined)') and (not after or value['profile']=='stage7-bwrap (unconfined)'),'INVALID_PROBE_OBSERVATION')
        return value
    except (ValueError,TypeError,KeyError):raise ValueError('INVALID_PROBE_OBSERVATION') from None


def probe_argv(rootfd,buildfd):
    args=sandbox.launch_argv(rootfd,buildfd);at=args.index('--')
    args[0]=HELPER
    return args[:at]+['--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--','/usr/bin/python3','-I','-S','-B','-c',OBSERVER]


def qualify(backend):
    result={'status':'BLOCKED','before':backend.baseline(),'profile_load':None,'after':None}
    before=result['before'];process=before['process']
    if before['validated']:
        result['status']='SUPPORTED_WITHOUT_PROFILE';return result
    known=(process.get('status')=='EXITED' and process.get('returncode')==1 and process.get('stderr_sha256') in KNOWN_FAILURES
           and process.get('stderr_bytes')==KNOWN_FAILURES[process['stderr_sha256']])
    if not known:return result
    result['eligible']=backend.eligible()
    if not result['eligible']:return result
    result['profile_load']=backend.load()
    if not result['profile_load']['loaded']:return result
    result['after']=backend.after()
    if result['after']['validated']:result['status']='SUPPORTED_SCOPED_PROFILE'
    return result


class Backend:
    def __init__(self,root,work,buildfd):
        self.root,self.work,self.buildfd=root,work,buildfd
        self.host={'namespaces':{n:os.readlink('/proc/self/ns/'+n) for n in NAMES}}
    def _probe(self,label):
        root=self.work/('probe-'+label);root.mkdir()
        for name in ('usr','lib','lib64','proc','dev','build'):(root/name).mkdir()
        fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:receipt,raw=sandbox.capture(probe_argv(fd,self.buildfd),timeout=10,stdout_limit=8192,stderr_limit=8192,pass_fds=(fd,self.buildfd))
        finally:os.close(fd)
        result={'process':receipt,'validated':False,'observation':None}
        if receipt['status']=='EXITED' and receipt['returncode']==0:
            try:
                result['observation']=validate_observation(prep._json(raw),self.host['namespaces'],after=label=='after')
                result['validated']=True
            except ValueError:result['validation_error']='INVALID_PROBE_OBSERVATION'
        return result
    def baseline(self):return self._probe('before')
    def after(self):return self._probe('after')
    def _profiles(self):
        receipt,raw=sandbox.capture(['/usr/bin/sudo','-n','/usr/bin/cat','/sys/kernel/security/apparmor/profiles'],timeout=5,stdout_limit=1048576,stderr_limit=8192)
        complete=receipt['status']=='EXITED' and receipt['returncode']==0
        lines=raw.splitlines() if complete else []
        facts={'transport':receipt,'unprivileged_profile':b'unprivileged_userns (enforce)' in lines,
               'dedicated_profile':b'stage7-bwrap (unconfined)' in lines,
               'any_dedicated_name':any(x.startswith(b'stage7-bwrap ') for x in lines)}
        return complete,facts
    def eligible(self):
        def small(path):
            try:return Path(path).read_bytes()[:32].strip()
            except OSError:return b''
        complete,facts=self._profiles();self.host['profile_list_before']=facts
        self.host['apparmor_enabled']=small('/sys/module/apparmor/parameters/enabled')==b'Y'
        self.host['restrict_unprivileged_userns']=small('/proc/sys/kernel/apparmor_restrict_unprivileged_userns')==b'1'
        return complete and facts['unprivileged_profile'] and not facts['any_dedicated_name'] and self.host['apparmor_enabled'] and self.host['restrict_unprivileged_userns'] and Path('/usr/sbin/apparmor_parser').is_file()
    def load(self):
        receipt,raw=sandbox.capture(['/usr/bin/sudo','-n','/usr/sbin/apparmor_parser','-r','--',str(self.root/PROFILE)],timeout=10,stdout_limit=8192,stderr_limit=8192)
        result={'process':receipt,'loaded':False}
        if receipt['status']=='EXITED' and receipt['returncode']==0:
            complete,facts=self._profiles();self.host['profile_list_after']=facts
            result['loaded']=complete and facts['dedicated_profile']
        return result


def validate_request(value):
    try:
        prep._need(type(value) is dict and set(value)=={'schema','request_id','repository','branch','workflow_path','reviewed_source_sha','budget','source_closure'},'INVALID_REQUEST')
        expected={'schema':'namespace-profile-request-v1','request_id':REQUEST_ID,'repository':prep.REPOSITORY,'branch':BRANCH,'workflow_path':WORKFLOW}
        prep._need(all(value[k]==v for k,v in expected.items()) and prep._digest(value['reviewed_source_sha'],40),'INVALID_REQUEST')
        b=value['budget']
        prep._need(type(b) is dict and b=={'runs':1,'attempts':1,'probes':2,'profile_loads':1} and all(type(v) is int for v in b.values()),'INVALID_REQUEST')
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
    listing=api('/actions/workflows/engine-clock-bwrap-profile-preflight.yml/runs?branch='+urllib.parse.quote(BRANCH,safe='')+'&per_page=2')
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
    out=root/'output/stage7-bwrap-profile-preflight'/REQUEST_ID
    out.mkdir(parents=True,exist_ok=True)
    result={'schema':'namespace-profile-result-v1','binding':binding,'status':'BLOCKED','errors':[],
            'candidate_execution':False,'model_execution':False,'build_execution':False,'image_ready':False,'native_admission':False}
    buildfd=None
    try:
        work=Path('/tmp/engine-clock-profile-preflight-'+REQUEST_ID);work.mkdir(mode=0o700)
        tool=Path(HELPER);st=tool.stat()
        prep._need(not tool.is_symlink() and st.st_uid==0 and st.st_mode&0o7777==0o755 and st.st_size<=1048576,'INVALID_PRIVATE_HELPER')
        result['host_helper_preparation']='PINNED_SOURCE_COMPILE'
        result['helper']={'sha256':hashlib.sha256(tool.read_bytes()).hexdigest(),'nbytes':st.st_size,'owner':st.st_uid,'mode':st.st_mode&0o7777,'source_sha256':'9760d007363e3abba7c747489910f9f82d9fca53ba3bd3282e396fa3c97a3314'}
        result['version_process'],version=sandbox.capture([HELPER,'--version'],timeout=5)
        help_receipt,help_raw=sandbox.capture([HELPER,'--help'],timeout=5);result['help_process']=help_receipt
        prep._need(result['version_process']['returncode']==0 and version==b'bubblewrap 0.12.0\n' and help_receipt['returncode']==0 and sandbox.supported_options(help_raw.decode('utf-8')),'UNSUPPORTED_HELPER')
        result['capacity']={};prep.check_host_capacity(work,result['capacity'])
        buildfd,result['build_mount']=prep.open_build_mount(REQUEST_ID)
        backend=Backend(root,work,buildfd);result['qualification']=qualify(backend);result['host']=backend.host
        result['status']=result['qualification']['status']
        result['profile_sha256']=hashlib.sha256((root/PROFILE).read_bytes()).hexdigest()
    except Exception:
        result['errors'].append('PREFLIGHT_FAILED')
    finally:
        if buildfd is not None:os.close(buildfd)
        raw=prep.canonical(result);prep._need(len(raw)<=131072,'RESULT_TOO_LARGE')
        (out/'preflight.json').write_bytes(raw)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--guard-only',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parent.parent
    try:
        if args.guard_only:authenticate(root,dict(os.environ))
        else:run(root,dict(os.environ))
    except Exception:
        print('SCOPED_PREFLIGHT_FAILED',file=sys.stderr);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
