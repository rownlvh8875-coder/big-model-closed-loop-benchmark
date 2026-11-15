from pathlib import Path
import json
import tempfile
import subprocess
import shutil
import struct
import unittest
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

if __name__=='__main__':unittest.main()
