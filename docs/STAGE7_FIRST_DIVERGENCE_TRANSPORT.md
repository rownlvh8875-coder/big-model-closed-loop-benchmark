[확인 기록] MetaDrive × MD-V3 7단계 개발 결과

권한 pipe와 초기 로그 경로의 수정 및 모델 없는 CI 전달 시험 기록이다. 공식 MD-V3 반복성 FAIL을 해결했다고 선언하지 않는다. PR33·PR34는 DRAFT이며 main 공식 모델 호출0, 7단계 미완료 상태를 유지한다.

실제 시험 source는 `910992742c8807ddc280f59b40261f7545b3e9c9`, [run43137405830](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43137405830), workflow415375833/job130915941509/attempt1이다. 기본 CI push43137405558/PR43137465537도 성공해 세 실행 합계5jobs SUCCESS였다. 현재 소스의 기본 unit log는485tests/56.071s/선택적7skips(ONNX/ORT1개,Panda CPU계약6개)이며 별도 ONNX interface job의 generated SMALL graph1test가 통과했다. 새 probe job에는 NumPy/OpenCV만 설치했고 MetaDrive/Panda/ORT/공식가중치·자산 명령은 없다.

아티팩트13907957454 (`stage7-first-divergence-transport`)는 ZIP5,889bytes, SHA256 `8eaacb58de5dd0b402441192d8aa6543813ca21f9b08a714c66406310838afa4`,3members/13,761uncompressedbytes다. probe.json,normal/process.log,early_exit/process.log만 포함한다. 원본 파일을 수정하거나 재압축해 검사하지 않았다. Root API/source/archive/strict-validator 검증은 통과했고 독립 검토는 CLEAR (fresh read-only API/raw/source review)이다.

실제 parentPID2959에서 wrapper2개와 고정 stdlib receiver2개를 순차 실행했다. MetaDrive provider/ORT session/공식 모델 호출은 모두0이다. 두 case는 모델 A/A나 영상 반복성 비교가 아니다.

| case | wrapper/PGID | receiverPID | readFD | 실제 결과 | 로그 | 그룹 회수 |
| --- | --- | --- | --- | --- | --- | --- |
| normal | 3027 | 3039 | 10 | 6769bytes/FIFO/EOF/FDclose,exit0 | 1045bytes | gone/reaped,true |
| early_exit | 3042 | 3054 | 10 | 수신 전 실제exit73,실제BrokenPipeError,stderr marker보존,permit_sent없음 | 550bytes | gone/reaped,true |

normal elapsed2.460361177s,early0.222756338s,total3.053193506s로 case120s(정리6s포함)/total300s 이내다. cleanup_errors는 두 경우 모두[]이며 nonce/PID/UUID/source/runtime 및 log SHA 연결을 확인했다. 로그 한도65536bytes/case와 최종 manifest 포함 전체2097152bytes를 지켰다. 생산 런처를 그대로 사용했고 probe에서만 fixed receiver와 -a 생략을 명시적으로 적용했다. 고정 display충돌 시 실패하며 서버 시작은 wrapper당1회,총최대2회다. 재실행·fallback·모델 실행은 없었다.

현재 actual runner는 **Ubuntu24/ImageVersion20261101.360.1**, Python3.11.18/GCC13.3.0,NumPy2.4.6/OpenCV5.0.0.93이다. 실제 wrapper `/usr/bin/xvfb-run`은2:21.1.12-1ubuntu1.9/SHA256 `48ee444c30fdaaede4cc311644b30e554162e956f949b206858e37eb8ba1ae05`,xauth1.1.2였다. 이전 실패 study의 Ubuntu26/Xvfb21.1.22와 다르다. 따라서 이 결과는 기록된 환경의 IPC와 오류 보존만 검증하며, 이전 동일 환경·그래픽·모델 pipeline 전체의 해결이나 binary/system 동일성을 증명하지 않는다.

