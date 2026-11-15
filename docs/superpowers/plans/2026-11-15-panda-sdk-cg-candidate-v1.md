# Cg-aware SDK Candidate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task, inline in the existing checkout. One fresh wholebranch reviewer at the end; no implementer delegation. Steps use checkbox syntax.

**Goal:** Produce one separately authenticated Cg-aware SDK build artifact that passes necessary static member-layout checks, without target execution or image replacement.

**Architecture:** Closed input qualification → separately versioned measured build → compile-only layout descriptor and bounded static gate → one build-only hosted authority/receipt. A static pass feeds a separate future image contract, never a runtime window.

**Tech Stack:** Python stdlib,existing bounded ELF/provider helpers,GCC13/makepanda,readelf/objdump,GitHub Actions ubuntu-24.04; no SDK/Panda/GL/Xvfb execution.

**Spec:** ../specs/2026-11-15-panda-sdk-cg-repair-design.md

## Global Constraints

All7087basefiles/modes at4b68ddd,299pins,10originals,main,Drafts102–121,native8/image3/mapping01/dispatch01/realGLX01 remain immutable. New production files extend the new source closure; preserve every existing260file identity without asserting that old glob-based closure counts stay260 after additions. Never reactivate/revalidate old requests against a new source head.

Source470e352, ABI0, explicitgcc13/g++13,new per-build tool profile; only the two pinned NVIDIA headers and current-image Cg providers. No oldsysroot/header/image modification or header stubs. One qualified build start,2workers,1200scompile/2400stotal,8GiBoutput/12GiBworkspace/16GiBinitialfree/32MiBlogs/256MiBcarrier. No target/probe execution or SDK/Panda/GL/Xvfb/model/ORT/cohort/image/publication/merge. Failure retains diagnostics, no retry.

## Review Focus

1. Parser-inc headers, Trace/toolkit DSOs, symlink/path substitution or host Cg fallback must never qualify as pinned image providers (Task1test).
2. Old headers/source/tool profiles or compiler-subtool drift must fail before a success record, including preflight failures with no compiler process (Task2test).
3. Forged layout JSON or descriptor agreeing while executable getters retain old offsets must reject; symbol/ELF extents and unknown instruction forms fail closed (Task3test).
4. Compile success, same revision/vtable width or root symbol availability must not imply full object ABI, crash repair, image installation or runtime authority (Task3test).
5. Failed/timeout jobs, reused request/run attempts, substituted carrier members or truncated logs must retain negative evidence and never consume/open a native window (Task4test).

---

### Task1: Closed Cg/source/provider input qualification

**Files:** Create scripts/panda_sdk_cg_inputs.py,tests/test_panda_sdk_cg_inputs.py,docs/evidence/panda-sdk-cg-candidate-01/inputs.json. Read only existing source/image authorities and docs/evidence/panda-sdk-cg-design-01/contract.json.

**Interfaces:** qualify_inputs(archive:Path,image_authority:Path,provider_data:dict[str,Path],out:Path)->dict writes a new private input tree and manifest. Returns schema/status,header/provider records,original authority hashes and explicit target_execution=False. Consumed by Task2; it cannot grant external artifact origin.

- [ ] Write test_exact_header_and_image_provider_selection: valid pinned inputs yield exactly Cg/cg.h,Cg/cgGL.h and the two image DSOs; fake parser-inc, Trace or toolkit whole-file hashes, unsafe names/links/duplicates and forged authority reject. Use small synthetic pinned fixtures for parser tests; actual pinned input acceptance is a DATA-only integration check, not mocked external provenance.
- [ ] Run `python -B -m unittest tests.test_panda_sdk_cg_inputs -v`; expected RED missing module/function.
- [ ] Implement closed TAR32MiB/inflated512MiB/20000member/1MiBselectedheader bounds and exact pins from contract; create-only out, no old tree writes. Validate existing image authority/inventory bytes and canonical provider membership. Record aliases and classify source/generated/private/host origins separately.
- [ ] Run the same tests; expected GREEN. Run actual input qualification on retained archive/provider DATA; expected pinned header digests and both current-image DSO digests, nativeFalse.
- [ ] Commit new qualifier/tests/evidence; no other runtime files change.

### Task2: Measured isolated-output build and compile-only descriptor

**Files:** Create scripts/build_panda_sdk_cg.py,native/panda_sdk_cg_v1/layout_contract.cxx,tests/test_build_panda_sdk_cg.py. Reuse unchanged source staging/ELF/dependency parsing primitives; never call the old GCC14-pinned build/profile entrypoint.

**Interfaces:** build(stage:Path,inputs:dict,out:Path,tool_profile:dict)->dict; compile_layout(sdk_include:Path,inputs:dict,out:Path,tool_profile:dict)->dict. Both preserve structured failed receipts. Task4supplies verified hosted context; Task3consumes candidate/descriptor paths and build manifest.

- [ ] Write test_cg_command_and_dependency_closure asserting --use-nvidiacg plus all four custom nvidiacg/cggl path options, ABI0/MD exactlyonce,2workers and originalsource identities; silent Cg disable, wrongcompiler, injected MAKEPANDA/RPM flags, host-header drift, missing tool, failed spawn and timeout reject with argv/preflight/return-or-exception/timing/log/owned-cleanup fields.
- [ ] Run `python -B -m unittest tests.test_build_panda_sdk_cg -v`; expected RED missing builder.
- [ ] Implement new gcc13/profile discovery and allowlisted environment. Capture source/private/tool/subtool/header inputs before; validate actual dependency files and used-input identities afterward. Use create-only output, recorded before-start latch and owned subprocess group; no implicit package install/fallback/rebuild.
- [ ] Add compile-only .panda_cg_layout descriptor per spec, using real generated glgsg.h/shader.h and probe-only -fno-access-control/-Wno-invalid-offsetof. Emit only data; -c only. Tests use a handwritten CPU layout type to verify capture/never-execute behavior. Do not load real SDK in tests.
- [ ] Run the same tests; expected GREEN, including every negative structured receipt. Commit builder/probe/tests; actual full target build remains deferred to Task4's authenticated slot.

