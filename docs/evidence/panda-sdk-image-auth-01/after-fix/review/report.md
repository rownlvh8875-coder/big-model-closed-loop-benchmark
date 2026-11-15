# Whole-branch senior review: SDK image authentication v1

Reviewed range: `16c690c0bfc586acf089ff15cb95431eb1412ca8..a1e2cdd4757300a5c1f0e8bb7affb8c3b3884994` in `/workspace/big-model-closed-loop-benchmark`.

**Verdict: Changes required before source activation.** No Critical issue found. Three Important issues and one Minor evidence omission follow. This is one fresh reviewer’s complete code gate, not an assertion of successful image production. Actual production remains NOT_RUN and actual source/run/artifact closeout belongs after this gate.

## Scope and evidence

Read all three added executable modules, the new workflow, all three test modules, plan/spec/review package and ledger rulings, and the relevant inherited transport, process, carrier ZIP, guarded tar/save, COPY layer, export, and inventory paths. All range changes are additions; no base-file edits were found. Repository status remained clean. No repository/index/branch writes, network calls, Docker daemon operations, SDK/native/library execution, or workflow activation occurred.

Independently ran the 14 added tests: all pass (2.000 seconds). CLI help/import checks also succeeded with isolated, site-disabled Python. Passing tests do not cover the consumer orchestration failure below. Safe offline reproductions are in `/tmp/panda-image-auth-review-diagnostics.py`; they use the real transport client with an in-memory response opener, a small ZIP, and a handwritten CPU child. The reported 1579-test full-suite result was read as existing evidence, not rerun or independently certified.

## Strengths

- External authority is established only in the live transport path; receipt semantics explicitly return external authority false. Caller-supplied source/activation/run expectations are checked against API-derived activation, workflow and run identities before artifact download.
- Request-only activation checks a single parent, a one-commit/one-file delta, regular file mode, and the actual Git blob identity. Source closure and immutable SDK/base pins prevent silent input replacement. Attempt, branch, actor, repository, workflow path and unique workflow-run checks reject the relevant replay/foreign cases.
- The reviewed workflow is push-filtered, uses pinned checkout/upload actions, disables persisted checkout credentials, requests read permissions, and never invokes a container start. The fixed recipe is FROM plus COPY; removal is preceded by owned-name/nonce/image/stopped-state checks.
- Image validation binds the actual archive, config digest and ordered diff IDs; the final COPY layer must contain the exact SDK file and ancestor directories. Producer export checks all 44,232 expected scoped file/link entries, while directory metadata and native/runtime authority remain expressly absent.
- The inherited transport retains bounded evidence and strips authorization on artifact redirects; guarded tar parsing checks hidden extension sizes before consuming them. Existing-output rejection and partial-file preservation are useful safeguards.

## Important issues

### I1 — Every first acceptance fails on duplicate API evidence filenames

**Location:** `scripts/accept_panda_sdk_image.py:26`; `scripts/produce_panda_sdk_image.py:42,52`; inherited `scripts/engine_clock_image_transport.py` `_json_url` existing-path rejection.

`accept_image` first calls `tree_request_mode` to find the request blob. It then calls `authenticate_context`, which calls `tree_request_mode` again on the same client. Both walks save `activation-tree-0.json`, `activation-tree-1.json`, and `activation-tree-2.json`. The client intentionally rejects an existing evidence file before making the next request. The second walk therefore always raises `IMAGE_TRANSPORT_REJECTED` on its first tree read, even for a completely valid run.

**Reproduction:** Run `/tmp/panda-image-auth-review-diagnostics.py` with the designated CPU Python. Two calls to the actual tree helper and actual Client, with valid in-memory tree responses, produce `duplicate_tree_call: IMAGE_TRANSPORT_REJECTED HTTP calls: 3 preserved files: 3`. Static tracing shows that exact two-walk sequence in the consumer.

**Impact:** The one-use producer could be consumed successfully but its output can never be accepted by this implementation. This is a deterministic first-use blocker, not a missing external-evidence complaint.

