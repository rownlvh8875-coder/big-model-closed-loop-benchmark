# Seven-route SDK and local renderer image implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL superpowers:executing-plans. Inline implementation, one fresh whole-branch review, no implementer delegation.

**Goal:** Implement the seven missing typed routes, build and classify a new SDK, and prepare a full local image containing its bytes without executing native renderer code.
**Architecture:** versioned native9 plus strict source stager/builder/dependency closure; exact selected-source/explicit-name qualification; COPY-only Docker image and stopped-export installed-byte verification. All runtime/native authority remains absent.
**Tech Stack:** C11/C++11/AMD64,Python3.11 stdlib,GCC/binutils/ASan/UBSan,makepanda,private sysroot,Docker data operations.
**Spec:** ../specs/2026-11-15-panda-sdk-routes-v2.md

## Global Constraints

Preserve4951basefiles/299pins/10originals/main/Drafts102–113/8nativehistories. Samecheckout/inline/noquestions/new ownbranch/Draft only; no publication/main/shared-base/request replay. Native/model/officialORT/Panda/GL/MetaDrive/SDK loading0; CPU generators/fake fixtures only. Safe256/slots64/contexts4/events10000 unchanged. Fresh source/build/image outputs; preserve failures. SDK900s/4threads/8GiB/log32MiB; image900s/6GiB/minfree16GiB,load/build/export/save180seach; no Docker START/RUN/PRUNE/shared cleanup. Static/byte/CPU success is not actual runtime/ABI/driver/native admission.

## Review Focus

1. Seven PFN signatures preserve pointer/uint32/ulong64/NULL/errno; malformed targets/displays still call originals once then reject metadata.
2. Draw/read pairs update only after successful current changes, per context; current drawable destruction invalidates observation without changing original GL behavior.
3. Old native/SDK/source/image remain byte-identical; new stage reconstructs exact upstream and C cache/C++ adapter language/linkage; no ambient compiler injection.
4. Real dependency files/source/host/generated/private/tool inputs bind current build and preprocessing; missing/mutated/escaped dependency inputs reject, and current identity is not relabeled historical proof.
5. Explicit252name/computed-source closure and image STOPPED export cannot promote local bytes into runtime or authenticated Actions/native authority; unsafe/unknown names and image extra changes reject.

### Task1: Versioned typed runtime/adapter and CPU regression

**Create:** native/panda_sdk_routes_v2/{panda_source_dispatch.h,panda_source_dispatch.cxx,panda_source_activity.h,panda_source_activity.cxx,panda_cache_adapter.h,panda_cache_adapter.cxx,readback_command_state.h,readback_command_state.c,readback_return_core.h};tests/fixtures/panda_sdk_routes_fixture.cxx;tests/panda_sdk_routes_cpu_support.py;tests/test_panda_sdk_routes.py.
**Interfaces:** existing33psd/pca/rcC APIs unchanged; events15–19 and slots21–27; private per-context draw/read pair, new storage magic. compile_cpu(out,native_dir,sanitize=False)->profile.
- [x] RED actual old runtime fails positive seven-route fixture while originals still forward; wrong target/display/current draw/read destroy, failed switches, NULL/rebind/defaultOFF preserve outcomes.
- [x] Implement only versioned native copies, exact PFN aliases/new arities/counters and adapter rules; normal/sanitized new cases plus old50/defaultOFF; record/commit.

### Task2: Fresh source/SDK with actual input closure

**Create:** scripts/panda_sdk_routes_stage.py; scripts/build_panda_sdk_routes.py; scripts/panda_sdk_routes_inputs.py;tests/test_panda_sdk_routes_build.py.
**Interfaces:** stage(upstream,out)->manifest;verify_stage(out)->manifest;build(stage,sysroot,out,threads=4)->receipt;parse_dependencies(bytes)->paths;capture_host_inputs()->map;qualify_dependencies(files,roots,pins)->closure.
- [ ] RED source/pin/tree drift, dependency escape/missing/mutation, ambient RPM/header injection and existing-output/budget rejection using real CPU fixtures.
- [ ] Implement fresh stager with old manifest retained/upstream reconstruction; controlled-MD build, compiler child/selection and used header/source/generated/private closure; actual build/static inspection, record/commit.

### Task3: Explicit name and computed resolver closure

**Create:** docs/evidence/panda-sdk-routes-02/name-profile.json;scripts/panda_sdk_routes_coverage.py;tests/test_panda_sdk_routes_coverage.py.
**Interfaces:** qualify_selected(selected_sources,runtime,profile)->report;audit_build(build_receipt,out)->report. Consume Task2 actual candidate/source/commands/dependency/tool records, produce selected-name/static-only qualification and CPU safe252 acceptance evidence.
- [ ] RED unclassified/unsafe/257names, changed explicit profile/runtime/forwarding/computed source and mismatched candidate/flags reject; allsevenroutes remove genuine blockers without cap change.
- [ ] Implement explicit semantic252profile and exact forwarding/finite resolver proof, actual new SDK preprocessing and CPU normal/sanitized evidence; record/commit.

### Task4: New full LOCAL image containing SDK bytes and closeout

**Create:** scripts/panda_sdk_routes_image.py;tests/test_panda_sdk_routes_image.py;docs/STAGE7_PANDA_SDK_ROUTES_{RESULT,LEDGER,CONTINUATION}.md;docs/evidence/panda-sdk-routes-02/.
**Interfaces:** inspect_export(tar,expected_manifest,deadline)->inventory;assemble_image(sdk_receipt,coverage,out)->receipt. Original authenticated base archive/manifest, newSDK data and COPY-only recipe produce local image/archive/rootfs/installed-byte evidence. Never start image or grant native authority.
- [ ] RED extra/missing/wrong-mode/hash/link/escape rootfs entries, changed other image files, invalid SDK/coverage or existing outputs reject; fake Docker process boundary verifies output behavior and no activation.
- [ ] Actual bounded base load/COPY build/stopped create/export/byte inspection/save/check; full tests/preservation/proof, one fresh wholebranch review and one Important/Critical TDDfixpass if needed, no rereview/minor polishing.
- Postcommit: ownDraft/exactHEAD push+PR CI4jobs/attempt1/artifacts0/body/fresh preservation/final receipt. No main/Cloud/registry update. Actual native/official/scientific work remains unqualified.
