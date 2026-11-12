# Engine-clock boundary observer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline; one final fresh whole-branch/contract review.

**Goal:** Deliver a reusable CPU-tested boundary observer and inactive future camera protocol design.
**Architecture:** Wrap existing perceive/taskMgr.step/RAM methods without extra calls, reading the TaskManager-owned clock at four boundaries only when enabled. Keep current source65 and all consumed admission paths unchanged.
**Tech Stack:** Python3.11 standard library; synthetic CPU fixtures only, no new dependencies.
**Spec:** docs/superpowers/specs/2026-11-12-engine-clock-boundaries-design.md

## Global Constraints

Current native/provider/GPU/ORT/official calls0; no active scientific workflow/request, no local native/Panda engine/Xvfb/weights, no old retries/re-extraction/Cloudsettings/publication/mainmerge/worktrees/historycleanup. Preserve producer65/protected13/baseline43/all43workflows/requests+acceptance. Observer getters do not advance clock/tasks/render. Future budgets/registration are design only; no admitted native result. Baseline generated SMALL graph separate.

## Review Focus

- Both inherited and instance method attributes must restore exactly, including partial setup and restoration failure; primary errors remain primary.
- OFF must not access globalClock or either clock getter; same original step/RAM/perceive calls and object identity remain.
- Nested/orphan/duplicate/wrong-thread/budget or caught getter failures must never masquerade as complete traces or issue extra original side effects.
- Count/time snapshots are non-atomic typed observations; equal/negative/nonmonotonic valid values must not imply GPU or task callback phase.
- Future marker-wrapper composition and producer70/admission/budget design must remain explicit and inactive; tests are synthetic, not installed-CI/native proof.

### Task 1: Observer and meaningful CPU tests

Files:create scripts/engine_clock_boundaries.py,tests/test_engine_clock_boundaries.py. Interfaces camera_clock_scope(provider,enabled,trace,*,max_pairs=6),validate_clock_trace(trace) exactly as spec.

- [ ] Write tests for ON/OFF exact method/getter counts, no clock owner access OFF, four-boundary call order, forwarding/object identity, own/inherited restoration, setup/body/getter/restore failures, primary/partial prefixes, caught errors, nesting/orphans/duplicates/wrong camera/thread/budget, clock-owner change, special signed/finite nonmonotonic values, malformed/forged/incomplete trace rejection and compatibility with the unchanged Texture marker_scope.
- [ ] Run targeted tests first; expected missing-module assertions RED. Implement minimal observer then run covering tests until GREEN. Do not claim each adversarial fixture independently observed RED unless it did.
- [ ] Run full CPU suite once after all integration tests pass: exact replay python -m unittest discover -s tests -v; expected all pass with optional dependency skips, real count logged. Commit code/tests, append completion evidence.

### Task 2: Concrete inactive protocol and source/verification report

Consumes tested observer schema/counters. Creates docs/evidence/STAGE7_ENGINE_CLOCK_PROTOCOL_DESIGN.json, docs/evidence/STAGE7_ENGINE_CLOCK_OBSERVER_AUDIT.json, docs/STAGE7_ENGINE_CLOCK_OBSERVER.md and updates continuation.

- [ ] Populate inactive status, current0nativecalls, future48/96clock-per-ONcase and proposed total144/288clock plus120/240Texture readings/getters,70source closure, fresh1+4provider protocol with authentic gates, exact fixed poses and bounds. No .github workflow/request or actual runtime result.
- [ ] Hash/read local TaskManager/source/API references without imports or binary-equality claim; distinguish prior whole-pair clock/profiler experiments from new boundaries. Record complete test evidence/rulings and honest unknowns. Verify source65/all43workflow preservation and current-only docs changes.

### Task 3: Independent review and Draft integration

- [ ] Commit code+design/results, package BASE..HEAD. One fresh strongest-model reviewer reads complete diff/spec/test evidence and executes targeted CPU contract tests independently; no duplicate fullsuite/native work.
- [ ] Resolve material findings in one inline fix pass with targeted RED→GREEN and necessary fullsuite if code changes; record all findings/dispositions.
- [ ] Add exact review receipt as metadata, push own branch once, create stacked DraftPR onPR38, verify actual baseline push/PR CI4jobs and no scientific/nativeworkflow. Final clean/source65/all43workflow/main/Draft/history checks. Keep reviewed code and post-review metadata heads separate.
