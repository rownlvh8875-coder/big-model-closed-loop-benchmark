# Legacy-action official MD-V3 candidate: bounded expansion

This protocol expands the separately labeled `feedback_both` plus opaque
unsorted type 1 candidate. The original-renderer official MD-V3 gate remains
**0/4 FAIL**. The existing candidate's two independently revalidated 4/4
cohorts (source run42979680883 and automatic main run42981493726) are separate
starting evidence: 16 processes, 192 parent inferences and 96 paired rows.
They are not expansion results or evidence of default adoption, universal
renderer equivalence, optical fidelity, driving quality or real-car readiness.

**Known action-coordinate defect:** every cohort in this guide uses the legacy
unconverted model-action binding. Model FRD positive curvature is rightward;
the unchanged virtual FLU yaw integrator treats positive curvature as leftward.
The missing fixed body-basis conversion invalidates motion-frame correctness
and tracking claims. Exact legacy repeatability remains a separate finding.
The corrected world-action protocol has not run; no historical action, pose,
raw output, state or gate has been relabeled.

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
and fresh four-document review. The frozen source/workflow review and the completed expansion artifact audit
are now clear. The protocol above was fixed before execution; the following
section records the completed legacy-action cohort. Keep negative results, first
mismatch/incomplete boundaries, actual route coverage and CPU audit overhead.
Original/default promotion, full renderer equivalence, optics, model ranking
and vehicle/controller claims remain false regardless of determinism.


## Completed legacy-action cohort and coordinate limitation

Official run [42987993022](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42987993022)
executed source `e84369c9f7f461a59c8d506b8b9efb2312297c03`; expansion module
SHA256 is `d86b3be67c8ac3dee31f0bf9928014d3880c8c55a6cd829bb3c46c464d16b42c`.
All twelve native jobs plus independent aggregation completed successfully.
Root and a fresh independent reviewer verified all thirteen API archive sizes,
SHA256s and safe members, and independently reconstructed every raw case and
final summary exactly. There are 74 unique safe ZIP members; no weights are
included. Evidence remains under `output/stage7-remote-evidence/run-42987993022/`.

| Legacy-action group | Complete exact cases | Fresh processes | Actual inferences / completed rows | Paired exact rows |
| --- | --- | --- | --- | --- |
| camera028 | 4/4 | 8 | 96 / 96 | 48 |
| native_ramps | 4/4 | 8 | 96 / 96 | 48 |
| longer160 | 4/4 | 8 | 1280 / 1280 | 640 |
| Total | 12/12 | 24 | 1472 / 1472 | 736 |

All24 UUIDs/nonces are unique and disjoint from the16 earlier base-cohort
identities; each case has two distinct same-runner PIDs. All source/warp/I420,
four raw float32 outputs, parent converted actions, aggregate and named states,
capture-entry/post-action poses and virtual times match exactly. There is no
first mismatch or incomplete step. Each capture records two ticks. Actual ORT
is1.31.1 with CPUExecutionProvider, basic optimization and no injected session.
All1472 raw action hashes and4416 typed named-state receipts were independently
checked. These counts describe observed work, not the planned budget alone.

Every long trial ends at virtual time7.99999999999998, with160 distinct I420,
image-state and feature-state hashes. The zero-desire state stays constant as
expected; history length alone does not prove all recurrence semantics valid.
Despite the constructed three-lane chain, all four long cases visit only the
first lane and end with active index0. Maximum absolute lateral deviations
are39.00889893289053/41.15546916242339m for seed20261109 LR/RL and
39.013354504690554/41.143709047701606m for seed20261110. All24 lane-truth
summary metrics were regenerated exactly from actual frame rows. These are
unscored virtual geometry observations. Eight seconds and nominal64m of
integrated path distance do not establish full S traversal or correct tracking.

