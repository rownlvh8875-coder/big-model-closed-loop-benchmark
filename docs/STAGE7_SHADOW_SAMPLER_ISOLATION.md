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
This pilot motivated the now-complete balanced cache CI experiment in
[STAGE7_SHADER_CACHE_HISTORY.md](STAGE7_SHADER_CACHE_HISTORY.md); no default
switch or repaired official model gate followed.

## Automatic merged-main cohorts independently revalidated

The PR #18 merge push on `177103b1b5bc47586d3366d542299f7cf4f28675`
started separate cohorts; they are now complete. PR #19 documentation later
merged as `ee3ded6e71b8b2cb8c5603c1c934c1eac20d1841`. The automatic cohorts
are independent repetitions, not replacements for run 42942700897 above.
Every one of their **19** archive SHA256/size/safe-path checks passed. Native
receipts and all uploaded case/final summaries were independently reproduced.

| Run | Experiment | Jobs | Native processes | Independent result |
| --- | --- | --- | --- | --- |
| [42944861575](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42944861575) | Sampler | 5/5 | 32 | Four case summaries and aggregate exact; 32 UUIDs, eight same-runner PIDs per case |
| [42944861604](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42944861604) | Capture order/ticks | 5/5 | 32 | Four case summaries and aggregate exact; original I420 21/40, each other arm 40/40 |
| [42944861717](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42944861717) | PSSM scheduling | 5/5 | 32 | Four case summaries and aggregate exact; original sequential I420 25/40, each other arm 40/40 |
| [42944861577](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42944861577) | Raw pixel clock | 4/4 | 16 | All four summaries exact; no sampler diagnostic on default path |

The automatic sampler cohort's rates are:

| Arm | Source Road /40 | Source Wide /40 | Warped Road /40 | Warped Wide /40 | I420 /40 | I420 post-warmup /32 | Complete static cases /4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `original_off` | 31 | 32 | 31 | 35 | 26 | 20 | 0 |
| `original_probe` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |
| `raw_linear_off` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |
| `raw_linear_probe` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |

Original OFF I420 per case (20261109 left-right/right-left, then 20261110
left-right/right-left) is **6/10, 5/10, 8/10, 7/10**; first differences are
steps **2, 2, 5, 5**. Other sampler arms match every field 10/10 in each case.
All 64 controlled inherited-state observations validate the same binding
classes as the source cohort: 32 original depth-comparison enabled and 32
linear comparison disabled. The repeated linear OFF 4/4 result does not erase
the source cohort's 3/4 result or establish an original moving-model repair.
Fixed arm order and the terminal observer's position remain confounds.

Within this automatic sampler cohort, original OFF/ON comparisons matched
source Road/Wide **71/72 of 80**, warped Road/Wide **71/75 of 80**, I420
**66/80**. Linear OFF/ON matched **74/72**, **74/80** and **74/80** respectively.
Original-versus-linear still matched **0/80 in every source/warp/I420 field**
with observer OFF and ON, so the sampler changes image semantics. Retained
metrics, totals, receipts and recomputations are under
`output/stage7-remote-evidence/run-42944861575/`; the other three runs use the
same `run-<id>/` layout, including full archive ledgers. No ONNX ran.

### Automatic merged-main archive ledger

| Run | Artifact ID | SHA256 | Bytes |
| --- | --- | --- | --- |
| 42944861575 | 13823515145 | `c86654b4d0f3992cc3db2a023f05529ab1dd67a014591b4d0c20cb0d310d86a9` | 8084 |
| 42944861575 | 13823395414 | `d421b20d14ee1fccbcb6198359ebc642d8737021884169396f1842a9249e8b5d` | 42258 |
| 42944861575 | 13823112180 | `a62dbd8808790a433e37ce36fc44c075086a5f7bfee193b6e75414cbd9b613e6` | 42625 |
| 42944861575 | 13822293244 | `3ab51709133b7525bfcbcaab535ab2f9bcba249ad08181e0e727b5b9164d0696` | 41568 |
| 42944861575 | 13821799431 | `f8a240098a55a8e71a08ae43a1f6e270bb216ad6be59543d64bd372dca8ad94e` | 39444 |
| 42944861604 | 13823181345 | `d0975088b78b9cdbc3117d2f753a5daf03eb9d4225bda20b072052a1a71b790e` | 37473 |
| 42944861604 | 13822647758 | `2199281ab133696c7f32ba1588b406c88ddb344d34776d2012a9cb13257ab778` | 37248 |
| 42944861604 | 13822298402 | `1985a7b04e25617c7416e970e99dd9c6f737fd85ac67c4cd52028171a956fed2` | 2441 |
| 42944861604 | 13822199861 | `90a40ee076fdf4fb2bf99b004f4236f395cccbcf32ea5d89249814bf0202fe63` | 33492 |
| 42944861604 | 13821958999 | `b763319fa8cd72922d6e814b14f9516324ed103ce64c219393e6296ea4030c42` | 36263 |
| 42944861717 | 13822324281 | `a663dd2f684e2247d8a51338083325471a711644a1fbec1af8a103c745127d71` | 32978 |
| 42944861717 | 13822229389 | `d57347a0e2f7e1744ad05529826fcc567ead719a3a5565e57e70e381b821d86f` | 33543 |
| 42944861717 | 13822103449 | `d7377c19608ba3cce2ab156894dcb5c839ac19eb8d20abc3f9f5147eec507318` | 1930 |
| 42944861717 | 13822034431 | `ef05e635b8008a510ce1a59458ecff69a29f360396e7ebf672034344cf891da2` | 33507 |
| 42944861717 | 13821804013 | `ed623702e439992452b9c6977dd8021f17214cb034ec31bc5284c5a6b828ffef` | 29277 |
| 42944861577 | 13823095920 | `c7c479cd684d51a3be8c7faa411d78c4a421cbdcda3d12f397e1001cb3ba33d3` | 17480 |
| 42944861577 | 13822516993 | `199579b39da9b796f104f271d5c98db49c4d0d98cd98add9c8df4cbab1062da4` | 20664 |
| 42944861577 | 13822083999 | `f70ea6851b52f37d7e3ad38076576166f735b61c6aeda17a7a4c0cffaa935b35` | 17602 |
| 42944861577 | 13822063059 | `a040a205bd78c994afb283dca02bf26bc12a766d6e0bcf57d96bd00a7528834c` | 16249 |

