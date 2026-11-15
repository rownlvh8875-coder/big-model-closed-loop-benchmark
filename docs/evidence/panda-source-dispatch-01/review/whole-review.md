# Sole fresh whole-branch review

Reviewer: /root/panda_source_dispatch_whole_review; gpt-6-astra/medium/fork_turns:none. Base5aefbd5ca54557de79d00c67282c086e8a6bca61; reviewedHEADaf583a8b5bc19fa596601301e2648a8d7268e852. Read-only; no subagents, no second opinion, no Panda/GL/unresolved inspection ELF loaded. Verdict With fixes;0Critical/2Important/1Minor.

Strengths: typed normalization/original forwarding/results/NULL/errno are sound in examined paths. Alias slots preserve distinct pointers and changed pointer forwarding. Exact source integration covers specified direct/common/GLX/POSIX/legacy sites. ReadPixels stays a bare original-only tail without capture arming or old ABI activation. Concrete evidence distinguishes compile/static inspection from native admission.

Important1 — native/panda_source_dispatch.cxx:87–94 and133+: original resolver runs outside reentry guard. Nested lookup or instrumented state calls can emit accepted metadata. CPU reproduction outer glBindBuffer lookup→nested begin/complete→outer completion yielded finish0/error0/events2. Require lifetime guard, still-forwarded originals, expected observational path marker/outer completion allowed. Cover nested resolver and resolver-to-state, errno/results and normal GLX/POSIX paths.

Important2 — scripts/build_panda_source_dispatch.py:155–159: disk-limit process.terminate targets makepanda only; shell/compiler descendants continue writing after failed receipt. CPU sparse-file reproduction observed a child's later marker. Process may also exit between observations without a final size check. Require isolated session/group; bounded TERM then KILL entire group on limit/error/interruption, stop descendants before receipt, final size check, CPU child/sparse tests.

Minor3 — scripts/build_panda_source_dispatch.py:139–141,167,184: resumed build overwrites build-receipt.json; numbered logs survive but previous command/returncode/timing/manifest receipt does not survive automatically. Actual committed attempt receipts were manually preserved and are unaffected. Recommend immutable numbered attempt receipts/latest summary. Under no-minor-polishing rule explicitly defer.

Reviewer independently reran19focusedPASS and63proofhashes,7281stagedfiles/upstreamtree,2674SDKoutputrecords,12dependency packages,6hostlinks, actual candidate static read-binding/oldABIreject/SHA and all3207base Gitobjects/modes. No native library loading or execution.

Recommendations: use one Important/Critical TDD fix pass; retain before-review proof unchanged, add fix evidence; keep Minor limitation explicit; finish exact-head Draft/CI.

Declined to judge (each requires executor ruling):

1. Actual driver/GPU correctness and native ON/OFF canaries: prohibited; allowance0.
2. New mapped ABI/allocation/camera/register/lifetime/image admission: future gates.
3. Bootstrap replay and buffer-deletion existing-cache delivery: deferred adapter.
4. Full Python/MetaDrive image parity and beyond-four-source coverage: minimal candidate.
5. Throw/longjmp callbacks, invalid spans and observer/storage lifetime violations: caller contract.
6. Concurrent initialization by multiple configuring threads: setup before context activity; no multi-initializer guarantee assessed.
7. Hostile concurrent source/sysroot replacement or malicious toolchains: ordinary retained-input build, not adversarial sandbox.
8. Exhaustive malformed-ELF fuzzing: actual/static/mutation checks, not general hostile-ELF certification.
9. Pending own-Draft/exact-head CI: scheduled after review.

Assessment With fixes: both Important findings must be corrected before closeout. No rereview authorized. This report retains the original review findings; executor rulings and subsequent verification are separate.
