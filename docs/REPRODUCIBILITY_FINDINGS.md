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

## 하드 게이트

| 구분 | 완료 기준 | 현재 |
|---|---|---|
| 1. 고정 포즈 카메라 | 같은 가상 입력으로 동일 road/wide RGB 해시 | 기본 시계 FAIL(3/2종), 고정 시계 검증 대기 |
| 2. 단일 모델 반복 | 동일 12스텝에서 지정한 수치/영상 재현 허용범위 충족 | FAIL |
| 3. 동일 시드 모델 비교 | 3D 차선 기준과 두 카메라 첫 프레임 일치 | 단기 입출력 경로 PASS, 모델 점수 금지 |
| 4. 긴 시나리오 | 2개의 연속 S자 굽이와 진출입 램프 전체 완주 | 미실시 |
| 5. 다중 시드/엔진 | 복수 시드·카메라 설정 및 독립 CARLA 관측 검증 | 미실시 |

**절대 원칙:** 실차 테스트 금지, 싼타페 등 실제 차종 동역학 제외, CD210·Carrot MPC/Params 배제, 공개 저장소에 원본 실차 로그 업로드 금지.
