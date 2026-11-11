# Experimental renderer candidate: official MD-V3 strict repeatability

The source and automatic main cohorts each pass the separately labeled
candidate strict gate **4/4** for `feedback_both` plus opaque unsorted type 1. The historical original official MD-V3 gate remains **0/4
PASS (FAIL)**. A candidate 4/4 is its own result and never replaces the original
record, adopts a default renderer, proves full rendering equivalence or permits
model ranking or real-vehicle claims.

Two independent 32-process opaque-order cohorts matched all source/warp/I420
fields 40/40 in both original-unsorted and combined-unsorted conditions, while
sorted controls still failed. The eight-process local terminal-depth v2 protocol
then found identical 2048×1024 DEPTH32F bytes across linear-only/combined and
sorted/unsorted conditions in seed 20261109 left-right: SHA256
`e2fad785dc9037146323996699cb8c2a23e517bb99acce5557ee5957fe234881`,
5347 nonclear texels, zero GL errors and exact state restoration. Unsorted
guard on/off also matched primary image bytes in that one case. That limited
terminal result supports a bounded candidate diagnostic, not universal shadow
or photometric equivalence. Readback/observer overhead, cache/history and scene
coverage remain limitations; the failed v1 ops attempt remains separate.

The new module delegates the existing public `run_target_lane_episode` loop.
It creates the original NativeMetaDriveProvider, chooses the same first native
curve lane and uses the exact NativeWorldCamera through a thin CPU audit that
calls capture once and forwards its source hashes. The original ego RGB
visibility is preserved. The static raw-clock experiment is not the model
episode runner, because that static path explicitly hides the visual ego.

The existing opaque policy context sets type 1 before provider creation,
preserves bin index/name/sort/active state and restores type 2 on exit/errors.
After provider initialization, `configure_sampler(engine, 'feedback_both')`
sets the already implemented linear atlas and bounded shadow-camera guard.
The guard adds only high-priority `use_pssm=False` and a white 1×1 RGBA8 atlas
placeholder to initially empty shadow-camera states; it preserves inherited
shaders. CPU receipts include complete typed bin/sampler/guard metadata and
task registries before/after the episode while the engine is alive.

All camera, lens, geometry, original Road-first sequential calls, PSSM.update,
Chase, two task ticks per pair, source 964×604, warped 512×256 and actual uint8
I420 [2,6,128,256] paths remain delegated unchanged. The episode retains speed
8 m/s, virtual dt .05, initial fraction .12, the first target lane and the
existing fixed-speed kinematics. There is no convergence, warmup capture,
tolerance, replay, image correction, RGB-retention observer, GPU query,
depth/HDR extraction, extra PSSM update or render, clock change, controller
override, action/state substitution or model-input repacking.

The candidate policy subclasses AuditedOfficialOnnx. It calls the parent reset
and step, with one actual inference per step and no per-step reset. The parent
hashes the actual ORT image feed and all recurrent states. Additional audit
records preserve each initial and post-step state separately:

| Name | Shape | Dtype | Bytes |
| --- | --- | --- | --- |
| state_img_q | [2,5,6,128,256] | uint8 | 1966080 |
| state_desire_q | [132,1,8] | float32 | 4224 |
| state_feat_q | [128,1,16384] | float32 | 8388608 |

Each receipt carries name/dtype/shape/nbytes/C-order SHA256 beside the parent
aggregate digest. Raw action evidence includes all four actual float32 values,
shape [4], 16 bytes and SHA256 from the original action slice 2062:2066, plus
the unchanged parent-converted ModelAction. JSON action values must round-trip
exactly through float32 and match their recorded bytes.

Capture audits record the entry virtual pose/time and before/after Panda clock
observations. Validation requires finite, consistent clocks, contiguous counts
and exactly two ticks; virtual before/after poses and times must agree exactly
with the unchanged kinematics. Wall times are validated and retained, not
required to match between processes. Named-state hashing reads about 10 MB per
step; extra audit time is reported as CPU overhead rather than free work.

