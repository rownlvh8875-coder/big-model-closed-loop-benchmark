# Sole read-only wholebranch review
Base09948dd5177d82882dcf1b4d1292160499dff31f; Head a706248418494ee3a8941321675820fe61bf9916.
Plan docs/superpowers/plans/2026-11-16-panda-loader-cpu-profile.md
Spec docs/superpowers/specs/2026-11-16-panda-loader-cpu-design.md
Ledger docs/STAGE7_PANDA_LOADER_CPU_LEDGER.md (five Rulings).
New closed CPU fixture core scripts/panda_loader_cpu_fixture.py and guarded image-loader CLI scripts/probe_panda_loader_versions.py. All old318sources/receipts immutable; ownsource322 verified. Host-only focused17PASS; full1887cases1880PASS7skip (1884ordinary/tmp+3actual/dev/shm). Preservation7997files/modes/old318/priorreceipts/history/main/priorDrafts/loadercache byte+mode GREEN. Fixed-image-loader actual calls0 until reviewed-sourceCI. Currentselected loader is236616B/SHA5fc094...,cache0600unchanged,standaloneELF no needed/imports/init. New explicit scope permits exactly4fixed-imageCPUfixture calls,not SDK/Panda/GL/Xvfb/officialmodel/ORT/cohort; historical target/scientific allowances0 unchanged. Four cases default7/mergednondefault7/missingdeclaredversion/wrongsymbolversion; no relaxation of six legacy blocks.

Review Focus (verbatim):

1. A valid symbol in the merged library must not hide missing declared-library version; explicit nondefault symbol lookup must retain name/type/version and actual bound provider distinctions (Task1).
2. Extra/tampered/symlinked fixture/loader paths,constructors,external neededs,RPATH,IFUNC or injected LD/compiler environment must be rejected before loader spawn (Task1).
3. Wrong return status alone,missing/truncated/spoofed trace,timeout/output limit/unreaped process must not become a passed negative or positive control (Task1).
4. Old318/prior receipts/fixed image inventory/cache loader/original provenance/ownsource322/CI and explicit CPU opt-in must all bind before four image-loader calls; partial failure consumes only observed slots and never retries (Task2).
5. Import/final-write/late-check failures must retain a fresh parseable negative and exact invocation facts without overwriting old results or admitting SDK/runtime/fullABI/fullclosure/Stage7 (Task2).


READ-ONLY checkout/index/HEAD/branches; no agents/network mutations/actual image-loader execution/fullsuite. You MAY run ONLY the two new focused modules with /workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B. Those tests execute handwritten CPU fixtures using HOST /lib64/ld-linux-x86-64.so.2,not the copied image loader or SDK; this host-only unit activity is authorized. Never invoke actual CLI --run-cpu-fixtures,never load SDK/Panda/GL/Xvfb/officialmodel/ORT/cohort. Do not inspect other SDD sibling contents or copy/dump large DATA. Lowdisk~80MiB. Relevant old helpers may be read, never modified.
Read new complete source/tests/contract and relevant immutable primitives. Pay attention to exact process accounting and persisted unknown bounds, no arbitrary SDK target graph, provenance/source322/CI/optin/fixed-output gates before the4image-loader calls. One fresh review,one Important TDDfixpass/no rereview. Report Strengths,Critical/Important/Minor(file:line,trigger,effect,fix),then EVERY declined/out-of-scope behavior with reason(or explicitly none),then assessment. Grade effects on reasonable users,not spec silence. No integration/merge decision.
