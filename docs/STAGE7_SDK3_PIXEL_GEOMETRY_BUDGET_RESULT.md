# SDK3 7자세 완료·CPU 보도벽 후보 관측, 전체 원본 재현은 불일치

2026-11-16 KST 기록. **600초 예산에서 7자세 캡처와 목표 픽셀의 CPU 기하 수집을290.405초에 완료했다.** 목표 Road7 전체 이미지는 기존 노란 분기와 정확히 일치하며, 픽셀(596,494)은 `[199,187,0]`이다. 다섯 CPU 광선의 가장 가까운 교차 후보는 보도벽 메시의 동일한 삼각형이며 중심 거리는8.420816이다. 하지만 Road4에서 두 픽셀이 달라 전체7자세 원본 재현 성공은 인정하지 않는다. 픽셀 원인·수리·GPU 소유권은 미확정이며 기존 공식 모델 행렬은3/4PASS·전체FAIL, Stage7는 미완료다.

[실제 실행43885514458](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43885514458)은 workflow420216705/attempt1이다. 검토·수정 소스`f7ee8e4089be9b31fc7af1dae924d146d13ea70b`, 요청만 추가한 활성화`e81e3fcc8ed46a8e32f7e6edf56843dbe19f0adf`에서 새 렌더러1개·공식 모델0개·ONNX 추론0회를 실행했다. 요청대로 자식600초·컨테이너630초·job20분만 적용하고 기존2CPU/10GiB와 렌더 설정·시계·원래 카메라/태스크·모든 기존 파일을 보존했다. 가짜 모델 인자로 자원 모드를 선택하지 않았다.

| 실제 관측 | 결과 |
|---|---|
| WORLD_READY | 저널 시작 후70.003초 |
| 캡처 한 쌍 | 30.715~31.629초,총7쌍 |
| 원본 이미지 | 14개 및 같은 Road7의 관찰용 별도 사본1개 검증 |
| 기하 수집 | Road7 원래 CPU 읽기 직후·카메라 복원 전,274.250초 진입 |
| CPU 순회 / 전체 기하 처리 | 0.026869 / 0.030843초 |
| 순회·선별 | 36노드,hidden3,bounds_missed31,메시2 |
| 정점·삼각형 | 585 / 1,004;카운터·소스 인덱스·교차 결과 재계산 일치 |
| 경계·스택 | 저널121행,30초 주기 Python 스택9개 |
| native / Xvfb / 컨테이너 종료 | 0 / 0 / 0,시간 초과 없음 |
| 정리 | provider.close·관찰 래퍼 복원true,OOMfalse,소유 컨테이너 제거true |
| 태스크·추론 | 원래14task ticks와 태스크 목록 유지,ORT모듈 미로딩 |

이 실행의 시간은 이전 관측의 준비93초·캡처42초보다 짧았다. 이전 수치로 잡은384초는 추정값이며, 이번 실측290초로 소급 교체하지 않는다. 같은 렌더링을 가볍게 바꾸거나 초기 reset의 원래 renderFrame 호출을 줄이지 않았다.

전체 재현 판정은 `INCONCLUSIVE_SOURCE_CPU_GEOMETRY_RECORDED`다. 14개 캡처 이미지를 모두 해제·해시 검증하고 과거 두 trial의 첫7캡처28개 원본과 비교했다. 과거 원본 manifest와 source SHA는 Git에 보존된 실행 보고서에도 대조했다. Road4만 공통 첫6프레임 기준에 불일치하며 다른 첫6이미지 및 Wide7은 일치한다. Road7은 과거run-1의 노란 전체 이미지와 완전히 같다. 과거run-0과의 Road7 차이는 알려진 한 픽셀 차이 그대로다.

| Road4의 두 변경 픽셀,좌상단 원점·0기준 | 과거 두 trial RGB | 이번 RGB |
|---|---|---|
| (175,359) | [174,169,166] | [140,143,75] |
| (555,454) | [171,166,159] | [131,142,78] |

Road4의 최대 채널 차이는91이며, 경계 사각형 전체가 바뀐 것이 아니라 위 두 픽셀만 바뀌었다. 따라서 `source_image_equivalence=false`, `renderer_diagnostic_passed=false`를 유지한다. Road7의 일치와 CPU 후보를 전체 폐루프/재현 성공으로 승격하지 않는다. Road4 차이는 Road7 기하 callback 이전에 관측됐지만, 이것만으로 관찰기·할당 이력·타이밍의 영향이나 고유 원인을 구분할 수 없다.

목표 픽셀의 중심/네 모서리 광선은 모두 보도벽 삼각형606을 가장 가깝게 교차한다. 소스 ID는 `[mesh1,primitive0,decomposed_triangle40,vertices40/39/4]`, 경로는 `render/world_np/1C/1C_sidewalk/polygon_node`다. 중심 교차 위치는 약`[76.229806,0.430132,-0.001713]`이며, 중심의 CPU barycentric은`[0.299879,0.205833,0.494288]`이다. 삼각형의 보관된 세계 정점은`[78.307243,1.072759,-0.150000]`, `[75.339989,0.154880,-0.150000]`, `[75.339989,0.154880,0.150000]`이다.

