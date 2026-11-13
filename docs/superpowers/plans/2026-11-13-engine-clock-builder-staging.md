# Builder staging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement/test safe staging and a bounded provider-free builder protocol, then hand off reviewed source for continuous operational execution.

**Architecture:** Pure plan compilation, descriptor-relative staging/verification, strict namespace runner/owned driver and independent wheel validation. No executable downloaded code during source/fixture work. Local kernel is unsupported; reviewed remote operation is a distinct next plan, not an unisolated fallback.

**Tech Stack:** Python3.11 stdlib, POSIX FD operations, bubblewrap namespace profile, unittest fixtures; inactive GitHub workflow template.

**Spec:** `docs/superpowers/specs/2026-11-13-engine-clock-builder-staging-design.md`

## Global Constraints

- Preserve old455trackedfiles except continuation/parent status docs; old workflows44 and producer70/registry8 unchanged.
- No local downloaded runtime/bootstrap/source execution; local trusted-true discovery failed UID mapping.
- Plan/stage limits128sources/20000nodes/512MiB/file128MiB/path4096/depth64/40hops/JSON16MiB/deadline180s.
- Run limits phase180s/cleanup5s/tmpfs256MiB/wheel1MiB/wire3MiB/stderr1MiB/perfile1MiB/perprocessAS1GiB/process64; no global containment overclaim.
- All native/image admissionfalse; old16refsnull/nativeallowance0. No worktrees/Cloud publish/main merge; retain all evidence/workspaces.

## Review Focus

1. Descriptor closure, alias normalization and generated-file conflicts versus actual nofollow/same-device writes and scans.
2. Absolute candidate links, file/directory races, existing destinations and partial failure preservation without host traversal.
3. Mandatory namespace/readonly/tmpfs/environment flags versus unsupported backend; bounded output/death cleanup and no secret serialization.
4. Strict wheel ZIP/layout/deflate/RECORD/payload validation versus forged child results and opaque caller hashes.
5. Remote request/source/API/attempt/duplicate-run binding, credential routing and inactive workflow activation boundary.

### Task 1: Safe staging plan, writer and exact-tree verifier

**Files:** create `scripts/engine_clock_builder_staging.py`, `tests/test_engine_clock_builder_staging.py`.

**Interfaces:** consumes normalized source descriptors; produces compile_plan/stage_tree/verify_tree with plan digest and non-admitting receipts for Task2.

- [x] Write filesystem fixtures for alias parents, generated config, conflicting/unsafe sources, exact files/modes/links, no extra/missing content, symlink races/hardlinks/existing roots/deadlines/caps and partial failure. Run focused tests before implementation. Expected: RED because module/behavior missing, not typo/import crash.
- [x] Implement compile_plan, stage_tree, verify_tree to pass those real filesystem tests. Expected: GREEN, host sentinel bytes unchanged, no process/network activity.
- [x] Run focused and full unittest suite; compare actual counts/skips and record failures; commit. Expected: all GREEN, no new native/provider/model calls.

### Task 2: Namespace protocol, owned driver, strict wheel and remote handoff

**Files:** create builder sandbox/driver/wheel/controller modules under `scripts/`, focused unittest files, inactive `docs/proposals/engine-clock-builder-preparation.workflow.json`; update only continuation/parent status among old files.

**Interfaces:** consumes Task1 plan/root verifier and PR47/48/49 input manifests. Produces fixed launch profile, bounded sanitized execution/output API, exact built-wheel validator and inactive remote source/request protocol.

- [ ] Write RED tests for mandatory isolation/env/root checks, unsupported-capability rejection, actual trusted-child pipe caps/timeouts/cleanup, secret sentinels, malformed output and strict wheel corruption/tails/RECORD/payloads. Expected: real missing behavior failures.
- [ ] Implement minimum source for tests; driver commands/protocol remain incapable of accidental execution on import or missing registered request. Expected: GREEN, no real downloaded runtime or remote workflow yet.
- [ ] Test remote API/source/attempt/duplicate request and artifact-boundary fixtures; implement controller/template. Expected: no network in fixtures, no active workflow addition yet.
- [ ] Run focused/full CPU suite and preservation checks; commit. Expected: GREEN and explicit source-only readiness.
- [ ] One fresh whole-branch review; regrade and one Important/Critical TDD fix pass if needed, no rereview; record all decline rulings/minors; own-branch Draft/basic CI. Expected: actual reviewed/final HEAD/CI, unchanged old gates.
- [ ] Continue without ending the user task into a distinct operational plan that registers reviewed source and exact provider-free remote request; activate only after source review/CI. Expected: real bounded evidence or preserved terminal failure, no unsupported local execution or old request reuse.
