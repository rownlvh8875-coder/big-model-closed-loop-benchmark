# Seven-stage development roadmap / 7단계 지속 개발 로드맵

기준: 2026-11-09 KST. 이 문서는 후속 대화·개발 세션에서 **진행 위치를 확인하기 위한 단일 작업 목록**이다. 사용자가 요청한 순서대로 차례로 수행하며 **실행되지 않은 시험을 PASS로 표시하지 않는다.**

## 고정 정책

- **실차 테스트 영구 제외:** 어떠한 단계에서도 실제 차량·실차 CAN·원격 차량 제어·실차 튜닝을 수행하지 않는다.
- **특정 차종 성능 제외:** 싼타페·쏘렌토 등 EPS·토크·타이어·차량 동역학을 성능 비교에 사용하지 않는다.
- **CD210 제외:** 대형 ONNX 모델만 비교하고 모델 오류 시 자동 폴백하지 않는다.
- **원본 모델 판단 분리:** Carrot 경로 MPC, 종방향·횡방향 튜닝과 모델 판단 성능을 혼합하지 않는다.
- **비공개 정보 보호:** 실주행 로그는 선택적인 오프라인 참고에 한정하고 공개 저장소에 업로드하지 않는다.
- **검증 증거:** 완료 단계는 해당 코드 커밋, 재현 명령, CI 실행 URL, 정량 결과, 적용 한계가 있어야만 완료로 변경한다.
- **시간 제약:** ChatGPT 세션 종료 뒤 개발이 자동 계속되는 것은 아니다. 다음 세션 시작 시 이 문서와 연결된 증거를 재확인한다.

## 순차 개발 목록

| 단계 | 목표 | 현재 상태 | 완료 조건 |
|---|---|---|---|
| **1** | S자 곡선·고속도로 진입/진출 램프 3D 차선 ↔ 실제 MetaDrive RGB 픽셀 재투영 | **완료 (초기 진단)** | 방향이 반전되는 S자 실제 3D 곡선과 진입/진출 램프의 실제 3D 차선을 각각 검증. road/wide 카메라, 2개 이상의 자세, 픽셀 잔차·검출률·음성대조·실패를 증거로 남김 |
| **2** | 차선 중심·침범 평가기 독립 검증 | **완료 (네이티브 기하 진단)** | 시뮬레이터 월드 좌표에서 진실값 도출, 좌우 부호·곡률 반전·차선폭·이탈 깊이 수학/단위시험 및 사전 기준 확정 |
| **3** | MD-V3 vs Light Speed 2 횡방향 실제 ONNX 폐루프 비교 | **진행 중 (12스텝 × 2모델 PASS)** | 동일 월드·시드·초기조건·이상적 운동학·실제 가상 영상·내부 상태관리, 반복 실행. 비정상 추론은 FAIL |
| **4** | 종방향 모델 평가 | **진행 중 (합성 세계·실영상 시험)** | 기준 횡방향 경로를 고정하고 감속·추종·정지·재출발 시나리오를 공통 조건으로 검증 |
| **5** | 그 밖의 대형모델 확대 | **진행 중 (3종 실행 확인)** | 모델별 ONNX 계약·해시·재귀 상태·내비 입력 분리, 조건을 만족한 모델만 벤치마크에 편입 |
| **6** | 모델별 결과 대시보드 | **진행 중 (오프라인 HTML 구현)** | 모델별 원본 plan/action, 진실값 차선 경계, 가상 경로, 종/횡 점수, 오류·반복 변동폭을 비교 |
| **7** | 장시간·반복·외부 엔진 교차검증 | **진행 중 (반복 영상 불일치 발견·CARLA 미검증)** | 여러 시드·곡선/램프·시간 간격·카메라 민감도; 필요 시 CARLA에서 검증. 적용 범위와 한계 고지 |

**상태 원칙:** `완료` / `진행 중` / `미착수` / `차단` / `미확인`만 사용하며 CI가 아직 안 돌았으면 ‘구현 완료’와 ‘실제 검증 통과’를 분리한다.

## 이미 확보된 기반 — 신규 7단계 완료 판정과 별개

- 독립 ONNX 실행기, MD-V3와 Light Speed 2의 기존 단기 추론 확인.
- 실제 MetaDrive 0.4.3 일반·광각 렌더링과 3D **직선** 차선 재투영의 초기 진단 확인.
- 관련 기록: [직선 차선 픽셀 정합성](METADRIVE_LANE_REPROJECTION.md), [광학 캘리브레이션](METADRIVE_OPTICAL_CALIBRATION.md), [ONNX 추론](ONNX_INFERENCE.md).

## 진행 기록

