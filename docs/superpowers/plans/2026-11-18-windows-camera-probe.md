# Windows model-free original camera probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox syntax.

**Goal:** Expose bounded original Windows camera checks without models and independently verify saved RGB.
**Architecture:** Pure readiness/capture/receiver module; cold CLI owns four fresh children using existing native helpers. Existing GPU/full-S producers stay unchanged.
**Tech Stack:** Python3.11stdlib + existing NumPy2.4.6/OpenCV5.0; optional Windows Panda1.10.13/MetaDrive0.4.3 only in actual owned child.
**Spec:** docs/superpowers/specs/2026-11-18-windows-camera-probe-design.md

## Global Constraints
Base92fc0b4, existing linked worktree/new feature/windows-camera-probe-v1; parent/original/main preserved. No local Panda/SDK/ORT/official model load. No model path, download or extra official execution. Assets absent=>BLOCKED, no automatic download. Four sequential owned240s Windows children, two poses each; no retry/outcome selection. Exact RGB/warp and original camera/terrain code; no sample/pixel/timing/steering changes. No main merge/environment publication. Native-camera result only virtual pinhole; all broader qualification flags false.

## Review Focus
1. Missing assets/wrong package/low modelRAM must block only appropriate work before native imports; camera-only does not admit models.
2. Child failure/timeout/interrupt must end the exact process and retain uncertainty/error receipts without a false PASS.
3. Modified source/canvas, invalid/trailing zlib, swapped case or stale pose/view must fail independent verification.
4. Child context or driver mismatch between views/cases must fail; saved GPU8x8 cannot certify cameraMSAA.
5. Cold help/inventory/verify must never import Panda/ORT or download; no result can imply fullS/physical/alltracks completion.

### Task 1: pure camera evidence and admission
Files: new bigbench/windows_camera_probe.py; tests/test_windows_camera_probe.py.
Interfaces: camera_readiness(inventory,versions,assets_version)->dict; capture_probe(camera,raw,lanes,intrinsics,out,seed,scene)->dict; verify_probe(report,directory)->dict. Uses original NativeWorldCamera observer contract and PinholeRectifier; produces source/canvas zlib and scoped receiver results.
- [ ] Write behavioral tests for4.24GiB camera admission/no modelgate relaxation, exact package/assets checks, two source/canvas captures, corrupted/trailing payloads, stale pose/view, swapped geometry. Run RED at missing implementation.
- [ ] Implement minimal pure readiness/capture/receiver. Run module and71portable baseline GREEN. Commit.

### Task 2: owned CLI and Windows handoff
Files: new scripts/probe_laptop_camera.py; tests/test_windows_camera_cli.py; laptop-portable.yml; docs/WINDOWS_CAMERA_PROBE.md; new evidence receipt directory.
Interfaces: inventory/probe/verify CLI; owned child nonce/PID/case/cleanup; parent sequential four workers and full scoped verification. Uses Task1 receiver. Source/context hash set pinned to actual executing checkout; source RGB retained after capture only.
- [ ] Cold help/missing-assets-before-native, child lifecycle timeout/reaping and four-case receiver negatives RED→GREEN.
- [ ] Implement CLI, read-only metadata/assets readiness, native child using original world/windows_context/NativeWorldCamera, both camera drivers and source hashes, Python download prohibition, all4case retention. Pure verify handles final source/library/case identity; no model imports.
- [ ] Add Windows CI branch/module and instructions for optional explicit asset install, no official model, retained originals/fresh output and virtual-only scope. Include sanitized source92fc actual GPU readbacks with offline receipt, no private raw handoff paths. Run focused tests/actionlint/diffcheck, commit.

### Task 3: final review/CI and delivery
- [ ] Single fresh most-capable reviewer for whole92..HEAD; one Critical/Important regression fix pass, Minors deferred/no rereview.
- [ ] Exact final-source canonical push+PR four jobs and Windows push+PR PASS; existing inherited software API PR smoke recorded separately, no new model/native Cloud task.
- [ ] Build source-pinned Windows ZIP, cold help/inventory/verify smoke, preserve original assets/refs/source54/GPU92 and worktree. Archive only own ledger/Rulings/Minors then delete only own scratch. Deliver actual Windows camera NOT_RUN and external fullS/physical/CARLA pending explicitly.

Single-review fix pass: direct CPython Windows venv worker launch with actual stdlib Windows venv identity CI;5s PID acknowledgement before native imports; interrupted spawn stays unknown/stops further children. Require one assigned cohort/parent/case, successful parent+child cold admission and lifecycle with no contradictory errors; canonical pose/role filenames and identical road/wide driver tuples. Check MetaDrive texture sentinel before native and selected output volume headroom. These strengthen Task2 receipts without changing original native producers/model gates. Defer two Minors, no rereview. Local whole-suite sandbox fork remains subject to sharedUID/RLIMIT_NPROC; exact-source hosted full suite required.
