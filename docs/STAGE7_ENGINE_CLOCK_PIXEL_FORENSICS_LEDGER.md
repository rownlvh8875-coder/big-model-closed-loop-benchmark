# Campaign03 saved clock/pixel ledger

Plan: superpowers/plans/2026-11-14-engine-clock-pixel-forensics.md
Base: dfffc3d7a81d44a58185d605972c9978086d957a; branch analysis/engine-clock-pixel-forensics-03.

Ruling: Continue inline in the existing checkout and create only a new branch — the
user already requested uninterrupted execution and no additional worktrees — branch
isolation does not protect unrelated uncommitted edits; initial tree was clean.

Ruling: Analyze saved03 bytes before requesting another native experiment — they
contain the first accepted same-host clock-boundary ABBA — this can narrow observable
signatures but cannot uniquely identify a GPU/shadow/task cause.

Pre-flight: Task1's pinned JSON report is consumed verbatim by Task2; Task3 consumes
reviewed code/report and exact commit IDs. No producer or original-file writes.

Task1 RED: new module absent;10/10 tests failed in setUp as expected.
The first GREEN attempt exposed a fixture error: arbitrary1000px focal lengths
violated the existing1324/283.5 optical contract. Corrected only the fixture.
Task1: complete — focused new10 plus existing33 CPU tests,43/43 PASS/0.582s,
command: pinned CPU python -B -m unittest tests.test_engine_clock_pixel_forensics
tests.test_first_divergence_pixel_forensics tests.test_texture_marker_state_sequences -v.
No frozen producer files changed. Original ZIPs will be read directly, not extracted.

Task2: complete — actual pinned CPU CLI PASS,30reconstructed pairs/60rawframes;
report264966B/SHA556410b01b38e03741989e98c130f6fc37962ddf9e576ec10a545d44dc040136.
Full pinnedCPU python -B -m unittest discover -s tests -v:
1209tests,0failures/0errors/7existing skips/111.217s. Full log and root crosscheck
retained under output/stage7-engine-clock-pixel-forensics-03/closeout/.
Review head57ce8b52b1b2ba26e9e6fc5206752c066fd9d3ca:
fresh gpt-6-astra/medium independently checked both fullZIPs/261Git+currentfiles/
all30endpoints/16subsets/catalogs/clock comparisons. C0/I0/M1; no code fix pass.
[Exact scope and findings](evidence/ENGINE_CLOCK_PIXEL_FORENSICS_03_REVIEW.md).

Final: minor (deferred): CP-M1 — reviewed57ce8b5 continuation's closeout wording
preceded actual Task3 receipt. Historical HEAD remains unchanged; cost: reading
that historical revision alone can imply premature remote verification. Actual
Task3 closeout is recorded separately, as already planned.

Final: Ruling: Native/GPU/observer-neutrality and unique-cause behavior remains
unjudged — no native action was authorized by this saved-byte experiment — cost:
the first renderer cause remains unresolved and no renderer fix is justified.

Final: Ruling: Model/ORT/driving/optics/geometry/fullS/strictPASS remains unjudged —
derived-only I420 has no real model-call association — cost: strict0/4FAIL and
Stage7INCOMPLETE remain, with no prediction of driving effects.

Final: Ruling: Offline byte provenance is accepted only in its stated scope — pinned
original SHA checks do not newly attest the live service or physical host — cost:
the previously accepted live acquisition remains an external trust boundary.

Final: Ruling: Root owns full-suite and future exact-head CI/Draft verification —
fresh reviewer independently ran43focused tests, not the fullsuite or futureCI —
cost: those closeout observations have one verifier rather than two.

Task3 local preflight: diff --check PASS; original03 workflow's branch/path filter
does not match this analysis branch. Main48e79a7ed5aedf6daa5a62ff68d2225af7955ef1,
prior evidencePR97 Draft/unmerged atdfffc3d7a81d44a58185d605972c9978086d957a;
sole03 run43571004531/attempt1SUCCESS preserved. No code changes after review.
Final push/PR/CI observations are retained in
output/stage7-engine-clock-pixel-forensics-03/closeout/final-verification.json and
the own branch Draft body. Their exact-head authority is separate from reviewed57ce8b5.
No new native request or allowance is introduced by this analysis branch.
