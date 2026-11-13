# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — 전용 bwrap profile 사전점검

요청02의 실제 namespace 생성·AppArmor enforced profile 전환·UID-map EPERM 관측에 따라, 새 trusted primary helper 경로 `/usr/local/libexec/stage7-bwrap`만 대상으로 userns 허용 profile을 검증한다. 기존 profile/sysctl/binary/workflow와 소비된 요청을 변경하지 않는다.03은 별도 run1/attempt1/최대probe2/profile-load1이다.

먼저 SHA로 고정한 bubblewrap0.12.0을 closed build env로 새로 컴파일한다. 설치된 AppArmor parser가 있어야 진행하며 AppArmor package 업그레이드는 하지 않는다. 원본 source와 binary를 보존한다. unchanged strict bwrap namespace/root/build-FD/cap-drop/userns-disable/env 조건으로 installed host Python의 고정 observer를 실행한다. 여섯 namespace 변경·UID/GID0·capability 전부0·허용 env keys·root EROFS·build 쓰기를 모두 확인한다.

baseline이 이미 통과하면 profile을 로드하지 않는다. 알려진 loopback failure hash와 현재 AppArmor 제한/기존 unprivileged profile/전용 profile 부재가 확인된 경우만 새 경로의 profile을 한 번 로드하고 같은 점검을 반복한다. 그 외는 BLOCKED다. profile 후에는 실제 child label까지 확인한다. 이는 helper backend 검증이며 candidate Python/OS staging, progressbar wheel, model/image/scientific 실행 승인이 아니다. Main 미병합·Cloud 미게시, Stage7 INCOMPLETE 판정은 유지한다.

소스 TDD·전체 시험·독립 검토·기본 CI 후 새 요청03을 단일 activation commit으로 등록한다. 실제 결과는 원본 API/ZIP/log·source/binary/profile bytes를 검증한 뒤 추가한다.

독립 검토7c226bf: Critical0/Important0/Minor1. 집중10개를 별도 검토자가 통과했고, root 전체857 PASS/7skip77.949초다. BP-M1(예외 경로의 이전 관측 보존 부족)은 fail-closed 상태의 진단 손실로 Minor 유예했다. [검토·판단·비용](evidence/STAGE7_ENGINE_CLOCK_BWRAP_PROFILE_PREFLIGHT_REVIEW.json)에 기록했다. 실제03 실행과 원격 CI는 아직 별도 확인 대상이다.
