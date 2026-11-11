# Shadow atlas feedback isolation (experimental, simulation only)

This experiment separates a shadow-pass atlas read/write binding hazard from
the confirmed nonshadow sampler/depth-compare type mismatch. It changes no
default renderer path. The original official MD-V3 strict gate remains the
prior **0/4 PASS (FAIL)**; cache isolation failed strict matching at 34/40
I420 frames. No official model retest is authorized until a repair is validated.

The local unmodified terminal probe at
`output/stage7-remote-evidence/shadow-feedback-terminal-probe.json` recorded
four shadow observations: depth attachment type GL_TEXTURE, atlas name 1,
mip level 0; active sampler2D PSSMShadowAtlas also bound name 1; use_pssm=1;
zero GL errors. Both original shadow camera initial states were empty. This
establishes a potential feedback binding, not proof that any original primitive
executed a fetch or that this hazard uniquely causes the observed image drift.
The manual PCF shader samples neighboring texels. This is not a case where
numeric identity alone, or a same-pixel ordering argument, proves safe accesses.
OpenGL 4.6 section 9.3.1, pages 325–326 describes framebuffer feedback loops.

Four opt-in modes are accepted only through `configure_sampler` and the new
matrix wrapper. The existing `original`/`raw_linear` APIs and their OFF/ON
receipt schema remain unchanged. The raw pixel-clock API, its CLI, provider,
camera and capture code are unchanged.

| Condition | Diagnostic mode | Atlas filtering | Shadow camera inputs |
| --- | --- | --- | --- |
| baseline | feedback_baseline | original FTShadow | original inherited inputs |
| linear | feedback_linear | min/mag FTLinear | original inherited inputs |
| shadow_guard | feedback_shadow_guard | original FTShadow | use_pssm=False, placeholder atlas |
| both | feedback_both | min/mag FTLinear | use_pssm=False, placeholder atlas |

The guard first requires both original shadow camera initial RenderStates to
be empty. It adds only `use_pssm` and `PSSMShadowAtlas` shader inputs, each at
priority 1,000,000, to those initial states. The placeholder is a white 1×1
RGBA8 texture with linear min/mag filtering. The guard neither assigns nor
disables a shader; inherited geometry, alpha behavior and other state still
apply. Unknown camera states fail before mutation; setup exceptions restore
both camera states and the atlas filters. No lens, mask, transform, geometry,
task, PSSM update or main chase camera change is part of the treatment.

Every native child keeps the original Road-first sequential schedule, two task
ticks per pair, original PSSM.update and Chase, ten complete primary frames,
warmup two, source 964×604, warped 512×256, actual uint8 I420 [2,6,128,256],
and the final +2 m camera movement positive control. Image analysis remains
after rendering. There is no image correction, replay, model inference,
weight download, score or real-vehicle testing.

Each condition runs two independent OFF processes followed by one independent
ON process. OFF installs no callbacks and loads no libGL query interface. ON
instruments only the final positive control after all primary captures. A
temporary zero-geometry node inherits the scene state and is visible only to
RGB|Shadow cameras. Display-region wrappers identify road, wide, shadow0 and
shadow1 on the draw thread; every wrapper and temporary node is removed on
exit, including exceptions. There are no texture-pixel extractions or later
renders. Expected observations per ON process: four shadow plus four RGB.

The observer records the actual program, active uniform sampler type/value,
use_pssm, atlas and placeholder native IDs, texture internal format, effective
sampler/texture comparison and filtering state, draw FBO, actual GL_SAMPLES and
GL_SAMPLE_BUFFERS, depth/color0
attachment object type/name/mip level, driver, GL errors and query duration.
A renderbuffer name is never treated as a texture alias merely because its
number equals a texture ID. Guarded shadow observations must show the RGBA8
placeholder with use_pssm=0, while RGB must retain the real depth atlas and
use_pssm=1. These are controlled inherited-state observations, not per-primitive
traces or proof of each draw's shader execution. They also do not establish
shadow accuracy or unchanged rendering semantics.
The framebuffer sample counts describe the actual framebuffer bound during
each observation, not the camera's requested 16× HDR MSAA setting. Validation
requires nonnegative integer counts, zero samples exactly when no sample buffer
is present, and GL_SAMPLE_BUFFERS equal to zero or one; it does not assume the
driver fulfills the requested sample count.

The four scene/seed cases use this cyclic Latin square. Every condition runs
first once; fixed OFF0/OFF1/ON0 ordering within a condition remains a limitation.
The single ON process supplies terminal state evidence, not a repeated ON arm.

| Seed / scene | Condition order |
| --- | --- |
| 20261109 / left-right | baseline, linear, shadow_guard, both |
| 20261109 / right-left | linear, shadow_guard, both, baseline |
| 20261110 / left-right | shadow_guard, both, baseline, linear |
| 20261110 / right-left | both, baseline, linear, shadow_guard |

