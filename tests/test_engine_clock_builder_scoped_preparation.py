"""Control and metadata fixtures; no target, namespace, policy or network execution."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from scripts import engine_clock_builder_scoped_preparation as b
except ImportError:b=None

ROOT=Path(__file__).resolve().parent.parent

class ScopedBuilderTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(b,'scoped builder02 adapter missing')
    def request(self):
        return {'schema':'builder-preparation-request-v2','request_id':'builder-20261113-02','repository':'rownlvh8875-coder/big-model-closed-loop-benchmark',
        'branch':'prepare/engine-clock-builder-20261113-02','workflow_path':'.github/workflows/engine-clock-builder-preparation-v2.yml','reviewed_source_sha':'1'*40,
        'budget':{'runs':1,'attempts':1,'builds':1,'probes':2,'profile_loads':1},'source_closure':{p:'0'*64 for p in b.CLOSURE},'inputs':b.prep.expected_inputs(ROOT)}
    def test_v2_only_request_and_closed_budgets(self):
        value=self.request();self.assertEqual(value,b.validate_request(value))
        for key,bad in [('request_id','builder-20261113-01'),('workflow_path','.github/workflows/engine-clock-builder-preparation.yml'),
                        ('budget',{'runs':1,'attempts':1,'builds':2,'probes':2,'profile_loads':1}),('source_closure',{'../SECRET': '0'*64}),('extra','SECRET')]:
            v=copy.deepcopy(value);v[key]=bad
            with self.assertRaisesRegex(ValueError,'^INVALID_REQUEST$'):b.validate_request(v)
        value['inputs'][0]['url']='https://SECRET_SENTINEL@github.com/a'
        with self.assertRaisesRegex(ValueError,'^INVALID_REQUEST$'):b.validate_request(value)
    def test_actual_qualified_support_record_and_mutations(self):
        value=json.loads((ROOT/b.SUPPORT).read_bytes());self.assertEqual(value,b.validate_support(value))
        for key,bad in [('status','BLOCKED'),('run_id',43416517415),('request_consumed',False),('after_validated',False),('model_execution',True)]:
            v=copy.deepcopy(value);v[key]=bad
            with self.assertRaisesRegex(ValueError,'^INVALID_SUPPORT$'):b.validate_support(v)
    def test_only_complete_supported_proof_is_admitted(self):
        current=json.loads((ROOT/b.SUPPORT).read_bytes())
        # Schema/provenance are separately validated; this predicate requires live step receipts.
        q={'status':'SUPPORTED_SCOPED_PROFILE','before':{'process':{'status':'EXITED','returncode':1},'validated':False},
           'profile_load':{'loaded':True,'process':{'status':'EXITED','returncode':0}},
           'after':{'validated':True,'process':{'status':'EXITED','returncode':0}}}
        self.assertTrue(b.supported(q))
        for bad in ({'status':'SUPPORTED_SCOPED_PROFILE'},{**q,'status':'BLOCKED'},{**q,'after':{'validated':False,'process':{'status':'EXITED','returncode':0}}}):self.assertFalse(b.supported(bad))
        self.assertTrue(b.supported({'status':'SUPPORTED_WITHOUT_PROFILE','before':{'validated':True,'process':{'status':'EXITED','returncode':0}},'profile_load':None,'after':None}))
    def test_candidate_argv_is_exact_sdk_except_private_executable(self):
        expected=b.prep.sandbox.launch_argv(10,11);expected[0]='/usr/local/libexec/stage7-bwrap'
        argv=b.private_launch_argv(10,11);self.assertEqual(expected,argv)
        self.assertEqual('/opt/hostedtoolcache/Python/3.11.18/x64/bin/python3.11',argv[argv.index('--')+1])
        self.assertNotIn('--ro-bind',argv)
    def test_probe_candidate_devices_must_be_distinct(self):
        self.assertTrue(b.independent_device(11,12));self.assertFalse(b.independent_device(11,11))
        for x,y in ((True,12),(0,12),(11,None)):self.assertFalse(b.independent_device(x,y))
    def test_unsupported_host_stops_before_transport_and_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'output/stage7-builder-preparation/builder-20261113-02';out.mkdir(parents=True)
            request=self.request()
            def failed(root,work,env,facts):facts.update(qualification={'status':'BLOCKED'},probe_device=11)
            with patch.object(b,'authenticate',return_value={}),patch.object(b.prep,'check_host_capacity'),patch.object(b,'qualify_host',side_effect=failed),patch.object(b.Path,'mkdir'),patch.object(b.prep,'download_input',side_effect=AssertionError('transport before admission')),patch.object(b.sandbox,'capture',side_effect=AssertionError('target before admission')):
                result=b.run_preparation(root,request,{})
            self.assertFalse(result['source_execution_attempted']);self.assertEqual([],result['transports']);self.assertEqual('FAILED_OR_INCOMPLETE',result['status'])
    def test_retention_roots_are_closed_and_include_separate_probe(self):
        roots=b.retention_roots()
        self.assertEqual({'workspace','build','probe-build','host-helper'},set(roots))
        self.assertEqual(Path('/tmp/engine-clock-build-builder-20261113-02'),roots['build'])
        self.assertEqual(Path('/tmp/engine-clock-build-builder-20261113-02-probe'),roots['probe-build'])
        self.assertNotIn(Path('/workspace'),roots.values());self.assertNotIn(Path('/tmp'),roots.values())
    def test_approved_candidate_plan_bytes_stay_exact(self):
        request=self.request();sources,payloads=b.prep.make_sources(ROOT,request);plan=b.prep.staging.compile_plan(sources);raw=b.prep.canonical(plan)
        self.assertEqual(51,len(request['inputs']));self.assertEqual(109285137,sum(r['nbytes'] for r in request['inputs']))
        self.assertEqual(52,len(sources));self.assertEqual('5371b2ba1e56fa15bc3068e8e579268b44f86091f7ed7a8e8d11fdb7a8c4838d',plan['plan_sha256'])
        self.assertEqual(8570595,len(raw));self.assertEqual('835121e2a4bb7e6996a94d1152209c5921f874d75454a19ee8c52b5189f85a25',hashlib.sha256(raw).hexdigest())

    def test_authenticate_uses_own_api_routes_support_and_exact_selected_pins(self):
        selected=copy.deepcopy(self.request()['inputs'])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in b.CLOSURE:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes((ROOT/name).read_bytes() if name in (b.SUPPORT,b.PROFILE) else b'fixture')
            request=self.request();request['source_closure']={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in b.CLOSURE}
            request_path=root/b.REQUEST_PATH;request_path.parent.mkdir(parents=True,exist_ok=True);request_path.write_bytes(b.canonical(request))
            prior={'sha':'3'*40,'truncated':False,'tree':[{'path':n,'type':'blob','mode':'100644','sha':b.prep.git_blob_sha((root/n).read_bytes())} for n in b.CLOSURE]}
            current=copy.deepcopy(prior);current['sha']='5'*40
            request_entry={'path':b.REQUEST_PATH,'type':'blob','mode':'100644','sha':b.prep.git_blob_sha(request_path.read_bytes())};current['tree'].append(request_entry)
            run={'id':123,'run_attempt':1,'head_sha':'2'*40,'head_branch':b.BRANCH,'event':'push','path':b.WORKFLOW,'repository':{'full_name':b.prep.REPOSITORY}}
            env={'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':b.prep.REPOSITORY,'GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':'2'*40,'GITHUB_RUN_ID':'123','GH_TOKEN':'SECRET_SENTINEL',
                 'GITHUB_REF':'refs/heads/'+b.BRANCH,'GITHUB_WORKFLOW_REF':b.prep.REPOSITORY+'/'+b.WORKFLOW+'@refs/heads/'+b.BRANCH,'GITHUB_WORKSPACE':str(root)}
            routes=[]
            def api(route,token):
                routes.append(route);base='/repos/'+b.prep.REPOSITORY
                mapping={base+'/actions/runs/123':run,
                    base+'/actions/workflows/engine-clock-builder-preparation-v2.yml/runs?branch=prepare%2Fengine-clock-builder-20261113-02&per_page=2':{'total_count':1,'workflow_runs':[run]},
                    base+'/git/commits/'+'2'*40:{'sha':'2'*40,'parents':[{'sha':'1'*40}],'tree':{'sha':'5'*40}},
                    base+'/git/commits/'+'1'*40:{'sha':'1'*40,'parents':[],'tree':{'sha':'3'*40}},
                    base+'/git/trees/'+'5'*40+'?recursive=1':current,base+'/git/trees/'+'3'*40+'?recursive=1':prior}
                self.assertIn(route,mapping,'unexpected API endpoint or commit-ish lookup');return mapping[route]
            with patch.object(b.prep,'api_json',side_effect=api),patch.object(b.prep,'expected_inputs',return_value=selected):
                self.assertEqual('2'*40,b.authenticate(root,request,env)['head_sha']);self.assertEqual(6,len(routes));routes.clear()
                env['GITHUB_RUN_ATTEMPT']='2'
                with self.assertRaisesRegex(ValueError,'^INVALID_REMOTE_ENVIRONMENT$'):b.authenticate(root,request,env)
                self.assertEqual([],routes);env['GITHUB_RUN_ATTEMPT']='1'
                request['inputs'][0]['sha256']='0'*64;request_path.write_bytes(b.canonical(request));request_entry['sha']=b.prep.git_blob_sha(request_path.read_bytes())
                with self.assertRaisesRegex(ValueError,'^INPUT_REGISTRATION_MISMATCH$'):b.authenticate(root,request,env)

    def test_retainer_rejects_unbound_context_before_reading_workspaces(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(b.retention,'preserve_workspaces',side_effect=AssertionError('retention before context')):
            with self.assertRaisesRegex(ValueError,'^INVALID_REMOTE_ENVIRONMENT$'):b.retain(Path(tmp),{})

if __name__=='__main__':unittest.main()
