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
