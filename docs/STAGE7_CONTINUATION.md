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
- PR #21 shadow-feedback isolation merged as
  `96069779c85a691a81d119f27cafe39160c70cfa` from final source
  `ce1015973fc35332cc5a217ea07adfa21e7bfdcc` after all **14 checks**,
  current-SHA Codex review without findings/no open threads, clear independent
  source/docs reviews, **281 local tests without skips**, and exact independent
  revalidation of the new 48-process feedback and old 32-process sampler cohorts.
- PR #22 completed-result documentation merged as
  `329b400f12999526157c5db24b27f70001ed57b4` from exact source
  `1a17b344be10bbfb62bb4077581a6ba40d7a1464` after four checks, Codex review
  without findings/no open threads and a fresh independent documentation review.
- PR #23 opaque ordering merged as `d1e209d61af5cfa7c482fe09712f85f7496958e6`
  from exact source `983732f8e4713686a669a16058e6a93da871a620` after nine checks,
  current-SHA Codex review without findings/no open threads and clear independent
  eight-file review. Run 42968294569 completed 5/5 jobs with all five artifact
  API SHA/size/safe-path checks and exact four-case/final regeneration.
- PR #24 completed opaque/depth documentation merged as
  `19db37e4e0e85af4377ce5b796e64a2c8934f34f` from exact source
  `55c17181dcc8b535ac3b07e0583dca1c4ce9a64c` after four successful checks,
  completed Codex review without findings/no open threads and a clear fresh
  independent four-document review. Main unit run **42978229606** passed.
- PR #25 experimental official-model renderer candidate merged as
  `e840022a73879164b4923f77dbb4aabaf1112131` from exact HEAD
  `0fbebed2358610a773d317ef8e857acf6ddf5c98` after nine checks, completed
  current-SHA Codex review without findings/no open threads and a clear
  independent raw-evidence review. **313 local tests passed without skips**.
- Candidate native module SHA256 is
  `5a9058102004e2f5eaa4c9dcab4c24d97a9d42702b7a9e7c248c4f576a30d22e`.
  Source candidate run **42979680883** completed 5/5 jobs, with all five API
  archive SHA/size/safe-path checks and exact four-case/final raw regeneration.
  Eight unique UUIDs/nonces and two distinct same-runner PIDs per case executed
  96 official model steps. Every required field matched in all 48 paired steps:
  **candidate 4/4 PASS**, historical unmodified original **0/4 PASS (FAIL)**.
- PR #26 completed results documentation merged as
  `1077144170346e23279a91c832ce414534f377fe` from exact source
  `0c8b86a501457b754ef3a90fd2535a566d75d54b`, after four successful checks,
  completed Codex review without findings/no open threads and a clear fresh
  independent four-document review. Both model cohorts and the cross-cohort
  comparison are fully recorded in `STAGE7_MDV3_RENDERER_CANDIDATE.md`.
- PR #27 remains open on `feat/stage7-mdv3-candidate-expansion`. Its frozen
  executable source is `e84369c9f7f461a59c8d506b8b9efb2312297c03`;
  source run **42987993022** completed all13 jobs. Root and fresh independent
  review verified all13 API archive sizes/SHAs/safe paths and exact raw case/
  final regeneration:24 fresh UUIDs/nonces,1472 actual inferences/completed
  rows,736 paired exact rows. camera028/native_ramps/longer160 each pass4/4
  **legacy-action repeatability only**, with no first mismatch/incomplete row.
  Source passed17 checks and Codex review without findings/no open threads.
  **329 local tests passed without skips**,16 also in the pure NumPy environment.
  A documentation-only result update still needs its own checks and review.
- **Confirmed model-to-world boundary defect:** legacy model FRD positive
  curvature is rightward; unchanged virtual FLU yaw integration treats it as
  leftward. The missing fixed right-handed body rotation is diag(1,-1,-1),
  determinant+1; world curvature must negate model curvature, acceleration
  stays unchanged. Pinned parser/publisher/controller source and nine pure
  signed/zero/nonzero-heading cases confirm this; no controller/plant ran.
  Source/model outputs, all historical states/actions/poses and gates remain
  unchanged. Every legacy candidate pass is repeatability-only, not motion
  validity, tracking or model quality. All four160-step cases visit only the
  first route lane (active index0), with39.0089–41.1555m maximum virtual lateral
  deviation. Eight seconds/nominal64m does not prove full S traversal.
