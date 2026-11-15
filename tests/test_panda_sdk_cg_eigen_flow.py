import copy,json,tempfile,unittest,zipfile
from pathlib import Path
from scripts import panda_sdk_cg_eigen_policy as a
from scripts import panda_sdk_cg_eigen_carrier as carrier
from scripts import accept_panda_sdk_cg_eigen as acceptor
from scripts import produce_panda_sdk_cg_eigen as producer
class FlowTests(unittest.TestCase):
 def request(self):return a.request_template('1'*40,[dict(event='push',run_id=11),dict(event='pull_request',run_id=12)],a.ROOT)
 def test_closed_build_only_authority(self):
  r=self.request();a.validate_request(r,a.ROOT)
  for mutate in [lambda x:x['permissions'].update(sdk_load=True),lambda x:x['budget'].update(build_attempts=2),lambda x:x.update(source_sha='bad'),lambda x:x['source_closure'].update({'scripts/forged.py':'0'*64}),lambda x:x.update(extra=True)]:
   bad=copy.deepcopy(r);mutate(bad)
   with self.assertRaises(ValueError):a.validate_request(bad,a.ROOT)
 def test_source_ci_exact_four_jobs_and_attempt_one(self):
  r=self.request();proof=[]
  for row in r['source_ci']:
   run=dict(id=row['run_id'],head_sha=r['source_sha'],head_branch=a.SOURCE_BRANCH,event=row['event'],workflow_id=411705464,path='.github/workflows/ci.yml',run_attempt=1,status='completed',conclusion='success',repository=dict(full_name=a.REPO))
   jobs=dict(total_count=2,jobs=[dict(name=n,run_id=row['run_id'],status='completed',conclusion='success') for n in ['synthetic-unit','onnx-interface-test']]);proof.append(dict(run=run,jobs=jobs,artifacts=dict(total_count=0,artifacts=[])))
  a.validate_ci(r,proof)
  for key,value in [('run_attempt',2),('run_attempt',True),('conclusion','failure'),('head_branch','main')]:
   bad=copy.deepcopy(proof);bad[0]['run'][key]=value
   with self.assertRaises(ValueError):a.validate_ci(r,bad)
 def test_request_only_activation(self):
  r=self.request();head='2'*40;commit=dict(sha=head,parents=[dict(sha=r['source_sha'])]);delta=dict(status='ahead',ahead_by=1,total_commits=1,commits=[dict(sha=head)],files=[dict(filename=a.REQUEST,status='added',sha='3'*40)]);a.validate_activation(r,head,commit,delta,'100644')
  bad=copy.deepcopy(delta);bad['files'].append(dict(filename='scripts/change.py',status='modified',sha='4'*40))
  with self.assertRaises(ValueError):a.validate_activation(r,head,commit,bad,'100644')
 def test_single_build_reservation(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'start.json';a.reserve_build(p)
   with self.assertRaises(ValueError):a.reserve_build(p)
   self.assertEqual(json.loads(p.read_text())['build_start_attempts'],1)
 def test_exact_build_run_no_retry(self):
  ctx=dict(repository=a.REPO,head_sha='2'*40,run_id=55,attempt=1,event='push',actor=a.OWNER)
  run=dict(id=55,head_sha='2'*40,head_branch=a.BRANCH,event='push',run_attempt=1,path=a.WORKFLOW,actor=dict(login=a.OWNER),repository=dict(full_name=a.REPO,id=a.REPO_ID),head_repository=dict(full_name=a.REPO,id=a.REPO_ID),status='in_progress',conclusion=None,workflow_id=77)
  workflow=dict(id=77,path=a.WORKFLOW,state='active');listing=dict(total_count=1,workflow_runs=[run]);a.validate_run(ctx,run,workflow,listing)
  for modify in ['retry','second','branch']:
   bad=copy.deepcopy(run);ls=copy.deepcopy(listing)
   if modify=='retry':bad['run_attempt']=2
   elif modify=='second':ls['total_count']=2;ls['workflow_runs'].append(run)
   else:bad['head_branch']='prepare/old'
   with self.assertRaises(ValueError):a.validate_run(ctx,bad,workflow,ls)
 def test_closed_carrier_keeps_negative_missing_files(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'ok.zip'
   with zipfile.ZipFile(p,'w') as z:z.writestr('reports/receipt.json','{}');z.writestr('logs/host.log','')
   r=carrier.extract_carrier(p,root/'out');self.assertEqual(set(r['files']),{'reports/receipt.json','logs/host.log'});self.assertFalse(r['native_admitted'])
 def test_carrier_unlisted_duplicate_link_and_truncation_reject(self):
  for mode in ['unknown','duplicate','symlink','truncated']:
   with tempfile.TemporaryDirectory() as d:
    root=Path(d);p=root/'bad.zip'
    with zipfile.ZipFile(p,'w') as z:
     z.writestr('reports/receipt.json','{}')
     if mode=='unknown':z.writestr('../escape','bad')
     if mode=='duplicate':
      import warnings
      with warnings.catch_warnings():warnings.simplefilter('ignore');z.writestr('reports/receipt.json','{}')
     if mode=='symlink':
      info=zipfile.ZipInfo('logs/host.log');info.external_attr=0o120777<<16;z.writestr(info,'/etc/passwd')
    if mode=='truncated':p.write_bytes(p.read_bytes()[:-5])
    with self.assertRaises(ValueError):carrier.extract_carrier(p,root/'out')
 def test_negative_semantics_never_asserts_observed_defaultoff(self):
  r=dict(schema='panda-sdk-cg-eigen-production-v2',status='BLOCKED',source_sha='1'*40,activation_sha='2'*40,run_id=55,request_sha256='3'*64,build_start_attempts=0,native_admitted=False,stage7_complete=False,target_execution=False,files={},omissions=sorted(carrier.FILES-{'reports/receipt.json'}))
  x=acceptor.validate_receipt(r,{'reports/receipt.json':{}},'1'*40,'2'*40,55,'3'*64);self.assertFalse(x['static_passed']);self.assertIsNone(x['source_observer_default_off_observed'])
  for key in ['native_admitted','target_execution','stage7_complete']:
   bad=dict(r,**{key:True})
   with self.assertRaises(ValueError):acceptor.validate_receipt(bad,{'reports/receipt.json':{}},'1'*40,'2'*40,55,'3'*64)
 def test_success_claim_requires_complete_actual_candidate_carrier(self):
  r=dict(schema='panda-sdk-cg-eigen-production-v2',status='CG_EIGEN_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME',source_sha='1'*40,activation_sha='2'*40,run_id=55,request_sha256='3'*64,build_start_attempts=1,native_admitted=False,stage7_complete=False,target_execution=False,files={},omissions=[])
  with self.assertRaises(ValueError):acceptor.validate_receipt(r,{'reports/receipt.json':{}},'1'*40,'2'*40,55,'3'*64)
 def test_producer_local_entry_never_compiles(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):producer.run_production(Path(d)/'out')
if __name__=='__main__':unittest.main()

class PackagingFailureTests(unittest.TestCase):
 def test_pinned_debian_headers_without_runtime_binaries(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);r=producer.populate_headers(root);self.assertTrue((root/'usr/include/GL/gl.h').is_file());self.assertTrue((root/'usr/include/X11/Xlib.h').is_file());self.assertFalse(list(root.rglob('*.so*')));self.assertTrue(r)
 def test_seal_partial_failure_preserves_closed_negative_receipt(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);bundle=root/'bundle';(bundle/'reports').mkdir(parents=True);(bundle/'reports/configuration.json').write_text('{}');r=dict(schema='panda-sdk-cg-eigen-production-v2',status='FAILED',source_sha='1'*40,activation_sha='2'*40,run_id=55,request_sha256='3'*64,build_start_attempts=0,native_admitted=False,stage7_complete=False,target_execution=False)
   producer.seal_failure_bundle(root,r);saved=json.loads((bundle/'reports/receipt.json').read_text());files={'reports/receipt.json':{},**saved['files']};self.assertFalse(acceptor.validate_receipt(saved,files,'1'*40,'2'*40,55,'3'*64)['static_passed'])
 def test_post_gate_failure_downgrades_success(self):
  r=dict(status='CG_EIGEN_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME',build_start_attempts=1);producer.record_failure(r,ValueError('post-validation failed'));self.assertEqual(r['status'],'FAILED')

class ClosedMetadataTests(unittest.TestCase):
 def test_unrecognized_observer_or_native_promotion_rejected(self):
  r=dict(schema='panda-sdk-cg-eigen-production-v2',status='BLOCKED',source_sha='1'*40,activation_sha='2'*40,run_id=55,request_sha256='3'*64,build_start_attempts=0,native_admitted=False,stage7_complete=False,target_execution=False,files={},omissions=sorted(carrier.FILES-{'reports/receipt.json'}),source_observer_default_off_observed=True)
  with self.assertRaises(ValueError):acceptor.validate_receipt(r,{'reports/receipt.json':{}},'1'*40,'2'*40,55,'3'*64)

class DurableFailureDiagnosticsTests(unittest.TestCase):
 def fixture(self,root):
  build=root/'work/build';(build/'makepanda').mkdir(parents=True);(build/'makepanda/stdout.log').write_bytes(b'compiler stdout');(build/'makepanda/stderr.log').write_bytes(b'compiler stderr');(build/'makepanda/command.json').write_text('{"argv":["compiler"],"returncode":3}')
  return build,dict(status='FAILED',build_start_attempts=1)
 def test_oversized_partial_candidate_keeps_both_logs_and_command(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);build,r=self.fixture(root);p=build/'sdk/lib/libpandagl.so';p.parent.mkdir(parents=True)
   with p.open('wb') as f:f.truncate(4*1024**2+1)
   try:producer.finalize_bundle(root,r,build,None,None,None)
   except BaseException:producer.seal_failure_bundle(root,r)
   self.assertEqual((root/'bundle/logs/makepanda.log').read_bytes(),b'compiler stdout');host=(root/'bundle/logs/host.log').read_bytes();self.assertIn(b'compiler stderr',host);self.assertIn(b'"returncode":3',host);self.assertIn('candidate/libpandagl.so.data',r['omissions']);self.assertTrue(r['diagnostics']['omitted_members'])
 def test_combined_overflow_is_bounded_and_explicit(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);build,r=self.fixture(root)
   for name in ['stdout','stderr']:
    with (build/'makepanda'/str(name+'.log')).open('wb') as f:f.truncate(16*1024**2)
   try:producer.finalize_bundle(root,r,build,None,None,None)
   except BaseException:producer.seal_failure_bundle(root,r)
   self.assertTrue((root/'bundle/logs/host.log').is_file());self.assertLessEqual(sum(p.stat().st_size for p in (root/'bundle/logs').iterdir()),32*1024**2);self.assertTrue(r['diagnostics']['truncated']);self.assertEqual(r['status'],'FAILED')

 def test_reading_diagnostic_atime_is_not_mistaken_for_byte_drift(self):
  import os
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);build,r=self.fixture(root)
   for p in (build/'makepanda').iterdir():os.utime(p,(946684800,946684800))
   producer.collect_diagnostics(root,r,build);self.assertIn(b'compiler stderr',(root/'bundle/logs/host.log').read_bytes());self.assertFalse(r['diagnostics']['truncated'])

class EigenCarrierTests(unittest.TestCase):
 def test_raw_descriptor_exact_length_and_closed_23_paths(self):
  self.assertEqual(len(carrier.FILES),23);self.assertEqual(carrier.FILE_LIMITS['candidate/layout-descriptor.data'],128)
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'short.zip'
   with zipfile.ZipFile(p,'w') as z:z.writestr('reports/receipt.json','{}');z.writestr('candidate/layout-descriptor.data',b'x'*127)
   with self.assertRaises(ValueError):carrier.extract_carrier(p,root/'out')
 def test_negative_eigen_receipt_keeps_observer_unknown(self):
  self.assertEqual(a.BRANCH,'prepare/panda-sdk-cg-eigen-build-20261116-02');self.assertEqual(a.SOURCE_BRANCH,'feature/panda-sdk-cg-eigen-candidate-v2')
  r=a.request_template('1'*40,[dict(event='push',run_id=11),dict(event='pull_request',run_id=12)],a.ROOT);self.assertEqual(r['contract_sha256'],a.eigen.CONTRACT_SHA)
  for name in ['scripts/panda_sdk_cg_eigen_gate.py','native/panda_sdk_cg_v2/layout_contract.cxx',a.eigen.CONTRACT]:self.assertIn(name,r['source_closure'])

class ReviewDiagnosticTests(unittest.TestCase):
 def test_short_stdout_full_stderr_keeps_commands_and_bounded_prefix(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);build=root/'work/build';(build/'makepanda').mkdir(parents=True);(build/'makepanda/stdout.log').write_bytes(b'short stdout');(build/'makepanda/command.json').write_text('{"argv":["compiler"],"returncode":3}');(build/'makepanda/stderr.log').write_bytes(b'e'*(16*1024**2));r=dict(status='FAILED',build_start_attempts=1)
   try:producer.finalize_bundle(root,r,build,None,None,None)
   except BaseException:producer.seal_failure_bundle(root,r)
   host=root/'bundle/logs/host.log';self.assertTrue(host.exists());self.assertLessEqual(host.stat().st_size,16*1024**2);self.assertIn(b'"returncode":3',host.read_bytes()[:4096]);self.assertTrue(r['diagnostics']['truncated']);self.assertNotIn('logs/host.log',r['omissions'])
