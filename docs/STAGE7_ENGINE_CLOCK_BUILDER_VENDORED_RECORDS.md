# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과 — builder04 vendored RECORD

[실제03 증거 PR64](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/64)의 namespace는 통과했고 bootstrap 설치 파일 검증에서 중단됐다. 원래 wheel의 setuptools vendored RECORD16개가 바이트 그대로 설치됐지만 구 검증기의 blanket RECORD 제외와 top-level-only 생성 metadata 허용이 충돌했다.03은 소진되며 개별 stage receipt를 나중에 만들어 채우지 않는다.

새 owned verifier는 실제 top-level distribution의 RECORD만 설치 재작성 대상으로 취급한다. nested/vendor RECORD와 모든 다른 원본 payload는 SHA256 일치를 요구한다. 누락/변조/미등록 metadata/unsafe·duplicate ZIP member/잘못된 pyc source·magic을 거부한다. 기존 nofollow bounded snapshot과 build 명령·source/tool/wheel 검증·namespace 관측/판정을 유지한다. 새로운 명시적 verifier 인자로 연결하며 기존 모듈을 monkeypatch하지 않는다.

새 parent는 고정 stage prefix/status/returncode/bytecount/SHA256 schema로 failure steps를 보존한다. package stdout/stderr 원문이나 환경은 공개하지 않는다. driver/core/envelope가 그대로 복원되도록 하고 source/provider 성공을 임의 추정하지 않는다. owned entry/tool verifier가 바뀌는 recipe/rootplan은 새 요청에 별도 pin으로 등록하며 기존51inputs109285137B를 유지한다.

별도 v4 workflow/request builder-20261113-04: run1/attempt1/build1/probes<=2/profileload<=1/candidate userns assertion<=1.39개03 closure 및 새 composed source를 닫아 등록하고 실제 sourceCI 후 request-only soleparent activation 하나를 허용한다. 같은 새 job에서 fresh backend와 빈 별도256MiB tmpfs/두FD/정해진 네 root retention을 검증한다. 구51workflow/source/test/policy/request/raw는 바꾸지 않는다. 모델/ORT/GL/과학 native/main merge/Cloud 게시 없이 wheel을 준비·검증하며 full-lock/image/native/Stage7 완료는 별도다.

독립 검토e042ccf C0/I1/M0. BR-I1은 마지막 최대64KiB read로 capture counts가 한도를 넘고 cleanup/transport가 상태를 바꿀 때 새failuredecoder가 기록을 버리는 문제다. 단일 TDD수정88f80e6에서 non-EXITED만 한 read overshoot를 수용하고 정상EXITED 한도와 더 큰 값 거부를 유지했다. RED13tests/errors8→집중13 PASS4.436초·전체905 PASS/7skip86.008초. 독립 검토자는 수정 전 집중12 PASS4.294초를 확인했으며 재검토는 하지 않았다. [판단과 비용](evidence/STAGE7_ENGINE_CLOCK_BUILDER_VENDORED_RECORDS_REVIEW.json)에 모두 기록했다. 실제03 보존 ZIP/inventory/pyc header만 사용한 새checker replay는 원본1036파일/설치1894파일 PASS이며 다운로드 코드 실행·설치tree 추출이 아니다.

실제04: source398a291/activationa9fee1c, workflow417318675/[run43436389710](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43436389710)/job131922493264, unique1/attempt1, 2026-11-13 22:45:08–22:46:49 Asia/Seoul terminalFAIL. sourceCIpush43435939247/PR43436021699 네 작업PASS/artifacts0. 요청04소진·재실행금지, retention/uploadSUCCESS.

namespace와 root12726nodes351886111B/51inputs109285137B 검증이 통과했다. 새 tool checker는 통과했고 실제 VENV/ENSUREPIP/TOOLS rc0, BUILD rc1의 고정 stage receipts를 보존했다. outer1716B/core1103B 및 BUILD의 공개 source-failure72B를 정확히 복원해 모든 stdout capture SHA256/크기와 대조했다. SMOKE와 wheel은 없다.

원인은 owned helper 결합 오류다. 기존 build.py의 `_driver()`는 옆 driver.py를 읽어 source_snapshot/_check_source_map/pip_wheel_args/validate_snapshots를 기대한다. 새 진입 driver.py는 namespace·stage adapter이며 이 API가 없고, 진짜 구 driver는 legacy-driver.py로 보존돼 있다. 첫 `driver.pip_wheel_args()` 평가에서 pip_main 호출 전 실패하므로 source unpack/build에 진입하지 않는다. 실제 보존 root의 세 owned 파일hash와 AST API 부재를 확인했고 빈 tmp/out 및 source-before/after 부재는 보조 근거다. 기존 모듈을 그대로 둔 채 새 owned build helper에서 legacy-driver.py를 명시적으로 읽도록 별도05를 준비한다. 진입 파일 분리 시 이 참조를 놓친 오류를 인정하고 배포 경로 fixture로 보완한다.

원본artifact14043643056 ZIP245892528B/SHA9b7fdf9bb3d890b7f91ad8123f02857ea9d5326ce5d8adac1a18f8fc8e0b6d8c; 전체14121항목(12923file/1030dir/168symlink), regular472466795B. TAR491816960B/SHAcf67a5f7e18043545825f68eaeb0026905856b8e14c90ac13602865c74be65b2, 단일gzip EOF/CRC/zero-tail7168B/allinventory/root/input/sourceclosure/soleparent/request-only/API/unique를 독립 확인했다. [결과](evidence/STAGE7_ENGINE_CLOCK_BUILDER_VENDORED_RECORDS_RESULT.json)와 output/stage7-builder-record-evidence/builder-20261113-04/ 원본을 보존한다. 모델/ORT/GL/과학native/main merge/Cloud 게시 및 full-lock/image/Stage7 완료는 없다.
