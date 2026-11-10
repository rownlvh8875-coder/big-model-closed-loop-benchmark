"""Pure Python profiler receipt contracts. These are NOT native Panda tests."""
import unittest

from bigbench.native_callback_profiler import (
    CallbackTraceError, summarize_callback_pair,
    summarize_callback_sequence,
)


def events_for(order, start=0):
    rows=[]
    for name in order:
        t=start+len(rows)*10
        rows.append({"order_in_trace":len(rows),"event":"call",
                     "callback":name,"perf_counter_ns":t})
        rows.append({"order_in_trace":len(rows),"event":"return",
                     "callback":name,"perf_counter_ns":t+5})
    return rows


class CallbackProfilerContracts(unittest.TestCase):
    def test_actual_order_pssm_first(self):
        e=events_for(["PSSM.update","MainCamera._chase_task"])
        x=summarize_callback_pair(e,1)
        self.assertEqual(x["actual_callback_calls"],2)
        self.assertEqual(x["per_taskmgr_step_callback_call_order"],
                         [["PSSM.update","MainCamera._chase_task"]])
        self.assertFalse(x["registered_task_objects_replaced"])
        self.assertTrue(x["trace_changes_cpu_timing"])

    def test_actual_order_chase_first_and_two_ticks(self):
        one=events_for(["MainCamera._chase_task","PSSM.update"])
        two=events_for(["PSSM.update","MainCamera._chase_task"],start=100)
        rows=one+two
        for i,v in enumerate(rows):
            v["order_in_trace"]=i
        r=summarize_callback_pair(rows,2)
        seq=summarize_callback_sequence([r,r],expected_steps=2)
        self.assertEqual(seq["observed_taskmgr_ticks"],4)
        self.assertFalse(seq["all_ticks_same_callback_order"])
        self.assertEqual(len(seq["order_frequencies"]),2)
        self.assertFalse(seq["model_driving_rank_allowed"])

    def test_missing_chase_task_cannot_be_assumed_from_sort(self):
        e=events_for(["PSSM.update","PSSM.update"])
        with self.assertRaises(CallbackTraceError):
            summarize_callback_pair(e,1)

    def test_unbalanced_and_reentrant_events_fail(self):
        e=events_for(["PSSM.update","MainCamera._chase_task"])
        with self.assertRaises(CallbackTraceError):
            summarize_callback_pair(e[:-1],1)
        broken=events_for(["PSSM.update","MainCamera._chase_task"])
        broken[1]["event"]="call"
        with self.assertRaises(CallbackTraceError):
            summarize_callback_pair(broken,1)
        backwards=events_for(["PSSM.update","MainCamera._chase_task"])
        backwards[2]["perf_counter_ns"]=0
        with self.assertRaises(CallbackTraceError):
            summarize_callback_pair(backwards,1)

    def test_two_exits_do_not_infer_interleaving(self):
        overlapping=[
          {"event":"call","callback":"PSSM.update","perf_counter_ns":1},
          {"event":"call","callback":"MainCamera._chase_task","perf_counter_ns":2},
          {"event":"return","callback":"MainCamera._chase_task","perf_counter_ns":3},
          {"event":"return","callback":"PSSM.update","perf_counter_ns":4},
        ]
        with self.assertRaises(CallbackTraceError):
            summarize_callback_pair(overlapping,1)


if __name__=="__main__":
    unittest.main()
