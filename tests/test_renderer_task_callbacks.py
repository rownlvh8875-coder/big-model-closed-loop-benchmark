"""Synthetic Python callbacks composed with the real CPU clock observer."""
from copy import deepcopy
import importlib
import sys
import threading
from types import SimpleNamespace
import unittest

from scripts.engine_clock_boundaries import camera_clock_scope
from tests.test_engine_clock_boundaries import FakeClock, FakeCamera, FakeManager

try:
    observer=importlib.import_module('scripts.renderer_task_callbacks')
except ModuleNotFoundError as exc:
    if exc.name!='scripts.renderer_task_callbacks':raise
    observer=None


class PSSM:
    def __init__(self):self.error=None;self.calls=0;self.result=1
    def update(self,task):
        self.calls+=1
        if self.error:raise self.error
        return self.result


class Chase:
    def __init__(self):self.calls=0
    def _chase_task(self,task):self.calls+=1;return 1


def state():
    return dict(pose=dict(xyz_m=[0.,0.,1.22],hpr_deg=[0.,0.,0.]),
                matrices=[[[float(i==j) for j in range(4)] for i in range(4)] for _ in range(2)],
                chase_run_task=True)


class Manager(FakeManager):
    def __init__(self,clock):
        super().__init__(clock);self.pssm=PSSM();self.chase=Chase();self.mode='normal'
    def step(self,*args,**kwargs):
        self.steps+=1;self.last_args=(args,kwargs)
        if self.mode=='unhook':sys.setprofile(None)
        methods=[self.pssm.update,self.chase._chase_task]
        if self.mode=='reverse':methods.reverse()
        if self.mode=='missing':methods=methods[:1]
        if self.mode=='duplicate':methods.insert(1,self.pssm.update)
        if self.mode=='foreign':methods[0]=PSSM().update
        for method in methods:
            try:method(SimpleNamespace(cont=1))
            except BaseException:
                if self.mode!='catch':raise
        self._clock.frame+=1;self._clock.time+=.125
        return self.result


class RendererTaskCallbackTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(observer,'bounded callback observer required')
    def fixture(self):
        m=Manager(FakeClock());r=FakeCamera(m);w=FakeCamera(m)
        p=SimpleNamespace(env=SimpleNamespace(engine=SimpleNamespace(taskMgr=m,
                          sensors={'bigbench_road':r,'bigbench_wide':w})))
        return p,m,r,w
    def scope(self,m,on,trace,clock,*,snapshot=state,pairs=1):
        return observer.task_callback_scope(m,on,trace,clock_trace=clock,max_pairs=pairs,
            targets={'PSSM.update':m.pssm.update,'MainCamera._chase_task':m.chase._chase_task} if on else None,
            snapshot=snapshot if on else None,task_continue=1)

    def test_exact_callbacks_associate_with_road_wide_and_preserve_calls(self):
        p,m,r,w=self.fixture();trace={};clock={}
        with self.scope(m,True,trace,clock),camera_clock_scope(p,True,clock,max_pairs=1):
            self.assertIs(r.perceive(),r.result);self.assertIs(w.perceive(),w.result)
        self.assertEqual((m.steps,r.reads,w.reads,m.pssm.calls,m.chase.calls),(2,1,1,2,2))
        self.assertEqual(m.last_args,(('step-token',),{'value':4}))
        self.assertEqual([s['camera'] for s in trace['steps']],['road','wide'])
        self.assertEqual([e['callback'] for e in trace['steps'][0]['events']],
                         ['PSSM.update']*2+['MainCamera._chase_task']*2)
        self.assertEqual(trace['snapshot_returns'],8)
        self.assertEqual(observer.validate_trace(trace)['native_execution_proven'],False)
        self.assertIsNone(sys.getprofile());self.assertNotIn('step',vars(m))

    def test_reversed_order_is_observed_not_replaced_with_assumed_sort(self):
        p,m,r,w=self.fixture();m.mode='reverse';trace={};clock={}
        with self.scope(m,True,trace,clock),camera_clock_scope(p,False,clock,max_pairs=1):r.perceive();w.perceive()
        self.assertEqual(trace['steps'][0]['events'][0]['callback'],'MainCamera._chase_task')

    def test_off_has_null_callback_evidence_and_no_state_reads_or_profile(self):
        p,m,r,w=self.fixture();trace={};clock={}
        with self.scope(m,False,trace,clock),camera_clock_scope(p,False,clock,max_pairs=1):
            r.perceive();w.perceive();self.assertIsNone(sys.getprofile())
        self.assertEqual([s['events'] for s in trace['steps']],[None,None])
        self.assertEqual(trace['snapshot_attempts'],0)
        self.assertEqual(observer.validate_trace(trace)['observed_callback_events'],None)

    def test_missing_duplicate_and_foreign_self_cannot_complete(self):
        for mode in ('missing','duplicate','foreign'):
            p,m,r,w=self.fixture();m.mode=mode;trace={};clock={}
            with self.subTest(mode=mode),self.assertRaises(observer.CallbackBoundaryError):
                with self.scope(m,True,trace,clock),camera_clock_scope(p,False,clock,max_pairs=1):r.perceive();w.perceive()
            self.assertEqual(trace['status'],'FAILED_OR_INCOMPLETE')
            self.assertIsNone(sys.getprofile());self.assertNotIn('step',vars(m))

    def test_python_exception_unwind_is_not_a_normal_task_continue_return(self):
        p,m,r,w=self.fixture();m.mode='catch';m.pssm.error=RuntimeError('callback broke');trace={};clock={}
        with self.assertRaises(observer.CallbackBoundaryError):
            with self.scope(m,True,trace,clock),camera_clock_scope(p,False,clock,max_pairs=1):r.perceive();w.perceive()
        self.assertIsNotNone(trace['error']);self.assertIsNone(sys.getprofile())

    def test_uncaught_original_callback_exception_identity_is_preserved(self):
        p,m,r,w=self.fixture();error=ValueError('original callback failed');m.pssm.error=error;trace={};clock={}
        with self.assertRaises(ValueError) as caught:
            with self.scope(m,True,trace,clock),camera_clock_scope(p,False,clock,max_pairs=1):r.perceive()
        self.assertIs(caught.exception,error);self.assertIsNone(sys.getprofile())

    def test_removed_hook_and_recursive_callbacks_cannot_complete(self):
        class Recursive(PSSM):
            def update(self,task):
                self.calls+=1
                if self.calls==1:self.update(task)
                return 1
        for mode in ('unhook','recursive'):
            p,m,r,w=self.fixture();trace={};clock={}
            if mode=='recursive':m.pssm=Recursive()
            else:m.mode=mode
            with self.subTest(mode=mode),self.assertRaises(observer.CallbackBoundaryError):
                with self.scope(m,True,trace,clock),camera_clock_scope(p,False,clock,max_pairs=1):r.perceive();w.perceive()
            self.assertIsNone(sys.getprofile())

    def test_callback_scope_stops_extra_original_step_before_budget_overrun(self):
        p,m,r,w=self.fixture();trace={};clock={}
        with self.assertRaises(observer.CallbackBoundaryError):
            with self.scope(m,True,trace,clock),camera_clock_scope(p,False,clock,max_pairs=2):
                r.perceive();w.perceive();r.perceive()
        self.assertEqual(m.steps,2)

    def test_wrong_callback_return_fails_even_if_step_returns(self):
        p,m,r,w=self.fixture();m.pssm.result=None;trace={};clock={}
        with self.assertRaises(observer.CallbackBoundaryError):
            with self.scope(m,True,trace,clock),camera_clock_scope(p,False,clock,max_pairs=1):r.perceive();w.perceive()

    def test_snapshot_exception_caught_by_engine_stays_failed(self):
        p,m,r,w=self.fixture();m.mode='catch';trace={};clock={}
        def broken():raise ValueError('snapshot broke')
        with self.assertRaises(observer.CallbackBoundaryError):
            with self.scope(m,True,trace,clock,snapshot=broken),camera_clock_scope(p,False,clock,max_pairs=1):r.perceive();w.perceive()
        self.assertEqual(trace['snapshot_attempts'],1);self.assertEqual(trace['snapshot_returns'],0)

    def test_snapshot_interruptions_and_deadlines_are_not_swallowed(self):
        for error in (KeyboardInterrupt('stop'),SystemExit(7),TimeoutError('deadline')):
            p,m,r,w=self.fixture();trace={};clock={}
            def interrupted():raise error
            with self.subTest(error=type(error)):
                with self.assertRaises(type(error)) as caught:
                    with self.scope(m,True,trace,clock,snapshot=interrupted),camera_clock_scope(p,False,clock,max_pairs=1):r.perceive()
                self.assertIs(caught.exception,error);self.assertIsNone(sys.getprofile())

    def test_snapshot_receipts_do_not_alias_callers_mutable_arrays(self):
        p,m,r,w=self.fixture();trace={};clock={};shared=state()
        with self.scope(m,True,trace,clock,snapshot=lambda:shared),camera_clock_scope(p,False,clock,max_pairs=1):r.perceive();w.perceive()
        shared['pose']['xyz_m'][0]=42.;shared['matrices'][0][0][0]=9.
        recorded=trace['steps'][0]['events'][0]['state']
        self.assertEqual(recorded['pose']['xyz_m'][0],0.)
        self.assertEqual(recorded['matrices'][0][0][0],1.)

    def test_nonfinite_or_wrong_split_state_fails_before_success(self):
        for bad in (dict(state(),matrices=[]),dict(state(),chase_run_task=1),
                    dict(state(),pose=dict(xyz_m=[float('nan'),0.,0.],hpr_deg=[0.,0.,0.]))):
            p,m,r,w=self.fixture();trace={};clock={}
            with self.subTest(bad=bad),self.assertRaises(observer.CallbackBoundaryError):
                with self.scope(m,True,trace,clock,snapshot=lambda:bad),camera_clock_scope(p,False,clock,max_pairs=1):r.perceive();w.perceive()

    def test_own_step_identity_and_body_exception_restore_exactly(self):
        p,m,r,w=self.fixture();saved=m.step;m.step=saved;trace={};clock={}
        with self.assertRaisesRegex(ValueError,'body failed'):
            with self.scope(m,True,trace,clock),camera_clock_scope(p,False,clock,max_pairs=1):raise ValueError('body failed')
        self.assertIs(m.step,saved);self.assertIsNone(sys.getprofile())

    def test_existing_profile_is_rejected_and_preserved(self):
        p,m,r,w=self.fixture();trace={}
        def prior(*_):pass
        sys.setprofile(prior)
        try:
            with self.assertRaises(observer.CallbackBoundaryError):
                with self.scope(m,True,trace,{}):pass
            self.assertIs(sys.getprofile(),prior)
        finally:sys.setprofile(None)
        self.assertNotIn('step',vars(m))

    def test_orphan_step_and_caught_wrong_thread_remain_failures(self):
        for threaded in (False,True):
            p,m,r,w=self.fixture();trace={};clock={};errors=[]
            def attempt():
                try:m.step()
                except BaseException as exc:errors.append(exc)
            with self.subTest(threaded=threaded),self.assertRaises(observer.CallbackBoundaryError):
                with self.scope(m,False,trace,clock):
                    if threaded:
                        t=threading.Thread(target=attempt);t.start();t.join()
                    else:attempt()
            self.assertEqual(m.steps,0);self.assertTrue(errors)

    def test_six_pairs_bound_snapshots_without_additional_steps(self):
        p,m,r,w=self.fixture();trace={};clock={}
        with self.scope(m,True,trace,clock,pairs=6),camera_clock_scope(p,True,clock,max_pairs=6):
            for _ in range(6):r.perceive();w.perceive()
        self.assertEqual((m.steps,trace['snapshot_returns']),(12,48))

    def test_validator_rejects_forged_state_hash_and_off_empty_events(self):
        for on in (False,True):
            p,m,r,w=self.fixture();trace={};clock={}
            with self.scope(m,on,trace,clock),camera_clock_scope(p,False,clock,max_pairs=1):r.perceive();w.perceive()
            if on:trace['steps'][0]['events'][0]['state']['mvp_sha256']='f'*64
            else:trace['steps'][0]['events']=[]
            with self.assertRaises(observer.CallbackBoundaryError):observer.validate_trace(trace)


if __name__=='__main__':unittest.main()
