# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — builder04 vendored RECORD

[실제03 증거 PR64](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/64)의 namespace는 통과했고 bootstrap 설치 파일 검증에서 중단됐다. 원래 wheel의 setuptools vendored RECORD16개가 바이트 그대로 설치됐지만 구 검증기의 blanket RECORD 제외와 top-level-only 생성 metadata 허용이 충돌했다.03은 소진되며 개별 stage receipt를 나중에 만들어 채우지 않는다.

새 owned verifier는 실제 top-level distribution의 RECORD만 설치 재작성 대상으로 취급한다. nested/vendor RECORD와 모든 다른 원본 payload는 SHA256 일치를 요구한다. 누락/변조/미등록 metadata/unsafe·duplicate ZIP member/잘못된 pyc source·magic을 거부한다. 기존 nofollow bounded snapshot과 build 명령·source/tool/wheel 검증·namespace 관측/판정을 유지한다. 새로운 명시적 verifier 인자로 연결하며 기존 모듈을 monkeypatch하지 않는다.

새 parent는 고정 stage prefix/status/returncode/bytecount/SHA256 schema로 failure steps를 보존한다. package stdout/stderr 원문이나 환경은 공개하지 않는다. driver/core/envelope가 그대로 복원되도록 하고 source/provider 성공을 임의 추정하지 않는다. owned entry/tool verifier가 바뀌는 recipe/rootplan은 새 요청에 별도 pin으로 등록하며 기존51inputs109285137B를 유지한다.

별도 v4 workflow/request builder-20261113-04: run1/attempt1/build1/probes<=2/profileload<=1/candidate userns assertion<=1.39개03 closure 및 새 composed source를 닫아 등록하고 실제 sourceCI 후 request-only soleparent activation 하나를 허용한다. 같은 새 job에서 fresh backend와 빈 별도256MiB tmpfs/두FD/정해진 네 root retention을 검증한다. 구51workflow/source/test/policy/request/raw는 바꾸지 않는다. 모델/ORT/GL/과학 native/main merge/Cloud 게시 없이 wheel을 준비·검증하며 full-lock/image/native/Stage7 완료는 별도다.
