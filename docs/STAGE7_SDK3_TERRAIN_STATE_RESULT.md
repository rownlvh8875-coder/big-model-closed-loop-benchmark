# SDK3 실제 지형 태그 상태 진단 결과

기존 GeomNode 검사에서 수집되지 않았던 절차적 지형의 실제 CPU 캐시 상태를 원래 Road7 read 경계에서 관찰했다. **GPU 픽셀 소유자·원인·수정은 입증하지 않았다.** 공식 판정은 **3/4 PASS·전체 FAIL·Stage7=false**이다.

## 실제 실행

- run: 44045492487, workflow: 421078638, attempt1, source: `bdd09f8f71a72fa55def13416edaacaaa077e45d`.
- activation: `fd8f3eeee6636948e9a110897c4b0354887947e2`; artifact: 14311766977, 16513968B, `sha256:509cac5040cc14106181648304d9e46aceed98b3fb954d38cf8887b79b299910`.
- 독립 수신 검증: True; native_completed: True; source images: 14; source_image_equivalence: False; renderer_diagnostic_passed: False.
- status: `INCONCLUSIVE_TERRAIN_STATE_RECORDED`; native elapsed: 331.344429s; timeout: False; cgroup memory.peak: "5821157376".
- native child/Xvfb/container return: 0/0/0; provider_closed: True; observers_restored: True; container_removed: True.
- 원래 task ticks: 14; extra_gpu_queries: 0; extra_render_tasks: 0; ORT loaded: False.

## 지형 관찰

terrain_present=True, terrain_complete=True, camera-tag shader exact match=True, CPU candidate windows=10.

`attribute`는22528×22528×float32, 상주 예상2030043136B로 명세의1GiB상한을 초과해5개 창 모두 `UNAVAILABLE_EXTENT`로 남겼다. 데이터 부재가 아니라 읽기 상한 때문이며 selector 값은 미관찰이다. Heightfield의20개 raw16bit 값은 모두2055, yellow의20개 raw4byte 값은 모두`00c8ff00`이었다. 다음 관찰 대상은 전체 복사 없이 이 큰 attribute 버퍼에서 제한된 scalar만 읽는 경로이다.

Node: `render/29aef82c-af82-4870-b99c-120bc1644f97/ShaderTerrainMesh`.
Camera tag context: `{"tag_state_key": "rgb", "tag_value": "TERRAIN", "has_tag_state": true}`.
Owner configuration: `{"available": true, "render": true, "use_mesh_terrain": false, "terrain_size": 2048, "height_scale": 50.0, "elevation_ratio": 2.0}`.

| CPU 기록 역할 | Shader ID | RenderState override |
|---|---:|---:|
| node_net | 0 | 0 |
| camera_initial | None | 0 |
| camera_tag | 1 | 0 |
| cpu_net_then_tag | 1 | 0 |

`cpu_net_then_tag`는 별도로 계산한 CPU 구성 예이며 실제 cull 상태로 주장하지 않는다. 카메라 태그의 캐시 소스는 고정 이미지의 terrain.vert/frag와 Panda 전처리 예상 바이트를 정확히 비교했다. 입력은 알려진24이름만 확인했고 numeric array의 unavailable 상태를 유지했다.

## 상주 CPU 텍스처 창

원래 CPU GeomNode의 최근접 후보점을 지형 좌표로 투영했다. **실제 지형 교점·GPU 샘플 좌표는 아니다.** 이미 상주한 CPU 버퍼에서 네 level0 텍셀만 읽었으며 전체 이미지 복사나 GPU readback은 하지 않았다. 아래 bilinear 계산은 CPU 참고값이며 실제 mipmap·anisotropy·렌더 색을 재구성하지 않는다.

| 역할 | 후보 ray | RAM 상태 | 원시 scalar 값 또는 bit pattern | CPU LOD0 참고값 |
|---|---|---|---|---|
| attribute | center | UNAVAILABLE_EXTENT | null | null |
| attribute | top_left | UNAVAILABLE_EXTENT | null | null |
| attribute | top_right | UNAVAILABLE_EXTENT | null | null |
| attribute | bottom_right | UNAVAILABLE_EXTENT | null | null |
| attribute | bottom_left | UNAVAILABLE_EXTENT | null | null |
| heightfield | center | CAPTURED | [2055, 2055, 2055, 2055] | null |
| heightfield | top_left | CAPTURED | [2055, 2055, 2055, 2055] | null |
| heightfield | top_right | CAPTURED | [2055, 2055, 2055, 2055] | null |
| heightfield | bottom_right | CAPTURED | [2055, 2055, 2055, 2055] | null |
| heightfield | bottom_left | CAPTURED | [2055, 2055, 2055, 2055] | null |
| yellow | center | CAPTURED | ["00c8ff00", "00c8ff00", "00c8ff00", "00c8ff00"] | null |
| yellow | top_left | CAPTURED | ["00c8ff00", "00c8ff00", "00c8ff00", "00c8ff00"] | null |
| yellow | top_right | CAPTURED | ["00c8ff00", "00c8ff00", "00c8ff00", "00c8ff00"] | null |
| yellow | bottom_right | CAPTURED | ["00c8ff00", "00c8ff00", "00c8ff00", "00c8ff00"] | null |
| yellow | bottom_left | CAPTURED | ["00c8ff00", "00c8ff00", "00c8ff00", "00c8ff00"] | null |

