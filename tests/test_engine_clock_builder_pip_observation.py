"""Safe diagnostic composition with owned code/fake pip, no target or namespace calls."""
import copy
import hashlib
import io
import json
import logging
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts import engine_clock_builder_bound_build as bound
try:
 from scripts import engine_clock_builder_pip_observation as o
 from scripts import engine_clock_builder_observed_build as h
 from scripts import engine_clock_builder_observed_preparation as b
except ImportError:o=h=b=None
ROOT=Path(__file__).resolve().parent.parent

class ObservationTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(o,'safe pip observer missing')
 def context(self):return (Path('/fixture/site'),{'pip/_internal/cli/base_command.py'},{ValueError:'builtin.ValueError',OSError:'builtin.OSError'})
 def test_prepare_proxy_records_fixed_failure_and_restores_original(self):
  original=lambda *a,**k:'original';real=SimpleNamespace(unpack_url=original);f=o.empty();proxy=o.PrepareProxy(real,f,types=self.context()[2]);seen=[]
  def hook(*args,**kwargs):seen.append(args);raise ValueError('SOURCE_LOCATION_MISMATCH')
  proxy.unpack_url=hook
  with self.assertRaisesRegex(ValueError,'^SOURCE_LOCATION_MISMATCH$'):real.unpack_url('link','/build/tmp/pip-wheel-x/progressbar_'+'a'*32)
  self.assertEqual(1,f['unpack_calls']);self.assertEqual('SOURCE_LOCATION_MISMATCH',f['hook_error_code']);self.assertEqual('builtin.ValueError',f['hook_exception_code']);self.assertTrue(f['location']['matches_owned_pattern'])
  proxy.unpack_url=original;self.assertIs(original,real.unpack_url);o.validate(f,members=self.context()[1])
 def test_hook_result_and_unknown_exception_text_never_serialized(self):
  original=lambda *a,**k:None;real=SimpleNamespace(unpack_url=original);f=o.empty();proxy=o.PrepareProxy(real,f,types=self.context()[2]);proxy.unpack_url=lambda *a,**k:73
  self.assertEqual(73,real.unpack_url('link','SECRET_SENTINEL'));self.assertEqual(1,f['hook_returns']);self.assertNotIn('SECRET',json.dumps(f))
  def bad(*a,**k):raise OSError(2,'SECRET_EXCEPTION')
  proxy.unpack_url=bad
  with self.assertRaises(OSError):real.unpack_url('link','/build/tmp/source')
  self.assertEqual(2,f['hook_errno']);self.assertNotIn('SECRET',json.dumps(f));proxy.unpack_url=original
 def stream(self):return bound._DigestText()
 def test_pip_factory_survives_handler_reconfiguration_and_restores_exactly(self):
  f=o.empty();out,err=self.stream(),self.stream();old=logging.getLogRecordFactory();args=['unchanged'];seen=[]
  def pip(passed):
   self.assertIs(args,passed);seen.append(passed)
   logger=logging.getLogger('pip');saved=list(logger.handlers);logger.handlers=[]
   try:
    try:raise ValueError('SECRET_EXCEPTION')
    except ValueError:
     logging.getLogRecordFactory()('pip',40,'/fixture/site/pip/_internal/cli/base_command.py',101,'SECRET_MESSAGE',(),sys.exc_info())
     logging.getLogRecordFactory()('pip',40,'/SECRET_UNKNOWN/file.py',2,'SECRET_MESSAGE',(),None)
   finally:logger.handlers=saved
   print('SECRET_STREAM');return 1
  with patch.object(sys,'stdout',out),patch.object(sys,'stderr',err):self.assertEqual(1,o.observe_pip(pip,args,f,context_info=self.context()))
  self.assertIs(old,logging.getLogRecordFactory());self.assertEqual(1,f['pip_returncode']);self.assertFalse(f['pip_raised']);self.assertEqual(2,len(f['error_sites']));self.assertIsNone(f['error_sites'][1]['member']);self.assertEqual('builtin.ValueError',f['error_sites'][0]['exception_code']);self.assertNotIn('SECRET',json.dumps(f));self.assertEqual(hashlib.sha256(b'SECRET_STREAM\n').hexdigest(),f['logs']['stdout_sha256']);o.validate(f,members=self.context()[1])
 def test_pip_exception_restores_factory_and_retains_stream_digest(self):
  f=o.empty();old=logging.getLogRecordFactory()
  def pip(args):raise ValueError('SECRET_SENTINEL')
  with patch.object(sys,'stdout',self.stream()),patch.object(sys,'stderr',self.stream()):
   with self.assertRaisesRegex(ValueError,'SECRET_SENTINEL'):o.observe_pip(pip,[],f,context_info=self.context())
  self.assertIs(old,logging.getLogRecordFactory());self.assertTrue(f['pip_raised']);self.assertEqual('builtin.ValueError',f['pip_exception_code']);self.assertNotIn('SECRET',json.dumps(f));o.validate(f,members=self.context()[1])
 def test_diagnostic_bounds_and_unknown_fields_rejected(self):
  f=o.empty();o.validate(f,members=set())
  for key,bad in [('extra','SECRET'),('pip_invocations',True),('unpack_calls',17),('error_sites',[{'member':'SECRET'}]),('pip_exception_code','SECRET')]:
   v=copy.deepcopy(f);v[key]=bad
   with self.assertRaisesRegex(ValueError,'^INVALID_PIP_OBSERVATION$'):o.validate(v,members=set())
 def test_record_limit_is_bounded(self):
  f=o.empty()
  def pip(args):
   factory=logging.getLogRecordFactory()
   for i in range(50):factory('pip',40,'/fixture/site/pip/_internal/cli/base_command.py',i+1,'SECRET',(),None)
   return 1
  with patch.object(sys,'stdout',self.stream()),patch.object(sys,'stderr',self.stream()):o.observe_pip(pip,[],f,context_info=self.context())
  self.assertEqual(16,len(f['error_sites']));self.assertNotIn('SECRET',json.dumps(f));o.validate(f,members=self.context()[1])
 def test_deployed_bound_helper_and_legacy_api_resolve_exactly(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'bound-build.py').write_bytes((ROOT/'scripts/engine_clock_builder_bound_build.py').read_bytes());(root/'legacy-driver.py').write_bytes((ROOT/'scripts/engine_clock_builder_driver.py').read_bytes())
   module=h.load_owned('fixture_bound',root/'bound-build.py');self.assertTrue(callable(module.run_with_snapshots));driver=module._driver();self.assertTrue(callable(driver.pip_wheel_args));self.assertEqual(str(root/'legacy-driver.py'),driver.__file__)
 def test_main_failure_exact_stdout_and_rc_even_if_evidence_write_fails(self):
  import pip._internal.cli.main as cli
  fake=SimpleNamespace(run_with_snapshots=lambda *a,**k:(_ for _ in ()).throw(ValueError('MISSING_SOURCE_UNPACK')),_write_manifest=lambda *a:(_ for _ in ()).throw(OSError('SECRET_WRITE')))
  def load(name,path):return o if name=='owned_pip_observation' else fake
  output=io.StringIO()
  with patch.object(h,'load_owned',side_effect=load),patch.object(o,'pip_context',return_value=self.context()),patch.object(h.sys,'argv',['fixture','--registered-pip-wheel-v1']),patch.object(h.sys,'version_info',(3,11,18)),patch.object(h.Path,'read_bytes',return_value=b'{"source_rows":[]}'),patch.object(h.sys,'stdout',output):
   self.assertEqual(1,h.main())
  self.assertEqual('{"schema":"source-snapshot-failure-v1","code":"SOURCE_SNAPSHOT_FAILED"}\n',output.getvalue())

class ObservedControllerTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(b,'v6 controller missing')
 def request(self):
  inputs=b.prep.expected_inputs(ROOT);sources,_=b.make_sources(ROOT,{'inputs':inputs});plan=b.staging.compile_plan(sources);raw=b.canonical(plan)
  return {'schema':'builder-preparation-request-v6','request_id':b.REQUEST_ID,'repository':b.prep.REPOSITORY,'branch':b.BRANCH,'workflow_path':b.WORKFLOW,'reviewed_source_sha':'1'*40,
   'budget':{'runs':1,'attempts':1,'builds':1,'probes':2,'profile_loads':1,'candidate_userns_assertions':1},'source_closure':{p:'0'*64 for p in b.CLOSURE},'inputs':inputs,
   'expected_plan':{'plan_sha256':plan['plan_sha256'],'serialized_sha256':hashlib.sha256(raw).hexdigest(),'nbytes':len(raw)}}
 def test_closed_request_and_exact_new_plan(self):
  req=self.request();self.assertEqual(req,b.validate_request(req));req['budget']['builds']=2
  with self.assertRaisesRegex(ValueError,'^INVALID_REQUEST$'):b.validate_request(req)
 def test_only_owned_entry_additions_and_no_original_validation_edits(self):
  req=self.request();old,op=b.previous.make_sources(ROOT,req);new,np=b.make_sources(ROOT,req);self.assertEqual(old[:-1],new[:-1])
  for p,raw in op.items():
   if p!='run/builder/build.py':self.assertEqual(raw,np[p])
  self.assertEqual(op['run/builder/build.py'],np['run/builder/bound-build.py']);self.assertIn('run/builder/observation.py',np);b.verify_plan(b.staging.compile_plan(new),req);self.assertEqual(b.previous.private_launch_argv(10,11),b.private_launch_argv(10,11))
 def test_workflow_and_retention_are_closed_to06(self):
  wf=json.loads((ROOT/b.WORKFLOW).read_bytes());self.assertEqual([b.BRANCH],wf['on']['push']['branches']);self.assertIn('--guard-only',wf['jobs']['prepare']['steps'][2]['run']);self.assertIn('always()',wf['jobs']['prepare']['steps'][-2]['if']);self.assertEqual(Path('/tmp/engine-clock-build-builder-20261113-06'),b.retention_roots()['build'])
  with patch.object(b.retention,'preserve_workspaces',side_effect=AssertionError('unbound retention')):
   with self.assertRaisesRegex(ValueError,'^INVALID_REMOTE_ENVIRONMENT$'):b.retain(ROOT,{})

class FullGuardTests(unittest.TestCase):
    request=ObservedControllerTests.request
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
                    base+'/actions/workflows/engine-clock-builder-preparation-v6.yml/runs?branch=prepare%2Fengine-clock-builder-20261113-06&per_page=2':{'total_count':1,'workflow_runs':[run]},
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
