"""No real policy load or namespace operation; controlled host-boundary fixtures."""
import copy
import unittest
import io
import json
import types
import contextlib
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import patch

try:
    from scripts import engine_clock_bwrap_profile_preflight as p
except ImportError:p=None


class Backend:
    def __init__(self,before,after=None,eligible=True,loaded=True):
        self.b,self.a,self.e,self.l,self.calls=before,after,eligible,loaded,[]
    def baseline(self):self.calls.append('before');return self.b
    def eligible(self):self.calls.append('eligible');return self.e
    def load(self):self.calls.append('load');return {'loaded':self.l}
    def after(self):self.calls.append('after');return self.a


class ProfileTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(p,'scoped bwrap preflight missing')
    def failed(self,hash=None):
        return {'validated':False,'process':{'status':'EXITED','returncode':1,'stderr_bytes':61,'stderr_sha256':hash or 'ed3471f7900377f86150471417911309833a36d664cb5af7409e139103f67ddf'}}
    def test_ready_baseline_never_loads_profile(self):
        b=Backend({'validated':True,'process':{'status':'EXITED','returncode':0}})
        r=p.qualify(b);self.assertEqual('SUPPORTED_WITHOUT_PROFILE',r['status']);self.assertEqual(['before'],b.calls)
    def test_known_block_loads_once_then_qualifies(self):
        b=Backend(self.failed(),{'validated':True,'process':{'status':'EXITED','returncode':0}})
        r=p.qualify(b);self.assertEqual('SUPPORTED_SCOPED_PROFILE',r['status']);self.assertEqual(['before','eligible','load','after'],b.calls)
    def test_unrelated_error_or_invalid_success_never_loads_policy(self):
        for before in (self.failed('0'*64),{'validated':False,'process':{'status':'EXITED','returncode':0}}, {'validated':False,'process':{'status':'TIMEOUT','returncode':None}}):
            b=Backend(before);self.assertEqual('BLOCKED',p.qualify(b)['status']);self.assertEqual(['before'],b.calls)
    def test_missing_preconditions_never_loads(self):
        b=Backend(self.failed(),eligible=False);self.assertEqual('BLOCKED',p.qualify(b)['status']);self.assertEqual(['before','eligible'],b.calls)
    def test_parser_failure_and_failed_after_do_not_retry(self):
        b=Backend(self.failed(),loaded=False);self.assertEqual('BLOCKED',p.qualify(b)['status']);self.assertEqual(['before','eligible','load'],b.calls)
        b=Backend(self.failed(),self.failed());self.assertEqual('BLOCKED',p.qualify(b)['status']);self.assertEqual(['before','eligible','load','after'],b.calls)
    def observation(self):
        names=('user','net','mnt','pid','ipc','uts')
        host={n:n+':[10]' for n in names}
        value={'namespaces':{n:n+':[20]' for n in names},'uid':0,'gid':0,
        'caps':{n:'0000000000000000' for n in ('CapEff','CapPrm','CapInh','CapAmb','CapBnd')},
        'env_keys':['LANG','LC_ALL','PATH','PIP_CONFIG_FILE','PIP_NO_COMPILE','PYTHONDONTWRITEBYTECODE','PYTHONHASHSEED','SOURCE_DATE_EPOCH','TMPDIR','TZ'],
        'root_write_errno':30,'build_write':True,'profile':'stage7-bwrap (unconfined)'}
        return host,value
    def test_observation_requires_changed_namespaces_zero_caps_closed_env_and_io_proof(self):
        host,value=self.observation();self.assertEqual(value,p.validate_observation(value,host,after=True))
        for case in ('namespace','uid','caps','env','root','build','profile','extra'):
            v=copy.deepcopy(value)
            if case=='namespace':v['namespaces']['net']='net:[10]'
            elif case=='uid':v['uid']=1001
            elif case=='caps':v['caps']['CapEff']='0000000000001000'
            elif case=='env':v['env_keys'].append('GH_TOKEN')
            elif case=='root':v['root_write_errno']=13
            elif case=='build':v['build_write']=False
            elif case=='profile':v['profile']='unconfined'
            else:v['extra']='SECRET_SENTINEL'
            with self.subTest(case=case),self.assertRaisesRegex(ValueError,'^INVALID_PROBE_OBSERVATION$'):p.validate_observation(v,host,after=True)
    def test_command_keeps_strict_flags_and_both_bound_descriptors(self):
        argv=p.probe_argv(10,11)
        self.assertEqual('/usr/local/libexec/stage7-bwrap',argv[0])
        self.assertEqual('10',argv[argv.index('--ro-bind-fd')+1]);self.assertEqual('11',argv[argv.index('--bind-fd')+1])
        for flag in ('--unshare-user','--unshare-net','--unshare-pid','--unshare-ipc','--unshare-uts','--disable-userns','--assert-userns-disabled','--cap-drop','--clearenv'):self.assertIn(flag,argv)
        self.assertEqual('/usr/bin/python3',argv[argv.index('--')+1])
        self.assertNotIn('GH_TOKEN',argv)
    def test_trusted_observer_marks_complete_literal_write_without_host_io(self):
        host,value=self.observation()
        fake=types.SimpleNamespace(environ={k:'' for k in value['env_keys']},getuid=lambda:0,getgid=lambda:0,
              readlink=lambda path:value['namespaces'][path.rsplit('/',1)[-1]],O_WRONLY=1,O_CREAT=64,O_EXCL=128,
              close=lambda fd:None,write=lambda fd,data:len(data))
        def osopen(path,flags,mode):
            if path=='/probe-root-write-forbidden':raise OSError(30,'fixture')
            self.assertEqual('/build/probe-marker',path);return 10
        fake.open=osopen
        def opened(path,*args,**kwargs):
            if path=='/proc/self/status':return io.StringIO(''.join(k+': 0000000000000000\n' for k in value['caps']))
            self.assertEqual('/proc/self/attr/current',path);return io.BytesIO(b'stage7-bwrap (unconfined)\n')
        output=io.StringIO()
        with patch.dict('sys.modules',{'os':fake}),patch('builtins.open',side_effect=opened),contextlib.redirect_stdout(output):
            exec(compile(p.OBSERVER,'trusted-observer','exec'),{})
        observation=json.loads(output.getvalue())
        self.assertTrue(observation['build_write'],'complete actual payload write must be accepted')
        self.assertEqual(observation,p.validate_observation(observation,host,after=True))

    def test_authenticate_uses_actual_tree_shas_and_rejects_attempt_source_and_run_mutations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in p.CLOSURE:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
            request={'schema':'namespace-profile-request-v1','request_id':p.REQUEST_ID,'repository':p.prep.REPOSITORY,'branch':p.BRANCH,'workflow_path':p.WORKFLOW,
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
                  base+'/actions/workflows/engine-clock-bwrap-profile-preflight.yml/runs?branch=diagnose%2Fengine-clock-namespace-20261113-03&per_page=2':{'total_count':1,'workflow_runs':[run]},
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

    def test_new_request_only_activation_rejects_old_ids_and_unrelated_delta(self):
        d={'schema':'namespace-profile-request-v1','request_id':'namespace-diagnostic-20261113-03','repository':'rownlvh8875-coder/big-model-closed-loop-benchmark',
        'branch':'diagnose/engine-clock-namespace-20261113-03','workflow_path':'.github/workflows/engine-clock-bwrap-profile-preflight.yml','reviewed_source_sha':'1'*40,
        'budget':{'runs':1,'attempts':1,'probes':2,'profile_loads':1},'source_closure':{x:'0'*64 for x in p.CLOSURE}}
        self.assertEqual(d,p.validate_request(d))
        for key,value in [('request_id','namespace-diagnostic-20261113-02'),('budget',{'runs':1,'attempts':1,'probes':3,'profile_loads':1}),('extra','SECRET_SENTINEL')]:
            v=copy.deepcopy(d);v[key]=value
            with self.assertRaisesRegex(ValueError,'^INVALID_REQUEST$'):p.validate_request(v)
        before={'truncated':False,'tree':[]};after={'sha':'3'*40,'truncated':False,'tree':[{'path':p.REQUEST_PATH,'type':'blob','mode':'100644','sha':'4'*40}]};commit={'sha':'2'*40,'parents':[{'sha':'1'*40}],'tree':{'sha':'3'*40}}
        self.assertIsNone(p.validate_activation(d,'2'*40,after,before,commit))
        after['tree'].append({'path':'unexpected','type':'blob','mode':'100644','sha':'5'*40})
        with self.assertRaisesRegex(ValueError,'^INVALID_ACTIVATION$'):p.validate_activation(d,'2'*40,after,before,commit)

if __name__=='__main__':unittest.main()
