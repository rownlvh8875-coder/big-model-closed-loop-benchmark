# Stage7 Python3.11.18 archive·bootstrap 입력 확인

**Python3.11.18 후보 archive의 실제 bytes와 내부 bootstrap 구성을 고정했다. Runtime·bootstrap·source build는 실행하지 않았다.** Archive 입력 검증이며 설치된 identity·완전한 OS 환경·이미지 준비 완료가 아니다.

기준 PR47 HEAD는 `04a487347d3a2e5c8630b5d7834f403db25f0ebd`, 실제 취득 source는 `c758a7f2378ba5a0208963e070fe6864161bf5ca`다. 취득 시작은 **2026-11-13 12:02:55 KST**다. 이후 검토·영수증 HEAD와 구분하며 이전 소비 요청은 재실행하지 않았다.

## 실제 배포물과 보존 증거

선택한 후보는 GitHub가 관리하는 `actions/python-versions`의 Ubuntu24.04/Linux x64 배포다. python.org의 공식 Linux binary라는 주장은 하지 않는다. Repository commit `9bc1fe8f6b4befbb1edd3955a1adc8fc086b3e08`의 버전 manifest가 release `3.11.18-40260280589`를 가리키며 release ID423814510/asset ID676813336이다. Release의 target_commitish는 `main` 문자열이며 이를 검증된 build source commit으로 바꾸지 않는다.

| 항목 | 실제 확인 |
| --- | --- |
| Archive | `python-3.11.18-linux-24.04-x64.tar.gz` |
| 크기 | 92,610,561bytes |
| SHA256 | `099ef30fc27f0d7067a67be5a5fb7fd66154cfa1e4186c88f71c3a3070c81abc` |
| 취득 | gh CLI1회/exit0, 약11.395554s, GitHub API 게시 digest 일치 |
| 시작 free / 관측 tree peak | 60,743,118,848bytes / 93,486,620bytes |
| 원본 보존 | 9파일 / 93,489,457bytes |
| 정적 검사 | 약3.781869s, decoded tar313,937,920bytes |
| 항목 | 10,546개: file9,971 / directory566 / symlink9 / hardlink0 |
| 전체 member manifest | 2,485,757bytes, artifact hash와 canonical hash 별도 |

원본은 `output/stage7-python-bootstrap-inputs/python-bootstrap-20261113-01`에 보존한다. [요청](evidence/STAGE7_ENGINE_CLOCK_PYTHON_BOOTSTRAP_REQUEST.json), [소비된 operator](evidence/STAGE7_ENGINE_CLOCK_PYTHON_BOOTSTRAP_OPERATOR.txt), [실제 receipt](evidence/STAGE7_ENGINE_CLOCK_PYTHON_BOOTSTRAP_RECEIPT.json), [audit](evidence/STAGE7_ENGINE_CLOCK_PYTHON_BOOTSTRAP_AUDIT.json)에 source·크기·hash·소비 상태를 기록했다. 요청 `python-bootstrap-20261113-01`은 소비됐고 추가 실행 승인은false다. Archive binary를 Git에 넣거나 Actions artifact로 업로드하지 않았다.

Discovery3회는 공개 commit/manifest/release metadata를 gh HTTPS로 읽고 크기를 수신 후 확인한 과정이다. 등록된 payload download와 구분한다. 실제 manifest는841,422bytes이며 원본4metadata snapshot의 hash를 실행 전에 요청에 묶었다. gh 내부 요청·redirect·TLS counter는 계측하지 않아null이다. Curl HTTP200/TLS0/redirect0 수치를 가져오지 않는다. 기본 HTTPS 검증·상속 proxy/CA 경로의 게시 digest 일치이며 publisher 서명/build attestation/독립 host 증명은 아니다. Polling peak는 hard quota나 RSS가 아니고 전체 end-to-end 비용도 측정하지 않았다.

## 정적으로 확인한 bootstrap과 실행 경로

[Member manifest](evidence/engine-clock-python-bootstrap/archive-members.json)는 모든 archive 파일의 실제 SHA256·mode·크기와 directory/link descriptor를 담는다. Archive 경로·중복·지원 타입·링크 해석·byte/entry/depth cap을 확인했다. Gzip/tar는 메모리 버퍼로 streaming하며 파일 트리를 추출하지 않았다. Header·source·wheel·ELF는 data로 읽었고 `ldd`, interpreter, `setup.sh`, ensurepip, venv, package import를 실행하지 않았다. 이 고정 archive 검사는 재사용 가능한 hostile-input admission API가 아니다.

`patchlevel.h`는3.11.18, sysconfig는 CPython311/x86_64 Linux와 shared build를 명시한다. `ensurepip` source의 pip24.0/setuptools79.0.1 상수, 빈 `WHEEL_PKG_DIR`, 실제 bundled wheel2개와 기존 site-packages metadata가 일치한다. Wheel2개의1,038 RECORD row/11,470,754decoded bytes를 검증했다. 이는 archive 내부 bytes/RECORD 일치이며 PyPI 원본·서명 검증은 별도로 하지 않았다. 기존 PR47 도구 pip26.2.2/setuptools80.9.0/wheel0.45.1과 bootstrap 버전을 혼동하지 않는다.

