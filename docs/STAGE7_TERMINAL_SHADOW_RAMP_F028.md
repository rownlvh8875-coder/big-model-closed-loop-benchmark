# Stage 7 — MetaDrive 실제 S자·진입/진출 램프, lane fraction 0.28 GPU shadow/HDR 비교

상태: **공식 MetaDrive 0.4.3 네이티브 실측 진행 중**. 본 문서는 모델 주행성능 또는 실제 차량의 안전성을 증명하지 않는다.

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
