"""CPU-only: catch missing durable boundaries, call duplication and lost kill exit."""
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from scripts import sdk3_capture_progress as m

class Task:
    def __init__(self):self.calls=0
    def step(self):self.calls+=1
class Sensor:
    def __init__(self,task):self.task=task;self.reads=0
    def get_rgb_array_cpu(self):self.reads+=1;return b'actual-rgb'
    def perceive(self):self.task.step();return self.get_rgb_array_cpu()
class Camera:
    def __init__(self):
        from types import SimpleNamespace
        self.task=Task();self.sensors={k:Sensor(self.task) for k in ('bigbench_road','bigbench_wide')};self.provider=SimpleNamespace(env=SimpleNamespace(engine=SimpleNamespace(sensors=self.sensors,taskMgr=self.task)))
    def capture(self,pose):return tuple(self.sensors['bigbench_'+k].perceive() for k in ('road','wide'))

class ProgressTests(unittest.TestCase):
    def test_original_nested_calls_and_instance_attributes_restore(self):
        with tempfile.TemporaryDirectory() as td:
            c=Camera();j=m.Journal(Path(td),dict(pid=os.getpid(),nonce='cpu'))
            with m.observe(c,j):self.assertEqual(c.capture(None),(b'actual-rgb',b'actual-rgb'))
            j.close();rows=m.read_journal(Path(td)/'progress.jsonl')
            self.assertEqual([r['event'] for r in rows],['capture.enter','perceive.enter','task_step.enter','task_step.return','get_rgb.enter','get_rgb.return','perceive.return','perceive.enter','task_step.enter','task_step.return','get_rgb.enter','get_rgb.return','perceive.return','capture.return'])
            self.assertEqual([r['camera'] for r in rows[1:7]],['road']*6);self.assertEqual(c.task.calls,2);self.assertEqual([s.reads for s in c.sensors.values()],[1,1]);self.assertNotIn('capture',vars(c));self.assertNotIn('step',vars(c.task));self.assertTrue(all('perceive' not in vars(s) and 'get_rgb_array_cpu' not in vars(s) for s in c.sensors.values()))
    def test_exception_propagates_and_owned_override_restores(self):
        with tempfile.TemporaryDirectory() as td:
            c=Camera()
            def fail():raise RuntimeError('real-boundary-error')
            c.sensors['bigbench_road'].get_rgb_array_cpu=fail;j=m.Journal(Path(td),dict(pid=os.getpid(),nonce='cpu'))
            with self.assertRaisesRegex(RuntimeError,'real-boundary-error'):
                with m.observe(c,j):c.capture(None)
            j.close();self.assertIs(c.sensors['bigbench_road'].get_rgb_array_cpu,fail);rows=m.read_journal(Path(td)/'progress.jsonl');self.assertEqual([r['event'] for r in rows[-3:]],['get_rgb.error','perceive.error','capture.error'])
    def test_journal_overflow_does_not_append_unbounded_event(self):
        with tempfile.TemporaryDirectory() as td:
            j=m.Journal(Path(td),dict(pid=os.getpid(),nonce='cpu'));j.emit('checkpoint',value='small');size=(Path(td)/'progress.jsonl').stat().st_size
            with self.assertRaises(ValueError):j.emit('checkpoint',value='x'*5000)
            self.assertEqual((Path(td)/'progress.jsonl').stat().st_size,size);j.close()
    def test_partial_or_reordered_journal_is_not_admitted(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'progress.jsonl';j=m.Journal(Path(td),dict(pid=os.getpid(),nonce='cpu'));j.emit('checkpoint');j.close();raw=p.read_bytes()
            for bad in [raw[:-1],raw+raw,raw.replace(b'"seq":1',b'"seq":4')]:
                p.write_bytes(bad)
                with self.subTest(bad=bad[:30]),self.assertRaises(ValueError):m.read_journal(p)
    def test_getter_cannot_be_claimed_outside_its_sensor_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            j=m.Journal(Path(td),dict(pid=os.getpid(),nonce='cpu'));j.emit('capture.enter',step=1);j.emit('get_rgb.enter',step=1,camera='road');j.close()
            with self.assertRaises(ValueError):m.read_journal(Path(td)/'progress.jsonl')
    def test_real_timed_stack_survives_until_context_exit(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'stacks.log';code="import sys,time;sys.path.insert(0,sys.argv[1]);from scripts.sdk3_capture_progress import stack_watchdog\ndef blocked_capture():time.sleep(.2)\nwith stack_watchdog(sys.argv[2],seconds=.05):blocked_capture()\n"
            subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(Path(__file__).resolve().parents[1]),str(p)],check=True,timeout=5,capture_output=True);self.assertIn('blocked_capture',p.read_text());size=p.stat().st_size;self.assertGreater(size,0)
    def test_real_watchdog_records_killed_child_exit_and_stops_server(self):
        with tempfile.TemporaryDirectory() as td:
            child=subprocess.Popen([sys.executable,'-I','-S','-c','import time;time.sleep(5)']);server=subprocess.Popen([sys.executable,'-I','-S','-c','import time;time.sleep(5)'])
            try:rc=m.wait_observed(child,server,.05,Path(td))
            finally:
                for p in (child,server):
                    if p.poll() is None:p.kill();p.wait()
            receipt=json.loads((Path(td)/'watchdog.json').read_text());self.assertEqual(rc,-9);self.assertTrue(receipt['timed_out']);self.assertEqual(receipt['child_returncode'],-9);self.assertEqual(receipt['pid'],child.pid);self.assertIsNotNone(server.returncode);self.assertIn('stat',receipt['proc_before_kill'])
