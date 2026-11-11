# Stage 7 continuation — verified results, renderer cause still open

## Current checkpoint (2026-11-11)

- PR #15 merged as `0c678facbf72c269c2453f472e64d8192b70d675` after verifying
  exact HEAD `f1dc88d476942de05f913cbc828a5fa5912e78a3`, nine checks,
  completed Codex review, no unresolved threads and both 32-process cohorts.
- PR #16 merged as `1d4a236cb85f4af3b94d6289b81aac89665f4c4e` after verifying
  exact HEAD `696008be2c9fa9a91ca5c928fb8f2462fc36f496`, nine checks,
  completed Codex review, resolved Xvfb finding and all new 32 raw receipts.
- Local full suite on the final source: **232 passed, no skips**. Five actual
  native processes validated both new modes and the status-aware launcher.
- Current documentation branch: `docs/stage7-verified-capture-findings`, based
  on the PR #16 merged main. Query GitHub for the assigned PR and latest SHA;
  do not assume a future PR number or reapply already merged changes.

The user authorized continued development and gated PR merges. Do not publish
or reconfigure the cloud environment. API access now works with supplied
GitHub authentication; never inspect/print credentials. Use the existing
isolated checkout, not a new worktree.

## Evidence already acquired and independently revalidated

Full details, first-difference RGB values, per-arm rates, artifact IDs, ZIP
SHA256 digests, limitations and source references are in
`STAGE7_RGB_SCHEDULER_FINDINGS.md`. Method: `STAGE7_CAPTURE_SCHEDULE_ISOLATION.md`.

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
There is still no validated renderer repair or new official ONNX gate.

## What remains unresolved

**Original official MD-V3 strict gate remains the prior 0/4 PASS (FAIL).**
There is no new causal renderer repair or new official ONNX run. Static
experimental 4/4 equality must not replace the original moving-camera gate.
No original camera default, PSSM/Chase callback, shader, model input bytes,
recurrent states or actions were changed. Geometry, rendering determinism,
real-sensor optical equivalence and driving performance remain separate.

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
gh pr list --state all --head docs/stage7-verified-capture-findings
gh run list --branch main --limit 12
```

First finish/check the documentation PR and its current-HEAD checks/review.
Native jobs automatically triggered by merges are separate cohorts; query
status before starting any manual repeat. Preserve cancelled/failed results.

Then continue cause isolation, retaining original PSSM/Chase and Road-first
controls. Prioritize a reproducible CI vs local/runtime explanation: record
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
python -m scripts.aggregate_native_mdv3_rgb_pixel_matrix \
  --root output/verified-original-pixels --out output/pixels-recomputed.json
```

Only a causally supported, rendering-semantics-validated repair can advance
Task 4. Then execute the separate original 2 seeds × 2 S-curves × 12 steps ×
2 independent processes strict MD-V3 gate (all source/warped RGB, actual I420,
action, all recurrent-state digests, pose and virtual time must match). Only
an exact 4/4 permits longer runs, more repeats, positions and ramp expansion.
Do not claim Stage 7 completion while this gate is open.
