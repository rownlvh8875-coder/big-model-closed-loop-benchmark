# Panda readback ABI implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Inline; one fresh whole-branch review, no implementer delegation.

**Goal:** Connect the CPU core to a precise pinned amd64 call ABI without loading GL.
**Architecture:** strict ELF byte qualification plus an inert assembly/C register bridge; compiled CPU caller tests and retained static/synthetic evidence.
**Tech Stack:** C11/GNU assembler/pthreads, Python3.11 stdlib, existing cc/readelf/objdump as offline tools.
**Spec:** ../specs/2026-11-14-panda-readback-abi.md

## Global Constraints

Preserve all2515basefiles at a0e072e450cf6591b9da686711196d56eb9165a1/299oldpins/originals/remainingnativeallowance0. No GL/Panda/provider/model/officialORT/native load/run or old request reuse. CPU-only compilation; no new worktree/delegated implementation. Core caps unchanged24records/64MiB/12windows/2reads/964x604/8MiB. No runtime loader/patcher/GL export/query/extra original invocation.

## Review Focus

1. SysV stack offsets/alignment and signed/7th argument transport preserve exact original behavior and callee-saved state.
2. Unqualified callers never cause caller-stack/metadata/pixel reads; owner/thread/reentrancy/OFF paths retain original forwarding.
3. Pinned ELF hash plus bounded executable mapping/call/PLT/relocation checks cannot accept a different instruction ABI.
4. Captured extent/Texture role never become guessed capacity, requester-derived producer identity or live allocation authority.
5. Bridge errors and failed final emission cannot be hidden by a valid core footer or manufactured success receipt.

### Task1: Strict pinned ELF qualification

**Files:** scripts/panda_readback_abi.py; tests/test_panda_readback_abi.py.
**Interfaces:** qualify_elf(blob:bytes)->dict; inspect_elf(blob:bytes)->dict for bounded structural checks; pinned contract carries method0x62c50,size4227,call0x6305c,return0x63061,PLT0x29aa0,GOT0xcc550,code/ELF SHA and SysV roles.

- [x] RED tests: syntheticELF64 has one executable mapping/directcall/PLT+JUMP_SLOT/unique dynsym; malformed/truncated/overlap/nonexec/foreignmachine/calltarget/relocation rejected. Exact real ELF mutation/qualification smoke is separate retained offline data check.
- [x] Minimal bounded parser+qualification; focused unittest PASS; commit with source-contract receipt.

### Task2: Assembly entry/C dispatcher and actual compiled CPU caller

**Files:** native/panda_readback_bridge.{h,c,S}; tests/fixtures/panda_readback_caller.S; tests/fixtures/panda_readback_fixture.c; tests/test_panda_readback_bridge.py.
**Interfaces:** pb_context_size, pb_install(storage,bytes,config,scratch,cap,emitter,user,binding),pb_begin(ctx,host,camera),pb_entry(original7args),pb_end,pb_finish,pb_get_stats. Binding supplies original,expected_return,expected_gsg,texture[2],cached-state callback. No runtime loader. rb_read_state capacity/producer overwritten by captured registers/registry.

- [x] RED compiled caller independently sets registers/stack locals and checks sentinels. Assertions: unchanged signedargs/stackpointer,errno/source,exact forwards; ON/OFF/outside;wrongreturn/tex/GSG/r15/extent/view/z/state/PBO/thread/reentrancy; Road/Wide/requester separation; strict codec+external receipt rejects bridge/footer failures.
- [x] Implement register snapshot and bounded dispatcher; focused PASS; compiled ASan/UBSan, inspect binary imports/no GL linkage; retain25+scenario raw CPU receipts and actual ELF source-binding audit.
- [ ] Full suite PASS; one fresh whole-branch source+static/synthetic review; one Important/Critical RED→GREEN fix pass and green suite, no rereview. Record all rulings/declined items/costs.
- [ ] Own Draft/exact push+PR sourceCI; final allbasefiles/299pins/originals/main/nativehistory audit. No native activation. Copy progress and delete only this plan's scratch.