- Next work is a separately versioned opt-in model-FRD→world-FLU action adapter
  around the unchanged audited policy, preserving raw outputs, I420 and states.
  A new complete-only original2seeds×2S×12×2 corrected gate must run before
  any corrected expansion. The adapter/fresh native gate is not yet executed.
  Detailed legacy results,13 archive hashes, coordinate proof and CPU costs:
  `STAGE7_MDV3_CANDIDATE_EXPANSION.md`. Original-renderer0/4 remains FAIL.
  Query actual HEAD/PR/Actions before merge or further pushes; do not rerun the
  completed heavy legacy expansion simply for documentation.
- Automatic merged-main model replication **42981493726** completed 5/5 jobs
  and also passes candidate 4/4. All five API archive SHA/size/safe-path checks
  and exact raw case/final regeneration passed; fresh independent read-only
  main-evidence review is clear. Unit main **42981493834** passed.
  Both cohorts have 16 unique UUIDs/nonces and 192 actual model steps without
  identity reuse, with two distinct same-runner PIDs per case. A read-only
  cross-cohort comparison also matches all four processes per case across all
  required fields and initial/configuration receipts (six pair combinations
  per case,288 row checks reusing192 model steps). Hardware identities were
  not retained; no hardware-equivalence claim follows. Main-evidence
  review and revised prospective expansion-plan review are clear. Do not
  launch another manual repeat. Results-documentation PR #26 has now merged;
  expansion push still needs its own frozen source/workflow review and checks.
- The new source passed **298 local tests without skips**. Two real production
  `both_unsorted` OFF processes passed native/bin/nonce controls and matched
  every source/warp/I420 field **10/10**, with fresh shared cache cold→populated.
  Evidence: `output/opaque-order-source-smoke/`. This validates the separate
  before-provider implementation path; no four-case or official gate is implied.
- The new 32-process source cohort is now fully revalidated: 32 unique UUIDs/
  nonces, eight same-runner PIDs per case and preserved CPU bin setup/capture/
  restore metadata. Both unsorted conditions match all image fields 40/40
  across four cases; original/Both state-sorted I420 matches 38/40 and 36/40.
  This is a policy effect in the balanced static matrix, not unique causality,
  renderer equivalence or the official model gate. Details: `STAGE7_OPAQUE_ORDER.md`.
- Automatic merged-main opaque run **42969968780** completed 5/5 jobs with
  all five API archive SHA/size/safe-path checks and exact raw case/final
  regeneration: 32 UUIDs/nonces, eight same-runner PIDs per case. Original
  state-sorted I420 is 37/40, Both state-sorted 36/40; both unsorted arms again
  match every field 40/40, complete 4/4. Unit run **42969968794** passed.
  The native module SHA remains unchanged from tested source 983732f.
- Local terminal-depth V2 is now complete: eight valid native processes,
  unique PIDs/UUIDs/nonces, statuses zero and one truthful extraction per
  custom receipt. All eight 8,388,608-byte atlas files are exact matches with
  5,347 nonclear texels; raw/binary/clock/state/cache revalidation and exact
  comparison passed. This bounded one-scene result is separate from the OFF
  matrices and does not promote renderer equivalence or an official gate.

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
- PR #21 source cohorts are complete: feedback **42957706605** (48 native
  processes, 128 GPU rows) and sampler **42957706445** (32, 64). All ten API
  archive SHA/size/safe-path checks and every case/final summary reproduced
  exactly. Full results and ledger: `STAGE7_SHADOW_FEEDBACK.md`.
- The merge automatically started separate main-source `9606977` cohorts:
  feedback **42961355528** completed 5/5 jobs; all five API archive SHA/size/
  safe-path checks and exact case/final recomputations passed, with 48 UUIDs,
  12 same-runner PIDs per case and 128 GPU rows. OFF I420 baseline/linear/
  guard/both matched 36/40, 36/40, 35/40, 32/40; complete cases 3/4, 2/4,
  3/4, 2/4. Sampler
  **42961355395** completed 5/5 jobs and all five API archive SHA/size/safe-path
  checks and four-case/final recomputations exactly passed: 32 UUIDs, eight
  same-runner PIDs per case, 64 GPU rows. Original OFF source Road/Wide 27/40
  and 30/40, warped 27/40 and 35/40, I420 23/40 (17/32 post-warmup), zero
  complete cases; other three arms every field 40/40, 32/32 post-warmup and
  4/4 static cases. Full five-archive ledger: `STAGE7_SHADOW_FEEDBACK.md`.
  Unit run **42961355303** passed. Both automatic cohorts are complete;
  preserve their negative results rather than manually repeating them.

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
Those earlier timing pilots established no repair. The later official-model
candidate 4/4 is recorded separately below; historical original 0/4 remains.

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
The [feedback plan](superpowers/plans/2026-11-11-shadow-feedback-isolation.md)
is implemented and its 48-native-process source cohort is complete. Each of
four conditions used two OFF repeats plus one terminal-only ON process per
case. All four case/final summaries exactly revalidated; 48 UUIDs, 12
same-runner PIDs per case, and 128 terminal GPU rows were verified.

