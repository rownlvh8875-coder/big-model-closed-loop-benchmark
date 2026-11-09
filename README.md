# Big Model Closed-Loop Benchmark

**대형 주행모델의 순수 횡방향·종방향 판단을 비교하기 위한 독립 폐루프 연구 프로젝트**

> **현재 상태: 실제 MD-V3·Light Speed 2 ONNX 각 5스텝 기술적 실행 성공 · 도식적 비보정 카메라 환경 · 주행성능 비교 미검증**

## 고정 원칙

- **실차 테스트 전면 금지** — 실도로 주행·실차 제어·CAN 송신·실차 Params 변경 기능을 포함하지 않습니다.
- **특정 차량 성능 평가 제외** — 싼타페·쏘렌토의 EPS, 타이어, 토크, 휠베이스, 구동계 특성을 사용하지 않습니다.
- **CD210 제외** — 모델 실행 실패 시 CD210 등 소형 모델로 폴백하지 않습니다.
- **Carrot 제어기 보정 제외** — 레인모드 MPC, 경로 오프셋, 조향 토크·속도 보정 등을 모델 성능 지표에 섞지 않습니다.
- **모델 출력 비교를 위한 공통 이상적 운동학** — 모든 시험 정책에 동일한 곡률·가속도 적분 규칙을 적용합니다.
- **기존 실차 주행로그는 선택적 오프라인 참고만** — 신규 실차 데이터 수집 불필요, 원본/민감정보를 공개하지 않습니다.

## 이번에 구현한 기능

| 기능 | 상태 | 주의사항 |
|---|---|---|
| 곡률 기반 합성도로 | **구현** | 직선, S자, 좌·우 램프 |
| 차종 독립 2D 이상적 운동학 | **구현** | 실차 물리 모델이 아님 |
| 가상 카메라 영상 렌더링 | **도식적 RGB 프로토타입** | 실제 ONNX 영상 정합성 미검증 |
| 모델 출력 → 위치/방향 → 다음 영상 폐루프 | **모의 카메라 정책으로 검증** | 실제 대형 ONNX 모델 실행 아님 |
| 선행차 감속 합성 시나리오 | **구현** | 선행차 비대응 외생 시나리오 |
| 차선 침범·중심 편차·반복성 지표 | **구현** | 가상 에이전트의 기하 지표 |
| 실행 로그 CSV/JSON · 첫/마지막 PNG | **구현** | 모의 정책 보고서는 `SYNTHETIC_MOCK_ONLY` |
| 두 모의 정책·4개 시나리오 비교 | **실행·로컬 시험** | **모델 성능 순위로 사용 금지** |
| ONNX 입출력·해시 조회 도구 | **코드 구현** | 실제 ONNX 파일 및 optional onnxruntime 필요 |
| 공식 Hugging Face ONNX 목록·명시적 해시 다운로드 도구 | **구현, 2개 공식 모델 SHA256 다운로드 검증** | 대용량 모델은 임시 Actions 환경에서만 다운로드 |
| 실제 대형모델 재귀 추론·영상 전처리 | **MD-V3·Light Speed 2 5스텝 실행 성공** | 단, 현재 영상은 도식적 비보정 입력이며 주행성능 검증 불가 |
| MetaDrive/CARLA 고화질 카메라 폐루프 | **미구현** | 합성 RGB 프로토타입과 별도 |

**중요:** 현재 생성하는 수치와 그래프는 **모의 정책에 대한 구조 검증** 결과이지, 대형모델의 종·횡방향 성능 평가가 아닙니다.

## 실행 방법

Python **3.11 이상**이면 기초 합성 시험에 별도 패키지 설치가 필요하지 않습니다.

```bash
# 저장소 루트에서 단위시험
python -m unittest discover -s tests -v

# 하나의 S자 곡선에 대한 도식적 RGB 폐루프 검증
python -m bigbench.cli smoke --scenario s_curve --out output/s_curve

# 2개 모의 카메라 정책 × 4개 시나리오 = 8개 합성 검증
python -m bigbench.cli smoke-compare --out output/mock_comparison

# 선택적: 공식 Hugging Face 메타데이터 조회 (네트워크 필요, 가중치 다운로드 없음)
python -m scripts.hf_models list

# 선택적: 로컬 ONNX 입출력 계약/해시 조사 (실제 추론 아님)
python -m pip install onnxruntime
python -m bigbench.cli inspect-onnx /path/to/model.onnx
```

