# Sole wholebranch review — Cg SDK candidate

Reviewed base `f0ceac1b0575824370ef86bd83a872d0bedf90d9` through head `33ab88cdbe6586ff87c23a9f8c2f2b472bf1c7a1` in `/workspace/big-model-closed-loop-benchmark`, against the review package, design, implementation plan, ledger rulings, and result. This was one read-only review, without subagents, target compilation/loading/execution, remote actions, or repository mutations.

## Strengths

- Genuine Cg header pins and current-image provider pins are checked against frozen image inventory/authority; private aliases must remain inside the qualified tree. Parser placeholders and toolkit/Trace providers cannot pass the byte identities.
- Source reconstruction, separate private inputs, explicit ABI0/dependency flags, create-only build reservation, and Actions-only entry guards maintain useful separation from consumed runtime windows.
- Integer getters are inspected from bounded executable ELF spans, the descriptor must be literal non-executable object DATA, and the gate consistently refuses runtime/full-ABI/crash-repair claims.
- Request-only activation, exact source CI identities, unique attempt/run/artifact policy, bounded closed ZIP extraction, and independent candidate/object recomputation provide substantial defense against accidental authority substitution.
- Independently ran the requested four focused modules: **36 tests passed in 0.964s**. These include real handwritten CPU object/assembly fixtures, never actual Panda execution. The larger owner-reported suite was not repeated.

## Critical findings

None identified.

## Important findings

### I1 — Measure and revalidate the compiler's actual selected subtools/link inputs

**Locations:** `scripts/build_panda_sdk_cg.py:85`, `scripts/build_panda_sdk_cg.py:87`, `scripts/build_panda_sdk_cg.py:146`.

The profile queries `cc1`/`cc1plus` and `collect2`, but records `/usr/bin/as` and `/usr/bin/ld` solely from the fixed TOOLS dictionary. GCC can select an assembler/linker in its compiler search prefixes instead. The profile also samples only `crtbeginS.o`, `libgcc.a`, and `libstdc++.so`, leaving ordinary selected shared-link inputs such as `crti.o`, `crtn.o`, `crtendS.o`, and `libgcc_s.so` outside the measured closure. Postflight checks only rehash the old records; it never reruns selection queries. A new earlier search-path candidate can therefore change selection while every recorded file remains identical, and the build can still claim the measured profile passed. `.d` files do not cover these linker/subtool inputs.

This matters because the user is spending one build attempt to obtain an attributable candidate, and compiler-subtool drift is an explicit fail-before-success boundary. This is a missing check in the new profile, not a claim that the future runner has already drifted.

**Smallest fix:** Query and record the actual assembler/linker and relevant selected link inputs using the same compiler/environment; bind search-selection facts (including relevant absent higher-priority candidates), and compare selection-query outputs as well as bytes before/after the owned build. Add a CPU fixture where selection changes without modifying any originally recorded file and require rejection before success.

### I2 — The vendor decoder accepts a decoy expected offset while the accessor uses the old offset

**Location:** `scripts/panda_sdk_cg_static_gate.py:25` (the immediate return of the first recognized operand; lines 20–31 implement the decoder).

`decode_vendor_getter` stops at the first matching load/address instruction and ignores the rest of the function. A function containing `mov rax,[rsi+0x670]; mov rax,[rsi+0x600]; ret` returns `0x670` from the decoder even though its returned value comes from the old member offset. An arbitrary or unknown suffix is likewise accepted. Consequently a descriptor containing the expected vendor offset can agree with this decoder while the executable accessor retains the old access, contrary to the forged-code and unknown-instruction fail-closed requirements.

**Independent reproduction:** Called the decoder on bytes `488b86` + little-endian `0x670` + `488b86` + little-endian `0x600` + `c3`; it returned `0x670`. No candidate was loaded or executed.

**Smallest fix:** Validate the complete supported accessor instruction shape/data flow through its return or known string-copy operation, rejecting unrecognized suffixes and later conflicting member accesses. Add a decoy-first-load fixture alongside the current old/new prefix fixtures. If a real compiler shape is unsupported, retain a negative result rather than accepting just its prefix.

### I3 — Packaging failures can discard the only uploaded negative diagnostics

**Locations:** `scripts/produce_panda_sdk_cg.py:100`, `scripts/produce_panda_sdk_cg.py:109`, `scripts/produce_panda_sdk_cg.py:144`; related structured-command omission at `scripts/build_panda_sdk_cg.py:116`.

