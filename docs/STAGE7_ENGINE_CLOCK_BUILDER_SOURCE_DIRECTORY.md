# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — builder07 source-directory

[실제06 증거 PR70](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/70)의 안전한 관측과 승인된 pip 원문은 최종 source directory 생성 시점 불일치를 입증했다. 원래 hook의 사전 lstat가 pip의 실제 디렉터리 생성보다 먼저 실행됐다. 구 요청/실패/source/raw는 불변으로 보존한다.

새 source-directory gate는 고정 /build/tmp 아래 등록된 두 component만 받는다. O_DIRECTORY|O_NOFOLLOW FD로 build/tmp/기존 parent/최종 leaf를 열고 build와 같은 device, 소유 UID, group/other 쓰기 금지, 이름과 열린 inode/device 일치, 빈 디렉터리를 요구한다. parent는 만들지 않으며 마지막 leaf만0700으로 mkdirat한다. symlink/traversal/file/nonempty/wrong-device/named-inode mismatch는 package callback 전에 거부한다. 새 final directory 준비 뒤 원래 location/empty/sourcehash/identity/before-after 검증을 바꾸지 않고 실행한다.

Gate proxy는 real prepare module에 연결되고 기존06 observer proxy 아래에 놓인다. 한 번의 준비만 허용하며 원래 hook을 정확히 복원한다. source-directory.json은 고정 stage/status/created/device/inode/UID/mode/empty/binding/errno/locationhash만4096B 이하 xb+nofollow로 저장한다. 원시 경로/예외/로그/환경을 남기지 않는다. 기존 bound/observer/legacy 파일, stage 명령, source failure/main wire와 strict wheel 검증은 그대로다.

CPU fixture는 구_missing_leaf ENOENT 재현과 새FD 준비 뒤 구guard 통과, immutable bound source hook+두 proxy+owned fake unpack의 before/after 검증, 성공/실패 복원과 main gate wiring/정확한72B stdout/rc1/evidence write 실패를 확인한다. 실제 다운로드 코드·source·namespace·policy 실행이 아니다. focused16 PASS, 전체 회귀 시험과 독립 검토는 별도 기록한다.

별도 v7/request builder-20261113-07 run1/attempt1/build1/probes<=2/profileload<=1/candidate userns assertion<=1/source_directory_preparations1. 모든51inputs109285137B, 구54workflow/source/test/request/raw는 그대로이며 owned entry/gate와 새rootplan만 등록한다. 기존 source/API/soleparent/request-only/unique/new-job backend/별도256MiB tmpfs/두FD/4root bounded retention gate를 유지한다. 모델/ORT/GL/과학native/main merge/Cloud 게시 및 full-lock/image/native/Stage7 완료는 없다.

독립 검토bb285227 C0/I0/M0. 집중16 PASS3.392초·전체943 PASS/7skip106.763초, 독립 집중16 PASS3.764초. 수정 pass/재검토는 없다. [검토·각 판단·비용](evidence/STAGE7_ENGINE_CLOCK_BUILDER_SOURCE_DIRECTORY_REVIEW.json)에 기록했다. 임의의 동시 same-UID/적대적 host를 방어하는 일반 filesystem sandbox라는 주장은 없으며, 기존 qualified namespace/build mount와 trusted primary 경계 아래 동작한다. 실제07의 pip/source/wheel/원본 결과는 sourceCI/별도등록 뒤 확인한다.
