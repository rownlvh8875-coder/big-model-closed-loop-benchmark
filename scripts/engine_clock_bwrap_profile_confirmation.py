"""One-use scoped backend confirmation with exact tool-owned PWD and retained facts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse

if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from scripts import engine_clock_bwrap_profile_preflight as previous
prep,sandbox=previous.prep,previous.sandbox
REQUEST_ID='namespace-diagnostic-20261113-04'
BRANCH='diagnose/engine-clock-namespace-20261113-04'
WORKFLOW='.github/workflows/engine-clock-bwrap-profile-confirmation.yml'
REQUEST_PATH='docs/requests/engine-clock-'+REQUEST_ID+'.json'
PROFILE,HELPER,NAMES,CAPS=previous.PROFILE,previous.HELPER,previous.NAMES,previous.CAPS
qualify=previous.qualify
CLOSURE=frozenset([WORKFLOW,PROFILE,'scripts/__init__.py',
    *['scripts/engine_clock_builder_'+x+'.py' for x in ('preparation','staging','sandbox','wheel','driver')],
    'scripts/engine_clock_bwrap_profile_preflight.py','scripts/engine_clock_bwrap_profile_confirmation.py',
    'tests/test_engine_clock_bwrap_profile_confirmation.py',
    'docs/superpowers/specs/2026-11-13-engine-clock-bwrap-profile-confirmation-design.md',
    'docs/superpowers/plans/2026-11-13-engine-clock-bwrap-profile-confirmation.md'])
OBSERVER="""import hashlib,json,os
v={'namespaces':{n:os.readlink('/proc/self/ns/'+n) for n in ('user','net','mnt','pid','ipc','uts')},'uid':os.getuid(),'gid':os.getgid(),'caps':{},'env_keys':sorted(os.environ),'root_write_errno':None,'build_write':False,'profile':None}
for line in open('/proc/self/status'):
 k,_,x=line.partition(':')
 if k in ('CapEff','CapPrm','CapInh','CapAmb','CapBnd'):v['caps'][k]=x.strip()
r=open('/proc/self/attr/current','rb').read(256).strip()
v['profile']=r.decode('ascii') if r in (b'unconfined',b'stage7-bwrap (unconfined)',b'unprivileged_userns (enforce)') else None
v['profile_sha256']=hashlib.sha256(r).hexdigest()
pwd=os.environ.get('PWD','')
v['pwd']=pwd if pwd=='/build' else None
v['pwd_sha256']=hashlib.sha256(pwd.encode()).hexdigest()
try:
 f=os.open('/probe-root-write-forbidden',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(f)
except OSError as e:v['root_write_errno']=e.errno
f=os.open('/build/probe-marker',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
v['build_write']=os.write(f,b'stage7-trusted-probe\\n')==21
os.close(f)
print(json.dumps(v,sort_keys=True))
"""


def parse_observation(value):
    """Transport safety checks allow meaningful admission failures to survive."""
    try:
        expected={'namespaces','uid','gid','caps','env_keys','root_write_errno','build_write','profile','profile_sha256','pwd','pwd_sha256'}
        prep._need(type(value) is dict and set(value)==expected,'INVALID_PROBE_WIRE')
        prep._need(type(value['namespaces']) is dict and set(value['namespaces'])==set(NAMES),'INVALID_PROBE_WIRE')
        for n in NAMES:prep._need(type(value['namespaces'][n]) is str and re.fullmatch(n+r':\[[0-9]{1,20}\]',value['namespaces'][n]),'INVALID_PROBE_WIRE')
        prep._need(all(type(value[k]) is int and 0<=value[k]<=4294967295 for k in ('uid','gid')),'INVALID_PROBE_WIRE')
        prep._need(type(value['caps']) is dict and set(value['caps'])==set(CAPS) and all(prep._digest(x,16) for x in value['caps'].values()),'INVALID_PROBE_WIRE')
        prep._need(type(value['env_keys']) is list and len(value['env_keys'])<=64 and all(type(k) is str and re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,63}',k) for k in value['env_keys']),'INVALID_PROBE_WIRE')
        error=value['root_write_errno'];prep._need(error is None or type(error) is int and 1<=error<=4095,'INVALID_PROBE_WIRE')
        prep._need(type(value['build_write']) is bool and value['profile'] in (None,'unconfined','stage7-bwrap (unconfined)','unprivileged_userns (enforce)') and value['pwd'] in (None,'/build'),'INVALID_PROBE_WIRE')
        prep._need(prep._digest(value['pwd_sha256']) and prep._digest(value['profile_sha256']),'INVALID_PROBE_WIRE')
        return value
    except (ValueError,TypeError,KeyError):raise ValueError('INVALID_PROBE_WIRE') from None


def validate_observation(value,host,after=False):
    try:
        parse_observation(value)
        prep._need(value['env_keys']==sorted([*sandbox.CHILD_ENV,'PWD']) and value['pwd']=='/build'
                   and value['pwd_sha256']==hashlib.sha256(b'/build').hexdigest(),'INVALID_PROBE_OBSERVATION')
        if value['profile'] is not None:prep._need(value['profile_sha256']==hashlib.sha256(value['profile'].encode()).hexdigest(),'INVALID_PROBE_OBSERVATION')
        base={k:v for k,v in value.items() if k not in ('pwd','pwd_sha256','profile_sha256')}
        base['env_keys']=[k for k in value['env_keys'] if k!='PWD']
        previous.validate_observation(base,host,after=after)
        return value
    except (ValueError,TypeError,KeyError):raise ValueError('INVALID_PROBE_OBSERVATION') from None


def probe_argv(rootfd,buildfd):
    args=previous.probe_argv(rootfd,buildfd);args[-1]=OBSERVER
    return args


class Backend(previous.Backend):
    def _probe(self,label):
        root=self.work/('probe-'+label);root.mkdir()
        for name in ('usr','lib','lib64','proc','dev','build'):(root/name).mkdir()
        fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:receipt,raw=sandbox.capture(probe_argv(fd,self.buildfd),timeout=10,stdout_limit=8192,stderr_limit=8192,pass_fds=(fd,self.buildfd))
        finally:os.close(fd)
        result={'process':receipt,'validated':False,'observation':None}
        if receipt['status']=='EXITED' and receipt['returncode']==0:
            try:result['observation']=parse_observation(prep._json(raw))
            except ValueError:result['validation_error']='INVALID_PROBE_WIRE';return result
            try:
                validate_observation(result['observation'],self.host['namespaces'],after=label=='after')
                result['validated']=True
            except ValueError:result['validation_error']='INVALID_PROBE_OBSERVATION'
        return result


def validate_request(value):
    try:
        prep._need(type(value) is dict and set(value)=={'schema','request_id','repository','branch','workflow_path','reviewed_source_sha','budget','source_closure'},'INVALID_REQUEST')
        expected={'schema':'namespace-profile-confirmation-request-v1','request_id':REQUEST_ID,'repository':prep.REPOSITORY,'branch':BRANCH,'workflow_path':WORKFLOW}
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
    listing=api('/actions/workflows/engine-clock-bwrap-profile-confirmation.yml/runs?branch='+urllib.parse.quote(BRANCH,safe='')+'&per_page=2')
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
        backend=Backend(root,work,buildfd)
        backend.host['kernel']=os.uname().release
        image=env.get('ImageVersion','');backend.host['image_version']=image if re.fullmatch(r'[0-9.\-]{1,64}',image) else None
        result['qualification']=qualify(backend);result['host']=backend.host
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
