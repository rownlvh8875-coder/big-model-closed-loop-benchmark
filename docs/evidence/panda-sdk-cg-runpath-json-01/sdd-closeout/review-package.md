# Whole-branch read-only review
Base: 5c31664d2033fcac9a76a52ffa9c006a22f71970
Head: 4d6ff753fec7c1e7d4c399983097e3027d145ab6
Plan: docs/superpowers/plans/2026-11-16-panda-sdk-cg-runpath-json-audit.md
Spec: docs/superpowers/specs/2026-11-16-panda-sdk-cg-runpath-json-design.md
Ledger: docs/STAGE7_PANDA_SDK_CG_RUNPATH_JSON_LEDGER.md (five Ruling lines)
Implementation: new scripts/panda_sdk_cg_runpath_json.py and scripts/accept_panda_sdk_cg_runpath_json.py; two new tests; immutable contract/frozen310 map.
Task1 focused8 PASS, Task2 focused9 PASS; combined17 PASS. Full regression GREEN: normal1848 with7skip + actual/dev/shm3PASS =1851cases1844PASS7skip. Errno28 investigation and environment-only matrix adjustment are recorded in ledger. Actual read-only audit follows review+CI. No SDK build/request/download/target/native/image/publication/merge; preserve source310 and oldFAILED. Low disk ~125MiB, do not duplicate large DATA.

Review Focus (verbatim):
1. Real ELF version tables survive serialize/parse and compare; int/bool,float/int,list changes and numeric-key collisions must never be normalized away (Task1).
2. Only version-table indices and the known provider-record location label are normalized; changed names/versions/missing rows/other data_path fields reject (Task1).
3. Same-sized poisoned cached ZIP/file/provider,symlinks,wrong run/source/CI/job/artifact or changed frozen source/old verdict cannot qualify (Task2).
4. Reusing caches cannot skip provenance,full evidence,actual ELF or provider recomputation; no legacy receiver call/global patch or new production request (Task2).
5. Catchable bootstrap/audit failures leave a negative fresh receipt without authentication/runtime flags or overwriting prior results (Task2).

Read-only: never alter working tree/index/HEAD/branches; no agents, network mutations, SDK/Panda/GL/officialmodel/ORT/image/native operations. You may run ONLY the two new focused test files using /workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B, never full suite. Use git show/diff. Inspect own new scratch only; don't inspect sibling sdd workspaces.
Review all changed source and relevant immutable primitives; grade concrete effects, not spec silence. List Strengths, Critical/Important/Minor with file:line, exact trigger, effect, fix. Before assessment list EACH declined/out-of-scope behavior with reason (or explicitly none). No rereview will occur; executor will do one Important TDD fix pass. Do not make integration/merge decisions or execute actual audit. Please keep report specific and concise.
