# Public ONNX action-frame native regression — completed, strict repeatability failed

The bounded source regression at **`a4f13887b70208470d7fb6edaf507281d8a4551f`** completed65 real model calls and all six episode reports. Parent/action-frame bindings validate, but the mandatory repeated MD-V3 diagnostic **FAILS**. [PR33](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/33) stays **DRAFT/open/unmerged**. No main regression has executed. Completed code review, basic CI, valid artifacts and a technically successful paired job do not override the strict failure.

## Source and actual execution

The branch is `fix/public-onnx-action-frame`, based on main `48e79a7ed5aedf6daa5a62ff68d2225af7955ef1`. The only phase2 runtime-config changes copy the accepted optical bootstrap into three model workflows; all triggers, parameters, suffix steps, thresholds, defaults and13 diagnostic/ModelSpec pins remain unchanged. Accepted no-model canary43095045331 belongs to earlier actual source `b56226c1e824099f5335adf5559e2dc1ee238a06`, with separately proven runtime equivalence, not an exact-a4f1388 model result.

| Run | Native job result | Complete reports/rows | Actual calls | Retained repeat decision |
| --- | --- | --- | ---: | --- |
| [43103222937](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43103222937), MD-V3 bounded-convergence repeat | **FAIL**, benchmark exit1 | 2 ×12 | 24 | `REPEATED_DIAGNOSTIC_MISMATCH` |
| [43103223193](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43103223193), MD-V3/LS2/MD-V3 | SUCCESS, technical comparison | 3 ×12 | 36 | A/A `REPEATED_DIAGNOSTIC_MISMATCH` |
| [43103223022](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43103223022), LS1 camera/model I/O | SUCCESS | 1 ×5 | 5 | No repeatability test |

Actual calls are **MD-V348 + LS2 12 + LS1 5 =65**. There are65 completed rows,65 parent-trace entries and65 applied-action bridge records, checked against source and complete reports. Embedded receipts and six matching sidecar files are copies of the same evidence; they are not extra graph calls. Only LS1 exports a5-row `model_inference.csv`; repeat/pair traces are JSON. Root and independent CPU revalidation make0 additional model/native calls.

Three configured native benchmark Python commands execute six sequential report-backed policy/world objects. There are no per-repeat OS PID/UUID/session receipts: this is **not six independently attested OS processes** or a fresh-process scientific cohort. Source creates one ORT session per policy, but actual runtime/session identities are not exported. Official weights remain only on ephemeral CI runners; local revalidation compares reported verified identities and pinned source/specs, without downloading/rehashing weights locally.

| Model | Verified/reported weight bytes | Weight SHA256 | Spec SHA256 | Parent-action basis / provenance |
| --- | ---: | --- | --- | --- |
| MD-V3 | 768750198 | `35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199` | `689f4d80082070b08ff35920e37d7070e811dfb42a279909751f79e900c735e2` | verified identity / FRD |
| Light Speed2 | 768749892 | `909a140019050a9d7f00db22dd4f4085928d2af9474a82244672ddab964f95a8` | `2ce9b7caaa50649612d8323c66d9bc193b4c89d39fb399ec00553055d3f87afa` | USER_DECLARATION / FRD |
| Light Speed1 | 792305602 | `6274eb4a3f3eb7ad1ab341d222bbba2ba709b06645dbbd15ac4971d6cb22ab21` | `f25bd9ef91503831b64de47be68c65a6a336e2f9fd348894e1c67902998ebe5a` | USER_DECLARATION / FRD |

MD-V3 `source_basis_verified` is true for the exact known triplet. Both LS bindings retain false: their FRD declaration is an operator declaration supported by the documented publisher convention, not a learned-weight basis certificate. Every bridge rotates parent curvature once into world FLU and preserves acceleration; parent traces, raw numeric outputs and timing exports are not rewritten. The binding's own `total_executed_model_calls` stays null;65 is the separate source-and-complete-evidence revalidation count.

## First divergence and causal limits

Both cases are seed20261109/S-left-right,12 model steps at fixed8m/s and virtual dt0.05s. The comparison requests a full-S route but the12-step interval is only a0.6s/nominal4.8m prefix; it does not complete the S or rank models.

| Comparison | First Wide canvas difference | First Road canvas difference | Packed-input sum at first difference | First applied-curvature difference | Maximum recorded position disagreement |
| --- | ---: | ---: | --- | --- | ---: |
| Bounded-convergence repeat | step2 | step3 | 48403935 /48403952 | 0.0063323974609375 /0.006336212158203125 | 2.22775385196078e-05m |
| Paired MD-V3 A/A | step4 | step5 | 48623340 /48623323 | 0.00788116455078125 /0.00787353515625 | 2.563175262204776e-05m |

At the first differing canvas in both cases, the **preceding recorded integrator pose is exactly equal**. The changed Wide canvas and packed input are therefore present before the current-step action is integrated. Action/post-step pose first differ at that same step; this does not establish equality of unrecorded native camera/PSSM/GPU/task state or all recurrent tensors. It is not a controlled before/after-factory attribution experiment.

`image_checksum` is the sum of the actual packed `new_img` tensor modulo2**32, computed by the frozen bare policy after validated graph execution. A different sum proves different input bytes. Equal sums would not prove equal tensors. The ±17 sum differences are **not changed-pixel counts**. Full per-step input SHA/tensor bytes, raw four-output arrays and named recurrent-state snapshots are absent from these generic artifacts.