수정은 권한 readFD를10이상으로 예약하고, permit 송신 전에 bounded log를 열고, nonblocking 부분 송신과 stdout/stderr 수집을 같은 시간 한도 안에서 처리한다. launch 소요시간을 wait 예산에서 빼고 원래 오류·cleanup 오류를 구분한다. 초기 exit73 case는 wrapper 종료만 기다려서는 서버가 reader를 잡는 경쟁 조건이 있어, 남은 original group을 passive wait/reap한 뒤 실제 pipe오류를 관찰하도록 수정했다. 이 단계는 오류를 인위적으로 발생시키거나 모델 권한 검사를 약화하지 않는다. 생산 `xvfb-run -a` argv·one-use admission·factory/actions/state/converter/default/6-16-10 및 보호13개/기존runtime43개/기존workflow40개는 유지했다. 새 producer/test/workflow를 포함한61개 Gitblob/current-file 해시가 일치한다.

코드 검증은57tests(ec16db7),75targeted+483full/no skips(a00b142),최종 reader-race fix36transporttests(9109927),실제actionlint/5bash-n,태스크·전체브랜치 독립 리뷰를 소스별로 기록했다. 483회 결과를 수정 후 소스로 바꿔 표기하지 않는다. 탐색용 private-case CPU fixture에서 subreaper누락으로 종료된 sleep좀비1개가 PID1에 남은 검증 이력이 있으며, 수정된 최종fixture와 생산run은 subreaper를 켜고 그룹회수를 확인한다. 이 이력은 이번 실제CI의 누수 또는 실제모델 실행을 뜻하지 않는다.

이전 source081a4c6/run43128201225/artifact13904515781은 여전히FAILED_OR_INCOMPLETE다. 모델 호출null/범위0..4,MetaDrive providers미확인0..1,원래 FD/childPID/stderr/state/RGB/output없음이라는 한계를 유지한다. FD3 CPU재현과 이번 FD10 성공으로 과거 계수를0으로 좁히거나 유일한 원인을 단정하지 않는다. [실패 기록](STAGE7_FIRST_DIVERGENCE_DIAGNOSTIC.md)과 [원본 기계 기록](evidence/STAGE7_FIRST_DIVERGENCE_FAILED_STUDY.json)을 참조한다.

Root는 소비된 모델 study를 재실행하지 않고 전용 브랜치의 zero-model probe로만 진행하기로 결정했다. 일회용 pipe를 유지하고FD>=10/조기로그·공유deadline을 사용했으며, 서버 재시도를 막는 probe-only -a생략을 문서화했다. 원격 ref를 문서 checkpoint에서 먼저 만들고 검사한 범위만 push했으며, offline source검증에는 read-only Git명령을 허용했다. 대가는 모델/state/영상 비교가 이번 범위에 없고, fixed display충돌은 재시도 없이 실패하며, 검증에 Git checkout이 필요하다는 점이다.

다음 과학 진단은 변경된 producer를 대상으로 새 source/canary/protocol을 등록한 뒤 별도로 진행해야 한다. 과거 accepted camera source70cf의58-path manifest를 현재61-path 소스로 바꿔 재사용할 수 없다. 실제 runner/Python/NumPy/OpenCV/Panda/ORT/image/source를 gate에서 확인하고 weight다운로드 전에 중단 조건을 유지한다. 원본0/4와 source-a4 strictFAIL,corrected candidate12/12,geometry/physical optics/full-S의 기존 제한을 변경하지 않는다. RGB/I420/ONNX 일치율은 이번 transport시험에서 미실행/해당없음이며 Stage7은 미완료다. Cloud게시·main병합·실차/CAN/CD210/Carrot튜닝·renderer승격·모델순위는 수행하지 않았다.

독립 검토 JSON SHA256 `7c14d244563ca3f3d23522287a10365516809fb6ee4b3e21a82bef5cc5d24bfb`이다. 재현 가능한 API·archive·source·case·제한·판단 기록은 [기계 기록](evidence/STAGE7_FIRST_DIVERGENCE_TRANSPORT.json)에 보존했다. Context/source/tool/unsafe path 사전검증 실패는 안전한 output할당 전이라 디렉터리를 만들지 않으며, 실행이 시작된 뒤의 실패는 bounded prefix/ledger를 남긴다.
