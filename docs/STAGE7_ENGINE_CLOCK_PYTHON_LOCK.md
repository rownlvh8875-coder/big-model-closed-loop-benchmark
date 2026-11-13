# Stage7 Python dependency lock 확인 결과

실제 파생 MetaDrive wheel을 입력으로 한 바이너리 전용 의존성 확인은 **`progressbar` 배포 형식에서 차단됐다. 완전한 lock은 아직 없다.** 소스 빌드·대체 패키지·설치로 우회하지 않았다. Task3와 이미지 준비는 미완료다.

## 실제 실행과 증거

기준은 PR45의 `cc6d3a986fb54c128b9d69f4e2a4d10eb7c2c898`다. 실행 전 등록 source HEAD는 `a4b5b1a917caa4cad58510b3f1b59e184d94037d`, 시작은 **2026-11-13 11:07:03 KST**다. 이후 증거·검토 HEAD를 실행 source로 바꾸지 않는다.

| 항목 | 실제 결과 |
| --- | --- |
| 입력 | 보존된 파생 wheel 72,968,610bytes / SHA256 `f949e89ff4bc32b72c8d09f5c61446bbc2b1f9b415b99a077c02b8df77c217f7` |
| 도구 | 기존 Python3.11.17 / pip26.2.2 |
| 후보 대상 | CPython3.11.18 / Linux amd64 / manylinux2.28 이하 호환 tag |
| 호출 | pip dry-run 1회, binary-only, 설치·소스 실행 없음 |
| pip 결과 | exit1, 약4.533520s, 성공 report 없음 |
| 원래 오류 | `No matching distribution found for progressbar` |
| 별도 metadata | PyPI progressbar JSON HTTP200 / TLS verify result0 / redirect0 / curl exit0 / 6,237bytes |
| 전체 operator | 약5.106188s, 실행 전 free60,749,467,648bytes |
| 저장 범위 | 로컬 원본6파일 합계19,988bytes, operation tree 관측 peak493,724bytes |

[요청](evidence/STAGE7_ENGINE_CLOCK_PYTHON_LOCK_REQUEST.json)과 [역사적 operator](evidence/STAGE7_ENGINE_CLOCK_PYTHON_LOCK_OPERATOR.txt)는 실행 전 commit에 등록했다. [실제 receipt](evidence/STAGE7_ENGINE_CLOCK_PYTHON_LOCK_RESULT.json), [pip 원문](evidence/engine-clock-python-lock/pip.log), [PyPI 원문](evidence/engine-clock-python-lock/progressbar-release.json), [audit](evidence/STAGE7_ENGINE_CLOCK_PYTHON_LOCK_AUDIT.json)을 보존한다. 요청 `python-lock-20261113-01`은 소비됐으며 재실행 승인은false다. 원래 attempt의 STARTED 상태는 시작 기록이고, terminal 결과는 receipt/audit에 별도로 남긴다.

Root는 입력 wheel hash, 실제 METADATA의 무조건부 `Requires-Dist: progressbar`, 저장된 각 원본 파일의 크기·SHA256, request/operator hash, pip exit·오류·report 부재, curl 상태와 PyPI 배포 형식을 독립적으로 확인했다. 원래 PR45 요청은 다시 실행하지 않았고 wheel도 다시 만들거나 내려받지 않았다. 현재 원본은 `output/stage7-python-lock-gate/python-lock-20261113-01`에 남긴다. PyPI JSON 외 curl 전체 transfer 원문은 로컬에 보존하고 공개 증거에는 필요한 상태 필드만 옮겼다.

## 확인한 사실과 해석 한계

현재 PyPI JSON에는 progressbar의 5개 release key가 있고 기록된 배포 파일은 모두 `sdist`다. 최신2.5 파일은 `progressbar-2.5.tar.gz`, 게시 size10,046bytes, 게시 SHA256 `5d81cb529da2e223b53962afd6c8ca0f05c6670e40309a7219eacc36af9b6c63`다. **이 hash는 PyPI metadata의 주장이다. 이 작업은 소스 payload를 받거나 hash를 직접 측정하지 않았다.**