| Feedback condition | Source Road/Wide /40 | Warped Road/Wide /40 | I420 /40 | Complete static cases /4 |
| --- | --- | --- | --- | --- |
| baseline | 36/39 | 36/40 | 36 | 3 |
| linear | 37/37 | 37/38 | 36 | 2 |
| shadow_guard | 37/36 | 37/40 | 37 | 3 |
| both | 35/34 | 35/37 | 33 | 2 |

No condition repaired strict 4/4 equality. Every first-running condition fails
its case; two second-position conditions also fail. Latin-square assignment
balances which condition starts first but fixed seed/scene orders, process/cache
history and OFF0 → OFF1 → ON0 sequencing still confound causal interpretation.
Terminal controlled-state bindings validate 32 rows in each of four intended
classes, with all 128 pre/post GL errors zero. Actual RGB samples/buffers are
8/1 and shadow 0/0; query-only sums span 1.657115–1.993208 ms per ON process.
These are not per-primitive fetch traces or total-overhead measurements.
Full rates, firsts, cross-condition image changes and all ten source-cohort
archive digests/byte sizes: [STAGE7_SHADOW_FEEDBACK.md](STAGE7_SHADOW_FEEDBACK.md).
The separate old-sampler regression matches original OFF I420 27/40 and
source Road/Wide 30/40 and 31/40, warped 30/40 and 35/40; other arms all 40/40.
Its 32 processes and 64 binding rows preserve compatibility, not a repair claim.

The automatic main feedback repetition **42961355528** independently reproduces
failure of every condition to match strict 4/4:

| Main feedback condition | Source Road/Wide /40 | Warped Road/Wide /40 | I420 /40 | I420 post-warmup /32 | Complete static cases /4 |
| --- | --- | --- | --- | --- | --- |
| baseline | 36/38 | 36/40 | 36 | 28 | 3 |
| linear | 37/37 | 37/38 | 36 | 29 | 2 |
| shadow_guard | 35/36 | 35/40 | 35 | 28 | 3 |
| both | 32/37 | 32/40 | 32 | 25 | 2 |

The six failed same-condition OFF comparisons are below; every other case/
condition has no source/warp/I420 difference across all ten frames.

| Seed | Scene | Main feedback condition | I420 /10 | First I420 | I420 different steps |
| --- | --- | --- | --- | --- | --- |
| 20261109 | left_right | baseline | 6 | 5 | 5, 7, 8, 10 |
| 20261109 | left_right | linear | 8 | 2 | 2, 7 |
| 20261109 | right_left | linear | 8 | 5 | 5, 6 |
| 20261110 | left_right | shadow_guard | 5 | 2 | 2, 3, 6, 7, 8 |
| 20261110 | left_right | both | 7 | 2 | 2, 6, 8 |
| 20261110 | right_left | both | 5 | 3 | 3, 5, 7, 9, 10 |

The cyclic orders and first-/second-position failure pattern recur, without
isolating a unique order/cache cause. Main OFF0/ON0 totals equal same-condition
OFF totals but remain temporal/process observations; baseline-to-linear/both
cross-condition matches are 0/40 for every field, and baseline-to-guard matches
source 32/29, warp 32/35, I420 28/40. Full per-case source/warp firsts,
comparisons and all five archive SHA/byte sizes are in the feedback guide.
Main feedback's 128 GPU rows again validate 32 rows per class, zero pre/post
GL errors, actual RGB samples/buffers 8/1 and shadow 0/0. Its summed query
duration range is 1.684994–4.932800 ms per ON process, separate from the
source cohort's 1.657115–1.993208 ms; neither is full instrumentation overhead.

