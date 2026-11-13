# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — builder06 pip boundary

[실제05 증거 PR68](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/68)는 MISSING_SOURCE_UNPACK까지 확인됐고 정확한 원인은 미확인이다. 구 요청은 소진 상태로 보존한다. 오류를 추정해 패키지나 source 검증을 바꾸지 않는다.

새 entry build.py는05 bound helper를 바이트 그대로 bound-build.py에 보존해 명시적으로 읽는다. prepare proxy는 원래 hook을 real pip module에 연결하고 마지막에 원래 함수를 정확히 복원한다. 고정 진단에는 pip 반환/예외 여부, hook 진입·정상반환 수, owned error code/errno, 위치의 shape/hash만 기록하며 인자·경로 원문은 저장하지 않는다. 원래 source hash/identity/before-after/로그 digest 제약과 pip args/결과/예외 전달을 유지한다.

Scoped LogRecordFactory는 원래 factory를 위임·복원하며 pip의 handler 재설정에도 남는다. 최대16개 ERROR/CRITICAL 좌표는 승인 pip26.2.2 wheel 안에 실제 존재하는 member만 허용하고 줄번호/level/승인된 예외 enum만 저장한다. 알 수 없는 경로는 null, 미등록 예외는 OTHER다. message/args/repr/traceback/environment를 포맷하거나 저장하지 않는다. 원래 _DigestText의 count/hash를 실패에도 보존한다. source-failure-v3는 고정 enum/검증된 typed observation만 xb로 저장하며 원래72B stdout/rc1은 유지한다.

CPU fixture는 원문 sentinel 유출 방지, 경로/예외 whitelist,16record 한도, pip의 logging handler 재설정, 성공/예외 시 factory·unpack 원래 함수 복원, 변경되지 않은 pip 인자/반환/예외·digest, 배포 helper/legacy API, main 실제 호출의 정확한 stdout/rc1/evidence write실패를 다룬다. 다운로드 코드·source·namespace·policy를 로컬에서 실행하지 않는다. 새 main fixture는06 구현에만 적용하며05의 보류 Minor 기록을 소급 변경하지 않는다.

별도 v6/request builder-20261113-06 run1/attempt1/build1/probes<=2/profileload<=1/candidate userns assertion<=1, 모든51inputs109285137B와 기존 entry/namespace/tool/snapshot 제약을 유지한다. owned recipe 추가는 새rootplan hash에 등록한다. old53workflow/source/test/request/raw는 불변이며 authenticated source/soleparent request-only/unique run/새job backend/별도256MiB tmpfs/두FD/정해진4root bounded retention을 그대로 요구한다. 모델/ORT/GL/과학native/main merge/Cloud 게시나 full-lock/image/Stage7 완료는 없다. 실제06 관측은 최종sourceCI/새등록 뒤에만 기록한다.
