# Stage 7 integration evidence and remaining validation

At this draft checkpoint, historical virtual intrinsics, RGB/I420 plumbing, sampled world-to-paint alignment and native target-lane arithmetic have verified passes. The experimental `feedback_both` plus opaque unsorted type 1 official MD-V3 candidate also has two separate twelve-step **4/4 legacy repeatability** cohorts. A newly confirmed missing FRD→FLU applied-action rotation means these legacy gates do not establish motion validity; the corrected adapter is TDD in progress, not complete, and its corrected native gate has not executed. The historical **unmodified original gate remains 0/4 FAIL**. None of these results establishes physical comma optics, global renderer equivalence, driving rank, default adoption or Stage 7 completion.

This document reconciles older guide status with retained evidence. A fresh independent read-only review is clear for all seven selected ZIPs, the 202-file manifest, frozen source identities and raw image/math recomputation. The reviewed findings and evidence bytes remain immutable. No future documentation PR number is presumed.

## Gates and evidence boundaries

| Gate | Verified evidence | Exact scope | Remaining limit |
|---|---|---|---|
| Virtual pinhole intrinsics and image response | 42569322601 and 42569804426 | Road/Wide measured lens geometry, 512×256 canvases and pose-dependent change; second run records actual uint8 I420 `[2,6,128,256]` | Not a real lens, source-to-canvas photometric equivalence or ONNX result |
| Straight native world-to-paint diagnostic | 42573166387 | MetaDrive straight block `S`, seed 20261109, two relative camera poses × two cameras, +27 px control | One sampled virtual scene; image threshold false positives/negatives remain |
| S-curve/ramp paint diagnostic | 42578810503 | Four native `C,C`/`r`/`R` scenes, two static poses × two cameras, revised focus-control gate | Gate changed after failed runs; not a preregistered holdout or candidate-specific paint validation |
| Native lane-truth arithmetic | 42582782731 | Eight chosen lanes, 24 center +24 deliberate right-intrusion samples, eight exact pure summaries | Coordinate self-consistency and chosen-footprint arithmetic; not an ONNX trajectory |
| Legacy official MD-V3 candidate repeatability | 42979680883 and 42981493726 | Each 4/4 at twelve steps; 16 unique UUIDs/nonces and 192 actual parent model steps combined | Legacy repeatability only; missing applied-action basis bridge prevents motion-validity claims; original 0/4 remains |
| Source I/O conventions | Pinned official source commit `e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42` | Numeric model-curvature formula and six I420 plane order match source conventions | Model-body FRD curvature still needs the missing FLU/world-yaw applied-action bridge; not production NV12 equivalence or model quality |
| Legacy official expansion | PR #27 source `e84369c9f7f461a59c8d506b8b9efb2312297c03`, run 42987993022 | **12/12 independently accepted legacy repeatability**; 24 processes, 1472 actual inferences/rows, 736 exact pairs; all 13 archives clear | Known action-basis gap remains; no motion-validity claim, correct tracking or PR merge follows |

The expansion protocol is [separately registered](superpowers/plans/2026-11-11-mdv3-candidate-expansion.md) and described in its [guide](STAGE7_MDV3_CANDIDATE_EXPANSION.md). Its collected source cohort has exact independent raw-data acceptance, and PR #27 merged as `bdcf91e4d3a98399503a0ba215b66920b0436c08`. Collection CI success alone cannot supply scientific acceptance or validate an action-frame contract. These separate geometry-guide drafts are intended for a documentation follow-up after that merge. Check retained execution state before starting another run; this document does not request a rerun.

## Historical geometry and optical archive ledger

The audit selected seven historical geometry/optics ZIPs, **22,532,317 bytes** total. Each API SHA256 and size matches; paths are bounded/safe and contain no symlinks. Original ZIPs, extracted PNG/JSON bytes, API run/job/artifact metadata and historical source snapshots remain under ignored `output/stage7-geometry-integration-audit/`. `verified_archives.json` records full hashes for every selected ZIP and member; `audit_manifest.json` covers 202 retained files. No official model weights are in these archives.

