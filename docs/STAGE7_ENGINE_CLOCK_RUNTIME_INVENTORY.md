# Stage7 설치 파일 목록 검증기 — Task2

Task1 다음 단계로 호출자가 지정한 파일 트리와 `installed-files-v1` 목록을 비교하는 검증기를 구현했다. 브랜치 `analysis/engine-clock-runtime-inventory`, base `2cc22c0e82dde25429a3f0216a3eb7405b127d5b`/Draft PR41이다. 실제 image 준비·수집이나 native 실행 승인은 없다. 시험은 작은 임시 파일 트리만 사용한다.

## 구현과 범위

[검증기](../scripts/engine_clock_runtime_inventory.py)의 `validate_inventory`는 메타데이터만 검증·복사한다. `collect_inventory(root, expected, deadline=...)`는 명시된 root의 파일 바이트·모드·symlink를 검사한다. Import 스캔과 CLI는 없다. [세부 계약](superpowers/specs/2026-11-12-engine-clock-runtime-inventory-design.md)에 exact schema·alias·제외·한도를 기록했다. Task1 identity와 파일 manifest는 다른 입력 형식이다.

모든6roots를 검사하고 중첩 root 파일은 중복 읽지 않는다. Descriptor-relative nofollow 순회, 파일 전후 identity 검사, 디렉터리 검사와 두 번째 metadata 순회로 변경·탈출을 거부한다. Atomic snapshot이나 실제 mount/host 인증은 아니다. 정확한4개 `/etc` metadata 예외는 payload를 읽지 않는다. 실제 Docker 배치와 외부 canonical alias 호환성은 아직 검증하지 않았다.

성공은 `INSTALLED_FILES_MATCH`, `complete=true`, 관측 manifest를 반환한다. 실패는 `FAILED_OR_INCOMPLETE`, `inventory=null`과 최대64개/256KiB 일치 prefix·단계·읽은 바이트를 남긴다. Prefix는 완전한 alias 검증이 아니다. 두 상태 모두 `native_admission=false`다. Canonical SHA는 artifact 원본 파일 SHA/API 인증과 다르다. 예상 manifest 자체의 출처는 아직 인증하지 않는다.

File512MiB/content3GiB/read4GiB/JSON16MiB/순회당100000nodes/depth256/link40/180초 한도를 적용한다. 두 순회 누적 visited_nodes<=200000이며 syscall 수가 아니다. Main-thread POSIX alarm을 소유하고 기존 timer가 있으면 거부하며 handler를 복원한다. 일반 blocking read를 중단하지만 kernel D-state/스케줄러의 hard realtime 보장은 없다. 해시 IO는 시간·cache에 영향을 주므로 observer-neutral이라고 부르지 않는다.

## 시험과 증거

집중 시험30개가 통과했다. 최초25개 missing-feature RED, constructor/path 수정, blocking-read deadline RED, main-thread/timer RED와 외부 예외 문자열 비저장 RED를 보존했다. 마지막 시험 삽입 중 기존 interrupt 블록을 잘못 옮겨 발생한 NameError는 시험 구조를 복원한 뒤 실제 노출2건의 RED만 다시 확인하고 구현을 수정했다. 이전 실패 로그도 삭제하지 않았다.

파일 변경·누락·추가·빈 파일·모드·root 중복·cross-root/루트 alias·cycle/escape/dangling link·제외 payload 비접근·FIFO/socket/device·예산·deadline·descriptor 정리·순회 중 변경·import guard를 시험한다. Fixture Unix socket은 파일 종류 거부 시험이며 외부 통신이 없다. Python child는 import guard 시험용이며 native child가 아니다. 전체 CPU 결과와 합성 fixture는 [audit](evidence/STAGE7_ENGINE_CLOCK_RUNTIME_INVENTORY_AUDIT.json), [fixture 영수증](evidence/STAGE7_ENGINE_CLOCK_RUNTIME_INVENTORY_FIXTURE.json)에 기록한다. 검토 HEAD와 후속 문서 영수증 HEAD/최종 CI를 구분한다.

## 판단과 비용

1. Caller-root fixture 검증만 한다. 실제 image provenance/config 인증은 Task3에 남는다.
2. 승인6roots/내부 alias/정확한4metadata 예외만 지원한다. 실제 image의 정당한 배치도 범위 밖이면 거부할 수 있다.
3. Nofollow/same-device/전후 검사와 node/depth/link 한도를 쓴다. Atomic snapshot/host attestation은 보장하지 못하고 큰 image가 제한에 걸릴 수 있다.
4. 완전 성공에만 manifest를 반환한다. 실패 prefix로 전체 완전성이나 artifact 인증을 주장할 수 없다.
5. Payload 재해시 없는 두 번째 metadata 순회를 한다. IO가 추가되고 마지막 검사 후 변경 가능성은 남는다.
6. Main-thread POSIX alarm을 소유하고 기존 timer가 있으면 거부한다. Process-global timer를 사용하며 다른 thread/platform과 hard realtime은 지원하지 않는다.

## 보존과 다음 단계

Producer70/workflows44/소비된 registry8 및 Task1 코드·시험·비활성 proposal을 보존한다. 실제 preparation16참조null/image·native readinessfalse/native allowance0이다. 실제 image/Dockerfile/준비 workflow/API adapter·공식 모델·ORT·GPU·clock 호출을 추가하지 않는다. SMALL TEST GRAPH 기본 CI는 별도다. Raw archive/extraction/controller 기록을 삭제하지 않는다.

과거 ABBA는 authentic terminal FAIL,7집계null/4case·6비교 NOT_RUN이다. 재시도·게이트 완화·잔여 case 재사용은 없다. 새 raw/canvas/I420/first-divergence 측정은 없다. Strict FAIL/expanded NOT_RUN/geometry·physical-optics·production-ISP·full-S 미검증/Stage7 INCOMPLETE/main 공식 호출0을 유지한다. Cloud 게시·main merge는 하지 않는다. 다음은 Task3 실제 입력 pin/비활성 adapter 설계·시험이며 실제 image 준비 실행은 별도 검토 뒤에만 진행할 수 있다.
