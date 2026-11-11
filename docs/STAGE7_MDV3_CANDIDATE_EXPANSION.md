# Experimental official MD-V3 candidate: bounded expansion

This protocol expands the separately labeled `feedback_both` plus opaque
unsorted type 1 candidate. The original-renderer official MD-V3 gate remains
**0/4 FAIL**. The existing candidate's two independently revalidated 4/4
cohorts (source run42979680883 and automatic main run42981493726) are separate
starting evidence: 16 processes, 192 parent inferences and 96 paired rows.
They are not expansion results or evidence of default adoption, universal
renderer equivalence, optical fidelity, driving quality or real-car readiness.

The reviewed plan fixes twelve cases, each with two fresh native/Panda and
CPU ORT processes, using seeds 20261109 and 20261110:

| Group | Actual native scenes | Initial fraction | Steps per process | Processes |
| --- | --- | --- | --- | --- |
| camera028 | left-right and right-left S | .28 | 12 | 8 |
| native_ramps | in_ramp / out_ramp, actual r/R blocks | .12 | 12 | 8 |
| longer160 | left-right and right-left S | .12 | 160 | 8 |

The planned inference budget is **1472** across 24 processes. Complete
episodes would supply 736 paired frame rows. Actual parent inferences and
completed frame rows are counted separately: the last inference can succeed
while its subsequent truth evaluation fails. No planned count is substituted
for observed work. Each group receives a separate verdict. Automatic base
replication and incomplete experiments cannot substitute for an expansion case.

The 160-step group is an eight-second, 64-metre ideal-motion longer prefix.
It exceeds the declared 128-entry feature and 132-entry desire histories, but
does not establish full S traversal or sustained long-run behavior. The
pre-execution plan changed the unexecuted 120-step draft to 160; a failure
never reduces the requested horizon or authorizes an automatic longer rerun.

Only four new files implement this protocol. Existing core, candidate source,
model spec and workflows remain unchanged. The new runner reuses the pinned
candidate policy factory, `CandidateAuditedOnnx`, CPU capture audit, sampler
and opaque context. One call to the public `run_target_lane_episode` owns the
actual reset, captures, inference, fixed-speed kinematics and native lane truth.
It uses original `NativeWorldCamera`, ego RGB visibility, Road-first sequential
capture, source 964×604, warp 512×256 and actual uint8 I420 [2,6,128,256].
Speed remains 8 m/s and virtual dt .05. There is no convergence, extra capture,
warmup, pixel tolerance, replay, image correction, I420 repacking, controller
override, action/state substitution, extra render/PSSM/tick/clock advance,
RGB retention, GPU query, or depth/HDR readback.

Native configuration uses the actual scenario map and existing native lane
selector. Receipts record generated block identities/directions, selected lane
identities/types/lengths/radii, and the actual initial pose. Ramp receipts keep
their actual r/R identity and selected ramp branch; they do not relabel an S
scene or imply complete merge/diverge traversal. Longer cases construct
`forward_contiguous_chain` between the two selected bends, then use unchanged
`NativeRouteProgress`. Ambiguous or disconnected links fail, with no nearest
lane fallback or progress clamping. Route IDs/lengths, final active index and
frame-derived successful truth visits are separate evidence. The active index
may advance before truth fails and cannot prove a successful visit. Circular
lane directions are scalar signs; straight connector directions are retained
as their actual two-component vector. A straight lane may have radius 0.

Root's separate geometry-only setup preflight preserved both attempts. The
first attempt, `output/expansion-geometry-smoke/`, failed with native status 2
when its ops serializer applied `float()` to the actual StraightLane direction
vector. This was a metadata failure, not an established route-builder failure.
After a CPU regression using the actual native lane classes, the corrected
v2 helper (SHA256
`be8b3d51eedc2635e5c2ed579d12d1e1c9e9161c65397f9c532fba1c87859c80`)
completed all four scene setups with status 0 under
`output/expansion-geometry-smoke-v2/`. In seed 20261109, each S chain contained
Circular 45.116761164 m, Straight approximately 60 m, then Circular
45.116761164 m; each native ramp selector returned two approximately
6.981317008 m, radius-40 circular lanes. Setup receipts checked bin restoration
and candidate guard configuration. These were one-seed setup observations,
not independent repeatability or an official model gate. No official weights,
inference or explicit camera capture participated; provider startup can render
internally, so zero explicit captures does not mean zero rendering.

`ExpansionCaptureAudit` calls its parent capture once and then records the
already computed source hash strings and returned warped pair hashes. It
retains no RGB arrays or frame objects. Recomputing the two warped hashes reads
**786432 extra CPU bytes per capture**, with a separately measured hash-audit
wall time. The additional named-state audit hashes 10358912 bytes per inference,
besides the unchanged parent aggregate state digest.
These costs are disclosed instrumentation, not free overhead. Every initial
and post-step named state retains its original name, dtype, shape, byte count
and SHA alongside the aggregate digest. All four raw float32 action values,
their bytes/schema and the unchanged converted ModelAction remain recorded.