따라서 binary-only 정책에서는 이 의존성을 충족하지 못했다. 전체 의존성 그래프가 수학적으로 충돌한다거나 progressbar가 Python3.11에서 실행 불가능하다는 결론은 아니다. `progressbar2` 등 이름이 다른 패키지를 넣거나 요구사항을 삭제하지 않았다. 앞서 출력된 다른 패키지 버전은 후보 metadata이며 선택·hash 검증된 lock이 아니다.

대상 옵션은 wheel 후보를 거르는 용도다. 실제 도구 Python3.11.17과 목표3.11.18은 다르고 pip의 일부 marker는 host에서 평가된다. glibc2.28은 후보 tag 범위이며 base image 선택·ABI·실행 호환성을 증명하지 않는다. Pip 전체 요청 수·network byte 합계는 계측하지 않아null이다. Tree peak는 polling 관측값으로 누적 전송량·메모리·강제 filesystem quota가 아니다. 임시 metadata를 pip가 정리한 사실을 원본 네트워크 응답 전체 보존으로 표현하지 않는다.

## 다음 실행 절차와 보존 게이트

다음은 progressbar2.5의 진짜 source와 build-tool closure를 고정하고, 소스 실행 전 별도 검토를 받는 준비 설계다. 원본 source hash·archive 정적 검사·license·build backend/tool wheel hash·격리/시간/디스크/출력 제한·산출 wheel RECORD 및 원본 대비 payload 검사를 정해야 한다. 기존 패키지 이름/요구사항을 보존하며 수정이 필요하면 별도 정책을 검토한다. 검토 전 `pip wheel`·`setup.py`·sdist metadata 실행은 하지 않는다.

그 뒤에만 완전한 Python graph와 base/Python/deb/asset digest를 해석하고 review한다. 현재는 incomplete lock/Dockerfile/adapter/workflow를 만들지 않는다. Parent Task3의 첫 checkbox도 미완료이며, image 준비16참조null/native allowance0을 유지한다.

기존 tracked389파일은 status 문서2개를 제외하고 동일하게 보존한다. Producer70/workflows44/consumed registry8·Task1/2·파생 변환기/시험/policy·비활성 proposal·과거 raw/controller/review workspace를 변경하거나 삭제하지 않는다. 새 product 코드/시험은 없고 변경되지 않은 local 전체 suite는 반복하지 않는다. 최종 Draft PR의 기본 CI는 실제 run/job 결과를 별도로 기록한다.

새 native process·공식 model/weights/ORT·provider/engine/Xvfb/GPU/clock·image build/pull/load/run은0이다. 기본 생성 SMALL ONNX CI는 별도다. 새 RGB/I420/ONNX 일치율·first-divergence 자료는 없다. 과거 strict0/4 FAIL, expanded NOT_RUN, ABBA terminal FAIL/7null/4case·6비교 NOT_RUN, geometry·optics·full-S 한계, Stage7 INCOMPLETE를 유지한다. Cloud 게시와 main 병합은 하지 않는다.

독립 whole-branch 검토는 `d220a1f86f1eff512fa324c32f0162ca707e734e`에서 Critical0/Important0/Minor0으로 증거 범위만 수락했다. [검토 원문](evidence/STAGE7_ENGINE_CLOCK_PYTHON_LOCK_REVIEW.md)을 보존한다. 검토 범위 밖 D1–D4는 audit에 root 판단과 비용을 기록했고, 이후 최종 HEAD/기본 CI는 Draft PR에서 별도로 확인한다. 이번 단계의 보류 Minor는 없다. 이전 PR45의 M1 attribute 표현 보류는 이번 검토의 지적사항으로 재분류하지 않는다.
