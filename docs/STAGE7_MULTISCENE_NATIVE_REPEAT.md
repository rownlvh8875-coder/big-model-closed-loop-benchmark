# 7단계: MetaDrive 다중 도로·시드·카메라 위치 및 공식 MD-V3 엄격 반복성

검증일: 2026-11-10. **실차/차량별 동역학/CD210/Carrot MPC 없음. 본 실험의 native CI 성공만으로 모델 주행성능 순위 산출 금지.**

## 기존 실험에서 이어받은 확인 사항

- 기존 단일 장면에서 `PSSM.update` 제거 뒤 워밍업 이후 RGB/I420 바이트 변화가 사라졌으나 일반화되지 않았다.
- HDR `scene_tex` GPU 읽기가 대상 카메라의 후속 RGB 갱신에 개입하는 현상이 독립 실험에서 확인됐다. 따라서 본 다중 장면/실제 ONNX 시험에서는 **GPU HDR 추출을 실행하지 않는다**.
- 별도 프로세스의 고정 영상 추론은 재현됐지만, **매 스텝 새 MetaDrive 영상을 쓰는 실제 가상 폐루프** 재현성은 남은 하드 게이트다.

## A. 카메라/그림자 업데이트 다중 시드·장면 A/B

코드: `scripts/native_scene_ablation_sweep.py`, `scripts/aggregate_multiscene_ablation.py`, `tests/test_multiscene_ablation.py`.