Each case retains 12 JSON receipts, 12 native logs and an execution ledger
binding ordered launch requests to UUID/PID, start/end time and raw/accepted
exit status. Validation requires 12 distinct same-runner PIDs per case and 48
distinct UUIDs across the cohort, identical WORLD poses, complete raw clock
timestamps/deltas, task registries, positive controls and full source/warp/I420
SHA timelines. OFF0/OFF1 equality is reported exactly, including first and all
differing steps. OFF0/ON0 comparisons are separately labeled temporal/process
observations: a terminal observer cannot repair earlier primary images.
Cross-condition image changes are also reported without asserting equivalence.

The launcher accepts native exit 0 or Xvfb cleanup exit 5 only after a fresh,
complete, validated receipt matches its new launch-request UUID. Preexisting
output/logs are rejected; missing, invalid and stale receipts fail. All other
native exit statuses are preserved. Failed or cancelled cohorts retain partial
logs/receipts and never count as complete matrices.

Run the case launcher only when native experiments are authorized:

```bash
python -m scripts.native_shadow_feedback_matrix --mode run-case \
  --root output/stage7-shadow-feedback --seed 20261109 \
  --scene s_curve_left_right
python -m scripts.native_shadow_feedback_matrix --mode aggregate \
  --root output/stage7-shadow-feedback \
  --out output/stage7-shadow-feedback/aggregate_summary.json
```

The workflow pins MetaDrive 0.4.3, Panda3D 1.10.13 and official assets size
134074203 / SHA256
`4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9`.
It runs four native jobs and a separate aggregate job. Five artifacts retain
raw JSON/log/ledger evidence and the aggregate, including hidden files, only
under the experiment output scope. The existing 32-process sampler workflow
is still triggered by changes to the shared sampler helper.

Before accepting a CI result, verify exact source HEAD/checks/review, all five
artifact API sizes and ZIP SHA256 digests, safe archive member paths and exact
raw reaggregation equality. Preserve every failed/cancelled attempt. This
guide defines the experiment and records the completed source cohort below.
All source claims for original MD-V3 repeatability, unique cause, model
scoring and real-vehicle testing remain false even when static frames match.


## Local source smoke before CI

The complete local suite passed **281 tests without skips**. Two real source
launcher processes with condition `both`, observer OFF, matched every source
Road/Wide, warped Road/Wide and I420 field **10/10** with the already-populated
local cache. Their raw receipts and comparison are in ignored
`output/shadow-feedback-local/`. A later fresh-shared-cache pair failed, as
recorded below; the matching smoke alone is not a repair.

One additional production-launcher ON process passed the full native/nonce/
configuration/binding validator, with eight terminal observations: four shadow
placeholder bindings with `use_pssm=0`, and four RGB real-atlas/raw-linear
bindings with `use_pssm=1`, all recorded GL errors zero. Actual samples/buffers
were **0/0** for shadow and **4/1** for RGB HDR, despite the upstream request
for 16× MSAA. This validates the supported local state setup, separate from the completed
CI cohort below and the original official MD-V3 gate.

An earlier exploratory guard pilot accidentally used a positional numeric
argument that selected Panda's vector overload, leaving the bool input at
priority zero. It was retained as
`shadow-feedback-terminal-guard-priority0-pilot.json`; explicit keyword/
ShaderInput priority fixed the setup and actual Panda CPU-contract tests pin
this behavior. Preliminary and source-API GPU probes are separate from the
three final source-launcher processes; none is an official ONNX run.

## Verified source and independent CI results (2026-11-11)

