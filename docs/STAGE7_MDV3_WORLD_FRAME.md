# Official MD-V3: opt-in model-to-world action basis bridge

**Current result:** corrected source 43005087003 and automatic main 43006858419 each independently pass 4/4. Together they contain 16 fresh UUIDs/nonces and 192 actual inferences/completed rows; all ten archives are independently clear.

This diagnostic introduces an explicit action-frame boundary around the
unchanged official audited MD-V3 policy. It runs the experimental Both+unsorted
renderer candidate. It does not migrate legacy consumers, promote a renderer
default, or establish tracking quality, full-S traversal, optical equivalence,
model ranking or real-vehicle readiness.

The legacy official original-renderer gate remains 0/4 FAIL. Legacy candidate
and expansion cohorts remain immutable repeatability evidence under their
unconverted action binding. Their bit-exact results do not demonstrate valid
motion semantics. The completed expansion's four 160-step cases stayed on
their first route lane and had approximately 39–41 m maximum virtual lateral
deviation. The frame mismatch is established; its sole responsibility for all
tracking error is not established. No old actions, poses, labels or raw JSON
are retroactively changed.

The numeric parent conversion remains
`raw_lateral_acceleration / max(2.5, speed)**2`. Model body/device FRD means
forward/right/down; the virtual integrator uses body FLU, forward/left/up,
with positive curvature increasing counterclockwise world heading. Both
bases are right-handed. The constant rotation is
`R = diag(1, -1, -1)`, determinant +1: a 180-degree body-basis rotation about
forward. Therefore applied world curvature is the negative of parent model
curvature, and longitudinal acceleration is unchanged. The global world axes
are fixed; the existing integrator handles the current heading. Neither world
Y nor the camera/image coordinates are globally flipped.

Pinned upstream catalog commit
`e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42` provides the reviewed source chain:
camera.py 73–88 declares the bases; modeld 114–115 computes model curvature;
parser 112–120 and fill_model_msg 100 preserve it; controlsd 217/225, 227,
262–265 preserves its sign before angle 23 and torque 171/174/306 negate it at
the left-positive steering boundary. These files were inspected as text.
No controller, vehicle plant, CAN, CD210, Carrot parameters or real car executes.

`WorldFramePolicyAdapter` composes the exact audited policy from the existing
pinned factory. Construction performs no reset. Its reset forwards once and
clears only bridge receipts; its step forwards the identical observation once,
then returns `ModelAction(-parent.curvature_1pm, parent.acceleration_mps2)`.
There is no tuning, smoothing, clipping, ground-truth input, scene/seed branch,
second inference, I420 repacking or raw-output rewriting. Parent raw four-action
values/bytes/SHA, input SHA, ModelTiming, aggregate state digest, all three
typed named-state receipts and parent-converted FRD action remain untouched.
The adapter forwards actual contract/session/state/trace/audit/output properties
and actual mock/injected-session flags; it never manufactures official flags.

Separate bridge receipts record sequence, source and applied action conventions,
constant body rotation, parent FRD action, applied FLU/world-CCW action and
measured CPU audit time. Frame tags apply only to the applied action; forwarded
plans, raw outputs and states retain their original convention. Wrong source
declarations, an adapter marker or an existing world-action convention fail
before repeated conversion.

The runner checks seven source-byte bindings before factory/ORT creation:

| Source | SHA256 |
| --- | --- |
| bigbench/onnx_policy.py | d983d5950296620a6ae89c88993829b4d2cebd35a6fd0e9046a980f75c9142da |
| scripts/native_mdv3_repeat_trial.py | ddaf0510a775c3a44c908bb4dedf4879ae88bfcb80e1f2d022a8b513a4f42427 |
| scripts/native_mdv3_renderer_candidate.py | 5a9058102004e2f5eaa4c9dcab4c24d97a9d42702b7a9e7c248c4f576a30d22e |
| scripts/native_mdv3_candidate_expansion.py | d86b3be67c8ac3dee31f0bf9928014d3880c8c55a6cd829bb3c46c464d16b42c |
| bigbench/kinematics.py | 58c92e9a5b584932cfe73ebbf7de888f2595e88ceacdabe9a457a78fa77bb70a |
| bigbench/native_model_campaign.py | 0bcb4ca73e1404a7164be1c879a200eeff5ca41e47e3035301d40fd173000bad |
| bigbench/metadrive_camera.py | 1c5661e6c9eea6445ebe55cb246e6b48d3384dd5a731353ba3f1a45599e338f9 |

