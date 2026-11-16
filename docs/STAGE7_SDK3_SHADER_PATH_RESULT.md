# SDK3 회색 Road7·shader 캐시 6개 관측, PSSM 보조 조회 부분 실패

2026-11-17 KST. **승인된 렌더러1개가430.266초에7자세·14이미지 캡처를 마쳤고,장면·skybox·톤매핑 shader3개/6stage의 CPU 캐시 문자열과 알려진 입력16개를 수집했다.** 목표 Road7은 과거 회색 분기와 전체 이미지가 같으며 `(596,494)=[167,163,158]`이다. Road2·Road6의 각 한 픽셀 차이와 PSSM 보조 행렬 조회 오류를 보존해 `INCONCLUSIVE_CACHED_SHADER_PATH_RECORDED`로 판정했다. 기존 공식 모델 행렬은3/4PASS·전체FAIL,수리 미입증·Stage7 미완료다.

[실제 실행43977840900](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43977840900)은 workflow420708931/attempt1이다. 검토·수정 소스`2b788afa5b95eab0da2e77f5f363077bb107f77f`에 요청만 추가한 활성화`6dd19484a6df0df5be122b941ba097208be488d5`를 실행했다. 사용자가 새 브랜치 푸시·Draft PR·CI 후 단일 진단을 명시적으로 승인한 뒤 진행했다. 기존600초 자식/630초 컨테이너/20분 job·2CPU/10GiB·private IPC·읽기 전용 루트·network none·uid65534·512MiB tmpfs와 고정 이미지/SDK/core/BaseCamera를 유지했다. 공식 모델0개·ONNX 추론0회이며,추가 렌더러 재실행·환경/레지스트리 게시·main 병합은 없다.

| 실제 기록 | 결과 |
|---|---|
| WORLD_READY | 저널 시작 후103.304초 |
| 캡처7쌍 | 각45.346~47.108초,원본14이미지 검증 |
| CPU 기하·재질 | 2메시·1,004삼각형·585정점,선택2삼각형·UV stage 표본15개,완료 |
| shader 관측 | 원래Road7 CPU 읽기 후·카메라 복원 전,406.068~406.073초 |
| shader 파일 | 고정 소스12개68,278B와 캐시6개11,767B,총80,045B |
| shader 관측 경과 | 0.004445초;20초 예산 초과가 아닌 API 오류로 부분 실패 |
| 경계·스택 | 저널121행,30초 주기 Python 스택14개 |
| 종료·정리 | native/Xvfb/컨테이너0/0/0,timeout/OOM없음,provider.close·관찰 래퍼 복원·소유 컨테이너 제거true |
| 메모리·태스크 | 최고5,820,911,616B,원래14task ticks 유지,ORT 미로딩 |

Road7 전체 SHA는`3d7ced2bf6e8c448d5f99695c03221599150c1c93f44e2abb28105041c67054f`로 과거run-0의 회색 이미지와 같다. 과거 두 trial의 첫7자세28개 원본과 비교한 공통 첫6자세의 변경은 다음 두 픽셀뿐이다. Wide는7개 모두 일치하고 Road4는 이번에 과거 원본과 완전 일치했다.

| 이미지·좌표(좌상단 원점·0기준) | 과거 두 trial RGB | 이번 RGB |
|---|---|---|
| Road2 `(401,393)` | [135,144,82] | [179,176,171] |
| Road6 `(556,468)` | [168,163,157] | [138,143,77] |

과거 노란run-1과는 알려진 Road7 한 픽셀 차이도 남는다. 직전 PR136과 비교하면 Road2·Road4·Road6·Road7의 네 이미지가 다르다. 따라서 이번에 회색 분기가 나왔다는 사실을 전체 원본 재현·결정론·수리 성공으로 승격하지 않는다. `source_image_equivalence=false`, `renderer_diagnostic_passed=false`다.

선택된 보도벽 후보는 삼각형606,중심 거리8.420816,소스`[1,0,40,40,39,4]`,경로`render/world_np/1C/1C_sidewalk/polygon_node`다. 과거 노란 PR136과 이번 회색 실행에서 보관된1,004개 세계 삼각형·소스ID,선택 정점/UV/normal,Material,텍스처 행렬·CPU sampler 수치와 텍스처 metadata/원본 SHA는 일치했다. 광선 barycentric·보간 UV는 완전 바이트 동일하지 않지만 최대 차이7.105e-15로 기존 CPU 허용값1e-9abs/1e-12rel 안에 있다. 이미지 SHA 기준은 완전 일치를 유지했다. 두 실행의 텍스처 바이트도 다시 해시 검증했다. 이 비교는 동적 포인터·UUID 경로·과거 미수집 shader 캐시·실제 uniform/raster/depth/조명 실행을 비교하지 않으며,고유 원인을 증명하지 않는다.

실제 캐시 shader3개는GLSL(language2),캐시 error flag는 모두false였다. 보도벽의 캐시 define에는 MAX_LIGHTS8·USE_EMISSION_MAP·ENABLE_SKINNING이 있고 USE_NORMAL_MAP·ENABLE_FOG·USE_OCCLUSION_MAP·USE_330 정의는 없었다. 실제pipeline 객체 플래그도 이 재구성과 일치했다. 이는 CPU 캐시의 조건이며 실제 실행된 GPU program의 증명은 아니다. 톤매핑의tex 입력 포인터/metadata는 원래Road의scene_tex와 같았고,capture용copy_texture와는 달랐다. scene_tex CPU metadata는964×604·4components·component_width4·component_type2·format21,exposure 입력 벡터는`[1,0,0,0]`이었다. HDR 픽셀 값과 실제 GL attachment는 읽지 않았다.

