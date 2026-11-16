# Source-bound Cg/Eigen RUNPATH candidate v3 design

## Intent, current scope and authority

The user asked to continue the next step identified by SDK2 closeout: a separate DATA-only loader-search contract. This task completes grounded diagnosis, this design and an implementation plan, with own Draft and exact-HEAD CI. It does not implement the future builder, allocate a build slot, reactivate a request, install a candidate or execute target code. Same checkout, inline, no repeated questions and own-Draft preferences persist; executor choices below are delegated choices, not a new user selection.

Authority: `docs/evidence/panda-sdk-cg-loader-search-01/contract.json`. Base6b1730c7cef597381cb3c7ec0d61a16264521b95/Draft125,7603existing files/modes. Preserve all299closed v2 source identities,282older source identities,299older pins,10originals,31sibling scratch trees/3846hashes,main,Drafts102–125,native8/image3/mapping/dispatch/realGLX/Cgbuild01/Eigenbuild02. No shared-base/main update/merge, Cloud/registry/environment publication, SDK/Panda/GL/Xvfb/officialmodel/ORT/cohort execution or image operations. Scientificallowance0/strict0of4FAIL/Stage7INCOMPLETE.

## Grounded observations and limits

SDK2 sourceba64c869c38bd9b1aac138ec81bf98738cda4dc1,activation0150f7dcc41b74660826f0d926eff3b26bdd2fec,workflow419583286/run43777541292/attempt1 compiled once and remains AUTHENTICATED_CG_EIGEN_BUILD_FAILED. Candidate1052968B/SHA332551094adbca1aa12f716ff8798566e522021b62f25c46a66a425873ea1297 has no DT_RPATH or DT_RUNPATH. Code/parent/raw match offsets major0x688/minor0x68c/vendor0x670,vector/memoryalignment16. Independent report coherence verifies4785inputs/101compilercommands/fourretainedartifacts. None changes the consumed negative verdict.

The frozen `Inventory.select` adds the Panda package only for four named Panda dependencies of the root; then it uses each object's own RUNPATH, otherwise RPATH, then fixed system directories. Root Cg/CgGL imports therefore reject, although the exact current-image files exist in the same package. Both immutable Cg providers have SONAME matching their basenames and DT_RPATH=$ORIGIN. CgGL's own Cg edge already resolves through its own RPATH: no transitive inheritance of a proposed root RUNPATH is assumed.

A separate diagnostic explicitly selecting only the root's two pinned Cg dependencies completes22providers/80edges. Root availability is1047resolved/0missing, with exactly `_ITM_deregisterTMCloneTable`, `__gmon_start__`, `_ITM_registerTMCloneTable` weak exceptions and no unsupported feature. A metadata-only hypothesis adding root RUNPATH=$ORIGIN produces the identical edges. Candidate bytes remain unchanged; this is neither an emitted ELF RUNPATH observation nor a new build gate/admission result.

Six provider-level strict audits retain missing rows: Cg13,CgGL5,dtool13,dtoolconfig15,panda48,pandaexpress16. Example: Cg requests pthread_key_create@GLIBC_2.2.5 from libpthread.so.0; libc exports the same version but its SONAME is libc.so.6, so the immutable strict name/version/library matcher excludes it. This demonstrates a matcher boundary, not proof that a real loader will resolve or fail those symbols. Keep every row; do not relax symbol-version rules, certify complete transitive availability, or infer prior SIGABRT repair.

## Approaches and delegated choice

1. **Selected: fresh source-built candidate emitting DT_RUNPATH=$ORIGIN.** Reuse the frozen inventory selector without Cg exceptions. New actual ELF bytes must carry the declared search path; the consumer re-parses them. Costs: a future separately qualified compile-only attempt and new wrappers; it can still fail later predicates.
2. Explicitly map the root's Cg imports as a new static policy. Useful for current conditional diagnosis, but it supplies an external selection assumption absent from the candidate. Retain as diagnostic only; it must not replace an emitted RUNPATH or promote SDK2.
3. Patch SDK2 ELF, set process LD_LIBRARY_PATH/preload, add system aliases or replace the wheel. These change consumed bytes/runtime conditions/image and expand scope. Excluded here; no fallback.

## Source and build environment

Future source470e352ab87ceae6e30429720e4690c8371f5a55/routes-v2,ABI0/float32,explicit gcc13/g++13,two workers,pinned530Eigen3.4.0 headers,genuine NVIDIA headers,private GL/X11/current-image providers remain unchanged. Preserve all consumed source and old guarded entrypoints. New wrappers may reuse only pure measurement/process/input/ELF functions; they cannot call a build/produce/accept entrypoint bound to SDK2's branch or monkeypatch module globals.

The one change to makepanda's link environment is the exact string:

`-Wl,-z,defs -Wl,--enable-new-dtags,-rpath,'$ORIGIN'`

Retain -z,defs. Pinned makepanda.py appends LDFLAGS to its compiler command string; makepandacore.oscmd uses shell=True. The embedded single quotes protect the literal token. Host printf-only probes with ORIGIN empty and ORIGIN=EXPANSION_SENTINEL both retain one linker argument `-Wl,--enable-new-dtags,-rpath,$ORIGIN`; no compiler or target was run. A later CPU-only link fixture must prove actual DT_RUNPATH emission before the SDK build.

