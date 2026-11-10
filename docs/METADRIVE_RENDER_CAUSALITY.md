# MetaDrive 0.4.3 RGB 원인 분리 시험 — 렌더 시점 / CPU 복사 / 장면 업데이트

**실험 성격:** 시뮬레이터 진단. **실차 테스트 0회**, 특정 차종 동역학·CD210·Carrot 튜닝 없음. 모델의 주행성능 순위 산출 불가.

## 배경: 먼저 확인된 사실

- [동일 MD-V3 입력 반복 재현성](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42755109268): 공식 ONNX 가중치·동일 MetaDrive RGB 프레임을 **한 번만 캡처한 뒤** 2개의 독립 추론 세션에 12스텝 넣으면 가상 궤적 차이 **0m**. **오픈루프 입력 고정**에 한정.
- [매 스텝 MetaDrive 새 영상 반복시험](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42741355594): 실제 영상 폐루프는 반복 RGB·가상 위치 미세 불일치. 카메라 바이트 차이가 모든 출력 차이의 유일한 원인인지는 미확인.
- 기존 고정 카메라 실험은 기본 가상 차량 시야와 동적 렌더링을 충분히 분리하지 못했다. 따라서 우선 구성 요소를 독립적으로 계측한다.

## MetaDrive 0.4.3 원본 코드의 검증된 호출 구조

