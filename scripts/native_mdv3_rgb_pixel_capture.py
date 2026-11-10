"""Bounded, opt-in CPU RGB retention for Stage 7 original-PSSM MD-V3.

The existing NativeWorldCamera already privately copies uint8 source images
before rectification and hashes them. This observer retains REFERENCES to
those copies for the first six camera pairs; it does not re-render/read the
GPU or serialize/compress pixels until AFTER the native ONNX episode ends.
It IS additional CPU/memory instrumentation, so its independent trials must
be labeled separately from an uninstrumented official exact-repeat gate.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import zlib

import numpy as np


SHAPE = (604, 964, 3)
MAX_CAPTURE_STEPS = 6
CAMERAS = ("road", "wide")
RAW_NBYTES = 604 * 964 * 3


class BoundedNativeRGBCapture:
    def __init__(self, max_steps: int = MAX_CAPTURE_STEPS):
        if type(max_steps) is not int or not 2 <= max_steps <= MAX_CAPTURE_STEPS:
            raise ValueError("invalid bounded raw RGB capture size")
        self.max_steps = max_steps
        self.observed_steps = 0
        self.captures: list[tuple[dict, dict]] = []

    def record_native_rgb(self, rgb: dict, hashes: dict):
        """Called once after a completed original road+wide camera pair.

        Retains the *already-owned* CPU uint8 arrays, NOT new GPU readback.
        Hash/data validation and compression are deferred until the end.
        """
        self.observed_steps += 1
        if self.observed_steps > self.max_steps:
            return
        if set(rgb) != set(CAMERAS) or set(hashes) != set(CAMERAS):
            raise ValueError("both real native road/wide images required")
        if any(not isinstance(rgb[k], np.ndarray)
               or rgb[k].dtype != np.uint8
               or rgb[k].shape != SHAPE
               or not rgb[k].flags.c_contiguous for k in CAMERAS):
            raise ValueError("original native RGB shape/dtype/contiguity invalid")
        self.captures.append(({k:rgb[k] for k in CAMERAS},
                              {k:hashes[k] for k in CAMERAS}))

    def save_after_episode(self, directory: Path, report: dict) -> dict:
        rows = report.get("frames", [])
        if (report.get("status") != "DIAGNOSTIC_EXECUTED"
            or self.observed_steps != report.get("completed_steps")
            or len(rows) != report.get("requested_steps")
            or len(self.captures) != min(self.max_steps, len(rows))):
            raise ValueError("incomplete original native RGB/ONNX episode")
        if report.get("pssm_update_preserved") is not True:
            raise ValueError("original PSSM was not preserved")
        if report.get("gpu_hdr_extraction") is not False:
            raise ValueError("GPU extraction cannot be mixed with the RGB probe")
        directory.mkdir(parents=True,exist_ok=True)
        images = []
        for i,(rgb, hashes) in enumerate(self.captures,1):
            for camera in CAMERAS:
                original_sha = rows[i-1][f"source_{camera}_rgb_sha256"]
                if hashes[camera] != original_sha:
                    raise ValueError("retained source SHA differs from actual ONNX trial")
                raw = rgb[camera].tobytes(order="C")
                if len(raw) != RAW_NBYTES or sha256(raw).hexdigest() != original_sha:
                    raise ValueError("retained native pixels differ from recorded SHA")
                name = f"step-{i:02d}-{camera}.rgb.zlib"
                compressed = zlib.compress(raw, level=6)
                (directory / name).write_bytes(compressed)
                images.append({
                    "step":i, "camera":camera, "file":name,
                    "sha256":original_sha, "raw_bytes":len(raw),
                    "compressed_bytes":len(compressed),
                })
        manifest = {
            "status":"CPU_ONLY_NATIVE_RGB_FIRST_STEPS_RETAINED",
            "probe_is_not_uninstrumented_original_strict_gate":True,
            "camera_capture_semantics":"original_perceive_sequential",
            "original_pssm_chase_tasks_preserved":True,
            "additional_gpu_readback_or_render_tasks":False,
            "original_native_image_shape_hwc":list(SHAPE),
            "seed":report["seed"],
            "scenario":report["scenario"],
            "model_sha256":report["model_sha256"],
            "process_uuid":report["process_uuid"],
            "total_native_onnx_steps":len(rows),
            "captured_step_count":len(self.captures),
            "images":images,
            "model_scoring_allowed":False,
            "real_vehicle_testing":False,
        }
        target=directory/"manifest.json"
        target.write_text(json.dumps(manifest,indent=2,ensure_ascii=False,
                                      allow_nan=False)+"\n",encoding="utf-8")
        return {
            "enabled":True,
            "captured_step_count":len(self.captures),
            "total_steps":len(rows),
            "archive_status":manifest["status"],
            "probe_may_perturb_cpu_scheduling":True,
            "is_uninstrumented_strict_repeatability_gate":False,
        }
