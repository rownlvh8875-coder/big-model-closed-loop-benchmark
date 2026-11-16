# Sole read-only wholebranch review
Basebbf8f872ef2353d0840ae61b435147cb9cf161df; Head6f54653d2d3eaf56a26b42a7b0693db92b06d5ea.
Plan docs/superpowers/plans/2026-11-16-panda-provider-version-audit.md
Spec docs/superpowers/specs/2026-11-16-panda-provider-version-design.md
Ledger docs/STAGE7_PANDA_PROVIDER_VERSION_LEDGER.md (five Ruling lines).
New model scripts/panda_provider_version_witness.py + read-only auditor scripts/audit_panda_provider_versions.py, two focused test files and fixed contract/frozen314 map. Focused16PASS; full1869cases1862PASS7skip (ordinary/tmp1866 + real/dev/shm3). Preservation7930files/modes,314source,oldreceipts/histories/main/priorDrafts GREEN. Exact current source318/Git verified; previous positive/negative receipts unchanged. New actual audit waits for review and sourceCI. Existing retained metadata comparison only gives110witnesses/0unexplained; no new origin authority.

Review Focus (verbatim):
1. A same-name/version export in an unrelated or disconnected library must never explain a miss; declared-library selection/version definition and pinned stub→target edge are both required (Task1).
2. Version/key/type contradictions,nondefault versioned exports,IFUNC/weak/unsupported inputs and duplicate needed edges must retain distinctions and never silently waive a strict row (Task1).
3. Frozen source314,prior positive/negative receipts,prior gate,ZIP/member/provider bytes and original producer/sourceCI/run/job/artifact identities must remain independently bound despite cache reuse (Task2).
4. Import/bootstrap/final-write failures must leave a fresh parseable negative when output is writable, never a stale authenticated result or overwritten old receipt (Task2).
5. A complete110witness report must preserve the6strict blocks and all false runtime/fullABI/fullclosure/crash/install/Stage7 flags, with exact ownsource318/CI and no target execution or production request (Task2).

Read-only checkout/index/HEAD/branches. No agents/network mutations/new actual audit/fullsuite. You may run ONLY two new focused tests with /workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B. No SDK/Panda/GL/Xvfb/officialmodel/ORT/image/target/native operations. Handwritten CPU ELF compilation in tests is permitted, never load/execute outputs. Disk~100MiB; do not copy large DATA or dump full gate/ELF. Inspect own scratch only, not sibling sdd contents. Old frozen receiver/checker files must stay unchanged.
Read complete new source/tests/contract and relevant immutable primitives. Treat completeness as DATA evidence, not runtime or replacing old strict verdicts. Grade actual effects, not spec silence. Report Strengths, Critical/Important/Minor with file:line/trigger/effect/fix. Before assessment list every declined/out-of-scope behavior and reason (or explicitly none). One Important fix pass, no rereview. Never make integration/merge decisions or modify files.
