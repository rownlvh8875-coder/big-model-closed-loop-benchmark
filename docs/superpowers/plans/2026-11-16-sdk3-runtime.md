# SDK3 runtime continuation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. One fresh whole-branch review, no implementer delegation. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Execute the three user-requested stages against actual SDK3 and preserve honest failures.
**Architecture:** A stdlib host orchestrator authenticates fixed artifacts and owns disposable containers; a small child records granular Panda/GLX checkpoints. Existing official-model producer/comparators remain unchanged.
**Tech Stack:** Python stdlib/unittest, Docker, pinned Panda image/SDK, GitHub Actions.
**Spec:** ../specs/2026-11-16-sdk3-runtime-design.md

## Global Constraints

Base2435bf438651916ff496c07d334ba264d56a71bc; all prior files/modes/requests/verdicts unchanged. Source work /dev/shm only because original volume ENOSPC. No merge or publication. Exact SDK/image/model pins and original rendering semantics from spec. New cohort only; no historical request reuse. Strict mismatch remainsFAIL; expansion requires4/4.

## Review Focus

1. Truncated/missing/reordered child checkpoints or nonzero exit must never pass (Task1 tests).
2. Wrong SDK/image ZIP/member bytes, duplicate/path-traversal members must fail before target spawn (Task1 tests).
3. Correct hash with wrong frame bytes/driver/cleanup must fail (Task1 tests).
4. An incomplete/equal-process/equal-UUID model pair must never pass or launch expansion (Task2 tests).
5. Container failures/timeouts must retain logs/status and remove only owned containers (Task1 tests and hosted evidence).

### Task1: Actual SDK3/GLX diagnostic pipeline
**Files:** scripts/panda_sdk3_runtime.py,scripts/panda_sdk3_diagnostic.py,tests/test_panda_sdk3_runtime.py,.github/workflows/panda-sdk3-runtime-v1.yml.
**Interfaces:** verify_member(zip_path,member,size,digest,out)->Path; validate_probe(events,report,returncode)->dict; run_host(out:Path,model_phase:bool)->dict. Child emits JSONL checkpoints and report.json.
- [x] Add tests for exact bytes, duplicate/traversal archive entries, incomplete checkpoints/nonzero exits, distinct exact RGB frames, driver/SDK/core identity and cleanup; run focused command,ExpectedRED.
- [x] Implement minimal fixed artifact/SDK3 staging and owned container/child checkpoint+frame checks; run focused,ExpectedGREEN. Commit.

### Task2: Conditional official MD-V3 cohort
**Files:** same orchestrator/workflow/test; existing scripts/native_mdv3_repeat_trial.py and comparators are consumed unchanged.
**Interfaces:** model_gate(verdicts:list[dict])->dict; calls existing compare_fresh_trials and aggregate_original_mdv3_current_recheck.
- [x] Add incomplete/duplicate pair/mismatch tests; run focused,ExpectedRED.
- [x] Add exact model download and eight fresh bounded model containers after two GLX passes; preserve all JSON and strict gate. Expansion remains conditional. Run focused,ExpectedGREEN. Commit.

### Task3: Review, real execution, diagnosis and closeout
- [ ] Run canonical CI/full suite; sole fresh review/one Important RED→GREEN fix pass; preserve original base. ExpectedGREEN before runtime.
- [ ] Push own Draft, then one request-only activation branch triggers the new workflow. Observe SDK/GLX and conditional model results; no inferred PASS. Diagnose any actual failure and make only evidence-supported changes under fresh versioned inputs.
- [ ] Record actual processes, gates, SHA/PR/Actions/artifacts and unresolved blockers. Update continuation through a new companion file without rewriting frozen history. Final exactHEAD CI/clean verification.
