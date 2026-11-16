# SDK3 캡처 진행 관측: 초기화 93초·캡처 한 쌍 42초

2026-11-16 22:46 KST 기록. **이번 실행에서는 렌더링이 진행됐으며, 160초 제한이 두 번째 Wide 캡처 중 만료됐다.** 월드 준비에93.233초, 첫 Road/Wide 한 쌍에41.581초가 걸렸다. 완료된 세 렌더 task step은 각각20.221·21.211·21.199초 후 복귀했고, CPU RGB 읽기는 각각 약0.002초였다. 기존의 불투명한 시간 초과를 실제 진행 경계와 비용으로 구분했다. 전체7자세 재현·픽셀 기하·원래 실패 수리는 아직 확인하지 못했다.

[실제 관측43877667984](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43877667984)은 workflow420168670/attempt1이다. 검토·수정 소스`e4a5cfcf1581272692f131caa75e1b3ee97a0290`, 요청 파일만 추가한 활성화`d9eed91761b927989a3ca3b6e32f933f036a5883`으로 **새 렌더러1개·공식 모델0개·ONNX 추론0회**를 실행했다. 관측 자료 검증은 성공했지만 native는 시간 초과로 실패했다. Actions의 success는 `TRACE_RECORDED_NATIVE_TIMEOUT`이라는 유효한 관측의 수집 성공이며, native 렌더링·재현·수리 PASS를 뜻하지 않는다.

| 관측 경계 | 저널 시작 후 시각 | 소요 wall / process CPU |
|---|---:|---:|
| provider 초기화 진입 | 4.488초 | — |
| WORLD_READY | 93.233초 | 진입 후88.745초 |
| 캡처1 Road task step | 93.234→113.455초 | 20.221 / 20.220초 |
| 캡처1 Road CPU RGB 읽기 | 113.455→113.457초 | 0.00177 / 0.00177초 |
| 캡처1 Wide task step | 113.459→134.670초 | 21.211 / 21.210초 |
| 캡처1 Wide CPU RGB 읽기 | 134.670→134.672초 | 0.00186 / 0.00187초 |
| 캡처1 전체 완료 | 134.815초 | 41.581 / 41.581초 |
| 캡처2 Road task step | 134.816→156.014초 | 21.199 / 21.197초 |
| 캡처2 Road CPU RGB 읽기 | 156.015→156.016초 | 0.00170 / 0.00170초 |
| 캡처2 Wide task step 진입 | 156.018초 | 종료 기록 없음 |

저널31행의 원래 호출 순서·중첩·완료/오류 전파를 재검증했다. 정확히 첫 캡처1개가 복귀했고, 그 원본 Road/Wide 이미지2개를 제한된 크기로 해제해 source SHA와 대조했다. 둘 다 기존 첫 프레임의 원본 SHA와 정확히 일치한다. 캡처2 Road getter는 복귀했지만 한 쌍의 원본 복사 관찰자까지 도달하지 않았으므로 그 픽셀을 보존·검증했다고 세지 않았다. 두 번째 Wide의 task step은 열린 상태였다. 전체7자세의 이미지 동등성은 `null`·미확인이다.

30초 주기의 Python 스택5개도 보존했다. 처음2개는 `base_engine.py:395`의 reset 렌더 반복, 다음1개는 reset 안의 task step→`ShowBase.__igLoop`, 마지막2개는 원래 카메라 캡처→perceive→task step→`ShowBase.__igLoop`에 있다. 고정 이미지 tar를 **데이터로만** 읽어 해당 줄을 대조했다. `base_engine.py:394–395`는 원래5회 `graphicsEngine.renderFrame()` 반복이며, `ShowBase.py:2158`도 `self.graphicsEngine.renderFrame()`이다. task step의`Task.py:504`는 `self.mgr.poll()`이다. 이미지·레이어·파일 SHA와 발췌는 [고정 스택 소스](evidence/sdk3-capture-progress-01/actual/frozen-stack-source.json)에 있다. 원래 reset/렌더 호출을 생략하거나 줄이지 않았다.

마지막 스택은 두 번째 Wide 진입 이전에 수집됐다. 따라서 **마지막 스택이 Wide2 내부를 직접 관측했다고 주장하지 않는다.** 종료 시점의 열린 Wide2 경계는 저널에서, 선행 renderFrame 경로는 별도의 스택에서 확인했다. task step은 전체 엔진 작업을 실행하므로 이를 해당 카메라만의 GPU 렌더 시간으로 해석하지 않는다. Python 스택은 네이티브 GPU/소프트웨어 래스터라이저 내부 스택이 아니며, 고유 원인이나 모든 교착 가능성을 배제하는 자료도 아니다.

