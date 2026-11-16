"""Synthetic pixels only; no Panda, Docker or official inference."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
import numpy as np
from scripts import sdk3_rgb_forensics as f
from scripts.native_mdv3_rgb_pixel_capture import BoundedNativeRGBCapture,SHAPE
from scripts import panda_sdk3_runtime as p
from tests.test_aggregate_original_mdv3_current_recheck import mock_trial


def make_trial(root,index,*,changed_step=None,arm='full_rgb'):
    folder=Path(root)/'pair'/f'run-{index}';folder.mkdir(parents=True)
    row=mock_trial(20261110,'s_curve_left_right',11 if index==0 else 24)
    row.update(selected_sdk_sha256=p.SDK_SHA,sdk_load_order='core-first',trial_evidence='ORIGINAL_PSSM_WITH_OPT_IN_CPU_RGB_RETENTION_PROBE' if arm=='full_rgb' else 'UNMODIFIED_METADRIVE_NEW_FRAME_OFFICIAL_ONNX_DIAGNOSTIC')
    observer=f.FullEpisodeRGBCapture() if arm=='full_rgb' else None
    for step,frame in enumerate(row['frames'],1):
        rgb={'road':np.full(SHAPE,30,dtype=np.uint8),'wide':np.full(SHAPE,70,dtype=np.uint8)}
        if step==changed_step:rgb['road'][5,7,1]=99
        digests={k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in rgb.items()}
        for camera in rgb:frame[f'source_{camera}_rgb_sha256']=digests[camera]
        if observer:observer.record_native_rgb(rgb,digests)
    if observer:row['raw_rgb_pixel_audit']=observer.save_after_episode(folder/'rgb',row)
    (folder/'run.json').write_text(json.dumps(row))
    return row


class FullEpisodeRGBForensics(unittest.TestCase):
    def test_observer_keeps_step12_without_expanding_legacy_six_step_behavior(self):
        with tempfile.TemporaryDirectory() as d:
            row=make_trial(d,0,changed_step=12)
            manifest=json.loads((Path(d)/'pair/run-0/rgb/manifest.json').read_text())
            self.assertEqual(manifest['captured_step_count'],12)
            self.assertEqual(len(manifest['images']),24)
            self.assertEqual(manifest['images'][-2]['step'],12)
            self.assertEqual(row['raw_rgb_pixel_audit']['captured_step_count'],12)
            self.assertEqual(BoundedNativeRGBCapture().max_steps,6)
            with self.assertRaises(ValueError):BoundedNativeRGBCapture(7)

    def test_step7_and_step12_pixels_have_exact_location_and_delta(self):
        for step in (7,12):
            with self.subTest(step=step),tempfile.TemporaryDirectory() as d:
                make_trial(d,0);make_trial(d,1,changed_step=step)
                result=f.analyze_pair(Path(d),'full_rgb')
                self.assertEqual(result['first_raw_source_diff_step'],step)
                metrics=result['pixel_metrics']['road'][step-1]
                self.assertEqual(metrics['changed_pixel_count'],1)
                self.assertEqual(metrics['bounding_box_xyxy_inclusive'],[7,5,7,5])
                self.assertEqual(metrics['first_12_changed_xy'],[[7,5]])
                self.assertEqual(metrics['maximum_absolute_channel_delta'],69)
                self.assertTrue(result['prior_step_pose_action_state_equal'])
                self.assertFalse(result['repair_proven'])

    def test_forged_truncated_reordered_and_wrong_scene_pixels_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            make_trial(d,0);make_trial(d,1)
            path=Path(d)/'pair/run-1/rgb/manifest.json';original=json.loads(path.read_text())
            for name in ('wrong_seed','duplicate','sha','missing'):
                value=copy.deepcopy(original)
                if name=='wrong_seed':value['seed']=20261109
                if name=='duplicate':value['images'][1]=copy.deepcopy(value['images'][0])
                if name=='sha':value['images'][12]['sha256']='00'*32
                if name=='missing':value['images'].pop()
                path.write_text(json.dumps(value))
                with self.subTest(name=name),self.assertRaises(ValueError):f.analyze_pair(Path(d),'full_rgb')
            path.write_text(json.dumps(original));raw=Path(d)/'pair/run-1/rgb/step-07-road.rgb.zlib';data=raw.read_bytes()
            for altered in (data[:-1],data+b'trailing'):
                raw.write_bytes(altered)
                with self.assertRaises(ValueError):f.analyze_pair(Path(d),'full_rgb')

    def test_equal_probe_and_equal_control_do_not_promote_original_matrix(self):
        for arm in ('control','full_rgb'):
            with self.subTest(arm=arm),tempfile.TemporaryDirectory() as d:
                make_trial(d,0,arm=arm);make_trial(d,1,arm=arm)
                result=f.analyze_pair(Path(d),arm)
                self.assertTrue(result['strict_pair_pass'])
                self.assertEqual(result['original_matrix_passed'],3)
                self.assertFalse(result['original_matrix_gate_passed'])
                self.assertFalse(result['stage7_complete'])
                self.assertFalse(result['repair_proven'])
                if arm=='control':self.assertIsNone(result['pixel_metrics'])

    def test_instrumented_trial_cannot_be_relabelled_as_control(self):
        with tempfile.TemporaryDirectory() as d:
            make_trial(d,0);make_trial(d,1)
            with self.assertRaises(ValueError):f.analyze_pair(Path(d),'control')

if __name__=='__main__':unittest.main()

class FullRGBDispatch(unittest.TestCase):
    def test_control_has_no_observer_and_probe_serializes_all_twelve_after_episode(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from scripts import native_mdv3_repeat_trial as n
        def episode(policy,config,*,full_s_route,camera_convergence,raw_rgb_observer):
            row=mock_trial(config.seed,config.scenario,100)
            policy.audit_rows=[];policy.trace=[None]*12
            for frame in row['frames']:
                rgb={k:np.full(SHAPE,30 if k=='road' else 70,dtype=np.uint8) for k in ('road','wide')}
                hashes={k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in rgb.items()}
                for camera in rgb:frame[f'source_{camera}_rgb_sha256']=hashes[camera]
                if raw_rgb_observer is not None:raw_rgb_observer.record_native_rgb(rgb,hashes)
                policy.audit_rows.append({k:frame[k] for k in ('new_img_sha256','raw_model_action','raw_action_sha256','state_after_step_sha256')})
            return row
        with tempfile.TemporaryDirectory() as tmp,patch.object(n,'AuditedOfficialOnnx',side_effect=lambda *a:SimpleNamespace()),patch.object(n,'run_native_episode',side_effect=episode):
            root=Path(tmp);kw=dict(model=root/'model',spec=root/'spec',scenario='s_curve_left_right',seed=20261110,steps=12,speed=8.,initial_fraction=.12)
            control=n.run_trial(**kw)
            self.assertNotIn('raw_rgb_pixel_audit',control)
            self.assertEqual(control['trial_evidence'],'UNMODIFIED_METADRIVE_NEW_FRAME_OFFICIAL_ONNX_DIAGNOSTIC')
            probe=n.run_trial(**kw,raw_rgb_dir=root/'rgb',raw_rgb_capture_factory=f.FullEpisodeRGBCapture)
            self.assertEqual(probe['raw_rgb_pixel_audit']['captured_step_count'],12)
            self.assertEqual(len(json.loads((root/'rgb/manifest.json').read_text())['images']),24)
            with self.assertRaises(ValueError):n.run_trial(**kw,raw_rgb_capture_factory=f.FullEpisodeRGBCapture)

    def test_full_rgb_flag_reaches_owned_child_and_disabled_path_has_no_capture(self):
        from types import SimpleNamespace
        from scripts import panda_sdk3_diagnostic as d
        args=SimpleNamespace(out='/out/run-0',nonce='ab'*16,load_order='core-first',factory='manual',reference_wheel=False,model_trial=True,seed=20261110,scenario='s_curve_left_right',full_rgb=True)
        command=d.owned_child_command(args,999)
        self.assertIn('--full-rgb',command)
        options=d.full_rgb_trial_options(args,Path(args.out))
        self.assertEqual(options['raw_rgb_dir'],Path('/out/run-0/rgb'))
        self.assertIs(options['raw_rgb_capture_factory'],f.FullEpisodeRGBCapture)
        args.full_rgb=False
        self.assertNotIn('--full-rgb',d.owned_child_command(args,999))
        self.assertEqual(d.full_rgb_trial_options(args,Path(args.out)),{})
        args.full_rgb=True;args.reference_wheel=True
        with self.assertRaises(ValueError):d.full_rgb_trial_options(args,Path(args.out))

    def test_pair_launcher_forwards_probe_flag_to_both_model_children(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from scripts import panda_sdk3_diagnostic as d
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);args=SimpleNamespace(out=str(root),seed=20261110,scenario='s_curve_left_right',full_rgb=True)
            class Child:
                pid=44
                def __init__(self,argv,**kw):
                    if '--full-rgb' not in argv:raise AssertionError('probe flag lost before display owner')
                    folder=Path(argv[argv.index('--out')+1]);index=int(folder.name[-1]);(folder/'native-child.json').write_text(json.dumps(dict(spawn_attempted=True,pid=11 if index==0 else 24,returncode=0,server_returncode=0)))
                def wait(self,timeout):return 0
            def redirected_path(value):
                text=str(value)
                return root/Path(text).name if text.startswith('/tmp/home-') else Path(value)
            with patch.object(d,'Path',side_effect=redirected_path),patch.object(d.subprocess,'Popen',Child):d.run_pair(args)
            receipt=json.loads((root/'pair.json').read_text())
            self.assertEqual(receipt['status'],'PAIR_COMPLETED')
            self.assertEqual(receipt['counts'],dict(known=2,upper=2,spawn_attempts=2))
