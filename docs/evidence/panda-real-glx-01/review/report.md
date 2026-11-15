# Senior Code Reviewer report — sole fresh wholebranch review

Reviewed range: `01ac0eeb72124870f9c91580d795d3b1222e25ea..c8e2b78c7206ba2d18e69a1b6b6ae9e6144af98d`.
Repository: `/workspace/big-model-closed-loop-benchmark`.
Review date: 2026-11-15. One reviewer, no subagents or rereview.

## Scope and evidence

Read the complete review package, spec, plan, ledger including all six Rulings, new executable modules, workflow, handwritten fixtures/tests, profile/preflight and result/continuation documents. Inspected relevant existing process-code verification and producer helpers as read-only dependencies. Treated retained historical records as evidence, not newly executable authority. Reviewed the new default-off SDK/Panda/softpipe contract against its stated limits rather than requiring physical GPU, complete C++ ABI, active capture or scientific qualification.

HEAD matched the requested head; git status was clean. Independently compared Git trees: all 6,844 base entries retain their object IDs and modes. Independently recomputed the source closure: all 260 entries exactly match `docs/evidence/panda-real-glx-01/before-review/source-closure.json`.

Executed only the authorized focused command:

`/workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B -m unittest tests.test_panda_real_glx_objects tests.test_panda_real_glx_runtime tests.test_panda_real_glx_flow -v`

Result: **30 tests passed in 2.217 seconds**. These compile/load only the handwritten CPU fixture and run fake server/Docker processes; no actual SDK/Panda/GL/Xvfb/Docker window was executed. The implementation's recorded full local matrix is 1,711 cases including the separate spacious-shm capacity case; this review did not rerun or independently certify that full matrix.

## Strengths

- Separate policy, workflow, request, producer and consumer keep the new resource/GL permissions out of consumed histories. The exact source closure, request-only activation, two source CI runs/four jobs, unique attempt/run, production job and artifact checks form a coherent external-origin chain. Pure receipt validation explicitly grants no external origin.
- The child uses an explicit pandagl factory and owned engine/output/texture/camera, with a software-renderer check, two bounded parent challenges and strict pixel/count/hash/order validation. Fake objects cannot grant actual-driver authority. Cleanup reports selected output/RAM observations without claiming full C++ deallocation.
- Full SDK executable ranges and the selected libGL entry/slot are observed at three checkpoints. Streamed file identity checks bind inode/device, stable metadata and authenticated content while accommodating large libraries. Generated executable regions and shared driver RAM have separate bounds and are not represented as authenticated image-origin code.
- The private protocol, recorded PID/start identities, owned process groups, server startup/finalization and container consumed marker provide bounded failure handling. The CPU tests exercise timeout, invalid/binary output retention, unexpected server exit, snapshot failure and repeat-start rejection.
- The container configuration explicitly limits memory, CPU, PIDs, time and tmpfs, separates namespaces and removes privileges. Read-only image/source bindings and fixed environment/argv avoid forwarding hosted credentials into the native window.
- Failure bundles retain available wire bytes with size/hash/base64 information, while successful interpretation still requires the closed runtime and external acceptance chain. The current documents consistently mark the actual new window NOT_RUN/unqualified and preserve scientific allowance zero, strict 0/4 FAIL and Stage7 INCOMPLETE.

## Critical findings

None.

## Important findings

None.

## Minor findings

### M1 — Failed acceptance still asserts an unconditionally default-off observer

**Location:** `scripts/accept_panda_real_glx_canary.py:31` (the `result.update(...)` in `accept_canary`).

**Effect:** Both successful and authenticated failed receipts set `source_observer_default_off=True`. Failed receipts are intentionally allowed without successful runtime semantics, and can represent failure before stats collection or failure precisely because the child's stats were not all zero. In either case the top-level acceptance field asserts an observation that was not established and may contradict the retained failure. The failed status and false software-object qualification prevent this from granting successful runtime/scientific authority, so this is nonblocking reporting accuracy rather than an Important qualification bypass.

**Fix:** Make this field express verified evidence only (for example, true only when validated successful semantics establish it, otherwise null/unknown), or explicitly name it as the requested policy rather than an observed result. Add a small CPU case covering an authenticated failed receipt with missing or nonzero observer stats if this is addressed in later authorized work. Do not expand the current review into a minor-polishing pass.

## Declined to judge

1. Actual installed Panda 1.10.13 API compatibility, output creation, GLX initialization and softpipe availability. No actual image execution was authorized for this review; fake API success is not evidence of real compatibility.
2. The outcome of the new real GLX attempt, including whether any frame is actually rendered/read and whether actual output/RAM cleanup succeeds. The attempt is still NOT_RUN/unqualified.
3. Physical GPU identity, acceleration, device isolation in a hardware deployment, or performance. This is explicitly a software-driver canary.
4. Full C++ ABI compatibility, complete object lifetime/deallocation, allocator correctness or all internal GLX context counts. Selected pointers/types and engine output/RAM observations do not establish those properties.
5. Continuous code immutability between checkpoints; generated-code origin, continuity or JIT attestation; complete GLVND/vendor/TLS dispatch or proof that every actual read traverses the selected slot. The code records bounded point-in-time evidence and expressly limits those claims.
6. Image origin for generated executable regions and private driver shared RAM. Their bounded allowance is intentional; their origins remain unqualified.
7. Active SDK observer/capture/cache/bridge/sink behavior, read-binding mutation, production RGB/I420 readback, or capture arming. These are outside the default-off window.
8. MetaDrive geometry/assets/scenes, official model/ORT behavior, MDV3 equality, scientific cohort admission, scientific performance or Stage7 completion. No such claim follows from tiny uniform RGB frames.
9. Future canonical hosted source CI, request-only activation, branch/PR publication, unique run/job/artifact identity, TLS download success, remote acceptance or final HEAD CI. Static controls are reviewed; future external events remain executor-owned gates.
10. Future final documentation, PR body, fresh remote preservation, clean-tree closeout, output receipt, and scratch cleanup. These are outstanding executor work, not review defects or reviewer-certified outcomes.
11. Fresh remote preservation of main, Drafts 102–119, old native/image/mapping/dispatch workflow histories or consumed states. The review used retained evidence and confirmed local base-tree preservation; it made no network calls.
12. Independent execution of the complete 1,711-case local matrix or its spacious-shm test. Only the authorized 30 focused fixtures were run here.
13. Every historical evidence log/JSON record as a fresh external fact, or a redesign/re-audit of old consumed engines. Historical evidence and reused helpers do not acquire new runtime authority through this branch.
14. Real hosted kernel/cgroup/proc/Docker behavior, Xvfb subprocess behavior and rare teardown races under native faults/OOM. The source checks and CPU failure tests are useful but do not replace the one qualified hosted attempt.
15. Arbitrary malicious-driver resistance or a comprehensive sandbox security certification. The trusted pinned-image execution, explicit generated-code allowance and selected snapshots define the narrower reviewed contract.

## Verdict

**No Critical or Important findings; one Minor reporting finding.** The reviewed implementation is suitable to proceed to the already-defined source CI and fresh activation gates, then the single authorized hosted attempt. This is a source/CPU-fixture review verdict, not qualification of the actual GLX window, future CI or scientific readiness. No rereview or minor-polishing pass is requested. Preserve failure honestly and do not retry a consumed attempt.

No repository/index/ref changes, network/downloads, old-output deletion, real SDK/Panda/GL/Xvfb/Docker execution or workflow dispatch were performed. The only persistent review artifact is this report in `/tmp`.
