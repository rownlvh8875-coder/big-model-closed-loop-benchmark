# MetaDrive × MD-V3 7단계 — 유지 호스트 캠페인01 결과

새 C 실행은 **실행 API 상태 확인에서 종료**됐다. C 승인·A 승인 요청·ABBA
4개 케이스·6개 비교는 모두 성립하지 않았다. 모델·ORT 호출0이며 기존 엄격
판정0/4 FAIL, Stage7 INCOMPLETE를 유지한다.

## 출처와 검증

- 소스 `5ab516cb4b52b40b589b97257604fc02487de1cd`,
  [Draft PR92](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/92).
  이전 생산 소스223개 바이트 보존, 새 폐쇄 소스235개.
- 집중16시험·전체1145시험 PASS/7skip/103.435초. 독립 소스 검토
  Critical0/Important0/Minor1; 부모 UUID 교차 확인 누락을 RED→GREEN 한 번으로
  수정했다. 재검토는 요청하지 않았다.
  [검토와 범위·비용 판정](evidence/ENGINE_CLOCK_HELD_ABBA_SOURCE_REVIEW.md).
- 정확한 소스 push43562901223/PR43562905120, 각 synthetic-unit 및
  onnx-interface-test SUCCESS/attempt1/artifacts0.
- 새 C `01ca6198d90f3624546b3a28c43507007b6d2354`는 소스 직계 자식이며
  C 요청 파일 하나만 추가했다. 요청SHA256
  `9694a844bb089bc36ebf21da7091345eb71f4dc559ff8b96648091338f693d1e`.
  [등록](evidence/engine-clock-held-abba-01/registration/registration.json).
- 유일한 [실행43563102068](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43563102068),
  workflow418051491/attempt1 FAILURE. native-host132350924448와
  canary-attestor132350924625가 모두 소스 인증 단계에서 실패했다.

## 원본이 보여 준 실패 경계

두 작업의 HTTP200 `live-run.json`이 각각 `queued`를 기록했다. 코드는
`validate_live`에서 `in_progress`를 요구하므로 다음 외부 출처 검증 전에
거부됐다. C 제어기1.188167454초, 검증 작업1.174286242초이며 종료 시각은
2026-11-14 KST14:46:09.471918와14:46:09.214647이다. 작업 실행 사실과
API 상태 사이의 불일치는 관찰됐지만, 정확한 GitHub 내부·프록시·캐시 원인은
증명되지 않았다.

보존된 원본 API로 순수 검증 함수를 다시 실행하면 같은 거부가 재현된다.
메모리 속 복사본의 상태 한 필드만 `in_progress`로 바꾸면 그 함수는 통과한다.
이는 원인 경계를 분리한 **CPU 가정 시험**이며 실제 상태 관찰이나 승인이 아니다.

| 원본 아티팩트 | ID | ZIP 바이트 | SHA256 |
| --- | --- | ---: | --- |
| C 실패 원본 | 14101256672 | 33625 | `150d6a822afdcfb946f76f6ffcd565685b0fc341340f019f7e73b2dd039c5b5a` |
| 검증 작업 진단 | 14101346363 | 33218 | `911651cc50e64316a52d7c93886c05573c1fe1eaa896f199b5d7cc6f2aac88ee` |

각 ZIP의 안전한 고유 멤버5개·CRC·크기·SHA, 선택된 모든 원본 바이트,
외부 실행·작업·workflow·유일성·아티팩트 API, C 추가 내용과235개 소스 고정,
정확한 소스 CI를 root가 대조했다.
[원본별 manifest와 HTTP 기록](evidence/engine-clock-held-abba-01/terminal-failure/),
[root 판정](evidence/engine-clock-held-abba-01/terminal-failure/root-acceptance.json).

소스 실행 순서에 근거한 image load/container/native start/provider/getter는0이다.
이는 OS·물리 호스트 증명이 아니다. 최초 실패 기록의 일반 provider 범위[0,4]는
수정하지 않았다. 실제 hostlease·이미지 인증·Docker·네이티브 위상 기록은 없고,
C 승인과 최종 attestation도 없다. A 단계는 건너뛰었고 A 요청은 발급하지 않았다.
독립 원본 검토는 이 종료 실패의 진위와 진단을 판단하며 C 성공을 승인하지 않는다.

## 보존과 다음 경계

이 캠페인은 소모됐으며 재실행·남은 케이스·예산 재사용은 없다. 소스·요청·원본·
이전16비활성 제안과 과거 실패/unknown을 보존했다. main 병합, Cloud 환경 게시,
레지스트리 게시, 공식 대형 모델 실행은 하지 않았다.

다음 소스 변경은 **성공 응답의 초기 queued 상태를 제한 시간 안에서 관찰하고,
실제 in_progress를 확인한 뒤 기존 검증을 통과시키는 별도 프로토콜**이다.
기존 queued를 승인 상태로 취급하지 않는다. HTTP 오류·실패/취소·시간 초과는 즉시
거부하고 모든 관찰을 보존해야 한다. 관찰된 queued→in_progress/지속 queued/
실패/지연 응답 시험, 새 소스 검토·정확한 CI·별도 요청이 필요하다. 이번 소스나
요청을 고쳐 다시 실행하지 않았다. 같은 호스트에서의 C/ABBA 실현 가능성과
실제 카메라 차이는 여전히 검증되지 않았다.
