# MetaDrive × MD-V3 — 실제 PSSM/Chase canary→ABBA 원본 승인

**봉인 실행기 연결과 실제5프로세스/30카메라쌍 검증을 완료했다.** source 검토·CI,
진짜 C원본 root/fresh 승인, 별도 A제어, 실제 ABBA 네 케이스와 원본 재구성이
통과했다. 추가로 **같은 관측 CPU pose/MVP·순서·시계 count·Texture에도 다른 RGB**를
확인했다. 이는 원인 후보를 좁히는 진단이며 **strict0/4FAIL·Stage7INCOMPLETE**다.

## A. 구현·소스·실행 출처

- source62dc0ab2230339eb0cae9519ba3bb7ab59722e2d,
  [Draft100](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/100).
  기존261파일과 검토된 observer/binding 불변,280sourcepins. 검증된 held03의
  여섯 실행 파일을 별도 이름으로 확장하고 callback schema·scope·전체 raw replay를
  연결했다. 전역 monkeypatch·원래 태스크 재등록/정렬·shader 변경은 없다.
- 모든 case에서 clock/Texture는 ON이며, callback만 C_ON 및
  **OFF0→ON0→ON1→OFF1**이다. OFF의 callback events는 null이다.
  callback최대48snapshot/1680namedgetter, clock64KiB+callback256KiB의 encoded
  보관량320KiB를 별도 명시했다. 실제 Python 객체 메모리는 이 수치와 같지 않다.
- C활성화51b5e2f0f6337f44a13ed4278946a2bae28875ff는 source직계 자식/새 C요청만 추가,
  SHAaf7813385adefb3a85a09218409f80b6adfe6de59642b660c4a9598076192da0.
- 실제 closedC·성공 C업로드·terminalSUCCESS 별도attestor·root+fresh 원본 승인 뒤
  live host를 다시 확인하고 A제어8643b72e114cd1d117630433706d1df3098b0511를 추가했다.
  C직계 자식/별도 A요청 하나, SHAe1352587c41737d71fa550373d923bba7e1b4f9141fcd9ebc79887a45abb394b.
  **실제 producer checkout은 C**이며 A는 제어 데이터다.
- 유일한 [실행43584877011](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43584877011),
  workflow418206888/attempt1 SUCCESS. host132417101877 및 별도canary-attestor 모두SUCCESS.
  C승인 시점에는 host/전체workflow가 in_progress였다. 나중 완료를 소급하지 않는다.

정확한 요청·sourceCI·API·작은 원본JSON은
[최종 권위](evidence/STAGE7_RENDERER_TASKS_SEALED_01_RESULT.json)와
[증거 인덱스](evidence/renderer-tasks-sealed-01/proof-index.json)에 보존했다.
요청은 원래 diagnostic Git커밋에도 남겼고 재적용·재실행하지 않았다.

## B. 검증과 실제 비용

source집중15시험PASS/5.210초, 전체1252시험: 실패0/기존7skip/112.724초.
fresh source검토 Critical0/Important0/Minor0, 독립15시험PASS/5.264초.
정확한 source push43584473103/jobs132415913307+132415913475,
PR43584527532/jobs132416076292+132416076584 모두SUCCESS/attempt1/artifacts0이다.
일반 생성 SMALL ONNX CI는 공식 MD-V3 모델 호출과 별개다.

| 정의된 capture 경로 | C | A 네 케이스 |
| --- | ---: | ---: |
| provider 생성/종료 | 1/1 | 4/4 |
| raw→canvas→derivedI420 재구성 쌍 | 6 | 24 |
| RAM읽기/taskMgr.step | 12/12 | 48/48 |
| Texture getter | 48 | 192 |
| clock snapshot/getter | 48/96 | 192/384 |
| callback state/named getter | 48/1680 | 96/3360 |
| 명시한 observer getter 합계 | 1824 | 3936 |
| output파일/항목 | 49/56 | 170/198 |
| 최종 output바이트 | 16566864 | 65724616 |

