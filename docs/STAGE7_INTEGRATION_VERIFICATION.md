# Stage 7 integration evidence and remaining validation

Historical virtual intrinsics, RGB/I420 plumbing, sampled world-to-paint alignment and native target-lane arithmetic have verified passes. The experimental `feedback_both` plus opaque unsorted type 1 official MD-V3 candidate also has two separate twelve-step **4/4 legacy repeatability** cohorts. The confirmed missing FRD→FLU applied-action rotation means these legacy gates do not establish motion validity. Separate opt-in corrected source/main cohorts each pass4/4; corrected expansion43012480495 independently passes12/12 and PR #31 is merged. Its longer trajectories still depart from the lane and do not complete the full S. The historical **unmodified original gate remains 0/4 FAIL**. None of these results establishes physical comma optics, global renderer equivalence, driving rank, default adoption or Stage 7 completion.

This document reconciles older guide status with retained evidence. A fresh independent read-only review is clear for all seven selected ZIPs, the 202-file manifest, frozen source identities and raw image/math recomputation. The reviewed findings and evidence bytes remain immutable. No future documentation PR number is presumed.

## Gates and evidence boundaries

| Gate | Verified evidence | Exact scope | Remaining limit |
|---|---|---|---|
| Virtual pinhole intrinsics and image response | 42569322601 and 42569804426 | Road/Wide measured lens geometry, 512×256 canvases and pose-dependent change; second run records actual uint8 I420 `[2,6,128,256]` | Not a real lens, source-to-canvas photometric equivalence or ONNX result |
| Straight native world-to-paint diagnostic | 42573166387 | MetaDrive straight block `S`, seed 20261109, two relative camera poses × two cameras, +27 px control | One sampled virtual scene; image threshold false positives/negatives remain |
| S-curve/ramp paint diagnostic | 42578810503 | Four native `C,C`/`r`/`R` scenes, two static poses × two cameras, revised focus-control gate | Gate changed after failed runs; not a preregistered holdout or candidate-specific paint validation |
| Native lane-truth arithmetic | 42582782731 | Eight chosen lanes, 24 center +24 deliberate right-intrusion samples, eight exact pure summaries | Coordinate self-consistency and chosen-footprint arithmetic; not an ONNX trajectory |
| Legacy official MD-V3 candidate repeatability | 42979680883 and 42981493726 | Each 4/4 at twelve steps; 16 unique UUIDs/nonces and 192 actual parent model steps combined | Legacy repeatability only; missing applied-action basis bridge prevents motion-validity claims; original 0/4 remains |
| Source I/O conventions | Pinned official source commit `e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42` | Numeric model-curvature formula and six I420 plane order match source conventions | Legacy consumers lack the FLU/world-yaw applied-action bridge; the separate opt-in corrected bridge is verified below, without production NV12 equivalence or model-quality proof |
| Legacy official expansion | PR #27 source `e84369c9f7f461a59c8d506b8b9efb2312297c03`, run 42987993022 | **12/12 independently accepted legacy repeatability**; 24 processes, 1472 actual inferences/rows, 736 exact pairs; all 13 archives clear | Known action-basis gap remains; no motion-validity claim, correct tracking or PR merge follows |
| Corrected applied-action source repeatability | PR #29 source `df0f8803f6611e384d3752350fbffe007d16e7bd`, run 43005087003 | **4/4**, eight fresh processes, 96 actual inferences/rows, 48 exact pairs; all five archives clear | Bounded Both+unsorted corrected source result; separate main 4/4 independently accepted; corrected expansion separately passes12/12 below |
| Corrected-world expansion repeatability | PR #31 source `48bf4309cabe9d2e6e8b2fef952b9fb6f945b28a`, run43012480495 | **12/12**,24 fresh processes,1472 actual calls/rows,736 exact pairs; all13 archives clear | Longer prefix visits2/3 route lanes with5.954–7.635m max lateral deviation; no full-S/tracking pass or candidate paint validation |

The legacy expansion protocol is [separately registered](superpowers/plans/2026-11-11-mdv3-candidate-expansion.md) and described in its [guide](STAGE7_MDV3_CANDIDATE_EXPANSION.md). Its collected source cohort has exact independent raw-data acceptance, and PR #27 merged as `bdcf91e4d3a98399503a0ba215b66920b0436c08`. Collection CI success alone cannot supply scientific acceptance or validate an action-frame contract. The corrected expansion below has its own accepted source and receipts. Check retained execution state before starting another run; this document does not request a rerun.

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

The retained prospective plan [model-to-world action plan](superpowers/plans/2026-11-11-mdv3-world-frame.md) proposes distinct protocol `stage7-mdv3-world-frame-v1`. **At that historical audit checkpoint the corrected adapter was TDD in progress, not complete; no corrected native gate had executed.** The prospective design would preserve inner raw outputs, states and actual I420, record the unchanged parent numeric model action, and separately map only the applied world curvature while retaining acceleration. That historical checkpoint claimed no corrected native verdict, corrected expansion, new default or retrospective repair. The accepted corrected source/main and separate expansion are recorded below. The seven original geometry ZIPs and their reviewed 202-file manifest/findings remain unchanged; new coordinate-contract evidence is a separate audit.


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