부모의160초 watchdog은 실제 자식 종료`-9`를 기록했다. 컨테이너 종료1, Xvfb 종료0, OOMKilled false, 소유 컨테이너 제거true다. 메모리 최고 사용량은5,820,428,288B로10GiB 제한 안에 있었다. `/proc/stat`·status·wchan을 실제 자식PID10과 대조했으며 상태R, user15720/system305ticks, wchan0이었다. tick을 별도 주파수 가정으로 초로 바꾸지 않았다. 완료된 task step의 process CPU와 wall 시간이 가까우며 렌더 호출들이 복귀했다는 점은 이번 실행의 긴 렌더 비용을 뒷받침한다. 강제 종료 전 provider.close·래퍼 복원·최종 모듈 감사가 완료됐다고 주장하지 않는다.

실제 명령과 SDK/core/BaseCamera/reference 바이트, softpipe, 기존 초기 task 목록, 2CPU·10GiB·privateIPC·읽기 전용 루트·uid65534·네트워크 없음·tmpfs512MiB를 확인했다. 원래 카메라 캡처와 센서/task 호출은 그대로 한 번씩 호출했고, 추가 GPU query/readback/task tick·렌더 설정·시계·기하 관찰은 넣지 않았다. 관측기와 이미지 보관이 실행 시간에 영향을 주므로 이번 값은 관측된 이 실행의 값이며 과거 두 실행의 정확한 타이밍으로 소급하지 않는다.

이번 실행에서는 준비93초와 첫 쌍42초 때문에160초 예산 안에 두 번째 쌍도 완료하지 못했다. 같은 쌍당 비용이 유지된다는 단순 추정은7자세에 약384초이며, 기하 조사45초와 변동 여유는 별도다. 이는 실측 완료 시간이 아니다. 다음 단계는 이 자료에 근거한 더 긴 단일 렌더러 예산을 별도 버전 요청으로 설계하는 것이다. **이번 요청의160/180초·자식1개 한도를 늘리거나 재시도하지 않았다.** 해상도·태스크·그림자 등을 바꿔 원래 장면을 가볍게 만들지도 않았다.

실행 전 단일 전체 변경 검토의 Important3개는 한 번의 RED→GREEN 수정 단계에서 처리했다. 누락·재정렬·중복·오류 은폐 trace 거부, 자식PID에 결합된 제한된 proc 증거 검증, 원본 불일치 시 diagnostic PASS 방지를 검증했다. 관련85개 CPU 회귀 테스트와 actionlint가 통과했다. 정확한 실행 소스의 canonical push43877069662/PR43877080639 네 작업 모두 성공했고, 양쪽 단위 테스트는 각각1,968개·7개 건너뜀이다. SDK/Panda/GLX/공식 모델은 로컬에서 실행하지 않았다.

산출물14231675746의 ZIP은1,796,462B, SHA`d3f86c502a03033b32a2f3bfc79ac643b961c52c6ab0efa77f21a31fb287491c`로 GitHub API와 대조했다. 원본30개 파일의 크기·SHA·보존 경로를 색인에 기록했고 JSON/JSONL/스택21개는 Git에, 원본 RGB·일반 로그9개는 Actions와 output에 보존했다. 이전48개 원본 이미지는 입력 인증에만 사용했고 새 이미지·새 추론으로 세지 않았다. 원본 이미지·SDK·실패 기록 및 이전31개 증거 디렉터리/3,846파일의 해시와 모드도 보존했다.

기존 공식 모델 행렬은 **3/4 PASS·전체 FAIL**, Stage7는 미완료다. 원래7번째 Road 한 픽셀 차이를 다시 관측하거나 픽셀 소유권·원인·수리·원래 폐루프 동등성을 증명하지 않았다. 게시·레지스트리 업로드·main 병합은 없다.

근거: [독립 관측 검증](evidence/sdk3-capture-progress-01/actual/independent-observation.json), [경계별 시간·스택 분석](evidence/sdk3-capture-progress-01/actual/boundary-analysis.json), [원본 저널](evidence/sdk3-capture-progress-01/actual/bundle/renderer/progress.jsonl), [원본 스택](evidence/sdk3-capture-progress-01/actual/bundle/renderer/stacks.log), [원본 보관 색인](evidence/sdk3-capture-progress-01/actual/retained-index.json), [검토·수정](evidence/sdk3-capture-progress-01/wholebranch-review.md), [판단 장부](evidence/sdk3-capture-progress-01/ledger.md). 최종 문서 커밋 CI와 초안PR134·기존PR133·main·원본 보존 영수증은 `output/stage7-sdk3-capture-progress-01/final-closeout/verification.json`에 별도로 남긴다.
