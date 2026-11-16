# SDK3 Road7 CPU UV·재질·텍스처 관측 완료, GPU 원인 미확정

2026-11-17 KST 기록. **7자세 재생을328.625초에 마치고 목표 픽셀의 CPU 후보 두 삼각형에 대한 UV·재질·샘플러와 텍스처3개를 수집했다.** Road7 전체 이미지는 기존 노란 분기와 정확히 같고 `(596,494)=[199,187,0]`이다. 하지만 Road4의 두 픽셀이 과거 원본과 달라 전체 원본 재현은 실패했다. 판정은 `INCONCLUSIVE_CPU_MATERIAL_RECORDED`이며, 기존 공식 모델 행렬은3/4 PASS·전체FAIL, 수리 미입증·Stage7 미완료다.

[실제 실행43958720772](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43958720772)은 workflow420614501/attempt1이다. 검토·수정 소스`10cc50ba3049c7919bc997b19b4b6caa50eadda9`에 요청만 추가한 활성화`8aecd89e75129a17cb91fd40b135e19bcbd1f567`을 사용했다. 새 렌더러1개·공식 모델0개·ONNX 추론0회다. 기존600초 자식/630초 컨테이너/20분 job,2CPU/10GiB,읽기 전용 루트·network none·private IPC·uid65534·512MiB tmpfs와 고정 이미지/SDK/core/BaseCamera를 유지했다. 원래 태스크·렌더 호출·시계·조명·샘플러를 바꾸지 않았다.

| 실제 관측 | 결과 |
|---|---|
| WORLD_READY | 저널 시작 후79.452초 |
| 7쌍 캡처 | 쌍마다34.532~35.791초,원본14이미지 검증 |
| CPU 기하 | 36노드,2메시,585정점,1,004삼각형,순회0.030886초 |
| 재질 수집 | 원래 Road7 CPU 읽기 직후·카메라 복원 전,선별2삼각형·2메시 |
| UV 표본 | 5광선×2삼각형=10표본,2D stage 표본15개 독립 재계산 |
| 텍스처 | 3개,저장3,656,083B;재질 처리 경과0.007043초 |
| 종료·정리 | native/Xvfb/컨테이너0/0/0,timeout/OOM없음,provider.close·관찰 래퍼 복원·소유 컨테이너 제거true |
| 기타 | 저널121행,30초 주기 스택10개,원래14task ticks 유지,ORT 미로딩 |
| 메모리 최고 사용량 | 5,823,385,600B |

`cpu_seconds`라는 manifest 필드는 이 재질 처리의 monotonic **경과 시간**이다. 프로세스 CPU 사용 시간으로 해석하지 않는다. RenderState·Geom·정점 데이터 포인터,장면 경로,primitive/정점 삼중항,세계 변환,목표 이미지 SHA와 geometry.npz SHA를 결합해 검증했다. 재질 진입/종료는 같은 저널 시계의 GEOMETRY_ENTER/RETURN 안에 있다. 캐시 RAM이 없으면 읽기·GPU 추출·강제 reload를 호출하지 않았다.

가장 가까운 CPU 후보는 이전과 같은 보도벽 삼각형606,경로`render/world_np/1C/1C_sidewalk/polygon_node`,소스`[1,0,40,40,39,4]`다. 중심 거리는8.420816이며 barycentric은`[0.299878922535,0.205832614318,0.494288463147]`이다. 보관된 texcoord 세 개는`[39.153621674,0.536379576]`,뒤 두 개는 모두`[37.669994354,0.077439882]`다. 이 값에서 중심 UV **`[38.1149029162141,0.215066222766967]`**를 재계산했다. 색상과 노멀 stage의 텍스처 행렬은 모두 단위행렬이며 변환 결과는`[u,v,0,1]`이다. shader에 의한 좌표 변환이나 projective division을 추가로 가정하지 않았다.

| 보도벽 stage | 텍스처·가용 바이트 | CPU 유효 샘플러 |
|---|---|---|
| default,mode0(M_modulate) | sidewalk/color.png,512×512;RAM 부재;파일561,437B 보관 | U/V repeat,min trilinear,mag linear,anisotropy8 |
| normal,mode9(M_normal) | sidewalk/normal.png,512×512;RAM1,048,576B·파일632,706B 보관 | U/V repeat,min/mag linear,anisotropy1 |

위 이름은 고정 Panda1.10.13 헤더의 열거값과 대조했다. 두 stage의 CPU sampler 값은 각각 texture default와 같았다. 이것이 GL에 실제 적용된 sampler 객체나 mipmap/미분값을 입증하지는 않는다. 보도벽 Material은 존재하지만 ambient/diffuse/emission/specular/basecolor는 모두 미정의이며 shininess0이다. 미정의를 검정 또는 노란 색으로 대신 해석하지 않았다. 원거리 SkyboxMesh 후보106은 중심 거리18,718.442017,UV약`[0.856733610466,0.373623362079]`이다. skybox.jpg는8192×4096,파일1,413,364B를 보관했고 RAM은 부재했다. 세 텍스처 모두 허용된 읽기 전용 MetaDrive assets 루트의 실제 파일이다.