[Native A/B GitHub Actions #42770691138](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42770691138)

- MetaDrive 0.4.3 공식 에셋 SHA256 검증, 각 baseline/shadow_off를 독립 Python+Xvfb 프로세스에서 실행
- 시드: `20261109`, `20261110`; 장면: `s_curve_left_right`, `s_curve_right_left`, `in_ramp`, `out_ramp`
- 각 지도에서 실제 MetaDrive 차선 좌표로 카메라 world pose 생성, 경로 진행률 `0.12`, `0.28`, 높이 `1.22m`
- 기본 가상 차체의 카메라 RGB만 숨김(과거 시험과 동일), 두 카메라 동일 `taskMgr.step` 한 틱당 한 프레임 쌍
- 조건마다 9프레임, 최초 2프레임 보존하되 후반 결과 별도 보고
- 로드/광각 원시 RGB, 보정 후 512×256 RGB, ONNX I420 `(2,6,128,256) uint8`의 프레임별 SHA256 및 픽셀/원소 차이
- 같은 완료 프레임의 CPU 재읽기 3회 비트 동일, 종료 후 +2m 이동 road/wide 양성대조 필수
- 성공은 **정확한 실측 JSON 취득**을 뜻한다. `shadow_off` 조건의 그림자 렌더링은 원래 기본 장면과 다른 영상이며, 모델 입력으로 대체하지 않는다.
- 한 조건이라도 누락되거나 양성대조 실패 시 `INCONCLUSIVE/ERROR` 기록. 변화가 없다고 강제로 '인과관계 증명' 판정 금지.

## B. 공식 MD-V3 신규 영상 폐루프 반복

코드: `scripts/native_mdv3_repeat_trial.py`, `scripts/compare_fresh_native_mdv3.py`, `tests/test_fresh_native_mdv3.py`.

[공식 MD-V3 GitHub Actions #42771081760](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42771081760)

- 가중치 공식 SHA256: `35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199`, 기존 모델 명세 `model_specs/md-v3.json`의 `new_img` 입력 계약 사용
- 각각의 독립 Python/Xvfb/ORT 프로세스는 **새 MetaDrive 세계와 새 모델 세션**으로 시작
- 초기 비교 조건: 2개 시드 × 좌→우/우→좌 S자, 고정 가상 속도 `8m/s`, 20Hz, 12스텝, 이상적 운동학
- 카메라 수렴 반복촬영 `0회`, 픽셀 허용오차 `0`, HDR GPU 추출 `0회`, PSSM 원래 업데이트 활성
- 매 스텝 원본 2카메라 모델 영상 SHA256, 실제 ONNX `new_img` 입력 바이트 SHA256, raw action 값/해시, 모든 recurrent state 출력 digest, 정확한 가상 시간/자세/좌표 기록
- 독립 반복 2개의 해당 필드를 **비트 단위/값 단위로 완전 일치**시킨 경우만 `STRICT_NATIVE_ONNX_REPEAT_MATCH`. 어떤 필드든 다르면 `STRICT_NATIVE_ONNX_REPEAT_MISMATCH`; 미실행이면 `ERROR`. 숫자 허용치·이미지 보간·동일 프레임 재사용으로 PASS를 만들지 않는다.
- 워크플로가 두 불일치 보고서를 정상 저장한 경우 CI가 'success'여도 실험의 **엄격 재현성 게이트는 FAIL**일 수 있다. 반드시 `strict_native_repeat_verdict.json`의 `exact_repeated_execution_gate_passed` 판정 확인.

## 2026-11-10 실제 CI 검증 완료 결과

- [Native 장면 A/B #42770691138](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42770691138): 16개 매트릭스 job **16/16 success**. 이는 독립 Native MetaDrive 시계열·양성대조·JSON 확보라는 의미이며 **16조건 영상 비트 일치 PASS가 아님**.
- [Official MD-V3 #42771081760](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42771081760): 4개 매트릭스 job **4/4 success**. 각 job의 MD-V3 12스텝 독립 ONNX 실행 2회는 정상 완료했지만 **엄격한 재현성 일치 0/4**, 네 조건 모두 verdict는 `STRICT_NATIVE_ONNX_REPEAT_MISMATCH`. 'CI success'와 'exact repeated execution gate PASS'는 다른 상태다.
- 아티팩트 내 `comparison.json`, `run_0.json`, `run_1.json`, `strict_native_repeat_verdict.json`를 실제 확인했다.

### 다중 도로·시드·카메라 위치: 기본 / 그림자 태스크 제거

다음은 실제 원본 아티팩트에서 **9프레임 중 워밍업 2프레임을 제외한 남은 프레임**의 I420 해시 고유 개수와 첫 후반 프레임 대비 최대 변경 원소 수다. 원본 첫 2프레임의 해시는 개별 JSON에 보존했다. 고유 해시 개수 1은 해당 **고정 포즈 단기 관측**에서만 일정함을 의미한다.

| 시드 | 장면 | 차선 진행률 | 기본 I420 고유 SHA | PSSM 제거 I420 고유 SHA | 기본 최대 변경 원소 | 제거 후 최대 변경 원소 |
|---|---|---:|---:|---:|---:|---:|
| 20261109 | in_ramp | 0.12 | 1 | 1 | 0 | 0 |
| 20261109 | in_ramp | 0.28 | 2 | 2 | 4 | 4 |
| 20261109 | out_ramp | 0.12 | 1 | 1 | 0 | 0 |
| 20261109 | out_ramp | 0.28 | 2 | 1 | 3 | 0 |
| 20261109 | s_curve_left_right | 0.12 | 2 | 2 | 12 | 8 |
| 20261109 | s_curve_left_right | 0.28 | 3 | 2 | 31 | 3 |
| 20261109 | s_curve_right_left | 0.12 | 3 | 1 | 28 | 0 |
| 20261109 | s_curve_right_left | 0.28 | 2 | 1 | 6 | 0 |
| 20261110 | in_ramp | 0.12 | 1 | 1 | 0 | 0 |
| 20261110 | in_ramp | 0.28 | 1 | 1 | 0 | 0 |
| 20261110 | out_ramp | 0.12 | 1 | 1 | 0 | 0 |
| 20261110 | out_ramp | 0.28 | 1 | 1 | 0 | 0 |
| 20261110 | s_curve_left_right | 0.12 | 2 | 2 | 12 | 8 |
| 20261110 | s_curve_left_right | 0.28 | 2 | 3 | 31 | 28 |
| 20261110 | s_curve_right_left | 0.12 | 2 | 1 | 26 | 0 |
| 20261110 | s_curve_right_left | 0.28 | 2 | 1 | 6 | 0 |

**관측 집계:** 기본 렌더링에서 I420 불일치는 10/16, PSSM 태스크 제거 후에도 불일치는 5/16. 기본 불일치가 PSSM 제거로 사라진 것은 5/16이다. 특히 시드 20261110 좌→우 S자 진행률 0.28에서는 I420 고유 해시 개수가 2→3으로 늘었다. **PSSM은 관측상 연관된 요소이지만 전체 현상의 충분한 해결책도, 증명된 유일 원인도 아니다.** 제거하면 렌더링 의미론이 달라져 ONNX 평가 기본값으로 적용할 수 없다.

### 공식 MD-V3 독립 실행: 원래 PSSM 및 카메라 획득 경로

| 시드 | S자 | 최초 불일치 스텝 | 최대 XY 차이 (mm) | 엄격 재현성 |
|---|---|---:|---:|---|
| 20261109 | 좌→우 | 4 | 0.048214 | FAIL |
| 20261109 | 우→좌 | 4 | 0.022125 | FAIL |
| 20261110 | 좌→우 | 7 | 0.034790 | FAIL |
| 20261110 | 우→좌 | 2 | 0.125117 | FAIL |

모두 동일 공식 MD-V3 SHA256, `8m/s`, `20Hz`, `12스텝`, 동일 시드·장면을 각각 독립 Python/Panda/Xvfb/ORT 프로세스에서 2회 실행했다. 첫 불일치에는 두 카메라 중 적어도 하나의 모델 화면 SHA, 실제 ONNX `new_img` SHA, 원시 action 또는 재귀 상태 차이가 포함된다. 최초 불일치 직전 스텝의 저장된 모델 입력·action·재귀상태·위치 값은 동등했다. **현재로서는 새 카메라 프레임 생성 또는 획득 경로에서의 차이가 주요 의심 지점이며, ONNX 추론기 단독 결함은 입증되지 않았다.**

**공식 판정:** PSSM 다중 조건 진단은 측정 완료. 공식 MD-V3 새로운 영상 폐루프의 엄격 재현성 게이트는 **4/4 실패**, 7단계 전체 **계속 진행 중**. 가상 위치 차이의 크기가 작다는 이유로 PASS로 승격하거나 모델간 주행 성능 순위를 공개하지 않는다.

## 미완료와 다음 단계

- 12스텝/두 시드의 짧은 시험만으로 장시간 S자 전체·램프 폐루프 완료, 고품질 모델 주행성능, camera 광학 동등성을 입증할 수 없다.
- CARLA 등 외부 독립 엔진의 광학/시나리오 교차검증은 별도 미완료.
- 본 문서의 실행 수치·PASS/FAIL 기록은 **GitHub Actions 결과 및 원본 JSON 아티팩트 확인 이후** 갱신한다. 설계나 기본 단위시험을 네이티브 시험 PASS로 치환하지 않는다.
