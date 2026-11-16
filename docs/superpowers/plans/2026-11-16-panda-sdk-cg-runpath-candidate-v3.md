# Source-bound Cg/Eigen RUNPATH v3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline in the existing checkout. One fresh wholebranch reviewer at the end, no implementer delegation. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce one separately authenticated Cg/Eigen compile-only candidate whose actual ELF RUNPATH declares `$ORIGIN`, then apply unchanged necessary layout/root-symbol checks.

**Architecture:** A new guarded measured builder retains all Eigen v2 facts and appends one exact link-environment constant. New gate/evidence checks inspect actual root and build-libpanda RUNPATH, then reuse immutable pure static primitives. Separately named request/workflow/consumer preserves all consumed sources/verdicts and never executes target code.

**Tech Stack:** Python stdlib,bounded ELF/ZIP helpers,GCC13/makepanda,ubuntu24.04; CPU-only handwritten fixtures locally.

**Spec:** ../specs/2026-11-16-panda-sdk-cg-runpath-design.md

## Global Constraints

This saved plan is not an active request. Future execution starts a new own feature/panda-sdk-cg-runpath-candidate-v3 branch from the completed design Draft; preserve all7603base files/modes plus this design's added files. Same checkout/inline/no repeated questions/own Draft preference persists.

No SDK/Panda/GL/Xvfb/target/officialmodel/ORT/cohort execution,ELF patching,image operations,oldrequest replay,publication,shared-base/main update or merge. Preserve299v2source identities,282older identities,299olderpins,10originals,31siblingtrees/3846hashes,main,Drafts102–125,native8/image3/mapping/dispatch/realGLX/Cgbuild01/Eigenbuild02. Root strong availability is not full provider closure, full ABI, crash repair or runtime authority. Scientific0/strict0of4FAIL/Stage7INCOMPLETE.

Source470e352/routes-v2/ABI0/float32/explicitgcc13/Eigen3.4.0 exact530headers/two workers unchanged. Future one SDK start,1200sSDK+descriptor/2400stotal,8GiBoutput/12GiBworkspace/16GiBinitialfree/32MiBlogs/256MiBcarrier/45minjob. No retry/fallback. Exact23file carrier unchanged. Fresh owned tool/input measurements and exact dependency origins remain required; only handwritten CPU fixtures may compile locally and are never loaded/executed.

New files: scripts/build_panda_sdk_cg_runpath.py (owned build),panda_sdk_cg_runpath_gate.py (actual tags/necessary static gate),panda_sdk_cg_runpath_evidence.py (report coherence),panda_sdk_cg_runpath_policy.py (authority),panda_sdk_cg_runpath_carrier.py (closed transport),produce_panda_sdk_cg_runpath.py,accept_panda_sdk_cg_runpath.py;workflow .github/workflows/panda-sdk-cg-runpath-build-v3.yml. All old source stays immutable. Future source map is frozen299 plus contract.future.source_closure_extra_files exactly11 =310identities.

## Review Focus

1. makepanda shell expansion/empty ORIGIN/contradictory linker options cannot substitute an absolute or empty path for literal `$ORIGIN`; actual root and retained build-libpanda tags both bind (Task1/2).
2. Root RUNPATH is not transitive: CgGL→Cg must use the immutable provider's own observed RPATH; no global package fallback or Inventory override is allowed (Task2).
3. Root symbols available while six provider-level audits block must not certify full dependency closure/runtime/SIGABRT repair; all diagnostic rows survive (Task2/3).
4. New wrappers must not call v2 guarded entrypoints or keep v2 owned work paths/source-CI/request/run bindings; all reports and four retained candidates bind to v3 (Task1/2/3).
5. Nonzero/timeout tool queries, failed SDK/layout/postcheck or asymmetric maximum logs preserve structured receipts and bounded diagnostics; failure never grants another start (Task3).

---

### Task1: New measured RUNPATH builder and link provenance

**Files:** Create scripts/build_panda_sdk_cg_runpath.py,tests/test_build_panda_sdk_cg_runpath.py. Read build_panda_sdk_cg_eigen.py and pinned makepanda.py/makepandacore.py without editing them.

**Interfaces:** build_environment(private:Path)->dict; build(stage:Path,qualified_cg:dict,qualified_eigen:dict,out:Path,tools:dict)->dict. Neutral compile facts retain status CG_EIGEN_SDK_COMPILED_NOT_LOADED; new schema panda-sdk-cg-runpath-build-v3 and fields runpath_contract_sha256,link_environment,link_commands. compile_layout(sdk_include:Path,qualified_inputs:dict,out:Path,tool_profile:dict,deadline:float)->dict owns the v3 guard/lifecycle and returns the same compiler-bound parent/raw/effective-config facts.

