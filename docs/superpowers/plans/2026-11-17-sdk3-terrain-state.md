# SDK3 Terrain State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline, one fresh whole-branch reviewer, no implementer agents. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Observe actual terrain tag/input CPU state in one unchanged Road7 replay.
**Architecture:** Pure CPU projection/footprint helpers; new borrowed-boundary native and strict receiver; versioned one-shot workflow over immutable runtime.
**Tech Stack:** Python/numpy/unittest,existing Panda1.10.13/SDK3/Actions.
**Spec:** ../specs/2026-11-17-sdk3-terrain-state-design.md

## Global Constraints
Base1ddcdc8e3b8a1c0022a07bc9844aeae613ca2b4c,additionsonly; preserve old bytes/original checkout. One native/0official model/0inference; no localSDK/Panda/GLX/model/install/GPUquery/readback/render/task/state setters/new dependencies/mainmerge/environment-registry publication. Same frozen image/SDK/core/BaseCamera/reference,2CPU/10GiB/privateIPC/networknone/readonlyroot/uid65534/tmpfs512MiB,600/630/20min. Terrain limits4states/4shaders/2sources/262144Bfile/2097152Btotal/1073741824Bresident/5candidatepoints/20sCPU. Known24inputnames; no all-input/GPU/cull/owner/depthtie/cause/repair/Stage7claim. Existing imageSHA exact and CPU1e-9abs/1e-12rel. Request-only diagnostic/sdk3-terrain-state-20261117-01,attempt1,one child.

## Review Focus
1. Candidate projection or source/tag evidence promoted to actual terrain intersection/draw/pixel owner: explicit false claims, named candidate points and scope tests.
2. Tag-state override/pointer/shader or final identity forged: bound states/source/hash/interval/restoration mutation tests.
3. RAM reads cause fullcopy, GPU readback, out-of-range/wrong-wrap reads: real memoryview buffers, halftexel/repeat/clamp/mirror, unavailable API and no-getData tests.
4. UV/texel offsets changed independently of actual geometry/matrix/owner binding: host recomputation plus pointer/UV/offset negatives.
5. New entry or workflow relaxes old budget/lifecycle/source gates or mutates moduleglobals: inherited tests, entry checks, requestscope and exactCI checks.

### Task1: bounded candidate and resident-window helpers
**Files:** Create scripts/sdk3_terrain_state.py,tests/test_sdk3_terrain_state.py.
**Interfaces:** candidate_samples(hits,local_to_world,elevation_ratio)->list; footprint(size_xy,uv,wrap_u,wrap_v)->list4xy; resident_window(texture,uv,core)->dict explicit availability/rawhex.
- [x] RED literal translated/scaled row matrix,ratio1/4,finite/singular/bounds,halftexel/repeat/clamp/mirror,readonly buffer corners/no fullcopy/notresident/unsupported extent+buffer tests. Expected missingmoduleFAIL.
- [x] GREEN minimal helpers. Run named unittest module:PASS; commit.

### Task2: borrowed terrain snapshot and strict receiver
**Files:** Create scripts/sdk3_terrain_state_native.py,scripts/run_sdk3_terrain_state.py,tests/test_sdk3_terrain_state_host.py,tests/sdk3_terrain_state_fixtures.py.
**Interfaces:** snapshot_terrain(core,engine,sensor,geometry,out,nonce,journal)->dict; validate_receipt(folder,reference,nonce)->dict retaining every previous gate and new terrain fields.
- [ ] RED actual snapshot with CPU doubles and coherent inherited receipt; bound fixed sources,states,ownertextures,candidatewindows; invalid finalshader/target/nonce/claims/pointer/UV/offset/rawbyte and absent/partial/unavailable tests. Expected missingmoduleFAIL.
- [ ] GREEN private adapters/strict receiver and versioned entry/authentication. Focused helper/newhost+inherited shader/material suitesPASS; commit.

### Task3: exact CI, one actual and closeout
**Files:** Create .github/workflows/sdk3-terrain-state-v1.yml,docs/STAGE7_SDK3_TERRAIN_STATE_RESULT.md,docs/evidence/sdk3-terrain-state-01/** only.
**Interfaces:** one request authenticates exact source push+PR4jobs and old immutable runtime; independent artifact analysis uses Task2 unchanged receiver.
- [ ] actionlintPASS; one fresh review and one Important RED-GREEN fix pass if needed; exactsourceCI4jobsPASS with logcounts.
- [ ] One request-only activation/one actual artifact; independently recompute analysis and CPU windows; preserve14images/originalfailure/partial statuses. No rerun same request.
- [ ] New DraftPR(parent139), finalexactHEADCI/logcounts/remote/body/parent/main/originalpreservation and own scratch archive/removal. No gate promotion.