오프라인에서는 SHA로 묶인512×512·8bit RGBA PNG 두 개만 OpenCV5.0.0으로 해독했다. color.png의 채널별 최솟값은`[53,47,22]`,최댓값은`[236,228,216]`이며 노란 목표RGB와 과거 회색RGB가 그대로 일치하는 원본 texel은 각각0개다. 색상 파일의 RAM은 없으므로 업로드 바이트 일치를 주장하지 않는다. 노멀의 기존 RAM은 PNG를 수직 반전하고 바이트 채널을BGRA로 놓았을 때 전체가 정확히 일치했다. 이는 두 CPU 바이트 배열의 수치적 관계이며 GPU 업로드·fragment 출력의 증거가 아니다. UV에 repeat 산술만 적용한 두 원점 가정의 점 표본도 별도 기록했으며 mipmap·anisotropy·shader·색 공간·조명을 재현한 결과로 사용하지 않았다. 따라서 원본 texel에 노란RGB가 없다는 사실로 shader나 텍스처 원인을 배제할 수 없다.

전체 원본14이미지를 과거 두 trial의 첫7자세28이미지와 해제·해시·픽셀 비교했다. Road4의 변경은 이전 PR135와 같은 두 픽셀이다: `(175,359)`에서`[174,169,166]→[140,143,75]`,`(555,454)`에서`[171,166,159]→[131,142,78]`,최대 채널 차이91이다. 첫6자세의 나머지11이미지와 Wide7은 일치하고 Road7은 과거 노란 분기 전체 SHA`5289613b610abe2270b4e7d98c106608689c55c216b2085d439eb39eec571adb`와 같다. **이번14이미지는 직전 PR135의14이미지와도 모두 완전 일치했다.** 이 관측만으로 결정론·원인·관찰기 무영향을 증명하지 않는다. `material_complete=true`는 선택한 CPU 상태 수집 완료이며,`source_image_equivalence=false`,`renderer_diagnostic_passed=false`는 유지한다.

단일 전체 변경 검토의 Important3개와 효과상 Important로 재분류한 availability 항목1개는 한 번의 RED→GREEN 단계로 수정했다. 잘못된 RenderState 결합,누락/비유한 재질,잘못된 무압축 열거값,모순된 RAM/파일 가용성을 거부한다. 새 테스트17개와 관련 CPU 회귀116개·actionlint가 통과했다. 정확한 실행 소스 canonical push43958000289/PR43958012762의 네 작업이 모두 통과했고,양쪽 단위 로그는 각각1,999개·7개 건너뜀이다. 로컬 SDK/Panda/GLX/공식 모델 실행은 없다.

산출물14273950515은16,468,042B,ZIP SHA`1fa322b6633e3bb4a4090174bfb2a30172f81d022748caf84aac9b54ed5ca7a2`로 API와 대조했다. 안전한 경로·해제 크기 제한을 적용하고 원본50파일의 크기·SHA·보관 위치를 색인했다. JSON/JSONL/스택23개는 Git에,원본 RGB·geometry.npz·텍스처 바이트·일반 로그27개는 Actions와output에 보존했다. 독립 분석과 재실행 가능한 CPU 분석 스크립트도 별도 해시 색인에 있다. 원본 체크아웃과6개 byte/mode pin,이전31개 디렉터리/3,846개 증거 파일을 보존했다.

다음 원인 구분에는 실제 draw/shader 입력·텍스처 샘플과 fragment 출력의 연결이 필요하다. 이번 CPU 상태는 GPU 소유권·실제 shader/texgen/미분/LOD/MSAA·깊이 attachment를 입증하지 않으며,고유 원인·수리·기존 행렬 통과로 승격하지 않는다. 추가 렌더러 재실행·모델 추론·환경/레지스트리 게시·main 병합은 하지 않았다.

근거: [독립 검증](evidence/sdk3-pixel-material-01/actual/independent-observation.json),[재질·UV 수치](evidence/sdk3-pixel-material-01/actual/material-analysis.json),[PNG 수치 검사](evidence/sdk3-pixel-material-01/actual/png-numeric-inspection.json),[과거 원본 비교](evidence/sdk3-pixel-material-01/actual/source-prefix-pixel-comparison.json),[직전 단계와14이미지 일치](evidence/sdk3-pixel-material-01/actual/prior-phase-image-comparison.json),[원본 보관 색인](evidence/sdk3-pixel-material-01/actual/retained-index.json),[파생 분석 색인](evidence/sdk3-pixel-material-01/actual/derived-analysis-index.json),[단일 검토](evidence/sdk3-pixel-material-01/wholebranch-review.md),[판단 장부](evidence/sdk3-pixel-material-01/ledger.md). 최종 문서 커밋 CI 및 초안PR136·기존PR135·main·원본 보존 영수증은`output/stage7-sdk3-pixel-material-01/final-closeout/verification.json`에 별도로 기록한다.
