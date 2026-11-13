# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — namespace 진단

새 요청 `namespace-diagnostic-20261113-01`의 소스 준비 기록이다. 아직 activation/run/result를 의미하지 않는다. `builder-20261113-01`은 실패로 소진됐고 재사용하지 않는다.

설치된 Ubuntu 24.04 Python의 stdlib만 사용한다. 사용자/네트워크 namespace를 모두 새로 만든 사실을 확인한 뒤 UID/GID mapping을 하고 loopback 주소 추가/활성화를 시도한다. 기본, bounding capability 제거, 모든 effective/permitted/inheritable capability 제거의 세 자식 프로세스를 각각 한 번 실행한다. 20초/32 KiB stdout/8 KiB stderr 제한과 기존 closed-environment capture SDK를 사용한다. 마지막 경우는 EPERM 음성 대조군이다.

호스트 정책은 변경하지 않는다. kernel journal은 지정 시간 범위에서 읽기만 하고, 진단 자식 PID와 일치하는 AppArmor net_admin 거부의 제한된 필드만 보존한다. 그 외 본문은 메모리에서 버린다. 로그 접근 실패나 관측 누락은 UNKNOWN이다. 진단 수집 성공은 전체 bubblewrap 격리/빌드/과학 실험 성공이 아니다.

소스 전체 변경에 대해 한 번의 fresh review와 기본 CI를 완료한 뒤 별도 activation commit으로 요청/소스 SHA256 closure를 등록한다. GitHub API run/head/branch/workflow/attempt/유일 실행 및 검토 소스 tree와 현재 tree의 closure를 모두 확인한 후 자식을 실행한다. 새 workflow만 추가하며 기존 45개 workflow를 변경하지 않는다.

기존 strict FAIL / expanded NOT_RUN / Stage 7 INCOMPLETE 판정은 유지한다. main 병합 및 Cloud 게시를 하지 않는다. 새 진단 결과는 원본 artifact와 API를 보존·검증한 뒤 이 문서에 추가한다.
