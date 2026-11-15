import copy,hashlib,importlib,json,os,socket,subprocess,sys,tempfile,time,unittest
from pathlib import Path
class RuntimeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.runtime=importlib.import_module('scripts.panda_real_glx_runtime');cls.profile=importlib.import_module('scripts.panda_real_glx_profile');cls.policy=importlib.import_module('scripts.panda_real_glx_policy');cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);src=cls.root/'cpu.c';src.write_text('''#include <stdint.h>
#include <stdio.h>
__attribute__((constructor)) static void msg(void){fputs("owned-CPU-only\\n",stderr);}
int get_pipe_type_pandagl(void){return 1;}
int psd_get_stats(void*p){for(unsigned i=0;i<48;i++)((unsigned char*)p)[i]=0;return 0;}
''');cls.lib=cls.root/'librealgl_fixture.so';subprocess.run(['/usr/bin/gcc','-shared','-fPIC','-O2',str(src),'-o',str(cls.lib)],check=True,capture_output=True);cls.p=cls.profile.make_profile(cls.lib.read_bytes(),fixture=True)
 @classmethod
 def tearDownClass(cls):
  if hasattr(cls,'tmp'):cls.tmp.cleanup()
 def test_owned_cpu_process_two_challenges_code_and_cleanup(self):
  r=self.runtime.run_window(self.lib,self.p,fixture=True,nonce='a'*32);self.runtime.validate_window(self.p,r);self.assertEqual(len(r['frames']),2);self.assertEqual(r['cleanup']['windows_after'],0);self.assertEqual(r['cleanup']['render_calls'],4);self.assertTrue(r['before']['code']['process_code_verified']);self.assertFalse(r['actual_driver_execution_verified']);self.assertFalse(r['native_admitted']);self.assertIn('owned-CPU-only',r['child_stderr']['text'])
 def test_foreign_nonce_stale_frame_code_and_extra_render_reject(self):
  r=self.runtime.run_window(self.lib,self.p,fixture=True)
  for kind in ('nonce','frame','code','renders','driver'):
   q=copy.deepcopy(r)
   if kind=='nonce':q['frames'][0]['nonce']='0'*32
   elif kind=='frame':q['frames'][1]=q['frames'][0]
   elif kind=='code':next(iter(q['after']['code']['ranges'].values()))['sha256']='0'*64
   elif kind=='renders':q['cleanup']['render_calls']=5
   else:q['objects']['driver']['renderer']='llvmpipe'
   with self.subTest(kind=kind),self.assertRaises(ValueError):self.runtime.validate_window(self.p,q)
 def test_no_actual_sdk_or_unregistered_local_driver_entry(self):
  p=self.profile.make_profile()
  with self.assertRaises(ValueError):self.runtime.run_window(self.policy.ROOT/self.policy.SDK,p,fixture=True)
  with self.assertRaises(ValueError):self.runtime.run_window(self.lib,self.p,fixture=False)
 def test_timeout_keeps_process_stage_and_binary_logs(self):
  with self.assertRaises(self.runtime.WindowFailure) as caught:self.runtime.run_window(self.lib,self.p,fixture=True,timeout=.001)
  self.assertEqual(caught.exception.receipt['status'],'FAILED');self.assertFalse(caught.exception.receipt['native_admitted']);self.assertIn('child_returncode',caught.exception.receipt)
 def test_streamed_file_hash_cache_rejects_changed_bytes_and_symlink(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);path=root/'large-image-file';raw=b'CPUdata'*400000;path.write_bytes(raw);st=path.stat();m=dict(entries=[dict(path=str(path),kind='file',mode=st.st_mode&511,nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())]);a=self.runtime.MapAudit(m);v=a.verify_file(str(path));self.assertEqual(v['nbytes'],len(raw));self.assertEqual(a.verify_file(str(path))['sha256'],v['sha256']);path.write_bytes(b'x'+raw[1:])
   with self.assertRaises(ValueError):a.verify_file(str(path))
   alias=root/'alias';alias.symlink_to(path)
   with self.assertRaises(ValueError):a.verify_file(str(alias))
 def test_generated_exec_and_shared_driver_regions_have_separate_limits(self):
  row=dict(path='',inode=0,start=4096,end=8192,perms='rwxp');v=self.runtime.special_regions([row],True);self.assertEqual(len(v['generated_code']),1)
  with self.assertRaises(ValueError):self.runtime.special_regions([row],False)
  with self.assertRaises(ValueError):self.runtime.special_regions([dict(row,path='[stack]')],True)
  with self.assertRaises(ValueError):self.runtime.special_regions([dict(row,start=4096+i*4096,end=8192+i*4096) for i in range(17)],True)
  with self.assertRaises(ValueError):self.runtime.special_regions([dict(row,end=4096+4*1024**2+4096)],True)
  shared=dict(row,path='/SYSV00000001 (deleted)',inode=1,perms='rw-s');v=self.runtime.special_regions([shared],True);self.assertEqual(len(v['shared_driver_memory']),1)
 def test_sparse_cpu_server_readiness_and_owned_reaping(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);script=root/'server.py';ready=root/'ready.sock';script.write_text('import socket,sys,time\ns=socket.socket(socket.AF_UNIX);s.bind(sys.argv[1]);s.listen(1);sys.stderr.write("CPU-server\\n");sys.stderr.flush();time.sleep(20)\n');server=self.runtime.OwnedServer([sys.executable,'-I','-S','-B',str(script),str(ready)],dict(PATH='/usr/bin:/bin'),root,ready,timeout=2);pid=server.pid;self.assertTrue(server.ready);r=server.stop();self.assertIn('CPU-server',r['stderr']['text']);self.assertTrue(r['reaped']);self.assertFalse(Path('/proc/'+str(pid)).exists())
 def test_sparse_server_failure_preserves_available_diagnostics(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);script=root/'server.py';script.write_text('import sys\nsys.stderr.write("CPU-server-start-failed\\n");raise SystemExit(3)\n')
   with self.assertRaises(self.runtime.ServerFailure) as caught:self.runtime.OwnedServer([sys.executable,'-I','-S','-B',str(script)],dict(PATH='/usr/bin:/bin'),root,root/'absent.sock',timeout=2)
   self.assertIn('CPU-server-start-failed',caught.exception.receipt['stderr']['text']);self.assertTrue(caught.exception.receipt['reaped'])
 def test_new_driver_scope_rejects_old_dispatch_request_and_budgets(self):
  a=self.policy;r=a.request_template('a'*40,[dict(event='push',run_id=1),dict(event='pull_request',run_id=2)],a.ROOT);a.validate_request(r,a.ROOT)
  for field,value in [('request_id','panda-sdk-dispatch-20261115-01'),('permissions',dict(model=True)),('budget',dict(render_frames=5))]:
   with self.assertRaises(ValueError):a.validate_request(dict(r,**{field:value}),a.ROOT)
 def test_missing_object_or_defaultoff_fields_cannot_validate(self):
  r=self.runtime.run_window(self.lib,self.p,fixture=True)
  for kind in ('objects','stats','bool','exe'):
   q=copy.deepcopy(r)
   if kind=='objects':q['objects']['objects']={}
   elif kind=='stats':q['source_stats'][0]['values']={}
   elif kind=='bool':q['source_stats'][1]['values']['configured']=False
   else:q['after']['exe_realpath']='/foreign/python'
   with self.subTest(kind=kind),self.assertRaises(ValueError):self.runtime.validate_window(self.p,q)
 def test_server_snapshot_failure_still_reaps_and_preserves_logs(self):
  from unittest.mock import Mock
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);script=root/'server.py';ready=root/'ready.sock';script.write_text('import socket,sys,time\ns=socket.socket(socket.AF_UNIX);s.bind(sys.argv[1]);s.listen(1);sys.stderr.write("CPU-finish-server\\n");sys.stderr.flush();time.sleep(20)\n');server=self.runtime.OwnedServer([sys.executable,'-I','-S','-B',str(script),str(ready)],dict(PATH='/usr/bin:/bin'),root,ready,timeout=2)
   try:
    audit=Mock();audit.snapshot.side_effect=ValueError('CPU map failure');result=self.runtime.finish_server(server,audit);self.assertTrue(result['server']['reaped']);self.assertIn('CPU-finish-server',result['server']['stderr']['text']);self.assertIn('CPU map failure',result['errors'][0])
   finally:server.stop()
 def test_unexpected_server_exit_is_a_failed_owned_lifecycle(self):
  from unittest.mock import Mock
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);script=root/'server.py';ready=root/'ready.sock';script.write_text('import socket,sys,time\ns=socket.socket(socket.AF_UNIX);s.bind(sys.argv[1]);s.listen(1);time.sleep(.2);raise SystemExit(3)\n');server=self.runtime.OwnedServer([sys.executable,'-I','-S','-B',str(script),str(ready)],dict(PATH='/usr/bin:/bin'),root,ready,timeout=2)
   server.child.wait(timeout=2);result=self.runtime.finish_server(server,Mock());self.assertTrue(result['server']['reaped']);self.assertTrue(result['errors'],'spontaneous server exit must not become clean teardown')
if __name__=='__main__':unittest.main()
