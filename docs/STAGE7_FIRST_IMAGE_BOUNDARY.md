# 7단계 후속: 원본 MetaDrive 센서 RGB → 모델 RGB → ONNX I420 최초 불일치 경계

**상태:** 비침습적 계측 구현 / 실측 네이티브 CI 재검증 필요. 실차 없음, 모델 성능 순위 금지.

## 이전 근거

- [MD-V3 정확한 신규 영상 반복 CI #42771081760](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42771081760): 2 시드×2 S자에서 공식 ONNX 매 스텝 신규 영상 독립 실행 4/4 성공, 엄격 재현성 0/4. 최초 불일치: 시드 20261109 두 장면 step 4, 시드 20261110 좌→우 step 7/우→좌 step 2. 정확한 가상 XY 최대 차이는 약 0.022~0.125mm.
- [다중 장면 원인 분리 #42770691138](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42770691138): 16조건 중 기본 I420 드리프트 10, PSSM 제거 후 5. PSSM 원인 단정 금지.
- [이전 GPU stage 개입 조사](PSSM_HDR_TRACE.md): HDR scene_tex의 extractTextureData가 대상 카메라의 이후 렌더 갱신에 개입하므로 **실제 ONNX 반복 실행 중 HDR texture GPU 추출은 수행하지 않는다**.

## 추가 계측 범위

- 기존 `bigbench/native_model_campaign.py:NativeWorldCamera.capture`의 `perceive` 결과에 대해 road/wide 원본 `964×604×3 uint8` 배열을 **즉시 복사**하고 SHA256을 계산한다. 별도 `taskMgr.step`·GPU 텍스처 추출·보간은 추가하지 않는다.
- 기존 `512×256` 모델 RGB 해시는 유지한다. `bigbench/onnx_policy.py`는 실제 ORT feed의 `new_img (2,6,128,256) uint8` 입력 SHA256을 ONNX 성공 호출 직후 직접 기록한다.
- `scripts/native_mdv3_repeat_trial.py`는 오리지널 MetaDrive source SHA / 모델 보정 후 RGB SHA / 실제 ONNX new_img SHA / 원시 action SHA / recurrent output SHA를 모두 한 스텝에 저장해야만 정상 실행 보고서를 작성한다.
- `scripts/compare_fresh_native_mdv3.py`는 두 독립 프로세스를 비트 동등성으로 비교하고, *최초 달라지는 계측 경계*를 다음 순서로 진단한다.
  1. `NATIVE_964x604_RGB`: 원본 영상 SHA가 다르면 영상 생성 또는 원본 센서 버퍼의 차이를 우선 조사. 원인은 아직 미확정
  2. `WARPED_512x256_RGB`: 원본 동일하지만 모델 화면 RGB에서 차이
  3. `ACTUAL_I420_NEW_IMG`: 두 RGB 화면 동일하지만 실제 ONNX 이미지 입력에서 차이
  4. `ONNX_ACTION_OR_RECURRENT`: 이미지 입력은 동일한데 ONNX 원시 action/recurrent 상태만 차이
  5. `POSE_OR_TIME_ONLY`: 위 데이터는 동일한데 가상 좌표/시간 차이
- 위 경계는 *관측상 처음 다른 SHA 분야*를 뜻하며 단일 물리 원인 또는 특정 Shader 결함을 확정하지 않는다.
- 모델 오류가 발생한 경우 `ERROR`, 한 번이라도 출력을 충족하지 않으면 `FAILED_OR_INCOMPLETE`. `pixel_tolerance=0`, `camera_convergence=0`, 무수정 PSSM 및 원본 카메라 구현 유지.

## 네이티브 CI

[새 source-stage MD-V3 repeat workflow](../.github/workflows/official-mdv3-fresh-repeat.yml)을 통해 기존 2×2 조건을 재실행해 `run_0.json`, `run_1.json`, `strict_native_repeat_verdict.json`을 보존한다. 공식 결과·최초 불일치 지점은 성공 아티팩트 확인 후 기록한다. 단위시험 `tests/test_native_source_pixel_receipt.py`는 mock에 불과하며 실측 근거가 아니다.

**완료 게이트는 그대로 미충족:** 실제 카메라 신규 영상 정확한 반복 재현성, 장시간 S자와 램프 전체, 외부 CARLA, 실제 렌즈 광학 동등성, 모델 간 성능 순위는 아직 미검증.


## 2026-11-10 원본 stage SHA 경계 재시험 중간 관측

[GitHub Actions #42772799803](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42772799803)의 시드 20261109 두 S자 실행 아티팩트에서 다음 순서를 확인했다. 해당 실험은 전용 GPU HDR extraction, 고정 영상 재생, 카메라 convergence를 사용하지 않는다.

| 시드 | 장면 | 원본 964×604 최초 불일치 | 워프 후 모델 RGB 최초 불일치 | 실제 I420 최초 불일치 | 원시 action 최초 불일치 |
|---|---|---:|---:|---:|---:|
| 20261109 | s_curve_left_right | 2스텝 (wide) | 6스텝 | 6스텝 | 6스텝 |
| 20261109 | s_curve_right_left | 3스텝 (wide) | 10스텝 | 10스텝 | 10스텝 |

따라서 기존 시험의 '첫 모델 입력 불일치'보다 **원본 센서 RGB 차이는 더 이른 시점부터 있었음**이 확인됐다. 초기 원본 차이는 모델 워프/정규화 입력에서 즉시 관측되지 않을 수 있다. 그러나 원본 RGB 단계에서 SHA만 다르다는 것으로 렌더러 내부 어떤 패스·쉐이더·CPU 읽기가 원인인지 단정할 수 없다.

**측정 개입 한계:** GPU 추출이나 추가 렌더 틱은 없지만 `np.array(copy=True)`와 원본 964×604 SHA256 계산이 각 카메라 획득 후 CPU 실행 시간을 늘린다. MetaDrive/Panda의 벽시계 기반 업데이트가 이에 영향을 받을 가능성을 배제할 수 없다. 이번 계측에서 관측된 최초 불일치 스텝을 무계측 과거 실행의 최초 스텝과 동등하게 간주하지 않는다.

이 중간 기록은 다음 전체 4조건 결과의 부분 집합이며, CI 정상 실행과 정확한 반복 일치 PASS를 구분한다.


## 2026-11-10 공식 ONNX 원본 센서 SHA 재시험 — 4/4 원본 아티팩트 확인

[네이티브 재시험 GitHub Actions #42772799803](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42772799803): 4개 매트릭스 job **모두 수집/실행 성공**. 실제 SHA256이 고정된 공식 MD-V3, 동일 장면/시드에서 별도 Python·Panda·Xvfb·ONNX 세션으로 각각 12스텝 실행. 원본 camera RGB를 새로 캡처하고 GPU HDR extraction, image replay, convergence, 허용오차를 사용하지 않았다. 각 job의 `strict_native_repeat_verdict.json`은 **4/4 STRICT_NATIVE_ONNX_REPEAT_MISMATCH**로 남는다.

| seed | scenario | native source raw 최초 불일치 스텝 | warped 512×256 RGB 최초 불일치 | 실제 ONNX I420 최초 불일치 | raw action 최초 불일치 | 최대 가상 XY 차이 (mm) |
|---|---|---:|---:|---:|---:|---:|
| 20261109 | s_curve_left_right | 2 (wide) | 6 | 6 | 6 | 0.051269 |
| 20261109 | s_curve_right_left | 3 (wide) | 10 | 10 | 10 | 0.035400 |
| 20261110 | s_curve_left_right | 2 (wide) | 6 | 6 | 6 | 0.065611 |
| 20261110 | s_curve_right_left | 2 (road) | 2 | 2 | 2 | 0.125117 |

**해석 경계:** 네 시험 모두 MetaDrive 원본 소스 영상 배열이 처음 달라진 단계 또는 그 이전에 모델 입력 차이가 나타난 것이 아니라, 원본 단계가 가장 이른 **관측 경계**였다. 세 시험은 원본 센서 해시 변화가 워프 RGB/ONNX I420 변화보다 앞섰고, 네 번째는 모든 단계의 해시 및 모델 출력이 같은 스텝에서 바뀌었다. 따라서 세 시험의 가장 초기 변화는 모델·I420 변환 이전의 센서 이미지 생성/획득 경로를 우선 조사하도록 지지한다. 네 번째는 단계가 동시이므로 시계열상 순서의 추가 구분이 불가능하다.

이 판정은 PSSM.update가 유일 원인이라는 증명이 아니며, Panda3D task clock, 순차 `perceive`, shadow atlas, 버퍼 갱신 중 정확히 어느 구성 요소인지 추가 실험이 필요하다. GPU 호출은 추가하지 않았지만 CPU에서 매 프레임 원본 RGB 배열 copy/SHA256을 수행해 **벽시계 기반 렌더 태스크의 진행 시각은 바뀔 수 있으므로** 무계측 이전 시험과 처음 변경된 프레임 번호를 직접 동등하게 취급하지 않는다.

**7단계 현 상태:** 공식 SHA-pinned MD-V3의 원본 새 영상 폐루프 exact reproducibility 0/4 FAIL. 실차/차량별 물리 모델, CD210 폴백, Carrot MPC, 모델 성능 순위 금지 유지. 다음 하드 게이트: 같은 초기 pose/이전 recurrent state에서 native raw RGB가 가장 먼저 갈라진 조건을 기준으로 camera별 task tick/clock/scene update를 추가 분리한다.
