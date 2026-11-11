# Stage 7 — verified cross-process scheduling and first-source pixel forensics

## Provenance

All listed artifact ZIP sizes and SHA256 digests were checked against the GitHub API before extraction. The current strengthened comparator recomputed the complete original 32-process aggregation, with 32 distinct process UUIDs, exactly matching the uploaded summary. PR #14 reanalysis decompressed all 96 retained original RGB images and checked their original ONNX-source SHA receipts. Its regenerated four-scene summary exactly matched the uploaded original summary.

## Original fixed-pose experiment: run 42927840424

Four native jobs plus one independent aggregation succeeded. This static-scene experiment contains no ONNX inference. Each arm compares two independent processes with the same seed, scene, capture mode and task treatment.

| Seed | Scene | Arm | Source Road/Wide matches | Warped Road/Wide matches | I420 matches | First source Road/Wide difference |
| --- | --- | --- | --- | --- | --- | --- |
| 20261109 | s_curve_left_right | sequential_original | 6/10, 9/10 | 6/10, 10/10 | 6/10 | 2, 8 |
| 20261109 | s_curve_left_right | paired_original | 10/10, 10/10 | 10/10, 10/10 | 10/10 | None, None |
| 20261109 | s_curve_left_right | sequential_pssm_task_removed | 10/10, 10/10 | 10/10, 10/10 | 10/10 | None, None |
| 20261109 | s_curve_left_right | paired_pssm_task_removed | 10/10, 10/10 | 10/10, 10/10 | 10/10 | None, None |
| 20261109 | s_curve_right_left | sequential_original | 10/10, 8/10 | 10/10, 8/10 | 8/10 | None, 5 |
| 20261109 | s_curve_right_left | paired_original | 10/10, 10/10 | 10/10, 10/10 | 10/10 | None, None |
| 20261109 | s_curve_right_left | sequential_pssm_task_removed | 10/10, 10/10 | 10/10, 10/10 | 10/10 | None, None |
| 20261109 | s_curve_right_left | paired_pssm_task_removed | 10/10, 10/10 | 10/10, 10/10 | 10/10 | None, None |
| 20261110 | s_curve_left_right | sequential_original | 8/10, 9/10 | 8/10, 10/10 | 8/10 | 5, 8 |
| 20261110 | s_curve_left_right | paired_original | 10/10, 10/10 | 10/10, 10/10 | 10/10 | None, None |
| 20261110 | s_curve_left_right | sequential_pssm_task_removed | 10/10, 10/10 | 10/10, 10/10 | 10/10 | None, None |
| 20261110 | s_curve_left_right | paired_pssm_task_removed | 10/10, 10/10 | 10/10, 10/10 | 10/10 | None, None |
| 20261110 | s_curve_right_left | sequential_original | 9/10, 8/10 | 9/10, 8/10 | 7/10 | 10, 5 |
| 20261110 | s_curve_right_left | paired_original | 10/10, 10/10 | 10/10, 10/10 | 10/10 | None, None |
| 20261110 | s_curve_right_left | sequential_pssm_task_removed | 10/10, 10/10 | 10/10, 10/10 | 10/10 | None, None |
| 20261110 | s_curve_right_left | paired_pssm_task_removed | 10/10, 10/10 | 10/10, 10/10 | 10/10 | None, None |

Across four scenes, sequential-original source Road/Wide match counts were 33/40 and 34/40; warped Road/Wide 33/40 and 36/40; I420 29/40. Paired-original and both PSSM task-removal arms each matched all 40 frames in every image field. Warmup frames are included in these denominators; the per-case JSON separately retains post-warmup counts.

Paired capture changes the sensor task-step schedule. PSSM removal changes renderer semantics. Neither static-scene result establishes original moving-camera MD-V3 determinism or a unique PSSM cause.

## Original MD-V3 RGB pixels: run 42924910245

Four native jobs plus one reanalysis job succeeded. Eight original-PSSM CPU-retention-probed ONNX processes completed 12 steps each; all four instrumented strict comparisons still failed. The first source mismatch was step 2 in all cases, with 1/8/3/13 changed pixels. I420 first differed at steps 6/2/6/2. These are original artifact observations, not a new model run.

Coordinates are zero-based, top-left origin; each native image is 964×604 uint8 RGB. All 25 changed pixels across four first-difference images are listed, not only a bounded coordinate sample.

