"""Synthetic factorial receipts; matching fixtures are not native evidence."""
import copy
import importlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from test_native_shadow_sampler import fixture as sampler_fixture
from test_shadow_feedback_probe import binding

CONDITIONS = ('baseline', 'linear', 'shadow_guard', 'both')
SEEDS = (20261109, 20261110)
SCENES = ('s_curve_left_right', 's_curve_right_left')


def module(test):
    test.assertIsNotNone(importlib.util.find_spec('scripts.native_shadow_feedback_matrix'),
                         'independent feedback matrix is not implemented')
    return importlib.import_module('scripts.native_shadow_feedback_matrix')


def fixture(seed, scene, condition, probe=False, repeat=0):
    linear, guard = condition in ('linear','both'), condition in ('shadow_guard','both')
    d = sampler_fixture(seed, scene, 'raw_linear_off' if linear else 'original_off', repeat)
    name = f'{seed}-{scene}-{condition}-{probe}-{repeat}'
    d.update(process_uuid=uuid.uuid5(uuid.NAMESPACE_DNS, name).hex,
             process_id=40000+CONDITIONS.index(condition)*10+int(probe)*2+repeat)
    c = d['shadow_sampler_diagnostic']['configuration']
    c.update(mode='feedback_'+condition, renderer_semantics_experimental=condition!='baseline',
        shadow_guard=dict(enabled=guard, original_camera_states_empty=[True,True], camera_count=2,
            shader_replaced=False, input_priority=1000000,
            inputs=['use_pssm','PSSMShadowAtlas'] if guard else [],
            placeholder=dict(dimensions=[1,1],format='RGBA8',rgba=[255]*4,filters=[1,1]) if guard else None))
    records=[]
    if probe:
        for camera in ('shadow0','shadow1','road','wide'):
            for _ in range(2):
                row=binding(camera,guard,linear)
                row['classification']=('SHADOW_GUARD_PLACEHOLDER_BOUND' if guard and camera.startswith('shadow')
                    else 'SHADOW_ATLAS_READ_WRITE_BINDING_HAZARD' if camera.startswith('shadow')
                    else 'RGB_ATLAS_RAW_LINEAR' if linear else 'RGB_ATLAS_COMPARE_ENABLED')
                records.append(row)
    p=d['shadow_sampler_diagnostic']['terminal_probe']
    p.update(status='TERMINAL_QUERY' if probe else 'OFF', records=records,
        query_duration_s=.008 if probe else 0.,
        method='terminal_feedback_inherited_state_zero_geometry_callback', texture_pixel_extraction=False)
    d['shadow_feedback_trial']=dict(condition=condition, terminal_probe_enabled=probe,
        repeat=repeat, request_uuid=uuid.uuid5(uuid.NAMESPACE_URL,name).hex)
    return d


def build(root, m):
    for seed in SEEDS:
        for scene in SCENES:
            folder=root/f'seed-{seed}'/scene;folder.mkdir(parents=True)
            offset=SEEDS.index(seed)*2+SCENES.index(scene)
            order=CONDITIONS[offset:]+CONDITIONS[:offset]
            rows=[]
            for condition in order:
                for probe,repeat in ((False,0),(False,1),(True,0)):
                    d=fixture(seed,scene,condition,probe,repeat)
                    filename=f'{condition}-{"on" if probe else "off"}_{repeat}.json'
                    (folder/filename).write_text(json.dumps(d))
                    rows.append(dict(sequence_index=len(rows), condition=condition,
                        terminal_probe_enabled=probe, repeat=repeat, filename=filename,
                        request_uuid=d['shadow_feedback_trial']['request_uuid'],
                        process_uuid=d['process_uuid'],process_id=d['process_id'],
                        started_ns=1000+len(rows)*10, finished_ns=1005+len(rows)*10,
                        native_exit_status=0, accepted_exit_status=0))
            (folder/'execution_ledger.json').write_text(json.dumps(dict(seed=seed,scenario=scene,
                condition_order=list(order),entries=rows)))
            (folder/'case_comparison.json').write_text(json.dumps(m.compare_case(root,seed,scene)))


