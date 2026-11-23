# 조향·가감속 통합 폐루프

통합 모드는 동결 Linux SDK3, llvmpipe, ORT 1.20.1 CPU와 원본
road/wide 카메라를 사용합니다. 출발 속도는 8 m/s이고 시간 간격은
0.05초입니다. 원본 출력의 목표곡률은 기존 FRD→FLU 변환을 한 번
거치며, 목표가속도는 공통 이상적 운동학의 속도 적분에 적용됩니다.
변경된 위치·방향·속도로 다음 라이브 프레임을 취득합니다. 첫 차선
침범, 경로 종점 도달, 또는 600스텝에서 종료합니다.

기존 `lateral`은 8 m/s 고정속도 시험입니다. 통합 시험은 별도의
`integrated` 트랙과 `full-s-integrated-v1` 실행 프로토콜을 사용합니다.
출발 위치·카메라와 첫 입력은 기존 Full-S 조건과 대조합니다.

```bash
python -B -m scripts.run_sdk3_benchmark_case integrated model \
  --sdk "$sdk" --deps "$deps" --model-file "$weight" --model-id fairy-tale \
  --seed 20261109 --scenario s_curve_left_right \
  --probe "$probes/20261109-s_curve_left_right/run-0" \
  --probe "$probes/20261109-s_curve_left_right/run-1" \
  --out output/integrated/fairy-tale/20261109-s_curve_left_right
```

`bigbench.benchmark_results.lateral_pair(..., integrated=True)`는
소유권과 카메라를 확인하고 모든 스텝의 곡률·가속도·속도·자세를
원본 ONNX 출력에서 다시 계산합니다. 각 모델의 완주와 두 실행의
엄격 반복성을 별도로 판정합니다. 이 검증에는 가상 차선 위의
조향·가감속 동시 적용이 포함되며 선행 차량이 포함된 종방향 시험은
기존 별도 트랙에서 확인합니다.
