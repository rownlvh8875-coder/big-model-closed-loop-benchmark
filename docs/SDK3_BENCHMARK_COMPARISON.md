# Linux SDK3 공식 모델 비교

이 도구는 md-v3와 Light Speed 2의 공식 ONNX를 고정된 MetaDrive 가상 시나리오에서 실행하고, 원본 결과를 오프라인 HTML에서 비교합니다. 적용 범위는 등록된 Linux SDK3 소프트웨어 렌더러·카메라·도로·모델 조합입니다.

## 준비

- Docker의 로컬 동결 이미지 ID는 `sha256:b9d673de93f1857e4dfa5ed6a48330d568ef96fce7f3cc975f0c688877e6e26e`입니다. SDK 파일은 실제 `libpandagl.so`와 고정 SHA-256을 확인합니다.
- SDK3 모델 자격은 호스트 가용 RAM 12 GiB, cgroup을 반영한 실제 가용 8 GiB, 빈 디스크 8 GiB, 동일한 네 CPU 및 ORT 1.20.1 CPU입니다.
- 공식 모델 파일의 정확한 크기, SHA-256과 입력 명세는 `model_specs/md-v3.json`과 `model_specs/light-speed-2.json`에 있습니다. Light Speed 2의 조향 좌표계는 기존 공식 두 모델 비교 명령과 같은 명시적 `model-frd` 선언입니다.

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
