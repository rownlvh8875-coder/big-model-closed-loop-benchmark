# Scoped Profile Confirmation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline; preserve checkout/scratch/originals.

**Goal:** Confirm the scoped helper backend with exact bwrap-owned PWD and retained failed observations.
**Architecture:** Separate adapter composes immutable03 policy/decision/flags; own04 registration and bounded observation wire/admission boundary.
**Tech Stack:** Python stdlib, pinned bwrap0.12.0, dedicated AppArmor ABI4 profile, GitHub Actions.
**Spec:** docs/superpowers/specs/2026-11-13-engine-clock-bwrap-profile-confirmation-design.md

## Global Constraints

Existing48 workflows/all prior source/tests/consumed01–03 unchanged. Request04/run1/attempt1/probes<=2/profile-loads<=1. Only fresh private trusted helper and same dedicated profile; no global policy/model/candidate build/image/scientific/main/Cloud action. Explicit env plus exactly PWD=/build; fivecapsets0/sixchangedns/UIDGID0/rootEROFS/buildwrite/afterlabel strict. Retain only safe structured fields; raw stdout8KiB perprobe/result131072B. Fullsuite/onefreshreview/sourceexactCI then one activation; retain raw/source/binary/profile.

## Review Focus

- PWD adds no arbitrary env permission: wrongPWD/extra credential name rejected; fixtures.
- Semantic failure retains actual safe fields: backend fake capture with real owned descriptors.
- Malformed/unknown output never persists raw text: wire mutation fixtures.
- Actual observer emits expected fixed proof and hashes: execute literal with fake OS/proc only.
- Composed controller has its own04 guard/API routes/closure and preserves same strict flags/both FDs: fixed argv and API-shaped fixtures.

### Task1: Confirmation adapter

**Files:** Create scripts/engine_clock_bwrap_profile_confirmation.py, tests/test_engine_clock_bwrap_profile_confirmation.py, .github/workflows/engine-clock-bwrap-profile-confirmation.yml, docs/STAGE7_ENGINE_CLOCK_BWRAP_PROFILE_CONFIRMATION.md.
**Interfaces:** parse_observation(value)->safe dict; validate_observation(value,host,after=False)->dict; Backend(previous.Backend)._probe overrides only observer/capture/retention; qualify=previous.qualify; own04 validate_request/activation/authenticate/run. No mutable global changes in previous module.

- [ ] RED new-module fixtures for exactPWD+hash, extra-env/wrongPWD/nonzero caps rejection, malformed wire, semantic-failure retention with real directory FDs, fake-OS observer execution, and own04 API guard/schema.
- [ ] Implement adapter/observer/workflow; focused PASS with no live namespace/profile/network operations.
- [ ] Full unittest PASS/7skip; old48 workflows/source unchanged; commit and one fresh review; Important/Critical one RED→GREEN/full pass, defer Minor.
- [ ] Source Draft/exact push+PR CI, new branch/all-run0 preflight, request-only sole-parent activation once.
- [ ] Consume original unique run/job/workflow/artifact bytes and after proof, record current kernel/image and limits. Never promote03 or fill missing old observations; retain original04 facts and source/binary/profile.

Tests: /workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -m unittest discover -s tests [-p test_engine_clock_bwrap_profile_confirmation.py]. Baseline857 PASS/7skip77.949s at915e0d6.
