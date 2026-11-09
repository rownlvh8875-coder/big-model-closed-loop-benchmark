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
| 공식 HF 공개 ONNX 목록 조회 | 도구 구현, 실 모델 다운로드 환경 확인 | `python scripts/hf_models.py list` | 공식 2개 모델 파일은 Actions 임시 저장소에 SHA 확인 후 다운로드됨 |
| SHA256 고정 단일 모델 다운로드 | **MD-V3·Light Speed 2 파일 검증 완료** | `python scripts/hf_models.py download ...` | 두 모델의 체크포인트 다운로드 성공, 파일은 Actions 종료 후 미보존 |
| ONNX I/O 검사기 | 코드 구현, 실제 2개 모델 그래프 계약 검증 | `pip install onnxruntime` 후 `python -m bigbench.cli inspect-onnx ...` | 실제 모델 추론 아님 |
| 대형 ONNX 실행기 및 recurrent state 연결 | **구현; 공식 MD-V3·Light Speed 2 연속 5스텝 추론 성공** | `bigbench/onnx_policy.py`, `tests/test_onnx_runtime_policy.py` | 해시/입출력/메모리 상태 계약 검증; 카메라 광학 미검증 |
| 실제 대형모델 영상 폐루프 성능 비교 | **미실시** | — | 실측 성능 순위 없음; 도식적 RGB는 비검증 입력 |
| MetaDrive 광학 정합 계층(기하학) | **구현, 단위시험 검증** | `python -m unittest discover -s tests -p test_optical_calibration.py -v` | 핀홀 내부 파라미터·기준점 투영 검증만 완료; 실제 MetaDrive 광학 검증 아님 |
| MetaDrive 실제 RGB 장면 캡처 | **MetaDrive 0.4.3 실제 오프스크린 RGB 프레임 생성 PASS** | 수동 워크플로 `metadrive-optical.yml` | GitHub Actions [42569322601](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42569322601)에서 두 렌즈의 핀홀 초점거리·프레임 변경 확인; 실제 광학 등가성은 미검증 |
| MetaDrive RGB→I420/YUV6 실제 입력 텐서 | **PASS** | [실제 카메라 입력 CI 42569804426](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42569804426) | (2,6,128,256), uint8, 두 카메라별 독립 프레임 및 가상 위치 이동 후 텐서 변경 |
| MetaDrive × 공식 MD-V3 실제 ONNX 영상 루프 | **3스텝 PASS (기술적 연결에 한정)** | [실제 MD-V3 CI 42570111317](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42570111317), [검증 결과 문서](METADRIVE_MDV3_SMOKE_RESULTS.md) | 원본 MD-V3 모델 가중치 사용, 상태 갱신·가상 이동·다음 영상 재추론; 실제 광학 및 주행성능 점수는 미검증 |
| MetaDrive 3D 차선좌표↔영상 픽셀 | **실제 MetaDrive 0.4.3 직선 도로·일반/광각 2자세 재투영 PASS** | [GitHub Actions 42573166387](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42573166387), [측정 보고서](METADRIVE_LANE_REPROJECTION.md) | 3D 차선 경계와 RGB 도색 픽셀 비교 오차 중앙값 0.765~1.467px, 27px 오정렬 음성대조 구분; **커브/실제 렌즈/모델 주행성능은 미검증** |
| CARLA 렌더러·광학 왜곡/외부 파라미터/시각 도메인 | **미검증** | — | 실제 comma 광학 등가성 및 모델 주행성능은 아직 검증 전 |
| 차량·실차·CAN·Carrot Params 조작 | **범위에서 영구 제외** | — | 이 프로젝트가 담당하지 않음 |

## 강제 구분

- `SYNTHETIC_MOCK_ONLY`: 현재 로컬 시험과 예제에서만 사용; **대형모델 성능 결과가 아님**.
- `CONTRACT_INSPECTED_NOT_DRIVING_VALIDATED`: ONNX 입력·출력 확인; 추론·폐루프 불합격.
- `UNVERIFIED_MODEL`: 자체 추론 검증·카메라 전처리·상태 검증 없는 외부 정책; 공식 성능 점수로 사용 금지.
- `OPEN_LOOP_ONLY`: 기록/사전 영상만 재생한 경우; 폐루프 결과로 주장 금지.

## 모델 다운로드를 자동으로 하지 않는 이유

공식 Hugging Face 저장소 `commaai/openpilot_driving_models`의 전체 용량은 여러 GB에 이른다. 이 리포지토리는 **모델 가중치를 GitHub에 직접 저장하지 않는다.** 개별 모델의 입력 계약·라이선스·해시·스토리지 요구량을 검증한 후, 다운로드 명령으로 파일 하나를 명시적으로 선택해야 한다.

## ONNX 실행기 추가 안내

[ONNX_INFERENCE.md](ONNX_INFERENCE.md) 및 [REAL_MODEL_SMOKE_RESULTS.md](REAL_MODEL_SMOKE_RESULTS.md) 참조. 주입 세션 테스트 더블과 소형 테스트 그래프 시험은 별도이며, **공식 MD-V3·Light Speed 2 모델 각각 실제 5스텝 추론**도 완료했습니다. 단 도식적 카메라의 광학 정합성과 주행 성능은 미검증입니다.

**MetaDrive 광학 단계 문서:** [`METADRIVE_OPTICAL_CALIBRATION.md`](METADRIVE_OPTICAL_CALIBRATION.md). 핀홀 기하학 검사는 실제 광학/주행성능 검증이 아니며, 실제 MetaDrive 0.4.3 렌더링·위치 변경에 따른 일반/광각 영상 변화와 공식 MD-V3 3스텝 기술적 영상 폐루프 연결은 [GitHub Actions 42569322601](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42569322601)에서 확인했으나 실제 comma 렌즈·영상 도메인과의 정합성은 미검증.

## 다음 구현 게이트

1. 나머지 대형모델 체크포인트의 입출력 명세·전처리·재귀 상태 확대 검증 (MD-V3 및 Light Speed 2는 5스텝 성공).
2. 현재 구현된 이중 I420/YUV 패킹을 실제 MetaDrive 렌더링 이미지에 적용하는 입력 구조·프레임 변경 게이트 검증(별도 CI 진행 중). 실제 comma 렌즈 왜곡·외부 보정·카메라 동등성은 향후 검증.
3. 기존 합성 도식 입력의 연속 추론 성공을 확인했으므로 실제 모델 시각 도메인에 적합한 렌더러로 폐루프를 재검증.
4. MetaDrive 직선 도로 재투영(일반·광각 2자세)은 검증했으며, **S자 곡선·램프 맵, 3D 차선-픽셀 정합성 확대와 카메라 외부/왜곡/영상 도메인 검증**은 별도 후속 게이트로 유지.
5. 모델별 동일 시나리오 비교, 반복 실행, 지표 통계 및 한계 보고.

기존 CarrotSIM 자산은 설계 참고로만 분석했으며, 비공개 파일·실차 로그·차량 응답 코드는 복사하지 않았다.
