# Experimental renderer candidate: official MD-V3 strict repeatability

This is a separately labeled candidate gate for `feedback_both` plus opaque
unsorted type 1. The historical original official MD-V3 gate remains **0/4
PASS (FAIL)**. A candidate 4/4 is its own result and never replaces the original
record, adopts a default renderer, proves full rendering equivalence or permits
model ranking or real-vehicle claims.

Two independent 32-process opaque-order cohorts matched all source/warp/I420
fields 40/40 in both original-unsorted and combined-unsorted conditions, while
sorted controls still failed. The eight-process local terminal-depth v2 protocol
then found identical 2048×1024 DEPTH32F bytes across linear-only/combined and
sorted/unsorted conditions in seed 20261109 left-right: SHA256
`e2fad785dc9037146323996699cb8c2a23e517bb99acce5557ee5957fe234881`,
5347 nonclear texels, zero GL errors and exact state restoration. Unsorted
guard on/off also matched primary image bytes in that one case. That limited
terminal result supports a bounded candidate diagnostic, not universal shadow
or photometric equivalence. Readback/observer overhead, cache/history and scene
coverage remain limitations; the failed v1 ops attempt remains separate.

The new module delegates the existing public `run_target_lane_episode` loop.
It creates the original NativeMetaDriveProvider, chooses the same first native
curve lane and uses the exact NativeWorldCamera through a thin CPU audit that
calls capture once and forwards its source hashes. The original ego RGB
visibility is preserved. The static raw-clock experiment is not the model
episode runner, because that static path explicitly hides the visual ego.

The existing opaque policy context sets type 1 before provider creation,
preserves bin index/name/sort/active state and restores type 2 on exit/errors.
After provider initialization, `configure_sampler(engine, 'feedback_both')`
sets the already implemented linear atlas and bounded shadow-camera guard.
The guard adds only high-priority `use_pssm=False` and a white 1×1 RGBA8 atlas
placeholder to initially empty shadow-camera states; it preserves inherited
shaders. CPU receipts include complete typed bin/sampler/guard metadata and
task registries before/after the episode while the engine is alive.

All camera, lens, geometry, original Road-first sequential calls, PSSM.update,
Chase, two task ticks per pair, source 964×604, warped 512×256 and actual uint8
I420 [2,6,128,256] paths remain delegated unchanged. The episode retains speed
8 m/s, virtual dt .05, initial fraction .12, the first target lane and the
existing fixed-speed kinematics. There is no convergence, warmup capture,
tolerance, replay, image correction, RGB-retention observer, GPU query,
depth/HDR extraction, extra PSSM update or render, clock change, controller
override, action/state substitution or model-input repacking.

The candidate policy subclasses AuditedOfficialOnnx. It calls the parent reset
and step, with one actual inference per step and no per-step reset. The parent
hashes the actual ORT image feed and all recurrent states. Additional audit
records preserve each initial and post-step state separately:

| Name | Shape | Dtype | Bytes |
| --- | --- | --- | --- |
| state_img_q | [2,5,6,128,256] | uint8 | 1966080 |
| state_desire_q | [132,1,8] | float32 | 4224 |
| state_feat_q | [128,1,16384] | float32 | 8388608 |

Each receipt carries name/dtype/shape/nbytes/C-order SHA256 beside the parent
aggregate digest. Raw action evidence includes all four actual float32 values,
shape [4], 16 bytes and SHA256 from the original action slice 2062:2066, plus
the unchanged parent-converted ModelAction. JSON action values must round-trip
exactly through float32 and match their recorded bytes.

Capture audits record the entry virtual pose/time and before/after Panda clock
observations. Validation requires finite, consistent clocks, contiguous counts
and exactly two ticks; virtual before/after poses and times must agree exactly
with the unchanged kinematics. Wall times are validated and retained, not
required to match between processes. Named-state hashing reads about 10 MB per
step; extra audit time is reported as CPU overhead rather than free work.

The strict gate uses two seeds × two S-curves × twelve steps × two independent
Panda/CPU ORT processes: **8 UUIDs/nonces, 96 model steps**, with two distinct
same-runner PIDs per case. Twelve capture rows, twelve parent ONNX trace entries
and twelve policy audit rows are required. Initial state is the exact parent
zero reset. Every source/warp/I420 hash, all four action values/bytes, aggregate
and named recurrent receipts, capture-entry and post-action virtual pose/time
must match. A single field/step difference fails the candidate gate.

The existing exact comparator handles common fields; new validation adds every
candidate state/action/capture/config field. Missing/malformed evidence is
rejected. Full raw JSON is saved before strict wire validation, preserving
partial rows and errors and avoiding tuple-serialization mistakes. Fresh launch
nonce/output/log checks apply; exit 0 or Xvfb cleanup 5 is accepted only with a
complete validated receipt for that request. Every other native status remains
a failure. Failed/cancelled attempts and logs are retained, never retried or
counted as completed cohorts. Case and final summaries regenerate exactly.

Official model identity is **768750198 bytes**, SHA256
`35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199`.
The unchanged spec byte SHA256 is
`689f4d80082070b08ff35920e37d7070e811dfb42a279909751f79e900c735e2`.
Both are checked before constructing ORT; no public test-model bypass exists.
The parent CPUExecutionProvider/ORT_ENABLE_BASIC settings remain unchanged.
Unit fakes are explicitly unit evidence and do not execute official weights.

The candidate-only workflow pins MetaDrive 0.4.3, Panda3D 1.10.13 and official
assets bytes 134074203 / SHA256
`4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9`.
Official weights download only into ephemeral CI `$RUNNER_TEMP/models`, never
local workspace storage or evidence artifacts. Four native jobs use maximum
parallelism two and sequential repeats, followed by independent aggregation.
Five artifacts retain only scoped JSON/log/ledger evidence, including hidden
files and failures. Existing source and existing workflows are unchanged.

Pure reaggregation uses no model, Panda initialization or native capture:

```bash
python -m scripts.native_mdv3_renderer_candidate --mode aggregate \
  --root output/stage7-mdv3-renderer-candidate \
  --out output/stage7-mdv3-renderer-candidate/aggregate_summary.json
```

This guide defines the candidate protocol, not a completed model result.
Before execution/promotion claims, finish the bounded semantic review, exact
source/check/review gates and all five artifact API size/SHA/safe-path checks,
then require exact independent raw reaggregation. Data-collection CI success
does not mean candidate PASS. Only a separately reported candidate exact 4/4
permits a later documented expansion; original/default adoption, optics,
geometry fidelity, long-run behavior and driving performance remain separate.
