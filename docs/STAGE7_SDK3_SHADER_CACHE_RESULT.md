# SDK3 PSSM 행렬·정확한 캐시 검증·실제 단일 재검증 3작업 완료

2026-11-17 KST. **요청한 세 작업을 순서대로 완료했다.** 실제 Panda에서 이전`UnalignedLMatrix4f.getCell` 오류 없이 PSSM owner 배열이 수집됐고,shader3개/6stage가 고정 Panda 전처리를 적용한 기대 바이트와 모두 정확히 일치했다. 새 렌더러1개는388.770초에7자세·14이미지 캡처를 완료했다. 다만 Road4의 두 픽셀 차이가 남아 전체 원본 재현은 실패했다. 기존 공식 모델 행렬3/4PASS·전체FAIL,수리 미입증·Stage7 미완료를 유지한다.

| 순차 작업 | 구현과 실제 확인 |
|---|---|
| 1.PSSM 비정렬 행렬 호환 | core.LMatrix4f로 명시적 복사 후4×4getCell;두 MVP 행렬과 near/far 두 쌍이 유한 값으로 저장됨 |
| 2.Panda 캐시 전처리 반영 | 기대 소스에만 고정 주석·공백·EOF 처리를 적용;실제 캐시6개의 전체 길이·SHA·바이트 일치 |
| 3.CI 후 새 단일 진단 | 정확 소스 canonical4작업 성공·양쪽2,030테스트/7skip 후1회 실행,산출물 독립 검증 통과 |

[실제 실행43985158042](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43985158042)은 workflow420741559/attempt1이다. 실행 소스`9fd62e72b204c42557e40d73c7a336eca765d466`,요청만 추가한 활성화`15b8b4f51f07ff2e6934fc604e906a7dce699bc7`을 사용했다. 기존600초 자식/630초 컨테이너/20분job,2CPU/10GiB,privateIPC·읽기 전용 루트·networknone·uid65534·512MiBtmpfs와 고정 이미지/SDK/core/BaseCamera를 보존했다. 공식 모델0개·ONNX 추론0회이며 추가 렌더러·환경/레지스트리 게시·main 병합은 없다.

첫 작업은 공개된 정렬 행렬 변환 생성자를 이용했다.16개 서로 다른 셀의 행·열 보존,원본 비변경·복사 독립성·비유한 값 거부를 테스트했다. SDK 없는 CPU 객체로 실제 snapshot 함수를 실행해 기존 함수의getCell 실패와 새 함수의 성공을 대조했다. 실제 실행에서는 owner.available=true,shader_complete=true,pssm_owner_arrays_recorded=true이며 예외·잘림 사유가 없다. MVP shape는`[2,4,4]`,near/far shape는`[2,2]`,값은`[[10.0,88.77685546875],[10.0,107.83857727050781]]`다. 이는 owner rig의 CPU 배열이며 실제 shader numeric input 또는 GPU uniform과 같다는 증명은 아니다.

두 번째 작업은 고정 Panda1.10.13 shader.cxx의 처리 중 관측된 입력 범위를 새 정책`panda1.10.13-observed-subset-v1`로 구현했다. 참고 소스 SHA는`aad792a474792b1d7af5c524f8326e718a4ae4cbaecb3b844824910d2d5dccf6`다. 일반 GLSL 컴파일러·전처리기로 주장하지 않는다. 기대 소스의 //주석·행 끝 ASCII 공백을 제거하고 빈 행·마지막LF를 처리한다. block comment·continuation·include/pragma/extension·코드의 quoted token·NUL·비ASCII·초과 크기 등은 거부한다. EOF 역슬래시 예외 한 건은 아래 보류 항목에 명시했다. **실제 캐시 바이트는 정규화하지 않는다.** 실제 캐시를CRLF로 바꾸거나 코드 토큰을 바꾸고 SHA를 다시 계산해도 일치로 인정하지 않는 회귀가 통과했다.

고정 MetaDrive 원본12파일과 pipeline define을 사용해 보도벽·skybox·톤매핑의 기대 캐시를 만들었다. 실제6stage의 전체 바이트가 모두 일치했고,직전 회색 분기 실행43977840900의 실제6개 캐시와도 완전히 같았다. 보도벽 vertex/fragment는1,987/7,996B,skybox는210/428B,톤매핑은466/680B다. source12개68,278B와 합쳐80,045B를 저장했다. 이 결과는 캐시 문자열의 일치이며 실제 실행 program·픽셀 소유권·색 계산의 고유 원인을 증명하지 않는다. GPUprogram/hardwareuniform/ownership/cause/repair/Stage7 proof flag는 모두false다.

| 실제 경계·수명 주기 | 결과 |
|---|---|
| WORLD_READY | 저널 시작 후92.715초 |
| 캡처7쌍 | 각41.396~42.506초,14이미지 검증 |
| shader CPU 관측 | 원래Road7 읽기 직후·카메라 복원 전,367.057~367.060초,경과0.003471초 |
| 기록 | 저널121행,30초 주기 스택12개,원래14task ticks 유지,ORT 미로딩 |
| 종료·정리 | native/Xvfb/컨테이너0/0/0,timeout/OOM없음,provider.close·관찰 래퍼 복원·소유 컨테이너 제거true |
| 메모리 최고 사용량 | 5,820,014,592B |

