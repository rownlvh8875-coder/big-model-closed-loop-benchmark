# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — namespace identity 보완

진단01은 소진됐다. 수집 run43410163534는 SUCCESS였지만 세 worker 모두 생성 직후 namespace 확인에 실패했고 admission은 BLOCKED다. 그 경로에서 after 상태를 저장하지 않아 어떤 확인이 실패했는지 알 수 없다. 원본은 별도 [결과 PR54](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/54)에 보존한다.

새 요청02는 이 관측 누락만 보완한다. 별도 모듈과 workflow를 사용하며 이전46 workflow·01 source/tests는 변경하지 않는다. ctypes 함수의 int ABI와 errno 초기화를 명시하고 unshare(0), USER|NET unshare, 설치된 util-linux USER|NET+map-root-user의 세 경우를 비교한다. self/thread-self namespace readlink/stat/open-fstat 각각의 수치 결과/오류 및 UID/GID map·profile·capability를 보존한다. syscall 성공·실패와 무관하게 after snapshot을 만든다. 네트워크 설정은 하지 않는다.

실제 hosted 결과/출처/원본 검증은 소스 검토·기본 CI·새 등록 후 별도 기록한다. 02도 run1/attempt1/workers3이며 이전01을 재실행하지 않는다. 설치된 util-linux는 자기 UID/GID mapping만 수행하고 root 정책을 변경하지 않는다. 세 경우는 mapping/exec 조건이 다르므로 bubblewrap 전체 경로의 호환성을 보증하지 않는다.

strict FAIL / expanded NOT_RUN / Stage 7 INCOMPLETE, main 미병합·Cloud 미게시 판정은 유지한다.

독립 소스 검토7414f17: Critical0/Important3/Minor1. 관련 없는 journal 기록의 가용성 표기, utility 실패 전 PID 보존, procfs 읽기 오류 구분을 한 차례 RED→GREEN 수정에 반영했다. launcher는 PID와 before snapshot을 먼저 flush한 뒤 고정 util-linux 명령을 exec하며, 실패해도 해당 PID의 kernel 관측을 보존한다. profile/maps/status/sysctls는 수치 errno·읽은 bytes 수·SHA·truncation을 별도로 기록한다. 전체 API orchestration fixture 보강은 NI-M1 Minor로 미뤘다. 상세 finding·판단·비용은 [검토 기록](evidence/STAGE7_ENGINE_CLOCK_NAMESPACE_IDENTITY_REVIEW.json)에 있다.

실제02: activation `e08d152890bee8f1d2004e8e03020383c5f114a0`, workflow417168959, [run43412775071](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43412775071)/job131843040332, attempt1/해당 workflow·branch run1. 2026-11-13 19:54:43–19:54:52 Asia/Seoul. 수집 workflow SUCCESS, 관측 상태 OBSERVATION_INCOMPLETE, admission BLOCKED; 요청02 소진·재사용 금지.

NOOP은 모든 namespace identity가 그대로였다. RAW USER|NET은 return0/errno0으로 생성됐고 readlink user4026531837→4026532316, net4026531833→4026532317이 self/thread-self 양쪽에서 바뀌었다. 이후 real UID/GID65534, 빈 UID/GID map, profile unconfined→unprivileged_userns(enforce), CapEff/CapPrm000001ffffffffff가 관측됐다. readlink는 성공했지만 stat/open은 모두 EACCES13이었다. 따라서01의 stat 기반 admission 중단을 namespace 생성 실패로 해석하면 안 된다.

설치 util-linux는 launcher PID2157의 before snapshot을 보존한 뒤 exit1이었다. stderr66B/SHA6b50086233b9e3c0f8f5ac5e8094da06d7a05f1c3be0b88baf49578943392a94가 공개 literal `unshare: write failed /proc/self/uid_map: Operation not permitted`와 newline까지 정확히 일치했다. 후속 snapshot은 NOT_RUN이다. 커널 기록은 두 PID2156/2157의 userns_create AUDIT를 포함한다. 이 증거는 프로필 전환과 UID mapping 거부를 보여주지만, 특정 AppArmor rule이나 과거 bwrap netlink errno까지 확정하지 않는다.

artifact14030466572 원본 ZIP37319B/SHA99571654741e1882a389f305d0b5869a0514189bcab15d3d895c8872c2f37adf, 단일 identity.json37179B/SHA66d84bc2ad6daf96c88ca1ece14c6f63d7b37582a3483f49c0ea1123ee00cacb. API digest/실제hash/CRC/경로·크기/source closure/activation 부모/request/run/head/attempt/유일 실행을 검증했다. 모든 원본은 `output/stage7-namespace-identity-evidence/namespace-diagnostic-20261113-02/`에 보존한다. [소비 영수증](evidence/STAGE7_ENGINE_CLOCK_NAMESPACE_IDENTITY_RESULT.json)을 참조한다.

소스1d07c70 기본 CI push43412404272/PR43412443741의 네 job 모두 SUCCESS/attempt1/artifacts0, 로컬847 PASS/7skip이다. 다음은 이 관측을 근거로 검증한 전용 bwrap 경로의 userns profile을 분리해 사전점검하는 별도 요청이다. 전체 격리·wheel/image·과학 실행 성공으로 승격하지 않는다.
