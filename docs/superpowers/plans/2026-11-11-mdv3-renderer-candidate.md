# Official MD-V3 renderer-candidate strict gate plan

> Required workflow: executing-plans, test-driven-development and fresh
> requesting-code-review. Delegate the isolated implementation and completed
> evidence documentation independently. No new worktree or environment publication.

## Decision and limits

Two independent opaque-order CI cohorts, 42968294569 and 42969968780, each
verified 32 native processes. Original/combined unsorted conditions matched
every source/warp/I420 field 40/40, 4/4 cases. Sorted controls still failed.
Actual original-renderer traces showed 53 pass-order differences despite
matching scoped unordered primary CPU draw inputs. These results establish a
repeatable ordering-policy control boundary, not a unique GPU microcause.

Eight local terminal-depth v2 processes independently verified unchanged
2048x1024 DEPTH32F atlas bytes across linear-only/combined guard and sorted/
unsorted conditions in seed20261109/left-right. Every depth SHA was
`e2fad785dc9037146323996699cb8c2a23e517bb99acce5557ee5957fe234881`,
with 5347 nonclear texels, zero GL errors, exact state restoration and no later
frame-count advance. In the unsorted comparisons, guard on/off also retained
exact primary image bytes. This supports shadow-depth preservation in this
one case; it is not universal shadow/photometric equivalence. Terminal ON
readback overhead, cache/order history and limited scene coverage remain.

Proceed only with an explicitly labeled **experimental candidate** model
diagnostic. Existing upstream/original defaults stay unchanged. The historical
original official MD-V3 gate remains **0/4 FAIL**. A candidate 4/4 is separately
reported and never silently relabeled original or adopted as a default.

## Goal and immutable contracts

Run the official MD-V3 weights in eight independent Panda/ORT processes:
2 seeds x2 S-curves x12 steps x2 repeats. Compare **all** source964x604 RGB,
warped512x256 RGB, actual uint8 I420(2,6,128,256) feed hashes, raw four-float
action values/bytes, all named recurrent-state receipts, capture-entry and
post-action virtual pose/time. One differing field/step means FAIL.

- Official weights bytes **768750198**, SHA256
  `35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199`;
  path `1365126a-e71e-4778-be00-8ab92dc82c09/12864/big_driving_supercombo.onnx`.
  Download only inside ephemeral CI. Never download official weights locally
  or upload them as evidence. Local generated/synthetic unit graphs are separate.
- Preserve md-v3 spec, action slice2062:2066, parent policy/session settings,
  recurrent-state continuity, original camera/lens/geometry/ego visibility,
  sequential Road-first captures, PSSM.update/Chase, original two task ticks,
  initial fraction.12, speed8, virtual dt.05 and existing kinematics.
- No convergence, warmup renders, tolerance, replay, pixel correction, extra
  PSSM updates, RGB retention observer, GPU queries/depth/HDR extraction, shader
  edit, controller override, state/action substitution, real vehicles or scores.
- Additional named-state/clock/capture audits are CPU work with disclosed
  overhead. Compare virtual time/pose exactly; validate finite consistent Panda
  clocks and two ticks without requiring equal wall times across processes.

## Minimal standalone architecture

Create new candidate module/tests/workflow/guide only; leave every existing
core module and existing workflow byte-identical. No supported-module monkeypatch.

The current public `run_target_lane_episode(policy,camera,lane,spec,route=None)`
owns reset, inference, kinematics and lane truth. Reuse it directly. Do not
reuse the static feedback/raw-clock trial: it hides visual ego from RGB, unlike
the original model campaign. Reuse exact `NativeWorldCamera` through a thin
delegating CPU audit that calls its capture exactly once and forwards its
source hashes, without changing pixels, input pairing or geometry visibility.

Construct the audited official policy as the old trial does. Enter existing
`opaque_bin_policy(1)` before provider creation, create unchanged
NativeMetaDriveProvider with the original scenario map configuration, call
`configure_sampler(engine,'feedback_both')` before model captures, select native
lanes identically and delegate the entire loop with lanes[0], route=None.
Close the provider on every exit and restore opaque bin type. Keep complete
typed sampler/guard/bin receipts and task registries before/after the episode.

