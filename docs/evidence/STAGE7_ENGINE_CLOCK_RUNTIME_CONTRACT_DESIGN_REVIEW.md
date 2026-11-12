# Engine-clock runtime contract design review

Reviewed `d7774ce40d62a19176ea2f5239edfc6644cf51ef..04c91d108cae25b1426529446f1bf4197bd9c710` from the supplied package. Its six document contents match the current files. No Git, network, tests, project imports, native execution or image operations were used. Only this report and its JSON companion were written.

**Verdict: WITH FIXES — 0 Critical, 1 Important, 0 Minor.** The design direction, inactive proposal and preserved evidence are suitable for a docs-only Draft. Correct I1 before describing the next pure metadata implementation contract as ready. Existing baseline CI remains pending on the final docs push; image preparation and native admission remain false.

## Strengths

- Docker-save archive SHA, Docker config digest, ordered diffIDs and closed installed-file manifest are separate bindings; registry publication is unnecessary.
- The strict observed host profile, installed contents and actual native selection have distinct assurance limits. No deterministic-pixel, GPU-freshness, physical-host or observer-neutrality proof is claimed.
- Current/future gates are separate. The proposal remains `INACTIVE_DESIGN_ONLY`, `execution_authorized=false`, with 16 null preparation references and zero native allowances.
- Old source/runtime gates and consumed registry bytes are preserved. C=`30dcc5b4075dd2cfaf25b3e8d90e324386a278af` remains accepted; A=`ab0ef77ab318a0683bdddb896e1e9db6b79e79e6` remains an authentic terminal acceptance failure. The ImageVersion difference is `20261111.370.1` versus `20261101.360.1`; all seven aggregates remain null, four cases/six comparisons were not run, and neither zero allocation nor reusable allowance is inferred.

## Findings

### Important I1 — Task 1 cannot infer a digest's object class from its text

Location: `docs/superpowers/plans/2026-11-12-engine-clock-runtime-contract.md:53`. Related: `docs/superpowers/plans/2026-11-12-engine-clock-runtime-contract.md:41`, `docs/superpowers/specs/2026-11-12-engine-clock-runtime-contract-design.md:55`, `docs/superpowers/specs/2026-11-12-engine-clock-runtime-contract-design.md:59`, `docs/superpowers/specs/2026-11-12-engine-clock-runtime-contract-design.md:86`, `docs/STAGE7_CONTINUATION.md:11`.

The required test says “tag/index/config/archive substitutions do not parse,” while Task 1 accepts only identity dictionaries and has no artifact/API/Docker inputs. A registry manifest/index digest, config digest and diffID share the same `sha256:<64hex>` syntax. Put a well-formed manifest digest into `config_digest` and recompute `core_sha256`: the specified shape parser has no evidence that identifies the referenced object's class. The same limitation applies to well-formed opaque archive SHA values. Comparison can detect a changed value against an expected identity; parsing alone cannot authenticate its origin.

This is an important plan defect: an implementer must invent an impossible check, expand the pure-tool boundary, or disregard an explicit required test. Restrict Task 1 to exact fields/literals, digest encoding, self-hash consistency and expected-field comparison. Wrong encodings/typed fields reject; changed well-formed values mismatch a different expected identity. Assign semantic object-class authentication to Task 3 using the authenticated archive and actual config/rootfs evidence. Clarify the spec test allocation and continuation summary without weakening the later artifact checks.

Expected verification after correction: a same-shaped substituted digest may pass shape validation but must mismatch a different expected identity; Task 3 rejects a manifest/index digest asserted as the authenticated archive's config.

No Critical or Minor findings.

## Builder check

1. How should Task 1 handle a well-formed manifest/index digest placed in `config_digest` with a consistent self-hash when no object evidence is an input? This changes the testable implementation contract. The existing pure metadata scope supports deferring semantic authentication to Task 3, and root can settle that correction under the delegated design authority.

Other important builder questions: **nothing important left**. Routine implementation choices do not need a new user decision.

## Evidence and preservation

- Saved maps match every current source70/workflow44/consumed-registry8 file; the current workflow count is 44. Compact producer70 SHA256 remains `6f8dcc2fc4aa7b1896a74d43ea4e030f89729b4b7851825cd0bbd444c6acab04`.
- All four recorded audit document hashes and all six source-reference hashes match. Source text supports the described metadata-only runtime recording and complete old runtime equality; no native module was imported.
- Five successful saved official responses match their size/SHA256 records, including the three immutable Git blob IDs. All three failed GitHub paths remain saved as unavailable; both official Docker HTML fallbacks are present and hash-correct. References support design principles, not the particular scheduling cause or historical binary equality.
- Current proposal semantics and absent future tool/collector/Dockerfile/adapter/example paths are consistent with the docs-only scope. Current Markdown links resolve. No new runtime tests exist or were run.
- Raw/controller histories were untouched; they were not replayed or freshly attested. Strict FAIL, expanded NOT_RUN, geometry/optics/full-S unvalidated and Stage7 INCOMPLETE remain.

