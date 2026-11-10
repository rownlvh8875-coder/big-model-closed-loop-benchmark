# Stage 7 — MetaDrive PSSM MVP · scene task metadata · virtual clock causal diagnostics

Status: **native matrix 8/8 diagnostic CI SUCCESS; official ONNX exact repeatability remains unpassed**.
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


## 2026-11-10 실제 네이티브 8×4 전수 결과

원본: [GitHub Actions #42782363322](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42782363322) SUCCESS, 총 **2 seed × 2 S-curves × 2 Panda clock regimes × 4 independent process arms = 32개의 native MetaDrive 0.4.3/Xvfb 프로세스**. 8개 매트릭스 job / 8개 아티팩트의 JSON 전수 확인. 공식 에셋 검증, road/wide +2m camera positive control, native task registration 및 global frame-count, numeric MVP 측정 계약 모두 통과. 성공은 **진단 관측 성공**이며 새 프레임 공식 MD-V3 ONNX exact-repeat 게이트 통과와 무관하다.

아래 수치는 워밍업 2프레임을 별도 보존하고 나머지 6프레임에서 계산. MVP는 PSSM shadow camera rig 행렬의 **고유 raw-f64 SHA 수**, Raw road/wide는 원본 964×604 RGB의 최대 변경 픽셀 수, I420은 final (2,6,128,256) 모델 입력의 고유 SHA 수다.

| Seed | S curve | Clock | condition | MVP SHA count | Raw Road/Wide max changed pixels | I420 SHA count |
|---|---|---|---|---:|---|---:|
| 20261109 | Left→Right | normal | sequential | 1 | 0/0 | 1 |
| 20261109 | Left→Right | normal | paired task | 1 | 0/2 | 1 |
| 20261109 | Left→Right | normal | graphics only | 1 | 0/0 | 1 |
| 20261109 | Left→Right | normal | PSSM-off task | 1 | 0/0 | 1 |
| 20261109 | Left→Right | fixed | sequential | 1 | 9/2 | 2 |
| 20261109 | Left→Right | fixed | paired task | 1 | 9/2 | 2 |
| 20261109 | Left→Right | fixed | graphics only | 1 | 0/0 | 1 |
| 20261109 | Left→Right | fixed | PSSM-off task | 1 | 0/0 | 1 |
| 20261109 | Right→Left | normal | sequential | 1 | 8/3 | 3 |
| 20261109 | Right→Left | normal | paired task | 1 | 0/0 | 1 |
| 20261109 | Right→Left | normal | graphics only | 1 | 0/0 | 1 |
| 20261109 | Right→Left | normal | PSSM-off task | 1 | 0/0 | 1 |
| 20261109 | Right→Left | fixed | sequential | 1 | 8/0 | 2 |
| 20261109 | Right→Left | fixed | paired task | 1 | 0/0 | 1 |
| 20261109 | Right→Left | fixed | graphics only | 1 | 0/0 | 1 |
| 20261109 | Right→Left | fixed | PSSM-off task | 1 | 0/0 | 1 |
| 20261110 | Left→Right | normal | sequential | 1 | 0/2 | 1 |
| 20261110 | Left→Right | normal | paired task | 1 | 0/2 | 1 |
| 20261110 | Left→Right | normal | graphics only | 1 | 0/0 | 1 |
| 20261110 | Left→Right | normal | PSSM-off task | 1 | 9/2 | 2 |
| 20261110 | Left→Right | fixed | sequential | 1 | 9/2 | 2 |
| 20261110 | Left→Right | fixed | paired task | 1 | 9/2 | 2 |
| 20261110 | Left→Right | fixed | graphics only | 1 | 0/0 | 1 |
| 20261110 | Left→Right | fixed | PSSM-off task | 1 | 0/0 | 1 |
| 20261110 | Right→Left | normal | sequential | 1 | 0/3 | 2 |
| 20261110 | Right→Left | normal | paired task | 1 | 8/3 | 2 |
| 20261110 | Right→Left | normal | graphics only | 1 | 0/0 | 1 |
| 20261110 | Right→Left | normal | PSSM-off task | 1 | 0/0 | 1 |
| 20261110 | Right→Left | fixed | sequential | 1 | 0/0 | 1 |
| 20261110 | Right→Left | fixed | paired task | 1 | 0/3 | 2 |
| 20261110 | Right→Left | fixed | graphics only | 1 | 8/3 | 3 |
| 20261110 | Right→Left | fixed | PSSM-off task | 1 | 8/3 | 3 |

### 관측된 연관성과 부정 가능한 가설

- **MVP 숫자 행렬의 후반부 SHA 변화는 0/32 조건**이었다. 그러나 후반 원본 road/wide RGB SHA 드리프트는 sequential 6/8, paired 6/8, graphics-only 1/8, PSSM-off 2/8이고 최종 I420 SHA 드리프트는 각각 **5/8, 4/8, 1/8, 2/8**. MVP 행렬값의 변동은 관측된 모든 RGB/I420 변화의 필요조건이 아니다.
- Baseline sequential/paired에서는 초기 카메라 쌍 2회에서 **before vs after MVP가 변경**됐지만, 이후 프레임에서는 행렬이 고정됐다. Graphics-only 및 PSSM-off에서는 MVP가 카메라 쌍 내에서 변경되지 않았다. 각 arm의 MVP 후반 해시는 일정해도 arm끼리 같은 값이라는 뜻은 아니다.
- Normal과 fixed virtual clock 비교: sequential I420 불일치 normal **2/4**, fixed **3/4**. 고정 시계가 모든 픽셀 드리프트를 제거하지 못한다는 결론에 한정해야 한다. 시계 고정은 공식 ONNX 평가에 적용하지 않는다.
- seed 20261110 Right→Left fixed에서 graphics-only 및 PSSM-off도 각각 raw **8/3픽셀**, I420 SHA **3개**. 앞선 다른 CPU 계측 조건에서는 두 모드가 안정적으로 관측됐기에 **GPU/Panda 렌더링과 계측 CPU 실행시간의 상호작용을 추가로 통제**해야 한다. 특정 모드를 항상 결정적이라고 주장할 수 없다.
- MetaDrive native task registration sort/chain metadata: dataLoop sort=-50; PSSM.update sort=0, update main chase camera sort=0 (같은 default chain); igLoop sort=50. 이는 **등록 값**일 뿐 실제 PSSM.update와 chase camera callback 실행 순서를 증명하지 않는다.
- 동일한 카메라/광원/scene shader GPU 상태는 현재 직접 관측하지 않았다. 본 실험은 CPU numeric MVP를 보고 GPU 그림자맵 texel을 추출하지 않았다.

### 여전히 검증되지 않은 항목

- MVP 행렬 SHA만으로 PSSM 그림자 atlas 렌더 패스 자체의 결함/영향 없음 판정 불가.
- 등록 Sort=0인 두 태스크의 **실제 callback 실행 순서** 미증명. sort만으로 서로의 호출 선후를 단정할 수 없다.
- clock dt 1/60로 고정해도 원래 MetaDrive 정상 렌더링과 의미적으로 동등하다는 증거가 아니다.
- CPU MVP, raw RGB, task metadata 조회가 스케줄에 미치는 벽시계 지연량과 이전 무계측 환경의 동등성 미증명.
- 7단계 공식 MD-V3 새 실영상 independent ONNX exact-repeatability는 이전 **0/4 PASS**, 모델 순위 불허.

**다음 최우선 gate:** 관측 부작용을 통제한 별도 태스크 callback 실행순서 실험으로 PSSM.update vs update main chase camera의 실제 호출 시각을 기록하고, shader depth atlas/표면 렌더를 가능한 한 비침습적으로 분리. 원래 파이프라인을 보존한 별도 대조군과 비교해야 한다. 실차/CAN/CD210/Carrot MPC 없이 수행하며 공식 ONNX 입력 대체 금지.
