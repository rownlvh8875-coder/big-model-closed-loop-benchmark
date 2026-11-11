# PSSM shadow sampler isolation implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test whether MetaDrive's depth comparison sampler conflicts with its manual-PCF GLSL sampler, without changing the original benchmark defaults.

**Architecture:** Add an opt-in sampler treatment and a terminal-only OpenGL binding probe to the existing raw pixel-clock trial. Compare four arms in independent processes: original and raw-linear filters, each with the terminal probe OFF/ON. The probe runs only during the moved-pose positive control after all ten primary frames; there are no later renders.

**Tech Stack:** Python 3.11, MetaDrive 0.4.3, Panda3D, ctypes/libGL, Xvfb, GitHub Actions.

**Spec:** `docs/STAGE7_CONTINUATION.md`; original user Stage 7 instructions. OpenGL 4.6 core specification section 11.1.3.11 (pp. 401–402) requires consistent sampler type and texture comparison mode.

## Global constraints

- Preserve original Road-first sequential capture, PSSM.update and Chase tasks; two task ticks per pair.
- Preserve native 964×604 RGB, model 512×256 RGB, uint8 I420 (2,6,128,256).
- Official MetaDrive assets SHA256: `4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9`.
- No model weights, ONNX inference, model scoring, real vehicles, environment publication or changed default renderer semantics.
- Ten primary frames, warmup two, two independent repeats × four arms × two seeds × two scenes = 32 processes.
- GPU observations are instrumented evidence, not proof of the original MD-V3 repeatability gate.

## Review focus

- A residual GL program without the actual atlas binding must not establish sampler incompatibility.
- A sampler object overrides texture parameters; query the effective sampler, with a texture-parameter fallback if no sampler object is bound.
- OFF must install no callbacks; ON must restore callbacks and GL active texture even when queries fail.
- Missing/mislabeled sampler receipts, missing road/wide probes, reused process identities and stale summaries must fail validation.
- Xvfb cleanup status 5 requires a newly generated, fully validated receipt; real native failures must remain failures.

### Task 1: Opt-in treatment and terminal probe

**Files:** Create `scripts/native_shadow_sampler_probe.py`; modify `scripts/native_raw_pixel_clock.py`; test `tests/test_shadow_sampler_probe.py`.

**Interfaces:** `configure_sampler(engine, mode) -> dict`; `terminal_sampler_probe(engine, enabled) -> context manager yielding dict`. Optional `shadow_sampler_mode=None` and `terminal_shadow_probe=False` parameters on `native_pixel_clock` preserve its original path when absent.

- [ ] Write failing tests for default no-op, original/linear receipts, restoration on errors and GL binding classification (real atlas/depth format/sampler2D/effective compare mode/use_pssm).
- [ ] Run targeted tests and observe failure before implementation.
- [ ] Implement treatment; bind callbacks only to road/wide HDR scene outputs during the final positive capture. Record callback duration, driver, shader SHA, program/uniform/binding/filter/compare state and errors. Reject preexisting draw callbacks rather than overwrite them.
- [ ] Run tests, then local real native trials for all four arms. Preserve failures and actual observed results.
- [ ] Commit implementation and validation tests.

### Task 2: Independent comparison and native CI

**Files:** Create `scripts/compare_native_shadow_sampler.py`, `scripts/run_native_shadow_sampler_trial.py`, `.github/workflows/stage7-shadow-sampler.yml`, `tests/test_native_shadow_sampler.py`.

**Interfaces:** `validate_sampler_trial(d, seed, scene, arm)`, `compare_scene(root, seed, scene) -> dict`, `aggregate_scenes(root) -> dict`, launcher `run_trial(seed, scene, arm, out) -> int`. Reuse original Road-first schedule validation and exact SHA comparisons.

- [ ] Write failing tests for field mismatches, missing GPU evidence, duplicate identities, altered summaries and launcher failure/status-5 contracts.
- [ ] Run tests and observe failure before implementation.
- [ ] Implement strict validation, two repeats per arm, four scenes and 32-process independent aggregation. Report primary image equality and terminal observations separately; unique cause and original ONNX gate flags always false.
- [ ] Run targeted/full tests, syntax/YAML checks, fresh code review and native CI on the exact PR HEAD.
- [ ] Download all artifacts, verify ZIP SHA/size, regenerate summaries exactly and record native counts/rates/first differences before gated merge.
- [ ] Update continuation/findings with exact evidence and remaining gates; no causal or Stage 7 completion claim from static matching alone.
