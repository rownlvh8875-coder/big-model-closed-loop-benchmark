# MetaDrive × MD-V3 — 실제 C→ABBA 카메라 검증 완료

**캠페인03의 C와 ABBA 네 케이스, 전체 workflow가 SUCCESS이며 root+독립 원본
검토가 승인했다.** 24쌍 재구성·여섯 비교·성공 controller·정상 종료·명시적 파일
예산 검사가 모두 통과했다. 이는 네이티브 카메라 실험의 승인이다. 공식 대형 모델
실행이나 기존 엄격 판정은 별도이며 **strict0/4 FAIL, Stage7 INCOMPLETE**를 유지한다.

## 수정과 출처

이전02는 네 케이스 종료 후170파일이 기존129상한에 걸려 실패했다. 원본·소스·
기존 검사는 보존했다. 새03프로토콜은 위상 예산을 C129파일/256항목,
A256파일/512항목으로 명시했다. 192MiB 바이트 한도, 케이스별129검사,
호스트·이미지·관찰·픽셀·프로세스·허용량 조건은 유지했다. 최종 phaseJSON 저장
전의 stat스냅샷과 최종 ZIP 바이트 수는 구분해 검증한다.

- 소스 `60f6d7fbadf9c0cdbeb087f6452d7b07ea77abd5`,
  [Draft PR96](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/96).
  이전248생산파일 불변/261고정파일. 집중31·전체1199시험 PASS/7skip/102.717초.
  독립 소스 검토 Critical0/Important0/새 Minor0;
  [계승 HV-M1·HV-M2와 모든 범위·비용 판정](evidence/ENGINE_CLOCK_HELD_ABBA_V3_SOURCE_REVIEW.md).
- 정확한 source push43570517907/jobs132373682916+132373683126,
  PR43570522632/jobs132373695864+132373696076 모두 SUCCESS/attempt1/artifacts0.
- C `fd57f5efab90c7b410b699250a47603f364aace5`: source직계 자식/C요청 하나 추가,
  SHA `03936937f07a814d07e16eaea138df3119826c0deb675c03df2da4f73ce21dc5`.
- 실제 root+fresh C승인 후 A제어 `498647977af799ba0b765440d44985565eee7d13`:
  C직계 자식/별도 A요청 하나 추가,
  SHA `13dd5753f6b5a9b593be615bc68a52151276d182c3df2ed200fa228584d97d85`.
  실제 생산 checkout/HEAD는 C이며 A는 제어 데이터다.
- 유일한 [실행43571004531](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43571004531),
  workflow418107188/attempt1 SUCCESS. host132375169212와 별도
  canary-attestor132375169062 모두 SUCCESS. A푸시로 추가 네이티브 실행은 없었다.

## 실제 검증 결과

C승인 때 host/workflow는 in_progress였다. 종료된 C와 성공한 C단계·업로드,
별도 완료SUCCESS attestor 및 실제 root+fresh 원본 승인이 먼저 확인됐고,
그 뒤 별도 A제어를 추가했다. 현재 전체 workflow의 terminalSUCCESS를 C승인
시점으로 소급하지 않는다. 실제 같은 호스트의 전체 C/A동일성도 통과했다:
Intel Xeon6973P-C/118CPUflags/affinity[0,1,2,3]/MemTotal16759304192,
kernel/image006/engine/env/resources. identity
`6563f6af12ed20dafbe5ff7a67e960f0878bb0ac40c1731b4d45ad1c92a03f2c`,
lease `a1e223ef7eccec368516008070beb7810f54d8ea736e4418b40bb57aa23ad229`.

| 검증 | C | A: OFF0/ON0/ON1/OFF1 |
| --- | ---: | ---: |
| provider 생성/종료 | 1/1 | 4/4 |
| 재구성 raw964×604→canvas512×256→derivedI420 쌍 | 6 | 24 |
| RAM읽기/task호출 | 12/12 | 48/48 |
| Texture관찰/clock스냅샷/getter | 24/48/144 | 96/96/384 |
| 위상 시간 | 77.652263339초 | 266.989968845초 |
| 위상 작업 시간 | 169.895932282초 | 339.817303953초 |
| 파일/항목 | 49/56 | 170/198 |
| 한도 파일/항목 | 129/256 | 256/512 |