## PR #21 shared-helper compatibility regression

PR #21 merged as `96069779c85a691a81d119f27cafe39160c70cfa` from final source
`ce1015973fc35332cc5a217ea07adfa21e7bfdcc` after all 14 checks, current-SHA
Codex review without findings, no open threads, clear independent source/docs
reviews and **281 local tests without skips**. The old sampler API/receipt
schema remained compatible. Separate sampler
[run 42957706445](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42957706445)
completed 5/5 jobs; all five archive API SHA/size/safe-path checks passed,
all four case summaries and the aggregate reproduced exactly, with 32 native
UUIDs, eight distinct same-runner PIDs per case and 64 validated GPU rows.

| Condition | Source Road /40 | Source Wide /40 | Warped Road /40 | Warped Wide /40 | I420 /40 | I420 post-warmup /32 | Complete static cases /4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `original_off` | 30 | 31 | 30 | 35 | 27 | 20 | 0 |
| `original_probe` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |
| `raw_linear_off` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |
| `raw_linear_probe` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |

| Seed | Scene | Original OFF I420 /10 | First source Road/Wide | First I420 | I420 different steps |
| --- | --- | --- | --- | --- | --- |
| 20261109 | left_right | 6 | 5/8 | 5 | 5, 7, 8, 10 |
| 20261109 | right_left | 9 | none/5 | 5 | 5 |
| 20261110 | left_right | 8 | 5/6 | 5 | 5, 7 |
| 20261110 | right_left | 4 | 2/4 | 2 | 2, 4, 5, 7, 9, 10 |

All three other arms matched every source/warp/I420 field 10/10 in every case.
The 64 terminal controlled-state observations again divide into 32 original
comparison-enabled and 32 raw-linear comparison-disabled rows. Original versus
linear still matched **0/80** for every source/warp/I420 field with observer
OFF and ON. Original OFF/ON matched source Road/Wide **70/71 of 80**, warped
**70/75**, I420 **67/80**; linear OFF/ON matched **60/54**, **60/60**, **46/80**.
Fixed arm order and terminal observation after all primary captures remain
confounds; these comparisons neither estimate unbiased overhead nor prove
retroactive repair. Retained raw/recomputed/totals/metrics evidence is under
`output/stage7-remote-evidence/run-42957706445/`.

The same source's new 48-process factorial feedback cohort, run 42957706605,
failed complete 4/4 matching in every condition. Its OFF I420 totals were
baseline 36/40, linear 36/40, shadow_guard 37/40 and both 33/40. Thus the old
sampler cohort's repeated linear 4/4 result is runtime/cohort evidence, not a
universal repair. A fresh-cache local combined OFF pair also failed I420 7/10.
See [the completed feedback guide](STAGE7_SHADOW_FEEDBACK.md) for all rates,
first differences, cross-condition changes, actual framebuffer samples,
query limits and the complete ten-archive ledger for both source cohorts.

## PR #21 automatic merged-main sampler repetition

The separate automatic main-source `9606977` sampler run **42961355395**
completed 5/5 jobs. All five API archive SHA/size/safe-path checks and exact
four-case/final regeneration passed, with **32 native UUIDs, eight distinct
same-runner PIDs per case and 64 validated GPU rows**. It is a separate cohort
from source run 42957706445, with different original OFF rates.

