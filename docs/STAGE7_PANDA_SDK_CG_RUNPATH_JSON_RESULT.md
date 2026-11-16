# SDK3 JSON 수락기 — 별도 DATA 정적 검증 결과

2026-11-16 KST. 새 계약의 수락 결과는 `AUTHENTICATED_CG_RUNPATH_JSON_SELECTED_STATIC_ACCEPTED_NOT_RUNTIME`이다. 기존 SDK3 실행43786081196/작업133033912459/산출물14191115165를 읽기 전용으로 재검증했다. 재빌드·새 요청 활성화·산출물 다운로드·이미지 조작·대상 실행은 모두0이다.

원인은 ELF 버전표의 정수 인덱스가 JSON에서 문자열 키로 저장되는 표현 차이였다. 새 수락기는 두 버전표의 직접 인덱스 키만 정규화하고, 자료형·값·순서·버전·라이브러리 연관·모든 제공자 진단을 비교한다. 제공자 기록의 검증된 `data_path` 위치 표지만 비교에서 제외한다. 소비된 소스310개와 원래 FAILED 수락 기록(SHAd21eca8a87c507f2cabc6f86e3a293b2c48ce23105a4864344655a94acad789d)은 변경하지 않았다.

새 감사 소스3280bb0d39645f384955ef99722520f50c5eb063의 소스314개를 Git 바이트와 확인했다. 소스 CI push43800686533/PR43800704764의4개 작업은 모두 attempt1SUCCESS/artifacts0이다. 원래 소스602f858/요청 전용 자식40dd718/원래 소스CI/실행/작업/산출물/61,661,546B ZIP/SHA와23개 파일을 재인증·재해시하고, 빌드 증거·현재 이미지 권위/인벤토리·저장된 제공자 바이트·실제 ELF를 독립 검사했다.

| 확인 대상 | 관측 결과 |
|---|---|
| 루트 ELF SHA256 | 27cd80fb1c06feaa7da8b5658cce918d1e3ab71c304a0c0ce42e30688ac008f3 |
| 실제 RUNPATH | 루트와 buildPanda 모두 `$ORIGIN`, RPATH 없음 |
| 오프셋 | major0x688/minor0x68c/vendor0x670 |
| 선택된 배치/API | 정렬16, vtable1024B,33개 내보내기, 상태 인스턴스1 |
| 루트 강한 심볼 | 1047개 해결/누락0/기존 약한 예외3 |
| 제공자 그래프 | 제공자22개/간선80개/지원하지 않는 기능0 |
| 제공자별 엄격 누락 | Cg13,CgGL5,dtool13,dtoolconfig15,panda48,pandaexpress16 — 그대로 보존 |

루트 결과는 전체 의존성 폐쇄나 런타임 적합성을 뜻하지 않는다. 기존 SONAME 기반 버전 심볼 판정의 제공자6개 블록이 남아 있다. full_object_abi/full_dependency_closure/runtime_mapping/previous_abort_fixed/candidate_installed/native_admitted/stage7_complete는 모두false이며, 관측하지 않은 default-off는None이다. 과학 실행 허용량0, strict0/4FAIL, Stage7INCOMPLETE를 유지한다.

검증: 실제 CPU ELF 버전표 JSON 왕복을 포함한19개 집중 시험PASS. 전체 로컬1853건 중1846PASS/7skip이다(일반/tmp1850건+실제/dev/shm3건). 기존 6개 가상 실행 시험의 Errno28을 재현한 뒤 실제 임시 경로를 fixture 환경에 등록했으며, 검사 가드·용량 사실·기존 시험 파일은 바꾸지 않았다. 정식 CI는 수정하지 않은 전체 발견 방식으로1853건을 확인했다.

독립 전체 브랜치 검토1회에서 발견된 Important2건은 새 프로세스에서 RED→GREEN으로 확인하고 한 번의 수정 과정에서 해결했다. 음성 기록 생성은 의존 모듈 로딩보다 먼저 수행하고, 최종 기록은 임시 파일/fsync/원자적 교체로 저장하여 실제 파일 쓰기 제한 오류에도 음성 기록을 보존한다. Critical/미룬Minor/재검토는0이다.

[Draft128](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/128)은 기존 Draft127을 기준으로 별도 유지한다. main·기존Draft·기존 실행 창·원본·설치SDK/이미지는 보존한다. 자체 scratch만 보관 후 제거하며,31개 형제 작업 공간의3846개 SHA는 유지한다. 환경 게시와 병합은 수행하지 않는다.

최종 문서 HEAD의 CI4개 작업/깨끗한 체크아웃/정확한 원격 HEAD 확인은 문서 커밋 후 `output/stage7-panda-sdk-cg-runpath-json-01/final-verification.json`에 기록한다. 이 영수증이 최종 운영 마무리 상태의 기준이다.

- [새 수락 기록](evidence/panda-sdk-cg-runpath-json-01/actual/acceptance.json)
- [정적 의미 요약](evidence/panda-sdk-cg-runpath-json-01/actual/semantic-summary.json)
- [증거 인덱스](evidence/panda-sdk-cg-runpath-json-01/proof-index.json)
- [검토 결과](evidence/panda-sdk-cg-runpath-json-01/wholebranch-review.md)
- [판단과 비용의 전체 기록](STAGE7_PANDA_SDK_CG_RUNPATH_JSON_LEDGER.md)