ELF81개의 정적 metadata를 읽었다. `bin/python3.11`은 x86_64이고 PT_INTERP는 `/lib64/ld-linux-x86-64.so.2`, RUNPATH는 `/opt/hostedtoolcache/Python/3.11.18/x64/lib`다. libpython에도 같은 절대 RUNPATH가 있다. DT_NEEDED 중 archive 내 같은 basename이 없는19이름을 [정적 결과](evidence/engine-clock-python-bootstrap/static-inspection.json)에 남겼다. 이는 파일명 수준의 관측이며 실제 loader 해석·transitive closure·GLIBC symbol version·ABI·실행 가능성 증거가 아니다.

배포물의 `setup.sh`는 기존 toolcache 경로를 지우는 분기와 pin 없는 pip upgrade 명령을 포함한다. [비활성 후보 binding](evidence/STAGE7_ENGINE_CLOCK_PYTHON_BOOTSTRAP_BINDING.json)은 이 script의 실행을 금지한다. 원본 archive/파일은 그대로 보존한다. 대신 미래 실행기는 검토된 경로에 정확한 bytes를 stage하고, 고정된 bundled bootstrap 및 PR47 도구만 offline으로 다뤄야 한다. 현재 이 실행기는 없다.

Archive에는 `distutils-precedence.pth` startup hook1개도 있다. 파일 hash를 manifest/binding 입력에 묶었고 실제 startup 동작은 실행하지 않았다. `-I`만으로 모든 site hook이 없어졌다고 간주하지 않는다. [입력 manifest](evidence/STAGE7_ENGINE_CLOCK_PYTHON_BOOTSTRAP_INPUTS.json)는 source/config/bootstrap/ELF와 이 한계를 분리한다.

## 다음 단계와 미완료 게이트

다음은 후보의 실제 OS/loader 및 transitive library hash·ABI 입력을 고정하고, prefix/mount·startup hook·venv staging·network 차단·용량/시간/cleanup 제한을 구현·fixture 검증하는 일이다. 원래 prefix를 다른 위치로 고치거나 loader 환경변수로 우회하지 않는다. 이 prefix는 builder 후보용이고 기존 main runtime inventory roots를 바꾸지 않는다. 다른 배포가 필요하면 별도 입력/정책 검토를 먼저 한다.

Archive SHA·manifest artifact SHA·canonical SHA는 설치된 runtime identity가 아니다. PR47 build policy의 null required runtime/bootstrap/launcher refs와 기존 image16참조는 채우지 않았다. Candidate binding은 새 입력 namespace이며 OS lock·실행기·fixture·실제 bootstrap/venv/version 확인과 새 소비 요청이 없으므로 **build_ready=false**다. 전체 Python/base/deb/asset lock·image 준비·Task3는 미완료다.

기존 tracked416파일은 continuation/parent Task3 status2개 외 그대로 보존한다. Producer70/workflows44/consumed registry8·기존 tools/tests/policies/proposal·원본 archive/controller/review workspace를 바꾸거나 삭제하지 않는다. Product 코드/시험은 없고 동일한 local 전체 suite는 반복하지 않는다. 최종 independent review와 기본 CI는 실제 source와 별도 HEAD로 기록한다.

새 native/provider/engine/Xvfb/GL/GPU/clock·공식 model/weights/ORT·image build/pull/load/run은0이다. 생성 SMALL ONNX 기본 CI는 별도다. 새 RGB/I420/공식 ONNX 일치율·first-divergence 수치는 없다. 기존 strict0/4 FAIL, expanded NOT_RUN, ABBA terminal FAIL/7null/4case·6비교 NOT_RUN, geometry·optics·full-S 한계와 **Stage7 INCOMPLETE**를 유지한다. Nativeallowance0, main 병합·Cloud 게시 없음.

독립 whole-branch/raw 검토는 `b1e0989bde0d95403503a61fb04af9eb58834f63`에서 Critical0/Important0/Minor0으로 증거 범위를 수락했다. [검토 기록](evidence/STAGE7_ENGINE_CLOCK_PYTHON_BOOTSTRAP_REVIEW.md)을 보존하고, 범위 밖7항목의 root 판단·비용은 audit에 남겼다. 보류 Minor는 없다. 이후 receipt-only HEAD와 기본 CI는 Draft PR에서 별도 확인하며, 검토 수락은 설치 identity·OS/ABI·bootstrap/source/image/native 실행이나 merge 승인이 아니다.

최종 문서 검사에서 검토 기록의 Markdown 줄끝 공백2곳을 정리했다. 원문 bytes는 commit `1ad4dafd1c16585e3338ab4bcf0d253b7b9aaff0`와 private 원본에 보존하고, audit에 원문·표시용 전사본의 hash를 구분했다. 검토 내용·판정과 제품 코드는 바뀌지 않았다.
