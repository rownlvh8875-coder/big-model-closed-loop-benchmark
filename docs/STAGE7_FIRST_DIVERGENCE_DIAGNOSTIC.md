[확인 기록] MetaDrive × MD-V3 7단계 개발 결과

등록된 모델 진단은 **실패·불완전**으로 종료했다. 실제 source `081a4c61a68e5cb00a89f1c9998e66c657a16657`, [run43128201225](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43128201225), job130885546863에서 API/raw/source/runtime gate와 공식 가중치 다운로드는 성공했으나 첫 A0 launcher의 권한 전달 중 `BrokenPipeError`가 발생했다. 기본 CI4jobs SUCCESS/diagnostic1job FAIL이다. 여섯 자식·24calls가 완료됐다고 해석하지 않는다.

실패 artifact13904515781은 ZIP5,057bytes, SHA256 `49b1b6994fc5fdd125245df71ea23cf337d63f1f231cd1501ce11535b43906c0`, study.json1개뿐이다. parentPID2877/launcherPID·PGID3004/cleanup후exit−15이며 childPID·UUID는null이다. model_calls는null, 하한0/상한4; 실제 native provider도 미확인0..1이다. trial/report/process.log/RGB/state/feed/output이 없어 모델 일치율·최초 불일치·대조군 차이를 산출할 수 없다. exit−15는 cleanup 기록이며 최초 자식 실패 이유를 증명하지 않는다. Root와 독립 검토는 API/ZIP/58source의 진본성과 실패 증거를 확인했으며 성공 study validator는 이 자료를 거부한다. 독립 검토163checks/JSON SHA256 `c20090d596c7022b55c84e5e56d6c1901c23b8b63e4bb6ac9d356a468ce821c5`.

소스의 log sink가 permit write 뒤에 생성되어 초기 자식 stderr를 보존하지 못했다. CI에 기록된 Ubuntu xvfb2:21.1.22-1ubuntu1.3의 공식 배포 패키지를 SHA검증해 읽으면 wrapper가FD3을 덮고 자식 실행 시 닫는다. 같은 FD계약을 CPU shell/Python으로 재현하면 FD3은 BrokenPipeError/자식EBADF, FD10은 전달 성공이었다. 실제 CI의 pipeFD와 원래 stderr는 없어 FD3충돌을 유일한 실제 원인이나 모델0회로 단정하지 않는다. 패키지·scriptSHA와 재현값, 실패 검토 요약은 [기계 기록](evidence/STAGE7_FIRST_DIVERGENCE_FAILED_STUDY.json)에 보존했다. 새 renderer/model/weight 실행 없이 얻은 결과다.

이 study는 재실행·연장하지 않는다. 다음은 분리된 브랜치에서 권한 pipeFD 보호와 조기 bounded log 보존을 CPU로 수정하고, 모델·MetaDrive·가중치 없는 CI transport probe를 검증하는 작업이다. 이후 새 모델 진단에는 변경된 producer의 새 source/canary/protocol 등록이 필요하며 이번 승인이나 실패 자료를 성공으로 재사용하지 않는다.

후속 IPC 수정의 actual zero-model 검증은 [별도 기록](STAGE7_FIRST_DIVERGENCE_TRANSPORT.md)에 보존했다. Ubuntu24의 정상/초기종료 두 경로만 승인했으며, 아래 Ubuntu26 실패의 model_calls null0..4/providers0..1 및 유일 원인 미확인 상태를 바꾸지 않는다.

카메라 관측 진단의 실제 CI 기록이다. 기존 source-a4의 12단계 MD-V3 반복성 FAIL은 계속 병합 차단 조건이다. PR33은 DRAFT이며 main 공식 모델 호출은0이다. 이 기록은 원본 렌더러의 반복성·물리 카메라 정합성·7단계 완료를 선언하지 않는다.

카메라 소스는 `70cf8adeeaf088097da18da50810230d04092bbb`이며, 첫 effective native canary 실행은 [43125348683](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43125348683), job130875887880이다. 같은 소스의 기본 CI push43125348715/PR43125358699도 성공했다. 세 실행 합계5jobs SUCCESS. 카메라 job의 CPU 진단66tests PASS; 공식 모델 gate/download/study steps는 SKIPPED였다.

앞선 소스 `6bf84c3264a847c413fdd265abda2925073bfe13`의 [43123979141](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43123979141)은 job-env의 지원되지 않는 runner.temp 참조로0jobs에서 실패했다. 네이티브/공식 모델 호출0이다. 새 소스는 경로 전달을 기존 요청 단계의 GITHUB_ENV로 옮겼으며, 실제 actionlint RED/GREEN, 경로에 공백을 둔 명령 전달 회귀 테스트,41modeltests/6workflowtests/9bash-n을 통과했다. 기존 실패 실행은 재실행하지 않았다.

