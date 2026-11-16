# SDK3 one-pixel CPU geometry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline;one fresh whole-branch reviewer before activation,no implementer delegation. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Map CPU geometry candidates at the authenticated one-pixel boundary without new model inference or a premature renderer fix.
**Architecture:** New finite ray math/native post-read CPU snapshot,seven-pose source-qualified replay,and pinned host/private command adapter;two independent native jobs. All existing files unchanged.
**Tech Stack:** Python/numpy/unittest,Panda3D1.10.13 through frozen SDK3/image,GitHub Actions.
**Spec:** ../specs/2026-11-16-sdk3-pixel-geometry-design.md

## Global Constraints

Based02fefd;additions only. Same image498447tar/configb9d673,SDK27cd/core8b037,originalsource pins unchanged. No local SDK/Panda/GLX/ORT;no model anywhere in this new run. Hosted2CPU/10GiB/readonly/privateIPC/uid65534/networknone;160s owned child/180s container. Two renderer children,max0official model/0inference. Prior43,506,956BfullRGB artifact hash as spec. Source first6andstep7mustmatch exact historical bytes before equivalence claim. Five rays/CPU triangles never actual GPU ownership/depth/cause; truncation/inconclusive retained. Main/env/registry publication and gate promotion forbidden.

## Review Focus

1. Wrong y-origin/pixel center/corner mapping,behind/parallel/degenerate/nonfinite geometry must not create false hits;Task1 literals.
2. CPU callback must run only after one original seventhRoadread and restore exactly even on failure;no extra capture;Task1 observer tests.
3. Wrong history/ref or missing/truncated geometry must remain inconclusive,not proof of pixel ownership or repair;Task2 negatives.
4. Native nonzero/unknown/OOM/cleanup/ID/profile/command/model mount cannot be admitted by matching hashes;Task2 table-driven negatives.
5. Source/native counts or replay status cannot become original closed-loop/model/4condition success;Task2 honest outcome tests and actual records.

### Task1: CPU geometry and native replay
**Files:** Create scripts/sdk3_pixel_geometry.py,scripts/sdk3_pixel_geometry_native.py,tests/test_sdk3_pixel_geometry.py.
**Interfaces:** pixel_samples(width,height,x,y); intersect_triangles(origin,direction,triangles,max_distance); post_read_observer(sensor,callback,target_call=7); replay/reference validators. New native CLI implements owned-child+one fresh pose replay through unchanged world camera.
- [x] Literal pixel mapping,front/behind/edge/parallel/degenerate/nonfinite triangle tests and callback ordering/restoration tests;ExpectedRED.
- [x] Minimal bounded CPU rays/geometry snapshot/native CLI and reference membership;ExpectedGREEN. Commit.

### Task2: Authenticated host workflow and actual diagnosis
**Files:** Create scripts/run_sdk3_pixel_geometry.py,.github/workflows/sdk3-pixel-geometry-v1.yml,tests/test_sdk3_pixel_geometry_host.py;new evidence/result doc only.
**Interfaces:** native_command(...,reference)->list; cloned run_container private globals; validate_receipt(folder,reference)->dict; exact prior/source authentication.
- [x] Add wrong source/replay/geometry/model/lifecycle/profile negative tests;ExpectedRED.
- [x] Implement pinned image/SDK/prior staging,zero-model2job execution and independent CPU reanalysis;ExpectedGREEN/actionlint;ownDraft parentPR132.
- [x] Exact-sourceCI4jobsSUCCESS;one fresh review;effect regrading and one ImportantRED→GREEN pass/no rereview;Minor ledger.
- [x] Request-only activation:actual2native/0model/0inference authenticated;both160sTIMEOUT,lastpersistedWORLD_READY,no geometry;negative evidence retained.
- [x] Report actual timeout and unknown candidates/limits;all662files retained/indexed. No renderer repair promotion.
- [ ] Final exactHEADCI/PRbody/remote/clean/original preservation and own-ledger archival/removal:authoritative result recorded in output/stage7-sdk3-pixel-geometry-01/final-closeout/verification.json after final commit.