PR [#21](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/21)
merged as `96069779c85a691a81d119f27cafe39160c70cfa` from final source HEAD
`ce1015973fc35332cc5a217ea07adfa21e7bfdcc` after **14 passing checks**,
current-SHA Codex review without findings, no open review threads and clear
independent source/documentation reviews. The final local suite passed
**281 tests without skips**. No original renderer default was promoted.

The feedback [run 42957706605](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42957706605)
and existing-sampler compatibility
[run 42957706445](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42957706445)
each completed **5/5 jobs**. All **ten** artifact API SHA256/byte sizes and safe
ZIP paths were verified. Every four-case summary and final aggregate was
recomputed exactly from native receipts: feedback **48 distinct UUIDs,
12 same-runner PIDs per case, 128 terminal GPU rows**; existing sampler
**32 distinct UUIDs, eight same-runner PIDs per case, 64 GPU rows**.
Feedback raw archives retain native logs, execution ledgers and receipts;
sampler raw archives retain eight trial receipts and a case summary per case.
Retained evidence is under `output/stage7-remote-evidence/run-<run-id>/`,
including `recomputed.json`, `totals.json`, `verified_archives.json` and
`revalidation.log`; the sampler run also has independently derived metrics.

### Feedback OFF repeatability

| Condition | Source Road /40 | Source Wide /40 | Warped Road /40 | Warped Wide /40 | I420 /40 | I420 post-warmup /32 | Complete static cases /4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `baseline` | 36 | 39 | 36 | 40 | 36 | 29 | 3 |
| `linear` | 37 | 37 | 37 | 38 | 36 | 29 | 2 |
| `shadow_guard` | 37 | 36 | 37 | 40 | 37 | 29 | 3 |
| `both` | 35 | 34 | 35 | 37 | 33 | 26 | 2 |

**No condition achieved strict all-field 4/4 equality.** The combined treatment
matches fewer I420 frames than baseline in this cohort, so combining the two
state interventions is not a repeatability repair. The guard removes the
observed inherited shadow atlas binding hazard and linear sampling corrects
the sampler-type configuration; neither fact establishes the unique pixel-drift
cause, intended shadow accuracy or bit-equivalent rendering semantics.

| Seed | Scene | Condition | Source Road/Wide /10 | Warped Road/Wide /10 | I420 /10 | First source Road/Wide | First I420 | I420 different steps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20261109 | left_right | `baseline` | 6/9 | 6/10 | 6 | 2/8 | 2 | 2, 5, 7, 10 |
| 20261109 | left_right | `linear` | 8/9 | 8/10 | 8 | 2/4 | 2 | 2, 7 |
| 20261109 | left_right | `shadow_guard` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | left_right | `both` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | right_left | `baseline` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | right_left | `linear` | 9/8 | 9/8 | 8 | 5/5 | 5 | 5, 6 |
| 20261109 | right_left | `shadow_guard` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | right_left | `both` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | left_right | `baseline` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | left_right | `linear` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | left_right | `shadow_guard` | 7/6 | 7/10 | 7 | 6/2 | 6 | 6, 7, 8 |
| 20261110 | left_right | `both` | 7/7 | 7/10 | 7 | 2/2 | 2 | 2, 6, 8 |
| 20261110 | right_left | `baseline` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | right_left | `linear` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | right_left | `shadow_guard` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | right_left | `both` | 8/7 | 8/7 | 6 | 5/3 | 3 | 3, 5, 6, 9 |

The condition-order table above is the actual validated execution order.
Every first-running condition fails strict matching in its assigned case:
baseline, linear, shadow_guard and both respectively. Linear also fails in
second position in 20261109 / left-right; both also fails in second position
in 20261110 / left-right. Each condition runs first once, but four fixed
seed/scene assignments, process initialization, persistent shader/cache state
and fixed OFF0 → OFF1 → ON0 order remain confounded. The pattern motivates
further isolation; it does not prove execution position or cache history is
the unique cause. Static matching in later processes cannot establish a
retroactive effect of an observer installed only after all primary captures.

### Terminal GPU bindings and actual framebuffer samples

| Validated classification | Rows |
| --- | --- |
| `SHADOW_ATLAS_READ_WRITE_BINDING_HAZARD` | 32 |
| `RGB_ATLAS_COMPARE_ENABLED` | 32 |
| `RGB_ATLAS_RAW_LINEAR` | 32 |
| `SHADOW_GUARD_PLACEHOLDER_BOUND` | 32 |

All **128/128** rows recorded zero GL errors both before and after the query.
The 64 RGB rows observed actual **8 samples / 1 sample buffer**; the 64 shadow
rows observed **0 / 0**. These are actual bound framebuffer counts, distinct
from the upstream 16× request and from local smoke's RGB 4/1. Unguarded shadow
rows observe the real depth atlas attached and bound for sampling; guarded
rows observe the non-depth placeholder with `use_pssm=0`. RGB retains its real
atlas and `use_pssm=1`, with comparison state determined by sampler condition.

Summed measured query duration per eight-observation ON process ranges from
**1.657115 to 1.993208 ms**. This excludes observer setup, positive-control
rendering and teardown; it is not full instrumentation overhead or a GPU
execution time. These controlled inherited-state bindings do not trace every
original primitive or prove that an atlas fetch actually executed. OFF has no
query interface/callback; one ON process per condition/case is state evidence,
not a repeated ON arm or an unbiased timing comparison.

### OFF/ON and cross-condition image observations

OFF0/ON0 primary comparisons are separate process/temporal observations. Their
aggregate counts happen to equal OFF0/OFF1 counts in this cohort; they are not
extra repeatability gates or evidence that the terminal observer repaired prior
frames. Baseline-to-treatment comparisons below use each condition's OFF0.

| Comparison | Source Road/Wide /40 | Warped Road/Wide /40 | I420 /40 |
| --- | --- | --- | --- |
| OFF0/ON0 `baseline` | 36/39 | 36/40 | 36 |
| OFF0/ON0 `linear` | 37/37 | 37/38 | 36 |
| OFF0/ON0 `shadow_guard` | 37/36 | 37/40 | 37 |
| OFF0/ON0 `both` | 35/34 | 35/37 | 33 |
| baseline OFF0 → `linear` | 0/0 | 0/0 | 0 |
| baseline OFF0 → `shadow_guard` | 34/30 | 34/35 | 30 |
| baseline OFF0 → `both` | 0/0 | 0/0 | 0 |

| Seed | Scene | OFF0 cross-condition comparison | Source Road/Wide /10 | Warped Road/Wide /10 | I420 /10 |
| --- | --- | --- | --- | --- | --- |
| 20261109 | left_right | baseline → `linear` | 0/0 | 0/0 | 0 |
| 20261109 | left_right | baseline → `shadow_guard` | 8/7 | 8/10 | 8 |
| 20261109 | left_right | baseline → `both` | 0/0 | 0/0 | 0 |
| 20261109 | right_left | baseline → `linear` | 0/0 | 0/0 | 0 |
| 20261109 | right_left | baseline → `shadow_guard` | 10/8 | 10/8 | 8 |
| 20261109 | right_left | baseline → `both` | 0/0 | 0/0 | 0 |
| 20261110 | left_right | baseline → `linear` | 0/0 | 0/0 | 0 |
| 20261110 | left_right | baseline → `shadow_guard` | 8/8 | 8/10 | 8 |
| 20261110 | left_right | baseline → `both` | 0/0 | 0/0 | 0 |
| 20261110 | right_left | baseline → `linear` | 0/0 | 0/0 | 0 |
| 20261110 | right_left | baseline → `shadow_guard` | 8/7 | 8/7 | 6 |
| 20261110 | right_left | baseline → `both` | 0/0 | 0/0 | 0 |

Linear and combined conditions differ from baseline in every source/warp/I420
frame in these OFF0 comparisons. Guard-only also changes images and matches
baseline I420 only 30/40. This experiment does not establish image-semantic
equivalence for any treatment; within-condition equality and cross-condition
similarity answer different questions.

### Existing sampler compatibility cohort

The unchanged 32-process sampler API/schema also revalidated exactly on final
source. Its original OFF source Road/Wide matched **30/40 and 31/40**, warped
Road/Wide **30/40 and 35/40**, I420 **27/40**; each other arm matched all source,
warp and I420 fields **40/40**. All 64 controlled inherited-state observations
validate the expected original/linear binding classes. Full rates and first
differences are appended to
[the sampler guide](STAGE7_SHADOW_SAMPLER_ISOLATION.md). This separate cohort's
linear OFF 4/4 result does not override failures in this factorial cohort,
the earlier sampler source cohort or the fresh-cache local combined treatment.

### Complete verified archive ledger

| Run | Artifact ID | SHA256 | Bytes |
| --- | --- | --- | --- |
| 42957706605 | 13828537890 | `ad07e3138c5449a68761287c0766ecc065a30f2342696fc0de239f81af191a75` | 15620 |
| 42957706605 | 13828323746 | `3da53d20acd673736fa9423aa099ddfcd8b3d7eab6b44b0335d8aeb9411e5a7a` | 72835 |
| 42957706605 | 13828048481 | `cc94119d032bf805af05131dc423394a9af55d99dd4b09784acd278c55b7c43e` | 80581 |
| 42957706605 | 13827833647 | `01ed0188a74ad2cb663c7df762d0ca2551775f14f442231a0ed1d7639c1f0971` | 76319 |
| 42957706605 | 13827599376 | `0bccdbd4a44604bb473450f41a1e185754385d545c48d3eaf7bda14001b8707b` | 77242 |
| 42957706445 | 13828675872 | `0bc15379975ff4c48a839bcf8c80acd0ef9b8d358eb5cd2f2591105caf890f1b` | 44742 |
| 42957706445 | 13828630846 | `e370ac4fb4f1f28bb44291ee107fa960fa669114b18cf785f90b0951e11c6360` | 39110 |
| 42957706445 | 13828626572 | `a1fc26110ec1a11017e1bb0bb0a233d01845832e4a1240b2d44db655c0550bf6` | 42758 |
| 42957706445 | 13828566860 | `b050280818ba76eafb7de96198e8616cb5e955db2057b10ebdf60caac647dd0b` | 8158 |
| 42957706445 | 13827704436 | `c825b55c21a3aee936afd39080f4e3fec33f6391da17294f9cafa8583fff942f` | 42295 |

### Verified automatic merged-main sampler cohort

The PR #21 merge's separate main-source `9606977` sampler
[run 42961355395](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42961355395)
completed **5/5 jobs**. All five artifact API SHA256/byte sizes and safe ZIP
paths were verified. Four case summaries and the final aggregate reproduced
exactly from **32 distinct native UUIDs, eight same-runner PIDs per case and
64 validated GPU rows**. This is a new cohort, separate from source run
42957706445 and the separately completed automatic feedback matrix below.

| Arm | Source Road /40 | Source Wide /40 | Warped Road /40 | Warped Wide /40 | I420 /40 | I420 post-warmup /32 | Complete static cases /4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `original_off` | 27 | 30 | 27 | 35 | 23 | 17 | 0 |
| `original_probe` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |
| `raw_linear_off` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |
| `raw_linear_probe` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |

The 64 controlled inherited-state observations again divide into 32 original
comparison-enabled and 32 raw-linear comparison-disabled rows. Every other arm
matches every source/warp/I420 field in all four cases, but the original OFF
arm still has zero complete cases. Fixed arm order and terminal observation
after primary capture remain confounds; repeated later static matching is
not an original moving-model repair. Retained evidence:
`output/stage7-remote-evidence/run-42961355395/{recomputed,totals,verified_archives}.json`,
`revalidation.log` and `metrics.json`. Sampler case archives contain eight
trial receipts plus a case summary; no native logs or execution ledger are
claimed for this workflow.

| Run | Artifact ID | SHA256 | Bytes |
| --- | --- | --- | --- |
| 42961355395 | 13830375357 | `4d598d89536f549355782a346301f70d6e295f88aef6afe5abcd316096f8259e` | 42708 |
| 42961355395 | 13830031992 | `bb87c776cb2d73e95958cae63ebd65e82e784d436fadd93d75109e77837dee33` | 8110 |
| 42961355395 | 13829991703 | `902bc9ddf878982e5f2e9cc0ade2a6703d1ecaa233ac45851d3ba36cb2e539a8` | 42632 |
| 42961355395 | 13829568703 | `b78ebd3d5a31c2b5fa7f89f2ce090aff5bef31714fa8231f60eb3e4ca94570ff` | 39892 |
| 42961355395 | 13829477484 | `ae8eaf9536233cd48d70629e8791e87194b52e3328a9798522f5dd12dba6141f` | 42195 |

### Verified automatic merged-main feedback cohort

The separate automatic main-source `9606977` feedback
[run 42961355528](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42961355528)
completed **5/5 jobs**. All five artifact API SHA256/byte sizes and safe ZIP
paths were verified. Every case summary and final aggregate reproduced
exactly from **48 distinct UUIDs, 12 same-runner PIDs per case and 128
validated terminal GPU rows**. This is a separate repetition of source run
42957706605, with its own rates and first differences. Feedback case archives
retain 12 native JSON/log pairs, the execution ledger and a case summary.
Retained evidence:
`output/stage7-remote-evidence/run-42961355528/{recomputed,totals,verified_archives}.json`
and `revalidation.log`.

| Condition | Source Road /40 | Source Wide /40 | Warped Road /40 | Warped Wide /40 | I420 /40 | I420 post-warmup /32 | Complete static cases /4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `baseline` | 36 | 38 | 36 | 40 | 36 | 28 | 3 |
| `linear` | 37 | 37 | 37 | 38 | 36 | 29 | 2 |
| `shadow_guard` | 35 | 36 | 35 | 40 | 35 | 28 | 3 |
| `both` | 32 | 37 | 32 | 40 | 32 | 25 | 2 |

Main feedback's 128 GPU rows again divide into 32 rows per intended binding
class, with zero pre/post GL errors in all rows. Actual RGB samples/buffers
remain 8/1 and shadow 0/0. Per-ON summed query duration is
**1.684994–4.932800 ms**, from this cohort's `gpu_metrics.json`; the earlier
source cohort's 1.657115–1.993208 ms range is separate. Query durations are
not full instrumentation overhead or evidence of unbiased process timing.

No condition achieves strict 4/4 equality in this repetition. The validated
cyclic condition orders are unchanged. Again every first-running condition
fails its case; linear in second position for 20261109 / left-right and both
in second position for 20261110 / left-right also fail. Fixed seed/scene
assignments, initialization/cache history and OFF0 → OFF1 → ON0 ordering
remain confounds, not a unique explanation of drift.

| Seed | Scene | Condition | Source Road/Wide /10 | Warped Road/Wide /10 | I420 /10 | First source Road/Wide | First I420 | I420 different steps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20261109 | left_right | `baseline` | 6/8 | 6/10 | 6 | 5/8 | 5 | 5, 7, 8, 10 |
| 20261109 | left_right | `linear` | 8/9 | 8/10 | 8 | 2/4 | 2 | 2, 7 |
| 20261109 | left_right | `shadow_guard` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | left_right | `both` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | right_left | `baseline` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | right_left | `linear` | 9/8 | 9/8 | 8 | 5/5 | 5 | 5, 6 |
| 20261109 | right_left | `shadow_guard` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261109 | right_left | `both` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | left_right | `baseline` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | left_right | `linear` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | left_right | `shadow_guard` | 5/6 | 5/10 | 5 | 2/2 | 2 | 2, 3, 6, 7, 8 |
| 20261110 | left_right | `both` | 7/7 | 7/10 | 7 | 2/2 | 2 | 2, 6, 8 |
| 20261110 | right_left | `baseline` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | right_left | `linear` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | right_left | `shadow_guard` | 10/10 | 10/10 | 10 | none/none | none | none |
| 20261110 | right_left | `both` | 5/10 | 5/10 | 5 | 3/none | 3 | 3, 5, 7, 9, 10 |

OFF0/ON0 and baseline OFF0-to-treatment comparisons remain separate temporal/
process and cross-condition observations, respectively. Terminal observation
occurs after primary captures and cannot repair earlier images. Linear and
both still match baseline in zero source/warp/I420 frames; guard-only matches
baseline I420 28/40. There is no demonstrated rendering-semantic equivalence.

| Comparison | Source Road/Wide /40 | Warped Road/Wide /40 | I420 /40 |
| --- | --- | --- | --- |
| OFF0/ON0 `baseline` | 36/38 | 36/40 | 36 |
| OFF0/ON0 `linear` | 37/37 | 37/38 | 36 |
| OFF0/ON0 `shadow_guard` | 35/36 | 35/40 | 35 |
| OFF0/ON0 `both` | 32/37 | 32/40 | 32 |
| baseline OFF0 → `linear` | 0/0 | 0/0 | 0 |
| baseline OFF0 → `shadow_guard` | 32/29 | 32/35 | 28 |
| baseline OFF0 → `both` | 0/0 | 0/0 | 0 |

The complete five-archive ledger for this automatic feedback cohort is:

| Run | Artifact ID | SHA256 | Bytes |
| --- | --- | --- | --- |
| 42961355528 | 13830297211 | `451389a938e090ffc568d832b4076aeb42ec470fa4837d4ba865cf104966d21f` | 15807 |
| 42961355528 | 13830032953 | `f7f22b822765152e1e3a93f1b8e7d44c31ec43e8a0a1dda3e0fffd06cde7b689` | 78948 |
| 42961355528 | 13829987493 | `79cbf959a1f70e0d8bbad25f7c7d47155729e1736f5cefd3d4dd6c83b6355eb0` | 80322 |
| 42961355528 | 13829824640 | `96eca2de59b4b329acbe9dbba88e32a890d901557cc7590dce0f1c647b0c3228` | 72843 |
| 42961355528 | 13829649419 | `c02d26f530e8e5ee6248572e1ce0cddfbd070471b57343d02d5ad9dcb1882aec` | 77447 |

## Additional local negative results and next source boundary

After the earlier hot-cache combined OFF smoke matched 10/10, two fresh-shared
Mesa-cache combined OFF processes were run for 20261109 / left-right. The
first started with an empty dedicated cache; the second began with the first
process's populated state. Source Road/Wide matched **7/10 and 8/10**, warped
Road/Wide **7/10 and 10/10**, I420 **7/10**. Road/I420 first differ at step **4**
and differ at **4, 6, 8**; Wide source differs at **4 and 10**. Native receipts,
logs, cache receipts and comparison are under
`output/shadow-feedback-local/fresh-mesa-both/`, especially `comparison.json`.
The first cache inventory grew from zero to 101 files / 1,851,262 bytes; the
later process started with that inventory and ended at 101 / 1,889,257.
This proves cache availability/population, not individual cache hits.

These processes explicitly used **`both` (raw-linear sampler plus shadow-input
guard), observer OFF**. Their generic schedule comparator labels the schedule
`sequential_road_first` and emits an original-control flag; that flag describes
the shared capture schedule and is misleading as a treatment label here.
The raw diagnostic configuration is `feedback_both`, and these experimental
renderer bytes must never be reported as original-control output. Earlier
hot-cache 10/10 smoke is not a repair, and this single local pair is not a
randomized cache-causality experiment.

A separate two-process local prototype then combined `both` with explicit
terrain gradients at divergent material/normal texture fetches. It **failed**
strict matching: source Road/Wide **6/10 and 8/10**, warped Road/Wide
**6/10 and 10/10**, I420 **6/10**. Road/I420 first differ at step **2**, with
differences **2, 4, 5, 8**; Wide source first differs at **3**, differences
**3, 4**. Retained data: `output/terrain-gradient-pilot-v2/{run-0,run-1,comparison}.json`.

| Prototype source | SHA256 |
| --- | --- |
| Unchanged vertex | `74fe5c4b1dfeb80ecf3f200ff2236aaff76cc802b3cc956a3f4be0ff80a857c3` |
| Original terrain fragment | `2c1104ff463d5cb6f0170dcd0a0efec6da1234faa611ce5fe6291a93a0bb9404` |
| Experimental terrain fragment | `2188cacd7bfef6d0173da85316eaf4ec6f61386baaa916c808527c73cc745135` |

The shader compiled without a reported ErrorFlag and the receipts explicitly
mark the shader edit/prototype. This is outside the current feedback schema:
its generic schedule/hash comparison must be labeled with the additional
modified-shader treatment. It used two local processes, no observer or official
weights, shared fresh cache cold → populated, and no randomized unmodified
control. Failure rules out this particular prototype as a complete repair;
it does not prove or disprove a unique gradient mechanism. An earlier v1
anchor assertion failed before capture and produced no native JSON; its log
is retained at `output/terrain-gradient-pilot/run-0.log`.

### Completed local llvmpipe worker pilot

The preregistered local worker pilot is complete for seed 20261109 /
left-right. Four unchanged original Road-first native processes ran in ABBA
order `default_0 → zero_0 → zero_1 → default_1`, requesting `LP_NUM_THREADS`
unset versus `0`, with one initially empty shared Mesa cache per arm (cold →
populated). No shader edit, observer, extra render, model weights or inference
was used. All four launcher statuses were zero, with four unique native UUIDs
and four distinct PIDs. Retained plan, native receipts/logs, before/after cache
file SHA manifests and comparisons are under `output/llvmpipe-worker-pilot/`,
including `plan.json`, `execution_receipts.json` and `comparisons.json`.

| Requested setting | Source Road/Wide /10 | Warped Road/Wide /10 | I420 /10 | First I420 | I420 different steps |
| --- | --- | --- | --- | --- | --- |
| `LP_NUM_THREADS` unset | 8/6 | 8/10 | 8 | 2 | 2, 7 |
| `LP_NUM_THREADS=0` | 8/8 | 8/10 | 8 | 2 | 2, 7 |

Whole-process wall times in execution order were **65.803, 112.260, 111.605,
61.028 s**. These include startup, rendering, analysis and shutdown and do
not measure pure worker overhead. The
[Mesa environment documentation](https://docs.mesa3d.org/envvars.html#envvar-LP_NUM_THREADS)
states that zero disables threading, and the retained pinned Mesa 25.0.7 source
`/workspace/.cloud-tools/stage7/lp_screen-25.0.7.c` reads `LP_NUM_THREADS` into
its worker-count setting. This is a requested environment intervention, not an
actual per-worker execution trace; an incidental total process-thread count
cannot confirm raster worker state.

Requested zero did **not** restore complete matching in this case. The result
does not support a necessary-parallelism or unique-cause claim. One seed/scene,
fixed ABBA order and cold → populated cache reuse remain confounds, and cache
inventories do not prove hits. A CI matrix is unnecessary to reject this
specific complete-fix candidate after its local mismatch; it does not rule out
all runtime scheduling mechanisms.

### Completed local apitrace capture and bounded draw-input analysis

The workspace-only apitrace v2 ABBA capture is complete for 20261109 /
left-right: `off_0 → on_0 → on_1 → off_1`. All four native receipts validate,
all raw native statuses are zero, and UUIDs/PIDs are distinct. Every arm uses
the same explicit Python default-SIGINT initialization before runpy of the
unchanged original capture module; the renderer/capture source is unchanged.
OFF loads no trace library. ON traces actual GL calls throughout primary
rendering, unlike the earlier terminal-only binding observer. One initially
empty shared Mesa cache per arm is reused cold → populated.

| Trace arm | Source Road/Wide /10 | Warped Road/Wide /10 | I420 /10 | I420 post-warmup /8 | First I420 | I420 different steps |
| --- | --- | --- | --- | --- | --- | --- |
| OFF | 8/8 | 8/10 | 8 | 7 | 2 | 2, 7 |
| ON | 7/2 | 7/10 | 7 | 5 | 7 | 7, 9, 10 |

ON source Wide first differs at step 1 and differs at 1, 2, 4, 5, 6, 8, 9, 10;
Road/I420 first differ at 7, with differences 7, 9, 10. Wide warped RGB matches
10/10. These are measured source-versus-warp timelines, not a causal trace result.

The exact schedule comparisons reproduced from the four raw native receipts.
Neither arm matches strictly. Whole-process wall times in ABBA order are
**81.540, 72.697, 81.861, 77.912 s**; these include startup, rendering,
analysis, shutdown and trace work, not pure query or instrumentation overhead.
The tracing tool logs that it hides program-binary formats, so ON changes
driver capability as well as timing. This single fixed-order/cache experiment
cannot yield a universal overhead estimate or prove that untraced draws have
the same state as the traced draws.

All four native JSON/logs, native JSON SHA receipts, execution/cache manifests,
comparisons and both complete raw traces are retained under
`output/apitrace-draw-pilot-v2/`, including `plan.json`,
`execution_receipts.json` and `comparisons.json`.

| Trace | Bytes | SHA256 |
| --- | --- | --- |
| `on_0.trace` | 209757595 | `9665413782cbe05d0f5460c8983643b5cdf8e6d8415ad88f2a2e85f135136e9a` |
| `on_1.trace` | 209758897 | `6ddef5fc8a2c29d6f296e991fe32322b22d73a38dfd86f8764e78990622d3192` |

The earlier attempt under `output/apitrace-draw-pilot/` retains a valid OFF0
receipt, but ON0 has native `ERROR` from the `None` SIGINT handler TypeError
and a partial trace; it is not a complete valid ABBA matrix. The common v2
bootstrap applies to OFF and ON, not just the traced arm.

The bounded read-only comparison of the two raw traces is complete. Retained
reports under `output/apitrace-draw-pilot-v2/analysis-agent/` are
`findings.json`, `draw-pass-comparison.json` and
`startup-transform-table-use.json`. The full streams contain **106,555 and
106,580 calls**, each with **2,901 geometry draws and 192 graphics-buffer
passes**. All **eight actual shader-source submissions** and **322 ordered
CPU texture uploads** match, including complete arguments and blob SHA256.
Host pointer identities were normalized; numeric GL names and buffer offsets
were retained. This does not reconstruct GPU-generated texture contents.

The first non-timestamp input difference is call **9027**, program 1,
`p3d_TransformTable[0]` with 100 matrices: **828 float entries differ in used
matrix slots 0–68**. The matching vertex weights/indices reference those
slots in startup draws **9029, 9375 and 9738**. Slots **69–99 are equal**;
this is not differing unused padding. Pinned Panda3D 1.10.13
`glShaderContext-1.10.13.cxx::update_transform_table` explicitly identity-fills
unused table slots. Only startup passes **19–21** have different geometry/
explicit-uniform multisets; this startup difference is not itself a proven
cause of later primary-frame drift.

Every primary/control pass matches the unordered geometry, explicit
current-program uniform and declared constant vertex-input multiset in the
analyzed scope. Geometry order differs in **53 passes**. Across **2,898
matched draws**, active sampler and CPU texture inputs are identical. The
first primary-window order difference is opaque pass **67**, FBO **3**:

| Trace | Skybox/terrain order in pass 67 |
| --- | --- |
| ON0 | skybox program 4, call 35777 → terrain program 10, call 35823 |
| ON1 | terrain program 10, call 35802 → skybox program 4, call 35828 |

The following Wide read calls **37381 / 37387** align with the first Wide
source-hash mismatch under the fixed host-schedule mapping. The trace has no
explicit Panda clock markers. Order also changes on matching image frames,
so this correlation establishes neither necessity nor sufficiency. In the
tracked rasterizer subset, six skybox `GL_MULTISAMPLE` differences occur only
on main framebuffer **7**; none occur on Road/Wide HDR framebuffers **3/5**.
Full GL state, GPU-produced atlas/HDR pixels and untraced per-primitive state
were not reconstructed. The original traced path retains its known sampler/
feedback hazards, and apitrace changes capability/timing. No unique cause,
additional driver defect or renderer repair follows from these scoped findings.

Pinned Panda3D 1.10.13 source under `/workspace/.cloud-tools/stage7/` gives a
concrete next boundary: `renderState-1.10.13.cxx` lines 164–184 orders render
attributes by **pointer**, then `cullBinStateSorted-1.10.13.I` lines 43–70
breaks ties with vertex-format, munged-data and transform **pointers**. That
source behavior is established; its causal role in these image mismatches is
not. It does not justify adopting a different default sort policy.

### Pending local opaque-bin intervention

A separate ABBA pilot is underway, preregistered at
`output/opaque-bin-pilot-v3/plan.json`: `state_sorted_0 → unsorted_0 → unsorted_1 →
state_sorted_1`, for 20261109 / left-right, with one initially empty shared
Mesa cache per arm (cold → populated). On top of experimental **`both`**, it
requests opaque `CullBinManager` type **2 (state-sorted)** versus **1 (unsorted)**
before primary frames. Original Road-first/PSSM/Chase, two ticks, shader source
and image processing remain unchanged; terminal observer is OFF with no GL
query or profiler. The extra bin intervention means these are **not ordinary
`both` cells**. A generic feedback receipt validates the shared Both fields,
not the additional bin semantics or actual draw order. This one fixed-order/
cache case has **no outcome recorded yet** and promotes no default render sort.

The active attempt is **v3**. Earlier v1 validated the in-memory `camera_pose`
tuple before writing and failed with a pose/positive-control schema error;
its native JSON was lost, with log/cache/`failed_attempt_record.json` retained
under `output/opaque-bin-pilot/`. That missing raw evidence is unrecoverable
and cannot count as a valid cohort. V2 saved an `OBSERVED_NATIVE_PIXEL_CLOCK`
JSON that passes the unchanged strict validator after JSON loading, but the
wrapper still returned **1** after validating the in-memory tuple; raw JSON,
log/cache and failure metadata remain in `output/opaque-bin-pilot-v2/`.
Schema-valid saved data does not turn that failed wrapper into a completed
matrix. V3 writes JSON, reloads it and applies the same strict wire validator.
The existing-fixture tuple/JSON-roundtrip reproduction confirms the wrapper
type issue; no native comparison criterion was relaxed and no source changed.

Per-camera `ShaderTerrainMesh` view-data lifetime and LOD state remain another
source-review hypothesis, with no validated repair or new matrix outcome
recorded here. Preserve independent OFF controls,
process/order receipts and source/warp/I420 measurements before promoting any
intervention. Original official MD-V3 remains the prior **0/4 PASS (FAIL)**;
there was no official-weight download or ONNX inference, defaults are unchanged,
and Stage 7 remains incomplete.

Both automatic main-source (`9606977`) cohorts are complete and independently
revalidated above: feedback **42961355528** (48 processes) and sampler
**42961355395** (32). Unit run **42961355303** passed. Do not repeat these
completed cohorts merely to rediscover their recorded failures. No default
repair or new official MD-V3 gate follows from these repetitions.
