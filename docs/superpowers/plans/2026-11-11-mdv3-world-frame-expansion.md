# Corrected MD-V3 world-frame expansion implementation plan

> **For agentic workers:** REQUIRED SUB-SKILLS: executing-plans and test-driven-development; fresh scientific/code/workflow review follows implementation. Root owns Git, execution, evidence acceptance and integration documentation. No implementation is authorized by this draft.

**Goal:** Validate the existing opt-in corrected-world action bridge across the same three bounded scenario groups previously studied under the legacy action binding.

**Architecture:** Add one standalone runner, its tests, workflow and guide. Reuse the frozen official world-frame policy factory, body-basis adapter, original capture/episode loop, renderer treatment and generic receipt helpers; write a new complete-only expansion protocol and validator for the actual groups and horizons. Existing producers, readers, adapter, model/spec, core and workflows remain byte-identical.

**Tech stack:** Python 3.11, NumPy-only receipt comparison, pinned CPU ONNX Runtime settings, MetaDrive 0.4.3/Panda3D 1.10.13 in separately authorized CI, GitHub Actions.

**Spec:** User Task 5 and the parent dispatch for this plan; `docs/superpowers/plans/2026-11-11-mdv3-world-frame.md`, `docs/STAGE7_MDV3_WORLD_FRAME.md` and `docs/superpowers/plans/2026-11-11-mdv3-candidate-expansion.md` supply the existing frame, source, capture and scenario contracts. This plan does not authorize reproducing legacy motion semantics.

## Historical preconditions and source-only evidence

- Historical source-only plan-review checkpoint: PR29 run43005087003 is independently accepted4/4 (8 processes/96 actual inferences, all5 API archives/raw exact) and PR29 merged as a5ef72ed3f492857eadd4b1198dbba381312aa80 from df0f8803f6611e384d3752350fbffe007d16e7bd. Automatic main43006858419 is still running and unaccepted; completed-results documentation has not merged. Only the source prerequisite is fulfilled.
- Before ANY triggering push, dispatch, native/model execution or publication of this new workflow, require independently accepted corrected source4/4 AND automatic main4/4, each with eight processes/96 steps and all five archive API SHA/size/safe-path checks plus exact raw case/final regeneration. This is TEN prerequisite archives across two separate cohorts. Thirteen archives belong to the legacy expansion or a future completed new expansion, not either four-case prerequisite.
- Require the completed corrected-world results documentation PR to merge after both acceptances. Query the actual PR/current HEAD; do not guess a future PR number or claim prerequisites from a partly completed run.
- Source-only TDD begins only after fresh review clears this prospective plan. Root controls the later feature branch, full checks/review, push and workflow trigger. No new native/GPU/model/CI/Git work is authorized during plan preparation.
- Legacy original0/4, legacy candidate/expansion passes, corrected source/main and this future expansion remain separate records. No pose/action relabeling, default promotion, renderer/optical equivalence, tracking-quality, full-S, long-run, ranking or real-car claim follows from exact repetition.

## Exact matrix and unchanged contracts

| Group | Actual native scenes | Fraction | Requested steps/process | Cases | Planned processes | Inference budget |
| --- | --- | --- | --- | --- | --- | --- |
| camera028 | s_curve_left_right / s_curve_right_left | .28 | 12 | 4 | 8 | 96 |
| native_ramps | in_ramp / out_ramp (actual r/R blocks) | .12 | 12 | 4 | 8 | 96 |
| longer160 | s_curve_left_right / s_curve_right_left | .12 | 160 | 4 | 8 | 1280 |

Seeds are exactly20261109/20261110; each case plans repeats0/1 in independent processes. Total: twelve cases,24 planned processes and1472 planned parent inferences. Full completion yields736 paired frame rows. These are budgets, not observed counts. A final truth failure can consume160 inferences while completing159 rows. Report actual parent inferences, completed rows and attempted/unattempted processes separately.