각 메시의 알려진 PSSM 이름8개를 기록했다. PSSMShadowAtlas는2048×1024·1component의PSSMShadowMap 텍스처, border_bias는`[0.0579999983311,0,0,0]` 벡터였다. pssm_mvps·pssm_nearfar·use_pssm·fog·split_count·light_direction은 numeric-array 형식으로 공개 추출을 하지 않고 unavailable로 유지했다. 입력 이름 전체의 일반 열거 또는 hardware uniform 값 확인으로 주장하지 않는다.

PSSM 소유 rig의 보조 배열을 추가 조회할 때 `AttributeError: 'panda3d.core.UnalignedLMatrix4f' object has no attribute 'getCell'`가 발생했다. 오류 전에6개 캐시·16개 알려진 입력·톤매핑 결합은 저장됐으며,부분 수집 검증이 이를 정상적으로 수용했다. `shader_complete=false`와원본 오류를 유지했다. 고정 헤더에서UnalignedLMatrix4는getCell이 없고LMatrix4에는 해당 비정렬 행렬을 받는 변환 생성자가 있음을 확인했다. 이 오류는 목표RGB의 원래 읽기 이후 발생했으며,회색/노란 분기 전환의 원인으로 단정하지 않는다. 승인된 단일 실행을 추가로 반복하거나 실행 소스를 소급 수정하지 않았다.

별도로 정확 바이트 비교의 불일치를 조사했다. 원래 수신 검증은MetaDrive loader의 출력과Panda 캐시를 바로 비교해 보도벽/skybox의4stage가 불일치하고톤매핑2stage만 일치했다. Panda1.10.13의`Shader::r_preprocess_source`·`do_load_source`·`do_read_source`는주석·행 끝 공백을 제거하고 마지막LF를 정리한다. 보관된6stage에한정해 이 고정 로직을 CPU로 재현한 결과 **모든 캐시의 길이·SHA가 완전히 일치했다.** 이 여섯 입력에는 block comment·continuation·include/pragma/extension이 없음을 확인했고,코드 토큰을 바꾼 대조는 일치하지 않았다. 일반GLSL 전처리기 구현이나 GPU compilation 증명이 아니며,기존manifest·수신 판정·원본 바이트는 바꾸지 않았다. 따라서 원래`shader_variants_matched=false`도 그대로 보존한다.

| 실제 캐시 | 바이트 수 | 전처리 재현 |
|---|---:|---|
| 보도벽 vertex / fragment | 1,987 / 7,996 | 각각 전체SHA 일치 |
| skybox vertex / fragment | 210 / 428 | 각각 전체SHA 일치 |
| 톤매핑 vertex / fragment | 466 / 680 | 각각 전체SHA 일치 |

정확한 실행 소스 canonical push43976973566/PR43977092390의 네 작업이 모두 성공했고,양쪽 원본 단위 로그는 각각2,015개·7개 건너뜀이다. 따라서 이전 준비 기록의 로컬 환경 실패를 hosted전체 스위트에서는 재현하지 않았다. 단일 전체 변경 검토의 Important3개는 한 번의RED→GREEN 단계로 수정했고,새16개·관련132개 CPU 회귀와actionlint가 통과했다. 이후 실행 코드·테스트·워크플로를 변경하지 않았다. 보류Minor1개는 오프라인tonemap의극단적 유한 입력overflow이며,native 수신 검증에서는 해당 함수를 호출하지 않는다.

산출물14281857204는16,497,997B,ZIP SHA`72bdaec41c638dc8506f3df27fe784c16dc9e13ea05789b5dc4c9cc61e49abff`로 API와 대조했다. 안전한 해제·크기 제한 후 원본69파일의 크기·SHA·보관 위치를 색인했다. JSON/JSONL/스택·shader/source 텍스트42개는 Git에,RGB·geometry.npz·텍스처 바이트·일반 로그27개는 Actions/output에 보존했다. 오프라인 분석 코드와 고정Panda 참고 소스도 해시 색인으로 보관했다. 원본6개 byte/mode pin과이전31개 디렉터리/3,846개 파일,원본 체크아웃과부모PR136·main을 보존했다.

남은 구현 보완은PSSM 비정렬 행렬의 명시적 변환과Panda 캐시 전처리를 반영한 검증이다. 실제 픽셀 원인 구분에는실제 실행 uniform·raster/depth·톤매핑 입력/출력의 연결 증거가 필요하다. 이번 기록만으로 GPU 소유권·고유 원인·수리·원래 폐루프 행렬 통과를 주장하지 않는다.

근거: [독립 검증](evidence/sdk3-shader-path-01/actual/independent-observation.json),[shader 분석](evidence/sdk3-shader-path-01/actual/shader-analysis.json),[전처리의6개SHA 재현](evidence/sdk3-shader-path-01/actual/panda-cache-reproduction.json),[과거 원본 비교](evidence/sdk3-shader-path-01/actual/source-prefix-pixel-comparison.json),[노란 분기와CPU 입력 비교](evidence/sdk3-shader-path-01/actual/prior-material-comparison.json),[원본 색인](evidence/sdk3-shader-path-01/actual/retained-index.json),[파생 분석 색인](evidence/sdk3-shader-path-01/actual/derived-analysis-index.json),[검토](evidence/sdk3-shader-path-01/wholebranch-review.md),[판단 장부](evidence/sdk3-shader-path-01/ledger.md). 최종 문서HEAD의CI·초안PR137·부모PR136·main·원본 보존 영수증은`output/stage7-sdk3-shader-path-01/final-closeout/verification.json`에 별도 기록한다.
