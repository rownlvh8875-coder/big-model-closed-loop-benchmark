import unittest,sys
from pathlib import Path
root=Path('/workspace/big-model-closed-loop-benchmark');sys.path.insert(0,str(root))
suite=unittest.defaultTestLoader.discover(str(root/'tests'))
def cases(s):
 for item in s:
  if isinstance(item,unittest.TestSuite):yield from cases(item)
  else:yield item
allcases=list(cases(suite));capacity=[t for t in allcases if t.id().endswith(('.PreparationTests.test_required_host_disk_capacity_is_measured_and_failure_facts_survive','.Abi0ImageFlowTests.test_full_memory_api_flow_reaches_download_after_exact_job','.FinalizationTests.test_full_six_child_schedule_and_final_publication_validation'))];assert len(capacity)==3
print('LOCAL_MATRIX: three real /dev/shm space-sensitive cases run separately; no filesystem facts mocked.',flush=True)
rest=unittest.TestSuite(t for t in allcases if t not in capacity);result=unittest.TextTestRunner(verbosity=2).run(rest)
raise SystemExit(0 if result.wasSuccessful() else 1)
