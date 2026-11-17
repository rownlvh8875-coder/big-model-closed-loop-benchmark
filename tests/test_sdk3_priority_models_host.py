from pathlib import Path
import copy,json,subprocess,sys,tempfile,unittest
try:from scripts import run_sdk3_priority_models as h
except ImportError:h=None
from tests.sdk3_priority_model_fixtures import report,case,write
from scripts import panda_sdk3_runtime as pins
class ModelHostContracts(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(h,'strict fresh candidate model host missing')
    def test_complete_actual_schema_keeps_original_strict_comparator(self):
        r=report(h);h.validate_model_report(r,20261110,'s_curve_left_right');self.assertEqual(h.compare_fresh_trials.__module__,'scripts.compare_fresh_native_mdv3')
    def test_model_sha_candidate_marker_counts_and_no_observer_flags_fail_closed(self):
        r=report(h)
        for key,value in [('model_sha256','f'*64),('trial_evidence','UNMODIFIED_METADRIVE_NEW_FRAME_OFFICIAL_ONNX_DIAGNOSTIC'),('actual_onnx_inferences_completed',11),('real_ort_session',False),('injected_session',True),('onnxruntime_version','wrong'),('raw_rgb_observer_used',True),('extra_gpu_queries',1),('draw_trace_library_mapped',True),('ld_preload_present',True),('original_unmodified_pipeline',True)]:
            x=copy.deepcopy(r);x[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):h.validate_model_report(x,20261110,'s_curve_left_right')
    def test_missing_source_input_recurrent_hash_or_nonfinite_action_is_rejected(self):
        r=report(h)
        for key,value in [('source_road_rgb_sha256','bad'),('state_after_step_sha256','bad'),('raw_model_action',[float('nan')]),('time_s',.123),('speed_mps',9.)]:
            x=copy.deepcopy(r);x['frames'][4][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):h.validate_model_report(x,20261110,'s_curve_left_right')
    def test_source_context_changes_or_wrong_policy_implementation_are_rejected(self):
        r=report(h)
        for key in h.expected_source_context():
            x=copy.deepcopy(r);x['source_context'][key]=False if type(x['source_context'][key]) is bool else 'f'*64
            with self.subTest(key=key),self.assertRaises(ValueError):h.validate_model_report(x,20261110,'s_curve_left_right')
    def test_complete_owned_pair_recomputes_unmodified_strict_verdict(self):
        with tempfile.TemporaryDirectory() as d:
            folder,_=case(h,d);row=h.validate_case(folder,20261110,'s_curve_left_right');self.assertTrue(row['verdict']['exact_repeated_execution_gate_passed']);self.assertEqual(row['official_model_processes'],2);self.assertEqual(row['onnx_inferences'],24)
    def test_pair_identity_lifecycle_counts_and_container_cleanup_mutations_reject(self):
        for kind in ('pid','lifecycle','cleanup','matrix_evidence'):
            with tempfile.TemporaryDirectory() as d:
                folder,_=case(h,d)
                if kind=='pid':p=folder/'pair/run-0/native-child.json';x=json.loads(p.read_text());x['pid']=999
                elif kind=='lifecycle':p=folder/'pair/run-0/model-trial-lifecycle.json';x=json.loads(p.read_text());x['inferences_completed_lower_bound']=11
                elif kind=='cleanup':p=folder/'pair/execution.json';x=json.loads(p.read_text());x['owned_container_removed']=False
                else:p=folder/'pair/run-0/report.json';x=json.loads(p.read_text());x['core_sha256']='f'*64
                write(p,x)
                with self.subTest(kind=kind),self.assertRaises(ValueError):h.validate_case(folder,20261110,'s_curve_left_right')
    def test_fresh_complete_matrix_requires_all_cases_and_eight_independent_processes(self):
        with tempfile.TemporaryDirectory() as d:
            rows=[h.validate_case(case(h,Path(d)/str(i),seed,scene,i)[0],seed,scene) for i,(seed,scene) in enumerate(sorted(pins.CASES))];value=h.aggregate_cases(rows);self.assertTrue(value['strict_pass']);self.assertEqual(value['official_model_processes'],8);self.assertEqual(value['onnx_inferences'],96)
            for bad in (rows[:3],[rows[0],rows[0],rows[2],rows[3]]):
                with self.assertRaises(ValueError):h.aggregate_cases(bad)
            bad=copy.deepcopy(rows);bad[1]['process_uuids'][0]=bad[0]['process_uuids'][0]
            with self.assertRaises(ValueError):h.aggregate_cases(bad)
    def test_real_disagreement_stays_a_failed_gate_without_outcome_filtering(self):
        with tempfile.TemporaryDirectory() as d:
            rows=[h.validate_case(case(h,Path(d)/str(i),seed,scene,i)[0],seed,scene) for i,(seed,scene) in enumerate(sorted(pins.CASES))];rows[2]['verdict'].update(status='STRICT_NATIVE_ONNX_REPEAT_MISMATCH',exact_repeated_execution_gate_passed=False);r=h.aggregate_cases(rows);self.assertFalse(r['strict_pass']);self.assertEqual(r['passed'],3);self.assertFalse(r['historical_original_matrix_replaced'])
    def test_renderer_source_changes_cannot_slip_into_model_cohort(self):
        h.validate_renderer_delta([]);h.validate_renderer_delta(['A\tscripts/new-model.py'])
        with self.assertRaises(ValueError):h.validate_renderer_delta(['M\tbigbench/sdk3_terrain_priority.py'])
    def test_model_command_has_no_gpu_observer_and_keeps_original_resource_profile(self):
        cmd=h.native_command('case',Path('/repo'),Path('/sdk'),Path('/out'),['--model-pair','--seed','20261110','--scenario','s_curve_left_right'],model=Path('/model'),deps=Path('/deps'),owner='a'*32);self.assertIn(h.ENTRY,cmd);self.assertIn('10g',cmd);self.assertFalse(any('drawtrace' in s or 'LD_PRELOAD' in s or 'LD_DEBUG' in s for s in cmd))
    def test_partial_lifecycle_or_unknown_child_never_reports_zero_inferences(self):
        with tempfile.TemporaryDirectory() as d:
            folder,_=case(h,d);path=folder/'pair/run-1/model-trial-lifecycle.json';life=json.loads(path.read_text());life.update(completed=False,status='EPISODE_PENDING',inferences_completed_lower_bound=0,inferences_completed_upper_bound=12);write(path,life);counts=h.observed_counts(folder/'pair');self.assertEqual(counts['known_model_processes'],2);self.assertEqual(counts['inferences_lower_bound'],12);self.assertEqual(counts['inferences_upper_bound'],24)
            path=folder/'pair/run-1/native-child.json';child=json.loads(path.read_text());child['pid']=None;write(path,child);counts=h.observed_counts(folder/'pair');self.assertEqual(counts['known_model_processes'],1);self.assertEqual(counts['upper_model_processes'],2);self.assertEqual(counts['inferences_upper_bound'],24)
    def test_request_scope_binds_renderer_and_exact_fresh_models(self):
        r=dict(schema='sdk3-priority-models-request-v1',official_model_processes=8,onnx_inferences=96,cases=[dict(seed=s,scenario=c) for s,c in sorted(pins.CASES)],repair_id=h.repair.REPAIR_ID,adapter_sha256=pins.digest(h.ROOT/'bigbench/sdk3_terrain_priority.py'),model_sha256=pins.MODEL_SHA,renderer=h.RENDERER)
        h.validate_request(r)
        for key,value in [('official_model_processes',2),('onnx_inferences',12),('cases',r['cases'][:3]),('renderer',dict(h.RENDERER,artifact_id=1)),('adapter_sha256','f'*64)]:
            x=copy.deepcopy(r);x[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):h.validate_request(x)
    def test_failed_renderer_gate_never_stages_or_downloads_model(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d,patch.object(h,'ROOT',Path(d)),patch.object(h,'authenticate_source',return_value={'source_sha':'a'*40}),patch.object(h,'authenticate_renderer',side_effect=ValueError('gate rejected')),patch.object(h,'stage_runtime') as stage:
            with self.assertRaisesRegex(ValueError,'gate rejected'):h.run(20261110,'s_curve_left_right')
            stage.assert_not_called();summary=json.loads(next(Path(d).rglob('summary.json')).read_text());self.assertEqual(summary['counts']['known_model_processes'],0);self.assertEqual(summary['counts']['inferences_upper_bound'],0)
    def test_host_cold_help(self):
        r=subprocess.run([sys.executable,'-I','-B',h.__file__,'--help'],capture_output=True,text=True,timeout=15);self.assertEqual(r.returncode,0,r.stderr)
if __name__=='__main__':unittest.main()
