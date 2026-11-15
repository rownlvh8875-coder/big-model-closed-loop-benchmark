# SDK static link repair implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL superpowers:executing-plans; inline same checkout,one fresh wholebranch review,no implementer delegation.

**Goal:** Identify and repair SDK/image dynamic-symbol incompatibility without native loading.
**Architecture:** bounded loader-table ELF inspection + authenticated selected image bytes/provider graph; fixed old-string-ABI rebuild; independent baseline/replacement availability and handoff,allruntime gates false.
**Tech Stack:** Python stdlib,C/C++ compiler fixtures (never loaded),GCC makepanda,existing archive/inventory/tool input guards.
**Spec:** ../specs/2026-11-15-panda-sdk-link-audit-v1.md

## Global Constraints

Basecd919/5950files/299pins/10originals/main/Drafts102–115/8nativehistories/twoimage requests preserved. No actual SDK/Panda/GL/MetaDrive/model/provider/officialORT/loader execution or container starts. Nativeallowance0/strict0of4FAIL/Stage7INCOMPLETE. New files/output only,oldSDK3e9/image0276 immutable. Bounds and explicit provider policy exactly as spec. No main/shared-base update/publication/request replay. RepairedSDK is not installed or mapped; handoff must state remaining gates.

## Review Focus

1. Section spoofing/version/default/hidden/weak/relocation data cannot create a false symbol-availability PASS or runtime authority.
2. Image overlay/whiteout/symlink/path/identity handling must bind exact final authenticated bytes,not similarly named host libraries.
3. Provider graph/search is explicitly scoped; duplicates,interposition/cache/loader namespace and object layout cannot be silently certified.
4. ABI0 flag/environment/dependency/tool closure must bind actual fresh build and source preprocessing,not retrospectively relabel old outputs.
5. Baseline misses/newcandidate handoff must retain old image failure and native gates; malformed/budget failures preserve evidence and cannot promote readiness.

### Task1: Bounded loader symbols and versions
**Create:** scripts/panda_sdk_link_elf.py;tests/test_panda_sdk_link_elf.py.
**Interfaces:** inspect_elf(bytes)->metadata;available_imports(root,providers)->report. Uses PT metadata only;no execution.
- [x] RED compiled CPU old/new stringABI mismatch/default+nondefault versions/weak/symbol metadata corruptions/sectionless fixtures.
- [x] Implement bounded parser and availability,run focused CPU-data tests,record/commit.

### Task2: Authenticated provider extraction and graph audit
**Create:** scripts/panda_sdk_link_image.py;scripts/audit_panda_sdk_link.py;tests/test_panda_sdk_link_image.py.
**Interfaces:** Inventory.resolve(path),SelectedImage.collect(paths)->DATArecords;qualify_image(image,inventory,root_candidate,out)->report.
- [x] RED final-layer replacement/whiteouts/escape/aliases/cycles/hash drift/ambiguous providers/existing-output/budget rejection with real tiny tar fixtures.
- [x] Verify actual image0276 and provider closure,independently audit baseline3e9,retain exact missing symbols/versions and raw byte identities;focusedtests/commit.

### Task3: ABI0 replacement build and complete handoff
**Create:** scripts/build_panda_sdk_link.py;tests/test_panda_sdk_link_build.py;docs/STAGE7_PANDA_SDK_LINK_{RESULT,LEDGER,CONTINUATION}.md;docs/evidence/panda-sdk-link-audit-01/.
**Interfaces:** build_env(sysroot)->fixed env;build(stage,sysroot,out)->receipt;new flags-MD;actual audit+hypothesis evidence and handoff payload.
- [x] RED wrong/ambient ABI/RPM/header flags and output reuse;minimal fixed builder,actual fresh compile/link/input verification/33API/defaultOFF static/source-name qualification; baseline+repair audit.
- [x] Fullsuite/preservation/one fresh review/one Important TDDfixpass;actual final static reports/handoffSDKdata,no runtime/image promotion;clean only own scratch after evidence copy.

**Post-commit closeout:** ownDraft/finalHEAD CI4jobs/attempt1/artifacts0/body/freshpreservation/finalreceipt. Its authoritative result is output/stage7-panda-sdk-link-audit-01/final-verification.json so the final commit identity can be checked without a self-referential tracked receipt.