| Run | Source HEAD | Artifact ID | ZIP bytes | ZIP SHA256 |
|---|---|---:|---:|---|
| [42569322601](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42569322601) | `fd1a8892b2feb67030d4e4ae71b0d3cd6e1e63df` | 13652950905 | 720429 | `83ce9a0b6deae68bc4b910eb39469b70ce9fbcbc16cdeb6d5e588d44da4f29dc` |
| [42569804426](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42569804426) | `2e2ae997319d9e1722e6c1fb60182112ec263689` | 13653175550 | 720494 | `c4a56751fd8059ff7cf371ec76627ba55d04e3d471c8b653d1a4bc8589b40f45` |
| [42573166387](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42573166387) | `2658e000e9eb6b3c5be3179ee721dd6319668ce4` | 13653847508 | 1510224 | `ba1345f6b53f007b10317ca9f2be5b39c137349cdaa0d74ab753c8e5c4da7a73` |
| [42577333433](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42577333433) | `a241e69be98a4534126cfae19fe0d1c1aaf4ead0` | 13655294080 | 6484083 | `25c812b84294206c3e26ab80fc28a2d17fe04879bdf16c9e2801868028c3b1fa` |
| [42578145473](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42578145473) | `fca809788d875732cee7bbc5bf60a9bf9868cefd` | 13656033035 | 6546613 | `6e2cbc3f7b4ec07bb4988879cd23244787ce6b24d561c2ba320cab3e08e3c020` |
| [42578810503](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42578810503) | `05b37dcf088824b2a08bbb26b628fd83134e12b3` | 13656049008 | 6548415 | `528e2df31dee726166f4719a0ec6299f97cbfb27a6d5ed5cf83f786a0dbf8507` |
| [42582782731](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42582782731) | `c1ea8cabd7ec79ab9a08e2f2f2228c3f7fff3a3e` | 13658405606 | 2059 | `5c600ade867e2873092f358a65ed7769b3fe23ed84a8372a8d74d0cd65d5d3ba` |

The two curved failures remain failures: run **42577333433 was 0/4**, and **42578145473 was 3/4** with left→right S inconclusive. The final 4/4 run has a changed contract, detailed below. Run 42582782731 additionally lists curved-image artifact 13657832137; that separate ZIP was not downloaded/rehashed in this audit. Its job success is API evidence, while pixel reproduction uses selected final artifact 13656049008. No checksum-verification claim is made for an unselected ZIP.

## What the virtual projection actually checks

The straight audit samples actual native painted road-boundary coordinates across the map (223 landmarks) and applies the borrowed vehicle-relative Panda camera transform. The curved audit borrows cameras into world origin: `(x,y,height)` and Panda heading `degrees(route_heading)−90`. Actual Road/Wide RGB is warped into separate model canvases using measured virtual lens intrinsics. Separate image segmentation searches rendered white/yellow paint near stored projected points; overlays are illustrative, not the evidence used for matching.

The source reference is a centered, aligned, zero-distortion pinhole approximation. Source 964×604 uses focal 1324/283.5 px; target 512×256 uses focal 910/455 px and principal y 47.6/151.8. `H = K_source @ inverse(K_model)` and `WARP_INVERSE_MAP` define the warp. Recorded virtual Road/Wide coverage is 0.99609375/1.0. Focal mismatch tolerance is 1%, principal-point tolerance 0.5 px. These are virtual-source conventions and crop checks, not measured physical mount or real lens parameters.

The final historical projection/optical/scenario/curve-audit files are byte-identical to the corresponding current source checked by the audit:

| File | SHA256 at historical 05b37dcf and current audit checkpoint |
|---|---|
| `bigbench/lane_reprojection.py` | `92e77ea0458a2b153960fc494452f558f6ccdc1b7736da4222d17fdf77c4ce12` |
| `bigbench/optical_calibration.py` | `1a3852d67ea2f15ef31a4224916fb71275f25010a5038179a7e0dd8e984c09ce` |
| `bigbench/curved_lane_scenarios.py` | `49013b0bf16b2969382bbcd890db559df9b78e2eb2a0aefec94d88b02d1af7d0` |
| `scripts/metadrive_curved_lane_audit.py` | `e340e8f08d6aedfd549ea9189ca13fdeefe0d88124be87ddb9463e533237fd76` |

