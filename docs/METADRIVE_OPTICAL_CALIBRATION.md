# MetaDrive virtual camera optical integration — Phase 1

**Status: IDEAL PINHOLE GEOMETRY UNIT TESTS PASS; native MetaDrive rendering is OPTIONAL and not yet confirmed locally.**

This work is a **simulator-only** experiment: no real vehicle testing, CAN, CD210, Carrot MPC or vehicle-specific dynamics.

## What was implemented

1. `bigbench/optical_calibration.py`: Reference camera intrinsics and independent road/wide homographies, strict source-shape and measured-lens checks, source coverage audit, and 512×256 rectified RGB outputs.
2. `bigbench/metadrive_camera.py`: Optional real MetaDrive RGB sensor classes (CPU RAM-backed) and camera-only virtual pose capture using `BaseCamera.perceive(new_parent_node=..., position=..., hpr=...)` with **no physics-based ego steering**. OnnxBigModelPolicy can consume the resulting paired model canvases.
3. `scripts/metadrive_optical_check.py`: Bounded, offscreen MetaDrive optical-check workflow with either two pose-shifted views or (when a model file and manifest are supplied) a short ONNX + virtual-pose feedback test. Outputs `optical_report.json` and rendered PNG images. **No model ranking or lane-intrusion metrics.**
4. `tests/test_optical_calibration.py`: deterministic pinhole landmark reprojection, source crop coverage, focal/centering mismatch rejection and test-double feedback proof.
5. `.github/workflows/metadrive-optical.yml`: manually triggered headless MetaDrive smoke, separate from mandatory CI. Run status must be checked before claiming native renderer validation.

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

The native simulator is not installed in the current sandbox, so these commands have **not been run locally with actual MetaDrive rendering**:

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

To run without downloading a large model, GitHub Actions provides the separate **manual** workflow `Real MetaDrive offscreen camera optical probe (NO real vehicle)`.

## Remaining optical validation gates — NOT PASSED

- Actual MetaDrive binary installation and offscreen native RGB capture in a real execution environment (separate manual CI).
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