A changed parent conversion fails the binding check instead of silently causing
a second sign conversion. Updating a binding requires another frame-contract
review. The unchanged model/spec factory verifies the actual 768750198-byte
official model SHA256
`35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199`
and spec SHA256
`689f4d80082070b08ff35920e37d7070e811dfb42a279909751f79e900c735e2`
before ORT. The runner requires the exact noninjected audited inner class;
there is no public model or session bypass.

The first corrected gate is deliberately bounded: seeds 20261109/20261110 ×
left-right/right-left native S × twelve steps × two fresh Panda/CPU ORT
processes, fraction .12, speed 8 m/s and dt .05. Full completion means eight
processes and 96 actual inferences. Corrected ramps, camera .28 and 160-step
episodes are not implemented here. They require a separately reviewed plan
after independently accepted corrected 4/4 evidence.

Actual capture remains owned by original `NativeWorldCamera` and the public
episode loop, called once. Ego visibility, Road-first sequential sensor reads,
source 964×604, warp 512×256, uint8 I420 [2,6,128,256], PSSM/Chase and two
ticks remain unchanged. Opaque type 1 is configured before provider creation;
feedback_both is configured after initialization. The existing CPU capture
audit adds 786432 warped bytes hashed per capture, besides the inherited
10358912-byte additional named-state audit and unchanged parent aggregate
digest. Audit costs are recorded, not claimed as free. No RGB retention,
warmup/convergence/replay, extra capture/render/PSSM/tick/clock advance, GPU
query or depth/HDR readback is introduced.

Protocol `stage7-mdv3-world-frame-v1` uses evidence label
`CANDIDATE_BOTH_UNSORTED_WORLD_FRAME_OFFICIAL_MDV3`. It has its own
`world_frame_exact_gate_passed` and four-case aggregate, separate from every
legacy gate. Generic legacy helpers validate parent FRD audit fields and
capture pose/clocks/hashes. New validation checks the actual new identity and
bridge, then computes kinematics using the applied WORLD action. No legacy
label/group/action is forged to invoke an old fixed validator. All source,
warp/I420, raw action and aggregate/named state receipts, entry and post-world
pose/time and bridge fields must match exactly. Finite wall times are retained
but excluded from across-process equality.

This gate is complete-only. Raw JSON containing every frame/capture/parent/
bridge audit and error is saved before reload and wire validation. Dangling
records after a failed step remain retained. Every incomplete requested
episode fails; legacy expansion's valid-partial collection rule is not used.
Native 0 or Xvfb cleanup 5 requires a fresh complete nonce-matched receipt;
every other native status remains a failure. There are no automatic retries.
Fresh output/logs, two distinct same-runner PIDs per case, eight distinct
cohort UUIDs/nonces and exact raw case/final regeneration are mandatory.

The new workflow runs four native case jobs with maximum parallelism two and
an independent NumPy-only aggregate, producing five scoped JSON/log artifacts.
It preserves failure artifacts and propagates shell pipeline failures. Pins
remain MetaDrive 0.4.3, Panda3D 1.10.13 and official assets 134074203 bytes /
SHA256 `4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9`.
Weights exist only in ephemeral CI `$RUNNER_TEMP/models`, never artifacts or
local test fixtures. Feature/main pushes affecting the new adapter, runner,
test or workflow trigger this bounded gate; explicit dispatch also exists.
One automatic merged-main run is predeclared as a **separate replication
cohort**, with its own eight UUIDs and 96 steps. Do not manually repeat a
completed run. Legacy PR27 acceptance/merge precedes any corrected trigger.

Before result acceptance, require current-source full tests and scientific/
code/workflow review, current-HEAD CI/Codex/no open threads, all five archive
API sizes/SHAs/safe paths and independent exact raw regeneration. Data-collection
CI success is not a gate PASS. Repeatability is separate from tracking quality;
no renderer-default, full-equivalence, optical, full-S, Stage7-completion,
ranking or real-vehicle claim follows.

Pure reaggregation uses no weights, graphics or model execution:

```bash
python -m scripts.native_mdv3_world_frame --mode aggregate \
  --root output/stage7-mdv3-world-frame \
  --out output/stage7-mdv3-world-frame/aggregate_summary.json
```

Unit contracts cover signed zero/nonzero headings, unchanged inner evidence,
source pins, full nonzero bridge/kinematics, raw-first failures and independent
receipt regeneration. Camera tests use CPU sensor/rectifier delegation fakes
and analytic projection; they are not optical or native GL validation. This
guide specifies the opt-in protocol; the independently accepted corrected source result is recorded below, followed by the independently accepted automatic-main replication.