class FeedbackMatrixTests(unittest.TestCase):
    def test_four_cases_balance_each_condition_in_every_position(self):
        m=module(self)
        orders=[m.condition_order(seed,scene) for seed in SEEDS for scene in SCENES]
        self.assertEqual(orders,[['baseline','linear','shadow_guard','both'],
            ['linear','shadow_guard','both','baseline'],['shadow_guard','both','baseline','linear'],
            ['both','baseline','linear','shadow_guard']])
        with self.assertRaises(ValueError):m.condition_order(0,SCENES[0])

    def test_all_twelve_trial_configurations_validate_and_reject_bad_controls(self):
        m=module(self)
        for condition in CONDITIONS:
            for probe,repeat in ((False,0),(False,1),(True,0)):
                d=fixture(SEEDS[0],SCENES[0],condition,probe,repeat)
                m.validate_trial(d,SEEDS[0],SCENES[0],condition,probe,repeat)
                for mutation in ('mode','guard','shader','tasks','pose','clock','source','hash',
                                 'i420','positive','uuid','probe','later_render','flags','unique_cause'):
                    bad=copy.deepcopy(d);diag=bad['shadow_sampler_diagnostic']
                    if mutation=='mode':diag['configuration']['mode']='original'
                    elif mutation=='guard':diag['configuration']['shadow_guard']['enabled']=not (condition in ('shadow_guard','both'))
                    elif mutation=='shader':diag['configuration']['loaded_fragment_shader_sha256']='e'*64
                    elif mutation=='tasks':bad['registered_tasks_after'].remove('PSSM.update')
                    elif mutation=='pose':bad['camera_pose'][0]=[float('nan'),0,0]
                    elif mutation=='clock':bad['clock_timeline'][1]['before']['frame_time_s']+=1
                    elif mutation=='source':bad['raw_sensor_rgb_dims']=[512,256]
                    elif mutation=='hash':bad['source_rgb']['road']['all_frame_sha256'][0]='invalid'
                    elif mutation=='i420':bad['onnx_i420']['all_frame_sha256'].pop()
                    elif mutation=='positive':bad['camera_plus_2m_positive']['wide']=False
                    elif mutation=='uuid':bad['process_uuid']='not-a-uuid'
                    elif mutation=='probe':diag['terminal_probe']['records']=[] if probe else [{}]
                    elif mutation=='later_render':diag['no_render_after_terminal_probe']=False
                    elif mutation=='unique_cause':bad['unique_renderer_cause_proven']=True
                    else:bad['model_scoring_allowed']=True
                    with self.subTest(condition=condition,probe=probe,mutation=mutation):
                        with self.assertRaises(ValueError):m.validate_trial(bad,SEEDS[0],SCENES[0],condition,probe,repeat)

    def test_48_unique_processes_and_real_mismatches_are_reported_without_gate_claim(self):
        m=module(self)
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root,m)
            result=m.aggregate_cases(root)
            self.assertEqual(result['independent_process_count'],48)
            for key in ('original_mdv3_repeatability_proven','unique_renderer_cause_proven','model_scoring_allowed'):
                self.assertIs(result[key],False)
            p=root/f'seed-{SEEDS[0]}'/SCENES[0]/'baseline-off_1.json'
            d=json.loads(p.read_text());d['onnx_i420']['all_frame_sha256'][1]='e'*64;p.write_text(json.dumps(d))
            r=m.compare_case(root,SEEDS[0],SCENES[0])
            self.assertEqual(r['conditions']['baseline']['off_repeat_comparison']['i420']['matched_full_timeline'],9)
            self.assertEqual(r['conditions']['baseline']['off_repeat_comparison']['i420']['first_different_step_1_based'],2)
            self.assertEqual(r['conditions']['baseline']['off_on_comparison_scope'],'temporal_process_observation_only')
            with self.assertRaisesRegex(ValueError,'stale'):m.aggregate_cases(root)

    def test_on_receipts_require_actual_consistent_framebuffer_sample_counts(self):
        m=module(self)
        for condition in CONDITIONS:
            for camera in ('shadow0','road'):
                d=fixture(SEEDS[0],SCENES[0],condition,True)
                row=next(row for row in d['shadow_sampler_diagnostic']['terminal_probe']['records']
                         if row['camera']==camera)
                row['framebuffer_samples']=4
                row['framebuffer_sample_buffers']=0
                with self.subTest(condition=condition,camera=camera):
                    with self.assertRaises(ValueError):m.validate_trial(d,SEEDS[0],SCENES[0],condition,True,0)

    def test_missing_or_reordered_ledger_and_reused_processes_fail(self):
        m=module(self)
        for mutation in ('missing','reorder','reuse_pid','reuse_uuid','nonce','timestamps','exit'):
            with TemporaryDirectory() as tmp:
                root=Path(tmp);build(root,m)
                folder=root/f'seed-{SEEDS[0]}'/SCENES[0];p=folder/'execution_ledger.json'
                d=json.loads(p.read_text())
                if mutation=='missing':d['entries'].pop()
                elif mutation=='reorder':d['entries'][0],d['entries'][3]=d['entries'][3],d['entries'][0]
                elif mutation=='timestamps':d['entries'][1]['started_ns']=1
                elif mutation=='exit':d['entries'][0]['native_exit_status']=2
                else:
                    q=folder/d['entries'][1]['filename'];trial=json.loads(q.read_text())
                    key='process_id' if mutation=='reuse_pid' else 'process_uuid'
                    if mutation=='nonce':trial['shadow_feedback_trial']['request_uuid']='f'*32
                    else:
                        trial[key]=d['entries'][0][key];d['entries'][1][key]=trial[key]
                    q.write_text(json.dumps(trial))
                p.write_text(json.dumps(d))
                with self.subTest(mutation=mutation):
                    with self.assertRaises(ValueError):m.compare_case(root,SEEDS[0],SCENES[0])

    def test_native_wrapper_calls_unchanged_clock_api_with_original_controls(self):
        m=module(self)
        d=fixture(SEEDS[0],SCENES[0],'both',True)
        with patch.object(m,'native_clock',return_value=d) as call:
            m.native_trial(seed=SEEDS[0],scene=SCENES[0],condition='both',probe=True,repeat=0,
                           request_uuid='a'*32)
        self.assertEqual(call.call_args.kwargs,dict(seed=SEEDS[0],scenario=SCENES[0],fraction=.12,
            mode='perceive_sequential',ablation='baseline',frames=10,warmup=2,
            shadow_sampler_mode='feedback_both',terminal_shadow_probe=True))

    def test_native_child_retains_raw_receipt_when_parent_validation_will_fail(self):
        m=module(self)
        d=fixture(SEEDS[0],SCENES[0],'both',True)
        d['shadow_sampler_diagnostic']['terminal_probe']['records'][0]['use_pssm']=1
        with TemporaryDirectory() as tmp:
            out=Path(tmp)/'raw.json'
            with patch.object(m,'native_trial',return_value=d):
                self.assertEqual(m.main(['--mode','native','--seed',str(SEEDS[0]),'--scene',SCENES[0],
                    '--condition','both','--probe','on','--repeat','0','--request-uuid','a'*32,'--out',str(out)]),0)
            saved=json.loads(out.read_text())
            self.assertEqual(saved['shadow_sampler_diagnostic']['terminal_probe']['records'],
                             d['shadow_sampler_diagnostic']['terminal_probe']['records'])
            with self.assertRaises(ValueError):m.validate_trial(saved,SEEDS[0],SCENES[0],'both',True,0)

    def test_case_launcher_writes_complete_ledger_and_preserves_native_failure(self):
        m=module(self)
        for failure in (False,True):
            with TemporaryDirectory() as tmp:
                root=Path(tmp)/'matrix'
                count=[]
                def native(command,**kwargs):
                    count.append(command)
                    if failure:return SimpleNamespace(returncode=7)
                    arg=lambda key:command[command.index(key)+1]
                    d=fixture(int(arg('--seed')),arg('--scene'),arg('--condition'),arg('--probe')=='on',int(arg('--repeat')))
                    d['shadow_feedback_trial']['request_uuid']=arg('--request-uuid')
                    Path(arg('--out')).write_text(json.dumps(d))
                    return SimpleNamespace(returncode=5 if len(count)==1 else 0)
                with patch.object(m.subprocess,'run',side_effect=native):
                    status=m.run_case(root=root,seed=SEEDS[0],scene=SCENES[0])
                self.assertEqual(status,7 if failure else 0)
                folder=root/f'seed-{SEEDS[0]}'/SCENES[0]
                ledger=json.loads((folder/'execution_ledger.json').read_text())
                self.assertEqual(len(count),1 if failure else 12)
                self.assertEqual(ledger['entries'][0]['native_exit_status'],7 if failure else 5)
                self.assertEqual(ledger['entries'][0]['accepted_exit_status'],7 if failure else 0)
                self.assertEqual((folder/'case_comparison.json').exists(),not failure)
                with self.assertRaises(ValueError):m.run_case(root=root,seed=SEEDS[0],scene=SCENES[0])


