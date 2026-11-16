# Task2: Source-bound fixed-image-loader execution

**Files:** Create scripts/probe_panda_loader_versions.py,tests/test_probe_panda_loader_versions.py; owned result/ledger/evidence.
**Interfaces:** probe(source:str,registrations:list,out:Path,run_cpu_fixtures:bool=False)->dict; frozen_state()->dict; verify_source(source:str)->dict. Consumes Task1 and unchanged old provenance/inventory/source primitives.

- [ ] Write source322/prior receipts/loader pin+metadata+private-copy/nooptin/wrongCI/bootstrap/final-write/freshout negatives and partial-case accounting. Run new tests; Expected RED missing module.
- [ ] Implement stdlib atomic receipt before imports,explicit CPU flag/exact source322+CI+prior receipts/original origin+image inventory/byte-pinned loader staging,closed fixture compilation/validation,then exactly4case slots. Recheck source/old receipts/loader bytes and preserve precise partial facts on failure; never retry/accept an arbitrary payload. Run focused tests; Expected GREEN.
- [ ] Run full known matrix; Expected GREEN. Sole fresh wholebranch review after commit, regrade,ONE Important RED→GREEN fix pass/fullgreen,Minor deferred/no rereview. Save source322 snapshot/logs.
- [ ] OwnDraft against feature/panda-provider-version-witness-v1 at09948dd(actual PR number),exact reviewed-sourceCI4jobs/attempt1/artifacts0; Expected PASS. Then explicit --run-cpu-fixtures with fixed loader cache exactlyonce/freshout; Expected observed4case outcomes or retained negative without relaxing checks.
- [ ] Document actual scope/counts/traces and limits,rulings,deferredMinors; preservebase7997/old318/histories/receipts/siblings. Archive/remove only ownscratch;docs-onlyfinalHEADCI4jobs/clean/exactremote/output-onlyfinalreceipt. Expected noSDK/native-science/newbuild/image/publication/merge; strict0of4FAIL/Stage7INCOMPLETE.