The strict gate uses two seeds × two S-curves × twelve steps × two independent
Panda/CPU ORT processes: **8 UUIDs/nonces, 96 model steps**, with two distinct
same-runner PIDs per case. Twelve capture rows, twelve parent ONNX trace entries
and twelve policy audit rows are required. Initial state is the exact parent
zero reset. Every source/warp/I420 hash, all four action values/bytes, aggregate
and named recurrent receipts, capture-entry and post-action virtual pose/time
must match. A single field/step difference fails the candidate gate.

The existing exact comparator handles common fields; new validation adds every
candidate state/action/capture/config field. Missing/malformed evidence is
rejected. Full raw JSON is saved before strict wire validation, preserving
partial rows and errors and avoiding tuple-serialization mistakes. Fresh launch
nonce/output/log checks apply; exit 0 or Xvfb cleanup 5 is accepted only with a
complete validated receipt for that request. Every other native status remains
a failure. Failed/cancelled attempts and logs are retained, never retried or
counted as completed cohorts. Case and final summaries regenerate exactly.

Official model identity is **768750198 bytes**, SHA256
`35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199`.
The unchanged spec byte SHA256 is
`689f4d80082070b08ff35920e37d7070e811dfb42a279909751f79e900c735e2`.
Both are checked before constructing ORT; no public test-model bypass exists.
The parent CPUExecutionProvider/ORT_ENABLE_BASIC settings remain unchanged.
Unit fakes are explicitly unit evidence and do not execute official weights.

The candidate-only workflow pins MetaDrive 0.4.3, Panda3D 1.10.13 and official
assets bytes 134074203 / SHA256
`4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9`.
Official weights download only into ephemeral CI `$RUNNER_TEMP/models`, never
local workspace storage or evidence artifacts. Four native jobs use maximum
parallelism two and sequential repeats, followed by independent aggregation.
Five artifacts retain only scoped JSON/log/ledger evidence, including hidden
files and failures. Existing source and existing workflows are unchanged.

Pure reaggregation uses no model, Panda initialization or native capture:

```bash
python -m scripts.native_mdv3_renderer_candidate --mode aggregate \
  --root output/stage7-mdv3-renderer-candidate \
  --out output/stage7-mdv3-renderer-candidate/aggregate_summary.json
```

This guide records the completed first source candidate cohort below.
Data-collection CI success alone is not a candidate PASS: the strict raw
comparison and every artifact must validate. A candidate exact 4/4 permits
only later separately documented candidate expansion, with original/default,
optics, geometry fidelity and driving-performance claims kept separate.


## Verified first official-model candidate result (2026-11-11)

