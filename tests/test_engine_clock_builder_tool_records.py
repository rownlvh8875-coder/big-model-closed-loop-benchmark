"""Owned fixture wheels only; no downloaded code, package builds or namespaces."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from scripts import engine_clock_builder_driver as legacy
try:
 from scripts import engine_clock_builder_tool_records as t
 from scripts import engine_clock_builder_record_preparation as b
except ImportError:t=b=None
ROOT=Path(__file__).resolve().parent.parent

class ToolRecordsTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(t,'owned original-RECORD verifier missing')
 def fixture(self,root):
  rows={'tool.py':b'x=1\n','tool-1.dist-info/METADATA':b'Name: tool\nVersion: 1\n','tool-1.dist-info/RECORD':b'old top record',
        'tool/vendor/dependency-2.dist-info/RECORD':b'original nested RECORD', 'tool/vendor/dependency-2.dist-info/METADATA':b'original vendor metadata'}
  wheel=root/'tool.whl';site=root/'site';site.mkdir()
  with zipfile.ZipFile(wheel,'w') as z:
   for p,raw in rows.items():
    z.writestr(p,raw);path=site/p;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
  (site/'tool-1.dist-info/RECORD').write_bytes(b'new installed record')
  (site/'tool-1.dist-info/INSTALLER').write_bytes(b'pip\n')
  return wheel,site
 def verify(self,site,wheel):return t.verify_tools(site,[wheel],snapshotter=legacy._snapshot,magic=importlib.util.MAGIC_NUMBER)
 def test_original_nested_record_is_payload_not_generated_metadata(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);wheel,site=self.fixture(root);result=self.verify(site,wheel)
   self.assertEqual(4,result['payload_files']);self.assertEqual(6,result['installed_files'])
   with self.assertRaisesRegex(ValueError,'^TOOL_PAYLOAD_MISMATCH$'):legacy.verify_tools(site,[wheel])
 def test_changed_or_missing_nested_record_rejected(self):
  for changed in (False,True):
   with tempfile.TemporaryDirectory() as tmp:
    wheel,site=self.fixture(Path(tmp));p=site/'tool/vendor/dependency-2.dist-info/RECORD'
    if changed:p.write_bytes(b'tampered')
    else:p.unlink()
    with self.assertRaisesRegex(ValueError,'^TOOL_PAYLOAD_MISMATCH$'):self.verify(site,wheel)
 def test_unknown_vendor_generated_metadata_and_arbitrary_file_rejected(self):
  for p in ('tool/vendor/dependency-2.dist-info/INSTALLER','evil.dist-info/RECORD','evil.py'):
   with tempfile.TemporaryDirectory() as tmp:
    wheel,site=self.fixture(Path(tmp));path=site/p;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'unknown')
    with self.assertRaisesRegex(ValueError,'^TOOL_PAYLOAD_MISMATCH$'):self.verify(site,wheel)
 def test_pyc_requires_source_and_matching_magic(self):
  with tempfile.TemporaryDirectory() as tmp:
   wheel,site=self.fixture(Path(tmp));cache=site/'__pycache__';cache.mkdir();p=cache/'tool.cpython-311.pyc';p.write_bytes(importlib.util.MAGIC_NUMBER+b'fixture')
   self.verify(site,wheel);p.write_bytes(b'BAD!')
   with self.assertRaises(ValueError):self.verify(site,wheel)
   p.unlink();(cache/'unknown.cpython-311.pyc').write_bytes(importlib.util.MAGIC_NUMBER)
   with self.assertRaises(ValueError):self.verify(site,wheel)
 def test_duplicate_and_unsafe_wheel_members_rejected(self):
  for name in ('tool.py','../SECRET','/absolute'):
   with tempfile.TemporaryDirectory() as tmp:
    wheel,site=self.fixture(Path(tmp))
    with zipfile.ZipFile(wheel,'a') as z:z.writestr(name,b'bad')
    with self.assertRaisesRegex(ValueError,'^TOOL_PAYLOAD_MISMATCH$'):self.verify(site,wheel)

class RecordControllerTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(b,'v4 preparation missing')
 def request(self):
  inputs=b.prep.expected_inputs(ROOT);sources,_=b.make_sources(ROOT,{'inputs':inputs});plan=b.staging.compile_plan(sources);raw=b.canonical(plan)
  return {'schema':'builder-preparation-request-v4','request_id':b.REQUEST_ID,'repository':b.prep.REPOSITORY,'branch':b.BRANCH,'workflow_path':b.WORKFLOW,'reviewed_source_sha':'1'*40,
          'budget':{'runs':1,'attempts':1,'builds':1,'probes':2,'profile_loads':1,'candidate_userns_assertions':1},'source_closure':{p:'0'*64 for p in b.CLOSURE},'inputs':inputs,
          'expected_plan':{'plan_sha256':plan['plan_sha256'],'serialized_sha256':hashlib.sha256(raw).hexdigest(),'nbytes':len(raw)}}
 def receipt(self):return {'stage':'VENV','status':'EXITED','returncode':0,'stdout_bytes':0,'stderr_bytes':0,'stdout_sha256':hashlib.sha256(b'').hexdigest(),'stderr_sha256':hashlib.sha256(b'').hexdigest()}
 def test_closed_v4_identity_budget_and_plan(self):
  r=self.request();self.assertEqual(r,b.validate_request(r))
  for key,bad in [('request_id','builder-20261113-03'),('source_closure',{}),('extra','SECRET')]:
   v=copy.deepcopy(r);v[key]=bad
   with self.assertRaisesRegex(ValueError,'^INVALID_REQUEST$'):b.validate_request(v)
  r['budget']['builds']=2
  with self.assertRaises(ValueError):b.validate_request(r)
 def test_original_sources_and_owned_payload_parity_and_new_plan(self):
  req=self.request();old,op=b.previous.make_sources(ROOT,req);new,np=b.make_sources(ROOT,req);self.assertEqual(old[:-1],new[:-1])
  for p,raw in op.items():
   if p!='run/builder/driver.py':self.assertEqual(raw,np[p])
  self.assertIn('run/builder/toolcheck.py',np);self.assertEqual(51,len(req['inputs']));self.assertEqual(109285137,sum(x['nbytes'] for x in req['inputs']))
  b.verify_plan(b.staging.compile_plan(new),req);req['expected_plan']['plan_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'^ROOT_PLAN_CHANGED$'):b.verify_plan(b.staging.compile_plan(new),req)
 def test_closed_failure_steps_are_reconstructable(self):
  core={'schema':'builder-driver-failure-v1','status':'FAILED','code':'TOOL_PAYLOAD_MISMATCH','steps':[self.receipt()]};raw=(json.dumps(core,sort_keys=True,separators=(',',':'))+'\n').encode()
  self.assertEqual(core,b.decode_failure(raw));self.assertEqual(raw,b.compact(b.decode_failure(raw)))
  for steps in ([{**self.receipt(),'extra':'SECRET'}],[{**self.receipt(),'stage':'BUILD'}],[{**self.receipt(),'status':'SECRET'}],[{**self.receipt(),'stdout_bytes':True}]):
   v={**core,'steps':steps}
   with self.assertRaisesRegex(ValueError,'^INVALID_DRIVER_WIRE$'):b.decode_failure(json.dumps(v).encode())
 def test_bounded_failure_read_overshoot_retained_and_reconstructed(self):
  for stream,limit in (('stdout',3145728),('stderr',1048576)):
   for status in ('OUTPUT_LIMIT','CLEANUP_FAILED','TRANSPORT_FAILED','TIMEOUT'):
    with self.subTest(stream=stream,status=status):
     row={**self.receipt(),'status':status,'returncode':-9,stream+'_bytes':limit+65536}
     core={'schema':'builder-driver-failure-v1','status':'FAILED','code':'COMMAND_FAILED','steps':[row]}
     raw=b.compact(core);self.assertEqual(core,b.decode_failure(raw));self.assertEqual(raw,b.compact(b.decode_failure(raw)))
     row[stream+'_bytes']+=1
     with self.assertRaisesRegex(ValueError,'^INVALID_DRIVER_WIRE$'):b.decode_failure(b.compact(core))
     row[stream+'_bytes']=limit+1;row['status']='EXITED'
     with self.assertRaisesRegex(ValueError,'^INVALID_DRIVER_WIRE$'):b.decode_failure(b.compact(core))

 def test_driver_and_argv_keep_namespace_and_commands(self):
  expected=b.sandbox.launch_argv(10,11);expected[0]=b.HELPER;expected[-1]='--registered-builder-v3';self.assertEqual(expected,b.private_launch_argv(10,11))
  text=(ROOT/'scripts/engine_clock_builder_record_driver.py').read_text();self.assertIn('proof.collect(facts);proof.validate(facts)',text);self.assertIn('legacy.commands().items()',text);self.assertNotIn('legacy.verify_tools(',text);self.assertEqual(2,text.count('toolcheck.verify_tools('))
 def test_stage_ast_parity_except_explicit_checker_dependency(self):
  import ast
  old=ast.parse((ROOT/'scripts/engine_clock_builder_namespace_driver.py').read_text());new=ast.parse((ROOT/'scripts/engine_clock_builder_record_driver.py').read_text())
  oldfun=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='run_stages');newfun=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='run_stages')
  class Normalize(ast.NodeTransformer):
   def visit_Call(self,node):
    self.generic_visit(node)
    if isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='toolcheck' and node.func.attr=='verify_tools':
     node.func.value.id='legacy';node.keywords=[]
    return node
  self.assertEqual([ast.dump(n) for n in oldfun.body],[ast.dump(Normalize().visit(n)) for n in newfun.body])
 def test_workflow_fixed_new_request_and_retention_context(self):
  wf=json.loads((ROOT/b.WORKFLOW).read_bytes());self.assertEqual([b.BRANCH],wf['on']['push']['branches']);self.assertIn('--guard-only',wf['jobs']['prepare']['steps'][2]['run']);self.assertIn('always()',wf['jobs']['prepare']['steps'][-2]['if'])
  self.assertEqual({'workspace','build','probe-build','host-helper'},set(b.retention_roots()));self.assertEqual(Path('/tmp/engine-clock-build-builder-20261113-04'),b.retention_roots()['build'])
  with patch.object(b.retention,'preserve_workspaces',side_effect=AssertionError('before binding')):
   with self.assertRaisesRegex(ValueError,'^INVALID_REMOTE_ENVIRONMENT$'):b.retain(ROOT,{})

class FullGuardTests(unittest.TestCase):
    request=RecordControllerTests.request
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
                    base+'/actions/workflows/engine-clock-builder-preparation-v4.yml/runs?branch=prepare%2Fengine-clock-builder-20261113-04&per_page=2':{'total_count':1,'workflow_runs':[run]},
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
