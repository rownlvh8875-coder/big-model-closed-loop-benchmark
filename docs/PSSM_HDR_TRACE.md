# MetaDrive PSSM 그림자맵 → HDR 장면 → 최종 RGB → ONNX I420 추적

상태: 신규 계측 구현, 실제 네이티브 CI 결과 검증 전. 실차 시험 없음. 주행모델 성능 순위 산출 금지.

## MetaDrive 0.4.3 원본 확인

- metadrive/engine/core/pssm.py의 PSSM.update는 shadow camera rig를 갱신하고 pssm_mvps 셰이더 입력값을 변경한다.
- 동일 파일의 PSSM.create_pssm_buffer는 PSSMShadowMap이라는 depth texture를 만들어 RTM_bind_or_copy 방식으로 GPU 버퍼에 연결한다.
- metadrive/component/sensors/rgb_camera.py는 RGBCamera.scene_tex HDR 장면 텍스처를 FilterManager와 tonemap shader에 연결한다.
- metadrive/component/sensors/base_camera.py의 perceive는 카메라 위치를 바꿀 때 engine.taskMgr.step을 호출한다.
- 앞선 A/B 시험에서 PSSM.update 제거만으로 특정 시드/포즈의 워밍업 이후 RGB/I420 해시 불일치가 사라졌으나, 해당 조건이 원래 렌더링과 같다고 증명한 것은 아니다.

## 신규 실험 프로토콜

코드: scripts/metadrive_hdr_trace.py, scripts/aggregate_hdr_trace.py.
자동시험: .github/workflows/hdr-pssm-trace.yml.
단위시험: tests/test_hdr_trace.py.

1. MetaDrive 0.4.3과 공식 자산 SHA256을 고정하고, 독립 Python/Xvfb 프로세스를 실행한다. 실차·CAN·CD210·Carrot MPC 사용 없음.
2. 시드 20261109 및 20261110, WORLD 포즈 origin 및 shifted(+2m X 이동)를 각각 교차한다. 씬 조건은 기본 가상 차체 RGB만 숨긴 ego_hidden, 캡처는 양쪽 카메라에 공통 taskMgr.step 1회.
3. 각 조합에서 baseline, PSSM.update만 제거, update main chase camera만 제거한 세 프로세스를 구동한다. igLoop는 항상 유지한다. 프레임 6개 중 앞 2개는 별도 워밍업 요약에만 제외하고 원본 해시를 모두 보존한다.
4. 같은 렌더 틱에서 pssm camera rig MVP 행렬, PSSM depth atlas, 두 카메라 HDR scene_tex, 원시 road/wide RGB, 최종 모델 입력 I420(2,6,128,256)을 차례대로 계측한다. 그림자맵·HDR의 raw RAM 바이트 해시, 길이, 텍스처 포맷·타입을 기록한다.
5. 동일 GPU 렌더 뒤 CPU RGB를 3회 반복 읽어 비트 동일성 확인. 끝나면 카메라 +2m 추가 이동으로 로드/와이드 양성 대조 수행.
6. 매 조건 후반 프레임의 SHA256 및 changed byte count를 산출하고, 독립 프로세스의 동일 인덱스 프레임 해시를 맞춰 비교한다. 원인 단정 및 모델 순위 산출은 금지한다.

## 엄격한 한계

- GPU 텍스처 바이트 차이 수를 픽셀 차이 수라고 해석하지 않는다. HDR float/half 포맷의 정밀한 공간 좌표 차이 비교는 후속 별도 검증 대상이다.
- extractTextureData는 새로운 렌더 틱을 발생시키지 않지만 GPU→CPU 동기화 등 이후 렌더 타이밍에 영향을 줄 수 있다. 무계측 기존 렌더링과 의미론적 동등성은 미확인이다.
- GPU 텍스처 획득 실패, 포맷 변경, 카메라 이동 양성 대조 실패, 태스크 제거 불일치는 ERROR/INCONCLUSIVE를 유지한다. 안정성 0 또는 성공으로 조작하지 않는다.
- 이번 A/B는 그림자 업데이트와 바이트 변화를 분리한 관측자료다. PSSM shader/그림자 패스 유일 원인의 증명은 아니다.
- 공식 대형 MD-V3/Light Speed 2 ONNX의 매 스텝 새 영상 반복 폐루프는 별도의 필수 게이트이며 미검증이다.

## 실행 결과 기록

- GitHub Actions: 새 워크플로의 성공/실패 및 아티팩트 확인 후 구체적 실행번호와 실제 수치를 이 문서에 별도 기록한다.
- 이전 단계 원인 분리: docs/METADRIVE_RENDER_CAUSALITY.md.
- 현재 개발 로드맵: docs/ROADMAP_7_STAGES.md.