Current `NativeWorldCamera` uses the corresponding world pose/heading and rectifier math. That source continuity does **not** turn old PNGs into a new `feedback_both`/unsorted paint gate. The historical images were rendered before the later sampler/shadow-input/bin interventions. Candidate-specific lane-paint validation and global semantic equivalence remain unestablished; the separate bounded terminal-atlas readback does not establish them globally either.

## The curve gate changed after failures

The one-seed final result is **4/4 scenarios and 16/16 image gates** at seed `20261109`. S-shaped cases use forward native `C,C` curves with opposite signed curvature; `S` in the straight guide is a different, straight block ID. S cameras use curve fractions **0.13 and 0.40**. Their chosen forward arcs have radius 55 m and length about 45.116761 m. Ramp scenes select two actual circular connectors per `r`/`R` block (radius 40 m, length about 6.981317 m) and capture **11 m upstream** along each tangent. Camera height 1.22 m and paint z=0.018 m are virtual code conventions.

The first attempt's +27 px control could match adjacent paint; ramp focus often had only 0–1 candidates. The second attempt added upstream viewpoints/multiple offsets, but still required global discrimination and allowed focus-or-global discrimination. **After inspecting those failures, the final version dropped required global discrimination, required focused-curve discrimination and added ±90 px offsets.** This is post hoc diagnostic-protocol development, not an unchanged initial gate or a preregistered holdout study. Earlier failures remain visible.

The final required global diagnostic is candidates≥8, matches≥5, fraction≥0.45 and matched-point median≤7 px. Focus requires candidates≥5, matches≥3, fraction≥0.35, median≤7 px and focus discrimination. Offsets are `(27,0)`, `(-27,0)`, `(0,-50)`, `(-38,-37)`, `(38,37)`, `(90,0)`, `(-90,0)`. A false-pose control is admissible only with at least `max(1,0.7×positive_candidates)` remaining points; at least one admissible focus control must lower match fraction by 0.15. It does not require all controls to discriminate.

Left→right `bend_2` Wide still reports **`global_negative_discriminating=false`**. Focus has 72/72 matches, median 0.422637 px; +90 px control retains 71 candidates with 46 matches (0.647887), so `focus_negative_discriminating=true`. Its final PASS follows the revised focus contract and does not prove a discriminating whole-frame control. Full per-image positives/residuals/controls are in [the curved guide](METADRIVE_CURVED_LANE_AUDIT.md) and retained JSON.

## What pure recomputation confirms

The audit executed each historical original paint function against untouched PNGs and stored projected points. It did not launch MetaDrive, import Panda/ORT, render, query GL/GPU, load weights or infer. Across **52 paint images** (straight 4 + three curved cohorts 48), match counts, detected pixel locations, negative-control fractions and status decisions match exactly. Calculated Euclidean/percentile residuals differ by at most **`1.7763568394002505e-15` px**, retained in `recomputed.json`. The 587 assertions do not mean entire JSON byte identity and do not create any new model-comparison tolerance.

The two optical artifacts additionally provide eight model-canvas PNGs. Pure rechecks reproduce their recorded homographies/coverage and distinct pose-dependent RGB; I420 can be derived from the canvases. The first optical report does not contain the later I420 contract fields, so this new derivation is not retroactive historical inference evidence. Raw 964×604 source PNGs and original camera-node matrices are absent; original source-to-canvas sampling or native projection cannot be fully regenerated from those saved canvases/points alone.

Paint detection uses brightness/color thresholds and a ±12 px horizontal/±2-row window. Residuals are conditional on a match. False paint matches, occlusion and missed markings remain possible; this is not semantic segmentation, depth-occlusion truth or an independent physical road measurement.

## Native lane truth is arithmetic and coordinate self-consistency

Run 42582782731 passed four scenarios, **eight chosen lanes, 24 center and 24 deliberate right-intrusion samples**. Sampling at lane fractions 0.2/0.5/0.8 checks native `lane.position`→`local_coordinates` self-consistency. A common virtual half-width 0.9 m and lane width 3.5 m give chosen right offset 1.05 m and expected intrusion 0.2 m. Native gate tolerances were 0.05 m for lateral/depth and 0.1 m longitudinal.

