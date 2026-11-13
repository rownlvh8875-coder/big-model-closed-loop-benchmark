# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — builder05 explicit build binding

[실제04 증거 PR66](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/66)는 VENV/ENSUREPIP/TOOLS까지 통과하고 owned helper 결합 오류로 pip_main 전에 실패했다. 새 진입 adapter를 driver.py에 배치하면서, 구 build.py가 그 파일의 legacy snapshot/pip API를 기대한다는 연결을 놓쳤다.04 및 모든 구 source/workflow/test/request/raw를 소진·불변으로 보존한다.

별도 owned bound_build는 옆 legacy-driver.py를 명시적으로 읽고 네 callable API를 확인하며 진입 adapter로 fallback하지 않는다. 기존 source snapshot/unpack hook/원본hash/identity/before-after/로그digest제한/pip인자/restoration/validation 본문은 AST로 동일하다. 같은 명령과 invocation을 유지한다. 실패하면 원래72B stdout wire와 함께 고정 enum만 담은 source-failure.json을 xb로 기록하며 원시 예외/pip로그/환경을 저장하지 않는다. evidence 쓰기 실패가 원래 실패 wire를 숨기지 않는다.

배포 경로 그대로 driver.py=owned entry, legacy-driver.py=원래 검증 모듈인 fixture에서 구helper는 fake pip 이전 실패, 새helper는 fake pip 경계 도달을 확인한다. 실제 다운로드 패키지/runtime/source 실행이나 namespace/policy 호출이 없는 CPU 검증이다. 새 recipe는 owned build.py만 바꾸고 나머지 namespace/entry/tool/제3자51inputs109285137B를 유지한다. 새 rootplan hash는 요청에 등록한다.

별도 v5 request builder-20261113-05는 run1/attempt1/build1/probes<=2/profileload<=1/candidate userns assertion<=1. 실제 sourceCI와52개composedsource closure/unique run/soleparent request-only/authenticated API를 확인하고 같은 job의 fresh backend·빈 별도256MiB noexec tmpfs·두FD·bounded4root retention을 요구한다. 구52workflow/source와 모든 raw를 보존한다. 모델/ORT/GL/과학native/main merge/Cloud 게시 없이 wheel을 준비·검증한다. full-lock/image/native/Stage7 완료는 별도다.
