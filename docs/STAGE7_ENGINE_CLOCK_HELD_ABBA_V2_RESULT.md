# MetaDrive × MD-V3 7단계 — 유지 호스트 캠페인02

**C는 원본 검증을 통과했다. 동일 호스트에서 ABBA 네 자식도 모두 정상 종료했고
24쌍과 여섯 비교를 검증했다. 그러나 마지막 129파일 제한에서 위상이 거부되어
전체 workflow는 FAILURE다.** 비교는 거부된 위상의 진단이며 성공 데이터셋이나
시계 관찰의 인과 효과를 승인하지 않는다. 엄격 판정0/4 FAIL, Stage7 INCOMPLETE,
공식 모델·ORT 호출0을 유지한다.

## 출처와 실제 실행

- 소스 `bee8072aa01d570a546ea709aa01103f069cf07f`,
  [Draft PR94](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/94).
  기존235생산파일 보존/248고정파일. 집중23시험·전체1168시험 PASS/7skip/109.862초.
  독립 소스 검토 Critical0/Important0/Minor2;
  [HV-M1 숫자타입·HV-M2 동료작업 검사 한계와 모든 범위·비용 판정](evidence/ENGINE_CLOCK_HELD_ABBA_V2_SOURCE_REVIEW.md).
- 정확한 source push43565241838/jobs132357538461+132357538778 및
  PR43565247152/jobs132357554707+132357554963 모두 SUCCESS/attempt1/artifacts0.
- C `23d3dbc85202c307546876645941e513cb7e567b`: 소스 직계 자식/C요청 하나 추가,
  SHA256 `3f47ae72482dd70bf467b12a6dc5bfb57b27c8ae0a8866da544d57406960dfd7`.
- 실제 root+fresh C승인 후 A `5ea6152755f348609d6a29f5b8b6eecf6ee9bde4`:
  C의 직계 자식/별도 A요청 하나 추가,
  SHA256 `b3570e8615ba1d4ce50d658788cf3ef058745e903124d8af1ff54e8652b8d724`.
  **실제 생산 checkout/HEAD는 C, A는 제어 데이터**다. C요청과248소스는 불변이다.
- 유일한 [실행43565472170](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43565472170),
  workflow418069748/attempt1. native-host132358240513는 A에서 FAILURE,
  독립 canary-attestor132358240800은 SUCCESS. C단계/업로드는 SUCCESS.
  A푸시는 별도 네이티브 workflow를 시작하지 않았다.

## C 승인과 같은 호스트의 의미

C종료 KST15:19:06.245677, 위상96.538009882초/전체190.790958389초.
카메라 생성·종료1/1,6raw964×604→canvas512×256→derivedI420쌍,
12RAM/12task/24Texture/48clock/144getters; exit0/reaped/groupgone/cleanup[].
102원본멤버·CRC·248Git핀·설치44232항목 각1670492280B·prefix/env/permit/
typedidentity/3copiedTAR/메모리·종료 기록을 root와 새 검토자가 대조했다.
독립 검토는 matching NumPy2.4.6/OpenCV5.0.0으로6쌍을 재구성했다.

C승인 시 **전체 workflow/host는 in_progress**였으며 C의 종료 기록과 성공한
C단계·업로드, 별도 완료SUCCESS attestor, 실제 root+fresh 원본 승인이 권위다.
이를 전체 workflow완료로 바꾸지 않는다. C실제 run API는 첫 관찰부터
in_progress였다(queued0). 이번 실행에서 queued→active 전이를 관찰했다고
주장하지 않는다. 대기·오류·시간 제한은 CPU시험으로 검증했다.

A에서 동일성 검사는 필드 생략 없이 통과했다: AMD EPYC7763/fullCPUflags,
affinity[0,1,2,3], MemTotal16760344576, kernel/image006/engine/env/resources.
identity `04c458dde07f5b754b46a3b42f1c9de48f03c7658d3e37864fbbf3d190ae282c`,
lease `cc3865accf0467f8e37348768a9a63b99a9f3fdb360949e6a9907ed88b3e8b6e`.
서로 다른 임의 호스트의 CPU를 허용한 결과가 아니다. 물리적 호스트 증명은 아니다.

## A의 실패 경계와 검증 가능한 진단

A 종료 KST15:34:05.935596. 제어 대기472.084237119초,
위상333.038901628초/위상 작업422.59161578초/전체894.675852528초.
OFF0/ON0/ON1/OFF1 모두 provider생성·종료1/1,6쌍,exit0/reaped/groupgone,
cleanup[]였다. 합계4provider/24쌍/48RAM/48task/96Texture/96clock/384getters.
다섯 preflight 설치/prefix/env/permit/typedidentity,3TAR,10메모리 기록을 검증했다.
cgroup최대4GiB/OOM0는 합산 메모리이며 RSS가 아니다. 과거04OOM은 증명되지 않았다.

