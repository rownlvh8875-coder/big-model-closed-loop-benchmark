# Four validation actual results · 2026-11-18 KST

**Full-S traversal FAIL 0/4; strict repeat PASS 4/4. Physical optics, actual Windows GPU/MSAA, and CARLA remain unverified. Stage 7 is not complete.** These results do not rank model driving quality.

| Track | Actual result | Boundary |
|---|---|---|
| Full prescribed S route | FAIL, all four conditions stop at first lane intrusion | Eight fresh official model processes, exactly 554 inferences |
| Virtual geometry/pinhole | PASS, four native probes, two poses × two original cameras each | Actual source RGB and warped RGB replay exactly under NumPy 2.4.6 / OpenCV 5.0.0; no physical dataset |
| Physical camera correspondence | BLOCKED | No measured offline images/calibration/independent poses supplied |
| Hardware GPU/MSAA | NOT_RUN on user's Windows RTX 3050 Ti | Hosted renderer is llvmpipe software, no physical GPU evidence |
| CARLA cross-engine | BLOCKED | No actual dedicated CARLA server connected; new adapter has pure/fake contract tests only |

| Seed | Scene | Steps per fresh trial | Virtual time | First intrusion (m) | Exact pair |
|---|---|---:|---:|---:|---|
| 20261109 | s_curve_left_right | 60 | 3.00 s | 0.009416859504221886 | PASS |
| 20261109 | s_curve_right_left | 90 | 4.50 s | 0.019439432303138826 | PASS |
| 20261110 | s_curve_left_right | 62 | 3.10 s | 0.008491617684201369 | PASS |
| 20261110 | s_curve_right_left | 65 | 3.25 s | 0.022855191046184498 | PASS |

Every trial stopped on the first native bend; none reached the connector/second bend. A repeatable failed traversal remains failed. The footprint half-width is 0.9 m, lane width 3.5 m. No intrusion tolerance, pose clamp, ground-truth steering, input replay, recurrent reset between segments, or policy tuning was introduced.

## Authenticated actual cohort 02

- [Actual run 44176109300](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/44176109300), workflow 421873536, attempt 1, diagnostic jobs all successful.
- Frozen source `54e2510adf9647a14161fe55461028dfb21f4758`; request-only activation `2993d1b2dce2fbf25985e1be25666afa23d47a91` on `diagnostic/sdk3-four-validation-20261118-02`.
- Exact source canonical push CI [44175298494](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/44175298494) and PR CI [44175310895](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/44175310895): four jobs PASS, 2,273 tests/7 skips in each complete suite plus one small-ONNX interface test each. Small-ONNX CI is not the official model run.
- Frozen image `sha256:b9d673de93f1857e4dfa5ed6a48330d568ef96fce7f3cc975f0c688877e6e26e`; SDK `27cd80fb1c06feaa7da8b5658cce918d1e3ab71c304a0c0ce42e30688ac008f3`; core `8b0372f1df91a930f18b2551f7fde5d5687e21bc79dee9ecd0dd2018cba72490`.
- Original official model SHA `35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199`, 768,750,198 bytes; real ORT 1.20.1 CPU. Original AuditedOfficialOnnx/NativeWorldCamera, existing single FRD→FLU adapter and unchanged RGB terrain priority candidate.
- Actual driver: `llvmpipe (LLVM 20.1.2, 256 bits)`, Mesa, GL 4.5 Compatibility Profile / Mesa 25.2.8. Two software workers; this is a distinct context from the prior short softpipe campaign.
- Registered cap: eight model children / 4,800 inferences, 600 steps each, 9,000 s child. All actual results retained; no retry/outcome selection. Models stopped at genuine lane intrusion, well before the cap.

[Independent receiver](actual-02/independent-receiver.json) authenticates run/workflow/attempt/source/activation/artifact SHA and reconstructs each route, raw action conversion, exact ideal kinematics and strict pair verdict. [Artifact inventory](actual-02/artifacts.json) contains authenticated IDs, SHA256, extents and expiry. Original ZIPs include source RGB compressed bytes and logs; Actions retention is 30 days. JSON model trials, lifecycle/container/owner receipts and the independently regenerated summary are also retained here. No weights are included. Actual producer source remains frozen at the source SHA; later laptop code is a separate, unexecuted runtime context.

## Negative pilot 01 retained

Run [44172902877](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/44172902877), workflow 421853166, source `0374130294f3003427d9e9fba643c22a99258f43`, activation `1d46c09287931aa0d537fc0c59763863da8fcb83`, one zero-model case only. The 4.11 host image reader disagreed with the native 5.0 warp. The measured 4.7545 s capture also exceeded the old 3,600 s child admission budget. It failed before any weights/model construction: **zero models / zero inferences**, remaining conditions not run.

Same-source CPU replays under [OpenCV 4.11](optical-replay-cv411.json) and [OpenCV 5.0](optical-replay-cv500.json) isolate the reader mismatch: 4.11 changes 15,200–22,706 channels by at most 3–4 levels; the matching 5.0 environment reproduces all four canvases exactly. Cohort 02 preregistered matching image libraries and the larger whole-600-step budget before any official-model outcome. Pilot 01 was not retried or relabeled.

## Windows follow-up

[Windows execution instructions](../../LAPTOP_FOUR_VALIDATIONS.md) start with a read-only inventory, then an explicit actual framebuffer probe. No notebook connection is present. Unit tests and Windows hosted inventory can prove portability only. The stock Windows Panda DLLs cannot inherit qualification from the Linux SDK3 `.so`. Offline measured-camera data remains local; absent data stays blocked. CARLA readiness is only a version/endpoint check; real cross-engine trials require an explicitly invoked dedicated server and independently measured route/camera bindings.

Previous PR144 source `8380e8a0c0583fa0e47af6b8bbb4b6446060e420`, original unmodified 3/4 failure and modified short candidate 4/4 are preserved. Their 12-step repeatability evidence is separate from this full-S motion evidence and does not imply full-route or physical fidelity success. No main merge, environment publication or image registry publication was performed.

## Post-review receiver checks

The [strengthened receiver receipt](strengthened-receiver-actual02.json) rechecks all five authenticated ZIP hashes, reconstructs the four actual camera probes with their case geometry, and binds every model trial to the corresponding qualified geometry. All eight model reports retain exactly the original case verdicts: zero full-S completions, four exact pairs, 554 inferences. Four in-memory scenario-swap negatives are rejected. This is CPU-only verification of frozen source54 artifacts; no extra model/native executions occurred.

The single whole-branch review found six Important issues. One regression-tested fix pass binds case geometry, guards both CARLA restoration paths against foreign actors and redundant map resets, reaps owned workers on all parent exits, measures enabled/disabled MSAA geometric-edge coverage, decodes training images to reject reencoded holdout leakage and numeric pose aliases, and checks actual returned CARLA image poses against pre-step ideal poses. These Windows/CARLA behavior contracts remain tested with pure/fake fixtures only until actual resources are supplied.
