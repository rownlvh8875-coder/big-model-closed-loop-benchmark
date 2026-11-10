# Stage 7 — 실제 Python PSSM/Chase 카메라 콜백 실행 순서 검증

상태: 네이티브 실험 진행 중. 실차 시험 및 공식 주행모델 성능 순위 금지.

## MetaDrive 0.4.3 원본에서 직접 확인한 두 콜백

- metadrive/engine/core/pssm.py:43 — self.update를 Panda task manager에 등록. 80~101행에서 PSSM.update는 camera_rig.update 및 pssm_mvps shader input 변경을 실행.
- metadrive/engine/core/main_camera.py:36, 221~224, 311~320 — update main chase camera는 MainCamera._chase_task로 등록되며, run_task 상태에 따라 내부 카메라 이동을 건너뛸 수 있음.
- metadrive/component/sensors/base_camera.py:183 — 각 원본 RGB 카메라 perceive 호출은 engine.taskMgr.step을 한번 실행.
- 이전 native CI에서 PSSM.update와 update main chase camera는 모두 default chain/sort 0에 등록되었다. 이는 실제 콜백 진입 순서의 증거가 아니므로 이번에는 함수 코드 객체의 실제 Python 호출을 추적한다.

## 새 실행기·분리 제약

- bigbench/native_callback_profiler.py는 Python sys.setprofile에서 정확한 PSSM.update 및 MainCamera._chase_task 함수 코드 객체의 call/return 이벤트만 수집한다. 콜백 task 자체를 제거/재등록/교체하지 않는다.
- Python 메인 스레드 콜백 이벤트에만 적용되고, GPU 셰이더/그림자 패스의 실행 순서를 보여주는 도구는 아니다.
- sys.setprofile은 CPU 실행 시간을 추가로 소모한다. Panda 기본 시계의 wall-clock 동작과 RGB 변화에 영향을 줄 수 있으므로, 이를 비침습적·결정적 관찰이라고 주장하지 않는다.
- scripts/native_callback_order_trial.py는 완전히 별도 MetaDrive/Panda3D 프로세스에서 unprofiled(원래 task graph 및 profiling OFF)와 profiled(동일 task graph 및 profiler ON)를 구별하여 8프레임을 촬영한다.
- 2개 시드 20261109/20261110 × 2개 실제 S자 장면 s_curve_left_right/s_curve_right_left × 2개 스케줄 sequential perceive (2 task ticks/카메라 쌍) / paired taskMgr (1 tick/쌍) = 8개 matrix job, 각각 2개 독립 프로세스.
- MetaDrive 0.4.3 SHA 검증 공식 자산 사용. 원본 964×604 road/wide RGB를 순서대로 수집, 모델 512×256 RGB 및 I420 처리와 변경 위치/해시는 전체 렌더 후에 산출.
- 태스크 세 개 PSSM.update / update main chase camera / igLoop가 계속 등록돼 있는지 전후 검사. 각 조건에서 +2m 카메라 이동 대조 양쪽 카메라 PASS, CPU 반복 readback 비트 일치, Panda frame count 타당성 필수.
- 테스트가 실행됐다고 actual order를 가정하지 않는다: Python profiler가 실제 call/return을 한 태스크 틱당 1회씩 정확하게 관측하지 못했다면 ERROR 또는 INCONCLUSIVE로 표시한다.
- scripts/compare_native_callback_order.py는 실제 raw call/return 이벤트를 다시 파싱해 콜백 선후를 결정하며, 무계측 대조와 source RGB/I420 해시, CPU 시간 차이도 별도로 보존한다.

## 검증과 종료 조건

- GitHub Actions workflow: .github/workflows/native-task-callback-order.yml. 공식 MetaDrive GPU 텍스처 extractTextureData 호출 없음. 원본 이미지 변조·pixel tolerance·반복 동일 영상 대체 없음.
- native CI가 성공하면 오직 해당 MetaDrive 0.4.3 CPU Python 콜백 실행 순서를 관측했다고 말할 수 있다. GPU draw 순서, 그림자 depth atlas의 실제 변경, PSSM 고유 근본 원인, 정식 모델 주행성능은 여전히 미증명.
- 이전 공식 SHA 고정 MD-V3 독립 신규 영상 원래 렌더링의 엄격 반복 일치는 0/4 FAIL. 7단계는 계속 진행 중이며 실차·CD210·Carrot MPC/Params·모델 주행성능 순위 산출은 금지한다.