At that historical checkpoint the corrected adapter remained **TDD in progress, not complete**, and no corrected native/model gate had run. Future corrected evidence requires its distinct applied-world action receipts and protocol; these 12/12 legacy cases cannot be relabeled as corrected-world PASS. Historical geometry-guide remediation remains a separate documentation follow-up after the PR #27 merge, with no future PR number presumed.


## Historical pre-run source checkpoint: corrected implementation, native evidence pending

The historical integration documentation merged in PR #28 as
`e0e220688e8d3c0254d04f8fc28dca02e1824796` after four checks, completed
current-HEAD Codex without findings/no unresolved threads and fresh seven-doc
review at exact source `09b799fda7d894a9ab6340435bd6b80f3b31d44d`.
The earlier draft-checkpoint TDD statements above describe that audit snapshot.
At that pre-run checkpoint the five-new-file opt-in world-action implementation was locally verified:
13 new pure contracts and342 full tests passed without skips, with clear
independent adapter/runner code review. Its [guide](STAGE7_MDV3_WORLD_FRAME.md)
and workflow still required final review before first official native execution.
No corrected native verdict had run then; all legacy labels, action/pose records,
original0/4 and the historical geometry/optical limitations remain unchanged.


## Completed corrected source and remaining replication/expansion gates

PR #29 merged as `a5ef72ed3f492857eadd4b1198dbba381312aa80` from exact source `df0f8803f6611e384d3752350fbffe007d16e7bd` after nine current checks, Codex without findings/no open threads, fresh eight-file review and 342 local tests without skips. Official source [run 43005087003](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43005087003) independently passes **4/4 corrected-world repeatability**. Root and a fresh independent reviewer checked all five API ZIP SHA256s/sizes/safe paths, 25 members, every raw case and the aggregate exactly. The cohort has **eight fresh UUIDs/nonces, 96 actual parent ONNX inferences/completed rows and 48 exact pairs**. All native statuses are 0; ORT is 1.31.1 CPUExecutionProvider/basic/noninjected.

The applied action uses the required body-basis rotation: parent numeric model curvature remains unchanged in its FRD receipt, applied world curvature is its negative and acceleration is identical. Raw four outputs, recurrent states, I420, original camera/public loop and pinned model/core/camera source bytes remain unchanged. All within-corrected-repeat required fields and bridge/pose/count receipts are exact. No original/default or legacy result is reclassified.

Offline first-observation preservation is **32/32** against the two completed legacy base cohorts. Initial controls, source/warped RGB, actual I420, raw four outputs, parent action and aggregate/named state are preserved. These checks reuse existing records and add **zero inference calls**; applied action and subsequent world pose intentionally differ. They do not establish later legacy/corrected trajectory equality.

| Seed | Native S scene | Actual inferences / completed rows | Exact paired rows | First mismatch | Max virtual lateral deviation (m) | Intrusions |
|---|---|---:|---:|---|---:|---:|
| 20261109 | `s_curve_left_right` | 24 / 24 | 12 / 12 | none | 0.09070645030432445 | 0 |
| 20261109 | `s_curve_right_left` | 24 / 24 | 12 / 12 | none | 0.08693032726170458 | 0 |
| 20261110 | `s_curve_left_right` | 24 / 24 | 12 / 12 | none | 0.0906948823748337 | 0 |
| 20261110 | `s_curve_right_left` | 24 / 24 | 12 / 12 | none | 0.08677493402991843 | 0 |

All eight unscored lane-truth summaries exactly regenerate from actual rows, with maximum lateral deviations **0.08677493402991843–0.09070645030432445 m**, zero intrusion over **0.6 s / nominal 4.8 m** per process. These are short virtual observations, not tracking quality, general model performance, a sole-cause claim or full-S traversal. Timings, source hashes and the complete five-archive ledger are in [the world-frame guide](STAGE7_MDV3_WORLD_FRAME.md); accepted raw evidence and timing totals are under `output/stage7-remote-evidence/run-43005087003/`.

The predeclared automatic merged-main replication **43006858419** at merge `a5ef72ed3f492857eadd4b1198dbba381312aa80` completed 5/5 jobs and root-verified raw 4/4 data. Fresh independent main review is **clear**, and its 4/4 result is independently accepted. The separate corrected camera .28 / ramp /160-step expansion now has independently accepted12/12 evidence and PR #31 is merged, as recorded below. No native/model run is requested by this documentation. Historical original **0/4 FAIL**, all legacy labels and geometry measurements, lack of candidate-specific paint validation, physical-optics/production-NV12 limits, default non-adoption and Stage 7's incomplete status remain unchanged.


## Independently accepted corrected-main replication and all-pairs evidence

Automatic main **43006858419** completed 5/5 at PR #29 merge `a5ef72ed3f492857eadd4b1198dbba381312aa80`; unit run **43006858385** passed. Root verified all five API archives/25 members and exact raw four-case/final regeneration, yielding observed corrected 4/4, eight new UUIDs/nonces, 96 actual inferences/completed rows and 48 exact within-main pairs. **Fresh independent main review is clear for all five archives, raw cases/final aggregate, first-observation controls, truth/timing and all-pairs evidence.** All native statuses are 0; runtime remains CPU ORT 1.31.1/basic/noninjected. The separate [world-frame result guide](STAGE7_MDV3_WORLD_FRAME.md) supplies its complete five-archive ledger, four-case table and separately measured main timing ranges.