| CPU 표본 광선 | 가장 가까운 보도벽 거리 | 다음 교차 후보 |
|---|---:|---|
| 중심 | 8.420816 | SkyboxMesh,18,718.442017 |
| 좌상 모서리 | 8.430505 | SkyboxMesh,18,717.068271 |
| 우상 모서리 | 8.410256 | SkyboxMesh,18,717.711231 |
| 우하 모서리 | 8.411154 | SkyboxMesh,18,719.820832 |
| 좌하 모서리 | 8.431405 | SkyboxMesh,18,719.178056 |

거리 단위는 보관된 near점에서 시작하는 CPU 세계 좌표 거리다. 원거리 SkyboxMesh는 shader가 있는 CPU 메시 후보다. 이 값들을 실제 실행된 GPU 깊이·도형 소유권으로 해석하지 않는다. 보도벽의 캐시된 net state에는 color/normal 텍스처와 생성 shader·조명이 있으나, 이번 기록은 해당 삼각형의 UV·텍스처 샘플 결과를 수집하지 않았다. 노란 픽셀이 보도벽 shader/텍스처에서 나왔다고 확정하지 않는다.

캐시된 Panda framebuffer 속성은 depth_bits0/multisamples0이었다. 이는 새 GL query로 확인한 depth attachment·샘플 위치가 아니며, 실제 깊이 버퍼 부재를 입증하지 않는다. 다섯 CPU 광선은 실제 MSAA 표본도 픽셀 원뿔의 전부도 아니다. CPU visible/bounds 선별·보관된 메시가 shader 변형·실제 cull/draw 전체를 포괄한다고 주장하지 않는다. 순회가 예산 안에 끝났어도 `cpu_scene_coverage_proven=false`다. raw state 포인터를 실행된 sort key나 원인으로 승격하지 않는다.

렌즈near는0.10000000149,far는100000이었다. 고정 Panda1.10.13의 clipdepth -1/+1과 far clamp1e-7,실제 캐시 float32 역행렬에서 구간을 독립 재구성했다. 최대 세계 endpoint 차이는1.819e-12,XY reprojection 오차는7.588e-8NDC였다. CPU endpoint 허용값32float32eps와 inverse residual1e-5는 float32 보정용이고, 교차 비교1e-9world/1e-12relative 및 원본 이미지의 완전 SHA 일치를 바꾸지 않는다. 정점585=285+300,삼각형1004=566+438 등 보관 자료와 카운터를 대조했다.

실행 전 단일 전체 변경 검토의 Important2개는 한 번의 RED→GREEN 수정 단계에서 처리했다. 잘못된 광선 방향/구간과 불가능한 메시 카운터를 거부하며 미완료 순회의 합법적인 부분 읽기는 허용한다. 관련99개 CPU 회귀 테스트와 actionlint가 통과했다. 정확한 실행 소스의 canonical push43884702699/PR43884712820 네 작업이 모두 성공했고, 양쪽 단위 테스트는 각각1,982개·7개 건너뜀이다. 로컬 SDK/Panda/GLX/공식 모델 실행은 없다.

산출물14235720020은13,427,083B,ZIP SHA`43475129a0cc3a6ab4d48f9f73eecdf18f1c7002887ef04af604eb9f99c4bd5c`로 GitHub API에 대조했다. 안전한 해제 경로·크기 제한 후 원본45파일의 크기·SHA·보관 위치를 기록했다. JSON/JSONL/스택22개는 Git에, 원본 RGB·geometry.npz·일반 로그23개는 Actions와 output에 보존했다. 모델 가중치는 없다. 초기 task 목록과 softpipe·실제 명령·SDK/core/BaseCamera/reference pins·자원/격리 설정을 확인했다. 메모리 최고 사용량은5,822,611,456B였다. 원본6개 byte/mode pin과 이전31개 디렉터리/3,846개 증거 파일도 보존했다.

다음 원인 구분은 일치한 Road7의 보도벽 후보 삼각형에 대한 UV·재질·텍스처/샘플러 상태와 실제 렌더 결과의 관계를 조사하는 일이다. 이번에는 추가 실행·shader/깊이/태스크 변경·수리 판정·환경/레지스트리 게시·main 병합을 하지 않았다.

근거: [독립 관측 검증](evidence/sdk3-pixel-geometry-budget-01/actual/independent-observation.json), [CPU 후보](evidence/sdk3-pixel-geometry-budget-01/actual/candidate-analysis.json), [원본 픽셀 비교](evidence/sdk3-pixel-geometry-budget-01/actual/source-prefix-pixel-comparison.json), [경계별 시간](evidence/sdk3-pixel-geometry-budget-01/actual/boundary-analysis.json), [원본 보관 색인](evidence/sdk3-pixel-geometry-budget-01/actual/retained-index.json), [검토·수정](evidence/sdk3-pixel-geometry-budget-01/wholebranch-review.md), [판단 장부](evidence/sdk3-pixel-geometry-budget-01/ledger.md). 최종 문서 커밋 CI 및 초안PR135·기존PR134·main·원본 보존 영수증은 `output/stage7-sdk3-pixel-geometry-budget-01/final-closeout/verification.json`에 별도로 기록한다.
