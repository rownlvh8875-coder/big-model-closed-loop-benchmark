"""Synthetic receipt contracts, never evidence of native determinism."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_native_capture_schedule import fixture as capture_fixture
from test_shadow_sampler_probe import binding
from scripts.compare_native_shadow_sampler import (
    ARMS, SHADER_SHA256, validate_sampler_trial, compare_scene, aggregate_scenes,
)
from scripts.run_native_shadow_sampler_trial import run_trial


def fixture(seed, scene, arm, index):
    d = capture_fixture(seed, scene, 'sequential_road_first', index)
    mode, probe = ARMS[arm]
    d.update(process_uuid=f'{seed}-{scene}-{arm}-{index}',
             process_id=30000+list(ARMS).index(arm)*10+index)
    for i,row in enumerate(d['clock_timeline']):
        before=dict(frame_time_s=i*.1,real_time_s=i*.2,dt_s=.05)
        after=dict(frame_time_s=(i+1)*.1,real_time_s=i*.2+.15,dt_s=.05)
        row['before'].update(before);row['after'].update(after)
        row['global_clock_time_delta_s']=after['frame_time_s']-before['frame_time_s']
        row['real_time_delta_s']=after['real_time_s']-before['real_time_s']
    rows=[]
    if probe:
        for camera in ('road','wide'):
            for _ in range(2):
                rows.append(dict(binding(effective_compare_mode=0 if mode=='raw_linear' else 0x884e),
                    program=10, unit=3, texture_compare_mode=0 if mode=='raw_linear' else 0x884e,
                    camera=camera, sampler=1, comparison_state_source='sampler_object',
                    classification='RAW_DEPTH_SAMPLER_CONSISTENT' if mode=='raw_linear'
                                   else 'NONSHADOW_DEPTH_COMPARE_ENABLED',
                    query_duration_s=.001, driver=dict(vendor='synthetic',renderer='synthetic',version='synthetic')))
    d['shadow_sampler_diagnostic']={
        'configuration':dict(mode=mode, filters_before=[6,6],
            filters_after=[1,1] if mode=='raw_linear' else [6,6],
            metadrive_version='0.4.3',loaded_fragment_shader_sha256=SHADER_SHA256,
            shader_edited=False,manual_pcf_sampler2d_confirmed=True,
            renderer_semantics_experimental=mode!='original'),
        'terminal_probe':dict(status='TERMINAL_QUERY' if probe else 'OFF',records=rows,
            query_duration_s=.004 if probe else 0.,
            scope='moved_pose_positive_control_after_all_primary_frames',
            primary_frames_instrumented=False,callbacks_removed=True,
            method='terminal_inherited_state_zero_geometry_callback',per_primitive_state_trace=False),
        'no_render_after_terminal_probe':True,
        'terminal_diagnostic_wall_time_s':1.,
    }
    return d


def build(root):
    for seed in (20261109,20261110):
        for scene in ('s_curve_left_right','s_curve_right_left'):
            folder=root/f'seed-{seed}'/scene
            folder.mkdir(parents=True)
            for arm in ARMS:
                for i in (0,1):
                    (folder/f'{arm}-run_{i}.json').write_text(json.dumps(fixture(seed,scene,arm,i)))
            (folder/'case_comparison.json').write_text(json.dumps(compare_scene(root,seed,scene)))


class ShadowSamplerReceiptTests(unittest.TestCase):
    def test_incomplete_or_error_bearing_gpu_binding_chain_cannot_pass(self):
        for mutation in ('program','unit','texture_compare_mode','negative_sampler','error','fallback_conflict'):
            with self.subTest(mutation=mutation):
                d=fixture(20261109,'s_curve_left_right','original_probe',0)
                row=d['shadow_sampler_diagnostic']['terminal_probe']['records'][0]
                if mutation in ('program','unit','texture_compare_mode'):del row[mutation]
                elif mutation=='negative_sampler':row['sampler']=-1
                elif mutation=='error':row['error']='RuntimeError: query failed'
                else:
                    row.update(sampler=0,comparison_state_source='texture',texture_compare_mode=0)
                with self.assertRaises(ValueError):
                    validate_sampler_trial(d,20261109,'s_curve_left_right','original_probe')

    def test_raw_clock_values_and_derived_deltas_are_verified_instead_of_trusting_flag(self):
        for mutation in ('missing','nan','negative_dt','negative_delta','wrong_delta',
                         'frame_time_gap','wall_time_reversal','bool'):
            with self.subTest(mutation=mutation):
                d=fixture(20261109,'s_curve_left_right','original_off',0)
                rows=d['clock_timeline'];row=rows[1]
                if mutation=='missing':del row['before']['real_time_s']
                elif mutation=='nan':row['after']['frame_time_s']=float('nan')
                elif mutation=='negative_dt':row['before']['dt_s']=-.01
                elif mutation=='negative_delta':row['real_time_delta_s']=-5
                elif mutation=='wrong_delta':row['global_clock_time_delta_s']+=.1
                elif mutation=='frame_time_gap':row['before']['frame_time_s']+=.01
                elif mutation=='wall_time_reversal':row['before']['real_time_s']-=.1
                else:row['after']['dt_s']=True
                with self.assertRaises(ValueError):
                    validate_sampler_trial(d,20261109,'s_curve_left_right','original_off')

    def test_four_arms_require_distinct_processes_and_exact_sha_comparisons(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); build(root)
            result=aggregate_scenes(root)
            self.assertEqual(result['independent_process_count'],32)
            self.assertFalse(result['original_mdv3_repeatability_proven'])
            self.assertFalse(result['unique_renderer_cause_proven'])
            self.assertEqual(len(result['per_scene']),4)

    def test_mislabeled_configuration_probe_and_false_gpu_claims_are_rejected(self):
        for mutation in ('mode','filters','shader','off_rows','off_duration','probe_scope',
                         'missing_wide','wrong_texture','wrong_compare','stale_classification',
                         'gl_error','negative_duration','callback','later_render','shader_edit'):
            with self.subTest(mutation=mutation):
                arm='original_probe' if mutation not in ('off_rows','off_duration') else 'original_off'
                d=fixture(20261109,'s_curve_left_right',arm,0)
                diagnostic=d['shadow_sampler_diagnostic']; c=diagnostic['configuration'];p=diagnostic['terminal_probe']
                if mutation=='mode':c['mode']='raw_linear'
                elif mutation=='filters':c['filters_after']=[1,1]
                elif mutation=='shader':c['loaded_fragment_shader_sha256']='e'*64
                elif mutation=='off_rows':p['records']=[{}]
                elif mutation=='off_duration':p['query_duration_s']=.1
                elif mutation=='probe_scope':p['primary_frames_instrumented']=True
                elif mutation=='missing_wide':p['records']=[r for r in p['records'] if r['camera']=='road']
                elif mutation=='wrong_texture':p['records'][0]['bound_texture']=99
                elif mutation=='wrong_compare':p['records'][0]['effective_compare_mode']=0
                elif mutation=='stale_classification':p['records'][0]['classification']='RAW_DEPTH_SAMPLER_CONSISTENT'
                elif mutation=='gl_error':p['records'][0]['gl_error_after']=0x502
                elif mutation=='negative_duration':p['query_duration_s']=-1
                elif mutation=='callback':p['callbacks_removed']=False
                elif mutation=='later_render':diagnostic['no_render_after_terminal_probe']=False
                else:c['shader_edited']=True
                with self.assertRaises(ValueError):validate_sampler_trial(d,20261109,'s_curve_left_right',arm)

    def test_altered_summary_and_process_reuse_fail_aggregation(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root)
            folder=root/'seed-20261109/s_curve_left_right'
            p=folder/'case_comparison.json'
            d=json.loads(p.read_text());d['independent_process_count']=7;p.write_text(json.dumps(d))
            with self.assertRaises(ValueError):aggregate_scenes(root)
            p=folder/'raw_linear_off-run_0.json';d=json.loads(p.read_text());d['process_id']=30000;p.write_text(json.dumps(d))
            with self.assertRaises(ValueError):compare_scene(root,20261109,'s_curve_left_right')

    def test_first_actual_i420_difference_is_preserved(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root)
            p=root/'seed-20261109/s_curve_left_right/original_off-run_1.json'
            d=json.loads(p.read_text());d['onnx_i420']['all_frame_sha256'][1]='e'*64;p.write_text(json.dumps(d))
            r=compare_scene(root,20261109,'s_curve_left_right')['arms']['original_off']['i420']
            self.assertEqual(r['matched_full_timeline'],9)
            self.assertEqual(r['first_different_step_1_based'],2)


class ShadowSamplerLauncherTests(unittest.TestCase):
    def invoke(self, status, *, write=True, invalid=False, stale=False):
        with TemporaryDirectory() as tmp:
            out=Path(tmp)/'trial.json'
            if stale:out.write_text('{}')
            def native(command):
                self.assertEqual(command[:2],['xvfb-run','-a'])
                self.assertIn('--terminal-shadow-probe',command)
                if write:
                    d=fixture(20261109,'s_curve_left_right','original_probe',0)
                    if invalid:d['registered_tasks_after'].remove('PSSM.update')
                    out.write_text(json.dumps(d))
                return SimpleNamespace(returncode=status)
            with patch('scripts.run_native_shadow_sampler_trial.subprocess.run',side_effect=native):
                return run_trial(seed=20261109,scene='s_curve_left_right',arm='original_probe',out=out)

    def test_fresh_valid_receipt_required_for_zero_and_cleanup_five(self):
        for status in (0,5):
            self.assertEqual(self.invoke(status),0)
            with self.assertRaises(ValueError):self.invoke(status,invalid=True)
            with self.assertRaises(FileNotFoundError):self.invoke(status,write=False)
        with self.assertRaises(ValueError):self.invoke(5,stale=True)

    def test_native_failure_preserved_even_when_receipt_exists(self):
        self.assertEqual(self.invoke(2),2)
        self.assertEqual(self.invoke(7),7)


if __name__=='__main__':unittest.main()
