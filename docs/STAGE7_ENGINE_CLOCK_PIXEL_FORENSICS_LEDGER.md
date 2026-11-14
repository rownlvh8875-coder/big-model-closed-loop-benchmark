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
