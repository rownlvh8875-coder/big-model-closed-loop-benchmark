# Sole wholebranch review — source-built Cg/Eigen RUNPATH v3

Reviewed base `69d722b95818841f7956498fb9f5ee2f88c2d616` through HEAD `e78c439ae41c33ec16912f89bbd6e125155184ca`, using the requesting-code-review `code-reviewer.md` template. Read the review package first, design, implementation plan, every ledger Ruling, all seven new implementation modules, workflow, four new test files, and immutable helpers at the build/process/tool, source/input/dependency, ELF/provider/layout, and transport integration boundaries. Also inspected the pinned makepanda link construction/shell invocation and retained old link-command text as DATA.

Checkout/index/HEAD/refs were not changed. No subagents, rereview, SDK build/link/load, target execution, network mutation, image operation, or full-suite run was performed. The only executed verification command was the authorized focused unittest discovery. It passed **34 tests in 4.330 seconds**; its handwritten CPU artifacts were never loaded or executed. HEAD remained the requested SHA and `git status --short` was empty. The supplied split full-suite result (1,830 cases, 1,823 pass, seven skips) is recorded evidence, not a full-suite result independently rerun by this reviewer. Findings below are source-traced; additional mutation/reproduction commands were not executed because the review permits only the focused test command.

## Strengths

- The actual ELF check is applied to both retained libraries and requires exactly `$ORIGIN` RUNPATH with no RPATH. The bounded immutable ELF parser rejects duplicate loader tags. The shell fixture verifies literal-origin emission with both empty and spoofed ORIGIN, and the pinned makepanda implementation appends the quoted LDFLAGS to the command passed through `shell=True` as expected (`build_panda_sdk_cg_runpath.py:16–39`; `panda_sdk_cg_runpath_gate.py:9–19`).
- Production uses the immutable object-local `Inventory.select` through the pure v2 gate. Root RUNPATH is not propagated to CgGL; its own observed provider metadata supplies its Cg edge. Provider bytes are checked against frozen image identities, with no production selector override or global Cg package fallback.
- Selected success retains provider audits and explicitly leaves full dependency closure, full ABI, runtime mapping, prior-abort repair, installation, native admission, and Stage7 completion false. The independent consumer compares the retained provider diagnostics against recomputation, including missing rows (`accept_panda_sdk_cg_runpath.py:14–19`).
- V3 owns its guarded build orchestration and create-only latch. It calls measurement/input/process primitives, not the old guarded build or layout entrypoints. The request, branch, workflow, artifact, source closure, producer work root, and acceptance status have distinct v3 bindings.
- Command-first diagnostics, bounded streams, nonzero/timeout query evidence, post-gate downgrade, and oversized optional-candidate omission are useful improvements. The tests exercise real inert CPU ELF bytes, real process failures, and real ZIP extraction rather than only asserted metadata.

## Issues

### Critical

None found. These findings do not establish target execution, promotion of SDK2, or an unsound runtime-admission claim.

### Important

#### I1. Partial optional candidates can make the entire negative carrier unextractable

**Files:** `scripts/produce_panda_sdk_cg_runpath.py:122–129`, `:139–146`; integration with `scripts/panda_sdk_cg_runpath_carrier.py:35`.

**Problem:** The producer copies any existing candidate that is at or below its maximum size. Its DATA reader permits zero bytes, and neither the copying path nor failure sealing rejects an empty ELF/object or a descriptor shorter than 128 bytes. The consumer's carrier preflight rejects zero-byte non-log members and requires the descriptor to be exactly 128 bytes. Consequently the producer can seal a validly hashed negative receipt and logs into an artifact that its own consumer rejects before extracting any evidence.

**Reproduction:** In the existing failed-build packaging fixture, leave `work/build/sdk/lib/libpandagl.so` as an empty regular file, or leave `work/build/layout-build/layout-descriptor.data` with 127 bytes. Finalize and ZIP the failure bundle, then feed it to `extract_carrier`. The producer includes that member; preflight rejects it at line 35. Calling `seal_failure_bundle` does not repair either case because its filter only checks upper bounds. An interrupted compiler/linker or interrupted descriptor write can leave precisely these incomplete outputs. The current oversized-partial test and short-descriptor extractor test cover the two ends separately and miss this round trip.

**Effect:** One permitted hosted failure can lose the independently extractable command/stream/receipt diagnostics even though those diagnostics are otherwise intact. There is no permitted retry to recover them.

**Fix:** Apply the carrier's lower/exact extent rules before copying optional candidates and again when sealing an existing partial bundle. Omit/quarantine nonconforming candidates, record the member and reason, preserve the negative receipt/logs, and leave the slot closed. Add a production-finalization → ZIP → extraction negative test for each zero-byte candidate and short descriptor. Do not weaken the extractor's exact raw-descriptor rule.

#### I2. Tool reports are not bound to v3 owned measurement paths

**Files:** `scripts/panda_sdk_cg_runpath_evidence.py:52–54`; reused behavior in `scripts/build_panda_sdk_cg_eigen.py:34–44` (`tool_facts`).

