# Task3 first input-gate final review

Reviewed base: `d54d43757eabc60d4f3f5b3d7e51f665bcc9f23e`

Reviewed head: `2e89ffe95b1382823248dd7595f254e1d271afaf`

Scope: fresh Senior Code Reviewer/builder evidence check of the entire seven-file documentation-only range, using the requesting-code-review template. Checkout, index and HEAD were read-only; only these review outputs were written. No suites, network, native operations, downloads, Docker, API calls, subagents or worktrees were used.

### Strengths

- `docs/evidence/engine-clock-image-inputs/metadrive-0.4.3.METADATA:24` and `docs/evidence/engine-clock-image-inputs/opencv-package-guidance.txt:6` support the shared-cv2 packaging-policy stop. The spec at line13 explicitly avoids claiming pip unsatisfiability or historical pixel causality.
- `docs/superpowers/specs/2026-11-12-engine-clock-image-inputs-design.md:9` distinguishes fetched, locally measured sidecar bytes from advertised, undownloaded wheel payload hashes. The retained source binding checks out.
- `docs/superpowers/plans/2026-11-12-engine-clock-runtime-contract.md:74` records an incomplete blocked gate and retains the unchecked first step at line80. The absent recipe/lock/adapter is truthful and follows the stop rule.
- `docs/superpowers/specs/2026-11-12-engine-clock-image-inputs-design.md:35` makes derivative provenance, payload preservation, RECORD/signature/license and hostile-input review future obligations. Line39 explicitly denies runtime/scientific assurance from a derivative alone. This is concrete enough as a next-policy proposal, not a transform specification or authorization.
- Frozen preservation maps match both reviewed commits and the working tree; the new audit preserves null/false/zero boundaries.

### Issues

#### Critical (Must Fix)

None.

#### Important (Should Fix)

None.

#### Minor (Nice to Have)

None.

### Evidence checked

- All seven BASE..HEAD changed documentation/evidence files read; no product code/test changes in diff; working tree initially clean and HEAD exact.
- Eight saved response bodies rehashed: byte counts and SHA256 all equal audit/receipts; sum 236879 bytes; all eight saved HTTP statuses 200, URLs and timestamps consistent.
- Python directory lists 3.11.18 archives; saved release JSON name/version fields confirm NumPy2.4.6, OpenCV headless5.0.0.93, Panda3D1.10.13, MetaDrive0.4.3 and OpenCV full5.0.0.93.
- MetaDrive simple JSON exact wheel entry binds filename and files.pythonhosted.org URL to advertised wheel SHA c6f8a42baac939a0af53a8e1cd9d48ec2bf0051917e7c19083e156a6506493d9; release JSON agrees. Core metadata SHA is 4fb69fa54bb0e8118315aecdc482597af69798e17e47df3c57fbca50d4e7bcf6.
- Public METADATA equals saved sidecar byte-for-byte: 11315 bytes, expected SHA; Name/Version and all Requires-Dist lines agree with audit, including unconditional opencv-python at line24.
- Public OpenCV excerpt is verbatim in saved headless release info.description; source body hash agrees. Public excerpt 619 bytes SHA513e79a66aac8f690e03573e287255ec4e39d45142447f9c14783b5c0e2a5394 matches audit.
- Four preservation snapshot hashes and counts match audit; all mapped 70 producer,44 workflow,8 registry,5 Task1/2 tool/test/proposal file hashes match working tree and Git objects at BOTH base and reviewed head.
- Public audit equals private input report JSON; all16 preparation refs null; readiness/execution false, allowance0, task3_complete false; planned Dockerfile,lock,adapter,test and preparation workflow example absent.
- Parent plan first Task3 checkbox remains unchecked and explicitly stops unsupported resolution; five progress rulings agree with audit and name costs; brief/report/review package read.

Reviewed changed files:

- `docs/STAGE7_CONTINUATION.md`
- `docs/STAGE7_ENGINE_CLOCK_IMAGE_INPUTS.md`
- `docs/evidence/STAGE7_ENGINE_CLOCK_IMAGE_INPUTS_AUDIT.json`
- `docs/evidence/engine-clock-image-inputs/metadrive-0.4.3.METADATA`
- `docs/evidence/engine-clock-image-inputs/opencv-package-guidance.txt`
- `docs/superpowers/plans/2026-11-12-engine-clock-runtime-contract.md`
- `docs/superpowers/specs/2026-11-12-engine-clock-image-inputs-design.md`

### Recommendations

Retain the current stop. The future derivative design must enumerate permitted metadata exceptions (including RECORD/signature handling) and prove runtime/asset byte preservation; this review does not approve that future policy or imply it closes the full graph. Root should bind any final review/CI receipts to the final documentation HEAD without marking Task3 complete.

### Declined to judge

- Independent live HTTP/TLS provenance, request execution counts, retries and time bounds: reviewed saved receipts and bodies only; no network replay or transport-code audit was authorized.
- Wheel payload authenticity, embedded METADATA equality and signatures: only the advertised wheel hash and fetched PEP658 sidecar were checked; wheel payload was not downloaded.
- Complete transitive dependency solvability and target-platform availability: release existence and this one packaging blocker do not resolve the full Python/OS/base/asset graph.
- Actual overlapping installation, import selection and shared-file overwrites: no installation or imports were performed; support-policy reasoning is sufficient for this stop gate.
- Derivative transform implementation, exact allowed member changes, distribution identity, RECORD/signature correctness, license compliance and hostile-archive defenses: proposed future design obligations, not implemented behavior.
- Derivative runtime compatibility and upstream endorsement: payload preservation alone cannot establish either, and the proposal explicitly does not claim them.
- Task1 identity comparison, synthetic-hash admission boundaries, legacy/partial rejection and kernel/CPU/engine mismatch behavior: frozen prior implementation; checked preservation rather than replaying its review or tests.
- Task2 closed inventory detection, modes, symlink escape/cycle handling, deadlines, Docker-managed /etc exclusions and legitimate aliases: frozen prior implementation; checked preservation, not runtime behavior.
- Future adapter API provenance, forged environment claims, token/proxy/Config.Env redaction and large archive streaming: adapter is absent and outside this stopped input gate.
- Actual lock/recipe, installed filesystem, Docker configuration/diffIDs, launch authentication, mounts, driver/GL selection and image compatibility: no preparation evidence exists in this increment.
- Download/disk/hash/load feasibility and timing neutrality: no actual image or package preparation occurred; future caps are not measurements.
- Native/model/weights/ORT/provider/engine/Xvfb/GPU/clock work and scientific pixel causality, determinism, geometry/optics/full-S validity: excluded from this documentation-only review and remain unvalidated.
- Complete raw archive/extraction/controller history replay or exhaustive filesystem forensic proof of zero execution: no raw artifact replay authorized; frozen mapped files and tracked diff checked only.
- Final branch CI, post-review corrections, Draft PR publication, merge and Cloud publication: root owns Git/CI; this review binds only the stated HEAD and grants no preparation or merge authority.

### Assessment

**Ready to merge?** No merge authorization; technically acceptable for the bounded Draft/unmerged checkpoint.

Technically acceptable as a bounded BLOCKED_INPUT_COMPATIBILITY documentation/evidence checkpoint. No Critical, Important or Minor findings. Task3 remains incomplete; this is not an approval to resolve via a derivative, prepare an image, run native work or merge. Final Draft/unmerged status and final-HEAD CI remain root responsibilities.
