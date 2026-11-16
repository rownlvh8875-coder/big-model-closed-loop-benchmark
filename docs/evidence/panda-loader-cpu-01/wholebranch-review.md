# Sole fresh wholebranch review

Reviewer:gpt-6-astra/high/read-only. Base09948dd5177d82882dcf1b4d1292160499dff31f..a706248418494ee3a8941321675820fe61bf9916. Authorized17host-only focused testsPASS3.236s; no checkout mutation or actual image-loader execution. No rereview.

Strengths: four real host controls distinguish library-version checks and explicit nondefault binding. Source322/history/CI/image provenance/loader bytes/CPU opt-in/fixed output precede image-loader calls. Atomic ledgers preserve conservative invocation bounds across write failures; nonzero alone cannot pass a control.

Critical:none identified.

Important1: oldline207 trusts relocation_kinds, but frozen inspector records only symbol-nonzero kinds. Additional symbol-zero RELATIVE/IRELATIVE or unparsed DT_RELR can execute relocation/resolver work outside the checked constant-return path. Require exact total relocation count(root1 already-checkedPLT,otherroles0) and reject unparsed encodings includingRELR; data-only pre-spawn regressions, no frozen helper changes.

Important2: oldlines195–203 validate bytes through unrounded PT_LOAD spans. Disjoint byte spans can share a rounded4KiB page with a different file mapping; later loader mapping can replace checked entry/function/PLT bytes. Add page-congruent ordered disjoint mapping checks and executable/unambiguous instruction mappings; data-only adversarial regression before spawn.

Minor(deferred): oldline253 excludes every basename manifest.json, so a nested cases/same_library/manifest.json is unaccounted in file closure/size. Exclude only the root manifest and validate unexpected nodes/directories in later cleanup. Current source-owned builder creates no nested manifests and they are not a loaded dependency, so deferred as resource/closure accounting polish rather than executable admission.

Declined/out of scope:

- Actual selected-image loader behavior: execution prohibited in review.
- Live remote CI/artifact responses: network prohibited; validation logic/retained contract inspected.
- Full regression/exhaustive preservation: prohibited; focused modules independently run.
- SDK/Panda/GL/Xvfb/model/ORT/cohort behavior and fullABI/runtime: excluded from CPU scope.
- Hostile replacement by same OS principal/root after checks: reviewed tampered inputs before validation, not control over Python/private directories.

Assessment: normal four-case path/accounting sound; two Important executable-graph corrections required before authorized image-loader run. No integration/merge decision.

Executor: RED eight data-only variants(RELATIVE,hiddenIRELATIVE,RELR,unparsedrelativecount,roundedmappingalias,incongruence,writablecode,executableGOT) then exact relocation/page/RX/RW-GOT guards→19focusedPASS(final tag whitelist included; see log). Crafted ELF data is never executed: rejection assertion precedes any run_cases call, which then confirms0start attempts. Full fix-pass suite/rulings in ledger.
