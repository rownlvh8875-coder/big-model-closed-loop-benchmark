# Sole wholebranch review — Eigen/Cg v2

Base: `67ecf8a4e391fc26ebed825c129ac16a417e084c`
Head: `0b866692a71e2543d95560d1b27917d7e22111e7`

Reviewed the package first, then the design, implementation plan, ledger (including all three Rulings), every new implementation file/workflow/test, and immutable helpers at their integration boundaries. The first three Rulings are reasonable: the existing checkout is preserved, the ledger carries task identity when helpers are unavailable, and versioned wrappers avoid changing consumed source. Wrapper reuse does not, however, fulfill a new requirement when the inherited primitive lacks that behavior (I2 below).

Review was read-only on checkout/index/HEAD/refs. Scratch was confined to `/tmp`. No subagent, network mutation, workflow activation, target SDK compilation/link/load/execution, Panda/GL/Xvfb/model/ORT/image operation occurred. The permitted focused suite compiled only its handwritten inert CPU fixtures. Existing build01 ELF was inspected and mutated only in memory as DATA; its request was not revalidated or reopened.

## Strengths

- The Eigen qualifier pins the archive and exact manifest, stages create-only files, rejects selected links and path aliases, bounds inflation/header sizes, and verifies the real 3.4.0 version macros. The builder checks private inputs both before and after compilation and rejects recognized host Eigen dependencies.
- Effective configuration is distinguished from generated configuration. The real-header descriptor has compile-time vector and allocator alignment assertions; the builder also collects preprocessor macros. A generated `LINMATH_ALIGN=1` without Eigen is not sufficient.
- The parent ET_REL object is parsed as DATA. Section extent overlap, descriptor flags, names, relocation associations, fixed size and raw-parent equality are checked without loading initialization code.
- The getter gate checks full supported function bodies, rejects repeated CET prefixes, IFUNC getters and overlapping getter extents, and associates the copy call with a named ABI0 import. Existing build01 still observes `0x678/0x67c/0x660` and remains incompatible.
- New source/request/workflow names and an exclusive build latch separate this attempt from build01. Request-only activation, source CI, run uniqueness, attempt one, artifact origin, closed ZIP members and resource bounds have explicit checks.
- Necessary static evidence stays separate from runtime/full-ABI/crash-repair authority. Success does not promote image installation, previous abort repair, runtime mapping or scientific allowance. Unknown default-off observation stays `None`.

## Verification

Ran the authorized command:

`/workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B -m unittest discover -s tests -p '*panda_sdk_cg_eigen*.py' -v`

Result: **37 tests passed in 2.196 seconds**. Did not repeat the full 1792-case suite. Additional narrow reproductions below exercised Python byte/file handling and a mocked failed host-tool query; no target code was run. Checkout status was clean on inspection.

## Issues

### Critical (Must Fix)

None found.

### Important (Should Fix)

#### I1. Individual host-log overflow removes all host diagnostics, including command receipts

**Files:** `scripts/produce_panda_sdk_cg_eigen.py:96`, `:102`, `:127`, `:142`.

`collect_diagnostics` gives `host.log` the remaining **combined** 32 MiB budget, although its individual closed limit is 16 MiB. With short makepanda stdout, stderr alone may legitimately reach the owned process's 16 MiB limit. Its path header plus command JSON push host.log over 16 MiB. `finalize_bundle` subsequently rejects the oversized log while hashing members, and `seal_failure_bundle` quarantines the entire file rather than retaining a bounded prefix. The command-first ordering therefore does not preserve the commands in the uploaded carrier.

**Concrete reproduction:** Create `work/build/makepanda/stdout.log` containing `short stdout`, `stderr.log` of exactly `16*1024**2` bytes, and `command.json` containing `{"argv":["compiler"],"returncode":3}`. Call `finalize_bundle` and its normal `seal_failure_bundle` fallback. Observed `bounded regular DATA input`, `bundle/logs/host.log` absent, `logs/host.log` in omissions, and `diagnostics.truncated == False`. This is within the process stream bounds and loses all stderr and structured commands from the carrier.

**Impact:** A failed sole build can close its slot while losing precisely the durable command/error evidence required by Review Focus 5. The existing overflow test fills stdout as well, leaving host.log only 16 MiB and missing this asymmetric case.

