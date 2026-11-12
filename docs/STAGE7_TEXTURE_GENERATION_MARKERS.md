[확인 기록] MetaDrive × MD-V3 7단계 개발 결과

ON canary와 OFF→ON→ON→OFF 카메라 실험을 각각 한 번 완료했다. ABBA의 첫 OFF만 나머지 세 process와 달랐고, ON 두 개와 마지막 OFF는 6쌍 모두 같았다. ON 표식은 모든 복사의 직전·직후에 같았다. **마커 읽기의 인과 효과, GPU 완료/freshness, 원래 strict PASS는 입증하지 않았다.**

## A. 변경과 실행 소스

저장소 `rownlvh8875-coder/big-model-closed-loop-benchmark`, 브랜치 `diagnostic/texture-generation-markers`, [Draft PR37](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/37)은 PR36 위에 쌓였다. 새 script/test/workflow/request와 문서를 추가했다. 기존 producer62/protected13/baseline43/42workflow/소비된 요청, renderer/converter/action/default/6-16-10은 보존했다. 자체 producer65는 old62+새script/test/workflow이며 mutable request는 별도로 Git에 바인딩한다. 기존 Continuation 문서만 새 결과로 갱신한다.

Canary source **`0a98918e746fe7df9d5502e21db91c3e5cd15396`**, ABBA activation source **`4814794243ca61a96264ebe04f4fb1b82f0eeecf`**다. 후자는 전자의 직접 단일 자식이며 request/acceptance/새문서5경로만 바꿨다. 실행 전에 실제 API·원본canaryZIP·root+fresh 수락·동일runtime·65개Git blob을 확인했다. 결과 문서 HEAD와 실행 source를 구분하며 현재 최종 HEAD는 `git rev-parse HEAD`와 PR37 headRefOid로 읽는다.

신규 script SHA256 `a37e7232441667d535fbad7dafbe5137c523f6931fde25400aaf17a066f43e02`, tests `7d7d8c6bc1e30817e7dc09914683475bc84ead0a1c622cee225cfa00c598bf30`, workflow `0fb338fce4cb33403c3d835f11f98e735f115c9ec6e24fe65269610017f051f8`이다.

## B. 실제 실행·원본·비교

두 native run은 workflow415702769/attempt1/push/Ubuntu24/SUCCESS다. 각 원본 ZIP을 한 번 다운로드·추출하고 모든 멤버를 API digest/크기/실행 source와 대조했다.

| Phase | 실제 run/job | Artifact / ZIP bytes | SHA256 | members / uncompressed bytes |
| --- | --- | --- | --- | --- |
| ON canary | [43177564313](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43177564313) /131045412519 |13925041858 /14,605,800 | `6a8c7a2e3495a5115938d17aee1da8c4e27f4e2ebc1b6350001e0f1090ee1994` |33 /15,795,803 |
| ABBA | [43178394897](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43178394897) /131048107858 |13925716196 /58,403,425 | `e6017f302e6879709bf089aaeca97fde9ca8828764b645c8e4bde473db6f16ce` |129 /63,162,078 |

Canary parent2941/launcher3012/native3024,53.433267887s. ABBA parent2728,157.788560458s; launcher/native는 OFF0=2870/2882,ON0=2979/2991,ON1=3086/3098,OFF1=3192/3204다. 모든 provider가 정상close·exit0·group gone/reaped·cleanup오류0이었다. ABBA case wall time은42.375479469/37.114864249/36.877195352/36.911891241s다.

총 **5fresh providers/30pairs/60observed RGB RAM copies/72sequence readings**, 공식 모델/실험ORT/추가GPU read0이다. 각 sequence reading은 get_image_modified와 get_seq를 각각1번 호출하므로 총144accessor invocations다. Constructor startup sensor activity는 observed counts 밖이다. 기본CI generated SMALL ONNX 테스트는 별도다. 로컬 native/Xvfb/공식 추론은 없었다.

ON 각case의 Road pre=post trace는12/14/16/18/20/22,Wide는13/15/17/19/21/23이다. Canary12행+ABBA24행 모두 pre=post이며 ABBA ON/ON의 절대값·within-read equality pattern도 같다. OFF는 getter0/모든표식null이고 OFF를 포함한 표식 비교는 null이다. 프로세스 사이 절대 UpdateSeq의 같음은 같은 영상/GPU 상태의 증명이 아니다.

| 비교 | 첫 raw / canvas 차이 | 첫 I420 차이 | 6쌍 전체 일치 |
| --- | --- | --- | --- |
| OFF0–ON0 |capture2/Road |capture4 |아니오 |
| OFF0–ON1 |capture2/Road |capture4 |아니오 |
| OFF0–OFF1 |capture2/Road |capture4 |아니오 |
| ON0–ON1 |없음 |없음 |raw/canvas/I420 모두 같음 |
| ON0–OFF1 |없음 |없음 |raw/canvas/I420 모두 같음 |
| ON1–OFF1 |없음 |없음 |raw/canvas/I420 모두 같음 |

