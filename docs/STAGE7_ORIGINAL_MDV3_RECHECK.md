# Stage 7 — 원래 PSSM 활성 공식 MD-V3 12-step 신규 영상 폐루프 독립 반복성 재검증

상태: **실제 공식 MD-V3 ONNX 네이티브 CI 실행 중**. 아래는 검증 절차이며, 실제 원본 CI·아티팩트 결과를 확인하기 전에는 PASS/FAIL 숫자를 새로 단정하지 않는다.

## 검증의 목적

이전 실험은 원래 MetaDrive 0.4.3의 PSSM.update와 Chase 카메라 실행순서와 terminal GPU shadow depth/HDR의 관계를 원인 분리했다. [별도 f0.28 native curve/ramp 조사](STAGE7_TERMINAL_SHADOW_RAMP_F028.md)는 56개의 진단용 프로세스에서 실험적 +2m 카메라 이동/extra PSSM 재갱신 조건을 비교했지만, **원래 MetaDrive renderer의 ONNX 폐루프 재현성 PASS를 확인하는 것은 아니다**.

이번 시험은 기존의 변경되지 않은 원래 native MetaDrive/MD-V3 추론 실행기를 다시 검증한다.

## 공식 원본 모델 및 소스 계약

- SHA256 고정 공식 MD-V3 모델: model ID 1365126a-e71e-4778-be00-8ab92dc82c09/12864/big_driving_supercombo.onnx, SHA256 35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199.
- 원본 코드: scripts/native_mdv3_repeat_trial.py 및 scripts/compare_fresh_native_mdv3.py. 이전 단계부터 사용해온 동일 대형 ONNX 실행 경로를 이번 단계에서 수정하지 않는다.
- MetaDrive 0.4.3 공식 렌더링 자산 크기/SHA256 고정, 기본 PSSM.update와 Chase callback 유지, GPU HDR depth 추출 없음, RGB 프레임 convergence/pixel tolerance/평균·재사용 없음.
- 2 seeds 20261109/20261110 × 실제 S curves s_curve_left_right/s_curve_right_left × 완전히 다른 두 개의 Python/Panda/Xvfb/ORT 추론 프로세스 = **4종 시나리오, 총 8개 독립 native ONNX 실행**.
- 각 ONNX 실행은 원본 MetaDrive에서 스텝마다 새로 촬영한 road/wide RGB(964×604)를 기존 렌즈 변환→I420 (2,6,128,256)로 공급하고, 실제 ORT new_img feed SHA256, 모델 raw action SHA, 모든 recurrent state SHA와 가상 위치/시간을 보존한다.
- 각 시뮬레이션 속도 8m/s, 20Hz, 12 steps, initial fraction 0.12. 원래 차선 geometry 기준이며 실제 차종/물리/오토파일럿 제어와 무관하다.
- scripts/aggregate_original_mdv3_current_recheck.py는 결과 4개 및 각 프로세스의 원본 run_0/run_1 JSON을 재해석하여 비교 도중 누락/위조된 verdict, 렌더링 PSSM 변경, ONNX file SHA mismatch, 모델 입력 interpolation/replay/허용오차 등을 fail-closed로 차단.
- GitHub Actions 진단 CI의 success는 실제 모델이 실행되고 데이터가 정합되게 저장됐다는 뜻이다. **4/4 exact bit-match**가 아니면 엄격한 폐루프 반복성 게이트는 FAIL이며 Stage 7 완료/모델 비교 절대 불허.

## 실행 및 아티팩트

[현재 공식 MD-V3 original native 재시험 workflow](../.github/workflows/stage7-original-mdv3-current-recheck.yml). 실행 후 각 장면/시드의 두 raw JSON, per-step 모델 actual feed와 recurrent output, strict native verdict, 최종 4조건 종합 verdict를 보존한다. 이번 시험은 실차·CAN·CD210·Carrot MPC·Params를 호출하지 않으며 모델 주행성능 순위를 산출하지 않는다.

### 이전 기준 (별도 실험)

이전 원본 모델 시험의 4조건 exact-repeat 통과는 **0/4**였다. 현재 실행 결과가 나오기 전에는 이 값은 **이전 기준**에만 해당한다. 이번 재시험 결과와 혼동해서는 안 된다.
