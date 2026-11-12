[확인 기록] MetaDrive × MD-V3 7단계 개발 결과

카메라 원본 검증과 새 모델 진단을 순차 완료했다. 모델 진단은 실제 자식6개·공식 MD-V3 호출24회를 완료했으며, 보존 관찰 A/A의 최초 차이는 step2 raw RGB에 있었다. **이는 진단 증거의 검증 성공이며 원래 반복성 FAIL의 해결은 아니다.**

## A. GitHub 반영

저장소는 `rownlvh8875-coder/big-model-closed-loop-benchmark`, 브랜치는 `fix/first-divergence-post-transport`다. [PR35](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/35)는 PR34 위의 DRAFT이며 PR33·34·35 모두 미병합이다. Canary source는 `65d2958ec80afa190af972d798929042f6bb8f27`, 모델 activation source는 `582cc594d127e9cde5ff3525e50c143f60285f75`다. 후자는 전자의 직접 자식이며 request/acceptance/docs4파일만 변경했다. 최종 문서 커밋은 과학 실행 source로 재표기하지 않는다.

새 workflow/request/context를 등록하고 producer 경로를61개에서62개로 확장했다. 기존 workflow41개, 소비된 request, 보호13개·baseline43개, 생산 런처·카메라·converter·정책·행동·6/16/10 계산 구현은 보존했다. 검토자는 허용된 context 상수·registry 외 구현 AST 동일성을 확인했다. Cloud 게시·main 병합·로컬 네이티브 실행·로컬 공식 가중치 다운로드는 없었다.

## B. 실제 시험

| 항목 | Canary | 새 모델 진단 |
| --- | --- | --- |
| Actions | [43148115766](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43148115766) | [43149053427](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43149053427) |
| workflow/job/attempt | 415459577/130950639709/1 | 415459577/130953643905/1 |
| source별 CI 합계 | 기본4+진단1 SUCCESS,FAIL0 | 기본4+진단1 SUCCESS,FAIL0 |
| 실제 provider/공식 호출 | 1/0 | 6/24(각4회) |
| 원본 artifact ID | 13912517168 | 13912454399 |
| ZIP bytes | 4,875,287 | 27,428,724 |
| members/uncompressed bytes | 12/5,273,958 | 141/187,115,633 |

Canary ZIP SHA256는 `48b72d5857b4409f09d427d95b66b30bd1c9c1eedfefaf066a895893d20d2aef`, 모델 ZIP SHA256는 `370ef36862e3da5bf39064acc732ff1728b0a0a549b6fba77045ce7380a8c748`다. 각 원본을 한 번만 추출했고 API digest·실제 bytes·파일 목록·source/runtime를 Root와 독립 검토자가 확인했다.

Canary는 PID2849/UUID1d418b7908dc4d21b1c902ebde75fc64, 수락2쌍/캡처5회/센서읽기10회(startup제외), ORT session0이다. raw→canvas4/4, 파생 I4202/2가 정확히 재계산됐다. 수렴 receipt의3/2회 시도와 changed/maxdelta0은 이전 전체 이미지가 미보존인 통계이므로 독립적인 전체 픽셀 재계산으로 표현하지 않는다. 실제 graph feed는 null이다.

모델 study는 parentPID3341에서 고정 순서 original0/proxy0/retention0/retention1/proxy1/original1로 실행됐다. Native child PID는3489/3539/3614/3728/3798/3848, wrapper·PGID는3476/3526/3601/3715/3785/3835다.6개 UUID/nonce/source/runtime 연결,24개 trace/bridge/이상 적분 상태 전이, provider closure, 모든 exit0·cleanup_errors[]와 로그 한도를 검증했다. 전체468.141821069s로 등록 한도 이내였다. 실제 API/source/runtime gate→정확한 공식 SHA 가중치 다운로드→study 순서를 확인했다. 재실행·잔여 한도 재사용은 없다.

현재 runtime은 Ubuntu24/ImageVersion20261101.360.1/Python3.11.18 GCC13.3.0, NumPy2.4.6/OpenCV5.0.0.93/Panda3D1.10.13/MetaDrive0.4.3/ORT1.31.1이다. 모델 실행과 canary receipt가 일치한다. 과거 Ubuntu26나 설치 바이너리 동일성을 입증하지 않는다.

보존군의8쌍 원본→16 canvas,8개 파생 I420→8개 실제 parent NEW_IMG SHA가 모두 정확히 재계산됐고88개 array 파일을 검증했다. 이는 각 실행 내부의 재구성 일치율이다. 독립 실행 간 retention A/A는 raw RGB2/8,canvas2/8,I4201/4,raw4출력1/4,plan1/4만 동일했다. 이 두 종류의 일치율을 혼동하지 않는다.

| 반복 대조 | Road canvas 최초 차이 | Wide canvas 최초 차이 | 실제 NEW_IMG SHA 최초 차이 | 추가 관측 |
| --- | --- | --- | --- | --- |
| original0/1 | step2 | step3 | 미관측 | 곡률·가속도·적분 상태 step2 |
| proxy0/1 | step4 | step2 | step2 | 가속도 step2;곡률·위치는4step 내 동일 |
| retention0/1 | step2 | step2 | step2 | raw RGB/raw4/plan/post-state step2,pre-state step3 |

총9개 동일군·관찰군 대조를 원본으로 재계산했다. 고정 순서와 군당2회뿐이므로 관찰자 효과의 인과 비교로 해석하지 않는다. 미관측 controls의 중간 raw/state/output은 null을 유지한다.

보존군 step1은 동일했다. Step2(t=.05)에는 accepted capture pose `(65.80328679516661,0.30605719684545585,heading .10091307127732403,speed8)`, intrinsics, 저장된 pre-state3개·fixed inputs3개가 같았다. 이 상태·feed는 source 재구성 스냅샷이며 실제 tensor interception은 아니다.

