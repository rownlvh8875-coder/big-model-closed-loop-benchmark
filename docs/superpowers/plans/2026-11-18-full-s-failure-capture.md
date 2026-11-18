# Full-S failure recording preparation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox syntax.

**Goal:** Prepare bounded failure-neighborhood pixel/state evidence without running a model.
**Architecture:** Separate source-hook camera proxy and original progress callback; immutable CPU snapshots and strict offline receiver. CLI plans/verifies only.
**Tech Stack:** Python3.11stdlib, existing NumPy/OpenCV, unittest, existing CPU/Windows CI.
**Spec:** docs/superpowers/specs/2026-11-18-full-s-failure-capture-design.md

## Global Constraints
Base349c270/new feature/full-s-failure-capture-v1, existing isolated worktree. No local native/Panda/SDK/ORT/official-model loads or new official model jobs. Original scientific producers/thresholds/old evidence unchanged. First+tail8,600 receipts,320MiB output/384MiB headroom requirement; no post-stop steps or invented counts. No native-run CLI/activation/workflow. No merge/publication. One final review, one Critical/Important RED→GREEN fix pass, Minors deferred.

## Review Focus
1. Partial inference or callback/storage failure must preserve known bounds, partial bytes and original failure; never certify full-S.
2. Retaining first+last8 must remain bounded through600 steps and not mutate observations, states, capture/model/reset counts or scientific rows.
3. Receiver must bind retained case/step/pose/pixels/raw action/state and source context, not accept self-consistent swaps or missing first/final evidence.
4. Unsafe/symlink/oversized/object/nonfinite input or insufficient disk must fail before unbounded allocation/write and leave unrelated data alone.
5. Cold plan/help/verify must not import simulators/ORT, launch models or activate workflows; structure validity is never native qualification.

### Task 1: bounded observer, receiver and offline CLI
Files: new bigbench/full_s_failure_capture.py; scripts/full_s_failure_capture.py; tests/test_full_s_failure_capture.py; docs/FULL_S_FAILURE_CAPTURE.md; update laptop-portable.yml only for new branch/test module.
Interfaces: recording_plan()->dict; capture_full_s(policy,camera,lanes,*,intrinsics,out,seed,scene,max_steps=600,progress=None)->original_report; verify_recording(root)->dict. No new native constructors.
- [x] Write failing behavioral tests for actual original run_full_s+adapter+AuditedOfficialOnnx with only external camera/ORT readback doubled: strict row equality/counts, partial inference, pre/post continuity, first+tail bound at600steps, occupied hook/restoration, cold CLI, disk limits, canonical receiver mutations and warp/input replay.
- [x] Implement finite typed immutable snapshots, constant retained packages, bounded final serialization, unchanged original loop integration and strict offline receiver. Implement cold plan/verify only; document integration boundary and limitations.
- [x] Run focused/new+full-S contracts and actionlint/diffcheck; commit task1.

### Task 2: independent review, whole CI and delivery
Consumes Task1 interfaces. Files: final evidence/report and existing workflow test declaration only; no scientific producers.
- [ ] Run whole suite, report existing shared-UID fork-limit failure by name without weakening limits. Push feature/DraftPR against349; exact hosted canonical+Windows whole checks required.
- [ ] Single fresh final review349..HEAD; root regrade, one RED→GREEN fix pass for Critical/Important, ledger Minors/rulings, no re-review.
- [ ] Verify final exact CI, old source/evidence and original protected hashes; deliver plan JSON, no-model fixture verification, source bundle and scoped report. Archive/delete only own scratch, leave all original outputs.