The longer group is one continuous160-step episode, eight virtual seconds/64m of ideal-motion travel, exceeding the declared128-entry feature/132-entry desire histories. It is a longer prefix, not full-S traversal or long-run proof. Do not split it into short resets, shrink requested steps after failure, extend failed runs, add other horizons or repeat a completed cohort automatically.

All cases preserve speed8m/s, virtual dt.05, the exact scenario map and lane selector, original NativeWorldCamera/ego visibility/Road-first sequential capture, source964x604, warp512x256 and actual uint8 I420[2,6,128,256]. The existing public episode owns reset, inference, kinematics and truth. Opaque1 precedes provider creation; feedback_both follows initialization. Preserve PSSM/Chase and two ticks. No convergence/warmup/replay/tolerance, raw-model/image/state rewriting or additional action transformation beyond the frozen body-basis bridge, extra capture/render/PSSM/tick/clock advance, GPU query/readback, RGB retention, optics/geometry/controller/model-ranking work.

## Ownership and interfaces

Create ONLY:
- `scripts/native_mdv3_world_frame_expansion.py`: actual case setup, new wire/control validation, child launcher/ledger, exact comparison and aggregation.
- `tests/test_native_mdv3_world_frame_expansion.py`: synthetic/private-factory contracts; no local official weights or native GL.
- `.github/workflows/stage7-mdv3-world-frame-expansion.yml`: twelve native jobs plus independent aggregation, feature-only triggers.
- `docs/STAGE7_MDV3_WORLD_FRAME_EXPANSION.md`: preregistered protocol, prerequisite status, failure/accounting rules and limits; no fabricated completed result.

Root owns this plan, prior guides and continuation/result documentation. Do not edit existing source/tests/spec/workflows or register this runner as a default.

Public new-runner interfaces:
- `campaign_spec(group, seed, scene, repeat=0) -> CampaignSpec`, closed table above; reject other combinations/repeats.
- `native_trial(*, model, spec, group, seed, scene, repeat, request_uuid) -> dict`.
- `validate_trial(d, group, seed, scene, repeat) -> None`, COMPLETE-ONLY; returns no partial-success classification.
- `compare_trials(a, b, group, seed, scene) -> dict`; complete receipts only.
- `launch_trial(*, model, spec, group, seed, scene, repeat, out, request_uuid=None, status_receipt=None) -> int`; preserve non0/5 native statuses.
- `run_case(*, root, model, spec, group, seed, scene) -> int`; two sequential planned children, stop current case after a failed/invalid child, no automatic retry. Other matrix cases continue with fail-fast false. Record unattempted repeat explicitly.
- `compare_case(root, group, seed, scene) -> dict`; `aggregate_cases(root) -> dict`; CLI native/run-case/case/aggregate.

Use protocol `stage7-mdv3-world-frame-expansion-v1`, evidence `CANDIDATE_BOTH_UNSORTED_WORLD_FRAME_OFFICIAL_MDV3_EXPANSION`, request object `world_frame_expansion_trial={group,seed,scenario,repeat,request_uuid}` and distinct `world_frame_expansion_gate_passed` fields. Do not substitute legacy/current four-case gate names or totals.

## Helper reuse and source bindings

