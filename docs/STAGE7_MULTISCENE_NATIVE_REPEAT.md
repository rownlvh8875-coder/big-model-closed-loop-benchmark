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

## 미완료와 다음 단계

- 12스텝/두 시드의 짧은 시험만으로 장시간 S자 전체·램프 폐루프 완료, 고품질 모델 주행성능, camera 광학 동등성을 입증할 수 없다.
- CARLA 등 외부 독립 엔진의 광학/시나리오 교차검증은 별도 미완료.
- 본 문서의 실행 수치·PASS/FAIL 기록은 **GitHub Actions 결과 및 원본 JSON 아티팩트 확인 이후** 갱신한다. 설계나 기본 단위시험을 네이티브 시험 PASS로 치환하지 않는다.
