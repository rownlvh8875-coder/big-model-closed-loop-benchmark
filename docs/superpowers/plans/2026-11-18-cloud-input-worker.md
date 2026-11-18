# Cloud input replay and Windows worker ownership Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox syntax.

**Goal:** Complete cloud-side camera/input evidence reconstruction and prove corrected legacy worker ownership without a simulator/model.
**Architecture:** Shared stdlib launch/admission helper for three entry points; readonly process-check uses actual legacy workers. Pure archive receiver reconstructs old source54 pixels and input digests.
**Tech Stack:** Python3.11stdlib, existing NumPy2.4.6/OpenCV5.0.0, unittest, existing Windows CI.
**Spec:** docs/superpowers/specs/2026-11-18-cloud-input-worker-design.md

## Global Constraints
Base40a2ee3/newfeature/cloud-input-and-windows-worker-v1 in existing linked worktree. No local native/Panda/SDK/ORT/model load, newofficial model jobs or private-task duplication. Frozen Linux producer/camera/model/rectifier/plant and original evidence unchanged. Windows-only coordinator/entry guards may change; full-S8GiB and dedicated-CARLA limits unchanged. No model/controller/threshold/input changes or generated fake camera evidence. No merge/publish. Exact final canonical/Windows CI; onefreshreview/onefixpass/Minordefer.

## Review Focus
1. Windows venv redirectors must not break actual PID/parent/prefix; Linux/default environment must retain behavior.
2. Interrupted launch before a handle exists must remain unknown; no child may import native/model/connect CARLA before its exact PID is acknowledged.
3. Readonly process-check must never acquire a CARLA lease or simulate/construct/load a model; successful metadata cannot promote full-S/camera/physical tracks.
4. Saved archive/members/case/first-step/audit swaps or truncated/trailing compressed pixels must fail; no reuse of pose1 as a model timestep.
5. First-step matching cannot certify later frames, model causality or full-route success; old0/4traversal/4/4repeat and all failures stay unchanged.

### Task 1: shared launch/admission and actual readonly worker check
Files: new bigbench/worker_ownership.py; scripts/run_laptop_validation.py, laptop_native_trial.py,laptop_carla_trial.py,probe_laptop_camera.py; tests/test_worker_ownership.py, existing portable tests/Windows workflow.
Interfaces: worker_launch()->(executable,env); await_parent_ack(out,parent,nonce,seed,scene,timeout=5)->owner; ownership_snapshot(owner,backend)->dict. Legacy launch_worker(...ownership_only=False) retains normal semantics; --mode process-check produces two owned stdlib receipts with no optional engine imports.
- [ ] Write RED tests for legacy Windows base-exe/env selection, parent PID ack, unknown spawn boundaries, both real entry points stdlib-only process-check, actual empty Windows venv execution.
- [ ] Implement shared helper and reuse all3launchers, guard both legacy workers before native imports, retain CARLA cleanup safety and unknown model bounds. Add cold ownership-only parser mode and coordinator process-check. Include helper/parent sources in new Windows context fingerprints.
- [ ] Run new+94portable tests GREEN/actionlint/diffcheck; commit and recordTask1.

### Task 2: cloud actual pixel/input replay
Files: scripts/verify_saved_camera_inputs.py; tests/test_saved_camera_inputs.py; docs/evidence/cloud-input-worker-20261118/*; docs/CLOUD_VALIDATION_PROGRESS.md.
Interfaces: replay_case(probe_bundle,model_reports,seed,scene)->dict; CLI --cohort-dir PATH --out PATH verifies five exact archived origins and saves scoped JSON. No model constructor/session or native imports.
- [ ] Write RED behavior tests for source→warp→I420/original adapter equality and ordered first-call binding; negative role/pose/audit/digest/ZIP/zlib/case swaps.
- [ ] Implement pure bounded archive receiver; pin authentic origin extents/digests and unchanged source54 semantic producers. Replay all4actual cases/8first inputs; preserve original full-S/repeat results and output full provenance/limits. Execute actual reconstruction in Cloud, not a new model job.
- [ ] Document completed Cloud checks versus genuinely external hardware/data; run relevant tests/diffcheck; commitTask2.

### Task 3: final review, exact CI and closeout
- [ ] Singlefreshmost-capablereview whole40..HEAD; regrade/oneCriticalImportantREDGREENpass, deferMinors/no rereview.
- [ ] Exact final canonical push/PR and Windows push/PR PASS (actual stdlib empty venv worker mode); inherited softwareAPI PRcheck scoped separately. Keep local known sharedUID sandbox failure visible.
- [ ] DraftPRagainstparent40, verify originals/refs/frozen science paths, archiveownledger/rulings/minors and deleteonlyownscratch. Deliver Cloud replay report/results; no request to run local work for already completed Cloud checks. Actual RTX camera and physical/CARLA remain unqualified.
