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

