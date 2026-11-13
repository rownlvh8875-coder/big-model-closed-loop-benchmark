# progressbar build inputs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Pin genuine source/build-tool bytes and produce a reviewed, inactive source-to-wheel policy without executing source.

**Architecture:** A consumed acquisition transcript downloads only registered files. Static archive/metadata inspection and an explicit target marker environment produce a component-input receipt and readiness blockers, never a complete runtime lock.

**Tech Stack:** Existing Python3.11.17/pip26.2.2 tools, stdlib, curl, public PyPI.

**Spec:** `docs/superpowers/specs/2026-11-13-engine-clock-progressbar-build-inputs-design.md`

## Global Constraints

- Target Python3.11.18/Linux amd64; actual tool Python3.11.17. Pins and original consumed evidence stay fixed.
- No third-party source execution/install, package/native/model/image calls, retries/redirects or default changes.
- One source/3JSON/3wheel fetches, <=240s outer/30s request; 64KiB/1MiB/8MiB individual payload ceilings,32MiB tree and>=1GiB initial free.
- Source static reads<=1MiB expanded/64members/128KiB member; tool wheel reads<=64MiB/5000members. No extraction or downloaded imports.
- No fabricated output hash/readiness/full lock. Retain all old/new raw workspaces; no worktree/Cloud publish/main merge.

## Review Focus

1. Genuine payload verification versus metadata claims/publisher signatures; component tool closure versus complete image lock.
2. Source syntax/packaging evidence versus target runtime compatibility or unreviewed source transformation.
3. Tar/gzip/wheel resource/path/RECORD checks, without treating static inspection as executable-code containment.
4. Offline build recipe prerequisites, finite cleanup/output checks and no hidden build fallback.
5. Actual execution source, reviewed HEAD, raw receipt and final CI remain separate; old contracts/evidence preserved.

### Task 1: Acquire static inputs, inspect and review the inactive build policy

**Files:** new spec/plan, `docs/evidence/STAGE7_ENGINE_CLOCK_PROGRESSBAR_*`, small raw metadata/static findings under `docs/evidence/engine-clock-progressbar/`, `docs/STAGE7_ENGINE_CLOCK_PROGRESSBAR_BUILD_INPUTS.md`; update continuation and parent Task3 status only.

**Interfaces:** consumes retained PR46 progressbar metadata and source pin; produces real source/tool file hashes, source/member/metadata findings and inactive component build policy. Output wheel and runtime/base/full-lock hashes remain null.

- [ ] Register request/operator/source commit before downloads. Expected: clean committed source and exclusive new output directory.
- [ ] Execute acquisition once and statically inspect hash-verified bytes; preserve failure without retry. Expected: real receipts and safe member inventory or original error.
- [ ] Check full default tool closure under explicit target markers; inspect actual source and packaging. Expected: supported facts and unresolved blockers, no source execution or fabricated build output.
- [ ] Write concrete inactive build/patch prerequisites and source/output verification policy, data evidence and continuation; independently validate hashes/links/preservation. Expected: all gates truthful, old tracked files except2status docs fixed.
- [ ] Commit, one fresh whole-branch review and root rulings, then own-branch Draft PR/basic CI. Expected: exact reviewed/final HEAD, actual4job conclusions and artifacts, no source/build/image/native permission implied. Final execution receipt lives in this plan's ledger and PR.