| Reviewed document | SHA256 |
| --- | --- |
| `docs/STAGE7_CONTINUATION.md` | `7abd8e616018f1a72d460fc24526b89b0489482f394007920a3cf730f0935775` |
| `docs/STAGE7_ENGINE_CLOCK_RUNTIME_CONTRACT.md` | `0fa966cd6767bd72fe8e55642f1f43879c147364d3dba1a6c3dc8c0dfc9ec553` |
| `docs/evidence/STAGE7_ENGINE_CLOCK_RUNTIME_CONTRACT_AUDIT.json` | `4d64f2a8a67051874d583112eeafd3a1797b47ee97705a5c47e4595bc753e2a8` |
| `docs/evidence/STAGE7_ENGINE_CLOCK_RUNTIME_CONTRACT_PROPOSAL.json` | `ab1631a7fc9c07ad6c5cd8c0ef0e61afdf6c4857ea6c93502d7d29fa01010ad0` |
| `docs/superpowers/plans/2026-11-12-engine-clock-runtime-contract.md` | `9958d53e2ad6f9aba80d12c260514769bd727f71b8352a826389743ff9d2ad2f` |
| `docs/superpowers/specs/2026-11-12-engine-clock-runtime-contract-design.md` | `df93ac7e2aebaa3e46785e3fedabdd51d082c485f8b4d75cbd6c8f79ff95be02` |

The package SHA256 is `fcae96ac77550f4b92f1df4920ee9f1c96797106600255210ddf2fdeb253d7c3`; saved reference-index SHA256 is `3ab663b59873e21d3f42c6e97327a1e861c62a4ca2f0cfe96ee0f814619aa3ee`. Full source/map/reference hashes and check results are in `design-review.json`.

## Declined to judge

- Actual image preparation, complete dependency-lock compatibility and measured storage/download/hash/load feasibility: Explicitly unavailable future Task 3 evidence with 16 null preparation references; current design grants no preparation execution.
- Actual archive/config/diffID object authentication and authentic API/container association: No prepared artifact or adapter exists. Future Task 3 is the correct evidence boundary; I1 addresses the conflicting Task 1 promise rather than accepting it.
- Concrete installed-tree collection, alias layouts, symlink traversal and filesystem race resistance: No Task 2 collector is implemented. The closed inventory and read-only-root rules provide design constraints; detailed collector behavior requires its separate implementation/review.
- Actual GL/driver/plugin selection, GPU identity/freshness, deterministic pixels, cache hits, identical physical hosts and observer neutrality: The design explicitly excludes these assurances. No authorized native probe or evidence exists.
- Future native FD/PID/group/ancestry/reaping integration and revised scientific budgets: Reserved for a separate new native protocol after provider-free acceptance; this increment cannot activate it or reuse consumed allowance.
- Independent historical raw/archive replay and proof of zero allocation in the failed ABBA: Replay/download/extraction are excluded. Saved source-bound rejection/registry records preserve seven null aggregates and do not claim zero allocation.
- Live GitHub CI/PR/main and Cloud service state: Root owns Git/CI and remote observations; this review uses the supplied exact-HEAD package and saved audit. Baseline CI is explicitly pending after the final docs push.
- New tool runtime behavior, code-quality tests and a complete CPU suite: Future Task 1 code/tests do not exist and the increment is documentation-only. No test/native execution was authorized or needed for the byte/semantic review.
- Routine module structure, exception names, diff record encoding and other builder-owned implementation choices: A competent implementer can choose these without changing the metadata-only contract or authorization scope.

## Pending evidence and readiness

I1 requires a documentation correction and review of its new exact HEAD. Root then records the existing baseline CI result on the final docs push. Future Task 1 still needs its implementation and meaningful pure fixtures; Task 2 remains a separate collector gate. Real locks/recipe/archive/config/diffIDs/manifest/preparation/launch evidence and measured resource/Docker feasibility remain absent future Task 3 requirements. A new native protocol/source/canary/acceptance/budget design is later still. This review grants no preparation, native or model execution and no scientific PASS.
