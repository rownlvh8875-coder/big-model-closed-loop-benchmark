# Sole fresh wholebranch review: SDK dispatch canary v1

## Scope and method

Reviewed base `1a307f4f4c0db10326ea2bbb3f980dd7e0ef1a0a` through head `950b48c09216541589c4ac8549f0046a23fed3ea` against the complete review package, specification, implementation plan, and every ledger Ruling. This is the one requested wholebranch review, not a rereview. Reviewed all new native/Python/workflow/test/data interfaces and relevant reused process, ELF, build, image and transport boundaries. Evidence JSON arrays and logs were treated as historical snapshots, not executable implementation modules.

Work was read-only in the repository and Git index/refs. No subagents, actual SDK/Panda/GL loads, Docker commands, hosted workflow execution, downloads, or old-output deletion occurred. Only authorized handwritten CPU test components were executed. This report is the reviewer's sole durable output.

Independent verification:

- `/workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B -m unittest tests.test_panda_sdk_dispatch_probe tests.test_panda_sdk_dispatch_runtime tests.test_panda_sdk_dispatch_flow -v`: **27 tests passed in 4.870 seconds**.
- Independent recursive Git tree comparison: all **6,671 base files and their modes/blob identities remain unchanged** at reviewed head.
- Independently recomputed source closure: **250 entries**, exactly equal to the committed before-review closure.
- Data-only reconstruction of the committed SDK executable profile passes against pinned SDK SHA `8d302ae2a610b56db4f7feca08fd736004cf6d3d9650fdb9834f19389a0b7342`.
- Git status was clean during review.

## Strengths

The implementation keeps the extra first-party probe explicitly separate from immutable-image membership. Its successful build receipt retains ELF bytes, source/project hashes, five tool identities, fixed command, and executable profile. The parent checks actual process executable bytes for both objects at two checkpoints, and wrapper/original addresses must belong to the respective verified code ranges. The child invokes the already opened SDK handle; there are no executable Python callback trampolines.

The probe exercises actual typed dispatch wrappers in the CPU-equivalent test target rather than manufacturing expected counters in Python. The forwarded argument/return trace, errno observations, bootstrap replay, buffer deletion, separate context state, deferred destruction, release, handle reuse, and adapter/cache guards are checked together. Production loading remains separately gated and cannot enter local fixture mode.

The new request, workflow, artifact name, branch, source closure, mapping-acceptance pin, source CI, request-only activation, unique run, attempt and production job gates are distinct from consumed histories. Fixed Docker argument validation, isolated runtime context checks, the pre-start consumed marker, private challenge pipes, and owned cleanup preserve the intended narrow authority. Failed probe reports and bounded failed-start binary output remain negative evidence, with no native/scientific promotion.

## Critical findings

**None.**

## Important findings

**None.** No demonstrated issue warrants blocking this implementation or consuming an Important fix pass on speculation.

## Minor findings

### M1 — Failed probe builds lose structured build provenance

**Files:** `scripts/panda_sdk_dispatch_probe.py:31`, `scripts/panda_sdk_dispatch_probe.py:33`, `scripts/run_panda_sdk_dispatch_canary.py:107`.

**Trigger and evidence:** The builder computes the pre-build project/tool identities and command record in local variables, but only returns them after compilation, post-build checks and ELF/dependency validation all succeed. If the compiler exits nonzero, or a subsequent build check rejects, `build_probe` raises and the caller's `probe_build` remains `None`. The no-Docker finalizer exports only `.stdout`/`.stderr` text files and `probe_build: null`; it does not export the available command, exit code, duration, pre-build tool identities, or partial post-build observations. The reused `cpu.run_command` does not independently persist that structured receipt.

**Actual user effect:** A genuine hosted preparation failure remains safely failed and its compiler diagnostic text is retained, but the downloaded three-file artifact lacks useful build provenance for diagnosing the only hosted attempt. A compiler that fails without diagnostic output is especially difficult to investigate. This is a diagnostic/evidence completeness issue, not an authority bypass or a false successful SDK observation; therefore **Minor**, not Important.

**Suggested fix:** In a future permitted change, persist a bounded incremental build receipt before compilation and attach it to a typed build exception (or read it into the failure bundle). Preserve command/return status and all already observed identities while explicitly marking unavailable post-build checks and output identity as unqualified. A CPU-only forced compiler failure can verify artifact retention. Deferring this minor is consistent with the stipulated no-polishing pass.

## Review Focus disposition

