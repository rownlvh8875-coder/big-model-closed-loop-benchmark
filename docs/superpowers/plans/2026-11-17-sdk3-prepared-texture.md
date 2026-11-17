# SDK3 prepared texture implementation plan

> Required: superpowers:executing-plans inline, TDD, one fresh wholebranch review; no implementer delegation.

Spec: ../specs/2026-11-17-sdk3-prepared-texture-design.md
Base: bf71fb9a794506b1fc64f996f4ff062cbb1b98a4. All old tracked bytes immutable. All spec bounds bind all tasks.

## Review Focus
1. Cache getters accidentally prepare, reload, query GPU, generate mipmaps, copy a large buffer, or mistake queued/nonresident for resident.
2. Shared/missing GSGs, unknown/negative caps, multiple views, absent/unsupported mip1 and partial metadata bypass honest completion or invent evidence.
3. Host fails to bind owner pointers, final terrain/material digests, clock interval, sparse offsets/UV/hash and the reference policy.
4. Cold -I-S bootstrap imports runtime dependencies early or private clones mutate old globals/lifecycle boundaries.
5. Cached bytes/cap bias/mip samples promote actual upload size, pixel owner, cause or repair. Independent hardware draws are deliberately outside this diagnostic.

### Task1: bounded cache/mip helper
Files: scripts/sdk3_prepared_texture.py,tests/test_sdk3_prepared_texture.py,reference-index and inert reference data.
Interface: POLICY,reference hash, minimum_bias(size,cap),texture_cache(texture,pgo),mip_metadata(texture),mip1_window(texture,uv,core).
- [x] Write tests first: literal bias11264/cap16384, unknowncap, readonly507510784B mip map four literal float bytes, no fullcopy/generation/prepare, missing mip no fetch, cache semantics. Run RED expected missing module assertion.
- [x] Implement minimal stdlib helper. Run named unittest GREEN and commit.

### Task2: native/host boundary
Files: scripts/sdk3_prepared_texture_native.py,scripts/run_sdk3_prepared_texture.py,tests/sdk3_prepared_texture_fixtures.py,tests/test_sdk3_prepared_texture_host.py,.github/workflows/sdk3-prepared-texture-v1.yml.
Interface: snapshot_prepared after old terrain snapshot; prepared.json; native command private adapter; host validation and request auth exact policies.
- [x] Tests first: real snapshot and sparse mip over CPU doubles, shared GSG dedup, missingoutput/cap/mip/partial failures, identity/hash/UV/offset/policy/count/claim mutation rejection, RSS limit32768/32769, cold help, old global invariance. RED expected missing entry.
- [x] Implement native/host wrappers and workflow; focused new+inherited unittest GREEN, actionlint; commit.

### Task3: review, exact CI, one actual and closeout
Interfaces: request-only activation, immutable runtime, independent raw artifact and pixels.
- [x] One fresh wholebranch review against spec/plan/ledger. Critical/Important one RED→GREEN fix pass; Minor defer.
- [x] Push new feature branch, create DraftPR based on PR141; exactsource push+PR four jobs and full unit counts PASS.
- [x] One fresh bounded diagnostic request. Authenticate run/attempt/activation/artifact/archive hashes, validate receiver, independently analyze cache caps/mip bytes and all14image SHA/pixels; retain raw and Git evidence, report actual limitations. No request rerun.
- [ ] Final evidence commit, exactfinal CI, DraftPR body/head/parent/main/original sixfiles preservation, archive own ledger and final external receipt; delete only own scratch. No publication/merge.