신규 HDR 추출 자체가 실패할 경우 CI 실패를 보존하고 기능 제한으로 공개한다. 실패를 모델 성능 PASS로 승격하지 않는다.


## 2026-11-10 첫 네이티브 검증 결과 — INCONCLUSIVE

[첫 GPU 프레임 계측 GitHub Actions #42766327307](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42766327307)은 매트릭스 4조건 모두 진단 실패로 기록했다. 독립 JSON 아티팩트는 각 조건별 보존했다.

- 단위시험 6개는 PASS였지만, 원본 PSSM camera rig가 반환한 UnalignedLMatrix4f 객체에 getCell()을 직접 호출하여 모든 PSSM 행렬 추출이 UNAVAILABLE로 기록됐다. 정상 LMatrix4f로 변환하여 셀을 읽도록 코드를 수정했다.
- Depth atlas와 각 카메라 HDR scene_tex의 GPU 바이트 추출은 관측 JSON에서 EXTRACTED였다.
- **중대한 양성 대조 실패:** 매 프레임 GPU 추출을 수행한 실험에서 마지막 카메라 +2m 이동 뒤에도 road/wide RGB가 달라지지 않았다. 같은 시드의 과거 무추출 A/B [#42759149254](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42759149254)는 양쪽 카메라 이동 반응 PASS. 현재 결과는 GPU 추출의 개입 가능성을 시사하지만 두 시험은 프레임 수 등 조건도 달라 유일 원인이라고 단정할 수 없다.
- 따라서 신규 실험의 RGB/HDR 일치 해시를 안정화 성공이나 렌더링 동등성으로 **절대 해석하지 않는다**. 다음 실험에는 GPU 추출 **이전**과 **이후** 각각 카메라 이동 양성 대조를 남기도록 했다.
- 이 단계는 모델 출력이나 차량 제어 평가가 아닌 **실험 계측 경로 검증**이며 7단계 미완료 상태를 유지한다.



## 2026-11-10 2차 검증 결과 — GPU 계측 개입 여부 분리

[네이티브 run #42767017309](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42767017309)의 모든 매트릭스 결과(2시드 × 2포즈 × baseline/PSSM-off/chase-off = 12조건)를 JSON 아티팩트로 검증했다.

- 각 12조건에서 GPU 추출 이전 +2m 이동 양성 대조는 road/wide 모두 true.
- 각 12조건에서 **매 프레임 GPU 추출을 수행한 이후** +2m 이동 양성 대조는 road/wide 모두 false.
- PSSM 행렬 자료형 호환 문제는 LMatrix4f 변환으로 해결돼 행렬·그림자맵·HDR 단계가 EXTRACTED로 기록됐다.
- 관측된 RGB/I420 비트 일치를 재현성 증거로 사용할 수 없다. 매 프레임 GPU 텍스처 추출이 이후 카메라 영상 갱신에 영향을 주는 강한 증거지만, 그림자맵·road HDR·wide HDR 중 구체적 호출과 원인 메커니즘은 미분리다.
- 위 12조건의 원본 데이터는 CI에서 전부 INCONCLUSIVE로 보존됐고 모델 성능 PASS·순위는 계속 금지한다.

## 다음 검증: GPU 추출 호출별 독립 대조

신규 [.github/workflows/gpu-probe-interference.yml](../.github/workflows/gpu-probe-interference.yml)은 각 시드의 origin 고정 pose에서 별도 프로세스 5조건을 수행한다.

- none: PSSM 숫자 행렬만 계측, **GPU texture extraction 0회**
- pssm_depth: 그림자 atlas만 매 프레임 추출
- road_hdr: 일반 카메라 HDR만 매 프레임 추출
- wide_hdr: 광각 HDR만 매 프레임 추출
- all: 세 GPU 텍스처를 매 프레임 모두 추출

모두 GPU 추출 전·후 카메라 +2m 이동 검사를 실시한다. no-GPU 대조군의 두 양성 대조가 PASS하지 않거나 요청한 stage texture가 추출되지 않으면 집계 실패. 반대로 특정 추출에서 영상 갱신 중단 현상이 발생하면 **DIAGNOSTIC OBSERVED**로 기록한다. 이는 결함 발생을 계측한 성공일 뿐 정식 시뮬레이터·ONNX 성능 PASS와 무관하다.

기존 모든 텍스처를 한 틱에서 읽는 workflow는 반복적인 거짓 재현성 주장과 CI 리소스 소모를 막기 위해 workflow_dispatch 수동 실행 전용으로 전환했다. 본 단계의 GPU 계측은 반드시 모델 평가 파이프라인과 분리한다.


## 2026-11-10 독립 GPU 호출별 추출 결과 (원본 아티팩트 근거, CI 집계 수정 중)

[첫 분리 실험 Actions #42767653990](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42767653990)의 프로세스별 JSON에서 원본 카메라가 +2m 이동에 반응하는지를 확인했다. 모든 조건의 사전 양성 대조는 road/wide 모두 True. 다음은 **GPU 추출 이후** 반응 관측값이다.

| 시드 | GPU 추출 | road 카메라 반응 | wide 카메라 반응 | 해석 |
|---|---|---|---|---|
| 20261109 | none | True | True | 정상 무추출 대조 |
| 20261109 | pssm_depth | True | True | 그림자맵만 추출해도 반응 유지 |
| 20261109 | road_hdr | **False** | True | road HDR 추출 후 road만 응답 손실 |
| 20261109 | wide_hdr | True | **False** | wide HDR 추출 후 wide만 응답 손실 |
| 20261110 | none | True | True | 정상 무추출 대조 |
| 20261110 | pssm_depth | True | True | 그림자맵만 추출해도 반응 유지 |
| 20261110 | road_hdr | **False** | True | road HDR 추출 후 road만 응답 손실 |
| 20261110 | wide_hdr | True | **False** | wide HDR 추출 후 wide만 응답 손실 |
| 20261110 | all | **False** | **False** | 양쪽 HDR 추출 후 양쪽 응답 손실 |

20261109 시드의 all 원시 JSON은 초기 CI가 xvfb-run 종료 정리 시 exit 5를 반환해 실행되지 않았다. 이 행을 추정해 채우지 않으며 재실행 시 다시 확인해야 한다.

**판단:** 정상적인 no-probe 이미지와 PSSM depth atlas 추출 이후 이미지는 다음 카메라 위치 변화에 반응한 반면, HDR scene_tex를 extractTextureData()로 읽은 카메라만 다음 RGB 출력이 이동에 반응하지 않았다. 따라서 **GPU 계측 API가 대상 카메라 렌더 경로에 개입한다는 강한 실험적 근거**를 확보했다. 이 관측은 그림자 업데이트 PSSM.update가 원래 작은 RGB 드리프트를 유발한 정확한 메커니즘을 설명하지 않는다.

초기 집계기가 road/wide 반응이 반드시 동시에 True 또는 False라고 가정해 선택적 개입을 집계 오류로 취급한 부분을 수정했다. 이후 집계는 카메라별 불리언을 별도 보존하고, 예외 처리로 진단 FAIL을 PASS로 바꾸지 않는다. GPU 추출이 없는 원본 경로와 공식 ONNX의 매 프레임 폐루프 반복 재현성은 **여전히 미완료**.


## 제3차: 마지막 프레임에서만 GPU 추출 (원본 시계열 교란 억제)

[신규 terminal-only native workflow](../.github/workflows/terminal-hdr-trace.yml)는 프레임 사이에 GPU texture extraction을 절대 수행하지 않고, **최종 RGB/I420 시계열을 모두 개인 메모리로 복사한 이후** 마지막 완료된 렌더 틱에서만 GPU 텍스처를 한 번씩 읽도록 설계했다.

- seed 20261109 및 20261110, 동일 WORLD 원점 pose, 프레임 4 및 6을 각각 독립 프로세스로 시험한다.
- baseline_no_gpu (GPU 추출 0회) / baseline_terminal (원본 PSSM + 종료 시점에서만 추출) / shadow_off_terminal (PSSM.update만 제거 + 종료 시점 추출)을 각각 별도 Python/Xvfb 프로세스에서 실행한다.
- 프레임마다 road/wide 원본 RGB, 모델 화면 및 ONNX I420 입력 배열 해시를 그대로 저장하고 첫 2프레임 역시 원본 시계열에 보존한다.
- 모든 프레임 수집 이전 +2m 카메라 이동 양성 대조, 마지막 GPU 추출 이후에는 렌더 틱 없이 CPU RGB를 한 번 더 읽어 해당 완료 프레임의 최종 RAM 바이트가 변경되지 않았는지 확인한다. 이 두 조건이 실패하면 INCONCLUSIVE로 기록한다.
- 최종 그림자맵/HDR 텍스처는 **각 프로세스의 마지막 프레임 한 장**만 추출한다. 따라서 최종 texture SHA 비교는 시계열 RGB 해시와 분리된 제한적 스냅샷 진단이며, HDR의 프레임별 드리프트나 셰이더 유일 원인을 증명하지 않는다.
- GitHub Actions run은 실제 실행 상태/아티팩트가 확보된 후 PASS/FAIL 및 SHA를 기재한다. 정식 ONNX 새 영상 폐루프 반복시험은 별도의 후속 게이트이다.