Earlier combined OFF local smoke with a populated cache matched all fields
10/10; the supported local ON state setup showed RGB 4/1 and shadow 0/0.
A later **fresh-shared-cache `both` OFF** pair failed: source Road/Wide 7/10
and 8/10, warped 7/10 and 10/10, I420 7/10, first I420 step 4, differences
4, 6, 8. Retained: `output/shadow-feedback-local/fresh-mesa-both/comparison.json`.
Its generic schedule comparator's original-control flag must not label the
experimental `feedback_both` treatment as original renderer output.

A separate local two-process `both` plus edited-terrain explicit-gradient
prototype also failed: source Road/Wide 6/10 and 8/10, warped 6/10 and 10/10,
I420 6/10, first step 2, differences 2, 4, 5, 8. Retained:
`output/terrain-gradient-pilot-v2/{run-0,run-1,comparison}.json`.
It preserves the vertex shader and explicitly edits the fragment shader;
it is outside the current feedback schema, has no observer/official weights,
and uses shared fresh cache cold → populated without a randomized unmodified
control. The earlier v1 anchor assertion failed before native capture/JSON;
log: `output/terrain-gradient-pilot/run-0.log`. These negative prototypes do
not establish a unique gradient cause. The next source-review hypothesis is
per-camera `ShaderTerrainMesh` view-data lifetime/LOD; no validated effect or
repair is recorded yet.

The preregistered local llvmpipe worker ABBA pilot is complete:
`default_0 → zero_0 → zero_1 → default_1`, `LP_NUM_THREADS` unset versus `0`,
one fresh shared cache per arm (cold → populated), four unchanged original
Road-first processes for 20261109 / left-right, no observer/shader/model.
All four launcher statuses were zero, with four distinct native UUIDs/PIDs.
Default source Road/Wide matched **8/10 and 6/10**, requested-zero **8/10 and
8/10**; both warped Road/Wide matched **8/10 and 10/10**, I420 **8/10**, first
difference **2**, differences **2, 7**. Whole-process wall times in ABBA order:
**65.803, 112.260, 111.605, 61.028 s**, not pure worker overhead. Retained:
`output/llvmpipe-worker-pilot/{plan,execution_receipts,comparisons}.json`, native
receipts/logs and before/after cache SHA manifests. Mesa documents zero as
disabling threading and pinned source reads the setting, but there is no actual
worker trace. Requested zero is not a complete fix; this single-case fixed
order/cache comparison does not establish necessary parallelism or unique
causality. A new CI matrix is not needed to falsify this complete-fix candidate.

Workspace-only apitrace v2 ABBA capture is complete: `off_0 → on_0 → on_1 →
off_1`, four valid native JSON, zero raw statuses and four unique UUIDs/PIDs.
OFF source Road/Wide matches 8/10 and 8/10, warped 8/10 and 10/10, I420 8/10
(post-warmup 7/8), first 2, differences 2 and 7. ON source matches 7/10 and
2/10, warped 7/10 and 10/10, I420 7/10 (post-warmup 5/8), first 7,
differences 7, 9, 10. Whole-process ABBA wall times are 81.540, 72.697,
81.861, 77.912 s, not pure overhead. All four JSON/logs, cache/native SHA
receipts, comparisons and both complete traces remain in
`output/apitrace-draw-pilot-v2/`; full trace sizes/SHA256 are in the feedback
guide. The earlier attempt retains valid OFF0 but failed ON0 `ERROR`/partial
trace under `output/apitrace-draw-pilot/`, not a full valid matrix.
V2 initializes Python's default SIGINT handler before runpy of the original
module in **all** arms. Capture/rendering source remains unchanged; the tracing
tool hides program-binary formats, changing driver capability as well as timing.
Bounded read-only trace forensics is complete, with reports under
`output/apitrace-draw-pilot-v2/analysis-agent/`. Full call counts are
106555/106580; each trace has 2901 geometry draws and 192 buffer passes.
Eight shader-source submissions and 322 ordered CPU texture uploads match
full arguments/blob SHA. The first non-timestamp difference, call 9027,
program 1's 100-matrix `p3d_TransformTable`, changes 828 floats in actually
used slots 0–68, affecting startup draws 9029/9375/9738. Slots 69–99 are equal
and Panda identity-fills unused slots; it is not differing padding.
Only startup passes 19–21 differ in unordered geometry/uniform inputs; every
primary/control pass matches analyzed geometry/explicit-uniform/constant-vertex
input multisets. Geometry order differs in 53 passes; 2898 matched draws
have identical active sampler/CPU texture inputs. First primary order change:
pass 67 / FBO 3, ON0 skybox call 35777 → terrain call 35823, ON1 terrain
call 35802 → skybox call 35828;
following Wide reads 37381/37387 align with its first source-frame mismatch.
Order also changes on equal frames, so necessity/sufficiency is unproven.
Six tracked skybox GL_MULTISAMPLE differences occur only on main FBO 7, none
on HDR FBOs 3/5; full GL state/GPU atlas contents were not reconstructed. Existing
original-path hazards and trace capability/timing changes prevent unique-cause
or GL-repair claims. Pinned Panda render-state/bin comparators use attribute,
vertex-format, munged-data and transform pointer ordering; this is source
behavior, not a demonstrated image-drift cause.

