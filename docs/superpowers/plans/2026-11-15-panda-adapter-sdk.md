# Panda activity/cache SDK implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL superpowers:executing-plans. Inline, one fresh whole-branch review, no implementer delegation.

**Goal:** Actual separate minimal SDK with single-image activity+adapter+cache and static/CPU linkage evidence.
**Architecture:** exact5file upstream integration plus9unchanged native files; constrained makepanda compile/link and bounded ELF interface checks. Fully defined CPU shared SDK exercises actual linked C/C++ components; real SDK stays DATA ONLY.
**Tech Stack:** Python3.11 stdlib, C11/C++11/GNUamd64/pthreads, makepanda/GCC/binutils/ASan/UBSan, private existing Debian sysroot.
**Spec:** ../specs/2026-11-15-panda-adapter-sdk.md

## Global Constraints

Preserve3878basefiles/299pins/10originals/main/Drafts102–111/8nativehistories. Samecheckout/inline/noquestions, ownDraft only; no main/shared-base/Cloud publication/request reuse. No actual Panda/GL/provider/MetaDrive/model/officialORT/native SDK loading/execution. Necessary CPU build generators and fake originals only. Nativeallowance0/strict0of4FAIL/Stage7INCOMPLETE. Source1GiB/30000members,manifest16MiB;build8GiB/log32MiB/900s/4threads;CPUcompile30s/scenario10s/log1MiB. No capture arming/autoinstall/GLquery/globalinstall/image replacement/runtime or coverage admission. One review/oneImportant-CriticalTDDfixpass/no rereview/minor polish.

## Review Focus

1. Exactly one source/runtime instance and required same-image definitions; hidden read tail still binds original GL import, no self-contained duplicate runtime/weak missing-activity fallback.
2. Source graph reconstructs exact upstream tree, immutable C/C++ inputs retain language/ABI and visibility; flags or extra files cannot silently compile unpinned code.
3. Source/dependency/tool/actual output binding and interrupted/failed build limits cannot produce a success receipt while children run or objects drift.
4. ELF export/import/dynamic checks derive from real bounded data/tool output and reject missing/undefined/changed symbols without loading real SDK or trusting supplied ready flags.
5. CPU shared-library bootstrap/lifecycle/PBO/lookup/errors/originals/errno/register behavior must match source ownership and never inflate CPU/link proof into actual renderer/image/native admission.

### Task1: Exact source/build graph integration

**Create:** scripts/panda_adapter_sdk_stage.py;tests/test_panda_adapter_sdk_stage.py; pinned makepanda source fixture in evidence.
**Interfaces:** transform(sources4,makepanda_bytes)->(changed4,changed_build,manifest);stage(upstream,dest)->dict;verify_stage(stage)->dict. Consume immutable4source transformer and9native pins, output baseline+new complete manifests.

- [x] RED pinned source/build mutation, target graph C/C++/NOHIDDEN/link inputs, exact include and changed count, foreign/existing/malformed source stage rejection. Execute only isolated CPU target-graph snippet, not full SDK code.
- [x] Implement minimal exact anchors/native copy/fresh stage/full upstream-tree reconstruction; focusedPASS and actual full source stage; record/commit.

### Task2: Constrained actual builder and static/CPU linkage

**Create:** scripts/build_panda_adapter_sdk.py;tests/test_panda_adapter_sdk_build.py;tests/test_panda_adapter_sdk_cpu.py.
**Interfaces:** build(stage,sysroot,out,threads=4)->dict;inspect_sdk(image,out)->dict;required_exports()/elf data parsers. Fixed compile/link/inspect commands with real receipts, no renderer.

- [ ] RED bad/partial/ready inputs/output/limits; required same-image symbol absence and actual old-runtime-without-activity strong-link rejection; CPU-only shared SDK bootstrap/lifetime/deletes/pending/errno/tail cases.
- [ ] Implement builder/ELF controls; actual fresh makepanda build with strict unresolved-symbol rejection and source/dependency/tool checks; preserve failures. CPU normal/sanitized50cases each; focused then fullsuite.
- [ ] One fresh whole-branch review; all rulings/declined costs, one Important/Critical TDDfixpass+fullsuite/no rereview; source/output/proof preservation and own scratch copy/removal; commit.
- Final immutable-head operation: ownDraft, exactHEAD workflow411705464 push+pull_request4jobs/attempt1/SUCCESS/artifacts0, fresh3878/299/10/oldrefs/histories/body roundtrip and retained final receipt. No main/sharedbase merge/publication.
