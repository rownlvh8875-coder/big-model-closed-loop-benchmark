"""Deployed-layout regression with owned code and fake pip; no downloaded execution."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts import engine_clock_builder_build as old
from scripts import engine_clock_builder_driver as legacy
try:
 from scripts import engine_clock_builder_bound_build as h
 from scripts import engine_clock_builder_bound_preparation as b
except ImportError:h=b=None
ROOT=Path(__file__).resolve().parent.parent

class BuildBindingTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(h,'explicitly bound build helper missing')
 def layout(self,root):
  (root/'driver.py').write_bytes((ROOT/'scripts/engine_clock_builder_record_driver.py').read_bytes())
  (root/'legacy-driver.py').write_bytes((ROOT/'scripts/engine_clock_builder_driver.py').read_bytes())
  return str(root/'build.py')
 def test_deployed_old_fails_before_fake_pip_new_reaches_boundary(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);name=self.layout(root);original=lambda *a,**k:None;prepare=SimpleNamespace(unpack_url=original);calls=[]
   def pip(args):calls.append(args);return 0
   with patch.object(old,'__file__',name):
    with self.assertRaisesRegex(ValueError,'^SOURCE_PAYLOAD_MISMATCH$'):old.run_with_snapshots(prepare,pip,[],tmp_root=root,evidence_root=root)
   self.assertEqual([],calls);self.assertIs(original,prepare.unpack_url)
   with patch.object(h,'__file__',name):
    with self.assertRaisesRegex(ValueError,'^MISSING_SOURCE_UNPACK$'):h.run_with_snapshots(prepare,pip,[],tmp_root=root,evidence_root=root)
   self.assertEqual([legacy.pip_wheel_args()],calls);self.assertIs(original,prepare.unpack_url)
 def test_explicit_legacy_api_and_never_entry_fallback(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);name=self.layout(root)
   with patch.object(h,'__file__',name):
    module=h._driver();self.assertEqual(str(root/'legacy-driver.py'),module.__file__)
    for api in ('source_snapshot','_check_source_map','pip_wheel_args','validate_snapshots'):self.assertTrue(callable(getattr(module,api)))
    (root/'legacy-driver.py').write_text('def pip_wheel_args(): return []\n')
    with self.assertRaisesRegex(ValueError,'^UNSUPPORTED_OWNED_DRIVER$'):h._driver()
    (root/'legacy-driver.py').unlink()
    with self.assertRaises(FileNotFoundError):h._driver()
 def test_original_snapshot_source_hook_and_pip_logic_ast_identical(self):
  before=ast.parse(Path(old.__file__).read_text());after=ast.parse(Path(h.__file__).read_text());names={'_DigestText','_location','_write_manifest','run_with_snapshots'}
  subset=lambda tree:{n.name:ast.dump(n) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names}
  self.assertEqual(subset(before),subset(after));self.assertEqual(names,set(subset(after)))
 def test_fixed_source_failure_enum_and_evidence_write_failure_are_safe(self):
  for exc,code in [(ValueError('PIP_WHEEL_FAILED'),'PIP_WHEEL_FAILED'),(ValueError('UNSUPPORTED_OWNED_DRIVER'),'UNSUPPORTED_OWNED_DRIVER'),(RuntimeError('SECRET_SENTINEL'),'SOURCE_SNAPSHOT_FAILED')]:
   for fail in (False,True):
    with patch.object(h,'_write_manifest',side_effect=OSError('SECRET_WRITE') if fail else None) as write:
     row=h.record_failure(exc);self.assertEqual({'schema':'source-failure-v2','status':'FAILED','code':code},row);write.assert_called_once_with(Path('/build/source-failure.json'),row);self.assertNotIn('SECRET',json.dumps(row))
 def test_old_public_stdout_failure_wire_preserved(self):
  text=Path(h.__file__).read_text();self.assertIn('{"schema":"source-snapshot-failure-v1","code":"SOURCE_SNAPSHOT_FAILED"}',text)
  self.assertIn('record_failure(exc)',text);self.assertIn('--registered-pip-wheel-v1',text)

class BoundControllerTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(b,'v5 controller missing')
 def request(self):
  inputs=b.prep.expected_inputs(ROOT);sources,_=b.make_sources(ROOT,{'inputs':inputs});plan=b.staging.compile_plan(sources);raw=b.canonical(plan)
  return {'schema':'builder-preparation-request-v5','request_id':b.REQUEST_ID,'repository':b.prep.REPOSITORY,'branch':b.BRANCH,'workflow_path':b.WORKFLOW,'reviewed_source_sha':'1'*40,
          'budget':{'runs':1,'attempts':1,'builds':1,'probes':2,'profile_loads':1,'candidate_userns_assertions':1},'source_closure':{p:'0'*64 for p in b.CLOSURE},'inputs':inputs,
          'expected_plan':{'plan_sha256':plan['plan_sha256'],'serialized_sha256':hashlib.sha256(raw).hexdigest(),'nbytes':len(raw)}}
 def test_v5_closed_budget_identity_and_plan(self):
  req=self.request();self.assertEqual(req,b.validate_request(req))
  for key,value in [('request_id','builder-20261113-04'),('source_closure',{}),('extra','SECRET')]:
   r=copy.deepcopy(req);r[key]=value
   with self.assertRaisesRegex(ValueError,'^INVALID_REQUEST$'):b.validate_request(r)
  req['budget']['builds']=2
  with self.assertRaises(ValueError):b.validate_request(req)
 def test_only_owned_build_payload_changes_and_exact_new_plan(self):
  req=self.request();original,op=b.previous.make_sources(ROOT,req);new,np=b.make_sources(ROOT,req);self.assertEqual(original[:-1],new[:-1]);self.assertEqual(set(op),set(np))
  self.assertEqual({'run/builder/build.py'},{p for p in op if op[p]!=np[p]});self.assertEqual(51,len(req['inputs']));self.assertEqual(109285137,sum(x['nbytes'] for x in req['inputs']))
  b.verify_plan(b.staging.compile_plan(new),req);req['expected_plan']['serialized_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'^ROOT_PLAN_CHANGED$'):b.verify_plan(b.staging.compile_plan(new),req)
 def test_entry_namespace_tools_commands_argv_unchanged(self):
  self.assertEqual(b.previous.private_launch_argv(10,11),b.private_launch_argv(10,11));self.assertEqual('--registered-builder-v3',b.private_launch_argv(10,11)[-1])
 def test_new_workflow_and_retention_binding(self):
  wf=json.loads((ROOT/b.WORKFLOW).read_bytes());self.assertEqual([b.BRANCH],wf['on']['push']['branches']);self.assertIn('--guard-only',wf['jobs']['prepare']['steps'][2]['run']);self.assertIn('always()',wf['jobs']['prepare']['steps'][-2]['if'])
  self.assertEqual({'workspace','build','probe-build','host-helper'},set(b.retention_roots()));self.assertEqual(Path('/tmp/engine-clock-build-builder-20261113-05'),b.retention_roots()['build'])
  with patch.object(b.retention,'preserve_workspaces',side_effect=AssertionError('before binding')):
   with self.assertRaisesRegex(ValueError,'^INVALID_REMOTE_ENVIRONMENT$'):b.retain(ROOT,{})

class FullGuardTests(unittest.TestCase):
    request=BoundControllerTests.request
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
                    base+'/actions/workflows/engine-clock-builder-preparation-v5.yml/runs?branch=prepare%2Fengine-clock-builder-20261113-05&per_page=2':{'total_count':1,'workflow_runs':[run]},
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
