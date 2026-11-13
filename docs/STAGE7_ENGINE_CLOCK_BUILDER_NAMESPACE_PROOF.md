# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — builder03 namespace proof

[builder02 원본 결과 PR62](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/62)는 소진된 실패로 보존한다. 입력51개와 후보 root 검증은 통과했지만 기존 namespace gate의 어느 묶음 조건이 실패했는지 값이 없으므로 특정 원인으로 단정하지 않는다.

새 owned driver는 Python3.11.18/isolated/no-site/B, UID/GID0, root/proc/dev/devpts readonly, build tmpfs/RW/256MiB 이하, 모든5 capability0, route/interface 조건을 typed facts에 보존한다. 모두 확인한 뒤 typed libc unshare(CLONE_NEWUSER)를 정확히 한 번 호출하고 rc=-1/errnoEPERM 또는ENOSPC를 요구한다. child-visible max_user_namespaces 숫자는 기록하되0/1 whitelist로 계층적 제한을 대체하지 않는다. 실제 unshare 성공·알 수 없는 실패·초기 조건 미충족이면 모든 패키지 단계 전에 종료한다. partial facts도 고정 schema로 보존하며 원시 환경/오류문자열은 남기지 않는다.

기존 driver는 바꾸지 않고 별도 legacy-driver.py로 배치한다. VENV/ENSUREPIP/TOOLS/BUILD/SMOKE, tool/source snapshot, wheel payload 검증과 core-v1 wire를 유지한다. 바깥 envelope-v2가 namespace facts를 전달한다. 새 owned driver와 proof module 때문에 recipe/rootplan hash는 새 요청에 등록하며, 모든 제3자51입력109285137B 및 archive member metadata는 동일하다.

새 v3 workflow/request builder-20261113-03만 허용하며 run1/attempt1/build1, fresh probe<=2/profileload<=1/candidate userns assertion<=1이다. 새로운 job에서 scoped backend를 다시 확인하고 서로 다른 빈256MiB probe/candidate noexec tmpfs와 두 FD 전달을 유지한다. 요청-only sole-parent activation, 전체 source closure/선택된 pin/API/유일 run/attempt를 검증한다. 닫힌 네 root의 원본 보존은 기존 nofollow/size/deadline 한도를 유지한다. 모델/ORT/GL/과학실행/native/main merge/Cloud 게시 없이 wheel까지 준비하고 검증한다. full dependency/image lock과 Stage7 완료를 자동 주장하지 않는다.

독립 검토807dff4: Critical0/Important0/Minor1(BN-M1: 실제 collector의 mountinfo/status/route parser 직접 fixture 부족). root는 Minor를 보류하고 모든 typed fact의 fail-closed 판정과 실제03 관측을 요구한다. 독립 집중18 PASS4.876초, root 전체892 PASS/7skip85.863초. [검토·각 판단·비용](evidence/STAGE7_ENGINE_CLOCK_BUILDER_NAMESPACE_PROOF_REVIEW.json)에 기록했다. 검토는 원격 동작·새 request/CI/원본 archive·wheel·image 성공 증거가 아니다.
