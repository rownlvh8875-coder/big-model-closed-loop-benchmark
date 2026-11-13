"""Owned filesystem fixtures and fake unpack; no foreign source or namespace execution."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts import engine_clock_builder_bound_build as bound
from scripts import engine_clock_builder_driver as legacy
from scripts import engine_clock_builder_pip_observation as observer
try:
 from scripts import engine_clock_builder_source_directory as d
 from scripts import engine_clock_builder_directory_preparation as b
except ImportError:d=b=None
ROOT=Path(__file__).resolve().parent.parent

class DirectoryTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(d,'secure source-directory gate missing')
 def layout(self,root):
  tmp=root/'tmp';tmp.mkdir();parent=tmp/'pip-wheel-fixture';parent.mkdir();return tmp,parent,parent/('progressbar_'+'a'*32)
 def prepare(self,root,tmp,target,facts=None):return d.prepare_directory(str(target),tmp_root=tmp,build_root=root,facts=facts)
 def test_original_missing_leaf_guard_then_secure_prepare_passes(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);tmp,parent,target=self.layout(root)
   with self.assertRaises(FileNotFoundError):bound._location(target,tmp)
   f=self.prepare(root,tmp,target);self.assertTrue(f['created']);self.assertTrue(f['empty']);self.assertEqual(0o700,f['target_mode']);self.assertTrue(f['target_named_inode_matches']);d.validate(f)
   self.assertEqual(target,bound._location(target,tmp)[0]);self.assertEqual(os.getuid(),target.stat().st_uid)
 def test_existing_empty_target_accepted_without_replacing_inode(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);tmp,parent,target=self.layout(root);target.mkdir(mode=0o700);ino=target.stat().st_ino;f=self.prepare(root,tmp,target)
   self.assertFalse(f['created']);self.assertEqual(ino,f['target_inode']);self.assertEqual(ino,target.stat().st_ino)
 def test_missing_parent_traversal_and_noncanonical_location_rejected(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);tmp,parent,target=self.layout(root)
   for p in (str(tmp/'pip-wheel-missing'/target.name),str(tmp/'..'/'outside'/target.name),str(target).replace('/tmp/','/tmp//')):
    f={}
    with self.assertRaisesRegex(ValueError,'^SOURCE_DIRECTORY_REJECTED$'):d.prepare_directory(p,tmp_root=tmp,build_root=root,facts=f)
    d.validate(f);self.assertEqual('REJECTED',f['status'])
   self.assertFalse(target.exists());self.assertFalse((root/'outside').exists())
 def test_symlink_parent_or_leaf_file_and_nonempty_rejected(self):
  for kind in ('parent_link','leaf_link','file','nonempty','writable'):
   with tempfile.TemporaryDirectory() as name:
    root=Path(name);tmp,parent,target=self.layout(root);outside=root/'outside';outside.mkdir()
    if kind=='parent_link':parent.rmdir();parent.symlink_to(outside,target_is_directory=True)
    elif kind=='leaf_link':target.symlink_to(outside,target_is_directory=True)
    elif kind=='file':target.write_bytes(b'preserve')
    else:
     target.mkdir(mode=0o700)
     if kind=='nonempty':(target/'preserve').write_bytes(b'original')
     else:target.chmod(0o777)
    with self.assertRaisesRegex(ValueError,'^SOURCE_DIRECTORY_REJECTED$'):self.prepare(root,tmp,target)
    self.assertEqual([],list(outside.iterdir()))
    if kind=='file':self.assertEqual(b'preserve',target.read_bytes())
    if kind=='nonempty':self.assertEqual(b'original',(target/'preserve').read_bytes())
 def test_wrong_device_is_rejected_before_leaf_creation(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);tmp,parent,target=self.layout(root);actual=os.fstat;calls=[]
   def changed(fd):
    value=actual(fd);calls.append(fd)
    if len(calls)==2:return SimpleNamespace(st_dev=value.st_dev+1,st_uid=value.st_uid,st_mode=value.st_mode,st_ino=value.st_ino)
    return value
   with patch.object(d.os,'fstat',side_effect=changed):
    with self.assertRaisesRegex(ValueError,'^SOURCE_DIRECTORY_REJECTED$'):self.prepare(root,tmp,target)
   self.assertFalse(target.exists())
 def test_named_inode_mismatch_rejected(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);tmp,parent,target=self.layout(root);actual=os.stat
   def changed(path,*args,**kwargs):
    value=actual(path,*args,**kwargs)
    if path==target.name and kwargs.get('dir_fd') is not None:return SimpleNamespace(st_dev=value.st_dev,st_ino=value.st_ino+1)
    return value
   with patch.object(d.os,'stat',side_effect=changed):
    with self.assertRaisesRegex(ValueError,'^SOURCE_DIRECTORY_REJECTED$'):self.prepare(root,tmp,target)
 def test_integrated_immutable_hook_and_both_proxies_validate_snapshots(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);tmp,parent,target=self.layout(root);events=[];payload=b'owned fixture\n';rows=[{'path':'progressbar/__init__.py','sha256':hashlib.sha256(payload).hexdigest()}]
   def unpack(link,location,*args,**kwargs):
    self.assertTrue(target.is_dir());(target/'progressbar').mkdir();(target/'progressbar/__init__.py').write_bytes(payload);return 'unpacked'
   real=SimpleNamespace(unpack_url=unpack);gated=d.PrepareProxy(real,tmp_root=tmp,build_root=root,emit=events.append);f=observer.empty();proxy=observer.PrepareProxy(gated,f,types={ValueError:'builtin.ValueError'})
   driver=SimpleNamespace(source_snapshot=legacy.source_snapshot,_check_source_map=legacy._check_source_map,pip_wheel_args=lambda:['fixed'],validate_snapshots=legacy.validate_snapshots)
   def pip(args):self.assertEqual(['fixed'],args);self.assertEqual('unpacked',real.unpack_url('link',str(target)));return 0
   with patch.object(bound,'_driver',return_value=driver):result=bound.run_with_snapshots(proxy,pip,rows,tmp_root=tmp,evidence_root=root)
   self.assertEqual('SOURCE_SNAPSHOTS_VERIFIED',result['status']);self.assertEqual(result['before']['files_sha256'],result['after']['files_sha256']);self.assertIs(unpack,real.unpack_url);self.assertEqual(1,len(events));self.assertEqual('EMPTY_SOURCE_DIRECTORY_READY',events[0]['status']);self.assertEqual(1,f['hook_returns'])
 def test_immutable_hook_failure_restores_both_proxies(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);tmp,parent,target=self.layout(root);events=[]
   def unpack(*a,**k):raise FileNotFoundError(2,'OWNED_FIXTURE')
   real=SimpleNamespace(unpack_url=unpack);gated=d.PrepareProxy(real,tmp_root=tmp,build_root=root,emit=events.append);f=observer.empty();proxy=observer.PrepareProxy(gated,f,types={FileNotFoundError:'builtin.FileNotFoundError'})
   driver=SimpleNamespace(pip_wheel_args=lambda:['fixed'])
   def pip(args):return real.unpack_url('link',str(target))
   with patch.object(bound,'_driver',return_value=driver):
    with self.assertRaisesRegex(ValueError,'^SOURCE_PAYLOAD_MISMATCH$'):bound.run_with_snapshots(proxy,pip,[],tmp_root=tmp,evidence_root=root)
   self.assertIs(unpack,real.unpack_url);self.assertEqual(1,len(events));self.assertEqual(0,f['hook_returns']);self.assertEqual('builtin.FileNotFoundError',f['hook_exception_code'])

 def test_ready_receipt_requires_location_hash(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);tmp,parent,target=self.layout(root);f=self.prepare(root,tmp,target);f['location_sha256']=None
   with self.assertRaisesRegex(ValueError,'^INVALID_SOURCE_DIRECTORY_FACTS$'):d.validate(f)

 def test_proxy_rejects_second_preparation_and_restores_original(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);tmp,parent,target=self.layout(root);original=lambda *a:None;real=SimpleNamespace(unpack_url=original);events=[];proxy=d.PrepareProxy(real,tmp_root=tmp,build_root=root,emit=events.append);proxy.unpack_url=lambda *a:7
   self.assertEqual(7,real.unpack_url('link',str(target)))
   with self.assertRaisesRegex(ValueError,'^SOURCE_DIRECTORY_REUSED$'):real.unpack_url('link',str(target))
   proxy.unpack_url=original;self.assertIs(original,real.unpack_url);self.assertEqual(1,len(events))
 def test_main_composes_gate_and_observer_and_preserves_failure_wire(self):
  import io
  from scripts import engine_clock_builder_directory_build as entry
  fake_gate=SimpleNamespace(PrepareProxy=lambda real:SimpleNamespace(unpack_url=real.unpack_url,marker='gated'))
  def run(proxy,*args):self.assertEqual('gated',proxy.real.marker);raise ValueError('MISSING_SOURCE_UNPACK')
  fake_bound=SimpleNamespace(run_with_snapshots=run,_write_manifest=lambda *args:(_ for _ in ()).throw(OSError('SECRET_WRITE')))
  def load(name,path):return {'owned_pip_observation':observer,'owned_bound_build':fake_bound,'owned_source_directory':fake_gate}[name]
  output=io.StringIO();context=(Path('/fixture/site'),set(),{ValueError:'builtin.ValueError'})
  with patch.object(entry,'load_owned',side_effect=load),patch.object(observer,'pip_context',return_value=context),patch.object(entry.sys,'argv',['fixture','--registered-pip-wheel-v1']),patch.object(entry.sys,'version_info',(3,11,18)),patch.object(entry.Path,'read_bytes',return_value=b'{"source_rows":[]}'),patch.object(entry.sys,'stdout',output):self.assertEqual(1,entry.main())
  self.assertEqual('{"schema":"source-snapshot-failure-v1","code":"SOURCE_SNAPSHOT_FAILED"}\n',output.getvalue())

 def test_receipt_unknown_text_rejected_and_exclusive_file_not_overwritten(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);tmp,parent,target=self.layout(root);f=self.prepare(root,tmp,target);p=root/'receipt.json';d.persist(f,path=p);original=p.read_bytes()
   with self.assertRaises(FileExistsError):d.persist(f,path=p)
   self.assertEqual(original,p.read_bytes());f['extra']='SECRET'
   with self.assertRaisesRegex(ValueError,'^INVALID_SOURCE_DIRECTORY_FACTS$'):d.validate(f)

class DirectoryControllerTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(b,'v7 controller missing')
 def request(self):
  inputs=b.prep.expected_inputs(ROOT);sources,_=b.make_sources(ROOT,{'inputs':inputs});plan=b.staging.compile_plan(sources);raw=b.canonical(plan)
  return {'schema':'builder-preparation-request-v7','request_id':b.REQUEST_ID,'repository':b.prep.REPOSITORY,'branch':b.BRANCH,'workflow_path':b.WORKFLOW,'reviewed_source_sha':'1'*40,
   'budget':{'runs':1,'attempts':1,'builds':1,'probes':2,'profile_loads':1,'candidate_userns_assertions':1,'source_directory_preparations':1},'source_closure':{p:'0'*64 for p in b.CLOSURE},'inputs':inputs,
   'expected_plan':{'plan_sha256':plan['plan_sha256'],'serialized_sha256':hashlib.sha256(raw).hexdigest(),'nbytes':len(raw)}}
 def test_closed_v7_and_one_directory_budget(self):
  req=self.request();self.assertEqual(req,b.validate_request(req));req['budget']['source_directory_preparations']=2
  with self.assertRaisesRegex(ValueError,'^INVALID_REQUEST$'):b.validate_request(req)
 def test_only_owned_entry_and_gate_added_original_payloads_unchanged(self):
  req=self.request();old,op=b.previous.make_sources(ROOT,req);new,np=b.make_sources(ROOT,req);self.assertEqual(old[:-1],new[:-1])
  for p,raw in op.items():
   if p!='run/builder/build.py':self.assertEqual(raw,np[p])
  self.assertEqual({'run/builder/source-directory.py'},set(np)-set(op));self.assertEqual(51,len(req['inputs']));self.assertEqual(109285137,sum(x['nbytes'] for x in req['inputs']));b.verify_plan(b.staging.compile_plan(new),req);self.assertEqual(b.previous.private_launch_argv(10,11),b.private_launch_argv(10,11))
 def test_workflow_and_retention_are_closed(self):
  wf=json.loads((ROOT/b.WORKFLOW).read_bytes());self.assertEqual([b.BRANCH],wf['on']['push']['branches']);self.assertIn('--guard-only',wf['jobs']['prepare']['steps'][2]['run']);self.assertIn('always()',wf['jobs']['prepare']['steps'][-2]['if']);self.assertEqual(Path('/tmp/engine-clock-build-builder-20261113-07'),b.retention_roots()['build'])
  with patch.object(b.retention,'preserve_workspaces',side_effect=AssertionError('unbound')):
   with self.assertRaisesRegex(ValueError,'^INVALID_REMOTE_ENVIRONMENT$'):b.retain(ROOT,{})

class FullGuardTests(unittest.TestCase):
    request=DirectoryControllerTests.request
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
                    base+'/actions/workflows/engine-clock-builder-preparation-v7.yml/runs?branch=prepare%2Fengine-clock-builder-20261113-07&per_page=2':{'total_count':1,'workflow_runs':[run]},
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
