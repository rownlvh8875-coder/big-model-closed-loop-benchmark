# Offline same-canvas color conversion audit

> **For agentic workers:** Root executes inline under the user's autonomous Stage7 instruction; use superpowers:executing-plans and one fresh independent source/result review. No native/model/CI dispatch is part of this task.

**Goal:** Measure the previously source-only RGB-conversion distinction on all128 already retained V3 model-canvas PNGs while GitHub evidence transport remains blocked.

**Architecture:** Read-only, source-pinned CPU analysis. Extract only the reviewed pure `rgb_to_nv12`, `align` and `get_nv12_info` AST function definitions from pinned official text; execute them in a NumPy-only namespace on each unchanged512×256 canvas, unpack active NV12 planes, and compare logical six planes with unchanged `rgb_frame_to_six`. Save measurements and provenance separately from immutable input data.

**Tech Stack:** Existing Python3.11/NumPy/OpenCV environment; stdlib PNG CRC/decompression, SHA256 and AST. External OPS helper/tests are archived with analysis provenance, not imported into the application.

**Spec:** Original autonomous Stage7 instruction plus `docs/STAGE7_INTEGRATION_VERIFICATION.md#rgb-and-i420-source-contract-audit` and preserved source-only audit `/tmp/stage7-rgb-i420-source-contract-audit.md`.

## Global constraints

- Existing128 warped PNGs from V3 only, selected before any numerical result; no new rendering, camera/GL/GPU reads, official weights, ONNX, controller or vehicle work.
- Freeze V3 ledger SHA256 `f1f2a9ffe80d85c98078ffc0e83460b92c7608cca12f65b4cc938ee61cf75e3f` and protocol `dfae8e79795a7890be78793603592afdc6074f2d4447a7a7004cb9e3de33c3ad`.
- Freeze20-source manifest `e4558054128c57eb66ba93d5713ddeb0c2aecec552a3700027b243277ccae068`; verify the two executed source-text hashes and preserved13 diagnostic/ModelSpec pins before image access.
- Existing adapter/packing/source/data remain unchanged. Same input holds warp/orientation fixed; official full1928×1208 SIM, pre-warp NV12, runtime production ISP and deployed warp equivalence are outside this calculation.
- This produces descriptive byte differences, no new PASS threshold, repeatability/tracking attribution, preferred converter, production replacement or Stage7 completion claim.
- Preserve PR33 optical/model/merge HOLD; no scientific retry or Cloud publication/reconfiguration. Read-only existing CI queries may continue independently.

## Review focus

- uint8 subtraction wrap, overflow and rounded2×2 chroma normalization: signed arithmetic and scalar-oracle tests.
- NV12 padding/interleave versus logical I420: extract only active planes; verify six-plane order with asymmetric pixels.
- Tampered/truncated PNG or source: pinned hashes, dimensions, CRCs and decoded-RGB SHA must pass before conversion; fail closed.
- Duplicate saved images: report both128 retained reads and unique RGB hashes; do not treat saved repeated canvases as independent trials.
- Scope: isolated same-canvas arithmetic is not actual official full-pipeline input or historical CI-runtime attestation.

### Task1: Frozen-input conversion comparison

**Files:** External `/workspace/.cloud-tools/stage7/offline_i420_audit.py` and `test_offline_i420_audit.py`; provenance/results under `output/stage7-offline-i420-conversion-audit/`; tracked result `docs/STAGE7_OFFLINE_I420_CONVERSION_AUDIT.md` after evidence review.

**Interface:** `sim_six(rgb, converter, layout)` returns active logical `[6,H/2,W/2] uint8`; `compare(a,b)` returns exact signed-difference statistics. The runner consumes the frozen ledger/source tree and writes source-bound per-image/all-image/unique-image measurements plus runtime/code provenance.

- [x] Write failing CPU tests for pinned scalar color values, asymmetric2×2 mean/plane order, signed-difference extremes, malformed PNG and source guards.
- [x] Implement only isolated pure-function loading, safe PNG/member verification, existing repo conversion and exact statistics; run the CPU suite to green.
- [x] Run the one frozen128-image CPU analysis; archive helper/tests/runtime and exact original member hashes. Record0 new native/model calls and unchanged source/data checks.
- [x] Obtain fresh independent source + complete result replay review, then document findings/limits and update continuation. Root owns Git/PR changes; applicable CI is observed, never presumed passed.

**Ruling:** this independent analysis is authorized by the user's instruction to continue independent work when integration is externally blocked. It extends a source-only finding with preserved-data arithmetic; it adds no application behavior or model input change.

Root and independent nine-test suites pass. The independent128-image replay is
byte-identical at analysis SHA256
`937a1986a88f92ffbd7c9af810cf38d476603aef63333be8a3ccf60df7e32026`;
all14 original provenance members and actual-sample scalar arithmetic were
independently checked. Fresh source/results review is CLEAR/root-accepted;
review SHA256 `d74065f0221d72a3990ebfef6738087e4662cf93033169750e075931690200b1`.
No material findings or deferred minors. The new four-doc commit changes no
runtime/workflow/source pins and requests basic CI only. Existing native/model/
merge/Cloud constraints remain in force; no CI/review success is presumed.
