import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json

from bigbench import benchmark_dashboard
from bigbench import benchmark_results
from bigbench.first_divergence import source_snapshot
from bigbench.longitudinal_world import scenario
from bigbench.sdk3_longitudinal import run_longitudinal_benchmark
from bigbench.kinematics import ModelAction
from scripts import build_sdk3_benchmark_dashboard, sdk3_sidewalk_full_s
from tests.test_native_longitudinal import FakeCamera, FakePolicy


class Sdk3CampaignTests(unittest.TestCase):
    def test_comparison_keeps_the_historical_source_pin_registry_valid(self):
        try:
            snapshot = source_snapshot()
        except ValueError as error:
            self.fail(str(error))
        self.assertIn('bigbench/native_longitudinal.py', snapshot)
        self.assertIn('bigbench/dashboard.py', snapshot)

    def test_light_speed_2_resolves_a_distinct_pinned_contract(self):
        self.assertTrue(hasattr(sdk3_sidewalk_full_s, 'official_model_spec'))
        official_model_spec = sdk3_sidewalk_full_s.official_model_spec
        first, _ = official_model_spec('md-v3')
        second, frame = official_model_spec('light-speed-2')

        self.assertNotEqual(first, second)
        self.assertEqual(second.name, 'light-speed-2.json')
        self.assertEqual(frame, 'model-frd')
        with self.assertRaises(ValueError):
            official_model_spec('n16')

    def test_longitudinal_candidate_stops_at_first_nonpositive_gap(self):
        class DrivingPolicy(FakePolicy):
            def step(self, observation):
                return ModelAction(curvature_1pm=0.0, acceleration_mps2=2.0)

        events = []
        report = run_longitudinal_benchmark(
            DrivingPolicy(), scenario('lead_brake'), FakeCamera(), steps=400,
            progress=events.append,
        )

        self.assertEqual(report['termination'], 'LEAD_GAP_NONPOSITIVE')
        self.assertLess(report['steps_completed'], 400)
        self.assertLessEqual(report['trace'][-1]['gap_m'], 0)
        self.assertTrue(all(row['gap_m'] > 0 for row in report['trace'][:-1]))
        self.assertEqual(events[-1]['status'], 'STEP_COMMITTED')

    def test_benchmark_dashboard_preserves_failed_and_pending_verdicts(self):
        self.assertTrue(hasattr(benchmark_dashboard, 'render_benchmark_dashboard'))
        report = {
            'lateral': [{
                'seed': 20261109, 'scenario': 's_curve_left_right', 'comparable': None,
                'models': {
                    'md-v3': {'traversal_passed': False, 'strict_repeat_passed': True,
                              'runs': [{'outcome':'LANE_INTRUSION', 'steps':298, 'intrusion_m':.003}]},
                    'light-speed-2': {'traversal_passed':None, 'strict_repeat_passed':None, 'runs':[]},
                },
            }],
            'longitudinal': [],
        }
        html = benchmark_dashboard.render_benchmark_dashboard(report)

        self.assertIn('LANE_INTRUSION', html)
        self.assertIn('298', html)
        self.assertIn('미판정', html)
        self.assertIn('Light Speed 2', html)
        self.assertIn('Linux SDK3 MetaDrive', html)
        self.assertIn('CARLA 교차검증 · 선택 검증, 미실행', html)

    def test_ramp_dashboard_shows_failed_traversal_separately_from_exact_repeat(self):
        case = dict(
            seed=20261109, scenario='in_ramp', traversal_passed=False, strict_repeat_passed=True,
            runs=[dict(outcome='LANE_INTRUSION', inference_bounds=[147, 147],
                       route_progress_m=60.66, final_route={'intrusion_m': .028})],
        )
        data = {'lateral': [], 'longitudinal': [], 'ramp': {
            'camera_pairs_verified': 4, 'models': {
                'md-v3': {'cases': [case], 'model_process_bounds': [1, 1],
                          'inference_bounds': [147, 147]},
            },
        }}
        html = benchmark_dashboard.render_benchmark_dashboard(data)
        self.assertIn('진입·진출 램프', html)
        self.assertIn('LANE_INTRUSION', html)
        self.assertIn('<td>실패</td><td>통과</td>', html)
        self.assertIn('147', html)

    def test_historical_dashboard_omits_ramps_without_optional_evidence(self):
        html = benchmark_dashboard.render_benchmark_dashboard({'lateral': [], 'longitudinal': []})
        self.assertNotIn('진입·진출 램프', html)

    def test_model_receipt_cannot_borrow_a_camera_gate_with_another_first_frame(self):
        self.assertTrue(hasattr(benchmark_results,'verify_camera_admission'))
        doc = dict(geometry=['lane'],intrinsics={'road':'lens'},driver={'renderer':'llvmpipe'},
                   input_variant='source_yuv_nearest_even')
        first = dict(source_sha256={'road':'a','wide':'b'},canvas_sha256=['c','d'],
                     actual_tensor_sha256='e')
        with TemporaryDirectory() as tmp:
            path = Path(tmp)/'camera-admission.json'
            path.write_text(json.dumps(dict(doc,rows=[dict(first,actual_tensor_sha256='other')])))
            with self.assertRaisesRegex(ValueError,'qualified first'):
                benchmark_results.verify_camera_admission(path,doc,first)

    def test_added_lateral_model_does_not_hide_a_camera_mismatch(self):
        reference = {'source': 'reference'}
        different = {'source': 'different'}
        def read_pair(_directory, name, _seed, _scenario):
            key = different if name == 'fairy-tale' else reference
            return {'status': 'VERIFIED'}, [key, key]

        with TemporaryDirectory() as folder, patch.object(benchmark_results, 'lateral_pair', read_pair):
            report = benchmark_results.build_comparison(
                folder, folder, folder, extra_lateral={'fairy-tale': folder})
        self.assertIn('fairy-tale', report['model_sha256'])
        self.assertTrue(all(case['comparable'] is False for case in report['lateral']))
        self.assertTrue(all('fairy-tale' not in case['models'] for case in report['longitudinal']))

    def test_added_ramp_model_must_match_every_registered_pose(self):
        def gate(tensor):
            return {'cases': [{'seed': 20261109, 'scenario': 'in_ramp',
                'probes': [{'context': {'driver': 'llvmpipe'}, 'rows': ['first', tensor]}]}]}

        self.assertEqual(build_sdk3_benchmark_dashboard.ramp_inputs(gate('same')),
                         build_sdk3_benchmark_dashboard.ramp_inputs(gate('same')))
        self.assertNotEqual(build_sdk3_benchmark_dashboard.ramp_inputs(gate('same')),
                            build_sdk3_benchmark_dashboard.ramp_inputs(gate('different')))

    def test_published_trajectory_is_pending_until_model_owner_returns(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = root/'20261109-s_curve_left_right'
            run = case/'run-0'
            run.mkdir(parents=True)
            (case/'pair-ledger.json').write_text(json.dumps([{'index':0,'returncode':None}]))
            (run/'run.json').write_text('{}')
            (run/'native-child.json').write_text(json.dumps({'returncode':None}))
            result,_ = benchmark_results.lateral_pair(root,'md-v3',20261109,'s_curve_left_right')
        self.assertEqual(result['status'],'PENDING')
        self.assertEqual(result['runs'],[])


    def test_longitudinal_report_and_lifecycle_must_bind_the_same_source(self):
        model, seed, scene = 'light-speed', 20261109, 'stop_go'
        report = dict(
            protocol='sdk3-longitudinal-v1', source_sha='a'*40, seed=seed, scenario=scene,
            status='RETURNED', runtime='cloud-local', pid=17, nonce='b'*32, policy_created=True,
            provider_closed=True, child_finalized_before_server_stop=True,
            official_model_process_bounds=[1,1], official_inference_bounds=[79,79],
            ort='1.20.1', providers=['CPUExecutionProvider'],
            model_sha256=benchmark_results.MODELS[model],
            sdk_sha256=benchmark_results.SDK_SHA, core_sha256=benchmark_results.CORE_SHA,
            input_variant='source_yuv_nearest_even', driver={'renderer':'llvmpipe'},
        )
        owner = dict(spawn_attempted=True, pid=17, returncode=0)
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder/'report.json').write_text(json.dumps(report))
            (folder/'native-child.json').write_text(json.dumps(owner))
            life = folder/'lifecycle.json'
            life.write_text(json.dumps(report))
            self.assertEqual(benchmark_results.verify_owner_and_model(folder, model, seed, scene), report)
            for change in ({'source_sha':'c'*40}, {'official_inference_bounds':[240,240]}):
                with self.subTest(change=change):
                    life.write_text(json.dumps(dict(report, **change)))
                    with self.assertRaisesRegex(ValueError, 'longitudinal lifecycle'):
                        benchmark_results.verify_owner_and_model(folder, model, seed, scene)

    def test_integrated_dashboard_accepts_distinct_registered_model_roots(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            args = ['--md-v3', tmp, '--light-speed-2', tmp, '--longitudinal', tmp,
                    '--integrated-full-s', 'md-v3', tmp, '--integrated-full-s', 'fairy-tale', tmp,
                    '--out', str(folder/'report')]
            self.assertEqual(build_sdk3_benchmark_dashboard.main(args), 0)
            report = json.loads((folder/'report/comparison.json').read_text())
            html = (folder/'report/index.html').read_text()
        self.assertIn('fairy-tale', report['model_sha256'])
        self.assertEqual(len(report['integrated55']), 4)
        self.assertEqual(len(report['integrated45']), 4)
        self.assertTrue(all(row['comparable'] is None for row in report['integrated55']))
        self.assertEqual(report['integrated45'][0]['models']['md-v3']['status'], 'PENDING')
        self.assertIn('45m 통합 Full-S', html)
        self.assertIn('실측·판정 대기', html)


if __name__ == '__main__':
    unittest.main()
