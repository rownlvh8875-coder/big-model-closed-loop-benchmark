import copy,unittest
try:
    from scripts import panda_sdk_integration as joint
except ImportError:joint=None
SDK='aa7e14e71f98b083faa60536ecf6b0a05e3996b4771d38e4a2ccfd43c0903088'
class JointAssessmentTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(joint,'joint execution assessment required')
    def reports(self):return (dict(schema='panda-selected-sdk-coverage-v1',candidate_sha256=SDK,blockers=['SAFE_NAME_CAP_EXCEEDED'],all_selected_lookups_routable=False,native_admitted=False,new_native_runs=0),dict(schema='panda-sdk-image-binding-assessment-v1',candidate_sha256=SDK,blockers=['CANDIDATE_SDK_NOT_INSTALLED'],candidate_image_ready=False,runtime_binding_qualified=False,native_admitted=False,new_native_runs=0))
    def test_both_upstream_failures_and_missing_live_gates_are_reported(self):
        r=joint.assess_execution(*self.reports());self.assertIn('coverage:SAFE_NAME_CAP_EXCEEDED',r['blockers']);self.assertIn('image:CANDIDATE_SDK_NOT_INSTALLED',r['blockers']);self.assertIn('MAPPED_NEW_ABI_NOT_QUALIFIED',r['blockers']);self.assertEqual(r['actual_native_processes'],0);self.assertEqual(r['status'],'BLOCKED_NOT_EXECUTED')
    def test_mismatched_or_missing_candidate_rejects(self):
        for value in (None,'b'*64):
            a,b=self.reports();b['candidate_sha256']=value
            with self.assertRaises(ValueError):joint.assess_execution(a,b)
    def test_supplied_readiness_cannot_authorize_native(self):
        a,b=self.reports();a.update(blockers=[],all_selected_lookups_routable=True);b.update(blockers=[],candidate_image_ready=True,runtime_binding_qualified=True)
        r=joint.assess_execution(a,b);self.assertFalse(r['execution_request_active']);self.assertEqual(r['native_allowance'],0);self.assertFalse(r['stage7_complete']);self.assertIn('AUTHENTICATED_PROCESS_WINDOW_SINK_RECEIPTS_MISSING',r['blockers'])
    def test_claim_of_native_execution_is_rejected(self):
        for key,value in [('native_admitted',True),('new_native_runs',1)]:
            a,b=self.reports();a[key]=value
            with self.assertRaises(ValueError):joint.assess_execution(a,b)
    def test_original_official_cohort_and_model_identity_are_retained(self):
        r=joint.assess_execution(*self.reports());self.assertEqual(r['planned_official_cohort'],dict(seeds=[20261109,20261110],scenes=['s_curve_left_right','s_curve_right_left'],steps=12,hz=20,speed_mps=8,independent_runs_per_condition=2,conditions=4,independent_processes=8));self.assertEqual(r['official_model']['sha256'],'35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199');self.assertEqual(r['official_model_calls'],0);self.assertEqual(r['inherited_strict_result'],'0/4 FAIL');self.assertEqual(r['new_official_result'],'NOT_RUN')
if __name__=='__main__':unittest.main()
