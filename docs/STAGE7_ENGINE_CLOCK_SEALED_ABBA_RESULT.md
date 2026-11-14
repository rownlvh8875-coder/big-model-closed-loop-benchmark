# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과

**새 카메라 canary C는 원본 검증과 독립 검토 모두 ACCEPT했다. ABBA A는 실제
CPU 모델·기능 목록이 달라 동일성 검사에서 거부됐으며,4개 케이스·6개 비교는
미실행이다. 전체7단계 완료나 공식 MD-V3 반복성 성공을 뜻하지 않는다.**

## A. GitHub 및 변경 범위

- 저장소: rownlvh8875-coder/big-model-closed-loop-benchmark.
- 실행 소스: `4f667825b2c4b913ed89328937bbccfd7139349f`,
  `fix/engine-clock-sealed-abba-timeout-v2`, [Draft PR90](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/90).
- 새C HEAD: `adcb489f39d812544155a976eca4895aed26f561`.
- 직접 자식A HEAD: `2981d89a17b2e1339be378db560960f6a4cc2729`.
  C→A변경은 요청JSON 하나뿐이며, 실제 실행 소스223개 파일은 동일하다.
- 결과 전용 브랜치: `evidence/engine-clock-sealed-abba-02`. 문서HEAD는 실행 소스가
  아니며 최신 전체SHA·결과PR·마지막 문서CI는 PR본문과 최종 응답에 기록한다.
- 핵심 구현: `scripts/engine_clock_sealed_abba_v2.py:21`의1800초 start예산,
  `scripts/engine_clock_sealed_abba_run_v2.py`의 실제 C/A동일성 gate,
  `scripts/engine_clock_sealed_abba_container_v2.py`의 인덱스별 실행/실패 기록.
  이전215개 소스와 소비된01요청·브랜치·원본은 변경하지 않았다.

## B. 실제 시험과 원본

| 항목 | 새C | ABBA A |
| --- | --- | --- |
| Actions | [43555898389](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43555898389) | [43556701512](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43556701512) |
| workflow/job |418007872/132328552158 |418007872/132331060583 |
| job/attempt |SUCCESS/1 |FAILURE/1 |
| 원본 artifact |14098196994 |14098023319 |
| ZIP바이트/항목 |338935214/98 |312967/35 |
| operation |179.382479144초 |56.174685970초 |
| 종료KST |2026-11-14 13:20:30.959542 |2026-11-14 13:27:58.060044 |
| 카메라 쌍/비교 |6쌍 재구성 일치 |4케이스·6비교 NOT_RUN |

C ZIP SHA256: `af9d1ce0ecadeae8777afc2e2cd3f1401089856ab20ae4c927ad7bb8e747da6b`.
A ZIP SHA256: `b343cf496497b4ea0407717b87907418b3645ebe972898611b33ac2ad738ce4b`.

C의 실제964×604 Road/Wide 원본6쌍→512×256실제 canvas→파생I420를 원본 바이트에서
독립 재구성했다.6/6변환과 hash/trace/pose연결이 일치했고, 재구성 불일치 위치는 없다.
이는 프로세스 간 RGB반복성이나 ONNX출력 일치율이 아니다. 공식 모델·ORT 호출0,
실제 graphfeed없음. 생성 SMALL그래프를 쓰는 기본CI는 별도다.

실제 C자식PID22/부모PID1, 공급자1개 생성·종료, exit0/회수/group소멸/cleanup오류없음.
RAM12/task12/Texture24(48getter)/clock snapshot48(96getter), 총 관측getter144회.
모든12개 상대 clock패턴[0,1,1,1]은 기술적 관측이며 GPU완료·프레임 신선도·중립성의
증거가 아니다. 원본PSSM/chase/카메라·task경로는 유지했다.

봉인 이미지006 CID `sha256:2b0854f1cf91e470994637f52f4e8c78c618ed00b1496a40bb05158290e01a37`,
기존 인증TAR/manifest를 사용했다. 부모·자식 각각 설치1670492280바이트와 prefix
23107322바이트, 실행 전 코드/전체Python/executable TAR3개를 확인했다. 초기·cv2후
환경, 실제 affinity/MemTotal, 타입별 host/identity기록, 선택된 매핑/모듈, FIFO허가와
자원 조건을 검증했다.4GiB cgroup최고 charge/OOM0/max이벤트1238은 비원자적 집계값이며
자식RSS나 모델 메모리가 아니다. 이전04의 OOM원인은 여전히 미확정이다.

