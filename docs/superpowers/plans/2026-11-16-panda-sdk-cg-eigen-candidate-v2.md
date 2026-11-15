# Eigen-aligned Cg SDK v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task inline in the existing checkout. One fresh wholebranch reviewer at the end, no implementer delegation. Steps use checkbox syntax.

**Goal:** Build one separately authenticated Cg+Eigen SDK candidate with effective16-byte vector alignment and a necessary byte-backed static gate; never execute target code.

**Architecture:** Closed Eigen/NVIDIA/current-image inputs → new measured builder and parent-object/raw128B descriptor extraction → CET-complete static gate → versioned one-use hosted authority and independent acceptance. All old source/requests/results remain immutable.

**Tech Stack:** Python stdlib,bounded ELF/ZIP helpers,GCC13/makepanda,readelf/objdump;ubuntu-24.04 compile-only.

**Spec:** ../specs/2026-11-16-panda-sdk-cg-eigen-design.md

## Global Constraints

No SDK/Panda/GL/Xvfb/target/model/officialORT/cohort execution,image operations,oldrequest replay,publication or main/shared-base update/merge. Preserve7325base files/modes at912c50b,282source identities,299olderpins,10originals,main,Drafts102–123,native8/image3/mapping/dispatch/realGLX/Cgbuild01 and31sibling trees/3846hashes. Current task is design-only; future execution starts a new own branch from its completed design Draft without modifying the base.

Source470e352/ABI0/float32/explicitgcc13;fresh per-build tools/subtool selection checks,private headers/providers,exact .d origins. One new build start,two workers,1200scompile/2400stotal,8GiBoutput/12GiBworkspace/16GiBinitialfree/32MiBlogs/256MiBcarrier,45minjob. Failures retained,no retry/fallback. Static success never means full ABI/crash repair/installed image/runtime readiness;scientific0/strict0of4FAIL/Stage7INCOMPLETE.

## Review Focus

1. Generated LINMATH_ALIGN=1 with HAVE_EIGEN absent must not count as effective16-byte alignment; host Eigen fallback and changed private headers reject (Task1/2).
2. Descriptor parent initializer code is never loaded; only the unique read-only128B relocation-free section can be extracted; forged relocation sh_info, section aliases or JSON/raw substitutions reject (Task2).
3. CET prefix support must not accept extra instructions, IFUNC, decoy vendor loads or arbitrary copy-call targets; consumed build01 remains incompatible (Task3).
4. Matching three offsets/revision/vtable cannot promote partial link diagnostics to complete ABI, prior SIGABRT repair or runtime authority (Task3).
5. A failed extraction/tool/deadline or partial oversized carrier retains structured commands and bounded diagnostic bytes; source/run/request retry/substitution never grants another slot (Task4).

---

### Task1: Exact Eigen header qualification

**Files:** Create scripts/panda_sdk_cg_eigen_inputs.py,tests/test_panda_sdk_cg_eigen_inputs.py; reuse frozen docs/evidence/panda-sdk-cg-residual-01/libeigen3-dev_3.4.0-4_all.deb.data,eigen-input.json,eigen-header-manifest.json,contract.json. Read old panda_sdk_cg_inputs helpers without editing them.

**Interfaces:** qualify_eigen(package:Path,private_root:Path)->dict stages exactly530files/8669561B under a fresh qualified Cg private root, returns schema/status/package pin/version/file records/staged root/target_execution=False. Task2 consumes this alongside the genuine Cg/current-provider manifest.

- [ ] Write test_exact_pinned_eigen_headers: exact archive1040780B/SHA1a167bb381acb90c1d8450a8f3e66a09d216dbc64b33ac8a082a0912513ef939,530exact header names/digests/version3.4.0; lapacke.h1058369B accepted under2MiB, no CMake/pkgconfig/runtime/package-script files staged. Synthetic parser negatives cover >4MiB package/>32MiBinflation/>2048members/>2MiBheader,links/traversal/duplicates/missing header/wrong version/host aliases and existing-output collisions; no old root writes.
- [ ] Run `python -B -m unittest discover -s tests -p test_panda_sdk_cg_eigen_inputs.py -v`; expected RED missing module.
- [ ] Implement closed ar/data.tar.xz parsing and manifest-bound membership, create-only owned header writes; verify generated effective expectations are future measurements, never asserted from the archive alone.
- [ ] Run same test; expected GREEN. Run actual archive qualification into a new DATA-only root; expected530matches and no installation/execution. Commit.