아티팩트는 `13902402855` (`stage7-first-divergence-canary`), ZIP4,883,414bytes, SHA256 `eae449d6c439eafad6eaab91364a600465ca0f25cb8659efdcf346998539053f`이다.12members/5,280,540uncompressedbytes로 receipt.json과 dataset/만 포함한다. raw964×604/canvas512×256 PNG8개와 packedI4202개, manifest/receipt2개이다. 실제 PythonPID3230/processUUID5bb94b2e1de640efae518cbd72a368ee에서 네이티브 제공자1개를 사용했다.

선택된 카메라 쌍2개, 실제 pair capture5회/sensor read10회이며 제공자 시작 렌더링은 계수에서 제외한다. 같은 포즈 수렴은3/2attempts, 설정6/16/10이다. 첫 선택의 changed pixels Road/Wide0/0,maxdelta0; 두 번째0/9,maxdelta8이다. 공식 모델 호출/ORT세션0이다. 두 포즈는 원래 첫 차선 fraction.12,8m/s와 frozen straight step_ideal dt.05이며 full-S실행이 아니다.

Root는 GitHub repository/workflow/event/branch/head/run/attempt1/SUCCESS, 아티팩트 API 크기·digest와 실제 ZIP, 안전한 멤버,58개 소스의 actual Gitblob/current-file 해시를 확인했다. 보호 대상13개/기존 런타임43개와 기존 워크플로는 고정했다. 선택된 raw→실측intrinsics→실제canvas4/4,canvas→packedI4202/2가 정확히 일치한다. canary packed는 derived-only이며 actual graph feedSHA는null이다. ONNX일치율은 미실행으로 산출하지 않는다. 독립 raw/API/source 검토 상태는 CLEAR (run43125348683/artifact13902402855, source58/ZIP12/PNG8/warp4/I4202 independently checked)이다.

별도 CPU 재생에서 onboarding NumPy1.26.4/OpenCV4.11.0.86은 저장 canvas와17,324/12,343/17,726/12,436pixels가 달랐고 최대channeldelta3/3/4/3이었다. CI기록 NumPy2.4.6/OpenCV5.0.0.93만 설치한 격리 CPU환경에서는4/4warps와2/2I420가 정확히 일치했다. NumPy2.4.6을 고정한 OpenCV4.11/5.0 비교에서도 이 차이가 나타났고, OpenCV4.11 고정 후 NumPy만 바꾸면4RGB출력은 같았다. 세 환경의 warp audit/homography도 같았다. 저장canvas→I420는 세 환경 모두 일치했다. 새 렌더/모델/전처리 변경 없이 얻은 CPU version/build 민감도이며, 원래 같은 런타임 안에서 발생한 반복성 FAIL의 원인으로 귀속하지 않는다. CI전체 binary/system 동일성은 증명하지 않았다.

아래 모델 진단은 실제 독립 승인 후 요청/승인메타데이터/docs 단일 커밋081a4c6으로 활성화했으나 위의 첫 launcher 단계에서 실패했다. 등록 당시 조건은 다음과 같았다. 그 커밋의 부모는 정확히 위 accepted canary source여야 하며 producer/test/workflow/runtime bytes는 같아야 한다. API/archive/source/runtime gate가 공식 가중치 다운로드보다 먼저 실행된다. 등록된 순서는 A0(original),B0(proxy),C0(retention),C1,B1,A1이며6freshPython/Xvfbchildren×4steps, 최대24MD-V3calls이다. child480s/study2400s,observerpayload256MiB/child,dataset1GiB,실패시중단/재시도없음.4step prefix에 차이가 없어도 기존12step FAIL을 PASS로 바꾸지 않는다.

원본0/4, corrected candidate12/12, geometry/physical optics/full-S의 기존 제한과7단계 미완료 상태는 유지한다. Cloud게시, main병합, renderer/converter/default변경, 실차/CAN/CD210/Carrot튜닝/모델순위는 수행하지 않는다.

독립 검토 JSON SHA256 `0d2216d8194e6a17d96f44dc71efc2ae45c33bdc8be794dac44cf857164fcd56`이며 재현 가능한 요약과 제한은 `.github/stage7-first-divergence-acceptance.json`에 보존했다. 모든 convergence 시도에는 hash/count/timing만 남았고 전체 픽셀은 선택된2쌍만 보존한다. 따라서 두 번째 수렴의9pixels/max8은 원래 receipt 값이며 이전 미보존canvas에서 독립 재계산할 수 없다.
