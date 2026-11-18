"""Evidence ownership handoff; native/render/model code is never used."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from scripts import run_recorded_worker_canary as host


@unittest.skipUnless(sys.platform=='linux','Linux evidence ownership')
class HandoffTests(unittest.TestCase):
    def test_handoff_requires_owned_removed_container_and_never_follows_link(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);native=root/'native';native.mkdir()
            with patch.object(host.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'',b'')) as run:
                for execution in ({'owned_container_removed':False},{'owned_container_removed':True,'ownership_unresolved':True}):
                    with self.assertRaises(ValueError):host.handoff_evidence(native,execution)
                run.assert_not_called()
                result=host.handoff_evidence(native,dict(owned_container_removed=True,ownership_unresolved=False))
                self.assertEqual(result['status'],'EVIDENCE_HANDED_TO_RUNNER')
                argv=run.call_args.args[0]
                self.assertIn('--no-dereference',argv);self.assertIn('--from=65534:65534',argv)
                self.assertEqual(argv[-1],str(native.absolute()))
                link=root/'link';link.symlink_to(native,target_is_directory=True)
                with self.assertRaises(ValueError):host.handoff_evidence(link,dict(owned_container_removed=True,ownership_unresolved=False))

    @unittest.skipUnless(os.environ.get('GITHUB_ACTIONS')=='true' and shutil.which('sudo'), 'actual different-UID check runs on hosted Linux CI')
    def test_actual_private_writer_uid_becomes_readable_only_after_stopped_handoff(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);root.chmod(0o755);native=root/'native';native.mkdir(mode=0o777);native.chmod(0o777)
            script="from pathlib import Path; import sys; p=Path(sys.argv[1])/'private';p.mkdir(mode=0o700);(p/'evidence').write_bytes(b'actual uid handoff')"
            subprocess.run(['sudo','-n','-u','#65534','/usr/bin/python3','-I','-S','-B','-c',script,str(native)],check=True,timeout=10)
            try:
                with self.assertRaises(PermissionError):(native/'private/evidence').read_bytes()
                host.handoff_evidence(native,dict(owned_container_removed=True,ownership_unresolved=False))
                self.assertEqual((native/'private/evidence').read_bytes(),b'actual uid handoff')
                self.assertEqual((native/'private').stat().st_uid,os.getuid())
                self.assertEqual((native/'private').stat().st_mode&0o777,0o700)
            finally:
                subprocess.run(['sudo','-n','chown','-R','--no-dereference',str(os.getuid())+':'+str(os.getgid()),'--',str(native)],check=True,timeout=10)
