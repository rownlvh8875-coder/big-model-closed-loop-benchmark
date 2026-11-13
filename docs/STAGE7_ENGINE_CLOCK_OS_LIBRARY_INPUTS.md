# Stage7 Ubuntu OS·library 입력 확인

**서명된 Ubuntu snapshot으로 패키지46개의 의존성 후보를 해석하고, 실제 deb bytes와 정적 SONAME/version-label coverage를 확인했다. 설치·runtime·bootstrap·source build는 실행하지 않았다.** 이 입력 집합은 완전한 Ubuntu 설치 상태나 이미지 identity가 아니다.

기준 PR48 HEAD는 `82156fe621339722ef687fb95d925aeb41968bef`다. Metadata 실행 source는 `b5fa7a1ec90f4503806765ce6346f107ee2ae00c`, 실제 deb 취득 source는 `cf479f0e62a61fa319f3d0a3c3507fbc3d3f9268`다. 시작은 각각 **2026-11-13 13:36:06 KST / 13:39:57 KST**이며 이후 증거·검토·최종 CI HEAD와 구분한다.

## 실제 metadata·payload 검증

Snapshot은 `https://snapshot.ubuntu.com/ubuntu/20261113T000000Z/`, noble/noble-updates/noble-security의 main/universe·amd64/all이다. Ubuntu Archive Automatic Signing Key2018 지문 `F6ECB3762474EDA9D21B7022871920D1991BC93C`를 정책 anchor로 고정했다. HTTPS로 받은 공개 키의 실제 지문과 InRelease3개의 GPG VALIDSIG가 일치한다. 이는 선택한 anchor에 대한 검증이며 독립 key-distribution/host attestation은 아니다.

Discovery2요청으로 base InRelease와 공개 키를 받고, 등록된 metadata operation에서 추가 InRelease2개/index6개를 받았다. Curl 요청은 모두 HTTP200/exit0/TLS verify result0/redirect0, application retry0이다. Signed Release의 SHA256/size로6개 compressed index를 확인했다. 세 Release 모두 Valid-Until 필드가 없어null로 보존했고, 고정 snapshot 이상의 freshness 보장은 주장하지 않는다.

| 항목 | 실제 결과 |
| --- | --- |
| Metadata/해석 | 약51.423935s, GPG signature3개/index6개 검증 |
| Resolver | host APT3.0.3, task-local APT_CONFIG·빈 status DB·file-only source, simulate |
| 선택 |46개 deb, 게시 크기 합계13,570,700bytes |
| 실제 취득 |46요청 모두 HTTP200/TLS0/redirect0/exit0, 약35.694546s |
| 실제 payload |46개 모두 게시 SHA256/size 일치, 합계13,570,700bytes |
| 원본 보존 | metadata49파일23,177,543bytes + deb operation140파일13,996,650bytes |
| 정적 검사 | 최종 약6.173919s, decoded tar streams360,867,840bytes(Python archive 포함) |
| OS descriptor | data2,480개 / control270개 |
| ELF |412개 unique objects, 그중 기존 Python archive의 ELF source81개 |
| 후보 대조 |510 DT_NEEDED /15 PT_INTERP basename 후보, 미해결·중복 SONAME0 / 누락 version label0 |

[Metadata 요청](evidence/STAGE7_ENGINE_CLOCK_OS_METADATA_REQUEST.json)·[operator](evidence/STAGE7_ENGINE_CLOCK_OS_METADATA_OPERATOR.txt)·[receipt](evidence/STAGE7_ENGINE_CLOCK_OS_METADATA_RECEIPT.json), [deb 요청](evidence/STAGE7_ENGINE_CLOCK_OS_DEBS_REQUEST.json)·[operator](evidence/STAGE7_ENGINE_CLOCK_OS_DEBS_OPERATOR.txt)·[receipt](evidence/STAGE7_ENGINE_CLOCK_OS_DEBS_RECEIPT.json), [audit](evidence/STAGE7_ENGINE_CLOCK_OS_AUDIT.json)에 실제 source/hash/소비 상태를 보존한다. 두 요청 모두 소비됐고 추가 실행 승인은false다. 과거 소비 요청은 재실행하지 않았다.

## 해석·서명 검증의 범위

처음 public-key import는 키를 가져온 뒤 optional gpg-agent startup 오류로 nonzero를 반환했다. 원래 로그를 보존했고 agent/service를 고치거나 시작하지 않았다. 기존 gpg의 no-autostart/no-auto-key-retrieve로 공개 키와 signature를 검증해 exit0·지문·VALIDSIG를 확인했다. 시스템 trust store는 바꾸지 않았다.

