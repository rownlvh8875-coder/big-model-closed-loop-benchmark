# Accepted-buffer first-divergence diagnostic design

## Intent and authorization

PR33 remains DRAFT/unmerged because source-a4f1388's completed65-call regression
failed. Its first observed Wide/packed-input differences are atsteps2/4, but the
generic artifacts lack raw accepted buffers/full state. The user requests
continued sequential autonomous development. Root chooses the bounded design
below; no old cohort, renderer default, gate, converter or source pin changes.
This is evidence collection, never an alternate PASS for the failed gate.

## Approaches and selected scope

Reusing hashes cannot recover missing pixels. Extra render/GPU probes would
change the capture sequence. Select the existing `NativeWorldCamera`
`raw_rgb_observer` hook plus a diagnostic-only forwarding camera wrapper and
policy observer. They retain CPU buffers from existing captures/model calls.
Scoped camera-factory interposition is restored in `finally`; no frozen source
file changes. The original-call arm remains unwrapped. Instrumentation may
change CPU timing/allocation: explicit controls measure this limitation.

## Registered phases and budgets

- First: **one native no-model canary**, seed20261109/S-left-right, two accepted
  camera pairs, convergence6/pixel16/channel10. First pose is the original
  lane initial_fraction0.12 at8m/s; second is one frozen `step_ideal` straight
  dt0.05 advance. Maximum12 pair captures/24 sensor calls, excluding provider
  startup. No weights/ORT session/model call. Verify selected raw→canvas warp
  and derived I420 identity before permitting the model phase.
- Only after root + fresh independent canary/source acceptance: **six fresh
  Python/Xvfb child trials ×4 steps = maximum24 MD-V3 calls**. Fixed campaign:
  seed20261109,`s_curve_left_right`,8m/s,dt0.05,initial_fraction0.12,
  full_s_route=False, convergence6/pixel16/channel10; normal renderer defaults.
- Arms: A=`original` unchanged public binding + `run_native_episode`, no proxy
  or raw observer; B=`proxy` forwarding camera/policy wrappers without retained
  image/state payload; C=`retention` same wrappers with accepted-buffer/state
  retention. Schedule **A0,B0,C0,C1,B1,A1**, sequential fresh child processes.
- Only MD-V3 exact triplet/auto FRD factory; original model/adapter/state logic.
  Weights download and execution are **ephemeral CI only**. Child PID, process
  UUID, request nonce and parent launch/exit ledger are real, not dummy IDs.
- Stop on any invalid/incomplete child; retain failure/partial evidence and do
  not retry or extend the4-step prefix. An unreproduced difference is
  inconclusive, not original repeatability PASS. Main execution stays0.
- Observer-retained payload cap256MiB/child, total dataset cap1GiB. Compute
  state+image retention estimate before native creation. Child timeout480s,
  study wall cap2400s; no automatic retry. Killed/untraced calls stay unknown
  within configured upper bounds, never reported as0/completed.

## Capture and model association

The raw hook receives the already copied CPU RGB dictionaries and native
hashes once after each original capture's rectification. The wrapper calls
the original capture exactly once, holds its returned immutable `SchematicPair`,
and pairs it with that capture's raw-hook event. In retention mode read actual
Panda lens intrinsics after capture using CPU getters only. No perceive,
task step, renderFrame, depth/HDR or extra GPU read occurs in observer code.
Only the latest attempt survives until a model observation selects it; retain
accepted pairs, not every full-size convergence attempt.

Before model forwarding, require the observation's Road/Wide objects to be the
selected pair's actual objects. Copy pre-state and fixed traffic/action_t
arrays; call parent `.step` exactly once on the identical observation; retain
actual raw4/plan outputs, named next-state copies and actual
`last_input_image_sha256`. Do not reset/step the parent additionally. Record
observer callback/wrapper/state-copy/hash CPU-side wall durations separately
from inclusive capture and graph time. The raw callback is nested inside the
original capture; do not double-count it or call perf_counter wall time CPU
execution time. Timing-only proxy controls are not unobserved originals.

After the episode and provider closure, write raw964×604 and canvas512×256 RGB
PNGs, typed `.npy` state/action/plan arrays and I420 bytes. Recompute warps using
the stored actual intrinsics and require exact saved-canvas equality. Recompute
I420 from the actual observed canvases and require its SHA equal the actual
graph-feed identity before calling it actual-input-equivalent. Other feed
descriptors are source-reconstructed; do not call them directly intercepted
session feeds. Preserve original generic report fields, including null raw
hashes through convergence; link new observed evidence in separate sidecars.

Controls A/B retain generic reports/bindings/runtime, not fabricated raw/state
buffers. Exact total camera attempts in unobserved A are unknown (bounded by
the original loop); B/C can count wrapper captures. Initialization renders
are outside those bounds. All six trials are a new4-step protocol, not an
exact historical a4f1388 replay, physical camera validation or model ranking.

## CI and fail-closed acceptance

Use a **new branch-only diagnostic workflow** on `fix/public-onnx-action-frame`
watching only its own producer/tests/request paths. Existing workflows remain
byte-identical. New request JSON initially selects `capture-canary`; root later
changes only request/acceptance metadata to `model-study` after raw acceptance.
This uses push events because new workflow_dispatch files may not be registered
on default main. It never auto-runs on main or on result-doc-only updates.

Before model download, validate the accepted canary's actual GitHub run/source,
successful conclusion, artifact API size/SHA, safe extraction, complete raw
records and source manifest. All producer/test/workflow/runtime dependency
bytes must equal the accepted canary; request/docs may differ. Read-only
`contents:read,actions:read` permissions, no secrets in outputs. Install the
same provided-route bootstrap and verify official MetaDrive archive size/SHA.
No code, gate or network workaround may authorize a model run without canary.

Artifact/association validity can succeed while observed RGB/state comparisons
differ. Store descriptive mismatch/no-difference/incomplete outcomes; never
claim an original strict PASS. Missing first pixel/state/GPU information stays
unknown. PR33's failed gate, original0/4, corrected12/12, geometry/optics/full-S
and Stage7 incomplete status remain untouched. No Cloud publication, real car,
CAN/CD210, controller tuning, model ranking or default promotion.

## Preflight implementation rulings

Fresh design review is CLEAR, with `.superpowers/sdd/2026-11-11-first-divergence/design-review.md` as the detailed guardrail record.
The complete fixed source-path set also covers bootstrap/download helpers,
project dependency declarations and runtime dependency closure. Bind canary
repository/workflow/event/branch/head/run/attempt/artifact through APIs and
verify its manifest against the actual API-bound commit and current checkout.
Record and compare required NumPy/OpenCV/Panda/ORT distribution/Python/image
versions before weights; do not imply whole installed binaries/system equality.

The model request must be a **single new commit whose parent is the accepted
canary source**, changing only registered request/acceptance metadata/docs.
Parent request mode must be capture-canary, current mode model-study;
`GITHUB_RUN_ATTEMPT` must be1. This prevents request whitespace/repeated model
activation and workflow reruns from spending another24 calls. No dispatch
trigger is added. Source manifests compare file-byte maps, not their different
head-bearing receipts. Reject a producer/test/workflow dependency drift before
weights. An incomplete returned report is a failed child even with process0.
Each child wait uses min(480s,remaining2400s study deadline); terminate/reap its
whole process group on timeout and stop. Exact counts on interrupted/untraced
execution remain unknown/bounded. Payload preflight includes transient/latest
observer buffers and typed state copies, not just on-disk compressed bytes.
