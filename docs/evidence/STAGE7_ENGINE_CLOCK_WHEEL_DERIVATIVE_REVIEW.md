# Whole-branch review

Reviewed BASE `b9812ae4a7d795c22fc277036064e57ae8cfd3dd` through HEAD `a4684d46d4e9fde9d9a32ec0b07428dbc93bc2eb`. One fresh Senior Code Reviewer; source/index/HEAD read-only.

## Strengths

- The interface is pure bytes-to-bytes with bounded fixed failure receipts; success and failure consistently deny origin, implementation, official, preparation, execution and native authority.
- The narrow metadata allowlist preserves license/entry-point/runtime bytes and attributes, including the tested zero-external_attr case; derivative Build/Generator/provenance and RECORD regeneration are explicit and deterministic.
- Raw central-directory checks precede ZipFile allocation, source RECORD closure/hash checks precede transformation, and failures clear output and preservation-complete claims.
- The evidence distinguishes synthetic carriers, genuine saved metadata, historical pre-fix tests and final tests; existing baseline files and scientific/preparation restrictions remain preserved.

## Critical

None found.

## Important

### R1: Compressed member ranges can conceal ignored bytes

File: `scripts/engine_clock_wheel_derivative.py:233`; related lines 221, 228, 248.

Malformed stored and deflated members pass validation and return complete after silently discarding bytes within their declared compressed ranges. The documented strict, unambiguous classic ZIP validation therefore overstates what was checked. This is not a claim of native execution or loss of RECORD-covered decoded payload.

Layout validation advances by declared compress_size, but ZipExtFile truncates to declared file_size and does not establish that the entire compressed range forms exactly one completed stream. stream.read(1) cannot detect this.

Fix: Require compress_size == file_size for ZIP_STORED. For DEFLATED, perform bounded chunked validation of the exact raw compressed range, requiring one completed raw deflate stream, no unused/trailing input and exact expanded length/CRC; preserve read/deadline budgets and discard partial results on failure. Cover empty members too, and test truncated or excess-output streams when implementing the same invariant.

Narrow reproduction (run with `PYTHONDONTWRITEBYTECODE=1 python`, repository root):

```python
import struct, hashlib
from time import perf_counter
from tests.test_engine_clock_wheel_derivative import fixture
from scripts.engine_clock_wheel_derivative import derive_wheel
from zipfile import ZIP_STORED, ZIP_DEFLATED
for compression in [ZIP_STORED, ZIP_DEFLATED]:
    source, meta = fixture(compression=compression)
    nlen, xlen = struct.unpack_from('<HH', source, 26)
    csize = struct.unpack_from('<L', source, 18)[0]
    end = 30+nlen+xlen+csize
    junk = b'UNACCOUNTED'
    raw = bytearray(source[:end]+junk+source[end:])
    struct.pack_into('<L', raw, 18, csize+len(junk))
    cd = struct.unpack_from('<L', source, len(source)-6)[0]+len(junk)
    struct.pack_into('<L', raw, len(raw)-6, cd)
    pos = cd
    while raw[pos:pos+4] == b'PK\x01\x02':
        loc = struct.unpack_from('<L', raw, pos+42)[0]
        if loc == 0:
            struct.pack_into('<L', raw, pos+20, csize+len(junk))
        else:
            struct.pack_into('<L', raw, pos+42, loc+len(junk))
        n,x,c = struct.unpack_from('<3H', raw, pos+28)
        pos += 46+n+x+c
    altered = bytes(raw)
    out,r = derive_wheel(altered, expected_source_sha256=hashlib.sha256(altered).hexdigest(), expected_metadata_sha256=hashlib.sha256(meta).hexdigest(), deadline=perf_counter()+10)
    print(compression,r['complete'],r['error_code'],junk in out if out else None)
```

- ZIP_STORED: complete=True, error_code=None, hidden_bytes_in_output=False; source SHA256 899d68d228632423e9fb396e319e84c5ecc99d2db6db7428c91edabdf4ef4e3a; 2428 bytes
- ZIP_DEFLATED: complete=True, error_code=None, hidden_bytes_in_output=False; source SHA256 9d3495740ec95a2458d6790c74a06ecdec4de9715a94703e52e5d0c5e8304b0d; 2117 bytes

### R2: New provenance file can collide with an existing directory or ancestor

File: `scripts/engine_clock_wheel_derivative.py:207`; related lines 212, 311, 315.

A valid source directory named ENGINE_CLOCK_DERIVATION.json/ or a child beneath that path passes source validation. Output then contains both the new regular marker file and a directory/descendant with the same canonical path, making extraction/install ambiguous or fail while receipt reports complete.

The existing-marker check compares exact archive names to PROOF, and ancestry checks only inspect source entries before the mandatory file is inserted.

Fix: Reserve the canonical PROOF path before accepting source members, rejecting that path as either file or directory and rejecting descendants, or validate the prospective output namespace with PROOF inserted. Retain original members by rejecting rather than deleting or renaming the conflicting source.

Narrow reproduction (run with `PYTHONDONTWRITEBYTECODE=1 python`, repository root):