## Completed corrected source gate: 4/4

[Official source run 43005087003](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43005087003) independently passes **4/4 corrected-world repeatability** under `stage7-mdv3-world-frame-v1` / `CANDIDATE_BOTH_UNSORTED_WORLD_FRAME_OFFICIAL_MDV3`. PR #29 merged as `a5ef72ed3f492857eadd4b1198dbba381312aa80` from exact source `df0f8803f6611e384d3752350fbffe007d16e7bd` after all nine current checks, completed Codex review with no findings/no open threads, fresh independent eight-file review and 342 local tests without skips. [Evidence acceptance comment](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/29#issuecomment-6793815647) records the accepted source cohort. Runner SHA256 is `cd57c4d407e96459921ca61c78eb81ef55851cd4fafa92ca917bbc7f494a3e38`.

Root and a fresh independent evidence reviewer checked all **five API archives, 25 members**, safe paths/no symlinks, all raw case comparisons and the final aggregate exactly. The cohort contains **eight fresh UUIDs/nonces, 96 actual parent inferences and 96 completed rows, forming 48 exact repeat pairs**. Both native process statuses are 0 in every case; the two PIDs are distinct within each same-runner case. There is no incomplete episode or first mismatch. Actual ORT is **1.31.1, CPUExecutionProvider, basic optimization (1), noninjected**. No hardware-equivalence claim follows from those runtime fields.

| Seed | Native S scene | Actual inferences / completed rows | Exact paired rows | First mismatch | Max virtual lateral deviation (m) | Intrusions |
|---|---|---:|---:|---|---:|---:|
| 20261109 | `s_curve_left_right` | 24 / 24 | 12 / 12 | none | 0.09070645030432445 | 0 |
| 20261109 | `s_curve_right_left` | 24 / 24 | 12 / 12 | none | 0.08693032726170458 | 0 |
| 20261110 | `s_curve_left_right` | 24 / 24 | 12 / 12 | none | 0.0906948823748337 | 0 |
| 20261110 | `s_curve_right_left` | 24 / 24 | 12 / 12 | none | 0.08677493402991843 | 0 |

Within each corrected pair, actual source Road/Wide RGB, warped RGB, I420 feed, all four raw action values/bytes/SHA, parent model action, aggregate and three named states, capture-entry/Panda counts, applied-action bridge and post-world pose/time match exactly. The applied curvature is precisely the negative of the unchanged parent model curvature; acceleration is unchanged. Every capture uses two ticks. The original public camera/episode loop, ego visibility, core source bindings, official model/spec and legacy data remain unchanged. No GPU queries/extracts or RGB retention observer were used.

### Offline initial-observation preservation: 32/32

All **32/32** retained first-step comparisons with the two legacy base cohorts (42979680883 and 42981493726) preserve matching initial-condition controls, source/warped RGB, actual I420, raw four outputs, parent-converted model action and aggregate/named recurrent state. The comparison reads existing raw records: **zero new inference calls and no frame replay**. Only applied curvature is negated at the bridge, with unchanged acceleration; post-action world poses therefore intentionally differ from legacy. This preservation result is limited to the identical initial observation. It does not claim later legacy/corrected images or trajectories remain identical after their world actions diverge.

### Unscored short virtual tracking observations

All eight lane-truth summaries exactly regenerate from their completed frame rows. Maximum virtual lateral deviations range **0.08677493402991843–0.09070645030432445 m**, with zero intrusion in all eight trials over **0.6 s / nominal 4.8 m** per process. Each trial has 12 distinct I420/image-state/feature-state hashes and the expected single zero-desire state hash. These are unscored observations in four short initial S-curve cases, not evidence of model quality, causal responsibility for all earlier error, full-S traversal, ramp/merge behavior or long-horizon performance. The strict gate is repeatability of the corrected applied-action contract.

### Measured audit and capture wall-time scopes

| Stored scope across 96 steps | Observed min–max | Sum |
|---|---:|---:|
| Additional named-state/action-receipt audit | 6.525147–14.730739 ms | 0.883356419 s |
| Additional warped-image hash audit | 0.440389–0.873498 ms | 0.058212926 s |
| Bridge validation/rotation/receipt preparation after parent step | 0.019675–0.390388 ms | 0.003825002 s |
| Whole delegated capture | 5.390421300–10.123913378 s | 661.821885053 s |

The bridge timer starts after the parent inference returns and covers its named validation/rotation/receipt-preparation interval; it does not measure complete inference, capture or all adapter overhead. The other extra audit timers also cover their named blocks only. Whole capture includes rendering/acquisition and is not pure instrumentation overhead. Sums span independent processes; no universal overhead or real-time performance claim follows.

