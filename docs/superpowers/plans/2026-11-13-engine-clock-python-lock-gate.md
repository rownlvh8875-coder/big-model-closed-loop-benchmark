# Python dependency lock gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Record an honest, bounded binary-only dependency resolution checkpoint against the real retained derivative wheel.

**Architecture:** A historical one-use operator transcript invokes existing pip in dry-run mode and saves raw results. No reusable production resolver or image adapter is added.

**Tech Stack:** Existing Python3.11.17/pip26.2.2, stdlib, curl, public PyPI.

**Spec:** `docs/superpowers/specs/2026-11-13-engine-clock-python-lock-gate-design.md`

## Global Constraints

- Fixed future pins: Python3.11.18/NumPy2.4.6/OpenCVheadless5.0.0.93/Panda1.10.13/MetaDrive0.4.3; actual tool Python3.11.17.
- No source build/install/import/image/native/model/ORT/provider calls. No retry or substitute dependency.
- One pip invocation <=240s/512MiB tree/1MiB log; >=1GiB initial free. One progressbar metadata request <=30s/2MiB.
- Keep inherited proxy/CA and TLS; no credential values. All readiness/admission flags false.
- Preserve old files, raw outputs and workspaces; no worktree creation/Cloud publish/main merge.

## Review Focus

1. Cross-target tags/markers are a screen, not a complete image lock or target-runtime test.
2. An absent wheel is distinguished from mathematical unsatisfiability and historical rendering cause.
3. Raw failure logs and real metadata agree; no swallowed source execution or relaxed rerun.
4. Tool/source/request/input hashes and actual execution HEAD remain distinct from later evidence/review HEAD.
5. Bounded process cleanup, output preservation and credential handling do not overclaim quota/host attestation.

### Task 1: Register, resolve once, preserve and review the gate

**Files:** new spec/plan, `docs/evidence/STAGE7_ENGINE_CLOCK_PYTHON_LOCK_{REQUEST,OPERATOR,RESULT,AUDIT,REVIEW}.*`, `docs/STAGE7_ENGINE_CLOCK_PYTHON_LOCK.md`; update only `docs/STAGE7_CONTINUATION.md` and parent Task3 status.

**Interfaces:** consumes PR45 local wheel input JSON and immutable retained bytes; produces non-admitting local operation evidence, never an installable lock or native allowance.

- [ ] Register request/operator and source commit before any package-resolution network action. Expected: clean committed source, new operation path, source/input hashes recorded.
- [ ] Execute the registered operator exactly once; preserve nonzero pip exit/report absence as real results. Expected: receipt+log and official progressbar JSON, or original bounded failure. No success assumed.
- [ ] Independently check retained wheel SHA, pip flags, exit/log, metadata file types and all saved output hashes. Expected: honest status, original inputs unchanged, readiness false; no product tests invented for data-only work.
- [ ] Write result/audit/continuation; commit; one fresh whole-branch review, ledger all findings and declined judgments. Expected: actual reviewed HEAD identified. Important/Critical source changes require one TDD fix pass; data-only corrections use direct evidence validation.
- [ ] Push own branch, create Draft PR against PR45, inspect actual baseline CI/jobs/artifact counts and final git/main/cloud preservation. Expected: final HEAD and observed conclusions, no native run or image preparation.
