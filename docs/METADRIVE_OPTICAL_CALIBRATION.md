# MetaDrive virtual camera optical integration — Phase 1

**Status (2026-11-09): IDEAL PINHOLE GEOMETRY TESTS PASS; actual MetaDrive 0.4.3 offscreen RGB rendering and pose-dependent model-canvas frames PASS on GitHub Actions. Real comma optics and driving performance NOT validated.**

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

These commands ran **in GitHub Actions using MetaDrive 0.4.3, Xvfb/software OpenGL, and the official 134,074,203-byte release assets**. The native simulator is not installed in the current sandbox:

```bash
python -m pip install '.[inference]' 'metadrive-simulator==0.4.3'
xvfb-run -a python -m scripts.metadrive_optical_check --out output/metadrive-optics --steps 2
```

For an existing, HASH-PINNED stateful large model (requires a separate local model cache, never committed):

```bash
xvfb-run -a python -m scripts.metadrive_optical_check \
  --model /path/to/md-v3.onnx --spec model_specs/md-v3.json \
  --steps 3 --out output/metadrive-mdv3-probe
```

To run without downloading a large model, GitHub Actions provides the separate workflow `Real MetaDrive offscreen camera optical probe (NO real vehicle)` (manual or scoped push). Official rendering assets were pre-fetched from the tagged release because MetaDrive's automatic download returned HTTP 504 on an earlier run.

## Native MetaDrive evidence (PASS, with explicit limitations)

- [GitHub Actions run 42569322601](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42569322601): completed successfully with native MetaDrive 0.4.3, Xvfb and software OpenGL.
- Official asset package: MetaDrive-0.4.3/assets.zip; 134,074,203 bytes; SHA256 **4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9**.
- Native artifact: **metadrive-optical-probe** with four distinct 512×256 PNG images and the optical_report.json audit. Both road and wide images change after the virtual camera moves.
- Narrow measured source: fx=1323.9998636, fy=1323.9999425 (target 1324 px). Wide measured source: fx=283.5000334, fy=283.5000503 (target 283.5 px).
- Narrow warp source coverage **0.99609375 (99.609375%)**; wide source coverage **1.0 (100%)**.
- These values confirm reference **pinhole intrinsics, digital cropping and actual frame changes**, NOT real comma lens fidelity or independent physical-world landmark pixel residuals.
- **PASS:** [GitHub Actions run 42569804426](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42569804426), commit 2e2ae997, verifies native MetaDrive source RGB → I420/YUV6 **(2,6,128,256), uint8** ONNX camera input. Road/wide packed tensors are different, and the final packed input changes after the virtual camera pose changes. **This does not confirm actual ONNX inferencing using MetaDrive imagery.**

## Remaining optical validation gates — NOT PASSED

- **PASSED (synthetic-only native rendering):** MetaDrive binary initialization, offscreen native RGB source capture and model-canvas warp, including a detectable image change when the virtual camera pose changes. This is not a claim of calibrated real camera optics.
- Coordinate system frame/orientation verified with real MetaDrive 3D landmarks and projection residuals, not only synthetic pinhole pixels. Positive yaw/left-right correctness and sensor height require validation.
- Camera **extrinsics** (physical translation, roll, pitch, yaw), **lens distortion** (notably wide/fisheye), rolling shutter, exposure, tonemapping, colorimetry and temporal camera synchronization.
- Equivalence to openpilot's production NV12 warp interpolation, color conversion, camera transforms and model preprocessing.
- MetaDrive world ground-truth road geometry linked to the model camera's visual world and evaluation lane boundaries. **Until then, this script cannot emit any lane-intrusion score or model driving ranking.**
- Fully audited repeated ONNX runs and model-to-model statistics using validated virtual cameras and identical conditions.

## Evidence distinctions

- `CAMERA_PROVIDER_TEST_DOUBLE_NOT_METADRIVE`: artificial RGB frames for adapter unit tests; not MetaDrive images.
- `METADRIVE_REAL_RENDER_PINHOLE_INTRINSICS_ONLY`: MetaDrive RGB rendered and source pinhole intrinsics checked; not equivalent to comma sensor.
- `METADRIVE_REAL_RENDER_VIRTUAL_PINHOLE_UNCALIBRATED`: real MetaDrive + ONNX inferencing from changing virtual positions; not a driving-performance score.

These labels must **never** be treated as real road safety, actual camera optical verification, or an approval to conduct physical-vehicle tests.