총5provider/30쌍/5760namedgetter를 소모했고 남은0이다. 이 수치는 원래 엔진 내부
getter·생성자 초기화 tick·vector/array 인덱싱·private matrix복사의 총수가 아니다.
35namedgetter/snapshot은 getPos/getHpr/get_mvp_array3개+getCell32개다.
private matrix생성/assign 각각288회, vector성분864회,array인덱스288회는 별도다.

C phase64.301037400초/operation153.205631973초. A phase223.640813287초,
operation284.644793749초, 제어 대기346.163134961초, A전체630.807928380초다.
종료2026-11-14 **19:34:29.343206 KST**. 이들은 기록된 운영 구간이며 계측 순수
overhead나 전체 캠페인 end-to-end 시간이 아니다. C수치는 뒤의 root/fresh 대기를
포함하지 않으며 대기 비용은 Acontrol 기록에 남는다.

같은 C/A의 전체 identity/lease가 일치했다. AMD EPYC9V45/119flags,
affinity[0,1,2,3]/MemTotal16760332288/image006/kernel/engine/env/resources,
identity00dd2466e6d58ab32644186fb9d6a1684897870f8ffcbbf3f8c3cecbec8165d8,
lease2fae1d66b79e815811256c2365503ab02a1c9f356de973145dc7eea5e53b0836.
4+10메모리 기록·inventory·prefix·3copiedTAR/위상·permit·정상exit/reap/groupcleanup을
확인했다. cgroup peak/limit4GiB·OOM0는 **RSS나 여유 메모리 증거가 아니다**.

## C. 실제 관측과 원인 제한

관측한 세 ON프로세스의36step 모두 실제 PSSM.update call→return→
MainCamera._chase_task call→return이었다. 각 ON에서 pose2상태/MVP3상태,
run_task=True였다. 최초 PSSM 갱신 뒤 wide호출2의 Chase에서 메인카메라 Z가
2.795000076→3.390000105m로 바뀌었고 다음 road호출3에서 MVP가 갱신됐다.
이후 관측한 pose/MVP는 안정적이다. 이 CPU 순서는 igLoop/GPU draw순서가 아니다.

**C_ON–ON0 및 C_ON–ON1의 호출2(wide/capture1)**에서 네 callback경계의
pose·MVP·flag·순서, 네 clock count,Texture 전후값이 같았지만 raw(544,352)가
**[97,100,61]→[83,90,26]**로 달랐다. 두 비교 행에 같은 한 전이가 나타난 것이다.
독립적인 두 원인 실험으로 세지 않는다. 절대 clock time은 다르며 같은 숫자
count/관측 상태가 같은 물리프레임·완전한 GPU상태를 뜻하지 않는다.

| A 비교 | raw+canvas 변경 픽셀/비교 픽셀 | 최초 raw/canvas/I420 차이 |
| --- | ---: | --- |
| OFF0–ON0 | 35/8559936 | wide1 / wide1 / capture1 |
| OFF0–ON1 | 35/8559936 | wide1 / wide1 / capture1 |
| OFF0–OFF1 | 35/8559936 | wide1 / wide1 / capture1 |
| ON0–ON1 | 0/8559936 | 없음 |
| ON0–OFF1 | 0/8559936 | 없음 |
| ON1–OFF1 | 0/8559936 | 없음 |

35는 raw6+canvas29다. OFF/ON은 **callback계측**을 가리킨다. OFF1도 ON들과
같으므로 이를 계측의 인과 효과나 중립성으로 단정하지 않는다. 과거 clockABBA03의
35픽셀과는 source/host/treatment가 다르므로 같은 실험이나 같은 원인으로 합치지 않는다.
같은 pose별 전체RGB 상태수는 road0:3/wide0:4/road.05:2/wide.05:1이며
큰 첫 상태도 보존했다. 첫 capture삭제나 pixel교정은 없다.

