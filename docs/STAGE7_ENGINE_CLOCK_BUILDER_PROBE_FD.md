# Builder preflight FD handoff — source-only correction

2026-11-13 Asia/Seoul. 원격 실패를 분석하면서 별도로 발견한 PF1을 수정했다. `capability_probe()`는 root와 build FD를 argv에 넣었으나 실제 자식에게는 root FD만 보존했다. 이제 실제 target launch와 동일하게 두 검증된 FD만 `pass_fds`로 전달한다. close_fds·환경·namespace/capability/quota·mount·resource 정책은 바꾸지 않았다.

회귀 시험은 helper version/help만 metadata fixture로 대체하고, 실제 bounded capture/Popen을 거친 trusted host Python 자식이 두 디렉터리 FD의 device/inode를 확인한다. 기존 소스는 `UNSUPPORTED_HOST_NAMESPACE`로 실패했고, 수정 후 두 identity가 모두 일치했다. namespace나 다운로드한 도구/Python/package를 실행한 검증이 아니다. 새 요청이나 실제 preflight/target 재실행을 하지 않았다.

기존 실제 요청01/producer78deaec/run43389231348/artifact14019513519는 loopback RTM_NEWADDR/EPERM으로 종료된 소비 완료 결과다. 그 오류는 bind 처리보다 먼저 발생했으므로 PF1을 원인으로 바꾸거나 수정 후 성공으로 재분류하지 않는다. 원본 source/evidence/등록/request/45workflow bytes와 raw/workspaces를 보존했다. [원격 실패 결과](STAGE7_ENGINE_CLOCK_BUILDER_PREPARATION.md)의 당시 code·artifact와 이번 수정 source는 다른 객체다.

집중90/전체816 CPU시험의 실제 결과, 이 별도 source delta의 한 번의 독립 검토와 최종 Draft/basic CI는 새 audit/PR에 기록한다. 기존 source 검토96e97dc 및 그 단일 Important 수정 pass를 재검토하는 절차가 아니다. M6(review SHA 외부 binding)·M7(reusable deadline 최대값)은 그대로 유예한다.

이 수정은 지원되는 backend에서 발생할 추가 FD 오류를 예방하는 source 품질 보완이다. 관측된 loopback 권한 거부의 host/kernel/LSM/capability 정책 원인은 미확정이고, 실제 namespace 지원이나 Python/bootstrap/build 호환성을 증명하지 않는다. wheel/full lock/image/native readinessfalse, old16image refsnull/nativeallowance0, strictFAIL/expandedNOT_RUN/ABBAterminalFAIL/geometry-optics-fullS/Stage7INCOMPLETE가 유지된다. Main merge/Cloud 게시·기존 native/model/default 실험을 하지 않았다. 실제 후속 실행에는 새 검토 프로토콜과 격리 전제 확인이 필요하다.

실제 로컬 결과: 단일 회귀1/0.029s, 집중90/1.355s, 전체816/69.171s PASS(7optional skips). 단 한 줄의 전달 tuple 수정과 이를 검증하는 trusted-child 시험이며, 미래 backend 지원 증거가 아니다. 원격 요청은 추가하지 않았다.
