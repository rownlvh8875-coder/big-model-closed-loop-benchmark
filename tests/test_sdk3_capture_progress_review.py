"""Single-review regressions: no native SDK invocation."""
import json,tempfile,unittest
from pathlib import Path
from tests import test_sdk3_capture_progress_host as fixtures
write=fixtures.write
from scripts import run_sdk3_capture_progress as h,panda_sdk3_runtime as p

class ReviewRegressions(unittest.TestCase):
    def test_complete_trace_cannot_omit_reorder_duplicate_or_swallow_sensor_events(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixtures.Admission().complete_fixture(d);path=dest/'progress.jsonl';original=[json.loads(line) for line in path.read_text().splitlines()]
            capture_only=[r for r in original if r['event'].startswith('capture.')]
            missing_getter=[r for r in original if not (r['step']==1 and r['event'].startswith('get_rgb.'))]
            swapped=[dict(r,camera=('wide' if r['camera']=='road' else 'road') if r['step']==1 and r['camera'] else r['camera']) for r in original]
            duplicated=original[:7]+original[1:7]+original[7:]
            swallowed=[dict(r,event='get_rgb.error') if r['step']==1 and r['camera']=='road' and r['event']=='get_rgb.return' else r for r in original]
            for bad in [capture_only,missing_getter,swapped,duplicated,swallowed]:
                rows=[dict(r,seq=i+1,elapsed_s=i*.001,cpu_s=i*.001) for i,r in enumerate(bad)];path.write_text(''.join(json.dumps(r,separators=(',',':'))+'\n' for r in rows))
                with self.subTest(events=[r['event'] for r in bad[:5]]),self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
    def test_proc_snapshot_must_be_bounded_and_bound_to_actual_child(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixtures.Admission().fixture(d);path=dest/'watchdog.json';original=json.loads(path.read_text())
            for bad in [{'stat':'99999 (unrelated) R 1'},{'stat_error':'FileNotFoundError','status_error':'FileNotFoundError','wchan_error':'FileNotFoundError'},{'stat':42},{'stat':'11 (python) R '+('0 '*10000)},{'stat':'11 (python) R 1','extra':'unbound'}]:
                row=dict(original,proc_before_kill=bad);write(path,row)
                with self.subTest(snapshot=str(bad)[:70]),self.assertRaises(ValueError):h.validate_receipt(dest,ref,nonce)
    def test_completed_source_mismatch_is_not_a_diagnostic_pass_or_summary_pass(self):
        with tempfile.TemporaryDirectory() as d:
            dest,ref,nonce=fixtures.Admission().complete_fixture(d);reference=json.loads(ref.read_text());reference['prefix_sha256'][0]['road']='00'*32;write(ref,reference);r=json.loads((dest/'report.json').read_text());r['reference_sha256']=p.digest(ref);write(dest/'report.json',r)
            result=h.validate_receipt(dest,ref,nonce);self.assertTrue(result['native_completed']);self.assertFalse(result['source_image_equivalence']);self.assertFalse(result['renderer_diagnostic_passed']);self.assertEqual(result['status'],'TRACE_RECORDED_NATIVE_COMPLETED_SOURCE_MISMATCH');summary=h.observation_summary({},result);self.assertFalse(summary['renderer_diagnostic_passed']);self.assertEqual(summary['status'],'TRACE_RECORDED_NATIVE_COMPLETED_SOURCE_MISMATCH')

    def test_failed_capture_cannot_be_hidden_by_starting_another_capture(self):
        from scripts.sdk3_capture_progress import Journal,read_journal
        with tempfile.TemporaryDirectory() as d:
            j=Journal(Path(d),dict(pid=11,nonce='cpu'))
            for event,camera in [('capture.enter',None),('perceive.enter','road'),('task_step.enter','road'),('task_step.return','road'),('get_rgb.enter','road'),('get_rgb.error','road'),('perceive.error','road'),('capture.error',None)]:j.emit(event,step=1,camera=camera)
            j.emit('capture.enter',step=2);j.close()
            with self.assertRaises(ValueError):read_journal(Path(d)/'progress.jsonl')
