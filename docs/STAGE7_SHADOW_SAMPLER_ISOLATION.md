# PSSM sampler type versus effective OpenGL comparison state

This is a static native renderer experiment. It does not change benchmark
defaults, run ONNX, or establish the original moving MD-V3 repeatability gate.

## Source hypothesis

MetaDrive 0.4.3 `engine/core/pssm.py::create_pssm_buffer` sets both filters of
the depth-component PSSM atlas to `FTShadow`. Panda3D 1.10.13 maps that filter
to `GL_TEXTURE_COMPARE_MODE = GL_COMPARE_REF_TO_TEXTURE` (sampler objects or
texture parameters). MetaDrive's loaded `simplepbr.frag` instead declares
`uniform sampler2D PSSMShadowAtlas`, reads `.r` with `texture2D`, and performs
its own `step(ref_depth, depth_sample)` nine-tap PCF.

The [OpenGL core specification 4.6, §11.1.3.11, pp. 401–402](https://registry.khronos.org/OpenGL/specs/gl/glspec46.core.pdf)
states that a non-shadow sampler reading a depth texture with comparison mode
enabled has undefined lookup results. That establishes a source-level
compatibility concern, not the unique cause of the earlier pixel drift.
The loaded shader string SHA256 is pinned to
`8eef67eb4384d6a74136b8e99b4c9bf0711e51ee88db7a248cd164c7a69f9ceb`.

## Independent arms

| Arm | Atlas min/mag filter | Terminal GPU observer |
| --- | --- | --- |
| `original_off` | Original `FTShadow` / `FTShadow` | OFF |
| `original_probe` | Original `FTShadow` / `FTShadow` | ON |
| `raw_linear_off` | Experimental `FTLinear` / `FTLinear` | OFF |
| `raw_linear_probe` | Experimental `FTLinear` / `FTLinear` | ON |

The linear treatment preserves the backend's linear min/mag filtering while
disabling hardware depth comparison, consistent with the shader's manual-PCF
input type. It changes renderer semantics and remains opt-in. This experiment
does not establish intended upstream visual appearance or shadow accuracy.

Each seed (20261109/20261110) and S-curve (left-right/right-left), fraction
0.12, uses two fresh processes per arm: 32 processes total. All preserve the
original Road-first `perceive()` path, two task ticks per pair, PSSM.update,
Chase, fixed WORLD pose, ten full primary frames and two-frame secondary
warmup. Source RGB, warped RGB and actual uint8 I420 SHA sequences are compared
without tolerance; pose movement by +2 m must change both cameras' buffers.

## Terminal observer and its limits

All ten primary image pairs are captured before installing any observer.
Only the final moved-pose positive control is instrumented. No renders follow
it. OFF loads no libGL and installs no callback or observer node.

A first local pilot queried the GL program after each display region. Its
last program sometimes had no PSSM atlas uniform, so those observations were
inconclusive. The experiment therefore installs a temporary **zero-geometry
CallbackNode** inheriting the native scene's PBR shader state, restricted to
the RGB camera mask and drawn in a late fixed bin. Panda loads its render
state before calling its draw callback. Display-region wrappers identify the
road/wide camera on the same draw thread. All nodes/callbacks and the active
texture unit are restored even on failure; existing callbacks are rejected.

This is a **controlled inherited-state binding observation**, not a trace of
every original geometry draw. The probe records the active sampler uniform
type, its unit, actual bound texture, expected PSSM atlas native ID, depth
internal format, `use_pssm`, effective sampler-object comparison/filter state
(texture fallback when no sampler object exists), GL errors and driver.
Residual programs, different textures, disabled shadow uniforms or GL errors
cannot certify the binding. Two valid observations per camera are required.

Query CPU time is retained per observation and summed. The terminal diagnostic
wall time also includes positive-control rendering, libGL loading, observer
setup and teardown; it is not a pure GPU-query overhead measurement. Primary
pair clock/wall receipts and OFF/ON image comparisons remain separate.
Independent process variation prevents interpreting their difference as an
unbiased estimate of instrumentation overhead.

## Execution and evidence gates

```bash
python -m unittest discover -s tests -p '*shadow_sampler*.py' -v
python -m scripts.run_native_shadow_sampler_trial --seed 20261109 \
  --scene s_curve_left_right --arm original_off --out output/fresh-original.json
python -m scripts.compare_native_shadow_sampler --mode aggregate \
  --root output/verified-shadow-sampler --out output/recomputed-sampler.json
```

The Actions workflow verifies official asset size/SHA and launches each trial
in a fresh Xvfb/Python process. Xvfb status 5 is accepted only with a newly
generated, fully validated receipt. Reused same-runner PIDs, reused cohort
UUIDs, missing trials, mislabeled treatments, incompatible GPU observations
and changed uploaded summaries fail the evidence gate. A verified experiment
may contain image mismatches; job success is not renderer determinism.

Before merging, verify the exact PR HEAD checks/review, download every raw
artifact, verify archive size/SHA and safe member paths, and regenerate the
four case summaries and final aggregate exactly. Record actual rates and
first differences, including failed/superseded pilots. A static improvement
alone never licenses a default switch or an original ONNX 4/4 PASS claim.