All eight frozen pure summary dictionaries exactly regenerate from the receipts. Maximum center lateral error is 7.105427357601002e-15 m; longitudinal error 2.842170943040401e-14 m; deliberate intrusion-depth error 9.936496070395151e-15 m. Each three-sample summary reports one event and **0.15 s from assigned dt=0.05 s**. These are **three sparse chosen poses**, not an actual continuous ONNX trajectory or measured elapsed driving time. No new native inverse-coordinate call is supplied by this receipt-only audit.

The [lane evaluator guide](LANE_TRUTH_EVALUATOR.md) preserves explicit target-lane identity and forbids nearest-lane fallback. This gate does not prove merge/route-switch selection, general model behavior or a driving score. Ground-truth lane data stays outside model inputs.

## Official source I/O facts and legacy candidate repeatability

The official catalog pins commit `e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42`. Read-only source inspection of `modeld.py` lines 114–115 shows raw lateral action divided by `max(2.5, v_ego)**2` to obtain curvature, matching the numeric model-FRD curvature in `OnnxBigModelPolicy`; the legacy path still lacks its separate FLU/world-yaw applied-action basis bridge. The official `compile_modeld.py` lines 100–109 order six I420 planes as Y even/even, odd/even, even/odd, odd/odd, U, V, matching `i420_planes_to_six`. The pinned files were never executed during this audit; their full hashes are in retained `source_manifest.json`. This is a source-convention fact, not equivalence to the remainder of official modeld smoothing, production NV12 warp/color/interpolation or optical/model quality.

[Candidate results](STAGE7_MDV3_RENDERER_CANDIDATE.md) separately document source run **42979680883**, source `0fbebed2358610a773d317ef8e857acf6ddf5c98`, and automatic-main run **42981493726** at merge `e840022a73879164b4923f77dbb4aabaf1112131`. Each strict legacy candidate repeatability gate passes 4/4 for the four registered twelve-step cases, including source RGB, warped RGB, actual I420, raw actions, aggregate/named states and pose/clock receipts. Together they contain **16 unique UUIDs/nonces and 192 actual parent ONNX steps**. PIDs are distinct within each same-runner case; hardware identities were not retained, so no cross-hardware equivalence claim is made.

A read-only all-pairs comparison among four processes/case covers six pairs/case, **24 pair comparisons and 288 paired-row checks**, reusing those **192 existing actual steps**; it executes no extra inference. Evidence is `output/stage7-remote-evidence/candidate-two-cohort-cross-comparison.json`. The two initial legacy 4/4 gates and their full ten-archive ledgers remain in the candidate guide. Their exact matching never tested the missing action-basis conversion or established motion validity. Neither all-pairs equality nor the historical pixel checks promote the candidate to an original/default result. The original official gate remains **0/4 FAIL**.

Legacy PR #27 source `e84369c9f7f461a59c8d506b8b9efb2312297c03` and official expansion run **42987993022** now have **fully independently accepted 12/12 legacy repeatability**. All 13 API ZIPs, 74 members and every raw case/final summary are clear. The source's full local suite has 329 passing tests without skips, which is CPU/source validation, not evidence of the missing applied-action conversion. PR #27 merged as `bdcf91e4d3a98399503a0ba215b66920b0436c08` from final documentation HEAD `46a77106e1bdceaa11e9001c32100250d1a82306` after four current checks, completed Codex review with no findings/no open threads and a clear fresh three-document review. The native source `e84369c9f7f461a59c8d506b8b9efb2312297c03` passed 17 checks separately. The legacy source, raw actions, poses, states and labels remain frozen; no motion-validity or correct-tracking verdict follows.

Physical optics, production preprocessing equivalence, renderer-wide semantic validation, statistical driving scores, default adoption and Stage 7 completion remain distinct open gates. Official weights stay in ephemeral CI storage; this audit and its documentation drafts introduce no local model cache or new model execution.