**Fix:** Bound host.log by `min(individual_host_limit, remaining_combined_limit)` from the outset. Preserve command metadata first, retain bounded stream prefixes, and record truncation/omission explicitly. Test short stdout with maximum stderr and multiple staging/descriptor logs as well as the symmetric existing case.

#### I2. Failed tool-selection queries do not retain the promised owned process receipts and diagnostics

**Files:** `scripts/build_panda_sdk_cg_eigen.py:11`, `scripts/produce_panda_sdk_cg_eigen.py:153`; inherited behavior at `scripts/build_panda_sdk_cg.py:83`, `:87`, `:94`.

The v2 builder aliases `measure_tools`/`verify_tools` directly to v1. Compiler selection queries use `subprocess.check_output`, append a query only after successful completion, and save only a generic failure string on error. They do not preserve bounded stdout/stderr, structured return status/timing/cleanup, or an owned process-group receipt for the failed query. Stderr is not captured by those calls. Reverification calls `measure_tools` without an output path, further limiting retained failure evidence.

**Concrete reproduction:** With file-recording mocked (no compiler launched), make the first `check_output` raise `CalledProcessError(9, ['/usr/bin/gcc-13','-dumpfullversion'], output=b'partial version', stderr=b'tool failed detail')`. The saved profile has `status=FAILED`, `queries=[]`, and only `CalledProcessError: Command ... returned non-zero exit status 9.` Neither diagnostic byte string is retained. A timeout likewise has no owned group receipt.

**Impact:** The explicit Task2/Task4 and Focus5 failed-tool/deadline evidence requirement is not implemented for preflight or postflight tool queries. This can block the only attempt before compilation with insufficient diagnostic evidence. This is a new wrapper contract issue, not a request to redesign all legacy tooling.

**Fix:** Add a v2 measured query path using the owned bounded process primitive, save the command before checking its success, and retain query receipts/logs through preflight and reverification failures. Preserve the old source unchanged. Add negative nonzero/timeout tests that inspect the final carrier's evidence.

#### I3. Independent acceptance leaves build evidence internally unchecked

**Files:** `scripts/accept_panda_sdk_cg_eigen.py:19`, `:30`; `scripts/panda_sdk_cg_eigen_gate.py:63`.

Success-carrier completeness checks require the reports' presence and bind their hashes to the producer's own file manifest, but the acceptance path never parses/validates `inputs.json`, `tools-before.json`, `tools-after.json`, `host-before.json`, `used-inputs.json`, `compile-dependencies.json`, `source-manifest.json`, or `sdk-output-manifest.json`. It also never reads `candidate/build-libpanda.so.data` to compare it with `compiler_build.build_panda_sha256`. The gate checks a small set of claimed build status/configuration fields and hashes for the other three candidate files; it does not replace those missing checks.

**Concrete counterexample by the complete success-path data flow:** For an otherwise qualifying authenticated carrier, replace `reports/used-inputs.json` with a report declaring a host Eigen input (or even `{}`), or replace build-libpanda with unrelated nonempty bytes under its size limit. Update the corresponding entry in the producer receipt's `files` map. Extraction and `validate_receipt` will accept those file hashes, and none of the subsequent acceptance checks reads the substituted report or compares build-libpanda with the build hash. The computed candidate/parent/raw/provider gate is unchanged. This was established by reading the full success path; no future hosted success was fabricated or invoked.

**Impact:** Output-origin authentication remains useful, but the promised independent consumer can accept internally contradictory authenticated evidence. It cannot enforce the stated source/tool/dependency facts independently, and a required retained build artifact can disagree with the build receipt unnoticed. This is not a claim that an unauthenticated party can forge a GitHub artifact or that runtime authority is granted.

**Fix:** Validate the received reports' schemas and cross-bind their records to pinned Eigen/source/provider identities and declared compiler commands; check dependency origins and effective input restrictions, compare pre/post tools, and bind every retained candidate to its receipt/output-manifest record. Distinguish remotely measured observations that cannot be independently remeasured from relationships that can and must be checked from the carrier. Add a success-shaped CPU acceptance fixture with one-at-a-time report/artifact contradictions; it must reject them without rerunning target code.

### Minor (Nice to Have)

#### M1. PLT validation is prefix/relocation validation, despite claims of complete PLT forms

**File:** `scripts/panda_sdk_cg_eigen_gate.py:36`; claim at `docs/STAGE7_PANDA_SDK_CG_EIGEN_CANDIDATE_RESULT.md:5`.

