# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — scoped builder02

검증된 전용 bwrap backend04의 [실제 증거 PR60](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/60)를 전제로 별도 builder02를 준비한다. 기존 builder01과 diagnostic01–04는 소진 상태로 보존하며 재실행하지 않는다.

새 v2 controller는 소스·요청·완전한 단일 request-only activation delta·유일 run/attempt를 확인하고, 같은 새 job에서 private helper/profile을 다시 검증한다. probe/candidate는 서로 다른 device의 빈256MiB noexec tmpfs를 사용한다. probe marker가 candidate에 남지 않는다. 실제 candidate argv는 기존 SDK에서 helper 경로만 바꾸며 host /usr overlay를 추가하지 않는다.

원래 입력51개/109285137B, source52개, rootplan self SHA5371b2ba1e56fa15bc3068e8e579268b44f86091f7ed7a8e8d11fdb7a8c4838d 및 JSON8570595B/SHA835121e2a4bb7e6996a94d1152209c5921f874d75454a19ee8c52b5189f85a25를 유지한다. 후보 Python3.11.18 원래 prefix/startup/venv/offline build/smoke와 source/wheel 검증을 변경하지 않는다. 후보 실행은 새 job 격리와 root FD 검증 뒤에만 허용한다.

별도 정해진 네 root(workspace/build/probe-build/closed-build host-helper)의 available contents를 기존 nofollow retention 한도 내에서 보존한다. 기존49 workflow와 이전 helpers/tests/policies는 수정하지 않는다. profile 전용 경로 외 기본 정책/sysctl을 변경하지 않는다. 모델/ORT/GL/과학 native/main merge/Cloud 게시를 하지 않으며, 성공한 wheel도 full-lock/image/native readiness로 승격하지 않는다. 실제 실행은 소스 검토·기본 CI 뒤 새 요청02를 등록한 후 기록한다.

독립 검토d0d9600 C0/I0/Minor1(BS-M1: valid retention delegation fixture 보강). 현재 네 root/출력/deadline 전달과 후보 argv/입력/격리 gate는 별도 검토자가 확인했다. 집중10 PASS/1.051초, root 전체874 PASS/7skip76.420초. [검토·판단·비용](evidence/STAGE7_ENGINE_CLOCK_BUILDER_SCOPED_PREPARATION_REVIEW.json)에 남겼으며 원격 CI/실제builder02는 별도 확인 대상이다.

실제builder02: activationad25f636cc00e27aa29c5a0612f392d24cae0600, workflow417258597/[run43427237320](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43427237320)/job131891557480, attempt1/유일 실행1. 2026-11-13 21:40:56–21:43:30 Asia/Seoul. 원격 terminal FAIL, 보존/upload SUCCESS; 요청02 소진·재실행 금지.

같은 새 job의 scoped qualification은 SUPPORTED_SCOPED_PROFILE이었다. 입력51개109285137B 모두 전송·hash 검증됐고351872090B/12723node 후보 root의 staging/path/open-FD 검증이 통과했다. 독립 소비자도 보존 TAR 전체 hash/metadata와 rootplan 모든 node 및51원본 입력을 대조했다. 대상 Python은 시작됐지만 driver namespace gate에서 종료됐다. stdout99B/SHA40f8525bb78487faa6438ae6862d032ddc5b66b862a4db6d352764e5bd2ade4f가 공개 고정 wire `{schema:builder-driver-failure-v1,status:FAILED,code:UNSUPPORTED_NAMESPACE,steps:[]}`의 canonical bytes와 정확히 일치한다. 따라서 VENV/ENSUREPIP/TOOLS/BUILD/SMOKE는 미진입이고 wheel은 없다. 빈 build 디렉터리는 보조 확인이며, 단순한 파일 부재에서 실행 수치를 추정한 것이 아니다.

기존 gate는 UID/GID, readonly flags, child-visible user.max_user_namespaces의0/1 whitelist를 같은 코드로 거부하고 실제 값을 저장하지 않는다. 어느 값이 실패했는지 아직 알 수 없다. bwrap은 부모 namespace limit을 설정하고 그 아래로 들어간 뒤 실제 추가 unshare 실패를 검사한다. child-visible 숫자만으로 계층적 제한을 판정하는 대리 조건 대신, 새 owned driver에서 실제 조건과 추가 userns 생성 거부를 기록·검증할 필요가 있다. readonly/quota/cap/network 조건은 유지하고 기존driver bytes와 원래 실패는 바꾸지 않는다.

원본 artifact14037493090 ZIP242295611B/SHAcf18867d5cab62df6f00edf0e3a28f5a505a49c827bdbb7603c95cf1d8bd7551. retained gzip229307520B/SHA7b410974e123546fdcd17d229977655fbe4b59d477c0f2db0bb8a4f7af2c9107, decoded TAR480819200B/SHA8b35b8b62960cf5bd78fa6cf3022ccb7368b9a69d54240863f6b2b50c2bfb001.12905항목(11878file/863dir/164symlink), regular462399995B, 단일 gzip EOF/CRC·zero-only tail10752B·모든 inventory path/type/mode/uid/gid/hash/target을 확인했다. payload를 로컬에서 실행하거나 symlink를 따라 추출하지 않았다. root-files.json의 기존8570595B/SHA835121e2...와 request/source closure/parent/head/유일 실행도 일치했다.

원본 API/log/ZIP/top-level files/decoded TAR는 output/stage7-builder-scoped-evidence/builder-20261113-02/에 보존한다. [결과 영수증](evidence/STAGE7_ENGINE_CLOCK_BUILDER_SCOPED_PREPARATION_RESULT.json)을 참조한다. 새builder03은 owned namespace driver 관측/판정 보완을 검토하고 별도 source/요청으로 실행해야 한다. old16image refsnull/nativeallowance0/Stage7 INCOMPLETE는 유지한다.
