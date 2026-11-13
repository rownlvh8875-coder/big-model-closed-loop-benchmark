# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — PWD 명시 확인

03은 profile 전 baseline exit1, 전용 profile 로드 후 exit0까지 관측했지만 validator가 after JSON을 거부·폐기했다.03은 BLOCKED로 소진됐고 원본은 [PR58](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/58)에 보존한다. 그 값을 hash/크기로 추정하지 않는다.

소스 bubblewrap.c:3427은 PWD를 선택 cwd로 설정한다. 새04 adapter는 기존 명시 env keys에 이 한 필드만 추가하고 PWD=/build·정규화 UTF8 hash를 검증한다. 자격 증명/proxy/다른 env 이름은 추가 허용하지 않는다. 여섯 namespace 변경, UID/GID0, 다섯 capability set0, root EROFS/build-write, after 전용 profile 검증은03 그대로다. 기존03 정책·decision logic을 immutable dependency로 재사용한다.

shape-safe 프레임은 semantic 검증 전에 저장한다. 그래서 정상 형식의 nonzero caps/변하지 않은 namespace/잘못된 허용 env 관측은 거부 후에도 남는다. 알 수 없는 필드나 raw text는 wire 단계에서 거부하고, 알 수 없는 profile/PWD 값은 null·hash만 출력한다. 새04 auth/closure/workflow로 run1/attempt1/probe최대2/profile-load최대1이며 기존48 workflow와 이전 source/tests/요청을 변경하지 않는다.

실제 실행은 소스 시험·독립 검토·기본 CI·새 단일 activation 등록 뒤 수행한다. model/candidate build/image/native/scientific gate, main merge 및 Cloud publication은 여전히 닫혀 있다.

독립 검토c794e5a C0/I0/Minor2(BC-M1 및 기존 BP-M1). 집중7개 별도 PASS, root 전체864 PASS/7skip73.094초. 현재 argv가03과 observer 외 동일함을 별도 검토자가 확인했다. 미래 flags fixture 보강과 예외 중간상태 보존은 Minor로 미뤘다. [판단·비용 기록](evidence/STAGE7_ENGINE_CLOCK_BWRAP_PROFILE_CONFIRMATION_REVIEW.json)을 참조한다. 원격 CI/실제04는 별도 확인 대상이다.

실제04 통과: activation4c02fb15e3a671c9aa2c9b42645260cd1d21ef41, workflow417212710/[run43419969613](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43419969613)/job131867219327, attempt1/해당 workflow·branch 실행1. 2026-11-13 20:48:21–20:48:49 Asia/Seoul. baseline exit1/기존 loopback hash, 전용 profile load1, after exit0/stderr0 및 전체 predicate 검증 PASS.04는 통과로 소진됐고 재사용하지 않는다.

여섯 namespace가 host와 모두 달랐고 UID/GID0, CapEff/Prm/Inh/Amb/Bnd 전부0, 허용 env10개+PWD=/build 및 hash, root write EROFS30/build write true, 실제 child profile stage7-bwrap(unconfined)을 확인했다. kernel7.0.0-1017-azure/image20261101.360.1, 기존 AppArmor restrict1/enforced unprivileged profile은 유지됐다. 이는 새 전용 helper 경로의 조건부 지원 증거다. 과거03 값을 복원하거나 다른 runner·전체 image·과학 실행을 승인하는 증거로 확대하지 않는다.

원본 artifact14033463063 ZIP329563B/SHAc1a3a2f7d99b8a362838bc7e312ef1842daf228097f07767c688dc5f4d6f28f3; preflight.json7834B/SHA87d6e5e28265e220d8daf76bbe8acd415f7f9bb164583f8dc85e3515f4aa79a9. helper194592B/SHAed290d7b467eba236ff705a83938ecf78a5dc055648ef5420937b9717b29af3e, pinned source126452B/SHA9760d007..., profile175B/SHAe00bd023...를 함께 보존했다. 원본 API/ZIP/log는 output/stage7-bwrap-profile-confirmation-evidence/namespace-diagnostic-20261113-04/에 남는다. [소비 영수증](evidence/STAGE7_ENGINE_CLOCK_BWRAP_PROFILE_CONFIRMATION_RESULT.json)의 hash/CRC/source/request/parent/HEAD/유일 실행 및 독립 predicate 재확인을 참조한다. 다운로드한 helper binary는 로컬 실행하지 않았다.

소스197cd79 exact CI push43419213544/PR43419601514 네 job SUCCESS/attempt1/artifacts0, full864 PASS/7skip이다. 다음 별도 builder02는 검증된 private helper/profile을 매번 새 job에서 먼저 확인하고, 독립된 빈 quota tmpfs에서 대상 Python3.11.18·입력51개·progressbar wheel을 준비해야 한다.04의 probe marker나 소비된 실행 예산을 후보 빌드에 재사용하지 않는다.
