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
- PR #19 documentation merged as `ee3ded6e71b8b2cb8c5603c1c934c1eac20d1841`.
- PR #20 cache history merged as `465bf0c49a585fecb8ad313cac3b29e96736b8b6`
  from final source `e3df7d1a74c2d7d7e6e2ac1cc3c3421da7b65eb8` after all
  nine checks, current-SHA Codex review without findings, fresh independent
  review, **259 local tests** and complete 24-process artifact revalidation.
- The PR #18 source had **248 passed, no skips** and four final native sampler
  smoke processes. PR #20 adds a separate final-validator local six-process
  cache case; earlier capture validation and its five processes remain separate.
- Current branch: `feat/stage7-shadow-feedback-isolation`, building the next
  opt-in factorial experiment. No assigned PR is recorded at this checkpoint;
  query GitHub for the latest branch HEAD/PR rather than inventing a number.

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
- PR #18 merged-main cohorts are complete and independently revalidated:
  sampler **42944861575** (32 processes), capture order **42944861604** (32),
  PSSM **42944861717** (32), raw clock **42944861577** (16). All 19 archive
  SHA/size/safe-path checks passed; every case/final summary reproduced exactly.
  Sampler original OFF source Road/Wide 31/40 and 32/40, warped 31/40 and
  35/40, I420 26/40; other three arms every field 40/40. Capture original
  I420 21/40; other arms 40/40. PSSM original sequential I420 25/40; other
  arms 40/40. Four raw-clock summaries exactly reproduced. Full ledgers and
  limits are in `STAGE7_SHADOW_SAMPLER_ISOLATION.md`; source unit run
  **42944861578** passed. These repetitions do not erase earlier failures.
- PR #20 merge push main cache cohort **42951160118** completed 5/5 jobs and
  was independently revalidated from all five archives/snapshots and 24 native
  receipts. Shared/isolated/disabled I420 matched 19/40, 34/40 and 29/40;
  source unit run **42951159987** passed. Do not repeat this completed cohort.

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

## Completed cache-history experiment and next hypothesis

The earlier four-process ABBA pilot (seed 20261109 left-right) matched shared
I420 8/10, isolated 10/10. Its shared source Road/Wide matched 8/10 and 6/10;
cache population was recorded outside native lifetimes under
`output/cache-order-pilot/`. It motivated the completed balanced experiment;
a directory inventory is not proof of a cache hit or unique cause.

PR #20's independent CI run **42948547486** completed **5/5 jobs**. All five
archive API hashes/sizes and safe paths, all retained cache snapshot rehashes,
four case summaries and the aggregate were verified: **24 unique native UUIDs
and six distinct same-runner PIDs per case**. Original sampler, Road-first,
PSSM/Chase, two task ticks and uninstrumented primary capture were preserved.

| Cache arm | Source Road/Wide /40 | Warped Road/Wide /40 | I420 /40 | Complete static cases /4 |
| --- | --- | --- | --- | --- |
| shared | 23/23 | 23/29 | 19 | 0 |
| isolated | 34/38 | 34/40 | 34 | 3 |
| disabled | 37/35 | 37/35 | 32 | 2 |

Isolated still fails 20261110 left-right: I420 4/10, first step 2, differences
2, 5, 6, 7, 9, 10. Disabled-first coincides with right-left and disabled-last
with left-right, so scene/order confounding prevents a causal order claim.
No cache arm is a strict 4/4 repair. Full per-case/order and cross-condition
rates, archive SHA/byte ledgers, logs and causal limits are in
[STAGE7_SHADER_CACHE_HISTORY.md](STAGE7_SHADER_CACHE_HISTORY.md). Evidence:
`output/stage7-remote-evidence/run-42948547486/{recomputed,totals,verified_archives}.json`
and `revalidation.log`. Cancelled **42947832747** and **42948096573** retain
all eight verified partial ZIPs, not full 24-process cohorts.

