# Missing fourth SDK3 model condition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline,one fresh review of this new addition,no implementer delegation. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Finish the fourth condition without repeating or dropping any completed case.
**Architecture:** New host-only controller authenticates03carrier,recomputes all three predetermined complete pairs,copies exact raw bytes,runs only the missing pair through unchanged f3helpers,and invokes unchanged full aggregator.
**Tech Stack:** Python stdlib/unittest,pinned Docker image/SDK/model,GitHub Actions.
**Spec:** ../specs/2026-11-16-sdk3-final-condition-design.md

## Global Constraints

Basef3bb85b6e692ecfd1efb54e2af3aabb93beb3c3e; all existing files unchanged; source additions only. Same10GiB/2CPU/softpipe/ORT1.20.1 profile. Prior03fixed135298B/SHAaed730...; include its failed third pair. New native2 only,selectedmatrix8,prior03actual8/7complete and02OOM1 separate. No main/registry/environment publication.

## Review Focus

1. A failing prior pair must be retained,never filtered (Task1fixturethirdFAIL).
2. Raw reports alone cannot hide nonzero/unknown native exit,OOM or cleanup (Task1negatives).
3. Wrong image/SDK/model/resources/seed or changed f3source must reject before target (Task1negatives/source delta guard).
4. An incomplete fourth prior pair must never be copied as complete or paired with a new PID (Task1copy test).
5. Final4case aggregate must revalidate source bytes and preserve strict failure (Task1aggregate test,actual execution).

### Task1: Host-only continuation and actual execution
**Files:** Create scripts/continue_panda_sdk3_models.py,tests/test_continue_panda_sdk3_models.py,.github/workflows/panda-sdk3-model-final-case-v1.yml; own evidence.
**Interfaces:** validate_source_delta(rows:list[str])->None; validate_case(folder:Path,seed:int,scene:str)->dict; copy_completed_cases(prior:Path,target:Path)->list[dict]; finalize_matrix(models:Path)->dict.
- [ ] Add real JSON-fixture tests for all five review focuses; focused commandExpectedRED.
- [ ] Implement exact provenance/byte-preserving composition/one missing pair/unchanged aggregate. FocusedExpectedGREEN;actionlint;commit/push.
- [ ] Exact sourceCI4jobs/sole fresh review/one ImportantRED→GREEN pass if needed;no rereview. ExpectedGREEN before activation04.
- [ ] Request-only04activation; observe exact native count2 and final recomputed four-case outcome; preserve negatives and actual source/Actions/artifact. Expectedhonest complete matrix,not necessarilyPASS.
- [ ] Final report/PRbody/continuation,source preservation,final docHEADCI and output receipt. No Stage7 completion or merge while strict fails.
