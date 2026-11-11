# Stage 7 continuation — verified results, renderer cause still open

## Current checkpoint (2026-11-11)

- PR #15 merged as `0c678facbf72c269c2453f472e64d8192b70d675` after verifying
  exact HEAD `f1dc88d476942de05f913cbc828a5fa5912e78a3`, nine checks,
  completed Codex review, no unresolved threads and both 32-process cohorts.
- PR #16 merged as `1d4a236cb85f4af3b94d6289b81aac89665f4c4e` after verifying
  exact HEAD `696008be2c9fa9a91ca5c928fb8f2462fc36f496`, nine checks,
  completed Codex review, resolved Xvfb finding and all new 32 raw receipts.
- PR #17 documentation merged as `a7726a3112ed48fda4d430ebfc5588032807e3fd`.
- PR #18 sampler diagnostics merged as `177103b1b5bc47586d3366d542299f7cf4f28675`
  after exact source HEAD `3adc288f244e001a22ce69ce73f0fa7d514ce98a` passed
  nine checks, current-SHA Codex review, independent review and full 32-process
  artifact revalidation. No default renderer change or repair promotion.
- Local full suite on the final source: **248 passed, no skips**. Four final
  native processes validated the new sampler/probe arms; earlier capture
  scheduling validation and its five native processes remain separate evidence.
- Current documentation branch: `docs/stage7-shadow-sampler-evidence`, based
  on the PR #18 merged main. Query GitHub for its assigned PR and latest SHA;
  do not assume a future PR number or reapply already merged changes.

The user authorized continued development and gated PR merges. Do not publish
or reconfigure the cloud environment. API access now works with supplied
GitHub authentication; never inspect/print credentials. Use the existing
isolated checkout, not a new worktree.

## Evidence already acquired and independently revalidated

Full details, first-difference RGB values, per-arm rates, artifact IDs, ZIP
SHA256 digests, limitations and source references are in
`STAGE7_RGB_SCHEDULER_FINDINGS.md`. Method: `STAGE7_CAPTURE_SCHEDULE_ISOLATION.md`.
New sampler defect, 32-process results, all archive digests and runtime limits:
`STAGE7_SHADOW_SAMPLER_ISOLATION.md`.

- Sampler run 42942700897: all five jobs/archives verified, 32 UUIDs, eight
  same-runner PIDs per case; all case/final summaries exactly regenerated.
  Original OFF source Road/Wide 27/40 each, I420 22/40; linear OFF source
  38/40 and 40/40, I420 38/40, only 3/4 complete static cases. The failure is
  seed 20261109 left-right: Road/I420 first step 2; I420 differs at 2 and 7.
  Both terminal-observer ON arms matched 40/40 primary frames, but the observer
  runs after all primary frames, so cannot establish a repair to earlier frames.
  Fixed arm order and process/cache history remain confounds.
- Sixty-four controlled inherited-state GPU observations validated actual atlas
  binding and nonshadow sampler: 32 original with depth comparison enabled,
  32 linear with comparison disabled. This violates/fixes the GL sampler type
  consistency rule, but does not prove unique drift causality or shadow accuracy.
  Original-versus-linear images/I420 all differ: semantics changed. No default
  switch is justified. Local linear OFF/ON source Wide also matched only 6/10.
- Shared-source regressions 42942287909 (16 processes/4 jobs), 42942287958
  (32/5), 42942287899 (32/5): every archive digest checked and all summaries
  exactly regenerated. Relevant capture/workflow/validator inputs equal at
  tested source 850172b and final source 3adc288. Default path has no sampler
  diagnostic receipt. Superseded 42942288117 is cancelled, with four ZIPs and
  seven validated partial original-OFF receipts; it is not a passed matrix.
- Merge push automatically started new cohorts on source main 177103b:
  sampler **42944861575**, capture order **42944861604**, PSSM **42944861717**,
  raw clock **42944861577**. They were still running at this checkpoint;
  source unit CI **42944861578** passed. Query these before any manual repeat.

- Original source-pixel run 42924910245: four native jobs + aggregate,
  eight instrumented MD-V3 processes, 12 ONNX steps each, 96 retained source
  RGB images re-decompressed/SHA-checked; uploaded summary exactly reproduced.
- PSSM scheduling runs 42927840424 and 42930483265: 32 processes each,
  all ten ZIPs verified and both full aggregates exactly reproduced.
- Camera-order/tick isolation run 42934781823: 32 distinct UUIDs, eight
  distinct same-runner PIDs per case; all five ZIPs and aggregate verified.
  Original Road-first I420 27/40; Wide-first, paired-one and paired-two 40/40
  each. Two ticks can match, so fewer ticks are not a necessary explanation.
- Shared-capture regressions 42933830938, 42933831001, 42933831083 succeeded;
  the relevant workflow/capture/validator inputs are identical at the final
  source HEAD. Four raw pixel-clock summaries and the 32-process PSSM summary
  were regenerated exactly; render-causality ZIP verified. Its six worlds
  share one Python process, unlike the independent-process matrices.
- Automatic merged-main order/tick run 42936911857 also completed and was
  revalidated from all 32 receipts and five archive digests: original I420
  22/40, each experimental mode 40/40. This is an independent CI repetition,
  not proof of an original moving-model repair.
- Historical callback runs 42819410983 and 42822587924: all sixteen archive
  SHA/size checks and comparison regenerations succeeded; 96 profiled ticks
  in each experiment put PSSM before Chase. CPU order is not GPU draw proof.