## Confirmed missing model-to-world applied-action rotation

Pinned official source and pure kinematic math establish **`CONFIRMED_MISSING_MODEL_TO_WORLD_ACTION_BASIS_ROTATION`** in `output/stage7-coordinate-contract-audit/coordinate_basis_proof.json`. The numeric formula is not the defect: model-body curvature is `raw_lateral / max(2.5, v_ego)**2`. Model/device FRD means forward/right/down, while the integrator's body FLU means forward/left/up and positive curvature increases counterclockwise world heading. **Both frames are right-handed.** The constant body-basis rotation is:

```text
R = diag(1, -1, -1), det(R) = +1
k_world_ccw = -k_model_right
acceleration_world_forward = acceleration_model_forward
```

This rotates the body basis 180° about forward; it does not flip global world Y, alter camera/image axes or tune a controller. `step_ideal` already rotates forward displacement using the current world heading. Pinned `camera.py` declares FRD/FLU; modeld/parser/message/control-source propagation preserves the model sign until a later left-positive steering boundary negates it. Those sources were read as text only; no external controller, vehicle plant or remote source was executed.

Nine retained synthetic signed/zero cases at initial headings 0, 0.6 and −1 rad demonstrate the mismatch. For raw lateral +8, speed 8 m/s and dt 0.05 s, model curvature +0.125 1/m produces legacy heading change +0.05 rad and body-left displacement +0.009998958 m. Applying the basis rotation produces heading change −0.05 rad and body-right displacement of the same magnitude. These are pure synthetic arithmetic controls, not additional ONNX or native-render steps. The gap is confirmed; its sole responsibility for every tracking error, optical equivalence and model quality is not proven.

All historical repeatability records retain their original raw four outputs, recurrent states, I420 inputs, parent actions, poses and labels. They are **legacy repeatability evidence only, not model-to-world motion-validity gates**, regardless of exact bit equality. The existing static paint-alignment and native lane-coordinate arithmetic remain separately valid within their sampled scope; neither exercised this action bridge.

The retained prospective plan [model-to-world action plan](superpowers/plans/2026-11-11-mdv3-world-frame.md) proposes distinct protocol `stage7-mdv3-world-frame-v1`. **The corrected adapter is TDD in progress, not complete; no corrected native gate has executed.** It will preserve inner raw outputs, states and actual I420, record the unchanged parent numeric model action, and separately map only the applied world curvature while retaining acceleration. No corrected native verdict, corrected expansion, new default or retrospective repair of legacy results is claimed. Its first separate corrected gate must be validated before any later corrected expansion. The seven original geometry ZIPs and their reviewed 202-file manifest/findings remain unchanged; new coordinate-contract evidence is a separate audit.


## Independently accepted legacy expansion: repeatability and tracking scope

[Run 42987993022](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42987993022) uses frozen PR #27 source `e84369c9f7f461a59c8d506b8b9efb2312297c03`, expansion-module SHA256 `d86b3be67c8ac3dee31f0bf9928014d3880c8c55a6cd829bb3c46c464d16b42c`. Root and a fresh independent evidence reviewer accepted all 13 API ZIP SHA256s/sizes/safe paths, 74 retained members, all 12 raw cases and the final aggregate. Evidence acceptance and PR #27 merge are separately recorded above. No additional experiment was executed to update these scratch guides.

| Legacy group | Complete exact cases | Fresh processes | Actual inferences / completed rows | Exact paired rows |
|---|---|---:|---:|---:|
| `camera028` | 4/4 | 8 | 96 / 96 | 48 |
| `native_ramps` | 4/4 | 8 | 96 / 96 | 48 |
| `longer160` | 4/4 | 8 | 1280 / 1280 | 640 |
| Total | **12/12** | **24** | **1472 / 1472** | **736** |

All 24 process UUIDs/nonces are fresh, with two distinct same-runner PIDs per case. Every required source/warp/I420/raw-action/aggregate-state/named-state/capture-entry/post-pose/time pair matches exactly. There is **no first mismatch or incomplete step**. These observed counts are no longer merely planned budgets, but they remain legacy-action repeatability evidence and never demonstrate the missing FRD→FLU bridge.

