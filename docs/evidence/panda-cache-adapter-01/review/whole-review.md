# Sole whole-branch review

Reviewer/root/panda_cache_adapter_whole_review, gpt-6-astra/medium/fork_turns:none; base55ab312dcded2a55640a560441010f8f2737531d→reviewed27d073a2724286c17541b459aa43827e550cca3f. Read-only/no subagents/no second opinion/no native/Panda/GL library load. VerdictWithfixes,0Critical/3Important/0Minor. Independent17focusedPASS5.239s and all248proofs/1667512bytes match; clean checkout.

Strengths: bounded POD/copy/no-op replay/PBO shadow fit immutable cache; pending current destruction preserves state; failures preserve errno and clear stale output; evidence distinguishes CPU metadata from native admission.

Important1 native/panda_cache_adapter.cxx:23–26,151–157: source lookup begin changes private pending state without exposed counter changes. Healthy FBO state then psd_lookup(glUnknownState) allowed pca_observe success/known255 and snapshot success/readFBO9 before resolution later failed finish. Already-consumed metadata cannot be retracted. Require a reliable pending-resolution signal and public-gate rejection; counter equality insufficient. Regression must cover supported and unknown pending lookup snapshot/observe without changing immutable source.

Important2 scripts/panda_cache_adapter_cpu.py:70 and delegated build_panda_source_dispatch.py:26–27: bare readelf resolves ambient PATH/inherited env, captured output unbounded and outside runner before controlled children. Harmless scratch wrapper executed twice. Require adapter-owned absolute pinned readelf path through sanitized bounded group runner/tool receipts; preserve old inspector. Test ambient PATH and actual inspection timeout/output limits.

Important3 scripts/panda_cache_adapter_cpu.py:13–21,46–49: readback_return_core.h is compiled transitively but missing from immutable pins/source receipt. Scratch RB_KNOWN_ALL255→127 still produced96successfulCPUcases because both fixture and cache shared modified definitions. Require pin/record of header, compiler dependency audit, regression rejecting modification before output.

Recommendations: one Important/Critical TDD fixpass, retain before-review evidence, add final verification; no rereview. Minor none.

Declined to judge:

1. Actual Panda compiled branch/name/alias/safe256profile: explicit future gates.
2. Driver acceptance of void GL, real GPU/rendered image correctness: CPU command metadata cannot establish.
3. Mapped ABI/allocation/camera/native lifetimes: future integration gates.
4. Producer/sink receipt authenticity: downstream integer combines caller status only.
5. Invalid pointers, overlapping output/input spans, concurrent setup, throw/longjmp: explicit storage/lifetime/serialization/normal-return preconditions.
6. External attached-cache mutation/finalization: exclusive adapter ownership precondition.
7. Hostile concurrent repository/tool replacement: no broad hostile-filesystem sandbox claim; findings need no race.
8. Own-Draft/exactHEADCI: explicitly after review.

AssessmentWithfixes. All3Important require correction; no Critical/Minor. Executor rulings and final test receipts are separate from this report.
