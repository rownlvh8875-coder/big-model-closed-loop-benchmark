# Engine-clock Task2 caller-root inventory contract

This addendum implements only Task2 of the [parent plan](../plans/2026-11-12-engine-clock-runtime-contract.md). Base: `2cc22c0e82dde25429a3f0216a3eb7405b127d5b` / Draft PR41. Task1 tool/test/inactive proposal remain byte-identical. Task3 preparation/authentication is unimplemented. This verifier grants no native admission.

## Interfaces and assurance

`validate_inventory(document: dict) -> dict` validates and copies metadata without filesystem IO. `collect_inventory(root: Path, expected: dict, *, deadline: float) -> dict` verifies only an explicitly supplied root against that manifest. No CLI, import-time scan, Docker/API adapter, subprocess, native import or actual image collection is provided. Executed filesystem fixtures are small temporary trees. A library-like filename has no special meaning; only bytes and metadata are inspected.

The expected manifest is caller-supplied and unauthenticated. A match covers these scoped tree observations. It does not authenticate an image/archive/config object, prove a complete installation or actual loaded GL/driver selection, GPU freshness, cache behavior, physical-host identity or observer neutrality. Hash IO consumes time and warms caches; fixture timing is not image feasibility or preflight neutrality.

## Exact manifest

Schema `installed-files-v1` has exactly `schema`, `roots`, `runtime_exclusions`, `entries`. Canonical JSON is UTF-8, sorted keys, compact separators, ensure_ascii=True, allow_nan=False, no trailing newline, at most16MiB. `canonical_manifest_sha256` is not the raw artifact-file SHA or API authentication.

Roots are sorted unique and include all six bases: `/etc`, `/lib`, `/lib64`, `/opt/python`, `/opt/venv`, `/usr`. Extra roots must lie beneath those bases; external canonical aliases fail closed. Nested roots do not repeat payload reads. Each root must resolve to an observed directory.

Entries are sorted unique by path, with exact fields:

- File: `{path, kind: "file", mode, nbytes, sha256}`. Mode exact integer0..0o7777; size exact integer0..512MiB; digest64 lowercase hexadecimal. Bool is not integer.
- Symlink: `{path, kind: "symlink", target}`. Target nonempty UTF-8, no NUL, at most4096bytes; absolute/relative allowed.

Paths are canonical absolute POSIX UTF-8, at most4096bytes/256components, no NUL, dot/dotdot, duplicate separators or trailing slash. Entries cannot descend through a file or symlink. Declared content totals at most3GiB. Hardlinks remain separate paths/read charges. Directory modes are not identity fields; empty directory topology is checked for stability but not serialized as payload.

The logical resolver expands components in order using the node graph, never host Path.resolve or a following open. Scope escapes, cycles, more than40 expansions and runtime-exclusion targets reject. Cross-base aliases are allowed. In-scope non-root dangling links are allowed without claiming loadability; root aliases must resolve to actual directories through existing intermediate components; a later dotdot cannot cancel a missing component. Unsupported legitimate future layouts can fail closed and require separate review.

## Runtime exclusions

Exactly `/etc/hostname`, `/etc/hosts`, `/etc/mtab`, `/etc/resolv.conf`, sorted. No wildcard/descendant exclusion. No payload descriptor/read/traversal. Absence or regular-file metadata is allowed; only mtab may be a symlink to exactly `/proc/mounts` or `/proc/self/mounts`. Directories, special files and other links reject. Other links cannot target exclusions. Actual Docker-managed mount/config compatibility remains Task3.

## Traversal, bounds and failures

Descriptor-relative POSIX traversal uses O_DIRECTORY/O_NOFOLLOW for directories and O_NOFOLLOW/O_NONBLOCK for files. Caller root and `/opt` ancestor are plain directories. Payload files/directories share root device; excluded metadata may differ. Device/inode/type/mode/size/mtime/ctime are checked before/after file reads and against the parent entry. Directory and symlink metadata are checked for changes. Symlinks never open payload.

The first pass hashes declared verified sizes without an extra EOF byte. The second compares metadata/topology without rehashing. This catches late changes to earlier siblings but is not an atomic snapshot, mount authentication, immutable-root proof or compromised-host defense; changes after the last observation remain possible.

Caps:512MiB/file,3GiB declared content,4GiB actual reads,16MiB canonical manifest,100000nodes/scan,256depth,40link expansions,1MiB chunks,64prefix descriptors/256KiB prefix JSON. Enumeration is bounded before sorting. Two scans give cumulative visited_nodes<=200000; this counts registered graph nodes, not syscalls. Tests can lower this new module's constants; production caps stay exact.

Deadline is finite absolute perf_counter(), exact int/float, not bool, capped at start+180s. Main-thread POSIX SIGALRM/ITIMER_REAL is required. Existing timers reject without replacement; the owned alarm and prior handler restore on exit. Ordinary blocking reads are interruptible, without a hard real-time guarantee for kernel uninterruptible IO/scheduling. Late completion cannot remain complete.

Owned descriptors close on failures/interrupts. KeyboardInterrupt/SystemExit propagate after cleanup. Ordinary failures return a bounded failed receipt. Only controlled private validation/watchdog messages may persist; uncontrolled exception text/file contents do not. Filesystem errors retain type/numeric errno plus already observed stage/path.

Result fields: `schema` (`engine-clock-file-inventory-result-v1`), `status`, `complete`, `native_admission` (alwaysFalse), `inventory`, `canonical_manifest_sha256`, `matched_entries`, `matched_prefix`, `bytes_read`, `visited_nodes`, `elapsed_s`, `failure_stage`, `failure_path`, `error`. Only complete INSTALLED_FILES_MATCH has inventory/digest. FAILED_OR_INCOMPLETE keeps bounded prefix/counters; prefix is individual descriptor matches, not complete global alias proof.

## Preservation and handoff

Producer70/workflows44/consumed registries8/raw archives/extractions/controller histories stay fixed. Task1 tool/test/proposal hashes are checked separately. Preparation16refs=null, readinessFalse, native allowance0. No actual image/native engine/Xvfb/model/ORT/GPU/clock/default/converter work, Cloud publication or main merge.

Old ABBA remains terminal authentic runtime FAIL,7null aggregates and4cases/6comparisons NOT_RUN; unused cases cannot be reused. Strict scientific FAIL, expanded NOT_RUN, geometry/physical-optics/production-ISP/full-S limits and Stage7 INCOMPLETE remain. Next: separately reviewed Task3 inputs/inactive adapter, then distinct actual image authentication and native protocol gates.
