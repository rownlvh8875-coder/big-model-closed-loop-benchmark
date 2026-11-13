# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — 전용 bwrap profile 사전점검

요청02의 실제 namespace 생성·AppArmor enforced profile 전환·UID-map EPERM 관측에 따라, 새 trusted primary helper 경로 `/usr/local/libexec/stage7-bwrap`만 대상으로 userns 허용 profile을 검증한다. 기존 profile/sysctl/binary/workflow와 소비된 요청을 변경하지 않는다.03은 별도 run1/attempt1/최대probe2/profile-load1이다.

먼저 SHA로 고정한 bubblewrap0.12.0을 closed build env로 새로 컴파일한다. 설치된 AppArmor parser가 있어야 진행하며 AppArmor package 업그레이드는 하지 않는다. 원본 source와 binary를 보존한다. unchanged strict bwrap namespace/root/build-FD/cap-drop/userns-disable/env 조건으로 installed host Python의 고정 observer를 실행한다. 여섯 namespace 변경·UID/GID0·capability 전부0·허용 env keys·root EROFS·build 쓰기를 모두 확인한다.

baseline이 이미 통과하면 profile을 로드하지 않는다. 알려진 loopback failure hash와 현재 AppArmor 제한/기존 unprivileged profile/전용 profile 부재가 확인된 경우만 새 경로의 profile을 한 번 로드하고 같은 점검을 반복한다. 그 외는 BLOCKED다. profile 후에는 실제 child label까지 확인한다. 이는 helper backend 검증이며 candidate Python/OS staging, progressbar wheel, model/image/scientific 실행 승인이 아니다. Main 미병합·Cloud 미게시, Stage7 INCOMPLETE 판정은 유지한다.

소스 TDD·전체 시험·독립 검토·기본 CI 후 새 요청03을 단일 activation commit으로 등록한다. 실제 결과는 원본 API/ZIP/log·source/binary/profile bytes를 검증한 뒤 추가한다.

독립 검토7c226bf: Critical0/Important0/Minor1. 집중10개를 별도 검토자가 통과했고, root 전체857 PASS/7skip77.949초다. BP-M1(예외 경로의 이전 관측 보존 부족)은 fail-closed 상태의 진단 손실로 Minor 유예했다. [검토·판단·비용](evidence/STAGE7_ENGINE_CLOCK_BWRAP_PROFILE_PREFLIGHT_REVIEW.json)에 기록했다. 실제03 실행과 원격 CI는 아직 별도 확인 대상이다.

실제03: activation a769a59b56d93bf93551835448952478df477813, workflow417191553/[run43416517415](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43416517415)/job131855679633, attempt1/유일 실행1. 2026-11-13 20:22:16–20:22:43 Asia/Seoul. 원격 수집 SUCCESS지만 admission은 BLOCKED_VALIDATION이다.03 소진·재사용 금지.

동일 job baseline은 exit1/stderr61B/기존 loopback hash ed3471f7...였다. AppArmor enabled/restrict1, enforced unprivileged profile 존재/전용 profile 부재를 확인하고 전용 profile을 정확히 한 번 로드했다. 이후 엄격한 argv의 installed-host Python은 exit0/stderr0/stdout612B였다. 다만 validator가 INVALID_PROBE_OBSERVATION으로 거부했고 그 경로에서 parsed 값을 저장하지 않아 정확히 어떤 필드가 실패했는지는 확인할 수 없다. 이를 전체 격리 통과로 승격하지 않는다.

보존된 bubblewrap0.12.0의 bubblewrap.c:3427이 PWD를 새 cwd로 자동 설정함을 확인했다.03 validator는 SDK의 명시 env keys만 인정해 이 프로그램 소유 필드를 빠뜨렸다. 이 소스 결함과 실패 프레임 보존 결함은 새04 확인 요청에서 보완한다. hash/출력 크기만으로 원래 관측값을 추정해 채우지 않는다.

원본 artifact14031284725 ZIP328216B/SHAfaa29840b896207eed7e3a61087722ef150d1ce6e5c9de3a124909d34e8e29cb; preflight.json6487B/SHAb520edefc7bf238c157497c863f23945debd3d9e0761b19169e39cc6fd0c14d5. source.tar.xz126452B/pinned9760d007..., host-helper.bwrap194592B/SHAed290d7b467eba236ff705a83938ecf78a5dc055648ef5420937b9717b29af3e, profile.apparmor175B/SHAe00bd0234d4d2a14a37d6780cab2a4ff080d7b7bd036b2c398f55a3b1903f14e를 원본 보존했다. 다운로드 binary를 로컬에서 실행하지 않았다. 모든 원본은 output/stage7-bwrap-profile-preflight-evidence/namespace-diagnostic-20261113-03/에 유지하며 [소비 영수증](evidence/STAGE7_ENGINE_CLOCK_BWRAP_PROFILE_PREFLIGHT_RESULT.json)의 파일별 hash/CRC/source/request/run/parent/유일 실행 확인을 참조한다.
