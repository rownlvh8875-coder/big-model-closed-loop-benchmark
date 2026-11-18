# Recorded worker parent, receiver and native camera canary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox syntax.

**Goal:** Finish parent/receiver connection and execute one real cloud SDK/camera/recorder canary with0official models.
**Architecture:** Shared recorded-body real/canary modes, sealed no-graph policy, frozen owned Xvfb/container helpers, strict receiver and request-only branch activation after exact source CI.
**Tech Stack:** Python3.11stdlib, existing NumPy2.4.6/CV5.0, frozen SDK3 Docker image, GitHub Actions.
**Spec:** docs/superpowers/specs/2026-11-18-recorded-worker-canary-design.md

## Global Constraints
Base3708b5f/feature/recorded-worker-canary-v1 in existing isolated worktree. No managed-host native/ORT/model loads, no official model/weights jobs anywhere; private taskunknown. OneCIcanary: seed20261109left_right,2captures/4perceives excluding startup, synthetic fixture state/action only. Same science/frozen capture helper unchanged.320MiB/384MiB recorder,240s child/300s container, existing10GiB/2CPU/pids128/netnone/readonly/uid65534/llvmpipe profile and frozen image/core/SDK pins. New own workflow/request only; activation request commit after reviewed source CI. No main merge/publication. One fresh final review, one Important/Critical regression pass, Minorsdefer. Runtime failures require evidence-led debug/new source before a new one-shot activation, not blind reruns.

## Review Focus
1. Canary must never construct a real policy/session/open weights or count fixture audits as real inference; synthetic state and actual camera bytes stay distinguishable.
2. Child/parent/case/nonce/source/cleanup and model/session receipt swaps or partial data must fail; unavailable native counts stay bounded/unknown.
3. Request auth rejects wrong branch/event/attempt/parent/source CI/delta/map before staging or runtime; canary cannot activate real-model mode.
4. Bounded ZIP/file parsing, symlinks/path traversal/duplicates/incomplete streams and output preservation must hold without running evidence code.
5. Actual new camera/recorder pass cannot imply RTX, physical optics, CARLA, real graph feed, baseline repeatability, model quality or full-S completion.

### Task 1: shared canary worker, parent and receivers
Files: bigbench/full_s_recorded_worker.py (orchestration only); new bigbench/recorded_worker_canary.py; scripts/recorded_worker_canary_native.py; tests/test_recorded_worker_canary.py; docs/RECORDED_WORKER_CANARY.md.
Interfaces: NoGraphPolicy(spec); run_camera_canary_trial(args); verify_trial(root,mode)->dict; validate_native_bundle(root)->dict; canary_command(...) reuses frozen runtime; read_native_ack(path)->owner; audit_zero_model(event,args).
- [x] RED tests real existing loop/collector on external-camera/SDK doubles, zero graph/weight audit, correct fixture counters, parent ACK and deadline/cleanup binding, real-mode rejection of fixture, corrupt receipts/payloads/paths and protected-source invariance.
- [x] Implement shared body mode and explicit synthetic policy, parent/child entry and pure bounded receiver. No scientific/capture-helper/global patch edits.
- [x] GREEN new+original worker/collector tests, commitTask1.

### Task 2: authenticated host and inactive workflow
Files: new scripts/run_recorded_worker_canary.py; .github/workflows/recorded-worker-canary.yml; docs/requests/recorded-worker-canary-20261118-01.json; auth/ZIP tests; laptop-portable.yml branch/module declaration.
Interfaces: source_manifest(source)->dict; authenticate_request(bundle)->request; host_run()->summary; receive_downloaded_archive(...)->dict, always0official models; Task1 receiver validates actual bundle.
- [x] RED wrong branch/parent/delta/attempt/CI/source map/mode/budget and malformed archive tests; cold plan/help no optional/native modules.
- [x] Implement host source auth, frozen stage_runtime, scoped container command and always-retained failure bundle; workflow zero-model only on own activation branch/request path.
- [x] GREEN targeted/actionlint/diffcheck; commitTask2.

### Task 3: review, exact CI, actual canary and delivery
- [ ] Whole suite (known selected-host sharedUID fork-timeout failure by name); single fresh final review3708..HEAD and one RED→GREEN Critical/Important pass; no rereview/Minorsdefer.
- [ ] Feature/DraftPR against3708; final exact canonical/Windows CI and code manifest. Create one request-only activation commit on diagnostic/recorded-worker-canary-20261118-01, attempt1, officialmodel limits0.
- [ ] Observe actual GitHub canary to terminal state, authenticate run/attempt/parent/source/artifact size+SHA and bounded receiver here. Diagnose real failure if any; preserve original failed attempts and never weaken gates.
- [ ] Preserve old artifacts/refs/science, record real images versus fixture tensors; deliver actual canary results and limits, archive/delete own scratch only, no publication/main merge.
