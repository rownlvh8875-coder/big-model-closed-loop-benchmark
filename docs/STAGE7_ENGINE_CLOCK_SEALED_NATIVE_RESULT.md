# [확인 기록] MetaDrive × MD-V3 7단계 개발 결과

원본 MetaDrive 카메라 폐루프 **카메라 전용 canary**의 실행과 원본 바이트 검증 기록이다.
공식 MD-V3 모델 추론이나 전체 7단계 완료를 뜻하지 않는다.

- 실제 실행: https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43548412476
- 실행/워크플로/작업:43548412476 /417960609 /132305005643, push/attempt1/SUCCESS.
- 실행 소스: `4d0372201b29d993c7c74b77bc95f59fc146563e`, [Draft PR87](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/87).
- 단일 요청 HEAD: `6fef49ae763ba386a2677484f491f2a994712c98`,205개 소스 파일 폐쇄집합.
- 원본 아티팩트:14095151728,338,901,808바이트,
  SHA256 `ea391fa87f421f838b5424f6b32c34b19990c53c247a954bb55e2c726e44458b`.
- 봉인 이미지006: 기존 인증 이미지/에셋을 그대로 사용. CID
  `sha256:2b0854f1cf91e470994637f52f4e8c78c618ed00b1496a40bb05158290e01a37`.

원본964×604 Road/Wide6쌍 → 실제512×256 화면 → 파생I420를 원본 파일에서 독립 재구성했다.
공급자1개 생성·종료, RAM읽기12회, 원본 task step12회, Texture읽기24개,
시계 snapshot48개/시계 getter96회, 총 관측 getter144회가 연결됐다.
부모PID1/자식PID22, 자식exit0, process group소멸·회수 및 cleanup오류없음.
원본 PSSM/chase 경로와 카메라 해상도를 유지했다. I420는 실제 모델 graph feed가 아니다.

부모·자식이 각각 설치 파일1,670,492,280바이트와 Python prefix23,107,322바이트를 검증했다.
실행 전 중단 컨테이너의 코드/Python전체/executable TAR3개를 독립 재검증했다.
초기 환경과 OpenCV import후 환경을 모두 기록하고, 부모의 검증된 초기 환경에서 자식을 시작했다.
정적 매핑388개는 이미지 파일 목록과 일치했다. Mesa cache index1개는 실행 중 생성된
비실행 데이터로 분리했다. 생성 메모리의 바이너리 동일성·기원은 주장하지 않는다.

컨테이너 예산4GiB, OOM/oom_kill0. 전체 cgroup 최고 charge4GiB와 max재회수 이벤트1357을
관측했다. 부모/Xvfb/파일 캐시를 포함하는 비원자적 관측이며 자식RSS·모델 메모리가 아니다.
이전04의 exit137을 OOM으로 소급 확정하지 않는다.

실행 종료: 2026-11-14 11:53:10 KST. Native phase 63.729초,
원본 인증·load·전처리 포함 operation 196.503초.

원본 source push/PR CI4작업이 정확한 HEAD에서 성공했고, 로컬 전체1108시험/기존skip7이
통과했다. 시계 상대 패턴12개 모두[0,1,1,1]였지만 GPU완료·프레임 신선도·계측 중립성의
증거는 아니다. cold cache와 파일 해싱 비용을 포함하므로 성능 중립 비교도 아니다.

실패01–05의 원본·요청·브랜치는 보존했다.05는6쌍 바이트 검증에 성공했어도 전체 프로토콜
실패로 남긴다.06만 별도의 새 소스로 검증했다. 기존 엄격 반복성0/4 FAIL,
확대시험NOT_RUN, 기하·광학·full-S 미검증, Stage7 INCOMPLETE는 유지한다.
이번 native 실행의 공식 모델·ORT 호출0회. 기본 CI의 생성 SMALL 그래프 시험은 별도다.
Cloud/registry 게시와 main병합은 수행하지 않았다.

상세 원본 메타데이터와 root검증은 `docs/evidence/engine-clock-sealed-native-06/`에 있다.
원본PNG/I420/대형TAR·ZIP은 Git에 넣지 않고 인증된 Actions아티팩트 및 로컬 output에 보존한다.
검토 보류사항·판단·비용은 continuation ledger와 V6_SOURCE_REVIEW 기록에 모두 남긴다.
다음은 이 결과를 근거로 **별도의 새로운 ABBA 프로토콜·예산·canary/C-A요청**을 설계하는
단계다. 현재06요청/미사용옛4case를 재실행할 수 없고, 미래 C/A호스트 일치나 모델실행을
자동으로 허용하지 않는다.

독립 root검증에 이어, 새 맥락의 원본 검토도 ACCEPT했다. 원본ZIP94개항목을 재검증하고
새 API로 실행·아티팩트 식별자를 확인했다. 보류된 판단11개와 그 비용은
`fresh-raw-review.md`에 전부 기록했다.