[저장 바이트 CPU 분석](evidence/renderer-tasks-sealed-01/saved-analysis.json):
200767B/SHAedd8c198b1d034452c695fe83176f96cb313d19866c1a51215e6939e5ed042c4,
raw논리보관104806080B/128MiB. OFF0→ON0에서 I420변경은 capture1:14값/합−43,
2:0,3:0,4:14/+43,5:5/−21,6:0이다. private사본의16subset도 계산했고 원래
endpoint와 일치했다. **현재 subset 전체는 fresh검토자가 독립 재계산하지 않았다**.
모델 counterfactual이나 실제 graphfeed 변경·모델 출력 예측으로 사용하지 않는다.

현재 결론은 관측한 CPU서명이 RGB를 유일하게 구분하지 못한다는 것이다.
실제 shader입력·GPU shadow/HDR/resolve·igLoop·RAM 완료 프레임의 연결은 아직
측정하지 않았다. MVP만 강제 고정하거나 태스크 순서를 바꿀 수정 근거는 없다.

## D. 원본·검토·보존

| 원본 | artifact ID | ZIP 바이트 | SHA256 |
| --- | ---: | ---: | --- |
| C | 14109786893 | 339202562 | 8a2743b188a43137201affe690e45253de6fcd9b32b557e6f15d17e750998477 |
| C attestation | 14109534917 | 1273 | 1c1e5f710fd2394c15a685392000081930812711ecb6a389ef87f8945d977eaf |
| A | 14110187940 | 406089326 | b20946a129b647bb450d452ec1bd84d3e7f4828540c0d45c70025f0f43a037e8 |

C103/A366원본항목의 CRC·바이트·SHA 및 전체 raw replay가 root+별도 fresh 검토에서
확인됐다. [C 실제 검토](evidence/renderer-tasks-sealed-01/canary/fresh-raw-review.md),
[A 실제 검토](evidence/renderer-tasks-sealed-01/abba/fresh-raw-review.md).
Root의 최초 fresh=false 기록과 별도 실제 fresh=true 기록을 함께 불변 보존한다.
C의 Important비용 주석은 correctness결함이 아닌 측정 한계로 판정해 위에 명시했다.
새 코드/원본 correctness Critical·Important·Minor 보류는 없다.

인덱스297proof/268원본JSON/7071318B와 작은 root·API·Git·CI 기록을 저장했다.
큰 설치 manifest8MB의 두 복제는 건너뛰고 기존 image006원본을 참조한다.
ZIP·PNG·I420·TAR는 output/stage7-renderer-tasks-sealed-01에 보존하며 Git에 넣지 않았다.
현재 raw 검토는 실제 live설치 tree를 다시 스캔하거나 native를 재실행한 검토가
아니다. 원본 runtime/permit 기록과 공통 CPU변환 helper에 대한 신뢰 경계가 남는다.

## E. 다음 게이트와 최종 원격 마감

다음 조사는 같은 서명인데 다른 RGB가 나온 지점의 **CPU shader입력→GPU shadow/HDR/
resolve→현재 RAM** 연결을 분리해야 한다. readback/동기화 관측은 자체 효과가
있으므로 별도 source·허용량·독립 대조와 원래 의미 보존 검증이 필요하다.
소모된 이번 요청을 다시 실행하지 않는다. 검증된 원인·수정 없이 공식 모델 strict
게이트를 통과했다고 주장하지 않는다. geometry/physical optics/determinism/
driving performance/fullS는 별개이고 Stage7은 미완료다.

소유 evidence Draft의 최종 HEAD·정확한 push/PR CI·미병합 판정은 해당 PR본문과
output/stage7-renderer-tasks-sealed-01/closeout/final-verification.json에 기록한다.
source62dc0ab와 실제producerC/controlA/evidenceHEAD를 구분한다. main병합·
Cloud/registry게시·공식 모델/ORT실행은 없었다.
