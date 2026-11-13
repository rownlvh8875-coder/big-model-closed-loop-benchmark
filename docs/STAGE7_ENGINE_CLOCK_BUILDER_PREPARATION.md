# Provider-free builder preparation — authentic terminal preflight failure

2026-11-13 Asia/Seoul. 등록한 실제 원격 작업은 격리 네트워크의 loopback 주소 설정에서 `RTM_NEWADDR / EPERM`으로 종료됐다. 대상 Python·OS·progressbar 입력 전송, staging, bootstrap, wheel build/smoke는 시작되지 않았다. 요청은 소비됐으며 재실행·권한 fallback·정책 완화를 하지 않았다. Stage7은 **INCOMPLETE**다.

## A. 저장소·소스·요청

저장소 `rownlvh8875-coder/big-model-closed-loop-benchmark`. 소스 Draft [PR50](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/50)의 최종 checkpoint는 `b0bfc46a8fb151897cec8f9db47965a39af66944`다. 실제 독립 검토96e97dc(C0/I5/M2), 단일 Important 수정9aaca760/843fb749, 독립 재검토 없음의 구분을 유지한다.89집중/815전체 CPU시험 PASS, 선택 의존성7skip이다.

새 요청 `builder-20261113-01`은 소스28파일을 승인 checkpoint와 byte-for-byte 비교하고51개 입력109285137B를 등록했다. 이전7전송 합계에는 PyPI metadata3개가 포함됐으므로, 이번 입력은 Python92610561B+46debs13570700B+source/tool4archives3103876B다. 초기 합계 불일치는 요청/워크플로 작성·실행 전에 검증에서 막혔고 새 계획의 값만 바로잡았다.

활성화 branch `prepare/engine-clock-builder-20261113-01`은 실제 producer `78deaec1a3158889f0f90ede159b9466bfc9b194`를 로컬에서 확정·기록한 뒤 한 번만 push했다. 요청 SHA`5b5ce1de1b00b963c781c2e1b2f46f44b716179be7f7b99295c910dc2080e18a`, workflow SHA`80d9af523f3eb59bf554e6d21d7e94eb590a5b36187ca540de9322582086fc4c`. 이후 증거 branch는 `evidence/engine-clock-builder-preparation`이며 활성화 branch는 변경하지 않는다. [등록](evidence/STAGE7_ENGINE_CLOCK_BUILDER_PREPARATION_REGISTRATION.json), [결과](evidence/STAGE7_ENGINE_CLOCK_BUILDER_PREPARATION_RESULT.json), [실패 binding](evidence/STAGE7_ENGINE_CLOCK_BUILDER_PREPARATION_BINDING.json), [audit](evidence/STAGE7_ENGINE_CLOCK_BUILDER_PREPARATION_AUDIT.json)을 분리했다.

## B. 실제 Actions·artifact

| 구분 | Run / job | 실제 결과 |
|---|---|---|
| 최종 소스 push CI |43386207237 / unit131755190312, SMALL131755189688|815/69.852s/7skip +1/0.049s, 모두PASS|
| 최종 소스 PR CI |43386214092 / unit131755210756, SMALL131755210996|815/46.434s/7skip +1/0.047s, 모두PASS|
| 실제 preparation |[43389231348](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43389231348) /131764894606 /workflow417016407|attempt1, FAIL, branch별 해당 workflow run1개|

Preparation은 16:55:25~16:55:46 KST, 총21초였다. source/API/unique-run guard와 pinned host helper 준비는 성공했고, mandatory namespace preflight가 실패했다. 보존·upload 단계는 성공했다. 실제 artifact14019513519, `engine-clock-builder-20261113-01`,582689B, SHA`977a9e8c3432e51ef0696b3793aa447f72be6ab41b19e58a37de237ba133ce62`가 API digest/size와 일치했다. 소스 CI는 attempt1/artifacts0이다. 이전 소스3ee2954의 CI4PASS는 audit의 과거 기록이며 최종 b0bfc46 검증과 혼동하지 않는다.

새 원본 run/job/artifact/workflow/tree APIs, log ZIP, result ZIP, top-level extraction, decoded TAR는 `output/stage7-builder-preparation-evidence/43389231348/`에 보존했다. 기존 archive·workspace는 삭제하거나 재다운로드하지 않았다.

## C. 독립 확인한 사실과 남은 불확실성