| Seed | Scene | Camera | XY | Run 0 RGB | Run 1 RGB |
| --- | --- | --- | --- | --- | --- |
| 20261109 | s_curve_left_right | wide | (113,334) | [189, 177, 47] | [194, 182, 25] |
| 20261109 | s_curve_right_left | road | (674,336) | [149, 147, 126] | [150, 148, 133] |
| 20261109 | s_curve_right_left | road | (628,338) | [194, 192, 195] | [190, 189, 191] |
| 20261109 | s_curve_right_left | road | (453,345) | [187, 177, 90] | [183, 173, 106] |
| 20261109 | s_curve_right_left | road | (405,347) | [149, 147, 133] | [151, 148, 139] |
| 20261109 | s_curve_right_left | road | (382,348) | [155, 151, 140] | [156, 152, 145] |
| 20261109 | s_curve_right_left | road | (108,365) | [142, 141, 109] | [143, 141, 116] |
| 20261109 | s_curve_right_left | road | (83,367) | [141, 142, 96] | [142, 142, 104] |
| 20261109 | s_curve_right_left | road | (14,372) | [140, 145, 88] | [142, 145, 99] |
| 20261110 | s_curve_left_right | wide | (851,409) | [116, 113, 92] | [109, 108, 82] |
| 20261110 | s_curve_left_right | wide | (936,436) | [127, 119, 106] | [123, 116, 100] |
| 20261110 | s_curve_left_right | wide | (748,475) | [118, 117, 99] | [113, 113, 90] |
| 20261110 | s_curve_right_left | road | (854,311) | [159, 157, 132] | [156, 155, 122] |
| 20261110 | s_curve_right_left | road | (887,312) | [152, 155, 101] | [149, 153, 86] |
| 20261110 | s_curve_right_left | road | (922,327) | [157, 150, 142] | [155, 150, 136] |
| 20261110 | s_curve_right_left | road | (947,327) | [154, 151, 157] | [153, 150, 158] |
| 20261110 | s_curve_right_left | road | (784,332) | [161, 157, 146] | [158, 155, 139] |
| 20261110 | s_curve_right_left | road | (759,333) | [156, 153, 137] | [154, 151, 130] |
| 20261110 | s_curve_right_left | road | (663,337) | [155, 151, 158] | [153, 150, 158] |
| 20261110 | s_curve_right_left | road | (375,349) | [153, 148, 151] | [152, 148, 153] |
| 20261110 | s_curve_right_left | road | (135,363) | [152, 149, 133] | [150, 149, 126] |
| 20261110 | s_curve_right_left | road | (141,363) | [142, 143, 106] | [139, 141, 96] |
| 20261110 | s_curve_right_left | road | (73,367) | [150, 144, 136] | [148, 144, 130] |
| 20261110 | s_curve_right_left | road | (0,373) | [191, 179, 61] | [195, 183, 35] |
| 20261110 | s_curve_right_left | road | (930,509) | [102, 105, 63] | [95, 100, 46] |

Visual inspection places the measured examples around curb/terrain/road-surface boundaries and markings; it does not provide a shadow/depth/material segmentation. The cropped samples preserve byte values using nearest-neighbor display, with markers only on a diagnostic figure. No source or model input is edited. Pixel locations alone cannot identify PSSM, multisampling, depth precision, callback timing, or driver behavior as the unique cause.

Only one original paired-process sample per seed/scene was retained by this run. Recurrent mismatch at the same world point across fresh independent runs is not established; same image coordinates over successive moving frames are not necessarily the same world location.

## Artifact IDs and verified ZIP digests

