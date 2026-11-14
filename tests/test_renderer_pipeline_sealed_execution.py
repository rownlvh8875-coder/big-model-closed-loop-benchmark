"""Synthetic camera bytes + callback metadata; no native acquisition authority."""
import copy
from pathlib import Path
import tempfile
import unittest
import numpy as np
import json
import test_engine_clock_held_abba_v3_execution as oldexecution
from test_renderer_pipeline_sealed_v1 import request
from scripts import engine_clock_boundaries as clock
from scripts import renderer_task_callbacks as cb
from tests import test_renderer_task_callbacks as synthetic
import test_engine_clock_native as oldtests
try:
    from scripts import renderer_pipeline_case as case
    from scripts import renderer_pipeline_sealed_v1 as n
    from scripts import renderer_pipeline_scopes as scopes
except ImportError:case=n=scopes=None


def callback_data(on):
    from tests import test_renderer_pipeline_observer as pipe
    from scripts import renderer_pipeline_observer as observer
    p,m,r,w,b=pipe.fixture();trace={};ct={}
    with observer.pipeline_scope(m,p.env.engine.sensors,on,trace,clock_trace=ct,binding=b if on else None,max_pairs=6),clock.camera_clock_scope(p,True,ct,max_pairs=6):
        for _ in range(6):r.perceive();w.perceive()
    count=48 if on else 0;submitted=24 if on else 0
    return dict(pipeline_enabled=on,pipeline_trace=trace,callback_enabled=on,
        callback_trace=observer.project_callbacks(trace),clock_trace=ct,clock_enabled=True,
        main_thread_id=trace['owner_thread'],callback_reader_counts=dict(snapshots_attempted=count,snapshots_returned=count,
        named_getter_attempts=35*count,named_getter_returns=35*count,private_matrix_allocations=2*count,
        private_matrix_assignments=2*count,vector_component_reads=6*count,matrix_array_reads=2*count),
        submission_reader_counts=dict(snapshots_attempted=submitted,snapshots_returned=submitted,
            named_getter_attempts=32*submitted,named_getter_returns=32*submitted,private_matrix_allocations=2*submitted,
            private_matrix_assignments=2*submitted,matrix_array_reads=2*submitted))


def fixture(root,phase='canary'):
    original,cases=oldtests.DatasetTests().fixture(Path(root),phase)
    for i,data in enumerate(cases):
        data.update(schema=case.CASE_SCHEMA,status='RENDERER_PIPELINE_CAMERA_REPLAY_RECORDED',protocol=case.PROTOCOL,limitation=case.LIMITATION)
        data.update(callback_data(n.callback_schedule(phase)[i]));original['launches'][i]['clock_enabled']=True
        (Path(root)/f'case_{i:02d}/case.json').write_bytes(n.canonical(data))
    return original,cases


def archive_fixture(root):
    root=Path(root);_,ctx,_,lease,phase=oldexecution.fixture(root)
    def read(name):return json.loads((root/name).read_bytes())
    def write(name,value):(root/name).write_bytes(n.canonical(value))
    req=request();raw=n.canonical(req);ctx.update(request_sha256=n.sha(raw),producer_request_sha256=n.sha(raw))
    binding=read('binding/binding.json')
    identity=n.identity_from_profiles(binding['receipt'],req['image_evidence']['expected'],binding['host'],binding['engine'],binding['identity']['host_details'])
    binding.update(schema='renderer-pipeline-sealed-binding-v1',request=req,producer_request=req,context=ctx,identity=identity)
    bsha=n.sha(n.canonical(binding))
    data=read('output/case_00/case.json');data.update(callback_data(True))
    data.update(schema=case.CASE_SCHEMA,status='RENDERER_PIPELINE_CAMERA_REPLAY_RECORDED',protocol=case.PROTOCOL,
                limitation=case.LIMITATION,context=ctx,source_snapshot=req['source_closure'],runtime=identity,request_sha256=n.sha(raw))
    write('output/case_00/case.json',data)
    for name,value in [('consumed-request.json',req),('producer-request.json',req),('source-authentication.json',ctx),('binding/binding.json',binding)]:write(name,value)
    for tag in ('parent','child-00'):
        proof=read('output/'+tag+'-admission.json');proof.update(identity=identity,binding_sha256=bsha)
        if tag=='child-00':proof['permit'].update(binding_sha256=bsha,identity_sha256=identity['core_sha256'])
        write('output/'+tag+'-admission.json',proof)
        p='output/'+tag+'-identity-comparison.json';d=read(p)
        d.update(observed=identity,observed_sha256=n.sha(n.canonical(identity)),accepted_sha256=n.sha(n.canonical(identity)));write(p,d)
    phase.update(schema='renderer-pipeline-sealed-phase-v1',status=n.recorded_status('canary'),context=ctx,identity=identity,
                 binding_sha256=bsha,budget=n.BUDGET,native_budget=n.native_budget('canary'))
    write('output/phase.json',phase);phase['member_audit']=n.audit_phase_members(root/'output','canary');write('output/phase.json',phase)
    control=read('controller.json');control.update(status=n.recorded_status('canary'),context=ctx,identity=identity,phase_sha256=n.sha(n.canonical(phase)));write('controller.json',control)
    result=read('result.json');result['status']=n.recorded_status('canary');write('result.json',result)
    return req,ctx


class RendererSealedExecutionTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(case,'new complete case/raw validator required')
    def test_full_synthetic_raw_canvas_i420_and_callback_case_replays(self):
        for phase in ('canary','abba'):
            with tempfile.TemporaryDirectory() as td:
                original,cases=fixture(td,phase)
                for i,data in enumerate(cases):
                    binding=dict(phase=phase,parent_pid=original['parent_pid'],parent_uuid=original['parent_uuid'],
                        context=original['context'],source_snapshot=original['source_snapshot'],runtime=original['runtime'],request_sha256=original['request_sha256'])
                    case._validate_case(Path(td)/f'case_{i:02d}',data,original['launches'][i],binding)
    def test_incomplete_or_unassociated_callbacks_and_reader_budget_fail_closed(self):
        baseline=callback_data(True)
        for mutate in (lambda d:d['callback_trace']['steps'][0].update(camera='wide'),
                       lambda d:d['callback_reader_counts'].update(named_getter_returns=0),
                       lambda d:d.update(callback_enabled=False),
                       lambda d:d['clock_trace']['calls'][0].update(camera='wide'),
                       lambda d:d['pipeline_trace']['steps'][0]['events'].pop(),
                       lambda d:d['submission_reader_counts'].update(named_getter_returns=0),
                       lambda d:d['callback_trace']['steps'][0]['events'][0]['state']['pose']['xyz_m'].__setitem__(0,99.)):
            d=copy.deepcopy(baseline);d.update(phase='canary',index=0);mutate(d)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):n.validate_callback_metadata(d)
    def test_off_callbacks_null_but_clock_snapshots_are_observed(self):
        d=callback_data(False);d.update(phase='abba',index=0);n.validate_callback_metadata(d)
        self.assertEqual(clock.validate_clock_trace(d['clock_trace'])['clock_snapshots'],48)
        d['callback_trace']['steps'][0]['events']=[]
        with self.assertRaises(ValueError):n.validate_callback_metadata(d)
    def test_callback_comparison_is_separate_from_common_clock_comparison(self):
        with tempfile.TemporaryDirectory() as td:
            _,cases=fixture(td,'abba');rows=case._comparisons(cases)
            self.assertEqual(len(rows),6)
            self.assertTrue(all(r['clock_observed'] for r in rows))
            self.assertEqual(rows[3]['callback_comparison_kind'],'ON/ON')
            self.assertIsNone(rows[0]['callback_states_equal'])
    def test_scope_composition_does_not_bind_off_callback_owners(self):
        p,m,r,w=synthetic.RendererTaskCallbackTests().fixture()
        r.result=np.zeros((604,964,3),np.uint8);w.result=np.zeros((604,964,3),np.uint8)
        d=dict(clock_enabled=True,clock_trace={},markers=[])
        def forbidden(_):raise AssertionError('OFF native callback binding')
        with scopes.observers(p,d,False,binder=forbidden):
            for _ in range(6):r.perceive();w.perceive()
        self.assertEqual(m.steps,12);self.assertEqual(d['callback_reader_counts']['named_getter_returns'],0)
        self.assertEqual(clock.validate_clock_trace(d['clock_trace'])['clock_snapshots'],48)

    def test_complete_canary_archive_and_inner_raw_replay_require_callbacks(self):
        from scripts import renderer_pipeline_sealed_v1_archive as archive
        from scripts import renderer_pipeline_sealed_v1_container as child
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);req,ctx=archive_fixture(p/'original');z=p/'synthetic.zip'
            oldexecution.zip_fixture(p/'original',z)
            checked=archive.validate_native_canary_archive(z,p/'selected',req,ctx,
                dict(id=51,name=n.artifact('canary'),size_in_bytes=z.stat().st_size,digest='sha256:'+n.sha(z.read_bytes())))
            self.assertFalse(checked['independent_pixel_replay'])
            effective=request('abba');effective['acceptance']['lease_sha256']=ctx['lease_sha256']
            replay=child.replay_canary(p/'selected/output',json.loads((p/'selected/output/phase.json').read_text()),effective)
            self.assertEqual(replay['capture_pairs'],6)

    def test_canary_archive_cannot_accept_wrong_callback_getter_receipt(self):
        from scripts import renderer_pipeline_sealed_v1_archive as archive
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);req,ctx=archive_fixture(p/'original')
            path=p/'original/output/case_00/case.json';data=json.loads(path.read_text())
            data['callback_reader_counts']['named_getter_returns']=0;path.write_bytes(n.canonical(data))
            z=p/'bad.zip';oldexecution.zip_fixture(p/'original',z)
            with self.assertRaises(ValueError):archive.validate_native_canary_archive(z,p/'selected',req,ctx,
                dict(id=51,name=n.artifact('canary'),size_in_bytes=z.stat().st_size,digest='sha256:'+n.sha(z.read_bytes())))


if __name__=='__main__':unittest.main()
