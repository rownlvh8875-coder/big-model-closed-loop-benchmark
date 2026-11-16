# SDK3 Shader Cache Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline,one fresh wholebranch reviewer,no implementer delegation. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Sequentially fix PSSM matrix reads,validate exact Panda-preprocessed caches,and run one fresh diagnostic.
**Architecture:** New stdlib finite matrix helper and native private adapter;bounded cache preprocessor+newreceiver;newversioneddriver/workflow over unchanged runtime.
**Tech Stack:** Python/unittest/numpy,existingPanda1.10.13/SDK3/Actions.
**Spec:** ../specs/2026-11-17-sdk3-shader-cache-design.md

## Global Constraints

Base1fab41913a864d77a0f78a4f2b1d8fb0021e6745,additionsonly. Onefreshnative/0officialmodel/0inference;600schild/630container/20minjob,2CPU/10GiB/privateIPC/readonlyroot/networknone/uid65534/tmpfs512MiB andsameimage/SDK/core/BaseCamera/reference. No localSDK/Panda/GLX/model/newdependencies/GPUqueries/readback/render/task/shader/sampler/light/clock/setters/environment-registrypublication/mainmerge. Same12sourcepins/256KiBpertext/2MiBtotal/8shaders/40meshes/20sCPU. Known8PSSMnames/numericarrayunavailability;allGPU/hardwareuniform/cause/repair/originalgate/Stage7false,imageSHAexact/CPU1e-9abs1e-12rel. Scope diagnostic/sdk3-shader-cache-20261117-01 and docs/requests/sdk3-shader-cache-20261117-01.json.

## Review Focus

1. Unaligned conversion transposes/aliases or nonfinite owner arrays get admitted: literal16distinctcells and actualsnapshot CPUdoubles in Task1/3.
2. Expected-only preprocessing accidentally normalizes actual cache bytes: rehashedCRLF/code mutations in Task2.
3. Unsupported GLSL syntax is silently misprocessed: block/continuation/quote/directive/NUL/oversize rejection in Task2.
4. Complete without owner data or forged mesh/target/material bindings passes: complete/partial owner and inherited binding negatives in Task3.
5. Private adapters mutate old modules or resource/lifecycle gates: unchangedglobals/entry/importclosure and full inherited regressions in Task3.

### Task1: PSSM unaligned matrix compatibility
**Files:** Create scripts/sdk3_pssm_matrix.py,scripts/sdk3_shader_cache_native.py,tests/test_sdk3_pssm_matrix.py.
**Interfaces:** matrix_rows(core,matrix)->list[list[float]] via core.LMatrix4f conversion;newnative snapshot_shader/core adapter andownedentry overoldnative.
- [ ] RED distinctrow/column non-getCell source,unaltered source,nonfinite,real oldsnapshot complete owner throughCPUdoubles. Expected missingmodule/oldAPI failure.
- [ ] GREEN minimalconvert+finiteguard andprivate snapshot adapter;CPUtestsPASS,commit.

### Task2: exact pinned cache preprocessing
**Files:** Create scripts/sdk3_shader_cache.py,tests/test_sdk3_shader_cache.py.
**Interfaces:** preprocess_cache(source:str)->str;uses strictbounded observedsubset only,never receives actualcache for normalization.
- [ ] RED literalcomments/blanklines/trailingwhitespace/EOF/sourceCRLF,unsupportedblock/continuation/quote/directive/NUL/oversize;all6prioractual cacheSHApositive/code negative. Expected missingmoduleFAIL.
- [ ] GREEN exactbounded implementation;CPUtestsPASS,commit.

### Task3: independent receiver,exact CI and one actual
**Files:** Create scripts/run_sdk3_shader_cache.py,tests/test_sdk3_shader_cache_host.py,.github/workflows/sdk3-shader-cache-v1.yml,newreport/evidenceonly.
**Interfaces:** validate_receipt(folder,reference,nonce)->dict withcachepolicyidentifier andowner-complete requirement;native helpers Task1,preprocess Task2,oldmaterialvalidation.
- [ ] RED coherent completeactual-sourcefixture;rehashedcacheCRLF/code mismatch,missing/nonfinite owner,partial and source mismatch,wrongbindings,entryhelp. Expected missingreceiverFAIL.
- [ ] GREEN reuseoldresource/source/lifecycle;expected-onlycachepreprocess;focusedregressions/actionlintPASS,commit.
- [ ] Solefreshreview,one ImportantRED→GREEN pass/no rereview;exactsourcefourCIjobs+unitlogsPASS.
- [ ] Oneversionedrequest;authenticateartifact/oldrawimages/geometry/material/cache+owner arrays,retainnegative/partial.
- [ ] Actualreport/ownDraftPR(parent137),finalexactHEADCI/logcounts/remote/body/parent/main/originalpreservation;own scratch archival/removal. No originalgatepromotion.