- [MetaDrive `BaseCamera.perceive`](https://github.com/metadriverse/metadrive/blob/MetaDrive-0.4.3/metadrive/component/sensors/base_camera.py#L163-L200): 카메라를 임시로 reparent/pose 변경하고 **`engine.taskMgr.step()`** 후 RGB를 읽고 원래 자세로 복구. road/wide를 순차 `perceive`하면 렌더 틱이 두 번 진행된다.
- [MetaDrive `ImageBuffer`](https://github.com/metadriverse/metadrive/blob/MetaDrive-0.4.3/metadrive/engine/core/image_buffer.py#L100-L109): CPU 텍스처 읽기의 기존 일반 경로와 이미지 수직 반전.
- [MetaDrive `RGBCamera`](https://github.com/metadriverse/metadrive/blob/MetaDrive-0.4.3/metadrive/component/sensors/rgb_camera.py#L25-L61): HDR scene texture 및 tonemap shader/filter 후처리.
- 본 프로젝트 [RAM 카메라](../bigbench/metadrive_camera.py)는 최종 RGB 버퍼에 `RTMCopyRam` 텍스처를 추가하고 `getRamImageAs("RGB")`로 읽는다.
- 소프트웨어 렌더링/하드웨어·그래픽 드라이버 차이는 추후 별도 검증이 필요하다.

## 이번에 작성한 독립 실험 계약

| 조건 | 내부 행위 | 무엇을 구분할 수 있는가 |
|---|---|---|
| `perceive_sequential` | road용 `taskMgr.step` 뒤 RGB 복사, wide용 `taskMgr.step` 뒤 RGB 복사 | 기존 공개 입력 경로의 시간차 포함 |
| `task_step_pair` | 두 카메라를 동시에 고정된 WORLD pose에 장착, **태스크 1틱** 실행 후 두 RGB 읽기 | road/wide 간 별도 render tick 제거 |
| `graphics_frame_pair` | 두 카메라 pose를 설정하고 **`graphicsEngine.renderFrame()` 1회**. `taskMgr.step` 금지 | 태스크 업데이트 없이 그래픽 프레임 생성 |
| 각 조건의 CPU 반복 읽기 | 렌더 완료 직후 동일 `RTMCopyRam`을 3회 읽고 직접 복사 | 별도 GPU 렌더 없이 CPU 데이터가 바뀌는지 |
| `ego_visible` vs `ego_hidden` | 기본 가상 차량의 **RGB 렌더 마스크만** 변경 | 장면 내 기본 가상 객체가 변동의 원인인지에 대한 대조 |
| 선택적 scene texture 탐침 | 본 실험 프레임 계측을 끝낸 **이후** `scene_tex`를 GPU에서 읽기 시도 | 최종 톤매핑 이전 텍스처 접근 가능성. 본 실험의 프레임 시계열과 섞지 않음 |

**모든 조건은 새 MetaDrive 환경·동일 seed에서 독립 실행**한다. 원래 장면의 기본 차량 시각 객체를 숨기더라도 물리 움직임이나 실제 차량 제어는 하지 않는다.

## 반드시 별도 기록할 데이터

- **원본 센서 RGB (`964×604`) 해시 및 픽셀 차이**: 전체 프레임 + 시작 2프레임을 별도 표시한 이후. 워밍업으로 전체 원본 불일치를 감추지 않음.
- **모델 입력 RGB (`512×256`) 해시·RGB 변경 픽셀·최대 채널 차이**.
- **최종 ONNX `new_img` (`2,6,128,256` `uint8`)** 텐서 SHA256·변경 원소 수·최대 차이.
- **CPU readback 반복 그룹**의 같은 장면 읽기 해시·변화 수. GPU 렌더를 추가로 수행하지 않아야 함.
- **Panda3D 시계 상태**, `taskMgr` 등록 태스크 이름, 기본 가상 차량의 transform 및 동일 자세 유지 여부.
- **양성 대조:** 카메라를 실제로 +2m 옮겼을 때 양쪽 영상이 바뀌지 않으면 stale buffer/렌더 경로 검증 불충분으로 표시.

## 해석의 경계

- 같은 GPU 프레임의 CPU 반복 읽기가 동일해도 **GPU→CPU 동기화의 모든 가능한 race condition이 사라졌다는 뜻은 아님**.
- `graphicsEngine.renderFrame`만 안정적이고 `taskMgr.step`이 불안정한 경우 **렌더 틱/태스크 또는 장면 업데이트와 상관관계**가 있다는 뜻이며, 특정 태스크·셰이더가 유일한 원인임을 증명하지 않는다.
- 기본 차량 숨김 후 안정화되면 **가상 차체 렌더/시야가 관련된다는 관측**이지만, 이것만으로 실제 comma 카메라의 입력 도메인이 보정됐다고 간주하지 않는다.
- **기록 영상 재생, 영상 보간·평균·블러, 결과 허용오차 완화**로 공식 폐루프 성능 PASS를 만들지 않는다.
- 미지원 실험/버퍼 접근 오류/양성 대조 실패는 `ERROR` 또는 `INCONCLUSIVE_NO_POSE_RESPONSE`로 그대로 남긴다.

## 실행 방법

MetaDrive 0.4.3, 대응 공식 자산·Xvfb·OpenGL 및 OpenCV/NumPy가 있는 Linux 시스템:

```bash
python -m unittest discover -s tests -p 'test_render_causality.py' -v

xvfb-run -a python -m scripts.metadrive_render_causality \
  --frames 5 --warmup 2 --seed 20261109 \
  --modes perceive_sequential task_step_pair graphics_frame_pair \
  --scenes ego_visible ego_hidden \
  --probe-pre-tonemap --out output/render-causality
```

[실제 MetaDrive GitHub Actions 워크플로](../.github/workflows/render-causality.yml)에서 공식 에셋의 SHA256을 확인한다.

## 2026-11-10: 6개 MetaDrive 실렌더 조건 측정 결과

**실제 근거:** [GitHub Actions #42757874100](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42757874100), 아티팩트 `meta-render-task-readback-scene-factorization` (id `13736736732`), 검증 커밋 `1240d57d49bbeecc0dda75d6c016453198a2979e`.

- MetaDrive **0.4.3**, 공식 렌더 자산 SHA256 고정, Ubuntu/Xvfb/software GL.
- **6/6 조건 `OBSERVED`**, 각 5프레임, 초기 2프레임을 보존하되 후반부 별도 요약. 카메라 +2m 포즈 이동 양성 대조는 모든 조건에서 road/wide 각각 PASS.
- **중간 CPU RAM 텍스처 재읽기:** 모든 조건·모든 프레임에서 추가 렌더 틱 없이 3회 읽기가 **bit-exact**. 따라서 관측된 RGB 변화는 단순 **반복 읽기**만으로 재현되지 않았다. GPU→CPU 동기화 문제 전체가 부정됐다는 뜻은 아님.
- 이상적인 카메라 raw→model RGB→I420 입력도 각 조건에서 독립 검증했다.

| 기본 가상 차량 RGB | 렌더 틱 | 2프레임 이후 raw road/wide 최대 변경 픽셀 | 2프레임 이후 model road/wide 최대 변경 픽셀 | 2프레임 이후 최종 ONNX I420 변경 원소 | 판정(관측만) |
|---|---|---|---|---:|---|
| 표시 | camera별 `perceive` | 0 / 2 | 0 / 0 | 0 | 텐서 동일 |
| 표시 | 두 카메라 `taskMgr.step` | 0 / 0 | 0 / 0 | 0 | 텐서 동일 |
| 표시 | 두 카메라 `graphicsEngine.renderFrame` | 0 / 0 | 0 / 0 | 0 | 텐서 동일 |
| 숨김 | camera별 `perceive` | **9 / 0** | **8 / 0** | **6** | RGB/I420 변경 |
| 숨김 | 두 카메라 `taskMgr.step` | **9 / 2** | **8 / 0** | **6** | RGB/I420 변경 |
| 숨김 | 두 카메라 `graphicsEngine.renderFrame` | **0 / 0** | **0 / 0** | **0** | 후반부 텐서 동일 |

**해석(조건부):** 이번 MetaDrive 장면에서는 `graphicsEngine.renderFrame()`만 호출한 경우, `taskMgr.step()`이 포함된 방식보다 후반부 영상 일관성이 좋았다. MetaDrive 기본 차량 RGB를 **숨기는 것만으로** 불일치가 없어지지 않았으며, 오히려 일부 숨김 조건에서만 변경 픽셀이 관측됐다. 특정 태스크·셰이더·RAM 복사 버그의 원인성을 아직 증명하지 못했다.

**중요 교란변수:** 여섯 조건은 각각 새 MetaDrive 객체를 만들었지만 **하나의 Python/Panda3D 전역 시계와 Xvfb 프로세스에서 순차 실행**됐다. 장면 옵션의 차이를 전역 clock 누적, 장면 초기화/실행 순서와 분리하지 못한 가능성이 있다. 본 결과를 충분조건·일반화·성능 판정으로 사용하면 안 된다.

### 재검증: 6개 독립 Python/Xvfb 프로세스

- `scripts/aggregate_render_causality.py`에서 **각 조건이 다른 프로세스에서 남긴 보고서**를 모으고, 조건 ID/seed/프레임 수/양성대조/실차·모델 점수 금지 플래그를 확인한다.
- [별도 프로세스 GitHub Actions](../.github/workflows/render-causality-process.yml): 각 조건을 별도 `xvfb-run -a python`으로 실행하고, 동일 seed에서 8프레임(초기 2프레임 별도) 관측. **시험 성공 여부와 수치는 CI 아티팩트가 확보된 뒤 따로 반영해야 한다.**
- 반복 시계열이 일치해도 실제 MD-V3/Light Speed 폐루프 성능 재현성은 별도 게이트다.

**검증 상태:** 위 첫 6조건 실렌더 감사는 **기술 진단 완료**, 인과관계 식별 및 모델 주행성능은 **미완료**.



## 독립 Python/Xvfb 프로세스 재검증 — 2026-11-10 PASS(관측)

**실행 증거:** [GitHub Actions #42758718405](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42758718405), 독립 프로세스 6개 모두 정상 관측. 아티팩트 `isolated-native-render-time-readback-scene` (id `13736842431`). 각 조건별 **8프레임**, 앞 2프레임을 원본에서 제거하지 않고 후반 별도 요약만 계산했다. Panda3D 시작 frame count는 여섯 조건 모두 10으로 확인돼 첫 실험의 공유 전역시계 누적 교란을 통제했다.

| 기본 가상 차량 RGB | 방식 | 소스 RGB 변경 픽셀 road / wide | 모델 512×256 변경 road / wide | I420 변경 원소 수 | I420 완전 일치(후반) |
|---|---|---|---|---:|---|
| 표시 | 순차 `perceive` | 4 / 0 | 2 / 0 | 1 | 아니오 |
| 표시 | 동시 `taskMgr.step` | 4 / 2 | 2 / 0 | 1 | 아니오 |
| 표시 | 동시 `graphicsEngine.renderFrame` | 0 / 2 | 0 / 0 | **0** | **예** |
| 숨김 | 순차 `perceive` | 9 / 2 | 8 / 0 | 6 | 아니오 |
| 숨김 | 동시 `taskMgr.step` | 9 / 2 | 8 / 0 | 6 | 아니오 |
| 숨김 | 동시 `graphicsEngine.renderFrame` | 0 / 0 | 0 / 0 | **0** | **예** |

위 RGB 변경 픽셀 수는 초기 2프레임을 제외한 나머지 표본에서 첫 후반 프레임과의 **최대 차이**다. 각 조건의 전체 8프레임 해시도 JSON에 보존했다.

**모든 조건에서** 렌더링 없이 같은 `RTMCopyRam` RGB 텍스처를 반복 읽은 해시는 완전히 동일했다. +2m 포즈 이동 양성 대조에서 두 카메라가 모두 변했다. 따라서 이 관측은 **고정 stale framebuffer만 읽어서 동일하게 보인 가짜 안정화**와 구분된다.

**해석:** 서로 독립된 Panda 프로세스로 다시 실행해도 `taskMgr.step()`이 실행되는 경로에서 픽셀 및 I420 텐서가 변화하고 `graphicsEngine.renderFrame()`만 사용하는 경로는 워밍업 이후 모델 입력이 일정한 경향이 확인됐다. 이는 **태스크/시간 기반 장면 업데이트의 영향 가설**을 강화한다. 하지만 단 한 시드·한 pose·한 GL 드라이버에서의 관측이며 **어느 특정 태스크가 바이트 차이를 발생시켰는지** 아직 분리하지 못했다.

**다음 분리:** MetaDrive에 등록된 `PSSM.update`(그림자 관련 태스크)와 `update main chase camera`를 각각 독립 시험에서 제외하되 `igLoop`은 반드시 유지한다. [전용 시험](../.github/workflows/scene-task-ablation.yml). 동적 장면·그림자를 제거한 영상은 원래 평가용 모델 입력과 동일하지 않으므로 모델 성능 점수로 사용하지 않는다.


## 장면 태스크 분리 — PSSM.update와 chase camera (2026-11-10)

[실제 GitHub Actions #42759149254](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42759149254)에서 조건별 별도 Python·Xvfb 프로세스를 생성하고, **`ego_hidden`, `task_step_pair`, 동일 seed 20261109·8프레임**을 비교했다. 아티팩트 `native-pssm-shadow-scene-ablation` (id `13737346002`).

`bigbench/task_ablation.py`는 사전에 허용한 시각 태스크 한 개만 제거한다. 반드시 `taskMgr.getAllTasks()`에 그 태스크가 정확히 1개 있어야 하며 **`igLoop`가 계속 실행되는지** 검증한다. 이 과정은 가상 렌더링에만 적용하고, 모델이나 실제 차량을 건드리지 않는다.

| 가상 장면 조건 | 후반 원본 road/wide 변경 픽셀 | 후반 모델 road/wide 변경 픽셀 | 후반 I420 변경 원소 | 비트 동일 I420 | +2m 포즈 변동 대조 |
|---|---|---|---:|---|---|
| 기본 `taskMgr.step` | 9 / 2 | 8 / 0 | 6 | 아니오 | road/wide 모두 PASS |
| **`PSSM.update`만 제거** | **0 / 0** | **0 / 0** | **0** | **예** | road/wide 모두 PASS |
| `update main chase camera`만 제거 | 9 / 2 | 8 / 0 | 6 | 아니오 | road/wide 모두 PASS |

모든 조건에서 GPU 재렌더 없이 같은 CPU `RTMCopyRam` 텍스처를 세 번 재읽은 데이터는 비트 단위 동일했다. `PSSM.update` 제거 시에도 `igLoop`은 살아 있고, 카메라를 +2m 옮기면 road/wide 화면이 바뀌므로 **빈/멈춘 화면을 재활용하는 거짓 안정화는 관측되지 않았다.**

**해석(중요):** 이 특정 MetaDrive 0.4.3·Ubuntu/Xvfb/software GL·단일 seed·고정 pose 조건에서 그림자 업데이트 태스크 `PSSM.update`의 수행 여부가 RGB/I420 불일치와 강하게 연관되며, chase camera 태스크의 제거로는 현상이 해소되지 않았다. 하지만 **그림자맵의 어느 패스·셰이더·렌더 상태가 최종 출력 9픽셀을 바꾸는지**, 다른 장면·시드에서도 같은지, 실제 comma 카메라 입력과 동일한지까지는 아직 증명하지 않았다.

**적용 금지:** `PSSM.update`를 제거한 렌더링은 그림자 갱신이 달라지는 **새 시뮬레이션 영상 조건**이다. 이를 원래 렌더러와 동일하다고 가정하거나 일반 모델 평가 기본 설정에 자동 적용하지 않는다. 모델 비교에서의 영상 도메인·장면 난이도 및 다중 시드 통제 검증이 선행되어야 한다. 실제 대형 ONNX의 **새 영상 폐루프 반복 재현성은 여전히 독립적인 미완료 게이트**다.

### 향후 후속 조사

1. `PSSM.update`의 그림자맵 갱신을 한 단계씩 제어하여 HDR `scene_tex`와 최종 `RTMCopyRam` 변화가 어디서 처음 발생하는지 검사.
2. 두 개 이상의 독립 시드·서로 다른 카메라 좌표·S자/램프 지도에서 동일 A/B 현상 반복 확인.
3. 조건을 문서화한 뒤 **공식 MD-V3 동일 모델 실제 새 카메라 폐루프**를 별도 반복시험하여 영상 해시/원본 action/가상 궤적의 일치 검증. 이 시험 전 모델 성능 순위 금지.
