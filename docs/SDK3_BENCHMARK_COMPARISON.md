# Linux SDK3 공식 모델 비교

이 도구는 md-v3, Light Speed 2, Fairy Tale, Light Speed의 공식 ONNX를 등록된 MetaDrive 가상 시나리오에서 실행하고, 원본 결과를 오프라인 HTML에서 비교합니다. 적용 범위는 등록된 Linux SDK3 소프트웨어 렌더러·카메라·도로·모델 조합입니다.

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

## 등록 모델 추가 비교

기존 두 모델의 원본은 기존 `--md-v3`, `--light-speed-2`,
`--longitudinal`, `--ramps` 옵션으로 지정합니다. 다음 옵션은
등록돼 있는 모델의 보존 자료를 해당 시험에 추가합니다.

| 옵션 | 전달할 원본 폴더 |
| --- | --- |
| `--extra-full-s MODEL ROOT` | `20261109-s_curve_left_right`처럼 조건별 원본이 들어 있는 폴더 |
| `--extra-longitudinal MODEL ROOT` | `20261109-lead_brake-fairy-tale`처럼 조건과 모델별 원본이 들어 있는 폴더 |
| `--extra-ramps MODEL EVIDENCE` | `camera-gate.json`, `probes/`, `models/`가 있는 폴더 |

예를 들어 Fairy Tale에 대해 다음 인자를 함께 전달합니다.

```bash
--extra-full-s fairy-tale fairy-tale-evidence/full-s/models
--extra-longitudinal fairy-tale fairy-tale-evidence/longitudinal/models
--extra-ramps fairy-tale fairy-tale-evidence/ramps
```

추가 모델도 실행 기록에서 직접 재검증합니다. Full-S와 종방향의
공통 입력 판정에는 해당 조건에 포함된 모든 모델이 들어갑니다.
램프는 원본 카메라 캡처에서 각 모델의 진입 판정을 재생성하고,
각 위치의 기하·렌더러·카메라와 입력이 기존 코호트와 같을 때 비교합니다.
종방향 자료는 조건·모델별 한 번 실행한 결과를 표시합니다.

## 네 모델의 통합 비교판 재현

[검증 결과, PDF, 채점표와 원본 해시 목록](evidence/sdk3-model-comparison-20261125/README.md)을 확인할 수 있습니다.

위 결과 명령에 Fairy Tale과 Light Speed의 fixed Full-S, 종방향,
램프 증거를 추가합니다. 통합 Full-S는 모델마다
`--integrated-full-s MODEL ROOT`를 한 번 지정합니다. `ROOT` 아래에는
`20261109-s_curve_left_right`처럼 55 m 조건별 폴더와
`20261109-s_curve_left_right_radius45`처럼 45 m 조건별 폴더를 둡니다.
각 폴더에는 원본 `camera-admission.json`, `pair-ledger.json`, `run-0/`, `run-1/`이
있어야 합니다. 여러 실험 폴더에 증거가 나뉘어 있으면 조건별 원본 폴더를
가리키는 심볼릭 링크를 이 구조에 둘 수 있습니다.

예시에서 `inputs`는 보존한 증거를 위 구조로 배치한 경로이며, `report`는
새 출력 폴더입니다. 기준 모델의 횡방향 원본은 상위 폴더의
`probe-admission.json`까지 함께 보존합니다.

```bash
python -B -m scripts.build_sdk3_benchmark_dashboard \
  --md-v3 inputs/md-v3-full-s/models \
  --light-speed-2 inputs/fixed/light-speed-2 \
  --longitudinal inputs/longitudinal/baseline \
  --ramps inputs/ramps/baseline \
  --extra-full-s fairy-tale inputs/fixed/fairy-tale \
  --extra-full-s light-speed inputs/fixed/light-speed \
  --extra-longitudinal fairy-tale inputs/longitudinal/fairy-tale \
  --extra-longitudinal light-speed inputs/longitudinal/light-speed \
  --extra-ramps fairy-tale inputs/ramps/fairy-tale \
  --extra-ramps light-speed inputs/ramps/light-speed \
  --integrated-full-s md-v3 inputs/integrated/md-v3 \
  --integrated-full-s light-speed-2 inputs/integrated/light-speed-2 \
  --integrated-full-s fairy-tale inputs/integrated/fairy-tale \
  --integrated-full-s light-speed inputs/integrated/light-speed \
  --out report
```

재현에는 새 모델 추론이나 Docker 실행이 필요하지 않습니다.
Python 3.11, NumPy 2.4.6, opencv-python-headless 5.0.0.93에서
보존된 모델·카메라·궤적 기록을 검증합니다. 원본의 파일 목록과
`inputs.SHA256SUMS`가 제공되는 경우 증거를 받은 폴더에서
`sha256sum -c inputs.SHA256SUMS`로 대조합니다.
통합 Full-S는 두 독립 실행의 종료 상태와 엄격 반복성을 기록합니다.
모델 간 공통 기하는 해당 조건의 첫 RGB와 입력 텐서까지 일치할 때 확인됩니다.
종방향은 모델·조건별 한 실행이며 수집 기록의 `source_sha`와 실제 추론 수를
최종 보고서와 대조합니다. 선행차 중심 간격이 0 이하가 되어 일찍 종료된 실행은
그 시점까지 관측된 추론 수로 검증합니다.

## 저장소 테스트 재현

전체 체크아웃에서 `python -B -m unittest discover -s tests`를 실행합니다.
`docs/evidence/`의 추적 파일은 일부 테스트의 입력입니다. Linux에서
PID 네임스페이스로 격리할 경우 Python을 살아 있는 부모 아래에서
새 세션으로 실행합니다. PID 1로 직접 실행하면 부모 PID가 0으로 보입니다.
외부 프로세스 그룹을 그대로 상속하면 새 네임스페이스에서 그룹 ID도
0으로 보일 수 있습니다. 아래 명령은 두 식별자를 모두 실제로 관측하게 합니다.

```bash
unshare --user --map-root-user --pid --fork --mount-proc \
  bash -c 'setsid "$@" & child=$!; wait "$child"' bash \
  python -B -m unittest discover -s tests
```
