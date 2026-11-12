# First-divergence pixel neighborhoods Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans sequentially; one fresh whole-branch review after CPU evidence/report.

**Goal:** Determine which saved raw pixel changes contribute to the recorded I420 difference with zero new native/model calls.

**Architecture:** A standalone CPU tool authenticates the retained original archive/extraction and replays unchanged production transforms with recorded intrinsics. Exact subset interventions are in-memory only; producer62 stays frozen.

**Tech Stack:** Python, NumPy2.4.6/OpenCV5.0.0.93 for archived replay; unittest CPU fixtures.

**Spec:** docs/superpowers/specs/2026-11-12-first-divergence-pixel-neighborhoods-design.md

## Global Constraints

- Forensic native/GPU/ORT/official calls0; unchanged baseline generated SMALL graph is separate.
- No download/re-extraction or input mutation.
- Preserve source62/protected13/baseline43/all42workflows/consumed requests.
- At most4changed pixels,2^Nsubsets,radius2neighborhoods,JSON<=1MiB/fresh/outside input.
- No worktrees/Cloud publication/main merge/default/renderer/converter/action changes.
- Original strictFAIL/geometry-optics-fullS limits/Stage7 incomplete.

## Review Focus

- uint8 subtraction must not wrap; border neighborhoods must not wrap around arrays.
- Interpolation/quantization can suppress or combine pixel effects; all-subset enumeration must test actual packed bytes and minimality.
- Counterfactual images must stay in-memory and must not be described as actual model inference.
- Wrong archive/version/source/extracted member must fail before a successful report.
- Existing or input-contained output must fail before writes and input bytes must remain unchanged.

### Task 1: CPU tool and behavioral tests

**Files:** Create scripts/first_divergence_pixel_forensics.py and tests/test_first_divergence_pixel_forensics.py.

**Interfaces:** pixel_locations(lhs,rhs),analyze_pair(raw_a,raw_b,intrinsics),verify_archive(root,archive),run(root,archive,out) return dict/list per spec; CLI --root --archive --out.

- [x] Write failing tests for signed pixel locations/edge patches, unchanged/cropped pixels, camera isolation, cap/input immutability, output/archive/runtime rejection; run RED.
- [x] Implement minimal pure CPU analysis and strict fixed-archive reader; run targeted GREEN.
- [x] Run full unittest once, check62source/pins/all42workflows unchanged; commit tool/tests.

### Task 2: Actual forensic evidence and source history

**Files:** Create docs/STAGE7_FIRST_DIVERGENCE_PIXEL_FORENSICS.md and docs/evidence/STAGE7_FIRST_DIVERGENCE_PIXEL_FORENSICS.json; update docs/STAGE7_CONTINUATION.md.

**Interfaces:** Consumes Task1 CLI and retained run43149053427 ZIP/extraction; produces authenticated CPU findings and exact next boundary, no native execution registration.

- [x] Refresh read-only run/job/artifact API metadata; authenticate existing ZIP; run tool with recorded CPU versions and preserve report/input digests.
- [x] Inspect4raw pixel neighborhoods, exact subset/camera influences and retained source/history; distinguish measured transforms from GPU hypotheses.
- [x] Write report/evidence/continuation and commit. Obtain fresh whole-branch code+evidence review; material fixes get RED/GREEN and required suite.
- [ ] Push reviewed branch/create stacked Draft PR; verify actual basic CI only, no native replay; record finalHEAD/CI/PR and keep original strictFAIL.
