# SDK3 capture progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline;one fresh whole-branch reviewer before activation,no implementer delegation. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Identify the active capture boundary at160s with durable progress and timed stacks.
**Architecture:** New bounded CPU journal/instance observers/watchdog;new native seven-pose entry and authenticated single-job host,existing sources unchanged.
**Tech Stack:** Python/unittest/numpy,faulthandler,existing frozen SDK3/Actions.
**Spec:** ../specs/2026-11-16-sdk3-capture-progress-design.md

## Global Constraints

Baseee1203b12cf6e185b754ef8095097296650d8270;additions only. One hostedrenderer/0officialmodels/0inferences,160schild/180scontainer,2CPU/10GiB/privateIPC/readonlyroot/networknone/uid65534/tmpfs512MiB. Existing frozen image/SDK/core/BaseCamera/prior fullRGB pins unchanged. No localnative/model/publication/mainmerge. Journal256events/4096B each/1MiBtotal;stacks30srepeat. Original3/4FAIL/Stage7false. One request diagnostic/sdk3-capture-progress-20261116-01;requestfile docs/requests/sdk3-capture-progress-20261116-01.json.

## Review Focus

1. Wrappers swallow/repeat/reorder calls or fail exact restoration;Task1 real Python doubles and exceptions.
2. Timed stack watchdog missing/cancelled early or parent loses kill returncode;Task1 harmless real subprocesses.
3. Partial/malformed/nested trace becomes complete or source-equivalent;Task2 literal journal/image negatives.
4. Wrong model mount/unknown exit/OOM/cleanup/PID/request/sourceCI admitted by timeout;Task2 admission mutation cases.
5. New observability gate interpreted as native/model/repairPASS;Task2 explicitfalse assertions and actual report.

### Task1: durable CPU observers and parent watchdog
**Files:** Create scripts/sdk3_capture_progress.py,tests/test_sdk3_capture_progress.py.
**Interfaces:** Journal(folder,identity);Journal.emit(event,step=0,camera=None,**metadata);observe(camera,journal)contextmanager;stack_watchdog(path,seconds=30)contextmanager;wait_observed(child,server,timeout,out)->int;read_journal(path)->list.
- [ ] RED: real nested capture/perceive/getter/step ordering,exact restoration/exception,bounds/sequence;ExpectedFAIL missing module/behavior.
- [ ] GREEN: bounded durable journal and instance wrappers,real subprocess stack+timeout/exit tests;ExpectedPASS. Commit.

### Task2: authenticated single renderer and independent closeout
**Files:** Create scripts/sdk3_capture_progress_native.py,scripts/run_sdk3_capture_progress.py,tests/test_sdk3_capture_progress_host.py,.github/workflows/sdk3-capture-progress-v1.yml,new evidence/report only.
**Interfaces:** native_command(...reference...);validate_receipt(folder,reference_path,nonce)->dict;authenticate_source(bundle);run(). Uses Task1 exact names.
- [ ] RED: timeout remains nativeFAIL,unknown exits/trace/PID/model/cleanup reject,source mismatch partialinconclusive;ExpectedFAIL missing module/behavior.
- [ ] GREEN: new zero-model native/bootstrap/progress/rawimages,parentwait and host pinnedstaging/request/resource guards;ExpectedfocusedPASS/actionlint.
- [ ] ExactsourceCI4jobsPASS;solefreshreview;one ImportantRED→GREEN fixpass/no rereview;Minorledger.
- [ ] Request-only single-child activation;authenticate actualartifact and independently recompute trace/images/lifecycle. Retain timeouts and unknowns.
- [ ] New result/DraftPR based on133;final exactHEADCI/log counts/remote/body/parent/main/original preservation. Archive/remove only this plan scratch. No original gate promotion.