### Task3: Necessary static member-layout and link gate

**Files:** Create scripts/panda_sdk_cg_static_gate.py,tests/test_panda_sdk_cg_static_gate.py. Reuse scripts/panda_sdk_link_elf.py/readback_process_mapping.py and image-provider selection without altering them.

**Interfaces:** audit_candidate(candidate:Path,layout_object:Path,build:dict,reference:Path,providers:dict[str,Path])->dict. Returns status CG_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME only after all spec predicates; otherwise STATIC_CG_CANDIDATE_REJECTED with reasons and native_admitted=False. Task4binds this output to authenticated compiler/carrier origin.

- [ ] Write test_old_and_forged_offsets_reject: old0x618/0x61c/0x600 reject; new0x688/0x68c/0x670 plus matching descriptor accepted only with all other supplied facts. Changed descriptor with old getter bytes, unknown machine instruction, truncated/overflow/ambiguous dynamic symbol spans and executable/init-array layout objects reject.
- [ ] Write test_no_runtime_promotion: candidate status never asserts full ABI/crash fix/installed image/runtime admission, even with equal revision/vtable1024 and all strong imports available. Changed Cg provider, missing API/state duplicate, unlisted weak exception or unqualified dependencies reject.
- [ ] Run `python -B -m unittest tests.test_panda_sdk_cg_static_gate -v`; expected RED missing gate.
- [ ] Implement bounded ELF-backed getters/descriptor checks and all spec static predicates. Existing ad-hoc .py.data investigation recipes are references only. Retain candidate sizes/macros/version diagnostics and unknown wheel configuration facts; infer no absent wheel sizes.
- [ ] Run the same tests; expected GREEN. Run gate against retained OLD SDK/reference as DATA; expected rejection with the three known offset mismatches. Commit gate/tests/negative evidence.

### Task4: One build-only hosted authority and truthful closeout

**Files:** Create scripts/panda_sdk_cg_build_policy.py,scripts/produce_panda_sdk_cg.py,scripts/accept_panda_sdk_cg.py,.github/workflows/panda-sdk-cg-build-v1.yml,tests/test_panda_sdk_cg_build_flow.py,docs/STAGE7_PANDA_SDK_CG_CANDIDATE_RESULT.md. Request path is docs/requests/panda-sdk-cg-build-20261115-01.json; prepare branch prepare/panda-sdk-cg-build-20261115-01. Version identifiers are new and cannot alias consumed histories.

**Interfaces:** request_template(source_sha:str,source_ci:list,root:Path)->dict binds extended closure and exact contract/pins/budgets/compile-only permissions. produce(request:dict,out:Path)->dict calls Tasks1–3 once. accept(source_sha:str,activation_sha:str,run_id:int,out:Path)->dict authenticates live API/TLS/closed carrier and distinguishes compiler-origin authentication from static semantic outcome.

- [ ] Write test_closed_build_only_authority covering exactlytwo canonical sourceCI events/four successful jobs/attempt1/artifacts0, request-only activation, unique prepare run/job/artifact and buildstart≤1. Altered source/image/header/budget/permissions, retry/second workflow run, native/Panda/GL/image capability or forged/truncated carrier rejects. Negative origin-authenticated receipts never assert static success or requested default-off as observed facts.
- [ ] Run `python -B -m unittest tests.test_panda_sdk_cg_build_flow -v`; expected RED missing host/policy/acceptor.
- [ ] Implement read-only contents permissions, ubuntu-24.04,45minute job, pinned checkout/upload actions, always-upload bounded build receipt/logs. No Docker or target start. Transfer current image/source artifacts as DATA and validate all pinned bytes before tool/build preflight. Implement the exact success carrier/failed omission contract from the spec and independently recompute Task3 from received candidate/object bytes plus authenticated providers. Missing tools/resources produce BLOCKED before latch; compile/gate failures consume one start and preserve evidence.
- [ ] Run focused tests and the full unmodified suite; expected GREEN. Record actual count instead of copying1711. Keep the existing real spacious-shm capacity-test arrangement if the local sandbox still requires it; hosted full suite remains mandatory.
- [ ] Perform ONE fresh wholebranch review, ONE Critical/Important TDD fix pass if required; defer Minor findings, no rereview. Verify no existing260source bytes, old native trees/authorities, references or originals changed. Create own Draft; canonical reviewed-source CI4jobs pass.
- [ ] Create the new request-only activation ONCE; observe one hosted build and independently accept source/CI/run/job/artifact/carrier plus actual candidate bytes. A mismatch/failure is retained; no retry, image prep or runtime fallback. The old realGLX01 remains consumed and unchanged.
- [ ] Write actual candidate result/continuation/evidence, archive/remove only this plan's scratch and collect exhaustive rulings/deferred minors. Final docs-only commit/exactHEAD CI4jobs/attempt1/artifacts0/body/fresh preservation/clean tree/output receipt. No image or SDK replacement. A static pass ends this plan; subsequent image/runtime work needs a separate contract.

## Self-review and handoff

Inputs→build→descriptor/gate→external acceptance signatures and required fields align. Each of five Review Focus cases has an owning negative test. Full wheel flags, complete C++ ABI, previous abort cause and actual Panda object behavior remain explicitly outside static success. This is the next implementation plan, not evidence it has run. User's inline/noquestions preference persists; do not reopen an execution-method menu.
