# PSSM sampler type versus effective OpenGL comparison state

This is a static native renderer experiment. It does not change benchmark
defaults, run ONNX, or establish the original moving MD-V3 repeatability gate.

## Source hypothesis

MetaDrive 0.4.3 `engine/core/pssm.py::create_pssm_buffer` sets both filters of
the depth-component PSSM atlas to `FTShadow`. Panda3D 1.10.13 maps that filter
to `GL_TEXTURE_COMPARE_MODE = GL_COMPARE_REF_TO_TEXTURE` (sampler objects or
texture parameters). MetaDrive's loaded `simplepbr.frag` instead declares
`uniform sampler2D PSSMShadowAtlas`, reads `.r` with `texture2D`, and performs
its own `step(ref_depth, depth_sample)` nine-tap PCF.

The [OpenGL core specification 4.6, §11.1.3.5, pp. 401–402](https://registry.khronos.org/OpenGL/specs/gl/glspec46.core.pdf)
states that a non-shadow sampler reading a depth texture with comparison mode
enabled has undefined lookup results. That establishes a source-level
compatibility concern, not the unique cause of the earlier pixel drift.
The base fragment string loaded with `_load_shader_str("simplepbr.frag", {})`
(no pipeline feature defines) has SHA256 pinned to
`8eef67eb4384d6a74136b8e99b4c9bf0711e51ee88db7a248cd164c7a69f9ceb`.
The receipt calls this `loaded_fragment_shader_sha256`; it is a base-source
contract check, not a hash of every compiled GL program or its feature defines.

## Independent arms

| Arm | Atlas min/mag filter | Terminal GPU observer |
| --- | --- | --- |
| `original_off` | Original `FTShadow` / `FTShadow` | OFF |
| `original_probe` | Original `FTShadow` / `FTShadow` | ON |
| `raw_linear_off` | Experimental `FTLinear` / `FTLinear` | OFF |
| `raw_linear_probe` | Experimental `FTLinear` / `FTLinear` | ON |

The linear treatment preserves the backend's linear min/mag filtering while
disabling hardware depth comparison, consistent with the shader's manual-PCF
input type. It changes renderer semantics and remains opt-in. This experiment
does not establish intended upstream visual appearance or shadow accuracy.

Each seed (20261109/20261110) and S-curve (left-right/right-left), fraction
0.12, uses two fresh processes per arm: 32 processes total. All preserve the
original Road-first `perceive()` path, two task ticks per pair, PSSM.update,
Chase, fixed WORLD pose, ten full primary frames and two-frame secondary
warmup. Source RGB, warped RGB and actual uint8 I420 SHA sequences are compared
without tolerance; pose movement by +2 m must change both cameras' buffers.

## Terminal observer and its limits

All ten primary image pairs are captured before installing any observer.
Only the final moved-pose positive control is instrumented. No renders follow
it. OFF does not load libGL through the diagnostic query module and installs no
callback or observer node. Native rendering still uses OpenGL normally.

A first local pilot queried the GL program after each display region. Its
last program sometimes had no PSSM atlas uniform, so those observations were
inconclusive. The experiment therefore installs a temporary **zero-geometry
CallbackNode** inheriting the native scene's PBR shader state, restricted to
the RGB camera mask and drawn in a late fixed bin. Panda loads its render
state before calling its draw callback. Display-region wrappers identify the
road/wide camera on the same draw thread. All nodes/callbacks and the active
texture unit are restored even on failure; existing callbacks are rejected.

This is a **controlled inherited-state binding observation**, not a trace of
every original geometry draw. The probe records the active sampler uniform
type, its unit, actual bound texture, expected PSSM atlas native ID, depth
internal format, `use_pssm`, effective sampler-object comparison/filter state
(texture fallback when no sampler object exists), GL errors and driver.
Residual programs, different textures, disabled shadow uniforms or GL errors
cannot certify the binding. Two valid observations per camera are required.

Query CPU time is retained per observation and summed. The terminal diagnostic
wall time also includes positive-control rendering, libGL loading, observer
setup and teardown; it is not a pure GPU-query overhead measurement. Primary
pair clock/wall receipts and OFF/ON image comparisons remain separate.
Independent process variation prevents interpreting their difference as an
unbiased estimate of instrumentation overhead.

## Execution and evidence gates

```bash
python -m unittest discover -s tests -p '*shadow_sampler*.py' -v
python -m scripts.run_native_shadow_sampler_trial --seed 20261109 \
  --scene s_curve_left_right --arm original_off --out output/fresh-original.json
python -m scripts.compare_native_shadow_sampler --mode aggregate \
  --root output/verified-shadow-sampler --out output/recomputed-sampler.json
```

The Actions workflow verifies official asset size/SHA and launches each trial
in a fresh Xvfb/Python process. Xvfb status 5 is accepted only with a newly
generated, fully validated receipt. Reused same-runner PIDs, reused cohort
UUIDs, missing trials, mislabeled treatments, incompatible GPU observations
and changed uploaded summaries fail the evidence gate. A verified experiment
may contain image mismatches; job success is not renderer determinism.

Before merging, verify the exact PR HEAD checks/review, download every raw
artifact, verify archive size/SHA and safe member paths, and regenerate the
four case summaries and final aggregate exactly. Record actual rates and
first differences, including failed/superseded pilots. A static improvement
alone never licenses a default switch or an original ONNX 4/4 PASS claim.


## Verified source result (2026-11-11)

PR [#18](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/18)
merged as `177103b1b5bc47586d3366d542299f7cf4f28675` after exact source HEAD
`3adc288f244e001a22ce69ce73f0fa7d514ce98a` passed all nine checks, current-SHA
Codex review without findings, independent read-only code review and no open
review threads. Local full suite: **248 passed, no skips**. Review exposed
and fixed raw-clock trust and incomplete/error-bearing GL-binding receipts;
8 clock and 6 binding mutation regressions first failed, then passed.

[Native Actions run 42942700897](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42942700897)
completed **5/5 jobs**. All five ZIP API SHA256/size values and safe member paths
were verified. All four case summaries and the final aggregate were regenerated
exactly, with **32 unique UUIDs and eight distinct same-runner PIDs per case**.
Raw artifact IDs: `13822815059`, `13822360732`, `13822245765`, `13821533979`;
independent aggregate: `13821339900`.
[Merge evidence comment](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/18#issuecomment-6785023215).

| Arm | Source Road /40 | Source Wide /40 | Warped Road /40 | Warped Wide /40 | I420 /40 | I420 post-warmup /32 | Complete static cases /4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `original_off` | 27 | 27 | 27 | 33 | 22 | 18 | 0 |
| `original_probe` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |
| `raw_linear_off` | 38 | 40 | 38 | 40 | 38 | 31 | 3 |
| `raw_linear_probe` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |

The linear OFF exception is seed 20261109 / left-right: Road source and warp,
and I420, first differ at **step 2**. I420 differs at **steps 2 and 7**, matching
8/10 full frames and 7/8 post-warmup frames. It therefore fails strict static
all-field repeatability. Original OFF I420 first differs at step 2 in every
case; source Road first differs at 2 in all cases, and source Wide first
steps are 3, 4, 1, 4 in seed/scene order below.

| Seed | Scene | original_off I420 /10 | raw_linear_off I420 /10 | raw_linear_off first Road/I420 |
| --- | --- | --- | --- | --- |
| 20261109 | s_curve_left_right | 6 | 8 | 2 |
| 20261109 | s_curve_right_left | 5 | 10 | none |
| 20261110 | s_curve_left_right | 7 | 10 | none |
| 20261110 | s_curve_right_left | 4 | 10 | none |

These are cross-process SHA comparisons. Exact cross-process changed-pixel
coordinates/channel deltas are not retained in this experiment; within-process
pixel examples do not establish cross-process locations.

### GPU state, timing and runtime

All **64** controlled inherited-state observations validated the real atlas
binding, `GL_DEPTH_COMPONENT32F`, `GL_SAMPLER_2D`, `use_pssm=1` and zero recorded
GL errors. Original probe: **32/32** comparison-enabled observations
(`0x884e`); linear probe: **32/32** comparison-disabled observations (`GL_NONE`).
Both kept min/mag `GL_LINEAR`. This proves the configuration-to-binding change,
not that this defect uniquely caused earlier drift or that every primitive was
traced. The temporary observer itself loads the inherited scene state.

CI: Ubuntu 26.04, Python 3.11.18, MetaDrive 0.4.3, Panda3D 1.10.13,
NumPy 2.4.6, OpenCV 5.0.0.93, Mesa 26.0.8-1ubuntu0.3,
llvmpipe LLVM 21.1.8 (256 bits), GL 4.5 compatibility profile. Package versions
came from the completed job log; GPU version strings came from the receipts.
Local: Python 3.11.17, MetaDrive 0.4.3, Panda3D 1.10.13, NumPy 1.26.4,
OpenCV 4.11.0.86, Mesa 25.0.7-2+deb13u1 / LLVM 19.1.7. These differences are
facts about the runtimes, not an isolated cause.

| Arm | Four-query CPU total per process (ms, min–max) | Terminal diagnostic wall (s, min–max) | Primary pair real-time median (s) |
| --- | --- | --- | --- |
| `original_off` | 0.000–0.000 | 5.232–7.623 | 6.263 |
| `original_probe` | 0.837–1.041 | 5.175–7.627 | 6.174 |
| `raw_linear_off` | 0.000–0.000 | 5.250–7.697 | 6.309 |
| `raw_linear_probe` | 0.813–0.971 | 5.263–7.713 | 6.200 |

The observer runs after all primary frames. Thus matching ON primary sequences
cannot establish a retroactive repair or an instrumentation timing benefit.
Primary OFF/ON comparisons across eight index-matched pairs (80 frames per
sampler mode) yielded:

| Sampler | Source Road/Wide /80 | Warped Road/Wide /80 | I420 /80 |
| --- | --- | --- | --- |
| original | 67/67 | 67/73 | 62 |
| raw_linear | 62/54 | 62/60 | 48 |

Original versus linear comparisons matched **0/80** for every source/warped/I420
field, both with observer OFF and ON. The sampler treatment changes image
semantics and is not a bit-equivalent renderer substitution.

All arms ran in a fixed order on each runner. In particular, the second pair
(`original_probe`) used the same primary capture/configuration as the first
pair (`original_off`), yet matched 40/40. Process execution order, persistent
shader/cache state and initialization history are therefore unresolved
confounds. No pair-level image equality proves that the later observer or the
sampler correction fixed earlier primary frames.

### Local and superseded evidence

Four final-format local processes, one per arm, passed all receipt checks.
Original OFF/ON primary source Road/Wide and I420 were 10/10; linear OFF/ON
source Road 10/10, source Wide **6/10**, I420 10/10. A single pair per sampler
mode is a pilot, not the four-scene independent CI matrix. Local terminal query
CPU totals were about 1.178 ms original and 1.917 ms linear. Original versus
linear primary images/I420 differed in all ten frames.

Earlier pilots remain in ignored output: one used a nonexistent MetaDrive
`__version__` attribute (fixed to `metadrive.version.VERSION`); the original
post-display-region query sometimes saw a non-PSSM last program and was
inconclusive. Revised zero-geometry observer receipts succeeded. Two standalone
exploratory GL probes also preceded the production-format trials; their
post-region observations are not counted as final evidence.

Superseded Actions **42942288117** was cancelled after validator strengthening.
Its four ZIP digests and **seven completed original-OFF partial receipts** were
verified with the final validator. It has no complete 32-process aggregate and
must never be counted as a passed matrix.

### Additional shared-source regressions

All relevant workflow/capture/shared-validator inputs are identical between
`850172b6b276960dcba5843bbdfe0a4320649670` and final source `3adc288`.

| Run | Result | Actual independent processes | Independent revalidation |
| --- | --- | --- | --- |
| [42942287909](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42942287909) | 4/4 jobs | 16 | Four pixel-clock summaries exactly reproduced; no sampler diagnostic on default path |
| [42942287958](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42942287958) | 5/5 jobs | 32 | All ZIPs verified; full PSSM aggregate exactly reproduced |
| [42942287899](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42942287899) | 5/5 jobs | 32 | All ZIPs verified; full capture-order aggregate exactly reproduced |

PSSM regression original sequential I420 matched **21/40**, each other arm
40/40. Capture-order regression original I420 matched **23/40**, each other
arm 40/40. These 80 processes are additional regressions; no ONNX was run.

### Verified archive ledger

IDs, complete SHA256 digests and byte sizes below were compared to the GitHub
artifact API metadata before extraction. The cancelled row group is partial
historical evidence, not a full cohort.

| Run | Artifact ID | SHA256 | Bytes |
| --- | --- | --- | --- |
| 42942700897 | 13822815059 | `b94e5c98ee8b90a26887baa3021e7fcc379f43f0b90217e926a6f9154746c10e` | 41936 |
| 42942700897 | 13822360732 | `e83ef7b940c4c20c49782a6b4630cfd9eb4fa7278cd3d2725d91dae2b7f8e5d2` | 40992 |
| 42942700897 | 13822245765 | `d9955cd0bb148c5da71f4dbfd2e19dc380d8482380420f9b41c597f2586ca50f` | 44673 |
| 42942700897 | 13821533979 | `012e4930ace205a093fced7f4eefe15685f8042bc8df776bf47ef23ac8122842` | 40942 |
| 42942700897 | 13821339900 | `0a99a03ea58e5ec6036966cd6ed0e38e40db3aa21117402b955a45ed6867e522` | 8259 |
| 42942287909 | 13821915189 | `4de8722a6461fc5df902e8bc6fe7f719c75b0080a501b5c0368de775ef3f8f1f` | 15624 |
| 42942287909 | 13821825402 | `40b1a4b6c5d86b4be2fb69eb7b9dbdd480518915ba33c624ce49db78859bdec2` | 17614 |
| 42942287909 | 13821735884 | `052559ffab45714941d867e16b69ae2b290967ab0427b0587e71181c9931529f` | 17483 |
| 42942287909 | 13821551714 | `60c6e9f4ecdcadd1e99e42d4bfb86e4a469ebd9b68d3dfa54334202911884259` | 20672 |
| 42942287958 | 13821996279 | `d5cfedd003ec9b6a140cfe44632c7d7091e5799516b949b5998a8a7057ad4a8d` | 33494 |
| 42942287958 | 13821641470 | `3eef5fa926db7491feadd632ff29fe2bed71baa6416f7d4e52bb15ce7f5b0503` | 35480 |
| 42942287958 | 13821557997 | `e91c9fbcc49756c8b7c38657a30d4c36ed49a4fb4424bb7aaf4fc8356703087f` | 1983 |
| 42942287958 | 13820904001 | `88d33ca0af184d16eeb2587648447111259c10516b0135f4559493d201a70a8c` | 29214 |
| 42942287958 | 13820584312 | `7a981b55b43c1c6f178b9af8b77d85b71450c20542f455c8cb305f41c8317aad` | 33046 |
| 42942287899 | 13822410042 | `28c540656e3513d5d26c92d6613ca6737632b23fb0a59c3057a92a1e68f35d51` | 2438 |
| 42942287899 | 13822195168 | `4cde4cc9cd6108949e74d09947a353a4570a961814de9227c6459672e2bec71b` | 37463 |
| 42942287899 | 13821921767 | `cefbff34b1e488e37e6f1ebba11fde84799f008b17892a360b847437c073c918` | 36532 |
| 42942287899 | 13821173926 | `683cfc1635ac69c8424480840284d35da8a329f3624251df61ca857180c9e6e8` | 33374 |
| 42942287899 | 13820913644 | `71c64ac1811acb5ae0ae058595b0ebd6e232bb948aae960a3d419004862862a6` | 35146 |
| 42942288117 | 13821790562 | `a68e2319ae42a5db3598b20d7a19d88de0d6d27f0b5f71c9efe2c70523566d4b` | 9257 |
| 42942288117 | 13821710793 | `a1f4b327f2be8d6457381b762018bcd33e3c2bfcd22c99007bba74cbab89c8f9` | 9513 |
| 42942288117 | 13821556671 | `ebaaaaaf336665da75bf1337c54fe4528f6265e75c6c2c1a1d668f50d2244195` | 4754 |
| 42942288117 | 13820997747 | `5bb4c36ff95440aa0f611b35ef493bdd89bbfa4b3cb566f25755288bc7f4313a` | 10105 |

## Local cache-history follow-up pilot

Four additional original Road-first native processes ran in ABBA order:
`shared_0`, `isolated_0`, `isolated_1`, `shared_1`, seed 20261109 / left-right.
Only `MESA_SHADER_CACHE_DIR` changed per subprocess; no sampler treatment,
GPU observer, clock/callback change or ONNX was used. Cache inventories were
measured in the launcher outside render intervals. All native receipts and
four distinct PID/UUIDs validated.

| Pair | Source Road/Wide /10 | Warped Road/Wide /10 | I420 /10 | First source Road/Wide; I420 |
| --- | --- | --- | --- | --- |
| Shared initially empty cache, first then later process | 8/6 | 8/10 | 8 | 2/1; 2 |
| Separate initially empty caches | 10/10 | 10/10 | 10 | none |

Shared I420 mismatches were steps **2 and 7**. Each initially empty cache
went from 0 files/0 bytes to **101 files / 1,670,747 bytes**. The later shared
process began with those 101 files and ended with 101 files / 1,692,275 bytes.
Whole process wall times in execution order: **85.350, 74.887, 68.323, 66.820 s**;
these include startup, rendering, analysis and shutdown, not pure cache cost.

This reproduces source/I420 differences locally with the original renderer
and provides a discriminating cache-availability candidate. It is one scene,
one seed and one pair per condition, with fixed ABBA order. File inventories
prove cache population, not individual cache hits or a unique causal chain.
Ignored local evidence: `output/cache-order-pilot/execution_receipts.json`,
`comparisons.json`, four native receipts/logs and all three cache directories.
A balanced multi-scene cache-availability/disabled-cache CI control is the next
experiment; do not switch defaults or claim a repaired official model gate.

## Decision and next causal boundary

This is a verified sampler compatibility defect and an incomplete renderer
intervention. Do not promote raw-linear sampling as a complete repeatability
repair: strict source/warp/I420 matching still failed with its observer OFF,
and original-to-linear image semantics changed.

**Original official MD-V3 repeatability remains the prior 0/4 PASS (FAIL).**
No new official ONNX run, recurrent-state/action comparison or expanded-scenario
gate occurred. Geometry defaults and original model camera are unchanged;
real-camera optical equivalence and driving performance remain unestablished.
Stage 7 is incomplete.

Next isolate execution/cache history with original Road-first/PSSM/Chase,
without sampler changes or in-sequence GPU observers. Compare a fresh shared
Mesa cache's first versus second process against two separate empty caches,
retain cache file/size inventories outside render intervals, alternate order,
and keep failed/non-discriminating pilots. A cache-directory change is an
experimental runtime control, not a default repair or proof of cache hits.
Only after a discriminating result should a balanced independent CI matrix
be added. Then trace the earliest projection/depth/HDR/RGB boundary with OFF
controls. A separately validated repair is required before official moving
MD-V3 2 seeds × 2 scenes × 12 steps × 2 processes and its strict 4/4 gate.
