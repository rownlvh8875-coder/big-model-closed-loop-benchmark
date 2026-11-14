"""Real lease files and deterministic finite polling; no external/native work."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
try:
    from scripts import engine_clock_held_abba_v2 as n
    from scripts import engine_clock_held_abba_v2_lifecycle as life
except ImportError:n=life=None

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL='docs/evidence/engine-clock-held-abba-01/terminal-failure/selected/engine-clock-held-abba-20261114-01-canary/api/live-run.json'


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


class VisibilityTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(life,'bounded actual-running observer missing')

    def run_fixture(self,status='queued'):
        # Complete recorded HTTP body; only new campaign identity is translated.
        value=json.loads((ROOT/ORIGINAL).read_bytes())
        value.update(head_branch=n.BRANCH,path=n.WORKFLOW,status=status,conclusion=None)
        return value

    def context(self):return dict(repository=n.REPOSITORY,event='push',attempt=1,run_id=43563102068,head_sha='01ca6198d90f3624546b3a28c43507007b6d2354')

    def exercise(self,values,*,deadline=1000.,ticks=None,method='run'):
        clock=Clock();seen=[];items=iter(values)
        class Client:
            def __init__(self,out):self.out=out;self.deadline=deadline
            def get_json(self,endpoint,name):
                seen.append((endpoint,name,self.deadline));value=next(items)
                if isinstance(value,Exception):raise value
                if ticks:clock.now+=ticks[len(seen)-1]
                (self.out/name).write_bytes(json.dumps(value).encode())
                return value
        with tempfile.TemporaryDirectory() as td:
            client=Client(Path(td));result=error=None
            try:
                if method=='run':result=life.observe_running(client,self.context(),clock=clock.clock,pause=clock.pause)
                else:result=life.find_job(client,self.context(),'native-host','caller-job',clock=clock.clock,pause=clock.pause)
            except Exception as exc:error=exc
            retained={p.name:p.read_bytes() for p in client.out.iterdir()}
            return result,error,seen,clock,client.deadline,retained

    def test_recorded_pending_waits_for_actual_active_and_retains_original_alias(self):
        original=json.loads((ROOT/ORIGINAL).read_bytes());self.assertEqual('queued',original['status'])
        result,error,seen,clock,deadline,raw=self.exercise([self.run_fixture(),self.run_fixture(),self.run_fixture('in_progress')])
        self.assertIsNone(error);run,proof=result
        self.assertEqual('in_progress',run['status']);self.assertEqual([5,5],clock.sleeps)
        self.assertEqual(3,len(seen));self.assertEqual(1000.,deadline)
        self.assertEqual([160.,160.,160.],[row[2] for row in seen])
        self.assertEqual(3,proof['snapshots']);self.assertEqual(2,proof['queued_snapshots'])
        self.assertEqual(raw['live-run-02.json'],raw['live-run.json'])
        self.assertEqual(['queued','queued','in_progress'],[json.loads(raw['live-run-%02d.json'%i])['status'] for i in range(3)])

    def test_persistent_queued_expires_without_returning_authority(self):
        result,error,seen,clock,deadline,raw=self.exercise([self.run_fixture() for _ in range(14)])
        self.assertIsInstance(error,ValueError);self.assertIsNone(result)
        self.assertEqual(12,len(seen));self.assertEqual(160.,clock.now);self.assertNotIn('live-run.json',raw)
        self.assertEqual(1000.,deadline)

    def test_each_snapshot_provenance_and_terminal_values_reject_immediately(self):
        for field,value in [('head_sha','9'*40),('head_branch','wrong'),('path','wrong'),('event','workflow_dispatch'),('run_attempt',2),('workflow_id',99),('status','completed'),('status','cancelled'),('conclusion','failure')]:
            bad=self.run_fixture('in_progress');bad[field]=value
            result,error,seen,clock,deadline,raw=self.exercise([self.run_fixture(),bad,self.run_fixture('in_progress')])
            self.assertIsInstance(error,ValueError,field);self.assertEqual(2,len(seen),field);self.assertNotIn('live-run.json',raw)

    def test_http_failure_never_retries_or_creates_active_alias(self):
        result,error,seen,clock,deadline,raw=self.exercise([ValueError('owned HTTP failure'),self.run_fixture('in_progress')])
        self.assertIsInstance(error,ValueError);self.assertEqual(1,len(seen));self.assertEqual([],clock.sleeps);self.assertEqual({},raw);self.assertEqual(1000.,deadline)

    def test_shared_deadline_and_late_active_response_do_not_extend_time(self):
        for end,ticks in [(103.,None),(1000.,[61.])]:
            values=[self.run_fixture()] if ticks is None else [self.run_fixture('in_progress')]
            result,error,seen,clock,deadline,raw=self.exercise(values,deadline=end,ticks=ticks)
            self.assertIsInstance(error,ValueError);self.assertEqual(1,len(seen));self.assertEqual(end,deadline)
            self.assertEqual(min(end,160.),seen[0][2]);self.assertNotIn('live-run.json',raw)

    def jobs(self,status='queued',conclusion=None):
        return dict(total_count=1,jobs=[dict(id=132350924448,name='native-host',run_id=43563102068,head_sha='01ca6198d90f3624546b3a28c43507007b6d2354',run_attempt=1,status=status,conclusion=conclusion,steps=[])])

    def test_caller_job_waits_for_actual_running_under_own_deadline(self):
        result,error,seen,clock,deadline,raw=self.exercise([self.jobs(),self.jobs('in_progress')],method='job')
        self.assertIsNone(error);self.assertEqual('in_progress',result['status']);self.assertEqual([5],clock.sleeps)
        self.assertEqual([130.,130.],[row[2] for row in seen]);self.assertEqual(1000.,deadline)

    def test_terminal_or_malformed_caller_job_has_no_retry(self):
        for bad in [self.jobs('completed','failure'),dict(total_count=2,jobs=self.jobs()['jobs']),dict(total_count=2,jobs=self.jobs()['jobs']*2)]:
            result,error,seen,clock,deadline,raw=self.exercise([bad,self.jobs('in_progress')],method='job')
            self.assertIsInstance(error,ValueError);self.assertEqual(1,len(seen));self.assertEqual([],clock.sleeps)


if __name__=='__main__':unittest.main()