In the strict run, both source-RGB hashes are null through the convergence wrapper; source964×604 bytes and first changed pixel coordinates/counts cannot be recovered. In the paired run, retained pre-warp Wide source-RGB hashes first differ atstep4 and Road atstep5, but source PNG bytes are still absent. Neither case identifies a unique sampler/PSSM/cache/pointer-order or timing microcause. Input nonrepeatability is established; pure ORT nondeterminism, physical optics and tracking causality are not.

The first strict Wide hashes are `79c6f1fb8a1f20726ca654780cd164d5e0c224cc4f0fb3253b470a0956863914` / `e901b55c3f9999a476a5349880e4d10ec06eb31063d307bc958293cc86c02cf3`; Road is still identical atstep2. The parent raw lateral values are−0.4052734375 /−0.405517578125 and unchanged long actions−0.041961669921875 /−0.0419921875. The checked basis rotation produces the positive applied curvatures shown above without erasing their difference.

Each strict episode completed12 same-pose convergence samples with0 failed samples. Maximum attempts observed were3 and6; maximum changed pixels accepted within those convergence comparisons were15 and8. Declared bounds remain6 captures,16 pixels and channel delta10. Same-pose bounded stability did not yield equality across the two independently initialized worlds. These15/8 counts describe within-sample acceptance, not the cross-run first changed pixels. No threshold was relaxed and no frame/pixel was replaced.

The paired workflow keeps its existing limited gate: initial Road camera SHA equality is true and technical reports are complete; its recorded A/A mismatch is not a successful repeatability gate. The standalone strict job exits1, skips its subsequent binding-verification step and preserves all five artifact files. Root/independent binding replay passes separately; it never changes that failed CI verdict.

## Raw archive and independent replay ledger

All three API digests/sizes and19 safe ZIP members were checked,407251 ZIP bytes total. Both saved repeat decisions regenerate exactly with the unchanged comparator. LS1's two saved last canvases and I420 plumbing also revalidate. All65 per-step parent/applied actions/rows pass the identity/trace/bridge checks; none is missing or incomplete.

| Kind | Artifact ID | ZIP bytes | Members | ZIP SHA256 |
| --- | ---: | ---: | ---: | --- |
| repeat | 13891659277 | 13689 | 5 | `62ac0196775430805e4df0da3d4a3605db50bc4d9b9a4dd617f88410b9a2007e` |
| pair | 13892982713 | 26102 | 9 | `bcc812aa06053cefd4dc38f569d47acba1483150234d404f452615a9e00bb16a` |
| light | 13893550134 | 367460 | 5 | `da4b834c866c29e5d9635eee2d61d1403a25ac912a27852519264b7798484e15` |

| Derived evidence | SHA256 |
| --- | --- |
| Strict source audit `audit-repeat.json` | `32b8f9a82903d7b9a9ce89eb812258b6f44a2ae0f9bc30337bd3454b98ac4c14` |
| Paired source audit `audit-pair.json` | `e2dfc38e6928dbe9bcbf9bafd8b790facdf1c1806edace162b7544c58f9a3de0` |
| LS1 source audit `audit-light.json` | `a8d5c64e4325b2b5c55ec1a6b29046aff2dd6c593d346820d5019829e97ec248` |
| Independent phase2 raw review | `bdb395f95ca3675ce5ff795af6542350c1700b0effdbc1aa0f9036b63f87a85e` |
| First-difference chronology | `a6a9fd4559be40da24673738fc154c10dac282469422930a0a4d068671f98cf3` |
| Bound15-file source manifest | `3d234923ab8ebc7a6f3aa12dc9e60f863c0b5162197ef37772c0e5459175d6d5` |
| Fresh whole18-file source review | `df35f2dbdb195c4f721694f748bcb66d0b86035e9cd6e462610eef8496fce978` |

Proof root is `output/stage7-public-action-frame/phase2-resume/`; unchanged API/ZIP/extracted records are under `output/stage7-remote-evidence/run-<id>/`. Source job logs are retained with a full hash ledger. Independent revalidation confirms65 calls and both mismatch verdicts; **artifact/frame-binding CLEAR coexists with strict repeatability FAIL**.

## Integration status and exact next action

Source basic runs43103223109/43103463642 passed4 jobs. Together with native results, source Actions has **6 successful jobs,1 failed,0 pending**. Source-a4f1388 Codex completed without findings and GraphQL had0 unresolved threads. Fresh whole-branch review is CLEAR, independently rerunning22 targeted CPU tests without skips and verifying13 pins/15-file manifest. Those are source/code acceptance facts, not native gate acceptance. The older383-test no-skip local result remains its separate source checkpoint; no new full local suite is claimed.

**PR33 stays DRAFT/open/unmerged.** No source-native retry or conditional main execution is authorized by these results. Main's65-call conditional budget remains unexecuted (**actual0**). A later doc-only commit must query its own basic/Codex checks and preserve this source's blocking failure; absence of a native trigger on docs cannot wash the failure away. No code/default/converter/threshold, Cloud setting or publication changed after measurement.

The next scientific step is a separately bounded and reviewed diagnostic design to retain the **actual accepted raw/warped buffers and actual-feed identity at the first divergence**, using existing captures rather than extra GPU reads/re-rendering, with an unobserved control and observer CPU-overhead accounting. Missing pixel coordinates/state/GPU evidence must stay unknown until collected. Declare its process/call/storage budget and source bindings before any new run; do not blindly repeat these65 calls, replay completed cohorts, switch to a passing renderer candidate as a default, change preprocessing or tune actions to force PASS.

Original scientific0/4FAIL, corrected candidate expansion12/12, V3 original2/4/candidate1/4 geometry and physical-optics/full-S/tracking limits remain unchanged. **Stage7 is incomplete; no real-vehicle/CAN/CD210/Carrot or model ranking work was performed.**