- Superseded matrix 42933831409 was cancelled after the Xvfb workflow fix;
  never count it as a passed experiment. Status 5 requires a fresh valid
  native receipt; stale/missing/invalid output and native failures still fail.

Local capture modes sometimes disagreed despite their CI counterparts
matching. A local hash-seed pilot (unset vs 0, ABBA, two independent repeats
per treatment, seed 20261109 left-right) matched 10/10 in both groups; it
provided no discriminating repair evidence. The external CPU-load pilot also matched 10/10 in two independent loaded
processes, despite median pair wall time increasing from about 4.3–4.5s to
9.2–9.7s. It did not reproduce disagreement in this one case. Workers were
stopped; preserve this limited negative result, not a universal timing claim.
There is still no validated renderer repeatability repair or new official ONNX gate.

## New local cache-history pilot

Four additional original Road-first processes, seed 20261109 left-right, ran
shared_0 → isolated_0 → isolated_1 → shared_1 with only per-process
`MESA_SHADER_CACHE_DIR` controls. Shared initially-empty then populated cache:
source Road/Wide 8/10 and 6/10, I420 8/10 (first 2; differences 2 and 7).
Separate initially-empty caches: every source/warp/I420 field 10/10.
Cache inventories proved population (0 → 101 files / 1,670,747 bytes); later
shared process started populated, ending 1,692,275 bytes. This is a
**discriminating local candidate**, not proof of hits or unique causality.
Raw local receipts, UUID/PIDs, logs and cache files are under ignored
`output/cache-order-pilot/`; see the sampler findings document for limits.

Next implement a balanced independent CI comparison of shared initially-empty
cache, separately empty caches and explicitly disabled disk cache, retaining
original sampler/PSSM/Chase/Road-first and uninstrumented primary captures.
Vary arm execution order across seed/scenes; record inventories only outside
native processes. Do not replay the already complete sampler matrix manually.

## What remains unresolved

**Original official MD-V3 strict gate remains the prior 0/4 PASS (FAIL).**
There is no new causal renderer repair or new official ONNX run. Static
experimental 4/4 equality must not replace the original moving-camera gate.
No original camera default, PSSM/Chase callback, shader, model input bytes,
recurrent states or actions were changed. Geometry, rendering determinism,
real-sensor optical equivalence and driving performance remain separate.
The sampler treatment is opt-in and experimentally changes rendered bytes;
its OFF observer arm still fails strict native matching.

First Wide source changes at step 2 in both left-right pixel cases are outside
all admitted model-warp support; actual warped RGB and I420 first differ at
step 6. Later edge pixels require more care: the conservative footprint is
not an exact sampling mask, and the measured historical lens matrix was not
retained. Do not overclaim that every earlier source difference is cropped.

## Resume without repeating completed experiments

```bash
cd /workspace/big-model-closed-loop-benchmark
source /workspace/.cloud-tools/onboarding/activate.sh
git status --short
git log -5 --oneline
gh pr list --state all --head docs/stage7-shadow-sampler-evidence
gh run list --branch main --limit 12
```

First finish/check the documentation PR and its current-HEAD checks/review.
Native jobs automatically triggered by merges are separate cohorts; query
status before starting any manual repeat. Preserve cancelled/failed results.

Then continue cause isolation, retaining original PSSM/Chase and Road-first
controls. Prioritize execution order, persistent shader/cache state and
initialization history: the later original-sampler primary pair matched in CI
even though its observer was installed only after its primary sequence.
Compare a fresh shared Mesa shader cache (cold then warm process) with two
isolated empty caches, alternate execution order and inventory caches only
outside native capture intervals. A directory inventory is not proof of cache
hits. Retain negative results; don't promote cache disabling or extra warmup
without discriminating causal evidence. Record a reproducible CI vs local/runtime explanation:
actual graphics-engine/output configuration, driver, package versions,
framebuffer properties and timing at noninterfering boundaries. Declared
multi_thread_render=true/Cull alone is insufficient: one local runtime probe
reported an engine threading model `/` with empty cull/draw names. Do not
adopt thread, clock, order, warmup or GPU barrier changes from declarations
or one matching sample. Any new readback/profiler/GPU probe needs an OFF
control, independent processes and explicit overhead/interference reporting.

Use SHA-pinned official assets and only ephemeral-CI official MD-V3 weights.
Keep raw data in CI artifacts/ignored `output/`, not Git. To revalidate a
cohort: list its artifact API metadata, download ZIPs, compare SHA256 and
sizes, inspect member paths, combine the four `seed-*/scene` subtrees, then
run the experiment's aggregate script and require exact equality with the
uploaded final summary. Current tools:

```bash
python -m scripts.compare_native_capture_schedule --mode aggregate \
  --root output/verified-capture-root --out output/capture-recomputed.json
python -m scripts.compare_native_pssm_cross_process --mode aggregate \
  --root output/verified-pssm-root --out output/pssm-recomputed.json
python -m scripts.compare_native_shadow_sampler --mode aggregate \
  --root output/verified-sampler-root --out output/sampler-recomputed.json
python -m scripts.aggregate_native_mdv3_rgb_pixel_matrix \
  --root output/verified-original-pixels --out output/pixels-recomputed.json
```

Only a causally supported, rendering-semantics-validated repair can advance
Task 4. Then execute the separate original 2 seeds × 2 S-curves × 12 steps ×
2 independent processes strict MD-V3 gate (all source/warped RGB, actual I420,
action, all recurrent-state digests, pose and virtual time must match). Only
an exact 4/4 permits longer runs, more repeats, positions and ramp expansion.
Do not claim Stage 7 completion while this gate is open.
