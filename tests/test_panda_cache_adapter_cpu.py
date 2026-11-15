import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
try:
    from scripts import panda_cache_adapter_cpu as cpu
except ImportError:
    cpu=None
ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/'docs/evidence/panda-source-dispatch-01/after-fix/build/candidate-libpandagl.so.data'
class CacheCpuHarnessTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(cpu,'bounded CPU adapter evidence harness required')
    def test_actual_normal_and_sanitized_scenarios_ignore_ambient_compiler_injection(self):
        with tempfile.TemporaryDirectory(prefix='pca-proof-') as folder,patch.dict(os.environ,{'CXXFLAGS':'--unrecognized-flag','GCC_EXEC_PREFIX':'/missing/','CPATH':'/missing/','ASAN_OPTIONS':'detect_leaks=0'}):
            out=Path(folder)/'proof';r=cpu.run_cpu(out,CANDIDATE)
            self.assertEqual(r['status'],'CPU_CONTRACT_VERIFIED_NATIVE_BLOCKED');self.assertFalse(r['native_admitted']);self.assertFalse(r.get('candidate_adapter_link_qualified',True));self.assertIs(r['candidate_static'].get('source_activity_extension_present'),False)
            self.assertEqual((r['scenarios_per_build'],len(r['builds'])),(50,2));self.assertTrue(r['normal_sanitized_identical'])
            self.assertEqual(r['builds'][0]['samples']['bootstrap']['replayed'],5)
            self.assertEqual(r['builds'][1]['samples']['delete_mutate']['pack_buffer'],0)
            self.assertEqual(json.loads((out/'receipt.json').read_text()),r)
    def test_ambient_readelf_is_not_executed(self):
        with tempfile.TemporaryDirectory(prefix='pca-readelf-') as folder:
            folder=Path(folder);binary=folder/'readelf';marker=folder/'ambient-used'
            binary.write_text('#!/bin/sh\nprintf called >> '+str(marker)+'\nexec /usr/bin/readelf "$@"\n');binary.chmod(0o755)
            with patch.dict(os.environ,{'PATH':str(folder)+':/usr/bin:/bin'}):r=cpu.run_cpu(folder/'proof',CANDIDATE)
            self.assertFalse(marker.exists(),'ambient readelf ran outside controlled runner')
            self.assertEqual(r['inspection']['tool']['path'],'/usr/bin/readelf')
    def test_inspection_timeout_and_output_are_bounded_by_actual_runner(self):
        self.assertTrue(hasattr(cpu,'inspect_cpu_candidate'),'adapter-owned bounded inspection required')
        real=cpu.run_command
        with tempfile.TemporaryDirectory(prefix='pca-inspect-limit-') as folder:
            for mode,script in (('timeout','import time;time.sleep(5)'),('output','print("X"*131073)')):
                out=Path(folder)/mode;out.mkdir()
                def limited(command,cwd,env,prefix,timeout,byte_limit=1048576):
                    return real([sys.executable,'-c',script],cwd,env,prefix,.05 if mode=='timeout' else 5,65536)
                with self.subTest(mode=mode),patch.object(cpu,'run_command',side_effect=limited),self.assertRaisesRegex(ValueError,mode):cpu.inspect_cpu_candidate(CANDIDATE,out)
    def test_transitive_abi_header_change_rejects_before_output(self):
        with tempfile.TemporaryDirectory(prefix='pca-abi-header-') as folder:
            folder=Path(folder)
            for name in set(cpu.SOURCES)|{'native/readback_return_core.h'}:
                p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
            p=folder/'native/readback_return_core.h';p.write_bytes(p.read_bytes().replace(b'255u',b'127u'))
            with patch.object(cpu,'ROOT',folder),self.assertRaisesRegex(ValueError,'source pin'):cpu.run_cpu(folder/'proof',CANDIDATE)
            self.assertFalse((folder/'proof').exists())
    def test_modified_candidate_rejects_before_creating_output(self):
        with tempfile.TemporaryDirectory(prefix='pca-bad-') as folder:
            folder=Path(folder);bad=folder/'candidate';bad.write_bytes(CANDIDATE.read_bytes()+b'X');out=folder/'proof'
            with self.assertRaises(ValueError):cpu.run_cpu(out,bad)
            self.assertFalse(out.exists())
    def test_existing_evidence_is_preserved(self):
        with tempfile.TemporaryDirectory(prefix='pca-reuse-') as folder:
            out=Path(folder);p=out/'keep';p.write_bytes(b'prior')
            with self.assertRaises(ValueError):cpu.run_cpu(out,CANDIDATE)
            self.assertEqual(p.read_bytes(),b'prior');self.assertEqual(list(out.iterdir()),[p])
    def test_changed_immutable_source_rejects_before_output_creation(self):
        with tempfile.TemporaryDirectory(prefix='pca-source-') as folder:
            folder=Path(folder)
            for name in cpu.SOURCES:
                p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
            p=folder/'native/readback_command_state.h';p.write_bytes(p.read_bytes()+b'\n')
            with patch.object(cpu,'ROOT',folder),self.assertRaisesRegex(ValueError,'source pin'):cpu.run_cpu(folder/'proof',CANDIDATE)
            self.assertFalse((folder/'proof').exists())
    def test_aggregate_sparse_output_limit_rejects(self):
        with tempfile.TemporaryDirectory(prefix='pca-disk-') as folder:
            folder=Path(folder)
            with (folder/'sparse').open('wb') as stream:stream.truncate(67108865)
            with self.assertRaisesRegex(ValueError,'output budget'):cpu.output_budget(folder)
    def test_symlink_fifo_and_metacharacter_paths_reject(self):
        with tempfile.TemporaryDirectory(prefix='pca-path-') as folder:
            folder=Path(folder);link=folder/'link';link.symlink_to(CANDIDATE);fifo=folder/'fifo';os.mkfifo(fifo)
            for candidate in (link,fifo):
                with self.subTest(candidate=candidate),self.assertRaises(ValueError):cpu.run_cpu(folder/'proof',candidate)
            with self.assertRaises(ValueError):cpu.run_cpu(folder/'proof;injected',CANDIDATE)
            self.assertFalse((folder/'proof').exists())
    def test_actual_command_timeout_and_fast_output_overrun_reject(self):
        with tempfile.TemporaryDirectory(prefix='pca-limit-') as folder:
            folder=Path(folder)
            with self.assertRaisesRegex(ValueError,'timeout'):cpu.run_command([sys.executable,'-c','import time;time.sleep(5)'],ROOT,cpu.cpu_environment(),folder/'timeout',.05)
            with self.assertRaisesRegex(ValueError,'output'):cpu.run_command([sys.executable,'-c','import sys;sys.stdout.write("X"*131073)'],ROOT,cpu.cpu_environment(),folder/'overflow',5,65536)
    def test_cli_bad_candidate_returns_failure_without_native_claim(self):
        with tempfile.TemporaryDirectory(prefix='pca-cli-') as folder:
            folder=Path(folder);bad=folder/'bad';bad.write_bytes(b'not candidate')
            p=subprocess.run([sys.executable,'-B','-m','scripts.panda_cache_adapter_cpu','--candidate',str(bad),'--out',str(folder/'proof')],cwd=ROOT,capture_output=True,text=True,timeout=5)
            self.assertEqual(p.returncode,2);self.assertFalse((folder/'proof').exists());self.assertNotIn('CPU_CONTRACT_VERIFIED',p.stdout)
if __name__=='__main__':unittest.main()