네 자식 검증과 여섯 비교 후 `texture_generation_markers._members`가 호출됐다.
기존 **129파일** 제한에 실제 output **170파일/65433113B**가 걸렸다.
192MiB 바이트 제한 안이며256 traversal 제한도 원인이 아니다. 원본 output을
CPU로 다시 검사해 같은 `ValueError: dataset byte/member cap`을 재현했다.
128케이스파일(4×32)에42개의 위상·입장 증거가 더해진 구성을 기존 제한이 수용하지
못했다. 전체1168시험과 소스 검토는 이 네이티브 집합 경계를 잡지 못했다.

원본 phase/result는 FAILED_OR_INCOMPLETE, container는 exit1/OOMfalse이며
성공 controller.json은 없다. 외부 `one-native-phase/IMAGE_DOCKER_REJECTED`는
이 종료의 wrapper 오류다. **실패·원본·129제한을 고치거나 성공으로 바꾸지 않았다.**
root+fresh는 종료 실패의 진위와 네 케이스 진단을 승인했다. 원래 일반 범위[0,4]는
보존했으며, 재구성한4개는 소스/데이터 기반 관찰이지 OS물리 증명이 아니다.

## 여섯 비교: 거부된 위상의 서술적 결과

| 비교 | raw/canvas/I420 | raw+canvas 변경 픽셀 합계 |
| --- | --- | ---: |
| OFF0–ON0 | 차이 있음, 최초 wide1 | 65/8559936 |
| OFF0–ON1 | 차이 있음, 최초 wide1 | 65/8559936 |
| OFF0–OFF1 | 차이 있음, 최초 wide1 | 65/8559936 |
| ON0–ON1 | 동일 | 0/8559936 |
| ON0–OFF1 | 동일 | 0/8559936 |
| ON1–OFF1 | 동일 | 0/8559936 |

차이는 와이드 원본6픽셀·캔버스59픽셀의 합계다. 로드 카메라는 동일했다.
ON/ON 상대clock패턴과 절대frame count는 같지만 절대time은 달랐다.
Texture marker값/동등패턴은 모두 같았다. OFF시 clock값을 읽지 않아 해당 비교는
null이다. 마지막 OFF가 두 ON과 같으므로 단순 ON/OFF 인과 결론은 성립하지 않는다.
GPU완료·신선도·observer중립성·geometry/optics/fullS는 여전히 증명되지 않았다.

## 원본·검토·다음 조건

| 아티팩트 | ID | ZIP 바이트 | SHA256 |
| --- | --- | ---: | --- |
| C | 14101349929 | 339040863 | `7c1f0342647a6e29d533464a67ef6afd46e7b74300c29f496a0bb61a5bf47f11` |
| 완료 Cattestation | 14101354880 | 1276 | `2ae498e10ae422781981dc15dacb5904bb620bb6891909fe32cabd3a35107f25` |
| A 실패 진단 | 14102811980 | 405384523 | `2270edb641dd8d7bec1c99498cb2e60def986dfa5612ac4780a88cd696d6a89e` |

[최종 권위](evidence/STAGE7_ENGINE_CLOCK_HELD_ABBA_02_RESULT.json),
[버전 관리 증거](evidence/engine-clock-held-abba-02/),
[C 원본 검토](evidence/engine-clock-held-abba-02/canary/fresh-raw-review.md),
[A 원본 검토와 모든 범위·비용 판정](evidence/engine-clock-held-abba-02/abba/fresh-raw-review.md),
[ledger](STAGE7_ENGINE_CLOCK_HELD_ABBA_V2_LEDGER.md)에 정확한 소스/CI/요청/API/
원본별 manifest·작은 원본JSON·root/fresh·픽셀 진단을 보존했다. 이미지/TAR/cache를
Git에 복제하지 않았다. 원본 ZIP과 전체 선택 데이터는 output에 그대로 남겼다.

캠페인 총5provider/30쌍/528getters를 소모했고 남은 허용량0이다. 재실행·남은
케이스 사용·main병합·Cloud/registry게시는 없었다. 기존 과거실패/16비활성제안/
strictFAIL은 불변이다. 다음은 **4케이스와 증거를 수용하는 명시적 위상 파일·순회
예산을 별도 소스/프로토콜에서 검증하는 수정**이다. 기존129guard와 소모 요청을
수정하지 않고170파일 재현시험/새 소스검토/정확한CI/별도요청이 필요하다.