### Source archive ledger

Every archive below belongs to run **43005087003** at exact source **`df0f8803f6611e384d3752350fbffe007d16e7bd`**. Original ZIPs, API metadata, combined/extracted raw JSON, `totals.json`, `verified_archives.json`, `recomputed.json` and `revalidation.log` remain under `output/stage7-remote-evidence/run-43005087003/`; metadata is `output/stage7-remote-evidence/artifacts-43005087003.json`. No weights are retained in artifacts.

| Artifact ID | ZIP bytes | ZIP SHA256 |
|---|---:|---|
| 13849345272 | 2141 | `d5f6f7341ae83f8424edef3399c0ff13b1d61743b1b1c7ea26a4fc2be8f130ff` |
| 13848745561 | 42649 | `4084e19017bd290b1d2d7545569c568d9f0752be1547602bf001906c181c2896` |
| 13848651289 | 42457 | `5e35d2f6ba214ad3b93c7165bfa698333fa8f67b0b8dfb6aac8c4616cab4db9b` |
| 13847992921 | 42517 | `75c591419940caf078fd938f59566fb02587cb18bd097912425f8ad16ea883a3` |
| 13847728676 | 42457 | `f4e7e1e2cf264549600138900dadcd501bb2dd1594d636ad37c1305850db3ecb` |

### Separate automatic-main replication and next gate

The predeclared automatic merged-main repeat **43006858419** at merge `a5ef72ed3f492857eadd4b1198dbba381312aa80` has completed 5/5 jobs. Root and a fresh independent reviewer verified its raw 4/4 comparison, artifacts and cross-cohort data. It is independently accepted as a separate main cohort. Do not rerun either completed cohort merely to rediscover its recorded result. Source and main identities, counts and acceptance states remain separate.

The first corrected source/main protocol remains a separate short gate. The distinct camera-fraction .28/native-ramp/160-step expansion now independently passes12/12 in run43012480495 and PR #31 is merged; its [separate guide](STAGE7_MDV3_WORLD_FRAME_EXPANSION.md) records actual execution and tracking limits. Legacy 12/12 expansion remains legacy; historical original-renderer **0/4 FAIL** remains unchanged. Source 4/4 does not adopt a renderer default, establish global render/photometric or physical-optical equivalence, rank models, prove full-S traversal or complete Stage 7.


## Independently accepted automatic-main replication: 4/4

Automatic merged-main [run 43006858419](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43006858419), at merge `a5ef72ed3f492857eadd4b1198dbba381312aa80`, completed **5/5 jobs**; main unit run **43006858385** passed separately. Root verified all five API ZIP SHA256s/sizes/safe paths, 25 members, every raw case and final regeneration exactly. Its observed raw corrected gate is **4/4** with eight new UUIDs/nonces, 96 actual inferences/completed rows and 48 exact within-cohort paired rows. **Fresh independent main-evidence review is clear, including all five archives, four raw cases/final aggregate, first-observation controls, truth/timing and cross-cohort comparisons.**

The runner source SHA256 remains `cd57c4d407e96459921ca61c78eb81ef55851cd4fafa92ca917bbc7f494a3e38`, byte-identical to the accepted feature source. All native statuses are 0, each same-runner case has two distinct PIDs and actual runtime remains ORT 1.31.1 CPUExecutionProvider/basic/noninjected. All required image/feed/action/state/bridge/pose/count fields exactly repeat within main; no mismatch or incomplete step is observed.

| Seed | Native S scene | Actual inferences / completed rows | Exact paired rows | First mismatch | Max virtual lateral deviation (m) | Intrusions |
|---|---|---:|---:|---|---:|---:|
| 20261109 | `s_curve_left_right` | 24 / 24 | 12 / 12 | none | 0.09070645030432445 | 0 |
| 20261109 | `s_curve_right_left` | 24 / 24 | 12 / 12 | none | 0.08693032726170458 | 0 |
| 20261110 | `s_curve_left_right` | 24 / 24 | 12 / 12 | none | 0.0906948823748337 | 0 |
| 20261110 | `s_curve_right_left` | 24 / 24 | 12 / 12 | none | 0.08677493402991843 | 0 |

All eight main unscored truth summaries match the corresponding source summaries, including zero intrusion and the same 0.08677493402991843–0.09070645030432445 m maximum-deviation range over 0.6 s / nominal 4.8 m. Main also has **32/32 offline first-observation preservation** comparisons with the two legacy base cohorts, without extra inference or replay. These short observations retain the source limits and establish no new model-quality/full-S claim.

