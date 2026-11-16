# SDK3 CPU pixel material Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline;one fresh whole-branch reviewer beforeactual,no implementer delegation. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Bind Road7CPUcandidate UV/material/sampler and bounded cache/filebytes to authenticated target/geometry.
**Architecture:** New pureCPU interpolation/boundedread helpers;new native material snapshot over unchangedbudget/progressprivateadapters;new receiver/source activation andonejobworkflow.
**Tech Stack:** Python/unittest/numpy,existingfrozenPanda1.10.13/SDK3/Actions.
**Spec:** ../specs/2026-11-17-sdk3-pixel-material-design.md

## Global Constraints

Base288fc0a80a11c28630239d031e61ffaf0d381e51;additionsonly. Onefreshnative/0officialmodel/0inference;600schild/630container/20minjob;original2CPU/10GiB/privateIPC/readonlyroot/networknone/uid65534/tmpfs512MiB andfrozenimage/SDK/core/BaseCamera/priorRGB pins. No localnative/model/renderchanges/GPUqueries/forcedRAMreload/publication/mainmerge. Max40triangles/8stages/16textures/8MiBfile/16MiBtotal/20sCPUmaterial. Allshader/GPU/cause/repair/originalgate/Stage7false. UVrecompute1e-9abs/1e-12rel,imageSHAexact. Requestfile docs/requests/sdk3-pixel-material-20261117-01.json;singlebranchdiagnostic/sdk3-pixel-material-20261117-01.

## Review Focus

1. Wrong barycentric/texcoord/texturematrix creates falseUV binding;Task1 literals andTask2 tamperingnegatives.
2. Missingcache causes GPUread/reload or unboundedallocation;Task1 fakecachedtexture sideeffects +boundedfile tests.
3. Stale mesh/vertex/primitive/state/target bindings accepted;Task2 sourceIDs/NPZ/position/UV/identity mutations.
4. Sampler defaults mistaken forstage overrides,unsupported/missing fields hidden;Task2 complete stage/texturefixture and explicit availability schema.
5. Source mismatch/partialstate/CPUcache promoted toshaderoutput/repair;Task2 falsegate assertions and actualreport.

### Task1: pureCPU UV and bounded texture/cache IO
**Files:** Create scripts/sdk3_pixel_material.py,tests/test_sdk3_pixel_material.py.
**Interfaces:** interpolate_uv(values,barycentric)->list;transform_uv(uv,matrix)->list;capture_cached_ram(texture,store)->dict;BoundedStore(folder,max_file=8MiB,max_total=16MiB).save/copy_asset.
- [ ] RED: literalUV/transform,invalid weights/nonfinite,unavailablecache neverread,expected/actualRAMlimits beforegetData,symlinkescape/oversize/globalbudget. ExpectedFAIL missingmodule.
- [ ] GREEN: minimalpuremath andboundedIO/noGPUfallback. ExpectedCPUtestsPASS. Commit.

### Task2: native cached state snapshot and independent admission
**Files:** Create scripts/sdk3_pixel_material_native.py,scripts/run_sdk3_pixel_material.py,tests/test_sdk3_pixel_material_host.py,.github/workflows/sdk3-pixel-material-v1.yml,new evidence/resultonly.
**Interfaces:** snapshot_material(core,engine,sensor,geometry,out,nonce)->manifest;native/hostprivateadapters;validate_receipt(folder,reference,nonce)->dict;authenticate_source(bundle);run(). Uses Task1helpers.
- [ ] RED: validUV/attribute/rawbindings;wrongPID/target/triangle/vertex/UV/matrix/stage/texture/rawbytes/budget rejects;unavailable/partial/source mismatch remainhonest. ExpectedFAIL missingbehavior.
- [ ] GREEN: actualcachedPanda reads/onegeometrysnapshot/noextraGPUcalls;readonlyassets+cacheonly;privateoriginal600/630 lifecycle andsource authentication. ExpectedfocusedPASS/actionlint.
- [ ] ExactsourceCI4jobsPASS;solefreshreview;one ImportantRED→GREEN pass/no rereview;Minorledger.
- [ ] One versionedactualrequest;authenticateZIP/lifecycle/images/geometry/material+independentUV,retainnegative/unavailable observations.
- [ ] Result/ownDraftPR(parent135);finalexactHEADCI/logcounts/remote/body/parent/main/originalpreservation;archive/removeonlyownsddscratch. No originalgatepromotion.