- Call `scripts.native_mdv3_world_frame._new_policy` ONCE. It already returns WorldFramePolicyAdapter around the exact official audited inner policy; do NOT wrap again. Constructor adds no reset; the one public episode reset preserves parent reset count2 and adapter reset count1. Forward actual runtime/mock/session/state/trace flags unchanged.
- Preserve the existing seven `SOURCE_BINDINGS` checks before factory/ORT, plus model768750198 bytes/SHA35976b11... and specSHA689f4d80... exactly from the frozen constants. Add a new receipt/check for direct frozen dependencies: adapter SHA275f5359a975d9e152f61df74cd57803e1322e1f9618784f0993e780516ec092 and world runner SHAcd57c4d407e96459921ca61c78eb81ef55851cd4fafa92ca917bbc7f494a3e38. Do not change the existing seven-pin table.
- Safe generic reuse from legacy expansion: ExpansionCaptureAudit, `_lane_receipt`, `_geometry`, `_visited`, `_validate_action` and `_validate_capture`. `_validate_action` checks/returns parent FRD action, not the applied world action. Existing `_validate_geometry` may be used with the ACTUAL group/scene only for geometry fields; additionally enforce exact generated block IDs I/C/C or I/r or I/R for the real case.
- Reuse world-frame `_bridge_action(receipt, parent, index)` for every actual index, including159/160. It supports arbitrary sequence indices and preserves constant R=diag(1,-1,-1), parent FRD receipt and applied FLU/world-CCW action.
- Do NOT call either complete fixed12-step `validate_trial`, world `_controls`/`_geometry_check`, legacy identity validator, or any old native runner by forging group/scenario/fraction/steps/labels/parent actions. New controls validate actual configuration, renderer/task/bin/runtime/reset and body-basis metadata directly.
- Use unchanged public `run_target_lane_episode` once. Short groups use the selected first native lane with route None. Longer160 builds `forward_contiguous_chain` between the two admitted native bends, then NativeRouteProgress. Ambiguous/missing/disconnected successors fail; no arbitrary ramp branch, nearest-lane fallback or clamping.
- Record actual block directions, selected/native route IDs/types/lengths/radii and scalar circular vs2-vector straight directions, initial pose, final active index and frame-derived successful visited truth IDs. Active index can advance before truth fails and is not successful coverage proof. Ramps retain real r/R identity and selected circular branch; no S relabeling or merge-traversal claim.

## Native format, failure and comparison rules

Retain unconditional full `capture_audit_rows`, `inference_audit_rows`, `bridge_receipts`, parent trace count, original public-return provenance/status/error and any separate outer lifecycle error. Keep all completed public frame rows and dangling post-capture/post-inference audits; never zip/truncate them away or fabricate a completed truth row. Record actual attempted native status in the ledger. Persist raw JSON FIRST, reload for wire checks, then decide CLI status.

Every successful gate trial requires exactly the ACTUAL planned N completed rows, N captures, N parent traces/audits and N bridge receipts, official noninjected CPU/basic settings, exact initial zero states, parent reset2/adapter reset1, complete provider close/bin restoration, unchanged tasks/renderer, no outer error and public DIAGNOSTIC_EXECUTED. Validate each raw4 float32 action/bytes/schema, aggregate+all three named typed state receipts, source/warp/I420 hashes, bridge and entry/post-world pose/time. Recompute all kinematics from the APPLIED WORLD action with unchanged step_ideal; retain FRD parent action untouched. Validate finite/consistent contiguous two-tick clocks; do not compare wall times across processes. Allow null inside-turn offsets on straight connectors.

Native0/cleanup5 requires a fresh full nonce-matched validated receipt. Native2 remains2; any incomplete requested episode fails case/workflow/gate even if both prefixes match, all1472 planned inferences were consumed, or a legacy partial collector would accept it. Other statuses/config/setup/capture/hash/model/close errors stay failures. No `VALID_FAILED_DIAGNOSTIC` success path or partial-prefix common comparator. Preserve all raw/error/log/ledger material before returning failure; explicitly retain unattempted repeat/case information. Two distinct same-runner PIDs per completed case and24 distinct cohort UUIDs/nonces are required for a full cohort; no fabricated identities for unattempted processes.

Full comparisons call unchanged `compare_fresh_trials` on two NEW-protocol validated COMPLETE trials, then compare every additional named-state/action/capture/bridge/configuration/native-route/truth field exactly. Bridge audit and other wall times are finite receipts, excluded from pair equality. One differing field at any requested step fails that case. Preserve first divergence and first incomplete step separately. Case/final summaries regenerate exactly.

