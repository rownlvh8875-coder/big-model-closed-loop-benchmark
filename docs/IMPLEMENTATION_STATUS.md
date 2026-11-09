# 실행 구현 현황 / Validation levels

기준: 2026-11-09. 이 프로젝트에서는 실차 테스트를 **절대** 수행하지 않는다.

| 단계 | 상태 | 재현 방법 | 실제 의미 |
|---|---|---|---|
| 합성 곡률 기반 도로/가상 에이전트 | 구현·로컬 단위시험 | `python -m unittest discover -s tests -v` | 특정 차량 동역학 없음 |
| 모의 RGB 카메라 프레임 | 구현·로컬 시험 | `python -m bigbench.cli smoke --scenario s_curve` | **도식적 영상**이며 실제 모델 입력에 대한 검증 아님 |
| 위치 변경 → 다음 영상 변경 | 구현·로컬 시험 | `test_schematic_camera_changes_when_ego_position_changes` | 구조적 영상 폐루프 검증 |
| 서로 다른 모의 카메라 정책 → 다른 궤적 | 구현·로컬 시험 | `test_distinct_mock_commands_change_trajectory` | **모의 정책만 사용**; ONNX 주행 성능이 아님 |
| 횡방향 오차·차선 침범·선행차 간격 | 구현·로컬 시험 | `frames.csv`, `summary.json` | 공통 폭을 갖는 가상 에이전트의 기하 지표 |
| 반복가능한 결과·CSV·PNG | 구현·로컬 시험 | `output/mock_smoke` | 모의 출력에 한함 |
| 공식 HF 공개 ONNX 목록 조회 | 도구 구현, 네트워크 미검증 | `python -m scripts.hf_models list` | 실제 파일 다운로드 없음 |
| SHA256 고정 단일 모델 다운로드 | 도구 구현, 네트워크/대형파일 미검증 | `python -m scripts.hf_models download ...` | 네트워크·디스크·사용자 명시적 선택 필요 |
| ONNX I/O 검사기 | 코드 구현, 실제 ONNX 미검증 | `pip install onnxruntime` 후 `python -m bigbench.cli inspect-onnx ...` | 실제 모델 추론 아님 |
| 실제 대형모델 추론 및 재귀 상태 유지 | **미구현** | — | 모델별 전처리·보정·입력 계약 추가 필요 |
| 실제 대형모델 영상 폐루프 성능 비교 | **미실시** | — | 실측 성능 순위 없음 |
| MetaDrive/CARLA 렌더러 연결 | **미구현** | — | 합성 RGB는 실제 모델 검증에 부적합할 수 있음 |
| 차량·실차·CAN·Carrot Params 조작 | **범위에서 영구 제외** | — | 이 프로젝트가 담당하지 않음 |

## 강제 구분

- `SYNTHETIC_MOCK_ONLY`: 현재 로컬 시험과 예제에서만 사용; **대형모델 성능 결과가 아님**.
- `CONTRACT_INSPECTED_NOT_DRIVING_VALIDATED`: ONNX 입력·출력 확인; 추론·폐루프 불합격.
- `UNVERIFIED_MODEL`: 자체 추론 검증·카메라 전처리·상태 검증 없는 외부 정책; 공식 성능 점수로 사용 금지.
- `OPEN_LOOP_ONLY`: 기록/사전 영상만 재생한 경우; 폐루프 결과로 주장 금지.

## 모델 다운로드를 자동으로 하지 않는 이유

공식 Hugging Face 저장소 `commaai/openpilot_driving_models`의 전체 용량은 여러 GB에 이른다. 이 리포지토리는 **모델 가중치를 GitHub에 직접 저장하지 않는다.** 개별 모델의 입력 계약·라이선스·해시·스토리지 요구량을 검증한 후, 다운로드 명령으로 파일 하나를 명시적으로 선택해야 한다.

## 다음 구현 게이트

1. ONNX 체크포인트의 입출력 명세를 직접 검사하고 모델별 변환기/재귀 상태 검증.
2. 가상 카메라 영상 → 모델이 요구하는 이중 영상/YUV/워프 표현으로 변환, 변환 정합성 테스트.
3. 모델의 원본 곡률·가속도 출력 → 동일 이상적 운동학 → 다음 모델 입력 영상으로 재연결.
4. MetaDrive 또는 CARLA 렌더러의 영상 품질과 차량 자세 재투영 검증.
5. 모델별 동일 시나리오 비교, 반복 실행, 지표 통계 및 한계 보고.

기존 CarrotSIM 자산은 설계 참고로만 분석했으며, 비공개 파일·실차 로그·차량 응답 코드는 복사하지 않았다.
