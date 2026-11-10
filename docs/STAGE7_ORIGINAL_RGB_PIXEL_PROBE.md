# Stage 7 — first 964×604 source RGB pixel disagreement, original PSSM MD-V3

## Hypothesis and scientific gate

Four repeated official original-PSSM MD-V3 native ONNX conditions previously failed **0/4 strict bit-exact repeatability**. The first raw road/wide RGB SHA divergence was at step 2–3; in some scenes it preceded changes to the actual ONNX input by several steps. A SHA comparison does not tell **where** the raw image differs. This experiment captures the original source image bytes and computes exact pixel-level differences without modifying the rendered model input.

**Original uninstrumented model repeatability remains a separate gate.** Retaining CPU image arrays for analysis uses additional memory and can change CPU timing, despite not inserting any extra GPU texture read, render or Panda task. This is *instrumented diagnosis only*, not proof of uninstrumented repeatability, GPU shadow causality, model driving skill or real-world safety.

## Experimental setup

- Simulator: MetaDrive **0.4.3**, same official SHA256-pinned assets as the existing original-MD-V3 recheck.
- Model: official **MD-V3** ONNX model ID 1365126a-e71e-4778-be00-8ab92dc82c09/12864/big_driving_supercombo.onnx; file SHA256 35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199. Model weights remain only on ephemeral CI runners.
- Matrix: seeds 20261109 and 20261110 × real MetaDrive S-curve left-right and right-left × two independent Panda/Xvfb/ONNX processes = **8 original-PSSM instrumented native sessions**, 12 fresh-image feedback steps per process. Source camera resolution **964×604**, road and wide.
- The default native camera path and the original perceive, PSSM/Chase task registration, rectification, I420 packing, ONNX inference, action and kinematics are unchanged when the opt-in observer is absent.
- The optional observer retains references to *already copied* original CPU source RGB arrays, **steps 1–6 only**. It adds no GPU memory extraction, frame rendering, task step, image byte mutation, per-step compression or image mask. Its extra CPU allocation is a potential timing confound that must be documented.
- **After** completing all 12 original ONNX feedback steps, the observer compresses the first six road/wide raw images per process with lossless zlib. Each source image is cross-checked to the recorded original SHA256 of the corresponding native ONNX episode.
- **After both independent processes finish**, a separate analyzer verifies bounded decompression, original SHA256, dimensions, process ID, scene, seed, model SHA and frame count. It calculates exact different pixel count, changed RGB channel count, per-channel absolute byte difference, bounding rectangle (inclusive XYXY), first 12 changed XY coordinates, a coarse 4×4 grid of changed-pixel counts, and a binary PNG mask at the earliest differing step. No pixel tolerance, image smoothing, frame replacement, or frame replay is permitted.
- The final four-case aggregate redownloads all raw compressed artifacts and independently recomputes every uploaded first-difference report. Missing images, malformed metadata and SHA mismatches fail closed.

## What can and cannot be concluded

Pixel locations can distinguish local changes from distributed frame differences and guide a later PSSM/Chase vs readback/timing A/B hypothesis. **They cannot, by themselves, identify the specific GPU shadow-pass root cause.** Neither a successful Actions run nor exact equality in an instrumented CPU-retention diagnostic proves the original uninstrumented MD-V3 strict-repeatability gate.

## Evidence / execution status

The previous **uninstrumented** official [native CI #42921722670](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42921722670) completed with **0/4 exact-match PASS**, even though its CI jobs reported SUCCESS. The first observed mismatch was at source RGB step 2 in all four cases in that run.

New instrumented pixel-difference CI results and exact pixel numbers must be added to this document only after confirming the actual completed GitHub Actions run, its commit and original artifacts. Synthetic unit tests are not evidence of native GPU results.

Stage 7 remains **NOT PASSED**. No real vehicle tests, CAN, CD210, Carrot MPC/Params, original-PSSM modification, or performance ranking.
