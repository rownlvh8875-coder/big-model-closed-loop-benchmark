# Python bootstrap inputs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Pin genuine candidate interpreter/bootstrap bytes and their remaining execution prerequisites.

**Architecture:** Immutable discovered manifest/release metadata selects one archive. A consumed historical download transcript and bounded static inspection produce an archive-member/bootstrap input manifest, not an installed/runtime admission identity.

**Tech Stack:** Existing Python3.11.17/stdlib/trusted pip metadata parser, standard GitHub CLI HTTPS; no downloaded code execution.

**Spec:** `docs/superpowers/specs/2026-11-13-engine-clock-python-bootstrap-inputs-design.md`

## Global Constraints

- Candidate3.11.18/Linux x64/Ubuntu24.04; actual inspector3.11.17. Existing product/version/rendering pins unchanged.
- Archive exactly92610561bytes/SHA099ef30fc27f0d7067a67be5a5fb7fd66154cfa1e4186c88f71c3a3070c81abc; single acquisition, no retry/fallback.
- Download180s+cleanup5s/free1GiB/archive128MiB/tree160MiB/log1MiB; polling not quota.
- Static tar<=512MiB/20000members/member128MiB/manifest16MiB/180s/address space1GiB; embedded wheels<=32MiB/5000members.
- No extraction/execution/install/native/model/image/loader changes. Preserve old evidence/workspaces; readiness false,16refsnull/nativeallowance0.

## Review Focus

1. Actions distribution provenance/digest agreement versus publisher attestation and installed binary identity.
2. Complete archive descriptor/hash coverage and bounded static member/alias/embedded-wheel handling.
3. Bootstrap source/config/wheel selection versus merely naming a pip version; external OS/loader closure stays explicit.
4. Download/process cleanup/credential redaction and polling versus hard quota; discovery limits differ from payload operation.
5. Archive/bootstrap/manifest hash classes, prefix/relocation/actual runtime uncertainty, unchanged old policy/source and honest next gate.

### Task 1: Acquire candidate archive and verify static bootstrap inputs

**Files:** new spec/plan, `docs/evidence/STAGE7_ENGINE_CLOCK_PYTHON_BOOTSTRAP_*`, small metadata/static findings under `docs/evidence/engine-clock-python-bootstrap/`, `docs/STAGE7_ENGINE_CLOCK_PYTHON_BOOTSTRAP_INPUTS.md`; update continuation/parent Task3 status only.

**Interfaces:** consumes retained discovered metadata hashes and PR47 fixed component input/policy; produces genuine archive SHA, closed archive descriptors, bootstrap component facts and remaining blockers. Installed identity/build/source execution/image readiness remain false.

- [ ] Register selected metadata/request/operator and source commit before archive download. Expected: clean committed source and exclusive new output directory.
- [ ] Acquire archive once; preserve original failure if any. Expected: exact published size/digest match or consumed terminal failure; no execution.
- [ ] Statically inspect bounded archive, source/config/bootstrap wheels/ELF facts and independently check output hashes. Expected: accurate component input manifest or original bounded failure; no runtime proof claim.
- [ ] Document candidate binding and remaining OS/loader/prefix/launcher gates; verify old-file preservation and links. Expected: old policy/proposal unchanged, no false filled runtime/image refs.
- [ ] Commit; one fresh whole-branch review, rule declines; own-branch Draft and actual final basic CI. Expected: distinct acquisition/review/final HEAD,4job conclusions/artifact counts, no publication/main merge/native/source execution. Final evidence in this plan's ledger and PR.
