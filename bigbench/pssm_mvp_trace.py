"""Pure, fail-closed numeric PSSM MVP and registered-task receipt helpers.

NO shader editing, no GPU texture extraction, no Panda rendering, no ONNX.
Exact 64-bit serialization of each observed Python float. This reports
correlations only: shader matrix changes do not establish a sole causal source.
"""
from __future__ import annotations

from hashlib import sha256
import math
import struct
from typing import Any

import numpy as np


def exact_mvp_receipt(matrices: list[list[list[float]]]) -> dict:
    """Digest nested [split][row][col] 4x4 matrices with no quantization."""
    if not matrices or not isinstance(matrices, list):
        raise ValueError("at least one PSSM split matrix required")
    values = []
    for matrix in matrices:
        if not isinstance(matrix, list) or len(matrix) != 4:
            raise ValueError("PSSM MVP matrix must contain exactly 4 rows")
        for row in matrix:
            if not isinstance(row, list) or len(row) != 4:
                raise ValueError("PSSM MVP row must contain exactly 4 numbers")
            for v in row:
                if not isinstance(v, (float, int)) or not math.isfinite(v):
                    raise ValueError("non-finite PSSM matrix component")
                values.append(float(v))
    payload = b"".join(struct.pack("!d", x) for x in values)
    return {
        "status": "MVP_VALUES_CAPTURED",
        "split_count": len(matrices),
        "shape": [len(matrices), 4, 4],
        "all_f64_sha256": sha256(payload).hexdigest(),
        "matrix_values": [[[float(z) for z in row] for row in m] for m in matrices],
        "encoding": "big-endian binary64 of unrounded matrix cell observations",
    }


def capture_native_pssm_mvp(engine: Any) -> dict:
    """Copy C++ UnalignedLMatrix4f into Panda LMatrix4f before reading cells."""
    from panda3d.core import LMatrix4f

    pssm = getattr(engine, "pssm", None)
    rig = getattr(pssm, "camera_rig", None)
    if rig is None:
        raise RuntimeError("native PSSM camera rig absent: cannot trace shadow matrices")
    raw_matrices = rig.get_mvp_array()
    rows = []
    for raw in raw_matrices:
        aligned = LMatrix4f()
        aligned.assign(raw)
        rows.append([
            [float(aligned.getCell(i, j)) for j in range(4)]
            for i in range(4)
        ])
    return exact_mvp_receipt(rows)


def summarize_mvp_sequence(receipts: list[dict], *, warmup: int = 2) -> dict:
    """Preserve startup and late matrices. A stable hash is not shader proof."""
    if not isinstance(receipts, list) or len(receipts) < 3:
        raise ValueError("at least 3 MVP observations required")
    if type(warmup) is not int or warmup < 0 or warmup > len(receipts) - 2:
        raise ValueError("invalid MVP warmup")
    if any(r.get("status") != "MVP_VALUES_CAPTURED" for r in receipts):
        raise ValueError("one or more MVP reads unavailable")
    shapes = [tuple(r["shape"]) for r in receipts]
    if any(x != shapes[0] for x in shapes):
        raise ValueError("MVP split/matrix layout changed")
    hashes = [x["all_f64_sha256"] for x in receipts]
    arrays = [np.asarray(r["matrix_values"], dtype=np.float64) for r in receipts]
    if not all(np.all(np.isfinite(a)) for a in arrays):
        raise ValueError("non-finite numeric MVP values")
    baseline = arrays[warmup]
    after = arrays[warmup:]
    changed_per_frame = [int(np.count_nonzero(a != baseline)) for a in after]
    max_abs_per_frame = [float(np.max(np.abs(a-baseline))) for a in after]
    first_changed = next(
        (i + warmup for i, n in enumerate(changed_per_frame) if n), None
    )
    return {
        "status": "OBSERVED_NUMERIC_MVP_SEQUENCE",
        "split_count": shapes[0][0],
        "frame_count": len(receipts),
        "warmup": warmup,
        "all_frame_exact_f64_sha256": hashes,
        "all_unique_mvp_sha256": len(set(hashes)),
        "post_warmup_unique_mvp_sha256": len(set(hashes[warmup:])),
        "bit_exact_post_warmup": len(set(hashes[warmup:])) == 1,
        "max_changed_matrix_elements_post_warmup": max(changed_per_frame),
        "max_absolute_numeric_matrix_delta_post_warmup": max(max_abs_per_frame),
        "first_changed_frame_index_zero_based": first_changed,
        "values_post_warmup": [r["matrix_values"] for r in receipts[warmup:]],
        "startup_values_first": receipts[0]["matrix_values"],
        "not_a_gpu_shadow_map_capture": True,
    }


def compare_mvp_and_rgb(mvp: dict, rgb_status: dict, *, warmup: int = 2) -> dict:
    """Classify temporal co-variation, not unique attribution."""
    if mvp.get("status") != "OBSERVED_NUMERIC_MVP_SEQUENCE":
        raise ValueError("no valid MVP sequence")
    if rgb_status.get("post_warmup_unique_sha256") is None:
        raise ValueError("RGB stability observation missing")
    matrix_changed = mvp["post_warmup_unique_mvp_sha256"] > 1
    rgb_changed = rgb_status["post_warmup_unique_sha256"] > 1
    label = ("BOTH_MVP_AND_RGB_CHANGED" if matrix_changed and rgb_changed
             else "MVP_CHANGED_RGB_STABLE" if matrix_changed
             else "MVP_STABLE_RGB_CHANGED" if rgb_changed
             else "BOTH_STABLE_IN_THIS_SCENE")
    return {
        "classification": label,
        "mvp_post_warmup_unique_hashes": mvp["post_warmup_unique_mvp_sha256"],
        "rgb_post_warmup_unique_hashes": rgb_status["post_warmup_unique_sha256"],
        "pssm_causality_proven": False,
        "render_semantics_equivalence_proven": False,
        "model_scoring_allowed": False,
    }


def registered_task_metadata(task_manager: Any) -> list[dict]:
    """Registration/order hints, NOT instrumentation of actual execution order."""
    rows = []
    tasks = task_manager.getAllTasks()
    for task in tasks:
        name = str(task.getName())
        sort = None
        chain = None
        try:
            sort = int(task.getSort())
        except (AttributeError, TypeError, ValueError):
            pass
        try:
            chain = str(task.getTaskChain())
        except (AttributeError, TypeError, ValueError):
            pass
        rows.append({"name": name, "sort": sort, "chain": chain})
    return sorted(rows, key=lambda x: (
        x["sort"] is None, x["sort"] if x["sort"] is not None else 0, x["name"]
    ))
