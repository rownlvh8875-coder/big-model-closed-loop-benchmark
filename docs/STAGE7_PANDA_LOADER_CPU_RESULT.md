# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과

2026-11-16 KST. 고정된 이미지 동적 로더를 작은 CPU 시험4개로 관측했다. 결과는 `FOUR_CPU_LOADER_VERSION_CASES_OBSERVED_NOT_SDK_RUNTIME`이다. 로더 프로세스4개, 확인된 CPU 진입2개, 의도한 로더 실패2개이며 SDK/GLX/공식 모델 실행은0이다. 이 결과를 공식 MD-V3의4조건 반복성 PASS로 해석하지 않는다.

저장소 rownlvh8875-coder/big-model-closed-loop-benchmark, 브랜치 feature/panda-loader-cpu-profile-v1, [Draft130](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/130). 감사 소스 전체 SHA는2577fe4167a3c69a81166b6c810e476384730eee이다. 최종 문서 HEAD는 커밋 후 output/stage7-panda-loader-cpu-01/final-verification.json에 기록한다.

새 파일 [panda_loader_cpu_fixture.py:144](../scripts/panda_loader_cpu_fixture.py#L144)는 고정 nostdlib C/어셈블리·버전 스크립트의 6개 컴파일 명령을 생성한다. [ELF 검증:218](../scripts/panda_loader_cpu_fixture.py#L218)과 [실행:356](../scripts/panda_loader_cpu_fixture.py#L356)은 실제 명령 바이트·재배치·페이지 매핑·사설 의존 그래프·환경·추적 로그·시도 횟수를 검사한다. scripts/probe_panda_loader_versions.py는 소스322/Git/CI/이전 판정/이미지 출처/로더 SHA/명시 실행 플래그/고정 출력 위치를 모두 확인한 뒤 네 번만 호출한다. 대응 시험 파일2개를 추가했다. 기존7997파일/모드와 소스318, 모든 이전 판정은 보존했다.

| CPU 시험 | 실제 반환값 | 관측 |
|---|---:|---|
| 동일 라이브러리의 기본 버전 | 7 | legacy 제공자 연결 |
| 별도 merged 라이브러리의 명시적 비기본 버전 | 7 | 요구 라이브러리 버전 확인 후 merged 제공자 연결 |
| 요구 라이브러리에 버전 없음 | 1 | 라이브러리 버전 검사에서 거부, probe 심볼 연결 없음 |
| 실제 제공 심볼의 버전 불일치 | 127 | 명시적 심볼 버전 검사에서 거부, probe 심볼 연결 없음 |

네 PID는326214/326215/326216/326217이다. 각 명령의 전체 stderr/빈 stdout/종료 상태/프로세스 정리 기록을 보존했다. 반환값만으로 성공을 판단하지 않고, GNU 로더의 버전 검사 및 정확한 제공자 바인딩 로그와 함께 검증했다. 첫 두 시험의 함수는 상수7을 반환하고 어셈블리 진입점은 SYS_exit만 수행한다. 나머지 두 시험은 진입 전에 실패했다.

로더는 기존 인증 이미지의 /usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2,236616B,SHA5fc0940888e9d2e1a00e66d6b1a559c36364ee867683652e1074fa576952cc3f이다. 캐시 원본 DATA의0600권한/바이트를 유지하고, 검증한 사설 복사본만0500으로 실행했다. 이미지 아티팩트14156262448과 원래 SDK3 실행43786081196/작업133033912459/산출물14191115165의 출처를 다시 확인했다. 이미지/SDK를 새로 만들거나 다운로드·압축해제·컨테이너 실행하지 않았다.

확인된 사실은 요구 라이브러리의 버전 존재 여부와 실제 심볼 제공자 선택이 별개의 조건이라는 점이다. 해당 버전이 있는 사설 legacy stub을 유지하면 다른 SONAME의 명시적 비기본 버전 심볼이 선택됐고, 어느 한 조건을 깨면 각각 다른 오류로 거부됐다. 선행110정적 근거와 일관되지만, 실제 SDK의110심볼 바인딩·객체 ABI·네임스페이스/인터포지션을 실행 검증한 것은 아니다. 기존6개 엄격 차단, 원래FAILED/selected-static/witness 판정은 변경하지 않았다.

시험: 집중19PASS. 전체 로컬1889건 중1882PASS/7skip이다(일반/tmp1886건+실제/dev/shm3건). 독립 전체 브랜치 검토1회에서 발견한 Important2건은 심볼0재배치/미해석 태그 및 둥근 페이지 별칭이었다. 실행하지 않는 ELF 자료8종으로 RED→GREEN을 확인하고, 정확한 재배치 수·동적 태그/플래그·4KiB 정렬/순서/비중첩LOAD·RX명령·RW비실행GOT 검사로 차단했다. 변조 자료는 로더를 시작하기 전에 거부했다. 재검토는 없었다.

소스 CI [push43815749321](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43815749321) 및 [PR43815807296](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43815807296)의4개 작업은 attempt1SUCCESS/artifacts0이며 두 단위시험 로그 모두1889건/7skip을 확인했다. 최종 문서 HEAD의 별도4개 CI/깨끗한 체크아웃/정확한 원격 HEAD는 최종 영수증에 기록한다.

미룬 Minor1건: 임의의 중첩 manifest.json은 일반 검증기의 파일·크기 집계에서 빠진다. 고정 생성기는 이를 만들지 않고 로드 대상도 아니지만, 자원 집계 후속 보강이 필요하다. 이번 Important 수정 과정에서 함께 수정하지 않았다.

공식 모델·과학 실행 허용량0, SDK 실행0, 공식 엄격 반복성은 기존0/4FAIL, 확대 재시험 미실행, Stage7INCOMPLETE이다. 원본 RGB/I420/공식 ONNX 일치율과 최초 불일치를 새로 측정하지 않았고 카메라 기하학·PSSM/Chase 경로를 변경하지 않았다. full_object_abi/full_dependency_closure/runtime_mapping/previous_abort_fixed/candidate_installed/native_admitted/stage7_complete는 모두false이다. 병합·환경 게시를 하지 않았다.

남은 큰 작업은①실제 SDK 바인딩/전체 객체 ABI 및 이전SIGABRT 분석·수정,②GLX/원본 렌더링 경로의 네이티브 검증,③공식 MD-V3 엄격4조건 재시험 후 확대·통합 검증과 병합 판단이다. 기존 과학/네이티브 창을 재사용하지 않고 필요한 검증 범위를 별도로 준비해야 한다.

- [실제 시험 기록](evidence/panda-loader-cpu-01/actual/acceptance.json)
- [네 시험 전체 실행 장부](evidence/panda-loader-cpu-01/actual/cases/ledger.json)
- [관측 요약](evidence/panda-loader-cpu-01/actual/summary.json)
- [증거 인덱스](evidence/panda-loader-cpu-01/proof-index.json)
- [검토 결과](evidence/panda-loader-cpu-01/wholebranch-review.md)
- [판단·비용 기록](STAGE7_PANDA_LOADER_CPU_LEDGER.md)