The final-format local six-process case also passed the final validator with
all existing summary fields exact. Shared/isolated/disabled I420: **8/10,
10/10, 8/10**; shared differs at 2 and 7, disabled at 4 and 8. Retained result:
`output/cache-matrix-local/seed-20261109/s_curve_left_right/final_validator_recomputed.json`.
It is distinct from the earlier four-process pilot and the CI cohort.

A new terminal-only local probe records four original shadow post-region
bindings: depth attachment `GL_TEXTURE` object 1 at level 0 and active atlas
texture 1 with `use_pssm=1`; both shadow camera initial states were empty.
Retained evidence: `output/stage7-remote-evidence/shadow-feedback-terminal-probe.json`.
This supports a potential read/write feedback binding hypothesis, not a
per-primitive trace, actual atlas-fetch proof or unique renderer cause.
The [next implementation plan](superpowers/plans/2026-11-11-shadow-feedback-isolation.md)
is a four-condition factorial comparison: original, linear sampler,
shadow-input guard, both; two OFF repeats and one terminal-only ON process
per condition/case, **48 native processes**. The implementation is present on
this branch; no four-scene CI results are established at this checkpoint.
A local combined-condition OFF pair matched every source/warp/I420 field
10/10. One production-launcher terminal ON process passed full native/nonce and eight
binding-row validation (shadow placeholder/use_pssm=0, RGB real atlas/raw-linear/
use_pssm=1). Actual shadow/RGB samples/buffers were 0/0 and 4/1. The complete
local suite passed 281 tests without skips.
These are local smoke observations, not a repaired official model gate.

## What remains unresolved

**Original official MD-V3 strict gate remains the prior 0/4 PASS (FAIL).**
There is no new causal renderer repair or new official ONNX run. Static
experimental 4/4 equality must not replace the original moving-camera gate.
No original camera default, PSSM/Chase callback, shader, model input bytes,
recurrent states or actions were changed. Geometry, rendering determinism,
real-sensor optical equivalence and driving performance remain separate.
The sampler treatment is opt-in and experimentally changes rendered bytes;
its source-cohort OFF arm failed strict native matching even though a later
merged-main static repetition matched 4/4. Cache controls also fail 4/4.

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
gh pr list --state all --head feat/stage7-shadow-feedback-isolation
gh run list --branch main --limit 12
```

Main cache run 42951160118 is already complete and independently revalidated
(24 native processes, exact summaries/snapshots). Shared/isolated/disabled
I420 matched 19/40, 34/40 and 29/40 respectively; no complete repair. Query
current branch HEAD/PR and any newer automatic cohorts before starting work.
Native jobs automatically triggered by merges are separate cohorts. Do not repeat
the complete sampler or cache matrices manually merely to rediscover their
recorded results. Preserve cancelled/failed evidence.

Continue the linked shadow-feedback factorial plan while retaining original
PSSM/Chase and Road-first controls. Keep sampler type and shadow-pass input
guard separate, balance condition order and retain two independent OFF
processes per condition. Terminal ON binding observations follow every primary
frame; they do not establish retroactive repairs or executed primitive fetches.
Do not promote cache disabling, linear sampling or a shadow-input guard without
causal and rendering-semantics validation. Record a reproducible CI vs local/runtime explanation:
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
python -m scripts.native_shader_cache_matrix --mode aggregate \
  --root output/verified-cache-root --out output/cache-recomputed.json
python -m scripts.aggregate_native_mdv3_rgb_pixel_matrix \
  --root output/verified-original-pixels --out output/pixels-recomputed.json
```

Only a causally supported, rendering-semantics-validated repair can advance
Task 4. Then execute the separate original 2 seeds × 2 S-curves × 12 steps ×
2 independent processes strict MD-V3 gate (all source/warped RGB, actual I420,
action, all recurrent-state digests, pose and virtual time must match). Only
an exact 4/4 permits longer runs, more repeats, positions and ramp expansion.
Do not claim Stage 7 completion while this gate is open.