5개 ZIP member가 정확히 `preparation.json`, `source-closure.json`, `retention.json`, `retained-inventory.json`, `retained-workspaces.tar.gz`다. 요청 원본 byte가 같고, source28파일이 승인 b0bfc46·실제 producer78deaec·원본 GitHub tree와 모두 일치했다. wheel과 root-files artifact는 없다.

내부 gzip527425B/SHA`afca2bf16d2afcbc4c94207a823ee16f18b824ce372f55cfe576248996b9fc5d`를 검사했다.120항목(91file/27directory/2symlink), regular bytes1241638 전체의 path/type/mode/uid/gid/hash/link가 inventory와 일치했다. 단일 gzip EOF/CRC와 TAR의 zero-only tail4608B를 검사했다. 물리 TAR1331200B/SHA`18381b66fc67ec80a971491278356e80cefce9f570a2a851d4697801a099a09d`. symlink를 따라 읽거나 archive payload를 실행하지 않았다.

공식 bubblewrap source126452B/SHA9760d007와 실제 설치본에 대응하는 보존 binary SHA`c09c5c5d549cb18ddf3e6f780a718d0a4b1e15039be1a1e220f8c82300521730`가 일치했다. version0.12.0/options 검사, 빈256MiB tmpfs의 type/device/inode/owner/flags 검사, host available disk91974352896B는 통과했다. 관측 kernel은 `7.0.0-1017-azure`다.

Trusted host true의 exit1/stderr61B/SHA`ed3471f7900377f86150471417911309833a36d664cb5af7409e139103f67ddf`는 보존된 `network.c:182`의 공개 literal과 C-locale errno1을 조합한 메시지의 SHA와 정확히 일치한다: `loopback: Failed RTM_NEWADDR: Operation not permitted`. 실제 stderr를 다시 수집하거나 production probe를 재실행한 결과가 아니다. 실패 지점은 확인했으나 정확한 kernel/LSM/capability 정책 원인은 미확정이다. 이를 user namespace 전체의 부재나 지원 가능성으로 확대하지 않는다.

소스 대조 중 별도의 latent PF1도 발견했다: capability probe의 capture가 root FD만 넘기고 build FD를 누락한다. 관측된 loopback 오류는 bind-mount 처리보다 먼저 발생하므로 PF1을 이번 실패 원인으로 주장하지 않는다. 이 결함은 별도 source-only 수정/회귀검증 대상으로 기록했다. 소비된 요청을 다시 실행하는 근거가 되지 않는다.

## D. 그대로 닫힌 gate

이번 요청의 component transport0B/0건, target launch0, staging/build/smoke **NOT_RUN**, wheel SHA null이다. 이는 명시적 실패 receipt·검증된 source flow·보존 workspace로 확인했으며, 기록 부재만으로 만든 수치가 아니다. host helper source 준비는 실제 수행됐다. full-lock/image/native readiness는false이고 old16image refsnull/nativeallowance0이다.

기존 producer70/old44workflow bytes/소비된 registry8/old tools·tests·policies·proposal과 raw/controller 이력을 유지한다. 새 provider-free workflow 하나로 total45이며 기존 native workflow나 old4ABBA cases는 재실행하지 않았다. strictFAIL/expandedNOT_RUN/ABBA authentic terminalFAIL/geometry-optics-fullS/Stage7INCOMPLETE가 그대로다. Main merge와 Cloud 게시를 하지 않았다.

## E. 후속 작업과 판단 기록

이 실패는 요청01의 terminal 결과다. wheel이 없으므로 새 full-Python-lock 작업의 입력 조건도 충족하지 못한다. 원격 재실행 없이 PF1 전달 경계를 owned trusted-child fixture로 수정·검증하고, 이후 실제 실행은 지원되는 격리 조건과 새 검토 프로토콜/요청이 확보돼야 한다. 소스 SHA와 실제 producer·최종 증거 SHA를 구분한다.

현재 source24개 판단/비용은 [source audit](evidence/STAGE7_ENGINE_CLOCK_BUILDER_STAGING_AUDIT.json)의 chronological rulings에, 이번 operation 판단/비용은 [operation audit](evidence/STAGE7_ENGINE_CLOCK_BUILDER_PREPARATION_AUDIT.json)에 순서대로 보존했다. M6(review SHA 외부 binding)·M7(reusable deadline 최대값)은 유예 상태이며, PF1은 새로 발견한 별도 Important followup이다. available-workspace 보존은 갑작스러운 runner 소실이나 upstream 내부 transient cleanup의 완전한 이력 보증이 아니다.