Extend `AuditedOfficialOnnx` by calling its parent step exactly once, then
reading actual outputs/state for extra audit fields. Never repack I420 or run
inference again to audit. Record initial and every post-step named state:

| Name | Shape | Dtype |
| --- | --- | --- |
| state_img_q | [2,5,6,128,256] | uint8 |
| state_desire_q | [132,1,8] | float32 |
| state_feat_q | [128,1,16384] | float32 |

Each state receipt includes exact name/shape/dtype/nbytes/C-order SHA, alongside
the existing all-state aggregate digest. Preserve dtype, including uint8 image
history. Record raw action shape[4]/float32/nbytes16/SHA and all four actual
values, plus the unchanged parent-converted ModelAction. Named-state hashing
reads about10MB per step; report it as audit overhead, not free instrumentation.

## Validation and failures

- [x] TDD meaningful RED contracts before implementation: wrong model/spec,
  state name/shape/dtype, raw-action schema/hash, changed capture/pose/time,
  one-field/one-step mismatches, stale/missing/nonce-invalid outputs, reused
  identities, incorrect renderer/task/bin/guard receipts and malformed clocks.
- [x] Test parent inference/camera capture delegation once, no per-step reset,
  uint8 history preserved, and original ego visibility retained. Fake policies
  and tiny graphs are unit evidence only, never official model execution.
- [x] Native child retains complete raw JSON/logs, partial audited rows and
  errors before validation. Reload JSON wire data before strict checks; no
  tuple-pose bug. Fresh nonce/output/log protocol, original native statuses
  retained. Accept Xvfb cleanup5 only with a complete fresh validated receipt.
- [x] Reuse `compare_fresh_trials` for exact common fields, layer strict named
  state/action/capture/config validation and comparison. Require 12 complete
  captures/inferences, zero extra GPU extraction, original tasks, finite raw
  clocks, expected two ticks and exact virtual before/after pose/time.
- [x] Case/final summaries independently regenerated from raw data; enforce
  eight UUIDs/nonces and two distinct same-runner PIDs per case. Reject stale
  summaries, missing fields and any rank/real-vehicle claim.
- [x] Metadata is `CANDIDATE_BOTH_UNSORTED_OFFICIAL_MDV3`, never the existing
  UNMODIFIED_METADRIVE label. Original-gate/default-promotion/full-renderer-
  equivalence/unique-microcause flags remain false. Candidate exact4/4 has its
  own explicit result. A successful data-collection CI is not a passed gate.
- [x] CI pins MetaDrive0.4.3, Panda1.10.13, official assets bytes134074203/SHA
  `4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9`,
  and official model bytes/SHA. Four native jobs, two repeats sequentially per
  job, maxparallel2, independent aggregate. Preserve raw receipts/logs and
  failures, including hidden evidence only within output scope; no weights.
- [ ] Full local tests, fresh code/scientific review and current-HEAD CI/Codex
  review/no open threads. Check five artifact API SHA/size/safe paths and exact
  raw reaggregation before any model-success assertion or gated merge.

Checked items above mean implemented contracts and unit/workflow verification,
not completed native/official-model evidence. The four new files are isolated
from all existing source/workflows. Fresh review found and corrected a partial
metadata issue: a constructed real session with zero recorded parent steps
must not claim official model execution. Its regression was observed failing
before the narrow fix; exact comparison rules were unchanged. Final source SHA:
`5a9058102004e2f5eaa4c9dcab4c24d97a9d42702b7a9e7c248c4f576a30d22e`.

## Ownership and next gate

Implementation: `scripts/native_mdv3_renderer_candidate.py`,
`tests/test_native_mdv3_renderer_candidate.py`,
`.github/workflows/stage7-mdv3-renderer-candidate.yml`,
`docs/STAGE7_MDV3_RENDERER_CANDIDATE.md`. Root owns this plan and completed
opaque/depth/continuation documentation.

Do not push or invoke the official-model workflow before the completed depth
protocol and bounded semantic decision above are independently reviewed.
Never lower comparisons after a failure; investigate the first real boundary.
Only candidate exact4/4 permits separately documented expansion: additional
independent repeats, camera fraction/position, native entry/exit ramps, longer
S-curves/steps and recurrent accumulation. Source geometry, deterministic
execution, real-sensor optics and driving performance remain separate.