A는 source흐름상 이미지 load/컨테이너/공급자 생성 전에 거부됐다. 원본에는 Docker
메타데이터 명령2개만 있고 phase/case/PNG/I420/복사TAR가 없다. 이는 인증된 소스 순서와
원본 기록에 근거한 결론이며 OS포렌식 증명이 아니다. 원본 generic provider범위[0,4]와
unknown표현은 고치지 않았다. A의 RGB/I420/ONNX일치율·최초 픽셀차이·실험군/대조군
차이는 데이터가 없어 **미측정**이다.

로컬 전체1129시험/기존skip7 PASS94.807초. 정확한 소스push43555577340와
PR43555631622 각각 synthetic-unit/onnx-interface-test 성공, attempt1/artifacts0.
마지막 증거문서HEAD의 CI는 실행 소스CI와 구분해 결과PR본문에 기록한다.

## C. 확인된 원인과 제한

| 독립적인 실제 차이 | C | A |
| --- | --- | --- |
| CPU모델 |AMD EPYC9V45 96-Core |AMD EPYC9V74 80-Core |
| CPU기능 목록 수 |119 |102 |

kernel/엔진/이미지/환경/자원 및 나머지 identity필드는 일치했다. affinity[0,1,2,3]와
MemTotal16760344576바이트도 같다. 파생된 내부·외부 hash2개 차이까지 독립 재계산해
원본 타입별 비교와 일치했다. 이 차이가 실제 A승인 거부 조건임은 확인됐다.
기존 RGB·모델 비반복성의 픽셀 원인이라고 확정하지 않는다.

이전01C는2100초 start인자가 frozen process.capture의1800초 상한을 넘어 Popen전
거부됐다. 실제원본49항목/정지컨테이너TAR3개/Statecreated와 실제 adapter CPU재현으로
확인했다. 실패01을 보존하고 새02에서 start상한만1800으로 낮췄다. 기존 프로세스
상한을 올리거나 실패 요청을 재실행하지 않았다. 독립 source검토의 Important3개
(원본ZIP이름/내부동일성차이/초기실패phase)도 한 번의 RED→GREEN수정으로 검증했다.

각 source scope의 새 검토, Important수정, 보류7Minor, 모든 declined판단·잘못됐을 때의
비용은 [첫 source검토](evidence/STAGE7_ENGINE_CLOCK_SEALED_ABBA_V1_SOURCE_REVIEW.md),
[상한 호환 source검토](evidence/STAGE7_ENGINE_CLOCK_SEALED_ABBA_V2_SOURCE_REVIEW.md),
[C원본검토](evidence/engine-clock-sealed-abba-02/canary/fresh-raw-review.md),
[A원본검토](evidence/engine-clock-sealed-abba-02/abba/fresh-raw-review.md)와 두 ledger에
전부 남겼다. 두 원본 검토는 root검증기의 쓰기없는 AST재사용과 별도 독립 API/hash검사를
병행했으므로, 처음부터 별도로 구현한 검증 알고리즘이라고 주장하지 않는다.

## D. 최종 게이트

C원본 root+fresh ACCEPT. A원본 root+fresh는 **실패의 진위**를 ACCEPT했고, A자체는
FAILED로 남는다. ABBA데이터·clock효과·중립성·GPU동기화 성공을 주장하지 않는다.
원래 공식 MD-V3엄격 반복성0/4 FAIL, 확대시험NOT_RUN, 기하·광학·full-S미검증,
Stage7 INCOMPLETE. 공식 모델·native ORT0, main미병합, Cloud/registry미게시.
기존실패/소비요청/옛미실행case예산은 모두 그대로다.

## E. 다음 단계와 보존 위치

우선 같은 측정 호스트를 유지하면서 C완료·원본 검토 후 A를 이어갈 수 있는 새 실행
생명주기를 설계·시험·검토해야 한다. 기존 동일성 조건이나 완료/출처 조건을 약화해
통과시키지 않는다. 새 소스·프로토콜·예산·요청이 필요하며 현재01/02나 옛4case를
재사용할 수 없다. 이후 새 C의 root+fresh수락과 실제 동일성 통과가 있을 때에만 새
4case/6comparison을 실행하고, 실제 RGB/I420/clock차이를 원본에서 집계한다.

기계 판독 최종 상태와93개 권위파일의 hash/크기는
[최종 JSON](evidence/STAGE7_ENGINE_CLOCK_SEALED_ABBA_02_RESULT.json)에 있다.
원본ZIP/PNG/I420/대형TAR는 Git에 넣지 않고 Actions원본과 로컬
`output/stage7-sealed-abba-root/`에 보존했다. 종료된 요청을 다시 실행하는 명령은 없다.
