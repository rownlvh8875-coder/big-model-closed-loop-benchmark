"""Pure unit contracts only. These do NOT constitute native Panda3D evidence."""
import copy
import unittest

from bigbench.pssm_mvp_trace import (
    exact_mvp_receipt, summarize_mvp_sequence, compare_mvp_and_rgb,
    registered_task_metadata,
)


def mvp(n=0.0):
    m=[[[float(i==j) for j in range(4)] for i in range(4)]]
    m[0][1][2]=float(n)
    return exact_mvp_receipt(m)


class FakeTask:
    def __init__(self, name, sort=0, chain="default"):
        self.name=name
        self.sort=sort
        self.chain=chain
    def getName(self): return self.name
    def getSort(self): return self.sort
    def getTaskChain(self): return self.chain


class Manager:
    def getAllTasks(self):
        return [FakeTask("igLoop",50),FakeTask("PSSM.update",0),
                FakeTask("update main chase camera",0)]


class MVPTraceContractTests(unittest.TestCase):
    def test_no_rounding_and_exact_digest(self):
        a=mvp(1e-8)
        b=mvp(2e-8)
        self.assertNotEqual(a["all_f64_sha256"],b["all_f64_sha256"])
        self.assertEqual(a["shape"],[1,4,4])
        self.assertEqual(a["matrix_values"][0][1][2],1e-8)

    def test_warmup_retained_and_matrix_delta_measured(self):
        reports=[mvp(1),mvp(2),mvp(3),mvp(3),mvp(4)]
        d=summarize_mvp_sequence(reports,warmup=2)
        self.assertEqual(len(d["all_frame_exact_f64_sha256"]),5)
        self.assertEqual(d["post_warmup_unique_mvp_sha256"],2)
        self.assertEqual(d["first_changed_frame_index_zero_based"],4)
        self.assertEqual(d["max_changed_matrix_elements_post_warmup"],1)
        self.assertEqual(d["max_absolute_numeric_matrix_delta_post_warmup"],1)
        self.assertFalse(d["bit_exact_post_warmup"])

    def test_unavailable_or_changed_matrix_layout_fails(self):
        with self.assertRaises(ValueError):
            exact_mvp_receipt([])
        with self.assertRaises(ValueError):
            exact_mvp_receipt([[[1,2,3,4]]])
        with self.assertRaises(ValueError):
            exact_mvp_receipt([[[float("nan")]*4]*4])
        with self.assertRaises(ValueError):
            summarize_mvp_sequence([mvp(0),mvp(0),{"status":"UNAVAILABLE"}])
        z=exact_mvp_receipt([mvp()["matrix_values"][0]]*2)
        with self.assertRaises(ValueError):
            summarize_mvp_sequence([mvp(0),mvp(0),z])

    def test_no_unique_causal_claim_from_mvp_rgb_joint_change(self):
        mm=summarize_mvp_sequence([mvp(0),mvp(0),mvp(0),mvp(1)])
        x=compare_mvp_and_rgb(mm,{"post_warmup_unique_sha256":2})
        self.assertEqual(x["classification"],"BOTH_MVP_AND_RGB_CHANGED")
        self.assertFalse(x["pssm_causality_proven"])
        self.assertFalse(x["model_scoring_allowed"])
        y=compare_mvp_and_rgb(mm,{"post_warmup_unique_sha256":1})
        self.assertEqual(y["classification"],"MVP_CHANGED_RGB_STABLE")

    def test_task_registry_sorted_but_not_execution_proof(self):
        rows=registered_task_metadata(Manager())
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[-1]["name"],"igLoop")
        self.assertEqual(rows[0]["sort"],0)
        self.assertEqual(rows[0]["chain"],"default")


if __name__=="__main__":
    unittest.main()
