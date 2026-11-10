# MetaDrive 원본 RGB 변경 픽셀 좌표와 Panda3D 렌더 틱 인과 분리

상태: 진단 코드·단위시험 구현, 네이티브 CI 실측 결과 확인 전.

## 이전 확인 사항

- 공식 MD-V3 독립 신규 영상 반복 검사 4개 조건 모두 엄격 비트 동일성 FAIL. 네 조건 모두 가장 이른 불일치는 MetaDrive 964×604 원본 RGB에서 관측되었으며, 3개 조건에서 실제 I420 모델 입력 변경보다 먼저 시작됐다.
- [공식 MD-V3 원본 센서 단계 분석](STAGE7_FIRST_IMAGE_BOUNDARY.md): 2개 시드 × 2개 S자 결과, 최초 원본 RGB 불일치 step 2/3/2/2. CPU 복사와 SHA 계산 자체가 벽시계 기반 렌더링에 영향을 줄 가능성 존재.
- [PSSM 다중 장면 진단](STAGE7_MULTISCENE_NATIVE_REPEAT.md): PSSM.update 제거 후에도 16조건 중 5조건에서 I420 불일치가 남았다.
- [HDR 계측 개입 조사](PSSM_HDR_TRACE.md): extractTextureData(scene_tex)가 해당 카메라의 후속 프레임 갱신에 영향을 준 사례가 있어 본 시험에서 GPU HDR texture extraction 금지.

## 시험 설계

구현: bigbench/native_pixel_clock.py, scripts/native_raw_pixel_clock.py, scripts/aggregate_native_pixel_clock.py.

- MetaDrive 0.4.3 공식 에셋 SHA256 고정, 시드 20261109와 20261110 × s_curve_left_right 및 s_curve_right_left 지도.
- 카메라 WORLD 위치는 MetaDrive 실제 차선 진행률 0.12, 높이 1.22m에서 계산한다.
- 고정 자세에서 원본 RGB 964×604×3 uint8를 워밍업 2프레임 포함 총 10프레임 촬영하고 원본 해시 보존.
- 각 시드·장면에서 4개 독립 Python/Xvfb/MetaDrive 프로세스: (1) 순차 perceive 기본 PSSM, (2) 동시 taskMgr.step 기본 PSSM, (3) 동시 graphicsEngine.renderFrame 기본 PSSM, (4) 동시 taskMgr.step에서 PSSM.update 하나만 제거.
- 촬영 사이 추가 GPU HDR 추출, GPU 렌더 틱, 모델 추론, 프레임 평균·필터·보간·기록 영상 재생 및 차량 제어 금지. 원본 RGB를 캡처 직후 복사하되 좌표/픽셀 차이 분석과 모델 RGB/I420 변환은 모든 촬영을 끝낸 뒤에 수행.
- 같은 완료 렌더 틱의 RTMCopyRam 반복 CPU 읽기 3회를 비트 동등성으로 확인. +2m 카메라 이동 양성대조가 RGB를 변화시키지 않으면 INCONCLUSIVE로 분리해 stale buffer가 거짓 안정화로 보이지 않게 한다.
- 매 프레임 ClockObject.getFrameCount, getFrameTime, getRealTime, getDt 값을 기록해 순차 perceive의 태스크 틱 2개, 동시 taskMgr.step 1개, graphicsFrame-only 0개를 구별.
- PSSM 제거와 graphicsFrame-only는 원본 렌더링과 시간 및 의미론이 다르므로 공식 ONNX 평가 기본값으로 적용 금지.

## 데이터 계약

- 변경 픽셀 좌표: top-left 0-based x=column, y=row. 전체 변경 픽셀 수, xyxy bounding box, 첫 변경 픽셀, 변경 RGB 값 최대 12개, 최대 채널 차이, 모든 원본 SHA256.
- 모델 입력 RGB: 촬영된 원본 배열에서 기존 512×256 렌즈 워프를 사후 계산해 변경 픽셀 영역 비교.
- 최종 I420: (2,6,128,256) uint8 입력의 변경 원소 수와 (camera,plane,row,col) 인덱스를 따로 기록. I420 요소 인덱스는 RGB 픽셀 좌표로 해석 금지.
- 첫 2프레임은 사후 warmup=2 요약에서만 구분하며 초기 차이는 원본에서 지우지 않는다.
- 값과 좌표가 어느 한 장면에서 같아도 ONNX 폐루프 재현성, 실차 광학 동등성이나 특정 shader 유일 원인을 증명하지 않는다.

## 결과 확인 기준

각 네이티브 시드·장면에서 taskMgr.step, graphicsFrame-only, 순차 perceive, PSSM-off의 원본 road/wide 변경 좌표/영역과 I420 변경 원소, 프레임 카운터/시간 차이를 비교한다. 정확한 실측 수치와 CI 실행 URL은 아티팩트 확보 후에만 기재한다.

7단계 미완료, 실차·CD210 폴백·Carrot MPC/Params·모델 간 공식 주행성능 순위 산출 금지 유지.
