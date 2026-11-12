# Task 2 fresh whole-branch review

Reviewed base: `2cc22c0e82dde25429a3f0216a3eb7405b127d5b`  
Reviewed head: `e0fc6f33e29732052c3619390b3a4dfd53a5bb62`

## Strengths

The module separates pure metadata validation from caller-root IO, performs descriptor-relative nofollow reads, checks file identity before/after hashing, and uses a second metadata pass without duplicate payload reads. Exclusions are narrow and inspected without payload reads. Controlled exception messages, bounded partial receipts and unconditional `native_admission=false` preserve useful assurance and privacy boundaries. Documentation clearly distinguishes synthetic inventory matching from image authenticity and native approval.

I read all nine changed files, the complete module and all 30 tests, binding addendum, parent design/plan, brief/report and six current Task2 rulings. Source/test hashes and every reported log hash matched. Final saved logs show 30 tests in 0.339s and 691 tests in 79.388s, seven optional native skips. Producer70/workflows44/registries8/Task1 three files match both their reported hashes and base bytes. I did not duplicate either suite.

## Issues

### Critical

None found.

### Important

**I1 — A dangling required-root alias is accepted as complete.** `scripts/engine_clock_runtime_inventory.py:126` (also unknown-node handling at line 134 and final-node-only root check at lines 419–420).

`_resolve` allows an absent intermediate node, then erases it when processing `..`. Consequently `/lib -> usr/missing/..` becomes `/usr` in the logical graph although POSIX resolution stops with ENOENT at `missing`. The final directory check accepts the existing `/usr`. This breaks the binding requirement that each declared root resolve to an actual directory and produces a false complete receipt.

Concrete narrow reproduction retained at `/tmp/task2-review-root-alias-5h4q8wyu`: create all required plain directories except `/lib`; create `/lib` as a relative symlink whose target is exactly `usr/missing/..`; leave `/usr/missing` absent. Supply all six roots, exact exclusions and the lone `/lib` symlink descriptor. With a five-second absolute deadline, collection returned `INSTALLED_FILES_MATCH`, `complete=true`, `bytes_read=0`, `native_admission=false`, while `(root/'lib').is_dir()` returned false. Expected: `FAILED_OR_INCOMPLETE`. This reproduction uses only a new tiny temporary tree; no host/image scan or native operation was performed.

Fix root resolution against the observed graph to require existing traversable directory components before processing later components, including `..`. Do not eliminate the separate allowed non-root dangling-link case or assume metadata-only graphs contain empty directories. Add a real-tree regression for this false success and retain valid alias/dotdot coverage. The absent native admission limits severity to Important.

### Minor

None found.

## Recommendations

Resolve I1 in the authorized single TDD fix pass, retain meaningful RED/GREEN evidence and distinguish this reviewed HEAD from any corrected or receipt-only HEAD. Keep image authentication and actual preparation in separately gated Task3.

## Declined to judge

- Task1 identity equality, legacy rejection, host ImageVersion semantics and CLI internals: frozen prior increment; checked byte preservation, not re-reviewed.
- Actual image/archive/config/diffID authenticity, dependency closure, lock inputs and preparation: unimplemented Task3, not established by caller manifests or fixture hashes.
- Forged environment-only container claims and sanitized Docker/API/Config.Env evidence: no adapter exists in Task2; Task3 must implement and test these independently.
- Actual Docker-managed mount compatibility, same-device bind mounts and mount authentication: device checks are not mount attestation; explicitly deferred.
- Physical-host authenticity, compromised-host resistance, malicious same-process monkeypatching and hostile concurrent manifest mutation: outside this local trusted-caller verifier threat model.
- Atomic snapshot and changes after the last observation, including same-content ABA or caller-root path replacement after opening: two observed passes are explicitly not an immutable-root proof.
- Loaded GL/driver selection, native provider behavior, GPU freshness, cache hits, deterministic pixels, model/ORT and scientific conclusions: not exercised or admitted by Task2.
- Observer neutrality, full-image resource feasibility and production-scale throughput: three-byte fixture timing and CPU test logs cannot establish these.
- Non-main-thread, non-POSIX and existing-process-timer support, kernel uninterruptible IO and hard real-time scheduling: explicit fail-closed/support limits in ruling six.
- External legitimate image aliases, layouts beyond the six bases, directory-mode identity, empty-directory identity and loadability of non-root dangling links: explicit restricted scope/identity choices; root-directory existence is still required and is the reported finding.
- Broad suite reruns and optional native integration skips: accepted hash-verified root logs as instructed; did not run native dependencies or duplicate suites.
- Remote CI, PR state, merge/publication and later receipt-only HEAD: owned by root; no network actions or approval inferred from this technical assessment.
- Historical raw ABBA archives, consumed allowance and controller histories: no replay or fresh authenticity audit; branch scope/protected-file preservation checked and existing terminal failure retained.

## Assessment

**Ready to merge? With fixes (technical scope only).** One demonstrated false-complete root-alias result needs correction; the rest of the reviewed change aligns with the limited Task2 contract and preserved evidence. Keep Draft/unmerged, native admission false, and Task3 unimplemented; this review provides no image or native authenticity approval.
