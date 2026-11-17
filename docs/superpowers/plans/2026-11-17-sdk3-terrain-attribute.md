# SDK3 Terrain Attribute Sparse Windows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline; one fresh wholebranch reviewer, no implementer delegation. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Read bounded selector texels from the existing2.03GB CPU-resident attribute buffer without copying it.
**Architecture:** Private helper/native/host adapters over unchanged terrain-state code; explicit logical extent and byte budgets; one authenticated native replay.
**Tech Stack:** Python stdlib/mmap/unittest,numpy already present,existing Panda1.10.13/SDK3/Actions.
**Spec:** ../specs/2026-11-17-sdk3-terrain-attribute-design.md

## Global Constraints
Base279ab9d6881a4924bb27aca6de198fd8e9ee1d04,additionsonly. Logical cap2147483648B,4texels/64Bwindow/960Btotal,5candidatepoints/3textures. Same24knowninputs/2frozen sources/4states/4shaders/262144Bfile/2097152Btext/20sCPU. No old files touched,localSDK/Panda/GLX/model/install/deps/GPUqueries/readback/extra render/task/state setters/mainmerge/environment-registrypublication. One native/0officialmodels/0inferences; same immutable image/SDK/core/BaseCamera/reference,2CPU10GiB/privateIPC/networknone/readonlyroot/uid65534/tmpfs512MiB,600/630/20min. ImageSHA exact,CPU1e-9abs/1e-12rel; allGPU/owner/cull/depthtie/cause/repair/originalgate/Stage7false. Request-only diagnostic/sdk3-terrain-attribute-20261117-01 attempt1.

## Review Focus
1. Raising logical extent causes whole-copy/scan or unbounded bytes: real2.03GBreadonly map/RSSdelta/64B+960B policy tests.
2. Native and host cap/policy/counter disagree or mutate old globals: real snapshot2GiB/admission and identity/global-preservation tests.
3. Sparse bytes/UV/offset/source/pointer bindings can be forged: inherited receiver plus policy/count/window mutation negatives.
4. Cold -I-S bootstrap imports numpy/Panda too soon or lifecycle bounds drift: exact coldhelp and command-budget/source-entry tests.
5. Captured selector values promote pixel/cause/repair claims or missing/partial values count as complete: absent/partial/unavailable/source mismatch false-gate regressions.

### Task1: sparse logical-buffer policy and real map tests
**Files:** Create scripts/sdk3_terrain_attribute.py,tests/test_sdk3_terrain_attribute.py.
**Interfaces:** resident_window(texture,uv,core)->dict via private original function clone;LIMITS,SPARSE_POLICY,proxy(),sample_bytes(manifest)->int.
- [x] RED real2030043136B readonly mmap,upperend/wrapped4literalfloat texels,no-getData/no-getRamImageAs/no-wholebytes andRSSdelta<32MiB; old helper remains1GiB;over2GiB untouched; sparse count/policy limits. Expected missingmoduleFAIL.
- [x] GREEN minimal stdlib adapter,budget helper; named unittestPASS,commit.

### Task2: native and host policy adapters
**Files:** Create scripts/sdk3_terrain_attribute_native.py,scripts/run_sdk3_terrain_attribute.py,tests/test_sdk3_terrain_attribute_host.py,tests/sdk3_terrain_attribute_fixtures.py.
**Interfaces:** snapshot_terrain(...) adds sparse_policy/sparse_sample_bytes_captured; validate_receipt(folder,reference,nonce)->dict adds attribute_window_count/attribute_collection_complete and no gate promotion.
- [x] RED actual snapshot over sparse large attribute CPUdouble; wrongpolicy/counter/offset/UV/hash/identity/flag negatives; originalreceiver rejects2GiB; absent/partial; native-I-S-Bhelp and identical Docker budgets. Expected missingentryFAIL.
- [x] GREEN private native andhost clones,newrequest authentication/versioned entry; focused new+inherited regressionsPASS;commit.

### Task3: exactCI,one actual and final evidence
**Files:** Create .github/workflows/sdk3-terrain-attribute-v1.yml,docs/STAGE7_SDK3_TERRAIN_ATTRIBUTE_RESULT.md,docs/evidence/sdk3-terrain-attribute-01/** only.
**Interfaces:** exactsourceCI/request/immutable runtime; independent artifact receipt and CPUfloat32/LOD0 candidate branch analysis,original sourcepixel gate retained.
- [x] actionlint,one fresh wholebranchreview/Importantfixonce ifany,exactsource4jobsPASS/logcounts.
- [x] One request-only activation/one actual; authenticate run/ZIP/reference/receiver/14images and sparse byte counts. No rerun same request.
- [ ] DraftPRparent140,finalexactHEAD4jobs/logcounts,remote/body/parent/main/originalpreservation; archive own ledger only and closeout. No benchmark promotion.

Sparse runtime RSS highwater before/after is recorded in KiB,independently typed/recomputed by receiver; delta>32768KiB forces partial with rss_delta_budget. This complements sparse code/byte counters and does not claim absence of all internal driver allocations. Native-I-S-Bhelp and host receipt mutations cover this metadata.