| Run | Artifact ID | Name | ZIP SHA256 |
| --- | --- | --- | --- |
| [42927840424](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42927840424) | 13816160190 | stage7-pssm-crossprocess-fourscene-summary | `53655e3c9b5678daa8cf6cbaf0ef4e9ab51a28be0cba36a321eae857735928d0` |
| [42927840424](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42927840424) | 13815905490 | stage7-pssm-crossprocess-20261109-s_curve_right_left | `aed5c694253ca777fbd658abd871e70c5cf4b41b8615de65faadd54fad5ad6da` |
| [42927840424](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42927840424) | 13815771440 | stage7-pssm-crossprocess-20261110-s_curve_right_left | `cb7839bb749cea260382eb64ea540220a4fcdb9d44aaab3ebbf07e65833bca49` |
| [42927840424](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42927840424) | 13815661222 | stage7-pssm-crossprocess-20261109-s_curve_left_right | `8921dadfe7f8f220f5800aee26d2747cd8fd6dcf416c7b5e7117a80a44707d9d` |
| [42927840424](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42927840424) | 13815481109 | stage7-pssm-crossprocess-20261110-s_curve_left_right | `dcaad013d70d1571f1f57b4b381a5f29a28249915f1bc5897b28da6677eac2c8` |
| [42924910245](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42924910245) | 13814521229 | stage7-rgb-pixels-20261110-s_curve_right_left | `5776eab00747225bbb1d221a3901f28ec8eda1347da554f5056f1b2ccb3f4b95` |
| [42924910245](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42924910245) | 13813667010 | stage7-rgb-pixels-20261109-s_curve_right_left | `01a88919fb6b056d18acd3cd3ca1cb77eac660b3644cfde7da551fec86dbb3cb` |
| [42924910245](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42924910245) | 13813582352 | stage7-rgb-pixels-20261110-s_curve_left_right | `81595518c94abfcae8f056369e88acebbc6bebe927240674adf7bd9dfed889fa` |
| [42924910245](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42924910245) | 13813377373 | stage7-rgb-pixels-20261109-s_curve_left_right | `0351c6339e89df8107d52e3a10cf3386a7c4e4f61c4a2e27fd4368879ef54165` |
| [42924910245](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42924910245) | 13813004995 | stage7-original-mdv3-source-rgb-pixel-summary | `0e9ddfb940892e9c42f59a03f9f0728bc849ac5a3d9acf71528faa4bc6aec3b7` |

## Local reproduction and limits

Ignored local archives, original extractions, combined copies, SHA manifests, regenerated summaries and the pixel contact sheet reside under `output/stage7-remote-evidence/`. Large original images and model weights are not committed. The original archive IDs and official model-source SHA receipts are sufficient to fetch and verify again while artifact retention permits.

Original uninstrumented official MD-V3 strict gate remains **0/4 PASS (FAIL)**. No renderer repair, model performance ranking, real-camera optical equivalence, or Stage 7 completion is claimed. The next controlled experiment must preserve a sequential-original control and label any paired moving-camera input as experimental until rendering semantics and full source/RGB/I420/action/state/pose repetition are separately evaluated.

## Strengthened-HEAD repeat cohort: run 42930483265

Exact tested HEAD: `f1dc88d476942de05f913cbc828a5fa5912e78a3`. Four native jobs and one independent aggregate succeeded. All five ZIP digests, 32 distinct process identities and the exact regenerated summary were verified before PR #15 was squash-merged as `0c678facbf72c269c2453f472e64d8192b70d675`. The nine final check runs and Codex review for the PR HEAD were complete without findings. [Verification comment](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/15#issuecomment-6783307935).

| Arm | Source Road/Wide | Warped Road/Wide | I420 |
| --- | --- | --- | --- |
| sequential_original | 30/40, 31/40 | 30/40, 36/40 | 27/40 |
| paired_original | 40/40, 40/40 | 40/40, 40/40 | 40/40 |
| sequential_pssm_task_removed | 40/40, 40/40 | 40/40, 40/40 | 40/40 |
| paired_pssm_task_removed | 40/40, 40/40 | 40/40, 40/40 | 40/40 |

Sequential-original first source difference steps (Road/Wide):

| Seed | Scene | Road | Wide |
| --- | --- | --- | --- |
| 20261109 | s_curve_left_right | 5 | 8 |
| 20261109 | s_curve_right_left | 5 | 5 |
| 20261110 | s_curve_left_right | 2 | 1 |
| 20261110 | s_curve_right_left | 10 | 5 |

| Artifact ID | Name | ZIP SHA256 |
| --- | --- | --- |
| 13816940286 | stage7-pssm-crossprocess-20261109-s_curve_left_right | `sha256:98cdd22f79bde47f0a0772e9bc71e1311ed0f38466792202bcf58399431c7135` |
| 13816726003 | stage7-pssm-crossprocess-20261110-s_curve_left_right | `sha256:8b1d833b383e0f7665dc4cb3823c8d3478ecbefc8ee1e1de383c0732913357b7` |
| 13816606497 | stage7-pssm-crossprocess-20261109-s_curve_right_left | `sha256:2866fb0549c5614452b3e4467a832319243521c19685c1cda5c60e65f8a555f0` |
| 13816013394 | stage7-pssm-crossprocess-fourscene-summary | `sha256:b5e7af978b3b686cc2bb7ac8d95a7ac76907aadac2e3c88095c5bf7a2feea65f` |
| 13815004950 | stage7-pssm-crossprocess-20261110-s_curve_right_left | `sha256:f231ff7aee6c39823845e2f66f95042b0fa16ae0310b61c80c271c7242df49e2` |

