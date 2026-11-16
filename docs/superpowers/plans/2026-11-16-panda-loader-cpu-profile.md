# Fixed loader CPU profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline in existing checkout. One fresh wholebranch reviewer after implementation, one Important fix pass; no implementer delegation. Steps use checkbox (`- [x]`) syntax.

**Goal:** Observe both version-library checking and cross-SONAME explicit-version binding with four fixed-image-loader CPU fixtures, preserving SDK authority boundaries.
**Architecture:** Closed fixture builder/validator/owned runner and separate source/CI/provenance-bound entrypoint. Four image-loader slots, no SDK payload selector.
**Tech Stack:** Python stdlib,ELF inspector,existing run_owned,gcc -nostdlib,handwritten CPU assembly/C/version scripts,unittest.
**Spec:** ../specs/2026-11-16-panda-loader-cpu-design.md

## Global Constraints

Base09948dd/Draft129,7997files/modes; old318 and all old receipts/verdicts immutable. Ownsource322=318+fourcontractpaths. Samecheckout/inline/noquestions/ownDraft. New bounded CPU-only scope:fixedimage loader236616B/SHA5fc094...,max4invocations with handwritten fixtures; SDK/Panda/GL/Xvfb/officialmodel/ORT/cohort target0,scientific0/oldnativeallowance0,strict0of4FAIL/Stage7INCOMPLETE. No SDK build/request activation/download/archive extraction/newimage/merge/publication. Preserve all old histories/originals/main/Drafts102–129/SDK/image/31siblings3846hashes. 20scompile/5sprobe/64KiBstream/8MiBtree/1200swhole; sanitizedenv/no preload/cache/hwcaps fallback/privatefixture-only closure. Known fullmatrix ordinary/tmp+3real/dev/shm,oldguards/capacity/tests unchanged.

## Review Focus

1. A valid symbol in the merged library must not hide missing declared-library version; explicit nondefault symbol lookup must retain name/type/version and actual bound provider distinctions (Task1).
2. Extra/tampered/symlinked fixture/loader paths,constructors,external neededs,RPATH,IFUNC or injected LD/compiler environment must be rejected before loader spawn (Task1).
3. Wrong return status alone,missing/truncated/spoofed trace,timeout/output limit/unreaped process must not become a passed negative or positive control (Task1).
4. Old318/prior receipts/fixed image inventory/cache loader/original provenance/ownsource322/CI and explicit CPU opt-in must all bind before four image-loader calls; partial failure consumes only observed slots and never retries (Task2).
5. Import/final-write/late-check failures must retain a fresh parseable negative and exact invocation facts without overwriting old results or admitting SDK/runtime/fullABI/fullclosure/Stage7 (Task2).

### Task1: Closed CPU fixture core

**Files:** Create scripts/panda_loader_cpu_fixture.py,tests/test_panda_loader_cpu_fixture.py; new contract/frozen318 map.
**Interfaces:** build_fixture(out:Path)->dict; validate_fixture(out:Path,manifest:dict)->None; run_cases(loader:Path,fixture:Path,manifest:dict,out:Path)->dict; validate_observation(case:str,command:dict,trace:str,paths:dict)->dict. contract(),source_closure(),validate_ci() feed Task2.

- [x] Write inert -nostdlib fixture behavior tests:hostGNUloader baseline7/merged-nondefault7,missing-library-version/wrong-target-version reject with required trace and no successful binding. All assertions refer actual CPU process effects, not mocked loader output.
- [x] Add fixture bytes/extra files/symlinks/ELF metadata/environment guards,wrong-loader/trace/status/stream/ownership/case/budget/oldsource/CI negatives. Run `python -B -m unittest discover -s tests -p test_panda_loader_cpu_fixture.py -v`; Expected RED missing module.
- [x] Implement exact sources/six compiler commands/closed metadata+byte manifests/private environment/bounded owned execution/case-slot ledger/trace+return validators. Add fixed contract/source322/ownCI. Run same; Expected GREEN, host-loader CPU cases separately labelled/no SDK qualification. Commit.

### Task2: Source-bound fixed-image-loader execution

**Files:** Create scripts/probe_panda_loader_versions.py,tests/test_probe_panda_loader_versions.py; owned result/ledger/evidence.
**Interfaces:** probe(source:str,registrations:list,out:Path,run_cpu_fixtures:bool=False)->dict; frozen_state()->dict; verify_source(source:str)->dict. Consumes Task1 and unchanged old provenance/inventory/source primitives.

- [x] Write source322/prior receipts/loader pin+metadata+private-copy/nooptin/wrongCI/bootstrap/final-write/freshout negatives and partial-case accounting. Run new tests; Expected RED missing module.
- [x] Implement stdlib atomic receipt before imports,explicit CPU flag/exact source322+CI+prior receipts/original origin+image inventory/byte-pinned loader staging,closed fixture compilation/validation,then exactly4case slots. Recheck source/old receipts/loader bytes and preserve precise partial facts on failure; never retry/accept an arbitrary payload. Run focused tests; Expected GREEN.
- [ ] Run full known matrix; Expected GREEN. Sole fresh wholebranch review after commit, regrade,ONE Important RED→GREEN fix pass/fullgreen,Minor deferred/no rereview. Save source322 snapshot/logs.
- [ ] OwnDraft against feature/panda-provider-version-witness-v1 at09948dd(actual PR number),exact reviewed-sourceCI4jobs/attempt1/artifacts0; Expected PASS. Then explicit --run-cpu-fixtures with fixed loader cache exactlyonce/freshout; Expected observed4case outcomes or retained negative without relaxing checks.
- [ ] Document actual scope/counts/traces and limits,rulings,deferredMinors; preservebase7997/old318/histories/receipts/siblings. Archive/remove only ownscratch;docs-onlyfinalHEADCI4jobs/clean/exactremote/output-onlyfinalreceipt. Expected noSDK/native-science/newbuild/image/publication/merge; strict0of4FAIL/Stage7INCOMPLETE.

## Self-review

Fixture manifest and observations are exact Task2 inputs; closed four-case names and cumulative invocation ledger align. Each focus has owning negatives. CPU fixture execution is new explicit scope, not a change to historical SDK authority. No unknown dependency or arbitrary target path.
