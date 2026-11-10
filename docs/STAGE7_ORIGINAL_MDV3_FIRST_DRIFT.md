# Stage 7 — original PSSM official MD-V3 first sensor → ONNX divergence timeline

## Evidence source and status

- [GitHub Actions #42900493535](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42900493535), **completed SUCCESS only as data acquisition/validation**; official SHA-pinned MD-V3 bit-exact independent repeatability **0/4 PASS**.
- Four original native data ZIPs, each containing **run_0.json**, **run_1.json** and **strict_native_repeat_verdict.json**, downloaded from that exact successful workflow. GitHub artifact IDs: `13801783662` (20261109 left_right), `13801454469` (20261109 right_left), `13803316395` (20261110 left_right), `13803257337` (20261110 right_left); original aggregated summary artifact `13803795755`.
- For each of 4 cases, two independent original MetaDrive 0.4.3 PSSM/Chase + official ONNX executions, **12 newly captured RGB→warped RGB→I420→ONNX/action/recurrent steps each**. First mismatch is the minimum 1-based step whose stored hash/value differs between the two raw process traces.
- **No newly invented native result**: values below are recomputed from the existing archived real raw JSON files, not mock tests. Added `first_divergence_timeline` consumes only those existing receipts; it never changes the camera, simulator, model, GPU or feedback loop.

## Verified first mismatch step per original raw data field

| Seed | Scenario | Native road RGB | Native wide RGB | Warped road RGB | Warped wide RGB | Actual ONNX `new_img` | Raw model action | Recurrent state |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20261109 | `s_curve_left_right` | 4 | **2** | 4 | 5 | **4** | 4 | 4 |
| 20261109 | `s_curve_right_left` | 10 | **3** | 10 | 11 | **10** | 10 | 10 |
| 20261110 | `s_curve_left_right` | 7 | **2** | 7 | 6 | **6** | 6 | 6 |
| 20261110 | `s_curve_right_left` | **2** | 3 | 2 | 3 | **2** | 2 | 2 |

Each table entry is a 1-based **earliest disagreeing step**, not the number of changed pixels/bytes. Per-field SHA equality was taken directly from the two complete original execution receipts; no image tolerance, forced equality, replay or adjusted camera schedule was applied.

## Interpretation, with explicit limits

1. In **three of four** cases (20261109 left_right, 20261109 right_left, 20261110 left_right), the **native source wide RGB** disagreed at steps **2/3/2** while the actual ONNX input SHA and model action remained equal until steps **4/10/6**. A source-camera hash mismatch alone therefore **does not imply an ONNX input/model-action mismatch on the same step**.
2. In the fourth case (20261110 right_left), native source road RGB, model input, action and recurrent state first disagreed **together at step 2**.
3. At each case's earliest native source-camera mismatch, **the immediately preceding frame's recorded virtual world X/Y, heading, time, raw model action SHA and recurrent-state SHA still matched** between the independent runs. This is a recorded-state observation; it does **not** verify every internal Panda camera/PSSM rig state or prove a sole renderer root cause.
4. The exact pixel positions and magnitudes of raw-camera differences are **not available from hashes**. The fact that some raw wide RGB differences did not initially propagate into the warped/I420 input may reflect cropping, resampling, quantization, or another pipeline behavior, but **none of those explanations has been distinguished by this test**.
5. Later differences in actions and virtual position are compatible with closed-loop amplification after different image inputs, but this experiment does not establish that PSSM shadow timing is the unique cause. GPU depth/HDR terminal-only A/B experiments intentionally changed renderer semantics and cannot be substituted as proof of original-MD-V3 deterministic performance.

## Gate / next evidence required

**Stage 7 remains NOT PASSED**: original PSSM native model strict independent reproducibility **0/4**, despite correct diagnostic execution. The next root-cause gate is a separate controlled native study of camera-buffer readback/task timing and raw per-pixel differences at the **first source mismatch step**, while preserving a clearly labeled untouched original renderer control. Only repeat strict original-MD-V3 ONNX trials after causality is genuinely established. Do not claim model rankings, real-vehicle capabilities, CAN, CD210, Carrot MPC/Params behavior, or physical driving reliability.
