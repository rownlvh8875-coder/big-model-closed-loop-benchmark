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
guide defines the experiment; it does not report a completed 48-process cohort.
All source claims for original MD-V3 repeatability, unique cause, model
scoring and real-vehicle testing remain false even when static frames match.


## Local source smoke before CI

The complete local suite passed **281 tests without skips**. Two real source
launcher processes with condition `both`, observer OFF, matched every source
Road/Wide, warped Road/Wide and I420 field **10/10**. Their raw receipts and
comparison are in ignored `output/shadow-feedback-local/`.

One additional production-launcher ON process passed the full native/nonce/
configuration/binding validator, with eight terminal observations: four shadow
placeholder bindings with `use_pssm=0`, and four RGB real-atlas/raw-linear
bindings with `use_pssm=1`, all recorded GL errors zero. Actual samples/buffers
were **0/0** for shadow and **4/1** for RGB HDR, despite the upstream request
for 16× MSAA. This validates the supported local state setup, not the future
four-scene result or original official MD-V3 gate.

An earlier exploratory guard pilot accidentally used a positional numeric
argument that selected Panda's vector overload, leaving the bool input at
priority zero. It was retained as
`shadow-feedback-terminal-guard-priority0-pilot.json`; explicit keyword/
ShaderInput priority fixed the setup and actual Panda CPU-contract tests pin
this behavior. Preliminary and source-API GPU probes are separate from the
three final source-launcher processes; none is an official ONNX run.