| Main stored wall-time scope across 96 steps | Observed min–max | Sum |
|---|---:|---:|
| Additional named-state/action-receipt audit | 6.702548–15.963714 ms | 0.768153976 s |
| Additional warped-image hash audit | 0.439404–0.528137 ms | 0.047782354 s |
| Bridge validation/rotation/receipt preparation after parent step | 0.021400–0.396610 ms | 0.004238950 s |
| Whole delegated capture | 5.230848001–9.306887024 s | 610.988510643 s |

The same timing boundaries apply as for source. The bridge interval excludes parent inference/capture and is not all adapter overhead; whole capture is not pure audit overhead or a real-time benchmark. Source timing ranges are not substituted for these separately measured main values.

### Separate main archive ledger

These archives belong to run **43006858419** at merge **`a5ef72ed3f492857eadd4b1198dbba381312aa80`**. Root-verified raw evidence, `totals.json`, `verified_archives.json`, `recomputed.json` and `revalidation.log` remain under `output/stage7-remote-evidence/run-43006858419/`; API metadata is `output/stage7-remote-evidence/artifacts-43006858419.json`. Fresh independent review of this separate main cohort is **clear**.

| Artifact ID | ZIP bytes | ZIP SHA256 |
|---|---:|---|
| 13849282831 | 42505 | `eba5f5b832ca05bae422bb24606623f9e0b42538f0eef88c812f84a6a88aacf9` |
| 13849211943 | 42486 | `400ab415a036e2fbf2e5bbf2258635f7f1993037137394633ce652dbd7bd27ce` |
| 13849053217 | 42461 | `36cc6fcbcdec12a07a8d54683949db70b1adff632d875c76b755bd351c9f77d7` |
| 13848822856 | 42563 | `ed7243af5e17b099a12f6a04d74d452badaae4e251572e99cce674549f02ddcd` |
| 13848578525 | 2141 | `7f82cae5676ebec0c7ed70b987641f7811aaa74faa8bcb84fb0f434c4ce1dede` |

### Existing-data source/main all-pairs comparison

The two corrected cohorts together contain **16 unique UUIDs/nonces and 192 actual inferences/completed rows**, disjoint from the 40 prior legacy model-process identities. Their initial within-cohort gates compare **96 paired rows** total (48 source +48 main). Root additionally compared all four processes in each case: six pair combinations/case, **24 pair comparisons and 288 exact paired-row checks**. All required controls, raw fields, named states, applied-action bridges and pose/count receipts match; metadata is not relabeled. This reads the same **192 existing model steps**, adding **zero inference calls**, not 288 new model executions.

Evidence is `output/stage7-remote-evidence/world-frame-two-cohort-cross-comparison.json`. Its bounded existing-data equality does not establish cross-hardware equivalence, renderer-wide semantics, physical optics or model quality. Both corrected cohorts and their all-pairs comparison are independently clear. Results documentation subsequently merged as PR #30. The separate corrected expansion is now independently accepted12/12 and PR #31 merged. Historical original 0/4, legacy-only verdicts and default non-adoption remain unchanged.


## Prerequisites recorded before corrected expansion

Results-documentation PR #30 merged as
`5e42eff117218725e5e211ac63a98eb761789be6`, from reviewed docs source
`f1327940faac9f3c1e6c5b09b33eca8c71416a8e` after four successful checks,
completed current-HEAD Codex without findings/no open threads and fresh
nine-document review. Main unit43010693730 passed. Both separately accepted
corrected4/4 cohorts/allTEN archives and results-doc merge now satisfy the
prospective expansion prerequisites. The [separate expansion guide](STAGE7_MDV3_WORLD_FRAME_EXPANSION.md)
registers camera.28, actual native r/R ramps and160-step prefixes. Source-only
implementation has361 passing local tests without skips and clear independent
source/workflow reviews. PR #31 subsequently merged as
`cb1e7bfe698fe3bc3df9540eeb7dc2557e671300`; run43012480495 independently
passes12/12 with24 fresh processes/1472 actual calls and rows/736 pairs, all13
archives and exact raw aggregate clear. All eight longer processes visit2/3
route lanes with5.95397990659991–7.634517723985033m maximum lateral deviation,
not full-S or sustained tracking. Generic bare-policy consumers and input-color
source differences remain [separate integration limits](STAGE7_INTEGRATION_VERIFICATION.md#generic-live-action-consumers-remain-legacy). All original/
legacy/corrected short gates and scientific limitations above stay separate.
