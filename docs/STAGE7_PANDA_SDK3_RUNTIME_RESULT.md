[확인 기록] MetaDrive × MD-V3 7단계 개발 결과

2026-11-16 KST. 저장소 rownlvh8875-coder/big-model-closed-loop-benchmark, 브랜치 feature/panda-sdk3-runtime-v1, [Draft PR131](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/131), 기준2435bf438651916ff496c07d334ba264d56a71bc. 실제03 검증 소스는 f3bb85b6e692ecfd1efb54e2af3aabb93beb3c3e, 실제04 보완 제어기 소스는 fce974e962dbc75b2abbb95fd1fd97ff064c334e이다. 최종 문서 HEAD는 마무리 확인 기록에 별도로 남긴다.

사용자가 남은 SDK/SIGABRT·GLX·공식 모델 세 작업의 연속 실행을 요청해 별도 새 코호트로 진행했다. 기존에 소비된 모든 요청·실행·판정은 유지했다. 로컬 Docker는 ENOSPC로 컨테이너 파일시스템 생성 전에 실패했고 대상 SDK는 실행되지 않았다. 원래 체크아웃은 보존하고, 소스 작업은 /dev/shm의 Git 사본에서 수행했다. 실제 대상은 GitHub Actions 임시 실행환경에서만 실행했다. 환경·레지스트리 게시와 main 병합은 하지 않았다.

| 범위 | 확인된 결과 | 한계 |
|---|---|---|
| 실제 SDK3 로딩·버전 바인딩 | 세 실제 SDK3 추적에서 기존110개 항목 각각110/110 libc 연결 관측. 코어/GSG 생성까지 도달, 이전SIGABRT 미관측 | 전체 C++ ABI나 일반 네임스페이스 동작의 보증은 아님 |
| 소프트웨어 GLX | 독립 SDK3/ShowBase2개 프로세스에서 각2개8×8RGB 도전값의192바이트 전부 일치, 종료0/정리 성공 | 원본964×604 센서·물리GPU·전체 렌더러 동등성을 이 작은 시험만으로 인정하지 않음 |
| 공식 모델02 | 실제 모델 프로세스1개가 ORT 로딩·MetaDrive 초기화 후4GiB 한도에서OOM/SIGKILL9 | 완료된 trial/strict pair 없음. 성공으로 재분류하지 않음 |
| 공식 모델03+04 | 네 조건 모두 재계산: 3/4 PASS, 전체FAIL | 최초 차이는 원본RGB 경계; 확대검증·Stage7완료 불가 |

SDK3는1052968B/SHA27cd80fb1c06feaa7da8b5658cce918d1e3ab71c304a0c0ce42e30688ac008f3이며 기존 인증 이미지의 libpandagl.so 경로에 읽기 전용으로 덮어 연결했다. 원래 이미지1727678464B/SHA4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698와 설치된 원래SDK992200B/SHA8d302ae2a610b56db4f7feca08fd736004cf6d3d9650fdb9834f19389a0b7342를 수정하지 않았다. 새SDK 빌드는0이다.

실제01은 [run43824577772](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43824577772), source013e54a12f4df94b3cc425104ce1c8d07a6e3780/activationaa36f89049458a7329938b2e6cd39980693c0e5c, 작업133155215158/attempt1FAIL이다. 산출물14205942495는2663566B/SHA0a03763f49bef35ed0ebb7aed758e7fb0138d8a4c18afc624067c7ad2944d518이다. 세SDK3 자식 모두 코어·GLX·정리 체크포인트에 도달했으나, 여섯192B 프레임은 모두0이고 종료1이었다. Xvfb를 Panda의 C++ 종료 처리 전에 끝내 X fatal 오류를 유발하는 검증기 수명 문제가 확인됐다. 별도 외부 소유자가 Panda 자식의 완전한 종료까지 서버를 유지하도록 수정했다.

실제02는 [run43827976143](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43827976143), source3bc46af75a2ef1f8cec415139c3688e0c14428ed/activation523d1525c9a960a804605dabfb7b8a38ac96d906, 작업133166205464/attempt1FAIL이다. 산출물14206869856는4627908B/SHA c6db9f8cb5a4e26f570fce6a8e91d6da96b5ec0c45f15d33f263bc20770a6d3b이다. 모델OOM 때문에 전체 작업은FAIL이며, 별도로 통과한 GLX 부분만 원본 바이트에서 재검증했다.

