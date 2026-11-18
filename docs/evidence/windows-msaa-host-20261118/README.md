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