**Recommendation:** Give evidence reads distinct namespaces or explicitly reuse the already authenticated commit/tree result without weakening blob/activation checks. Add a full offline consumer orchestration test that uses the real evidence-writing transport boundary and reaches the download gate; isolated validator dictionary tests cannot catch this.

### I2 — ZIP metadata allocation and extraction time are not bounded before parsing

**Location:** new call sites `scripts/accept_panda_sdk_image.py:13,26` and `scripts/produce_panda_sdk_image.py:73`; inherited implementation `scripts/engine_clock_image_archive_v2.py:310–330`.

The new paths delegate to `extract_image_bundle`, which constructs `zipfile.ZipFile(stream)` before checking that there are exactly three members. The constructor reads the entire central directory and materializes every `ZipInfo`; the outer 2 GiB file limit is not a reasonable metadata allocation limit. Member name/extra/comment metadata is likewise consumed before any small carrier-specific bound. Extraction has no deadline parameter/check and accepts every compression method supported by stdlib instead of constraining the decoder and its resource behavior. Consequently the stated before-allocation ZIP/metadata and total-time contract is not implemented at this boundary.

**Reproduction:** The diagnostic creates a harmless 837,802-byte ZIP with 10,000 empty entries and instruments `ZipFile._RealGetContents`. Output: `ZIP parsed entries before policy rejection: 10000`, followed only then by `IMAGE_BUNDLE_REJECTED`. No oversized or dangerous allocation was attempted. Scaling toward the admitted archive size can allocate millions of Python objects before the three-member rejection. Inspecting the extraction loop confirms no elapsed-time check.

**Impact:** A malformed carrier can exhaust memory or exceed the caller's deadline before a controlled policy rejection. Digest authentication proves the bytes' origin; it does not implement the explicitly required parser resource limits. The new consumer must protect against malformed remote outputs as well as ordinary valid uploads.

**Recommendation:** Add a new bounded carrier implementation/wrapper without editing immutable historical helpers. Preflight EOCD/ZIP64 and central-directory sizes/counts, name/extra/comment budgets and permitted compression before constructing unbounded stdlib structures; apply a shared absolute extraction deadline and retain existing CRC, duplicate, symlink, closed-member, and decompressed-size checks. Test that rejection happens before the large read/object-allocation operation, not merely eventually.

### I3 — Docker child credentials are filtered by a short denylist, not excluded

**Location:** `scripts/produce_panda_sdk_image.py:23–25,31`.

`DockerData` copies the entire parent environment, then removes only four named token variables and selected loader/Docker endpoint variables. Other actual credential variables, including `GH_ENTERPRISE_TOKEN`, remain in every child environment. This does not meet review focus 3's stated boundary that Docker children cannot inherit credentials. The tests prove only the three names explicitly asserted in the handwritten child.

**Reproduction:** The diagnostic adds only a synthetic `GH_ENTERPRISE_TOKEN`, constructs the real DockerData boundary, and runs a handwritten CPU child through `call(['version'])`. It prints `extra_token_inherited=True`. No real secret was read or exposed.

**Impact:** Additional credentials in the runner environment cross into the Docker client and any children it invokes, despite the advertised separation. This finding does not claim that an extra real credential is currently configured or that any leak occurred.

**Recommendation:** Construct a deliberately small environment preserving only documented operational settings, including the explicitly authorized Docker config/proxy settings, rather than copying all environment variables. Pin safe executable search behavior where needed. Test multiple credential families and arbitrary injected secrets alongside the settings that genuinely must survive; do not solve this by adding only the reproduced token name.

## Minor issue

### M1 — Actual producer jobs are not retrieved for acceptance evidence

**Location:** `scripts/accept_panda_sdk_image.py:26–28`; `scripts/produce_panda_sdk_image.py:54–57`.