다음 수치는 독립 두 실행 사이의 차이이며, 같은 실행 내부의6/16/10 수렴 판정 통계와 구분한다.

| step2 자료 | 달라진 수 | 최대 절대 차이 |
| --- | --- | --- |
| raw Road | 3픽셀/9채널값 | 93 |
| raw Wide | 1픽셀/3채널값 | 6 |
| canvas Road | 3픽셀/9채널값 | 50 |
| canvas Wide | 9픽셀/23채널값 | 4 |
| packed I420 | 13바이트값 | 7 |
| raw4 | 3값 | .0009765625 |
| plan | 562값 | .0625 |
| post-state image/features | 13/11286값 | 7/.03125 |

실제 입력 체크섬은48497357 대48497389(차이32,픽셀 수 아님)였다. raw 횡가속도는−.409912109375 대−.41064453125, 적용 곡률은+.006404876708984375 대+.00641632080078125, 가속도는−.0418701171875 대−.041748046875다. 보존군4step 최대 위치차는2.1362285073773703e−06m였다. 픽셀 상세 보고 SHA256는 `9c290cd8d1c32069ac8a1767d327fceb158bd44d644b77a6f7d7ed78e4aceb0a`다.

코드 검증은 로컬 targeted103/full486(no skips), 실제 actionlint/bash-n PASS다. 현재 source CI unit486개 중 선택 의존성7개(ONNX/ORT1,Panda CPU6)를 건너뛰었고 별도 generated SMALL ONNX1test는 통과했다. 공식 가중치 추론과 작은 테스트 그래프는 별도 집계다.

## C. 원인과 한계

확인된 사실은 차이가 CPU warp/I420 이전의 저장 raw RGB에 이미 존재한다는 것이다. 동일한 intrinsics로 각 실행의 raw→canvas→I420를 정확히 재구성했으므로 이 retained 증거에는 설명되지 않은 CPU 변환 바이트 차이가 없다. 기록된 순서는 raw/input/output·post-state step2,다음 pre-state step3이다.

그러나 GPU buffer/task/shader/depth/동기화 상태와 모든 실제 graph feed를 관측하지 않았다. 같은 이미지를 다시 주입하는 모델 반사실 비교도 실행하지 않았다. 따라서 유일한 GPU 원인·ORT 비결정성 부재·관찰자 효과 부재·이전 Ubuntu26 실패의 유일 원인은 미확정이다. 새 증거는 원인 후보를 raw sensor/render/readback 경계로 좁히는 근거이지 최종 인과 증명이 아니다.

독립 source review PASS의 JSON SHA256는 `80b7c27bb92a91bc540cf211898978b7d3450438b4217c501e08fceb95697a7d`, canary raw ACCEPTED는 `101e51c2c68a2a09c89e478f01fd3be2a57d546cf269a1b716e23b91cf423a71`, 모델 raw ACCEPTED_COMPLETE_DESCRIPTIVE는 `669c7cfe27a644e8301815e4a9c35797b4ed32d12968c905cf147ed951c197e9`다. CPU 파일 검증은 수락된 recorded runtime를 명시적인 replay context로 사용했다. 로컬 native runtime 독립 증명으로 표현하지 않는다.

## D. 최종 게이트

공식 MD-V3 원래 strict 반복성은 **FAIL**이다. 새4step 진단에서도 각 군의 영상 불일치를 관측했다. 수정 후 확대 시나리오는 미실행이며 과거 candidate12/12를 새 소스나 원본 PASS로 바꾸지 않는다. 원본 renderer0/4, geometry original2/4·candidate1/4 및 image gates62PASS/66INCONCLUSIVE를 유지한다. 물리 광학/production ISP/전체 S자 주행 검증은 미완료이며7단계 전체도 미완료다.

이전081a4c6/run43128201225는 소비된 실패로 모델 호출null/0..4,provider미확인0..1을 유지한다. 이번24회로 그 과거 값을 좁히지 않는다. 이번 단계 합계는 camera1+model6=7nativeproviders,공식호출24회이며 main 공식 호출은0이다. PR33·34·35는 DRAFT/미병합,main `48e79a7ed5aedf6daa5a62ff68d2225af7955ef1`,Cloud미게시다.

## E. 후속 순서와 판단

1. 추가 native/model 실행 없이 저장 step2의 raw 차이 좌표·이웃 픽셀·camera/source 이력을 분석한다.
2. raw sensor/render/readback 경계의 GPU/task/shader/buffer 상태를 구분할 최소 관측안을 설계한다. 관측자 대조와 새 source/canary/호출 한도를 별도로 등록한 뒤 실행한다. converter/renderer/default/6-16-10을 근거 없이 바꾸지 않는다.
3. 원인과 수정 근거를 확보한 뒤 원래 strict와 확대 시나리오를 다시 검증한다. 소비된 study를 재시작하지 않는다.

Root의 판단은 새 workflow/request/context 분리(새 CI identity 검증 비용),Ubuntu24·정확한 배포 버전 고정(과거 OS·binary 동일성 주장 불가),새24-call 상한 protocol(최대24회·6children 비용),현재 checkout과 모든 원본 이력 보존(디스크 사용),게시된 부모에서 remote ref 초기화(기본 CI2jobs 추가 비용)였다. 모든 판단과 원본 수치는 [기계 기록](evidence/STAGE7_POST_TRANSPORT_DIAGNOSTIC.json)에 보존했다. 탐색 CPU helper 오류와 수정 기록도 controller 이력에 남겼으며 원본·생산 소스를 바꾸지 않았다.