These are two different CI cohorts, not pooled proof of causality. The native sequential mismatch counts and first-difference steps vary across cohorts. Paired and PSSM-task-removal matches remain static-scene observations. No official renderer default was changed.

## Revalidated CPU callback timing and upstream source

The original eight callback-order artifacts from [run 42819410983](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42819410983) and eight pose/MVP artifacts from [run 42822587924](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42822587924) were downloaded with ZIP SHA/size verification. Recomputing all sixteen published comparison JSONs from their raw callback entry/exit events reproduced them exactly.

All **96 recorded profiled CPU task ticks** in the order experiment entered and returned from PSSM.update before MainCamera._chase_task. The separate pose/MVP experiment also reconstructed 96 observed-arm ticks in that order; Chase changed main-camera position on one initial tick in each of its eight observed conditions. These measurements distinguish actual profiled Python invocation order from registered sort numbers. They do not establish GPU draw/depth order, an overhead-free unprofiled sequence, or causality for the original moving-model pixel changes.

The installed MetaDrive 0.4.3 source registers PSSM.update, updates its shadow rig from the main camera and resets film-size cache each tick; upstream BaseCamera.perceive mounts a single sensor, runs taskMgr.step and restores it. RGBCamera requests a floating-point HDR target and multisampling before fixed-exposure tonemapping. Requested multisample count is not proof of the negotiated driver framebuffer format.

