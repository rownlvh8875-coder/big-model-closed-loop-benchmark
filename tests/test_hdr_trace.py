"""Unit test doubles only: cannot claim native MetaDrive evidence from this suite."""
import unittest

from scripts.metadrive_hdr_trace import (
    STAGES, gpu_readback, receipt, summarize_stream, compare_reports,
)


class Ram:
    def __init__(self, data): self.data = data
    def getData(self): return self.data


class Texture:
    def __init__(self, data): self.data = data
    def getRamImage(self): return Ram(self.data)
    def getXSize(self): return 2
    def getYSize(self): return 2
    def getZSize(self): return 1
    def getFormat(self): return 12
    def getComponentType(self): return 7


class Graphics:
    def __init__(self, ok=True): self.ok = ok; self.calls = 0
    def extractTextureData(self, texture, gsg):
        self.calls += 1
        return self.ok


class Engine:
    def __init__(self, ok=True): self.graphicsEngine = Graphics(ok)


class TraceContractTests(unittest.TestCase):
    def test_unavailable_gpu_is_not_identical(self):
        engine = Engine(False)
        item = gpu_readback(engine, "hdr", Texture(b"test"), object())
        self.assertEqual(item[0]["status"], "UNAVAILABLE")
        result = summarize_stream([item] * 4, 2)
        self.assertIsNone(result["bit_exact_after_warmup"])
        self.assertEqual(result["status"], "INCONCLUSIVE_STAGE_UNAVAILABLE")
        self.assertEqual(engine.graphicsEngine.calls, 1)

    def test_successful_readback_metadata(self):
        engine = Engine()
        item = gpu_readback(engine, "hdr", Texture(b"test"), object())
        self.assertEqual(item[0]["metadata"]["dimensions"], [2, 2, 1])
        result = summarize_stream([item] * 4, 2)
        self.assertTrue(result["bit_exact_after_warmup"])
        self.assertEqual(engine.graphicsEngine.calls, 1)

    def test_raw_byte_differences_keep_startup(self):
        samples = [receipt(v, "stage") for v in (b"aaa", b"abc", b"abb", b"abc")]
        result = summarize_stream(samples, 2)
        self.assertFalse(result["bit_exact_all"])
        self.assertFalse(result["bit_exact_after_warmup"])
        self.assertEqual(result["max_changed_bytes_after_warmup"], 1)
        self.assertEqual(result["first_changed_byte_offsets_after_warmup"], [2])
        self.assertEqual(len(result["frames"]), 4)

    def test_layout_changes_fail_closed(self):
        a = receipt(b"a", "stage")
        b = receipt(b"ab", "stage")
        result = summarize_stream([a, a, a, b], 2)
        self.assertEqual(result["status"], "INCONCLUSIVE_LAYOUT_CHANGED")
        self.assertIsNone(result["bit_exact_after_warmup"])

    @staticmethod
    def fake_report(name):
        conditions = {"baseline": None, "shadow_disabled": "PSSM.update",
                      "chase_disabled": "update main chase camera"}
        stages = {stage: summarize_stream([receipt(b"a", stage)] * 4, 2)
                  for stage in STAGES}
        return {
            "status": "OBSERVED_BUFFER_CHAIN",
            "seed": 20261109, "pose_id": "origin",
            "pose": [[0, 0, 1.22], [-90, 0, 0]],
            "frames": 4, "warmup": 2, "scene": "ego_hidden",
            "capture_mode": "task_step_pair",
            "ablation": name, "removed_task": conditions[name],
            "stages": stages,
            "real_vehicle_testing": False, "model_scoring_allowed": False,
        }

    def test_matched_reports_do_not_rank_models(self):
        reports = {name: self.fake_report(name)
                   for name in ("baseline", "shadow_disabled", "chase_disabled")}
        comparison = compare_reports(reports)
        self.assertTrue(comparison["ranking_prohibited"])
        self.assertFalse(comparison["model_scoring_allowed"])
        self.assertEqual(comparison["between_process_same_index"]["shadow_disabled"]
                         ["road_hdr"]["same_index_equal_hashes"], 2)
        reports["chase_disabled"]["seed"] = 20261110
        with self.assertRaises(ValueError):
            compare_reports(reports)

    def test_missing_stage_prohibits_claim(self):
        reports = {name: self.fake_report(name)
                   for name in ("baseline", "shadow_disabled", "chase_disabled")}
        reports["shadow_disabled"]["status"] = "INCONCLUSIVE_NATIVE_TRACE"
        with self.assertRaises(ValueError):
            compare_reports(reports)


if __name__ == "__main__":
    unittest.main()
