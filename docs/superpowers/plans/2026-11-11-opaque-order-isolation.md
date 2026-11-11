# Opaque bin order isolation plan

> Required workflow: executing-plans and test-driven-development. Delegate the
> isolated new implementation and completed-result documentation independently
> with dispatching-parallel-agents; request fresh code/scientific review.

## Evidence and question

PR #21 merged diagnostic source as `96069779c85a691a81d119f27cafe39160c70cfa`.
PR #22 merged completed evidence as `329b400f12999526157c5db24b27f70001ed57b4`.
Both 48-process feedback cohorts failed strict 4/4, including `both`.
Two actual original-renderer GL traces reproduced different source RGB while
their scoped primary unordered CPU draw inputs matched and 53 pass orders
differed. GPU-produced textures/full state were not reconstructed; source has
known GL hazards. Pinned Panda sorting compares attribute/data/transform pointers.

Local four-process ABBA `output/opaque-bin-pilot-v3/` tested **only** feedback
`both` with opaque state-sorted type 2 versus unsorted type 1. State-sorted
source Road/Wide 9/10 and 5/10, warped 9/10 and 10/10, I420 9/10 (first 9).
Unsorted matched all source/warped/I420 10/10. Four UUIDs/PIDs and validated
fresh receipts, original PSSM/Chase/two ticks/+2m control retained. This is a
single-case ordering/cache-confounded pilot, not a repair or official model gate.
Earlier v1/v2 wrapper failures are retained and do not count as matrices.

Question: does the ordering policy change repeatability independently of the
combined sampler/shadow guard treatment across both seeds and both S-curves?

## Scope and architecture

Create a **new** standalone module, tests, workflow and guide. Keep all existing
provider/camera/raw capture/feedback/sampler/model modules byte-identical.
Reuse the public feedback native-trial function and its OFF receipt validator.
Do not monkeypatch capture/configuration functions in the supported module.

Four conditions: original_state_sorted, original_unsorted, both_state_sorted,
both_unsorted. Original maps to feedback_baseline; both maps to feedback_both.
Each condition runs two independent observer-OFF processes; four scene/seed
cases use a cyclic Latin square so each condition runs first once: **32 native
processes**, eight distinct same-runner PIDs per case. Fixed repeat0/repeat1
ordering remains explicit. This has no ON/GPU-query arm.

Before creating the provider, lazily obtain CullBinManager and require the
existing opaque bin to be state-sorted type 2. Baseline makes no bin mutation;
unsorted sets only that bin's type to 1. Preserve bin index/name/sort/active
state and restore the original type on exit/errors. Assert the requested type
survives native initialization/capture. The API may apply a type change on the
next frame; add no render/task tick/warmup. Record setup CPU reads explicitly;
do not call the setup overhead-free or an actual primary per-draw trace.

Native source uses Road-first/PSSM/Chase, two ticks/pair, ten primary frames,
warmup two, +2m positive controls, 964x604 source, 512x256 warp, actual uint8
I420(2,6,128,256). No shader edits, image correction/replay, weights, inference,
real vehicles, scoring, clock/lens/pose/task changes or environment publication.

## Implementation contracts

- [x] TDD meaningful failures first: four condition identities, bin-type-only
  setup/restoration, unknown bin rejection before mutation, fresh launch nonce,
  full raw clock/task/pose/readback/image controls, reused PID/UUID, wrong bin
  receipts, incomplete/stale summaries and native exit contracts.
- [x] Preserve the operations bug regression: native results may contain tuple
  poses. Write full raw JSON **before** strict validation; reload JSON for the
  existing wire-schema validator. Invalid captures retain raw JSON/logs. Never
  relax controls or relabel nonzero statuses as successful captures.
- [x] Parent accepts exit 0 or Xvfb cleanup 5 only with fresh complete validated
  JSON matching the request UUID; retain all other status/error ledger entries.
  Existing output/logs are rejected. Child exceptions retain error receipts.
- [x] Validate explicit condition, mode, original/requested/final/restored bin
  types, native configuration and all original raw controls. Aggregation is lazy
  and does not initialize Panda/GL. Verify every case/final summary exactly.
- [x] Report exact per-condition repeat source/warped/I420 SHA matching and first/
  all mismatching steps. Keep sorting cross-condition comparisons separate.
  Optional same-index membership in either control repeat is an observation
  only, never an alternate gate, tolerance, correction or equivalence proof.
- [x] Source claim flags original MD-V3 repeatability, unique cause and renderer
  equivalence stay false, even for static 4/4. Keep original gate prior 0/4 FAIL.
- [x] CI four native jobs plus independent aggregate; pin MetaDrive0.4.3,
  Panda1.10.13 and official assets bytes134074203 / SHA256
  `4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9`.
  Retain hidden files only in the evidence scope, including failures/ledgers/logs.
- [x] Full local tests, real native smoke, fresh source/scientific reviews,
  exact-HEAD CI/Codex review/no unresolved threads, five archive API SHA/size/
  safe-path checks and exact raw reaggregation before gated diagnostic merge.


## Files and ownership