차이가 있는 세 비교는 동일한 차이를 보였다. Capture2:Road(254,363)1raw픽셀/max39→canvas2픽셀/max7,I420는같다. Capture4:Road1픽셀/max39+Wide(544,352)1픽셀/max35→canvasRoad2/Wide12픽셀,I42014값/max9/첫flatindex226481,checksum48,398,753→48,398,710이다. Capture5:Road3픽셀/max93→canvas3픽셀/max50,I4205값/max7/첫index24785,checksum48,497,357→48,497,378이다. Capture1/3/6은 해당 비교에서도 같다. 좌표는(x,y),좌상단 원점/raw964×604다. 여섯 비교의 raw/canvas 각각60/72카메라배열,I42030/36쌍이 일치했다. 새 captureindex는 이전 모델stepindex가 아니다.

모든 phase 내부의 raw→실제lenscanvas **60/60카메라배열**, derived I420 **30/30쌍**을 정확히 재계산했다. 신규 I420는 `DERIVED_ONLY_NO_MODEL_CALL`이며 실제graph feed가 아니다. 실제runtime은 Ubuntu24/ImageVersion20261101.360.1/Python3.11.18 GCC13.3/NumPy2.4.6/OpenCVheadless5.0.0.93(cv2 5.0.0)/Panda1.10.13/MetaDrive0.4.3/설치ORT없음이다. 이전 모델 실험의 ORT1.31.1 존재와 구분한다.

Case마다 논리 retained payload28,039,104B,transient 사전추정32,319,072B는32MiB 범위다. RSS측정이 아니다. Frozen disk reservation38,171,904B는40MiB 범위이며 log1MiB/JSON2MiB/dataset192MiB 한도를 지켰다. 각child270s/cleanup포함300s/phase1320s 이내다. 각 isolated Mesa cache는 빈 상태에서50files로 채워졌다. Canary1,661,172B,ABBA1,671,098/1,671,099/1,671,099/1,671,099B다. Route population 증거이며 개별cache hit/바이너리동일성을 입증하지 않는다.

[Canary root](evidence/STAGE7_TEXTURE_MARKER_CANARY.json),[canary 독립수락](evidence/STAGE7_TEXTURE_MARKER_CANARY_REVIEW.json),[ABBA root와 모든비교](evidence/STAGE7_TEXTURE_MARKER_ABBA.json)에 source65/runtime/nonce/UUID/PID/로그/예산/cache 기록을 보존했다. Root JSON SHA는canary `63a9cc4faa23f0a13a02bb89c9aa5f55d22cf03110b923223be3ca9743b3bac0`,ABBA `1a91181a753610f37fcdd71e6d647652e1ec423e67437f05fa4691ed58b3b779`다.

## C. CPU 일치관계와 인과의 한계

추가 native 없이 canary 같은pose의capture5/6을 이전 수락된 retention0/1의 modelstep2와 비교했다. 이전 ZIP SHA와 선택된trial/PNG/packed 원본바이트를 재추출 없이 확인했다. 이전A의 Road는새capture5,Wide는새capture6과 raw/canvas가 정확히 같고,이전B는Road6+Wide5와 같다. 이 두 CPU canvas 교차조합은 이전 actual-input SHA와체크섬48,497,357/48,497,389를 각각 정확히 재구성한다. 실제새동일capture쌍5/5와6/6은48,497,368/48,497,378이며 어느 이전joint입력과도 같지 않다. [Posthoc CPU보고서](evidence/STAGE7_TEXTURE_MARKER_CROSS_HISTORY.json),SHA `2a455f507c9b5e0e63685c8987c949ac3f3ee734c5e5d810d6845c99e3b65ba8`다. 새 모델입력공급이나 모델출력 반사실은 없다.

이는 관측된 카메라별 영상상태의 구체적인 연결이다. 다른capture의 두 카메라를 섞은 CPU 조합을 실제 동시 프레임으로 부르지 않는다. 이전 모델 실험의 graphdelay/ORT/cachehistory와 새camera-only 조건이 다르므로 temporalphase,HDR/resolve/shadow/terrain/LOD/dither/RAM copy 중 유일한 원인이나 물리기제를 판정할 수 없다.

