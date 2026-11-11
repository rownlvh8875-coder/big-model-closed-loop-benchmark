# MetaDrive S자 곡선·진입/진출 램프 3D 차선 ↔ RGB 재투영 진단

상태 (2026-11-11 증거 재확인): **2026-11-09 네이티브 가상 차선 픽셀 진단 4/4 PASS**. 최초 0/4 및 두 번째 3/4 기록은 그대로 보존한다. 최종 게이트는 앞선 실패를 본 뒤 변경한 진단 기준이며, 사전 등록된 독립 홀드아웃 검증이 아니다. 실차 테스트 0회, 차량별 제어기·동역학·CD210 제외.

## 기존 직선 검증의 한계

직전 직선 블록 `S`의 재투영은 실제 MetaDrive RGB와 지도 선을 비교했지만, 연속 곡률 반전 및 진입/진출 램프의 시야에서 같은 결과를 보장하지 않는다. **이번 단계는 차선 중심주행 성능시험이 아니라 가상도로 정답 경계가 영상의 실제 도색과 같은 위치를 가리키는지** 검사하는 사전조건이다.

## 구현과 검증 범위

- `bigbench/curved_lane_scenarios.py`: 공식 MetaDrive `C`, `r`, `R` 블록을 이용한 네 가지 시나리오 구성. S자 두 블록의 방향을 `0→1`, `1→0`으로 고정하고 실제 *forward circular lane*의 곡률 부호가 반대인지 검사한다. 반대방향 차선을 잘못 가져와 곡률 반전을 증명하지 못하도록 방지.
- `bigbench/metadrive_camera.py`: `NativeMetaDriveProvider`에 선택적 지도 설정을 전달. 기존 직선 호출에서는 이전 설정을 유지.
- `scripts/metadrive_curved_lane_audit.py`: 실제 MetaDrive 엔진의 월드 좌표 `(x,y,z)`에 카메라를 배치하고, 차선의 기하학적 접선 방향을 카메라 방향으로 사용. Panda3D 원점 기준 동일 카메라 자세에서 RGB 캡처와 3D 점 재투영 수행.
- `tests/test_curved_lane_scenarios.py`: 블록 ID, S자 방향 고정, 실제 전방 곡률 반전, 램프 좌표 부재시 차단, 세계→Panda 카메라 방향 단위시험.
- `.github/workflows/metadrive-curved-lanes.yml`: MetaDrive 0.4.3 공식 자산을 SHA256 검증한 뒤 Xvfb 실영상으로 네 시나리오 모두 검사. **정합성이 불분명한 경우 FAIL**, 합성 결과 아티팩트 업로드.

## 재투영 실험 계약

1. 공식 MetaDrive PGMap에 실제 곡선 블록 2개 또는 진입/진출 램프 블록을 생성한다.
2. 도로 네트워크의 `lane.position(s,±width_at(s)/2)`에서 3D 차선 도색 점을 추출한다.
3. 각 곡선 커넥터의 진행방향 헤딩을 따라, 물리 엔진에서 독립적인 월드 좌표 카메라를 배치한다.
4. 동일한 3D 위치·헤딩에서 road/wide MetaDrive RGB를 렌더하고 원본 기준 핀홀 모델 화면 512×256으로 워프한다.
5. 실제 영상의 흰색/노란색 도색 픽셀을 별도로 검출해 예측 픽셀 오차·매칭률을 기록한다.
6. 전체 장면의 차선뿐 아니라 **해당 곡선/램프 도로 자신의 차선 표시**가 실제로 검출됐는지 검사한다.
7. 여러 방향의 2D 위치 오정렬을 시험한다. 평행 차선에 잘못 매칭될 수 있으므로 27px 가로 이동 하나만으로 실패 판정을 내리지 않는다.
8. 7m 정도의 짧은 램프 커넥터는 가상 카메라를 접선 방향으로 상류 11m 이동해 곡선 표시가 충분히 보이도록 촬영하며, 보이는 지점이 충분하지 않으면 INCONCLUSIVE로 기록한다.

초기 진단 문턱값은 전체 영역과 대상 곡선 영역 모두 매칭률 및 오차 중앙값을 따로 평가하며, **임시 진단값**이지 최종 광학 정합성 보증이나 모델 주행 성능 점수가 아니다. 검출 픽셀이 부족하거나 잘못된 색상 임계값에 의해 누락되면 `INCONCLUSIVE_OR_MISMATCH`로 남는다.