1. **Probe identity:** Successful production flow binds the reviewed source and six project inputs to actual compiler observations, ELF bytes and runtime PT code. The extra file is explicitly source-bound, not authenticated-image membership. Full compiler/system-header closure is explicitly excluded. M1 covers partial build-failure provenance only.
2. **Installed dispatch observations:** The source implements typed original forwarding and command lifecycle observations, and independent handwritten CPU tests pass. The installed-SDK execution path is present and appropriately gated; no actual installed observation is claimed by this review.
3. **New permissions and origin:** Closed new authority prevents substituting old request identities or permissions. CI, activation, unique run and consumer job/artifact checks are present. Review completion is an executor-controlled procedural prerequisite; this review does not invent an additional automated review-attestation requirement.
4. **Parent, restrictions and partial failure:** Examined private-pipe ownership, process/code/maps verification, fixed create/start arguments, runtime context checks, consumed-before-start persistence, timeout capture and verified owned kill/removal. No demonstrated blocking failure was found. Point-in-time observations are not continuous immutability guarantees.
5. **Failure preservation and claim scope:** Structured ABI failures and bounded failed-start bytes are retained as failures. Compilation failure output is retained with the minor provenance limitation above. Object/GPU/native/scientific readiness remains false throughout the supported outcome paths.

## Declined to judge — exhaustive exclusions for this review

The following are explicitly not certified; none is silently treated as complete or as a blocking code finding:

1. **Actual new hosted dispatch success, failure, or consumption:** NOT_RUN/unqualified at review time. Executing the real window is prohibited for this reviewer and remains executor-owned.
2. **Actual installed SDK bootstrap/live counts, errno, forwarding, deletion, context reuse or C ABI behavior:** Only handwritten CPU equivalents were executed. The production code can measure these, but this review cannot supply the measurements.
3. **Actual hosted probe compiler/output identity or cross-image loader compatibility:** No hosted build or real probe-plus-SDK load occurred. Static inspection and local probe builds do not establish those future facts.
4. **Full system-header, compiler-spec/plugin, toolchain or reproducible-build closure:** The ledger explicitly accepts limited five-tool/project-input provenance and leaves broader host provenance unqualified. This review does not upgrade it or require a new toolchain project.
5. **Future canonical reviewed-source CI, request-only activation, live API lineage, unique run/job/artifact and authenticated external acceptance:** Inspected code and CPU/memory API tests only; future real API receipts remain executor-owned.
6. **Future final-head CI, Draft PR/body, final result commit, output receipt and cleanup completion:** Plan items are expressly unfinished and not evidence against the current implementation's claimed milestone.
7. **Fresh external preservation of main, Drafts 102–118, eight native histories, three image histories and consumed mapping01 during this review:** Historical preservation snapshots were available, and all base file blobs/modes were independently preserved, but no fresh network queries were authorized or made. This is not a certification of current remote state.
8. **Full local 1,681-case matrix and spacious-shm capacity case:** Historical logs were considered but not independently rerun; independent execution was limited to the authorized 27 focused tests.
9. **Actual Docker/kernel/cgroup/seccomp, namespace, filesystem and timeout cleanup behavior on the future hosted runner:** Fixed code paths and fake-CLI tests were reviewed; no real container was created, started, inspected or removed.
10. **Global absence of initializer GL activity or arbitrary behavior within every image dependency:** The spec allows normal dependency initializer lifecycle and explicitly does not certify global initializer GL-freedom.
11. **Continuous process-code immutability, all data/GOT relocations, global symbol interposition correctness or arbitrary hostile host/compiler compromise:** The contract supplies authenticated origin plus bounded point-in-time executable-code checks; it does not claim continuous attestation or a hostile-host proof.
12. **Real Panda C++ object/Texture/GSG ABI, real GLX contexts, original GPU dispatch, rendering, pixel freshness or hardware-driver state:** Deliberately outside this CPU-original dispatch contract.
13. **Producer/sink delivery, RGB/I420, Panda Python, MetaDrive, model/official ORT/ONNX execution, scientific equality/divergence/performance and the official four-condition/eight-process cohort:** None is exercised or admitted by this canary.
14. **Registry/Cloud publication, image rebuild, merge/main/shared-base updates or old request replay:** Outside authorization and not performed; no readiness recommendation for these actions is implied.
15. **Broad redesign of immutable consumed engines or exhaustive independent audit of their historical contracts:** Inspected relevant reused interfaces for this branch's integration. Preserving their bytes is intentional; this is not a renewed certification of every earlier implementation.

## Assessment

**Implementation review outcome: no blocking findings; 0 Critical, 0 Important, 1 Minor.** The reviewed branch is suitable to proceed to its already specified executor-owned source CI and gated one-use hosted attempt, subject to their own checks. This is not approval of an unobserved canary result, authenticated acceptance, merge, publication or scientific admission. The current new dispatch window remains **NOT_RUN/unqualified**, with scientific allowance **0**, strict result **0/4 FAIL**, and **Stage7 INCOMPLETE**. No rereview was performed or requested.
