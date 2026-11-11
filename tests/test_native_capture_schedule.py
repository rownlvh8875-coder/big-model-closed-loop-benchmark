"""Synthetic receipt validation only; these fixtures are not native evidence."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from test_native_pssm_cross_process import mock_native
from scripts.compare_native_capture_schedule import (
    SCHEDULES, compare_schedule_repeats, compare_scene, aggregate_scenes,
)


def fixture(seed,scene,arm,index):
    d=mock_native(seed,scene,'sequential_original',index)
    mode,ticks=SCHEDULES[arm]
    d.update(mode=mode,process_uuid=f'{seed}-{scene}-{arm}-{index}',
             process_id=20000+list(SCHEDULES).index(arm)*10+index,
             task_manager_step_invocations_from_capture_call_path=ticks,
             expected_panda_global_frame_count_delta_per_pair=ticks)
    d['clock_timeline']=[{'render_frame_index_zero_based':i,
        'before':{'frame_count':i*ticks},'after':{'frame_count':(i+1)*ticks},
        'global_clock_frame_count_delta':ticks} for i in range(10)]
    d['registered_tasks_after']=list(d['registered_tasks_before'])
    return d


def build(root):
    for seed in (20261109,20261110):
        for scene in ('s_curve_left_right','s_curve_right_left'):
            folder=root/f'seed-{seed}'/scene
            folder.mkdir(parents=True)
            for arm in SCHEDULES:
                for i in (0,1):
                    (folder/f'{arm}-run_{i}.json').write_text(json.dumps(fixture(seed,scene,arm,i)))
            (folder/'case_comparison.json').write_text(json.dumps(compare_scene(root,seed,scene)))


class NativeCaptureScheduleTests(unittest.TestCase):
    def test_actual_source_mismatch_is_reported_without_tolerance(self):
        a=fixture(20261109,'s_curve_left_right','sequential_road_first',0)
        b=fixture(20261109,'s_curve_left_right','sequential_road_first',1)
        b['source_rgb']['road']['all_frame_sha256'][1]='e'*64
        r=compare_schedule_repeats(a,b,20261109,'s_curve_left_right','sequential_road_first')
        self.assertEqual(r['source_rgb']['road']['matched_full_timeline'],9)
        self.assertEqual(r['source_rgb']['road']['first_different_step_1_based'],2)
        self.assertFalse(r['all_image_fields_bit_exact'])

    def test_paired_two_ticks_never_proves_original_mdv3_gate(self):
        a=fixture(20261109,'s_curve_left_right','paired_two_ticks',0)
        b=fixture(20261109,'s_curve_left_right','paired_two_ticks',1)
        r=compare_schedule_repeats(a,b,20261109,'s_curve_left_right','paired_two_ticks')
        self.assertTrue(r['all_image_fields_bit_exact'])
        self.assertFalse(r['is_original_sequential_control'])
        self.assertFalse(r['original_mdv3_repeatability_proven'])

    def test_mode_task_count_and_raw_clock_evidence_cannot_be_mislabeled(self):
        for mutation in ('mode','task_count','clock_count','clock_order','clock_end','expected_count','clock_gap'):
            with self.subTest(mutation=mutation):
                a=fixture(20261109,'s_curve_left_right','paired_two_ticks',0)
                b=fixture(20261109,'s_curve_left_right','paired_two_ticks',1)
                if mutation=='mode': b['mode']='task_step_pair'
                elif mutation=='task_count': b['task_manager_step_invocations_from_capture_call_path']=1
                elif mutation=='clock_count': b['clock_timeline'][0]['global_clock_frame_count_delta']=1
                elif mutation=='clock_order': b['clock_timeline'][1]['render_frame_index_zero_based']=0
                elif mutation=='clock_end': b['clock_timeline'][0]['after']['frame_count']=1
                elif mutation=='expected_count': b['expected_panda_global_frame_count_delta_per_pair']=1
                else:
                    b['clock_timeline'][1]['before']['frame_count']+=2
                    b['clock_timeline'][1]['after']['frame_count']+=2
                with self.assertRaises(ValueError):
                    compare_schedule_repeats(a,b,20261109,'s_curve_left_right','paired_two_ticks')

    def test_original_pssm_chase_and_both_pose_controls_are_required(self):
        for mutation in ('pssm','chase','positive','pose','process','hash'):
            with self.subTest(mutation=mutation):
                a=fixture(20261109,'s_curve_left_right','sequential_wide_first',0)
                b=fixture(20261109,'s_curve_left_right','sequential_wide_first',1)
                if mutation=='pssm': b['registered_tasks_before'].remove('PSSM.update')
                elif mutation=='chase': b['registered_tasks_before'].remove('update main chase camera')
                elif mutation=='positive': b['camera_plus_2m_positive']['wide']=False
                elif mutation=='pose': b['camera_pose'][0][0]+=1
                elif mutation=='process': b['process_uuid']=a['process_uuid']
                else: b['source_rgb']['wide']['all_frame_sha256'].pop()
                with self.assertRaises(ValueError):
                    compare_schedule_repeats(a,b,20261109,'s_curve_left_right','sequential_wide_first')

    def test_post_capture_task_loss_and_invalid_camera_geometry_are_rejected(self):
        for mutation in ('post_chase','short_pose','nonfinite_pose'):
            with self.subTest(mutation=mutation):
                a=fixture(20261109,'s_curve_left_right','paired_one_tick',0)
                b=fixture(20261109,'s_curve_left_right','paired_one_tick',1)
                if mutation=='post_chase':
                    b['registered_tasks_after'].remove('update main chase camera')
                elif mutation=='short_pose':
                    a['camera_pose']=b['camera_pose']=[[0.],[0.]]
                else:
                    a['camera_pose']=b['camera_pose']=[[float('inf'),0.,1.22],[0.,0.,0.]]
                with self.assertRaises(ValueError):
                    compare_schedule_repeats(a,b,20261109,'s_curve_left_right','paired_one_tick')

    def test_aggregate_recomputes_all_32_trials_and_rejects_modified_summary(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root)
            r=aggregate_scenes(root)
            self.assertEqual(r['independent_process_count'],32)
            self.assertEqual(len(r['per_scene']),4)
            self.assertFalse(r['original_mdv3_repeatability_proven'])
            p=root/'seed-20261109/s_curve_left_right/case_comparison.json'
            altered=json.loads(p.read_text())
            altered['arms']['paired_one_tick']['i420']['matched_full_timeline']=9
            p.write_text(json.dumps(altered))
            with self.assertRaises(ValueError): aggregate_scenes(root)

    def test_reusing_a_process_uuid_in_another_scene_is_invalid(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root)
            p=root/'seed-20261110/s_curve_left_right/sequential_road_first-run_0.json'
            d=json.loads(p.read_text())
            d['process_uuid']='20261109-s_curve_left_right-sequential_road_first-0'
            p.write_text(json.dumps(d))
            folder=p.parent
            (folder/'case_comparison.json').write_text(json.dumps(compare_scene(root,20261110,'s_curve_left_right')))
            with self.assertRaises(ValueError): aggregate_scenes(root)

    def test_same_runner_processes_cannot_be_reused_across_treatments(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);build(root)
            folder=root/'seed-20261109/s_curve_left_right'
            for i in (0,1):
                p=folder/f'paired_two_ticks-run_{i}.json'
                d=json.loads(p.read_text())
                d['process_id']=20000+i
                p.write_text(json.dumps(d))
            with self.assertRaises(ValueError):
                compare_scene(root,20261109,'s_curve_left_right')
