# 기능 구현·실제 검증 현황 (2026-11-09)

**최신 근거:** [GitHub 7단계 로드맵](ROADMAP_7_STAGES.md) / [검증 체크리스트 Issue #1](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/issues/1).

실차 테스트·실차 제어·차종별 물리·CD210·Carrot MPC/Params 최적화는 **영구 제외**한다. 모델 실행의 성공과 모델 성능 판정을 혼동하지 않는다.

| 구분 | 구현/시험 상태 | 정확한 의미 |
|---|---|---|
| 독립 기하학·운동학 | 구현, 합성 단위시험 PASS | 차종별 차량 동역학 미사용 |
| ONNX 계약·SHA·재귀 상태 | MD-V3/Light Speed 2/Light Speed 실제 실행 확인 | 기타 후보의 호환성 미확인 |
| MetaDrive 실제 일반·광각 영상 | MetaDrive 0.4.3/Xvfb CI PASS | 이상적 핀홀 렌더링, 실제 comma 렌즈·색감·카메라 등가 아님 |
| MetaDrive 3D 경계↔영상 도색 | 직선·좌→우/우→좌 S자·진입/진출 램프 PASS | RGB 색 임계값 기반 가상 기하학 진단 |
| 실제 네이티브 목표 차선·침범 계산 | 네 곡선/램프 네이티브 지도 및 합성 경계 시험 PASS | 실도로 모델 성능 아님 |
| 실제 모델 횡방향 폐루프 | MD-V3·Light Speed 2 **각 12스텝** PASS | S자 전체 주행·다중 시드·모델 간 순위 미완료 |
| 두 굽이 S자 네이티브 차로 연결 | 좌→우 및 우→좌 **3개 연결 구간** 지도 게이트 PASS | 실제 ONNX로 둘째 굽이 완주까지 증명하지 않음 |
| 종방향 합성 가상 선행차 | lead_brake/stop_go/cut_in 세계·지표 모듈 구현 | 별도의 카메라 입력 검증 필요 |
| MD-V3 실제 종방향 선행차 영상 | 공식 MD-V3 **26스텝** PASS | 전체 감속·재출발/끼어들기 결과 미검증 |
| 모델 후보 확대 | 공식 Light Speed 5스텝 PASS, N16 manifest 확인 | N16 내비/지도 입력 공급 미구현 |
| HTML+SVG 읽기전용 대시보드 | 실제 MD-V3·Light Speed 2 결과에서 생성 PASS | 모델 순위 금지, 상시 웹 UI 미구현 |
| 다중 시드 매니페스트·반복 검사 | 구현·합성 단위시험 PASS | **실제 같은 MD-V3 모델 반복 영상 해시 MISMATCH** |
| 가상 카메라 고정 시계 | 실험 기능 구현, 실제 MetaDrive 시험 후 판단 | 기본 clock 드리프트 확인; 고정 시계 우열 아직 판정 전 |
| CARLA 독립 엔진 비교 | 데이터 계약과 단위시험만 구현 | **실제 CARLA 렌더링·교차 검증 미실시** |

## 근거가 확인된 GitHub Actions

- [곡선·램프 3D 차선 재투영 4종](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42578810503)
- [네이티브 목표차선·침범 평가기](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42582782731)
- [실제 MD-V3/Light Speed 2 12스텝](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42583866722)
- [두 모델 실행 결과 HTML 대시보드](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585146636)
- [Light Speed 공식 ONNX MetaDrive 영상 5스텝](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585073433)
- [MD-V3 가상 선행차 영상 종방향 추론 26스텝](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585288256)
- [연결된 전체 S자 네이티브 차로 3개 지도 검증](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585805153)
- [실제 ONNX 동일 모델 반복 재현성 불일치](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585174235)
- [고정 가상 포즈에서 기본 Panda 렌더링 드리프트](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42586162386)

## 검증 분류 원칙

- `TEST_DOUBLE_NOT_REAL_ONNX` / `SYNTHETIC_MOCK_ONLY`: 모의 정책·합성 그래프/입력만 평가, 실 ONNX 증거 아님.
- `CONTRACT_INSPECTED_NOT_DRIVING_VALIDATED`: 파일 구조·형상·해시만 확인, 모델 추론·주행 검증 아님.
- `NATIVE_METADRIVE_PINHOLE_MODEL_DIAGNOSTIC_NOT_VALIDATED_RANKING`: 실제 가상 RGB와 ONNX 및 이상적 운동학의 짧은 폐루프 연결 확인, 모델 성능 순위 아님.
- `REPEATED_DIAGNOSTIC_MISMATCH`: 동일 초기 조건에서 영상·위치 데이터 재현 불일치, 원인 해결 전 비교 점수 신뢰성 제약.
- `OPEN_LOOP_ONLY`: 녹화 영상 반복 또는 기록된 modelV2, 폐루프 모델 성적 불인정.
- `CARLA_UNVERIFIED`: 독립 CARLA 실행 증거가 없는 상태.

## 다음 필수 완료 게이트

1. 기본/고정 Panda 시계의 영상 재현성을 같은 환경에서 다시 비교하고 결정적/통제 가능한 렌더 조건 확보.
2. 반복 ONNX 시험에서 동일 시드·체크포인트·경로의 시간축/영상/주행 위치 재현성 확보.
3. 양방향 S자·램프 전 구간의 **두 개 모델 이상, 충분한 연속 시점** 종/횡 폐루프 시험 완료.
4. 선행차 제동·정지·재출발·끼어들기 전체 구간의 모델별 가감속 판단 비교.
5. N16 등 모델별 내비/지도 입력 계약 충족 및 후보 확대.
6. 다중 시드·렌더 조건·독립 CARLA 교차검증. 모델 판단 결과를 실도로 주행성능으로 해석하지 않음.

## 공개·데이터 정책

- 모델 원본 가중치는 공식 Hugging Face에서 해시 고정해 GitHub Actions의 임시 경로로 받는다. 공개 GitHub 소스에 포함하지 않는다.
- 실제 장치/차량 제어 및 원본 개인 실주행로그 업로드는 하지 않는다.
- 기존 CarrotSIM 코드는 구조 참고로만 검토하고 비공개 자산/개인정보·특정 차종 응답 모델을 복사하지 않는다.
