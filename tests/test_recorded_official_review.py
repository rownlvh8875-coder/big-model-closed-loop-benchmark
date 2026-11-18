"""One combined final-review regression pass, CPU data/metadata only."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from bigbench import recorded_official_execution as c
from bigbench import recorded_official_dependencies as deps

PTH=b'import os; exec(\'try: __import__("coloredlogs").auto_install() if os.environ.get("COLOREDLOGS_AUTO_INSTALL") else None\\nexcept ImportError: pass\')\n'

class ReviewRegressions(unittest.TestCase):
    def test_exact_original_coloredlogs_hook_is_removed_without_running_it(self):
        self.assertEqual(len(PTH),147);self.assertEqual(hashlib.sha256(PTH).hexdigest(),'dda83a855986efa5cd87f0248b0199c0086eb0e8e7fece7d6741959c5ce39536')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'coloredlogs.pth';path.write_bytes(PTH)
            receipt=deps.remove_inert_hook(root)
            self.assertFalse(path.exists());self.assertFalse(receipt['site_processing_used'])
            path.write_bytes(PTH+b' ')
            with self.assertRaises(ValueError):deps.remove_inert_hook(root)
            self.assertTrue(path.exists())
    def test_eight_gibibyte_gate_requires_both_host_and_cgroup_headroom(self):
        for host,maximum,current in ((7*1024**3,10*1024**3,0),(20*1024**3,10*1024**3,3*1024**3),(20*1024**3,'max',0)):
            with self.subTest(host=host,current=current),self.assertRaises(ValueError):c.model_memory_gate(host,maximum,current)
        result=c.model_memory_gate(12*1024**3,10*1024**3,1024**3)
        self.assertEqual(result['effective_available_bytes'],9*1024**3)
        self.assertEqual(result['minimum_model_ram_bytes'],8*1024**3)
        self.assertTrue(result['admitted'])
    def test_auxiliary_source_ci_is_required_before_staging(self):
        from tests import test_recorded_official as fixtures
        from scripts import run_recorded_official as h
        r,x,m,ci=fixtures.AdmissionTests().good();external=fixtures.AdmissionTests().external(r,x,m,ci)
        for key in ('windows_push','windows_pr','software_api_pr'):
            bad=dict(ci);bad.pop(key,None)
            with self.subTest(key=key),self.assertRaises(ValueError):h.validate_admission(r,x,manifest=m,ci=bad,**external)


@unittest.skipUnless(sys.platform=='linux','native envelope CPU fixtures are Linux-only')
class FailureAndOriginRegressions(unittest.TestCase):
    def fixture(self,root,kind='graph'):
        from tests.test_recorded_official_bundle import BundleTests
        case=BundleTests();case.build(root,kind);return case
    def test_missing_lifecycle_does_not_discard_a_valid_surviving_trial(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);case=self.fixture(root)
            (root/'native/observed-trial/recorded-trial-lifecycle.json').unlink()
            result=case.verify(root)
            self.assertEqual(result['status'],'INCOMPLETE_EVIDENCE');self.assertEqual(result['official_inference_bounds'],[1,2])
    def test_partial_exit_and_failed_cleanup_keep_body_and_do_not_claim_success(self):
        for change in ({'owned_container_removed':False,'cleanup_failure':'fixture removal failure'}, {'failure':'TimeoutExpired: fixture','returncode':None,'stopped_state':None,'status':'FAILED'}):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);case=self.fixture(root)
                path=root/'native/execution.json';data=json.loads(path.read_text());data.update(change);case.write(path,data)
                result=case.verify(root)
                self.assertNotEqual(result['status'],'COMPLETE_DIAGNOSTIC');self.assertEqual(result['body']['verified_recording_inference_bounds'],[1,2])
                self.assertTrue(result['infrastructure_errors'])
    def test_missing_actual_driver_is_incomplete_and_different_driver_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);case=self.fixture(root,'complete');path=root/'native/observed-trial/recorded-trial.json'
            original=json.loads(path.read_text())
            for driver in (None,dict(renderer='different',vendor='other',version='other')):
                value=dict(original,driver=driver);case.write(path,value)
                top_path=root/'native/report.json';top=json.loads(top_path.read_text());top['recorded_trial_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();case.write(top_path,top)
                parent=root/'native/parent-completion.json';value=json.loads(parent.read_text());value['report_sha256']=hashlib.sha256(top_path.read_bytes()).hexdigest();case.write(parent,value)
                if driver is None:self.assertNotEqual(case.verify(root)['status'],'COMPLETE_DIAGNOSTIC')
                else:
                    with self.assertRaises(ValueError):case.verify(root)
    def test_primary_error_survives_secondary_digest_and_report_write_failures(self):
        events=[];secondary=[];primary=RuntimeError('original graph failure')
        def fail():raise OSError('secondary write failure')
        c.finalize_preserving_primary(primary,[fail,lambda:events.append('continued')],secondary)
        self.assertEqual(events,['continued']);self.assertTrue(any('secondary write failure' in v for v in secondary))
        with self.assertRaisesRegex(OSError,'secondary write failure'):c.finalize_preserving_primary(None,[fail],[])
    def test_absent_current_run_in_repository_snapshot_is_not_a_lock(self):
        with self.assertRaises(ValueError):c.validate_public_activity([dict(total_count=0,workflow_runs=[])],current_id=987)
    def test_source_sha_rejected_before_git_or_file_allocation(self):
        from scripts import run_recorded_official as h
        with patch.object(h.subprocess,'Popen',side_effect=AssertionError('git must remain cold')):
            with self.assertRaises(ValueError):h.source_manifest('not-a-sha')
    def test_dependency_count_bound_precedes_distribution_metadata_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for n in range(3):(root/str(n)).write_bytes(b'x')
            with patch.object(deps,'MAX_FILES',2),patch.object(deps,'installed_versions',side_effect=AssertionError('metadata read before namespace bound')):
                with self.assertRaises(ValueError):deps.describe(root)
    def test_full_admission_repeated_before_official_model_download_and_container(self):
        from scripts import run_recorded_official as h
        import inspect
        text=inspect.getsource(h.run)
        self.assertLess(text.index("refresh_admission(bundle,'before-model'"),text.index('model=download_checked('))
        self.assertLess(text.index("refresh_admission(bundle,'before-container'"),text.index('execution=c.clone('))
        workflow=(c.ROOT/c.WORKFLOW).read_text();self.assertIn('timeout-minutes: 210',workflow)


@unittest.skipUnless(sys.platform=='linux','Linux-only native finalization wrappers')
class MoreReviewRegressions(unittest.TestCase):
    def test_native_finalizer_preserves_graph_primary_after_digest_and_write_errors(self):
        from scripts import recorded_official_native as native
        from tests import test_full_s_recorded_receiver as fixtures
        from bigbench.full_s_recorded_worker import _read_receipt
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fixtures.trial_fixture(root/'observed-trial','graph')
            life=_read_receipt(root/'observed-trial/recorded-trial-lifecycle.json')
            report={k:life[k] for k in ('pid','parent_pid','nonce','seed','scenario')};report['failure']='original graph failure'
            with patch.object(native.pins,'digest',side_effect=OSError('digest failed')),patch.object(native.pins,'write',side_effect=OSError('write failed')):
                native.finalize_child(root,report,RuntimeError('original graph failure'))
            self.assertEqual(report['failure'],'original graph failure');self.assertEqual(len(report['secondary_errors']),2)
    def test_successful_body_followed_by_native_observer_failure_remains_partial(self):
        from tests.test_recorded_official_bundle import BundleTests
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);case=BundleTests();case.build(root)
            top=root/'native/report.json';value=json.loads(top.read_text());value.update(status='FAILED',failure='OSError: observer failed');case.write(top,value)
            child=root/'native/native-child.json';value=json.loads(child.read_text());value['returncode']=1;case.write(child,value)
            parent=root/'native/parent-completion.json';value=json.loads(parent.read_text());value.update(returncode=1,native_child_sha256=hashlib.sha256(child.read_bytes()).hexdigest(),report_sha256=hashlib.sha256(top.read_bytes()).hexdigest());case.write(parent,value)
            execution=root/'native/execution.json';value=json.loads(execution.read_text());value['returncode']=value['stopped_state']['ExitCode']=1;case.write(execution,value)
            result=case.verify(root)
            self.assertEqual(result['status'],'PARTIAL_DIAGNOSTIC');self.assertTrue(result['body']['producer_reported_body_success'])
            self.assertIn('observer failed',' '.join(result['infrastructure_errors']))
    def test_unresolved_ownership_only_preserves_runner_owned_regular_receipts(self):
        from scripts import run_recorded_official as host
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'native';out.mkdir();(out/'execution.json').write_bytes(b'{}');(out/'private').mkdir()
            (out/'link').symlink_to(c.ROOT/c.RUNTIME)
            result=host.retain_runner_evidence(out,root/'quarantine')
            self.assertEqual(result['retained'],['execution.json']);self.assertFalse((out/'link').exists());self.assertTrue((root/'quarantine/private').exists())


@unittest.skipUnless(sys.platform=='linux','Linux-only native envelope CPU fixtures')
class EarlyFailureRegression(unittest.TestCase):
    def test_failure_before_source_check_keeps_unknown_bounds_and_available_host_evidence(self):
        import shutil
        from tests.test_recorded_official_bundle import BundleTests
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);case=BundleTests();case.build(root,'graph');shutil.rmtree(root/'native/observed-trial')
            top=root/'native/report.json';value=json.loads(top.read_text())
            for key in ('source_map_sha256','sdk_sha256','core_sha256','dependencies','model_memory','source_stats_before','source_stats_after'):value.pop(key,None)
            value.update(parent_admission_checked=False,recorded_trial_sha256=None,official_model_process_bounds=[0,1],official_inference_bounds=[0,600],failure='ValueError: pre-source failure')
            case.write(top,value);parent=root/'native/parent-completion.json';value=json.loads(parent.read_text());value['report_sha256']=hashlib.sha256(top.read_bytes()).hexdigest();case.write(parent,value)
            # No body means no geometry/driver measurements to supply.
            from scripts import run_recorded_official as host
            with patch.object(host,'source_manifest',return_value=case.mapping):result=c.validate_native_bundle(root)
            self.assertEqual(result['status'],'INCOMPLETE_EVIDENCE');self.assertEqual(result['official_inference_bounds'],[0,600])
            self.assertIn('pre-source failure',' '.join(result['infrastructure_errors']))

if __name__=='__main__':unittest.main()
