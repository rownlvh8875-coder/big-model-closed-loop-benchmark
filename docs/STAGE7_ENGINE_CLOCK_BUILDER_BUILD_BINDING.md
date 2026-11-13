# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — builder05 explicit build binding

[실제04 증거 PR66](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/66)는 VENV/ENSUREPIP/TOOLS까지 통과하고 owned helper 결합 오류로 pip_main 전에 실패했다. 새 진입 adapter를 driver.py에 배치하면서, 구 build.py가 그 파일의 legacy snapshot/pip API를 기대한다는 연결을 놓쳤다.04 및 모든 구 source/workflow/test/request/raw를 소진·불변으로 보존한다.

별도 owned bound_build는 옆 legacy-driver.py를 명시적으로 읽고 네 callable API를 확인하며 진입 adapter로 fallback하지 않는다. 기존 source snapshot/unpack hook/원본hash/identity/before-after/로그digest제한/pip인자/restoration/validation 본문은 AST로 동일하다. 같은 명령과 invocation을 유지한다. 실패하면 원래72B stdout wire와 함께 고정 enum만 담은 source-failure.json을 xb로 기록하며 원시 예외/pip로그/환경을 저장하지 않는다. evidence 쓰기 실패가 원래 실패 wire를 숨기지 않는다.

배포 경로 그대로 driver.py=owned entry, legacy-driver.py=원래 검증 모듈인 fixture에서 구helper는 fake pip 이전 실패, 새helper는 fake pip 경계 도달을 확인한다. 실제 다운로드 패키지/runtime/source 실행이나 namespace/policy 호출이 없는 CPU 검증이다. 새 recipe는 owned build.py만 바꾸고 나머지 namespace/entry/tool/제3자51inputs109285137B를 유지한다. 새 rootplan hash는 요청에 등록한다.

별도 v5 request builder-20261113-05는 run1/attempt1/build1/probes<=2/profileload<=1/candidate userns assertion<=1. 실제 sourceCI와52개composedsource closure/unique run/soleparent request-only/authenticated API를 확인하고 같은 job의 fresh backend·빈 별도256MiB noexec tmpfs·두FD·bounded4root retention을 요구한다. 구52workflow/source와 모든 raw를 보존한다. 모델/ORT/GL/과학native/main merge/Cloud 게시 없이 wheel을 준비·검증한다. full-lock/image/native/Stage7 완료는 별도다.

독립 검토bbf6797 C0/I0/Minor1(BB-M1: main 통합 호출 대신 failure wire literal 검사). 현재 main의 고정 wire/rc1과 record_failure의 write-error 처리는 검토로 확인했고, 후속 stdout/status 변경 회귀 커버리지 비용을 남겨 Minor를 보류했다. root 집중10 PASS4.477초·전체915 PASS/7skip98.754초, 독립 집중10 PASS5.139초. 수정 pass/재검토는 없다. [검토·각 판단·비용](evidence/STAGE7_ENGINE_CLOCK_BUILDER_BUILD_BINDING_REVIEW.json)에 남겼다. 실제 sourceCI/05/pip/source/wheel 성공은 별도 확인한다.

실제05: source5726e61/activationc981a4a, workflow417334313/[run43438618230](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43438618230)/job131930113206 unique1/attempt1, 2026-11-13 23:00:12–23:02:46 Asia/Seoul terminalFAIL. sourceCIpush43438199149/PR43438257300 네 작업PASS/artifacts0. retention/uploadSUCCESS,05소진·재실행금지.

fresh namespace/root12726nodes351886906B/51inputs109285137B 검증과 VENV/ENSUREPIP/TOOLS rc0는 통과했다. BUILD rc1의 고정72B failure 및 전체 core/envelope를 정확히 복원해 capture hashes와 일치시켰다. 별도 source-failure.json은 MISSING_SOURCE_UNPACK이다. legacy API binding 후 pip_main이 captured unpack 없이 반환한 경로까지 확인되지만 pip 반환값·자체 hook 단계·에러 좌표/종류·실패 시 로그digest는 이전 helper가 보존하지 않았다. 따라서 정확한 pip 원인이나 progressbar source 실행 여부를 단정하지 않는다. source-before/after와 wheel이 없고 SMOKE는 미진입이다.

원본artifact14044606421 ZIP245893691B/SHAfca9e6131492c80cd33c55ff4f1782d27d54553c69048db30c63aabc28610bc3, TAR491816960B/SHA863579e114f18eaebc60d1806209c3a1bc50678bdd6ed2e55f0ea0c8be83b6b7.14124항목(12924file/1032dir/168symlink) regular472467670B, 단일gzip EOF/CRC/zero-tail4608B/allinventory/root/input/API/closure/soleparent/request-only/unique를 확인했다. 원본은 output/stage7-builder-binding-evidence/builder-20261113-05/와 [결과JSON](evidence/STAGE7_ENGINE_CLOCK_BUILDER_BUILD_BINDING_RESULT.json)에 보존한다. 기존 CPU의 신뢰된 pip26.2.2로 CLI 인자 parse만 확인했으며 source/network 작업을 하지 않았다. 새06은 조건을 낮추지 않고 fixed pip 반환값·hook 단계·승인 pip 코드 좌표/예외 enum·실패 로그digest를 관측하도록 준비한다. 원시 로그/환경은 저장하지 않으며 모델/native/image/full-lock/Stage7 완료는 없다.
