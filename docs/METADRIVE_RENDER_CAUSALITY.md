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

**검증 상태:** 본 문서에 적힌 시험코드의 구현·단위시험과 실제 native-render 시험 결과는 분리한다. CI 아티팩트의 6개 조건별 JSON 및 `causality_summary.json`을 확인하기 전에는 특정 원인/해결을 확정하지 않는다.
