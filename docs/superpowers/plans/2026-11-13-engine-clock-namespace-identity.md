# Namespace Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline; preserve existing checkout and artifacts.

**Goal:** Retain post-unshare identity facts even when isolation admission cannot be proven.
**Architecture:** Separate fixed stdlib observer, three fresh control processes, unchanged bounded capture/API helpers. No network configuration.
**Tech Stack:** Python stdlib, typed ctypes, installed util-linux, GitHub Actions.
**Spec:** docs/superpowers/specs/2026-11-13-engine-clock-namespace-identity-design.md

## Global Constraints

Existing46 workflows/old01 source/tests/artifacts unchanged. Request namespace-diagnostic-20261113-02; branch diagnose/engine-clock-namespace-20261113-02; run1/attempt1/workers3. No model/build/loopback/policy/main/Cloud operations. Twenty seconds/32KiB stdout/8KiB stderr per worker; journal10s/1MiB; total result131072B. Preserve all scratch. One fresh whole-delta review; one Important/Critical TDD pass, Minor deferred.

## Review Focus

- Returned success with unreadable or unchanged namespace IDs must retain after facts, with no admission claim; worker fixture.
- libc errno must not be stale; explicit typed call and reset, controlled callable fixture.
- Procfs permission errors and unknown text must be observable without leaking raw text; real temporary proc fixture.
- Empty/unrelated kernel records cannot prove availability or LSM absence; journal fixtures.
- Activation must be sole-parent/request-only, not arbitrary source mutation; API-shaped guard fixtures.

### Task 1: New identity observer and one-use execution

**Files:** Create scripts/engine_clock_namespace_identity.py, tests/test_engine_clock_namespace_identity.py, .github/workflows/engine-clock-namespace-identity.yml, docs/STAGE7_ENGINE_CLOCK_NAMESPACE_IDENTITY.md. No changes to existing production files.
**Interfaces:** Reuse unchanged builder helpers, with observer-local bounded proc readers carrying errno metadata; snapshot(proc=Path('/proc'))->dict, worker(case, backend=None)->dict, typed_unshare(libc, flags)->dict, parse_journal(raw,pids)->dict, authenticate(root,env)->binding, run(root,env)->result. Produce identity.json.

- [ ] Write failing tests for after-state retention on success/error, typed errno reset, syscall flags, procfs numeric failures/readlink/map redaction, strict profile labels, matching kernel observations/empty logs, fixed commands and one-use activation guard.
- [ ] Run focused unittest; expected assertion RED absent observer.
- [ ] Implement fixed observer/workflow and exact request-only guard. Always retain snapshots; no network methods exist.
- [ ] Run focused and full tests; expected PASS with existing7 optional skips. Compare all46 workflow bytes and old01 source/tests unchanged.
- [ ] Commit; one fresh review of delta from991cbbc. Regrade/record all findings/declines and fix Important/Critical once RED→GREEN/full suite.
- [ ] Source Draft PR/exact-head push+PR CI before registering request02 as sole added file in one activation commit. Verify branch absent and all-workflow branch run count0, then push once.
- [ ] Consume original run/job/workflow/artifact bytes; verify hashes/CRC/source/run/parent/request uniqueness. Record actual facts and cause limits, preserve consumed02, advance only with supported evidence.

Test commands: /workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -m unittest discover -s tests [-p test_engine_clock_namespace_identity.py]. Baseline834 PASS/7skip at991cbbc.
