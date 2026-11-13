# Python wheel-input closure implementation plan

> Apply executing-plans inline/TDD; preserve checkout/raw/workspaces.

Spec docs/superpowers/specs/2026-11-14-engine-clock-python-wheel-closure-design.md; base264da597c32f0189e4f9ed1e7f27d71dffd8006d.

1. Pure fixture wheel reader: safe paths/types/duplicates/conflicts/CRC/RECORD/top-level-vs-vendored record, metadata/name/version/tags/Python/caps, startup-hook descriptors, actual bytes/hash; no payload execution.
2. Target graph fixtures: fullversion host/target marker disagreement, extras fixed-point/cycles, missing/incompatible/orphan/duplicate/directURL/unknownextra/kernel-marker/dualcv2 rejection. Publisher metadata exact URL/size/hash/non-yanked match and provenance-pinned local inputs. No native import fixtures.
3. One-use local operator/request/soleparent-only activation/sourceclosure/tool/index config/input/limits guards; pip download only binary/no retries/no install, bounded local raw/log/metadata retention, target graph and all actual payload/publisher checks before canonical lock. Fixed safe status/error/proxy presence receipts; raw messages never public.
4. Focused/full CPU, one fresh read-only independent review and one Important/Critical TDD fix pass/no rereview; ledger each decline/cost/Minor. Source Draft/exactpush+PRCI, fresh local request-only activation and one operation. Preserve/independently inspect actual wheel lock/graph/publisher bytes or authentic failure. No oldrequest retry or image/native promotion. Continue base/OS/assets/image preparation only after complete verified wheel input lock and separate review of actual values.

CPU /workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -m unittest discover -s tests. No network/package source/native/image call in fixtures. Operation consumes newrequest02 once; old python-lock01 remains failed immutable.
