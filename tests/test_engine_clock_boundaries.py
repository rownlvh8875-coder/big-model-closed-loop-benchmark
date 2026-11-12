"""Synthetic CPU contracts only: no Panda clock, engine, provider or GPU."""
from copy import deepcopy
import importlib
import threading
from types import SimpleNamespace
import unittest

try:
    observer=importlib.import_module('scripts.engine_clock_boundaries')
except ModuleNotFoundError as exc:
    if exc.name!='scripts.engine_clock_boundaries':raise
    observer=None


class FakeClock:
    def __init__(self):
        self.frame=0;self.time=0.;self.count_calls=0;self.time_calls=0
        self.fail_count=None;self.fail_time=None;self.count_values=None;self.time_values=None
    def getFrameCount(self):
        self.count_calls+=1
        if self.count_calls==self.fail_count:raise RuntimeError('count getter failed')
        return self.count_values[self.count_calls-1] if self.count_values is not None else self.frame
    def getFrameTime(self):
        self.time_calls+=1
        if self.time_calls==self.fail_time:raise RuntimeError('time getter failed')
        return self.time_values[self.time_calls-1] if self.time_values is not None else self.time


class FakeManager:
    def __init__(self,clock):
        self._clock=clock;self.steps=0;self.result=object();self.owner_reads=0;self.forbid_owner=False
    @property
    def globalClock(self):
        self.owner_reads+=1
        if self.forbid_owner:raise AssertionError('observer accessed OFF clock owner')
        return self._clock
    def step(self,*args,**kwargs):
        self.steps+=1;self.last_args=(args,kwargs)
        self._clock.frame+=1;self._clock.time+=.125
        return self.result


class FakeTexture:
    def __init__(self):self.image_calls=0;self.seq_calls=0
    def get_image_modified(self):self.image_calls+=1;return self
    def get_seq(self):self.seq_calls+=1;return 123


class FakeCamera:
    def __init__(self,manager):
        self.manager=manager;self.perceives=0;self.reads=0;self.result=object();self.copy_texture=FakeTexture()
        self.ram_error=None;self.duplicate_ram=False;self.catch_duplicate=False;self.skip_step=False
        self.reject_install=False;self.reject_delete=False
    def __setattr__(self,name,value):
        if name=='get_rgb_array_cpu' and vars(self).get('reject_install'):
            raise RuntimeError('setup denied')
        object.__setattr__(self,name,value)
    def __delattr__(self,name):
        if name=='perceive' and self.reject_delete:raise RuntimeError('restore denied')
        object.__delattr__(self,name)
    def perceive(self,*args,**kwargs):
        self.perceives+=1;self.last_args=(args,kwargs)
        if not self.skip_step:self.last_step_result=self.manager.step('step-token',value=4)
        if getattr(self,'forward_ram_kwargs',False):result=self.get_rgb_array_cpu('ram-token',**kwargs)
        else:result=self.get_rgb_array_cpu('ram-token',value=5)
        if self.duplicate_ram:
            try:self.get_rgb_array_cpu()
            except RuntimeError:
                if not self.catch_duplicate:raise
        return result
    def get_rgb_array_cpu(self,*args,**kwargs):
        self.reads+=1;self.last_ram_args=(args,kwargs)
        if self.ram_error:raise self.ram_error
        return self.result


class EngineClockBoundaryTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(observer,'CPU clock-boundary observer required')
    def fixture(self):
        clock=FakeClock();manager=FakeManager(clock);road=FakeCamera(manager);wide=FakeCamera(manager)
        provider=SimpleNamespace(env=SimpleNamespace(engine=SimpleNamespace(taskMgr=manager,
            sensors={'bigbench_road':road,'bigbench_wide':wide})))
        return provider,clock,manager,road,wide
    def pair(self,road,wide):return road.perceive('pose',to_float=False),wide.perceive('pose',to_float=False)
    def assert_inherited_restored(self,manager,road,wide):
        self.assertNotIn('step',vars(manager))
        for camera in (road,wide):
            self.assertNotIn('perceive',vars(camera));self.assertNotIn('get_rgb_array_cpu',vars(camera))

    def test_on_four_boundaries_forwarding_identity_and_exact_original_calls(self):
        p,c,m,r,w=self.fixture();trace={}
        with observer.camera_clock_scope(p,True,trace,max_pairs=1):a,b=self.pair(r,w)
        self.assertIs(a,r.result);self.assertIs(b,w.result);self.assertIs(r.last_step_result,m.result)
        self.assertEqual(r.last_args,(('pose',),{'to_float':False}))
        self.assertEqual(r.last_ram_args,(('ram-token',),{'value':5}))
        self.assertEqual(m.last_args,(('step-token',),{'value':4}))
        self.assertEqual((m.steps,r.perceives,w.perceives,r.reads,w.reads),(2,1,1,1,1))
        self.assertEqual((c.count_calls,c.time_calls),(8,8))
        self.assertEqual([trace['calls'][0]['snapshots'][k]['frame_count'] for k in
                          ('before_perceive','before_ram_method','after_ram_method','after_perceive')],[0,1,1,1])
        self.assertEqual([e['event'] for e in trace['events'][:6]],
            ['perceive_enter','task_step_enter','task_step_return','ram_enter','ram_return','perceive_return'])
        result=observer.validate_clock_trace(trace)
        self.assertEqual((result['clock_snapshots'],result['observer_clock_getter_invocations']),(8,16))
        self.assertFalse(result['clock_pairs_atomic']);self.assertFalse(result['gpu_frame_identity_proven'])
        self.assert_inherited_restored(m,r,w)

    def test_off_never_reads_clock_owner_or_getters_and_keeps_same_method_path(self):
        p,c,m,r,w=self.fixture();m.forbid_owner=True;trace={}
        with observer.camera_clock_scope(p,False,trace,max_pairs=1):self.pair(r,w)
        self.assertEqual((m.owner_reads,c.count_calls,c.time_calls),(0,0,0))
        self.assertEqual((m.steps,r.reads,w.reads),(2,1,1))
        self.assertTrue(all(v is None for row in trace['calls'] for v in row['snapshots'].values()))
        self.assertEqual(observer.validate_clock_trace(trace)['clock_snapshots'],0)
        self.assert_inherited_restored(m,r,w)

    def test_wrapper_internal_names_are_not_consumed_from_original_kwargs(self):
        p,c,m,r,w=self.fixture();r.forward_ram_kwargs=True;w.forward_ram_kwargs=True;token=object();trace={}
        kwargs={'_kind':'wide','_bound':token}
        with observer.camera_clock_scope(p,False,trace,max_pairs=1):
            self.assertIs(r.perceive(**kwargs),r.result)
            self.assertIs(w.perceive(**kwargs),w.result)
        self.assertEqual(r.last_args,((),kwargs));self.assertEqual(w.last_args,((),kwargs))
        self.assertEqual(r.last_ram_args,(('ram-token',),kwargs))
        self.assertEqual(w.last_ram_args,(('ram-token',),kwargs))

    def test_six_pairs_reach_registered_caps_without_extra_original_calls(self):
        p,c,m,r,w=self.fixture();trace={}
        with observer.camera_clock_scope(p,True,trace):
            for _ in range(6):self.pair(r,w)
        self.assertEqual((m.steps,r.reads,w.reads,c.count_calls,c.time_calls),(12,6,6,48,48))
        self.assertEqual(len(trace['events']),72)
        self.assertEqual(observer.validate_clock_trace(trace)['pairs'],6)

    def test_own_attributes_restore_exact_previous_objects(self):
        p,c,m,r,w=self.fixture();saved=[]
        for obj,name in ((m,'step'),(r,'perceive'),(r,'get_rgb_array_cpu'),(w,'perceive'),(w,'get_rgb_array_cpu')):
            bound=getattr(obj,name);setattr(obj,name,bound);saved.append((obj,name,bound))
        with observer.camera_clock_scope(p,True,{},max_pairs=1):self.pair(r,w)
        for obj,name,value in saved:self.assertIs(vars(obj)[name],value)

    def test_partial_setup_failure_restores_every_installed_attribute(self):
        p,c,m,r,w=self.fixture();w.reject_install=True;trace={}
        with self.assertRaisesRegex(RuntimeError,'setup denied'):
            with observer.camera_clock_scope(p,True,trace,max_pairs=1):self.fail('must not enter body')
        self.assertTrue(trace['restoration_complete']);self.assertEqual(m.steps,0)
        self.assert_inherited_restored(m,r,w)

    def test_body_error_is_primary_and_complete_method_calls_do_not_promote_success(self):
        p,c,m,r,w=self.fixture();trace={};primary=RuntimeError('body primary')
        with self.assertRaises(RuntimeError) as got:
            with observer.camera_clock_scope(p,True,trace,max_pairs=1):
                self.pair(r,w);raise primary
        self.assertIs(got.exception,primary);self.assertEqual(trace['status'],'FAILED_OR_INCOMPLETE')
        with self.assertRaises(RuntimeError):observer.validate_clock_trace(trace)
        self.assert_inherited_restored(m,r,w)

    def test_first_time_getter_failure_keeps_returned_count_prefix(self):
        p,c,m,r,w=self.fixture();c.fail_time=1;trace={}
        with self.assertRaisesRegex(RuntimeError,'time getter failed'):
            with observer.camera_clock_scope(p,True,trace,max_pairs=1):r.perceive()
        s=trace['calls'][0]['snapshots']['before_perceive']
        self.assertEqual(s['frame_count'],0);self.assertIsNone(s['frame_time_s'])
        self.assertTrue(s['frame_count_returned']);self.assertFalse(s['frame_time_returned'])
        self.assertEqual((r.perceives,r.reads,m.steps,c.count_calls,c.time_calls),(0,0,0,1,1))
        self.assert_inherited_restored(m,r,w)

    def test_pre_ram_getter_failure_does_not_call_original_ram(self):
        p,c,m,r,w=self.fixture();c.fail_count=2;trace={}
        with self.assertRaisesRegex(RuntimeError,'count getter failed'):
            with observer.camera_clock_scope(p,True,trace,max_pairs=1):r.perceive()
        row=trace['calls'][0]
        self.assertTrue(row['task_step_returned']);self.assertFalse(row['ram_attempted'])
        self.assertEqual((m.steps,r.reads,c.count_calls,c.time_calls),(1,0,2,1))
        self.assert_inherited_restored(m,r,w)

    def test_post_ram_getter_failure_keeps_actual_ram_return(self):
        p,c,m,r,w=self.fixture();c.fail_count=3;trace={}
        with self.assertRaisesRegex(RuntimeError,'count getter failed'):
            with observer.camera_clock_scope(p,True,trace,max_pairs=1):r.perceive()
        row=trace['calls'][0];self.assertTrue(row['ram_returned']);self.assertFalse(row['perceive_returned'])
        self.assertEqual((m.steps,r.reads,c.count_calls,c.time_calls),(1,1,3,2))

    def test_underlying_ram_error_preserves_primary_and_call_bounds(self):
        p,c,m,r,w=self.fixture();primary=RuntimeError('RAM primary');r.ram_error=primary;trace={}
        with self.assertRaises(RuntimeError) as got:
            with observer.camera_clock_scope(p,True,trace,max_pairs=1):r.perceive()
        self.assertIs(got.exception,primary);self.assertEqual((r.reads,m.steps),(1,1))
        self.assertTrue(trace['calls'][0]['ram_attempted']);self.assertFalse(trace['calls'][0]['ram_returned'])
        self.assert_inherited_restored(m,r,w)

    def test_duplicate_ram_is_blocked_and_caught_violation_stays_fatal(self):
        p,c,m,r,w=self.fixture();r.duplicate_ram=True;r.catch_duplicate=True;trace={}
        with self.assertRaises(RuntimeError):
            with observer.camera_clock_scope(p,True,trace,max_pairs=1):
                try:r.perceive()
                except RuntimeError:pass
        self.assertEqual(r.reads,1);self.assertIsNotNone(trace['error'])
        self.assert_inherited_restored(m,r,w)

    def test_wrong_camera_or_orphan_calls_are_blocked_before_original_side_effects(self):
        for which in ('wide','ram','step'):
            p,c,m,r,w=self.fixture();trace={}
            with self.subTest(which=which),self.assertRaises(RuntimeError):
                with observer.camera_clock_scope(p,True,trace,max_pairs=1):
                    {'wide':w.perceive,'ram':r.get_rgb_array_cpu,'step':m.step}[which]()
            self.assertEqual((m.steps,r.reads,w.reads,r.perceives,w.perceives),(0,0,0,0,0))
            self.assert_inherited_restored(m,r,w)

    def test_missing_step_and_incomplete_capture_count_never_validate(self):
        for skip in (True,False):
            p,c,m,r,w=self.fixture();r.skip_step=skip;trace={}
            with self.subTest(skip=skip),self.assertRaises(RuntimeError):
                with observer.camera_clock_scope(p,True,trace,max_pairs=1):r.perceive()
            with self.assertRaises(RuntimeError):observer.validate_clock_trace(trace)

    def test_budget_and_nested_scope_are_blocked_without_extra_original_calls(self):
        p,c,m,r,w=self.fixture();trace={}
        with self.assertRaises(RuntimeError):
            with observer.camera_clock_scope(p,True,trace,max_pairs=1):
                self.pair(r,w);r.perceive()
        self.assertEqual((m.steps,r.reads,w.reads),(2,1,1))
        p,c,m,r,w=self.fixture()
        with self.assertRaises(RuntimeError):
            with observer.camera_clock_scope(p,True,{},max_pairs=1):
                with observer.camera_clock_scope(p,True,{},max_pairs=1):pass
        self.assertEqual(m.steps,0);self.assert_inherited_restored(m,r,w)

    def test_foreign_thread_cannot_issue_original_method_calls(self):
        p,c,m,r,w=self.fixture();trace={};errors=[]
        def target():
            try:r.perceive()
            except BaseException as exc:errors.append(exc)
        with self.assertRaises(RuntimeError):
            with observer.camera_clock_scope(p,True,trace,max_pairs=1):
                t=threading.Thread(target=target);t.start();t.join()
        self.assertEqual(len(errors),1);self.assertEqual((m.steps,r.perceives,r.reads),(0,0,0))

    def test_clock_owner_change_fails_before_original_perceive(self):
        p,c,m,r,w=self.fixture();trace={}
        with self.assertRaises(RuntimeError):
            with observer.camera_clock_scope(p,True,trace,max_pairs=1):m._clock=FakeClock();r.perceive()
        self.assertEqual((m.steps,r.perceives,r.reads),(0,0,0))

    def test_signed_negative_nonmonotonic_finite_observations_are_preserved(self):
        p,c,m,r,w=self.fixture();trace={};c.count_values=[5,4,4,3,-1,-2,-3,-4];c.time_values=[-1.,-2.,-2.,-3.,0.,2.,1.,-4.]
        with observer.camera_clock_scope(p,True,trace,max_pairs=1):self.pair(r,w)
        self.assertEqual(observer.validate_clock_trace(trace)['clock_snapshots'],8)
        self.assertEqual(trace['calls'][1]['snapshots']['after_perceive']['frame_count'],-4)

    def test_invalid_counter_and_nonfinite_time_fail_with_valid_json_prefix(self):
        for count,time in ((True,0.),(2**63,0.),(0,float('nan')),(0,float('inf'))):
            p,c,m,r,w=self.fixture();trace={};c.count_values=[count];c.time_values=[time]
            with self.subTest(count=count,time=time),self.assertRaises(RuntimeError):
                with observer.camera_clock_scope(p,True,trace,max_pairs=1):r.perceive()
            import json
            json.dumps(trace,allow_nan=False)
            self.assertEqual(r.perceives,0)

    def test_restoration_only_error_is_explicit_and_primary_body_error_survives(self):
        for body in (False,True):
            p,c,m,r,w=self.fixture();trace={};primary=RuntimeError('body primary')
            with self.subTest(body=body),self.assertRaises(RuntimeError) as got:
                with observer.camera_clock_scope(p,True,trace,max_pairs=1):
                    self.pair(r,w);r.reject_delete=True
                    if body:raise primary
            self.assertFalse(trace['restoration_complete']);self.assertTrue(trace['restoration_errors'])
            if body:self.assertIs(got.exception,primary);self.assertTrue(primary.__notes__)

    def test_validator_rejects_forged_counts_order_off_values_and_extra_fields(self):
        p,c,m,r,w=self.fixture();trace={}
        with observer.camera_clock_scope(p,False,trace,max_pairs=1):self.pair(r,w)
        bad=[];x=deepcopy(trace);x['counts']['ram_returns']=1;bad.append(x)
        x=deepcopy(trace);x['events'][0]['camera']='wide';bad.append(x)
        x=deepcopy(trace);x['calls'][0]['snapshots']['before_perceive']={'frame_count':0};bad.append(x)
        x=deepcopy(trace);x['unregistered']=1;bad.append(x)
        for x in bad:
            with self.assertRaises(RuntimeError):observer.validate_clock_trace(x)

    def test_configuration_rejected_without_wrapping_or_clock_reads(self):
        p,c,m,r,w=self.fixture()
        for enabled,pairs,trace in ((1,1,{}),(True,True,{}),(True,0,{}),(True,7,{}),(True,1,{'keep':1})):
            with self.subTest(enabled=enabled,pairs=pairs),self.assertRaises(RuntimeError):
                with observer.camera_clock_scope(p,enabled,trace,max_pairs=pairs):pass
        self.assertEqual((m.steps,c.count_calls,c.time_calls),(0,0,0));self.assert_inherited_restored(m,r,w)

    def test_composition_with_unchanged_common_texture_marker_wrapper(self):
        import numpy as np
        from scripts.texture_generation_markers import marker_scope
        p,c,m,r,w=self.fixture();trace={};markers=[]
        r.result=np.zeros((604,964,3),np.uint8);w.result=np.ones((604,964,3),np.uint8)
        with marker_scope(p,True,markers):
            saved=r.get_rgb_array_cpu
            with observer.camera_clock_scope(p,True,trace,max_pairs=1):a,b=self.pair(r,w)
            self.assertIs(vars(r)['get_rgb_array_cpu'],saved)
        self.assertIs(a,r.result);self.assertIs(b,w.result);self.assertEqual(len(markers),2)
        self.assertEqual((r.copy_texture.seq_calls,w.copy_texture.seq_calls),(2,2))
        self.assertEqual(observer.validate_clock_trace(trace)['clock_snapshots'],8)
        self.assert_inherited_restored(m,r,w)


if __name__=='__main__':unittest.main()
