# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — PWD 명시 확인

03은 profile 전 baseline exit1, 전용 profile 로드 후 exit0까지 관측했지만 validator가 after JSON을 거부·폐기했다.03은 BLOCKED로 소진됐고 원본은 [PR58](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/58)에 보존한다. 그 값을 hash/크기로 추정하지 않는다.

소스 bubblewrap.c:3427은 PWD를 선택 cwd로 설정한다. 새04 adapter는 기존 명시 env keys에 이 한 필드만 추가하고 PWD=/build·정규화 UTF8 hash를 검증한다. 자격 증명/proxy/다른 env 이름은 추가 허용하지 않는다. 여섯 namespace 변경, UID/GID0, 다섯 capability set0, root EROFS/build-write, after 전용 profile 검증은03 그대로다. 기존03 정책·decision logic을 immutable dependency로 재사용한다.

shape-safe 프레임은 semantic 검증 전에 저장한다. 그래서 정상 형식의 nonzero caps/변하지 않은 namespace/잘못된 허용 env 관측은 거부 후에도 남는다. 알 수 없는 필드나 raw text는 wire 단계에서 거부하고, 알 수 없는 profile/PWD 값은 null·hash만 출력한다. 새04 auth/closure/workflow로 run1/attempt1/probe최대2/profile-load최대1이며 기존48 workflow와 이전 source/tests/요청을 변경하지 않는다.

실제 실행은 소스 시험·독립 검토·기본 CI·새 단일 activation 등록 뒤 수행한다. model/candidate build/image/native/scientific gate, main merge 및 Cloud publication은 여전히 닫혀 있다.
