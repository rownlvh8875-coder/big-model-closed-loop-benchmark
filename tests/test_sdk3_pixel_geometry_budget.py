"""CPU-only budget/ownership/observer contracts; never invokes Docker or SDK."""
import json,subprocess,sys,tempfile,unittest,zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from scripts import sdk3_pixel_geometry_budget_native as n,sdk3_pixel_geometry_budget_runtime as r
from scripts.sdk3_capture_progress import Journal,read_journal
from tests.test_sdk3_capture_progress import Camera,Sensor

class Borrowed(Sensor):
    def __init__(self,task):super().__init__(task);self.borrowed=False;self.rgb=np.zeros((604,964,3),np.uint8);self.rgb[494,596]=[17,23,45]
    def get_rgb_array_cpu(self):self.reads+=1;return self.rgb
    def perceive(self):
        self.borrowed=True
        try:self.task.step();return self.get_rgb_array_cpu()
        finally:self.borrowed=False

class BudgetTests(unittest.TestCase):
    def test_seventh_original_read_is_inspected_before_restore_with_no_extra_ticks(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);c=Camera();c.sensors={k:Borrowed(c.task) for k in c.sensors};c.provider.env.engine.sensors=c.sensors;j=Journal(out,dict(pid=11,nonce='ab'*16));seen=[]
            def snapshot(engine,sensor,folder):seen.append((sensor.borrowed,sensor.reads,c.task.calls));return dict(cpu_test_only=True)
            with n.geometry_observe(c,j,out,'ab'*16,snapshot=snapshot):
                for _ in range(7):c.capture(None)
            j.close();manifest=json.loads((out/'geometry-observer.json').read_text());self.assertEqual(seen,[(True,7,13)]);self.assertEqual(c.task.calls,14);self.assertEqual(manifest['observer'],dict(read_attempts=7,reads=7,inspection_attempts=1,inspections=1));self.assertTrue(manifest['observers_restored']);self.assertEqual(manifest['target_pixel_rgb'],[17,23,45]);self.assertEqual(len(zlib.decompress((out/'target-road.rgb.zlib').read_bytes())),1746768);self.assertNotIn('get_rgb_array_cpu',vars(c.sensors['bigbench_road']));read_journal(out/'progress.jsonl')
    def test_snapshot_error_preserves_target_bytes_and_restores_observers(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);c=Camera();c.sensors={k:Borrowed(c.task) for k in c.sensors};c.provider.env.engine.sensors=c.sensors;j=Journal(out,dict(pid=11,nonce='ab'*16))
            def fail(*args):raise RuntimeError('cpu-snapshot-error')
            with self.assertRaisesRegex(RuntimeError,'cpu-snapshot-error'):
                with n.geometry_observe(c,j,out,'ab'*16,snapshot=fail):
                    for _ in range(7):c.capture(None)
            j.close();m=json.loads((out/'geometry-observer.json').read_text());self.assertTrue(m['observers_restored']);self.assertIn('cpu-snapshot-error',m['failure']);self.assertTrue((out/'target-road.rgb.zlib').exists());self.assertNotIn('capture',vars(c));read_journal(out/'progress.jsonl')
    def test_real_harmless_child_uses_600_second_receipt_and_reaps_server(self):
        with tempfile.TemporaryDirectory() as td:
            child=subprocess.Popen([sys.executable,'-I','-S','-c','pass']);server=subprocess.Popen([sys.executable,'-I','-S','-c','import time;time.sleep(3)'])
            try:rc=n.wait_renderer(child,server,160,Path(td))
            finally:
                for process in (child,server):
                    if process.poll() is None:process.kill();process.wait()
            self.assertEqual(rc,0);self.assertEqual(json.loads((Path(td)/'watchdog.json').read_text())['timeout_seconds'],600);self.assertIsNotNone(server.returncode)
    def fixture(self,root):
        owner='ef'*16;cid='cd'*32;actual=dict(Id=cid,Config=dict(Labels={'stage7.sdk3.owner':owner}),HostConfig={},State=dict(Running=False,Pid=0,OOMKilled=False,ExitCode=0));return owner,cid,actual
    def test_actual_attach_uses_630_seconds_and_owned_cleanup(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);owner,cid,actual=self.fixture(root);calls=[]
            def run(cmd,**kw):calls.append((cmd,kw.get('timeout')));return SimpleNamespace(returncode=0)
            with patch.object(r.secrets,'token_hex',return_value=owner),patch.object(r,'inspect_container',side_effect=[None,actual,actual]),patch.object(r.subprocess,'run',side_effect=run):result=r.run_renderer('owned',root/'sdk',root/'renderer',['--repeat','0','--nonce','ab'*16],root/'reference.json')
            self.assertTrue(result['owned_container_removed']);self.assertIn((['docker','start','--attach',cid],630),calls);cmd=json.loads((root/'renderer/command.json').read_text())['argv'];self.assertIn('/work/repo/scripts/sdk3_pixel_geometry_budget_native.py',cmd);self.assertNotIn('/model.onnx',' '.join(cmd));self.assertFalse(result['ownership_unresolved'])
    def test_create_timeout_recovers_only_matching_owned_label(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);owner,cid,actual=self.fixture(root);calls=[]
            def run(cmd,**kw):
                calls.append(cmd)
                if cmd[:2]==['docker','create']:raise subprocess.TimeoutExpired(cmd,90)
                return SimpleNamespace(returncode=0)
            with patch.object(r.secrets,'token_hex',return_value=owner),patch.object(r,'inspect_container',side_effect=[None,actual]),patch.object(r.subprocess,'run',side_effect=run):result=r.run_renderer('owned',root/'sdk',root/'renderer',[],root/'reference.json')
            self.assertTrue(result['owned_container_removed']);self.assertEqual(calls[-1],['docker','rm','--force',cid]);self.assertIn('TimeoutExpired',result['failure'])
    def test_foreign_created_container_is_never_removed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);owner,cid,actual=self.fixture(root);actual['Config']['Labels']['stage7.sdk3.owner']='00'*16;calls=[]
            def run(cmd,**kw):calls.append(cmd);return SimpleNamespace(returncode=0)
            with patch.object(r.secrets,'token_hex',return_value=owner),patch.object(r,'inspect_container',side_effect=[None,actual,actual]),patch.object(r.subprocess,'run',side_effect=run):result=r.run_renderer('owned',root/'sdk',root/'renderer',[],root/'reference.json')
            self.assertTrue(result['ownership_unresolved']);self.assertFalse(result['owned_container_removed']);self.assertFalse(any(cmd[:2]==['docker','rm'] for cmd in calls))
