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
- 매 프레임 ClockObject.getFrameCount, getFrameTime, getRealTime, getDt 기록. **실제 네이티브 첫 시험에서 Panda 글로벌 frameCount는 순차 perceive +2, taskMgr.step 쌍 +1, graphicsFrame-only +1이었다.** graphicsFrame-only의 frameCount도 +1이므로 **글로벌 카운터 자체로 taskMgr 실행 여부를 판별할 수 없다.** taskMgr.step 호출 횟수(순차 2, 동시 task 1, graphicsFrame-only 0)는 검토된 캡처 함수의 호출 경로에서 따로 정의하고, 측정된 글로벌 frameCount와 혼동하지 않는다.
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


## 2026-11-10 첫 CI에서 확인된 카운터 해석 오류와 수정

[첫 실행 CI #42775954822](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42775954822)의 20261109 좌→우 S자 JSON 원본에서 순차 perceive 조건의 frameCount delta는 2/프레임, 공통 taskMgr.step은 1/프레임, **graphicsEngine.renderFrame() 직접 호출도 1/프레임**임을 확인했다. 당시 코드에서 graphicsFrame-only를 0으로 예상한 것이 잘못되어 이 조건은 INCONCLUSIVE로 남았고, 실행 성공으로 기록하지 않았다.

새 버전은 **Panda 글로벌 frame count(관측치)** 와 **taskMgr.step 호출 횟수(검토된 캡처 함수의 호출 계약)** 를 다른 필드로 저장한다. 예측이 관측값과 다르면 정상 판정하지 않으며, 원래 실험의 실패/취소 기록을 삭제하지 않는다. 그 밖의 네이티브 픽셀 위치 및 I420 변화는 재실행 CI에서 확인 후 기재한다.


## 2026-11-10 최종 네이티브 CI 측정 결과

실측 증거: [GitHub Actions #42776577784](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42776577784). 2개 시드 × 2종 S자 × 각각 4개 독립 프로세스 = 총 16개 MetaDrive 0.4.3/Panda/Xvfb 프로세스. **4/4 매트릭스 job SUCCESS**이며 원본 JSON과 집계 아티팩트 4개 모두 확보했다. 정상 완료는 관측 자료를 수집했다는 뜻이며 모델 성능 PASS가 아니다.

### 워밍업 이후 RGB·I420 실제 최대 변화

각 원본 road/wide는 964×604 RGB이고, I420은 (2,6,128,256) uint8. 아래 road/wide는 변경된 원본 RGB 픽셀 최대 수, I420은 모델 입력 변경 원소 최대 수다. 샘플은 각 조건 총 10프레임, 워밍업 2프레임을 별도 요약하되 원본 해시를 보존했다.

| 시드 | S자 | 원래 카메라별 순차 perceive (road/wide · I420) | 공통 taskMgr.step (road/wide · I420) | graphicsFrame 단독 (road/wide · I420) | PSSM.update 제거 taskMgr.step (road/wide · I420) |
|---|---|---|---|---|---|
| 20261109 | 좌→우 | 9/2 · 12 | 9/2 · 12 | 0/0 · 0 | 0/0 · 0 |
| 20261110 | 좌→우 | 9/2 · 12 | 9/2 · 12 | 0/0 · 0 | 0/0 · 0 |
| 20261109 | 우→좌 | 8/3 · 26 | 0/0 · 0 | 0/0 · 0 | 0/0 · 0 |
| 20261110 | 우→좌 | 8/3 · 26 | 0/3 · 26 | 0/0 · 0 | 0/0 · 0 |

모든 16개 프로세스에서 **road/wide 카메라 +2m 이동 양성 대조 PASS**, 동일 완료 프레임 CPU RAM 재읽기 3회 bit-exact PASS, 가상 차량 transform 불변, PSSM/igLoop 등록 여부 검증 PASS.

### 최초 변경 픽셀 실측

원본 센서 영상의 첫 변경 픽셀은 zero-based top-left (x,y) 기준:

- 좌→우 S자 순차 perceive와 공통 taskMgr.step: road **(22,343)**, wide **(210,322)**. 이번 두 시드 모두 해당 픽셀 위치에서 변경이 관측됐다.
- 우→좌 S자 순차 perceive: road **(901,312)**, wide **(590,304)**. 두 시드에서 동일한 첫 변경 좌표가 관측됐다.
- 우→좌 S자 공통 taskMgr.step: 시드 20261109은 road/wide 모두 워밍업 후 변경 없음, 시드 20261110은 road 변경 없음, wide **(590,304)** 포함 최대 3픽셀 변경.
- graphicsFrame-only와 이번 4개 PSSM 제거 조건은 변경 픽셀 0, I420 변경 원소 0. 단, 카메라 위치 이동에 실제 반응했으므로 stale frame 거짓 안정화는 관측되지 않았다.

### Panda 글로벌 clock 해석 정정

초기 CI #42775954822의 graphicsFrame-only 조건은 글로벌 frameCount +0을 잘못 기대하여 INCONCLUSIVE로 기록했다. 원본 JSON은 다음 실제 수치를 보여줬고, 최종 CI #42776577784에서도 재현됐다.

| 촬영 방식 | Panda 전역 frameCount 증가/카메라 쌍 | 검토된 Python 호출 경로에서 taskMgr.step 호출/카메라 쌍 |
|---|---:|---:|
| 순차 perceive | 2 | 2 |
| 동시 taskMgr.step | 1 | 1 |
| 동시 graphicsEngine.renderFrame | **1** | **0** |

Panda 글로벌 frameCount 자체는 taskMgr.step 호출 수가 아니다. clock frame count가 +1이어도 그래픽 프레임을 생성했을 뿐 scene task가 실행되었다는 의미는 아니다. 실제 taskMgr.step 호출 횟수는 검사된 기존 캡처 함수의 소스 코드에 근거한 **호출 경로 계약**이지 프레임 카운터에서 직접 측정한 수치가 아니다.

### 판단 범위와 남은 게이트

- 기본 taskMgr.step 또는 순차 perceive 경로의 작은 픽셀 차이는 일부 카메라/시드에서 유지됐고, 이번 4개 한정 조건에서는 PSSM 태스크 제거 시 안정화됐다. **다른 카메라 진행률 및 램프를 포함한 이전 16조건에서는 PSSM 제거 후에도 5조건에서 I420 차이가 남았으므로 보편적 안정화 방법이 아니다.**
- graphicsFrame-only와 PSSM-off는 원래 렌더 스케줄/그림자 의미론이 다르므로 공식 MD-V3 평가 영상으로 무조건 치환하지 않는다.
- 이 실험은 **고정 자세에서 같은 프로세스 내 여러 프레임을 비교**한다. 별도의 Python 프로세스에서 모델을 실제로 폐루프 실행하는 원래 재현성 게이트와 다르다.
- 각 프레임 CPU 복사, 시계 조회는 원래 벽시계 기반 실행에 일정한 계측 오버헤드를 유발할 수 있다. 이 차이만으로 특정 GPU shader, PSSM shadow atlas, RAM copy의 단독 결함을 확정하지 않는다.
- 다음 게이트: PSSM의 rig MVP 변화, 인접 graphics frame 상태, 고정 시계/태스크 순서의 영향을 비침습적으로 추가 분리하고 그 뒤 공식 MD-V3 신규 영상 독립 폐루프 반복 재실행. 실차 테스트·CD210/Carrot 폴백·모델 주행성능 순위 산출 금지, 7단계 **미완료**.
