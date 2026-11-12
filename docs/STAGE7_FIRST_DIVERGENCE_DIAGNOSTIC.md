[확인 기록] MetaDrive × MD-V3 7단계 개발 결과

카메라 관측 진단의 실제 CI 기록이다. 기존 source-a4의 12단계 MD-V3 반복성 FAIL은 계속 병합 차단 조건이다. PR33은 DRAFT이며 main 공식 모델 호출은0이다. 이 기록은 원본 렌더러의 반복성·물리 카메라 정합성·7단계 완료를 선언하지 않는다.

카메라 소스는 `70cf8adeeaf088097da18da50810230d04092bbb`이며, 첫 effective native canary 실행은 [43125348683](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43125348683), job130875887880이다. 같은 소스의 기본 CI push43125348715/PR43125358699도 성공했다. 세 실행 합계5jobs SUCCESS. 카메라 job의 CPU 진단66tests PASS; 공식 모델 gate/download/study steps는 SKIPPED였다.

앞선 소스 `6bf84c3264a847c413fdd265abda2925073bfe13`의 [43123979141](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43123979141)은 job-env의 지원되지 않는 runner.temp 참조로0jobs에서 실패했다. 네이티브/공식 모델 호출0이다. 새 소스는 경로 전달을 기존 요청 단계의 GITHUB_ENV로 옮겼으며, 실제 actionlint RED/GREEN, 경로에 공백을 둔 명령 전달 회귀 테스트,41modeltests/6workflowtests/9bash-n을 통과했다. 기존 실패 실행은 재실행하지 않았다.

아티팩트는 `13902402855` (`stage7-first-divergence-canary`), ZIP4,883,414bytes, SHA256 `eae449d6c439eafad6eaab91364a600465ca0f25cb8659efdcf346998539053f`이다.12members/5,280,540uncompressedbytes로 receipt.json과 dataset/만 포함한다. raw964×604/canvas512×256 PNG8개와 packedI4202개, manifest/receipt2개이다. 실제 PythonPID3230/processUUID5bb94b2e1de640efae518cbd72a368ee에서 네이티브 제공자1개를 사용했다.

선택된 카메라 쌍2개, 실제 pair capture5회/sensor read10회이며 제공자 시작 렌더링은 계수에서 제외한다. 같은 포즈 수렴은3/2attempts, 설정6/16/10이다. 첫 선택의 changed pixels Road/Wide0/0,maxdelta0; 두 번째0/9,maxdelta8이다. 공식 모델 호출/ORT세션0이다. 두 포즈는 원래 첫 차선 fraction.12,8m/s와 frozen straight step_ideal dt.05이며 full-S실행이 아니다.

Root는 GitHub repository/workflow/event/branch/head/run/attempt1/SUCCESS, 아티팩트 API 크기·digest와 실제 ZIP, 안전한 멤버,58개 소스의 actual Gitblob/current-file 해시를 확인했다. 보호 대상13개/기존 런타임43개와 기존 워크플로는 고정했다. 선택된 raw→실측intrinsics→실제canvas4/4,canvas→packedI4202/2가 정확히 일치한다. canary packed는 derived-only이며 actual graph feedSHA는null이다. ONNX일치율은 미실행으로 산출하지 않는다. 독립 raw/API/source 검토 상태는 CLEAR (run43125348683/artifact13902402855, source58/ZIP12/PNG8/warp4/I4202 independently checked)이다.

별도 CPU 재생에서 onboarding NumPy1.26.4/OpenCV4.11.0.86은 저장 canvas와17,324/12,343/17,726/12,436pixels가 달랐고 최대channeldelta3/3/4/3이었다. CI기록 NumPy2.4.6/OpenCV5.0.0.93만 설치한 격리 CPU환경에서는4/4warps와2/2I420가 정확히 일치했다. NumPy2.4.6을 고정한 OpenCV4.11/5.0 비교에서도 이 차이가 나타났고, OpenCV4.11 고정 후 NumPy만 바꾸면4RGB출력은 같았다. 세 환경의 warp audit/homography도 같았다. 저장canvas→I420는 세 환경 모두 일치했다. 새 렌더/모델/전처리 변경 없이 얻은 CPU version/build 민감도이며, 원래 같은 런타임 안에서 발생한 반복성 FAIL의 원인으로 귀속하지 않는다. CI전체 binary/system 동일성은 증명하지 않았다.

다음 모델 진단은 실제 독립 승인 후에만 요청/승인메타데이터/docs 단일 커밋으로 활성화한다. 그 커밋의 부모는 정확히 위 accepted canary source여야 하며 producer/test/workflow/runtime bytes는 같아야 한다. API/archive/source/runtime gate가 공식 가중치 다운로드보다 먼저 실행된다. 등록된 순서는 A0(original),B0(proxy),C0(retention),C1,B1,A1이며6freshPython/Xvfbchildren×4steps, 최대24MD-V3calls이다. child480s/study2400s,observerpayload256MiB/child,dataset1GiB,실패시중단/재시도없음.4step prefix에 차이가 없어도 기존12step FAIL을 PASS로 바꾸지 않는다.

원본0/4, corrected candidate12/12, geometry/physical optics/full-S의 기존 제한과7단계 미완료 상태는 유지한다. Cloud게시, main병합, renderer/converter/default변경, 실차/CAN/CD210/Carrot튜닝/모델순위는 수행하지 않는다.

독립 검토 JSON SHA256 `0d2216d8194e6a17d96f44dc71efc2ae45c33bdc8be794dac44cf857164fcd56`이며 재현 가능한 요약과 제한은 `.github/stage7-first-divergence-acceptance.json`에 보존했다. 모든 convergence 시도에는 hash/count/timing만 남았고 전체 픽셀은 선택된2쌍만 보존한다. 따라서 두 번째 수렴의9pixels/max8은 원래 receipt 값이며 이전 미보존canvas에서 독립 재계산할 수 없다.
