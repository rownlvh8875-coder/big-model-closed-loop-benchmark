"""CPU metadata/command regressions; these fixtures never certify native origin."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from bigbench import recorded_official_execution as c

class DependencyTests(unittest.TestCase):
    def test_descriptor_rejects_extra_missing_mutated_symlink_and_oversize_file(self):
        from bigbench import recorded_official_dependencies as d
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'module.py').write_bytes(b'pure fixture')
            versions={k:v['version'] for k,v in json.loads((c.ROOT/c.RUNTIME).read_text())['packages'].items()}
            with patch.object(d,'installed_versions',return_value=versions):
                desc=d.describe(root);d.verify(root,desc)
                (root/'extra.py').write_bytes(b'extra')
                with self.assertRaises(ValueError):d.verify(root,desc)
                (root/'extra.py').unlink();(root/'module.py').write_bytes(b'changed')
                with self.assertRaises(ValueError):d.verify(root,desc)
                (root/'module.py').unlink()
                with self.assertRaises(ValueError):d.verify(root,desc)
                if os.name!='nt':
                    (root/'module.py').symlink_to(c.ROOT/c.RUNTIME)
                    with self.assertRaises(ValueError):d.describe(root)
                    (root/'module.py').unlink()
                with (root/'huge').open('wb') as stream:stream.truncate(128*1024**2+1)
                with self.assertRaises(ValueError):d.describe(root)
    def test_versions_and_wheel_declaration_are_not_arbitrary(self):
        from bigbench import recorded_official_dependencies as d
        declaration=d.declaration()
        self.assertEqual(len(declaration['packages']),8)
        for name,changes in (('onnxruntime',{'version':'999'}),('sympy',{'url':'https://evil.test/model.whl'}),('protobuf',{'sha256':'0'*64})):
            bad=copy.deepcopy(declaration);bad['packages'][name].update(changes)
            with self.assertRaises(ValueError):d.validate_declaration(bad)
        with tempfile.TemporaryDirectory() as tmp,patch.object(d,'installed_versions',return_value={}):
            with self.assertRaises(ValueError):d.describe(Path(tmp))

@unittest.skipUnless(sys.platform=='linux','Linux-only owned Docker/Xvfb orchestration')
class NativeTests(unittest.TestCase):
    def test_command_keeps_original_resources_and_exact_model_mounts(self):
        from scripts import run_recorded_official as h
        cmd=h.official_command('x',Path('/repo'),Path('/sdk'),Path('/out'),[],owner='a'*32,model=Path('/weights'),deps=Path('/deps'))
        self.assertIn(h.ENTRY,cmd);self.assertIn('--read-only',cmd);self.assertIn('none',cmd)
        for flag,value in (('--memory','10g'),('--cpus','2'),('--pids-limit','128')):self.assertEqual(cmd[cmd.index(flag)+1],value)
        self.assertEqual(sum(v=='--mount' for v in cmd),5)
        with self.assertRaises(ValueError):h.official_command('x',Path('/r'),Path('/s'),Path('/o'),[],owner='a'*32)
    def test_attach_deadline_is_scoped_and_other_commands_are_unchanged(self):
        from scripts import run_recorded_official as h
        import subprocess
        with patch.object(subprocess,'run',return_value='fixture') as run:
            self.assertEqual(h.DeadlineProcess.run(['docker','start','--attach','id'],timeout=18180),'fixture')
            self.assertEqual(run.call_args.kwargs['timeout'],9030)
            h.DeadlineProcess.run(['docker','create'],timeout=90)
            self.assertEqual(run.call_args.kwargs['timeout'],90)
    def test_native_ack_requires_actual_live_child_and_registered_real_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);launch=dict(parent_pid=os.getppid(),seed=c.CASE[0],scenario=c.CASE[1],mode=c.MODE)
            native=dict(pid=os.getpid(),spawn_attempted=True,returncode=None,server_returncode=None)
            (root/'launch.json').write_text(json.dumps(launch));(root/'native-child.json').write_text(json.dumps(native))
            self.assertEqual(c.read_native_ack(root/'owner.json')['pid'],os.getpid())
            for change in ({'pid':1},{'returncode':0},{'spawn_attempted':False},{'server_returncode':0}):
                (root/'native-child.json').write_text(json.dumps(dict(native,**change)))
                with self.assertRaises(ValueError):c.read_native_ack(root/'owner.json')
    def test_original_trial_is_invoked_once_and_original_failure_propagates(self):
        from scripts import recorded_official_native as n
        from bigbench import full_s_recorded_worker as w
        from types import SimpleNamespace
        args=SimpleNamespace(out='fixture-out',nonce='a'*32)
        with patch.object(w,'run_recorded_trial',side_effect=RuntimeError('original')) as body,patch.object(w,'run_camera_canary_trial',side_effect=AssertionError('fixture path')):
            with self.assertRaisesRegex(RuntimeError,'original'):n.invoke_body(args)
            self.assertEqual(body.call_count,1)
            actual=body.call_args.args[0];self.assertEqual((actual.seed,actual.scenario),c.CASE)
            self.assertEqual(Path(actual.out),Path(args.out)/'observed-trial')

if __name__=='__main__':unittest.main()