The official [Panda3D 1.10.13 PSSMCameraRig source](https://github.com/panda3d/panda3d/blob/v1.10.13/contrib/src/rplight/pssmCameraRig.cxx#L141) computes stable-CSM texel snapping via fmod and inverse MVP, and its film-size cache and projection depend on the main camera. This provides candidate numerical/render-state boundaries to inspect; it is not proof of a defect or a reason to change the renderer. The downloaded source SHA256 was `0c81e0e00bfafb22387fa8812681e37829e99d0b0bf3c7c1ffbaa70694b60e66`.

The loaded installed tonemap.frag SHA256 was `835b7ccb2d88f79d3d92b2009e142ad88453939a37a6e156808809e069c9af12`; simplepbr.frag was `8eef67eb4384d6a74136b8e99b4c9bf0711e51ee88db7a248cd164c7a69f9ceb`. The inspected PBR shader samples the PSSM shadow atlas and compares reference depth. No change to these sources, uniforms, shader passes or the Panda binary was made.

| Run | Artifact ID | Verified ZIP SHA256 |
| --- | --- | --- |
| 42819410983 | 13767585064 | `sha256:9f98aeb165ef46fdbad018405ea7bbc54aa10088a360e06ed80ea69603352e7b` |
| 42819410983 | 13767345021 | `sha256:7ca3dfc6622e7e5872072128001477e8fb1945f306dee37ba7d3569b569e6c2e` |
| 42819410983 | 13766455265 | `sha256:6e552726fb0fc13ec5c0bd886e8f5a4f7f772e2a8c8a71b35ee1630b16d88bac` |
| 42819410983 | 13766370283 | `sha256:8824c4f672acc9ccbe06183546042e3f0ac6f68c468fad61439ba3a07265901f` |
| 42819410983 | 13766281197 | `sha256:f4104fb2b36627845d7eb9ff831f4460a85e8a2c7580260a376ef141c1772767` |
| 42819410983 | 13765884179 | `sha256:7427353a0056895e3967deb48208f0f572b9f379c3a56fb0b0cab916fb0a3022` |
| 42819410983 | 13765484755 | `sha256:31b463e4f52e495e136280c6cd4d6ea52a39c62b168162127f1c511e717adb25` |
| 42819410983 | 13765364850 | `sha256:fa1e54b8e052237b7cfb20823394432eee2ba9a4baca8a9df9279071f9df5a0f` |
| 42822587924 | 13768360043 | `sha256:695ddcdf2c6295e35739e8ac4683917b1013b1e0bfcccc1356ab25f7d7180796` |
| 42822587924 | 13768245570 | `sha256:5df50aa5184f869b628d84c5bf35897d9d97d49075a4ed01ddaa448ef5bf2677` |
| 42822587924 | 13768146012 | `sha256:4e2738625e815635e1bd507754e9eaa0bcc8ed8bc6a04395f5525a8536f3327d` |
| 42822587924 | 13767987753 | `sha256:27176dbf1d64e914cd8d5e6346f39b4ab47f5bcce45ad3f9d6c5fc46d16c99a2` |
| 42822587924 | 13767907895 | `sha256:04ac1947fdbd76a13423daae9447c885f6494399d2cd33e532388f6262cbc0ac` |
| 42822587924 | 13767174347 | `sha256:8c714433b6a9e91a17c339ecec26b53ffac05c4babad53df1b2e35fcb186e03e` |
| 42822587924 | 13766944546 | `sha256:603ab98ee979f6e538cb551b57551f7ee485fdfca2d628c136e29450e7f6c0b7` |
| 42822587924 | 13766364971 | `sha256:a6d243dbdb2592b72da278603afd7dcf76c49dd724108338bdaa6eed6c5b77ff` |

## Verified camera-order / shared-tick isolation — PR #16

[Run 42934781823](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42934781823), exact HEAD `696008be2c9fa9a91ca5c928fb8f2462fc36f496`: all four native jobs and independent aggregation succeeded. All five ZIPs were SHA256/size verified. The current comparator reconstructed all 32 raw receipts and matched the uploaded final summary exactly, with 32 unique UUIDs and eight unique PIDs in each same-runner scene. All nine current-HEAD checks and Codex review passed. [PR #16](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/16) merged as `1d4a236cb85f4af3b94d6289b81aac89665f4c4e` after the Xvfb review finding was fixed and resolved.

| Treatment | Source Road/Wide /40 | Warped Road/Wide /40 | I420 /40 | Post-warmup I420 /32 | Cases exact in every image field /4 |
| --- | --- | --- | --- | --- | --- |
| sequential_road_first | 33, 30 | 33, 34 | 27 | 20 | 0 |
| sequential_wide_first | 40, 40 | 40, 40 | 40 | 32 | 4 |
| paired_one_tick | 40, 40 | 40, 40 | 40 | 32 | 4 |
| paired_two_ticks | 40, 40 | 40, 40 | 40 | 32 | 4 |

| Seed | Scene | Original Road first difference | Original Wide first difference | Original I420 matches /10 |
| --- | --- | --- | --- | --- |
| 20261109 | s_curve_left_right | 5 | 8 | 6 |
| 20261109 | s_curve_right_left | None | 5 | 9 |
| 20261110 | s_curve_left_right | 5 | 6 | 8 |
| 20261110 | s_curve_right_left | 2 | 3 | 4 |

All other treatment/case combinations had no observed source-image difference in their ten-frame repeats. This is a static scene with no ONNX inference; it is **not** the official MD-V3 4/4 gate.

**Supported inference:** Reducing the task tick count from two to one is not necessary for static equality in this cohort: wide-first sequential and paired-two-tick treatments both kept two ticks and matched all image fields. Order/mounting/timing remain possible factors.

**Rejected overclaim:** Neither wide-first nor paired-two-tick is a universal deterministic fix. The earlier local two-repeat pilots had source/I420 mismatches under concurrent treatments on a different environment. CI vs local differences do not isolate CPU load, driver, dependencies or scheduling as a unique cause. No default capture path was changed.

| Artifact ID | Name | ZIP SHA256 |
| --- | --- | --- |
| 13818805315 | stage7-capture-schedule-20261109-s_curve_right_left | `sha256:bc9fc63137448804e881f0ca192ec969d1335a4e1ddc752c34c1ea692afced08` |
| 13818421156 | stage7-capture-schedule-20261110-s_curve_right_left | `sha256:0d59ddbd3b499f7600366907f894ff311456f4657395d1f07850f62e22cd7839` |
| 13818292223 | stage7-capture-schedule-20261110-s_curve_left_right | `sha256:34c32c29124f4560e822f0e0ca3f44690392217f536d675031f8836db93d2b7b` |
| 13818287640 | stage7-capture-schedule-fourscene-summary | `sha256:82f55992f442d39d25b893b3061ff6b89302bf41b6b75fc99256fc7812d29038` |
| 13817484091 | stage7-capture-schedule-20261109-s_curve_left_right | `sha256:60e5bedf19fa9aea7404bf6a07aae82a8131478b7481cdcf09a783d2dab4dada` |

The superseded initial matrix run 42933831409 was cancelled after the Xvfb status-handling review correction, and is not counted as a successful experiment. The validated launcher accepts cleanup-only status 5 only with a fresh complete native receipt; other failures remain failures. Regression tests include stale, absent and invalid output. Full local suite: 232 passed, no skips.

Existing shared-capture regressions also succeeded on d6e7db0: raw pixel-clock 42933830938 (four cases /16 independent processes, all summaries regenerated), original PSSM cross-process 42933831083 (five jobs /32 raw receipts reaggregated with exact summary equality), and render causality 42933831001 (one Python process, six fresh-world conditions; verified ZIP). Their workflow and transitive capture/common-validator inputs are byte-identical at the corrected HEAD. These scope-matched regressions are distinct from the new exact-HEAD 32-process matrix.

## Why first source differences can precede model-input differences

For both left-right original MD-V3 pixel cases, the first differing pixels at step 2 were in Wide only. The actual first differing warped-Wide RGB and ONNX I420 feeds were both step 6; Road was byte-identical through all six retained steps.

The implemented centered zero-rotation pinhole warp gives a conservative source footprint for Wide of approximately **x=[319.90,643.47], y=[205.47,367.94]**, including the full admitted ±1% focal interval and an extra source pixel on each side for bilinear support. All first step-2 changed pixels — (113,334) for seed 20261109, and (851,409), (936,436), (748,475) for seed 20261110 — lie outside that union. Thus those initial pixel differences cannot influence that step's model canvas under the validated projection contract. This agrees with the recorded identical warped-RGB and new_img SHA values.

This does not prove that every later pre-step-6 source change is outside the crop. Seed 20261109 has an edge change at (642,357) at step 5, inside the conservative union, while the actual warped RGB remains equal. The actual measured lens matrix was not retained, so an exact boundary/rounding explanation for that edge pixel is not claimed. At step 6, interior source changes include (478,329) and (406,313), respectively, when the recorded warped RGB and I420 first differ. Crop/interpolation/input packing are separate boundaries; a source pixel difference is not automatically an ONNX input difference or a renderer-cause proof.

## Additional local hypotheses

Four sequential ABBA pilot processes compared PYTHONHASHSEED unset versus 0 at seed 20261109 / left-right, leaving original camera/PSSM/Chase paths untouched. Both two-process groups matched source Road, Wide and I420 **10/10**. The pilot did not discriminate the treatments and provides no evidence that fixing Python hashing repairs the renderer. No environment default was adopted.

A fresh runtime probe reported MetaDrive config multi_thread_render=true and mode=Cull, but GraphicsEngine.getThreadingModel() returned `/` with empty cull/draw names. The local renderer identified as llvmpipe (LLVM 19.1.7, 256 bits), Mesa 25.0.7-2+deb13u1. This is one local engine-property observation, not a report for every graphics output or CI machine. Declared configuration alone does not establish actual render-thread execution; no threading-based root cause or repair is inferred.

## External CPU-load pilot — negative/discriminating limit

After the hash-seed pilot, two more separate original Road-first native
processes used the same seed 20261109, left-right static scene, ten pairs,
original PSSM/Chase and no ONNX, with three bounded external SHA-compute CPU
workers. The workers were stopped and reaped after both captures. The local
host had five available CPUs and sufficient memory; load was limited to three
small workers and left the rendering process running normally.

Both loaded runs still matched Road source RGB, Wide source RGB, warped RGB
and I420 **10/10**. The quiet baseline pair from the earlier local pilot also
matched 10/10. Median measured pair wall-time was 4.2663 / 4.5079 seconds in
the quiet processes and 9.1843 / 9.6783 seconds under load. Thus the load
intervention materially slowed capture but did not reproduce disagreement in
this one case. Timing slowdown alone is not sufficient evidence of pixel
mismatch here. This sequential, single-case pilot is not a randomized
multi-scene or per-callback profiling-overhead experiment, so it cannot rule
out CPU timing effects in other conditions. No runtime setting or rendering
repair was adopted from it.

Local receipts, process identities and manifest are in ignored
`output/cpu-load-pilot/`; hash-seed receipts are in `output/hashseed-pilot/`.
The main forensic evidence remains the original, independently SHA-verified
CI artifacts listed above. Official uninstrumented MD-V3 strict repeatability
remains the prior **0/4 PASS (FAIL)**. No new official ONNX trial or broader
model scenario expansion was executed without a validated repair.
