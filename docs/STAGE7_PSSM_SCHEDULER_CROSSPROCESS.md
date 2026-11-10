# Stage 7 — independent-process PSSM task scheduling A/B at fixed WORLD camera pose

## Why this follow-up is necessary

[Actual official MD-V3 original-source RGB pixel probe #42924910245](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42924910245) observed the first raw camera difference at step 2 in all four cases, with **1 / 8 / 3 / 13 changed source pixels**, and fully revalidated the original compressed RGB bytes and official ONNX SHA receipts. Those facts establish sparse first-image differences **but not their unique cause**.

Earlier [native raw pixel clock experiment #42776577784](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42776577784) compared **within-process** RGB changes over time under multiple Panda task/camera modes. PSSM task ablation suppressed post-warmup changes in some scenes, but [16-condition broader study](STAGE7_MULTISCENE_NATIVE_REPEAT.md) showed variability persisted with PSSM removal in other scenes. Cross-process comparisons of the same treatment are a different, still necessary question.

## Strict fixed-pose experiment

The next experiment measures whether **two fully independent MetaDrive processes** give the same raw RGB/I420 series when PSSM task scheduling and camera capture mode are each held fixed.

- Upstream MetaDrive **0.4.3**, official release assets SHA256/size checked, real native maps S-curves left-right/right-left, seeds **20261109/20261110**.
- Same lane-derived WORLD camera pose at fraction **0.12**, height 1.22 m. Ten original road/wide RGB source frames at 964×604 for each process, with first two preserved as warmup. Crop/rectification yields model RGB and packed I420 **only as an interface diagnostic, without ONNX inference**.
- Four independent treatment arms per seed/scene, **two separate Python/Panda/Xvfb processes each** (4 scenes × 4 arms × 2 independent repeats = **32 total processes**):
  1. Sequential road→wide perceive, **original PSSM.update enabled**; taskMgr.step twice per camera pair.
  2. Paired road+wide through a shared taskMgr.step, **original PSSM.update enabled**; one step per camera pair.
  3. Sequential perceive with **PSSM.update task explicitly removed** (experimental modified renderer).
  4. Paired taskMgr.step with **PSSM.update task explicitly removed** (experimental modified renderer).
- Only **within the same arm** are two independent process RGB, warped model RGB and I420 SHA series compared. Comparing original vs ablated raw image SHA as an equality requirement is invalid because the renderer semantics differ.
- Every arm preserves both cameras' +2m WORLD pose positive controls, three repeated completed-frame CPU RAM readbacks, original/ablated PSSM task-registry evidence, source/model/I420 SHA sequence, verified Panda frame count vs taskMgr call-path count, clock timeline, and process UUID + PID.
- Fail closed if a seeded native pair, metadata, process UUID, original camera pose, PSSM task membership, original image SHA list, clock evidence or positive control is missing or inconsistent. Aggregation recomputes all four scene summaries from the original per-process JSON.
- No intermediate GPU texture extraction, model input rewrites, camera convergence tolerance, video replay, extra frame creation, real-car system, or model quality ranking.

## Inference boundaries

Even if the original PSSM-on arm has more independent-process image mismatches than the PSSM-task-removed arm, **this is only a controlled rendering association**, not proof of a shader defect or unique PSSM root cause. PSSM removal changes visual semantics and must not be adopted as the default original renderer or used to assert official MD-V3 performance.

The original strict **fresh-frame MD-V3 ONNX** repeatability gate is separate and remains **0/4 exact-match PASS**. This no-ONNX, stationary-scene A/B cannot close Stage 7. New numbers/CI status must be appended only after all 32 native processes and strict raw JSON aggregate complete successfully.

## Evidence pending new run

This file is the registered method and test plan. A software unit CI PASS is not a native measurement; actual observed cross-process frame matches and published artifact IDs will be recorded after successful GitHub Actions execution.
