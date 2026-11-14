# Renderer callback boundary implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans; inline, one fresh final review.

**Goal:** A bounded, fail-closed PSSM/Chase observer associated with camera calls, plus source-authenticated binding preparation.
**Architecture:** New modules compose with frozen clock observer. Pure Python profile hook observes original code/self and snapshots supplied state. Native classes are injected only by a future admitted caller.
**Tech Stack:** Python3.11, unittest, stdlib profile/AST/ZIP/hash. CPU-only environment.
**Spec:** ../specs/2026-11-14-renderer-task-boundaries.md

## Global Constraints

Preserve261 producer pins and original03 artifacts/requests. No native imports,
provider/model/ORT/GL/getter execution here, task/shader edits, new native allowance,
worktree, main merge or Cloud/registry publication.12steps/48snapshots/256KiB trace.
OFF callback events null; snapshots non-atomic and timing-intrusive. Never treat
synthetic PASS or static wheel/manifest equality as actual native evidence.

## Review Focus

1. Exceptions caught by a task loop must not become successful callback returns.
2. Profile hook and inherited/own step attributes restore on every exit; prior hooks preserved.
3. Same code with foreign self, recursion, wrong camera call or thread cannot forge association.
4. Snapshot failure, mutated/aliased data, nonfinite matrices and cap overruns fail closed.
5. Pinned source equality and structural fake tests cannot acquire native execution authority.

### Task 1: Bounded callback observer

**Files:** scripts/renderer_task_callbacks.py, tests/test_renderer_task_callbacks.py.
**Interfaces:** task_callback_scope(manager,enabled,trace,*,clock_trace,targets,snapshot,task_continue,max_pairs)
and validate_trace(trace); consumes frozen camera_clock_scope's active call ledger.

- [ ] Write behavior tests for normal ordered/reversed exact callback observation,
  OFFnull/no snapshots, explicit camera association, caught snapshot/callback failures,
  foreignself, returnNone/unwind, recursion/missing/duplicate callbacks, caps/thread/hook,
  exact argument/result forwarding and restoration. Run: missing module RED.
- [ ] Implement minimum fail-closed bounded observer. Run focused new+clock tests:
  expected PASS, original calls unchanged, no native modules loaded.
- [ ] Commit; record RED/GREEN and source-preservation receipt in ledger.

### Task 2: Structural adapter and pinned source audit

**Files:** scripts/renderer_task_binding.py, tests/test_renderer_task_binding.py;
docs/evidence/RENDERER_TASK_BOUNDARY_SOURCE_AUDIT.json and result document.
**Interfaces:** bind_engine(engine,*,pssm_class,chase_class,matrix_class,task_continue)
returns targets/snapshot/return contract for Task1; audit_sources(wheel,manifest,out).

- [ ] Add RED tests for engine ownership/class association, exact two-split finite
  snapshots, independent copies, named getter budgets, missing/unsafe/foreign inputs.
- [ ] Implement adapter and bounded source audit; expected focused PASS.
- [ ] Execute audit on retained wheel/accepted image manifest; expected four source
  files byte-identical and AST ranges recorded, downloaded-code execution0.
- [ ] Full unittest suite PASS with existing skips. One fresh read-only whole-change
  review including audit originals. One Critical/Important TDD fix pass only;
  Minor deferred, every declined-scope ruling and cost retained. Commit evidence.

### Task 3: Draft and exact-head closeout

**Interfaces:** Task1/2 code+audit feed own Draft on analysis/engine-clock-pixel-forensics-03.

- [ ] Push own source branch, Draft PR, verify exact-head push+PR CI jobs and no extra
  native workflow run/main change. General SMALL graph CI is separate from MD-V3.
- [ ] Record final authority in exact Draft body and local closeout receipt;
  keep reviewed source head separate from subsequent docs-only head.
- [ ] Final reports code/audit complete, actual native NOT_RUN and remaining integration
  gate explicitly, with all rulings/costs and deferred Minor findings.