## 원본 이미지 비교

Historical trial0과의 변경: `[{"step": 4, "camera": "road", "changed_rgb": [{"xy": [175, 359], "historical": [174, 169, 166], "actual": [140, 143, 75]}, {"xy": [555, 454], "historical": [171, 166, 159], "actual": [131, 142, 78]}]}, {"step": 7, "camera": "road", "changed_rgb": [{"xy": [596, 494], "historical": [167, 163, 158], "actual": [199, 187, 0]}]}]`.

Historical trial1과의 변경: `[{"step": 4, "camera": "road", "changed_rgb": [{"xy": [175, 359], "historical": [174, 169, 166], "actual": [140, 143, 75]}, {"xy": [555, 454], "historical": [171, 166, 159], "actual": [131, 142, 78]}]}]`.

## 초기 부팅 실패와 복구

첫 run44042878824/artifact14310940477은 `-I -S`에서 helper의 NumPy 조기 import로 **main 이전**에 종료했다. 인증 ZIP SHA는 `141aa88da6fda25c449fe5a5cbc2ba5b8bcbc231fb1a19c6298eb86479720f78`이다. owned renderer child=0, SDK/GLX bootstrap 미도달, 컨테이너 정리 완료/noOOM을 원본 stderr·고정 소스 제어 흐름·부팅 기록 부재로 확인했다. 첫 요청/증거는 보존하고 재실행하지 않았다.

NumPy를 검증된 런타임 이후의 계산 함수로 옮겼고 정확한 `-I -S -B --help` RED→GREEN 회귀를 추가했다. 첫 실패 증거 해시에 연결된 별도 request02/workflowv2로 복구했다. **호스트 진단 작업2개, 총 owned renderer1개, 공식 모델0개/ONNX추론0회**이다. 리소스/동일 native 명령/동일 수신 검증기를 유지했다.

## 검증과 보존

독립 리뷰 Critical0/Important1/Minor0; 부분 수집 거부 결함은 실제 producer 중단 회귀 RED→GREEN으로 수정했다. 재리뷰는 없었다. 별도 부팅 결함 회귀와 복구 진입점 회귀까지 관련115tests/actionlintPASS. 최종 실측 소스 `bdd09f8f71a72fa55def13416edaacaaa077e45d`의 push/PR canonical4jobsPASS, 양쪽2083tests/7skips를 로그로 확인했다. 미룬 Minor0개다.

원본 checkout과 주요6아티팩트 해시/모드 및 이전31디렉터리3846파일 해시를 보존했다. base1ddcdc8e3b8a1c0022a07bc9844aeae613ca2b4c 대비 추가 파일만 존재하며 main merge나 환경/레지스트리 게시를 하지 않았다. 코드·테스트·workflow는 이번 실측 이후 동결한다.

Draft PR: https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/140 (base Draft139).
근거: [terrain analysis](evidence/sdk3-terrain-state-02/actual/terrain-analysis.json), [independent observation](evidence/sdk3-terrain-state-02/actual/independent-observation.json), [source pixels](evidence/sdk3-terrain-state-02/actual/source-prefix-pixel-comparison.json), [retained index](evidence/sdk3-terrain-state-02/actual/retained-index.json), [bootstrap failure proof](evidence/sdk3-terrain-state-01/bootstrap-failure-verification.json), [review](evidence/sdk3-terrain-state-01/review/whole-branch-review.md), [ledger](evidence/sdk3-terrain-state-02/ledger.md).

최종 문서 커밋 exact-HEAD CI와 원격 PR/body/부모/main/원본 보존 확인은 커밋 자기참조를 피하기 위해 `output/stage7-sdk3-terrain-state-02/final-closeout/verification.json` 및 `final-ledger.md`에 기록한다.