- **2026-11-09:** 7단계 작업 목록 고정. MetaDrive의 원시 곡선·진입/진출 램프 차선 재투영과 실렌더링 CI를 검증. [GitHub Actions #42578810503](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42578810503)에서 좌→우 S자, 우→좌 S자, 진입 램프, 진출 램프 **네 장면 모두 진단 PASS**를 확인. 해당 결과는 MetaDrive 내부 핀홀 투영·색 임계값 기반 도색 검출에 한정되며 실제 렌즈/도로/모델 성능 증거가 아니다.
- **다음 검증 항목:** 2단계 `bigbench/lane_truth.py`의 차선 중심·침범 판단을 실제 MetaDrive 곡선/램프 월드 좌표와 결합하고, 목표 차로가 바뀌는 분기·합류에서 잘못된 최근접 차로 선택을 방지한다. 1단계의 PASS는 정해진 카메라/시나리오에서의 진단값으로서 장시간·다양한 조명으로 일반화할 수 없다.

- **2026-11-09:** [MetaDrive 네이티브 기하 CI #42582782731](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42582782731) 로그에서 S자 2종·램프 2종의 목표 차선 위치/오프셋/0.2m 침범 예제와 기존 카메라 차선 재투영 모두 PASS 확인. **2단계 초기 기하학적 검증 완료**, 차선 변경·합류 시 목표 차선 선택 정책은 향후 벤치마크에서 명시해야 하며 실제 주행모델의 성능을 검증하지 않음. **3단계 시작.**

## 2–7단계 후속 개발 기록 (2026-11-09, 증거 기준)

- **3단계:** [GitHub Actions #42583866722](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42583866722)에서 SHA256 고정 MD-V3 및 Light Speed 2를 **같은 MetaDrive S자 첫 곡선·고정 속도로 12스텝씩** 실제 실행. `bigbench/native_model_campaign.py`, `scripts/compare_native_onnx.py` 구현. 기술적 모델-카메라-운동학 폐루프 PASS이며 **전체 S자 완주·차량/실도로 성능 순위는 미검증**.
- **4단계:** `bigbench/longitudinal_world.py`의 가상 선행차 감속·정지/재출발·끼어들기 및 `native_longitudinal.py`의 영상 기반 원시 ONNX 가속도 루프 코드 구현. 첫 네이티브 MD-V3 시험 [#42584970188](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42584970188)에서는 선행차 생성 시 `spawn_lane_index` 누락으로 실패했으나 수정 후 [#42585288256](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585288256)에서 **MD-V3 가상 선행차 영상·가감속 26스텝 PASS**. 감속·정지·재출발 전체 종방향 성능 검증은 미완료.
- **5단계:** `bigbench/model_eligibility.py`와 테스트로 SHA 고정 모델 명세·재귀 입력·내비게이션 조건 검증. 기존 두 모델에 더해 [공식 Light Speed 실영상 5스텝 검증 #42585073433](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585073433) PASS. N16 지도/내비 입력은 아직 검증되지 않았으므로 우회·0 채우기 금지. **전체 후보 모델 확대 미완료**.
- **6단계:** `bigbench/dashboard.py`, `scripts/build_dashboard.py` 및 테스트가 오프라인 CSV/JSON 기반 HTML+SVG 비교 화면을 제공. 실제 두 모델의 실행 결과에서 HTML/SVG를 생성하는 [CI #42585146636](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585146636) PASS를 확인. 웹 호스팅·라이브 UI는 미완료. **웹 호스팅·실시간 GUI가 아니라 오프라인 읽기 전용 결과 뷰어**.
- **7단계:** `bigbench/reproducibility.py` 및 테스트로 실험 매니페스트 SHA, 동일 시드·모델·시간축·영상 해시/위치의 반복 비교 기능 구현. 실제 MD-V3 재실행 [#42585174235](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585174235)은 **REPEATED_DIAGNOSTIC_MISMATCH**(마지막 위치 차이 0.193mm; 5스텝부터 카메라 해시 불일치). 고정 포즈 카메라 단독 [#42586162386](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42586162386)도 기본 시계에서 road 3종/wide 2종 프레임. [재현성 조사](REPRODUCIBILITY_FINDINGS.md)와 opt-in Panda 고정 시계 실험 추가. 전체 구간·다중 시드·CARLA 교차검증 **미완료**, 모델 순위 금지.
- **고정 원칙 불변:** 실제 차량 테스트 없음, 차량별 동역학 없음, CD210 폴백 없음, Carrot MPC/Params 튜닝 없음. 모델/가상 환경의 진단값을 실도로 안전성과 동일시하지 않음.

## 다음 세션에서 이어가는 법

1. `main`의 이 파일과 최신 CI 결과를 읽는다.
2. `진행 중` 단계의 이전 실행 증거와 차단 요인을 확인한다.
3. 이전 PASS를 재현 또는 근거 확인한 뒤 미완료 게이트부터 이어간다.
4. 실제 검증을 마친 뒤에만 해당 단계 상태와 실행 URL/측정 결과를 수정한다.
5. 종료 시 다음에 이어갈 정확한 게이트를 이 문서에 갱신한다.