Implementation: `scripts/native_opaque_order_matrix.py`,
`tests/test_native_opaque_order_matrix.py`,
`.github/workflows/stage7-opaque-order.yml`, `docs/STAGE7_OPAQUE_ORDER.md`.
Root owns this plan, continuation and previous-evidence checkpoint updates.

Do not adopt a new default ordering or call a repair solely from static equality.
If the result discriminates, assess causal/rendering semantics before the
separate official 2-seed x2-S-curve x12-step x2-process original MD-V3 strict
source/warp/I420/action/recurrent-state/pose/time 4/4 gate. Expansion waits.


## Completed source evidence (2026-11-11)

PR #23 merged as `d1e209d61af5cfa7c482fe09712f85f7496958e6` from exact source
`983732f8e4713686a669a16058e6a93da871a620` after nine passing checks,
current-SHA Codex review without findings/no open threads, clear independent
eight-file review and 298 local tests without skips. Two production
Both-unsorted smoke processes matched source/warp/I420 10/10. CI run
42968294569 completed 5/5 jobs; all five API artifact SHA/size/safe paths and
exact four-case/final regeneration passed, with 32 distinct native UUIDs/
nonces and eight same-runner PIDs per case. CPU bin type 2/1 and preserved
metadata/restoration validated in all 32 receipts. No actual GL query or
per-draw tracing is part of this OFF matrix.

Original state-sorted source Road/Wide matched 38/38 of 40, warp 38/40,
I420 38/40 (30/32 post-warmup), with 3/4 complete static cases. Both
state-sorted source matched 36/36, warp 36/40, I420 36/40 (29/32 post-warmup),
with 3/4 complete cases. Each unsorted condition matched every image field
40/40 (32/32 post-warmup), with 4/4 complete static cases. Original
state-sorted fails 20261109 left-right at I420 steps 5 and 7; Both
state-sorted fails 20261110 left-right at 2, 7, 8 and 9. Cross-sorting I420
equality is 58/80 original and 48/80 Both, so no bit/rendering equivalence
is proved. Full per-case rates/firsts, cross metrics, package-log
scope and complete five-archive ledger are in
[the ordering guide](../../STAGE7_OPAQUE_ORDER.md).

This is bounded evidence that policy changes observed repeatability in the
balanced four-case static matrix; unique mechanism, intended shadows and
renderer equivalence remain unproven. No default ordering or official MD-V3
gate is promoted; prior 0/4 PASS (FAIL) remains. Automatic main run 42969968780
is now complete and independently revalidated below; unit 42969968794 passed.
Do not manually repeat completed cohorts merely to rediscover their results.

## Completed automatic main repetition

Main-source `d1e209d` run 42969968780 completed 5/5 jobs; all five artifact API
SHA/size/safe-path checks and exact case/final raw regeneration passed, with
32 UUIDs/nonces and eight PIDs per case. The native module SHA is unchanged
from tested source 983732f. Original state-sorted source Road/Wide is 37/37
of 40, warp 37/40, I420 37/40 (30/32 post-warmup), complete 3/4. Both
state-sorted is source 36/36, warp 36/40, I420 36/40 (29/32), complete 3/4.
Each unsorted condition again matches all image fields 40/40 (32/32),
complete 4/4. Original state-sorted fails 20261109 left-right at I420 steps
2, 9, 10; Both state-sorted fails 20261110 left-right at 2, 7, 8, 9.
Cross-sorting I420 is 55/80 original and 48/80 Both. Full rates, firsts and
all five archive SHA/byte rows are in the ordering guide. No new GPU-state
observation, renderer equivalence, unique cause or model PASS is established.

## Open semantic and model gates

- [ ] Complete causal/rendering-semantic validation. The first external
  eight-process depth protocol stopped as failed/partial at entry 5,
  Both-unsorted repeat 1, status 2 before capture because the reused feedback
  trial rejects probe=True/repeat 1. Four valid native depth-read captures and
  the fifth ERROR/zero-extraction receipt/log/ledger remain under
  `output/terminal-atlas-semantics/`; these are not a completed cohort or
  semantic-equivalence result. Old helper SHA
  `131857958a2ab1a551dbec7da9481c9d274d1da822bfb7c416d9a2a38d805801`
  remains immutable. V2 is running at `output/terminal-atlas-semantics-v2/`,
  using public native_pixel_clock with the same capture arguments and custom
  repeat metadata. Root exact-helper SHA review and nine CPU tests, including
  all eight configurations stopped before provider/GL, passed. Reviewed SHA:
  `08f9a1da50b4dec790720bfcda0789dd074b2f09bed38f4dd58b845e304a7033`. Retain
  partial/failure evidence, avoid duplicate launches/automatic retries and
  relax no comparison gate. This operations-only one-extraction protocol is
  outside the supported OFF schema; product source/32-process matrices remain
  unaffected.
- [ ] Only after a validated repair, run the separate original moving MD-V3
  strict 2-seed × 2-scene × 12-step × 2-process gate over source/warp/I420,
  actions, recurrent states, pose and time. Require exact 4/4 before expansion.
