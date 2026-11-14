"""Actual CPython built-in C-call events on synthetic objects; never native evidence."""
from copy import deepcopy
from hashlib import sha256
import importlib
import sys
import threading
from types import SimpleNamespace
import unittest
from scripts.engine_clock_boundaries import camera_clock_scope
from tests.test_engine_clock_boundaries import FakeClock,FakeCamera,FakeManager
from tests.test_renderer_task_callbacks import state

try:
    observer=importlib.import_module('scripts.renderer_pipeline_observer')
except ModuleNotFoundError as exc:
    if exc.name!='scripts.renderer_pipeline_observer':raise
    observer=None


class PSSM:
    def __init__(self,render):self.render=render;self.matrices=state()['matrices'];self.error=None
    def update(self,task):
        mvp_array=self.matrices
        self.render.extend(mvp_array)
        if self.error:raise self.error
        return 1


class Chase:
    def chase(self,task):return 1


class Engine:
    def __init__(self):self.render=[];self.graphics=[];self.pssm=PSSM(self.render);self.chase=Chase()
    def igloop(self,task):self.graphics.append('frame');return 1


class Manager(FakeManager):
    def __init__(self,clock,engine):super().__init__(clock);self.engine=engine;self.mode='normal'
    def step(self,*args,**kwargs):
        self.steps+=1;self.last_args=(args,kwargs)
        funcs=[self.engine.pssm.update,self.engine.chase.chase,self.engine.igloop]
        if self.mode=='reverse':funcs.reverse()
        if self.mode=='missing':funcs=funcs[:2]
        if self.mode=='unhook':sys.setprofile(None)
        for f in funcs:
            try:f(SimpleNamespace(cont=1))
            except BaseException:
                if self.mode!='catch':raise
        self._clock.frame+=1;self._clock.time+=.125
        return self.result


class RAM(FakeCamera):
    def __init__(self,m):super().__init__(m);self.storage=bytearray(b'RGB');self.error=None
    def get_rgb_array_cpu(self,*args,**kwargs):
        self.reads+=1;self.last_ram_args=(args,kwargs)
        data=self.storage.copy()
        if self.error:raise self.error
        return self.result


def fixture():
    engine=Engine();m=Manager(FakeClock(),engine);r=RAM(m);w=RAM(m)
    engine.taskMgr=m;engine.sensors={'bigbench_road':r,'bigbench_wide':w}
    p=SimpleNamespace(env=SimpleNamespace(engine=engine))
    b=dict(python={'PSSM.update':engine.pssm.update,'MainCamera._chase_task':engine.chase.chase,
        'igLoop':engine.igloop,'road_ram':r.get_rgb_array_cpu,'wide_ram':w.get_rgb_array_cpu},
        c={'shader_inputs':engine.render.extend,'render_frame':engine.graphics.append,
           'road_image_as':r.storage.copy,'wide_image_as':w.storage.copy},
        snapshot=state,submission=lambda raw:dict(matrices=deepcopy(raw)))
    return p,m,r,w,b


class PipelineObserverTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(observer,'bounded pipeline profiler required')
    def scope(self,p,on,t,ct,b,*,pairs=1):
        return observer.pipeline_scope(p.env.engine.taskMgr,p.env.engine.sensors,on,t,
            clock_trace=ct,binding=b if on else None,max_pairs=pairs)
    def run_pair(self,on=True,mode='normal',pairs=1):
        p,m,r,w,b=fixture();m.mode=mode;t={};ct={}
        with self.scope(p,on,t,ct,b,pairs=pairs),camera_clock_scope(p,True,ct,max_pairs=pairs):
            for _ in range(pairs):
                self.assertIs(r.perceive(),r.result);self.assertIs(w.perceive(),w.result)
        return p,m,r,w,b,t,ct

    def test_original_cpu_submission_render_and_ram_calls_are_observed_in_order(self):
        p,m,r,w,b,t,ct=self.run_pair()
        row=t['steps'][0]
        self.assertEqual([(e['event'],e['callback']) for e in row['events']],
            [('call','PSSM.update'),('c_call','shader_inputs'),('c_return','shader_inputs'),('return','PSSM.update'),
             ('call','MainCamera._chase_task'),('return','MainCamera._chase_task'),('call','igLoop'),
             ('c_call','render_frame'),('c_return','render_frame'),('return','igLoop')])
        self.assertEqual([(e['event'],e['callback']) for e in row['ram_events']],
            [('call','RAM.method'),('c_call','RAM.image_as'),('c_return','RAM.image_as'),('return','RAM.method')])
        self.assertEqual((m.steps,r.reads,w.reads,len(p.env.engine.graphics)),(2,1,1,2))
        self.assertEqual(m.last_args,(('step-token',),{'value':4}))
        self.assertIs(r.last_step_result,m.result)
        self.assertTrue(row['result_identity_matched'])
        self.assertFalse(observer.validate_trace(t)['gpu_completion_proven'])
        self.assertIsNone(sys.getprofile());self.assertNotIn('step',vars(m))

    def test_reversed_python_task_order_is_measured_without_extra_render_or_read(self):
        p,m,r,w,b,t,ct=self.run_pair(mode='reverse')
        self.assertEqual(t['steps'][0]['events'][0]['callback'],'igLoop')
        self.assertEqual((m.steps,r.reads,w.reads),(2,1,1))

    def test_off_is_null_and_projects_unobserved_callbacks(self):
        p,m,r,w,b,t,ct=self.run_pair(False)
        self.assertTrue(all(s['events'] is None and s['ram_events'] is None for s in t['steps']))
        self.assertEqual(t['counts']['profile_installs'],0)
        projection=observer.project_callbacks(t)
        self.assertTrue(all(s['events'] is None for s in projection['steps']))
        self.assertEqual(observer.validate_trace(t)['observed_pipeline_events'],None)

    def test_legacy_callback_projection_passes_unchanged_pure_validator(self):
        from scripts.renderer_task_callbacks import validate_trace
        *_,t,ct=self.run_pair()
        p=observer.project_callbacks(t)
        self.assertEqual(validate_trace(p)['observed_callback_events'],8)
        self.assertEqual([e['callback'] for e in p['steps'][0]['events']],['PSSM.update']*2+['MainCamera._chase_task']*2)
        p['steps'][0]['events'][0]['state']['matrices'][0][0][0]=99.
        self.assertEqual(t['steps'][0]['events'][0]['state']['matrices'][0][0][0],1.)

    def test_missing_task_removed_hook_and_foreign_c_owner_fail(self):
        for mode in ('missing','unhook','wrong_c'):
            p,m,r,w,b=fixture();t={};ct={}
            if mode=='wrong_c':b['c']['shader_inputs']=[].extend
            else:m.mode=mode
            with self.subTest(mode=mode),self.assertRaises(observer.PipelineError):
                with self.scope(p,True,t,ct,b),camera_clock_scope(p,True,ct,max_pairs=1):r.perceive();w.perceive()
            self.assertEqual(t['status'],'FAILED_OR_INCOMPLETE');self.assertIsNone(sys.getprofile())

    def test_original_python_exceptions_and_interruptions_keep_identity(self):
        for target in ('pssm','ram','snapshot'):
            p,m,r,w,b=fixture();t={};ct={};error=ValueError('original failure')
            if target=='pssm':p.env.engine.pssm.error=error
            elif target=='ram':r.error=error
            else:
                error=TimeoutError('deadline')
                def failed():raise error
                b['snapshot']=failed
            with self.subTest(target=target):
                with self.assertRaises(type(error)) as caught:
                    with self.scope(p,True,t,ct,b),camera_clock_scope(p,True,ct,max_pairs=1):r.perceive()
                self.assertIs(caught.exception,error);self.assertIsNone(sys.getprofile())

    def test_c_exception_is_not_a_successful_submission(self):
        class FailingPSSM(PSSM):
            def update(self,task):
                mvp_array=self.matrices
                self.render.index(mvp_array)
                return 1
        p,m,r,w,b=fixture();e=p.env.engine;e.pssm=FailingPSSM(e.render);m.mode='catch';t={};ct={}
        b['python']['PSSM.update']=e.pssm.update;b['c']['shader_inputs']=e.render.index
        with self.assertRaises(observer.PipelineError):
            with self.scope(p,True,t,ct,b),camera_clock_scope(p,True,ct,max_pairs=1):r.perceive()
        self.assertIsNotNone(t['error']);self.assertIsNone(sys.getprofile())
        self.assertEqual(t['steps'][0]['events'][-1]['event'],'c_exception')

    def test_caught_malformed_clock_binding_remains_sticky(self):
        for bad in (None,{'call':True,'camera':'road'}):
            p,m,r,w,b=fixture();t={};ct={'calls':[bad]}
            with self.subTest(bad=bad),self.assertRaises(observer.PipelineError):
                with self.scope(p,False,t,ct,b):
                    try:m.step()
                    except Exception:pass
                    ct.clear()
                    with camera_clock_scope(p,True,ct,max_pairs=1):r.perceive();w.perceive()
            self.assertEqual(m.steps,0)

    def test_prior_hook_own_attributes_and_body_error_restore(self):
        p,m,r,w,b=fixture();saved=m.step;m.step=saved;t={};ct={}
        with self.assertRaisesRegex(ValueError,'body'):
            with self.scope(p,True,t,ct,b):raise ValueError('body')
        self.assertIs(m.step,saved);self.assertIsNone(sys.getprofile())
        def prior(*_):pass
        sys.setprofile(prior)
        try:
            with self.assertRaises(observer.PipelineError):
                with self.scope(p,True,{}, {},b):pass
            self.assertIs(sys.getprofile(),prior)
        finally:sys.setprofile(None)

    def test_six_pairs_reach_exact_event_and_snapshot_bounds(self):
        *_,t,ct=self.run_pair(pairs=6)
        checked=observer.validate_trace(t)
        self.assertEqual(checked['observed_pipeline_events'],168)
        self.assertEqual((t['counts']['rig_returns'],t['counts']['submission_returns']),(48,24))
        self.assertEqual(t['counts']['profile_installs'],24)

    def test_wrong_thread_or_caught_extra_step_cannot_complete(self):
        p,m,r,w,b=fixture();t={};ct={};errors=[]
        def other():
            try:m.step()
            except Exception as e:errors.append(e)
        with self.assertRaises(observer.PipelineError):
            with self.scope(p,False,t,ct,b):
                x=threading.Thread(target=other);x.start();x.join()
        self.assertTrue(errors);self.assertEqual(m.steps,0)

    def test_submitted_values_are_copied_and_digest_is_verified(self):
        *_,t,ct=self.run_pair()
        bad=deepcopy(t);bad['steps'][0]['events'][1]['state']['mvp_sha256']='f'*64
        with self.assertRaises(observer.PipelineError):observer.validate_trace(bad)


if __name__=='__main__':unittest.main()
