# Linux SDK3 공식 모델 비교

이 도구는 md-v3와 Light Speed 2의 공식 ONNX를 고정된 MetaDrive 가상 시나리오에서 실행하고, 원본 결과를 오프라인 HTML에서 비교합니다. 적용 범위는 등록된 Linux SDK3 소프트웨어 렌더러·카메라·도로·모델 조합입니다.

## 범위와 결과 열기

현재 비교판은 동결 Linux SDK3 MetaDrive의 full-S, 진입·진출 램프, 종방향을 다룹니다. 보존된 결과는 같은 폴더의 `index.html`과 `comparison.json`으로 확인합니다. 보고서를 다시 만들 때는 원본 실행 기록을 읽어 검증합니다.

CARLA 교차검증은 선택 항목이며 미실행입니다. Windows 공식 모델과 실측 광학·센서 NV12는 [별도 검증 범위](remaining-validation-handoff.md)입니다.

## 준비

- Docker의 로컬 동결 이미지 ID는 `sha256:b9d673de93f1857e4dfa5ed6a48330d568ef96fce7f3cc975f0c688877e6e26e`입니다. SDK 파일은 실제 `libpandagl.so`와 고정 SHA-256을 확인합니다.
- SDK3 모델 자격은 호스트 가용 RAM 12 GiB, cgroup을 반영한 실제 가용 8 GiB, 빈 디스크 8 GiB, 동일한 네 CPU 및 ORT 1.20.1 CPU입니다.
- 공식 모델 파일의 정확한 크기, SHA-256과 입력 명세는 `model_specs/md-v3.json`과 `model_specs/light-speed-2.json`에 있습니다. Light Speed 2의 조향 좌표계는 기존 공식 두 모델 비교 명령과 같은 명시적 `model-frd` 선언입니다.

Linux x86-64의 Python 3.11에서 `deps`가 새 로컬 경로일 때, 다음 고정 버전으로 ORT 런타임을 준비합니다. NumPy 2.4.6과 OpenCV 5.0.0.93은 동결 이미지에서 사용합니다.

```bash
python3.11 -m pip install --only-binary=:all: --no-deps --target "$deps" \
  onnxruntime==1.20.1 flatbuffers==24.3.25 coloredlogs==15.0.1 \
  humanfriendly==10.0 packaging==24.2 protobuf==5.29.5 sympy==1.13.3 mpmath==1.3.0
```

## 실행

아래는 한 횡방향 조건입니다. `sdk`, `deps`, `weight` 변수에는 로컬의 동결 SDK 파일, 지침에 맞춘 ORT 디렉터리, 해당 공식 ONNX 파일을 지정합니다. 모델 실행 때 출력 폴더 바로 아래에 각 독립 프로세스의 로그와 실행 기록이 생성됩니다.

```bash
for index in 0 1; do
  python -m scripts.run_sdk3_benchmark_case lateral probe \
    --sdk "$sdk" --seed 20261109 --scenario s_curve_left_right \
    --out "output/camera/20261109-s_curve_left_right-$index"
done
python -m scripts.run_sdk3_benchmark_case lateral model \
  --sdk "$sdk" --deps "$deps" --model-file "$weight" --model-id light-speed-2 \
  --seed 20261109 --scenario s_curve_left_right \
  --probe output/camera/20261109-s_curve_left_right-0 \
  --probe output/camera/20261109-s_curve_left_right-1 \
  --out output/light-speed-2/20261109-s_curve_left_right
```

20261109와 20261110에 좌→우, 우→좌를 각각 실행합니다. 각 모델·조건은 최대 두 독립 프로세스이며 프로세스당 600스텝·9,000초입니다. 속도 8 m/s, 시간 간격 0.05초, 기존 단일 FRD→FLU 변환과 최초 차선 침범 종료를 적용합니다.

종방향은 같은 명령의 첫 인자를 `longitudinal`로 바꾸고, 시나리오별 실제 무모델 카메라 프로브를 별도로 준비합니다. `lead_brake`와 `stop_go`는 240스텝, `cut_in`은 200스텝입니다. 네이티브 직선 차선 위의 동일 위치와 20 Hz 선행차 일정을 사용합니다. 중앙 간격이 처음 0 이하에 이르거나 등록된 스텝에 도달하면 종료합니다. 종방향 출력 폴더 이름은 `20261109-<scenario>-<model-id>`입니다.

## 결과

```bash
python -m scripts.build_sdk3_benchmark_dashboard \
  --md-v3 output/md-v3 --light-speed-2 output/light-speed-2 \
  --longitudinal output/longitudinal --out output/comparison
```

`comparison.json`과 `index.html`에서 실제 추론으로 재구성한 실행 상태·완주·엄격 반복성, 최초 차선 침범, 선행차 중심 간격·TTC 및 정지·재출발을 확인합니다. 원본 파일과 정리 기록이 유효해야 판정을 제공합니다. 교차모델 비교에는 공통 경로·렌즈·렌더러와 첫 원본 RGB·입력 텐서가 일치해야 합니다. 각 모델의 이후 프레임은 그 모델 자체의 동작에 따른 새 포즈에서 촬영합니다.

## 진입·진출 램프

`scripts.run_sdk3_ramp_case`는 같은 동결 SDK3에서 MetaDrive의 실제 `in_ramp`와
`out_ramp` 도로를 실행합니다. 진입은 램프 직선의 12%부터 가속차로 끝까지,
진출은 감속차로의 12%부터 진출 직선 끝까지입니다. 각 경로는 실제 도로 구간
다섯 개로 구성됩니다. 본선 차로 변경은 별도 검증 범위입니다.

정해진 두 시드의 두 램프를 각각 새 프로세스 두 개로 사전검증합니다.
아래 예시는 아직 없는 `output/ramps` 경로를 사용합니다.

```bash
ramps=output/ramps
for seed in 20261109 20261110; do
  for scenario in in_ramp out_ramp; do
    for index in 0 1; do
      python -m scripts.run_sdk3_ramp_case probe --sdk "$sdk" \
        --seed "$seed" --scenario "$scenario" \
        --out "$ramps/probes/$seed-$scenario/run-$index"
    done
  done
done
python -m scripts.verify_sdk3_ramps probe "$ramps/probes" \
  --out "$ramps/camera-gate.json"
```

오프라인 카메라 검증에는 Python 3.11, NumPy 2.4.6과
opencv-python-headless 5.0.0.93을 사용합니다. 네 조건이 모두 통과하면 동일한
커밋의 깨끗한 작업 트리에서 공식 모델을 한 프로세스씩 실행합니다.
`weight`는 `--model-id`에 맞는 검증된 모델 파일입니다. 같은 시드와 시나리오에
`run-0`과 `run-1`을 따로 실행합니다.

```bash
python -m scripts.run_sdk3_ramp_case model \
  --sdk "$sdk" --deps "$deps" --model-file "$weight" --model-id light-speed-2 \
  --seed 20261109 --scenario in_ramp --gate "$ramps/camera-gate.json" \
  --out "$ramps/models/light-speed-2/20261109-in_ramp/run-0"
```

통합 비교 화면에는 기존 명령에 `--ramps "$ramps"`를 추가합니다. 경로 아래에
`camera-gate.json`, `probes/`, `models/`가 함께 있어야 합니다. 검증기는
보존된 RGB에서 카메라 캔버스와 모델 입력을 다시 만들고 각 실행을 원래
사전검증과 대조합니다. 결과에는 모델별 실제 추론 수, 각 조건의 완주와
엄격 반복, 침범 위치가 포함됩니다. `index.html`과 `comparison.json`을
같은 폴더에서 열 수 있습니다.