The gate reads a 16-byte stub, recognizes optional CET/BND and `ff25 disp32`, and validates its loader relocation, but ignores all remaining bytes. On consumed build01 the clone stub at virtual `0x2de20` is `f30f1efaff25eea30a00660f1f440000`. Replacing its last six bytes with `cc cc cc cc cc cc` in memory still allows `candidate_offsets` to return the old three offsets. This does not admit build01, and those bytes are unreachable after the unconditional jump in this CET stub, so the demonstrated effect is strict grammar/claim mismatch rather than a demonstrated wrong call target or runtime promotion.

Either validate the full supported PLT shapes (including the applicable lazy stub structure) and add suffix mutation tests, or narrow the complete-PLT claim explicitly. I have not graded unreachable padding changes as a Critical/Important semantic exploit.

## Review Focus assessment (verbatim cases)

1. **Generated LINMATH_ALIGN=1 with HAVE_EIGEN absent must not count as effective16-byte alignment; host Eigen fallback and changed private headers reject (Task1/2).** Builder/descriptor handling is sound for the inspected paths; independent consumer report enforcement is incomplete (I3).
2. **Descriptor parent initializer code is never loaded; only the unique read-only128B relocation-free section can be extracted; forged relocation sh_info, section aliases or JSON/raw substitutions reject (Task2).** Inspected section and relocation checks and focused tests support this boundary. No target parent loading occurs.
3. **CET prefix support must not accept extra instructions, IFUNC, decoy vendor loads or arbitrary copy-call targets; consumed build01 remains incompatible (Task3).** Whole getter/template and import association checks reject the covered negatives. Complete PLT suffix language is stronger than the implementation (M1). Build01 remains incompatible.
4. **Matching three offsets/revision/vtable cannot promote partial link diagnostics to complete ABI, prior SIGABRT repair or runtime authority (Task3).** Correctly restricted flags and statuses in gate and consumer; no promotion found.
5. **A failed extraction/tool/deadline or partial oversized carrier retains structured commands and bounded diagnostic bytes; source/run/request retry/substitution never grants another slot (Task4).** Attempt/source/run controls are explicit and fail closed. Diagnostic retention has confirmed exceptions I1/I2; independent evidence contradictions are I3.

## Recommendations

Use the authorized single TDD fix pass for I1–I3, with focused negative tests proving retention and independently checked evidence relationships. Retain old sources/requests/receipts byte-for-byte. Record a separate ruling on M1. The expected future compile/source-CI/acceptance gates remain future work; this review has not run them and does not grant an additional slot or runtime authority.

## Declined to judge

- Actual future v2 compile success and actual new offset values: the hosted build is explicitly gated on this review/source CI and has not run; absence is not an implementation finding.
- Full object ABI and unknown wheel class sizes/compiler configuration: not established by the selected-layout contract and not claimed by the implementation.
- Prior SIGABRT cause/repair: runtime diagnosis is outside this compile-only task; the implementation leaves repair false.
- Runtime loader binding/order/interposition and complete transitive dependency closure: the inherited symbol-availability result explicitly limits its scope; no runtime qualification is claimed.
- Panda/GL/Xvfb/model/ORT behavior, SDK installation, image publication and scientific readiness: prohibited in this task and not inferred from static checks.
- Continuous tool execution integrity, deterministic rebuilds and aggregate cgroup memory guarantees: the design explicitly claims point-in-time selection measurements, not those guarantees.
- General redesign of immutable legacy source/tool/ELF helpers: reviewed their relevant v2 integration boundaries only; I2 flags the resulting v2 requirement gap without requiring edits to consumed code.
- Release-signature provenance for the pinned Debian package: the spec explicitly retains HTTPS metadata/digest evidence and does not claim Release GPG verification.
- The remaining full historical preservation inventory and full 1792-case rerun: owner evidence was supplied; this seat inspected the branch scope and ran the authorized focused suite rather than repeating prohibited broad execution.

## Assessment

**Ready to merge? With fixes** (I1–I3 before advancing to the authorized source-CI/new-build gate; merging itself is not authorized by this task).

The implementation has a strong data-only layout boundary and preserves compile-only authority, but durable failure evidence and independent acceptance do not yet meet the promised contract. The 37 passing focused tests do not cover the confirmed asymmetric log loss, failed tool-query evidence, or contradictory success-carrier reports.