OFF도 common raw retention과 동일wrapper를 쓴다. 원래 비계측 경로의 대조가 아니다. 기존RAMmethod를 한번 호출하고 같은 array object를 반환한다. 고정schedule은retained0의pose0네번+pose1두번이며 retained1의첫pose세번이나6/16/10수렴/모델timing을 재현하지 않는다. 모든6쌍저장/해싱/표식/coldcache/freshprocess는 시간·할당에 영향을 줄 수 있다. 추가render/task/readback/barrier는 없다. 첫OFF와 마지막OFF도 달라 단일고정순서campaign은 마커의 인과효과나 첫case차이의 원인을 분리하지 못한다. 같은표식은 freshness/GPU완료/observer neutrality 보장이 아니다.

## D. 검증과 기존 게이트

초기source `ccb34a6a26cd8b90f0eab1f78b9f9de0eecd4418`의 전체542tests/선택7skip과 T1-R1수정source의46covering·50optional integration/skip0을 구분한다. 수정은 close예외 후 이미 받은raw/canvas를 failure-onlyCPU prefix로 보존하며 provider_closed=false/FAILED를 유지한다. Hardkill 미저장RAM복구를 주장하지 않는다. Task/fix/source전체검토PASS,source전체검토SHA `b183f72c93de97d588797b8695f070f764406f753cdec3a5a5afc66842103fff`다. 실제source기본push43177564041/PR43177608658와 activation push43178395141/PR43178401591의 각4jobs SUCCESS,currentunit544tests/선택7skip(ORT1/PandaCPU6),SMALL ONNX1test별도다. [검증·판단기록](evidence/STAGE7_TEXTURE_MARKER_AUDIT.json)에 정확한job/리뷰/판단을 보존한다. 최종문서HEAD CI는 별도로 조회하며 실험source로 재명명하지 않는다.

Canary fresh수락SHA `e57d9eb33411474013bda59566815e8d77f807e3c74d59e597a721a7b0f85390`다. ABBA와posthoc도 fresh 독립검토 ACCEPTED_ABBA_DESCRIPTIVE/지적0으로 수락됐다. [독립수락 기록](evidence/STAGE7_TEXTURE_MARKER_ABBA_REVIEW.json)의 SHA256는 `d19f8df7d49ef7d17dd73d08dcf9fe671f56dbccf7eb08abe3e723481cd272f8`이다. 최종 전체브랜치 검토는 이 기록 이후 문서포함 HEAD를 별도로 확인한다.

공식 strict **FAIL**,확대시나리오 미실행,원래renderer0/4·역사적candidate12/12·geometry original2/4/candidate1/4·물리optics/productionISP/fullS미검증·Stage7미완료를 유지한다. Main공식호출0/Cloud미게시/PR33–37DRAFT·미병합이다. 과거6native/24officialcalls는 이번 카메라실험 수에 더하지 않는다. 소비된 과거 실패/성공 요청을 재실행하지 않았다.

## E. 다음 순서와 내린 판단

두 one-shot phase는 소비되었다. 다음은 저장 영상과 read-only 설치소스 참조로 카메라별 상태/샘플·시간의 후보 경계를 좁히는 CPU분석이다. 새native가 필요하면 새설계·source·canary·정확한예산을 별도등록해야 한다. 이번 요청retry/연장/남은allowance재사용,임의barrier/tasktick/shader/converter/default변경,strict승격/mainmerge는 없다.

| 순서 | 판단과 이유 | 비용·한계 |
| --- | --- | --- |
|1|ONcanary 후 별도게이트ABBA로 native API를 먼저검증|최대5providers/30pairs,모델pipeline증명아님|
|2|retained0의4+2고정재생/graphdelay없음|모델timing·adaptive수렴미재현|
|3|보존launcher의 고정camera-child치환,이harness만-a생략|permit62/자체65context분리,공식model admission증명아님|
|4|매case 빈isolatedMesa cache|과거sharedcache와 다르고 coldcompile시간영향|
|5|worktree/Cloud게시/mainmerge/기록삭제없음,nativeCI전용|디스크·Draft체인유지|
|6|Task1독립구현·task/fix/source검토,root만Git/CI|추가검토context비용,동시구현없음|
|7|논리memory32MiB/disk40MiB분리|disk+8MiB/case,4case최악174MiB/전체192MiB; 정확한예약38,171,904B로사전정정|
|8|원격branch를 기존게시baseC8에 먼저생성|기본CI2jobs추가,그base에 새native workflow없음|
|9|복구가능close실패 후 boundedCPU snapshot보존|closure미확정 실패자료,hardkill미저장RAM미복구|
|10|이전endpoint와새capture5/6의posthocCPU비교|cross-study혼입,실제동시프레임/새graphfeed/인과phase증명아님|

모든판단은 ledger와audit에 순서·비용을 보존한다. 기존raw/controller history와 본작업의 검토기록도 삭제하지 않았다.