**Problem:** The evidence checker compares tool facts and byte identities, but `tool_facts` deliberately excludes `evidence_path`, query `stdout_path`/`stderr_path`, and query result `cwd`. The v3 wrapper adds no ownership validation for those fields. Thus old SDK2 measurement locations, or absent query working-directory provenance, remain acceptable in a supposedly v3-coherent success carrier.

**Reproduction:** Start with the passing v3 success-shaped evidence fixture. Change each tool profile's `evidence_path` and each query stream path to the corresponding `stage7-panda-sdk-cg-eigen-candidate-02/producer/work/...` location, and set query result `cwd` to an unrelated or old location. Keep measured bytes/query outputs unchanged, and update the outer report file map as normal. None of these mutated fields is consulted by `validate_build_evidence` or the independent consumer. The existing passing fixture already supplies `/cpu/stdout.log` and `/cpu/stderr.log` and omits the query result `cwd` entirely, demonstrating the missing check without another execution.

**Effect:** A stale measurement report can be presented as fresh v3-owned provenance. This directly contradicts the promised rejection of v2-owned work/report bindings and weakens the independent freshness/coherence evidence, even though actual candidate ELF checks remain in place.

**Fix:** In the new v3 validator, require canonical profile paths under the exact v3 work root, the expected initial profile and postcheck/recheck forms, the query directories derived from each profile path, and query `cwd` equal to the reported repository root. Cross-bind the report profiles and query receipts/streams to their retained `host.log` records using the diagnostic manifest's ordered paths and saved lengths; the current validator does not read that log. Keep neutral v2 tool schemas and immutable helper code unchanged. Add one-at-a-time old-root/path/cwd mutations, including missing fields.

#### I3. Descriptor/configuration evidence contains unvalidated command and report relationships

**Files:** `scripts/panda_sdk_cg_runpath_evidence.py:64–65`, `:97`; `scripts/accept_panda_sdk_cg_runpath.py:40`; producer emission at `scripts/build_panda_sdk_cg_runpath.py:65–69` and `scripts/produce_panda_sdk_cg_runpath.py:119`.

**Problem:** Independent evidence validation checks the descriptor compile command but never checks `build.layout.macro_command`, its exact preprocessing argv/result/streams, or the relationship between `build.layout.effective_configuration` and the top-level effective configuration. Separately, `reports/layout.json` is emitted and hashed but is never compared with the descriptor's independently recomputed layout; the consumer compares only `reports/gate.json`'s embedded layout. Hashing an internally contradictory report does not establish its coherence.

**Reproduction:** The existing passing v3 success-shaped fixture inherits a `layout` object with no `macro_command` or nested `effective_configuration` at all, yet receives `records_coherent=True`. On a complete success-shaped carrier, replace the macro command with a failed or wrong-argv command while keeping the claimed top-level macros, or change `reports/layout.json` to different member offsets/class sizes and update its receipt file-map digest. The evidence checker and consumer have no reads/checks that reject those particular contradictions. The latter report can even be arbitrary nonempty JSON without affecting the checked gate layout.

**Effect:** Acceptance can certify coherent effective-configuration/descriptor evidence while its own retained preprocessing receipt says the measurement failed, or while its standalone layout report disagrees with the actual descriptor. These reports are central review artifacts for the selected-layout result; users reasonably expect them to describe the admitted static facts consistently.

**Fix:** Validate the exact derived macro-preprocessing command, successful owned execution, stream/hash relationships, and equality of nested/top-level/reported effective configuration. The required command and macro stdout bytes already survive in `host.log`: `collect_diagnostics` appends a relative-path header followed by each stream's saved bytes, with ordered paths/lengths in `receipt.diagnostics.streams`; positive carriers require no truncation. Reconstruct and bind those records, parse the retained macro stdout, and compare its measured macro subset/hash with the declared configuration. Compare `reports/layout.json` with `literal.verify_pair`'s actual result (and the retained gate layout). Ensure producer-side coherence validation covers these same relationships before sealing success. Extend the new fixture to include real-shaped macro provenance and add independent deletion, failure, argv, hash, nested-fact, and standalone-layout contradiction tests. No target execution is needed.

#### I4. Early hosted preflight failures escape before durable receipt creation

**Files:** `scripts/produce_panda_sdk_cg_runpath.py:148–151`, `:169–173`; `.github/workflows/panda-sdk-cg-runpath-build-v3.yml:30–38`.

**Problem:** After the Actions guard passes, request reading/parsing/closure validation, output setup, environment-context conversion, and `BuildClient` construction occur before the protected receipt/finalization lifecycle. A failure in these steps reaches `main`'s one-line console error without sealing a failure receipt. The upload step only warns when the bundle is absent, so the required negative artifact need not exist.

**Reproduction:** In a qualified Actions context, supply a malformed request or one whose closure fails validation. `a.validate_request` raises at line 149 before `out` or `receipt` exists. The workflow then runs its always-upload step against a nonexistent bundle. A setup failure after directory creation but before receipt initialization has the same missing-receipt outcome. This is a source-traced failure path; no request or hosted run was created during review.