LDFLAGS is global to this SDK build, so all its linked SDK libraries receive the flag. Bind the environment before starting and retain the actual root/build-libpanda link argv from makepanda output, with flag cardinality and -z,defs checked. Independently inspect both retained libpandagl and build-libpanda: DT_RUNPATH must equal exactly `$ORIGIN`, DT_RPATH must be absent. Record the global SDK-output effect; frozen image providers and their original RPATHs are never changed. No host/env expansion, empty path, colon list, ${ORIGIN} alternative, absolute/sysroot path, escaped dollar, duplicate/contradictory tag or disable-new-dtags is permitted.

The v3 builder owns its action guard, branch/latch/receipt lifecycle and environment; never monkeypatch the v2 builder's build_environment/action_context. Preserve measured owned queries, pre/post source/private/tool facts, used dependency origins, generated AND effective Eigen/LINMATH/alignment configuration, parent/raw extraction and the shared1200s deadline. A neutral compile-facts schema/status `CG_EIGEN_SDK_COMPILED_NOT_LOADED` may retain its exact meaning; v3 adds bound `runpath_contract_sha256`, `link_environment`, and two actual `link_commands`. The new admission status and origin namespace remain separate.

## Necessary gate and independent consumer

A new runpath gate first validates actual candidate and retained build-libpanda RPATH/RUNPATH, expected source-built environment/argv/byte receipts and contract. It then invokes only the immutable pure v2 audit_candidate on actual bytes/facts/providers. The existing selector now observes the emitted root RUNPATH; there is no Inventory override or manually supplied import map in production/acceptance. Require unchanged offsets,section-only128B descriptor/configuration/Cg pair/1024vtable/33requiredAPIs/one source state/root strong availability and original three weak exceptions. No root missing strong import or unsupported feature is waived.

New gate success is `CG_EIGEN_RUNPATH_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME`. It still leaves full_object_abi_qualified,full_dependency_closure_qualified,runtime_mapping_qualified,previous_abort_fixed,candidate_installed,native_admitted,stage7_complete false. Keep all provider-level strict diagnostics and unknown wheel sizes/flags. SDK2 bytes with null RUNPATH must reject even though their selected layout matches.

A separately versioned evidence validator uses v3 owned paths and source identity, binds all23carrier files, tools/inputs/source/dependencies/output manifests, all4retainedcandidate hashes, and the exact environment/link argv. Its root input tree/descriptor project remain the frozen v2 source; do not retain SDK2's producer/work root accidentally. The producer validates coherence before sealing success; the independent consumer repeats it and re-extracts parent/raw, actual RUNPATH, current-image DATA graph and gate. It authenticates its own source/CI/request/run/job/artifact and never revalidates SDK2's consumed request. Report coherence does not independently remeasure remote host tools/headers.

## Future authority and carrier

Names are frozen by contract.future: feature/panda-sdk-cg-runpath-candidate-v3,prepare/panda-sdk-cg-runpath-build-20261116-03,workflow panda-sdk-cg-runpath-build-v3.yml,request docs/requests/panda-sdk-cg-runpath-build-20261116-03.json,artifact panda-sdk-cg-runpath-build-20261116-03,output stage7-panda-sdk-cg-runpath-candidate-03. No request/ref/workflow is created by this design task.

Future source closure is the exact frozen299map plus the contract's11explicit source/evidence paths =310identities, all recomputed and closed; no dynamic old glob or semantic rewrite of consumed maps. Seven new Python modules separate builder/gate/evidence/policy/carrier/producer/consumer; reuse the immutable v2 descriptor and qualifier. Every imported helper is already included in299.

Future implementation: TDD/full unmodified tests/one fresh wholebranch review/one Critical-Important fix pass/exact reviewed-source push+PR CI4jobs/attempt1/artifacts0 precede a create-only request child and a single new hosted request. The request binds exact repository/owner/source/contract/closure/budget/compile-only permissions; unique run/job/attempt1/artifact and TLS/digest/closed-carrier authentication. One SDK build start, no retry/fallback/reuse. Failure retains available bounded diagnostics and closes its request.

Reuse exact v2 23member names/limits:4DATA candidates,17JSON reports,2logs; optional3directory entries,max26ZIPentries/65536central-directory bytes. New environment/link-command provenance lives inside compiler receipt/gate JSON, so no extra carrier member. Always preserve owned tool/staging/build/layout command return/timing/reaping and bounded stdout/stderr before optional candidates; logs16MiBeach/32MiBcombined,artifact256MiB. ubuntu24.04/read-onlycontents+actions/pinnedcheckout+upload/45min;compile1200s(sharedSDK+descriptor),whole2400s,2workers,8GiBoutput/12GiBworkspace/16GiBinitialfree. Point-in-time measurements, no continuous integrity/reproducibility/cgroup claim. Unknown observer default-off is None. No generated target execution, installation, image preparation/publication or native/scientific promotion.

## Completion and remaining work

This task closes with pinned old artifacts, frozen source299, reproducible DATA controls/hypotheses, provider-level limits, builder-checked design, self-checked plan, old history/file preservation, own Draft, exactHEAD CI4jobs and an output-only final receipt. Actual emitted v3 RUNPATH and all later static predicates remain unobserved until that separate implementation and one-use production task. Existing SDK2 stays failed/consumed; no new build is implied by this document.
