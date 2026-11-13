# Builder probe FD correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. One fresh review of this separate delta; no implementation agents or live request replay.

**Goal:** Deliver the verified root and build descriptors to the capability-probe child without changing isolation policy or the consumed failure.

**Architecture:** One capture-call correction, with a real trusted-child descriptor identity regression. Source/evidence/producer identities stay distinct; no namespace or downloaded code execution.

**Tech Stack:** Python3.11 unittest/tempfile/POSIX fstat and reviewed bounded capture/Popen transport.

**Spec:** `docs/superpowers/specs/2026-11-13-engine-clock-builder-probe-fd-design.md`

## Global Constraints

- Basea103c1ebe4611bb859336c4bb7dbe3f88e485aa9/DraftPR51; immutable consumed producer78deaec/request01/run43389231348/artifact14019513519. Observed RTM_NEWADDR/EPERM is not attributed to PF1.
- Change only new builder preparation source/test plus own docs/permitted status. Preserve all45workflow bytes/request/registrations/evidence/old producer70/registry8/legacy policies/tools/tests/proposal/raw/workspaces.
- Actual capture keeps close_fds/literal env/limits and passes exactly root+build FDs. No namespace, downloaded-code execution, new request, fallback, Cloud publish/main merge/worktree/deletion. Native0/16null/Stage7INCOMPLETE.

## Review Focus

1. Merely checking argv numbers does not prove FD delivery: actual child fstat identities must match both parent directories.
2. A closed FD could be reused for another object: compare device/inode, not existence alone.
3. Metadata stubs must never execute the fixture helper or claim real namespace support.
4. The correction must not expose unrelated inherited descriptors, secrets, broader mounts or a changed namespace profile.
5. Corrected future source must not relabel the earlier producer or turn its consumed failure into success.

### Task1: Reproduce, correct and qualify the source-only handoff

**Files:** modify `scripts/engine_clock_builder_preparation.py:382`, `tests/test_engine_clock_builder_preparation.py`; create own report/audit; update permitted continuation/parent/source-plan status only.

**Interfaces:** consumes `capability_probe(work: Path, buildfd: int, facts: dict|None)` and `sandbox.capture(argv, timeout, pass_fds)`. Produces the same receipts/signatures, with both intended descriptor identities preserved into the child.

- [x] Add `test_preflight_preserves_both_directory_descriptors_in_real_trusted_child`: metadata-only helper/version/help stubs, actual trusted host Python fstat child and real capture. Expected old source: root identity true/build identity false, preflight failure; no namespace or downloaded code.
- [x] Run the focused regression and retain behavioral RED, then change only `pass_fds=(fd,)` to `pass_fds=(fd, buildfd)`. Expected: both device/inode identities match; no unrelated source/profile changes.
- [x] Run focused/new-builder/full CPU checks and preservation/diff checks. Expected:90new-builder/816full tests with7optional skips, based on actual output rather than assumed counts; immutable workflows/request/evidence unchanged.
- [ ] Commit, one fresh narrow whole-branch review, regrade/one Important-Critical TDD pass if needed (Minors deferred/no rereview), final own Draft/basic CI and API body roundtrip. Expected: actual reviewed/final source/CI identities recorded; no target replay or backend-success claim.