Aggregation always distinguishes1472 planned budget/24 planned processes from observed successfully committed parent-step/completed-row/attempt counts. A policy/session/output-validation failure may execute ORT before the frozen parent commits trace/audit, even when its retained prefix is well formed. Therefore len(trace) proves only successfully committed parent steps on that failure, not total inference calls. Report that known committed-step count separately and mark total executed inference count UNKNOWN whenever an uncommitted failed policy attempt may have run; never substitute committed steps or requested length for that total. Exact total inference counts may be established only where frozen control flow and receipts prove the phase (for example complete episodes, fully audited public truth failures, setup before any policy step, capture failure before policy invocation, or close after a completed episode). Ambiguous phase or malformed evidence also yields unknown plus a concrete error. A cohort containing unknown totals must report its known committed lower bound and unknown-case count, not an invented aggregate actual-inference total. Incomplete/missing pairs never become complete comparisons. The aggregate can preserve a diagnostic failure summary with per-group/per-case errors and observed counts, but exits nonzero on any incomplete or invalid attempted case. This accounting is not partial acceptance. Complete repeat mismatches may remain successful data collection with an explicitly false exact gate, as in the existing diagnostics.

## Review focus

1. Factory already applies the bridge: double wrapping must fail, with raw/state/FRD parent evidence unchanged.
2. Generic helper scope: no fixed12-step or S-only validation may be reached through substituted fields; all actual late159/160 rows must be checked.
3. Last-step truth failure:160 inferences/159 rows is incomplete, with dangling source/warp/I420/state/bridge retained and native2 unmodified.
4. Actual native geometry: scalar circular and vector connector directions, real ramps, explicit route ordering and nullable straight truth must survive; active index alone is not traversal.
5. Trigger/accounting integrity: missing prerequisites, hidden native failures/pipeline status, stale summaries or unattempted repeats cannot produce accepted full counts or a full gate.

## Task 1: Actual configuration and one unchanged episode

**Files:** Create the new runner and dedicated test only.
**Consumes:** frozen helper interfaces/source bindings above.
**Produces:** campaign_spec and native_trial with the new raw schema consumed by Task2.

- [ ] Write RED contracts `test_all_twelve_actual_configs` (24 repeats, summed1472 budget), rejected combinations, real ramp labels and longer160 horizon. Assert constructor adds no reset and factory result is not rewrapped.
- [ ] Write RED private-factory lifecycle tests using the actual public loop: one parent step/capture, original ego visibility, applied-world motion/unchanged parent FRD receipt, real native-route transitions, source checks before factory, task/close/bin finally behavior and no new RGB retention.
- [ ] Run `python -m unittest discover -s tests -p 'test_native_mdv3_world_frame_expansion.py' -v`; expected explicit missing-feature FAIL, not import/setup failures. Save RED evidence before production code.
- [ ] Implement minimal actual case setup and raw receipts. No full episode copy, old module monkeypatch, fake12 metadata, second adapter, additional inference or changed renderer/capture.
- [ ] Rerun targeted contracts; expected PASS. Freeze source/test only after Task2, before root fullsuite/fresh review. Root alone commits/stages.

## Task 2: Complete-only wire, launcher and independent regeneration

**Files:** Extend only the same new runner/test.
**Consumes:** actual Task1 schema; produces validate_trial/compare_trials/launch_trial/run_case/compare_case/aggregate_cases and native/run-case/case/aggregate CLI.

