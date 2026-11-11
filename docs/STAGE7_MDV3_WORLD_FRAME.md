# Official MD-V3: opt-in model-to-world action basis bridge

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
guide specifies an opt-in protocol, not a completed corrected native cohort.
