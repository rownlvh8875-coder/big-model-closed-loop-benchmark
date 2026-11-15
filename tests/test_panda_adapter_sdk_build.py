from pathlib import Path
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile,time,unittest
try:
    from scripts import build_panda_adapter_sdk as sdk
except ImportError:sdk=None
ROOT=Path(__file__).resolve().parents[1]
class AdapterSdkBuildTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(sdk,'bounded activity/cache SDK builder required')
    def test_partial_source_and_invalid_parallelism_do_not_create_output(self):
        with tempfile.TemporaryDirectory(prefix='as-build-') as folder:
            folder=Path(folder);out=folder/'build'
            for threads in (0,5,True,4):
                with self.assertRaises((ValueError,OSError)):sdk.build(folder,folder,out,threads)
                self.assertFalse(out.exists())
    def test_existing_build_evidence_is_never_overwritten(self):
        with tempfile.TemporaryDirectory(prefix='as-existing-') as folder:
            folder=Path(folder);out=folder/'build';out.mkdir();(out/'keep').write_bytes(b'old')
            with self.assertRaises(ValueError):sdk.build(folder,folder,out)
            self.assertEqual(list(out.iterdir()),[out/'keep']);self.assertEqual((out/'keep').read_bytes(),b'old')
    def test_extracted_sysroot_must_match_pinned_archive_and_no_extra_inputs(self):
        with tempfile.TemporaryDirectory(prefix='as-deps-') as folder:
            folder=Path(folder);root=folder/'root';p=root/'usr/include/a.h';p.parent.mkdir(parents=True);p.write_bytes(b'int x;\n')
            stream=io.BytesIO()
            with tarfile.open(fileobj=stream,mode='w:xz') as tar:
                t=tarfile.TarInfo('./usr/include/a.h');t.size=7;t.mode=0o644;tar.addfile(t,io.BytesIO(b'int x;\n'))
            payload=stream.getvalue();header=b'data.tar.xz/    '.ljust(16)+b'0'.ljust(12)+b'0'.ljust(6)+b'0'.ljust(6)+b'100644'.ljust(8)+str(len(payload)).encode().ljust(10)+b'`\n'
            deb=folder/'input.deb';deb.write_bytes(b'!<arch>\n'+header+payload+(b'\n' if len(payload)%2 else b''))
            rows=[dict(path=str(deb),nbytes=deb.stat().st_size,sha256=hashlib.sha256(deb.read_bytes()).hexdigest())]
            r=sdk.verify_sysroot(root,rows,[]);self.assertEqual(len(r),1)
            p.write_bytes(b'changed')
            with self.assertRaises(ValueError):sdk.verify_sysroot(root,rows,[])
            p.write_bytes(b'int x;\n');(root/'extra').write_bytes(b'new')
            with self.assertRaises(ValueError):sdk.verify_sysroot(root,rows,[])
    def test_fast_final_output_and_timeout_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='as-limits-') as folder:
            folder=Path(folder)
            for name,body,timeout in (('disk','from pathlib import Path;Path("sparse").write_bytes(b"x"*5000)',5),('log','print("x"*5000)',5),('time','import time;time.sleep(5)',.05)):
                out=folder/name;out.mkdir();r=sdk.run_build([sys.executable,'-c',body],out,sdk.build_env(folder),out,timeout,4096,1024)
                with self.subTest(name=name):self.assertNotEqual(r['status'],'success')
    def test_disk_failure_stops_descendants_before_receipt(self):
        with tempfile.TemporaryDirectory(prefix='as-child-') as folder:
            out=Path(folder);child="import signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path('ready').touch();time.sleep(2);Path('late').touch()"
            body="import subprocess,sys,time;from pathlib import Path;subprocess.Popen([sys.executable,'-c',"+repr(child)+"]);\nwhile not Path('ready').exists():time.sleep(.01)\nPath('sparse').write_bytes(b'x'*5000)\ntime.sleep(5)"
            r=sdk.run_build([sys.executable,'-c',body],out,sdk.build_env(out),out,10,4096,1024);self.assertNotEqual(r['status'],'success');time.sleep(2.1);self.assertFalse((out/'late').exists())
    def test_rpm_flags_cannot_inject_external_header_in_c_or_cxx(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix='as-rpm-') as folder:
            folder=Path(folder);header=folder/'external.h';header.write_text('int unpinned_external_definition=17;\n')
            for compiler,standard,suffix in (('/usr/bin/gcc','c11','c'),('/usr/bin/g++','c++11','cxx')):
                source=folder/('input.'+suffix);source.write_text('int owned_definition=1;\n');obj=folder/(suffix+'.o')
                with patch.dict(os.environ,{'RPM_OPT_FLAGS':'-include '+str(header)}):env=sdk.build_env(folder)
                # Pinned makepanda appends RPM_OPT_FLAGS to both CFLAGS and CXXFLAGS.
                import shlex
                command=[compiler,'-std='+standard,'-c',str(source),'-o',str(obj),*shlex.split(env.get('RPM_OPT_FLAGS',''))]
                subprocess.run(command,check=True,capture_output=True,env=env,timeout=10)
                symbols=subprocess.check_output(['/usr/bin/readelf','-WsW',str(obj)],env=env,text=True,timeout=10)
                with self.subTest(language=suffix):self.assertNotIn('unpinned_external_definition',symbols);self.assertIn('owned_definition',symbols)
    def test_controlled_environment_discards_linker_and_loader_injection(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix='as-env-') as folder,patch.dict(os.environ,{'LDFLAGS':'-bad','GCC_EXEC_PREFIX':'/bad','LD_AUDIT':'/bad'}):
            env=sdk.build_env(Path(folder));p=subprocess.run(['/usr/bin/gcc','--version'],env=env,capture_output=True,text=True,timeout=5)
            self.assertEqual((p.returncode,p.stderr),(0,''));self.assertEqual(env['LDFLAGS'],'-Wl,-z,defs')
if __name__=='__main__':unittest.main()
