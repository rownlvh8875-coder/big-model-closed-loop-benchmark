# First-divergence accepted-buffer diagnostic implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development task-by-task, with TDD and task review, then broad final review. Root owns Git, CI, acceptance and any integration. User authorization permits continued execution without repeated technical questions; no worktree or Cloud publication.

**Goal:** Collect source/canvas/feed/state evidence at a bounded first divergence while measuring observer intervention.

**Architecture:** New opt-in CPU-buffer observer/validator, unchanged native episode/model source, then gated CI canary and six fresh four-step control/retention children. No existing renderer, converter, action or workflow behavior changes.

**Tech Stack:** Python3.11/NumPy/OpenCV, existing MetaDrive0.4.3/Panda/Xvfb, public MD-V3 factory, stdlib typed-file/SHA/ZIP/subprocess validation and GitHub CLI read-only APIs.

**Spec:** `docs/superpowers/specs/2026-11-11-first-divergence-design.md`.

## Global constraints

- PR33 DRAFT/unmerged; source-a4 strictFAIL remains blocking. No old65-call retry or main run.
- Preserve all13 diagnostic/ModelSpec pins, public factory/adapter/episode/convergence/optical/image conversion source bytes and existing workflows. New files only except result documentation after acceptance.
- Canary1 native process,2 accepted pairs, convergence6/16/10, at most12 pair/24 sensor calls excluding startup; model/ORT calls0.
- Conditional model study A0,B0,C0,C1,B1,A1, six fresh children ×4 steps = maximum24 official MD-V3 calls, original/proxy/retention modes; seed20261109,S-left-right,8m/s,dt0.05,fraction0.12,full_s_route=False,convergence6/16/10.
- Ephemeral-CI-only weights/models/native runs. No local native/model/weight downloads. CPU unit tests use real pure functions and small specific renderer/policy doubles only.
- Retained payload256MiB/child; dataset1GiB; child480s; study2400s. Fail closed, no retry/extension; incomplete counts stay unknown or bounded.
- No extra capture/render/task/GPU reads, substituted pixels/frames, extra parent resets/steps, default promotion or original scientific PASS claim.

## Review focus

- Accepted last-attempt raw/pair/observation association through convergence; identity plus offline raw→warp→packed-feed SHA checks.
- Unobserved control stays unwrapped; scoped module factory restoration on errors; observer effects/timing/allocation remain explicit.
- Exact once-only model forwarding/reset, real runtime/IDs, typed immutable state copies and preserved exceptions/partial evidence.
- Safe member paths/ZIPs/PNG CRCs/NPY(no pickle), budgets and fail-closed tamper/missing/source mismatch behavior.
- Model phase cannot download/start weights before API/source-bound canary acceptance; only request/docs may change between phases.

### Task 1: Accepted-buffer observer, pure validation and camera-only canary

**Files:** create `bigbench/first_divergence.py`, `scripts/first_divergence_audit.py`, `tests/test_first_divergence.py`.

**Interfaces:** `capture_scope(arm,collector)` temporarily interposes only camera factory for proxy/retention, restores original in finally; `CaptureCollector` binds the existing raw callback to returned pair/accepted observation and retained payload. `validate_capture_dataset(root)` verifies file/member hashes, PNG/warp/I420 association and absence of model claims. `capture_canary(out)` executes the registered camera-only path on CI. CLI initially supports `capture-canary` and `validate-canary`. Lazy native/ORT imports; importing/testing the module launches nothing.

- [ ] Write failing behavioral tests for accepted-last-attempt association, stale/wrong pair rejection, changed/mutated raw buffers, byte-exact warp/packed derivation, missing/unsafe members, cap enforcement, no-extra-capture and exception restoration. Use independently derived fixture values; no source-string tests.
- [ ] Implement pure collector/I/O/source-pinning plus scoped camera interposition and no-model canary. Serialize only after capture/provider close. Source pin map covers frozen13 plus actual pure dependencies/public factory and new producer/test/workflow snapshots (new files registered once Task2 exists).
- [ ] Run targeted CPU tests and project `python -m unittest discover -s tests -v`; preserve RED/GREEN logs and a source-bound task report.
- [ ] Fresh task review (spec + quality) and fixes before Task2. No Git/CI/native operation by worker.

### Task 2: Four-step model controls, parent ledger and gated branch workflow

**Files:** create `bigbench/first_divergence_model.py`, `tests/test_first_divergence_model.py`, `.github/workflows/stage7-first-divergence.yml`, `.github/stage7-first-divergence-request.json`; extend the new CLI/core validators from Task1 only.

**Interfaces:** `run_trial(model,spec,arm,repeat,nonce,out)` uses public auto-FRD factory and frozen `run_native_episode`; `run_study(model,spec,out)` launches registered six-child schedule; `validate_study(root)` verifies IDs/counts/typed states/actual-feed identity and derives descriptive comparisons. `verify_accepted_canary(request,out)` gates API/run/source/archive/capture validity before weights. CLI adds `native-trial`, `model-study`, `validate-study`, `verify-accepted-canary`.

- [ ] Write failing behavior tests for exactly-once forwarded steps/resets, true pre/post state snapshots, feed-SHA mismatch rejection, missing outputs/partial failures, unique nonce/PID/source checks, budgets/schedule abort and no retry. Test the API/archive gate with controlled transport payloads, not real network/weights.
- [ ] Implement forwarding-only B and retention C policies; A stays unwrapped. Keep original report/binding fields untouched. Defer I420 reconstruction and all artifact writes until provider closure. Only retention C stores full accepted buffers and raw4/plan/named state arrays.
- [ ] Implement parent/child lifecycle and safe replay; enforce CI/temp-root official weight identity; keep graph-call counts unknown on untraced failures. Record separate observer timing and actual runtime flags.
- [ ] Add new branch-only push workflow/request initially `capture-canary`. Same provided-route bootstrap/assets SHA; `actions:read,contents:read` only. Model-study request must pass source/API-bound canary gate before download. Existing workflows/gates remain unchanged. Main/new doc-only changes do not trigger this study.
- [ ] Run targeted + project CPU suite, validate executable workflow/gate behavior with fixtures and prove changed-path trigger scope. Fresh task and broad source review before first push.

### Root execution and evidence acceptance

- [ ] First push: basic CI + one no-model native canary only; validate API ZIP/full raw association with fresh independent review. No model download/session/call.
- [ ] Only accepted canary: review concrete request-only mode/acceptance change, push once for24-call-ceiling study; no producer/runtime edit between phases.
- [ ] Verify all raw source/API/member/PNG/state/feed identities, process ledger and counts; derive first differences without changing verdicts or datasets. Independent evidence review.
- [ ] Commit result/continuation docs, observe applicable CI/Codex; retain PR33 strict failure and main0. No original/default promotion or Stage7 completion claim.

**Ruling:** root selects three arms and a four-step prefix to control instrumentation and limit new calls. This is a new diagnostic protocol; absence of a difference within four steps is inconclusive, never a repair of the failed12-step gate. Existing autonomous authorization covers reversible implementation/testing/CI, not a failed-gate merge or Cloud publication.
