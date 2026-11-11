# Opaque bin ordering isolation (experimental, simulation only)

This 32-process diagnostic asks whether opaque drawing policy changes static
repeatability independently of the combined sampler/shadow-camera treatment.
It introduces no default renderer change. The original official MD-V3 strict
gate remains **0/4 PASS (FAIL)**. Static equality cannot establish renderer
equivalence, unique causality, accurate shadows or a repaired model gate.

The motivating four-process ABBA pilot used only feedback `both` in one scene
at seed 20261109. Its state-sorted repeats matched source Road/Wide 9/10 and
5/10, warped 9/10 and 10/10, and I420 9/10, first difference step 9. Unsorted
matched all five image fields 10/10. The complete receipts are retained under
ignored `output/opaque-bin-pilot-v3/`; four UUIDs/PIDs, statuses zero, walls
82.702/78.100/71.165/68.015 seconds. Earlier v1/v2 wrapper failures remain
failed attempts. One case and cold/cache execution history confound that pilot.
Same-index membership in either control repeat was Road/model Road/I420 16/20
and Wide 20/20; this is an observation, not an alternate equality gate or proof
of semantic equivalence.

Actual original-renderer GL traces provide a separate boundary observation:
primary unordered CPU geometry, explicit uniforms and active CPU texture inputs
matched within the measured scope while 53 framebuffer-pass draw orders differed.
GPU-generated contents and complete GL state were not reconstructed; tracing
changes timing/capabilities and the original renderer retains known GL hazards.
Order changes also occurred on matching images. Pinned Panda source sorts opaque
render states/data/transforms using pointer comparisons, which motivates a
controlled policy experiment without proving that sorting uniquely causes drift.

| Condition | Existing feedback mode | Opaque bin type |
| --- | --- | --- |
| original_state_sorted | feedback_baseline | original state_sorted, 2 |
| original_unsorted | feedback_baseline | experimental unsorted, 1 |
| both_state_sorted | feedback_both | original state_sorted, 2 |
| both_unsorted | feedback_both | experimental unsorted, 1 |

Before provider creation, the standalone wrapper lazily obtains the global
CullBinManager and requires an existing opaque bin of type 2. State-sorted
controls make no bin mutation. Unsorted changes only that bin's type to 1,
preserving index, name, sort and active state. CPU receipts record the original,
configured, after-capture and restored states. Requested policy and preserved
metadata must survive initialization/capture; the original type is restored on
exit and errors. Panda may apply the type transition at the next frame; no
extra frame, task step, warmup or synchronization is added.

These setup reads are interventions with unmeasured overhead. They are not
GPU queries, current-binding observations or actual primary per-draw ordering
traces. The new module calls the existing public feedback native-trial function
and strict OFF validator. It does not monkeypatch existing modules. Existing
provider, camera, capture, feedback, sampler, shader, workflow and model code
remain unchanged.

Each condition runs two independent observer-OFF native processes. There are no
ON callbacks or GL binding probes. Every child retains original Road-first
sequential capture, original PSSM.update and Chase, two ticks per pair, ten full
primary frames, warmup two and the final +2 m positive control. Source is
964×604, warped RGB 512×256 and actual uint8 I420 [2,6,128,256]. No correction,
replay, inference, weights, scores, real vehicles, clock, task, lens or pose
changes belong to this experiment.

The four scene/seed cases use cyclic Latin-square condition orders; repeat 0
then repeat 1 remains fixed and explicitly recorded.

| Seed / scene | Condition order |
| --- | --- |
| 20261109 / left-right | original_state_sorted, original_unsorted, both_state_sorted, both_unsorted |
| 20261109 / right-left | original_unsorted, both_state_sorted, both_unsorted, original_state_sorted |
| 20261110 / left-right | both_state_sorted, both_unsorted, original_state_sorted, original_unsorted |
| 20261110 / right-left | both_unsorted, original_state_sorted, original_unsorted, both_state_sorted |

Every case retains eight raw JSON receipts, native logs and an execution ledger
with condition/repeat order, fresh request nonce, UUID/PID, start/end timestamps
and raw/accepted exit status. Validation requires eight distinct same-runner
PIDs per case and 32 UUIDs across the cohort, matching WORLD poses and original
bin metadata, full raw clock timestamps/deltas, unchanged task registries,
readback controls, +2 m positives and complete source/warp/I420 SHA timelines.
Condition-repeat equality is exact, with first and all differing steps retained;
sorting cross-condition comparisons are reported separately and prove no
renderer equivalence. No membership test replaces exact matching.

Native results can contain tuple poses. The child writes the complete raw JSON
before strict validation, reloads the wire JSON, then calls the existing OFF
validator. An invalid capture keeps its full raw receipt and returns failure.
A post-capture policy error also retains captured fields and the original
capture status separately. The launcher accepts exit 0 or Xvfb cleanup exit 5
only with fresh, complete validated JSON matching its request nonce. Existing
JSON/logs, stale nonce, missing or invalid receipts fail. Other native statuses
remain failures. Partial/error ledgers and logs survive; failed or cancelled
cohorts never count as complete matrices.

Run only when native experiments are authorized:

```bash
python -m scripts.native_opaque_order_matrix --mode run-case \
  --root output/stage7-opaque-order --seed 20261109 \
  --scene s_curve_left_right
python -m scripts.native_opaque_order_matrix --mode aggregate \
  --root output/stage7-opaque-order \
  --out output/stage7-opaque-order/aggregate_summary.json
```

Aggregation imports neither Panda nor a GL query interface. It regenerates every
case from raw receipts and rejects modified/stale case summaries. If the standard
aggregate summary already exists, it must also match exact regeneration.

The workflow pins MetaDrive 0.4.3, Panda3D 1.10.13 and official assets size
134074203 / SHA256
`4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9`.
Four native jobs and an independent aggregate retain five artifacts, including
hidden evidence files, only under the experiment's output directory. Acceptance
requires exact source HEAD/checks/review, five artifact API size/ZIP SHA checks,
safe archive paths and exact raw reaggregation. Preserve failures/cancellations.

This guide defines the new matrix and reports the preceding local pilot; it
does not claim a completed 32-process CI result. A discriminating result still
needs causal and rendering-semantics validation before the separate original
2-seed × 2-S-curve × 12-step × 2-process MD-V3 gate covering source, warp, I420,
actions, recurrent states, pose and time. Expansion waits for its exact 4/4.

## Local source validation before CI

The complete local suite passed **298 tests without skips**, including 17 new
opaque-order contract tests. Two real production-launcher `both_unsorted`
processes passed strict native/bin/nonce validation with a fresh dedicated
shared Mesa cache (cold, then populated). Every source Road/Wide, warped
Road/Wide and I420 field matched **10/10**. Both raw receipts recorded opaque
index2/name opaque/sort20/active true, configured type2→1, type1 after capture,
and restored type2. Existing task/clock/readback and +2m controls passed.

Evidence: `output/opaque-order-source-smoke/{source_receipt,comparison}.json`
and `both_unsorted-{0,1}.json`/logs. The new module SHA remained unchanged
through both captures. This validates the supported before-provider path,
separately from the earlier after-provider-hook ABBA pilot. It is one static
seed/scene pair, not the four-case CI or official MD-V3 gate, a unique cause,
or a renderer-equivalence result. No weight or ONNX inference was used.