class FeedbackLauncherTests(unittest.TestCase):
    def invoke(self,status,*,write=True,invalid=False,stale=False):
        m=module(self)
        with TemporaryDirectory() as tmp:
            out=Path(tmp)/'trial.json'
            if stale:out.write_text('{}')
            def native(command,**kwargs):
                self.assertEqual(command[:2],['xvfb-run','-a'])
                self.assertIn('scripts.native_shadow_feedback_matrix',command)
                self.assertEqual(command[command.index('--mode')+1],'native')
                if write:
                    d=fixture(SEEDS[0],SCENES[0],'baseline',True)
                    d['shadow_feedback_trial']['request_uuid']=command[command.index('--request-uuid')+1]
                    if invalid:d['registered_tasks_after'].remove('PSSM.update')
                    out.write_text(json.dumps(d))
                return SimpleNamespace(returncode=status)
            with patch.object(m.subprocess,'run',side_effect=native):
                return m.launch_trial(seed=SEEDS[0],scene=SCENES[0],condition='baseline',
                    probe=True,repeat=0,out=out)

    def test_fresh_complete_receipt_required_for_zero_and_xvfb_cleanup_five(self):
        for status in (0,5):
            self.assertEqual(self.invoke(status),0)
            with self.assertRaises(ValueError):self.invoke(status,invalid=True)
            with self.assertRaises(FileNotFoundError):self.invoke(status,write=False)
        with self.assertRaises(ValueError):self.invoke(5,stale=True)

    def test_all_other_native_statuses_are_preserved(self):
        for status in (1,2,7,-9):self.assertEqual(self.invoke(status),status)
