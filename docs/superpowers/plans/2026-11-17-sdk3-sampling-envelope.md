# SDK3 Sampling Envelope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline; TDD; one fresh wholebranch reviewer, no implementer delegation. Steps use checkbox syntax.

**Goal:** Quantify whether modeled precision alone changes the yellow predicate at already-captured mip1 candidates.
**Architecture:** Stdlib numerical helper, authenticated CPU-only evidence driver, additions-only output/report.
**Tech Stack:** Python3.11 stdlib/unittest; unchanged prior host receiver uses existing numpy; no new dependencies.
**Spec:** ../specs/2026-11-17-sdk3-sampling-envelope-design.md

## Global Constraints
Base d6eb529d52364117a01d446652f2e938089625c2; all old tracked bytes immutable.11fixedinputs,1MiB/file2MiBtotal,indexSHA pinned;5points,135scenarios,1MiBoutput. No new renderer/model/inference/GPUquery/readback/install/runtime change. Only within-cell scalar arithmetic; unavailable never invented. SNORM/UNORM/FMA/8-bit12-bit weights are hypothetical, not hardware guarantees. All actualhardware/owner/cause/repair/Stage7false; original3/4PASS overallFAIL. NewDraftPR based on PR142,no mainmerge/environmentregistrypublication. Exact final canonical4jobs/attempt1/artifacts0 required.

## Review Focus
1. Numerical model silently claims driver precision/format or predicts actual RGB; testfalseclaims in result schema.
2. Sparse footprint crosses a cell, wraps or duplicates corners; missing/partial values must remain unavailable and unextrapolated.
3. Strict threshold equality, flat derivatives, out-of-domain roots and nonfinite values yield false branch flips or meaningless world distances.
4. Float32 separate/FMA or normalized-code ties differ from stated model; literal numerical/branch tests pin assumptions.
5. Pinned input loading accepts mutated index/bytes/identity or a prior-validation claim as a fresh capture; integration negative tests and explicit provenance.

### Task 1: numerical helper
**Files:** Create scripts/sdk3_sampling_envelope.py,tests/test_sdk3_sampling_envelope.py,input-index/spec/plan.
**Interfaces:** normalize(values,mode)->list; attribute_uv(local_uv,ratio,mode)->list; fractions(uv,size)->list; bilinear(values,fractions,bits=None)->float; threshold_roots(values,fractions)->list; conditional_envelope(values,fractions,bits)->dict; scenario(window,uv,format_mode,weight_bits)->dict.
- [ ] RED literals SNORM.075→10/127/.15→19/127,UNORM.075→19/255,ties/clamps; .01/.11 strict; known bilinear/linearaxis roots/flat/outsidecell; f32 path/ratio; unavailable/cell escape/nonfinite. Run unittest tests.test_sdk3_sampling_envelope; Expected missing-helper FAIL.
- [ ] GREEN minimal helper, all namedtestsPASS, commit.

### Task 2: authenticated CPU driver
**Files:** Create scripts/run_sdk3_sampling_envelope.py,tests/test_sdk3_sampling_envelope_host.py.
**Interfaces:** load_inputs(root)->dict exactpinned receipts; analyze(inputs)->dict, main --out directory (fresh only) writesresult.json; no native execution.
- [ ] RED actualfixedinputs integration5points/135scenarios, result flagsfalse, SNORMconditionalroots; byte/index/identity tamper, coldhelp/freshoutput. Run unittest tests.test_sdk3_sampling_envelope_host; Expected missing-driver FAIL.
- [ ] GREEN minimal loader/model enumeration/output/CLI; focused new+old prepared/terrain/window regressionsPASS and commit.

### Task 3: actual CPU result, one review, final CI and closeout
**Files:** Create docs/STAGE7_SDK3_SAMPLING_ENVELOPE_RESULT.md,docs/evidence/sdk3-sampling-envelope-01/result.json,input-analysis.json,review/**,scriptsdata only.
- [ ] Execute actual CPU driver from fixedinputs; independently recompute center SNORM/roots, inspect all135scenarios/5points and conditional intervals; hash result/provenance, commit evidence.
- [ ] One fresh wholebranch review against spec/plan/ledger; Important fixonce RED→GREEN+suite, Minor defer; no rereview.
- [ ] Push new feature branch/createDraftPRparent142; exact finalHEADpush+PR4jobsPASS/fullcounts. Update PR with concreteactual results.
- [ ] Verify finalhead/body/parent/main/originalsixfiles/sourceadditionsonly; archive ownledger, externalexactHEAD receipt, deleteonlyownscratch. Originalmatrixunchanged/no publication.