### Task2: Measured Eigen-aware builder and section-only descriptor

**Files:** Create scripts/build_panda_sdk_cg_eigen.py,scripts/panda_sdk_cg_eigen_layout.py,native/panda_sdk_cg_v2/layout_contract.cxx,tests/test_build_panda_sdk_cg_eigen.py,tests/test_panda_sdk_cg_eigen_layout.py. Old builder/staging/scripts remain immutable.

**Interfaces:** build(stage:Path,qualified_cg:dict,qualified_eigen:dict,out:Path,tools:dict)->dict preserves positive/negative structured receipts. extract_literal(parent:bytes)->dict returns exact raw128bytes,section facts,parent/section SHA and target_execution=False; validate_descriptor(raw:bytes)->dict returns measured fields/offsets without origin/runtime authority. Task3 consumes candidate+parent+raw+build facts.

- [ ] Write test_eigen_command_and_effective_alignment: --use-eigen/--eigen-incdir private/eigen3 plus all prior Cg/GL/X11 flags,ABI0/MD once,two workers. Generated HAVE_EIGEN/HAVE_CG/HAVE_X11 true,Python/double false; effective guard must reject LINMATH_ALIGN generated1 but undefined by dtoolbase, alignof(LVecBase4f)!=16 or memory alignment!=16. Changed selected tool/query/input and host Eigen .d origin reject; failed preflight/owned spawn/timeout/layout compile saves argv/return/timing/reaping before success checks. Use only handwritten CPU fixtures locally.
- [ ] Write test_parent_init_is_data_but_selected_relocation_rejects: handwritten CPU ET_REL parent may contain an unrelated initializer, never loaded; unique read-only .panda_cg_layout_v2 exact128B extracts verbatim. Wrong magic/version/flags/length,duplicate/overlap/truncated sections,selected REL/RELA with forged sh_info and parent/raw byte substitution reject. Descriptor flag facts never grant origin or static admission.
- [ ] Run both modules via unittest discover; expected RED missing modules/functions.
- [ ] Implement new guarded Actions entry and build command. Reuse only unchanged pure measurement/process/source/input helpers; old build/compile_layout entrypoints bind old branch/flags and MUST NOT be called. Fresh private/header/source/tool records before; used deps and selected queries/bytes after. Add Eigen to package argv; reject host Eigen paths. Capture generated/effective config and generated delta without inferring wheel configuration.
- [ ] Implement16word descriptor from real headers: magic0x50414e4441434732,2,8,0,1,four sizes,vendor/major/minor,Eigen1,effective-LINMATH1,vector alignment16,memory alignment16. Probe-only access flags; -c only. Extract exact raw bytes with bounded ELF section/relocation rules; retain whole parent as inert DATA. Compiler guarded assertions, not JSON, prove effective configuration.
- [ ] Run same modules; expected GREEN. Verify a real handwritten CPU parent/raw derivation only; no actual SDK compile locally. Commit.

### Task3: Complete CET-aware necessary static gate

**Files:** Create scripts/panda_sdk_cg_eigen_gate.py,tests/test_panda_sdk_cg_eigen_gate.py. Read frozen libpandagl/build-libpanda/parent DATA from build01 and old reference/provider authorities; edit none.

**Interfaces:** audit_candidate(candidate:Path,parent:Path,descriptor:Path,build:dict,providers:dict[str,Path])->dict. Exact success status CG_EIGEN_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME, otherwise STATIC_CG_EIGEN_CANDIDATE_REJECTED with observed facts/reasons and no runtime/fullABI/crash/install authority.

- [ ] Write test_cet_complete_getters_and_consumed_candidate_rejects: optional exactlyone f30f1efa then exact mov-disp32/ret; both known complete vendor copy bodies and validated import call targets. Extra/truncated prefix,suffix,IFUNC,overlapping/W+X/unbacked symbols,decoy expected then old loads or arbitrary call target reject. Actual build01 supports observation but retains0x678/0x67c/0x660 mismatch; matching descriptor cannot override code.
- [ ] Write test_literal_code_config_link_all_required: byte parent/raw equivalence plus actual build facts/effective Eigen/alignment, offsets0x688/0x68c/0x670,vtable1024,33exports/one state and exact current-image imports/Cg pair/original3weak exceptions are all required. Missing/changed provider,strong import,API/state or unknown feature rejects. Equal offsets/revision/vtable never assert complete ABI/runtime binding/abort fix/image installation; wheel sizes remain unknown.
- [ ] Run `python -B -m unittest discover -s tests -p test_panda_sdk_cg_eigen_gate.py -v`; expected RED.
- [ ] Implement bounded whole-function byte templates and PLT/loader association, independent128B parent extraction plus fixed descriptor validation and existing static provider/API checks. Keep origin separate. Do not use ad-hoc forensic recipes as admission parsers.
- [ ] Run same tests; expected GREEN. DATA-only negative integration on consumed build01 must still reject; this does not revalidate or reopen its request. Commit.

