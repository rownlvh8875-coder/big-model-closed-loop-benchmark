"""Portable negative admission/receipt tests; no native imports or model."""
import copy
import unittest
from bigbench import preprocess_experiment_protocol as c


class ProtocolTests(unittest.TestCase):
    def test_cohort_is_exactly_eight_distinct_registered_arms(self):
        self.assertEqual(len(c.TRIALS),8)
        self.assertEqual(len(set(c.TRIALS)),8)
        self.assertEqual(c.LIMITS['official_models'],8)
        self.assertEqual(c.LIMITS['official_inferences'],4800)
        self.assertEqual(c.LIMITS['trials'],[list(x) for x in c.TRIALS])
        for trial in c.TRIALS:
            c.validate_trial(*trial)
        for trial in [(20261111,'s_curve_left_right','rgb_linear'),
                      (20261109,'s_curve_left_right','nearest'),
                      (True,'s_curve_left_right','rgb_linear')]:
            with self.assertRaises(ValueError): c.validate_trial(*trial)

    def test_real_session_and_completion_are_mandatory(self):
        r = dict(protocol=c.TRIAL_PROTOCOL,status='RETURNED',seed=20261109,
            scenario='s_curve_left_right',variant='rgb_linear',pid=22,parent_pid=21,
            nonce='a'*32,source='b'*40,activation='c'*40,approval='d'*40,
            run_id='123',real_session=True,injected_session=False,providers=['CPUExecutionProvider'],
            ort_version='1.20.1',provider_closed=True,inference_bounds=[1,1],
            model_process_bounds=[1,1],input_rows=[dict(step=1,actual_tensor_sha256='e'*64,initial_recurrent_sha256='f'*64)],
            initial_recurrent_sha256='f'*64,
            trajectory=dict(experimental_policy_scope=c.POLICY_SCOPE,input_variant='rgb_linear',initial_recurrent_sha256='f'*64,protocol='full-s-closed-loop-v1',trial_completed=True,
                completed_steps=1,actual_inference_bounds=[1,1],model_sha256=c.MODEL_SHA,
                model_test_double=False,injected_session=False,ground_truth_control_used=False,
                frames=[dict(step=1,new_img_sha256='e'*64)]))
        c.validate_trial_receipt(r)
        for key,value in [('real_session',False),('injected_session',True),
                          ('provider_closed',False),('providers',['CUDAExecutionProvider']),
                          ('inference_bounds',[1,2]),('pid',True),('ort_version','1.21.0')]:
            bad = copy.deepcopy(r);bad[key]=value
            with self.assertRaises(ValueError):c.validate_trial_receipt(bad)
        bad = copy.deepcopy(r);bad['trajectory']['frames'][0]['new_img_sha256']='f'*64
        with self.assertRaises(ValueError):c.validate_trial_receipt(bad)

    def test_scoped_host_never_changes_consumed_workflow(self):
        from scripts import run_recorded_official as old
        from scripts import run_preprocess_experiment as new
        self.assertNotEqual(old.c.BRANCH,new.c.BRANCH)
        self.assertNotEqual(old.c.REQUEST,new.c.REQUEST)
        self.assertNotEqual(old.c.WORKFLOW,new.c.WORKFLOW)
        self.assertEqual(old.c.LIMITS['official_models'],1)
        self.assertEqual(new.plan()['official_model_processes'],0)

    def test_fresh_admission_binds_all_seven_source_jobs_and_cohort(self):
        from scripts import run_preprocess_experiment as host
        from tests.test_recorded_official import AdmissionTests
        old = AdmissionTests()
        r,x,m,ci = c.clone(AdmissionTests.good,c=c,host=host)(old)
        for role in ('windows_push','windows_pr','software_api_pr'):
            ci[role]['jobs']['jobs'][0]['name']='software-host-allocation' if role=='software_api_pr' else 'windows-contracts'
        external = c.clone(AdmissionTests.external,c=c)(old,r,x,m,ci)
        self.assertEqual(host.validate_admission(r,x,manifest=m,ci=ci,**external)['source'],r['source'])
        for changes in ({'attempt':2},{'branch':'diagnostic/recorded-official-20261118-01'},
                        {'delta':['M\tbigbench/onnx_policy.py']}):
            with self.assertRaises(ValueError):
                host.validate_admission(r,dict(x,**changes),manifest=m,ci=ci,**external)
        for changes in ({'official_models':9},{'official_inferences':4801},{'trials':[]}):
            bad = copy.deepcopy(r);bad['limits'].update(changes)
            with self.assertRaises(ValueError):host.validate_admission(bad,x,manifest=m,ci=ci,**external)
        bad = copy.deepcopy(ci);bad['windows_push']['run']['conclusion']='failure'
        with self.assertRaises(ValueError):host.validate_admission(r,x,manifest=m,ci=bad,**external)

    def test_cold_plan_has_no_native_or_numpy_import(self):
        import json,subprocess,sys
        from scripts import run_preprocess_experiment as host
        proc = subprocess.run([sys.executable,'-I','-S','-B',str(host.ROOT/'scripts/run_preprocess_experiment.py'),'plan'],capture_output=True,text=True,timeout=20)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(json.loads(proc.stdout)['heavy_modules_loaded'],[])


if __name__ == '__main__':unittest.main()
