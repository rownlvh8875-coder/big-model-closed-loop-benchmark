# Sole whole-branch review, one correction pass

Read-only gpt-6-astra/high reviewed dacce235..58ae11b. Critical0/Important3/Minor1. No rereview.

Important fixes: missing argparse entry import; captured UTF8 bytes must not receive universal newline normalization; preserve each shader descriptor before saving stages so oversize/timeout retains saved vertex evidence. Tests: --help real isolated subprocess; rehashed LF→CRLF mismatch; real snapshot with CPU doubles for oversize fragment and between-stage timeout. Corrected synthetic PID fixture before confirming the actual orphan-file RED.16 new CPU tests/actionlint PASS; whole-suite result is recorded separately,not presumed green.

Deferred Minor: extreme finite tonemap inputs can overflow toNaN; native receipt admission never calls this offline function.

Every declined item is ledgered with cost: actual runtime; hosted CI/request/artifact/PR; GPU execution/uniform/output; rootcause/repair/matrix/Stage7; actual skybox variant; independent image extraction; full baseline semantics; coherent producer fabrication. Remote push was auto-review rejected due prior no-publication instruction. No remote write/native activation performed.