**The experimental candidate passes its strict gate 4/4.** PR
[#25](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/25)
merged as `e840022a73879164b4923f77dbb4aabaf1112131` after exact source HEAD
`0fbebed2358610a773d317ef8e857acf6ddf5c98` passed all nine checks, completed
current-SHA Codex review without findings/no open threads and clear independent
raw-evidence review. **313 local tests passed without skips**. Native module
SHA256 remained
`5a9058102004e2f5eaa4c9dcab4c24d97a9d42702b7a9e7c248c4f576a30d22e`.
[Merge evidence comment](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/25#issuecomment-6790149167).

[Source Actions run 42979680883](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42979680883)
completed **5/5 jobs**. Every one of the five API archive SHA256/byte sizes and
safe ZIP paths passed verification. All four case summaries and the final
aggregate exactly reproduced from raw JSON and ledgers: **eight unique native
UUIDs/nonces**, two distinct same-runner PIDs per case, **96 actual model
steps and 48 paired-step comparisons**. There is no mismatch or tolerance in
any required field.

| Seed | Scene | Source Road/Wide /12 | Warped Road/Wide /12 | I420 /12 | Action/state/pose-time matches /12 | First difference | Candidate gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 20261109 | left_right | 12/12 | 12/12 | 12 | 12 each | none | PASS |
| 20261109 | right_left | 12/12 | 12/12 | 12 | 12 each | none | PASS |
| 20261110 | left_right | 12/12 | 12/12 | 12 | 12 each | none | PASS |
| 20261110 | right_left | 12/12 | 12/12 | 12 | 12 each | none | PASS |

| Required paired-step field group | Matches /48 |
| --- | --- |
| Source Road and Wide full RGB | 48 each |
| Warped Road and Wide RGB | 48 each |
| Actual uint8 I420 feed | 48 |
| All four raw float32 action values and bytes | 48 |
| Parent-converted ModelAction | 48 |
| Aggregate recurrent-state receipt | 48 |
| state_img_q / state_desire_q / state_feat_q receipts | 48 each |
| Capture-entry virtual pose | 48 |
| Post-action virtual pose, speed and time | 48 each |

Each process reports ONNX Runtime **1.31.1**, **CPUExecutionProvider** only,
**ORT_ENABLE_BASIC / optimization level 1** and no injected session. Official
model/spec identities match the pinned values above. The public episode loop,
original NativeWorldCamera and original ego visibility are retained; there are
no extra GPU queries, texture extracts, RGB observers or inference calls.
Panda clocks satisfy finite/contiguous two-tick controls; virtual capture-entry
and post-action pose/time match exactly. Wall-time equality is not a gate.

The evidence evolves through the episode: in every one of the eight trials,
each source/warped/I420 timeline has **12 distinct hashes**, as do raw actions
and aggregate state. Named image and feature states each have **12 distinct
post-step hashes**. Desire state has **one constant zero-state hash**, matching
the expected zero-desire contract, rather than a per-step state reset. The
two expected construction/episode resets and twelve parent policy steps are
validated; recurrent state remains continuous across those steps.

### Audit timing and retained evidence

| Stored wall-time scope | Observed min–max | Total across 96 steps |
| --- | --- | --- |
| Additional named-state audit block | 5.533088–13.862155 ms | 0.662456844 s |
| Whole delegated capture | 4.091141–9.297873 s | 520.860844211 s |

`named_state_audit_wall_s` covers the additional post-parent-step named-state/
action-receipt audit block. It excludes the parent inference/capture path;
it is not end-to-end instrumentation overhead. Whole capture times include
native rendering/readback and are not pure audit overhead. These are measured
wall scopes in this cohort, not a universal timing comparison or real-time
performance result.

Raw case archives retain two native JSON/log pairs, the execution ledger and
case summary; the summary archive retains the independent aggregate. They do
not retain official weights. Local evidence under
`output/stage7-remote-evidence/run-42979680883/` includes `recomputed.json`,
`totals.json`, `verified_archives.json` and `revalidation.log`; retained API
metadata is `output/stage7-remote-evidence/artifacts-42979680883.json`.

| Run | Artifact ID | SHA256 | Bytes |
| --- | --- | --- | --- |
| 42979680883 | 13837476939 | `8235596204a48b60698786471cc78afe7e3b2d9f913315176227e87274dd94ba` | 2101 |
| 42979680883 | 13837291091 | `ef137200bca193a045a270e9f3fe2e39f815cefad7b1e3a71756680e70104d94` | 25126 |
| 42979680883 | 13837042270 | `2a7ae20b5cd27b0a7e66703e19eed30daee8504ebb830ec425d40e02b274bb22` | 25114 |
| 42979680883 | 13836908106 | `72b47692072c4fda2bb9c9f2ae6b76f39e15f324a79dfd0ebd644772154260b9` | 24987 |
| 42979680883 | 13836788252 | `9dd027bfe1da28598be8d6294448d9a7f758b7da37a4804615e1120151e7739c` | 25103 |

## Completed automatic merged-main replication

Automatic main [run 42981493726](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42981493726),
on merge source `e840022a73879164b4923f77dbb4aabaf1112131`, completed **5/5 jobs**
and also reports **candidate 4/4 PASS**. All five API archive SHA256/byte sizes
and safe paths were verified; all four raw case summaries and the final
aggregate regenerated exactly. Fresh independent read-only review of this
main cohort's API/archive/raw evidence is clear. Unit main **42981493834** passed.

This is a separate eight-process / 96-model-step repetition with eight fresh
UUIDs/nonces and two distinct same-runner PIDs per case. All 48 within-cohort
paired steps match every required source/warp/I420, four-action value/byte,
aggregate/named-state and capture-entry/post-action virtual pose/time field.
No mismatch or tolerance occurs.

| Seed | Scene | Source Road/Wide /12 | Warped Road/Wide /12 | I420 /12 | Action/state/pose-time matches /12 | First difference | Candidate gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 20261109 | left_right | 12/12 | 12/12 | 12 | 12 each | none | PASS |
| 20261109 | right_left | 12/12 | 12/12 | 12 | 12 each | none | PASS |
| 20261110 | left_right | 12/12 | 12/12 | 12 | 12 each | none | PASS |
| 20261110 | right_left | 12/12 | 12/12 | 12 | 12 each | none | PASS |

All eight main trials again have twelve distinct source/warp/I420 hashes;
image/feature state hashes have twelve and desire retains the expected one
zero-state hash. CPU ORT **1.31.1**, CPUExecutionProvider/BASIC level **1**,
original camera/episode/ego visibility and zero GPU query/extraction/observer
controls validate again. The native module SHA remains unchanged.

| Main-cohort wall-time scope | Observed min–max | Total across 96 steps |
| --- | --- | --- |
| Additional named-state audit block | 6.495361–16.398507 ms | 0.733913688 s |
| Whole delegated capture | 5.182054–9.343551 s | 581.412606980 s |

These are the same narrow extra-audit and whole-capture timing scopes defined
above. They are not pure inference/instrumentation overhead or a universal
performance comparison. Raw evidence is retained under
`output/stage7-remote-evidence/run-42981493726/`; API metadata is
`output/stage7-remote-evidence/artifacts-42981493726.json`.

| Run | Artifact ID | SHA256 | Bytes |
| --- | --- | --- | --- |
| 42981493726 | 13838740095 | `22954c2822f71ab061bc33ed2abed2d50821f06b755bccc49184af03b8eff7b7` | 25096 |
| 42981493726 | 13837733434 | `f53ce10371b6d65d8dbc7827a2cba5e78ec1693db413dff33ada34072828404b` | 25116 |
| 42981493726 | 13837649488 | `fde71f5a7cff8925ab9182926708b97fc9e9e64dab2d5e7270403f1efc356094` | 25070 |
| 42981493726 | 13837577864 | `900e46eade3829b817170c99fec8f9733ea296a0288803fdb68cb20d1ae7434a` | 25174 |
| 42981493726 | 13837204271 | `86da3b2be2ab634c325533278d405b585539578a7cc5b0894b4c4f5968a7c232` | 2097 |

The source and main cohorts together contain **16 unique UUIDs/nonces and
192 actual model steps**, with no identity reuse. The two initial gates compare
within each cohort's independent repeat pairs. An additional read-only comparison
of all four processes per case also matches every required field, named state,
capture entry/count and initial/configuration receipt: all six process-pair
combinations in each of four cases are exact. Those288 pairwise row checks
reuse the existing192 model steps; they are not new inferences. Evidence:
`output/stage7-remote-evidence/candidate-two-cohort-cross-comparison.json`.
CPU/GPU hardware identities were not retained, so this is a bounded raw-data
comparison, not a hardware-equivalence claim. Fresh main-evidence review is
clear. The revised [prospective expansion plan](superpowers/plans/2026-11-11-mdv3-candidate-expansion.md)
also has clear independent review. No expanded-campaign result is recorded
here. The results
documentation PR also needs fresh review, current-HEAD CI and merge before
any expansion workflow is pushed; its future PR number is not presumed.

## Interpretation and next checkpoint

This is the first completed **`CANDIDATE_BOTH_UNSORTED_OFFICIAL_MDV3`** 4/4
source cohort using official inference and the original model camera/episode
path. It is separate from the historical **unmodified original 0/4 PASS
(FAIL)** record and preserves every earlier failed or partial experiment.
No original/default renderer has been promoted. Full rendering or photometric
equivalence, a unique GPU microcause, real-sensor optical fidelity, driving rank,
long-horizon behavior and Stage 7 completion are not established by this gate.
The bounded result covers only the registered twelve-step cases; later
expansion needs its own documented protocol and exact comparisons.

Source run **42979680883** and automatic main **42981493726** are complete
and independently reaggregated. Do not manually repeat either merely to
rediscover its recorded result. The revised expansion plan is reviewed;
complete fresh results-documentation review/current-HEAD CI/merge before
expanded native/model execution or workflow push under that candidate protocol. Every later result keeps its candidate label; original gate/default
adoption, optics, driving performance and Stage 7 completion remain distinct.
