# Campaign03 saved clock/pixel implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Inline execution, one fresh whole-change review.

**Goal:** Narrow the strictFAIL investigation with authenticated saved03 clock/RGB evidence and exact CPU propagation.
**Architecture:** Read selected members directly from immutable pinned ZIPs; reuse pure CPU transforms and catalogs. No native producer modifications.
**Tech Stack:** Python3.11, NumPy2.4.6, opencv-python-headless5.0.0.93, unittest.
**Spec:** ../specs/2026-11-14-engine-clock-pixel-forensics.md

## Global Constraints

No new worktree, provider, renderer, getters, ORT, model, original overwrite, allowance,
main merge or Cloud/registry publication. All261 producer pins unchanged. Logical raw
retention128MiB, output2MiB, sparse64pixels, subsets≤16/capture. OFF clocks are null.
Counter values are per-process and not physical frame IDs. strict0/4FAIL remains.

## Review Focus

1. Foreign/corrupt ZIP or unsafe member cannot acquire accepted provenance.
2. OFF clock data is never treated as zero or measured equality.
3. Capture/camera/pose/intrinsic associations cannot silently cross.
4. Broad first-capture states are retained; sparse cap applies only ordinal cohorts.
5. CPU subsets cannot mutate originals or claim real model/GPU interventions.

### Task 1: Authenticated saved-byte adapter and analysis

**Files:** Create scripts/engine_clock_pixel_forensics.py and tests/test_engine_clock_pixel_forensics.py.
**Interfaces:** Consumes the two fixed03 ZIPs and existing pure analyze_pair/state_catalog;
produces run(canary_archive, abba_archive, out) and compare_observations(left,right).

- [ ] Write tests for equal counters/differentRGB, OFF nulls, wrong camera/ordinal,
  corrupt/duplicate/traversal ZIP members, decoded hash/transform mismatch, broad
  states retained and derived-only packed association. Use literal expected values.
- [ ] Run focused unittest; Expected: missing new module failures (RED).
- [ ] Implement bounded pinned archive admission, source/context association, endpoint
  reconstruction, complete catalog, clock comparisons and copied-array subsets.
- [ ] Run focused plus existing CPU forensic/state tests; Expected: all pass.
- [ ] Commit code/tests and record command/outcome in this plan's ledger.

### Task 2: Actual03 execution and independent review

**Files:** New docs/evidence/STAGE7_ENGINE_CLOCK_PIXEL_FORENSICS_03.json and
docs/STAGE7_ENGINE_CLOCK_PIXEL_FORENSICS.md; update continuation and ledger.
**Interfaces:** Consumes Task1 CLI and originals; produces scientific report and review package.

- [ ] Run pinned CPU CLI against retained originals into a fresh output file.
  Expected:30 reconstructed pairs/60rawframes,0newnative/model/ORT, strictFAIL retained.
- [ ] Inspect counts, exact coordinates/subsets and saved clock examples; write findings
  and explicit limits. Verify current261 producer hashes remain unchanged.
- [ ] Run full unit suite; Expected: pass with existing environment-dependent skips.
- [ ] One fresh read-only whole-change review (code+tests+actualreport), most capable
  available reviewer. Re-grade findings; one Critical/Important RED→GREEN fix pass;
  defer Minor and ledger all declined-scope decisions/costs. No second reviewer.

### Task 3: Draft and verification

**Interfaces:** Consumes reviewed change; produces own branch/DraftPR and exact-head CI records.

- [ ] Commit verified evidence and push own branch; create Draft against prior evidence
  branch. Expected: exact HEAD, Draft/unmerged, no native workflows triggered.
- [ ] Verify both exact-head CI events and jobs; record generated SMALL graph separately
  from official model calls. Verify workflow03 run count and main SHA unchanged.
- [ ] Update Draft body using exact JSON PATCH/roundtrip. Final report gives findings,
  test/CI/review evidence, limitations, exhaustive rulings and deferred Minor items.
