# MetaDrive × 공식 MD-V3: 요청한 세 작업 완료

2026-11-18KST. 실제 렌더링 차이의 원인을 입증하고, 원인에 맞춘 RGBterrainpriority 수정을 검증했으며, 공식 대형ONNX의 새4조건 폐루프 재현성 검증을 통과했다. 기존 미수정 파이프라인3/4FAIL은 보존한다.

| 작업 | 실제 결과 | 증거 |
|---|---|---|
| 렌더링 원인 | Road7(596,494)에서 geometry와terrain의 D24정규화 깊이floatbits가 모두1065153572. 원래GL_LESS는 뒤에 그리는terrain을 거부한다. 한픽셀 깊이clear 실험에서 그픽셀만 gray167/163/158→yellow199/187/0; 14쌍의 원본이미지비교에서 해당픽셀을 제외한 모든픽셀은동일 | [원인03](evidence/sdk3-renderer-completion-01/depth-mechanism-03/target-depth-cause.json) |
| 원인별 수정 | 두RGB카메라의 기존Terrain tagstate에 background/-1bin만추가. 셰이더·GL_LESS·depthwrite·PSSM·원래캡처시계 유지. 8x8canary8이미지의 모든픽셀 통과; 독립candidate-off/trace 원본14이미지 모두일치, terrain이geometry보다먼저실행, depthclear없음 | [수정04](evidence/sdk3-renderer-completion-01/priority-repair-04/README.md) |
| 공식대형ONNX 폐루프 | 새4조건 모두엄격일치. 독립4컨테이너·8프로세스·96실제추론. 원본RGB/warp/I420입력/원시출력/재귀상태/궤적/시각 모두일치. 허용오차·입력재생·추가렌더·수렴관측없음 | [공식모델01](evidence/sdk3-renderer-completion-01/official-model-cohort-01/README.md) |

| seed | 장면 | 독립실행 | 완료추론 | 엄격비교 |
|---|---|---:|---:|---|
| 20261109 | s_curve_left_right | 2 | 24 | PASS |
| 20261109 | s_curve_right_left | 2 | 24 | PASS |
| 20261110 | s_curve_left_right | 2 | 24 | PASS |
| 20261110 | s_curve_right_left | 2 | 24 | PASS |

공식모델은768750198bytes/SHA25635976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199, ORT1.20.1CPU다. 모델실행소스ce983fa4a03fe87c43d7ea0e2f2900a017e09cf3, 실제[run44115577232](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/44115577232), workflow421509332/attempt1, activation30d20f2793d5983711124e07a19e12ea49512331. 모든조건에 동일한SDK27cd80fb…/imageb9d673de…/수정adapter16aafa7d…를사용했다. 실패한이전canary와관측차이도그대로보존했다.

독립검토에서찾은 두Important를 한차례RED→GREEN으로보강했다. Scissor가private1x1resolve를잘라버리는미지원조건은명시적으로거부한다. 수신기는불완전관측·무효스냅샷·미검증sample수·부분행렬/지형행을거부한다. 관련83테스트와actionlint통과. 강화한수신기로원인03·수정04·공식모델01을재검증해모두통과했다. [검토·수정기록](evidence/sdk3-renderer-completion-01/final-review/review-and-fix.md), [재검증](evidence/sdk3-renderer-completion-01/final-review/final-stronger-revalidation.json), [보존검사](evidence/sdk3-renderer-completion-01/final-review/final-original-preservation.json).

실제증거에는 원래실행한helper/sourceSHA를유지한다. 후속C의좁은거부guard는CPU가짜GL로검증했으며, 수정helper를실제GPU에서새로실행했다고주장하지않는다. 기존실험은해당실패조건이없었고모델프로듀서·카메라·정책·수정adapter는동일하다.

이번4/4는수정후의짧은기술적재현성통과다. 실제driver는Mesa softpipe, 유효sample1이며 물리GPU/MSAA>1·실제광학·전체S경로·CARLA·주행품질·7단계전체완료를인증하지않는다. main/부모PR143/원본checkout과기존artifact6개는보존했고, 환경·레지스트리게시나merge는수행하지않는다. [DraftPR144](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/144)의최종HEAD CI및최종외부수신기록으로마지막closeout을확인한다.
