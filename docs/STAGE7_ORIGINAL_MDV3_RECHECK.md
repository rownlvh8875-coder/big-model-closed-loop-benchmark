# Stage 7 — 원래 PSSM 활성 공식 MD-V3 12-step 신규 영상 폐루프 독립 반복성 재검증

상태: **실제 공식 MD-V3 ONNX 네이티브 CI 종료 — 4조건 비트 단위 엄격 반복성 0/4 FAIL**. 이것은 측정 인프라 오류가 아니라 독립 프로세스간 원본 RGB 및 모델 입력 불일치가 관측된 결과이며, GitHub Actions 작업 완료(SUCCESS)와 모델 결정성 검증(PASS)은 서로 다르다.

## 이번 네이티브 재시험의 검증 결과 (실제 CI 로그)

- [원본 PSSM/MD-V3 네이티브 8개 ONNX 프로세스 + 요약 CI #42900493535](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42900493535): 네이티브 job 4/4, 요약 job 1/1 SUCCESS. 원본 4개 장면의 각 2개 독립 프로세스에서 모두 12스텝 완료. 로그에 남은 **strict exact 반복성은 0/4**.
- 최초 관측된 차이는 모든 장면에서 **NATIVE_964x604_RGB**. 이는 모델 I420/추론 이전에 원본 카메라 프레임 SHA 불일치가 존재함을 뜻하며, PSSM이 *유일한 원인*이거나 GPU 그림자가 *특정 프레임의 직접 원인*이라는 증거는 아님.
- 각 조건의 최대 `xy` 위치 차이는 해당 12스텝 동안 두 독립 실행 간 가상 주행 위치 차이(미터)이며 실차 측정치가 아님.

| seed | 실제 MetaDrive 장면 | 첫 불일치 스텝 | 첫 관측 불일치 경계 | 최대 XY 차이 (m) | 엄격 게이트 |
| --- | --- | ---: | --- | ---: | --- |
| 20261109 | s_curve_left_right | 2 | NATIVE_964x604_RGB | 0.0000482141848116049 | FAIL |
| 20261109 | s_curve_right_left | 3 | NATIVE_964x604_RGB | 0.0000354003571377404 | FAIL |
| 20261110 | s_curve_left_right | 2 | NATIVE_964x604_RGB | 0.00009154976541192115 | FAIL |
| 20261110 | s_curve_right_left | 2 | NATIVE_964x604_RGB | 0.0001235916833621279 | FAIL |

**판정:** Stage 7 미완료. GPU terminal-only 진단 성공/원본 MD-V3 독립 결정성은 서로 다른 검증 게이트이다. 다음 단계는 첫 RGB 차이 이전의 카메라 WORLD pose, task tick, PSSM MVP를 원본 시뮬레이터의 관측 교란을 통제하면서 세분화하고, 동일 조건 독립 반복 시 그 차이가 선행하는지 검증하는 것이다. 모델 랭킹, 원래 renderer 변경, 실차 성능 주장 금지.

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

이전 원본 모델 시험의 4조건 exact-repeat 통과는 **0/4**였다. 이번 재시험도 **0/4**였음이 CI #42900493535에서 확인되었다. 두 시험의 수치를 합산하거나 독립 동일 조건 성공으로 주장하지 않는다.