The new wire protocol is `stage7-mdv3-candidate-expansion-v1`. Its evidence
label is `CANDIDATE_BOTH_UNSORTED_OFFICIAL_MDV3_EXPANSION`; it never claims an
unmodified renderer. Actual group, scenario, fraction and requested steps are
validated directly. No baseline metadata is forged to call the fixed 12-step
candidate validator. Each successful capture has finite raw Panda clocks,
exactly two contiguous ticks and the actual entry pose. Every completed
post-action pose/time must equal the unchanged kinematics exactly. Actual wall
times are retained and validated, not required to match between processes.
Straight connector truth may legitimately have a null inside-turn offset.

Raw JSON is written before reload and wire validation. All capture and parent
inference audit records are retained, including an extra final record when
truth fails after capture/inference. A valid failed diagnostic requires all of:

- The public episode itself returned `LaneTruthError: ` or
  `RouteContractError: ` after at least one completed row and before requested
  completion, with explicit return provenance and no outer lifecycle error.
- Exactly one extra successful capture, parent inference and complete audit,
  including source/warp/actual-I420/action/all-state hashes, entry pose and clocks.
- Valid normal model/runtime/reset/task/guard/bin/closure/restoration controls.
- Actual native exit **2**, preserved as 2 and classified
  `VALID_FAILED_DIAGNOSTIC`.

Such a receipt always fails its full expansion case with reason
`INCOMPLETE_REQUESTED_EPISODE` and first incomplete step `m+1`. Even two
identical partial prefixes, or 160 actual inferences with only 159 completed
rows, cannot pass the 160-step gate. No partial receipt reaches the common
complete-trial comparator. Hash-audit/capture/model/setup/close errors, zero-row
failures, malformed or missing evidence remain infrastructure failures.
Partial status 0/cleanup 5 and complete status 2 are invalid. Status 0 or Xvfb
cleanup 5 requires a fresh complete validated receipt for the launch nonce.

Case collection may succeed after preserving two valid failed diagnostics;
native exit 2 remains recorded, and the expansion gate remains false. Every
other native status is preserved as failure. There is no automatic retry.
Fresh output/log paths, nonce/UUID checks, two distinct same-runner PIDs per
case, sequential children and all 24 distinct cohort UUIDs/nonces are required.
Completed pairs use the unchanged common exact comparator plus every extra
named-state/action/capture/configuration/route/truth check. One difference at
any planned step fails. Case and final summaries independently regenerate
exactly, with actual counts summed from raw receipts.

The new workflow runs twelve case jobs with maximum parallelism two, a
120-minute bound per case, and a pure aggregation job. Thirteen scoped
artifacts preserve raw receipts, errors, logs, actual-status ledgers and the
summary; model files are excluded. MetaDrive 0.4.3, Panda3D 1.10.13 and official
assets are pinned: 134074203 bytes, SHA256
`4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9`.
The unchanged official model is 768750198 bytes, SHA256
`35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199`;
spec SHA256 is
`689f4d80082070b08ff35920e37d7070e811dfb42a279909751f79e900c735e2`.
Actual files are verified before ORT. Weights exist only in ephemeral CI
`$RUNNER_TEMP/models`; there is no public test-model bypass.

Push triggers require a `feat/**` branch and changes to the new module, test
or workflow. Automatic main merge pushes do not rerun this heavy experiment.
Explicit workflow dispatch remains available for a separately justified
replication. Before any triggering push or dispatch, require independent main
base-replication 4/4 review and merge of the completed candidate-results docs.
All twelve native checks and exact evidence review belong to the feature
source before merge. Current-HEAD checks/Codex review, all thirteen archive
API sizes/SHAs/safe paths and exact independent raw regeneration precede any
result claim. Data-collection CI success never means expansion gate PASS.

Pure reaggregation requires NumPy only, without model files or graphics:

```bash
python -m scripts.native_mdv3_candidate_expansion --mode aggregate \
  --root output/stage7-mdv3-candidate-expansion \
  --out output/stage7-mdv3-candidate-expansion/aggregate_summary.json
```

Unit tests use explicitly synthetic fixtures/private factories and the shared
public episode loop; installed native lane classes are exercised CPU-only.
They make no official execution claims. Full local suite:329 passed without
skips, including16 new contracts; those16 passed in a separate NumPy-only
environment too. The retained RED log records11 missing-implementation failures
before code was written. New workflow validation includes a shell regression:
a failed Python pipeline can be masked by tee without pipefail, so independent
aggregation explicitly enables `set -euo pipefail` and retains failures.

The main-base replication review and results-documentation prerequisite are
complete. PR #26 merged as `1077144170346e23279a91c832ce414534f377fe`
after exact-HEAD checks, completed Codex review/no findings/no open threads
and fresh four-document review. The expansion still requires its own frozen
source/workflow review, CI and artifact validation. This guide specifies the protocol;
it reports no completed expansion cohort. Keep negative results, first
mismatch/incomplete boundaries, actual route coverage and CPU audit overhead.
Original/default promotion, full renderer equivalence, optics, model ranking
and vehicle/controller claims remain false regardless of determinism.
