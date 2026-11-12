# Stage7 registered engine-clock camera evidence

**Canary는 원본 검토를 통과했고, ABBA는 runner의 ImageVersion 차이로 provider 실행 전 중단됐다.** 네 case 및 여섯 비교는 미실행이다. 실패 phase의 집계는 모두 null이며 성공한 ABBA 또는 renderer 원인 규명으로 표시하지 않는다. 재시도·남은 allowance 재사용·runtime gate 완화는 하지 않았다.

## Identity and actual runs

Repository rownlvh8875-coder/big-model-closed-loop-benchmark; branch diagnostic/engine-clock-boundaries; [Draft PR40](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/pull/40), base design/engine-clock-boundaries/PR39. Published base dc71e3617c70e544bd09c53378adaabed660b245. 기존 producer/helper67개, protected13/baseline43, 기존43 workflows 및 소비된 요청/승인/실험 기록은 보존했다. 새 producer70 compact sorted-JSON SHA256은 `6f8dcc2fc4aa7b1896a74d43ea4e030f89729b4b7851825cd0bbd444c6acab04`이다. 새 request/acceptance는 별도로 Git-bound이며 producer closure에서 제외한다.

| Phase | Actual source | Run / job | Result | Artifact / ZIP bytes |
| --- | --- | --- | --- | --- |
| Canary | 30dcc5b4075dd2cfaf25b3e8d90e324386a278af | [43249493437](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43249493437) /131291074475 | SUCCESS, root+fresh ACCEPTED_CANARY |13957438550 /14608013 |
| ABBA | ab0ef77ab318a0683bdddb896e1e9db6b79e79e6 | [43251145868](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/43251145868) /131296956425 | FAILURE, acceptance stage |13958034562 /5421 |

Both use workflow416199727, push/attempt1. ABBA source is the exactly single-parent direct child of accepted canary source; changed paths are only new request/acceptance/docs, all70 producer bytes frozen. Source commits and later evidence/review-only HEADs are distinct; read the current full HEAD with `git rev-parse HEAD` and the actual final CI in the Draft PR.

Canary artifact `stage7-engine-clock-canary`: SHA256 `e36df3c500c6a0f82a2a91f426d505ceb922f2cb47bd4a95e0d575a8455908c1`,33members/15827111uncompressedB. ABBA artifact `stage7-engine-clock-abba`: SHA256 `0492e32c50f6549c635a150e76637b5e498ad84be3f2e364257b6ba4396dc656`,1member `phase.json`/12123uncompressedB. Root downloaded and extracted each original once, verified API size/digest and every original/extracted byte. ABBA runner separately authenticated and validated accepted canary archive before its final runtime comparison.

## Measured canary

Parent3229/launcher3305/native3317; phase32.321771705s; one provider constructed and closed, exit0, reaped/group gone, cleanup errors empty. Fixed pose0 four pairs and pose1 two pairs; six accepted pairs,12 RAM reads,12 original TaskManager steps,24 Texture sequence readings,48 clock snapshots and96 clock getter invocations. Texture each reading uses two accessor calls:48 Texture+96 clock=144 observer getter invocations actually recorded, excluding startup and existing internal engine reads. Planned whole campaign528 was not completed.

Raw12 images→recorded actual lens canvases12 images and six derived I420 arrays rederive exactly. Each wrapper row binds original RAM hash, capture ordinal/camera, marker row, clock row and saved PNG. These are derived-only arrays, with no new actual graph feed. The trace has72 events, matching actual child main-thread and owner_thread140374616009600; five clock-wrapped attributes restored. All12 clock relative count vectors were measured `[0,1,1,1]`, first10→11; all Texture pre/post values were equal12..23. These values were measured, not required advancement/monotonicity/freshness gates.

Runtime common version fields: Ubuntu24,Python3.11.18,NumPy2.4.6,OpenCVheadless5.0.0.93(cv2 5.0.0),Panda1.10.13,MetaDrive0.4.3; installed/importedORT absent. Canary ImageVersion20261111.370.1. Logical retention estimate32384608B<32MiB (not RSS); retained payload28039104B; disk reservation38171904B<40MiB; actual payload15742189B; case JSON63523B; trace19123B<64KiB; log1519B; dataset15827111B<192MiB. Fresh empty external Mesa cache populated50files/1671101B, bounded64MiB/1024files. Launch+wait30.806911422s/case31.079335332s meet270/300s,phase below1320s. Inventory does not prove individual cache hits or binary equality.

## Authentic ABBA rejection

