# Pinned Panda dispatch coverage

Base93475a36e8a68889aa632182dccd4cdc3dde39c0;feature/panda-dispatch-coverage-v1.
Static audit completed; native installation/canary readiness is BLOCKED. Original
strict0/4FAIL/Stage7INCOMPLETE remain. This task executes Python/cc/binutils only,
never loads the Panda ELF or runs GL/MetaDrive/provider/model/officialORT/native.

The new ELF reader derives relocation-backed imports from actual PT_DYNAMIC
RELA/JMPREL tables, with bounded load/string/symbol/slot validation. Section headers
can be removed without losing imports; an address-taken CPU function is found via
GLOB_DAT as well as JUMP_SLOT. The pinned Panda image has741function imports,105GL
function imports and14needed libraries. All105GL slots independently match readelf.
Legacy glXCreateContext is imported at slot0xcd150; glXGetProcAddress/ARB are absent
from that import inventory. These are file facts, not runtime execution receipts.

Four upstream source files and LICENSE match the exact Git blobs of commit
470e352ab87ceae6e30429720e4690c8371f5a55 and SHA256 pins. The lexer retains both
preprocessor branches, distinguishes comments/strings/declarations/computed calls,
and reports334distinct literal extension names,93direct-source names.268literal
spellings occur in ELF, which does not establish active compiled branches. The
conservative union with imports has445names; the pinned17route declarations cover
16of them, leaving429unclassified. This exceeds the existing256safe-name budget
even before requiring unsupported state mutation handling. No unknown name is
automatically made safe.

The current profile forbids16missing names from being safe, including legacy
glXCreateContext,glDeleteBuffers/ARB,conditional OES/NV/SGIX aliases and some GLX
drawable operations. Broad prefix prohibitions do not prove every name changes
captured state; a future profile must classify or adapt them explicitly. Source
includes a private GLXproc resolver and POSIXdlopen/dlsym fallback, plus the unified
compiled-function-table path. A GOT-only candidate cannot claim complete coverage.
The preferred next implementation candidate is source-integrated dispatch before
temporary context creation, at every unified extension return and at direct
state-call originals. No modified Panda build or installer has been implemented
or qualified by this audit. Camera/native lifetimes, runtime ABI, driver state,
GPU write freshness, new image/environment/transport and fresh ON/OFF contract
remain separate gates. Existing environment guard still rejects ambient preload.

Final verification:26focusedPASS0.573s;1441fulltests/1434PASS/7skip95.257s;
12actual CPUCLI scenarios pass/reject as expected, preserving existing output on
reuse and rejecting image/source/delivery/symlink/allowlist mutations. CPUfixture
is compiled but never loaded/executed. Compile/link0.032046540s excludes tests,
review,CI,development and native instrumentation overhead. Evidence retains the
independent comparison's initial OBJECT-variable prefix error and its raw inputs;
the production parser did not change. Rawregex335versuslexical334 is explained by
an upstream block-commented glDepthRangedNV lookup, not a lost active lexical call.

The sole fresh whole-branch review at1c3077021f4fe05764a2a78ae14f681ca7158ab7 found
0Critical/4Important/0Minor. One TDDfixpass addressed invalid symbol extents/table
aliasing (loader SysV/GNU hash counts, nullsymbol, nonoverlap, index bounds),
LF/CRLF phase-two splice loss (before comments/tokens, physical lines preserved),
server/client attribute restore/reset names admitted as safe (now prohibited),
and FIFO inputs blocking before validation (regular-file/nonblocking guards).
GNU/SysV/both CPUhash profiles match independent symbol counts; strings/chars do
not alter parenthesis nesting. The reader is a structural undefined-function-
import profile, not a complete loader or R_X86_64_64/full-call-path inspector.
Reviewed pre-fix raw evidence remains under before-review-final/ and its GitHEAD.
All8reviewer-declined behaviors have executor rulings; no rereview/minor polishing.
Final immutable-source Draft/CI/head receipts are in the PR body and retained
output/stage7-panda-dispatch-coverage-01/final-verification.json after commit.

All3083basefiles/299oldpins/10originals/main/Drafts102–108/eightnativehistories are
preserved. No Cloud/registry publication, main/sharedbase push/merge, consumed
request reuse or new native/provider/model/officialORT run. Indexed proof files,
source pins and later review/final exact-source CI receipts accompany this result.
