# Stage 7 — MetaDrive PSSM MVP · scene task metadata · virtual clock causal diagnostics

Status: **native test running / measured results not yet certified**.
This is an instrumented simulation diagnostic, NOT an official driving-model benchmark.

## Upstream source confirmation (MetaDrive 0.4.3)

Verified source commit/tag **MetaDrive-0.4.3**:
- \`metadrive/engine/core/pssm.py\` lines 39-43: PSSM initializes the shadow camera rig, buffer, shader inputs and registers \`self.update\` as Panda task.
- Lines 89-101: \`PSSM.update\` transforms a directional light vector and invokes \`camera_rig.update(engine.camera, light_dir)\`; its numeric \`get_mvp_array()\` is copied into \`pssm_mvps\` scene shader input, then film-size cache reset.
- Lines 232-234: the shadow atlas uses a GPU depth texture and an ordered render buffer.
- \`metadrive/component/sensors/base_camera.py\` line 183: a single source camera \`perceive\` invokes \`engine.taskMgr.step()\`. Two sequential road/wide calls advance two task ticks.
- \`metadrive/engine/core/engine_core.py\` lines 356-360: rendering is conducted by Panda igLoop when taskMgr.step runs. Bypassing taskMgr directly changes scene behavior.

**Important:** The MVP camera matrix is a CPU-side projection/transform observation. It is NOT the GPU shadow depth map, nor proof that shadows were drawn differently. Inspecting numeric matrices can itself cause CPU timing overhead, so we do not call this run the uninstrumented original pipeline.

## Reproduction protocol

\`scripts/native_pssm_mvp_task_trace.py\` records all data in fresh MetaDrive 0.4.3/Panda3D/Xvfb processes, pinned to the official release and SHA256-verified assets.

Compare each independent condition with **8 virtual camera-frame pairs**, and preserve the first two warmup frames in raw evidence:

1. \`sequential_baseline\`: \`road.perceive\` then \`wide.perceive\`, each calls taskMgr.step. Measure MVP/clock **before, after road, after wide**; two actual taskMgr call paths and two Panda global frames.
2. \`paired_baseline\`: mount both cameras at exact same WORLD pose; one taskMgr.step followed by both readbacks. One task call/global frame.
3. \`graphics_only\`: graphicsEngine.renderFrame once, with zero taskMgr.step calls but **one Panda global frame**. Never use as official camera simulation by itself.
4. \`paired_pssm_off\`: identical paired taskMgr.step path, removing **only** \`PSSM.update\` from task manager; igLoop stays active. Scene semantics differ from baseline.

Matrix: seeds \`20261109\`/\`20261110\`, native scenarios \`s_curve_left_right\`/\`s_curve_right_left\`, Panda normal clock/fixed virtual clock. The selected fixed native WORLD camera pose is based on lane fraction \`0.12\`, height \`1.22m\`.

Each frame records (a) exact native PSSM MVP split ×4×4 float values, big-endian binary64 hash and maximum changed matrix elements; (b) main scene camera pose and light pose; (c) Panda global frame clock counts/times; (d) task *registration sort and chain metadata*; and (e) actual raw camera RGB and model I420 SHA hashes. Plus two-meter pose-shift **both-camera positive control** prevents stale GPU buffers being classified as stable.

Expensive RGB differencing and I420 warp are **post-capture** only. No HDR extractTextureData, CUDA, model weights, CARLA, real vehicle, controller code, CD210 or Carrot fallback.

## Interpretation limits

- Panda \`getAllTasks()\` and \`getSort()\` reveal **registered tasks/ordering hints**, not definitive order or frequency in which tasks executed. Actual code-path taskMgr.step count is recorded separately from Panda global frameCount.
- PSSM MVP matrix variation is only **correlated** with final road/wide RGB variation. No unique shader cause, physical optics equivalence, or model driving quality inferred.
- The fixed virtual clock changes task timing/render semantics and must **never** be substituted into official MD-V3 repeatability runs without a fresh independent validation gate.
- If any requested MVP read fails, matrix layout changes, graphics loop task disappears, clock values nonfinite, camera pose positive control fails, or a condition report is missing, classify INCONCLUSIVE/ERROR. **Do not invent zero changes or PASS**.
- The earlier official SHA-pinned MD-V3 strict native fresh-frame repeated test still had **0/4 exact matches**. No official model ranking is allowed.

## Native CI evidence

[GitHub Actions — PSSM MVP and virtual-clock](../.github/workflows/pssm-mvp-task-clock.yml) runs the matrix and saves JSON receipts with per-frame numeric values and exact RGB hashes.

The workflow's job-level SUCCESS means *diagnostic collection succeeded*. Only measured receipts can support claims of MVP/clock associations. The exact run and quantitative results should be appended **after** CI and artifacts have been inspected.

## Next gate

If the MVP / light / main scene camera and native RGB observations remain inconsistent under matched fixed timing, test non-PSSM scene updates with a strictly controlled task schedule. Then rerun official MD-V3 untouched new-camera-frame repeated 12-step diagnostics across independent ORT/Panda contexts. 7th-stage completion and model ranking remain blocked.
