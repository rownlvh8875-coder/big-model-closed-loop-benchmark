# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — namespace identity 보완

진단01은 소진됐다. 수집 run43410163534는 SUCCESS였지만 세 worker 모두 생성 직후 namespace 확인에 실패했고 admission은 BLOCKED다. 그 경로에서 after 상태를 저장하지 않아 어떤 확인이 실패했는지 알 수 없다. 원본은 별도 [결과 PR54](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/54)에 보존한다.

새 요청02는 이 관측 누락만 보완한다. 별도 모듈과 workflow를 사용하며 이전46 workflow·01 source/tests는 변경하지 않는다. ctypes 함수의 int ABI와 errno 초기화를 명시하고 unshare(0), USER|NET unshare, 설치된 util-linux USER|NET+map-root-user의 세 경우를 비교한다. self/thread-self namespace readlink/stat/open-fstat 각각의 수치 결과/오류 및 UID/GID map·profile·capability를 보존한다. syscall 성공·실패와 무관하게 after snapshot을 만든다. 네트워크 설정은 하지 않는다.

실제 hosted 결과/출처/원본 검증은 소스 검토·기본 CI·새 등록 후 별도 기록한다. 02도 run1/attempt1/workers3이며 이전01을 재실행하지 않는다. 설치된 util-linux는 자기 UID/GID mapping만 수행하고 root 정책을 변경하지 않는다. 세 경우는 mapping/exec 조건이 다르므로 bubblewrap 전체 경로의 호환성을 보증하지 않는다.

strict FAIL / expanded NOT_RUN / Stage 7 INCOMPLETE, main 미병합·Cloud 미게시 판정은 유지한다.
