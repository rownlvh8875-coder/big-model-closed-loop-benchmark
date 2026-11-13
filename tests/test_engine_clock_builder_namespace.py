"""Namespace property fixtures. Never invoke live unshare, target or policy."""
import copy
import errno
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from scripts import engine_clock_builder_namespace as n
    from scripts import engine_clock_builder_namespace_driver as d
    from scripts import engine_clock_builder_namespace_preparation as b
except ImportError:n=d=b=None
ROOT=Path(__file__).resolve().parent.parent


def valid():
    return {'schema':'builder-namespace-proof-v1','python':{'version':[3,11,18],'isolated':True,'no_site':True,'dont_write_bytecode':True},
            'uid':0,'gid':0,'readonly':{p:True for p in ('/','/proc','/dev','/dev/pts')},
            'build':{'bytes':268435456,'readonly':False,'tmpfs':True},'visible_userns_limit':62983,
            'capabilities':{k:0 for k in ('CapEff','CapPrm','CapInh','CapAmb','CapBnd')},
            'network':{'interfaces_present':False,'interface_count':None,'only_loopback':None,'route_lines':1},
            'errors':[],'additional_userns':{'status':'RETURNED','returncode':-1,'errno':errno.ENOSPC}}


class FakeBackend:
    def __init__(self,initial=None,answer=(-1,errno.ENOSPC)):
        self.initial=copy.deepcopy(initial or valid());self.answer=answer;self.calls=0
    def collect_initial(self,facts):
        facts.update(copy.deepcopy(self.initial));facts['additional_userns']={'status':'NOT_RUN','returncode':None,'errno':None}
    def unshare(self):self.calls+=1;return self.answer


class NamespaceTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(n,'owned proof module missing')
    def test_large_child_visible_limit_accepts_only_actual_denial(self):
        backend=FakeBackend();facts={};n.collect(facts,backend);self.assertEqual(facts,n.validate(facts));self.assertEqual(1,backend.calls)
        self.assertEqual(62983,facts['visible_userns_limit'])
    def test_small_limit_does_not_substitute_for_denial(self):
        initial=valid();initial['visible_userns_limit']=1
        backend=FakeBackend(initial,(0,0));facts={};n.collect(facts,backend)
        self.assertEqual(0,facts['additional_userns']['returncode']);self.assertEqual(1,backend.calls)
        with self.assertRaisesRegex(ValueError,'^UNSUPPORTED_NAMESPACE$'):n.validate(facts)
    def test_initial_violations_block_assertion_and_preserve_facts(self):
        mutations=[('uid',1),('readonly',{'/':False,'/proc':True,'/dev':True,'/dev/pts':True}),
            ('build',{'bytes':268435457,'readonly':False,'tmpfs':True}),('build',{'bytes':1,'readonly':False,'tmpfs':False}),
            ('capabilities',{**valid()['capabilities'],'CapBnd':1}),('network',{'interfaces_present':True,'interface_count':2,'only_loopback':False,'route_lines':2}),
            ('python',{'version':[3,11,17],'isolated':True,'no_site':True,'dont_write_bytecode':True}),('visible_userns_limit',None)]
        for key,value in mutations:
            with self.subTest(key=key,value=value):
                initial=valid();initial[key]=value;backend=FakeBackend(initial);facts={};n.collect(facts,backend)
                self.assertEqual(0,backend.calls);self.assertEqual(value,facts[key]);n.validate_shape(facts)
                with self.assertRaises(ValueError):n.validate(facts)
    def test_unshare_error_and_wrong_errno_are_not_proof(self):
        for answer in ((-1,errno.EINVAL),(-1,0),(1,0),(True,1)):
            backend=FakeBackend(answer=answer);facts={};n.collect(facts,backend)
            with self.assertRaises(ValueError):n.validate(facts)
    def test_partial_collection_survives_and_is_fail_closed(self):
        class Broken:
            def collect_initial(self,facts):facts['uid']=0;raise OSError('SECRET_SENTINEL')
            def unshare(self):raise AssertionError('unsafe assertion')
        facts={};n.collect(facts,Broken());n.validate_shape(facts)
        self.assertEqual(0,facts['uid']);self.assertNotIn('SECRET',json.dumps(facts));self.assertTrue(facts['errors'])
        with self.assertRaises(ValueError):n.validate(facts)
    def test_unknown_fields_and_untyped_values_rejected(self):
        for key,value in (('extra','SECRET'),('uid',True),('visible_userns_limit','1'),('errors',['SECRET'])):
            facts=valid();facts[key]=value
            with self.assertRaisesRegex(ValueError,'^INVALID_NAMESPACE_FACTS$'):n.validate_shape(facts)
    def test_typed_libc_boundary_resets_errno_and_uses_exact_flag(self):
        class Fn:
            def __call__(self,flag):self.flag=flag;return -1
        class Lib:unshare=Fn()
        lib=Lib()
        with patch.object(n.ctypes,'CDLL',return_value=lib) as load,patch.object(n.ctypes,'set_errno') as reset,patch.object(n.ctypes,'get_errno',return_value=28):
            self.assertEqual((-1,28),n.LiveBackend().unshare())
        load.assert_called_once_with(None,use_errno=True);reset.assert_called_once_with(0)
        self.assertEqual([n.ctypes.c_int],lib.unshare.argtypes);self.assertIs(n.ctypes.c_int,lib.unshare.restype);self.assertEqual(0x10000000,lib.unshare.flag)
    def test_driver_rejects_before_legacy_load_or_package_steps(self):
        facts=valid();facts['uid']=1
        class Proof:
            @staticmethod
            def collect(dest):dest.update(facts)
            validate=staticmethod(lambda dest:n.validate(dest))
        with patch.object(d,'load_owned',return_value=Proof) as load,patch.object(d,'run_stages',side_effect=AssertionError('package before namespace')):
            wire,rc=d.execute();self.assertEqual(1,rc);self.assertEqual([],wire['result']['steps']);self.assertEqual(1,wire['namespace']['uid']);self.assertEqual(1,load.call_count)
    def test_all_legacy_stage_operations_preserved_structurally(self):
        import ast
        from scripts import engine_clock_builder_driver as old
        legacy=ast.parse(Path(old.__file__).read_text())
        original=next(node for node in legacy.body if isinstance(node,ast.FunctionDef) and node.name=='main')
        original_try=next(node for node in original.body if isinstance(node,ast.Try))
        start=next(i for i,node in enumerate(original_try.body) if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='helper_spec' for t in node.targets))
        original_body=original_try.body[start:]
        class BindLegacy(ast.NodeTransformer):
            def visit_Name(self,node):
                if node.id in ('BASE','VENV','OUTPUT','commands','verify_tools','validate_snapshots'):
                    return ast.Attribute(value=ast.Name(id='legacy',ctx=ast.Load()),attr=node.id,ctx=node.ctx)
                return node
        expected=[BindLegacy().visit(node) for node in original_body]
        adapter=ast.parse(Path(d.__file__).read_text())
        actual=next(node for node in adapter.body if isinstance(node,ast.FunctionDef) and node.name=='run_stages').body[1:-1]
        self.assertEqual([ast.dump(node) for node in expected],[ast.dump(node) for node in actual])

    def test_stage_commands_are_legacy_and_core_schema_preserved(self):
        from scripts import engine_clock_builder_driver as old
        self.assertIn('legacy.commands().items()',Path(d.__file__).read_text())
        self.assertEqual(['VENV','ENSUREPIP','TOOLS','BUILD','SMOKE'],list(old.commands()))
        self.assertNotIn('_namespace_checks()',Path(d.__file__).read_text())


class NamespaceControllerTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(b,'v3 controller missing')
    def request(self):
        sources,_=b.make_sources(ROOT,{'inputs':b.prep.expected_inputs(ROOT)});plan=b.staging.compile_plan(sources);raw=b.canonical(plan)
        return {'schema':'builder-preparation-request-v3','request_id':b.REQUEST_ID,'repository':b.prep.REPOSITORY,'branch':b.BRANCH,'workflow_path':b.WORKFLOW,
            'reviewed_source_sha':'1'*40,'budget':{'runs':1,'attempts':1,'builds':1,'probes':2,'profile_loads':1,'candidate_userns_assertions':1},
            'source_closure':{p:'0'*64 for p in b.CLOSURE},'inputs':b.prep.expected_inputs(ROOT),
            'expected_plan':{'plan_sha256':plan['plan_sha256'],'serialized_sha256':hashlib.sha256(raw).hexdigest(),'nbytes':len(raw)}}
    def test_unsupported_host_stops_before_transport_and_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'output/stage7-builder-preparation/builder-20261113-03';out.mkdir(parents=True)
            request=self.request()
            def failed(root,work,env,facts):facts.update(qualification={'status':'BLOCKED'},probe_device=11)
            with patch.object(b,'authenticate',return_value={}),patch.object(b.prep,'check_host_capacity'),patch.object(b,'qualify_host',side_effect=failed),patch.object(b.Path,'mkdir'),patch.object(b.prep,'download_input',side_effect=AssertionError('transport before admission')),patch.object(b.sandbox,'capture',side_effect=AssertionError('target before admission')):
                result=b.run_preparation(root,request,{})
            self.assertFalse(result['source_execution_attempted']);self.assertEqual([],result['transports']);self.assertEqual('FAILED_OR_INCOMPLETE',result['status'])
    def test_closed_request_budgets_and_new_plan(self):
        value=self.request();self.assertEqual(value,b.validate_request(value))
        for key,bad in [('request_id','builder-20261113-02'),('expected_plan',{'plan_sha256':'0'*64}),('extra','SECRET')]:
            v=copy.deepcopy(value);v[key]=bad
            with self.assertRaisesRegex(ValueError,'^INVALID_REQUEST$'):b.validate_request(v)
        value['budget']['candidate_userns_assertions']=2
        with self.assertRaises(ValueError):b.validate_request(value)
    def test_every_third_party_source_and_legacy_payload_unchanged(self):
        request=self.request();old,op=b.prep.make_sources(ROOT,request);new,np=b.make_sources(ROOT,request)
        self.assertEqual(old[:-1],new[:-1]);self.assertEqual(51,len(request['inputs']));self.assertEqual(109285137,sum(r['nbytes'] for r in request['inputs']))
        for p,raw in op.items():self.assertEqual(raw,np['run/builder/legacy-driver.py' if p=='run/builder/driver.py' else p])
        self.assertNotEqual(op['run/builder/driver.py'],np['run/builder/driver.py']);self.assertIn('run/builder/namespace.py',np)
        self.assertNotEqual('5371b2ba1e56fa15bc3068e8e579268b44f86091f7ed7a8e8d11fdb7a8c4838d',request['expected_plan']['plan_sha256'])
        b.verify_plan(b.staging.compile_plan(new),request)
        request['expected_plan']['serialized_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'^ROOT_PLAN_CHANGED$'):b.verify_plan(b.staging.compile_plan(new),request)
    def test_candidate_argv_keeps_fds_and_all_security_options(self):
        expected=b.sandbox.launch_argv(10,11);expected[0]=b.HELPER;expected[-1]='--registered-builder-v2'
        self.assertEqual(expected,b.private_launch_argv(10,11));self.assertNotIn('--ro-bind',expected)
    def test_safe_failure_envelope_retains_partial_namespace(self):
        facts=valid();facts['readonly']['/proc']=False
        core={'schema':'builder-driver-failure-v1','status':'FAILED','code':'UNSUPPORTED_NAMESPACE','steps':[]}
        raw=json.dumps({'schema':'builder-driver-envelope-v2','namespace':facts,'result':core}).encode()
        proof,core_raw=b.decode_envelope(raw);self.assertFalse(proof['readonly']['/proc']);self.assertEqual('UNSUPPORTED_NAMESPACE',b.sandbox.failure_code(core_raw))
        for value in ({'schema':'bad','namespace':facts,'result':core},{'schema':'builder-driver-envelope-v2','namespace':{**facts,'extra':'SECRET'},'result':core}):
            with self.assertRaisesRegex(ValueError,'^INVALID_DRIVER_WIRE$'):b.decode_envelope(json.dumps(value).encode())
    def test_retention_valid_context_delegates_exact_closed_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);env={'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':b.prep.REPOSITORY,'GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':'2'*40,'GITHUB_RUN_ID':'123','GH_TOKEN':'SECRET',
                'GITHUB_REF':'refs/heads/'+b.BRANCH,'GITHUB_WORKFLOW_REF':b.prep.REPOSITORY+'/'+b.WORKFLOW+'@refs/heads/'+b.BRANCH,'GITHUB_WORKSPACE':str(root)}
            with patch.object(b.retention,'preserve_workspaces',return_value={'status':'fixture'}) as retain,patch.object(b,'perf_counter',return_value=10):
                self.assertEqual({'status':'fixture'},b.retain(root,env))
                retain.assert_called_once_with(b.retention_roots(),root/'output/stage7-builder-preparation'/b.REQUEST_ID,deadline=190)
            self.assertEqual({'workspace','build','probe-build','host-helper'},set(b.retention_roots()))
    def test_workflow_one_use_and_bounded_always_retention(self):
        wf=json.loads((ROOT/b.WORKFLOW).read_bytes());self.assertEqual([b.BRANCH],wf['on']['push']['branches']);steps=wf['jobs']['prepare']['steps']
        self.assertIn('--guard-only',steps[2]['run']);self.assertIn('--retain',steps[-2]['run']);self.assertIn('always()',steps[-2]['if']);self.assertNotIn('pull_request',wf['on'])

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
                    base+'/actions/workflows/engine-clock-builder-preparation-v3.yml/runs?branch=prepare%2Fengine-clock-builder-20261113-03&per_page=2':{'total_count':1,'workflow_runs':[run]},
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

if __name__=='__main__':unittest.main()