### Task4: New one-use compile-only production and independent acceptance

**Files:** Create scripts/panda_sdk_cg_eigen_policy.py,scripts/panda_sdk_cg_eigen_carrier.py,scripts/produce_panda_sdk_cg_eigen.py,scripts/accept_panda_sdk_cg_eigen.py,.github/workflows/panda-sdk-cg-eigen-build-v2.yml,tests/test_panda_sdk_cg_eigen_flow.py,docs/STAGE7_PANDA_SDK_CG_EIGEN_CANDIDATE_RESULT.md. New request/branch/id are fixed in the spec; no old workflow/request/producer edits.

**Interfaces:** request_template(source_sha:str,source_ci:list,root:Path)->dict extends preserved282source identities with new code/descriptor/Eigen inputs; produce(request:dict,out:Path)->dict calls Tasks1–3 at most one SDK build start; accept(source_sha:str,activation_sha:str,run_id:int,out:Path)->dict authenticates origin independently and recomputes received SDK/parent/raw/gate facts against exact image DATA. Carrier extraction returns closed member hashes/omissions, no authority.

- [ ] Write test_closed_eigen_build_authority: two canonical source CI events/four successful jobs/attempt1/artifacts0,request-only child,new unique run/job/attempt1/artifact. Source/permission/header/budget/branch/closure mutation, reused request/retry/second run, descriptor substitution or unlisted carrier member rejects. Negative observed default-off is None.
- [ ] Write test_durable_negative_eigen_carrier: failed spawn/compile/layout extraction/deadline/postcheck/oversized candidate preserves exact owned command metadata and bounded logs before optional members, with explicit truncation/omissions. Success requires all23closed files with exact paths/limits from contract.success_carrier_file_limits and no other members; failure never opens runtime or retries. Test fake init-bearing parent never loaded.
- [ ] Run focused module; expected RED missing host/policy/carrier/consumer.
- [ ] Implement exact carrier naming/limits from contract.success_carrier_file_limits (23files;≤26entries/65536Bcentral directory), then read-only ubuntu-24.04/45min/pinned action workflow,attempt1 guard,create-only build latch and closed bounds. Four DATA candidates including parent≤1MiB/raw exactly128B;17reports≤16MiB each;2logs≤32MiB combined;ZIP≤256MiB. Producer and independent consumer both validate raw-parent equivalence and actual effective configuration; copied claims alone do not qualify. Always-upload bounded negative diagnostics.
- [ ] Run focused suite and full unmodified tests; expected GREEN, record actual counts, genuine spacious-shm capacity test arrangement if needed. No fake capacity or oldtest edits.
- [ ] One fresh wholebranch review; one Critical/Important RED→GREEN fix pass with green full suite, deferred Minors/no rereview. Preserve all design-base files/modes/pins/authorities/history; own Draft/exact reviewed-source CI4jobs PASS.
- [ ] Create the new request-only ref ONCE, observe one hosted compile-only run, authenticate source/request/CI/job/artifact and independently recompute actual bytes. Any failure is retained and closes this request; no retry/image/native fallback. Never reuse build01.
- [ ] Write actual result/continuation/index; archive/remove only this implementation plan's scratch; exhaustive rulings/deferred Minors. Final docs-only HEAD/exact CI4jobs/attempt1/artifacts0/body/preservation/clean-tree/outside-commit receipt. Old wheel/image/SDK remain unchanged; static pass only feeds a separate future image/runtime contract.

## Self-review

Spec inputs→builder/effective descriptor→whole-code gate→independent carrier acceptance have matching signatures and fields. Five Review Focus lines each own negative tests. Source-alignment diagnosis is not treated as proof that v2 builds/matches; unknown wheel flags/sizes and SIGABRT cause remain unknown. No new build slot is granted by saving this plan; preserve the user's inline/samecheckout preference without reopening an execution-method menu.
