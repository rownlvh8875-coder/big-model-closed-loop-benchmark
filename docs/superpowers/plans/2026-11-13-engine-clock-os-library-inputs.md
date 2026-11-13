# OS/library inputs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Resolve and measure genuine signed Ubuntu package inputs and their static ELF coverage for the Python builder candidate.

**Architecture:** Two registered data operations: signed metadata/local APT resolution produces a hash-bound package plan; exact deb acquisition/static inspection consumes it. Both remain input evidence, not an installed OS or execution admission.

**Tech Stack:** Existing Python3.11.17/stdlib, curl/gpg, host APT simulation, dpkg-deb tar streams, readelf metadata only.

**Spec:** `docs/superpowers/specs/2026-11-13-engine-clock-os-library-inputs-design.md`

## Global Constraints

- Fixed snapshot20261113T000000Z/noble+updates+security/main+universe/amd64+all and signer F6ECB3762474EDA9D21B7022871920D1991BC93C.
- No install/maintainer/bootstrap/runtime/native/model/image/source execution, source/profile/loader override or old request replay.
- Metadata600s/request30s/index64MiB/total192MiB/decoded512MiB; APT120s/call, task-local file-only/empty status DB, logs4MiB/workspace1GiB/free2GiB.
- Deb acquisition600s/128files/file64MiB/total256MiB; static180s/decoded512MiB/50000members/member128MiB/manifest16MiB; ELF blobs256MiB/output32MiB.
- Readinessfalse/old16refsnull/nativeallowance0; preserve all raw/workspaces. No worktree/Cloud publish/main merge.

## Review Focus

1. Pinned GPG anchor and signed Release/index/payload hash chain; snapshot/date/validity and local APT trusted=yes scope.
2. Task-local empty-state solver isolation and exact selected metadata closure versus installed OS/Essential/postinst completeness.
3. Deb/control/data descriptor coverage, rooted links/collisions, nonexec ELF analysis and resource/failure preservation.
4. Candidate SONAME/version-label coverage versus real loader/symbol/ABI behavior and unresolved usrmerge/prefix/config paths.
5. Separate operation source/package plan/manifest hash classes, immutable old policies/proposal/gates, truthful final review/CI.

### Task 1: Signed metadata and isolated dependency resolution

**Files:** new spec/plan/request/operator and signed metadata/package-plan evidence under `docs/evidence/engine-clock-os-inputs/`.

**Interfaces:** consumes PR48 uncovered dependency names and cached discovery/key bytes; produces exact `package-plan.json` with name/version/architecture/Filename/Size/SHA256 and signatures/index bindings, or retained original failure.

- [ ] Register metadata request/operator/source before new downloads. Expected: clean source, exclusive output path, discovery hashes pinned.
- [ ] Verify signed metadata/index bytes; run only task-local file-only APT update and --simulate. Expected: VALID signatures/actual index hashes and coherent selected package plan, or stop unsupported.
- [ ] Independently validate plan/source/index bindings and unchanged old files. Expected: no actual package installation or installed-state claim; commit genuine plan before Task2 request.

### Task 2: Exact payload/static ELF evidence and final review

**Files:** package request/operator/receipt, member/control/ELF coverage evidence, `docs/STAGE7_ENGINE_CLOCK_OS_LIBRARY_INPUTS.md`; update continuation/parent Task3 status only.

**Interfaces:** consumes exact Task1 package-plan hash and old retained Python archive; produces measured deb hashes/static file and ELF facts, with all installed/execution readinessfalse.

- [ ] Register exact payload request/source, fetch selected debs once and hash actual bytes. Expected: full hash match or retained consumed failure; no fallback/retry.
- [ ] Inspect control/data/ELF streams and version-label coverage under caps. Expected: truthful candidate mapping/coverage and unresolved runtime prerequisites, never actual ABI PASS.
- [ ] Validate raw hashes/provenance/links/old preservation; commit; one fresh whole-branch review with all decline rulings. Expected: actual reviewed HEAD, no product changes/tests or local suite duplication.
- [ ] Own-branch Draft/final basic CI/API/remote/main/Cloud checks. Expected: exact final HEAD/actual4job/artifact results; no publication/merge/native/source execution. Final execution status in this plan's ledger/PR.
