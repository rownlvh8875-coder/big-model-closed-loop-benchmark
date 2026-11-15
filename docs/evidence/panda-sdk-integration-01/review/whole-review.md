# Sole fresh whole-branch review

Reviewer gpt-6-astra/medium/forknone; reviewed BASE45df9244b4e212af3c5f18628ba7639608a0b4cd..HEAD4d1b404c0c12dbd79f5422206bab2cdde2b50235. Read-only; no subagents or actual native code; no rereview. Report follows.

### Strengths

- The implementation honestly reports the requested image/runtime/closed-loop work as **incomplete**. Old-image acceptance never qualifies SDK `aa7e`; native allowance remains zero, with inherited `0/4 FAIL`.
- Coverage subtracts actual typed routes before applying the immutable 256-name cap. Unsafe and computed lookups remain explicit blockers.
- Image inspection binds the retained archive, config, rootfs and installed inventory to pinned authority.
- Independent verification passed all **19 focused tests**. All **53 proof hashes** and six implementation/test hashes match. Reprocessing the retained raw TU data reproduced all selected snapshots and coverage fields. All 65 branch changes are additions.

### Issues

#### Critical

None found.

#### Important

1. **Compiler subprocess is outside the verified executable closure.**
   **File:** `scripts/panda_sdk_coverage.py:96`
   Verification checks only the executables listed in the old receipt. That list includes `g++` but excludes its actual C++ preprocessor executable, `cc1plus` (present at `/usr/libexec/gcc/x86_64-linux-gnu/14/cc1plus`). Changing that executable leaves every checked tool digest unchanged; line 106 then invokes the driver, which executes the unchecked subprocess. This violates the explicit requirement to reject tool mutation before executable invocation.
   **Fix:** Bind and verify the actual preprocessing executable and relevant compiler selection configuration before invoking the driver. Add a rejection test using isolated fixtures/mocks; do not mutate host executables. Distinguish newly captured tool identity from unrecorded original-build identity.

2. **Malformed marker spelling bypasses source-origin rejection.**
   **File:** `scripts/panda_sdk_coverage.py:27`
   Only `# ` and `#line` prefixes enter marker validation. I reproduced acceptance of:
   ```text
   # 1 "source/x.cxx"
   get_extension_func("glGood");
   #	1 "foreign/x.cxx"
   get_extension_func("glBad");
   ```
   `select_sources` attributes both calls to `source/x.cxx`, retaining the malformed tab-prefixed marker as ordinary source. Leading whitespace provides a similar bypass. This defeats the stated malformed-marker rejection boundary and can contaminate selected-source inventories.
   **Fix:** Recognize marker-like directives independently of their whitespace spelling, then either validate their exact permitted syntax or reject them. Add tests for tab/leading-whitespace markers and foreign origins.

3. **Build-log identity is not authenticated.**
   **File:** `scripts/panda_sdk_coverage.py:102`
   `makepanda.log` is absent from the pinned SDK output manifest. `verify_commands` checks only matching output commands; changing other log bytes or replacing the log with just the two expected command lines still passes. Consequently, the claimed rejection of log mutation is not implemented, and the command comparison does not authenticate its original-log provenance.
   **Fix:** Verify the log’s retained authoritative size/hash before parsing it and recheck after preprocessing. Preserve the existing exact-command comparison. Add a regression where an unrelated log byte changes while both expected command lines remain intact.

#### Minor

None raised.

### Recommendations

Address the three input-validation gaps in the permitted fix pass, retaining existing failed and successful evidence unchanged. Keep the explicit incomplete-scientific-work boundary in the final report.

### Declined to judge

- Actual Panda/GL/SDK/MetaDrive/provider/model/ORT runtime behavior: prohibited by this review’s execution boundary and not established by static evidence.
- Original complete host-header/object-path equivalence: the original closure was not captured; the ledger accurately disclaims it.
- Fresh image construction, mapped ABI, installation/lifetime/driver qualification and official closed-loop results: absent and explicitly unfinished; this assessment cannot establish them.
- Reexecution of the full image audit and 1,522-test suite: excluded by the review instructions; retained evidence was inspected, and only the authorized focused suite was rerun.
- Current remote PR/CI/main/native-history state: retained snapshots were inspected; fresh remote closeout remains a subsequent plan step.

### Assessment

**Ready to merge? With fixes.**

The assessment boundary is honest, the retained results reproduce, and no native-admission escalation was found. The three verification gaps should be fixed before accepting the branch’s claimed input-authentication guarantees; even afterward, it remains an incomplete runtime/scientific deliverable.
