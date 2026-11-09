# MetaDrive 3D 차선 경계 ↔ 카메라 영상 픽셀 재투영 검증

**목표:** 가상도로의 실제 MetaDrive 차선 경계 좌표가 모델 입력용 카메라 영상의 물리적인 차선 표시 픽셀과 일치하는지 독립적으로 확인한다.

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

## 시험 상태와 신뢰도

- 순수 Python 합성 테스트는 3D→픽셀 투영의 좌표계, 도색 검출 및 의도적인 위치 오차에 대한 자동 검증을 수행한다.
- **실제 MetaDrive를 실행한 결과는 GitHub Actions가 완료되고 아티팩트를 확인한 뒤에만** 기록한다.
- 실도로 카메라 렌즈 왜곡, 광각 피쉬아이, 실차 센서 노출/색감, 3D 도로 높이 및 주변 장면에 따른 검출 오차까지 제거된 것은 아니다.
- 영상 도색 검출은 위양성/위음성을 일으킬 수 있다. 명확한 근거가 부족한 경우 `INCONCLUSIVE_OR_MISMATCH`로 남기고, 모델의 종/횡 성능 점수는 생성하지 않는다.