CPU 기하·재질 수집도 완료했다.1,004삼각형·585정점 중 가장 가까운 후보는 기존 보도벽 삼각형606,거리8.420816이며,보관된 UV·재질·텍스처 상태와 기하 결합 검증을 유지했다. 알려진 PSSM 입력8개×2메시=16개를 기록했고,공개 getter로 읽지 않은 numeric-array 입력은 여전히unavailable이다. CPU owner 배열 확보를 해당 입력의 실제 GPU 값으로 승격하지 않았다. HDR 픽셀 값·실제 depth attachment·MSAA·draw 소유권은 읽지 않았다.

목표 Road7은 노란 분기 전체 SHA`5289613b610abe2270b4e7d98c106608689c55c216b2085d439eb39eec571adb`와 같고 `(596,494)=[199,187,0]`이다. 과거 두 trial의 첫7자세28개 원본을 해제·해시·픽셀 비교했으며,첫6자세의 변경은 Road4의 다음 두 픽셀이다. 그 외 첫6자세11이미지와Wide7은 일치한다.

| 좌표(좌상단 원점·0기준) | 과거 두 trial RGB | 이번 RGB |
|---|---|---|
| Road4 `(175,359)` | [174,169,166] | [140,143,75] |
| Road4 `(555,454)` | [171,166,159] | [131,142,78] |

과거 노란run-1과Road7은 완전 일치하고,회색run-0과는 알려진 한 픽셀 차이도 남는다. 직전 회색 실행43977840900과 비교하면Road2·Road4·Road6·Road7의 네 이미지가 다르다. 전체 source_image_equivalence=false와renderer_diagnostic_passed=false를 유지했다. 새 판정은`INCONCLUSIVE_PREPROCESSED_SHADER_CACHE_RECORDED`다. 수집기 보완 성공을 렌더링 결정론·공식 모델의 수리 성공으로 해석하지 않는다.

새 테스트15개·관련 CPU 회귀147개와actionlint가 통과했다. 단일 read-only 전체 변경 검토는Critical0/Important0/Minor1이며,독립101개 CPU 테스트도 통과했다. Important 수정·재검토는 필요 없었다. 실행 소스 canonical push43984035709/PR43984316066의 네 작업과양쪽 원본 단위 로그2,030개·7개 건너뜀을 확인한 뒤 진단을 시작했다. 실행 뒤 코드·테스트·워크플로와 원래 고정 소스는 변경하지 않았다. 디스크0·고정/tmp·공유 메모리 매핑 등 이전 로컬 전체 스위트 제약은 그대로여서 반복하지 않았고,전체 검증에는 정확한 hosted CI를 사용했다.

보류Minor1개는`preprocess_cache`가파일 끝의 역슬래시를 거부하지 않는 경우다. Panda의EOF 처리와 기대 문자열이 달라질 수 있지만 현재 고정12소스/관측6stage에는 해당 입력이 없고,실제 캐시의 엄격한 비교를 완화하지 않는다. 기존 오프라인tonemap의극단적 유한 입력overflow는 이번 세 작업 범위 밖으로 원래 함수를 보존했다.

산출물14285208580은16,498,410B,ZIP SHA`f1b752c7eb3a2262e16ff4a3de082654d89aeb038b1b38f5c1853503608ccd65`로 API에 대조했다. 안전한 경로·크기 제한 후 원본69파일의 크기·SHA·보관 위치를 색인했다. JSON/JSONL/스택·source/shader 텍스트42개는 Git에,RGB·geometry.npz·텍스처 바이트·일반 로그27개는 Actions/output에 보존했다. 파생 분석14파일도 해시 색인에 있다. 원본 체크아웃·6개 byte/mode pin·이전31개 디렉터리/3,846개 파일과 부모PR137·main의 보존을 확인한다.

남은 연구 과제는 회색·노란 분기의 실제 uniform·raster/depth·톤매핑 입력/출력 연결이다. 이번 세 작업의 정상 수집 검증과 원래 폐루프 모델 행렬의 통과 판정은 별개이며,원래 실패 증거는 유지한다.

근거: [수정의 실제 확인](evidence/sdk3-shader-cache-01/actual/repair-verification.json),[독립 검증](evidence/sdk3-shader-cache-01/actual/independent-observation.json),[캐시·owner 분석](evidence/sdk3-shader-cache-01/actual/shader-analysis.json),[원본 픽셀 비교](evidence/sdk3-shader-cache-01/actual/source-prefix-pixel-comparison.json),[원본 색인](evidence/sdk3-shader-cache-01/actual/retained-index.json),[파생 분석 색인](evidence/sdk3-shader-cache-01/actual/derived-analysis-index.json),[단일 검토](evidence/sdk3-shader-cache-01/wholebranch-review.md),[판단 장부](evidence/sdk3-shader-cache-01/ledger.md). 최종 문서HEAD의CI·초안PR138·부모PR137·main·원본 보존 영수증은`output/stage7-sdk3-shader-cache-01/final-closeout/verification.json`에 별도로 기록한다.
