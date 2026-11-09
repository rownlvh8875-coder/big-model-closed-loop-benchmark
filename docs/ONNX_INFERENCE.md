# 대형 주행모델 ONNX 실행기 — 구현/검증 경계

> 기준: 2026-11-09. **실차 테스트 없음 · CD210 사용 안 함 · 특정 차량 성능 파라미터 없음.**

## 지금 구현된 것

- 공식 `carrot-wip` 모델 카탈로그와 구조가 같은 **stateful** ONNX 그래프용 실행기 (`bigbench/onnx_policy.py`)
- ONNX 파일 **SHA256 + 바이트 크기**, 입력·출력 이름/형상/타입, `state_*` → `next_state_*` 계약 검사
- 매 실행마다 두 영상 `(2,6,128,256)`으로 변환하고 동일한 메모리 상태를 이어받아 추론
- 콤마 소스 `compile_modeld.py`의 `frames_to_tensor`와 같은 **I420 Y 채널 2×2 샘플 + U/V 플레인 패킹** (`bigbench/image_adapter.py`)
- 모델의 원시 action 중 **횡가속도 → 곡률** `action[0] / max(2.5, v_ego)**2`, `action[1]` 종가속도 추출 (Carrot MPC/토크보정/평활화 사용하지 않음)
- 모델 출력 결측·비유한값·상태 불일치·해시 불일치 시 즉시 실패; CD210 폴백 없음
- 실제 ONNX Runtime을 사용한 **소형 합성 테스트 그래프** 검증을 위한 GitHub Actions 작업

## 공식 대형모델 실행 검증 (2026-11-09)

MD-V3와 Light Speed 2 모델을 공식 Hugging Face에서 SHA256/크기를 검증하고 다운로드하여, GitHub Actions CPU 환경에서 각각 **5스텝** 실행했습니다. 둘 다 ONNX 모델의 `new_img` 입력과 recurrent state 전달을 포함한 전체 구조 시험에 통과했습니다. 결과는 [실행 기록](REAL_MODEL_SMOKE_RESULTS.md) 참조.

이 결과는 **ONNX 실행기 호환성 검증이지 주행모델 성능 검증이 아닙니다**. 영상은 카메라 광학이 검증되지 않은 도식적 영상이므로 다른 모델과 비교한 순위나 차선 유지 성능 점수는 발표하지 않습니다.

## 가장 중요한 한계

**현재 그림 생성기는 512×256의 도식적 RGB 화면 두 개를 생성할 뿐, 실제 comma 4의 광학계가 아닙니다.**

- 실제 comma road/wide 카메라의 서로 다른 내부 파라미터, 렌즈 왜곡, 외부 파라미터, 촬영 높이, 포토메트릭 특성, 정확한 perspective warp는 아직 재현되지 않았습니다.
- `rgb_frame_to_six`는 픽셀 배열 포맷만 맞춥니다. **텐서 크기가 맞는 것이 모델 의미의 정상 주행 입력을 보장하지 않습니다.**
- 입력이 도식적 영상이므로 실제 ONNX 실행에 성공하더라도 *도로 인식 정확도 / 안전 / 모델 순위 / 성능 우열*로 발표하면 안 됩니다.
- 공식 MD-V3 및 Light Speed 2 가중치는 GitHub Actions **임시 CPU 실행기**에서 성공적으로 추론했지만, 본 로컬 컨테이너에 원본 가중치나 ONNX Runtime을 영구 저장하지 않았습니다. GPU/Jetson 성능은 검증하지 않았습니다.
- 모델 입력 영상이 차량 이동에 반응하지만, 현실적인 camera-rendering 폐루프로서 유효한지는 **MetaDrive/CARLA 등 별도 렌더러 및 정합성 검증**이 필요합니다.
- **과거 큐를 그래프 내부 상태로 갖는 옛 queued 모델** (`img`, `big_img`, `features_buffer`)은 현재 지원하지 않습니다. `new_img`와 `state_*`/`next_state_*`를 갖는 모델만 지원합니다.
- **N16 지도 모델:** `nav_map`·`navigation`을 실제 계약대로 제공하는 소스가 아직 없어서 기본 CLI에서 실행 실패합니다. 임의의 0을 넣어 시험 결과를 만들지 않습니다.

## 실행 방법 (설치된 컴퓨터에서)

