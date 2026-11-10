# Stage 7 — post-Chase PSSM 재갱신과 종료 시점 GPU Shadow Depth/HDR/원본 RGB 비교

현재 상태: **공식 MetaDrive 0.4.3 native 4/4 진단 CI SUCCESS, 28개 독립 프로세스 GPU 원본 바이트 검증 완료**. 시뮬레이션 전용이며 공식 모델 반복재현성·주행성능 순위 미통과.

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

## 2026-11-10 실제 4개 장면·28개 원본 프로세스 검증 결과

[GitHub Actions #42828142647](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/42828142647) **completed SUCCESS (4/4 matrix jobs)**. 시드 20261109·20261110×S자 방향 2종×7개 네이티브 조건 = 총 28개 독립 Python/Panda/Xvfb 프로세스. 공식 MetaDrive 0.4.3 에셋 SHA256, 두 카메라의 렌더 자세 +2m 이동 양성대조, GPU 추출 전 프레임별 RGB/I420 보존, GPU 추출 후 동일 RAM RGB 보존, post-Chase Sort 25 태스크 호출·PSSM numeric MVP 변경을 검증했다.

### 가상 메인 카메라 +2m 이후 Post-Chase PSSM 재갱신의 GPU raw 바이트 변화

아래 수치는 `offset_probe_terminal`(Sort 25에서 카메라/MVP를 **읽기만 함**)과 `offset_sync_terminal`(Sort 25에서 **PSSM.update를 한 번 더 호출**)의 **서로 독립된 마지막 프레임 GPU 스냅샷 원본 바이트를 직접 비교한 결과**. 모두 texture component layout 일치 검증 뒤 바뀐 GPU 원본 **byte count**임. HDR 색상 픽셀 수 또는 shadow map texel 수가 아니다.

| 시드 | S자 | pssm_depth changed bytes | road_hdr changed bytes | wide_hdr changed bytes |
|---|---|---:|---:|---:|
| 20261109 | 좌→우 | 22,634 | 118,825 | 17,695 |
| 20261109 | 우→좌 | 22,634 | 57,120 | 16,792 |
| 20261110 | 좌→우 | 22,308 | 105,722 | 13,720 |
| 20261110 | 우→좌 | 22,308 | 40,200 | 8,454 |

**순수 CPU 관측의 음성대조:** 네 장면 모두 `offset_terminal` (sort25 추가 태스크 없음) vs `offset_probe_terminal` (sort25 읽기만 함)의 그림자 깊이/HDR 두 카메라 **3개 raw GPU 텍스처 전부 바이트 동일**(3 stages×4 conditions = 12/12).

**그림자 atlas 복귀 양성 증거:** 네 장면 모두 `offset_sync_terminal`에서 마지막 그림자 깊이 raw GPU 바이트가 +2m 개입을 전혀 넣지 않은 `natural_terminal`과 **정확히 일치**했다 (4/4, 각각 8,388,608 raw bytes). 이때 두 조건의 HDR raw bytes는 작은 잔여 차이가 있었다. 원래 HDR 대비 sync HDR raw 바이트 차이:

| 시드·장면 | Road HDR 변경 raw byte | Wide HDR 변경 raw byte |
|---|---:|---:|
| 20261109 좌→우 | 51 | 12 |
| 20261109 우→좌 | 49 | 18 |
| 20261110 좌→우 | 0 | 12 |
| 20261110 우→좌 | 0 | 18 |

**CPU 모델 입력 원본 증거:** `offset_no_gpu` vs `offset_terminal`은 네 장면 모두 원본 road/wide 및 I420의 **5/5 타임스텝 SHA**가 일치했다. 즉 이번 두 실험군의 종료 시점 GPU probe는 이미 저장된 5개 영상의 내용을 바꾸지 않았다. 반면 `natural_no_gpu` vs `natural_terminal` 및 `offset_sync_no_gpu` vs `offset_sync_terminal`은 일부 프레임 SHA가 일치하지 않았다. 이는 별도 Panda 프로세스 자체의 렌더링 변동/CPU 타이밍 교란을 배제할 수 없음을 보여준다.

### 기술적 결론과 남은 검증

- 의도적 메인 카메라 +2m 개입이 만들어낸 PSSM shadow atlas 차이는 같은 프레임 Chase 이후 PSSM을 추가 갱신하는 **별도 실험 조건**에서 기본 무개입 atlas와 동일해졌으며, 최종 HDR에도 측정 가능한 차이가 발생했다. 따라서 이 실험에서 **그림자 depth 및 HDR GPU 바이트가 post-Chase MVP 계산 시점에 민감한 것**은 반복 관측된다.
- 그러나 이 시험은 원래 MetaDrive의 CPU/GPU 동기화나 실행 순서를 수정한 **가상 개입군**이며, 원본 렌더링의 실제 후반부 미세 RGB 불일치가 해당 시차에서 기인했다는 증명은 아니다. GPU 원본 바이트 비교는 서로 다른 프로세스에서 얻었으므로 독립 렌더링 변동을 포함한다. 진단에서 보인 0~51 HDR raw byte 차이도 본래 GPU texel·RGB 픽셀 및 주행 결과로 직접 변환할 수 없다.
- 최종 프레임 1개에서만 GPU shadow/HDR 추출. 매 프레임 GPU 시간 추적을 수행하면 이전에 관측된 읽기 간섭이 재발할 수 있으므로 하지 않는다. 독립 실행 반복시험에서 해당 A/B 효과가 일관적인지 다른 카메라 pose·램프 장면에서 추가 재현성을 확인해야 한다.
- **공식 MD-V3 원래 신규 프레임 독립 ONNX 폐루프 엄격 repeatability 0/4 PASS 문제는 그대로**. 모델 안전성/공식 모델 주행성능 순위를 산출하지 않으며 Stage 7 미완료. 실차/CAN/CD210/Carrot MPC·Params·차종별 튜닝 모두 제외.
- 다음 하드 게이트: 순수 원본 렌더링의 CPU/그림자 행렬 갱신 지연과 최종 RGB 불일치 사이의 연관성을 **동일 프레임/동일 상태에서 독립 반복 가능한 방식**으로 측정하고, 정합 개선으로 활용하려면 반드시 원래 코드 경로와 동등성 검증 후 공식 MD-V3 신규영상 독립 추론 반복시험 재실행.