- [ ] Write RED nonzero-action full fixtures for all groups: validate applied-world recurrence and unchanged raw/FRD parent action, all named states and actual configuration. Mock fixed old validators to raise, proving they are not used.
- [ ] Write RED late159/160 mutations across raw/state/bridge/clock/capture hashes/pose/route, source pins, actual block IDs/directions, runtime/reset/tasks/bin/guard and claims. Check finite timing without pair wall-time equality.
- [ ] Write RED well-formed prefix policy/session/output failures that may execute without committing an audit: known committed steps remain counted, total actual inference count is UNKNOWN, and cohort totals cannot silently use the lower bound as an exact count.
- [ ] Write RED partial m+1 cases (including159+1), public vs outer error, missing dangling hashes/states/bridge, wrong native statuses, raw-first tuple serialization, stale/nonmatching nonce, PID/UUID reuse, and unattempted-repeat bookkeeping. Every incomplete is nonzero/gate false; neither expansion partial collector nor common comparator runs on it.
- [ ] Write RED complete12-case/global24-identity regeneration and failed-cohort accounting tests: actual inferred/completed counts separate, stale summaries/missing cases/invalid counts fail. Preserve diagnostic summary/error before aggregate nonzero exit.
- [ ] Run targeted tests to observe each new RED, implement minimal checks, then rerun expected PASS. Do not add any model-file/session bypass.
- [ ] Verify pure NumPy-only import/reaggregation with Panda/MetaDrive/ORT unavailable, using synthetic data explicitly labeled unit evidence. Run unchanged world-frame13, base candidate15, legacy expansion16 and common comparator7 contracts; expected all PASS. Root runs the full suite and fresh review after handoff, not concurrently with any native work.

## Task 3: Scoped workflow, guide and publication hold

**Files:** Create only the new workflow/guide; source/tests remain frozen except review fixes with RED→GREEN.

- [ ] Write/verify workflow contracts: exact12 matrix entries, maxparallel2/fail-fast false, bounded120-minute cases, sequential repeats, feature `feat/**` pushes gated by only new runner/test/workflow paths, explicit dispatch, NO automatic main merge trigger. There is no automatic heavy replication cohort.
- [ ] Pin unchanged MetaDrive0.4.3/Panda1.10.13/assets/model/spec and parent CPU/basic ORT settings. Official weights only ephemeral CI; never local or artifacts. Unit jobs use private fakes, no official claims.
- [ ] Preserve12 scoped case artifacts and one independent aggregate artifact, including failure logs/ledgers/diagnostic summaries; missing artifacts/cohort is failure, not an invented complete13. Aggregate uses `if: always()`, strict `set -euo pipefail` before any pipeline and NumPy-only dependencies. Unexpected status/invalid/incomplete cases remain red.
- [ ] Guide records exact matrix/1472budget/736possible pairs, new protocol, proper body-basis/applied-world vs parent evidence, complete-only failures/accounting, actual route/truth coverage, measured CPU audit overhead and all unproven claims. State prerequisite status truthfully; no result fabrication or corrected expansion run yet.
- [ ] Parse YAML, verify exact matrix/triggers/pins/artifact scopes and embedded Python syntax; expected PASS. Verify frozen old fingerprints and all targeted/pure checks; root then runs fullsuite and whole-change scientific/code/workflow/doc review on exact source.
- [x] Execution/evidence gate fulfilled: root verified BOTH prerequisite4/4 cohorts/allTEN archives and PR #30 merge before triggering. PR #31 source48bf4309 passed17 current checks/Codex without findings/no open threads; run43012480495 and all13 new API archives/raw case/final regeneration are independently accepted. PR #31 merged as cb1e7bfe698fe3bc3df9540eeb7dc2557e671300. Preserve every negative result; no automatic retry or default promotion.

## Self-review and handoff

The plan covers only the three requested actual corrected groups. Helper/factory interfaces match current source; no core/API change is required. The main architecture risks are double wrapping and mistakenly reaching fixed validators, not missing lower-level episode APIs. All five review-focus boundaries have explicit Task1/2/3 tests. This prospective plan is saved under /tmp for fresh parent/scientific review. Implementation and all experiment triggers remain on hold until the relevant review/prerequisite gates clear.


## Historical source-only review checkpoint

The prospective plan received fresh independent scientific/code review CLEAR
at SHA256 `2131f4a099b94dae3d0d6397b1631f0ff77973673874446551ac26ff1112cce0`.
Source-only TDD is now authorized within the exact four-new-file ownership.
Root still owns Git/evidence. Automatic main43006858419 remains unaccepted;
all native/model/CI/push/dispatch triggers stay HOLD until both corrected4/4
cohorts/allTEN archives and completed-results documentation merge are verified.
No expanded native episode has executed and no completed budget is presumed.


