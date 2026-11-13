"""Owned descriptor and fixed observer fixtures; no live bwrap/profile/network."""
import copy
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

try:
    from scripts import engine_clock_bwrap_profile_confirmation as p
except ImportError:p=None


class ConfirmationTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(p,'owned-PWD confirmation missing')
    def fixture(self):
        host={n:n+':[10]' for n in ('user','net','mnt','pid','ipc','uts')}
        label='stage7-bwrap (unconfined)'
        v={'namespaces':{n:n+':[20]' for n in host},'uid':0,'gid':0,
           'caps':{n:'0000000000000000' for n in ('CapEff','CapPrm','CapInh','CapAmb','CapBnd')},
           'env_keys':['LANG','LC_ALL','PATH','PIP_CONFIG_FILE','PIP_NO_COMPILE','PWD','PYTHONDONTWRITEBYTECODE','PYTHONHASHSEED','SOURCE_DATE_EPOCH','TMPDIR','TZ'],
           'root_write_errno':30,'build_write':True,'profile':label,'profile_sha256':hashlib.sha256(label.encode()).hexdigest(),
           'pwd':'/build','pwd_sha256':hashlib.sha256(b'/build').hexdigest()}
        return host,v
    def test_exact_owned_pwd_is_valid_without_mutating_observation(self):
        host,v=self.fixture();original=copy.deepcopy(v)
        self.assertEqual(v,p.validate_observation(v,host,after=True));self.assertEqual(original,v)
    def test_wrong_pwd_extra_credentials_caps_and_namespace_are_not_admitted(self):
        host,v=self.fixture()
        for kind in ('pwd','hash','extraenv','caps','namespace'):
            bad=copy.deepcopy(v)
            if kind=='pwd':bad['pwd']=None
            elif kind=='hash':bad['pwd_sha256']='0'*64
            elif kind=='extraenv':bad['env_keys'].append('GH_TOKEN')
            elif kind=='caps':bad['caps']['CapEff']='0000000000001000'
            else:bad['namespaces']['net']='net:[10]'
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'^INVALID_PROBE_OBSERVATION$'):p.validate_observation(bad,host,after=True)
    def test_shape_safe_wire_keeps_semantic_failure_but_rejects_unknown_text(self):
        host,v=self.fixture();v['caps']['CapEff']='0000000000001000';self.assertEqual(v,p.parse_observation(v))
        for kind in ('extra','profile','pwd','namespace','cap','env'):
            bad=copy.deepcopy(v)
            if kind=='extra':bad['unknown']='SECRET_SENTINEL'
            elif kind=='profile':bad['profile']='SECRET_SENTINEL'
            elif kind=='pwd':bad['pwd']='SECRET_SENTINEL'
            elif kind=='namespace':bad['namespaces']['net']='SECRET_SENTINEL'
            elif kind=='cap':bad['caps']['CapEff']='SECRET_SENTINEL'
            else:bad['env_keys'].append('SECRET=value')
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'^INVALID_PROBE_WIRE$'):p.parse_observation(bad)
    def test_backend_retains_rejected_facts_and_passes_real_owned_fds(self):
        host,v=self.fixture();v['caps']['CapEff']='0000000000001000'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);build=root/'build';build.mkdir();fd=os.open(build,os.O_RDONLY|os.O_DIRECTORY)
            try:
                backend=p.Backend(root,root,fd);backend.host['namespaces']=host
                def capture(argv,**kwargs):
                    descriptors=kwargs['pass_fds'];self.assertEqual(fd,descriptors[1]);self.assertNotEqual(fd,descriptors[0])
                    self.assertEqual((os.stat(build).st_dev,os.stat(build).st_ino),(os.fstat(descriptors[1]).st_dev,os.fstat(descriptors[1]).st_ino))
                    self.assertEqual('before',Path(os.readlink('/proc/self/fd/'+str(descriptors[0]))).name.removeprefix('probe-'))
                    self.assertEqual('/usr/local/libexec/stage7-bwrap',argv[0]);self.assertEqual(p.OBSERVER,argv[-1])
                    return {'status':'EXITED','returncode':0},json.dumps(v).encode()
                with patch.object(p.sandbox,'capture',side_effect=capture):r=backend.baseline()
                self.assertFalse(r['validated']);self.assertEqual(v,r['observation']);self.assertEqual('INVALID_PROBE_OBSERVATION',r['validation_error'])
            finally:os.close(fd)
    def test_observer_emits_owned_pwd_and_safe_hashes_without_host_io(self):
        host,v=self.fixture()
        fake=types.SimpleNamespace(environ={**{k:'' for k in v['env_keys']},'PWD':'/build'},getuid=lambda:0,getgid=lambda:0,
        readlink=lambda path:v['namespaces'][path.rsplit('/',1)[-1]],O_WRONLY=1,O_CREAT=64,O_EXCL=128,close=lambda fd:None,write=lambda fd,data:len(data))
        def osopen(path,*args):
            if path=='/probe-root-write-forbidden':raise OSError(30,'fixture')
            self.assertEqual('/build/probe-marker',path);return 10
        fake.open=osopen
        def opened(path,*args):
            if path=='/proc/self/status':return io.StringIO(''.join(k+': 0000000000000000\n' for k in v['caps']))
            self.assertEqual('/proc/self/attr/current',path);return io.BytesIO(b'stage7-bwrap (unconfined)\n')
        output=io.StringIO()
        with patch.dict('sys.modules',{'os':fake}),patch('builtins.open',side_effect=opened),contextlib.redirect_stdout(output):exec(compile(p.OBSERVER,'trusted-observer','exec'),{})
        observed=json.loads(output.getvalue());self.assertEqual(v,observed);self.assertEqual(observed,p.validate_observation(observed,host,after=True))
    def test_request04_own_identity_and_same_budgets(self):
        d={'schema':'namespace-profile-confirmation-request-v1','request_id':'namespace-diagnostic-20261113-04','repository':'rownlvh8875-coder/big-model-closed-loop-benchmark',
        'branch':'diagnose/engine-clock-namespace-20261113-04','workflow_path':'.github/workflows/engine-clock-bwrap-profile-confirmation.yml','reviewed_source_sha':'1'*40,
        'budget':{'runs':1,'attempts':1,'probes':2,'profile_loads':1},'source_closure':{x:'0'*64 for x in p.CLOSURE}}
        self.assertEqual(d,p.validate_request(d));d['request_id']='namespace-diagnostic-20261113-03'
        with self.assertRaisesRegex(ValueError,'^INVALID_REQUEST$'):p.validate_request(d)


    def test_authenticate_uses_actual_tree_shas_and_rejects_attempt_source_and_run_mutations(self):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                for name in p.CLOSURE:
                    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
                request={'schema':'namespace-profile-confirmation-request-v1','request_id':p.REQUEST_ID,'repository':p.prep.REPOSITORY,'branch':p.BRANCH,'workflow_path':p.WORKFLOW,
                         'reviewed_source_sha':'1'*40,'budget':{'runs':1,'attempts':1,'probes':2,'profile_loads':1},'source_closure':{name:hashlib.sha256(b'fixture').hexdigest() for name in p.CLOSURE}}
                path=root/p.REQUEST_PATH;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(p.prep.canonical(request))
                prior={'sha':'3'*40,'truncated':False,'tree':[{'path':n,'type':'blob','mode':'100644','sha':p.prep.git_blob_sha(b'fixture')} for n in p.CLOSURE]}
                current=copy.deepcopy(prior);current['sha']='5'*40;current['tree'].append({'path':p.REQUEST_PATH,'type':'blob','mode':'100644','sha':p.prep.git_blob_sha(path.read_bytes())})
                run={'id':123,'run_attempt':1,'head_sha':'2'*40,'head_branch':p.BRANCH,'event':'push','path':p.WORKFLOW,'repository':{'full_name':p.prep.REPOSITORY}}
                env={'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':p.prep.REPOSITORY,'GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':'2'*40,'GITHUB_RUN_ID':'123','GH_TOKEN':'SECRET_SENTINEL',
                     'GITHUB_REF':'refs/heads/'+p.BRANCH,'GITHUB_WORKFLOW_REF':p.prep.REPOSITORY+'/'+p.WORKFLOW+'@refs/heads/'+p.BRANCH,'GITHUB_WORKSPACE':str(root)}
                routes=[]
                def api(route,token):
                    routes.append(route)
                    base='/repos/'+p.prep.REPOSITORY
                    mapping={base+'/actions/runs/123':run,
                      base+'/actions/workflows/engine-clock-bwrap-profile-confirmation.yml/runs?branch=diagnose%2Fengine-clock-namespace-20261113-04&per_page=2':{'total_count':1,'workflow_runs':[run]},
                      base+'/git/commits/'+'2'*40:{'sha':'2'*40,'parents':[{'sha':'1'*40}],'tree':{'sha':'5'*40}},
                      base+'/git/commits/'+'1'*40:{'sha':'1'*40,'parents':[],'tree':{'sha':'3'*40}},
                      base+'/git/trees/'+'5'*40+'?recursive=1':current,base+'/git/trees/'+'3'*40+'?recursive=1':prior}
                    self.assertIn(route,mapping,'unexpected API route or commit-ish tree lookup')
                    return mapping[route]
                with patch.object(p.prep,'api_json',side_effect=api):
                    self.assertEqual('2'*40,p.authenticate(root,env)['head_sha'])
                    self.assertEqual(6,len(routes));routes.clear()
                    env['GITHUB_RUN_ATTEMPT']='2'
                    with self.assertRaisesRegex(ValueError,'^INVALID_REMOTE_ENVIRONMENT$'):p.authenticate(root,env)
                    self.assertEqual([],routes);env['GITHUB_RUN_ATTEMPT']='1'
                    run['path']='.github/workflows/other.yml'
                    with self.assertRaisesRegex(ValueError,'^INVALID_RUN_CONTEXT$'):p.authenticate(root,env)
                    run['path']=p.WORKFLOW
                    (root/p.PROFILE).write_bytes(b'changed')
                    with self.assertRaisesRegex(ValueError,'^SOURCE_CLOSURE_MISMATCH$'):p.authenticate(root,env)

if __name__=='__main__':unittest.main()
