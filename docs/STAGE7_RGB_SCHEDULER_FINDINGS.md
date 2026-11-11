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