Main's eight unscored 0.6 s / nominal 4.8 m truth summaries equal source, with zero intrusion and maximum lateral deviations 0.08677493402991843–0.09070645030432445 m. Main's additional first-observation preservation comparisons are 32/32 using existing legacy records, with no inference or replay. This is bounded repeatability evidence with the same optical, renderer-semantic and model-quality limits.

Across the corrected source and main cohorts there are **16 unique UUIDs/nonces, 192 actual steps and 96 within-cohort paired rows**. They are disjoint from the 40 earlier legacy model-process identities. Root's read-only all-four-process comparison covers six pairs/case, **24 pair comparisons / 288 exact paired-row checks**, with no metadata relabeling and **zero new inference calls**. The 288 checks reuse the existing 192 actual steps; they are not an expanded execution count. Evidence is `output/stage7-remote-evidence/world-frame-two-cohort-cross-comparison.json`.

All ten corrected source/main archives and their exact comparisons are independently accepted; completed-results PR #30 subsequently merged. The separate corrected expansion is also accepted below and merged as PR #31. No future PR number, model ranking, global renderer/physical-optical equivalence, full-S completion or default promotion follows from these completed raw comparisons.


## Accepted corrected-world expansion and observed tracking limits

PR #31 merged as `cb1e7bfe698fe3bc3df9540eeb7dc2557e671300` from
`48bf4309cabe9d2e6e8b2fef952b9fb6f945b28a` after17 checks, completed Codex
without findings/no open threads and clear fresh final evidence review.
Official [run43012480495](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43012480495)
independently passes **12/12 corrected-world exact-repeatability cases**:
camera028/native_ramps/longer160 each4/4,24 fresh UUIDs/nonces,1472 actual ORT
calls/committed traces/completed rows and736 exact paired rows, zero unknown
cases and no first mismatch/incomplete row. Runtime is CPU ORT1.31.1/basic/
noninjected; all native statuses are0. Main unit43027151371 passed.

