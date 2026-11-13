# Stage7 progressbar 원본·빌드 도구 입력 확인

**progressbar2.5 원본과 고정 빌드 도구 wheel3개의 실제 bytes를 확보·검증했다. 빌드는 아직 실행하지 않았다.** 구성 도구의 기본 metadata 의존성은 닫혔지만 Python/bootstrap/OS·격리 실행기·전체 image lock은 포함하지 않는다.

기준 PR46 HEAD는 `3fbc5c0193e0a45d766c7efe276fcf4f3369b42e`다. 실제 취득 source는 `bacf44f2e1f6e010b413e4400a5c47d26ac7026b`, 시작 **2026-11-13 11:31:31 KST**다. 이전 pip 실패나 MetaDrive wheel 변환 요청은 다시 실행하지 않았다.

## 실제 취득 결과

| 입력 | 실제 bytes | SHA256 |
| --- | ---: | --- |
| progressbar2.5 source | 10,046 | `5d81cb529da2e223b53962afd6c8ca0f05c6670e40309a7219eacc36af9b6c63` |
| pip26.2.2 wheel | 1,819,850 | `fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70` |
| setuptools80.9.0 wheel | 1,201,486 | `062d34222ad13e0cc312a4c02d73f059e86a4acbfbdea8f8f76b28c99f306922` |
| wheel0.45.1 wheel | 72,494 | `708e7481cc80179af0e556bbf0cc00b8444c7321e2700b8d8580231d13017248` |

등록한 source1/버전 JSON3/tool wheel3, 총7요청 모두 HTTP200/curl exit0/TLS verify result0/redirect0이다. Application retry0, payload 합계3,137,991bytes, 취득2.953218s다. 로컬 원본23파일 합계3,202,941bytes를 `output/stage7-progressbar-build-inputs/progressbar-input-20261113-01`에 보존한다. Payload 합계는 HTTP/TLS overhead나 curl transfer JSON 크기를 포함하지 않는다.

[실행 전 요청](evidence/STAGE7_ENGINE_CLOCK_PROGRESSBAR_REQUEST.json), [소비된 역사적 operator](evidence/STAGE7_ENGINE_CLOCK_PROGRESSBAR_OPERATOR.txt), [실제 영수증](evidence/STAGE7_ENGINE_CLOCK_PROGRESSBAR_RECEIPT.json), [audit](evidence/STAGE7_ENGINE_CLOCK_PROGRESSBAR_AUDIT.json)을 보존한다. 요청 `progressbar-input-20261113-01`은 소비됐고 추가 실행 승인은false다. 실제 source/archive/tool 파일은 로컬 입력이며 Actions artifact나 upstream 서명·host attestation이 아니다. Git에는 작은 metadata/정적 검사 결과만 추가했다.

## 정적 검사에서 확인한 사실

Source gzip은61,440bytes tar로 풀리며18member(15file/3directory)가 있다. 경로·중복·확장 header·링크·특수파일·크기 조건을 검사하고 모든 파일의 hash를 기록했다. 파일 트리 추출·설치·source import/실행은 하지 않았다. Python 파일6개는 실제 도구 Python3.11.17에서 AST parse를 통과했다. Runtime package 파일은4개다. 이는 목표3.11.18의 실행 호환성이나 API 동작 검증이 아니다.

`setup.py`는 `setuptools`와 실제 `progressbar` package를 import하고, mtime 조건에 따라 README를 다시 쓴다. 따라서 미래 build를 단순 metadata 읽기로 분류할 수 없다. 원본의 BSD/LGPL 선택 고지·조건을 정적 결과에 그대로 남겼고, 미래 wheel에도 원래 license bytes를 보존하도록 했다. 현재 source rewrite/2to3/대체 package는 선택하거나 실행하지 않았다.

Tool wheel3개는 최상위 METADATA Name/Version/Requires-Python, py3-none-any·purelib tag, 총1,027 RECORD row와10,035,956 decoded bytes를 확인했다. RECORD 자기 행3개는 빈 hash/size 규칙이며 나머지1,024파일의 SHA256/size를 검증했다. Setuptools 내부의 vendored `.dist-info`는 최상위 배포 metadata와 구분했다. 최초 탐색의 넓은 metadata suffix 선택이 vendored 항목도 찾았던 사실은 private 검사 기록에 남겼고, 입력 다운로드나 정책을 재실행하지 않았다.

