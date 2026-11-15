# Panda source dispatch candidate implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL superpowers:executing-plans. Inline, one fresh whole-branch review; no implementer delegation.

**Goal:** Implement source-site dispatch hooks and build a separate pinned Panda GL/X11 candidate without native activation.
**Architecture:** inert C++ hook runtime + exact-source transformer + constrained compile/ELF receipt runner. Existing cache/core/bridge stay unchanged; no capture arming.
**Tech Stack:** C++11/GNUamd64/pthreads, Python3.11 stdlib, makepanda, workspace-only Debian dev headers.
**Spec:** ../specs/2026-11-15-panda-source-dispatch.md

## Global Constraints

Preserve3207basefiles/299pins/10originals/main/Drafts102–109/8nativehistories. Samecheckout/inline/noquestions; onefreshreview/oneImportant-CriticalTDDfixpass/no rereview/minorpolish. No GL/Panda/MetaDrive/provider/model/officialORT loading/native replay, oldrequest reuse, Cloudregistry publication or main/sharedbase push/merge. Nativeallowance0/strict0of4FAIL/Stage7INCOMPLETE. Caps4sources×1MiB,delete32,safe256×63B,event10000,routes64,source1GiB,build8GiB,threads4. No global install/old image replacement. Minimal GL/X11 build lacks Python/image parity and grants no runtime ABI/driver/GPU/canary authority.

## Review Focus

1. Typed normalization/default-OFF/error forwarding must preserve every original call, args, return/NULL and both errno values without added GL/resolver calls.
2. Resolver aliases/name snapshot/pointer mismatch/unknown-safe classification must preserve capabilities while sticky failure prevents metadata acceptance.
3. Delete spans, wrong-thread/reentry/callback/cap/finalization and read-tail register/stack transport must fail closed without suppressing originals or arming old ABI.
4. Exact source edits must cover compiled/common/GLX/POSIX paths and early legacy context without touching literals/comments, duplicating original expressions or overwriting existing trees.
5. Dependencies/build receipts must bind actual source/objects/commands/failures and cannot elevate partial/minimal build or supplied flags into native/image admission.

### Task1: Source hook runtime and CPU originals

**Create:** native/panda_source_dispatch.h;native/panda_source_dispatch.cxx;tests/fixtures/panda_source_dispatch_fixture.cxx;tests/test_panda_source_dispatch.py.
**Interfaces:** psd_configure(observer,user,safe,count,cap);psd_finish;psd_stats;psd_bind_read(original);psd_before/after;psd_lookup_begin/resolved/path;psd::call<Kind>(typedoriginal,normalizedargs);psd_read_pixels tail. psd_event fixed kind/origin/seq/args[5]/actualreturned/name[64]/deletecount/names[32]. POD global state, no custom constructors or GL linkage.

- [x] RED compiled CPU scenarios for Focus1–3, including inactive/active/closed, aliases/NULL/mismatch/name mutation, normalized conversions/errno, context failure/delete snapshot, thread/reentry/callback/budget/unsafe/finish and 7arg/register tail.
- [x] Implement runtime; focusedPASS and normal/ASan/UBSan CPU evidence, no native library load; commit.

### Task2: Exact pinned source integration

**Create:** scripts/panda_source_dispatch.py;tests/test_panda_source_dispatch_patch.py.
**Interfaces:** transform_sources(sources:dict)->(changed:dict,manifest:dict);stage(upstream:Path,dest:Path)->manifest. Consumes runtime files, prior four SOURCE_PINS and exact Gitcommit; produces changed files + runtime in glstuff, patch manifest with counts/old/new hashes and readinessFalse. CLI --upstream --out.

- [x] RED actual pinned source transformations, direct legacy/state/readtail tokens, compiled+runtime extension snapshots, GLX/POSIX original expressions exactly once; mutation/alreadypatched/foreignGit/existingoutput rejection. Compile representative transformed CPU methods, never load Panda.
- [x] Implement lexical outside-comment/string edits and isolated clean source stage; focusedPASS, actual full source stage/manifest; commit.

### Task3: Actual candidate build and closeout

**Create:** scripts/build_panda_source_dispatch.py;tests/test_panda_source_dispatch_build.py;RESULT/LEDGER/CONTINUATION and indexed evidence.
**Interfaces:** build(stage:Path,sysroot:Path,out:Path,threads:int=4)->dict. Fixed makepanda command and recorded env/tool/source/dependency pins, validated fresh paths; actual ELF hash/symbols/import/oldABI-reject/readtail data inspection. Never runs built Panda/GL/PView/tests/installer/wheel.

- [x] RED bad manifest/path/flags/overwrite/partial-success admission tests; implement constrained runner.
- [x] Extract exact dev packages to private sysroot, actual makepanda compile/link; inspect resulting candidate without loading, retain partial/failure facts as needed. New method/runtime qualification staysFalse.
- [ ] Fullsuite, onefreshwholebranchreview,oneImportant-CriticalRED→GREENfixpass+suite; exhaustive rulings/declined costs, no rereview. OwnDraft/exactHEADCI, final3207/299/10/oldrefs/histories audit; copy/remove only ownplan scratch.