**Effect:** The unique run is consumed with no SDK start, but its structured reason/context cannot be independently retained through the specified carrier. This violates the explicit failed-entrypoint/preflight diagnostic requirement and makes a non-retryable failure harder to close accurately.

**Fix:** Preserve local/unauthorized guard rejection, then establish a safe owned diagnostic lifecycle before fallible hosted request/bootstrap work. Seal a bounded blocked receipt and diagnostic details for these failures, using explicit unknown/unvalidated identity fields where necessary rather than inventing authenticated facts. Keep start count zero and no retry authority. Test valid Actions-context malformed request/closure failure and client/bootstrap failure through the entrypoint and artifact path, not just `record_failure` in isolation.

### Minor

#### M1. Dense multi-operation lines impede review of authority and failure boundaries

**Files:** `scripts/produce_panda_sdk_cg_runpath.py:149–156`; `scripts/accept_panda_sdk_cg_runpath.py:36–41`; `scripts/panda_sdk_cg_runpath_evidence.py:37–65`.

Large semicolon-separated lines combine authentication, resource checks, mutations, and report transitions. This made the placement of the bootstrap outside `try` and the unchecked report relationships harder to see. When touching these new modules, split stages into ordinary statements or small named helpers. This is a maintainability improvement, not a separate release blocker, and can be deferred under the one-fix-pass plan.

## Recommendations

Resolve I1–I4 in the permitted Important fix pass before source CI and the single hosted compile-only request. Concentrate additional tests on consumer-visible round trips and independent one-field contradictions; a passing producer helper test alone does not demonstrate that its negative artifact is consumable. Keep the frozen v2 code, source identities, SDK2 verdict, provider matcher, and one-start policy unchanged. Do not use a hosted SDK attempt to discover these local evidence-contract failures.

The overall design and namespace separation align with the plan. The four Important issues are omissions in the implementation's promised independent evidence and durable failure behavior, not reasons to relax the design or reinterpret SDK2. The ledger's inline-work, manual-brief, split genuine-filesystem test, immutable-wrapper, and narrow raw-log whitespace rulings are reasonable and do not explain away these gaps.

## Considered and declined / outside scope

- Actual SDK3 emitted ELF bytes and hosted success/failure: unobserved by design; the one future build is gated on this review and was not run.
- Runtime loader behavior, full provider closure, full object ABI, and SIGABRT repair: excluded from qualification; the code retains explicit false flags and the six strict provider-audit failures are not waived.
- Changing the immutable provider version/library matcher or adding a Cg/package fallback: outside the selected solution; the actual production path keeps the existing object-local selector.
- Revalidating or replaying consumed SDK2 source/request/build evidence: expressly prohibited; old files were read only as immutable integration context and negative controls.
- Independent remote host tool/header remeasurement: not provided by this carrier and explicitly disclaimed; I2 asks for report ownership/coherence, not impossible local remeasurement of the remote host.
- Broadening link-command validation into a complete hostile GCC-driver grammar: not required for the fixed source/environment contract; both actual ELF tags are checked, the permitted LDFLAGS is exact, and contradictory supported linker options tested here reject. No standalone security claim about arbitrary attacker-controlled compilers is made.
- Root-failure partial graph diagnostic retention inside the immutable v2 audit: not expanded here; the requested root-success/six-provider-failure case computes and retains the complete diagnostics. The review does not certify partial traversal diagnostics for all failed graphs.
- Rewriting frozen source/tree/ZIP/TLS primitives or defending against a malicious administrator changing the authenticated source: no new concrete integration defect was found at those reviewed boundaries; arbitrary upstream/platform compromise is outside this compile-only evidence task.
- Continuous integrity, hard cgroup containment, and exact ongoing workspace accounting: the design explicitly limits these to bounded process/output behavior and point-in-time observations; no stronger claim was treated as established.
- Hard runner termination, checkout failure, or artifact service outage before any Python code can run: outside an in-process receipt guarantee; I4 concerns ordinary catchable failures after the valid Actions guard, where durable diagnostics are implementable.
- Full-suite recomputation, preservation of every historical remote ref, future exact-source CI, request-only activation, and hosted artifact acceptance: restricted or future work for the executor; the reviewer verified only the allowed focused command and local read-only status.
- Source closure's exclusion of the new test files: the exact 310 identities are frozen by the approved contract and include the production workflow/modules; tests remain exercised by source CI. No closure expansion is requested.
- Neutral v2 descriptor/tool/input schema names and the frozen `native/panda_sdk_cg_v2` source path: intentionally reusable facts, unlike the owned producer/work paths called out in I2; these names are not themselves stale authorization.
- Macro/layout and report mutations were not dynamically executed beyond the allowed existing focused suite: authorization limited reviewer execution; source paths and the already-passing incomplete fixture supply the stated evidence, and the executor should add the proposed regressions in the fix pass.

## Assessment

**Ready to merge / proceed to the one hosted build? With fixes — not yet.**

The literal-RUNPATH mechanism, immutable provider selection, and restricted static verdict are soundly separated and the authorized 34-test suite passes. Fix the four Important failure-carrier and evidence-coherence gaps before consuming the sole hosted attempt; none warrants another SDK2 attempt or any runtime/scientific promotion.