| Arm | Source Road /40 | Source Wide /40 | Warped Road /40 | Warped Wide /40 | I420 /40 | I420 post-warmup /32 | Complete static cases /4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `original_off` | 27 | 30 | 27 | 35 | 23 | 17 | 0 |
| `original_probe` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |
| `raw_linear_off` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |
| `raw_linear_probe` | 40 | 40 | 40 | 40 | 40 | 32 | 4 |

| Seed | Scene | Original OFF I420 /10 | First source Road/Wide | First I420 | I420 different steps |
| --- | --- | --- | --- | --- | --- |
| 20261109 | left_right | 6 | 5/8 | 5 | 5, 7, 8, 10 |
| 20261109 | right_left | 4 | 2/3 | 2 | 2, 3, 5, 7, 8, 10 |
| 20261110 | left_right | 6 | 2/1 | 2 | 2, 7, 9, 10 |
| 20261110 | right_left | 7 | 10/5 | 5 | 5, 7, 10 |


All three other arms match every field 10/10 in each case. Original OFF/ON
primary comparisons match source Road/Wide **67/70 of 80**, warped **67/75**,
I420 **63/80**; linear OFF/ON matches **74/72**, **74/80** and **74/80**.
Original-versus-linear still matches **0/80** in all source/warp/I420 fields,
with observer OFF and ON. The 64 controlled-state observations divide into
32 comparison-enabled original and 32 comparison-disabled linear rows.
Fixed order, process/cache history and terminal observer position remain
confounds; these repetitions do not establish a repair or unbiased overhead.
Retained raw/recomputed/totals/metrics evidence is under
`output/stage7-remote-evidence/run-42961355395/`. The complete five-archive
SHA256/byte ledger is in [the feedback guide](STAGE7_SHADOW_FEEDBACK.md).
Automatic feedback run 42961355528 also completed 5/5 jobs with all five
archives and the 48-process/128-GPU-row aggregate exactly revalidated. Its OFF
I420 baseline/linear/guard/both totals are 36/40, 36/40, 35/40 and 32/40;
complete cases 3/4, 2/4, 3/4 and 2/4. The feedback guide preserves full
source/warp rates, per-case firsts, comparisons, fixed-order limits and its
separate five-archive ledger. No condition is a 4/4 repeatability repair.

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

The balanced cache experiment is now complete: PR #20 merged as
`465bf0c49a585fecb8ad313cac3b29e96736b8b6`; run 42948547486 has 24 validated
native processes. Shared/isolated/disabled I420 matched 19/40, 34/40 and 32/40,
with only 0/4, 3/4 and 2/4 complete static cases. See the
[cache findings](STAGE7_SHADER_CACHE_HISTORY.md) for every source/warp rate,
case/order, archive and causal limit. Cache availability remains an
experimental control; neither isolation nor disabling repaired all cases.

The [shadow-feedback isolation plan](superpowers/plans/2026-11-11-shadow-feedback-isolation.md)
is now implemented and its 48-process source cohort is complete. Controlled
terminal bindings validate the intended shadow guard/RGB atlas separation,
but every condition still fails strict 4/4 static matching. These observations
are not per-primitive fetch traces or unique-cause proof. The
[feedback guide](STAGE7_SHADOW_FEEDBACK.md) also preserves the failed local
fresh-cache combined pair and separate edited-terrain-gradient prototype.
Per-camera terrain view-data lifetime/LOD is a next source-review hypothesis,
with no validated repair outcome. The separate four-process local llvmpipe
worker ABBA pilot is complete: requested-zero and default both match I420 only
8/10, differing at 2 and 7; requested-zero is not a complete fix. See the
feedback guide for full rates, fixed order/cache limits and lack of an actual
worker trace. The workspace-only apitrace v2 ABBA capture is complete with
four valid native receipts; OFF/ON I420 match only 8/10 and 7/10. The feedback
guide records the retained raw JSON/log/execution/cache evidence paths and
both complete trace hashes. Bounded trace analysis is complete: primary/control
unordered geometry/explicit-uniform/constant-vertex inputs match, but geometry
order differs in 53 passes. Used startup transform matrices also differ;
GPU-produced texture/full-state equality and a unique cause remain unproven.
The common SIGINT bootstrap applies to every arm; ON hides program-binary
formats, changing driver capability/timing. A local extra opaque-bin intervention
on Both is pending as `output/opaque-bin-pilot-v3/`, not an ordinary Both cell
or default render-sort change. Earlier v1 lost raw JSON before serialization;
v2 saved valid JSON but retained wrapper status 1 from in-memory tuple
validation. Neither is a completed matrix. V3 validates JSON after reloading,
without relaxing criteria. See the feedback guide for retained failure evidence,
exact findings and limits. Keep OFF controls and failures. A separately validated repair is required before the original moving MD-V3 2 seeds ×
2 scenes × 12 steps × 2 processes strict 4/4 gate.
