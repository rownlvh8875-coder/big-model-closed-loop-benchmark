# Dedicated Bwrap Profile Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Preserve checkout, scratch and raw evidence.

**Goal:** Verify a private trusted bwrap backend with a narrowly attached AppArmor userns profile if baseline demonstrates the known block.
**Architecture:** Guarded one-use controller, pinned primary helper compile, strict before/after trusted-host observer, one optional profile load. Reuse existing immutable capture and builder helpers.
**Tech Stack:** Python stdlib, bubblewrap0.12.0, installed AppArmor parser, GitHub Actions.
**Spec:** docs/superpowers/specs/2026-11-13-engine-clock-bwrap-profile-preflight-design.md

## Global Constraints

Existing47 workflows/source/tests and consumed requests fixed. Request namespace-diagnostic-20261113-03/run1/attempt1/probes<=2/profile_loads<=1. Only new root-owned /usr/local/libexec/stage7-bwrap profile; no sysctls/default policy modifications. No candidate/model/build/image/scientific execution, main merge or Cloud publication. SDK full flags/both FDs; verified256MiB noexec tmpfs; source0.12.0 hash9760d007...3314. Source TDD/full CPU/one fresh review/exact-head CI before activation. Keep raw/source/binary artifacts.

## Review Focus

- Unrelated baseline failure never loads policy: decision fixture.
- Apparent exit0 with invalid isolation/caps/env/write proof never qualifies or loads policy: observation mutation fixtures.
- Root/build descriptors preserved and helper pathname fixed: command boundary fixtures.
- Parser failure/missing preconditions never retries or falls back: bounded backend fixtures.
- Activation/source/tree/API provenance rejects unrelated changes before setup: API-shaped fixtures.

### Task1: Guarded scoped profile preflight

**Files:** Create scripts/engine_clock_bwrap_profile_preflight.py, tests/test_engine_clock_bwrap_profile_preflight.py, docs/proposals/stage7-bwrap.apparmor, .github/workflows/engine-clock-bwrap-profile-preflight.yml, docs/STAGE7_ENGINE_CLOCK_BWRAP_PROFILE_PREFLIGHT.md.
**Interfaces:** qualify(backend)->dict consumes baseline(), eligible(), load(), after(); validate_observation(value,host,after=False)->dict enforces literal proof; probe_argv(rootfd,buildfd)->list; authenticate/root guard produces one-use binding. Reuse prep/sandbox pure helpers.

- [ ] RED fixtures for ready baseline, recognized blocked baseline then profile+ready, unrelated failure/invalid success, missing prerequisites, parser failure, failed after, observation mutations, fixed helper/FD argv and one-use complete activation delta.
- [ ] Implement decision/controller/profile/workflow; test fixed trusted observer only. Expected focused PASS, no live namespace/parser/network calls in CPU tests.
- [ ] Full unittest suite PASS/7 optional skips; verify47 old workflows/source unchanged; commit, one fresh read-only review, one Important/Critical RED→GREEN pass and full suite, defer Minor.
- [ ] Push source/Draft exact-head CI; register03 request-only sole-parent commit after branch/all-run0 checks; push once.
- [ ] Consume unique run/jobs/workflow/artifact original bytes; validate source/binary/profile/probe facts and before/after limits, publish Draft evidence only; qualify narrowly or state authentic blocker.

Commands use /workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -m unittest discover -s tests [-p test_engine_clock_bwrap_profile_preflight.py]. Baseline847 PASS/7skip at1d07c70.
