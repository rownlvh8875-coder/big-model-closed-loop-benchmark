"""Official SHA-pinned MD-V3, ONE fresh real MetaDrive+ONNX episode per process.

No camera convergence, HDR extraction, pixel tolerance, input replay, CARLA,
CD210, Carrot MPC, physical vehicle or performance ranking. This is a strict
same-model repeatability *observation*, not any driving-quality metric.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import uuid

import numpy as np

from bigbench.native_model_campaign import CampaignSpec, run_native_episode
from bigbench.onnx_policy import OnnxBigModelPolicy
from scripts.native_mdv3_rgb_pixel_capture import BoundedNativeRGBCapture


def recurrent_receipt(states: dict[str, np.ndarray]) -> str:
    """Digest all recurrent tensors with names, shapes, dtypes and exact bytes."""
    if not states:
        raise ValueError("missing recurrent model state")
    digest=sha256()
    for name, tensor in sorted(states.items()):
        value=np.asarray(tensor)
        if not np.all(np.isfinite(value)):
            raise ValueError("nonfinite recurrent model state")
        digest.update(name.encode("utf-8")+b"\0")
        digest.update(str(value.dtype).encode("ascii")+b"\0")
        digest.update(json.dumps(list(value.shape),separators=(",",":")).encode("ascii")+b"\0")
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


class AuditedOfficialOnnx(OnnxBigModelPolicy):
    """No input rewriting or controller override: record outputs of parent step."""
    def reset(self):
        super().reset()
        self.audit_rows=[]

    def step(self, observation):
        action=super().step(observation)
        raw=self.last_model_outputs["action"] if self.last_model_outputs is not None else None
        if raw is None or self.last_input_image_sha256 is None:
            raise RuntimeError("ONNX input/action audit unavailable")
        raw_values=[float(v) for v in raw]
        if not all(math.isfinite(v) for v in raw_values):
            raise RuntimeError("nonfinite raw model action")
        self.audit_rows.append({
            "new_img_sha256": self.last_input_image_sha256,
            "raw_model_action": raw_values,
            "raw_action_sha256": sha256(raw.tobytes(order="C")).hexdigest(),
            "state_after_step_sha256": recurrent_receipt(self.state),
        })
        return action


def run_trial(*, model: Path, spec: Path, scenario: str,
              seed: int, steps: int, speed: float, initial_fraction: float,
              raw_rgb_dir: Path | None = None) -> dict:
    if type(seed) is not int or type(steps) is not int or not 2 <= steps <= 30:
        raise ValueError("bounded seed/ONNX step count invalid")
    if initial_fraction not in (0.12, 0.28):
        raise ValueError("fraction is not admitted by reproducibility matrix")
    config=CampaignSpec(
        scenario=scenario,seed=seed,steps=steps,
        speed_mps=speed,initial_fraction=initial_fraction,
    )
    policy=AuditedOfficialOnnx(model,spec)
    raw_observer=BoundedNativeRGBCapture() if raw_rgb_dir is not None else None
    report=run_native_episode(policy,config,
                              full_s_route=False, camera_convergence=0,
                              raw_rgb_observer=raw_observer)
    rows=report.get("frames",[])
    if len(rows)!=len(policy.audit_rows) or len(policy.trace)!=len(rows):
        raise RuntimeError("native frame/ONNX audit step count differs")
    for row, audit in zip(rows,policy.audit_rows):
        if ("road_frame_sha256" not in row or "wide_frame_sha256" not in row
                or not row.get("source_road_rgb_sha256")
                or not row.get("source_wide_rgb_sha256")):
            raise RuntimeError("native original RGB or warped camera frame hashes absent")
        row.update(audit)
    report["status"]="DIAGNOSTIC_EXECUTED" if (
        report["status"]=="DIAGNOSTIC_EXECUTED" and len(rows)==steps
    ) else "FAILED_OR_INCOMPLETE"
    report.update({
        "process_id":os.getpid(),"process_uuid":uuid.uuid4().hex,
        "camera_capture_mode":"native_MetaDrive_perceive_sequential_per_step",
        "camera_convergence_attempts":0,"camera_pixel_tolerance":0,
        "camera_image_interpolation_or_replay":False,
        "gpu_hdr_extraction":False,"pssm_update_preserved":True,
        "initial_fraction":initial_fraction,
        "raw_action_and_recurrent_sha_captured_per_step":True,
        "actual_onnx_image_feed_sha_captured_per_step":True,
        "native_source_964x604_rgb_sha_captured_per_step":True,
        "real_vehicle_testing":False,"model_scoring_allowed":False,
        "cd210_fallback":False,"carrot_tuning_used":False,
        "trial_evidence":(
            "ORIGINAL_PSSM_WITH_OPT_IN_CPU_RGB_RETENTION_PROBE"
            if raw_observer is not None
            else "UNMODIFIED_METADRIVE_NEW_FRAME_OFFICIAL_ONNX_DIAGNOSTIC"
        ),
    })
    if raw_observer is not None:
        # CPU serialization occurs ONLY after the full model episode.
        report["raw_rgb_pixel_audit"]=raw_observer.save_after_episode(
            raw_rgb_dir,report
        )
    return report


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description="One isolated official MD-V3 native ONNX trial")
    p.add_argument("--model",type=Path,required=True)
    p.add_argument("--spec",type=Path,required=True)
    p.add_argument("--scenario",choices=("s_curve_left_right","s_curve_right_left"),
                   required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--steps",type=int,default=12)
    p.add_argument("--speed",type=float,default=8.)
    p.add_argument("--initial-fraction",type=float,default=.12)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--raw-rgb-dir",type=Path,default=None,
                   help="opt-in CPU retention of first six 964x604 RGB pairs; "
                        "instrumented diagnosis, NOT uninstrumented strict gate")
    a=p.parse_args(argv)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    try:
        report=run_trial(model=a.model,spec=a.spec,scenario=a.scenario,seed=a.seed,
                         steps=a.steps,speed=a.speed,
                         initial_fraction=a.initial_fraction,
                         raw_rgb_dir=a.raw_rgb_dir)
    except Exception as exc:
        report={
            "status":"ERROR",
            "error":f"{type(exc).__name__}: {exc}",
            "scenario":a.scenario,"seed":a.seed,
            "model_scoring_allowed":False,"real_vehicle_testing":False,
        }
    a.out.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
                     encoding="utf-8")
    print("OFFICIAL_MDV3_NATIVE_TRIAL",a.scenario,a.seed,
          report["status"],report.get("completed_steps"),flush=True)
    return 0 if report["status"]=="DIAGNOSTIC_EXECUTED" else 2


if __name__=="__main__":
    raise SystemExit(main())