## Historical prerequisite acceptance, publication still held

Source43005087003 and automatic-main43006858419 now each independently pass
corrected4/4. Root and fresh evidence review accepted allTEN prerequisite API
ZIP SHAs/bytes/safe paths and exact raw four-case/final regeneration. Sixteen
fresh UUIDs/nonces and192 actual inferences/completed rows are distinct from40
selected legacy identities; the read-only24pair/288row cross-cohort comparison
is exact without relabeling repeats or adding inference. Source-only expansion
TDD is underway. Completed-results documentation has not merged yet, and the
expansion's full tests/fresh source/workflow review remain required before
ANY triggering push/dispatch/native/model work. The planned1472 budget has
not been executed; no corrected expansion result is claimed.


## Final local implementation and fulfilled execution prerequisites

PR #30 merged as `5e42eff117218725e5e211ac63a98eb761789be6` after exact
source `f1327940faac9f3c1e6c5b09b33eca8c71416a8e` passed4 checks,
current-HEAD Codex without findings/no open threads and fresh9doc review;
main unit43010693730 passed. Both prerequisite cohorts/allTEN archives and
completed-results docs merge are now fulfilled.

Four new files are implemented; every existing source/spec/test/workflow and
all9 dependency hashes remain unchanged. Meaningful RED evidence preceded
implementation and review fixes: impossible surplus audit/bridge/capture/row
counts now yield UNKNOWN plus errors while retaining valid committed lower
bounds, and independent aggregation runs despite download/test failure once
its environment is ready. Missing-case pure shell evidence writes summary/log
and exits2. No failed status is masked and no raw record is truncated.
Final19 dedicated tests and361 full local tests pass without skips (43.098s,
`/tmp/stage7-world-frame-expansion-full-2.log`). Pure NumPy synthetic full and
failed aggregates work with Panda/MetaDrive/ORT imports prohibited. Fresh
independent code and workflow/guide reviews are clear. Whole-change exact-source
review remains before the first triggering push, followed by current-HEAD CI/
Codex/no threads and all13 actual archive/raw acceptance checks. No corrected
expansion native/model episode has run;1472 remains only the planned budget.


## Completed execution and evidence acceptance

The preceding source-only/pending paragraphs are dated protocol-development
checkpoints. The implementation and all execution prerequisites are now
fulfilled. PR #31 merged as `cb1e7bfe698fe3bc3df9540eeb7dc2557e671300` from
exact source `48bf4309cabe9d2e6e8b2fef952b9fb6f945b28a` after17 checks,
completed Codex without findings/no open threads and fresh final evidence
review. Run43012480495 passes12/12 corrected-world repeatability, each group4/4:
24 fresh UUIDs/nonces,1472 actual ORT calls/committed traces/completed rows,
736 exact paired rows and zero unknown cases. All13 API ZIP SHA256s/bytes/safe
paths,74 members and every raw case/final aggregate are independently clear.
The [result guide](../../STAGE7_MDV3_WORLD_FRAME_EXPANSION.md) records the full
ledger, timing scopes and actual truth coverage. Main unit43027151371 passed;
there is no automatic heavy main replication.

The longer prefix is not full-S or sustained tracking: all eight processes
visit2/3 route lanes and max lateral deviations are5.95397990659991–
7.634517723985033m. The correct bridge and exact repetition do not validate
model quality, paint/physical optics or renderer equivalence/default adoption.
Generic live action consumers, source-only RGB/I420 differences and the
preserved failed paint V2 launches remain separate integration limits. The
separate local V3 paint schedule is complete (16 native processes/128 RGB
reads), root replay exact and fresh full independent evidence review CLEAR/
root-accepted. Original
scene gates pass2/4/candidate1/4; focused-control failure and sparse ramps
prevent whole-cohort geometry confirmation. No model-scoring, default-promotion
or new-run gate is marked complete here.