## 실행

선택 의존성 `metadrive-simulator==0.4.3`, OpenCV, NumPy, Xvfb, 공식 MetaDrive 렌더링 자산이 필요하다.

```bash
python -m unittest discover -s tests -p 'test_curved_lane_scenarios.py' -v
xvfb-run -a python -m scripts.metadrive_curved_lane_audit \
  --scenarios s_curve_left_right s_curve_right_left in_ramp out_ramp \
  --seed 20261109 --strict --out output/metadrive-curved-lanes
```

산출물: 각 시나리오의 `curved_lane_report.json`, road/wide 실제 렌더링 PNG 및 오버레이, 종합 `curved_lane_summary.json`. 모델 가중치, 실주행 로그, CAN 자료 없음.

**확인된 범위:** 최종 [CI 42578810503](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42578810503)은 seed `20261109`, 4개 장면 × 2개 정적 자세 × road/wide의 16개 영상 진단을 통과했다. 아래의 최종 결과와 기준 변경 이력을 함께 읽어야 한다. 이 완료 기록은 이후 `feedback_both`/unsorted 후보 렌더러 전용 도색 게이트, 전역 렌더링 동등성 또는 실물 광학 검증을 뜻하지 않는다.

## 출처

- [MetaDrive Curve ID=C](https://github.com/metadriverse/metadrive/blob/main/metadrive/component/pgblock/curve.py)
- [MetaDrive InRamp ID=r / OutRamp ID=R](https://github.com/metadriverse/metadrive/blob/main/metadrive/component/pgblock/ramp.py)
- [PGMap deterministic block config](https://github.com/metadriverse/metadrive/blob/main/metadrive/component/map/pg_map.py)
- [MetaDrive lane position/width](https://github.com/metadriverse/metadrive/blob/main/metadrive/component/lane/abs_lane.py)
- [기존 직선 재투영 측정](METADRIVE_LANE_REPROJECTION.md)
- [7단계 개발 로드맵](ROADMAP_7_STAGES.md)

### 최초 실렌더링 진단 실패 및 보완(2026-11-09)

[CI 실행 42577333433](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42577333433)은 4개 사례 모두 INCONCLUSIVE로 끝났다. 그러나 S자 2종은 실제 서로 반대 부호의 양쪽 곡선이 생성됐고 관측 픽셀 오차 중앙값은 수 픽셀 이하였다. 실패 원인은 **인위적인 +27px 수평 이동이 평행 차선에 다시 일치하는 오정렬 대조** 및 **짧은 램프 커넥터 자체의 검출 후보가 0~1개뿐**인 문제였다. 해당 오류를 검증 프로토콜의 결함으로 확인하여 다중 방향 대조와 램프 상류 시점을 추가했다. 이 기록은 최종 결과가 나온 뒤에도 **0/4 INCONCLUSIVE**로 유지한다. 후속 실행은 아래에서 분리한다.

### 두 번째 CI 진단 및 초점 재설계

[CI 42578145473](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42578145473)에서는 네 종류 중 **우→좌 S자, 진입 램프, 진출 램프 3종 PASS**, 좌→우 S자 1종 INCONCLUSIVE였다. 후자의 두 번째 곡선 광각 카메라는 **곡선 자체의 3D 예측 점 72개가 72개 모두 RGB 도색과 매칭**되며 오차 중앙값 **0.423px**를 기록했다. 다만 도로 전역의 흰색·노란색 픽셀 밀도가 매우 높아 기존 27/38px 오정렬은 해당 곡선의 판별력을 측정하지 못했다. 따라서 전역 차선의 오정렬은 진단값으로 유지하되, **해당 물리적 곡선 자체의 오정렬 판별력을 필수 게이트**로 조정했다. 90px 이동 대조를 추가하되 가시 후보 70% 미만이 되면 그 대조는 기각한다. 이는 지표의 표본 선택 및 대조방식 변경이다. 이 두 번째 실행은 **3/4 PASS**로 유지하며, 최종 변경 기준과 재실행은 다음 절에서 분리한다.


## 최종 재실행과 변경된 게이트

[실행 42578810503](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42578810503), source `05b37dcf088824b2a08bbb26b628fd83134e12b3`은 **4/4 시나리오, 16/16 영상 진단 PASS**다. 직선 블록 `S`와 S자 장면을 구분한다. S자 장면은 실제 `C,C` 블록의 서로 반대인 전방 곡률을 검사하며, 진입/진출 램프는 실제 `r`/`R` 블록이다.

최종 표본은 seed `20261109` 한 개다. S자 카메라는 각 전방 원호의 진행률 `0.13`, `0.40`에 위치한다. 선택된 S 원호는 반경 55 m, 길이 약 45.116761 m다. 각 램프는 반경 40 m, 길이 약 6.981317 m의 서로 다른 원형 커넥터 두 개를 선택하고 각각 접선 방향으로 상류 11 m에서 촬영한다. 높이 1.22 m와 도색 좌표 z=0.018 m는 가상 소스 규약이다.

**게이트는 앞선 실패를 확인한 뒤 바뀌었다.** 두 번째 실행은 전역 음성대조의 판별력을 필수로 요구했고, 대상 곡선에서는 대상 또는 전역 판별력 중 하나를 허용했다. 최종 실행은 전역 판별력을 진단값으로 남기고 **대상 곡선 자체의 판별력을 필수**로 바꿨으며 ±90 px 대조를 추가했다. 따라서 최종 PASS를 최초 계약을 그대로 통과한 결과나 사전 등록된 홀드아웃 검증으로 해석하면 안 된다.

최종 문턱값은 다음과 같다.

- 전체 영역: 후보 ≥8, 매칭 ≥5, 매칭률 ≥0.45, 매칭된 점의 잔차 중앙값 ≤7 px.
- 대상 곡선/램프: 후보 ≥5, 매칭 ≥3, 매칭률 ≥0.35, 잔차 중앙값 ≤7 px 및 대상 음성대조 판별력.
- 음성대조 오프셋: `(27,0)`, `(-27,0)`, `(0,-50)`, `(-38,-37)`, `(38,37)`, `(90,0)`, `(-90,0)` px. 양성 표본의 70% 이상이 화면에 남는 대조만 적격이며, 그중 하나 이상에서 매칭률이 0.15 이상 감소해야 한다. 모든 대조가 실패해야 한다는 뜻은 아니다.

특히 좌→우 S자 `bend_2` wide의 **`global_negative_discriminating=false`는 그대로다**. 최종 대상 곡선은 72/72 매칭, 중앙값 0.422637 px이고, 적격 +90 px 대조는 71개 후보 중 46개 매칭(0.647887)으로 `focus_negative_discriminating=true`다. 이 대상 기준을 통과했으므로 전체 장면의 모든 음성대조가 판별력을 가진다고 주장하지 않는다.

| 시나리오 | 자세 | 카메라 | 전체 매칭/후보 | 대상 곡선 매칭/후보 | 대상 중앙값 px | 대상 P90 px | 최저 매칭률의 적격 대조 | 대조 후보 | 대조 매칭률 |
|---|---|---|---:|---:|---:|---:|---|---:|---:|
| `in_ramp` | `bend_1` | road | 197/267 | 30/30 | 0.535819 | 1.799281 | `[-38, -37]` | 30 | 0.166667 |
| `in_ramp` | `bend_1` | wide | 271/389 | 30/30 | 0.495057 | 1.172766 | `[-27, 0]` | 30 | 0.166667 |
| `in_ramp` | `bend_2` | road | 326/339 | 30/30 | 0.399258 | 0.508329 | `[90, 0]` | 30 | 0.500000 |
| `in_ramp` | `bend_2` | wide | 294/389 | 30/30 | 0.419943 | 0.652105 | `[27, 0]` | 30 | 0.500000 |
| `out_ramp` | `bend_1` | road | 321/321 | 30/30 | 0.399495 | 0.508675 | `[27, 0]` | 30 | 0.500000 |
| `out_ramp` | `bend_1` | wide | 356/400 | 30/30 | 0.420063 | 0.612883 | `[27, 0]` | 30 | 0.500000 |
| `out_ramp` | `bend_2` | road | 72/72 | 30/30 | 0.485250 | 0.994984 | `[-38, -37]` | 30 | 0.000000 |
| `out_ramp` | `bend_2` | wide | 129/150 | 30/30 | 0.455528 | 0.760004 | `[27, 0]` | 30 | 0.500000 |
| `s_curve_left_right` | `bend_1` | road | 88/88 | 88/88 | 0.516174 | 1.081733 | `[0, -50]` | 88 | 0.340909 |
| `s_curve_left_right` | `bend_1` | wide | 193/209 | 120/120 | 0.401546 | 0.702159 | `[38, 37]` | 108 | 0.175926 |
| `s_curve_left_right` | `bend_2` | road | 208/214 | 46/46 | 0.371225 | 0.522727 | `[0, -50]` | 46 | 0.804348 |
| `s_curve_left_right` | `bend_2` | wide | 278/416 | 72/72 | 0.422637 | 0.567462 | `[90, 0]` | 71 | 0.647887 |
| `s_curve_right_left` | `bend_1` | road | 168/175 | 60/60 | 0.472262 | 1.647966 | `[-90, 0]` | 58 | 0.344828 |
| `s_curve_right_left` | `bend_1` | wide | 279/424 | 121/121 | 0.508460 | 1.272775 | `[90, 0]` | 105 | 0.419048 |
| `s_curve_right_left` | `bend_2` | road | 75/75 | 65/65 | 0.717806 | 1.305302 | `[-38, -37]` | 51 | 0.490196 |
| `s_curve_right_left` | `bend_2` | wide | 278/303 | 75/75 | 0.478342 | 1.050896 | `[0, -50]` | 75 | 0.813333 |

## 원본 아카이브와 순수 재검산

세 곡선 실행의 API ZIP SHA256/크기/안전 경로 및 심볼릭 링크 부재를 확인했다. 실패 실행의 원본 PNG/JSON도 보존했다.

| Run | Source HEAD | Artifact ID | ZIP bytes | ZIP SHA256 |
|---|---|---:|---:|---|
| [42577333433](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42577333433) | `a241e69be98a4534126cfae19fe0d1c1aaf4ead0` | 13655294080 | 6484083 | `25c812b84294206c3e26ab80fc28a2d17fe04879bdf16c9e2801868028c3b1fa` |
| [42578145473](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42578145473) | `fca809788d875732cee7bbc5bf60a9bf9868cefd` | 13656033035 | 6546613 | `6e2cbc3f7b4ec07bb4988879cd23244787ce6b24d561c2ba320cab3e08e3c020` |
| [42578810503](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42578810503) | `05b37dcf088824b2a08bbb26b628fd83134e12b3` | 13656049008 | 6548415 | `528e2df31dee726166f4719a0ec6299f97cbfb27a6d5ed5cf83f786a0dbf8507` |

전체 7개 광학·직선·곡선·기하 아카이브 원장은 [통합 검증 기록](STAGE7_INTEGRATION_VERIFICATION.md)에 있다. 현재 감사 자료는 무시되는 `output/stage7-geometry-integration-audit/`에 있으며 `verified_archives.json`이 원본 ZIP과 각 멤버의 전체 SHA256/바이트 수를 기록한다.

2026-11-11 재검산은 **새 렌더링 없이** 각 과거 커밋의 원래 함수를 원본 PNG와 저장된 투영점에 적용했다. 곡선 48장과 직선 4장의 매칭 수·검출 픽셀 좌표·대조 매칭률·판정은 정확히 재현됐다. Euclidean/백분위 잔차의 부동소수점 차이는 최대 `1.7763568394002505e-15` px로 `recomputed.json`에 남긴다. 전체 JSON이 바이트 동일하다는 뜻이 아니며, 모델 반복 비교에 새 허용오차를 추가한 것도 아니다. 원본 Panda 카메라 노드나 지도를 재생성하지 않았으므로 이번 재검산이 새 기하 실험을 추가하지 않는다.

최종 감사 소스의 `lane_reprojection.py`, `optical_calibration.py`, `curved_lane_scenarios.py`, `metadrive_curved_lane_audit.py`는 확인 당시 현행 파일과 바이트 동일했다. 그러나 과거 PNG는 이후의 sampler/shadow-input/opaque-bin 후보 설정으로 촬영한 영상이 아니다. **후보 전용 도색 정합성 게이트와 전역 렌더러 동등성은 새로 통과하지 않았다.**

색 임계값 검출은 배경·연석 위양성, 도색 미검출과 가려짐을 완전히 배제하지 않는다. 잔차는 매칭된 점에 한정된다. 실물 렌즈 왜곡·장착 외부 파라미터·노출/색감·시간 동기, 생산 NV12 워프/색 변환 동등성, 모델 주행 성능이나 순위는 이 진단의 결과가 아니다. `driving_model_scoring_allowed=false`를 유지한다.


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