- [ ] Write tests test_exact_quoted_origin_environment and test_cpu_link_emits_runpath_with_origin_unset_and_spoofed. Assert environment equals immutable base environment except exact LDFLAGS `-Wl,-z,defs -Wl,--enable-new-dtags,-rpath,'$ORIGIN'`. Two inert CPU ELF links through the same shell interpretation, ORIGIN empty or EXPANSION_SENTINEL, both have DT_RUNPATH exactly `$ORIGIN`, DT_RPATH absent; never load/execute outputs. Unquoted,absolute,empty,list,duplicate/disable-new-dtags mutations reject.
- [ ] Write test_v3_guard_deadline_and_failed_command_evidence: reject v2 branch/local entry; v2 build/compile_layout sentinels must never be called. New branch prepare/panda-sdk-cg-runpath-build-20261116-03,attempt1,owned build latch. Failed preflight/nonzero/timeout/layout and exhausted shared deadline retain argv/return/timing/streams/reaping before raising; do not run SDK locally.
- [ ] Run `python -B -m unittest discover -s tests -p test_build_panda_sdk_cg_runpath.py -v`. Expected RED missing module/functions.
- [ ] Implement the v3 owned builder using only unchanged pure v2 measurement/process/qualifier/literal helpers. Copy guarded orchestration where necessary; never monkeypatch v2 globals. Preserve all actual source/private/tool/config/compile-dependency/descriptor checks and the shared1200s deadline. Capture the exact link environment before SDK start; parse actual root and build-libpanda link argv from makepanda stdout, require exactly one literal-origin option/enable-new-dtags/-z,defs and no contradictory tag option. Global LDFLAGS affects all linked SDK outputs; bind complete output manifest and both retained ELF identities.
- [ ] Run same test. Expected GREEN, CPU fixture DATA only. Commit.

### Task2: Actual RUNPATH gate and independent report coherence

**Files:** Create scripts/panda_sdk_cg_runpath_gate.py,scripts/panda_sdk_cg_runpath_evidence.py,tests/test_panda_sdk_cg_runpath_gate.py,tests/test_panda_sdk_cg_runpath_evidence.py. Reuse unchanged descriptor native/panda_sdk_cg_v2/layout_contract.cxx and pure v2 audit/parser helpers.

**Interfaces:** validate_runpath(candidate:bytes,build_panda:bytes)->dict requires both actual tags; audit_candidate(candidate:Path,parent:Path,descriptor:Path,build_panda:Path,build:dict,providers:dict[str,Path])->dict; validate_build_evidence(receipt:dict,bundle:Path)->dict rebinds all retained artifacts/reports to v3 roots/contract.

- [ ] Write test_actual_tags_required_for_both_retained_elfs: `$ORIGIN` RUNPATH and absent RPATH on each pass tag predicate only; null,empty,colon-list,absolute,${ORIGIN},escaped-dollar,duplicate-tag,DT_RPATH-only or JSON-only claims reject. Consumed SDK2 bytes reject unchanged despite matching selected layout. Reject a substituted build-libpanda even if producer file-map hash is updated.
- [ ] Write test_frozen_selector_uses_each_object_own_paths: new root bytes with RUNPATH resolve exact pinned Cg/CgGL; CgGL→Cg uses its own RPATH=$ORIGIN. A synthetic child with no own search path must reject a dependency found only in the root RUNPATH. No extra requester/name/global package exception. Wrong Cg hash/SONAME,missingstrong import or altered weak set rejects.
- [ ] Write test_selected_success_does_not_promote_provider_diagnostics: retain all provider-level strict missing rows; success remains only necessary selected-layout/root-availability evidence. full_dependency_closure_qualified/full_object_abi_qualified/runtime_mapping_qualified/previous_abort_fixed/candidate_installed/native_admitted/stage7_complete all False. Unknown wheel facts/default-off stay unknown.
- [ ] Write test_v3_report_contradictions with a success-shaped CPU fixture: old v2 owned root/source/contract,wrongenvironment/linkargv,tool/source/private/Eigen/.d/output/candidatehash/parent/raw contradictions reject one at a time, even after receipt file-map updates. Ensure actual four candidate hashes match compiler/output receipts. No remote host tool/header remeasurement claim.
- [ ] Run `python -B -m unittest discover -s tests -p '*panda_sdk_cg_runpath*.py' -v`. Expected RED missing gate/evidence.
- [ ] Implement bounded actual-tag/contract/environment/link-argv checks and independent v3 evidence validation. After new facts pass, call only pure immutable v2 audit_candidate on actual bytes/build facts/current provider DATA with the original Inventory selector. New success CG_EIGEN_RUNPATH_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME; all other predicates remain mandatory. New evidence validator uses v3 producer/work roots, pinned unchanged source manifest/native descriptor and pre/post tool/source/input/output/dependency relationships; never call v2 validator with its hardcoded SDK2 root or reinterpret its request.
- [ ] Run same tests. Expected GREEN; DATA-only consumed SDK2 negative stays negative. Commit.

