# Stage 7 — PSSM 그림자 행렬과 Chase 카메라 WORLD pose의 콜백 경계 검증

기준: 2026-11-10. 상태: **네이티브 8개 매트릭스 8/8 CI SUCCESS 및 원본 24개 프로세스 아티팩트 전수 검증 완료**. **7단계 미완료, 공식 MD-V3 신영상 독립 폐루프 exact 반복재현성 미통과, 모델 순위 및 실차 제외**.

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

## 2026-11-10 실제 실험 8/8 결과

[MetaDrive 네이티브 A/B CI #42822587924](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42822587924) **completed SUCCESS (8/8 jobs)**. MetaDrive 0.4.3 공식 wheel/자산 SHA256 검증, 서로 독립적인 프로세스 `boundary_control`/`boundary_observed`/`virtual_x_intervention` 총 **24개**, 모든 원본 JSON 8 ZIP 확인. 8프레임×2시드×2 S자×paired(1 tick)/sequential(2 ticks)의 실제 profiled CPU 콜백 총 **96틱**. 각 arm 양 카메라 +2m 영상 반응 및 같은 RAM buffer의 반복 CPU read bit-exact 검사 통과. 이 SUCCESS는 시뮬레이터 진단 자료 수집 성공이지 공식 ONNX 신영상 독립 반복성 PASS가 아니다.

### 실제 콜백 참조 시차: 초기 카메라 추적 + 인위적 개입

- **PSSM 콜백이 Chase보다 먼저 호출/반환: 96/96 ticks**. PSSM 시점의 numeric 그림자 MVP는 Chase에서 직접 변경되지 않았으며, 실측 장면에서는 메인 카메라가 Chase 콜백으로 움직인 **다음 태스크 틱**에 MVP 갱신이 관측됐다(8/8 조건). Chase `run_task` 플래그는 96/96개 실제 진입 이벤트에서 true.
- 시드 `20261109`: 초기 Chase 콜백에서 메인 카메라 WORLD 위치가 **0.595000m** 이동(주로 높이 Z=2.795000→3.390000m). Paired 촬영은 프레임 index 1의 이동→index 2의 PSSM MVP 변경. Sequential 촬영은 프레임 index 0의 두 번째 틱에서 이동→다음 프레임 index 1 첫 번째 틱에 MVP 변경. 같은 현상은 좌→우/우→좌 모두 관측됐다.
- 시드 `20261110`: 초기 Chase 콜백의 메인 카메라 위치 변화 약 **7.025242m**, Y=-3.5→+3.5m 및 Z=2.795000→3.390000m. 다음 태스크 틱 MVP 갱신 4/4 조건에서 확인.
- 가상 메인 카메라 X방향 +2m 개입: 8개 조합 각각 프레임 index 3과 5, 총 **16/16회**. 모든 경우 실제 `PSSM.update` 진입이 변경된 WORLD 좌표와 일치(0m 오차), 그 콜백에서 MVP가 바뀌었고, 뒤이어 Chase가 메인 카메라를 2m 이동해 되돌렸으며, Chase 콜백 내부에서는 MVP가 바뀌지 않았다.
- 이 결과로 **프로파일러로 관측한 MetaDrive 내부 CPU 행렬 계산이 Chase 갱신 전 메인 카메라 자세를 사용한다**는 점은 확인됐다. 하지만 고정 포즈에서는 후반부 Chase 이동이 없었고, 이 현상 하나로 시뮬레이터 미세 픽셀 흔들림의 원인을 확정하지 않는다. 원래 GPU 그림자 texel 결과는 측정하지 않았다.

### 실험별 전수 시계열 요약

아래 I420 고유 SHA 개수는 8프레임 중 최초 2프레임을 분리한 이후 프레임 기준. `비개입↔계측 같은 프레임`은 서로 **독립된 프로세스 두 개의 동일 인덱스 입력**이 비트 동일했던 횟수로, 특정 arm의 원인·성능 순위로 해석할 수 없다.

| Seed | S curve | Capture | PSSM before Chase | 원래 카메라 이동 (m) | 다음 틱 MVP 갱신 | +2m 개입 통과 | I420 고유 SHA (비개입 / 계측 / 가상 개입) | 비개입↔계측 같은 프레임 |
|---|---|---|---:|---:|---|---:|---|---:|
| 20261109 | Left→Right | paired | 8/8 | 0.595000 | YES | 2/2 | 2 / 1 / 2 | 7/8 |
| 20261109 | Left→Right | sequential | 16/16 | 0.595000 | YES | 2/2 | 1 / 2 / 3 | 5/8 |
| 20261109 | Right→Left | paired | 8/8 | 0.595000 | YES | 2/2 | 2 / 2 / 4 | 4/8 |
| 20261109 | Right→Left | sequential | 16/16 | 0.595000 | YES | 2/2 | 3 / 3 / 5 | 4/8 |
| 20261110 | Left→Right | paired | 8/8 | 7.025242 | YES | 2/2 | 2 / 2 / 3 | 5/8 |
| 20261110 | Left→Right | sequential | 16/16 | 7.025242 | YES | 2/2 | 2 / 2 / 3 | 6/8 |
| 20261110 | Right→Left | paired | 8/8 | 7.025242 | YES | 2/2 | 2 / 2 / 4 | 5/8 |
| 20261110 | Right→Left | sequential | 16/16 | 7.025242 | YES | 2/2 | 2 / 2 / 4 | 5/8 |

### 필수 한계 및 다음 게이트

- 원래 CPU 콜백 순서와 PSSM numeric MVP를 측정했으나, **GPU 그림자맵 패스/깊이 버퍼/표면 셰이더가 이 시차로 인해 실제 어떤 texel을 바꾸는지는 확인되지 않았다**. HDR `extractTextureData(scene_tex)`를 호출하면 렌더 갱신에 개입한다는 이전 증거가 있어 이번에는 해당 추출을 하지 않았다.
- `sys.setprofile`와 여러 WORLD pose/MVP 수치의 반복 CPU 조회는 벽시계 실행에 개입한다. 계측 OFF/ON 두 독립 프로세스의 I420 8프레임 시계열이 **8개 비교 모두 완전 일치하지 않았으므로**, 인위적인 CPU 계측이 없을 때도 동일한 시차/픽셀 변화가 정확히 반복된다고 주장할 수 없다. 하지만 무계측 환경에도 알려진 native 변동이 있으므로 그 원인을 profiler의 overhead 하나로 단정해서도 안 된다.
- +2m 가상 메인 카메라 변경은 **원래 그림자/카메라 렌더링 의미를 의도적으로 변경한 인과 분리 조건**이다. 이를 모델 재현성 개선의 운영 설정으로 채택하거나 MD-V3의 공식 입력 영상으로 사용하지 않는다.
- **다음 단계:** 원래 MetaDrive task 등록을 보존하는 조건에서 Chase 카메라 갱신 뒤 PSSM 카메라 rig 정합이 해상도·그림자 atlas·최종 RGB의 미세 흔들림에 미치는 영향을, GPU readback 개입을 통제하는 별도 A/B로 시험한다. 이후 원래 시뮬레이터 신규 프레임·공식 MD-V3 독립 ONNX 반복 게이트를 다시 평가한다.
- 7단계 미완료. 실차/CAN/CD210·Carrot MPC/Params·차종별 동역학, 공식 모델 성능 순위 산출 금지.
