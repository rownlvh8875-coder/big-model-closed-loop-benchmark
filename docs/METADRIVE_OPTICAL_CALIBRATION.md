# MetaDrive virtual camera optical integration — Phase 1

**Status (2026-11-11 evidence review): historical native pinhole intrinsics, pose-dependent RGB/I420 plumbing and sampled virtual straight/S-curve/ramp paint-alignment diagnostics PASS. Real comma optics, production preprocessing equivalence and driving performance remain unvalidated. The later renderer candidate has separate bounded inference-repeatability results; these historical images do not provide a candidate-specific paint gate.**

This work is a **simulator-only** experiment: no real vehicle testing, CAN, CD210, Carrot MPC or vehicle-specific dynamics.

## What was implemented

1. `bigbench/optical_calibration.py`: Reference camera intrinsics and independent road/wide homographies, strict source-shape and measured-lens checks, source coverage audit, and 512×256 rectified RGB outputs.
2. `bigbench/metadrive_camera.py`: Optional real MetaDrive RGB sensor classes (CPU RAM-backed) and camera-only virtual pose capture using `BaseCamera.perceive(new_parent_node=..., position=..., hpr=...)` with **no physics-based ego steering**. OnnxBigModelPolicy can consume the resulting paired model canvases.
3. `scripts/metadrive_optical_check.py`: Bounded, offscreen MetaDrive optical-check workflow with either two pose-shifted views or (when a model file and manifest are supplied) a short ONNX + virtual-pose feedback test. Outputs `optical_report.json` and rendered PNG images. **No model ranking or lane-intrusion metrics.**
4. `tests/test_optical_calibration.py`: deterministic pinhole landmark reprojection, source crop coverage, focal/centering mismatch rejection and test-double feedback proof.
5. `.github/workflows/metadrive-optical.yml`: optional native headless MetaDrive smoke, triggered on optical-related code changes or manually; run status must be checked before claiming native renderer validation.

## Pinhole intrinsics and model transforms

