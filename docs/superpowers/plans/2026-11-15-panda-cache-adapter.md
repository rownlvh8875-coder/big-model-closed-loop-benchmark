# Panda source command-cache adapter implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL superpowers:executing-plans. Inline execution, one fresh whole-branch review; no implementer delegation.

**Goal:** Deliver bounded source-observer bootstrap/delete/lifecycle application into immutable command cache, verified with CPU originals only.
**Architecture:** C++ POD adapter around psd and rc public APIs, no-op replay plus per-context PBO/pending-destroy shadow. CPU harness compiles actual components and pins prior candidate as data; no source SDK rebuild or loading.
**Tech Stack:** C++11/C11/GNUamd64/pthreads, Python3.11 stdlib, cc/binutils/ASan/UBSan.
**Spec:** ../specs/2026-11-15-panda-cache-adapter.md

## Global Constraints

Preserve3329basefiles/299pins/10originals/main/Drafts102–110/8nativehistories. Samecheckout/inline/noquestions; no main/shared-base update, Cloud/registry publish, old request reuse, Panda/GL/MetaDrive/provider/model/officialORT/native execution/loading. Nativeallowance0/strict0of4FAIL/Stage7INCOMPLETE.3MiBadapter/10000events/32delete/256x63Bsafe/2live4lifetimes/32FBOslots; harness64MiBoutput,10sscenario,30scompile. Original cache/runtime/bridge/SDK unchanged; no capture arming/driver/image/profile qualification. One fresh review/oneImportant-CriticalTDDfixpass/no rereview/minorpolish.

## Review Focus

1. Source callback/forward/resolution/path/event counters, lifecycle ordering, delayed source errors and bounded bootstrap replay cannot silently drop/duplicate commands or accept in-flight/failed metadata.
2. Copied deletion inputs before original mutation, PBO reset before any FBO readiness, unrelated/zero/duplicate names and unshared context isolation cannot restore stale bindings.
3. Actual GLX creation/current returns, sharing/display/handle reuse and deferred current-context destruction cannot invent a live/current context or release its state early.
4. Attach/snapshot/observe/finalize on foreign/reentrant/dirty/closed/overlapping storage and failed downstream finalization must reject, preserve originals/errno, and expose no stale output or capture authority.
5. Harness candidate/source/tool/process/output binding must reflect actual CPU execution; modified candidate/FIFO/symlink/existing output/ambient flags must reject without native loading or overwriting proof.

### Task1: Native observer adapter and CPU behavioral tests

**Create:** native/panda_cache_adapter.h;native/panda_cache_adapter.cxx;tests/fixtures/panda_cache_adapter_fixture.cxx;tests/test_panda_cache_adapter.py.
**Interfaces:** exact pca APIs in spec consume immutable psd_event/psd_counts and rc public state APIs; produce command-derived snapshots/stats/combined finish result. No-op signatures exactly match cache commands; C cache compiled separately.

- [x] RED tests for missing adapter, bootstrap/live equivalence and no repeated originals, copied buffer/FBO deletion and context isolation, all context creation forms/failure/current switching/pending-destroy/reuse, counter/shape/thread/reentry/cap/attach/identity/finish failures, unchanged/overwritten errno and original-only7arg/register read tail.
- [x] Implement minimal adapter and CPU fixture; run focused tests including malformed spans with ASan/UBSan. Expected: PASS, originals/errno preserved, unhealthy metadata rejected, no native authority.
- [x] Record results/rulings, commit tested implementation.

### Task2: Bounded CPU evidence harness and closeout

**Create:** scripts/panda_cache_adapter_cpu.py;tests/test_panda_cache_adapter_cpu.py;RESULT/LEDGER/CONTINUATION and indexed proof.
**Interfaces:** compile_fixture(out:Path,sanitize:bool)->commands;run_cpu(out:Path,candidate:Path)->dict. Uses immutable candidate SHA/static checker as data, exact source hashes, normal+ASan/UBSan CPU scenarios; returns CPU-contract status with runtime/nativeFalse.

- [x] RED CLI candidate/source/path/overwrite/time/output/ambient flag and actual-case receipt tests. Expected: reject foreign/unsafe inputs before product execution, preserve existing output.
- [x] Implement fixed compiler/scenario commands and source/candidate/output pins, run all normal/sanitized scenarios; focusedPASS then whole unittest discover suite, actual preservation3329/299/10/oldrefs/histories.
- [x] One fresh whole-branch review, rule on every finding/declined behavior; one Important/Critical TDDfixpass+fullsuite, no rereview/minorpolish; retain before/final proofs and copy/remove only own scratch; commit.
- Final immutable-head operation: ownDraft against55ab312 branch, exactHEAD workflow411705464 push+pull_request each2jobs/attempt1/success/artifacts0, fresh preservation/body roundtrip and retained final receipt. No main/shared-base merge/push/Cloud publication.
