# 대형 ONNX MetaDrive 반복실행 재현성 분석 (2026-11-09)

**판정: 7단계 반복 실행 게이트 미통과 · 모델 주행성능 순위 산출 금지.**

## 근거

- 동일 SHA256 MD-V3 ONNX, 같은 `s_curve_left_right` 맵, 같은 시드 20261109, 속도 8m/s, 20Hz, 각 12스텝으로 독립 반복
- [GitHub Actions run #42585174235](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42585174235), 결과 아티팩트 `native-curve-two-big-models-diagnostic`, 모델 가중치는 공개 아티팩트에 포함되지 않음
- 반복 비교 결과: `REPEATED_DIAGNOSTIC_MISMATCH`; 12스텝 마지막의 두 가상 위치 차이 약 **0.00019256m(0.193mm)**; RGB 해시 일부 불일치
- **1~4스텝:** 일반/광각 카메라 해시, 모델 곡률·종가속도, 가상 위치 일치
- **5스텝:** 이전 위치가 같은데도 일반 카메라 해시 불일치가 최초 발견. 이후 원시 모델 출력과 위치에도 미세 차이 누적
- **6스텝부터:** 일반·광각 해시 모두 달라진 스텝 확인. 이 시점부터 모델 출력 차이도 발생
- 따라서 현 단계에서 **반복 입력 영상 자체가 동일하지 않음**은 관측되지만, 원인이 렌더 엔진의 실시간 task clock, 버퍼 업데이트, 셰이더, 객체 애니메이션 중 무엇인지는 단정하지 않음.

## ONNX를 제외한 독립 대조

[Fixed-pose camera run #42586162386](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42586162386): 동일한 가상 X/Y/헤딩·시드에서 MetaDrive 일반/광각 영상을 12회 촬영하여 **일반 이미지 해시 3종, 광각 이미지 해시 2종**을 관측. 즉 ONNX 추론과 가상 차량 이동을 제외해도 RGB 프레임이 변화할 수 있다.

이것은 원인 가설을 좁히는 증거이지만 완전한 인과 분리는 아니다.

## 수정 및 재시험

- [Panda3D ClockObject 공식 문서](https://docs.panda3d.org/1.10/python/reference/panda3d.core.ClockObject)의 비실시간 시계 `M_non_real_time`과 고정 `dt` 적용 방식을 별도 opt-in 기능으로 추가.
- `bigbench/panda_clock.py`: 가상 시계의 시작·종료와 원래 시계 모드 복원.
- `NativeMetaDriveProvider(fixed_virtual_clock=True)`: 새로운 시뮬레이터 구성 전에 가상 프레임 시계를 고정해 렌더링 시점의 벽시계 의존성을 줄이는 실험.
- `scripts/metadrive_camera_stability.py --fixed-clock` 및 [재시험 CI](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/workflows/camera-stability.yml): 기본 렌더러와 고정 가상 시계에서 동일 포즈 RGB 해시를 각각 기록.
- **재시험 결과 확인 전에는 고정 시계 모드를 모델 비교의 디폴트로 적용하지 않는다.** 고정 시계가 안정적으로 동작해도 ONNX 반복시험과 여러 시드·장면의 별도 증거가 필요하다.

## 2026-11-10: 개별 RGB 픽셀·모델 입력 차이 원인 분리

**근거:** [MetaDrive 영상 픽셀 감사 #42738118074](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42738118074) 및 [기본 차량 RGB 가림 제거 진단 #42739088166](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42739088166).

### 원본 RGB와 I420 입력의 관측치

- 가상 세계 X/Y/헤딩을 고정하고 **12프레임** 촬영한 뒤 첫 2프레임을 초기 렌더링 구간으로 구분했다. 원본 전체 12프레임의 상태는 양쪽 설정에서 여전히 `FIXED_POSE_CAMERA_DRIFT`.
- **초기 2프레임 제외, 기본 MetaDrive 그래픽 포함:** 일반 카메라 512×256 = 131,072픽셀 중 최대 **2픽셀** 차이; 최대 RGB 채널 차이 **7**; 광각 카메라는 남은 10프레임에서 **완전 일치**.
- 같은 조건에서 기존 `RGB→I420` 변환을 독립 재계산한 결과, **모델 입력 배열**은 일반 카메라에서 최대 **원소 1개(최대 값 차이 4)**가 다르고 광각 입력은 동일. 이는 이전 SHA 전체 불일치가 실제로 얼마나 작은 픽셀 변화인지 설명할 뿐, 모델 recurrent 출력 영향이 없음을 증명하지는 않는다.
- **시야 검증에서 발견된 별도 결함:** world (0,0) 고정 포즈에 MetaDrive의 기본 가상 차량 차체가 크게 보이며 앞쪽 도로 시야를 가렸다. 이 고정 포즈 시험은 원래부터 차선 영상 품질을 대표할 수 없었다.
- **기본 차량 차체만 RGB 카메라에서 숨긴 분리 시험:** 일반 카메라 최대 **8픽셀**, 최대 RGB 차이 **8**, 광각은 초기 2프레임 제외 완전 일치. 차체 가림은 제거됐으나 RGB 렌더링의 비트 수준 불일치는 지속됐다. 가상 모델/물리 동역학은 변경하지 않았다.
- **Panda 시계를 고정해도** 위 픽셀 불일치는 완전히 사라지지 않았다. 현재 근거로 특정 그림자·셰이더·버퍼 비동기화가 유일한 원인이라고 단정할 수 없다.
- 실제 시험에서 오차가 작다는 이유로 기존 `REPEATED_DIAGNOSTIC_MISMATCH`를 PASS로 승격하지 않는다.

### 새로운 무보간·무보정 입력 수렴 실험

- `bigbench/frame_stability.py`: 실제 RGB 배열의 변경 픽셀 개수/좌표 범위/평균 및 최대 채널 차이를 독립 계측.
- `scripts/metadrive_camera_stability.py --pixel-audit --warmup 2 --save-frames`: 전체 원본 해시와 워밍업 이후 픽셀 진단을 **별도** 기록. 워밍업으로 원본 불일치를 가리지 않는다.
- `bigbench/camera_convergence.py`: 동일 시뮬레이터 포즈에서 **연속된 road·wide RGB 프레임 두 쌍이 완전히 같을 때만** 입력을 확정하는 선택적 실험. 원본 픽셀을 수정·평균·블러하거나 기록 영상을 대체하지 않는다. 최대 반복 횟수 이내 실패 시 즉시 차단한다. 원래 카메라의 실시간 촬영 정책과 달라진다는 사실도 명시.
- `scripts/run_same_model_repeat.py` 및 [실제 MD-V3 반복 CI](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/workflows/model-camera-repeat.yml): 독립 새 MetaDrive 환경에서 MD-V3를 2번 실행하고 영상 SHA/시간축/가상 자세를 비교. **실제 실험 결과 확인 전까지 개선 효과 미확인**.

### 현재 결론

**픽셀 수준의 매우 작은 변화가 확인됐지만, 정확한 비트 재현성은 아직 실패다.** 같은 모델 반복 결과의 시계열 재현성, 긴 S자 전구간, 다중 시드와 외부 CARLA 교차검증을 완료하기 전에는 확정적 모델 순위 산출 금지. 카메라 수렴을 적용해 성공하더라도 **다중 캡처 선택에 따른 조건 변화**를 별도 표시해야 한다.

## 2026-11-10: 독립 ONNX 세션 원인 분리 — 고정 영상 PASS

**결과:** [실제 MD-V3 frozen-camera CI #42755109268](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42755109268) 및 [첫 실행 #42755048641](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42755048641)에서 공식 SHA256 고정 MD-V3를 **두 개의 독립 ONNX Runtime 세션**으로 실행했다.

- 단일 MetaDrive 가상 카메라 road/wide 영상 쌍을 **정확히 1회 촬영**하고, 두 모델 세션에 같은 이미지 바이트를 각 12스텝 재입력한다.
- 모델의 `reset()`으로 재귀 상태를 독립 초기화한다. 모델의 action(곡률/가속도)과 공통 이상적 운동학의 결과를 직접 비교한다.
- 두 실행의 결과: `SYNTHETIC_REPEATED_DIAGNOSTIC_MATCH`, **가상 위치 최대 차이 0m**. 동일 영상, 동일 계약·가상 시간축에서 ONNX 추론/상태연결 경로가 재현된다는 기술적 근거다.
- `bigbench/frozen_camera_diagnostic.py`는 모델 action(목표곡률·가속도) **정확한 값 일치**도 별도 진단한다. 이미지 입력 해시 일치 여부와 모델 출력 일치 여부를 분리한다.
- `tests/test_frozen_camera_diagnostic.py`의 테스트 더블은 실제 ONNX 성능을 증명하지 않으며, 가짜 정책은 별도 `OPEN_LOOP_FIXED_RGB_TEST_DOUBLE_NOT_ONNX`로 구분한다.
- **엄격한 제한:** 이 시험은 촬영 영상을 반복하므로 `OPEN_LOOP_FIXED_NATIVE_RGB_ONNX_REPRODUCIBILITY_ONLY`다. 실제 영상 폐루프 주행, 모델 차선 유지 성능, 실제 comma 광학 동등성 및 안정성 검증은 아니다.

**원인 분리 해석:** 카메라가 매 단계 새로운 영상을 만드는 반복시험에서만 나타난 불일치의 우선 조사 대상은 MetaDrive/Panda3D의 이미지 생성·시점/버퍼/장면 업데이트 경로다. 이것이 렌더러 단독의 결함을 *증명*하는 것은 아니다. 재귀 상태 초기화·모델 실행 경로의 재현성 검사는 고정 영상 조건에서는 통과했다.

**남은 하드 게이트:** 실제 폐루프에서 동일 가상 포즈/도로/시드가 같은 RGB 배열과 모델 입력 배열을 내는지, 그림자·톤매핑·렌더 태스크/복사 RAM 버퍼·동적 오브젝트를 분리한 뒤 다시 검증한다. 숫자 허용오차를 임의 확대해 전체 모델 비교를 PASS 처리하지 않는다.

## 2026-11-10: 렌더 틱·RAM 읽기·장면 마스크 6조건 실험

- 공식 MetaDrive 0.4.3로 [실제 CI #42757874100](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42757874100) 실행: **6개 조건 모두 원본·모델 RGB·I420 측정/양성 대조 완료**. 원시 증거 아티팩트 `meta-render-task-readback-scene-factorization` (id 13736736732).
- GPU 재렌더 없이 `RTMCopyRam` 최종 텍스처를 3회 반복 읽은 **모든 표본에서 비트 단위 완전 일치**. 단순 CPU readback 재호출만으로는 기존 불일치가 재현되지 않음.
- 동일 pose/초기 2프레임 제외/기본 MetaDrive 차량 **RGB 숨김**: 카메라별 `perceive`와 두 카메라 동시 `taskMgr.step`에서는 원본 narrow 최대 9픽셀 변화, I420 최대 6개 원소 변화. `graphicsEngine.renderFrame()`을 직접 1회 호출한 조건에서는 이후 narrow/wide 및 I420 모두 동일. **2m 포즈 이동 시 두 카메라 모두 실제 변화**했으므로 단순 stale frame은 아님.
- 기본 가상 차량 시각화 표시/숨김을 바꾸면 드리프트 패턴이 달라진다. '가상 차량 표시'만이 단독 원인이라는 가설은 이번 결과로 지지되지 않는다.
- **공유 프로세스·전역 시계 교란이 남음.** 이를 통제할 [독립 Python/Xvfb 프로세스 실험](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/workflows/render-causality-process.yml)과 `PSSM.update` / `update main chase camera` 개별 태스크 차단 실험을 별도 실행. 증거 확인 전에는 인과관계를 확정하지 않음.
- [세부 통계/소스 규약](METADRIVE_RENDER_CAUSALITY.md) 참조. 모델 재현성 전체 게이트는 계속 **미통과**.

## 하드 게이트

| 구분 | 완료 기준 | 현재 |
|---|---|---|
| 1. 고정 포즈 카메라 | 같은 가상 입력으로 동일 road/wide RGB 해시 | 기본 시계 FAIL(3/2종), 고정 시계 검증 대기 |
| 2. 단일 모델 반복 | 동일 12스텝에서 지정한 수치/영상 재현 허용범위 충족 | **고정 영상 12스텝 PASS**, 실제 새 렌더링 폐루프는 FAIL |
| 3. 동일 시드 모델 비교 | 3D 차선 기준과 두 카메라 첫 프레임 일치 | 단기 입출력 경로 PASS, 모델 점수 금지 |
| 4. 긴 시나리오 | 2개의 연속 S자 굽이와 진출입 램프 전체 완주 | 미실시 |
| 5. 다중 시드/엔진 | 복수 시드·카메라 설정 및 독립 CARLA 관측 검증 | 미실시 |

**절대 원칙:** 실차 테스트 금지, 싼타페 등 실제 차종 동역학 제외, CD210·Carrot MPC/Params 배제, 공개 저장소에 원본 실차 로그 업로드 금지.
