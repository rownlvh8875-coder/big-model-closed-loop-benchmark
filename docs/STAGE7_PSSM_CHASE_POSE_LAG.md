# Stage 7 — PSSM 그림자 행렬과 Chase 카메라 WORLD pose의 콜백 경계 검증

기준: 2026-11-10. 상태: 실제 네이티브 시험 진행 중. **7단계 미완료, 공식 MD-V3 신영상 독립 폐루프 exact 반복재현성 미통과, 모델 순위 및 실차 제외**.

## 원본 MetaDrive 0.4.3 코드 직접 확인

- `metadrive/engine/core/pssm.py` 43행: `self.update`를 Panda task로 등록. 89~101행에서 `camera_rig.update(self.engine.camera,light_dir)`, CPU MVP 배열을 `pssm_mvps` shader 입력으로 전달, 카메라 rig film-size cache 초기화.
- `metadrive/engine/core/main_camera.py` 36, 221~273, 311~320행: `update main chase camera`는 `MainCamera._chase_task` 함수로 등록. `run_task=False`인 경우 early-return할 수 있으며 동작 중 카메라 위치/자세를 변경.
- `metadrive/component/sensors/base_camera.py` 179~183행: 각 MetaDrive RGB 카메라 `perceive` 호출은 해당 카메라를 이동한 뒤 `engine.taskMgr.step()`을 한 번 실행.
- [이전 네이티브 실제 콜백 순서 증거](STAGE7_NATIVE_CALLBACK_ORDER.md): 2 seed×2 S-curves×paired/sequential, 총 96/96 profiled task ticks에서 **PSSM.update call→return→MainCamera._chase_task call→return**. 등록 sort가 아니라 실제 Python 프로파일러 이벤트 기반.

## 실행기/대조군

- `bigbench/pssm_chase_pose_trace.py`: `sys.setprofile` 기반 함수 코드 객체 필터로 각 콜백 진입/종료의 `engine.camera.getPos/getHpr(engine.render)` WORLD pose와 `PSSM.camera_rig.get_mvp_array()` 숫자 4×4×split 배열 및 해시를 동시에 읽는다. GPU atlas depth texture를 읽거나 렌더링하지 않음.
- `scripts/native_pssm_chase_pose_trial.py`: 세 개 독립 프로세스를 실행한다. (1) `boundary_control`은 콜백 내부 프로파일링 없이 원본 taskMgr 및 WORLD pose 외부 시점만 관측; (2) `boundary_observed`는 동일한 원본 태스크를 유지한 채 콜백 경계에서 numeric WORLD pose/MVP를 관측; (3) `virtual_x_intervention`은 별도 **SIM ONLY** 가상 카메라에 3,5 프레임 직전 +2m X 오프셋을 의도적으로 적용한 상태에서 같은 프로파일링 수행. 개입 조건은 원래 장면과 다르며 어떤 ONNX 모델 입력으로도 대체 불가.
- 실험 매트릭스: 시드 20261109/20261110 × 실제 S자 좌→우/우→좌 × paired/sequential 카메라 캡처 = 8개. 각 세 가지 실험 arm은 **서로 독립적인 MetaDrive/Panda/Xvfb Python 프로세스**, 총 24개. MetaDrive 0.4.3 공식 에셋 크기·SHA256 검증.
- 각 프로세스에서 8프레임 촬영, 워밍업 2프레임의 원본 SHA는 보존하며 이후 프레임만 별도 요약. 원본 두 카메라 964×604 RGB, 모델 RGB 512×256, 모델 I420 `(2,6,128,256) uint8`를 기록. RGB difference와 I420 변환은 모든 프레임 촬영 이후 실행.
- 본질적인 **양성대조**: 각 arm의 로드/광각 이미지가 카메라 2m 이동에 실제로 반응해야 함. 개입 arm에서는 의도한 +2m 가상 카메라 WORLD pose가 실제 적용됐는지 별도 재측정. 원본 태스크 등록 상태가 바뀌거나 profiler raw callback call/return이 누락되면 오류.
- `scripts/aggregate_pssm_chase_pose.py`: 모델 입력 시각과 실제 Python callback 경계 및 행렬 관계를 검토. 단순 결론 레이블은 실제 기록된 원본 raw 이벤트를 다시 검증한 후에만 생성.

## 판정 기준과 절대 한계

- PSSM 진입 pose와 Chase 종료 pose의 차이가 **관측**되고, PSSM MVP가 PSSM 콜백 중 갱신된 경우 해당 가상 시뮬레이터에서의 순서·시차 후보를 평가할 근거가 된다. 단, 가상 카메라 조작 arm은 인위적 개입이므로 실제 무개입 장면에서 프레임 지연이 존재한다는 증거가 되지 않는다.
- 두 콜백의 CPU 실행 순서는 GPU 셰이더 draw/PSMM shadow atlas depth 업데이트의 실제 GPU 순서와 다르다. `extractTextureData(scene_tex)`는 이전 실험에서 캡처 후속 프레임을 교란했으므로 수행하지 않는다.
- `sys.setprofile`와 CPU MVP/WORLD pose 관찰 자체가 Panda wall-clock scheduling에 영향을 줄 수 있다. 프로파일링 OFF 프로세스와의 별도 RGB/I420 시계열 비교는 이 개입의 **상관성**만 보여준다.
- 본 시험의 GitHub Actions success는 코드/시뮬레이터 증거 수집 성공에 한정된다. 광학 동등성, 모델 안전성, 공식 신영상 폐루프 반복 PASS, 주행모델 순위가 아님.
- 실차/CAN/EPS/차종 물리/CD210 폴백/Carrot MPC·Params 사용 금지. 관련 코드를 호출하지 않는다.

## 실측 자료

[네이티브 CI](../.github/workflows/native-pssm-chase-pose-lag.yml)의 원본 아티팩트 8개와 각 arm의 raw JSON·`pose_boundary_comparison.json` 검증 이후 실제 수치·판정을 추가한다. 비실행 결과는 PASS로 기재하지 않는다.