| 실제02 대조 | 종료 | RGB 결과 |
|---|---:|---|
| 원본 게시 휠/수동 생성 | 0 | 두 프레임 검정, 도전값FAIL |
| SDK3/수동 생성 | 0 | 두 프레임 검정, 도전값FAIL |
| 원본 게시 휠/표준ShowBase | 0 | 두 도전값 정확 일치 |
| SDK3/표준ShowBase 독립1 | 0 | 두 도전값 정확 일치 |
| SDK3/표준ShowBase 독립2 | 0 | 두 도전값 정확 일치 |

대조용 원본913073B/SHAf38e0734a5344eda9a11e3024695febf2cea0177aa80985b67ceef5837a088d7은 기존 이미지의 원본 레이어에서 DATA로 추출했고 이전 게시 휠 근거와 일치했다. 원본 대조군을 SDK 성공으로 계산하지 않는다. 두 수동 생성 결과가 원본/SDK3 모두 검정이고 표준 생성은 양쪽 모두 성공해, 검정 영상이 SDK3에만 발생하는 문제라는 가설은 배제됐다. 표준 생성은 depth24/back_buffers1, 수동 생성은 해당 요청이 없었다. 어느 개별 속성이 직접 원인인지까지 단정하지 않는다. 제품의 원본 렌더러·카메라를 변경한 것이 아니라 검사에 표준 Panda 생성 경로를 사용했다.

모델02의 실제PID11은 SIGKILL9, DockerOOMKilledTrue로 종료했다. 정리된 Xvfb는 종료0이며 소유 컨테이너도 제거했다. 공식 모델03은 이 실패와 구분해 새8개 프로세스로 시작했다. 02의 실패한 모델 코호트는 수락하지 않고, 두 SDK3 GLX 프로세스의 원본 픽셀·종료·서버 수명·독립 컨테이너만 재계산한다.

실제03은 [run43830776012](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43830776012), sourcef3bb85b6e692ecfd1efb54e2af3aabb93beb3c3e/activation1b9888f1b42b18b3b10ed66131a5c7a0b15fc00d, 작업133175317326에서60분 한도에 도달해 취소됐다. 산출물14212471670/135298B/SHAaed730fb9e709756c48b73d82fe88c15245306427ad526291deb3caa9344dc85를 보존했다. 실제8개 모델 자식이 시작됐고7개trial이 완료됐다. 첫3조건의 독립 쌍은2PASS/1FAIL이며,20261110좌→우는7스텝 원본RoadRGB부터 차이가 시작됐다. 전체4조건 판정은 아래 실제04 보완 결과에 기록한다. 코호트는2seeds×2S장면×2독립 실행,12스텝/8m/s/.12/20Hz이다. 가중치768750198B/SHA35976b11be3904eb78e32f7dc55a6abf8e9433ac5aa391a1998f1e9ce001b199는CI에만 다운로드한다. 원본PSSM/Chase·964×604 RGB·512×256 변환·uint8 I420(2,6,128,256)·raw action·재귀 상태와 정확 비교를 유지한다. 변경한 것은 모델 컨테이너10GiB/호스트 가용12GiB 조건이다. 기존 ORT 연산 설정·모델 수치·입출력·카메라 해상도는 변경하지 않았다.



마지막 조건은 [실제04 run43845729539](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43845729539)에서 완료했다. sourcefce974e962dbc75b2abbb95fd1fd97ff064c334e, activation1573e07218dc5153f168f504592f1f87e4922579, workflow419974420/attempt1SUCCESS, artifact14216386095/291036B/sha256:657c03078b4670a892ae8f52e81fec9067e625cb7003a4d725c9cb72f08f193c. 새 호스트 제어기만 추가했고 f3의 모든 기존 파일·모드는 그대로다. 03에서 완료한 세 조건 전체를 결과와 무관하게 원본 바이트 그대로 가져왔다. 중단된 네 번째 쌍의 첫 실행을 재사용하지 않고 해당 조건에 새 두 프로세스를 사용했다. 따라서 이것은03+04연속 행렬이며, 단일 작업에서8개 모두 완료했다는 의미는 아니다.

