# Big Model Closed-Loop Benchmark

**대형 주행모델의 종·횡방향 판단을 비교하기 위한 순수 가상 폐루프 연구 프로젝트**

> **진행 현황 (2026-11-09):** MD-V3·Light Speed 2·Light Speed **공식 ONNX 3종 실행 기술검증 성공**. MetaDrive 실제 3D S자·진입/진출 램프 영상↔차선 좌표 정합성 진단 성공. **전체 S자 완주, 실제 광학 동등성 및 모델 주행성능 순위는 미검증.** [7단계 진행 기록](docs/ROADMAP_7_STAGES.md).

## 절대 원칙

- **실차 테스트를 수행하지 않습니다.** 실제 차량 CAN, Params 설정 변경, 실도로 주행·튜닝을 개발하지 않습니다.
- **차종별 물리 성능 제외:** 싼타페·쏘렌토 등 EPS, 타이어, 토크, 차량 구동계는 시뮬레이션 결과에 사용하지 않습니다.
- **CD210 제외:** 대형 ONNX 실행 실패 시 CD210이나 소형 모델로 폴백하지 않습니다.
- **Carrot 보정 제외:** 모델 고유 판단과 당근 MPC·경로오프셋·제어기 튜닝을 혼합하지 않습니다.
- **공통 이상적 운동학:** 곡률·가속도에 따른 가상 위치/속도 변화만 계산합니다. 특정 차량의 주행 반응을 모사하지 않습니다.
- **공개 데이터 원칙:** 개인 실주행 로그/영상·기기 식별정보는 이 공개 저장소에 올리지 않습니다.
- **정직한 증거 분류:** 합성 정책/실제 ONNX 입력 추론/가상 차량 상태 갱신/광학 정합성/모델 주행성능을 반드시 구분합니다.

## 검증된 기능과 미완료 사항

| 영역 | 확인된 결과 | 미완료·제약 |
|---|---|---|
| ONNX 런타임 | 공식 MD-V3·Light Speed 2·Light Speed 체크포인트 직접 로드 및 추론 | 다른 후보 추가, N16 전용 내비게이션 공급 |
| 가상 RGB·I420 | MetaDrive 0.4.3 일반·광각 카메라 렌더 및 6채널 영상 모델 입력 | 실제 comma 4 렌즈 왜곡/조도/노출/광학 등가성 |
| S자/램프 3D ↔ 이미지 | 좌→우 S자, 우→좌 S자, 진입·진출 램프 4종 독립 도색 픽셀 진단 PASS | 계절·조명·다양한 지도 확대 검증 |
| 횡방향 모델 루프 | MD-V3·Light Speed 2 각각 동일한 초기 조건에서 실제 MetaDrive 12스텝 실행 | S자 전구간 완주/모델 순위 |
| 종방향 모델 루프 | MD-V3 가상 선행차가 그려진 RGB로 26스텝 가감속 추론 | 전체 감속·정지·재출발·끼어들기 평가 |
| 결과 시각화 | 두 모델 실행 결과의 **오프라인 HTML/SVG 비교 대시보드** 생성 | 상시 운영형 UI, 신뢰 가능한 모델 순위 |
| 재현성 | 이미지 해시·위치·시드 반복 검사 구현 | **반복 RGB 해시 불일치 확인**; 원인 조사 및 고정 가상 시계 테스트 진행 |
| CARLA 교차검증 | 두 엔진의 증거를 요구하는 계약·단위시험 구현 | **실제 CARLA 실행 미실시** |

**중요:** 위 PASS는 가상환경 내부의 기술적 연결·기하 정합성에 관한 판정으로, 대형모델의 현실 주행 성능·안전성 순위와 다릅니다.

## 코드 및 공식 검증 근거

- [7단계 개발 순서·진행 기록](docs/ROADMAP_7_STAGES.md) · [GitHub Issue #1](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/issues/1)
- [대형모델 3종 등록·검증 기록](docs/MODEL_INVENTORY_STATUS.md)
- [광학 정합성·곡선도로 픽셀 검사](docs/METADRIVE_CURVED_LANE_AUDIT.md) — [S자·진입/진출 램프 4종 PASS](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42578810503)
- [차로 중심·침범 독립 평가](docs/LANE_TRUTH_EVALUATOR.md) — [실제 MetaDrive S자·램프 기하 시험](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42582782731)
- [MD-V3·Light Speed 2 실제 12스텝 가상 곡선 폐루프](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42583866722)
- [MD-V3 실제 선행차 영상/가속도 추론 26스텝](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585288256)
- [Light Speed 실영상 입력/추론 5스텝](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585073433)
- [두 공식 ONNX 실행 JSON → HTML 대시보드](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585146636)
- [반복실행 불일치·카메라 드리프트 조사](docs/REPRODUCIBILITY_FINDINGS.md) — [동일 모델 반복 검증 불일치](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585174235)

## 재현 명령

Python 3.11 이상을 권장합니다.

```bash
python -m pip install '.[inference]'
python -m unittest discover -s tests -v

# 모델 파일을 내려받지 않는 읽기 전용 계약 인벤토리
python -m scripts.model_preflight --spec-dir model_specs --out output/model-inventory.json

# 기존 모의 정책으로 기초 폐루프 구조 확인 (공식 성능 점수 아님)
python -m bigbench.cli smoke --scenario s_curve --out output/mock-s-curve

# 이미 실행하여 생성된 두 모델의 기술 진단 JSON을 HTML 대시보드로 변환
python -m scripts.build_dashboard --first output/native-paired/model_a.json \
  --second output/native-paired/model_b.json \
  --comparison output/native-paired/paired_diagnostic.json \
  --out output/native-paired/dashboard.html
```

MetaDrive는 별도 렌더링 의존성, Xvfb 및 공식 자산이 필요하며, 가중치는 **공식 Hugging Face에서 SHA256으로 검증해 임시 캐시로만** 다운로드합니다. GitHub에 ONNX 원본 가중치를 커밋하지 않습니다. 명시된 GitHub Actions 워크플로가 실제 렌더러와 모델의 재현 실행을 담당합니다.

## 참고 프로젝트

- [openpilot](https://github.com/commaai/openpilot)
- [carrotpilot](https://github.com/ajouatom/openpilot/tree/carrot-wip)
- [공식 공개 대형 주행모델](https://huggingface.co/commaai/openpilot_driving_models/tree/main)
- [MetaDrive](https://github.com/metadriverse/metadrive)
- [CARLA](https://github.com/carla-simulator/carla)

> **최종 프로젝트 목적은 대형모델 판단을 가상도로에서 독립적으로 비교하는 것이며, 현재 기준으로 주행모델 간 확정적인 안전성·성능 순위는 제공하지 않습니다.**
