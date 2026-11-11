# 차종 비종속 3D 원시 차선 좌표 기반 횡방향 평가기 — 2단계 개발

**상태 (2026-11-11 재확인): 2026-11-09 MetaDrive S자/램프 4종의 대상 기하 진단 PASS. 8개 차로의 중심 24개·의도적 우측 침범 24개 표본과 순수 집계 8개를 재확인했다. 이 결과는 모델 주행 성능 검증이 아니다.** 실차 테스트·실차 CAN·차량별 동역학·CD210/Carrot 튜닝 제외.

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
- [.github/workflows/metadrive-curved-lanes.yml](../.github/workflows/metadrive-curved-lanes.yml)에 실제 지도 4종 통합시험 추가. [CI 실행 #42582782731](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42582782731)의 원본 수치·API 아카이브·작업 성공을 확인하여 **실제 MetaDrive 기하 진단 PASS**로 기록한다.
- 1단계 네 종류 곡선/램프 영상 정합성 진단 PASS: [CI #42578810503](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42578810503). 이 기록은 2단계 평가기 성능 검증과 별개임.

## 네이티브 통합 증거

- [GitHub Actions #42582782731](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42582782731): S자 2종/진입·진출 램프 2종 모두 `PASS_NATIVE_TARGET_LANE_GEOMETRY_GATE` 확인.
- 목표 차로 ID 고정, 중심선 오차, 공통 가상 반폭을 이용한 의도적 0.2m 경계 침범 계산에 대한 점검임. **모델 주행/동적 정책 검증 아님**.
- 2단계의 기초 수학 및 네이티브 지도 시험은 완료. 남은 시험은 목표 노선별 전환점/합류 판단과 실제 ONNX 에피소드 연결 시 다시 수행.

## 통과한 계약과 원본 증거

source `c1ea8cabd7ec79ab9a08e2f2f2228c3f7fff3a3e`, seed `20261109`에서 네 장면 각각 두 차로를 선택했다. 각 차로의 길이 비율 `0.2`, `0.5`, `0.8`에서 `lane.position`으로 만든 중심 및 우측 점을 `local_coordinates`로 되돌리는 **네이티브 기하의 자가일관성** 시험이다. 별도의 실측 도로 정답을 얻은 것은 아니다.

공통 가상 반폭은 0.9 m, 해당 차로 폭은 3.5 m다. 우측 오프셋 `3.5/2 − 0.9 + 0.2 = 1.05 m`를 선택하여 0.2 m 침범을 의도적으로 만든다. 원래 게이트는 중심·우측 횡좌표·침범 깊이 오차 ≤0.05 m, 중심 종좌표 오차 ≤0.1 m를 요구했다. 세 우측 표본을 dt=0.05 s로 집계하면 침범 이벤트 1개·기간 0.15 s다. **이 0.15 s는 서로 떨어진 세 선택 자세에 부여한 집계 간격의 산술 결과이며, 실제 시간에 연속된 ONNX 궤적이나 주행 지속시간의 증거가 아니다.**

| Run | Source HEAD | Artifact ID | ZIP bytes | ZIP SHA256 |
|---|---|---:|---:|---|
| [42582782731](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42582782731) | `c1ea8cabd7ec79ab9a08e2f2f2228c3f7fff3a3e` | 13658405606 | 2059 | `5c600ade867e2873092f358a65ed7769b3fe23ed84a8372a8d74d0cd65d5d3ba` |

API ZIP SHA256/크기/안전 경로·심볼릭 링크 부재를 확인했다. 원본 JSON SHA256은 `e441e579888b57bb2cce7f90b4ee650da2309e7c931f69ceb3a408ad829f321c`이다. 2026-11-11 순수 재검산에서 8개 집계 dict는 과거 원래 함수와 정확히 일치했다. 최대 중심 횡오차 `7.105427357601002e-15` m, 최대 중심 종오차 `2.842170943040401e-14` m, 최대 우측 횡오차 `9.992007221626409e-15` m, 최대 의도적 0.2 m 침범 오차 `9.936496070395151e-15` m다. 재검산은 저장된 수치와 산술을 확인하며, 네이티브 지도/역좌표 연산을 새로 실행하지 않았다.

전체 7개 역사적 아카이브와 한계는 [통합 검증 기록](STAGE7_INTEGRATION_VERIFICATION.md)에 있다. 원본 및 순수 재검산은 무시되는 `output/stage7-geometry-integration-audit/`의 `verified_archives.json`, `lane_truth_recomputed.json`에 보존한다. 이 실행의 별도 곡선 영상 아카이브 `13657832137`은 이번 감사에서 다운로드/재해시하지 않았으며, 영상 수치의 재현은 앞선 최종 `42578810503` 아카이브에 근거한다.

## 여전히 열려 있는 검증

1. 합류/분기/차선 변경에서 목표 노선·차로 전환 정책의 타당성. 더 가까운 차로가 있더라도 지정한 목표 ID를 자동 대체하지 않는다. 이 네이티브 시험은 선택한 각 차로의 정적 점을 검사했으며 동적 전환 정책을 검증하지 않았다.
2. 임의 장면·조명·가려짐·차로 높이·도색 두께/위치에 대한 영상 정합성. 과거 직선/S자/램프의 표본 진단은 통과했지만 전역 광학 보증이 아니다. 곡선의 최종 음성대조 기준은 실패 뒤 변경됐으며 그 이력은 [곡선 가이드](METADRIVE_CURVED_LANE_AUDIT.md)에 남긴다.
3. 이후 `feedback_both`/unsorted 후보 렌더러 전용 도색 게이트 및 전역 렌더링/실물 광학/생산 NV12 전처리 동등성. 과거 도색 영상으로 이 후보 설정을 새로 검증하지 않았다.
4. 모델 주행 성능·순위와 통계적 일반화. 공식 후보의 별도 반복 동일성 PASS를 이 기하 산술 시험이나 실제 주행 품질로 치환하지 않는다. 평가기의 진실값은 모델에 추가 입력으로 제공하지 않는다.

기초 수학과 이 네이티브 자가일관성 진단은 완료됐지만, 모든 장면의 평가 타당성이나 모델 폐루프 성능평가를 완료한 것은 아니다. `model_scoring_allowed=false`와 실차 제외를 유지한다.

## 소스

- [MetaDrive AbstractLane](https://github.com/metadriverse/metadrive/blob/main/metadrive/component/lane/abs_lane.py)
- [MetaDrive StraightLane 좌표계](https://github.com/metadriverse/metadrive/blob/main/metadrive/component/lane/straight_lane.py)
- [7단계 개발 로드맵](ROADMAP_7_STAGES.md)


## 적용 동작 좌표계: 확인된 레거시 연결 누락

`output/stage7-coordinate-contract-audit/coordinate_basis_proof.json`의 고정 공식 소스·순수 수학 증거에서 **모델 몸체 FRD → 가상 적분기 몸체 FLU의 적용 동작 회전이 누락**됐음을 확인했다. FRD는 전방/우측/아래, FLU는 전방/좌측/위다. **둘 다 오른손 좌표계**이며 `R = diag(1,-1,-1)`, 행렬식 +1인 전방축 180° 회전이다. 필요한 관계는 `k_world = -k_model`이고 종가속도는 그대로다. 전역 world-Y 또는 영상/카메라 축을 뒤집거나 제어기를 튜닝하는 변경이 아니다.

숫자 변환 `k_model = raw_lateral / max(2.5, speed)**2` 자체는 맞지만, 그 모델 우측 양의 곡률을 반시계 world yaw 양의 적분기에 몸체 기준 변환 없이 전달했다. 따라서 후보 4/4 및 PR #27 source `e84369c9f7f461a59c8d506b8b9efb2312297c03`을 포함한 기존 모델 게이트는 **레거시 반복 동일성만 확인하며 동작의 모델→월드 의미 타당성을 증명하지 않는다**. 위의 정적 도색 정합성/지도 좌표 산술은 모델 동작 연결을 시험한 것이 아니므로 서로 분리한다.

이전 감사 시점에는 교정 어댑터가 **TDD 구현 중이며 미완료**였고 교정 네이티브 게이트는 **미실행**이었다. 당시 계획은 raw 모델 출력 4개·재귀 상태·실제 I420를 보존하고 적용 동작만 별도 회전하며, 부모 모델 동작과 적용 world 동작을 분리 기록하는 것이다. 과거 동작·자세·라벨은 수정하지 않는다. 이 연결 누락이 추종 오차의 유일 원인이나 모델 품질/광학 동등성을 증명한 것은 아니다. [통합 검증 기록](STAGE7_INTEGRATION_VERIFICATION.md)에 증거 범위와 당시 미실행이던 교정 게이트를 구분한다.


레거시 확대 실행 **42987993022**의 독립 검증이 완료됐다. `camera028`, `native_ramps`, `longer160` 각 **4/4**, 총 **12/12 레거시 반복 동일성 PASS**이며, 새 UUID/nonce 24개, 실제 추론·완료 행 1472개, 정확히 일치하는 쌍 736행이다. 13개 API ZIP·74개 멤버와 모든 원시 사례/최종 집계의 검토가 명확하다. 알려진 동작 기준 변환 누락의 타당성을 통과한 것은 아니다. 긴 실행 네 사례(반복 프로세스 8개)는 모두 세 노선 차로 중 첫 차로만 방문했고 최종 active index는 0이며, 최대 가상 횡오차는 약 39–41 m다. 정확한 사례별 값과 아카이브는 [통합 기록](STAGE7_INTEGRATION_VERIFICATION.md)에 남긴다. PR #27은 최종 문서 HEAD `46a77106e1bdceaa11e9001c32100250d1a82306`의 현행 체크 4개, Codex 지적 없음·미해결 스레드 0개 및 새 문서 3개 독립 검토 후 `bdcf91e4d3a98399503a0ba215b66920b0436c08`로 병합됐다. 네이티브 source `e84369c9f7f461a59c8d506b8b9efb2312297c03`의 17개 체크와는 구분한다. 그 기록 시점에는 교정 어댑터가 **TDD 구현 중이며 미완료**, 교정 네이티브 게이트는 미실행이었다. 이 기하 문서 초안들은 PR #27 병합 이후의 별도 문서 변경으로 유지한다.


현재 후속 기록: PR #29가 `a5ef72ed3f492857eadd4b1198dbba381312aa80`로 병합됐고, [교정 world-frame 가이드](STAGE7_MDV3_WORLD_FRAME.md)에 공식 source 실행 **43005087003의 4/4 교정 반복 동일성 PASS**를 기록한다. 독립 검증된 8개 새 프로세스·96개 실제 추론/완료 행·48개 일치 쌍이며, 별도 자동 main 실행 **43006858419**도 5/5 완료 후 원시 4/4·아카이브·전수 쌍 비교의 새 독립 검토가 명확하여 **별도 코호트로 수락**됐다. 소스+main의 16개 UUID/nonce·192개 실제 추론/완료 행에 대해 원래 코호트 내 비교는 96쌍이며, 추가 288개 전수 쌍 비교는 같은 자료를 재사용해 새 추론을 만들지 않는다. 이 소스 결과는 과거 도색 영상·기하 수치나 레거시 라벨을 수정하지 않으며, 주행 품질·전체 S자 완주·광학/렌더링 동등성·원본 게이트 PASS를 뜻하지 않는다.


## 후속 교정 확대 실행과 아직 열린 영상 검증

PR #31은 `cb1e7bfe698fe3bc3df9540eeb7dc2557e671300`으로 병합됐다.
별도 [교정 확대 기록](STAGE7_MDV3_WORLD_FRAME_EXPANSION.md)의 실행43012480495는
세 그룹 각4/4, 총12/12 **교정 반복 동일성**으로 독립 수락됐다(24개 새
프로세스,1472회 실제 추론/완료 행,736쌍). 긴 실행8개는 노선3개 중2개만
방문하고 최대 횡오차5.95397990659991–7.634517723985033m를 기록했다.
전체 S 완주·정확한 지속 추종·모델 품질이나 과거 도색 게이트의 재검증은 아니다.

후보 전용 paint V2는16회 모두 `xvfb-run` 파일 부재로 시작에 실패했다.
native 실행0/RGB 획득0이며, 기하 불일치를 측정한 결과가 아니다. 원래
실패 기록은 그대로 보존됐다. 별도 V3는16개 정상 native 프로세스/128회 RGB
획득을 완료했고 root strict 재집계와 새 전수 독립 증거 검토는 CLEAR/root 수락이다.
이는 증거 무결성 수락이며 전체 장면 기하 PASS가 아니다.
original은 장면2/4, candidate는1/4 게이트를 통과했다. candidate S_RL의
필수 focused 음성대조가 실패했고 양쪽 ramp는 집중 후보0–1개로 부족했다.
영상62 PASS/66 inconclusive는 반복 동일성 비율이나 전체 기하 PASS가 아니다.
[통합 검증 기록](STAGE7_INTEGRATION_VERIFICATION.md#candidate-specific-paint-v2-startup-failure-and-completed-v3-observations)은
그 실패와 남은 generic MD-V3 동작 연결, SIM/OpenCV 소스 차이를 구분한다.
과거 도색/기하 수치·실패·post hoc 기준과 scoring 금지는 그대로다.
