# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과

2026-11-16 KST. 제공자 버전 심볼 항목110건의 읽기 전용 진단을 완료했다. 새 결과는 `AUTHENTICATED_PROVIDER_VERSION_WITNESSES_NOT_RUNTIME`이다. 이는 실제 로더 바인딩이나 기존 엄격 판정의 통과를 뜻하지 않는다.

저장소는 rownlvh8875-coder/big-model-closed-loop-benchmark, 브랜치는 feature/panda-provider-version-witness-v1이며 [Draft129](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/129)을 기존 Draft128 기준으로 유지한다. 감사 소스 전체 SHA는 `ee70b3c046794aed49fedba79a40d4166d024712`이다. 최종 문서 HEAD는 커밋 후 `output/stage7-panda-provider-version-01/final-verification.json`에 기록한다.

새 코드 두 파일은 scripts/panda_provider_version_witness.py:189(순수 버전/간선/심볼 근거 검사), scripts/audit_panda_provider_versions.py:104(소스·CI·출처·바이트 재검증과 실패 기록)이다. 각각 대응하는 새 시험 파일을 추가했다. 이전7930파일/모드와 source314, 원래FAILED 및 새selected-static 수락 기록은 변경하지 않았다.

확인된 원인은 기존 available_imports가 요구된 version_library와 제공자 SONAME의 일치를 요구한다는 점이다. 현재 이미지의 libpthread/libdl은 해당 버전 정의와 libc 의존성을 유지하지만, 실제 같은 이름·자료형·버전의 일반 함수 내보내기는 libc.so.6에 있다. 새 진단은 기존 누락을 유지한 채 요구 라이브러리 선택·버전 정의·직접 의존 간선·고정 libc 내보내기를 각각 확인한다. 임의의 SONAME 완화나 전역 이름 검색으로 통과시키지 않는다.

| 요구 라이브러리와 버전 | 확인한 항목 |
|---|---:|
| libpthread.so.0 / GLIBC_2.2.5 | 87 |
| libpthread.so.0 / GLIBC_2.3.2 | 6 |
| libdl.so.2 / GLIBC_2.2.5 | 17 |
| 합계 / 설명하지 못한 항목 | 110 / 0 |

루트를 포함한23개 객체의 기존 심볼 판정도 대조했다. 기존6개 제공자의 엄격 누락(Cg13,CgGL5,dtool13,dtoolconfig15,panda48,pandaexpress16)은 그대로다. 원래FAILED 기록 SHA는 d21eca8a87c507f2cabc6f86e3a293b2c48ce23105a4864344655a94acad789d, 이전selected-static 기록 SHA는4045e856383d3bf947688f1f4998083f1cb5d8b4ceea5dad94b430ce6e6c0a46로 보존됐다.

원본 SDK3 실행43786081196/작업133033912459/산출물14191115165의 출처를 재인증하고, 기존61,661,546B ZIP과23개 파일·인벤토리 기반 제공자 DATA를 재해시했다. 전체 빌드 증거와 실제 ELF 게이트를 다시 계산하고, 저장된 생산 보고서 및 이전15MiB 게이트와 비교했다. 새 근거는 재계산한 메타데이터에서 만들었다. 기존 ZIP·게이트를 다시 다운로드하거나 복제하지 않았다.

시험: 집중17PASS. 전체 로컬1870건 중1863PASS/7skip이다(일반/tmp1867건+실제/dev/shm3건). 기존 가드·용량 측정·시험 파일은 유지했다. 독립 전체 브랜치 검토1회에서 발견된 버전 정의/요구 인덱스 교집합 문제는 정수 및 JSON 문자열 키 두 형태로 RED→GREEN을 확인하고 한 번의 수정 과정에서 해결했다. 미룬Minor와 재검토는0이다.

소스 CI는 [push43806544432](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43806544432) 및 [PR43806559945](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43806559945)이며4개 작업 모두 attempt1SUCCESS/artifacts0이다. 두 정식 단위시험 로그도1870건/7skip을 확인했다. 최종 문서 HEAD의 별도4개 CI 작업·정확한 원격 HEAD·깨끗한 체크아웃은 최종 영수증으로 마무리한다.

새 SDK 빌드·요청 활성화·산출물 다운로드·추출·이미지 조작·대상/과학 네이티브 실행·병합·환경 게시 모두0이다. 원본 RGB/I420/공식 ONNX 일치율과 최초 불일치를 새로 측정하지 않았다. 카메라 기하학과 원본 PSSM/Chase 경로도 변경하지 않았다. 과학 실행 허용량0, 공식 엄격 반복성0/4FAIL, 확대 반복성 미실행, Stage7INCOMPLETE를 유지한다.

다음 미확인 범위는 실제 로더의 바인딩/네임스페이스/인터포지션 및 전체 객체 ABI이다. 이번 근거로 이전 SIGABRT 수정이나 실행 준비를 선언하지 않는다. full_object_abi/full_dependency_closure/runtime_mapping/previous_abort_fixed/candidate_installed/native_admitted/stage7_complete는 모두false이다. main·이전Draft·실행 이력·원본·설치SDK/이미지와31형제 작업 공간3846개SHA를 보존하며, 자체 scratch만 보관 후 제거한다.

- [새 감사 기록](evidence/panda-provider-version-01/actual/acceptance.json)
- [110건 전체 근거](evidence/panda-provider-version-01/actual/witness-report.json)
- [결과 요약](evidence/panda-provider-version-01/actual/summary.json)
- [증거 인덱스](evidence/panda-provider-version-01/proof-index.json)
- [검토 결과](evidence/panda-provider-version-01/wholebranch-review.md)
- [판단과 비용 기록](STAGE7_PANDA_PROVIDER_VERSION_LEDGER.md)
