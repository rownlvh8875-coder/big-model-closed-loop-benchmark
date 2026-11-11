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

This guide defines the matrix and records its completed source cohort below.
A discriminating static result still needs causal and rendering-semantics
validation before the separate original moving MD-V3 gate. Expansion waits
for that gate's exact 4/4.

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

## Verified source and balanced CI result (2026-11-11)

PR [#23](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/23)
merged as `d1e209d61af5cfa7c482fe09712f85f7496958e6` from exact source HEAD
`983732f8e4713686a669a16058e6a93da871a620` after **nine passing checks**,
current-SHA Codex review without findings/no open threads and a clear independent
eight-file source/scientific review. The local suite passed **298 tests without
skips**; the two production-launcher Both-unsorted smoke processes above matched
all image fields 10/10. No default renderer change or model gate was promoted.

[Native run 42968294569](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42968294569)
completed **5/5 jobs**. All five artifact API byte sizes, SHA256 digests and
safe ZIP paths were verified. All four case summaries and the final aggregate
were regenerated exactly from **32 unique native UUIDs and fresh request
nonces, eight distinct same-runner PIDs per case**. Each raw receipt passed the
original OFF clock/task/pose/readback/+2 m controls and explicit CPU bin checks.
Raw JSON/logs, case execution ledgers and summaries remain in the archives.
Independent evidence is retained under
`output/stage7-remote-evidence/run-42968294569/`: `recomputed.json`, `totals.json`,
`verified_archives.json` and `revalidation.log`.

### Exact within-condition repeatability

| Condition | Source Road /40 | Source Wide /40 | Warped Road /40 | Warped Wide /40 | I420 /40 | I420 post-warmup /32 | Complete static cases /4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `original_state_sorted` | 38 | 38 | 38 | 40 | 38 | 30 | 3 |
| `original_unsorted` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |
| `both_state_sorted` | 36 | 36 | 36 | 40 | 36 | 29 | 3 |
| `both_unsorted` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |

Changing the requested opaque-bin policy changed observed repeatability in
this balanced four-case matrix for both feedback modes. Both unsorted conditions
match every source/warp/I420 field in all four cases, while each state-sorted
condition fails one case. This is bounded evidence about the policy intervention,
not proof of a unique pointer-order/GPU mechanism, universal determinism or
rendering equivalence. The original moving-model gate remains separately open.

| Seed | Scene | Condition | Source Road/Wide /10 | Warped Road/Wide /10 | I420 /10 | First source Road/Wide | First I420 | I420 different steps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20261109 | left_right | `original_state_sorted` | 8/8 | 8/10 | 8 | 5/4 | 5 | 5, 7 |
| 20261109 | left_right | `original_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | left_right | `both_state_sorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | left_right | `both_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | right_left | `original_state_sorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | right_left | `original_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | right_left | `both_state_sorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | right_left | `both_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | left_right | `original_state_sorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | left_right | `original_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | left_right | `both_state_sorted` | 6/6 | 6/10 | 6 | 2/4 | 2 | 2, 7, 8, 9 |
| 20261110 | left_right | `both_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | right_left | `original_state_sorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | right_left | `original_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | right_left | `both_state_sorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | right_left | `both_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |

Original state-sorted fails **20261109 / left-right**: Road source/warp and
I420 first differ at **5**, I420 at **5 and 7**; Wide source first differs at
**4**. Both state-sorted fails **20261110 / left-right**: Road/I420 first differ
at **2**, I420 at **2, 7, 8, 9**; Wide source first differs at **4**. Every other
case/condition matches every field 10/10. The cyclic orders listed earlier are
the validated execution orders. Each condition runs first once; repeat 0 → 1
remains fixed, and this finite cohort does not isolate every initialization,
process/cache or runtime contribution.

### Cross-policy images and CPU setup scope

Cross-policy comparisons pair the same repeat index within each seed/scene,
for eight pairs / 80 frames per feedback mode. They are separate image-semantic
observations, not additional repeatability gates or membership tests.

| Feedback mode, state-sorted versus unsorted | Source Road/Wide /80 | Warped Road/Wide /80 | I420 /80 |
| --- | --- | --- | --- |
| original | 62/66 | 62/76 | 58 |
| both | 62/58 | 62/66 | 48 |

The policies are not bit-equivalent across all frames in either feedback mode.
A static improvement alone does not establish intended shadows, equivalent
model inputs or a safe default substitution.

All 32 CPU receipts record original opaque metadata index **2**, name `opaque`,
sort **20**, active **true**. State-sorted keeps type **2** throughout; unsorted
records type **1** after setup and capture, and type **2** after restoration.
Other metadata is preserved. Setup precedes provider creation; this validates
the supported path independently from the earlier after-provider local pilot.
These CPU receipts verify the requested bin policy and restoration, not actual
per-draw order or GPU sampler state. This OFF matrix performs **no GPU binding
queries, framebuffer-sample queries, texture extraction or per-draw trace**.
Prior experiments' GL renderer strings, sample counts and sampler observations
must not be reported as observations from this cohort.

### Runtime evidence and complete archive ledger

Completed job setup logs record **CPython 3.11.18, MetaDrive 0.4.3, Panda3D
1.10.13, NumPy 2.4.6, OpenCV 5.0.0.93, panda3d-gltf 0.13 and simplepbr 0.13.1**.
These are actual setup/pip log observations retained in
`runtime-log-evidence.json` under this run's evidence directory. They do not
identify the active GL renderer/driver or actual framebuffer samples, which
were not queried in this OFF cohort.

| Run | Artifact ID | SHA256 | Bytes |
| --- | --- | --- | --- |
| 42968294569 | 13833300695 | `169fc140c47e0b8b412f8796831fb4663bd585d6d731fd05a14fceaa4f1c07d8` | 46133 |
| 42968294569 | 13833230672 | `6f8789be556cdb315199cf6b1f21282258f07269957b3495a9ab8401620731fc` | 48300 |
| 42968294569 | 13833090943 | `aeb4ef7949c2003eff101bbee1b8ccd06be9030fae4a075fc0b141ce592f286b` | 46312 |
| 42968294569 | 13832875977 | `1e05dd51ab7fac78e5cf6e04f3fe2c2b64a3b7275cfd0315d657f511ff8ae3fe` | 46476 |
| 42968294569 | 13832417402 | `a3d7cc1ae79102d075c59fe4fbadeb65d00ee8205f15a580b091bf250d4901ab` | 7483 |

## Verified automatic merged-main repetition

The PR #23 merge started separate main-source `d1e209d` opaque-order
[run 42969968780](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42969968780),
now complete **5/5 jobs**. All five artifact API SHA256/byte sizes and safe ZIP
paths were checked, and every case summary and final aggregate reproduced
exactly from **32 unique UUIDs/nonces and eight distinct same-runner PIDs per
case**. The relevant implementation is unchanged from tested source `983732f`;
native module SHA256 is
`314f83f63218b0cc2b19c69b7145eba4fa0b184c27cbb17c258803e1613e5214`.
Unit main run **42969968794** passed. This automatic cohort is independent of
source run 42968294569 and is not a manual repeat.

| Condition | Source Road /40 | Source Wide /40 | Warped Road /40 | Warped Wide /40 | I420 /40 | I420 post-warmup /32 | Complete static cases /4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `original_state_sorted` | 37 | 37 | 37 | 40 | 37 | 30 | 3 |
| `original_unsorted` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |
| `both_state_sorted` | 36 | 36 | 36 | 40 | 36 | 29 | 3 |
| `both_unsorted` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |

Both unsorted conditions again match every image field in all four cases;
each state-sorted condition matches only 3/4. Original state-sorted's exception
is again 20261109 / left-right, now I420 **7/10**, first **2**, differences
**2, 9, 10**. Both state-sorted fails 20261110 / left-right at **2, 7, 8, 9**,
matching I420 **6/10**. The two cohorts support the bounded policy finding,
without proving universal determinism, a unique mechanism or image equivalence.
The same cyclic orders and fixed repeat 0 → 1 apply.

| Seed | Scene | Condition | Source Road/Wide /10 | Warped Road/Wide /10 | I420 /10 | First source Road/Wide | First I420 | I420 different steps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20261109 | left_right | `original_state_sorted` | 7/7 | 7/10 | 7 | 2/4 | 2 | 2, 9, 10 |
| 20261109 | left_right | `original_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | left_right | `both_state_sorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | left_right | `both_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | right_left | `original_state_sorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | right_left | `original_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | right_left | `both_state_sorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | right_left | `both_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | left_right | `original_state_sorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | left_right | `original_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | left_right | `both_state_sorted` | 6/6 | 6/10 | 6 | 2/4 | 2 | 2, 7, 8, 9 |
| 20261110 | left_right | `both_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | right_left | `original_state_sorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | right_left | `original_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | right_left | `both_state_sorted` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | right_left | `both_unsorted` | 10/10 | 10/10 | 10 | none/none | none | none |

Cross-policy comparisons still show image differences:

| Feedback mode, state-sorted versus unsorted | Source Road/Wide /80 | Warped Road/Wide /80 | I420 /80 |
| --- | --- | --- | --- |
| original | 59/63 | 59/76 | 55 |
| both | 62/58 | 62/66 | 48 |

All 32 native OFF/bin/nonce controls, CPU requested-policy preservation and
restoration pass again. This repetition adds no actual GPU binding/sample
queries, texture extraction, GL renderer observation or per-draw trace.
Package/GL facts from a different cohort are not assigned to these receipts.
Raw JSON/logs/ledgers and independent `recomputed.json`, `totals.json`,
`verified_archives.json` and `revalidation.log` remain under
`output/stage7-remote-evidence/run-42969968780/`.

| Run | Artifact ID | SHA256 | Bytes |
| --- | --- | --- | --- |
| 42969968780 | 13833895008 | `fc7f1c5f2594b3039fa11240613f1d4ea20327cba80687decd57f7213feafc5d` | 46659 |
| 42969968780 | 13833661675 | `99cef77e07a19ac470c85fc9a84263c48c93189705d495814c31ed2d88ff3317` | 7513 |
| 42969968780 | 13833542276 | `ebdd13ef33c7787e1d573c254dd437bd5bfb0721a61dfa455f86098ce0545bad` | 48342 |
| 42969968780 | 13833198284 | `237a22219d1bc6cb085f2306eb599f3569048623b66f32b4a19c20f771090f97` | 46009 |
| 42969968780 | 13832873427 | `1c0a57f8b547c71cbd4559cd8e69e3d72ea837b7a15fbcb26b770bc87dd9f995` | 46473 |

## Local terminal-depth validation and remaining model gates

The balanced ordering experiment and its artifact gate are complete. Causal
and rendering-semantic validation remain open; no default sort policy is
adopted. The first external eight-process terminal-depth protocol is **failed
and partial**, stopped at its fifth entry: `both_unsorted`, repeat 1, returned
status **2 before capture** because the reused `feedback_native_trial` forbids
`probe=True` with repeat 1. **Four valid native captures with depth reads** are
retained; they do not form a completed eight-process cohort or establish a
semantic comparison. The fifth raw `ERROR` receipt records **zero extractions**;
its log and failed ledger entry are preserved at
`output/terminal-atlas-semantics/`. Captured depth-read receipts truthfully
record one extraction and remain outside the supported OFF schema.
The old helper stays immutable at SHA256
`131857958a2ab1a551dbec7da9481c9d274d1da822bfb7c416d9a2a38d805801`.
Preserve the four valid partial observations and the failure; do not restart
that helper or promote a depth-hash/equivalence outcome from this partial set.

### Completed V2 custom terminal-depth protocol

V2 is complete: **8/8 valid native processes, all statuses zero**, with eight
unique PIDs, UUIDs and request nonces. Root's independent revalidation checked
every raw JSON/binary, depth range/statistic, original +2 m/task/clock controls,
GL errors/restoration, source/helper identity and final cache file hashes;
the complete comparison reproduced exactly. Retained evidence is under
`output/terminal-atlas-semantics-v2/`: all eight JSON/log/float32 files,
`plan.json`, `execution_ledger.json`, `comparison.json` and
`independent_revalidation.json`.

The frozen external helper SHA256 is
`08f9a1da50b4dec790720bfcda0789dd074b2f09bed38f4dd58b845e304a7033`.
Its exact-SHA review and nine CPU tests preceded this native run. It uses
public `native_pixel_clock` directly with custom condition/repeat metadata;
this is **not a standard feedback or 32-process OFF matrix cell**. Each process
truthfully records **one GPU texture extraction**. The terminal ON observer
runs only in the final +2 m control, after ten primary image pairs; callbacks
are removed before one level-0 `glGetTexImage` depth read. Read-before,
read-after and post-provider-return frame counts all remain **32**, with no
later capture render, zero recorded GL errors and all saved readback GL state
restored. Cache roots are private per condition, cold then populated; final
manifests were rehashed after completion.

Each terminal atlas has **2048×1024 float32 texels**, **8,388,608 bytes** and
**2,097,152 finite values in [0,1]**, including **5,347 nonclear texels**;
minimum is **0.3487148582935333**, maximum **1.0**. All eight raw binaries have
SHA256
`e2fad785dc9037146323996699cb8c2a23e517bb99acce5557ee5957fe234881`.
Every within-condition, linear-to-Both guard and cross-sorting terminal-depth
comparison is byte-exact, with **zero changed texels and maximum absolute
Delta 0**. This is one terminal snapshot per process, not a depth trace of
every primary frame.

The following primary image SHA comparisons are separate from that terminal
atlas result. Each row compares two independent terminal-ON processes in the
same condition; cross-condition rows pair the same repeat index:

| Terminal-ON condition | Primary source Road/Wide /10 | Primary warped Road/Wide /10 | Primary I420 /10 | I420 post-warmup /8 | First I420 | I420 different steps |
| --- | --- | --- | --- | --- | --- | --- |
| `linear_state_sorted` | 8/8 | 8/10 | 8 | 7 | 2 | 2, 7 |
| `linear_unsorted` | 10/10 | 10/10 | 10 | 8 | none | none |
| `both_state_sorted` | 7/8 | 7/10 | 7 | 5 | 4 | 4, 6, 8 |
| `both_unsorted` | 10/10 | 10/10 | 10 | 8 | none | none |

| Primary image comparison | Repeat index | Source Road/Wide /10 | Warped Road/Wide /10 | I420 /10 |
| --- | --- | --- | --- | --- |
| linear → Both, state_sorted | 0 | 7/7 | 7/10 | 7 |
| linear → Both, state_sorted | 1 | 8/9 | 8/10 | 8 |
| linear → Both, unsorted | 0 | 10/10 | 10/10 | 10 |
| linear → Both, unsorted | 1 | 10/10 | 10/10 | 10 |
| state-sorted → unsorted, linear | 0 | 7/10 | 7/10 | 7 |
| state-sorted → unsorted, linear | 1 | 9/8 | 9/10 | 9 |
| state-sorted → unsorted, both | 0 | 8/7 | 8/10 | 8 |
| state-sorted → unsorted, both | 1 | 9/9 | 9/10 | 9 |

Guard on/off comparisons with unsorted rendering match every primary source,
warp and I420 field in both repeat-indexed pairs. Sorted primary images still
vary despite identical terminal atlas bytes. This supports **terminal shadow-
depth preservation and no observed guard-related primary byte change in these
unsorted pairs**, confined to seed 20261109 / left-right. It establishes neither
global physical shadow accuracy, photometric equivalence nor unique causality.
Terminal observer/readback effects, fixed order, cache history, independent
processes and one static scene limit generalization.

Only direct `glGetTexImage` wall time spans **0.920867–1.796358 ms**; this
excludes other queries, setup/restoration, file IO and the whole terminal
intervention, and is not an unbiased total-overhead estimate. This local
probe actually records Mesa **25.0.7-2+deb13u1**, llvmpipe **LLVM 19.1.7
(256 bits)** and **GL 4.5 compatibility profile**. The observed threading model
is **`/`**, with empty cull/draw names; it does not prove a native worker count.
These are probe observations, not new GL observations from the OFF CI matrices.

### Bounded acceptance and prospective candidate

The completed depth protocol supports this bounded semantic acceptance; it
does not establish a universal renderer-equivalence repair or change defaults.
The [prospective MD-V3 renderer-candidate plan](superpowers/plans/2026-11-11-mdv3-renderer-candidate.md)
is the next explicit experimental diagnostic after independent review of these
findings. It must use the original **`NativeWorldCamera`** and public
**`run_target_lane_episode`** path. The static feedback/raw-clock trial hides
visual ego and cannot substitute for the original model campaign's visibility.
Any candidate result must retain its candidate label and be reported separately
from the historical original gate.

No official weights, ONNX inference or candidate model run has executed in
this evidence. The original official MD-V3 gate remains the prior **0/4 PASS
(FAIL)**, and Stage 7 remains incomplete. PR #24's completed-depth append still
requires a new documentation commit and refreshed exact-HEAD CI/Codex review
before merge; no updated-HEAD completion is assumed here.

Both opaque-order CI cohorts, source **42968294569** and automatic main
**42969968780**, are complete and independently revalidated. Do not manually
repeat either merely to rediscover its recorded result. V1 remains failed/
partial and preserved; V2 is complete and independently revalidated. Broader
semantic claims, the prospective candidate model test, the original model gate
and default-policy adoption remain open.
