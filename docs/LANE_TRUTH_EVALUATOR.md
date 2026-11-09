# 차종 비종속 3D 원시 차선 좌표 기반 횡방향 평가기 — 2단계 개발

**상태 (2026-11-09): 합성 단위시험 + MetaDrive S자/램프 4종 대상 기하 평가기 통합 진단 PASS. 실제 대형모델 성능 검증은 미실시.** 실차 테스트·실차 CAN·차량별 동역학·CD210/Carrot 튜닝 제외.

## 무엇을 계산하는가?

`bigbench/lane_truth.py`는 **대형모델에 절대 제공하지 않는 정답 데이터 영역**에서 MetaDrive 네이티브 차선 도로의 `lane.local_coordinates`, `lane.width_at`, `lane.heading_theta_at`을 이용해 다음 관측치를 계산한다.

- 전방 이동거리 `s`(m)와 **오른쪽이 양(+)인** 차로 중심 상대 오프셋 `r`(m)
- 진짜 지도 차로 폭 `w(s)`(m)
- 방향이 있는 곡률 `κ = Δheading / Δs`(1/m)
- 차로 기준 헤딩 오차(rad)
- 공통 가상 에이전트 반폭 `a`를 기준으로 한 좌/우 경계 여유 `w/2 ± r − a`(m)
- 가상 에이전트 침범 깊이 `max(0, -left_clearance, -right_clearance)`(m)
- 커브 안쪽 방향으로 치우친 오프셋 `−sign(κ)·r`(m); 직선에서는 `None`

`a`는 가상 형상의 수학적 반폭에 불과하며 **싼타페 등 실제 차량 치수·조향 반응을 의미하지 않는다.** 향후 비교시험에서는 모든 모델에 동일한 값을 고정하고 별도 민감도 시험으로 구별한다.

## 검증 근거

- 좌/우 직선 정상화, 정확한 반폭을 이용한 침범 거리, 양·음 곡률에서 안쪽 방향 부호가 바뀌는지, 헤딩 오차 계산을 합성 해석적 차로 수식으로 검증했다.
- 차로 범위 밖의 상태, 비정상 데이터, 폭/반폭 무효 입력을 **실패로 기록**한다.
- 여러 차선 중 선택할 경우 물리적 횡 오차가 가장 작은 **유효 차선**만 사용한다. 이는 모델에 추가 입력을 제공하지 않는 사후 평가기이며, 실제 운전 경로 선택의 타당성을 보장하지 않는다.

## 재현

```bash
python -m unittest discover -s tests -p 'test_lane_truth.py' -v
```

## 2단계 진행 추가 기록 (2026-11-09)

- `bigbench/lane_truth.py`: `evaluate_target_lane_by_id` 추가. 지정한 `lane.index`가 없거나 중복이면 실패하며 **최근접 차선 자동 대체 금지**.
- 동일 파일: `summarize_lane_truth` 추가. 공통 가상 시간 간격에서 평균·최대·P90 중심 오차, 침범 깊이 최대값, 침범 횟수·지속시간을 평가 목적으로만 산출.
- `tests/test_lane_truth.py`: 분기 차선이 더 가까운 상황에서도 지정한 목표 차선이 유지되는지, 경계 초과 깊이와 침범 시간 계산이 일치하는지 검증.
- `scripts/metadrive_lane_truth_audit.py`: MetaDrive 0.4.3의 실제 S자·진입/진출 램프 `lane.position`과 `local_coordinates`를 이용한 기하학적 자가일관성·침범 지표 검사기. 실제 차량/ONNX 추론을 사용하지 않음.
- [.github/workflows/metadrive-curved-lanes.yml](../.github/workflows/metadrive-curved-lanes.yml)에 실제 지도 4종 통합시험 추가. [CI 실행 #42582782731](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42582782731) 결과 확인 전에는 **실제 MetaDrive 2단계 PASS로 표시하지 않음**.
- 1단계 네 종류 곡선/램프 영상 정합성 진단 PASS: [CI #42578810503](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42578810503). 이 기록은 2단계 평가기 성능 검증과 별개임.

## 네이티브 통합 증거

- [GitHub Actions #42582782731](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42582782731): S자 2종/진입·진출 램프 2종 모두 `PASS_NATIVE_TARGET_LANE_GEOMETRY_GATE` 확인.
- 목표 차로 ID 고정, 중심선 오차, 공통 가상 반폭을 이용한 의도적 0.2m 경계 침범 계산에 대한 점검임. **모델 주행/동적 정책 검증 아님**.
- 2단계의 기초 수학 및 네이티브 지도 시험은 완료. 남은 시험은 목표 노선별 전환점/합류 판단과 실제 ONNX 에피소드 연결 시 다시 수행.

## 아직 수행하지 않은 필수 검증

1. 실제 MetaDrive 0.4.3 S자 및 진출입 램프 지도의 진실값을 이 평가기로 입력해 좌·우 부호와 구간 전환을 검사한다.
2. 선택된 목표 차로와 단순 최근접 차로가 달라지는 상황을 구분한다. 차로 변경이나 교차 구간에서 최근접 차로만 따르면 침범이 사라진 것처럼 보일 수 있으므로 **모델 평가 시 목표 차로 식별자를 고정/명시**해야 한다.
3. 1단계의 영상-3D 좌표 정합성이 통과하기 전에는 이 수식에서 나온 차선 침범/오차를 대형 ONNX 모델의 공식 점수로 사용하지 않는다.
4. 실제 차선 도색 경계가 차로 중심으로부터 정확한 반폭인지, 날씨·조명 조건에 따른 차이가 있는지도 따로 검증한다.

위 조건을 완료하기 전에는 **2단계 초안/계산기 구현**일 뿐, 폐루프 모델 성능평가가 아니다.

## 소스

- [MetaDrive AbstractLane](https://github.com/metadriverse/metadrive/blob/main/metadrive/component/lane/abs_lane.py)
- [MetaDrive StraightLane 좌표계](https://github.com/metadriverse/metadrive/blob/main/metadrive/component/lane/straight_lane.py)
- [7단계 개발 로드맵](ROADMAP_7_STAGES.md)
