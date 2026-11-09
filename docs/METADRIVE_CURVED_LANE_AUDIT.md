# MetaDrive S자 곡선·진입/진출 램프 3D 차선 ↔ RGB 재투영 진단

상태: **코드 구축 / GitHub Actions 실렌더링 검증 전** (2026-11-09). 실차 테스트 0회, 차량별 제어기·동역학·CD210 제외.

## 기존 직선 검증의 한계

직전 직선 블록 `S`의 재투영은 실제 MetaDrive RGB와 지도 선을 비교했지만, 연속 곡률 반전 및 진입/진출 램프의 시야에서 같은 결과를 보장하지 않는다. **이번 단계는 차선 중심주행 성능시험이 아니라 가상도로 정답 경계가 영상의 실제 도색과 같은 위치를 가리키는지** 검사하는 사전조건이다.

## 신규 코드

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
7. 예상 픽셀을 27px 인위적으로 이동시켜 정상 위치 대비 검출률이 낮아지는지도 확인한다.

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

**현재 상태의 명시적 한계:** 이 문서 작성 시점에 4개 시나리오의 실제 MetaDrive 실렌더링 게이트가 확인되지 않았다. GitHub Actions 결과를 조회하여 통과한 시나리오만 검증 완료로 표시해야 한다.

## 출처

- [MetaDrive Curve ID=C](https://github.com/metadriverse/metadrive/blob/main/metadrive/component/pgblock/curve.py)
- [MetaDrive InRamp ID=r / OutRamp ID=R](https://github.com/metadriverse/metadrive/blob/main/metadrive/component/pgblock/ramp.py)
- [PGMap deterministic block config](https://github.com/metadriverse/metadrive/blob/main/metadrive/component/map/pg_map.py)
- [MetaDrive lane position/width](https://github.com/metadriverse/metadrive/blob/main/metadrive/component/lane/abs_lane.py)
- [기존 직선 재투영 측정](METADRIVE_LANE_REPROJECTION.md)
- [7단계 개발 로드맵](ROADMAP_7_STAGES.md)