These numbers come from the published **zero-distortion pinhole approximation** in:
- [`commaai/openpilot/openpilot/common/transformations/camera.py`](https://github.com/commaai/openpilot/blob/master/openpilot/common/transformations/camera.py): narrow `K`: source `1928×1208`, `fx=fy=2648`, center `(964,604)`; wide `fx=fy=567`.
- [`commaai/openpilot/openpilot/common/transformations/model.py`](https://github.com/commaai/openpilot/blob/master/openpilot/common/transformations/model.py): model narrow `512×256`, focal `910`, center `(256,47.6)`; model big/wide `512×256`, focal `455`, center `(256,151.8)`.
- [`ajouatom/openpilot/openpilot/selfdrive/modeld/modeld.py`](https://github.com/ajouatom/openpilot/blob/carrot-wip/openpilot/selfdrive/modeld/modeld.py): ordinary image uses `get_warp_matrix(..., False)`, big image uses `get_warp_matrix(..., True)`.

For the current **aligned, zero-rotation** assumption, destination-to-source homography is
`H = K_source @ inverse(K_model)`.

The adapter feeds this mapping into `cv2.warpPerspective(..., WARP_INVERSE_MAP)` so that raw-rendered source pixels are sampled into the model's intended camera coordinates **before** RGB→I420→6-plane packing.

Default MetaDrive source rendering resolution is `964×604` (exact 1/2 scale of the source reference), which scales both focal lengths and principal points equally. This is a geometric-equivalent lower-resolution rendering, not a photometric-quality or aliasing-equivalent substitute for actual camera frames.

| Camera | Source pinhole focal at 964×604 | Horizontal FOV | Model target focal | Model horizon y |
|---|---:|---:|---:|---:|
| narrow road | 1324 px | ≈40.01° | 910 px | 47.6 px |
| wide road | 283.5 px | ≈119.07° | 455 px | 151.8 px |

Both raw camera lenses are measured through Panda3D `getFilmSize/getFocalLength/getFilmOffset` and checked against the reference (default focal tolerance 1%, principal point ±0.5 px). Crop coverage must be ≥99%. **An unexpected lens, nonzero film offset, aspect mismatch or blank/stale frames fails the optical probe** instead of silently resizing or fabricating success.

## Executing the real MetaDrive probe (on a compatible PC or Github Actions)

These geometry-only commands ran **in GitHub Actions on 2026-11-09 using MetaDrive 0.4.3, Xvfb/software OpenGL and the official 134,074,203-byte release assets**. The earlier statement that the simulator was absent described the 2026-11-09 sandbox, not the current Cloud environment:

```bash
python -m pip install '.[inference]' 'metadrive-simulator==0.4.3'
xvfb-run -a python -m scripts.metadrive_optical_check --out output/metadrive-optics --steps 2
```

Official model weights and inference belong to the reviewed CI workflows, using ephemeral `$RUNNER_TEMP/models` and the pinned manifest; do not create a persistent local model cache for this task. The model CLI still exists, but the local model-path example is intentionally replaced by the [candidate workflow/results](STAGE7_MDV3_RENDERER_CANDIDATE.md) and [bounded expansion protocol](STAGE7_MDV3_CANDIDATE_EXPANSION.md). A geometry-only command does not authorize a model execution.

To run without downloading a large model, GitHub Actions provides the separate workflow `Real MetaDrive offscreen camera optical probe (NO real vehicle)` (manual or scoped push). Official rendering assets were pre-fetched from the tagged release because MetaDrive's automatic download returned HTTP 504 on an earlier run.

## Native MetaDrive evidence (PASS, with explicit limitations)

- [GitHub Actions run 42569322601](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42569322601): completed successfully with native MetaDrive 0.4.3, Xvfb and software OpenGL.
- Official asset package: MetaDrive-0.4.3/assets.zip; 134,074,203 bytes; SHA256 **4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9**.
- Native artifact: **metadrive-optical-probe** with four distinct 512×256 PNG images and the optical_report.json audit. Both road and wide images change after the virtual camera moves.
- Narrow measured source: fx=1323.9998636, fy=1323.9999425 (target 1324 px). Wide measured source: fx=283.5000334, fy=283.5000503 (target 283.5 px).
- Narrow warp source coverage **0.99609375 (99.609375%)**; wide source coverage **1.0 (100%)**.
- These values confirm reference **pinhole intrinsics, digital cropping and actual frame changes**, NOT real comma lens fidelity or independent physical-world landmark pixel residuals.
- **PASS:** [GitHub Actions run 42569804426](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42569804426), commit 2e2ae997, verifies native MetaDrive source RGB → I420/YUV6 **(2,6,128,256), uint8** ONNX camera input. Road/wide packed tensors are different, and the final packed input changes after the virtual camera pose changes. **This does not confirm actual ONNX inferencing using MetaDrive imagery.**

## Virtual gates that passed, with retained scope

- Native pinhole lens measurement, offscreen RGB, model-canvas warp and pose-dependent frame changes passed the two optical runs above. The first report records the optical probe; the second adds the actual I420 shape/distinctness/pose-change checks. Neither optical probe ran ONNX.
- [Straight virtual world-to-paint projection](METADRIVE_LANE_REPROJECTION.md) passed run 42573166387: one seed, two camera poses and both cameras, including a +27 px negative control.
- [S-curve/ramp projection](METADRIVE_CURVED_LANE_AUDIT.md) passed final run 42578810503: one seed `20261109`, four scenes and two static poses/cameras per scene. Initial 0/4 and second 3/4 failures remain recorded. The final focus gate changed after those failures and is not a preregistered holdout. Left→right bend 2 Wide retains `global_negative_discriminating=false`; only its focused curve control satisfies the final required discrimination.
- [Native target-lane math](LANE_TRUTH_EVALUATOR.md) passed run 42582782731 on eight selected lanes. This is geometric coordinate self-consistency and deliberate footprint arithmetic, not an ONNX trajectory or driving score.

## Remaining optical and performance gates

Physical camera extrinsics (translation/roll/pitch/yaw), lens distortion/fisheye, rolling shutter, exposure, tonemapping, colorimetry and temporal synchronization remain unvalidated. The sampled virtual reprojection checks do not measure a real mount or establish universal left/right/yaw/height calibration under arbitrary poses. Production NV12 warp interpolation, color conversion and camera-preprocessing equivalence also remain unverified.

The experimental official MD-V3 candidate separately passes two twelve-step 4/4 repeatability cohorts; this is not a statistical model ranking or physical optical validation. Its later `feedback_both`/unsorted renderer was not used for the historical paint PNGs, so a candidate-specific paint gate and global renderer equivalence have not been established. Legacy expansion run 42987993022 now has independently accepted 12/12 legacy repeatability, including all 13 archives. It does not establish motion validity because its applied-action basis bridge is missing; PR #27 merged as `bdcf91e4d3a98399503a0ba215b66920b0436c08`. [Integration evidence and limits](STAGE7_INTEGRATION_VERIFICATION.md) distinguish these gates. Stage 7 and driving-performance rankings remain open.

## Archive verification and pure image audit

| Run | Source HEAD | Artifact ID | ZIP bytes | ZIP SHA256 |
|---|---|---:|---:|---|
| [42569322601](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42569322601) | `fd1a8892b2feb67030d4e4ae71b0d3cd6e1e63df` | 13652950905 | 720429 | `83ce9a0b6deae68bc4b910eb39469b70ce9fbcbc16cdeb6d5e588d44da4f29dc` |
| [42569804426](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42569804426) | `2e2ae997319d9e1722e6c1fb60182112ec263689` | 13653175550 | 720494 | `c4a56751fd8059ff7cf371ec76627ba55d04e3d471c8b653d1a4bc8589b40f45` |

The complete seven-archive historical ledger is in [integration verification](STAGE7_INTEGRATION_VERIFICATION.md). Original ZIPs and member bytes, API metadata, source snapshots and full hashes are retained in ignored `output/stage7-geometry-integration-audit/`. API SHA256/size, bounded safe ZIP paths and absence of symlinks were verified.

The two optical artifacts contain model-canvas PNGs, not raw 964×604 source PNGs. Pure rechecks reproduce recorded homographies/coverage and verify distinct pose-dependent images; I420 can be reconstructed from those canvases. That reconstruction cannot regenerate the original source-to-canvas sampling or add historical ONNX evidence to the first probe. All 52 paint images elsewhere in the audit reproduce counts, detected coordinates, controls and gates; calculated residuals have at most `1.7763568394002505e-15` px floating-point roundoff. Original JSON is not claimed wholly byte-identical, and no model comparison tolerance changes.

## Evidence distinctions

- `CAMERA_PROVIDER_TEST_DOUBLE_NOT_METADRIVE`: artificial RGB frames for adapter unit tests; not MetaDrive images.
- `METADRIVE_REAL_RENDER_PINHOLE_INTRINSICS_ONLY`: MetaDrive RGB rendered and source pinhole intrinsics checked; not equivalent to comma sensor.
- `METADRIVE_REAL_RENDER_VIRTUAL_PINHOLE_UNCALIBRATED`: real MetaDrive + ONNX inferencing from changing virtual positions; not a driving-performance score.

These labels must **never** be treated as real road safety, actual camera optical verification, or an approval to conduct physical-vehicle tests.


## Applied-action frame contract: confirmed legacy gap

Read-only pinned-source and pure-math evidence in `output/stage7-coordinate-contract-audit/coordinate_basis_proof.json` confirms a missing **model-body FRD → integrator-body FLU applied-action rotation** in the legacy path. Model FRD is forward/right/down; the virtual integrator expects forward/left/up with positive curvature increasing counterclockwise world heading. **Both bases are right-handed.** `R = diag(1,-1,-1)` has determinant +1 and rotates the body basis 180° about forward. The required bridge is `k_world = -k_model`; longitudinal acceleration is unchanged. This is not a global world-Y flip, camera/image change, controller tuning or smoothing.

The numeric model convention `k_model = raw_lateral / max(2.5, speed)**2` is correct. Its unchanged value was applied directly to the differently signed world-yaw integrator. Therefore historical model repeatability gates, including the candidate 4/4 cohorts and PR #27 source `e84369c9f7f461a59c8d506b8b9efb2312297c03`, establish **legacy repeatability only, not valid model-to-world motion binding**. The static geometry/pixel and lane-coordinate checks above remain their own bounded results; they never exercised this model-action bridge.

A prospective corrected protocol preserves all four raw model outputs, recurrent states and actual I420 evidence, and separately rotates only the applied action. At that earlier audit checkpoint the corrected adapter was **TDD in progress, not complete**, and its native gate had **not executed**. It must retain separate parent-model/applied-world receipts and a distinct gate; old actions, poses and labels stay immutable. The sign gap is confirmed, but its sole responsibility for tracking errors, model quality and renderer/optical equivalence is unproven. [Integration verification](STAGE7_INTEGRATION_VERIFICATION.md) records the evidence and pending validation.


Legacy expansion run **42987993022** is now fully independently revalidated: `camera028`, `native_ramps` and `longer160` each pass **4/4 legacy repeatability**, total **12/12**, with 24 fresh UUIDs/nonces, 1472 actual inferences/completed rows and 736 exact paired rows. All 13 API ZIPs/74 members and every raw case/final summary are independently clear. This does not validate the known missing action-basis bridge. All four long cases (eight repeats) remain on the first of three route lanes, final active index 0, with maximum virtual lateral deviations about 39–41 m. The [integration record](STAGE7_INTEGRATION_VERIFICATION.md) preserves exact per-case values and the archive ledger. PR #27 merged as `bdcf91e4d3a98399503a0ba215b66920b0436c08` from final documentation HEAD `46a77106e1bdceaa11e9001c32100250d1a82306` after four current checks, completed Codex review with no findings/no open threads and a clear fresh three-document review. The native source `e84369c9f7f461a59c8d506b8b9efb2312297c03` passed 17 checks separately. At that historical checkpoint the corrected adapter was **TDD in progress, not complete**, with no corrected native gate executed. These historical geometry-guide drafts remain a separate documentation follow-up after that merge.


Current follow-up: PR #29 merged as `a5ef72ed3f492857eadd4b1198dbba381312aa80`. The [world-frame guide](STAGE7_MDV3_WORLD_FRAME.md) records independently accepted official source run **43005087003, 4/4 corrected repeatability**, eight fresh processes, 96 actual inferences/completed rows and 48 exact pairs. Separate automatic main **43006858419** completed 5/5 and is independently accepted at 4/4 after clear archive/raw/all-pairs evidence review. Combined corrected source/main data contain 16 UUIDs/nonces and 192 actual steps, 96 within-cohort paired rows and 288 all-pairs checks reusing those same steps with zero new inference. This source result does not rewrite historical paint/geometry values or legacy labels, prove tracking quality/full-S traversal or optical/renderer equivalence, or change the original 0/4 gate.
