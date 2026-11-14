"""Real lease files and deterministic finite polling; no external/native work."""
import copy
from pathlib import Path
import tempfile
import unittest
try:
    from scripts import engine_clock_held_abba as n
    from scripts import engine_clock_held_abba_lifecycle as life
except ImportError:n=life=None


class Clock:
    def __init__(self):self.now=100.;self.sleeps=[]
    def clock(self):return self.now
    def pause(self,s):self.sleeps.append(s);self.now+=s


class LifecycleTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(life,'retained host lease/control boundary missing')
    def facts(self):return dict(head_sha='2'*40,producer_head_sha='2'*40,source_sha='1'*40,run_id=21,workflow_id=31,job_id=41)

    def test_lease_rejects_different_run_boot_producer_and_elapsed_lifetime(self):
        ctx=self.facts();boot=b'01234567-0123-4567-89ab-0123456789ab\n'
        lease=life.create_lease(ctx,boot,100.)
        life.validate_lease(lease,ctx,boot,101.)
        for key,value in [('job_id',42),('head_sha','3'*40),('run_id',22)]:
            bad=dict(ctx);bad[key]=value
            with self.assertRaises(ValueError):life.validate_lease(lease,bad,boot,101.)
        for data,now in [(boot.replace(b'01234567',b'11234567',1),101.),(boot,99.),(boot,6100.)]:
            with self.assertRaises(ValueError):life.validate_lease(lease,ctx,data,now)

    def test_private_lease_is_once_only_and_symlink_or_hardlink_rejects(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'lease.json';lease=life.create_lease(self.facts(),b'01234567-0123-4567-89ab-0123456789ab\n',100.)
            life.write_lease(path,lease);self.assertEqual(0o600,path.stat().st_mode&0o777)
            self.assertEqual(lease,life.read_lease(path))
            with self.assertRaises(ValueError):life.write_lease(path,lease)
            link=Path(td)/'alias';link.symlink_to(path)
            with self.assertRaises(ValueError):life.read_lease(link)
            import os
            os.link(path,Path(td)/'hard')
            with self.assertRaises(ValueError):life.read_lease(path)

    def test_pending_control_snapshots_keep_finite_cadence(self):
        clock=Clock();items=iter(['C','C','A']);saved=[]
        result=life.bounded_poll(lambda:next(items),lambda x:x=='A',lambda i,v:saved.append((i,v)),clock=clock.clock,pause=clock.pause,seconds=20,maximum=5)
        self.assertEqual('A',result);self.assertEqual([(0,'C'),(1,'C'),(2,'A')],saved)
        self.assertEqual([5,5],clock.sleeps)

    def test_http_failure_late_result_and_poll_limit_never_retry(self):
        clock=Clock();calls=[]
        def fail():calls.append(1);raise ValueError('owned HTTP failure')
        with self.assertRaises(ValueError):life.bounded_poll(fail,lambda x:True,lambda *a:None,clock=clock.clock,pause=clock.pause,seconds=20,maximum=5)
        self.assertEqual(1,len(calls));self.assertEqual([],clock.sleeps)
        def late():clock.now+=4;return 'A'
        with self.assertRaises(ValueError):life.bounded_poll(late,lambda x:True,lambda *a:None,clock=clock.clock,pause=clock.pause,seconds=3,maximum=5)
        clock=Clock();calls=[]
        def pending():calls.append(1);return None
        with self.assertRaises(ValueError):life.bounded_poll(pending,lambda x:False,lambda *a:None,clock=clock.clock,pause=clock.pause,seconds=100,maximum=2)
        self.assertEqual(2,len(calls))


if __name__=='__main__':unittest.main()