```python
import hashlib,io
from time import perf_counter
from zipfile import ZipFile
from tests.test_engine_clock_wheel_derivative import fixture,PROOF
from scripts.engine_clock_wheel_derivative import derive_wheel
for name in [PROOF+'/',PROOF+'/child']:
    source,meta=fixture(changes={name:b'' if name.endswith('/') else b'payload'})
    out,r=derive_wheel(source,expected_source_sha256=hashlib.sha256(source).hexdigest(),expected_metadata_sha256=hashlib.sha256(meta).hexdigest(),deadline=perf_counter()+10)
    print(r['complete'],[n for n in ZipFile(io.BytesIO(out)).namelist() if n.startswith(PROOF)])
```

- PROOF+/ source SHA256 9254b2e01a7eda3fff8f0f1891bdd756d459cf4db42f7417e2ae4ebda8dc6e73: complete=True, output includes PROOF and PROOF+/
- PROOF+/child source SHA256 3a3911f53693e7fe2e151bfaca88fdc22433200a8f92b397c6f1ffd519c5a685: complete=True, output includes PROOF and PROOF+/child

## Minor

None raised.

## Recommendations

Fix both output-namespace and compressed-stream closure invariants without broadening the accepted archive policy. Add focused regressions and perform the already authorized material-fix verification pass; retain original review/evidence.

## Declined to judge

- Actual official wheel download, WHEEL/layout compatibility, origin and API/Git authentication: excluded by the explicit synthetic-only scope; caller pins do not establish origin.
- Transform implementation authentication or policy-hash authorization: future authenticated wrapper responsibility; current receipts correctly deny it.
- Real installed dependency graph, package resolver behavior, OpenCV runtime compatibility and supported complete environment: no install or full lock is authorized or implemented.
- License/legal compatibility, redistribution rights, upstream endorsement and signed-wheel support: preservation is byte-level only; signed inputs intentionally reject.
- Native MetaDrive/Panda/ORT/model/engine/GPU/GL execution, observer neutrality, deterministic pixels, scientific causality and historical ABBA replay: expressly excluded, allowance remains zero.
- Real-wheel memory/disk/download/hash/load feasibility and multi-GiB transport: synthetic fixtures do not measure these; documented in-memory caps are not transport feasibility evidence.
- Hard realtime preemption or deadlines during future blocking IO: this helper promises cooperative bounded in-memory checks only.
- Acceptance of otherwise valid ZIP64, descriptors, extras, comments, signed archives, alternate metadata/WHEEL conventions or alternate platform tags: deliberate fail-closed policy, not supported compatibility.
- Cross-platform case folding, Unicode normalization and filesystem-specific extraction aliases beyond canonical POSIX names: no extraction occurs and no portable filesystem support is claimed.
- Malicious runtime code or asset content in a caller-pinned wheel: payload is intentionally opaque and never executed; this transform is not a malware scanner.
- Final remote branch publication, Draft PR state, CI job IDs, main/Cloud state and post-review receipt commit: root owns these later checks; review makes no merge/publication authorization.
- General historical source/test behavior beyond preservation and saved suite evidence: unrelated existing implementation is frozen; no old raw replay or duplicate test run was authorized.

## Exact evidence checked

- FIRST read final-review-package.md; read binding design, implementation plan, task-1-brief.md, task-1-report.md/json and all six Ruling lines in progress.md.
- Read all 399 production lines and all 315 test lines (29 tests), policy, guide, fixture, public audit, and full set of changed status documents across exact BASE..HEAD.
- HEAD independently equals reviewed head; git status --short empty before report creation; git diff lists 11 changed/added files.
- Compared Git blob IDs for all 366 baseline tracked files: only the three declared status documents changed. Existing source/tests/workflows are byte-identical.
- Independently verified all nine saved log sizes and SHA256 values against task-1-report.json; final focused log says 29 tests in 0.102s OK; final full log says 721 tests in 71.982s OK (skipped=7). These are saved executor results, not reviewer test executions.
- Historical evidence verified: initial 27 missing-feature failures, first integration 1 fixture error, 27-test and 28-test green logs, central-budget RED, zero-attribute RED and pre-fix 720-test result retained distinctly.
- Current implementation SHA256 5c82a5cb408d7139f70719612f0144931909bb8c36211688ac0bbc5ca0a265d2 and test SHA256 94d7ef1e150d659b92a15edc7659a077b5e576edeffe53681aa4888fb1ec4eb9 independently match report.
- Saved synthetic original 2417 bytes and derived 3475 bytes independently match public fixture SHA256 values; public audit JSON equals task-1-report.json.
- Ran only two narrow new concern-specific repro programs, each with two variants; all four malformed/conflicting inputs unexpectedly returned complete. Exact scripts and observations are retained in this report. No focused/full suite rerun.
- No source/index/HEAD edits, subagents, worktrees, network/API/download/install/native/model/engine/ORT/Docker/old raw replay/cleanup. Only final-branch-review.md and final-branch-review.json written.

## Assessment

With fixes: not ready to proceed as a completed strict archive validator at this reviewed HEAD. Resolve R1 and R2 in the authorized single inline TDD fix pass and retain updated evidence; no second review requested. This assessment is only for the synthetic derivative increment, with Draft/unmerged status and no actual official-wheel/image/native preparation authority.
