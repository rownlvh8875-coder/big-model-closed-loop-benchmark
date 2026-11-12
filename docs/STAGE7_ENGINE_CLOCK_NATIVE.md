# Stage7 registered engine-clock camera evidence

기존 관측기(PR39)와 소비된 실험을 보존한 새 source70 프로토콜이다. 동일한 Texture/RAM 관측과 raw 보존을 양쪽에 적용하고, 시계 관측만 OFF/ON으로 바꾼다. OFF는 원래 비계측 renderer를 뜻하지 않는다.

## Source and gates

Base dc71e3617c70e544bd09c53378adaabed660b245; branch diagnostic/engine-clock-boundaries; stacked Draft PR40, base design/engine-clock-boundaries. Canary C=30dcc5b4075dd2cfaf25b3e8d90e324386a278af. Source70 compact sorted-JSON SHA256 6f8dcc2fc4aa7b1896a74d43ea4e030f89729b4b7851825cd0bbd444c6acab04. Mutable request/acceptance excluded and Git-bound separately. Existing67 producer/helper files and43 workflows unchanged.

독립 소스 검토가 canary 요청에 의존하는 테스트를 발견했다. canary 실행 전에 테스트 하나의 파일에서 fixture를 격리하고 두 요청 모드의 실제 워크플로 CPU 명령을 검증했다. 최초 로컬 전체644개/78.215초/선택 의존성7skip 기록은9bb9ebb의 기록이며, 테스트 수정 후의 양쪽82개 검증 및 실제CI 결과와 구분한다. 실행 코드/워크플로/초기 요청은 수정하지 않았다. 수정 재검토는30dcc5b에서 통과했다.

## Canary

Run43249493437/workflow416199727/job131291074475, push/attempt1, SUCCESS. Artifact13957438550(stage7-engine-clock-canary),ZIP14608013B, SHA256 e36df3c500c6a0f82a2a91f426d505ceb922f2cb47bd4a95e0d575a8455908c1,33members/15827111uncompressedB. 원본 ZIP은 한 번만 내려받아 추출했고 API digest/size와 모든 추출 바이트가 일치했다. Root pure validation 통과, 독립 raw 검토도 ACCEPTED_CANARY로 승인했다. 검토 JSON SHA256 3becdc31974dfdb237d1bfe0997d84d69fa26b1ce14f19dd3b9793284dbc1857. Root receipt SHA256 9ddd964ff049117e3e50cd998a83340d40bffd8b8e6ce8fddffdc6c16c9f911b.

실제 부모3229/launcher3305/native3317, phase32.321771705초. Provider1개 생성·종료, 고정6쌍/12RAM/12original task step/24Texture sequence readings/48clock snapshots/96clock getter invocations. Texture 각 reading은 accessor2회다. Clock counts/times는 비원자적 로컬 메타데이터이며 GPU frame ID가 아니다. 원본 raw12장→실제 lens canvas12장, 파생I420 6개를 CPU에서 정확히 재계산했다. 새로운 graph feed는 없다.

Runtime: Ubuntu24/ImageVersion20261111.370.1/Python3.11.18/NumPy2.4.6/OpenCVheadless5.0.0.93(cv2 5.0.0)/Panda1.10.13/MetaDrive0.4.3; installed/importedORT absent. 이전 역사적 실험의 이미지20261101.360.1과 다르므로 과거와의 binary equality는 주장하지 않는다. ABBA는 이 canary와 전체 runtime identity가 같아야 한다.

## Interpretation and limits

시계 경계는 common Texture/RAM/hash wrapper를 포함한다. startup 및 엔진 내부 기존 clock reads는 observer 집계에서 제외한다. Signed count 변화와 유한 time 값은 그대로 기록하며 +1/단조성/동일 epoch를 합격 기준으로 삼지 않는다. GPU completion/freshness, callback order, cache hit, observer neutrality, binary equality와 유일 원인은 입증하지 못한다. Native harness의 공식 모델·ORT·추가GPU읽기0, 기본CI의 생성SMALL ONNX는 별도다.

Strict scientific FAIL; expanded-not-run; geometry/physical optics/production ISP/full-S 미검증; Stage7 INCOMPLETE. 원래 renderer strict0/4와 기존 geometry2/4/candidate1/4, image62PASS/66inconclusive, full-S 미완료 상태를 바꾸지 않는다. Main 공식 호출0, Cloud 설정 변경·게시0, main merge0, Draft 유지. 실패/unused allowance의 재사용 및 기존 실험 재실행은 하지 않는다.

## Registered direct-child ABBA

이 커밋은 승인된 canary C의 직접 자식이며 producer70/runtime을 고정한다. 요청과 별도 승인 파일에 실제 run/artifact/size/digest 및 root/fresh 승인 값을 기록했다. 다음 한 번의 ABBA는 clockOFF0/ON0/ON1/OFF1, 각6쌍, common TextureON이다. 활성화 시점에는 ABBA actual run/artifact가 아직 없으며 성공을 주장하지 않는다. 실제 API·부모·변경경로·source70·runtime·canary 원본 ZIP/raw gate를 통과해야 provider를 생성한다. Root의 원본 ZIP 추출은 artifact당 한 번이며, ABBA runner는 실행 전 승인된 canary archive를 별도로 인증·검증한다.

Canary 기본CI push43249493559/PR43249507794의 네 작업 SUCCESS. Push unit131291074511:644tests/38.672s/7skip, SMALL131291075042:1test/0.084s. 최초 base-only push43243457833의 두 기본CI 작업도 성공했으며 새 native workflow가 없었다.