| seed | S장면 | 엄격 반복성 | 최초 차이 스텝 | 최초 관측 경계 | 원본 실행 |
|---|---|---|---:|---|---|
| 20261109 | 좌→우 | PASS | — | — | 03 |
| 20261109 | 우→좌 | PASS | — | — | 03 |
| 20261110 | 좌→우 | FAIL | 7 | NATIVE_964x604_RGB | 03 |
| 20261110 | 우→좌 | PASS | — | — | 04 |

네 조건을 원본 보고서에서 독립 재계산한 결과 **3/4, 전체FAIL**이다. 선택한8trial/96회 추론 모두 완료·원래 모델/PSSM/해상도/비교 기준을 유지했다. 네 컨테이너는 각각독립이고, 각 쌍의실제PID는11/24,UUID도서로다르다. 모든 선택trial은 native종료0·Xvfb종료0·OOMfalse·소유컨테이너제거를 확인했다. 03의선택3조건 전파일 바이트 동일성을 다시 확인했다. 판정에 사용하지 않은03의추가완료trial과중단trial도 원본 묶음에 유지했다.

48개 비교스텝의 완전일치: 원본RoadRGB 42/48, WideRGB 43/48, 변환RoadRGB 42/48, 변환WideRGB 43/48, 실제ONNX new_img 42/48, raw action 42/48, 재귀상태 42/48. 선택trial의원본카메라에서검정전체0프레임은0이며, 각12스텝의Road/Wide해시는모두12개고유값을가졌다.

모델프로세스 총시작은02의OOM1 +03의8 +04의2 =11,12스텝완료trial은9,선택행렬은8이다. 선택하지않은03의완료trial1개를성공률이나엄격쌍으로다시계산하지않았다. 최초차이는원본RGB해시경계에서관측됐다. 원본픽셀좌표나단일렌더러원인까지확정한것은아니며,허용오차·이미지재생·PSSM비활성화로판정을통과시키지않았다. 기존 엄격 0/4 PASS·전체 FAIL과 이번 3/4 PASS·전체 FAIL은별도결과로함께유지한다. 확대검증과Stage7완료는불허상태다.

실제03 소스CI는 push43830148858/PR43830155844 네 작업 SUCCESS/1909건/7skip. 실제04 소스CI는 push43844509370/PR43844518229 네 작업 모두attempt1SUCCESS/artifacts0, 두 단위시험 로그 모두1914건/7skip이다. 기존runtime집중20PASS와신규보완집중5PASS. 기존독립검토의네Important항목은한번의RED→GREEN수정으로처리했다. 새호스트추가분의독립검토는Critical/Important0,경미한거부경로테스트보강1건유보이다. 재검토는하지않았다. 최종문서HEAD의정확한CI·PR대조는output마무리확인서에별도로남긴다.

원래 체크아웃2435bf4의8106파일/Git모드와 소스322를 보존했다. 원본 이미지·SDK·후보·이전d21/4045/aaca 판정을2026-11-16 17:32 KST 및 19:08 KST에 재해시했다. 전체 C++ ABI/일반 런타임 매핑/렌더러 동등성/원래SIGABRT의 단일 인과원인까지 포괄하는 성공은 선언하지 않는다. 카메라 기하학·실센서 광학 동등성을 새로 측정하지 않았다. 공식 엄격 반복성의 기존0/4FAIL은 유지하며 이번 03+04 연속 행렬은 3/4 PASS·전체 FAIL로 별도 기록한다. 확대 검증과 Stage7 완료는 아직 인정하지 않는다.

근거: [실제01](evidence/panda-sdk3-runtime-01/attempt-01/summary.json), [실제02](evidence/panda-sdk3-runtime-01/attempt-02/summary.json), [선택GLX 수락](evidence/panda-sdk3-runtime-01/attempt-02/selected-glx-acceptance.json), [판단·비용 장부](evidence/panda-sdk3-runtime-01/ledger.md), [검토](evidence/panda-sdk3-runtime-01/wholebranch-review.md). 대형 추적 로그·ZIP은 각 retained-index.json의 해시로 연결한 output 원본에 남겼다.


최종 보완 근거: [04원본·독립집계](evidence/panda-sdk3-final-condition-04/actual04/independent-analysis.json), [03→04전파일해시](evidence/panda-sdk3-final-condition-04/actual04/retained-index.json), [보완검토](evidence/panda-sdk3-final-condition-04/wholebranch-review.md), [보완판단장부](evidence/panda-sdk3-final-condition-04/ledger.md).
