# 공식 대형 ONNX 체크포인트 실행 검증 기록

**검증일:** 2026-11-09 (KST)  
**검증 종류:** 모델 파일·입출력 계약·ONNX Runtime 추론·재귀 상태·가상 영상 폐루프 연결 **구조 시험**  
**실차 시험:** 없음  
**유효한 모델 주행성능 점수:** 없음

## 1. 공식 모델로 확인한 사실

두 모델은 `commaai/openpilot_driving_models`에서 각 파일을 다운로드했고, `ajouatom/openpilot`의 모델 카탈로그 명세에 기재된 원본 ONNX SHA256·파일 크기와 대조한 후 실행했습니다. GitHub Actions의 Ubuntu / Python 3.11 / ONNX Runtime CPUExecutionProvider 환경입니다.

| 모델 | 모델 카탈로그 기대 바이트 | 원본 SHA256 | ONNX 실제 추론 | 5스텝 구조 시험 |
|---|---:|---|---|---|
| MD-V3 | 768,750,198 | `35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199` | 성공 | 성공 |
| Light Speed 2 | 768,749,892 | `909a140019050a9d7f00db22dd4f4085928d2af9474a82244672ddab964f95a8` | 성공 | 성공 |

GitHub Actions 출력은 다음을 확인했습니다.

- 체크포인트 각각 SHA256 검증 다운로드 성공
- 모델 그래프의 입력/출력 이름·형상·타입 검증 성공
- `(2,6,128,256)` 도식적 RGB→I420 패킹 텐서를 각 스텝의 `new_img`에 전달
- `state_*`를 `next_state_*`로 갱신하면서 **5회 연속 실제 모델 추론** 완료
- 모델의 `action`에서 횡가속도·종가속도를 읽고 공통 운동학 갱신 경로 연결
- 모델 오류 시 다른 모델이나 CD210으로 폴백하지 않음

**로그에 남은 CPU 평균 추론시간 (각각 5스텝의 관측값):** MD-V3 **896.3ms**, Light Speed 2 **855.4ms**. 이 수치는 서로 다른 GitHub Actions CPU 인스턴스의 짧은 실행에서 관측됐고, 동일 GPU 비교시험이 아니므로 **모델 간 속도 순위로 해석해서는 안 됩니다.**

### 재현 가능한 증거

- [공식 MD-V3 단일 1스텝 성공](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42566378548)
- [공식 MD-V3 및 Light Speed 2의 5스텝 각각 성공](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42566586103)
- [GitHub Actions 실행 스크립트](../.github/workflows/real-mdv3-one-step.yml)
- [모델 실행기](../bigbench/onnx_policy.py)
- [모델 계약 검사](../bigbench/onnx_contract.py)
- [모델 6채널 I420 영상변환](../bigbench/image_adapter.py)

## 2. 이 시험에서 확인하지 못한 것

이번 합성 영상은 단순한 2D 도식적 도로/선행차 묘사이며 **comma 4의 실제 road/wide 광학·노출·왜곡·보정·워프와 같지 않습니다.**

따라서 모델 출력값이 수치적으로 유한하고 가상 이동으로 연결됐더라도 다음을 주장할 수 없습니다.

- MD-V3와 Light Speed 2 중 어느 모델이 실제로 차선을 더 잘 유지하는지
- S자·램프 코너 커팅의 차이 및 정량적 안전/승차감 점수
- 실제 차량 또는 싼타페의 조향·가감속·차선 이탈 결과
- 20Hz 실시간 처리가 가능하다는 보장
- Light Speed 1, N16, 레거시 큐형 모델 등의 실행 호환성

**현재 출력의 증거 분류:** `ONNX_EXECUTED_SCHEMATIC_INPUT_UNCALIBRATED`  
**허용되는 결론:** 실제 대형 ONNX 모델의 입출력·재귀 상태·기술적 가상 루프 연결이 작동함  
**금지되는 결론:** 대형모델 주행성능 비교·순위·실도로 안전성 검증 완료

## 3. 이어서 필요한 작업

1. MetaDrive/CARLA 등에서 가상 위치에 따른 **실제 카메라 광학 모델 기반 이미지**를 생성하는 렌더러 인터페이스 구성.
2. comma의 영상 전처리·투영/왜곡 보정과 비교 가능한 이미지 정합성 검증.
3. 더 많은 대형모델의 입력 계약 지원(특히 N16의 지도 입력, 과거 queued export의 입력 상태 관리).
4. 위 조건이 만족된 다음에만 횡방향·종방향 모델 성능 평가, 반복 시드 및 통계 보고서 실시.

**고정 제외:** 실차 테스트, 특정 차량의 성능 파라미터, CD210 비교·폴백, Carrot Params 튜닝 및 실차 CAN 송신.
