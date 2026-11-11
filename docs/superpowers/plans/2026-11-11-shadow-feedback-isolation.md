# Shadow atlas feedback isolation implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Independent completed-result documentation is delegated separately with superpowers:dispatching-parallel-agents.

**Goal:** Separate the observed shadow-pass atlas read/write binding hazard from the confirmed sampler-type mismatch, without promoting either intervention as a repair.

**Architecture:** Extend only the opt-in sampler diagnostic helper with four new feedback experiment modes; reuse the unchanged `native_pixel_clock` API directly. A shadow-camera initial-state guard supplies `use_pssm=False` and a non-depth placeholder atlas only to the shadow cameras, preserving inherited shaders/geometry and RGB sampling. Four factorial conditions each have two OFF native repeats plus one terminal-only ON observer process per scene: 48 native processes total.

**Tech Stack:** MetaDrive 0.4.3, Panda3D 1.10.13, ctypes OpenGL queries, Xvfb/Python3.11, GitHub Actions.

**Spec:** Original Stage7 instructions; `docs/STAGE7_CONTINUATION.md`; local `output/stage7-remote-evidence/shadow-feedback-terminal-probe.json`; [OpenGL4.6 §9.3.1 pp325–326](https://registry.khronos.org/OpenGL/specs/gl/glspec46.core.pdf).

## Global constraints

- Keep original Road-first sequential capture, PSSM.update, Chase, two ticks/pair, ten full primary frames, warmup2, +2m positive controls.
- Source964×604, model512×256, actual uint8 I420(2,6,128,256); no image correction/replay, ONNX/model weights, scoring or real vehicles.
- No publication/environment setup changes. No original `NativeWorldCamera`, capture helper, task order, shader source, extra update, lens or model state/action changes.
- Official assets size134074203 and SHA256 `4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9`.
- A post-region/controlled-state observation is not per-primitive tracing or proof that a fetch executed. No unique-cause or repaired-gate claim from state bindings/static equality.
- Cache-only experiment failed strict matching; official MD-V3 remains prior0/4 PASS (FAIL). Do not launch official model retest yet.

## Evidence and proposed bounded guard

The local terminal-only unmodified shadow-region probe yielded four observations:
drawFBO1; depth attachment GL_TEXTURE id1 level0; active PSSMShadowAtlas sampler2D bound id1; use_pssm1; zero GL errors. Both shadow camera initial RenderStates were empty. This identifies a potential read/write feedback binding. Shader PCF reads neighboring texels; inspect actual source before describing execution/geometry implications.

For the guard, require both original shadow camera initial states empty before any mutation. Create a 1×1 white RGBA8 texture with linear filtering; compose only high-priority shader inputs `use_pssm=False`, `PSSMShadowAtlas=placeholder` into each camera's initial state. Do not assign/disable a shader or alter any camera node transform/lens/mask. Reject unexpected states atomically; roll back on setup errors. The guard changes only shadow-pass shader inputs; RGB keeps original atlas/use_pssm. This must be measured, not assumed.

## Review focus

- Existing `original` / `raw_linear` diagnostic modes and old OFF/ON receipt schema remain backward compatible.
- Guard must not leak into RGB or replace inherited geometry/alpha shader; unknown/preexisting camera states fail before mutation.
- FBO texture/renderbuffer namespaces and mip levels matter; matching numeric IDs alone do not prove aliasing.
- OFF installs no observers/libGL query interface; ON only during terminal +2m control after all primary pairs, removed on every exit. No texture pixel extraction or later renders.
- Two OFF processes establish repeatability; one ON process supplies state evidence, not a second ON repeat. Latin-square condition order and execution ledger prevent always running the combined condition last.

### Task 1: Guard and terminal binding observer

**Files:** Modify `scripts/native_shadow_sampler_probe.py`; create `scripts/native_shadow_feedback_probe.py`; create focused tests. Do not modify `scripts/native_raw_pixel_clock.py` or original provider/model/capture modules.

**Interfaces:** Four extra configure modes `feedback_baseline`, `feedback_linear`, `feedback_shadow_guard`, `feedback_both`. `configure_sampler(engine, mode)` delegates bounded guard setup and sets a private experiment marker for these modes only. Existing `terminal_sampler_probe(engine, enabled=...)` dispatches to the new observer only for that marker; original modes retain existing behavior/schema. New helper exposes guard setup and terminal context APIs, plus pure binding classification/validation helpers.

- [x] Write/run failing tests before implementation: atomic empty-state guard, only two inputs/inherited shader preserved, unexpected-state rollback, framebuffer texture ID/type/level checks, true OFF, observer restoration and wrong RGB/shadow bindings rejected.
- [x] Implement and run targeted tests. ON observes a temporary zero-geometry inherited-state node restricted to RGB|Shadow, with display-region wrappers identifying road/wide/shadow0/shadow1 on the draw thread. Record actual atlas and placeholder IDs, active uniform sampler/type/value, effective compare/filter state, FBO depth/color attachment type/name/level, GL errors, driver and query time. Expect four shadow + four RGB observations per process; allow no per-primitive claim.
- [x] Preserve existing sampler tests; optional actual Panda state-contract tests must run in native CI when Panda is installed. Parent runs real GPU smoke after implementation.

### Task 2: Factorial independent matrix and CI

**Files:** Create `scripts/native_shadow_feedback_matrix.py`, `tests/test_native_shadow_feedback_matrix.py`, `.github/workflows/stage7-shadow-feedback.yml`, `docs/STAGE7_SHADOW_FEEDBACK.md`. Optional extraction of shared raw-clock validation in existing sampler comparator is allowed; no other existing source edits.

**Interfaces:** `condition_order(seed,scene)`, `launch_trial(...)`, native trial wrapper calling `native_pixel_clock(...)`, strict trial/case/aggregate validators and CLI. Conditions baseline/linear/shadow_guard/both; each runs OFF0, OFF1, ON0. Four scene/seed cases use cyclic Latin-square orders so every condition runs first once. Each case ledger has12 native processes; cohort48 UUIDs and12 same-runner PIDs/case.

- [x] Write/run failing fixture tests for all configurations/probes, real mismatch reporting, process reuse, stale summaries, execution order, clock/source/task/pose controls, and Xvfb0/5 fresh validated receipt contract (other statuses preserved).
- [x] Implement native child and parent case launcher with fresh outputs, logs and execution ledger. OFF comparisons are exact source/warped/I420 SHA; OFF0/ON0 comparisons are separately labeled temporal/process observations. Source flags unique cause/original MD-V3 gate/model scoring always false.
- [x] Workflow pins assets and MetaDrive, runs four native jobs plus independent aggregate, retains all raw JSON/logs with hidden files and safe evidence scope. Add existing-helper source paths so compatibility regressions remain active.
- [x] Parent runs full tests, local real smoke, fresh read-only whole-branch review, exact-HEAD CI/review, all five artifact API hashes/sizes and exact raw reaggregation before gated merge. Preserve cancellations/failures. Document actual results/limits; promote no default fix without proof.


## Completed source result (2026-11-11)

PR #21 merged as `96069779c85a691a81d119f27cafe39160c70cfa` from source
`ce1015973fc35332cc5a217ea07adfa21e7bfdcc` after all 14 checks, current-SHA
Codex review without findings/no open threads, clear source/docs reviews and
281 local tests without skips. Feedback run 42957706605 and shared-helper
sampler run 42957706445 each completed 5/5 jobs; all ten API archive
SHA/size/safe paths and exact four-case/final reaggregations were checked.
Feedback: 48 UUIDs, 12 same-runner PIDs per case, 128 GPU rows. Sampler:
32 UUIDs, eight PIDs per case, 64 GPU rows.

Implementation and evidence collection completed; a repair did not. Feedback
OFF I420 matched 36/40 baseline, 36/40 linear, 37/40 shadow_guard and 33/40
both; complete static cases were 3/4, 2/4, 3/4 and 2/4. All intended terminal
binding classes were observed, with zero pre/post GL errors in 128 rows;
actual CI RGB samples/buffers were 8/1 and shadow 0/0. A fresh-cache local
combined OFF pair also failed I420 7/10, and a separate edited-gradient local
prototype failed 6/10. These are negative results, not unique-cause proof.
Full rates, firsts, order confounds, cross-condition comparisons, local labels,
query limits and all ten archive digests/byte sizes are in
[the completed feedback guide](../../STAGE7_SHADOW_FEEDBACK.md).

No official weights or ONNX inference were used; original official MD-V3
remains prior 0/4 PASS (FAIL), defaults remain unchanged, and Stage 7 remains
incomplete. Automatic main feedback 42961355528 completed 5/5 jobs and all
five API archive SHA/size/safe paths plus exact four-case/final summaries
revalidated: 48 UUIDs, 12 PIDs per case and 128 GPU rows. Main feedback OFF
I420 baseline/linear/guard/both matched 36/40, 36/40, 35/40 and 32/40;
complete cases 3/4, 2/4, 3/4 and 2/4. Full source/warp rates, per-case firsts,
OFF/ON and cross-condition comparisons and all five archive hashes/byte sizes
are in the feedback guide. Separate main sampler 42961355395 completed 5/5
jobs; all five
archive SHA/size/safe paths and exact four-case/final summaries revalidated,
with 32 UUIDs, eight PIDs per case and 64 GPU rows. Original OFF source
Road/Wide matched 27/30 of 40, warp 27/35, I420 23/40 (17/32 post-warmup,
0/4 complete cases); other arms every field 40/40. Full archive ledger and
rates are in the feedback guide. Unit run 42961355303 passed.
Both automatic cohorts are complete; preserve their failures without manual repeats. Per-camera terrain view-data lifetime
and LOD state remain a next source-review hypothesis, not a validated result.

The separate local llvmpipe worker ABBA pilot at
`output/llvmpipe-worker-pilot/` is complete: four successful distinct original
native processes, no observer/shader/model, `LP_NUM_THREADS` unset versus 0,
one initially empty shared cache per arm then populated reuse. Both I420
comparisons matched 8/10, first difference 2, differences 2 and 7. Default
source Road/Wide matched 8/6 and requested-zero 8/8; warped Road/Wide matched
8/10 in both arms. Whole-process ABBA wall times were 65.803, 112.260,
111.605 and 61.028 s, not pure overhead. Requested zero is not a complete fix;
no actual worker trace, necessary-parallelism or unique-cause claim follows.
The plan, execution/cache SHA receipts and comparisons retain this negative
single-case fixed-order result; no CI expansion is needed to falsify that
complete-fix candidate. Workspace-only apitrace v2 ABBA capture is complete:
four valid native JSON/zero statuses/distinct UUIDs and PIDs, exact OFF I420
8/10 (first 2, differences 2 and 7) and ON 7/10 (first 7, differences 7, 9, 10).
All four JSON/logs, native/cache SHA receipts and complete traces are retained
in `output/apitrace-draw-pilot-v2/`; the feedback guide records both trace byte
sizes/hashes. The earlier attempt's OFF0 was
valid but ON0 retained native ERROR/partial trace, not a complete matrix.
V2 initializes the same default Python SIGINT handler in every arm. ON also
hides program-binary formats, changing driver capability as well as timing;
ABBA wall times do not establish universal overhead. Bounded trace analysis
is complete (`analysis-agent/findings.json`): 106555/106580 calls, 2901 geometry
draws/192 passes each; eight shader-source submissions and 322 ordered CPU
texture uploads match. First non-timestamp difference is used startup
p3d_TransformTable slots 0–68 at call 9027, not unused slots 69–99. All primary/control
unordered analyzed geometry/uniform/constant-vertex inputs match; 53 geometry
orders differ, without a necessary/sufficient/unique causal relation. Full GPU
textures/state are not reconstructed. Pinned Panda pointer-based state/bin
sorting motivates a bounded local intervention, not a default policy change.

The separate extra opaque-bin ABBA pilot on experimental Both is pending at
`output/opaque-bin-pilot-v3/plan.json`: `state_sorted_0 → unsorted_0 → unsorted_1 →
state_sorted_1`; opaque enum 2 versus 1 before primary frames, one fresh shared
cache per arm, original PSSM/Chase/ticks/shaders preserved and observer OFF.
These are not ordinary Both cells; generic feedback validation does not
certify the extra bin semantics or actual order. V1's in-memory tuple check
failed before writing/lost raw JSON; v2 saved schema-valid observed JSON but
retained wrapper status 1 from the tuple check. Logs/cache/failure records are
preserved in v1/v2 directories; neither is a completed matrix. V3 writes and
reloads JSON before unchanged strict wire validation; the existing-fixture
roundtrip repro passed, with no native criterion relaxed or source change.
No outcome or render-sort adoption is established. Full trace findings and limitations are in the
feedback guide. Per-camera terrain view-data lifetime/LOD remains unproven.
