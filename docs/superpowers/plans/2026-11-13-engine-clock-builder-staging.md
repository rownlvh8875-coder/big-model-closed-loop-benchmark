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
- Run limits phase180s/cleanup5s/tmpfs256MiB/wheel1MiB/wire3MiB/stderr1MiB/perfile4MiB/perprocessAS1GiB/process64; no global containment overclaim.
- Qualified I5 repair: one predeclared host tmpfs hard256MiB passed by fixed FD; retention outer1GiB/gzip900MiB/physicalTAR900MiB/regular-files800MiB/nodes40000/file128MiB/manifest16MiB/archiving180s. Preserve available original/partial workspaces on graceful success/failure; abrupt loss remains incomplete.
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

- [x] Write RED tests for mandatory isolation/env/root checks, unsupported-capability rejection, actual trusted-child pipe caps/timeouts/cleanup, secret sentinels, malformed output and strict wheel corruption/tails/RECORD/payloads. Expected: real missing behavior failures.
- [x] Implement minimum source for tests; driver commands/protocol remain incapable of accidental execution on import or missing registered request. Expected: GREEN, no real downloaded runtime or remote workflow yet.
- [x] Test remote API/source/attempt/duplicate request and artifact-boundary fixtures; implement controller/template. Expected: no network in fixtures, no active workflow addition yet.
- [x] Run focused/full CPU suite and preservation checks; commit. Expected: GREEN and explicit source-only readiness.
- [ ] One fresh whole-branch review; regrade and one Important/Critical TDD fix pass if needed, no rereview; record all decline rulings/minors; own-branch Draft/basic CI. Expected: actual reviewed/final HEAD/CI, unchanged old gates.
- [ ] Continue without ending the user task into a distinct operational plan that registers reviewed source and exact provider-free remote request; activate only after source review/CI. Expected: real bounded evidence or preserved terminal failure, no unsupported local execution or old request reuse.

Review outcome:96e97dc C0/I5/M2. Root accepted I1-I5; single qualified TDD fix code9aaca76095e611f6ec1bf73700bb1f6a2e33254c has88focused/814full CPUtests PASS,7optional skips. No independent rereview. M6review-SHA binding and M7reusable deadline maximum remain deferred, with operational external binding/controlled180s callers. Fresh review and all root rulings are retained in the new review/audit; exact-final-source basic CI and the separate operation follow.

Final same-pass I5 refinement: available host disk>=1073741824bytes is measured and recorded before component input transport, with failure facts retained. Qualified code `843fb749abe5c672d65d534fac150c90ec1ac3d3` follows initial fix `9aaca76095e611f6ec1bf73700bb1f6a2e33254c`;89focused/815full CPUtests PASS/7optional skips (full74.276s). Preliminary3ee2954 CI4jobs passed/814unit+1SMALL per event/artifacts0, but is historical; exact final source CI is recorded separately in Draft PR50. No target execution or second independent review occurred.
