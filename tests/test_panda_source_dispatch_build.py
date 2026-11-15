from pathlib import Path
import json
import tempfile
import subprocess
import shutil
import struct
import os
import signal
import time
import unittest
from unittest.mock import patch
try:
    from scripts import build_panda_source_dispatch as builder
except ImportError:
    builder=None

class SourceBuildTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(builder,'constrained compile-only source builder required')
    def test_foreign_or_missing_manifest_rejects_before_build_output(self):
        with tempfile.TemporaryDirectory(prefix='psd-build-') as folder:
            folder=Path(folder);stage=folder/'source';stage.mkdir();sysroot=folder/'sysroot';sysroot.mkdir();out=folder/'build'
            with self.assertRaises(ValueError):builder.build(stage,sysroot,out)
            self.assertFalse(out.exists())
    def test_forged_ready_flags_do_not_authorize_partial_source(self):
        with tempfile.TemporaryDirectory(prefix='psd-build-') as folder:
            folder=Path(folder);stage=folder/'source';stage.mkdir();out=folder/'build'
            (stage/'source-dispatch-manifest.json').write_text(json.dumps(dict(schema='panda-source-dispatch-transform-v1',upstream_revision='470e352ab87ceae6e30429720e4690c8371f5a55',runtime_admission_ready=True,source_tree=[])))
            with self.assertRaises(ValueError):builder.build(stage,folder,out)
            self.assertFalse(out.exists())
    def test_existing_output_and_invalid_parallelism_preserve_evidence(self):
        with tempfile.TemporaryDirectory(prefix='psd-build-') as folder:
            folder=Path(folder);out=folder/'build';out.mkdir();sentinel=out/'keep';sentinel.write_bytes(b'prior')
            for threads in (0,5,True):
                with self.subTest(threads=threads),self.assertRaises(ValueError):builder.build(folder,folder,out,threads)
            self.assertEqual(sentinel.read_bytes(),b'prior');self.assertEqual(list(out.iterdir()),[sentinel])
    def test_shell_metacharacter_path_rejects_without_command_execution(self):
        with tempfile.TemporaryDirectory(prefix='psd-build-') as folder:
            folder=Path(folder);bad=folder/'source;injected';bad.mkdir();out=folder/'build'
            with self.assertRaises(ValueError):builder.build(bad,folder,out)
            self.assertFalse(out.exists())
    def test_private_parser_generator_receives_its_private_data_directory(self):
        with tempfile.TemporaryDirectory(prefix='psd-generator-') as folder:
            folder=Path(folder);binary=folder/'usr/bin';data=folder/'usr/share/bison';binary.mkdir(parents=True);data.mkdir(parents=True)
            (data/'cpu.dat').write_text('private CPU generator data')
            script=binary/'bison';script.write_text('#!/bin/sh\ncat "$BISON_PKGDATADIR/cpu.dat"\n');script.chmod(0o755)
            self.assertTrue(hasattr(builder,'build_environment'),'private parser generator environment required')
            env=builder.build_environment(folder)
            p=subprocess.run(['bison','--version'],env=env,capture_output=True,text=True,timeout=5)
            self.assertEqual((p.returncode,p.stdout),(0,'private CPU generator data'))
    def test_original_read_relocation_and_bare_tail_are_checked_as_data(self):
        self.assertTrue(hasattr(builder,'inspect_candidate'),'R_X86_64_64 original-read binding inspection required')
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='psd-inspect-') as folder:
            folder=Path(folder);header=folder/'original.h'
            header.write_text('#include <stdint.h>\nextern "C" void glReadPixels(int32_t,int32_t,int32_t,int32_t,uint32_t,uint32_t,void*);\n')
            library=folder/'cpu-data-only.so'
            subprocess.run([shutil.which('g++'),'-std=c++11','-shared','-fPIC','-O2','-pthread','-I',str(root/'native'),
                            '-include',str(header),'-DPSD_ORIGINAL_READ=glReadPixels',str(root/'native/panda_source_dispatch.cxx'),'-o',str(library)],check=True,capture_output=True,timeout=30)
            # Unresolved GL-shaped symbol: this ELF is inspected only, NEVER loaded.
            result=builder.inspect_candidate(library)
            self.assertTrue(result['read_tail_original_binding']);self.assertTrue(result['old_abi_profile_rejected']);self.assertFalse(result['runtime_admission_ready'])
            raw=library.read_bytes();bad=folder/'bad.so'
            bad.write_bytes(raw.replace(b'glReadPixels\0',b'glFailPixels\0'))
            with self.assertRaises(ValueError):builder.inspect_candidate(bad)

            changed=bytearray(raw);changed[result['read_tail_file_offset']]=0x90;bad.write_bytes(changed)
            with self.assertRaises(ValueError):builder.inspect_candidate(bad)

    def run_cpu_build_failure(self,mode):
        # Only source qualification is replaced: process launch, sparse-size
        # accounting, termination and failed receipt are the production builder.
        # Real source qualification/build is covered separately by pinned evidence.
        with tempfile.TemporaryDirectory(prefix='psd-children-') as folder:
            folder=Path(folder);stage=folder/'source';stage.mkdir();out=folder/'build';sysroot=folder/'sysroot'
            (stage/'source-dispatch-manifest.json').write_text('{}')
            for relative in ('usr/include/GL/gl.h','usr/include/GL/glx.h','usr/include/X11/Xlib.h','usr/lib/x86_64-linux-gnu/libGL.so','usr/lib/x86_64-linux-gnu/libX11.so'):
                p=sysroot/relative;p.parent.mkdir(parents=True,exist_ok=True);p.touch()
            driver=stage/'makepanda/makepanda.py';driver.parent.mkdir()
            driver.write_text('''import os,sys,time,subprocess
from pathlib import Path
out=Path(sys.argv[sys.argv.index('--outputdir')+1]).parent
(out/'parent.pid').write_text(str(os.getpid()))
mode='''+repr(mode)+'''
if mode!='final_size':
    child="""import os,signal,time
from pathlib import Path
signal.signal(signal.SIGTERM,signal.SIG_IGN)
out=Path("""+repr(str(out))+""")
(out/'child.pid').write_text(str(os.getpid()))
time.sleep(2)
(out/'late-marker').write_text('child still writes')
"""
    subprocess.Popen([sys.executable,'-c',child])
    while not (out/'child.pid').exists():time.sleep(.01)
if mode!='interrupt':
    with (out/'sparse').open('wb') as stream:stream.truncate(8589934593)
if mode!='final_size':time.sleep(20)
''')
            real_sleep=time.sleep;interrupted=False
            def interrupt_once(seconds):
                nonlocal interrupted
                if interrupted:return real_sleep(min(seconds,.01))
                deadline=time.monotonic()+3
                while not (out/'child.pid').exists() and time.monotonic()<deadline:real_sleep(.01)
                interrupted=True;raise KeyboardInterrupt()
            try:
                with patch.object(builder,'verify_stage',return_value={'source_tree':[]}):
                    if mode=='interrupt':
                        with patch.object(builder.time,'sleep',side_effect=interrupt_once),self.assertRaises(KeyboardInterrupt):builder.build(stage,sysroot,out)
                    elif mode=='final_size':
                        with self.assertRaisesRegex(ValueError,'disk limit'):builder.build(stage,sysroot,out)
                    else:
                        with self.assertRaises(ValueError):builder.build(stage,sysroot,out)
                self.assertTrue((out/'build-receipt.json').is_file(),'interrupted build lost its failed receipt')
                receipt=json.loads((out/'build-receipt.json').read_text())
                self.assertEqual(receipt['status'],'failed');self.assertFalse(receipt['native_admitted'])
                if mode=='final_size':self.assertEqual(receipt['returncode'],0)
                else:
                    real_sleep(2.1)
                    self.assertFalse((out/'late-marker').exists(),'build descendant wrote after failed receipt')
            finally:
                for name in ('parent.pid','child.pid'):
                    p=out/name
                    if p.exists():
                        try:os.kill(int(p.read_text()),signal.SIGKILL)
                        except ProcessLookupError:pass
    def test_disk_limit_stops_signal_ignoring_build_descendants(self):self.run_cpu_build_failure('active')
    def test_final_disk_size_is_checked_even_after_fast_success_exit(self):self.run_cpu_build_failure('final_size')
    def test_interrupted_build_stops_descendants_before_failed_receipt(self):self.run_cpu_build_failure('interrupt')

if __name__=='__main__':unittest.main()
