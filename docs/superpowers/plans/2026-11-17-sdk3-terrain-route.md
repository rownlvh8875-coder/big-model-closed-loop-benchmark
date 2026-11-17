# SDK3 Terrain Route Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline; one fresh whole-branch reviewer, no implementer delegation. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Prove and bound the missing procedural-terrain source route, preserving original failures.
**Architecture:** Independently retain selected immutable image sources, then a code-anchored bounded CPU audit over exact sources and prior actual shader/geometry evidence. No native trial.
**Tech Stack:** Python stdlib/unittest, unchanged expected-only Panda cache preprocessor, canonical GitHub CI.
**Spec:** ../specs/2026-11-17-sdk3-terrain-route-design.md

## Global Constraints
Base7997c1907d9edd4012116e3749a5c0c732ebf7bc; additions only. No old bytes changed, local SDK/Panda/GLX/model, new dependencies, native renderer, GPU queries/readback, render/task/state setters, environment/registry publication, or main merge. Inputs <=262144B each and1048576B total, no symlinks/escape. Immutable image tar4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698/configb9d673de93f1857e4dfa5ed6a48330d568ef96fce7f3cc975f0c688877e6e26e; prior run43985158042. CPU route evidence never promotes runtime execution/pixel owner/cause/repair/official matrix/Stage7.

## Review Focus
1. assets/shaders sample mistaken for actual assets/../shaders route: exact source path and nonmatching decoy hashes tested.
2. Rehashed or substituted source/capture evidence silently admitted: code-anchored inventory and every input byte tested.
3. CPU route discovery claimed as actual tag override, draw, depth tie or owner: explicit unobserved runtime fields and false flags tested.
4. Cached shader text normalized before comparison: unchanged actual bytes and expected-only preprocessing tested.
5. Symlink/path escape, oversize or source side effects: confined regular inputs and inert .data sources; mutation and subprocess CLI tested.

### Task1: source route auditor and exact evidence
**Files:** Create scripts/sdk3_terrain_route.py,tests/test_sdk3_terrain_route.py,docs/evidence/sdk3-terrain-route-01/{input-index.json,image-source-verification.json,frozen-source/**.data}.
**Interfaces:** audit(repo_root:Path)->dict, CLI python -I -B scripts/sdk3_terrain_route.py; JSON stdout only. index SHA baked into code; reads only named bounded regular files, no native imports.
- [x] Independently hash original image, inspect selected paths through layer order, retain exact sources and extraction receipt.
- [x] RED fixture-backed route/decoy/yellow/displacement/cache-absence/false-gates and mutation/missing/oversize/symlink/CLI tests. Expected missing auditor FAIL.
- [x] GREEN minimal stdlib validator and cited source inventory; all named tests and inherited shader/material tests PASS. Commit source + tests + pins.

### Task2: evidence, review and exact CI closeout
**Files:** Create docs/STAGE7_SDK3_TERRAIN_ROUTE_RESULT.md,docs/evidence/sdk3-terrain-route-01/{audit.json,verification/**,review/**,ledger.md}.
**Interfaces:** consumes audit result; report states source coverage gap, unknown live tag state and next runtime question; no native repair claim.
- [x] Reproduce exact JSON twice, verify old inputs unchanged and additions-only. Expected byte-identical audit and same original matrix3/4FAIL/Stage7false.
- [x] One fresh review against spec/plan; fix Important once RED-GREEN if any, defer Minor. Commit audit/report/Draft PR.
- [ ] Exact final HEAD canonical push+PR CI four jobs PASS; count unit tests from logs. Verify remote Draft PR/source/main/parent/original preservation and close own scratch. No extra native run or publication.