Host에 gpgv가 없어 각 InRelease와 index를 먼저 독립 검증한 뒤, 검증된 plaintext Release/index만 `trusted=yes`인 로컬 file:// mirror로 APT에 제공했다. [Resolver profile](evidence/engine-clock-os-inputs/resolver-profile.json)은 빈 상태 DB, private etc/lists/cache, global config/hooks/source 배제와 전후 hash를 기록한다. 네트워크 source 신뢰 우회나 설치 권한을 부여한 것이 아니다. [APT 출력](evidence/engine-clock-os-inputs/apt-simulate.txt)의 Inst/Conf는 simulation의 제안이며 실제 unpack/configure/script 실행이 아니다.

[Package plan](evidence/engine-clock-os-inputs/package-plan.json)은 package/version/architecture/Filename/Size/SHA256와 서명된 source index를 묶는다. APT가 선택한 Depends/Pre-Depends metadata closure이며, Essential package의 암묵적 존재나 완전한 base filesystem을 증명하지 않는다. Support roots base-files/mawk/libc-bin도 명시했다. Recommends/Suggests는 선택하지 않았다.

## 정적 파일·ELF 대조와 한계

Trusted host dpkg-deb의 ctrl-tarfile/fsys-tarfile 출력만 읽어 [package/control member manifest](evidence/engine-clock-os-inputs/package-members.json)를 만들었다. Maintainer script도 실행하지 않고 descriptor/hash로 남겼다. Rootfs tree를 추출하거나 설치하지 않았으며 ELF만 SHA 이름·mode0400의 분석용 blob으로 보존해 trusted readelf로 읽었다. 분석용 ELF 합계71,600,504bytes/readelf 출력2,433,659bytes이며 target binary·ldd·GPU/provider를 실행하지 않았다.

[정적 coverage](evidence/engine-clock-os-inputs/static-coverage.json)는 실제 파일·SONAME 후보와 required/defined version label을 대조했다. **미해결·중복·누락 label0은 이 후보 데이터의 정적 coverage 결과다. 실제 loader 경로·symbol binding·ABI/layout·호출 동작 PASS가 아니다.** PT_INTERP의 실제 경로 해석도 검증하지 않았다. 원래 Python prefix/RUNPATH와 `.pth` 조건은 그대로이며 loader env/relocation 변경과 배포 setup.sh 실행을 허용하지 않는다.

초기 private 분석에서 directory alias가 미해결로 표시되는 분류 오류를 발견했다. Directory/file/missing-path probe의 RED→GREEN과 전체 cached-byte 정적 재검사를 수행했고 원본 source/output을 보존했다. 재검사 중 기존 stderr 경로 충돌도 보존하고 별도 분석 디렉터리에서 완료했다. 다운로드·패키지 설치·runtime 재시도는 없었다. 최종 미해결 rootfs link는 `usr/share/zoneinfo/localtime -> /etc/localtime`1개다. 기본 directory alias는 파일 byte 없음과 구분해 정상 분류했다.

## 다음 단계와 유지한 게이트

[입력 집합](evidence/STAGE7_ENGINE_CLOCK_OS_INPUTS.json)과 [비활성 binding](evidence/STAGE7_ENGINE_CLOCK_OS_BINDING.json)은 새 component namespace다. 다음은 정확한 payload union·root alias·prefix·timezone 등 config·ownership/mode·startup hook·venv staging 정책과 bounded offline 실행기/fixture를 구현·검토하는 일이다. Maintainer scripts를 대신 실행하거나 임의 loader override로 경로를 맞추지 않는다. 그 뒤 별도 source-controlled 요청이 있어야 실제 provider-free bootstrap/build를 검증할 수 있다.

Package plan/member hash를 설치된 OS/image identity로 바꾸지 않았다. 기존 PR47/48 policy/binding의 null required refs와 image 준비16참조는 그대로다. 실제 OS/ABI/staging/격리/cleanup 증거가 없으므로 build_ready/full_lock/image_readyfalse, nativeallowance0, Task3 미완료다.

기존 tracked429파일은 continuation/parent Task3 status2개 외 그대로 보존한다. Producer70/workflows44/registry8·기존 tools/tests/policies/proposal·old/new raw/controller/review workspace를 변경·삭제하지 않는다. Product 코드/시험은 없고 local 전체 suite는 반복하지 않는다. 최종 independent review와 기본 CI는 source와 별도 HEAD로 기록한다.

새 simulator/native child·공식 model/weights/ORT·image build/pull/load/run·engine/Xvfb/GL/GPU/clock 작업은0이다. 생성 SMALL ONNX 기본 CI는 별도다. 새 RGB/I420/공식 ONNX 일치율·first-divergence 수치는 없다. 기존 strict0/4 FAIL, expanded NOT_RUN, ABBA terminal FAIL/7null/4case·6비교 NOT_RUN, geometry·optics·full-S 한계와 **Stage7 INCOMPLETE**를 유지한다. main 병합·Cloud 게시 없음.
