# MetaDrive 3D 차선 경계 ↔ 카메라 영상 픽셀 재투영 검증

**상태 (2026-11-11 재확인):** 직선 가상도로의 2026-11-09 네이티브 픽셀 정합성 진단 PASS. 후속 S자/램프 4종도 별도의 수정된 진단 기준으로 PASS했으며 [곡선 기록](METADRIVE_CURVED_LANE_AUDIT.md)에 실패 이력과 함께 남긴다.

**목표:** 가상도로의 실제 MetaDrive 차선 경계 좌표가 모델 입력용 영상의 렌더링된 차선 도색 픽셀과 일치하는지 별도 영상 검출로 확인한다.

**프로젝트 범위:** 합성 가상환경만 사용. 실차 테스트, 차량별 물리 파라미터, CD210, Carrot Params 및 실제 차량 CAN 연결은 없다. 이 단계는 ONNX 주행 성능 평가가 아니다.

## 근거와 구현

- MetaDrive [`StraightLane.position()` / `width_at()`](https://github.com/metadriverse/metadrive/blob/main/metadrive/component/lane/straight_lane.py#L60-L74)은 도로의 2D 중심 및 횡좌표를 제공한다.
- MetaDrive [`PGBlock._construct_lane_line_in_block()`](https://github.com/metadriverse/metadrive/blob/main/metadrive/component/pgblock/pg_block.py#L330-L358)은 차선폭의 `-1/2` 및 `+1/2` 지점에 실제 차선 표시를 만든다. 중복 경계에는 중복 도색하지 않으며 `BROKEN`은 끊어진 선이다.
- MetaDrive [`coordinates_shift.py`](https://github.com/metadriverse/metadrive/blob/main/metadrive/utils/coordinates_shift.py)는 현행 MetaDrive 세계 X/Y와 Panda3D 세계 X/Y를 동일하게 취급한다. 단, **카메라가 차량 노드에 매달린 상대 위치·방향**은 Panda3D에서 실제로 적용된 노드 변환을 사용한다.
- [`BaseCamera.perceive()`](https://github.com/metadriverse/metadrive/blob/main/metadrive/component/sensors/base_camera.py#L132-L206)는 캡처 시 임시로 카메라를 대여하고 촬영 후 원래 부모·자세로 되돌린다. 본 검증은 동일한 상대 자세를 재적용하여 **실제 Panda3D 카메라 노드에 대한 세계→카메라 변환**을 얻는다.
- 기존 [`optical_calibration.py`](../bigbench/optical_calibration.py)는 소스 이미지 픽셀을 공식 zero-distortion 핀홀 카메라 규약의 512×256 모델 캔버스로 변환한다.

## 두 독립 증거

1. **3D 정답 경로:** MetaDrive 도로/차선 API에서 해당 차선의 실제 좌·우 도색 경계 좌표를 획득한다. 차선 중심을 임의로 만들지 않는다.
2. **2D 관측 영상:** 엔진이 렌더링한 RGB 이미지에서 흰색·노란색 차선 표시를 **별도 영상 검출**한다. 3D 투영 결과를 이미지에 덧칠한 것만으로 일치 판정을 하지 않는다.

각 3D 지점은 실제 Panda3D 노드 변환으로 카메라 좌표(+Y 전방)로 변환하고, 모델 핀홀 워프를 거쳐 모델용 영상의 예상 픽셀로 계산한다. 영상 자체에서 검출된 가까운 도색 픽셀과의 거리를 픽셀 단위로 기록한다.

## 의도적인 오정렬 검사

예상 픽셀 좌표를 인위적으로 **27px 이동**시킨 음성 대조도 함께 측정한다. 이 대조군이 정상 예측과 비슷한 검출률을 보인다면 RGB 기반 검사가 너무 느슨하거나 차선이 아닌 다른 물체를 잘못 검출한 것일 수 있어 성공 판정하지 않는다.

## 실행

MetaDrive 0.4.3과 대응 렌더링 자산을 설치한 Linux/Xvfb 환경:

```bash
xvfb-run -a python -m scripts.metadrive_lane_audit --out output/metadrive-lanes
```

미확정 결과까지 저장하고 분석하려면:

```bash
xvfb-run -a python -m scripts.metadrive_lane_audit --allow-inconclusive --out output/metadrive-lanes
```

GitHub Actions: [metadrive-lane-reprojection.yml](../.github/workflows/metadrive-lane-reprojection.yml) (코드 변경 또는 수동 실행).

### 산출물

- `lane_reprojection_report.json`: 도로 출처, 카메라별 랜드마크 3D 좌표, 예상 픽셀, 영상에서 검출된 픽셀, 오차, 음성대조 수치.
- `road_baseline.png` / `wide_baseline.png` 및 `*_shifted.png`: 실제 MetaDrive 렌더링 후 광학 변환된 모델용 RGB.
- `*_reprojection.png`: **빨간 원=3D 좌표에서 투영한 예상 위치, 초록 점=RGB에서 별도로 관측한 도색 위치**, 노란 선=픽셀 잔차.

## 실제 MetaDrive 0.4.3 검증 결과 (2026-11-09)

**결과:** `PASS_VIRTUAL_METADRIVE_LANE_PIXEL_ALIGNMENT_DIAGNOSTIC`. [GitHub Actions run 42573166387](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42573166387)에서 실제 렌더링·추출·픽셀 비교 게이트를 통과했다. 관련 [검증 아티팩트 13653847508](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42573166387/artifacts/13653847508)는 9개 파일(모델 캔버스 4장, 검증 오버레이 4장, JSON 1개)로 구성된다.

- 검증 코드 커밋: [`2658e000`](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/commit/2658e000e9eb6b3c5be3179ee721dd6319668ce4)
- 엔진/환경: MetaDrive **0.4.3**, 공식 자산 파일 SHA256 `4f0da9f5143a1258131c5b55f77bdf170c0f9bce8a9f18dd41b3678df779eac9`, GitHub Actions Ubuntu/Xvfb + CPU OpenGL
- 테스트 도로: MetaDrive 맵 블록 `S`(직선), **실제 도로 네트워크 전체**에서 3D 차선 도색 경계 223개를 추출. 시작 차로만 탐색하는 초기 구현은 진단 가능 도색 좌표를 찾지 못해 실패했으며, 전체 도로 네트워크 표본화로 수정해 재시험했다.
- 카메라: 일반(road)·광각(wide), **카메라 기본 위치와 가상 이동 후 위치** 2개 자세에서 각각 촬영

| 가상 카메라 자세 | 카메라 | 모델 영상 내 예상 3D 차선 점 | RGB 도색과 매칭 | 매칭률 | 오차 중앙값(px) | 오차 90백분위(px) | 27px 오정렬 대조군 매칭률 |
|---|---|---:|---:|---:|---:|---:|---:|
| 최초 | 일반 | 154 | 142 | 92.21% | **0.765** | 4.938 | 41.56% |
| 최초 | 광각 | 179 | 156 | 87.15% | **1.467** | 6.858 | 41.90% |
| 이동 후 | 일반 | 155 | 155 | 100% | **0.872** | 3.675 | 37.42% |
| 이동 후 | 광각 | 179 | 128 | 71.51% | **0.920** | 4.398 | 39.66% |

**해석:** 3D 도로 좌표에서 계산한 차선 표시의 투영 위치가, 이번 MetaDrive 실제 RGB 영상에서 별도 검출한 도색 픽셀과 상당히 가깝다. 인위적인 오정렬에서는 검출률이 감소하여 픽셀 검사에 위치 판별력이 있음을 확인했다. 그러나 이는 **이번 직선 가상도로·두 카메라 자세·밝기/색 임계값 기반 검사에서의 결과**다. 미검출 도색, 잘못 검출된 비도로 픽셀, 특정 영상 조도에 따른 편향까지 배제하지 않는다.

**후속 확인:** S자/램프의 별도 [최종 실행 42578810503](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42578810503)은 수정된 대상 곡선 게이트에서 4/4 PASS다. 최초 0/4, 두 번째 3/4 이후 기준을 변경한 결과이므로 본 직선의 단일 +27 px 대조와 동일한 실험으로 합치지 않는다.

**미검증:** 독립 3D 레이저/시맨틱 세그멘테이션 정답, 실제 comma 렌즈 왜곡·외부 파라미터·영상 도메인 동등성, 생산 NV12 전처리 동등성, 대형모델 주행성능 순위. 이 직선 시험은 ONNX 추론을 수행하지 않았으며 **`model_score_allowed=false`**를 유지한다.

## 시험 상태와 신뢰도

- 순수 Python 합성 테스트는 3D→픽셀 투영의 좌표계, 도색 검출 및 의도적인 위치 오차에 대한 자동 검증을 수행한다.
- **MetaDrive 0.4.3 실제 렌더링 검증은 위 실행기록과 아티팩트로 확인됐다.** 직선 가상도로의 현재 환경에 한정된 결과이며, 새 시나리오는 다시 독립 검증해야 한다.
- 실도로 카메라 렌즈 왜곡, 광각 피쉬아이, 실차 센서 노출/색감, 3D 도로 높이 및 주변 장면에 따른 검출 오차까지 제거된 것은 아니다.
- 영상 도색 검출은 위양성/위음성을 일으킬 수 있다. 명확한 근거가 부족한 경우 `INCONCLUSIVE_OR_MISMATCH`로 남기고, 모델의 종/횡 성능 점수는 생성하지 않는다.


## 이 직선 게이트의 정확한 계약과 증거

원래 직선 게이트는 투영점 ≥8, RGB 매칭 ≥5, 매칭률 ≥0.45, 매칭점 잔차 중앙값 ≤7 px 및 +27 px 대조 매칭률이 양성보다 낮을 것을 요구했다. 후속 곡선 게이트의 0.15 매칭률 감소와 70% 후보 유지 요건은 이 직선 실행에 소급 적용하지 않는다. seed `20261109` 하나, `S` 직선 지도, 차량 노드에 상대적으로 대여한 카메라 두 자세의 road/wide 총 4장에 한정된 결과다.

| Run | Source HEAD | Artifact ID | ZIP bytes | ZIP SHA256 |
|---|---|---:|---:|---|
| [42573166387](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42573166387) | `2658e000e9eb6b3c5be3179ee721dd6319668ce4` | 13653847508 | 1510224 | `ba1345f6b53f007b10317ca9f2be5b39c137349cdaa0d74ab753c8e5c4da7a73` |

2026-11-11 API ZIP SHA256/바이트 수/안전 경로와 원본 9개 멤버를 확인했다. 원래 함수로 실제 4개 모델 캔버스 PNG를 재검산하여 매칭 수, 검출 픽셀 좌표, 음성대조 매칭률 및 PASS 판정을 그대로 재현했다. 모든 과거 도색 영상 52장 중 부동소수점 잔차의 최대 차이는 `1.7763568394002505e-15` px다. 전체 보고서가 바이트 동일하다는 주장이 아니며 모델의 엄격한 바이트 비교 게이트를 완화하지 않는다.

무시되는 `output/stage7-geometry-integration-audit/`에 원본 ZIP/PNG/JSON, API 메타데이터, 전체 SHA256 원장, 원래 소스와 순수 재검산이 있다. [통합 검증 기록](STAGE7_INTEGRATION_VERIFICATION.md)은 전체 7개 아카이브와 각 게이트의 한계를 묶는다. 이 재검산은 저장된 투영점을 이용하며 원래 지도나 Panda 카메라 변환을 새로 생성하지 않았다.

현행 투영·핀홀 코드가 최종 과거 소스와 바이트 동일하더라도, 이 과거 영상은 이후 `feedback_both`/unsorted 후보로 촬영한 것이 아니다. 후보 전용 차선 도색 게이트, 전역 렌더링/실물 광학 동등성, 모델 점수를 새로 확인한 결과로 사용하지 않는다.


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
