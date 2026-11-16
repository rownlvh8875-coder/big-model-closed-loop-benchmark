import os,sys,unittest
root='/workspace/big-model-closed-loop-benchmark';sys.path[:0]=[root,root+'/tests']
import test_first_divergence_model as f
_original_fixture_setup=f.ValidationTests.setUp
def actual_fixture_setup(self):
 _original_fixture_setup(self)
 os.environ['RUNNER_TEMP']='/dev/shm'
f.ValidationTests.setUp=actual_fixture_setup
class ActualShmFinalization(f.FinalizationTests):
 def setUp(self):
  super().setUp()
  # This isolated test really writes under /dev/shm. Preserve the guard and
  # all application logic; register the actual ephemeral root after fixture setup.
  os.environ['RUNNER_TEMP']='/dev/shm'
suite=unittest.TestSuite([ActualShmFinalization('test_full_six_child_schedule_and_final_publication_validation')])
suite.addTests(unittest.defaultTestLoader.loadTestsFromNames(['tests.test_engine_clock_builder_preparation.PreparationTests.test_required_host_disk_capacity_is_measured_and_failure_facts_survive','tests.test_panda_sdk_abi0_image_flow.Abi0ImageFlowTests.test_full_memory_api_flow_reaches_download_after_exact_job']))
print('Actual /dev/shm TMPDIR and RUNNER_TEMP for the six-child DATA fixture; no capacity/guard/application mocks.',flush=True)
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
