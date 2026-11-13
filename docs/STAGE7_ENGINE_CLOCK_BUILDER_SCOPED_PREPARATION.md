# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — scoped builder02

검증된 전용 bwrap backend04의 [실제 증거 PR60](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/60)를 전제로 별도 builder02를 준비한다. 기존 builder01과 diagnostic01–04는 소진 상태로 보존하며 재실행하지 않는다.

새 v2 controller는 소스·요청·완전한 단일 request-only activation delta·유일 run/attempt를 확인하고, 같은 새 job에서 private helper/profile을 다시 검증한다. probe/candidate는 서로 다른 device의 빈256MiB noexec tmpfs를 사용한다. probe marker가 candidate에 남지 않는다. 실제 candidate argv는 기존 SDK에서 helper 경로만 바꾸며 host /usr overlay를 추가하지 않는다.

원래 입력51개/109285137B, source52개, rootplan self SHA5371b2ba1e56fa15bc3068e8e579268b44f86091f7ed7a8e8d11fdb7a8c4838d 및 JSON8570595B/SHA835121e2a4bb7e6996a94d1152209c5921f874d75454a19ee8c52b5189f85a25를 유지한다. 후보 Python3.11.18 원래 prefix/startup/venv/offline build/smoke와 source/wheel 검증을 변경하지 않는다. 후보 실행은 새 job 격리와 root FD 검증 뒤에만 허용한다.

별도 정해진 네 root(workspace/build/probe-build/closed-build host-helper)의 available contents를 기존 nofollow retention 한도 내에서 보존한다. 기존49 workflow와 이전 helpers/tests/policies는 수정하지 않는다. profile 전용 경로 외 기본 정책/sysctl을 변경하지 않는다. 모델/ORT/GL/과학 native/main merge/Cloud 게시를 하지 않으며, 성공한 wheel도 full-lock/image/native readiness로 승격하지 않는다. 실제 실행은 소스 검토·기본 CI 뒤 새 요청02를 등록한 후 기록한다.