Every long trial completes 160 steps, ends at virtual time 7.99999999999998 s and has 160 distinct I420/image-state/feature-state hashes; the expected zero-desire state remains constant. The four long cases (eight process repeats) **visit only the first of the three route lanes and finish at active index 0**. The maximum absolute lateral errors below are identical between the two repeats in each case:

| Long case | Maximum virtual lateral deviation (m) | Visited route lanes | Final active index |
|---|---:|---:|---:|
| 20261109 / `s_curve_left_right` | 39.00889893289053 | 1 of 3 | 0 |
| 20261109 / `s_curve_right_left` | 41.15546916242339 | 1 of 3 | 0 |
| 20261110 / `s_curve_left_right` | 39.013354504690554 | 1 of 3 | 0 |
| 20261110 / `s_curve_right_left` | 41.143709047701606 | 1 of 3 | 0 |

All 24 lane-truth summaries exactly regenerate from actual frame rows, as retained in `output/stage7-remote-evidence/run-42987993022/tracking_scope_revalidation.json`. They are unscored virtual geometry observations. Eight seconds and nominal 64 m of integrated path distance do not prove full S traversal or correct tracking. The confirmed missing body-basis action bridge is a boundary defect, but these observations do not prove it is the sole cause of every tracking error.

### Accepted expansion archive ledger

Each artifact below belongs to run **42987993022** at source **`e84369c9f7f461a59c8d506b8b9efb2312297c03`**. Original archives, case/final exact regeneration, `totals.json`, `verified_archives.json` and tracking receipts remain under `output/stage7-remote-evidence/run-42987993022/`; this new model-cohort ledger is separate from the immutable historical seven-archive geometry ledger above.

| Artifact ID | ZIP bytes | ZIP SHA256 |
|---|---:|---|
| 13846305290 | 4058 | `2a886edbdd69cae67cfa24dbd2a6bac15027f40e220b2ab828c258a29472fd3d` |
| 13845617914 | 379456 | `b34facfed1ad8d800c657a1485ffbaf2c31c65c9d9636eda54d9ef4de4156aee` |
| 13844647784 | 381798 | `12803d69259b048b8ac2982a9519078f42fce36877c492fd1a8401550f50eb3e` |
| 13843468186 | 382109 | `93404c4fde9f83c600f8753b80a70aa0603244659c272722a4217bc80c5cfe3b` |
| 13842713664 | 379990 | `dd5927d899cc048894fc397fc87d8d1de61c280c07752490aecada9bfb56748d` |
| 13841735302 | 38027 | `ad857804f2a4ea80996d2a7d8092c2f09e6c3db547d642092c7dd5d8261e007c` |
| 13841661971 | 38085 | `4b79a2d60dd28f7c04bbd998bff2dd74ebd5679521ba8d1b38b17b6f842e9f5d` |
| 13840726305 | 38208 | `29c02cfae9e89b2b36904df618cd7be28efe82c57b2b7ac2a0b3f9c8b7178564` |
| 13840668097 | 37881 | `5bb26baea8ea7cdd7f709d1b6857dd8592c47a2c95272bce2be16769d9707936` |
| 13840653861 | 38069 | `ca51bc6cffbe61f3d097960b0b32ec21a11b6f84a1236f66d1183cd6ca98454e` |
| 13840617979 | 38195 | `d4a5e2c27feb2d3e300b7cd4fa1c0ac3c4c67cdd9e1764a5a3070e4e5c602801` |
| 13840382793 | 38200 | `4d35394157299564b1f7339b6751306be928186d134d35355ec101bb09e5a944` |
| 13840362369 | 38071 | `c79edc8c404672c1c3cd5082e2a4b706b426995bcdd718b244f91024c1fa9e52` |

The corrected adapter remains **TDD in progress, not complete**, and no corrected native/model gate has run. Future corrected evidence requires its distinct applied-world action receipts and protocol; these 12/12 legacy cases cannot be relabeled as corrected-world PASS. Historical geometry-guide remediation remains a separate documentation follow-up after the PR #27 merge, with no future PR number presumed.
