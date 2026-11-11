# Stage 7 — isolate camera order from shared-mount task tick count

## Evidence and hypothesis

PR #15 merged after both original and strengthened-HEAD 32-process cohorts
were independently validated. Sequential-original I420 matched 29/40 then
27/40 frames, while paired-original and both PSSM task-removal arms matched
40/40 in each cohort. This association does not isolate camera mounting,
readout order, task tick count, or PSSM state as the unique cause.

The original model RGB pixel artifacts were also revalidated. The first
25 changed pixels lie near road/curb/terrain boundaries in the reviewed
images; no material, shadow or depth semantic segmentation was measured.

## Registered independent A/B design

MetaDrive 0.4.3, SHA256-pinned official assets, native 964×604 Road/Wide,
model RGB 512×256, packed I420 `(2,6,128,256) uint8`. Fixed lane WORLD pose
at fraction 0.12, height 1.22m. Seeds 20261109 and 20261110, S-curves
left-right and right-left, ten frame pairs with the first two retained as
warmup. Each condition uses two separate Python/Panda/Xvfb processes:

| Arm | Mount/read schedule | Task ticks per pair |
| --- | --- | ---: |
| sequential_road_first | Original Road perceive then Wide perceive; each camera restored by upstream perceive | 2 |
| sequential_wide_first | Experimental Wide perceive then Road perceive; same upstream restore behavior | 2 |
| paired_one_tick | Mount both at the requested WORLD pose, run one task tick, then read both CPU textures | 1 |
| paired_two_ticks | Mount both at the requested WORLD pose, run two consecutive task ticks, then read both CPU textures | 2 |

All conditions retain the original PSSM.update, Chase and igLoop tasks.
There is no GPU texture extraction, additional shader/MVP update, fixed-clock
intervention, ONNX inference, image tolerance, smoothing, replay or model
ranking. CPU repeat readback and +2m pose positive controls remain required.
This is 4 cases × 4 arms × 2 repeats = 32 independent native processes.

Comparisons are only between repeats of the SAME treatment. A paired-two-tick
result can distinguish reducing task count from keeping both cameras mounted,
but it still changes image sampling time relative to sequential perceive.
Reversing camera order changes both which sensor is sampled earlier and
which camera is temporarily mounted in each tick. It cannot by itself isolate
GPU draw ordering, a shader defect, or a single callback. CPU copies and
validation add timing overhead in every arm; no claim of overhead-free capture.

## Implementation plan and checks

- [x] Test original/reversed order and one/two shared ticks using the real
  capture helper with small fake node/texture boundary adapters.
- [x] Extend only diagnostic capture-mode dispatch in
  `scripts/metadrive_render_causality.py` and `scripts/native_raw_pixel_clock.py`.
  Leave original model camera/policy and all existing defaults unchanged.
- [x] Add a strict comparator/aggregate in
  `scripts/compare_native_capture_schedule.py` with tests rejecting missing,
  stale, mismatched-mode/tick/task/hash/process/control evidence.
- [x] Add an explicit native workflow, four cases, eight separate processes
  each, with an independent raw-receipt reaggregation job.
- [ ] Run targeted and full tests, local representative native modes, review,
  GitHub unit/native CI and archive SHA revalidation before merging.

Report source Road/Wide RGB, warped Road/Wide RGB, I420 match counts, every
first difference, metadata and artifact IDs. Hash equality in a static scene
is not original moving-camera MD-V3 repeatability. The official strict gate
remains **0/4 PASS (FAIL)** until its separate original conditions are rerun
following a causally justified, semantics-validated repair.

## Local implementation validation

Full suite: 232 passed, no skips. Four real independent native processes
exercised both new modes (two repeats each) and their clock/task/pose/SHA
receipts passed validation. At seed 20261109, left-right scene, wide-first
source Road/Wide matched 8/10 and 5/10, I420 8/10; paired-two-tick source
Road/Wide matched 8/10 and 8/10, I420 8/10. This local compatibility sample
used concurrent treatments on the cloud CPU host; causal interpretation
awaits the separately provisioned CI jobs with their original controls.

A read-only reviewer found that UUID uniqueness alone could overcount
independent processes. A failing regression was added and a same-runner
per-scene PID uniqueness guard fixed it; no bare-PID uniqueness is required
across different CI machines. No additional review findings were identified.

New native CI and actual artifact results have not yet been recorded here.

## Xvfb cleanup-status review correction

The GitHub review identified the repository's known Xvfb cleanup exit status 5.
The new `scripts/run_native_capture_trial.py` rejects preexisting output,
launches one fresh native process, preserves other failure statuses, and
accepts status 0 or cleanup-only status 5 only after the full newly generated
native task/clock/pose/hash receipt validates. Missing or invalid receipts
still fail. Five runner tests plus the full 232-test suite passed. New exact-
HEAD native CI and automated review must be confirmed after this correction.
