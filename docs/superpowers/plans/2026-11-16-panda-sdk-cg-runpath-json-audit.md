# SDK3 JSON receiver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline in the existing checkout. One fresh wholebranch reviewer after implementation, one Important fix pass; no implementer delegation. Steps use checkbox (`- [x]`) syntax.

**Goal:** Independently qualify the pinned SDK3 DATA artifact using correct JSON version-key comparison without changing consumed code/verdicts or rebuilding.
**Architecture:** Narrow pure JSON comparator plus separate read-only receiver. Reuse immutable origin/ZIP/evidence/ELF/provider primitives, a new fixed contract and source314.
**Tech Stack:** Python stdlib,GitHub read-only transport,handwritten inert CPU ELF version fixtures,unittest.
**Spec:** ../specs/2026-11-16-panda-sdk-cg-runpath-json-design.md

## Global Constraints

Base5c31664/Draft127,7863files/modes; preserve old310source identities,oldfailedreceipt,all prior pinned inputs/originals/main/Drafts102–127/native/image/mapping/dispatch/GLX/Cg/Eigen/RUNPATH histories and31siblings3846hashes. Samecheckout/inline/noquestions/ownDraft. No SDK build/activation/download/ELFpatch/imageoperation/target/SDK/Panda/GL/Xvfb/officialmodel/ORT/cohort execution,merge or publication. Scientific0/strict0of4FAIL/Stage7INCOMPLETE. Source314=310+fourcontractpaths; budget1200s,existing23file carrier/256MiBZIP/16MiBJSON bounds unchanged. Missing cache fails, no fallback. Root strong availability is not full ABI/provider closure/runtime/crash repair.

## Review Focus

1. Real ELF version tables survive serialize/parse and compare; int/bool,float/int,list changes and numeric-key collisions must never be normalized away (Task1).
2. Only version-table indices and the known provider-record location label are normalized; changed names/versions/missing rows/other data_path fields reject (Task1).
3. Same-sized poisoned cached ZIP/file/provider,symlinks,wrong run/source/CI/job/artifact or changed frozen source/old verdict cannot qualify (Task2).
4. Reusing caches cannot skip provenance,full evidence,actual ELF or provider recomputation; no legacy receiver call/global patch or new production request (Task2).
5. Catchable bootstrap/audit failures leave a negative fresh receipt without authentication/runtime flags or overwriting prior results (Task2).

### Task1: Narrow JSON semantic comparison

**Files:** Create scripts/panda_sdk_cg_runpath_json.py,tests/test_panda_sdk_cg_runpath_json.py.
**Interfaces:** canonical_metadata(metadata:dict)->dict; validate_reported_gate(claimed:dict,recomputed:dict,providers:dict,metadata:dict)->None. Export contract()/source_closure(root)/validate_audit_ci(source,registrations,proofs) for Task2 using hardpinned contract and original310map.

- [x] Write actual handwritten CPU shared-library/version-script fixture; inspect_elf emits integer version keys, JSON round trip makes strings. New comparison must accept equal metadata while old receiver still rejects. Never load/execute fixtures.
- [x] Write type/order/value/version/missing-row/unknown-field/advisory-path/numeric-key collision/bool/nonfinite/depth/node/string bound negatives. All ordinary scalar types preserved, only canonical table indices0..32767 normalize; reject duplicate raw JSON with existing strict parser.
- [x] Run `python -B -m unittest discover -s tests -p test_panda_sdk_cg_runpath_json.py -v`; Expected RED missing module. Implement narrow canonicalization and original selected gate field checks, typed deep equality and sole scoped provider-record data_path exception. Add closed contract/source314 and exact own-sourceCI2events/4jobs/attempt1/artifacts0 checks.
- [x] Run same; Expected GREEN. Commit tests/code/ledger.

### Task2: Pinned DATA-only receiver and actual audit

**Files:** Create scripts/accept_panda_sdk_cg_runpath_json.py,tests/test_accept_panda_sdk_cg_runpath_json.py,new own result/ledger/evidence. No old file edits or workflow/request files.
**Interfaces:** audit(source:str,registrations:list,out:Path)->dict; verify_cached_carrier(zip_path:Path,candidate:Path)->dict; provider_paths(inventory:dict,cache:Path)->dict. Uses Task1 comparison/contract/ownsourceCI and immutable v3 origin/carrier/evidence/static functions.

- [x] Write fixed tuple/sourceCI/source314 and cache/ZIP/hash/path/symlink/oldfailedreceipt negatives, typed report contradictions, missing cache and bootstrap failure receipts. Positive toy carrier checks no authority by itself; mock only remote reads or heavyweight static integration boundaries, never checks under test.
- [x] Run new test; Expected RED missing receiver. Implement own source verification against git-show, exact live original request/CI/run/job/artifact authentication and bounded existing-cache ZIP→retained23files→receipt binding. No download/extraction duplicate or build/activation. Rehash cached provider bytes through original inventory/static gate; full evidence then actual gate recomputation and Task1 comparison. Preserve original FAILED receipt and false runtime/fullABI/science flags. Recheck frozen source/cache before success; fresh positive/negative receipt and compact/full output evidence.
- [x] Run focused and full unchanged tests via known split real-filesystem matrix; Expected GREEN with observed counts. One fresh wholebranch review, one Critical/Important TDD fix pass/fullgreen suite, Minor deferred, no rereview.
- [x] Push own Draft, exact reviewed-sourceCI4jobs/attempt1/artifacts0; Expected PASS. Run new read-only audit of fixed run43786081196/artifact14191115165 after CI, no SDK build/request. Expected observed separate selected-static acceptance or retained negative; do not alter old verdict or waive semantics.
- [ ] Close with proof index,actual result/rulings/deferredMinors,ownscratcharchive/removal,base7863/source310/oldhistories/siblings preserved,docs-onlyfinalHEADCI4jobs and output-only final receipt. Expected clean/exactremoteHEAD/ownDraftunmerged; SDKbuild/activation/native/image/publication/merge0.

## Self-review

Both tasks share exact comparator/contract/source/CI signatures. Five focus cases have negative tests. Receiver preserves all source/evidence/ELF predicates and consumes the same pinned DATA, with typed JSON normalization rather than dropping version tables. Original failure stays immutable; new positive status is separate and never runtime admission. No unknown interface or new dependency.

Operational closeout after the final docs commit is recorded in output/stage7-panda-sdk-cg-runpath-json-01/final-verification.json; that output-only receipt closes the remaining finalHEADCI/clean/remote portion without another documentation commit.
