# First-divergence launch transport implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development task-by-task. Root owns Git/CI and selects sequential execution under existing autonomous authorization. No worktrees or repeated permission questions.

**Goal:** Repair inherited-pipe/early-log handling and verify real Xvfb IPC without models.
**Architecture:** Keep production launcher/admission intact; reserve a wrapper-safe pipe FD and begin bounded logs before writes. A fixed CPU receiver exercises that launcher through actual CI xvfb-run; probe-only -a omission bounds server starts. It never enters policy/renderer code.
**Tech Stack:** Python3.11 stdlib/Linux pipes/fcntl/selectors, existing NumPy/OpenCV imports, GitHub Actions/Xvfb.
**Spec:** `docs/superpowers/specs/2026-11-12-first-divergence-transport-design.md`.

## Global Constraints

- Branch `fix/first-divergence-launch-transport`, base2b2c6420e9ce1bbda5683f3afb94600e705a1371; no worktrees; root sole Git/CI owner.
- No old study retry/extension, official weights/MetaDrive/Panda/camera/policy execution. New transport tests/probe/workflow execute no ORT; unchanged baseline small-graph tests are separately allowed. Local transport tests use CPU shell/receiver fixtures only; real Xvfb CI only.
- All13 protected/43 baseline files, existing workflows/request/native admission/converter/actions/thresholds unchanged. PR33 draft/a4strictFAIL/mainofficial0/Stage7incomplete persist.
- Production readFD>=10 and existing resource/deadline caps; probe<=2 wrappers,120s/case300s/total,64KiB/log2MiB/dataset, zero official-model/ORT/MetaDrive calls.

## Review Focus

- Wrapper clobbers FD3: real CPU fixture must receive the permit on reserved descriptor and keep one-use validation.
- Child exits before permit: bounded stderr and original write error survive, without inventing zero model counts.
- Closed/error paths: all FDs/output handles/groups are reclaimed, no timeout deadlock or unbounded output.
- Probe substitutes only receiver, retaining real production launch mechanics; absence of policy/native modules and dummy model paths fail closed.
- Workflow branch/path/context/resource/artifact rules prevent old-model/new-weight execution and repeated probe events.

### Task1: Wrapper-safe pipe and early bounded log repair

**Files:** modify `bigbench/first_divergence_model.py` and affected fixtures in `tests/test_first_divergence_model.py`; create `tests/test_first_divergence_transport.py`.
**Interfaces:** `_launch_trial(model,spec,out,arm,repeat,nonce,parent_uuid,index,launch_row, *, timeout=CHILD_LIMIT_S)` preserves positional callers and returns existing `_BoundedChild`; finite positive timeout<=480. Pump writes/output within deadline; run_study deducts launch elapsed before wait and marks launch timeouts. Preserve exception/row semantics. Read FD>=10; process.log exists and captures actual launch-FD phase before permit errors.

- [ ] Write behavioral RED tests using actual OS pipes/stdPython/shell FD3-clobber fixture, early exit, pre-read output/partial writes/non-reading timeout, bounded stderr, FD closure and original-error/cleanup separation. No Xvfb/native calls.
- [ ] Implement minimal descriptor reservation and output lifecycle fix; leave factory/state/actions/report/gate semantics unchanged.
- [ ] Run new transport tests and affected existing model tests. Save exact command/output/source receipts; full suite once after Task2 final wiring.
- [ ] Root commit; fresh task spec/quality review, scoped fixes; record API handoff for Task2.

### Task2: Fixed zero-model transport probe and isolated workflow

**Files:** create `scripts/first_divergence_transport_probe.py`, `.github/workflows/stage7-first-divergence-transport.yml`; modify `bigbench/first_divergence.py` source registry and `tests/test_first_divergence_transport.py`.
**Interfaces:** `run_probe(out:Path)->dict`, `validate_probe(root:Path)->dict`; CLI `run --out` / `validate --root`, internal fixed receive mode. Consume unchanged production `_launch_trial` via narrow Popen receiver substitution; no production arbitrary-command parameter. Probe additionally removes -a explicitly to bound actual server starts; passes min(remaining120s execution budget after6s cleanup reserve,remaining300s total), then deducts launch elapsed before wait.

- [ ] Write RED CPU fixture tests for two-case success/intentional exit73 with bounded full-wrapper synchronization, nonce/group/source/current-context association, early-log retention, caps/deadlines/stop/no retry, malformed/missing/extra evidence and no native modules. Explicitly test both argv substitutions, raw-handle cleanup and exact3-member success output.
- [ ] Implement actual CI/temp-root/source/attempt1 guarded run and offline strict validator; fixed stdlib receiver, dummy nonexistent model paths, acceptance env removed; only JSON/logs.
- [ ] Add new branch-only push workflow with contents:read, pinned CPU imports, provided bootstrap, xvfb-run+xauth preflight, bounded probe and always-upload; no weights/assets/native packages. Register all3 new producer/test/workflow paths.
- [ ] Run targeted and one final full existing CPU suite, parsed config+bash-n+real actionlint; fresh task and broad branch reviews before push.

### Root execution and evidence

- [ ] Verify remote/branch/source hashes and actual push trigger set; existing native workflow excluded. Push once; draft stacked PR against `fix/public-onnx-action-frame`.
- [ ] Observe basic CI and transport job; download API-bound ZIP once, strict root replay and fresh independent raw review. No retries or automatic models.
- [ ] Commit results/continuation docs, confirm doc-only CI, preserve PR33/stackedPR draft and old unknown0..4 failure. Future scientific collection requires fresh source/canary/protocol; no gate promotion.