The pinned official source catalog commit
`e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42` makes the missing action bridge
explicit: camera.py73–88 declares forward/right/down and forward/left/up body
bases; modeld114–115 computes raw lateral action divided by speed squared.
Parser112–120 and fill_model_msg100 pass action through; controlsd217/225,
227 and262–265 preserve the model sign, while latcontrol_angle23 and the
torque boundary171/174/306 explicitly negate it for left-positive steering.
Only source text was inspected; no controller or vehicle plant was executed.
Both bases are right-handed. The fixed rotation is `diag(1,-1,-1)`, determinant
+1: world CCW curvature must be the negative of model right-positive curvature,
with unchanged longitudinal acceleration. Global world Y and image axes do not
flip. The numeric parent conversion is correct in its model convention; the
missing conversion is at its application to the virtual world.

Pure signed/zero/nonzero-heading proofs and pinned source hashes are retained
under `output/stage7-coordinate-contract-audit/`. They establish this boundary
defect, not its sole responsibility for all observed tracking errors or model
quality. A separately versioned opt-in adapter is planned to preserve the raw
four outputs and every image/state/audit byte while applying only the explicit
body-basis conversion before unchanged kinematics. No corrected native gate
has executed. Legacy repeatability results cannot become corrected-world PASS.

Measured CPU named-state audit time over1472 inferences is5.106884–23.107618ms,
sum10.242388566s. Extra warped-image hashing is0.358269–0.870031ms per capture,
sum0.653893655s. Whole capture wall time is3.714707410–9.774991554s,
sum7599.978521674s across independent processes; this includes rendering and
capture and is not pure instrumentation overhead or a real-time benchmark.
No CPU/GPU hardware-equivalence, real optics or performance claim follows.

The source commit passed17 checks and current-source Codex review without
findings or unresolved threads. A later documentation-only commit records
these results and limitations; it must pass its own applicable checks/review.
Its runnable code, workflow, specs and model binding must remain byte-identical
to this independently audited source. The path-filtered heavy workflow does
not rerun solely for result documentation. Neither the historical original
0/4 gate nor renderer-default non-adoption changes.

| Artifact ID | Bytes | ZIP SHA256 |
| --- | --- | --- |
| 13846305290 | 4058 | `2a886edbdd69cae67cfa24dbd2a6bac15027f40e220b2ab828c258a29472fd3d` |
| 13845617914 | 379456 | `b34facfed1ad8d800c657a1485ffbaf2c31c65c9d9636eda54d9ef4de4156aee` |
| 13844647784 | 381798 | `12803d69259b048b8ac2982a9519078f42fce36877c492fd1a8401550f50eb3e` |
| 13843468186 | 382109 | `93404c4fde9f83c600f8753b80a70aa0603244659c272722a4217bc80c5cfe3b` |
| 13842713664 | 379990 | `dd5927d899cc048894fc397fc87d8d1de61c280c07752490aecada9bfb56748d` |
| 13841735302 | 38027 | `ad857804f2a4ea80996d2a7d8092c2f09e6c3db547d642092c7dd5d8261e007c` |
| 13841661971 | 38085 | `4b79a2d60dd28f7c04bbd998bff2dd74ebd5679521ba8d1b38b17b6f842e9f5d` |
| 13840726305 | 38208 | `29c02cfae9e89b2b36904df618cd7be28efe82c57b2b7ac2a0b3f9c8b7178564` |
| 13840668097 | 37881 | `5bb26baea8ea7cdd7f709d1b6857dd8592c47a2c95272bce2be16769d9707936` |
| 13840653861 | 38069 | `ca51bc6cffbe61f3d097960b0b32ec21a11b6f84a1236f66d1183cd6ca98454e` |
| 13840617979 | 38195 | `d4a5e2c27feb2d3e300b7cd4fa1c0ac3c4c67cdd9e1764a5a3070e4e5c602801` |
| 13840382793 | 38200 | `4d35394157299564b1f7339b6751306be928186d134d35355ec101bb09e5a944` |
| 13840362369 | 38071 | `c79edc8c404672c1c3cd5082e2a4b706b426995bcdd718b244f91024c1fa9e52` |