The spec says acceptance retrieves the actual successful run **and jobs**. The only `/jobs` calls here are for the two source-CI runs; no production-run jobs response is fetched or preserved. An authenticated successful run with this exact source-bound single-job workflow is meaningful authority, so I do not treat this as an origin bypass. It is a concrete evidence-completeness gap relative to the requested closeout. Retrieve and bind the producer jobs during acceptance, or explicitly record this omission and its consequence in the ledger. No cosmetic rewrite is requested.

## Recommendations for the authorized single fix pass

Fix I1–I3 together before activating the one-use branch; retain immutable historical code by putting new boundary logic in the new modules if needed. Add CPU-only regression tests that exercise integration and pre-allocation rejection, then run the required focused/full checks. Keep actual source CI, source-only activation, successful first producer execution and independent API/download acceptance as separate subsequent gates. Do not describe these static/test fixes as actual image provenance or native qualification. M1 can be handled as a recorded minor ruling if the authorized scope excludes minor polishing.

## Declined to judge / boundaries of this verdict

- **Actual new image provenance, artifact identity/digests, CI/run/job results, upload/download availability and successful first Actions execution:** no production was run and network actions were prohibited. Existing synthetic dictionaries are not external authority. These remain mandatory subsequent closeout evidence, not completed claims.
- **Current GitHub workflow registration/visibility, API eventual consistency, artifact retention/expiry and live API schema/version behavior:** reviewed the endpoint/field assumptions in code, but made no live requests. No additional concrete API incompatibility beyond I1 was established.
- **GitHub/TLS/runner/action compromise or a malicious authorized repository owner:** the selected trust model explicitly trusts API-authenticated source/run/artifact lineage; this review does not supply cryptographic build attestation, Sigstore or SLSA.
- **Actual hosted Docker version/daemon behavior, legacy builder availability, output layout, operation timing, free disk, and client executable sizes:** forbidden to invoke Docker; reviewed static recipe/arguments, parsers and resource gates only. A successful help/import check does not certify Docker producibility on the hosted runner.
- **Real loader, credential-helper and Docker config/proxy behavior:** exercised only handwritten CPU children, not real Docker or credential helpers. I3 demonstrates environment inheritance, not an observed credential exfiltration incident.
- **Native Panda/SDK/GL/MetaDrive/provider/model/ORT operation, mapped ABI, dispatch/install/lifetime behavior, actual driver compatibility, process-window-sink evidence and scientific canaries:** deliberately unexecuted and outside this bytes-and-lineage gate. Native allowance stays zero and Stage 7 remains incomplete.
- **Independent owner-side stopped export/runtime equivalence:** consumer intentionally relies on the authenticated producer export plus independent archive/layer/manifest parsing. The ledger explicitly accepts this limitation; no local Docker replay was performed or inferred.
- **Directory metadata, owners, xattrs, unscoped rootfs paths and runtime-excluded files:** excluded by the inherited inventory contract and expressly disclaimed. Exact file/link inventory does not broaden those claims.
- **Historical 5798-file content, 299 pins, 10 originals, prior drafts/main/native workflow histories and old SDK/local-image evidence as fresh external facts:** the diff shows additions only and the preservation records were available, but I did not reauthenticate or recompute every historical preservation record. Historical modules/evidence were not modified.
- **Full 1579-test execution and any unrelated old functionality:** the existing full-suite log was not rerun; independently ran only the 14 added tests and safe diagnostics appropriate to this review. Inherited code was examined insofar as the new executable paths rely on it, not recertified wholesale.
- **Memory/time exhaustion at maximum admitted sizes:** intentionally did not allocate gigabytes or run long exhaustion probes. I2 is supported by bounded instrumentation and control-flow inspection; exact worst-case resource consumption is not experimentally measured.
- **Final PR, exact final-HEAD CI, actual activation and final preservation/cleanup receipts:** later task gates, not part of this pre-activation code review. No merge, publication, cleanup of shared resources, or second review was performed.

No Critical finding is inferred from a hypothetical native execution or external attacker absent supporting evidence. The Important findings above suffice to withhold the code gate until the single authorized fix pass.
