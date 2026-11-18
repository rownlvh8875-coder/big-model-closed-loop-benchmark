# Recorded full-S worker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox syntax.

**Goal:** Connect the prepared recorder to a separate owned trial body and verify the entrypoint without native/model execution.
**Architecture:** New orchestration uses original model/world/camera/capture helper and preserves its report; portable stdlib process-check reuses shared ownership handshake. CLI never starts a model.
**Tech Stack:** Python3.11stdlib, existing NumPy/OpenCV, unittest and hosted Linux/Windows CI.
**Spec:** docs/superpowers/specs/2026-11-18-full-s-recorded-worker-design.md

## Global Constraints
Basefad8924/feature/full-s-recorded-worker-v1, existing isolated worktree; private taskNOT_OBSERVED per user reply. No official-model/native execution/download/activation; no main merge or publication. Original scientific producers/capture helper/evidence unchanged. Fixed600steps/.05s/8m/s/.12start, existing9000s/8model/4800call upstream limits and recorder320MiB/384MiB headroom unchanged. One fresh final review, one Critical/Important RED→GREEN pass; Minors defer. Existing sharedUID local fork-timeout failure stays visible; exact hosted whole CI is completion gate.

## Review Focus
1. Errors before model creation, during partial inference, after audit and during provider close/receipt persistence must preserve primary error, bounds and available report.
2. Body invokes original constructors/loop once and restores no global state because none is patched; old report bytes and failure outcomes remain unchanged.
3. Actual ownership-only child requires exact PID/parent/nonce/case/mode ACK before optional imports; ambiguous creation must remain unknown and stop.
4. Output paths, symlink ancestors, fresh-directory/receipt size and cold CLI modes must preserve existing files and not activate native/model code.
5. Source/fixture/session metadata and process-only PASS cannot certify real model/native/RTX/physical/CARLA or duplicate the unknown private job.

### Task 1: worker body and cold actual-entry diagnostics
Files: new bigbench/full_s_recorded_worker.py; scripts/full_s_recorded_worker.py; tests/test_full_s_recorded_worker.py; docs/FULL_S_RECORDED_WORKER.md; laptop-portable.yml new branch/module only.
Interfaces: preflight()->dict; run_recorded_trial(args)->dict; process_check(out)->dict; worker_check(args)->int. TrialFailure exposes report,inference_bounds,primary_error,secondary_errors. args mirrors old full_trial:out,nonce,seed,scenario. Parent admission/bootstrap remains caller-owned.
- [x] RED tests: original body/loop+recorder under only external graph/world/camera doubles, constructor failure, partial inference, audited-no-frame, close error plus primary failure, write failure, guarded cold help/preflight and real subprocess/empty-venv ownership, interrupted Popen and mismatched ACK, path preservation.
- [x] Implement orchestration and separate receipts; attach recorder without modifying original loop/source. Implement read-only preflight/process-check and internal check child; no native-run command.
- [x] GREEN focused/new+core tests, actionlint/diffcheck, commitTask1.

### Task 2: one final review, exact CI and delivery
Consumes Task1 interfaces. Files: final test evidence/delivery outside old evidence; no old producer changes.
- [ ] Whole suite, explicit old sharedUID failure by name; feature push/DraftPR againstfad; exact canonical and Windows CI.
- [ ] Single fresh reviewfad..HEAD; root regrade and one regression fix pass, defer Minors/no rereview.
- [ ] Verify old originals/refs/science/capture bytes and final exact CI; demonstrate cold preflight/actual owned entry/check-only receipts. Archive/delete own scratch only and deliver final report; private job remains unobserved and no native/model is activated.
