# Stage 7 — post-Chase PSSM 재갱신과 종료 시점 GPU Shadow Depth/HDR/원본 RGB 비교

현재 상태: 네이티브 시험 시작, **원본 결과 확인 전**. 시뮬레이션 전용, 공식 모델 주행성능 순위 금지.

## 이전 근거

- MetaDrive-0.4.3 `metadrive/engine/core/pssm.py` 89~101행: `PSSM.update`는 현재 `engine.camera`로 shadow rig MVP를 갱신하고 GPU shader 입력 `pssm_mvps`를 설정. 127~158, 192~236행에서 shadow depth GPU buffer에 depth atlas를 연결.
- MetaDrive-0.4.3 `metadrive/component/sensors/rgb_camera.py` 25~60행: 최종 카메라 RGB 전에 HDR `scene_tex`를 톤매핑 입력에 사용.
- [앞선 native PSSM/Chase pose 검증](STAGE7_PSSM_CHASE_POSE_LAG.md): 시드 2개, S자 2종에서 PSSM → Chase 실행순서 96/96틱, Chase 이동 이후 다음 틱 MVP 갱신 8/8조건. 초기 가상 카메라 X +2m 개입 시 PSSM이 움직인 위치를 참조했으나, 실제 후반 RGB 흔들림의 원인인지 미증명.
- [기존 GPU readback 간섭 보고서](PSSM_HDR_TRACE.md): RGB/HDR `extractTextureData(scene_tex)`를 시계열 도중 읽으면 해당 카메라의 후속 RGB 갱신을 방해할 수 있었다. 종료 시점 한 번 추출하는 방법만 원본 RGB 시계열을 먼저 보호하는 방식으로 사용.

## 신규 실험: 7개 독립 원본 네이티브 프로세스

2시드(20261109/20261110)×2 실제 S자 장면×7 arms = **28개 독립 MetaDrive/Panda/Xvfb 프로세스**, 각 5프레임(워밍업 2포함), 공동 `taskMgr.step` 1회/카메라 쌍, 실제 차선 진행률 0.12·WORLD 카메라 높이 1.22m.

| 조건 | 마지막 프레임 메인 카메라 +2m | Sort 25 추가 Panda 태스크 | GPU readback |
|---|---|---|---|
| natural_no_gpu | 아니오 | 없음 | 없음 |
| natural_terminal | 아니오 | 없음 | 촬영 종료 후 |
| offset_no_gpu | 예 | 없음 | 없음 |
| offset_terminal | 예 | 없음 | 촬영 종료 후 |
| offset_probe_terminal | 예 | CPU 카메라 pose/MVP 읽기만 | 촬영 종료 후 |
| offset_sync_no_gpu | 예 | Chase 이후 `PSSM.update` 추가 1회 | 없음 |
| offset_sync_terminal | 예 | Chase 이후 `PSSM.update` 추가 1회 | 촬영 종료 후 |

원본 PSSM·Chase 태스크는 그대로 sort=0, Panda igLoop는 sort=50. `offset_probe_terminal` 및 `offset_sync_*`만 이름을 명시한 **추가 실험 태스크 sort=25**를 넣는다. 따라서 Chase와 igLoop 사이의 CPU 카메라 자세/MVP를 관측하거나 PSSM을 재계산하지만 **원본 MetaDrive 렌더링과 동일하다고 주장할 수 없다**.

## 정확한 측정 계약

- 각 프로세스의 원래 카메라 RGB RAM 읽기 전·후 프레임, warped 512×256 RGB, final 2×6×128×256 uint8 I420 해시 및 실제 변경 픽셀/원소 수를 보존.
- 어떠한 GPU depth/HDR 추출도 **마지막 RGB·I420 완료 이전**에 실행하지 않는다. 종료 시점의 `pssm_depth`, `road_hdr`, `wide_hdr` 각각 한 번만 추출한 뒤 GPU 원본 바이트를 무손실 zlib로 보존.
- raw GPU 파일의 SHA256, byte count, Panda format·component type·dimensions를 집계 시 다시 검증하며 바뀐 바이트의 정확한 offset/count를 비교. **GPU 바이트 offset은 이미지 좌표나 shadow texel 개수를 의미하지 않는다**.
- +2m 카메라 WORLD pose 반응(road/wide)을 GPU readback 전에 별도로 시험. 최종 GPU readback 직후 같은 RAM RGB가 바뀌지 않았는지 재검증. GPU 추출 후 추가 렌더링은 하지 않음.
- CPU sort-25 probe와 sync는 실제 1틱 1번 실행 및 sort=25 등록 여부 확인. X+2m 개입은 마지막 프레임에만 있어야 하며, sync arm은 개입 프레임의 PSSM MVP가 실제 추가 갱신으로 변화했는지 필수 확인.
- `natural_no_gpu`와 `offset_no_gpu`는 GPU 추출이 없는 대조군. terminal arm 시계열과 별도 프로세스 같은 프레임 해시를 비교하되 **독립 프로세스 자체의 불일치 가능성이 있어 정확한 인과효과로 간주하지 않음**.

## 보고 기준

- 신규 네이티브 CI SUCCESS는 실제 28개 GPU/CPU 진단 자료가 수집됐다는 뜻만 의미. sync arm의 GPU depth/HDR 바이트 차이가 있어도 그것만으로 PSSM 지연이 **후반부 픽셀 흔들림의 유일 원인**이라고 결론 내리지 않는다.
- 만약 어떤 GPU stage 추출이 unavailable, 서명/레이아웃 불일치, +2m 양성대조 실패, 최종 RAM RGB 변조, task graph/sort 불일치라면 ERROR/INCONCLUSIVE를 남기고 정상 판정하지 않는다.
- 해당 GPU depth/HDR는 **최종 1프레임 스냅샷**이다. 서로 다른 프로세스의 GPU 바이트를 비교할 수는 있으나, 타이밍별 shadow map 변화 시계열 또는 GPU draw 인과관계를 직접 보여주지는 않는다.
- 공식 MD-V3 신규 프레임 폐루프의 엄격 독립 재현성 이전 0/4 PASS. **Stage 7 미완료**, 실차·CAN·CD210 폴백·Carrot MPC·Params·모델 순위·현실 차량 튜닝 금지.

실제 수치와 검증된 CI 링크는 JSON+압축 원본 바이트를 확인한 이후 추가한다.
