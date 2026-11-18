# Windows host correction and saved full-S observations · 2026-11-18 KST

## Corrected allocation boundary

Local handoff reports original stock-Panda Windows allocation failure and a separate successful host experiment. Source14297e2 passes neither host nor GSG to makeOutput. Official Panda1.10.13 [WGL FBO retry](https://github.com/panda3d/panda3d/blob/v1.10.13/panda/src/wgldisplay/wglGraphicsPipe.cxx#L146-L149) rejects host==nullptr. The corrected producer opens an owned zero-sample offscreen context host, validates its GSG, deactivates it, then passes that host/GSG to the requested-MSAA canary. It never lowers requested canary samples or changes uniform/edge/shader/WGL readback criteria. Callback, canary, host and ShowBase cleanup is exercised on failure.

Attemptv2 distinguishes the corrected producer. Original failures and the separately reported in-memory experiment remain their own results. Actual Windows RTX retesting is still required; fake WGL and hosted Linux stock-Panda allocation smoke cannot certify it. Hosted Linux smoke is zero-model, one no-scene render, and reports software driver/framework sample properties only. Its source-bound Actions artifact is the API evidence, not a hardware/MSAA pixel PASS.

## Read-only retrospective, no new model run

The [derived JSON](saved-full-s-observations.json) binds exact SHA256 of all eight saved raw reports and their duplicate copies to authenticated run44176109300 / source54e2510. Pure trajectory replay validates original actions, the existing one-time FRD→FLU bridge, ideal plant and first intrusion. Both fresh processes in each condition yield identical derived summaries and original strict verdicts. This is the original8models/554inferences; **new models/inferences0**, not the separately reported pending Codex task. Original full-S completion remains0/4 and strict repeat4/4.

| Seed | Scene | Steps | Virtual seconds | Mean applied curvature magnitude / native first-bend curvature | Final lateral-right m |
|---|---|---:|---:|---:|---:|
| 20261109 | s_curve_left_right | 60 | 3.00 | 83.41% | 0.859417 |
| 20261109 | s_curve_right_left | 90 | 4.50 | 91.54% | -0.869439 |
| 20261110 | s_curve_left_right | 62 | 3.10 | 84.55% | 0.858492 |
| 20261110 | s_curve_right_left | 65 | 3.25 | 79.72% | -0.872855 |

Every applied world curvature has the same sign as its native first-bend curvature (554/554 model steps across all eight trials). Thus an opposite-signed applied curvature is not the observed departure mechanism in these saved records. Mean applied magnitude is79.72–91.54% of the native bend's1/55m curvature. The actual trajectories drift outward and first exceed the0.85m center offset allowance (3.5m lane,0.9m footprint half-width) after60/90/62/65steps. Final intrusion is0.00849–0.02286m; all previous committed rows satisfy the original zero-intrusion requirement.

These are observed steering/trajectory mechanics. They do **not** establish whether weaker turning arose from imagery, optical/frame contracts, model initialization or other model behavior, and do not rank driving quality. The geometric raw-acceleration reference in JSON is an offline unit comparison only; no truth/steering was supplied to the model or controller. No policy, speed, threshold, input or recurrent state was changed to force completion.

The user's separate cloud task remains unobserved in this chat; no available tool can query that private task by its handoff metadata. This work did not duplicate it or relabel old results as new.

## Local next check

Use the corrected feature/windows-msaa-host-v1 code and the existing Windows Python3.11/Panda1.10.13 environment. Run the fresh-output GPU command in [Windows instructions](../../LAPTOP_FOUR_VALIDATIONS.md#host-수정본-재검사), then inspect actual readbacks. Reported4.68GiB freeRAM still fails the8GiB local model gate; GPU host correction does not relax it. The local raw experiment/diff/logs were not attached, so their reported PASS and9338-file preservation claim were not independently recomputed here. No raw private handoff file is published.

## Actual hosted software API receipt

Source `1c034eea59c8084c625ba888cf1a05f6da072373` passed [push44204724169](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/44204724169) and [PR44204730469](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/44204730469) native API smoke. Root authenticated each run/attempt/head, artifact extent/digest, and raw JSON. [Source-bound receipt](software-api/source-1c034ee-ci-receipt.json) and separate [push](software-api/push-report.json)/[PR](software-api/pull_request-report.json) reports preserve the actual Linux stock-Panda result: llvmpipeLLVM20.1.2/Mesa25.2.8-0ubuntu0.24.04.5, requested/framework-reported4samples, one no-scene render, owned outputs removed, zero models/inferences. All WGL/hardware/model-camera/physical/CARLA qualification flags remain false. The same source's canonical4jobs passed2320tests/7skips plus one small-ONNX test each, and Windows portable push/PR passed68tests each. These measured receipts belong to source1c034ee even if later evidence/review commits have another HEAD; exactfinalHEAD CI is recorded in the external closeout receipt.

## Ownership and backend evidence boundary after review

The retained source1c034ee smoke reports check eventual cleanup after ShowBase.destroy; they do not independently prove ExitStack cleanup because ShowBase removes all windows. The strengthened smoke-v2 checks registry restoration BEFORE that fallback and rejects a deliberately omitted host or canary cleanup callback. ExactfinalHEAD smoke-v2 results are authenticated in the closeout receipt/Actions artifacts. Historical source1c receipts remain unchanged with their original limited scope.

The corrected allocator now records requested construction separately from actual native output TypeHandle names and whether the resulting canary GSG is the host GSG. It allows a valid alternate pbuffer/parasite target without calling it an FBO; unchanged actualGLsample/state/edge/pixel gates still determine the hardware verdict. The marker is `OWNED_ZERO_SAMPLE_OFFSCREEN_HOST_AND_REQUESTED_MSAA_OUTPUT_V2`. No fresh actualWindowsRTX retest has been observed.