명시적 CPython3.11.18/Linux amd64 marker 값과 extra 미선택 조건에서 세 도구의 활성 기본 Requires-Dist는0개다. 선택한 도구 버전은 executor의 고정 후보 선택이며 최신 버전·보안 인증·실행 호환성 주장과 다르다. Vendored code는 wheel 전체 hash에 묶여 있지만 extras를 선택한 closure나 별도 bootstrap closure를 검증한 것은 아니다. [정적 결과](evidence/engine-clock-progressbar/static-inspection.json), 원본 버전 JSON3개와 [입력 manifest](evidence/STAGE7_ENGINE_CLOCK_PROGRESSBAR_BUILD_INPUTS.json)에 전체 조건을 기록했다.

## 비활성 build 정책과 다음 단계

[Build policy](evidence/STAGE7_ENGINE_CLOCK_PROGRESSBAR_BUILD_POLICY.json)는 실행 요청이 아니다. 원본4runtime파일/license를 보존하고, 정확한 source hash와 tool wheel3개를 사용하는 offline build 및 산출 wheel의 정확한 파일 집합·METADATA/WHEEL/RECORD/hash 검사를 정했다. 산출 wheel은 upstream 게시 wheel이 아니며 hash는 실제 생성 전까지null이다. 예상 license 경로 등 출력이 다르면 원래 실패를 보존하고 정책을 자동 확장하지 않는다.

다음은 **Python3.11.18 실행 파일·stdlib·venv/ensurepip와 bootstrap pip의 실제 hash closure를 독립적으로 고정한 뒤**, source 실행용 격리 실행기·fixture 검증·새 소비 요청을 구현·검토하는 일이다. 이 bootstrap은 이번 세 wheel의 기본 의존성 closure 밖이다. 별도 builder runtime은 전체 MetaDrive/native image 없이 준비할 수 있으나, 이번 결과로 준비됐다고 간주하지 않는다.

미래 정책은 phase180s/cleanup5s, writable tree256MiB, wheel/decoded/log 각1MiB·member64·free1GiB와 process-group reaping을 요구한다. 이는 새 package build의 비활성 한도이며 과거 native1320/270s·이미지16GiB 조건을 대체하지 않는다. 실제 network/filesystem 격리·용량 제한·로그 정제·종료 보장이 구현·검증되기 전에는 source를 실행하지 않는다. Polling만으로 hard quota를 증명하지 않는다. 현재 이 실행기·격리 fixture·authenticated target/bootstrap이 없어 **build_ready=false**다.

## 보존과 최종 게이트

기존 tracked401파일은 continuation/parent Task3 status2개 외에 그대로 보존한다. Producer70/workflows44/consumed registry8·기존 tools/tests/policy/proposal·old raw/controller/review workspace는 바꾸지 않는다. 새 product 코드/시험은 없고 동일한 local 전체 suite는 반복하지 않는다. Source/다운로드 도구를 import하지 않았으며 기존 trusted pip의 vendored packaging만 marker parsing에 사용했다. 독립 검토·최종 기본 CI는 실행 source와 다른 HEAD로 별도 기록한다.

새 공식 model/weights/ORT·native/provider/engine/Xvfb/GL/GPU/clock·image build/pull/load/run은0이다. 생성 SMALL ONNX 기본 CI는 별도다. 새 RGB/I420/공식 ONNX 일치율·first-divergence 수치는 없다. 기존 strict0/4 FAIL, expanded NOT_RUN, ABBA terminal FAIL/7null/4case·6비교 NOT_RUN, geometry·optics·full-S 한계와 **Stage7 INCOMPLETE**를 유지한다. 전체 Python/base/deb/asset lock·image 준비16참조null/nativeallowance0·Task3 미완료이며 main 병합·Cloud 게시는 없다.
