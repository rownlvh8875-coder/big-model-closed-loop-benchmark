"""CPU unit fixtures only. Native evidence comes from the separate CI canary."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    from bigbench import recorded_worker_canary as canary
except ImportError:
    canary = None
from bigbench import full_s_recorded_worker as worker
from tests.test_full_s_failure_capture import SourceCamera, INTRINSICS, route

ROOT = Path(__file__).resolve().parents[1]


class CanaryTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(canary, 'zero-model recorded-worker connection missing')

    def fixture(self, out):
        from scripts import sdk3_four_validation_trial as original
        from bigbench import native_model_campaign as campaign
        class Lens:
            def __init__(self, role): self.i = INTRINSICS[role]
            def getFilmSize(self): return 964/self.i.fx, 604/self.i.fy
            def getFilmOffset(self): return 0., 0.
            def getFocalLength(self): return 1.
        class Provider:
            calls = 0
            def __init__(self):
                self.env = SimpleNamespace(engine=SimpleNamespace(sensors={
                    'bigbench_'+r: SimpleNamespace(get_lens=lambda r=r: Lens(r)) for r in ('road', 'wide')}))
            def close(self): self.calls += 1
        provider = Provider()
        class Camera(SourceCamera):
            def __init__(self, value): super().__init__(); self.provider = value
        stats = dict(returned=0, guards_ok=True, values={k:0 for k in canary.STAT_FIELDS})
        args = SimpleNamespace(out=out, nonce='a'*32, seed=20261109, scenario='s_curve_left_right')
        with patch.object(original, '_world', return_value=(provider, route(), {})), \
             patch.object(original, 'driver_info', return_value={'renderer':'CPU_UNIT_FIXTURE_ONLY'}), \
             patch.object(campaign, 'NativeWorldCamera', Camera), \
             patch('scripts.sdk3_priority_model_native.source_stats_after', return_value=stats), \
             patch('scripts.native_mdv3_repeat_trial.AuditedOfficialOnnx', side_effect=AssertionError('real policy constructed')):
            result = worker.run_camera_canary_trial(args)
        return result, provider

    @unittest.skipUnless(sys.platform=='linux','native orchestration body is Linux-only')
    def test_actual_loop_and_recorder_use_two_fixture_audits_without_graph(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'trial'
            result, provider = self.fixture(out)
            self.assertEqual(provider.calls, 1)
            self.assertEqual(result['mode'], canary.MODE)
            self.assertEqual(result['max_steps'], 2)
            self.assertEqual(result['fixture_policy_audit_bounds'], [2,2])
            self.assertEqual(result['official_inference_bounds'], [0,0])
            self.assertTrue(result['model_test_double'])
            self.assertFalse(result['onnxruntime']['real_session'])
            checked = canary.verify_trial(out, mode=canary.MODE)
            self.assertTrue(checked['recording_structure_valid'])
            self.assertFalse(checked['origin_authenticated'])
            self.assertFalse(checked['model_camera_qualified'])
            with self.assertRaises(ValueError): canary.verify_trial(out, mode='OFFICIAL_MODEL')

    @unittest.skipUnless(sys.platform=='linux','native orchestration body is Linux-only')
    def test_receiver_rejects_lifecycle_pid_nonce_count_session_and_cleanup_swaps(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'trial';self.fixture(out)
            for name,changes in (
                ('recorded-trial.json',{'nonce':'b'*32}),
                ('recorded-trial-lifecycle.json',{'pid':123}),
                ('recorded-trial.json',{'fixture_policy_audit_bounds':[1,2]}),
                ('recorded-trial.json',{'onnxruntime':{'real_session':True}}),
                ('recorded-trial.json',{'provider_closed':False}),
                ('recorded-trial.json',{'official_inference_bounds':[0,1]})):
                path=out/name;raw=path.read_bytes();data=json.loads(raw);data.update(changes);path.write_text(json.dumps(data))
                with self.subTest(name=name,changes=changes),self.assertRaises(ValueError):canary.verify_trial(out,mode=canary.MODE)
                path.write_bytes(raw)

    def test_sealed_policy_never_checks_a_weight_file_or_constructs_a_session(self):
        from bigbench.onnx_contract import ModelContract
        from bigbench.model_world_frame import WorldFramePolicyAdapter,SOURCE_ACTION_FRAME
        from bigbench.full_s_validation import run_full_s
        with patch.object(ModelContract,'check_file',side_effect=AssertionError('weight access')):
            p=canary.NoGraphPolicy(ROOT/'model_specs/md-v3.json')
            report=run_full_s(WorldFramePolicyAdapter(p,source_action_frame=SOURCE_ACTION_FRAME),SourceCamera(),route(),seed=20261109,scene='s_curve_left_right',max_steps=2)
        self.assertFalse(hasattr(p,'session'))
        self.assertEqual(report['completed_steps'],2)
        self.assertTrue(all(r['raw_model_action']==[0.,0.,0.,0.] for r in report['frames']))
        self.assertEqual(len(p.audit_rows),2)

    def test_two_step_replay_rejects_pose_route_and_outcome_corruption(self):
        from bigbench.model_world_frame import WorldFramePolicyAdapter,SOURCE_ACTION_FRAME
        from bigbench.full_s_validation import run_full_s
        p=canary.NoGraphPolicy(ROOT/'model_specs/md-v3.json')
        value=run_full_s(WorldFramePolicyAdapter(p,source_action_frame=SOURCE_ACTION_FRAME),SourceCamera(),route(),seed=20261109,scene='s_curve_left_right',max_steps=2)
        for row in value['geometry']:
            row['lane_class']='metadrive.component.lane.'+('circular_lane.CircularLane' if row['shape']['kind']=='circular' else 'straight_lane.StraightLane')
        self.assertTrue(canary.validate_canary_trajectory(value)['two_step_trajectory_valid'])
        for change in (lambda d:d['frames'][0].update(world_x_m=0.),lambda d:d.update(traversal_passed=True),
                       lambda d:d['frames'][1]['route'].update(lateral_right_m=999.),lambda d:d.update(outcome='FULL_S_COMPLETED')):
            data=copy.deepcopy(value);change(data)
            with self.assertRaises(ValueError):canary.validate_canary_trajectory(data)

    def test_audit_denies_weight_open_and_ort_import_without_denying_image_data(self):
        audit=canary.ZeroModelAudit()
        audit('open',('/out/pixels.bin','wb',0))
        audit('import',('numpy',None,None,None,None))
        for event,args in (('open',('/model.onnx','rb',0)),('open',(b'/tmp/model.ORT','rb',0)),('import',('onnxruntime.capi',None,None,None,None))):
            with self.assertRaises(RuntimeError):audit(event,args)
        self.assertEqual(audit.snapshot(),dict(weight_open_attempts=2,ort_import_attempts=1))

    def test_native_ack_requires_exact_live_identity_and_nonfinal_parent_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            launch=dict(parent_pid=os.getppid(),nonce='a'*32,seed=20261109,scenario='s_curve_left_right',mode=canary.MODE)
            native=dict(spawn_attempted=True,pid=os.getpid(),returncode=None,server_returncode=None)
            (root/'launch.json').write_text(json.dumps(launch));(root/'native-child.json').write_text(json.dumps(native))
            value=canary.read_native_ack(root/'owner.json')
            self.assertTrue(value['spawn_succeeded'])
            native['pid']+=1;(root/'native-child.json').write_text(json.dumps(native))
            with self.assertRaises(ValueError):canary.read_native_ack(root/'owner.json')
            native['pid']=os.getpid();native['returncode']=0;(root/'native-child.json').write_text(json.dumps(native))
            with self.assertRaises(ValueError):canary.read_native_ack(root/'owner.json')

    def test_cold_canary_help_and_plan_import_no_optional_runtime(self):
        script=ROOT/'scripts/run_recorded_worker_canary.py'
        for arguments in (['--help'],['plan']):
            result=subprocess.run([sys.executable,'-I','-S','-B',str(script),*arguments],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            if arguments==['plan']:
                data=json.loads(result.stdout)
                self.assertEqual(data['official_model_processes'],0)
                self.assertEqual(data['heavy_modules_loaded'],[])


if __name__=='__main__':unittest.main()
