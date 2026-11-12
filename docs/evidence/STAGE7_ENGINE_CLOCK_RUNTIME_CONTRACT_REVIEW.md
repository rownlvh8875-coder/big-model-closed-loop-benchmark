# Final whole-branch review

Reviewed `d7774ce40d62a19176ea2f5239edfc6644cf51ef..a2317468e3a3b4bf1a6e81a6c3d40c92e08331e3` using the supplied whole-branch package and current sources. **PASS with one minor documentation correction: 0 Critical, 0 Important, 1 Minor.** Suitable for Draft as pure metadata Task1 and an inactive future design. This is not image preparation, native admission or scientific approval. Subsequent status-only HEAD and baseline CI need separate receipts.

## Strengths

- Exact schema/types/literals and canonical core hash reject legacy/partial/unknown/NaN/duplicate inputs; ordered diffIDs stay binding and output is limited to64 field paths.
- Matching synthetic hashes never authorize native execution; inactive proposal validation separately returns execution_authorized=false.
- Original Important I1 is closed in corrected spec/plan and explicit same-shaped substitution regression; actual authentication remains Task3.
- Old source70/workflow44/registry8 bytes and historical terminal failure are preserved; new tool is outside consumed producer closure.
- Task2/3 inventory, Docker metadata, sanitization and streaming requirements are explicit future gates rather than fabricated current coverage.

## Findings

### Minor M1 — align completion wording with actual Task1 evidence

Locations: `docs/superpowers/plans/2026-11-12-engine-clock-runtime-contract.md:54`; `docs/superpowers/specs/2026-11-12-engine-clock-runtime-contract-design.md:90` and `:92`.

The checked plan item claims adjacent PID/nonce/ImageVersion provenance fixtures, but the test at tests/test_engine_clock_runtime_contract.py:179 only checks forbidden provenance and legacy/extra inputs; the matching test at :114 has no adjacent provenance fixtures. The spec closing handoff also still calls this documentation-only and Task1 the next task. Opening scope and actual implementation correctly say Task1 is complete.

Describe the actual rejection and standalone identity-match coverage without inventing unused-fixture evidence; label initial documentation-only statements historical and set the current next task to Task2. No production change or repeated full suite is needed.

No Critical or Important findings. The original design Important I1 is **closed**, not ignored: spec:86 and plan:53 now distinguish syntax/field comparison from object authenticity; test:122 permits a valid substituted hash, detects its differing field and never grants native admission, even when fabricated records match. Implementation:212 always returns native_admission=false.

## Evidence

Read the full change scope, Task1 report, plan/spec and historical design-review receipt. Verified exact HEAD, all current audit document hashes, source/test hashes, all five retained test-log hashes, six source reference hashes, saved70/44/8 preservation maps with zero mismatches, five official successful response hashes and retention of three unavailable paths. No full diff was regenerated. No tests, native imports, Docker, network, Git mutations or raw replay were performed.

Retained evidence records meaningful17-test missing-implementation RED; initial16-pass/1 guard-fixture failure; corrected focused17/0.498s; one full661/73.571s with7 expected optional-dependency skips. These are retained execution receipts, not reviewer reruns. The corrected guard permits pathlib's urllib.parse while blocking external/native/process imports. Source and test hashes match those receipts.

Legacy ImageVersion equality is untouched. The new parser rejects old/partial/version-only records and provenance envelopes; strict core host/kernel/CPU/engine differences bind or reject. It has no outer ImageVersion input or actual preflight authenticity check. No projection of historical records is implemented.

C30dcc remains accepted and Aab0ef77 remains an authentic terminal runtime failure solely on recorded ImageVersion, with7 null aggregates and4cases/6comparisons not run; no allocation witness or reusable allowance is inferred. Proposal has16 null preparation references, zero native allowance and preparation/admission false. Strict FAIL, expanded NOT_RUN, geometry/optics/full-S unvalidated, Stage7 INCOMPLETE, main official calls0, Cloud unpublished and Draft unmerged remain the stated boundaries.

## Declined to judge

- **Actual image/archive/config/diffID object authentication and API/container association:** Task3 is unimplemented and all16 preparation references remain null; Task1 parses and compares opaque metadata only.
- **Closed installed-tree collection, missing/extra files, modes, symlink escapes/cycles, alias traversal and filesystem race resistance:** Task2 is unimplemented. Spec constrains closed roots, bounded traversal and exact four Docker metadata exclusions; no collector behavior or coverage is claimed.
- **Concrete Docker-managed /etc compatibility and legitimate alias layouts:** Only design rules exist, including exact /etc/mtab exception; actual image layouts require Task2/3 evidence.
- **Sanitized actual host/container evidence, env-only forgery rejection, Config.Env/token/proxy redaction and image streaming transport:** Future Task3 tests and adapter are explicit; no API/Docker/image artifact exists. Current CLI path-only errors/comparisons were reviewed separately.
- **Real dependency lock compatibility, prepared image feasibility, disk/hash/load/download costs and Docker compatibility:** Unavailable future evidence; limits are proposed caps, not measurements or activation.
- **Actual GL/driver/plugin selection, GPU identity/freshness, pixels, cache hits, physical-host equality and observer neutrality:** Outside stated assurance and no native probing authorized.
- **Future native FD/PID/ancestry/group/reaping integration and revised budgets:** Requires a separately registered native protocol after accepted provider-free evidence; old allowance cannot be reused.
- **Fresh historical raw/archive replay or proof of zero allocation in terminal ABBA:** Replay prohibited and unnecessary; retained source bindings and null aggregates are preserved, not freshly attested.
- **Live CI, PR, main and Cloud service state or later status-only HEAD:** Review is exact local HEAD; root owns subsequent remote/CI observations and must report them separately.
- **Independent repetition of full/focused test suites:** Explicitly disallowed absent an uncovered behavioral doubt. Exact source/test/log hashes and retained 17 focused/661 full result were checked; no unresolved runtime doubt warranted a rerun.

## Review identity

JSON SHA256: `771e987e1f802f1ed8c48eaa2fed385f2e9b0beb4395d29fc6c386e2ba7030a8`. Exact reviewed HEAD: `a2317468e3a3b4bf1a6e81a6c3d40c92e08331e3`. Only this report and its JSON companion were written. M1 is a documented minor for root closure; no hidden deferred production findings.
