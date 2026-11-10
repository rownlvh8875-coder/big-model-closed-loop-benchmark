# Stage 7 — MetaDrive 실제 S자·진입/진출 램프, lane fraction 0.28 GPU shadow/HDR 비교

상태: **공식 MetaDrive 0.4.3 네이티브 8/8 조건+통합 집계 SUCCESS; 공식 ONNX 반복 재현성 미통과**. 본 문서는 모델 주행성능 또는 실제 차량의 안전성을 증명하지 않는다.

## 원본 정보 및 이전 시험과의 차이

- [기존 fraction 0.12 결과](STAGE7_TERMINAL_SHADOW_SYNC.md): 20261109/20261110 × 2종 S자, 28개 독립 MetaDrive/Panda 프로세스에서 terminal-only shadow depth/road HDR/wide HDR A/B를 측정. 두 독립 CI 실행 최종 GPU raw SHA는 48/48 일치했으나 모델-ready I420 5프레임 전체는 138/140 SHA 일치로 엄격한 반복 결정성이 여전히 미완료였다.
- 이번 시험은 [실제 곡선·램프 native geometry](../bigbench/curved_lane_scenarios.py)의 S자 s_curve_left_right/s_curve_right_left, 진입 램프 in_ramp(MetaDrive block r), 진출 램프 out_ramp(block R)의 차선 객체에서 camera pose를 **lane fraction 0.28**로 직접 구한다.
- 이전 S자 시험의 fraction 0.12보다 진행된 카메라 위치이고, 램프 두 장면은 실제 MetaDrive ramp block의 원호 차선을 사용하므로 단순 S자 영상 재활용이나 가짜 램프가 아니다.
- 시드 20261109, 20261110 × 네 장면 = 8개 matrix job. 각 job의 7개 별도 MetaDrive 0.4.3/Xvfb/Panda 프로세스(총 **56개**)에서 GPU/noGPU, final +2m main-camera X 이동, Sort 25 관측, Sort 25 Chase 이후 한 번 더 PSSM.update를 수행하는 조작을 비교한다.

## 원본 렌더링 의미론과 GPU 측정 간섭 통제

- natural_no_gpu와 natural_terminal은 원래 PSSM.update/Chase/igLoop의 순서를 보존한다.
- offset_no_gpu, offset_terminal은 종료 프레임 직전 가상 메인 카메라 X를 +2m **의도적으로** 옮기는 반증 실험. 이를 원래 렌더링이나 실제 모델 입력으로 대체하면 안 된다.
- offset_probe_terminal은 Chase 이후 Sort 25에서 CPU 숫자 행렬과 메인 카메라를 관찰하는 추가 태스크를 등록하며, GPU readback은 촬영 후에만 한다.
- offset_sync_no_gpu, offset_sync_terminal은 동일한 Sort 25 실험 경로에서 PSSM.update를 Chase 이후 추가 실행하는 조작 조건으로, **원본 renderer 의미론이 변한다**.
- 모든 원본 RGB(964×604 ×2), warped RGB(512×256 ×2), I420 (2,6,128,256) uint8의 5프레임을 수집하고, CPU RAM 중복 읽기 bit-exact 확인 뒤 **마지막 프레임 이후** terminal GPU PSSM depth+road/wide HDR 각각 1회만 추출한다.
- 각 GPU texture 원본 바이너리와 레이아웃·SHA256·무손실 zlib 파일을 보존. Raw changed byte count와 SHA만 비교하며 byte offset을 픽셀·그림자 texel 수로 해석하지 않는다.
- 두 카메라 각각 +2m WORLD 위치 이동에 RGB가 반응해야 하고, GPU 추출 이후 마지막 RAM RGB가 그대로여야 한다. 실패 시 ERROR/INCONCLUSIVE를 SUCCESS로 바꾸지 않는다.

## 판정 기준

- scripts/aggregate_terminal_shadow_pose_sweep.py는 여덟 seed/scene/pose를 모두 요구하며 fraction 0.28·실제 장면·7 arm·3 GPU texture·다섯 GPU 바이트 비교 쌍·원본 카메라 양성대조를 fail-closed 검증한다.
- 결과는 본래 연산과 PSSM 재갱신의 **종단 GPU 바이트 차이에 대한 상관적 관측**이다. 독립 프로세스의 자연 변동, shader pass 자체, 원본 후반부 RGB drift의 단독 원인 또는 MD-V3 모델 안전성/품질을 증명하지 않는다.
- GitHub Actions success는 **자료 수집 및 검증 파이프라인 성공**이다. GPU depth/HDR 차이나 post-Chase sync가 원본 영상의 비트 결정성을 보장한다고 해석하면 안 된다.
- 원래 MD-V3 ONNX 신규 프레임 독립 폐루프 엄격 반복은 마지막 공식 시험 기준 **0/4 PASS**, 7단계 계속 미완료. 실차·CAN·CD210·Carrot MPC/Params 및 주행성능 순위 금지.

## 실행 및 증거