네이티브 실측 8개 조합의 원본 JSON/URL과 호출 순서 수치는 GitHub CI 결과를 확인한 뒤 기재한다.

## 2026-11-10 실제 8/8 Native CI 검증 완료

원본 [MetaDrive Python callback order Actions #42819410983](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42819410983) — 8개 matrix job SUCCESS, 8개 원본 아티팩트 ZIP 모두 열어 확인. 각각 unprofiled + profiled **2개 독립 Python/MetaDrive/Panda/Xvfb 프로세스**를 실행했으므로 총 16개 네이티브 프로세스. 공식 MetaDrive-0.4.3 release assets SHA256 체크, 양 카메라 +2m pose 이동 양성대조, 원본 RGB 및 I420/CPU readback 검증을 포함한다.

**실제 Python 콜백 call/return 이벤트:** 8개 독립 profiled 프로세스에서 총 96개 taskMgr.step 틱 모두 PSSM.update call → return → MainCamera._chase_task call → return 순서를 확인했다. paired 스케줄은 4 조합×8틱=32/32, sequential 스케줄은 4 조합×16틱=64/64. Chase 콜백의 run_task flag는 96/96 entry에서 true였다. 이 결과는 **profiled CPU thread의 실제 Python callback 실행순서**이고 GPU shadow render pass 순서를 증명하지는 않는다.

### 별도 프로세스 무계측 대비 원본 카메라/I420 비교

8프레임 중 unprofiled와 profiled 두 독립 프로세스의 동일 step I420 SHA 일치 수, 그리고 각 프로세스 워밍업 2프레임 이후 I420 SHA 고유 개수.

| seed | scenario | camera capture | observed callback ticks | unprofiled I420 unique | profiled I420 unique | cross-process matching I420 steps |
|---|---|---|---:|---:|---:|---:|
| 20261109 | s_curve_left_right | paired | 8 | 2 | 2 | 7/8 |
| 20261109 | s_curve_left_right | sequential | 16 | 1 | 2 | 7/8 |
| 20261109 | s_curve_right_left | paired | 8 | 1 | 1 | 8/8 |
| 20261109 | s_curve_right_left | sequential | 16 | 3 | 2 | 4/8 |
| 20261110 | s_curve_left_right | paired | 8 | 2 | 2 | 7/8 |
| 20261110 | s_curve_left_right | sequential | 16 | 1 | 1 | 8/8 |
| 20261110 | s_curve_right_left | paired | 8 | 3 | 2 | 3/8 |
| 20261110 | s_curve_right_left | sequential | 16 | 2 | 3 | 3/8 |

**8개 중 6개 조합의 이미지 시계열은 일부 step에서 불일치**, 2개 조합은 전체 8프레임 I420 SHA가 동일했다. 일부 조합은 profiler가 켜진 후후반 SHA 고유 개수가 증가하고, 일부는 감소했다. 이것은 두 프로세스가 독립 실행된 결과이므로 **차이의 원인을 sys.setprofile overhead 하나로 단정하거나 콜백 계측이 시뮬레이터를 원래대로 재현한다는 증거가 아니다**. 실제 callback Python 실행순서는 이번 profiled 96틱에서만 확인됐다.

### 의미와 다음 하드 게이트

1. PSSM.update가 그림자 rig MVP를 갱신하고 나서 MainCamera._chase_task가 실행됐다는 사실은 확인됐다. 그러나 실제 camera pose가 chase 콜백에서 달라졌는지, MVP가 전 프레임 자세를 사용했는지, GPU 그림자 atlas가 달라졌는지는 확인하지 않았다.
2. MainCamera.run_task flag가 true였다는 것은 조기 반환 조건을 통과했다는 뜻일 뿐 해당 함수가 매 틱 카메라 위치를 변경했다고 보장하지 않는다.
3. 다음 단계는 **콜백 진입·반환 시 main camera pose 및 PSSM numeric MVP의 일치 관계**를 추가 별도 실험에서 확인하되, timing overhead를 profiling-off 대조와 분리해 분석한다.
4. 이번 관측은 고정 세계 자세에서의 MetaDrive render/task 진단이다. 실제 MD-V3 신규 카메라 영상 독립 ONNX 폐루프 exact repeatability는 여전히 **0/4 PASS**, 7단계 **미완료**. 실차·CD210·Carrot MPC/Params 폴백, 공식 주행성능 모델 순위는 금지한다.