Actual phase: `FAILED_OR_INCOMPLETE`, `failure_stage=acceptance`, error `ValueError: accepted raw dataset context/source/runtime mismatch`, elapsed5.471793702s. Accepted canary context and source70 match; the only unequal runtime field is ImageVersion: canary `20261111.370.1`, ABBA `20261101.360.1`. The strict gate rejects the pair as designed before the case loop. No `_case` launch is recorded and no child ledger/raw/clock OFF/ON comparison is present. Source-bound control flow and authenticated phase/job logs support pre-loop rejection; this is not independent OS tracing or a zero-allocation claim from missing files.

All seven failed aggregates (`providers`, `accepted_pairs`, `observed_reads`, `marker_reads`, `task_step_calls`, `clock_snapshots`, `clock_getter_invocations`) remain null. `launches=[]`, `comparisons=[]`; strict successful-dataset validation rejects this incomplete phase. Four cases and all six cross-case comparisons are not run. Do not sum null aggregates as zero, label ABBA accepted-descriptive, claim matched OFF/ON inputs or manufacture a new first difference. Root receipt and independent review accept only the authentic failure evidence.

This establishes the proximate reason for admission rejection. It does not establish an installed-binary difference, a renderer fault or GPU pixel cause. The two hosted runners reported different ImageVersion values despite the same ubuntu-24.04 label; no unique explanation for rollout/scheduling is inferred. Existing successful canary remains valid within its own recorded runtime.

## Verification and records

Source review found an Important mutable-request test dependency before any native push. Initial full local644tests/78.215s/7optional skips apply to9bb9ebb. Test-only fix at30dcc5b isolates scenario fixtures and executes the unchanged real workflow CPU command under both valid modes:82canary/9.667s and82ABBA/9.349s, zero skips/real API/provider calls, on-disk request unchanged. Original failure/harness logs retained; no full local suite repeated. Independent scoped review passed at30dcc5b. Actionlint and bash checks passed; provided native bootstrap and old workflows unchanged.

Actual sourceC basic CI push43249493559/PR43249507794:four successful jobs. Push unit131291074511 ran644tests/38.672s/7skip; generated SMALL ONNX131291075042 ran1test/0.084s. ActivationA basic CI push43251145850/PR43251160849:four jobs successful, separately from failed diagnostic. Initial remote base-only push43243457833:two successful basic jobs, no new workflow there. Final docs-only push/basic CI and exact final HEAD are recorded in Draft PR40; the diagnostic failure is retained and is not made green.

Machine/human receipts are under `docs/evidence/STAGE7_ENGINE_CLOCK_{CANARY,CANARY_REVIEW,ABBA,ABBA_REVIEW,RUNTIME_REJECTION,AUDIT}`. Source review and scoped fix review are retained separately. Audit records exact review identities, hashes, rulings and costs. Controller workspace, raw originals, extracts, logs, failures and all earlier study histories are retained. No worktree/local native/Panda engine/Xvfb/official weight download/model inference/Cloud configuration change/publication/main merge was performed.

## Interpretation and continuation

Common Texture/RAM/raw retention is ON in both planned arms; OFF means clock getter OFF, not the original uninstrumented renderer. Clock windows include common Texture/RAM/hash wrapper work. Snapshot count/time pairs are non-atomic local metadata, not GPU frame identity, completion/freshness, callback order or a shared cross-process epoch. Observer neutrality, cache hits, installed binary equality and unique cause remain unproved. New harness official/ORT/extra GPU reads0; baseline generated SMALL graph is separate.

No new cross-process first difference is available. Historical official-model step2 raw Road3/Wide1 pixels→13I420 values/checksum+32 and raw4/plan/post-state divergence at2,pre-state at3 remain historical; new canary capture ordinals are not those model steps. See [prior diagnostic](STAGE7_POST_TRANSPORT_DIAGNOSTIC.md), [pixel forensics](STAGE7_FIRST_DIVERGENCE_PIXEL_FORENSICS.md) and [state sequences](STAGE7_TEXTURE_STATE_SEQUENCES.md). This study neither reruns nor explains them.

Next is a separate provider-free runtime-contract design branch: assess an immutable execution image/binary identity and how it can be authenticated before any separately registered experiment. Preserve the present same-runtime rejection; do not edit/retry consumed source/request or reuse the four unexecuted cases. Any future native study requires its own new protocol/source/canary/acceptance/budgets and must distinguish runtime labels from actual binary identity.

Strict scientific FAIL; expanded-not-run; original renderer strict0/4, historical corrected candidate12/12 and24fresh-process accepted results are not original PASS/default promotion. Geometry original2/4/candidate1/4, image62PASS/66inconclusive; physical optics/production ISP/full-S remain unvalidated. Stage7 INCOMPLETE, main official calls0, Cloud unpublished, Draft unmerged. No real-car/CAN/CD210/Carrot/ranking claim.