[실험용 GitHub Actions 원본 workflow](../.github/workflows/terminal-shadow-pose-ramp-sweep.yml). 원본 8개 조건 아티팩트와 집계 JSON의 실제 수치·실패 원인은 CI 검증 후에만 추가한다.


## 2026-11-11 실제 GPU 네이티브 8조건 실측 결과

[GitHub Actions #42897373586](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42897373586): **네이티브 8/8 job과 통합 sweep-summary 1/1 job 모두 SUCCESS**. 공식 MetaDrive 0.4.3 release 에셋 정확한 SHA256 검증, 시드 2개 × 실제 2개 S자+진입/진출 램프 × lane fraction 0.28 × 서로 독립된 7개 프로세스 = 총 **56개 Python/Panda/Xvfb 네이티브 실행**. 8개 raw GPU artifact ZIP과 통합 집계 아티팩트에 측정값 보존. 완전한 소스 프레임 결정성이나 모델 품질이 아니라 **GPU 원인 분리 진단의 자료 수집 성공**이다.

### GPU terminal snapshot (각 장면 마지막 1프레임만)

다음 수치는 메인 가상 카메라 최종 프레임 X +2m 이동 후 Sort 25에서 **읽기만 한 조건**과, 별도의 Sort 25에서 **Chase 이후 PSSM.update를 한 번 더 실행한 조건**의 서로 독립된 최종 GPU 텍스처 원본 바이트 차이다.

| seed | MetaDrive geometry | 그림자 depth 변경 raw bytes | Road HDR 변경 raw bytes | Wide HDR 변경 raw bytes |
|---|---|---:|---:|---:|
| 20261109 | s_curve_left_right | 22,634 | 234,865 | 56,228 |
| 20261109 | s_curve_right_left | 22,634 | 91,811 | 26,482 |
| 20261109 | in_ramp | 22,634 | 296,598 | 53,781 |
| 20261109 | out_ramp | 22,634 | 6 | 17 |
| 20261110 | s_curve_left_right | 22,308 | 298,811 | 34,648 |
| 20261110 | s_curve_right_left | 22,308 | 58,093 | 17,159 |
| 20261110 | in_ramp | 22,308 | 224,344 | 33,439 |
| 20261110 | out_ramp | 22,308 | 11 | 6 |

- **단순 Sort 25 읽기 관측 vs 아무 Sort 25 태스크 없는 오프셋 조건:** 여덟 장면의 3종 GPU stage 모두 **24/24개 최종 바이너리 동일**. 단순한 추가 CPU 관측 태스크는 이번 GPU 최종 바이트 값을 바꾸지 않았다는 음성대조 결과다.
- **PSSM 재갱신 후 그림자 깊이 복귀:** 여덟 장면에서 **8/8 그림자 depth raw GPU stage가 가상 메인 카메라 +2m 개입 없는 원래 장면의 마지막 그림자 텍스처와 완전히 일치**했다. 이는 해당 동일 장면의 최종 GPU depth binary 관측이다. CPU/GPU draw 순서 자체를 텍스처로 직접 관측한 것은 아니다.
- **진입 램프 대비 진출 램프:** 그림자 depth 변경량은 같은 시드에서 동일하지만, 진입 램프 Road HDR은 224,344~296,598 raw bytes, 진출 램프는 6~11 raw bytes 변경에 그쳤다. 원본 RGB 화면에서 보이는 표면과 그림자 영역이 장면에 따라 달라진다는 것과 부합하지만, **raw GPU 바이트 수는 화면의 픽셀 수, 실제 그림자 texel 수, 주행 오차를 뜻하지 않는다**.
- 실제 native lane pose는 지오메트리에서 직접 산출됐다. 예로 20261109 out_ramp fraction .28 메인 가상 카메라 위치는 x=110.8528320993924, y=-3.3523554271601887, z=1.22 m이며 in_ramp는 x=82.95876624245881, y=-8.335987885201776, z=1.22 m다. 시드 20261110 out_ramp는 x=105.29852606911896로 달라졌으므로 seed별 서로 독립된 native road geometry에서 평가됐다.

### 엄격한 판정 범위

이 데이터는 **마지막 한 프레임의 GPU shadow depth/HDR 원본 바이트**를 각각 다른 Panda 프로세스에서 관측한 것이다. 본래 그림자셰이더가 반드시 잘못되었다거나, 원본 게임 루프의 후반 RGB 흔들림이 PSSM 시차 한 가지 때문에 발생했다는 인과 증명은 불가능하다. PSSM을 추가로 한 번 실행한 실험 arm은 원래 MetaDrive/MD-V3 평가용 장면의 의미론을 바꾼다.

이번 단계에서도 실제 MD-V3 ONNX를 추론하지 않았으므로 **7단계 모델 폐루프 엄격 반복 재현성 게이트는 계속 FAIL/미완료**다. 실차·CAN·CD210·Carrot MPC/Params·모델 주행성능 순위 금지. 다음 우선순위는 **원래 PSSM/Chase 코드 경로에서 공식 MD-V3 신규 영상 독립 12-step 두 프로세스 반복성 재검증** 및 지속적인 GPU 텍스처 모니터링이 원본 RGB에 개입하지 않는 방법의 별도 연구다.