`smoke` 실행 시 `frames.csv`, `summary.json`, `first_camera.png`, `last_camera.png`가 생성됩니다. `smoke-compare`는 `comparison.json`을 추가로 생성합니다. 결과는 `output/`에 저장하며 GitHub에 게시하지 않습니다.

모델 파일은 **자동 다운로드하지 않습니다.** 개별 모델의 파일 크기, SHA256 및 입출력 계약을 검증한 뒤 필요할 때 `python -m scripts.hf_models download --path ... --sha256 ...`를 사용하도록 설계했습니다. 모델 가중치를 공개 GitHub에 커밋하지 않습니다.

## 실제 대형 ONNX 기술적 실행 검증 (2026-11-09)

- **MD-V3:** 공식 ONNX(768,750,198바이트) SHA256 검증, CPU ONNX Runtime **5스텝 성공**
- **Light Speed 2:** 공식 ONNX(768,749,892바이트) SHA256 검증, CPU ONNX Runtime **5스텝 성공**
- 모델별 `new_img` 이중 카메라 I420 입력, `state_*` → `next_state_*` 갱신, 곡률·가속도 변환 및 변한 가상 위치의 다음 프레임 전달을 실행했습니다.
- **영상 광학·왜곡·정합성은 미검증**이므로 모델별 차선 유지 성능이나 주행 안전성 순위는 만들지 않았습니다.

[공식 대형모델 연속 5스텝 Actions 기록](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42566586103)

ONNX 실행 테스트(별도 컴퓨터에서, 원본 모델을 직접 내려받은 경우):

```bash
python -m pip install '.[inference]'
python -m bigbench.cli run-onnx --model models/YOUR_MODEL.onnx \
  --spec model_specs/md-v3.json --scenario s_curve --steps 5 \
  --accept-uncalibrated-vision
```

이 명령은 **기술적 구조 시험**이며 실제 주행 성능 벤치마크가 아닙니다.

## 문서

- [PROJECT_PLAN.md](PROJECT_PLAN.md) — 전체 계획서 및 기존 CarrotSIM 자산 활용 방안
- [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md) — 검증 수준과 미구현 사항의 명시적 구분
- [docs/ONNX_INFERENCE.md](docs/ONNX_INFERENCE.md) — 실제 모델 실행기, 입력 변환, 제한 사항
- [docs/REAL_MODEL_SMOKE_RESULTS.md](docs/REAL_MODEL_SMOKE_RESULTS.md) — 공식 ONNX 모델 실행 결과 및 근거

## MetaDrive 가상 카메라 광학 연동 및 공식 대형 ONNX 실행 (기술적 검증 완료)

- [MetaDrive 광학·핀홀 워프 검증 문서](docs/METADRIVE_OPTICAL_CALIBRATION.md)
- [실제 MetaDrive 일반·광각 RGB 렌더링 PASS](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42569322601)
- [MetaDrive RGB → ONNX 입력 (2,6,128,256) PASS](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42569804426)
- [공식 MD-V3 + 실제 MetaDrive 카메라 3스텝 추론 PASS](docs/METADRIVE_MDV3_SMOKE_RESULTS.md) ([GitHub Actions 증거](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42570111317))
- [실카메라 광학 게이트 워크플로](.github/workflows/metadrive-optical.yml) 및 [공식 MD-V3 통합시험 워크플로](.github/workflows/metadrive-mdv3-inference.yml)

**증거 범위:** 실제 MetaDrive 렌더링 영상의 핀홀 내부 파라미터·YUV6 입력 규격 및 실제 MD-V3 ONNX 재귀 추론/가상 위치 갱신의 **기술적 연결만 확인**했습니다. 실제 comma의 렌즈 왜곡·외부 캘리브레이션·광학 정합, 도로 정답 기준 성능, 코너 커팅/종방향 모델 순위는 미검증입니다.

## 참고 저장소

- [carrotpilot / carrot-wip](https://github.com/ajouatom/openpilot/tree/carrot-wip)
- [commaai/openpilot](https://github.com/commaai/openpilot)
- [commaai 대형모델](https://huggingface.co/commaai/openpilot_driving_models/tree/main)
- [기존 Carrot-comma-SIM](https://github.com/rownlvh8875-coder/Carrot-comma-SIM)
- [기존 비공개 CarrotSIM](https://github.com/rownlvh8875-coder/carrotsimPrivately-)
- [MetaDrive](https://github.com/metadriverse/metadrive)
- [CARLA](https://github.com/carla-simulator/carla)

**이 프로젝트는 실차 안전성 검증이 아니며, 실제 차량 성능이나 주행 안전성을 보장하지 않습니다.**