The local **Both plus opaque-bin modifier** v3 pilot is complete at
`output/opaque-bin-pilot-v3/`: `state_sorted_0 → unsorted_0 → unsorted_1 →
state_sorted_1`, four unique native UUIDs/PIDs, all raw statuses zero, raw JSON
SHA/request-nonce receipts and unchanged strict wire validation. It used one
fresh shared Mesa cache per arm (cold → populated), seed 20261109 / left-right,
observer OFF/no GL query/profiler, no shader changes or extra ticks.

| Local bin treatment on Both | Source Road/Wide /10 | Warped Road/Wide /10 | I420 /10 | First I420; different steps |
| --- | --- | --- | --- | --- |
| state-sorted, type 2 | 9/5 | 9/10 | 9 | 9; 9 |
| unsorted, type 1 | 10/10 | 10/10 | 10 | none |

Typed bin reads are 2 → 2 versus 2 → 1 before primary captures. Whole-process
ABBA wall times are 82.702, 78.100, 71.165, 68.015 s, not pure sorting cost.
Within each state-sorted process post-warmup Road/Wide/I420 has 2/2/2 unique
hashes, versus 1/1/1 for each unsorted process; those within-process counts
are separate from two-process repeatability. Same-index treated-frame
membership in either state-sorted repeat is 16/20 for Road/warped Road/I420,
20/20 for Wide/warped Wide. Membership is not equivalence proof, tolerance
or an alternate gate. Fixed ABBA/cache history and one case still confound
causality; local unsorted 10/10 is not a repaired official 4/4 gate.

V1's in-memory pose-tuple validation failed before writing, losing native JSON;
log/cache/failure metadata remain under `output/opaque-bin-pilot/`. V2 saved
valid observed JSON, but retained wrapper status 1 from the in-memory tuple
check; data/failure metadata remain under `output/opaque-bin-pilot-v2/`.
Neither is included in v3's four successful processes. V3 writes and reloads
JSON before unchanged strict validation; no native criterion was relaxed.

The [opaque-order isolation plan](superpowers/plans/2026-11-11-opaque-order-isolation.md)
is now implemented and its source cohort **42968294569** is complete. Four
conditions cross original feedback_baseline / feedback_both with opaque type
2 / 1, using two independent OFF repeats per case and cyclic Latin order:
**32 native processes, 32 unique UUIDs/nonces and eight PIDs per case**. All
five archives and every case/final summary exactly revalidated.

| Opaque condition | Source Road/Wide /40 | Warped Road/Wide /40 | I420 /40 | Post-warmup I420 /32 | Complete static cases /4 |
| --- | --- | --- | --- | --- | --- |
| original_state_sorted | 38/38 | 38/40 | 38 | 30 | 3 |
| original_unsorted | 40/40 | 40/40 | 40 | 32 | 4 |
| both_state_sorted | 36/36 | 36/40 | 36 | 29 | 3 |
| both_unsorted | 40/40 | 40/40 | 40 | 32 | 4 |

Only the two state-sorted cases below fail; all other condition/case image
fields match 10/10. Full tables, execution orders, raw evidence paths and the
complete five-archive SHA/byte ledger are in
[STAGE7_OPAQUE_ORDER.md](STAGE7_OPAQUE_ORDER.md).

| Seed | Scene | Opaque condition | I420 /10 | First source Road/Wide | First I420 | I420 different steps |
| --- | --- | --- | --- | --- | --- | --- |
| 20261109 | left_right | original_state_sorted | 8 | 5/4 | 5 | 5, 7 |
| 20261110 | left_right | both_state_sorted | 6 | 2/4 | 2 | 2, 7, 8, 9 |

