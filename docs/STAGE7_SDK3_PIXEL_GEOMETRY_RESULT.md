# SDK3 단일 픽셀 CPU 기하 진단: 두 렌더러의 160초 제한 실패

2026-11-16 22:03 KST 기록. **실제 진단은 실패했고, 픽셀 기하 후보를 얻지 못했다.** 두 독립 렌더러 자식 모두 월드 초기화 후 160초 watchdog에 걸렸다. 이번 결과로 원본 픽셀과의 동등성, 기하 후보, 픽셀 원인 또는 수리를 판정할 수 없다. 기존 공식 모델 4조건 행렬은 **3/4 PASS·전체 FAIL**, 7단계는 미완료 상태다.

[실제 실행 43870880328](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43870880328)은 workflow420125951, attempt1, 두 작업 모두 failure다. 검토·수정된 소스는 `6423b55624bcd0785056cb0e5577abda1b0dc52b`, 요청 파일만 추가한 활성화는 `b498db9f247f93f57b1e4e19e0b921d9f6440557`이다. 실행 전 해당 소스의 canonical push43870103980/PR43870112433 네 CI 작업이 모두 성공했으며, 양쪽 단위 테스트 로그는 각각 1,951개·7개 건너뜀이다. **CI 통과와 실제 렌더러 실패를 분리한다.**

| 항목 | 반복 0 | 반복 1 |
|---|---|---|
| 새 렌더러 자식 | 1 | 1 |
| 공식 모델 프로세스 / ONNX 추론 | 0 / 0 | 0 / 0 |
| 마지막 영속 체크포인트 | WORLD_READY | WORLD_READY |
| 자식 watchdog | 160초 TimeoutExpired | 160초 TimeoutExpired |
| 기록된 native 종료 코드 | null·미확인 | null·미확인 |
| 컨테이너 종료 / Xvfb 종료 | 1 / 0 | 1 / 0 |
| OOMKilled / 소유 컨테이너 제거 | false / true | false / true |
| cgroup 메모리 최고 사용량 | 5,821,292,544 B | 5,824,749,568 B |
| 7번째 목표 이미지 / geometry.npz | 없음 / 없음 | 없음 / 없음 |

두 컨테이너 ID와 프로세스 UUID가 각각 서로 다름을 확인했다. 두 컨테이너 안에서 PID가 모두10인 것은 별도 PID 네임스페이스의 값이므로 독립성 판단에 사용하지 않았다. 실제 SDK/core/BaseCamera 바이트와 참조 파일 SHA, 2CPU·10GiB·private IPC·읽기 전용 루트·네트워크 없음·uid65534 및 모델/의존성 마운트 부재를 원본 명령과 기록에서 확인했다. 소유 컨테이너는 모두 제거됐지만, 강제 종료 전 provider.close·getter 복원과 최종 모듈 감사가 완료됐다고 주장하지 않는다.

`WORLD_READY` 기록의 captures는 빈 배열이다. 루프 중 매 프레임을 영속 저장하지 않으므로 **실제 완료한 캡처 수는 알 수 없다**. 첫 캡처에서 막혔다거나 첫6프레임이 불일치했다고 해석할 수 없다. 7번째 Road CPU 읽기 직후 체크포인트·목표 이미지·기하 아카이브가 없으며, 느린 렌더링·특정 캡처 정체·교착을 구별하는 스택/시간 자료도 없다. `child_finalized_before_server_stop` 표시를 native 성공 종료로 승격하지 않는다. 상위 양성 검증기는 컨테이너 종료1을 올바르게 거부했다.

실험은 이전 실패 조건 seed20261110/s_curve_left_right의 동일한 첫7카메라 진입 자세를 공식 모델 없이 재현하도록 설계했다. 첫6프레임의 Road/Wide SHA와 알려진 7번째 Road 두 가지 및 Wide SHA가 정확히 일치해야 이전 이미지와의 동등성을 인정한다. 이번에는 그 비교를 수행할 자료를 얻지 못했다. 기존 [1픽셀 차이](STAGE7_SDK3_RGB_FORENSICS_RESULT.md)의 위치(좌상단 원점·0기준596,494), RGB `[167,163,158]` 대 `[199,187,0]`를 이번에 다시 관측했다고 주장하지 않는다.

준비된 CPU 관찰은 원래 Road 읽기 직후·카메라 복원 전에 중심/네 모서리 광선과 CPU 삼각형을 기록한다. 이 다섯 광선은 실제 MSAA 위치가 아니며 CPU net state도 GPU cull/draw state가 아니다. 수치 허용값은 CPU 계산에만 적용하며 이미지 해시는 완전 일치가 필요하다. 실제 CPU 후보조차 없는 이번 관측에서 GPU 소유권·깊이 동률·그림자/재질 고유 원인·수리 성공을 주장할 근거는 없다.

실행 전 단일 전체 변경 검토에서 확인한 bootstrap·순회 예산·NPY 헤더 할당 문제는 한 번의 수정 단계에서 RED→GREEN으로 검증했다. 관련68개 CPU 테스트와 actionlint 및 전체 CI가 통과했다. 실제 Panda API·렌더 시간·최종화 동작은 그 CPU 테스트가 증명하는 범위 밖이다.

다음 원인 구분에 필요한 것은 제한 시간 안의 캡처별 진행 기록과 시간 초과 전 스택 관측이다. 이를 통해 콜드 렌더 비용과 정체 위치를 구분한 뒤 별도의 버전 요청과 예산을 정해야 한다. 이번 두 자식 예산은 모두 사용했으며, 제한 시간을 늘린 재실행이나 추가 모델 실행은 하지 않았다.

원본 ZIP 두 개를 GitHub API의 크기·SHA와 대조했고 안전한 경로/해제 크기 제한으로 수집했다. 산출물14228082465는43,533,073B, SHA`e6546c03bc0c5249fcfa1e270abd76ac83ee4ed995c1117dc82ee88388a77bae`; 산출물14227059497은43,533,074B, SHA`0b78018ed15b7fced29523c2ac142c230831bec8c3163ce6dfabd570337128e1`이다. 두 ZIP에 포함된 과거 full-RGB 자료는 새 이미지나 새 추론으로 세지 않았다. 전체662개 파일의 크기·SHA·보존 경로를 색인에 기록했다. JSON/TXT는 새 증거 폴더에, 큰 압축 이미지·로그는 Actions와 output에 보존했다.

근거: [독립 실패 분석](evidence/sdk3-pixel-geometry-01/actual/negative-analysis.json), [양성 검증 거부 결과](evidence/sdk3-pixel-geometry-01/actual/independent-comparison.json), [원본 보관 색인](evidence/sdk3-pixel-geometry-01/actual/retained-index.json), [정확한 소스 CI](evidence/sdk3-pixel-geometry-01/source-ci-reviewed/verification.json), [검토·수정](evidence/sdk3-pixel-geometry-01/wholebranch-review.md), [판단 장부](evidence/sdk3-pixel-geometry-01/ledger.md), [원본 해시 보존](evidence/sdk3-pixel-geometry-01/original-preservation.json). 최종 문서 커밋의 CI 및 초안 PR133·기존 PR132·main·원본 보존 확인 영수증은 `output/stage7-sdk3-pixel-geometry-01/final-closeout/verification.json`에 별도로 기록한다. 환경·레지스트리 게시나 main 병합은 하지 않는다.