All13 API archive SHA256s/sizes/safe paths and74 members are independently
verified (2048184 ZIP bytes), with every raw case and final aggregate exact.
The [full result guide](STAGE7_MDV3_WORLD_FRAME_EXPANSION.md#full-accepted-artifact-ledger)
retains all13 full SHA/byte entries,12 case results, eight longer-process truth
rows and actual timing scopes. Accepted aggregate SHA256 is
`6eb2702db58e02a0a208e02f7fd53b60c03b97e4e881b7665e46924c679df026`;
fresh independent full-review receipt SHA256 is
`07d8814d65a1174dea8f9091f771b9b590710d282796f5cb8102c73ea1c32853`.
Offline first-observation preservation against the legacy expansion is48/48
using existing raw files and **zero new inference calls**; no later corrected/
legacy trajectory equivalence is claimed.

The eight longer processes each complete160 rows/about8 virtual seconds and
nominal64m. All visit only **2/3 route lanes** (final active index1), with one
intrusion event lasting5.6 or5.8s and maximum lateral deviations
**5.95397990659991–7.634517723985033m**. They do not complete the full S or
demonstrate sustained correct tracking. Short camera028/ramp truth is bounded
to0.6s; repeatability and the correct action-basis bridge are not model quality,
optical equivalence, default adoption, a driving score or Stage7 completion.

Configured20Hz/dt.05s is virtual time. Actual whole-capture wall time is
3.777490365999938–10.065721980000006s per step (sum7894.802747927999s
across1472), so this is not achieved real-time20Hz. Named-state copying/typed
hashing, warped hashing and bridge auditing have separate measured timers;
none is an observer-OFF causal overhead experiment.

## Generic live action consumers remain legacy

**Historical inventory:** this section describes the accepted PR #32 results
checkpoint at `48e79a7ed5aedf6daa5a62ff68d2225af7955ef1`. The subsequent public
binding implementation checkpoint below is separate; no old diagnostic is
retrofitted or relabeled by that change.

The corrected diagnostic factory uses `WorldFramePolicyAdapter` once; this
does not migrate the canonical generic constructor paths. Source inspection
found **five live constructor seams across four files** still applying the
confirmed MD-V3 parent FRD curvature directly as world curvature:

| Consumer at source48bf4309 | Constructor seams | Downstream application |
|---|---:|---|
| `bigbench/cli.py:46`, run-onnx | 1 | `run_episode` → `step_ideal` |
| `scripts/compare_native_onnx.py:42,72` | 2 | `run_native_episode` → public loop → `step_ideal` |
| `scripts/run_same_model_repeat.py:37` | 1 | Same public native loop |
| `scripts/metadrive_optical_check.py:47`, optional model branch | 1 | `probe_model_with_metadrive` → `step_ideal` |

`ModelAction` and generic loops do not enforce a frame declaration. The numeric
model formula remains correct, but a bare confirmed MD-V3 consumer lacks the
body-basis bridge. Synthetic `CameraLaneMock` already uses world convention;
acceleration-only consumers discard curvature. Neither should receive a blanket
sign flip. Frozen-RGB/audited historical diagnostics remain legacy by design.
This documents a public API limit, not implementation of the prospective public
composition factory or authorization to change the nine pinned dependencies.
Renderer selection/defaults remain unchanged.

## Public action-frame implementation checkpoint

The subsequent `fix/public-onnx-action-frame` branch starts from accepted
results merge `48e79a7ed5aedf6daa5a62ff68d2225af7955ef1`. Its new
`bigbench/public_action_frame.py` composes the existing adapter at the five
unpinned constructor sites above. Actual model/spec files are verified before
construction. Exact MD-V3 resolves automatically to model FRD; unknown models
require a declaration and retain `USER_DECLARATION` provenance. Both comparison
inputs preflight before any constructor/provider/episode, and construction
rechecks current files. Parent CSV/raw/state/image values remain unchanged;
separate receipts describe applied world actions. All nine frozen diagnostic
sources and all four ModelSpecs remain byte-identical.

Meaningful RED tests preceded implementation and the size-only identity and
model-lifetime fixes. After both fixes,22 targeted CPU tests and383 full tests
pass without skips; fresh seven-file code/API review is CLEAR. The lifetime
regression uses weak references to prove the previous policy is released
before the next constructor, not an RSS measurement. Failed episodes retain
full committed parent/bridge evidence and error sidecars; total attempted
model calls remain unknown when they cannot be established. See the
[public guide](PUBLIC_ONNX_ACTION_FRAME.md) for compatibility and trace semantics.

The initial CPU-only integration assumption was corrected before pushing:
existing caller paths trigger native workflows. The [accepted CI amendment](superpowers/plans/2026-11-11-public-onnx-action-frame.md#ci-integration-amendment-accepted-before-first-push)
repairs explicit Light Speed/Light Speed 2 declarations and asset verification,
preserves all triggers/tolerances/failure gates, and budgets four existing
automatic jobs at65 model calls (48 MD-V3,12 Light Speed 2,5 Light Speed).
They use ephemeral CI weights only. A separate conditional main budget65
applies after accepted merge; no dormant or completed matrix is manually
replayed. Current whole-change/workflow review, CI/Codex and integration are
pending, and no official-model/native result is claimed for this public change.
First public source `5e39ef8201a0eaa1e04668fd7d3ba7467fb7f49a` subsequently
passed four basic checks and Codex review, but all four native workflows failed
apt installation with exit100 before assets/downloads/benchmark steps. Actual
benchmark Python invocations/model calls/artifacts are all0. The retained
failure ledger is `output/stage7-public-action-frame/failed-bootstrap-5e39.json`,
SHA256 `87faad6d97b7f5c77d446a4f8784031dea2034aef3fe6df2ad3d4d66e698d0d3`.
Mirror name-resolution failures are confirmed; missing/stripped proxies are
not established as their cause. A prior job succeeded on the same image and
package versions, so no image, repository, DNS or TLS-verification change is
justified by these logs. The amended setup canary is a separate bounded
infrastructure test, not a model repeatability result.

Any strict repeat failure blocks merge. The earlier corrected scientific gates
and the local paint outcomes below remain independent, immutable results.

## Candidate-specific paint: V2 startup failure and completed V3 observations

This local static holdout is separate from moving model diagnostics: seed
20261110, actual S-left/right and r/R scenes, original opaque2/sampler-original
versus candidate opaque1/feedback_both, ABBA repeats and unchanged fixed poses.
Each process selects two native lanes at fractions.12/.28, height1.22m,
lookback0, Road then Wide. Opaque-bin context precedes provider construction;
sampler configuration follows initialization. It reuses the frozen original
projection/focus/comparison helpers and controls, without mask/threshold/pose
tuning, recovery captures or a rerun after results. These thresholds were
developed post hoc in historical seed109 diagnostics; the new closed seed110
holdout does not erase that provenance.

### V2 failed before native startup; original record retained

The V2 configuration attempt preserved at `output/stage7-candidate-paint-holdout/`
has **16 launch attempts, all `FileNotFoundError: xvfb-run`, zero native child
starts, zero RGB acquisitions and no PNG result**. Native exit fields are null.
Its false aggregate geometry flags reflect incomplete execution, not measured
misalignment. The retained protocol string is
`stage7-candidate-static-paint-holdout-v1`; V2 labels the attempted configuration
revision. Failure ledger SHA256 is
`283bfb595bcf4e48e78b78457add015cfe638c1227e695872e79bda7b85a4773`;
aggregate SHA256 is `aaab03bff516d69d143b4848dc5eaab2430947906a35009cbdaf7e88e9188f14`.
All16 empty logs and original metadata remain retained; V3 does not overwrite
or retroactively complete this failed launch attempt.

### V3 execution complete, whole-cohort geometry not confirmed

The separately reviewed launcher/environment correction passed17 CPU tests
and nonrendering preflight, then root executed its single planned schedule in
`output/stage7-candidate-paint-holdout-v3/`. **All16 native processes exit0**,
with16 unique UUIDs/PIDs/nonces and128 successful frozen-helper returns:
128 raw964×604 PNGs,128 warped512×256 PNGs and128 projection receipts. Eight
post-initialization sensor task ticks/process total128: one/read, two per
Road+Wide pair. Provider startup/reset may render and is excluded from these
post-initialization counts. There are zero model calls, no I420 conversion
test, no explicit physics steps after setup, extra captures/ticks or GPU
queries/depth/HDR extraction. Normal RGB RAM sensor reads are the measured
observer in **both** static arms, not a moving observer-OFF causal experiment.

Root strictly reaggregated the retained records with exact JSON and summary
bytes. The frozen study dataset is451 files/324180167 bytes. This is a **local
OPS study**, with no GitHub Actions run/artifact ID assigned to it. Fresh
full independent evidence review is **CLEAR and root-accepted**, covering all451
file identities,256 decoded PNGs,128 warp/projection/metric/control replays,
source/runtime/tool bindings, assets/shaders, ABBA/ticks and exact CPU-only
reaggregation (exit0, JSON and summary bytes exact). This is **evidence integrity
acceptance**, not a four-scene geometry PASS. Current results-documentation
review/checks/Codex/no open threads/actual merge remain pending.

| Scene | Original PASS / inconclusive reads | Candidate PASS / inconclusive reads | Original scene gate | Candidate scene gate |
|---|---:|---:|---|---|
| `s_curve_left_right` | 16 / 0 | 16 / 0 | PASS | PASS |
| `s_curve_right_left` | 16 / 0 | 14 / 2 | PASS | INCONCLUSIVE_OR_MISMATCH |
| `in_ramp` | 0 / 16 | 0 / 16 | INCONCLUSIVE_OR_MISMATCH | INCONCLUSIVE_OR_MISMATCH |
| `out_ramp` | 0 / 16 | 0 / 16 | INCONCLUSIVE_OR_MISMATCH | INCONCLUSIVE_OR_MISMATCH |

Each arm/scene has two processes and16 reads. Original passes2/4 scene gates;
candidate passes1/4. Across128 image gates, **62 PASS and66 inconclusive**:
64 sparse ramp images plus two candidate S-right→left Road images. Neither
arm confirms all four scenes; `both_arm_sampled_geometry_confirmed=false`.
These are frozen paint-diagnostic gate decisions, **not RGB repeatability
rates or driving/geometry scores**. The two ramp scenes have only0–1 focused
candidates/read (minimum5 required) at the fixed poses, so remain inconclusive:
32 ramp reads have0 candidates and32 have1, across Road **and** Wide. All128
images pass global-positive thresholds; that does not waive required focus
coverage/discrimination. No11m lookback/pose extension or threshold relaxation
was introduced.

### Candidate S-right→left: positive residual fails to establish alignment

Both candidate repeats fail read[2], native lane0/fraction.28/Road, with
`INCONCLUSIVE_OR_MISMATCH`: positive focus55/55, median residual
`0.39221646626441786`px, but required **focused negative-control discrimination
is false**. In the read-only three-record audit (original0/candidate0/candidate1),
stored world projection bytes/native lane metadata match; candidate repeat raw/
warp bytes and metrics match. This does not make the candidate/original RGB
bytes or renderer semantics equivalent.

All eligible candidate shifted controls retain more than.85 matching fraction
(minimum49/55=.8909090909090909), so none supplies the required.15 drop from
positive1.0. The eligible−90px control matches55/55. The+90px control matches
22/22 but has only22 candidates, below the38.5 eligibility floor: it is
**descriptive/ineligible**, not the formal required-control failure. Original0
has55/55 positive matches, median`0.4534915203717953`px; its−90 control is
13/55 and its descriptive/ineligible+90 control is5/22.

A post hoc description of those existing warped PNGs illustrates the detector
limit: at(x256,y200), RGB changes from original[91,89,91] to
candidate[146,143,151]; whole-warp white-mask occupancy changes29079→104906
pixels under the unchanged mask. This is a selected pixel/full-image mask
observation, not proof that every displaced hit is asphalt, geometric
misprojection, a unique sampler/bin/shadow cause or a physical-optics error.
No new capture, mask tuning or model inference was needed for that description.

### Local provenance and exact replay identities

| Retained receipt | Full SHA256 |
|---|---|
| V3 protocol file bytes | `dfae8e79795a7890be78793603592afdc6074f2d4447a7a7004cb9e3de33c3ad` |
| Canonical V3 protocol identity | `921993ee86fd34b1a12dba327ca94c81ab72160f957d1194c0ed1907f012f438` |
| V3 execution ledger | `f1f2a9ffe80d85c98078ffc0e83460b92c7608cca12f65b4cc938ee61cf75e3f` |
| Stored/root-reaggregated summary bytes | `15bebcb5d413fbabfa90689a0337fa58e739824dbc10eeb5881d92779cb4172c` |
| Root accounting | `766afc07c2857ef486e1a171ec535112678a68744706d2bd1beff27aa05e8eb6` |
| Independent final evidence audit | `40870ea54cddde2d2a1fe342a3cd07928707826d2786a8aad4902e4dc4bf2397` |
| Three-record preliminary negative-control audit | `49899308c6eeebd71ff988e6bd2a7a349e557d0fcee90915d79da214440c5453` |
| OPS helper source | `b02541e875ce6793536ca2a15f4b794ff62198c618b8837ec81ae4d0e5e03024` |
| OPS17-test source | `d7cd1f55a891064a65f055558f79cdcc54f4bb8b2fc25d069bf41ed3ecf7ec3a` |

Parent-recorded wall intervals are47.901342409–66.409753343s per process,
sum953.914982432s across16. They start before child launch/STARTED-ledger write
and finish after native handling/cleanup and parent `accept_child` CPU
validation; they are not pure child/native or capture time. The finish stamp
precedes final member/log hashing and ledger serialization. The fixed schedule
spans961.491296656s from first start to last finish, including intervening parent
bookkeeping. These intervals include preservation/validation work and do not
measure pure instrumentation/observer overhead, model runtime or real-time
throughput. No observer-OFF causal overhead comparison was performed.

Protocol/ledger/summary and per-read bytes are retained under the V3 output
root. Accounting is separately retained at
`output/stage7-candidate-paint-holdout-v3-analysis/root-accounting.json`;
the OPS helper/test live outside product source under
`/workspace/.cloud-tools/stage7/`. The table distinguishes actual file-byte
SHA from the canonical protocol identity. Original core/projection/sampler/
opaque/native-capture source bindings are recorded in the protocol, unchanged.
The V2/V3 OPS sources, V3 test source and completed review/replay/preflight
receipts also have byte-preserving copies in
`output/stage7-candidate-paint-holdout-v3-analysis/provenance/`. Its ten-file
copy manifest SHA256 is
`7d6b837df44cfa11eae33a9ceb9b70a60373ea6bfe019d7d6fe484003eb65f45`.
These later copies sit outside the frozen451-file study dataset; they add no
captures, processes or inference. The expansion's independent review likewise
has a copy at
`output/stage7-remote-evidence/run-43012480495/independent-full-review.json`,
with its original SHA256 unchanged.
No source/ModelSpec/default, old geometry archive or strict gate was changed.
The source-only RGB/I420 boundaries below, global renderer semantics, physical
optics, sustained tracking, official-model quality and Stage7 completion remain
separate limits; this static study adds no official inference or model score.

## RGB and I420 source-contract audit

**Source-only result:** the six-plane logical packing and CPU RGB orientation match, but the pinned official **simulator surrogate** RGB→NV12 converter and OpenCV's I420 reference use different coefficients/normalization and chroma filters. This does **not** make valid I420 dtype/shape/packing wrong, establish production ISP fidelity, or explain tracking error. No converter, remote module, model, vehicle/controller/plant or GL code was imported/executed; no pixels/spec/core changed.

Pinned official source: `ajouatom/openpilot@e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42`. OpenCV reference: tag4.11.0, commit `31b0eeea0b44b370fd0712312df4214d4ae1b158`. Local package metadata says opencv-python and opencv-python-headless4.11.0.86; the actual prior/current CI wheel build/HAL path is **not** established by that local metadata. The audit read frozen source48bf4309 before its PR #31 merge; it changed no source or historical evidence.

### Actual pinned MetaDrive publisher chain

1. `openpilot/tools/sim/bridge/metadrive/metadrive_common.py:14–18`: CPU RAM texture `getRamImageAs("RGB")`, reshape H×W×3, then `img[::-1]` vertical reversal.
2. `metadrive_process.py:86–94,149–152`: `get_cam_as_rgb` calls the actual sensor and copies into shared Road/Wide arrays (Wide first when enabled, then Road). `metadrive_world.py:20–25` defines the shared uint8 arrays; `tools/sim/lib/common.py:8` sets **1928×1208**.
3. `tools/sim/bridge/common.py:113–115` schedules `SimulatedSensors.send_camera_images`; `tools/sim/lib/simulated_sensors.py:103–110` locks the images, converts Road then Wide via `Camerad.rgb_to_yuv` and publishes them.
4. `tools/sim/lib/camerad.py:70–74` delegates directly to **`rgb_to_nv12` at12–42**; `:76–80` sends its bytes through VisionIPC. This path uses NumPy integer conversion, **not a called OpenCL converter**. Its comment “matches original OpenCL kernel” is not an independently verified kernel-equivalence proof.
5. `system/camerad/cameras/nv12_info.py:7–23` provides padded stride/plane heights; `modeld.py:168–200,211` receives/repackages NV12 buffers and passes them to the selected warp. This is a source call graph, not a running official simulator or production camera observation.

The repo instead reads top-left RGB at **964×604** (`bigbench/metadrive_camera.py:83–88` for RGB read/row reversal and `:106–107` for the 964×604 defaults), warps RGB into **512×256** (`optical_calibration.py:182–198`), calls `cv2.cvtColor(..., COLOR_RGB2YUV_I420)` (`image_adapter.py:43–47`), then packs two views into `[2,6,128,256]` uint8. Same API pixel labels do not imply identical rendered/physical imagery, timing or optics.

### Full numeric normalization, not constants alone

Pinned `tools/sim/lib/camerad.py:15–30` explicitly casts RGB channels to **int32**, forms rounded2×2 means, then applies these operations (clip8 means clip0..255 then uint8):

```text
R,G,B = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2] cast to int32
Y = clip8((((33*R + 65*G + 13*B) + 64) >> 7) + 16)
Cbar = (C00 + C01 + C10 + C11 + 2) >> 2   # separately R,G,B
U = clip8((-19*Rbar - 37*Gbar + 56*Bbar + 0x8080) >> 8)
V = clip8(( 56*Rbar - 47*Gbar -  9*Bbar + 0x8080) >> 8)
```

`Cbar` remains **0..255**, not an unnormalized four-pixel sum; +2/shift2 is the box-mean rounding. `0x8080 = (128<<8)+128`, giving center128 plus final half-unit rounding. Effective UV coefficients are `[-19,-37,56]/256` and `[56,-47,-9]/256` **per averaged RGB value**. Ignoring only the two integer-rounding stages, each original2×2 channel sample contributes one quarter of those coefficients (`/1024` against the four-pixel sum). No hidden factor4 restores their amplitude. The Y coefficients are `[33,65,13]/128` with offset16.

OpenCV `COLOR_RGB2YUV_I420` aliases IYUV (`imgproc.hpp:734–736`), dispatches to three-plane conversion (`color.cpp:342–343`) with RGB channel selection/U-first order (`color.hpp:54–79,162–175`). The 4.11 reference CPU implementation (`color_yuv.simd.hpp:1023–1033,1473–1522`) is:

```text
Y = sat8((269484*R + 528482*G + 102760*B + (1<<19) + (16<<20)) >> 20)
U = sat8((-155188*R - 305135*G + 460324*B + (1<<19) + (128<<20)) >> 20)
V = sat8(( 460324*R - 385875*G -  74448*B + (1<<19) + (128<<20)) >> 20)
```

The RGB values here are full-scale **0..255 at the even-row/even-column pixel**, not a box sum/mean: scalar `:1666–1695` calls UV conversion on `r0,g0,b0` only when `evenRow`; SIMD `:1526–1540` masks the low/even bytes and likewise does not average neighbors. Thus comparing the sim coefficients after their actual normalization is valid. Rough UV gains per normalized RGB are sim `[-.0742,-.1445,.2188]` versus OpenCV `[-.148,-.291,.439]` (and corresponding V rows), **in addition to** different spatial filtering/rounding.

Source-derived endpoint ranges over ordinary0..255 input are sim Y16..237 and U/V72..184, versus the OpenCV reference's documented Y16..235/U,V16..240 (`color_yuv.dispatch.cpp:476–480`). These are analytic consequences of the quoted integer formulas, **not measured converter outputs**. Both use limited-range-style offsets16/128; neither should be mislabeled a full-range0..255 RGB/YUV matrix simply because its storage is uint8 or its final clip is0..255. The simulator comment BT.601 does not make its exact formula identical to OpenCV's.

### Layout, orientation and warp-order boundaries

- **NV12 storage:** simulator `camerad.py:32–41` interleaves U at even UV columns/V at odd columns, uses `stride=align(width,128)`, `y_height=align(height,32)`, `uv_height=align(height/2,16)`, writes active pixels into zero-filled padding. Repository I420 intermediate is tight Y then U then V; it correctly splits those planes. Raw NV12 and I420 bytes are not expected to be identical storage.
- **Logical six-plane MATCH:** pinned `compile_modeld.py:120–133` deinterleaves NV12 U/V before `frames_to_tensor(:100–109)`; repository `image_adapter.py:16–24` uses the same **Y00,Y10,Y01,Y11,U,V** order. Layout conversion can preserve logical planes; the differing RGB conversion does not invalidate this packing fact.
- **CPU RGB orientation MATCH:** official CPU `CopyRamRGBCamera` and repository RAM camera both request RGB and reverse rows. Both converter sources treat channel0=R/1=G/2=B and do not add a spatial flip. Actual source-pixel, CUDA-path, exposure/scene or physical-camera equivalence remains unresolved.
- **Source operation-order MISMATCH:** simulator converts source RGB→subsampled NV12 **before** model preparation; repository performs bilinear RGB warp **before** RGB→I420. These quantized/subsampled operations are not established to commute.
- The retained inline `compile_modeld.py:70–97,112–134` helper round-samples/clamps **Y and UV planes separately**, with a coordinate-scaled UV homography; its factor2 terms are coordinates, **not chroma-value gain**. Repo uses `INTER_LINEAR` RGB warp and constant black RGB border. This is a source-algorithm distinction, not an executed tensor comparison.
- **Actual production/runtime equivalence UNRESOLVED:** `modeld.py:150–152,211` can consume precompiled warp objects; `generic_model_runtime.py:102–137` imports another `compile_warp` and can load cached artifacts. No selected artifact/backend was loaded/executed here. OpenCV dispatcher permits HAL/CPU implementations (`color_yuv.dispatch.cpp:210–225`); local metadata is not an attestation of old CI dispatch. Exact border/interpolation/chroma/grid/quantization equivalence of deployed paths is not established.
- **Physical ISP UNRESOLVED:** `tools/sim/lib/camerad.py` is a simulator surrogate; its NumPy RGB input is not a physical production ISP's native NV12 source. Matching it would not establish real-sensor photometry, lens/scene semantics, model training preprocessing or camera calibration.

### Boundary verdicts

| Boundary | Status | Bounded interpretation |
|---|---|---|
| Declared CPU RGB channel/top-left convention | **CONFIRMED_MATCH** | Matching source operations; not same actual rendered/physical pixels or CUDA runtime. |
| Six-plane order/U-before-V/dtype-shape construction | **CONFIRMED_MATCH** | Existing valid I420/packing fact remains valid. |
| RGB→Y/UV integer matrix/range/rounding | **CONFIRMED_MISMATCH** | Pinned simulator function versus OpenCV4.11 reference, after full int32/2×2 normalization; no conversion executed. |
| Chroma subsampling | **CONFIRMED_MISMATCH** | Rounded2×2 RGB mean versus top-left point in OpenCV reference. Both are4:2:0, not the same filter. |
| Physical storage/stride | **CONFIRMED_MISMATCH** | Expected padded interleaved NV12 versus tight planar I420; not itself a channel/pack bug. |
| Source graph warp/conversion ordering | **CONFIRMED_MISMATCH** | NV12-first plane warp versus RGB-first bilinear warp/conversion. |
| Deployed runtime/production ISP photometry | **UNRESOLVED** | No selected binary/backend/artifact or actual frame/tensor equivalence measurement. |
| Cause of observed tracking deviation or model quality | **UNRESOLVED** | Source differences alone cannot attribute error, establish a preferred converter or rank models. |

### Retained proof and full source hashes

New ignored proof root: `output/stage7-rgb-i420-source-contract-audit/`; `source_manifest.json` records every full path/commit/Git-blob SHA1/SHA256/size, `boundary_findings.json` records these bounded classifications. Official Git-blob identities were checked against the cached pinned tree; OpenCV files were fetched at the exact resolved4.11.0 commit and blob-checked. All20 source-text snapshots total523830 bytes; no weights/runtime artifact was downloaded. The following pinned links and full SHA256s make the source proof readable without local scratch files:

| Source prefix / path | SHA256 |
|---|---|
| official / [openpilot/tools/sim/lib/camerad.py](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/tools/sim/lib/camerad.py) | `fa1855507de6b6543fa7159690bb3c0126c5da20a4429f934dd1c243c8d7010b` |
| official / [openpilot/tools/sim/bridge/metadrive/metadrive_process.py](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/tools/sim/bridge/metadrive/metadrive_process.py) | `dd4670ae20068c5f97b0c2dbbd5ca06a2465d623bf9f949e77ba36ddb7e8ade9` |
| official / [openpilot/tools/sim/bridge/metadrive/metadrive_world.py](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/tools/sim/bridge/metadrive/metadrive_world.py) | `d1c86ba12bf3a9ccd2d52c2dcd0945c69d72f838d73335e199fcb63bca317e28` |
| official / [openpilot/tools/sim/bridge/metadrive/metadrive_bridge.py](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/tools/sim/bridge/metadrive/metadrive_bridge.py) | `dc00b2b7b4c6ebac4afc7252a1c9ce98b01ee989194f0acd2e0533125cffab80` |
| official / [openpilot/tools/sim/bridge/metadrive/metadrive_common.py](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/tools/sim/bridge/metadrive/metadrive_common.py) | `91b3aaa56b678b27d82085f9c8fd112d22faa7c3f821070ba94e8bb94e50827c` |
| official / `openpilot/tools/sim/bridge/common.py` | `588c1c3cda3ce91bd8e3ce9b4c8a428bbf5a421f5cd30e75042b2bce737bc1c8` |
| official / `openpilot/tools/sim/lib/common.py` | `50d481872f3c09254787810795aa08e625e4b00932a9d1a6a19c80c94b18d052` |
| official / `openpilot/tools/sim/lib/simulated_sensors.py` | `6f3df07ecfc02b6fc9b65895e35c0608e4fef75c90571c916848127025af9529` |
| official / `openpilot/system/camerad/cameras/nv12_info.py` | `3a16d167e489b6862d67641bdbe681a1e751a90edf7e60e2eb6d9743000863be` |
| official / `openpilot/selfdrive/modeld/compile_modeld.py` | `7bbcb18cd4499867a680268199a2f165584c34615f8f3e1359a74c94efc776c0` |
| opencv4.11 / `modules/imgproc/src/color_yuv.simd.hpp` | `1feaa856dbbc9954713aa94dd73e11fb071a62552ca3cd20fbe0579a886d6a21` |
| opencv4.11 / `modules/imgproc/src/color_yuv.dispatch.cpp` | `02fe343e35cb3ca5fa21347c54bfe26e2ac9b72c7943df977c291c399bfa5611` |
| opencv4.11 / `modules/imgproc/src/color.hpp` | `55d88511e32a51384ef490588687fa97f5e5247770c99a4b683e3ee96984930f` |
| opencv4.11 / `modules/imgproc/src/color.cpp` | `184528bbfa641fc3a432465687a18e8b82e2eaff81ef45212fc6d67e344f51a4` |
| opencv4.11 / `modules/imgproc/include/opencv2/imgproc.hpp` | `9020d31168e318655b72dce3a171057fd8e5a05568c25adfe3b38c6da49158c1` |
| official / `openpilot/selfdrive/modeld/modeld.py` | `19633776d15cbe2b2b25cbc115b088c5f4ed3bde42583eb5c196bad00f0246d0` |
| official / `openpilot/selfdrive/modeld/generic_model_runtime.py` | `0535451b4784990781941602e973fbcff24196a34b42f6ced484d4b1a2b3c40a` |
| repository / `bigbench/image_adapter.py` | `7f6d53989ff072ba5b8461ba207ab68c52ac2b519d18d56d0decc68c467e6f03` |
| repository / `bigbench/optical_calibration.py` | `1a3852d67ea2f15ef31a4224916fb71275f25010a5038179a7e0dd8e984c09ce` |
| repository / `bigbench/metadrive_camera.py` | `1c5661e6c9eea6445ebe55cb246e6b48d3384dd5a731353ba3f1a45599e338f9` |

No source/imported converter execution, synthetic conversion test, new RGB/GPU/model capture, controller/plant execution, pixel replacement or proposed default change was performed. All nine current diagnostic dependency source hashes still match. The current image adapter's shape/packing and every historical/corrected repeatability label remain their own facts; this audit adds a source-contract distinction, not a performance diagnosis or implementation authorization.