Cross-sorting image equality is original source 62/66 of 80, warp 62/76,
I420 58/80; Both source 62/58, warp 62/66, I420 48/80. Thus policy changes
observed repeatability in this balanced matrix without proving byte/rendering
equivalence or a unique microcause. The CPU bin receipts preserve original
index 2/name opaque/sort 20/active true, requested type 2 or 1 through capture
and restoration to 2. This OFF matrix has no GPU queries or actual per-draw trace;
previous GL renderer/sample/sampler observations are not new cohort evidence.
Actual setup logs record Python 3.11.18, MetaDrive 0.4.3, Panda3D 1.10.13,
NumPy 2.4.6 and OpenCV 5.0.0.93; `runtime-log-evidence.json` retains those package observations,
not a queried GL renderer.

The separate automatic main repetition **42969968780** is now complete and
exactly revalidated from all 32 raw receipts and five verified archives.

| Automatic main opaque condition | Source Road/Wide /40 | Warped Road/Wide /40 | I420 /40 | Post-warmup I420 /32 | Complete static cases /4 |
| --- | --- | --- | --- | --- | --- |
| original_state_sorted | 37/37 | 37/40 | 37 | 30 | 3 |
| original_unsorted | 40/40 | 40/40 | 40 | 32 | 4 |
| both_state_sorted | 36/36 | 36/40 | 36 | 29 | 3 |
| both_unsorted | 40/40 | 40/40 | 40 | 32 | 4 |

| Seed | Scene | Automatic main condition | I420 /10 | First source Road/Wide | First I420 | I420 different steps |
| --- | --- | --- | --- | --- | --- | --- |
| 20261109 | left_right | original_state_sorted | 7 | 2/4 | 2 | 2, 9, 10 |
| 20261110 | left_right | both_state_sorted | 6 | 2/4 | 2 | 2, 7, 8, 9 |

All other main condition/case image fields match 10/10. Main cross-sorting
matches original source 59/63 of 80, warp 59/76, I420 55/80; Both source
62/58, warp 62/66, I420 48/80. The five-archive SHA/byte ledger and full
case tables are in the ordering guide. This reproduces static unsorted 4/4,
not renderer equivalence or the original moving-model gate. Requested CPU bin
and restoration controls pass; the new cohort adds no GL renderer/sample/
sampler observations or draw trace. No manual repetition is needed.

The supported module sets the bin before provider creation, independently
from the earlier pilot's after-provider hook. Rendering-semantic validation
and the official moving model gate remain open. A separate external operations
helper's first eight-process protocol stopped as **failed/partial** at entry 5,
`both_unsorted` repeat 1, status 2 before capture: the reused feedback native
trial rejects `probe=True`/repeat 1. Four valid native depth-read captures are
retained, not a complete eight-process cohort or semantic-equivalence result.
The fifth raw ERROR has zero extractions; its log/ledger are retained at
`output/terminal-atlas-semantics/`. The old helper remains immutable at SHA
`131857958a2ab1a551dbec7da9481c9d274d1da822bfb7c416d9a2a38d805801`.
Do not restart it or hide the valid partial observations and failed entry.

V2 at `output/terminal-atlas-semantics-v2/` is complete and independently
revalidated: **8/8 valid native processes, all statuses zero, eight unique
PIDs/UUIDs/nonces**, exact raw comparison and final cache rehashes. Frozen
helper SHA is
`08f9a1da50b4dec790720bfcda0789dd074b2f09bed38f4dd58b845e304a7033`;
exact-helper review and nine CPU tests preceded native execution. The custom
public-raw-API protocol truthfully records one extraction per process, outside
the supported OFF schema. Terminal ON is after primary frames; saved GL state
is restored, recorded GL errors are zero and frame counts before/after read
and after provider return all remain 32.