Python 3.11+ 및 충분한 메모리가 필요합니다. 대형 모델은 파일 자체가 수백 MB 이상이며, CPU 실행 가능성은 모델마다 다릅니다.

```bash
python -m pip install '.[inference]'
python -m unittest discover -s tests -v
```

해시 검증을 위해 **해당 ONNX 체크포인트와 일치하는 모델 카탈로그 명세**를 사용합니다. 이 프로젝트에 포함된 `model_specs/` 파일은 소스 코드에 공개된 **카탈로그 명세 스냅샷**으로, 실제 ONNX 다운로드 파일의 해시 검증을 통과해야 합니다.

```bash
python -m bigbench.cli inspect-onnx models/your-big-model.onnx
python -m bigbench.cli run-onnx \
  --model models/your-big-model.onnx \
  --spec model_specs/light-speed-2.json \
  --scenario s_curve \
  --steps 10 \
  --out output/onnx-schematic-smoke \
  --accept-uncalibrated-vision
```

`--accept-uncalibrated-vision`이 없으면 실행하지 않습니다. 위 경로 `models/your-big-model.onnx`는 **예시**이며 현재 저장소에 모델이 포함된 것이 아닙니다. 각 모델의 크기·해시를 검사한 뒤 개인 로컬 캐시에 내려받아야 합니다.

출력:

- `frames.csv`: 가상 에이전트 중심 편차·속도·곡률·차선 경계 근접
- `model_inference.csv`: 각 스텝 원시 횡가속도·종가속도·목표곡률·추론지연
- `summary.json`: **ONNX_EXECUTED_SCHEMATIC_INPUT_UNCALIBRATED** 분류 및 SHA256
- `first_camera.png`, `last_camera.png`: 가상 영상 경로가 위치에 따라 달라짐을 확인하기 위한 이미지

**모델별 성능 순위를 산출하지 않습니다.** 특히 추론 지연이 0.05초를 넘더라도 결정적 가상 시간은 바꾸지 않으며, 실시간 성능 측정은 별도의 지표입니다.

## 검증 단계

| 게이트 | 현재 상태 | 근거 |
|---|---|---|
| 입력·출력 계약 / 파일 해시 검증 | 코드 + 단위시험 | `onnx_contract.py`, `test_onnx_runtime_policy.py` |
| I420 6채널 레이아웃 | 구현 + 단위시험 | `image_adapter.py` |
| 비정상 모델 거절 및 recurrence | 코드 + 테스트 더블 | `onnx_policy.py`, `test_onnx_runtime_policy.py` |
| ONNX Runtime로 ONNX 추론 실제 호출 | GitHub Actions 전용 소형 테스트 그래프 | `test_onnx_ort_integration.py` |
| 공식 commaai 대형 ONNX 추론 | **MD-V3·Light Speed 2 각각 5스텝 통과** | `REAL_MODEL_SMOKE_RESULTS.md` 및 GitHub Actions 실행 기록 |
| 정확한 카메라 광학·왜곡·워프 | **미검증** | 광학 파라미터·렌더러 필요 |
| 실제 대형모델의 의미 있는 폐루프 비교 | **미완료** | 위 조건 충족 전 금지 |

## 소스 기준

- [`ajouatom/openpilot` carrot-wip commit `e318f767`](https://github.com/ajouatom/openpilot/tree/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42)
- [모델 카탈로그](https://github.com/ajouatom/openpilot/tree/carrot-wip/openpilot/selfdrive/modeld/model_catalog)
- [I420 패킹 근거 `compile_modeld.py` 100–109행](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/selfdrive/modeld/compile_modeld.py#L100-L109)
- [행동 출력 변환 근거 `modeld.py` 94–125행](https://github.com/ajouatom/openpilot/blob/e318f767ff7dc96d25a3bcc2b46f9f3daf6e9e42/openpilot/selfdrive/modeld/modeld.py#L94-L125)
- [공식 공개 모델](https://huggingface.co/commaai/openpilot_driving_models/tree/main)

## 저장소 공개·안전 정책

- 가중치·기기 식별 정보·개인 영상·주행로그는 공개 GitHub에 업로드하지 않습니다.
- 이미 공개된 모델은 공식 Hugging Face에서 얻습니다. 별도의 사용자 Hugging Face 업로드는 **현재 필요하지 않습니다**.
- 실제 차량 CAN, 파라미터·조향·구동계 제어 코드를 포함하지 않습니다.
