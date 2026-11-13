# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — namespace 진단

새 요청 `namespace-diagnostic-20261113-01`의 소스 준비 기록이다. 아직 activation/run/result를 의미하지 않는다. `builder-20261113-01`은 실패로 소진됐고 재사용하지 않는다.

설치된 Ubuntu 24.04 Python의 stdlib만 사용한다. 사용자/네트워크 namespace를 모두 새로 만든 사실을 확인한 뒤 UID/GID mapping을 하고 loopback 주소 추가/활성화를 시도한다. 기본, bounding capability 제거, 모든 effective/permitted/inheritable capability 제거의 세 자식 프로세스를 각각 한 번 실행한다. 20초/32 KiB stdout/8 KiB stderr 제한과 기존 closed-environment capture SDK를 사용한다. 마지막 경우는 EPERM 음성 대조군이다.

호스트 정책은 변경하지 않는다. kernel journal은 지정 시간 범위에서 읽기만 하고, 진단 자식 PID와 일치하는 AppArmor net_admin 거부의 제한된 필드만 보존한다. 그 외 본문은 메모리에서 버린다. 로그 접근 실패나 관측 누락은 UNKNOWN이다. 진단 수집 성공은 전체 bubblewrap 격리/빌드/과학 실험 성공이 아니다.

소스 전체 변경에 대해 한 번의 fresh review와 기본 CI를 완료한 뒤 별도 activation commit으로 요청/소스 SHA256 closure를 등록한다. GitHub API run/head/branch/workflow/attempt/유일 실행 및 검토 소스 tree와 현재 tree의 closure를 모두 확인한 후 자식을 실행한다. 새 workflow만 추가하며 기존 45개 workflow를 변경하지 않는다.

기존 strict FAIL / expanded NOT_RUN / Stage 7 INCOMPLETE 판정은 유지한다. main 병합 및 Cloud 게시를 하지 않는다. 새 진단 결과는 원본 artifact와 API를 보존·검증한 뒤 이 문서에 추가한다.

독립 소스 검토: `58760d231747b9a4ed3e19433abd104763c981ed`, Critical 0 / Important 2 / Minor 2. Important 두 건은 activation 단일 부모·전체 request-only delta 검증과 ACK 원 요청 bytes 검증이다. 한 차례 수정에서 두 회귀 실패를 먼저 확인했고, API commit-ish tree 응답의 SHA 차이도 실제 read-only API와 fixture RED→GREEN으로 반영했다. 재검토를 받았다는 주장은 하지 않는다. 상세 finding/판단/비용은 [검토 기록](evidence/STAGE7_ENGINE_CLOCK_NAMESPACE_DIAGNOSTIC_REVIEW.json)에 있다.

미룬 Minor: ND-M1은 비어 있는 journalctl 성공 출력의 READ_COMPLETE 표시이고, ND-M2는 비 ASCII profile bytes를 알려진 label로 분류할 수 있는 경우다. byte 수·SHA를 보존하며 빈 로그/label만으로 AppArmor 원인이나 빌드 준비를 확정하지 않는다.

이전 bubblewrap stderr의 정확한 문구는 보존한다. 다만 원본 network.c의 rtnl_read_reply가 오류 응답에서 errno를 복사하지 않으므로 문구의 EPERM은 실제 netlink 오류 번호를 증명하지 않는다. 새 진단은 ACK에서 signed errno를 직접 읽는다.

최종 수정 소스 로컬 검증: 집중 18개 PASS, 전체 834개 PASS / 선택적 native 의존성 skip 7개, 94.450초. 원격 CI 및 실제 진단은 아직 별도 확인 대상이다.