### Task3: Separate one-use production, acceptance and exact closeout

**Files:** Create scripts/panda_sdk_cg_runpath_policy.py,scripts/panda_sdk_cg_runpath_carrier.py,scripts/produce_panda_sdk_cg_runpath.py,scripts/accept_panda_sdk_cg_runpath.py,.github/workflows/panda-sdk-cg-runpath-build-v3.yml,tests/test_panda_sdk_cg_runpath_flow.py,new own result/ledger/evidence paths. Never edit old workflow/request/results.

**Interfaces:** request_template(source_sha:str,source_ci:list,root:Path)->dict; run_production(out:Path|None)->dict calls Task1/2 at most one SDK start; accept_build(source:str,activation:str,run_id:int,out:Path)->dict authenticates new origin and recomputes Task2 checks. Carrier API extract_carrier(zip:Path,out:Path)->dict supplies closed member hashes/omissions only, never authority.

- [ ] Write tests for exact contract.future names/310source identities,request-only child,canonical source CI2events/4jobs/attempt1/artifacts0,one new run/job/artifact/attempt1 and create-only start latch. Any old SDK2 identity,changedpermission/header/budget/closure,secondrun,retry,source substitution or unlisted member rejects. Current saved design grants no active request.
- [ ] Write durable negative tests: failed owned query/compile/layout/postcheck/entrypoint,partial oversized file,short stdout with maxstderr,multiple command profiles. Bound each log16MiB and combined32MiB; preserve command-first metadata/available streams and explicit truncation/omissions. Exact23file success/26maxentries/65536centraldirectory and four candidates bind; raw128B exact. New link environment/argv live in existing receipt/gate JSON, no extra member.
- [ ] Run `python -B -m unittest discover -s tests -p '*panda_sdk_cg_runpath*.py' -v`. Expected RED missing policy/producer/consumer/carrier.
- [ ] Implement new namespaces/guards/closed carrier/workflow with contract.future values. Compile-only permissions/read-onlycontents+actions/pinnedcheckout+upload/ubuntu24.04/45min/attempt1/alwaysoneartifact. Producer and independent consumer use Task2 on actual root/buildPanda/parent/raw/current-image DATA; status and request metadata alone never qualify. Preserve neutral compile facts while namespacing new production/acceptance statuses and contract SHA.
- [ ] Run focused and complete unmodified tests. Expected GREEN with actual counts; use genuine spacious-shm capacity case arrangement when needed, no fake capacity or oldtest edits. One fresh wholebranch review, one Critical/Important RED→GREEN pass/fullgreen suite, defer Minors/no rereview. Preserve all baseline files/pins/histories before source CI.
- [ ] Push own Draft; exact reviewed-source canonical CI4jobs/attempt1/artifacts0 must pass. Only then create one fresh request-only child/ref for prepare/panda-sdk-cg-runpath-build-20261116-03 and observe one hosted build/attempt1. Expected outcome is an observed positive OR retained negative, never presumed success. No retry if preflight/compile/static gate fails.
- [ ] Independently accept exact request/source/run/job/artifact/TLS/closed bytes and recompute actual RUNPATH/layout/config/source/tools/dependencies/providers/root availability. Preserve raw candidate/ZIP/provider DATA output-only with exact proof index and compact Git reports/logs. Failure closes slot, never relaxes consumed gates or grants target execution.
- [ ] Close with actual result,all rulings/costs/deferredMinors,own scratch archive/removal,31sibling preservation,final docs-only HEAD CI4jobs and outside-commit receipt. Expected clean checkout/exactremoteHEAD/ownDraftunmerged/mainandpriorDraftsunchanged; scientific0/strict0of4FAIL/Stage7INCOMPLETE even on static success.

## Self-review

Source299+11closed paths=310; builder neutral compile-fact fields remain valid input to pure v2 gate while new runpath/origin checks bind v3. Environment/global-output scope and both retained ELF checks align. Root RUNPATH is not propagated to children; observed CgGL RPATH supplies its own edge. All five Review Focus cases own explicit tests. Provider-level failures, full ABI, actual emitted tags and runtime behavior remain separate unknowns; no consumed result changes. This plan is shorter than its combined builder/gate/authority implementation and leaves ordinary code structure to the implementer.
