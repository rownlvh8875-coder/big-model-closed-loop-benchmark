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

## 2026-11-10 재현성 원인 분리 추가 검증

- **PASS (단일 고정 영상 원인 분리):** [CI #42755109268](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42755109268). 고정 MetaDrive RGB 단일 촬영 후 두 독립 ONNX 세션에서 공식 MD-V3 12스텝 반복 추론 결과 **동일**, 가상 위치 차이 0m.
- **FAIL (실제 매 스텝 렌더):** [CI #42741355594](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42741355594). 픽셀 오차 허용 모드에서도 12스텝 모델 재현성 불일치. 카메라 이미지 바이트가 달라지므로 모델 성능 순위 산출 금지.
- **해석:** 현재 가설의 우선순위는 MetaDrive/Panda3D 렌더링·카메라 프레임 획득 및 장면 업데이트 경로. 원인은 아직 특정하지 못했고, 고정 영상 테스트는 **오픈루프 원인 분리**이므로 7단계 전체 완료로 판정하지 않음.
- **다음 정확한 작업:** 같은 가상 자세의 이미지 차이를 버퍼/렌더 타이밍·동적 오브젝트·후처리로 나누어 실험하고, 각 실험에서 두 카메라 원본 RGB와 최종 모델 I420 텐서의 프레임별 변화·범위를 저장. 이후 독립 새 ONNX 세션의 **실제 영상 폐루프** 동일 조건 재현성 재검사.
- 세부 분석: [재현성 결과](REPRODUCIBILITY_FINDINGS.md), [고정 영상 분리 코드](../bigbench/frozen_camera_diagnostic.py).

## 2026-11-10 · 장면/렌더링 원인 분리 진행 업데이트

- [MetaDrive 6조건 실렌더](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42757874100) 및 [각 조건 별도 프로세스 반복](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42758718405): GPU 새 렌더 없이 CPU RAM 텍스처를 재읽는 단계는 완전 일치. `taskMgr.step` 실행 시 원본 픽셀 및 최종 I420의 소량 차이가 있으나, 두 카메라를 동시에 `graphicsEngine.renderFrame`만 호출하면 후반 I420은 완전 일치.
- [그림자/추적 태스크 A/B](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42759149254): 가상 `PSSM.update` 제거 시 후반 RGB/I420 불일치 **0**, `update main chase camera` 제거 시 변화 **유지**. `igLoop`은 계속 동작, 카메라 포즈 변경 양성 대조 PASS. **장면 태스크의 영향은 분리**, 동일한 렌더링 의미·다중 시드/포즈/모델 폐루프 재현성이 검증됐다는 뜻 아님.
- 다음 작업 게이트: `PSSM.update`에 의한 HDR scene texture/톤매핑 과정의 변경점 추적 → 다중 seed·pose 검증 → 공식 대형 ONNX **새 영상 폐루프 재현성** 재시험. **7단계 전체 완료 및 모델 순위 산출은 보류**.
- 자세한 시험 통계: [렌더링 인과 분리 문서](METADRIVE_RENDER_CAUSALITY.md).



## 2026-11-10 · 7단계 HDR/PSSM GPU 계측 검증 확대

- [GPU 텍스처 전체 추출 CI #42766327307](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42766327307): 2 seed × 2 pose × 3 ablation = 12 native 조건에서 GPU PSSM depth/HDR 바이트 계측을 수행했으나 PSSM 행렬 자료형 오류 및 카메라 이동 양성 대조 실패로 모든 조건 INCONCLUSIVE. 원본 아티팩트 보존.
- [행렬 호환 수정 후 CI #42767017309](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42767017309): 12조건 모두 GPU 추출 **이전** road/wide +2m 이동 PASS, 매 프레임 GPU 추출 **이후** road/wide 이동 반응 FALSE. 이 조건의 비트 동일 RGB/I420을 시뮬레이터 재현성 PASS로 사용할 수 없음. GPU readback 개입 가설을 우선 조사.
- 독립 호출 분리: [.github/workflows/gpu-probe-interference.yml](../.github/workflows/gpu-probe-interference.yml), no-GPU / shadow depth / road HDR / wide HDR / all 다섯 조건을 프로세스별로 따로 실행, [상세 문서](PSSM_HDR_TRACE.md) 참조. **실험을 관측했다고 모델 폐루프를 통과한 것으로 판단하지 않는다.**
- **7단계 상태: 계속 진행 중**, 메타드라이브 원래 파이프라인의 정확한 신규 프레임 재현성과 공식 MD-V3 모델 실제 영상 폐루프 반복성은 미완료. 실차 테스트 및 모델 성능 순위 금지 유지.

## 2026-11-10 · 최종 GPU 계측 간섭/종료시점 HDR CI 검증

- [GPU 개별 추출 CI #42768683086](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42768683086): 네이티브 seed 20261109/20261110 **2/2 진단 성공**. no GPU, PSSM depth만 읽을 때 road/wide 이동 반응 보존; road HDR 읽으면 road만, wide HDR 읽으면 wide만 후속 이동 반응 상실; 둘 다 읽으면 둘 다 상실. **침습적 계측 중단 현상은 모델 성능 PASS가 아님**.
- [종료 프레임 전용 HDR CI #42769095626](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42769095626): seed 2개 × 4/6프레임 **4/4 진단 성공**. 모든 RGB/I420을 먼저 캡처하고 종료 시점에서만 PSSM depth/HDR 텍스처 추출. seed 20261109, 6프레임 기본 무추출 및 종료시점 probe 조건 I420 해시 종류 **2**, PSSM.update 제거 조건 **1**. seed 20261110, 6프레임은 세 조건 모두 I420 종류 **1**. 짧은 표본·단일 pose이므로 인과관계의 일반화/실제 주행모델 공식 재현성 PASS 불가.
- [원시 결과·제약·시드별 표](PSSM_HDR_TRACE.md). 다음 정확한 작업: 프레임별 HDR 차이를 침습하지 않고 확보하는 방법 검증 → 더 긴 시드/장면/pose 반복 → 공식 MD-V3 신규 RGB 폐루프 **반복 동일성 게이트**. 7단계 미완료, 모델 순위 금지 유지.

## 2026-11-10 · 다중 시드/장면/카메라 위치 + 공식 MD-V3 신규 영상 반복 게이트

- [네이티브 다중 장면 CI #42770691138](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42770691138): MetaDrive 0.4.3 공식 렌더 에셋 고정, 시드 20261109/20261110 × S자 2종·램프 2종 × 차선 진행률 0.12/0.28 = **16개 비교 세트(32개 독립 native 프로세스)**. 16/16 CI에서 raw RGB/I420 시계열과 +2m 자세 변경 양성대조 기록 성공. 기본 상태 I420 해시 드리프트 10/16, PSSM.update 제거 시에도 5/16 드리프트, 제거로 안정화된 조건 5/16. 특히 좌→우 S자 20261110/0.28에서 PSSM 제거 뒤 I420 SHA 고유 개수 2→3. **PSSM.update가 유일하고 충분한 원인이라는 가설은 지지되지 않음**.
- [공식 MD-V3 신규 영상 CI #42771081760](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42771081760): SHA `35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199`, 원래 MetaDrive PSSM/카메라 획득 경로, 8m/s/20Hz/12스텝, 동일 시드·장면을 독립 Python/Xvfb/ORT 세션으로 두 번 실행. **4/4 실제 실행·근거 수집 성공, 정확한 반복 일치 0/4**. 최초 불일치 좌→우/우→좌 S자: seed 20261109 = step 4/4; seed 20261110 = step 7/2. 최대 가상 XY 차이 약 0.048/0.022/0.035/0.125mm.
- 검사 강화: `bigbench/onnx_policy.py`가 실제 ONNX new_img 입력 SHA256을 모델 실행 성공 후 저장; 독립 실행 보고서가 매 step 입력·raw action·재귀 state digest·가상 pose를 비교. 픽셀 완화·HDR GPU 캡처·보간·고정 영상 재생 없음. **CI success를 엄격 재현성 PASS로 치환 금지**.
- [조건별 전수 실측표](STAGE7_MULTISCENE_NATIVE_REPEAT.md). 다음 우선 작업은 추가 메타드라이브 렌더 틱/그림자 이외 상태변화의 비침습적 분리, 원본 source 964×604 SHA 대조, 최초 차이가 나는 프레임의 렌더 스케줄 확인, 더 긴 시계열 및 외부 CARLA 교차검증. 공식 MD-V3 엄격 반복 게이트가 실패하므로 모델 주행성능 순위 불가.
- **7단계는 여전히 진행 중**. 실차 시험·CD210 폴백·Carrot MPC/차량별 동역학·주행성능 순위 산출 금지 유지.

## 2026-11-10 · 공식 MD-V3 원본 964×604 RGB 최초 차이 관측 경계 검증

- [원본 센서 RGB 단계별 CI #42772799803](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42772799803): SHA가 고정된 공식 MD-V3와 기본 MetaDrive 신규 프레임을 2시드×2 S자×독립 2회·12스텝 실행. **4/4 실제 ONNX 실행·진단자료 수집 성공, 엄격한 비트/수치 재현성 0/4 FAIL**.
- 모델 입력과 원본 센서 분리: `NativeWorldCamera.capture`에서 두 카메라의 964×604 uint8 RGB를 즉시 복사·SHA256. 기존 워프 후 512×256 RGB, 실제 ORT `new_img` I420 해시 및 raw action·recurrent output SHA와 시계열 대조. GPU HDR/그림자맵 추출·영상 보정·다중 캡처 없음.
- 최초 원본 RGB 해시 불일치: seed 20261109 좌→우 step 2(wide), 우→좌 step 3(wide), seed 20261110 좌→우 step 2(wide), 우→좌 step 2(road). 실제 I420 입력 최초 불일치: 각각 step **6/10/6/2**. 즉 **3/4는 원본 센서 단계에서 더 이른 불일치가 검출**되고 1/4는 동시에 관측됨. 근거: [원본·모델·I420 단계별 전수표](STAGE7_FIRST_IMAGE_BOUNDARY.md).
- **판정:** MetaDrive/Panda3D 센서 영상 생성·획득 경로를 다음 원인 분리의 우선 대상으로 유지한다. `PSSM.update` 유일 원인/수정책이라는 단정 금지. 원본 RGB 복사·SHA 자체도 CPU 수행시간과 실시간 task scheduling을 교란할 수 있어 무계측 결과와 최초 스텝 직접 일치 검증 불가.
- 다음 정확한 게이트: 같은 카메라 pose/이전 모델 state에서 카메라별 순차 `taskMgr.step` 시점·원본 framebuffer/scene task/clock 변화 분리. 7단계는 **계속 진행 중**, 모델 성능 순위 및 실차·CD210/Carrot 폴백 금지.

## 2026-11-10 · 원본 RGB 픽셀 좌표 및 Panda 프레임/태스크 분리 (재시도 완료)

- [GitHub Actions #42776577784](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42776577784): 공식 MetaDrive 0.4.3 고정 자산, 시드 2개 × S자 2종 × 4개 독립 렌더 방법/태스크 조건 = **총 16개 별도 Python/Panda/Xvfb 프로세스, CI 4/4 정상 계측**. 카메라 +2m 이동 양성대조 및 RTMCopyRam CPU 재읽기 일치 확인, GPU HDR extractTextureData 호출 없음.
- 기본 순차 perceive의 변경량은 좌→우 S자 두 시드에서 road/wide **9/2픽셀, I420 12개 원소**, 우→좌 S자는 **8/3픽셀, I420 26개 원소**. 첫 변경 road/wide 픽셀은 좌→우 **(22,343)/(210,322)**, 우→좌 **(901,312)/(590,304)** (0-base top-left 좌표).
- 같은 pose에서 graphicsFrame만 호출한 조건은 4/4 모두 후반 변경 픽셀과 I420 원소 0. PSSM.update만 제거한 동시 taskMgr.step 조건도 이번 네 조건에서는 모두 0. 다만 이전 다중 위치/램프 16조건에서는 PSSM 제거 후에도 5조건에서 I420 변화가 남았으므로 전체 현상 해결책으로 적용 불가.
- **새로 수정된 계측 오류:** Panda 전역 frameCount 증가는 순차 perceive +2, 공통 taskMgr.step +1, **graphicsEngine.renderFrame 단독도 +1**. 따라서 글로벌 프레임 카운터를 실제 taskMgr.step 호출 횟수로 해석할 수 없음. 호출 횟수는 소스 호출 경로를 통해 별도 기록.
- [전수 실험방법·시드별 수치·변경 좌표·해석 제한](STAGE7_RAW_PIXEL_CLOCK_CAUSALITY.md). 7단계 원래 공식 MD-V3 실제 신규 영상 독립 폐루프 4조건 엄격 재현성은 여전히 FAIL. 모델간 성능 순위 금지, 실차/차종 동역학/CD210/Carrot MPC·Params 폴백 제외.
- **다음 게이트:** PSSM camera rig MVP/그림자 상태 업데이트 및 타 Panda task·시계가 원본 센서 RGB 픽셀을 변화시키는 경로의 비침습적 단계별 분리. 여러 pose/seed에서 다시 확인한 뒤 동일 공식 MD-V3 폐루프 반복성 재검증.


## 2026-11-10 · PSSM shadow MVP · Panda task sort · 고정 시계 추가 원인 분리

- [GitHub Actions #42782363322](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42782363322): MetaDrive 0.4.3 SHA 고정 공식 자산, 2 seed × 2 S-curves × 일반/고정 Panda clock × 4 native render/task arms = **32개 독립 Python/Panda/Xvfb 프로세스, 8/8 native CI 성공**. 8프레임과 최초 2프레임 원본 보존, PSSM shadow camera rig 4×4 numeric MVP 행렬, CPU original RGB/I420 SHA 및 Panda clock/scene camera/light/task registration 동시 관측. HDR GPU texture extraction 없음.
- 워밍업 이후 numeric MVP SHA 변화는 **0/32** 조건이었으나 original RGB SHA 변경은 sequential perceive **6/8**, paired taskMgr **6/8**, graphicsFrame-only **1/8**, paired PSSM.update 제거 **2/8**. final I420 변경은 각각 **5/8, 4/8, 1/8, 2/8**. **MVP 행렬 변화는 RGB/I420 드리프트의 필요조건이 아님.**
- Fixed virtual clock 1/60초 조건도 sequential mode I420 변경 **3/4**, normal clock sequential mode는 **2/4**. clock 고정은 포괄적인 안정화 수단으로 검증되지 않음. PSSM 업데이트 제거는 변경된 renderer 의미를 가져 공식 ONNX 입력으로 채택 금지.
- 실제 native task registration: PSSM.update 및 update main chase camera가 **같은 default chain / sort 0**, igLoop sort 50, dataLoop sort -50. 이 값은 등록 메타데이터이며 callback의 실제 실행 순서/선후 관계가 증명된 것은 아님. 특히 두 sort-0 태스크의 호출 선후를 다음 과제로 격리해야 함.
- [전체 32조건 실측·원본 CI 아티팩트·한계](STAGE7_PSSM_MVP_TASK_CLOCK.md). 성공은 계측 성공이고 공식 MD-V3 ONNX 원래 신규영상 independent repeated strict-match는 이전 **0/4 PASS**로 **7단계 미완료 유지**.
- 다음 게이트: 실제 등록 sort 0 태스크의 callback 실행 순서와 메인 카메라 변환/PSMM MVP 갱신 시각의 비침습적 분리, 가능한 경우 GPU shadow atlas와 final RGB 경로를 계측 개입 통제 하에서 비교한 뒤 공식 ONNX 독립 반복 재시험. 실차/차종 plant/CD210/Carrot MPC·Params 및 모델 주행성능 순위 금지.

## 2026-11-10 · 실제 PSSM 및 Chase callback 진입 순서 추적 완료

- [MetaDrive 0.4.3 실제 Python callback 네이티브 CI #42819410983](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42819410983): 2개 시드 × 2개 S자 × sequential/paired 카메라 = **8개 진단 job SUCCESS**, 각 job은 원래 Panda task를 수정하지 않는 unprofiled/profiler ON 독립 프로세스 2개씩 수행(16개). 원본 ZIP 8개와 실제 콜백 진입/반환 이벤트를 전수 확인.
- **실제 Python 함수 호출순서 PSSM.update → MainCamera._chase_task**. Sequential 64/64, paired 32/32, 합계 96/96 native taskMgr.step 틱에서 동일한 선후. Chase run_task flag는 96/96 entry에서 True. PSSM/Chase 등록은 둘 다 sort=0이지만 이번 결론은 등록 sort가 아니라 sys.setprofile로 관측된 Python call/return을 근거로 함.
- unprofiled/profiler ON 두 독립 native 프로세스의 **동일 step I420 SHA는 8개 비교 중 2개만 8/8 전체 일치**, 6개는 일부 프레임 불일치. sys.setprofile는 task registration을 바꾸지 않지만 CPU scheduling을 교란할 수 있고 원래 MetaDrive에도 독립 실행 영상 변동이 존재하므로, 이 차이를 profiler 하나의 인과 효과로 단정하거나 원래 unprofiled 콜백 순서가 측정됐다고 표현하면 안 됨.
- [8조건 전수 실측·실험 제한](STAGE7_NATIVE_CALLBACK_ORDER.md). 실제 콜백 실행 순서는 관측됐으나 **메인 카메라 위치가 Chase 안에서 이동했는지, 그림자 MVP가 이전 카메라 pose로 계산됐는지, GPU shadow map이 언제 그려졌는지는 아직 미증명**. 7단계 미완료, 공식 MD-V3 독립 신규 영상 12스텝 strict-repeatability 0/4, 모델 공식 주행성능 순위 불가.
- **다음 하드 게이트:** 독립 계측군에서 PSSM/Chase 콜백의 entry/exit 시점별 main camera pose 및 numeric MVP를 함께 기록하고, 무계측 대조군과 CPU timing을 비교해 PSSM의 실제 camera-pose 지연 가설을 검증. 이후 GPU 그림자 패스 영향과 원래 ONNX 폐루프 엄격 재현성을 재시험. 실차/CAN/CD210·Carrot MPC/차량 튜닝 전부 제외.

## 2026-11-10 · PSSM과 Chase 메인 카메라 WORLD 자세 실제 콜백 경계 검증

- [MetaDrive 콜백 자세+MVP 네이티브 CI #42822587924](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42822587924): 시드 20261109/20261110 × S자 2종 × paired/sequential 촬영 = 8개 A/B/C job, 원래 장면 no-profiler / 원래 장면 profiled / 가상 카메라 X+2m 개입 profiled 총 24개 독립 MetaDrive 0.4.3/Panda/Xvfb 프로세스, **8/8 진단 CI SUCCESS**. 공식 자산 SHA 체크, 두 카메라 +2m 이동 양성대조 및 CPU RAM readback 동일성 확인.
- Python 원본 `PSSM.update` call/return→`MainCamera._chase_task` call/return 순서 **96/96 taskMgr 틱** 확인. 실제 profiled 장면의 첫 Chase 카메라 움직임은 seed 20261109 약 **0.595m**, seed 20261110 약 **7.025242m**. PSSM은 **Chase 이동 직전 메인 카메라 WORLD pose의 MVP**를 계산하고, 다음 taskMgr 틱에서 Chase 이후 pose 기준 MVP로 갱신되는 모습 8/8조건 확인. Sequential은 한 프레임 내 두 틱을 별도로 계측해 다음 틱 위치를 기록.
- SIM-ONLY 별도 개입군에서 프레임 index 3/5에 엔진 메인 카메라 X좌표를 실제 +2m 변경: **16/16회** PSSM 진입 pose가 개입 좌표와 정확히 일치, PSSM 콜백에서 MVP 변경, 이후 Chase가 메인 카메라를 복귀시키는 동안 MVP 변경 없음. 이는 CPU 기반 **PSSM 선행 참조 시차를 직접 관찰**한 결과지만 원래 렌더링을 변형한 개입군과 GPU 그림자 draw 결과를 동일시해서는 안 됨.
- 원래 장면과 CPU 계측 장면의 독립 I420 전체 8프레임 완전 일치는 **0/8**. CPU 프로파일러/MVP 조회의 스케줄 오버헤드와 기존 원래 렌더러 변동이 교란 요인. 이 결과를 특정 그림자 셰이더의 유일한 원인/자동 해결책으로 사용 금지.
- [전수 데이터·시드별 수치·한계](STAGE7_PSSM_CHASE_POSE_LAG.md). **Stage 7은 계속 진행 중**. 공식 MD-V3 원래 신규 프레임 독립 ONNX 엄격 재현성 0/4 PASS 상태 유지. 실차·CD210·Carrot MPC·Params·차량별 물리·모델 성능 순위 제외.
- **다음 게이트:** 동일 MetaDrive 기본 task/PSSM을 유지한 채 원래 메인 카메라/그림자 rig의 한 틱 시차가 GPU shadow-pass/최종 RGB에 미치는 영향을 비침습적 측정과 별도 개입 A/B로 확인, 이후 공식 MD-V3 새 영상 독립 폐루프 반복시험 재평가.

## 2026-11-10 · 종료시점 그림자 GPU depth/HDR와 post-Chase PSSM 정합 인과 진단

- [Native terminal-only shadow/HDR CI #42828142647](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42828142647): MetaDrive 0.4.3 공식 렌더링 자산 SHA256 고정, 2시드×실제 S자 2종×7개 독립 Panda 프로세스 = **28개 독립 native 실행, 4/4 matrix CI SUCCESS**. 원본 4 ZIP에서 lossless compressed GPU depth/HDR 바이트, 판정 JSON·원본 RGB·I420 데이터 전체 검증.
- 실험 arm은 원래 noGPU/종단GPU, 마지막 프레임 메인 카메라 X +2m 이후 기본 GPU·noGPU, 순수 Sort25 관측, 별도 Sort25에서 **PSSM.update를 Chase 이후 추가 1회 실행**한 noGPU/종단GPU 총 7개. 원래 task 이름·sort0/0/50 보존, Sort25 추가는 명시적 가상 개입으로 원본 renderer와 동등하지 않음.
- **GPU readback은 모든 원본 RGB/I420 캡처가 종료된 뒤에만 1회 수행.** 두 카메라 +2m 이동 양성대조, GPU 추출 후 마지막 CPU RAM RGB 동일성, raw GPU binary SHA256/레이아웃/무손실 zlib 파일 전체 검증.
- 오프셋 상태에서 **단순 Sort25 관측만 추가한 조건 vs 아무 태스크 추가 없는 조건:** 네 장면×그림자 depth/Road HDR/Wide HDR **12/12개 raw GPU stage 전부 비트 일치**.
- 같은 오프셋에서 **Chase 이후 PSSM 재갱신:** raw 그림자 깊이는 시드 20261109 두 S자 각각 **22,634바이트**, 20261110 두 S자 각각 **22,308바이트** 변경. Road HDR 40,200~118,825바이트, Wide HDR 8,454~17,695바이트 변경. GPU raw byte 차이는 texel/픽셀 수가 아님.
- **재갱신 후 그림자 atlas가 원래 무개입 자연장면의 마지막 그림자 GPU bytes와 4/4조건 전체 완전 일치.** Road HDR 잔여 차이 0/0/49/51바이트, Wide HDR 잔여 차이 12/12/18/18바이트. GPU 그림자 깊이·HDR이 post-Chase MVP 계산 시점에 민감함을 뒷받침하지만, 독립 프로세스/CPU timing으로 인해 후반 RGB 미세 흔들림의 **유일한 원인이라는 증거는 아님**.
- [7조건 재현방법·전수 GPU raw byte 비교·한계](STAGE7_TERMINAL_SHADOW_SYNC.md). GPU depth/HDR는 마지막 **단일 프레임**의 바이너리만 관측했고 이후 추가 렌더링을 하지 않아 GPU 추출 간섭을 시계열과 분리함. noGPU vs terminal 원본 프레임은 offset no-sync arm에서 4/4 × 5/5 모두 일치했지만 그 밖에는 독립 프로세스 변동이 남음.
- **Stage 7 계속 미완료:** 원래 동작을 변경한 실험적 Sort25 추가 PSSM 호출은 공식 MD-V3 ONNX 입력/렌더러로 사용 금지. 원래 MetaDrive PSSM task와 매번 신규 RGB를 쓰는 공식 MD-V3 독립 폐루프 엄격 반복 일치는 기존 **0/4 PASS**. 실차/CAN/CD210·Carrot MPC/Params·차종 물리·모델 주행성능 순위 제외.
- **다음 게이트:** 동일 초기 camera pose/시드와 독립 실행 2회 이상에서 원래 renderer의 GPU depth/HDR/RGB 최종 1프레임 재현성 분포를 계측하고, 다른 camera fraction/램프에도 A/B가 지속되는지 확인. GPU HDR 추출을 프레임 사이에 넣지 않고 원래 PSSM 활성 코드 경로의 공식 MD-V3 strict-repeatability gate로 복귀.

## 2026-11-11 · MetaDrive S자·실제 진입/진출 램프 f0.28 GPU shadow 깊이/HDR 확대

- [네이티브 curve+ramp GPU terminal-only CI #42897373586](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42897373586): 공식 MetaDrive 0.4.3 release asset SHA256 검증, 2 seed × 네 장면(S curve 2+in/out ramp) × real lane fraction **0.28** × 7 GPU/noGPU·Sort25/미변경 프레임 대조군 = **56개 별도 native Panda/Xvfb process, matrix 8/8 + strict summary 1/1 SUCCESS**.
- **GPU 최종 1프레임 비교:** 단순 Sort25 observation-only와 원본 offset 무추가 태스크 조건 8장면×3종 GPU texture = **24/24 비트 일치**, 별도 post-Chase 추가 PSSM.update 후 raw depth atlas가 원래 무개입 자연 장면 depth atlas와 **8/8 비트 일치**. 그림자 raw depth changed bytes는 seed 20261109에서 22,634, seed 20261110에서 22,308 (장면 4종 모두 같은 시드에서 동일).
- 도로별 최종 HDR changed raw bytes는 좌→우 S자 road 234,865~298,811, 우→좌 S자 road 58,093~91,811, **진입 램프 road 224,344~296,598**, **진출 램프 road 6~11**. GPU 바이트 변화는 raw texel/화면 픽셀 수가 아니며 모델 성능 개선이나 그림자 버그 유일 원인의 인과 증명도 아니다.
- [최종 native GPU 8조건 실제 수치와 장면별 카메라 좌표](STAGE7_TERMINAL_SHADOW_RAMP_F028.md). 해당 CI는 별도 프로세스에서 원래 MetaDrive 렌더링에 영향을 주는 extra PSSM sync/가상 카메라 +2m 조작도 수행했으므로 **원래 모델 입력 영상으로 대체 금지**.
- **Stage 7 하드 게이트 계속 열림:** 공식 원래 PSSM.update와 Chase 활성 상태의 MD-V3 실제 ONNX 새 프레임 폐루프 **독립 실행 strict-repeatability 지난 검증 0/4 PASS**. 다음 단계는 원래 모델 SHA 핀ning/원본 렌더 경로를 유지한 두 실행 12-step×2시드×2 S자 정확 반복 재검증 및 불일치 원본 RGB/ONNX 입력/출력·recurrent state 위치 측정.
- 실차/CAN/CD210 폴백·Carrot MPC/Params·차량별 물리·모델 주행성능 순위 금지. 이번 성공은 네이티브 GPU **진단 수집 성공**에 국한.

## 다음 세션에서 이어가는 법

1. `main`의 이 파일과 최신 CI 결과를 읽는다.
2. `진행 중` 단계의 이전 실행 증거와 차단 요인을 확인한다.
3. 이전 PASS를 재현 또는 근거 확인한 뒤 미완료 게이트부터 이어간다.
4. 실제 검증을 마친 뒤에만 해당 단계 상태와 실행 URL/측정 결과를 수정한다.
5. 종료 시 다음에 이어갈 정확한 게이트를 이 문서에 갱신한다.
