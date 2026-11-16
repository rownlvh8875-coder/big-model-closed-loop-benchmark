# SDK3 Shader Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline;onefreshwholebranchreviewer,no implementer delegation. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Bind actualcachedscene/tonemap shaders and known PSSM inputs to Road7 evidence.
**Architecture:** PureCPU exactvariant/tonemap helper;new native observer over material private adapters;independent receiver and onejobworkflow.
**Tech Stack:** Python/unittest/numpy,frozenPanda1.10.13/SDK3/Actions.
**Spec:** ../specs/2026-11-17-sdk3-shader-path-design.md

## Global Constraints

Base dacce23588e45dfd986f69f1ec00f23e0be051ed;additionsonly. Onefreshnative/0officialmodel/0inference;600schild/630container/20minjob;2CPU/10GiB/privateIPC/readonlyroot/networknone/uid65534/tmpfs512MiB and unchanged image/SDK/core/BaseCamera/reference pins. No local SDK/native/model/newdependencies/GPUqueries/render/task/shader/sampler/setter/forcedRAM/readback/publication/mainmerge. Twelveexactfrozen sources;256KiBtext/2MiBtotal/max8shaders/40meshbindings/20s cooperative observer. Known8PSSMnames only;numericarraysunavailable,ownerrigdata notbounduniformproof. AllGPUowner/hardwareuniform/cause/repair/originalgate/Stage7false;original3/4FAIL. Requestdocs/requests/sdk3-shader-path-20261117-01.json on diagnostic/sdk3-shader-path-20261117-01.

## Review Focus

1. Wrong shader variant or scene/tonemap interchange: exact source/config/define-order and tampering negatives in Task2.
2. Cached shader or owner arrays promoted to executed GPU program/uniforms: explicit falseflags/typeavailability in Task2.
3. Stale target/material/state/tonemaptexture bindings: hash/pointer substitutions in Task2.
4. Partial/time/oversize/missinginputs masquerade as complete: bounded text and explicit partial/unavailable cases in Task1/2.
5. Native observer mutates old modules or camera lifecycle: private adapters,existing receipts/regressions/sourceclosure in Task2.

### Task1: exact shader variant and CPU tonemap
**Files:** Create scripts/sdk3_shader_path.py,tests/test_sdk3_shader_path.py;newfrozen-source evidenceonly.
**Interfaces:** variant(raw:str,defines:dict,stage:str)->str;pipeline_defines(config:dict)->dict;tonemap(rgb,exposure=1)->array;TextStore(folder).save(text,label)->descriptor with file/nbytes/SHA.
- [ ] RED literal alias/order/USE330/missingversion,boundedUTF8/globalbudget,tonemapzero/knownfinitevector/negative/invalidvalues. Expected missingmoduleFAIL.
- [ ] GREEN minimalpurefunctions,run CPUtestsPASS,commit.

### Task2: cached source/input native observation and independent admission
**Files:** Create scripts/sdk3_shader_path_native.py,scripts/run_sdk3_shader_path.py,tests/test_sdk3_shader_path_host.py,.github/workflows/sdk3-shader-path-v1.yml,newresult/evidenceonly.
**Interfaces:** snapshot_shader(core,engine,sensor,geometry,out,nonce,journal)->manifest;validate_receipt(folder,reference,nonce)->dict. Uses Task1 and unchangedmaterialvalidator/privateadapters.
- [ ] RED validactualsources/variant and knowninput availability;wrongtarget/material/state/hash/defines/scene_tex/falseflags/arrayvalues/partial rejectorremainhonest. Expected missingbehaviorFAIL.
- [ ] GREEN nativegetters/privateadapters/noextraGPU/no setters;receiver oldgates+exactsource/shader/text/input/identity/time/budgetchecks. Focusedregressions/actionlintPASS,commit.
- [ ] ExactsourcefourCIjobsPASS;solefreshreview and ONE ImportantRED→GREEN pass/no rereview;Minorledger.
- [ ] One versionedactualrequest;authenticateartifact/oldimages/geometry/material/newshader receipt,retainfailure/partial/source mismatch.
- [ ] Finalreport/ownDraftPR(parent136),exactHEADfourCI/logcounts/remote/body/parent/main/originalpreservation;own scratch archive/remove. No originalgatepromotion.
