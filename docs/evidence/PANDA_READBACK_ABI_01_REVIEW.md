# Sole fresh whole-branch review

Reviewer panda_readback_abi_01_whole_review, gpt-6-astra/medium,fresh context.
Basea0e072e450cf6591b9da686711196d56eb9165a1..099fd9af1b36da4b9038cb44794f846ac954e04a.
Original verdict: Critical0,Important1,Minor0; With fixes. One fix pass/no rereview.

## Strengths and independent checks

Assembly preserves7SysVarguments,callee-saved registers/alignment; retained GSG
instructions independently support+28/+48stack slots andRBX/RBP/R12/R15roles.
Exact ELF qualification is separate from structural inspection/runtime admission;
pinned file qualified independently and method fingerprint matches binary excerpt.
Caller/identity checks precede caller-local reads; extent/producer replace callback
claims. Bridge finish failures invalidate receipt acceptance despite footer0,
including OFF/final-emission failures.

Reviewer verified44proof hashes/sizes(1,219,988B),31retainedraw acceptance outcomes,
and all31freshly rebuilt ASan/UBSan scenarios against retained bytes/counters.
All18focused tests passed. Fullsuite log1369PASS7skip inspected, not rerun.
57paths added, no base edits; working tree remained clean.

## Important1: pre-call observer changes original incoming errno

native/panda_readback_bridge.c:94–99;fixture:57. Observer sets errnoEIO; original
may use incoming errno or leave it unchanged. Saving errno after rb_read cannot
undo the changed input. Existing original always set EDOM, masking this.
Independent temporary CPUfixture set EDOM before invocation and removed original
errnoassignment: enabledbasic errno_ok0/finish0; OFF errno_ok1; args/register/source
checks remained successful. Save incoming errno before bridge observation and
restore immediately before forwarding, preserving original returned errno after.
Add unchanged-errno and incoming-verification regressions alongside overwrite case.

## Recommendations

Apply fix/regressions in the authorized pass; rerun focused/sanitizer checks and
retain the distinction between synthetic transport and live admission.

## Declined to judge (author must rule on each)

1. Runtime mapping,dispatch installation,preload compatibility: explicitly inactive; file identity cannot establish them.
2. Native allocation validity/lifetime: extent transport tested; synthetic memory cannot qualify actual Panda allocation authority.
3. Live cached GL state/Texture camera registration: unqualified caller prerequisites.
4. Authentic native receipt transport/fabricated dictionaries: CPUstream/receipt consistency only; native attestation deferred.
5. GPU correctness,fidelity,native overhead,provider/model execution,Stage7 completion: no corresponding execution authorized/performed.
6. Entry-before-install,expired context/scratch,concurrent lifecycle,nonlocal exits/unwinding: outside documented API preconditions.
7. Cubemap,multiview/other excluded paths: intentionally rejected pending separate ABI qualification.
8. Arbitrary structural inspection as admission: inspect_elf explicitly grants no admission; exactqualification remains hash-bound.

## Assessment

With fixes. Static qualification/inert CPUbridge are independently supported, but
pre-call errno leak violates transparent original behavior and needs correction.
No reviewed evidence establishes native activation or runtime admission.