All eight 2048×1024 float32 atlases are **8,388,608 bytes**, **2,097,152 finite
[0,1] texels**, **5,347 nonclear**, min **0.3487148582935333**, max **1.0**, with
common SHA
`e2fad785dc9037146323996699cb8c2a23e517bb99acce5557ee5957fe234881`.
Within-condition, guard and sorting comparisons all have zero changed depth
texels/max Delta 0, byte-exact. Primary within-condition I420 is linear sorted
8/10, linear unsorted 10/10, Both sorted 7/10, Both unsorted 10/10. Linear→Both
I420 is 7/10 and 8/10 for sorted repeats, 10/10 and 10/10 for unsorted; every
source/warp field also matches 10/10 in both unsorted guard comparisons.
Full five-field tables are in the ordering guide. This supports terminal depth
preservation and no observed guard byte change in the unsorted pairs in one
static 20261109 / left-right scene, not global shadow accuracy/photometric
or renderer equivalence. ON/readback/order/cache/process effects remain limits.
Direct glGetTexImage-only time is 0.920867–1.796358 ms, excluding other queries,
setup/IO/whole terminal cost. The local probe observes Mesa 25.0.7-2+deb13u1,
llvmpipe LLVM 19.1.7 / GL 4.5 compatibility, actual threading model `/` with empty
cull/draw names; those are not OFF CI matrix GPU observations.

## First official-model candidate source gate: 4/4 PASS

The [candidate plan](superpowers/plans/2026-11-11-mdv3-renderer-candidate.md)
is implemented and its first source cohort is complete. It uses the original
`NativeWorldCamera` and public `run_target_lane_episode`, preserving original
ego RGB visibility, original task/capture/kinematic behavior and official model
identity. It applies the opt-in Both-plus-unsorted treatment; the static trial
that hides visual ego is not used for the model episode. Runtime is actual
CPU ONNX Runtime 1.31.1 with CPUExecutionProvider/ORT_ENABLE_BASIC (level 1).
No extra inference, GPU query, texture extraction or RGB observer was added.

| Seed | Scene | Source Road/Wide /12 | Warped Road/Wide /12 | I420 /12 | Action/state/pose-time matches /12 | First difference | Candidate gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 20261109 | left_right | 12/12 | 12/12 | 12 | 12 each | none | PASS |
| 20261109 | right_left | 12/12 | 12/12 | 12 | 12 each | none | PASS |
| 20261110 | left_right | 12/12 | 12/12 | 12 | 12 each | none | PASS |
| 20261110 | right_left | 12/12 | 12/12 | 12 | 12 each | none | PASS |

Across 48 paired steps, every source/warped RGB and actual I420 feed hash,
all four raw action values/bytes, parent action conversion, aggregate and all
three typed named-state receipts, capture-entry pose and post-action virtual
pose/time match exactly. No first mismatch or tolerance occurs. Every trial
has twelve distinct source/warp/I420, action and aggregate-state hashes;
named image/feature states have twelve, while desire remains the expected
constant zero state. Initial/reset/schema and two-tick clock controls validate.

Additional named-state audit wall time is **5.533088–13.862155 ms** per step,
total **0.662456844 s** across 96 model steps. This stored extra audit block
includes state/action receipt work after the parent step; it is not full
inference/instrumentation overhead. Whole delegated capture spans
**4.091141–9.297873 s**, not pure overhead. All four case summaries and final
aggregate exactly reproduce from the eight raw JSONs, ledgers and five verified
ZIPs. The [candidate guide](STAGE7_MDV3_RENDERER_CANDIDATE.md) records full
48/48 fields, state schema, archive SHA/byte ledger and limits. Evidence:
`output/stage7-remote-evidence/run-42979680883/` and
`output/stage7-remote-evidence/artifacts-42979680883.json`.

This official-model **candidate** 4/4 is separate from historical original
0/4 FAIL and does not adopt defaults, prove renderer/optical equivalence,
identify a unique microcause, rank driving or complete Stage 7. Earlier
unmodified, sampler/cache/feedback failures and partial protocols remain
preserved. Automatic main replication 42981493726 is now complete and also
passes candidate 4/4; its fresh independent evidence review is clear.

The main repetition executes another eight native processes / 96 actual model
steps, with all 48 required within-cohort paired comparisons and all three
named states exact. Every main source/warp/I420 sequence and named image/
feature state has twelve distinct hashes; desire remains the expected zero
state. ORT remains CPU 1.31.1/BASIC level 1 and no GPU query/extraction/observer is added.
Main extra named-state audit wall time is 6.495361–16.398507 ms, sum 0.733913688 s;
whole capture 5.182054–9.343551 s is not pure overhead. The guide records its
own five-archive SHA/byte ledger and raw evidence at
`output/stage7-remote-evidence/run-42981493726/`. Together the source and main
cohorts have 16 unique UUIDs/nonces, 192 model steps and no identity reuse;
these exact comparisons are within each cohort's repeat pairs.
Per-camera terrain view-data lifetime/LOD remains a separate unproven
source-review hypothesis. The [feedback guide](STAGE7_SHADOW_FEEDBACK.md)
records the worker pilot's full rates, evidence paths and causal limits.