A제어 대기는384.694295262초, 전체724.511598962초,
종료2026-11-14 KST16:40:10.592409이다. 최종 출력65449553B는192MiB 이내이며
저장 전 스냅샷65446270B와 다르다. 모든 자식 exit0/reaped/groupgone/cleanup[],
성공 controller존재/phaseSHA일치/containerexit0/OOMfalse를 확인했다. A의 다섯
설치 검사 각각44232항목/1670492280B, prefix/env/permit/선택된 로드 파일,
3copiedTAR,10메모리 기록도 검증됐다. cgroup최대4GiB/OOM0는 합산 메모리이며
RSS가 아니다. 과거04OOM을 증명하지 않는다.

## 서술적 비교

| 비교 | raw/canvas 변경 픽셀 합계 | 최초 차이 |
| --- | ---: | --- |
| OFF0–ON0 | 35/8559936 | road2, I420은3 |
| OFF0–ON1 | 35/8559936 | road2, I420은3 |
| OFF0–OFF1 | 35/8559936 | road2, I420은3 |
| ON0–ON1 | 0/8559936 | 없음 |
| ON0–OFF1 | 0/8559936 | 없음 |
| ON1–OFF1 | 0/8559936 | 없음 |

차이는 raw6픽셀·canvas29픽셀의 합계다. ON0·ON1·마지막 OFF1은 raw/canvas/I420
모두 동일했다. ON/ON 상대 clock패턴·절대 count는 같고 절대time은 달랐다.
Texture marker패턴·값도 모두 같았다. OFF에서는 clock을 읽지 않아 비교가 null이다.
이 결과는 시계 관찰 ON/OFF의 인과 효과나 GPU신선도·observer중립성 증명이 아니다.
02의65픽셀 진단과는 서로 다른 호스트·프로토콜의 별도 실험이므로 합치지 않는다.

## 원본·권위·한계

| 원본 | ID | ZIP 바이트 | SHA256 |
| --- | --- | ---: | --- |
| C | 14104039420 | 339057032 | `1484ea8be64763afa10b6cce1053f09790390ce3580adf1bfa90525b279606e7` |
| 완료 Cattestation | 14103949539 | 1276 | `d75027ec0cc2cce57593d69aa18955d0893cd752c8986cd3cae48e0c7e001b87` |
| A | 14103669668 | 405545950 | `cf1a03b478e15bc9c0533ef4bc2e8e644cb2a16df20ad3f6f341c409b6ea7505` |

[최종 권위](evidence/STAGE7_ENGINE_CLOCK_HELD_ABBA_03_RESULT.json),
[증거 인덱스](evidence/engine-clock-held-abba-03/proof-index.json),
[C 원본 검토](evidence/engine-clock-held-abba-03/canary/fresh-raw-review.md),
[A 원본 검토와 모든 범위·비용 판정](evidence/engine-clock-held-abba-03/abba/fresh-raw-review.md),
[ledger](STAGE7_ENGINE_CLOCK_HELD_ABBA_V3_LEDGER.md)에 원본별 manifest·작은 원본JSON·
API·CI·Git·root/fresh·픽셀 진단을 보존한다. 원본 ZIP·PNG·I420·TAR·cache는 output에
남기고 Git에는 복제하지 않았다. 최초 root보고의 freshflagfalse는 별도 진짜 fresh
승인 기록과 함께 불변으로 남겼다. 검토는 고정 알고리즘을 공유하므로 공통
validator 결함 가능성이 남으며, 실제 기계·생성 코드의 물리적 동일성을 증명하지 않는다.

03허용량은 총5provider/30쌍/528getters로 소모됐고 남은0이다. 이전02실패·129guard·
소모 요청·이전16비활성제안은 불변이며 재실행·main병합·Cloud/registry게시는 없었다.
API 숫자타입·동료 작업 구조 보강 HV-M1/HV-M2 두 건은 계승된 보류 사항이다.
공식 모델 graphfeed·기존 strictFAIL·geometry/optics/fullS 원인은 해결되지 않았다.
이 카메라 ABBA 승인을 공식 대형 모델 또는 과학적 성공 권위로 사용하지 않는다.