Candidates are copied before logs. If a failed/partial candidate exceeds its carrier bound, `_copy` raises immediately; the fallback seals only files already in the bundle, and neither diagnostic log has been copied. Similarly, a combined log overflow raises before writing `host.log`, discarding the stderr/staging portion instead of retaining a bounded negative diagnostic tail or prefix with explicit truncation metadata. The raw work directory is not the uploaded artifact.

**Independent reproduction:** In a temporary CPU fixture, created a sparse `libpandagl.so` of 4 MiB + 1 byte and small stdout/stderr files, then called `finalize_bundle` followed by `seal_failure_bundle` as production does. The sealed receipt listed **no logs**, although both raw log files existed. This is an expected failure mode the receipt path is supposed to preserve, not a malformed external carrier attack.

There is a related loss of structured evidence on descriptor compile failure: `compile_layout` raises before returning its command record, the build receipt does not attach it, and packaging copies only `*.log`, not the saved `command.json`. Thus the retained artifact lacks that failed command's exact argv/return/timing/cleanup record.

**Smallest fix:** Assemble bounded negative logs and owned command records independently of optional candidate copying; declare oversized members omitted without aborting diagnostic collection. Make overflow/truncation explicit in the receipt, and attach the layout command result before checking success. Add failure-carrier tests for oversized partial output, combined log overflow, and failed layout compilation.

## Minor findings

### M1 — Configuration capture has no comparison to the prior profile

**Location:** `scripts/build_panda_sdk_cg.py:136`.

The builder captures the generated dtool macros and checks four required values, but never emits the planned comparison against the prior generated configuration. The measured candidate remains interpretable, but users must manually discover other changed compile-time features. Add a recorded old/new macro delta when convenient; do not turn that comparison into an assertion about unknown wheel flags.

## Recommendations

Complete the one authorized Critical/Important fix pass before qualifying or spending the hosted build attempt. Preserve the current fail-closed behavior and explicit non-runtime status. The independent focused suite passed, but its current assertions do not cover the three findings above. Minor M1 can be explicitly deferred under the agreed review process; this review does not request another review seat or a rereview.

## Declined to judge

- Actual hosted GCC13/Panda compilation success and candidate layout values — no qualified build has run; this review was explicitly forbidden to spend that attempt.
- Actual current/future ubuntu-24.04 tool availability, capacity, and compiler behavior — external runner facts remain to be measured during authorized preflight; absence is permitted to yield BLOCKED.
- Live canonical source-CI, request activation, run/job/artifact origin, and TLS acceptance — reviewed policy code, but no network workflow activation or remote mutation was allowed or performed.
- Full C++ object ABI or wheel class-size parity — the wheel lacks its generating C++ configuration headers and selected member checks intentionally provide only necessary evidence.
- Cause or repair of the previous SIGABRT — requires separate native diagnostic evidence; static success explicitly cannot establish it.
- SDK/Panda loads, GL/GLX/GSG behavior, Xvfb, model/ORT/cohort execution, and observed default-off statistics — prohibited runtime activity and outside this compile-only plan.
- Image installation/replacement, image preparation, Docker load/start, registry/Cloud publication, and main/shared-base merge — separate future authority, not granted by this candidate gate.
- Full dynamic loader binding, interposition, symbol-version compatibility, and complete dependency closure — inherited audit reports selected static root availability and retains diagnostics, explicitly not runtime binding qualification.
- Independent publisher authenticity/signature for the NVIDIA archive — design deliberately claims HTTPS acquisition plus exact retained digest, not an unavailable publisher attestation.
- Continuous compiler-execution attestation, bit-for-bit reproducibility, and aggregate cgroup memory enforcement — explicitly excluded from the measured direct-host design; I1 concerns the promised point-in-time selection checks, not those stronger claims.
- Exhaustive re-audit/redesign of all inherited ELF, transport, source-staging, and archive helpers — inspected relevant integration boundaries; review package expressly limits wholesale legacy redesign.
- Independent re-fetch of every preserved remote branch/Draft/history and re-hash of every sibling scratch file — owner preservation evidence is retained; no remote mutation or broad preservation re-audit was requested from this seat.
- Repetition of the full 1747-case owner verification matrix — focused 36 were independently repeated; the owner-provided larger logs remain the evidence for that broader run.
- Scientific equality/divergence/performance results or Stage7 completion — scientific allowance remains zero and strict result remains 0/4 FAIL.

## Assessment

**Ready to proceed to the one hosted build: With fixes.** The implementation has substantial source/origin/ELF boundary coverage and truthful runtime disclaimers, but the promised selected-subtool measurement, vendor-accessor rejection, and durable negative evidence have concrete gaps. Address I1–I3 before spending the one build attempt; future external acceptance and runtime proof remain separate outstanding work, not findings that a local review can certify.
