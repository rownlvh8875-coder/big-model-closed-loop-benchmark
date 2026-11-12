# Task 1 independent source review

Reviewed full HEAD `9bb9ebbbf2ca67da0e12705b9ec20ac843ab8c8c` against BASE `edbaa90d291f32d77e15ec77f091e5bcf3eef483`. Read the brief/addendum first, binding design, actor report/machine claims, and complete supplied diff. This is the Task1 spec/quality and sole pre-native source gate, not native evidence acceptance.

**Spec ❌. Task quality: Needs fixes. Not ready for the sole native canary.** One Important blocker must be repaired before source70 freezes at canary; no Critical issue found. The production runner's reviewed admission/capture/validation architecture otherwise matches the contract. Native feasibility remains ⚠ unverified.

## Important

**I1 — CI CPU tests depend on the mutable request being canary; required ABBA activation fails before its native phase.** `tests/test_engine_clock_native.py:731`, `tests/test_engine_clock_native.py:412`, `tests/test_engine_clock_native.py:554`, `tests/test_engine_clock_native.py:943`; workflow `.github/workflows/stage7-engine-clock-boundaries.yml:66` (CPU tests step).

The registered-phase test copies the live request into its fake Git response, executes the workflow step, and unconditionally expects `b'mode=canary\n'`. With the required valid ABBA request this becomes `b'mode=abba\n'` and fails. Its negative request is also fixed to canary. The lifecycle test at line412 reads the real request in run_phase while its `_context` stub returns canary: ABBA triggers `registered phase changed during admission`, and `_case` is never called. The subreaper test at line554 similarly fails at phase mismatch rather than reaching its asserted subreaper failure. The failure-ledger regression at line943 hardcodes the canary output while loading the real request, so ABBA fails `_output` before reaching its intended injected gates. The test at line421 can pass as a generic failure for the wrong reason when ABBA is active.

Concrete provider-free reproduction: ran only `LifecycleTests.test_phase_stops_after_first_failed_case_and_retains_failure_ledger`, overlaying `Path.read_bytes` for exactly `m.REPO/m.REQUEST` with a syntactically valid ABBA acceptance request in memory. All other file reads stayed real, no file/request changed, and existing native boundaries remained mocked. Result: **FAIL**, 1 test in0.005s, `tests/test_engine_clock_native.py:418`, `AssertionError: 0 != 1` for launch.call_count. This confirms the mutable-request dependency independently of actor rationale.

Impact: workflow CPU tests run before `scripts.engine_clock_native run`. Canary may run successfully, but its metadata-only ABBA child cannot pass these tests. Repairing tests after canary would change frozen source70 and invalidate the required direct-parent accepted activation. Thus this blocks the canary source gate now.

Fix scope: isolate scenario-specific phase tests from the mutable repository request, and make the actual registered-phase integration check correct for both valid modes. Add provider-free verification of the workflow test command under both initial canary and valid ABBA request bytes without any native/API execution. Preserve source70/admission restrictions; do not skip CPU tests in ABBA or weaken the request gate.

## Strengths

- Separate source70 and request binding, exact current Actions/workflow/head/attempt/status, live Git blobs/tracked cleanliness, runtime pins/absent installed and imported ORT, and unique workflow run checks precede native construction. Child repeats its own gates and checks actual Python main-thread ownership.
- Frozen one-use FIFO FD transport is retained. Exact command/kwargs substitution, no `-a`, single launch, cleared model acceptance, nonexistent dummy model, live ancestor/parent/group/nonce/schedule bindings, deadline deduction, bounded drain/cleanup and conservative missing-ledger provider bounds are explicit. Focused frozen `_launch_trial` inspection supports adapter compatibility.
- Common Texture observers remain ON for both clock arms; composition encloses Texture/RAM/hash work in the clock windows. Six fixed captures, original method counts, trace max_pairs6/thread/event links, marker hashes and accepted raw/canvas/I420 reconstruction are checked. Signed count differences do not impose monotonicity, expected increments or cross-process epoch identity.
- Strict successful case/phase member schemas, limits and all six ABBA comparisons are covered with genuine frozen collector/PNG/CPU transform fixtures. Failure traces, constructor uncertainty, close-unconfirmed raw/canvas preservation and actual persisted-prefix metadata are retained without false successful closure or I420 on close failure.
- Acceptance authenticates successful own canary run/artifact/original ZIP, direct single parent, changed-path whitelist, source70 bytes and full runtime identity before ABBA. Registered workflow has exact scope, pins, common bootstrap/assets route and real newline output. Root receipt independently reports current Git-bound phase output hex `6d6f64653d63616e6172790a`.
- Derivative validation/launch duplication is a documented frozen-protocol tradeoff, not by itself a defect. Reused helpers have matching semantics; no relabeled old-schema validation or old-module-global rewriting was found. Dense formatting makes review harder but does not warrant an additional blocker.

## Critical / Minor

Critical: none identified. Minor: no separate actionable finding beyond I1.

## Verification and preservation

Read-only Git confirmed the full reviewed HEAD and no tracked changes. No Git mutations, worktrees, network/dependency/native/Panda/Xvfb/model/ORT actions or subagents were performed. Only this report is written. Complete diff adds the four Task1-owned files plus root-owned design addendum; no old producer/helper/workflow/request/history changes appear. Root's pre-native receipt reports preserved67/workflows43/source70 verification and19 verified log hashes; these are supporting root evidence, not independent native proof.

Actor reports focused82/13.021s and full644/78.215s with7 expected skips; no full suite was repeated. Those runs exercise the current canary request and do not cover I1. The one additional targeted test was justified by the uncovered ABBA-request dependency and failed as described. No native readiness was inferred from fake sensors or stdlib transport.

## Residual uncertainty and disposition

⚠ Actual Actions API/status availability, pinned dependency installation, provided system bootstrap, Xvfb collision behavior, installed Panda/MetaDrive method compatibility, cache population, real engine cleanup and native time/storage behavior remain unexecuted and unverified. The CPU suite and source inspection cannot establish these. This is expected at a source gate, but I1 is a deterministic preventable blocker, not native uncertainty.

After repair, require a scoped independent review of the request-independent tests and appropriate CPU verification before the one-shot canary. No retry/extension/old replay is authorized by this review. Canary acceptance and direct-child ABBA admission remain later gates; strict scientific FAIL, expanded-not-run, geometry/optics/full-S/Stage7 incomplete, main official calls0 and the separate baseline SMALL graph remain unchanged.