## What remains unresolved

**Historical unmodified original MD-V3 remains 0/4 PASS (FAIL); the explicitly
labeled experimental candidate source cohort now passes 4/4.** These are
separate records. Candidate success does not prove full renderer equivalence,
photometric/sensor optics, a unique GPU microcause or driving performance,
and it does not promote a renderer default or complete Stage 7. The candidate
preserves original model-camera/public-loop behavior and audited recurrence;
its rendering interventions and CPU audits remain explicitly labeled.
The earlier raw-linear/cache/feedback failures remain part of the evidence.

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
gh pr list --state all --head feat/stage7-mdv3-candidate-expansion
gh run list --branch main --limit 12
```

Main cache run 42951160118 is already complete and independently revalidated
(24 native processes, exact summaries/snapshots). Shared/isolated/disabled
I420 matched 19/40, 34/40 and 29/40 respectively; no complete repair. Query
current branch HEAD/PR before starting work. Automatic feedback 42961355528
and sampler 42961355395 are already complete and independently revalidated;
feedback OFF I420 is 36/36/35/32 of 40, sampler original OFF 23/40 and other
arms 40/40. Unit run 42961355303 passed.
Do not manually repeat complete sampler/cache/feedback matrices merely to
rediscover recorded results. Preserve cancelled/failed evidence.

The feedback and ordering source cohorts, the bounded terminal-depth protocol
and the first official candidate source gate are complete. Do not replay them
merely to rediscover their recorded results. Automatic candidate replication
**42981493726** is complete and exactly revalidated, with clear fresh
independent review; unit main **42981493834** passed. The
[prospective expansion plan](superpowers/plans/2026-11-11-mdv3-candidate-expansion.md)
has clear independent review of its revised protocol. Results-documentation
PR #26 is merged. Legacy expansion run42987993022 is also complete and
independently revalidated (24 processes,1472 inferences,736 exact pairs; each
group4/4 legacy-action repeatability only). Finish PR #27 result-documentation
checks/current-HEAD review and gated merge; do not launch that cohort again.
Then continue the separately versioned corrected-world adapter and its original
four complete12-step cases before any corrected expansion. Preserve every
failure/partial result and exact legacy labels; no historical gate/default changes.

The trace/depth comparisons remain bounded input/one-scene evidence. Preserve
raw files and distinguish traced correlations or terminal depth preservation
from universal untraced causal/photometric behavior. Keep the original
NativeWorldCamera/public episode path for model diagnostics; do not substitute
the visual-ego-hiding static trial or relax state/action/image/pose/time gates.
Continue source review of per-camera terrain view-data lifetime/LOD while
preserving original PSSM/Chase and Road-first controls
and two independent OFF processes per condition. Terminal ON bindings do not
establish retroactive repairs or executed primitive fetches. Keep edited-shader
prototypes separate from original-control and supported feedback receipts.
Do not promote cache disabling, linear sampling, a shadow-input guard or a
terrain edit without causal and rendering-semantics validation. Record a
reproducible CI vs local/runtime explanation:
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
python -m scripts.native_shadow_feedback_matrix --mode aggregate \
  --root output/verified-feedback-root --out output/feedback-recomputed.json
python -m scripts.aggregate_native_mdv3_rgb_pixel_matrix \
  --root output/verified-original-pixels --out output/pixels-recomputed.json
```

The source and main candidate strict gates each pass4/4 for their registered
twelve-step cases, and the completed legacy expansion passes4/4 per group.
These use the confirmed incorrect unconverted action-frame binding. Finish
PR #27 documentation checks/review/merge, then implement/review the separate
corrected-world adapter and original four-case complete gate. Inspect actual
HEAD/PR/Actions before any corrected trigger; no legacy cohort rerun is needed.
Keep all source/warp/I420, raw action, aggregate/named recurrence and virtual
pose/time comparisons exact. Historical original 0/4 remains unchanged;
default promotion, global geometry/optical fidelity, driving ranking and
Stage 7 completion require separate evidence.
