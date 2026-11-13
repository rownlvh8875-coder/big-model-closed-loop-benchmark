# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — builder06 pip boundary

[실제05 증거 PR68](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/68)는 MISSING_SOURCE_UNPACK까지 확인됐고 정확한 원인은 미확인이다. 구 요청은 소진 상태로 보존한다. 오류를 추정해 패키지나 source 검증을 바꾸지 않는다.

새 entry build.py는05 bound helper를 바이트 그대로 bound-build.py에 보존해 명시적으로 읽는다. prepare proxy는 원래 hook을 real pip module에 연결하고 마지막에 원래 함수를 정확히 복원한다. 고정 진단에는 pip 반환/예외 여부, hook 진입·정상반환 수, owned error code/errno, 위치의 shape/hash만 기록하며 인자·경로 원문은 저장하지 않는다. 원래 source hash/identity/before-after/로그 digest 제약과 pip args/결과/예외 전달을 유지한다.

Scoped LogRecordFactory는 원래 factory를 위임·복원하며 pip의 handler 재설정에도 남는다. 최대16개 ERROR/CRITICAL 좌표는 승인 pip26.2.2 wheel 안에 실제 존재하는 member만 허용하고 줄번호/level/승인된 예외 enum만 저장한다. 알 수 없는 경로는 null, 미등록 예외는 OTHER다. message/args/repr/traceback/environment를 포맷하거나 저장하지 않는다. 원래 _DigestText의 count/hash를 실패에도 보존한다. source-failure-v3는 고정 enum/검증된 typed observation만 xb로 저장하며 원래72B stdout/rc1은 유지한다.

CPU fixture는 원문 sentinel 유출 방지, 경로/예외 whitelist,16record 한도, pip의 logging handler 재설정, 성공/예외 시 factory·unpack 원래 함수 복원, 변경되지 않은 pip 인자/반환/예외·digest, 배포 helper/legacy API, main 실제 호출의 정확한 stdout/rc1/evidence write실패를 다룬다. 다운로드 코드·source·namespace·policy를 로컬에서 실행하지 않는다. 새 main fixture는06 구현에만 적용하며05의 보류 Minor 기록을 소급 변경하지 않는다.

별도 v6/request builder-20261113-06 run1/attempt1/build1/probes<=2/profileload<=1/candidate userns assertion<=1, 모든51inputs109285137B와 기존 entry/namespace/tool/snapshot 제약을 유지한다. owned recipe 추가는 새rootplan hash에 등록한다. old53workflow/source/test/request/raw는 불변이며 authenticated source/soleparent request-only/unique run/새job backend/별도256MiB tmpfs/두FD/정해진4root bounded retention을 그대로 요구한다. 모델/ORT/GL/과학native/main merge/Cloud 게시나 full-lock/image/Stage7 완료는 없다. 실제06 관측은 최종sourceCI/새등록 뒤에만 기록한다.

독립 검토8663c90 C0/I0/Minor1(PB-M1: logging reset 시험은 handler 삭제·factory 직접 호출이며 dictConfig+logger.error 정상 dispatch fixture는 없음). root는 factory 위치상 handler 재설정과 독립이라는 검토 판단을 수용하고 회귀 커버리지 비용과 함께 Minor를 보류했다. 집중12 PASS3.576초·전체927 PASS/7skip94.178초, 독립 집중12 PASS3.610초. 수정 pass/재검토는 없다. [검토·각 판단·비용](evidence/STAGE7_ENGINE_CLOCK_BUILDER_PIP_BOUNDARY_REVIEW.json)에 기록했다. 실제sourceCI/06/원본 artifact/원인·source·wheel 성공은 별도 root 검증 대상이다.

실제06: source15409cf/activation8f2b8c6, workflow417365792/[run43443371678](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43443371678)/job131946437674 unique1/attempt1, 2026-11-13 23:30:36–23:33:07 Asia/Seoul terminalFAIL. sourceCIpush43442713265/PR43442777664 네 작업PASS/artifacts0, retention/uploadSUCCESS.06소진·재실행금지.

새 관측은 검증됐고 observer_errors0이다. pip1회/반환2/raisefalse, hook1회/정상반환0, hook builtin.FileNotFoundError/errno2, 위치는 tmp아래 등록regex일치였다. 승인 pip base_command.py165의 ERROR 좌표와 exception enum이 저장됐고 원시log 대신 stdout85B/stderr3927B의 SHA256만 저장됐다. namespace/root12728nodes351898227B/51inputs109285137B 및 VENV/ENSUREPIP/TOOLS 통과 후 BUILD가 중단됐다.

승인된 실제 pip wheel SHAfd7f4d...의 원문을 읽어 lifecycle을 확인했다. req_install.py349–363은 parent만 만들고 최종 target path를 TempDirectory에 전달한다. temp_dir.py133–136은 path=None일 때만 디렉터리를 만든다. prepare.py의 unpack_url 이후 untar_file.py가 아니라 utils/unpacking.py173에서 ensure_dir(location)을 수행한다. 반면 구 owned _location은 original unpack 호출 전에 최종 디렉터리까지 lstat한다. 따라서 그 시점에 아직 없는 target에서 ENOENT가 발생한다.06에서는 source unpack/metadata 실행 전 실패이며05의 누락된 관측을 소급 채우지는 않는다.07은 tmpfs 안 최종 빈 디렉터리만 FD/no-follow로 준비한 뒤 모든 원래 source 검증을 그대로 사용하도록 보완한다.

원본artifact14046297195 ZIP245898358B/SHA933a32e4797003ef879dc71eea87ea219007ffb980d237013f2aea9e6fa1b453;14126항목(12926file/1032dir/168symlink), regular472479810B. TAR491827200B/SHAc6d919df042d18d925dc0396b90c95467900d59f174720e1342aa26c4977682f, 단일gzip EOF/CRC/zero-tail1024B/allinventory/root/input/API/closure/soleparent/request-only/unique와 exactcore/envelope hashes를 확인했다. [실제 결과·공개소스 anchors](evidence/STAGE7_ENGINE_CLOCK_BUILDER_PIP_BOUNDARY_RESULT.json)와 output/stage7-builder-pip-evidence/builder-20261113-06/ 원본을 보존한다. wheel/SMOKE/full-lock/image/native/Stage7 완료와 모델/ORT/GL/과학호출/main merge/Cloud 게시가 없다.
