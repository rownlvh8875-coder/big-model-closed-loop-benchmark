# Namespace Diagnostic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Obtain one new model-free observation of namespace/capability/loopback failure on Ubuntu 24.04.

**Architecture:** A fixed stdlib Python worker creates isolated user and network namespaces. A guarded parent launches three bounded workers with the existing closed-environment capture SDK and records sanitized facts and optional matching kernel denials.

**Tech Stack:** Python stdlib, ctypes Linux syscalls, rtnetlink, GitHub Actions.

**Spec:** docs/superpowers/specs/2026-11-13-engine-clock-namespace-diagnostic-design.md

## Global Constraints

- No model/native/render/ORT/GL execution, old request retry, main merge, Cloud publish or host policy modification.
- Existing 45 workflow bytes and all prior artifacts stay unchanged.
- Request namespace-diagnostic-20261113-01, branch diagnose/engine-clock-namespace-20261113-01, one run/attempt, three workers; 20 seconds each, 32 KiB stdout/8 KiB stderr per worker.
- Only network mutations inside proven new user AND network namespaces. No arbitrary commands or child credentials.
- One fresh whole-delta review, one Important/Critical TDD fix pass; preserve scratch/evidence per user preference.

## Review Focus

- Namespace creation succeeds but one identity stays unchanged: fail closed before mapping/network writes; tested by fake backend.
- Netlink malformed/mismatched ACKs: reject without reporting success; binary fixtures.
- Effective versus bounding capability changes: record independently; worker ordering fixture.
- Kernel log missing/unrelated/sensitive: UNKNOWN or hash, only our PIDs and net_admin denial fields retained; fixtures.
- Replayed/mismatched activation: reject second attempt, duplicate run, changed closure; API-shaped fixtures.

### Task 1: Guarded three-case diagnostic

**Files:** Create scripts/engine_clock_namespace_diagnostic.py, tests/test_engine_clock_namespace_diagnostic.py, .github/workflows/engine-clock-namespace-diagnostic.yml and docs/STAGE7_ENGINE_CLOCK_NAMESPACE_DIAGNOSTIC.md.

**Interfaces:** Consumes existing builder sandbox.capture, preparation API/context/closure helpers; produces a bounded JSON diagnostic-v1 result and source binding. No existing production file changes.

- [ ] Write tests for isolation failure stopping mutation, fixed case order, capability intervention, netlink ACK parsing, fact/audit redaction and one-use guard/source closure.
- [ ] Run focused unittest; expected RED absent implementation (assert module availability rather than importing absent module).
- [ ] Implement run_worker(case, backend=None), parse_ack(raw, seq), facts(), filter_denials(raw, pids), authenticate(root, env), run(root, env); create fixed one-use workflow.
- [ ] Run focused and full unittest suites; expected PASS, existing optional native skips only.
- [ ] Commit and obtain one fresh-context review of the new delta. Re-grade every finding/decline with costs. Fix Important/Critical once using RED→GREEN, then full suite.
- [ ] Push reviewed source branch/Draft PR, observe exact-head basic CI. Register new request in a single activation commit and push once only after CI passes.
- [ ] Consume original API/run/job/artifact bytes, verify bounded result and source binding, preserve all evidence, document actual diagnosis and next supported action.

Verification commands use /workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -m unittest discover -s tests, with focused -p test_engine_clock_namespace_diagnostic.py first. Expected full baseline 816 tests/7 optional skips before adding tests. No product dependencies installed.
