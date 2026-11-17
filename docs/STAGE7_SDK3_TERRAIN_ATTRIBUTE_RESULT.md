# SDK3 대형 attribute 버퍼 제한 읽기 결과

**2.03GB 상주 attribute 버퍼에서 선택값20개를80바이트로 읽었다. 모두 float32 `0.0`이었고, 관찰 구간 RSS 최고치 증가량은0KiB였다.** 기존 CPU 후보점의 level0 보간에서는 노란 차선 조건이 성립하지 않았다. 실제 GPU 샘플링·픽셀 소유자·원인·수정은 미확정이다. 공식 판정은 **3/4 PASS·전체 FAIL·Stage7=false**를 유지한다.

## 제한과 실측

| 항목 | 관찰 |
|---|---:|
| attribute 논리 크기 | 2030043136B |
| attribute 창/texel/복사한 원시 바이트 | 5/20/80B |
| 전체 terrain 창/복사한 원시 바이트 | 15/200B |
| 관찰 전후 프로세스 RSS 최고치 | [5768500, 5768500]KiB |
| 관찰 구간 RSS 최고치 차이 | 0KiB |
| 새 허용 논리 크기 | 2147483648B |
| 창당/전체 원시 바이트 예산 | 64B/960B |
| RSS 차이 부분 판정 상한 | 32768KiB |

기존1GiB 도구와 검증기는 변경하지 않았다. 새 비공개 함수 사본만2GiB 논리 크기를 허용하며 기존의 네 텍셀 읽기·좌표·wrap·범위·해시 검사를 유지한다. 전체 버퍼 변환·복사·스캔이나 GPU readback은 없다. 실제2.03GB 읽기 전용 sparse mmap의 끝부분/반복 경계를 literal 값으로 검증했고, CPU 테스트 RSS 증가도32MiB 미만이었다. RSS 최고치 차이는 모든 내부 할당을 검출하는 보장은 아니다.

## 실제 선택값

| ray | UV | 네 rawfloat32 값 | CPU level0 보간 | CPU yellow 조건 |
|---|---|---|---:|---|
| center | [1.5744431697582306, 1.5004200512163417] | [0.0, 0.0, 0.0, 0.0] | 0.0 | False |
| top_left | [1.57445297703116, 1.5004230849612568] | [0.0, 0.0, 0.0, 0.0] | 0.0 | False |
| top_right | [1.574433386625932, 1.5004170249389985] | [0.0, 0.0, 0.0, 0.0] | 0.0 | False |
| bottom_right | [1.574433386625932, 1.5004170249389985] | [0.0, 0.0, 0.0, 0.0] | 0.0 | False |
| bottom_left | [1.57445297703116, 1.5004230849612568] | [0.0, 0.0, 0.0, 0.0] | 0.0 | False |

모든 원시 hex는 `00000000`이었다. 이들은 기존 최근접 CPU GeomNode 후보점을 지형 좌표로 투영한 위치의 값이다. 실제 지형 교점이나 GPU raster/MSAA 샘플 위치로 주장하지 않는다. CPU bounds 조건은 통과했으나 `attribute.r > 0.01` 조건이 거짓이었다. 실제 mip/필터링·준비된 텍스처·좌표 보간·가시성은 이 관찰로 확인되지 않는다.

## 실행과 원본 픽셀

Run44054071896,workflow421129416,attempt1,source`76d92c5cfe8218fb556f640d4df03846708d88a4`,activation`b823f04d1a67504623946057c4157db0b6ff235b`. Artifact14314907454/16513617B,`sha256:b660bfe523da55972fe725b0793a6ca4c4ecad2e680159347c49e1df238a1d70`. 독립 수신 검증 통과,7포즈/14원본 이미지/1renderer/0공식모델/0ONNX추론이다. Native elapsed289.795796s,child/Xvfb/container return0/0/0,no timeout/noOOM,provider close/observer restoration/container removal 모두 완료했다. 원래taskticks14,extra_gpu_queries0/extra_render_tasks0,ORT 미로드다.

Terrain complete/tagshader exact match/attribute collection complete 모두true;4CPUstates/2cachedshaders/2sources/3textures/5candidatepoints다. Inspector elapsed0.010083858s. cgroup memory.peak=5821898752B.

Road7(596,494)은 **[167, 163, 158] 회색**, fullSHA`3d7ced2bf6e8c448d5f99695c03221599150c1c93f44e2abb28105041c67054f`로 역사적 회색 이미지와 일치한다. 원본 전체 동등성은false,renderer_diagnostic_passed=false,status`INCONCLUSIVE_TERRAIN_ATTRIBUTE_RECORDED`다.

Historical trial0과의 변경: `[{"step": 2, "camera": "road", "changed_rgb": [{"xy": [401, 393], "historical": [135, 144, 82], "actual": [179, 176, 171]}]}]`.

Historical trial1과의 변경: `[{"step": 2, "camera": "road", "changed_rgb": [{"xy": [401, 393], "historical": [135, 144, 82], "actual": [179, 176, 171]}]}, {"step": 7, "camera": "road", "changed_rgb": [{"xy": [596, 494], "historical": [199, 187, 0], "actual": [167, 163, 158]}]}]`.

## 검증·보존과 다음 관찰

새16tests와 기존 관련 회귀 합계131PASS,actionlintPASS. 독립 리뷰 Critical0/Important0/Minor1,별도51CPUtests와RSS32768/32769KiB경계/강제partial/위조완료거부/동일Docker명령/cold-I-S-B독립검사PASS. 경미 지적은 해당 RSS 경계·위조완료 동작의 영구 회귀 테스트가 아직 없다는1건이며 계획대로 미뤘다. 수정 pass/재리뷰는0회다.

실측 소스의 canonical push44053108922/PR44053121302 네 작업PASS,양쪽2099tests/7skips를 로그로 확인했다. 본 단계는 단일 요청·단일 actual/단일renderer다. 코드·테스트·workflow는 실측 이후 동결한다. base279ab9d6881a4924bb27aca6de198fd8e9ee1d04 대비 추가 파일만 존재하며 원본 checkout/주요6아티팩트 해시·모드/이전31디렉터리3846파일 해시를 보존했다. 환경·레지스트리 게시나 main merge는 하지 않았다.

다음 관찰 대상은 CPU 후보와 실제 준비된 텍스처의 샘플링·좌표 매핑·가시 표면의 차이다. 이번에 읽은0.0만으로 이전 노란 픽셀의 원인을 확정하지 않는다.

Draft PR: https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/141 (base Draft140).
근거: [sparse budget](evidence/sdk3-terrain-attribute-01/actual/sparse-budget-verification.json),[terrain analysis](evidence/sdk3-terrain-attribute-01/actual/terrain-analysis.json),[independent observation](evidence/sdk3-terrain-attribute-01/actual/independent-observation.json),[source pixels](evidence/sdk3-terrain-attribute-01/actual/source-prefix-pixel-comparison.json),[retained index](evidence/sdk3-terrain-attribute-01/actual/retained-index.json),[review](evidence/sdk3-terrain-attribute-01/review/whole-branch-review.md),[ledger](evidence/sdk3-terrain-attribute-01/ledger.md).

최종 문서 커밋 exact-HEAD CI와 원격 PR/body/부모/main/원본 보존은 커밋 자기참조를 피하기 위해 `output/stage7-sdk3-terrain-attribute-01/final-closeout/verification.json` 및 `final-ledger.md`에 기록한다.
