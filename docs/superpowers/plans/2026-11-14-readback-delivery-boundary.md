# Readback delivery boundary implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Inline, one fresh whole-branch review; no implementer delegation.

**Goal:** Deliver typed original calls into the cache and bind CPU producer completion to actual process/code/channel evidence.
**Architecture:** inert Cdispatch/bootstrap/tail entry; Python proc/ELF/code checker; kernel-credential packet/spool collector. Actual compiled CPU child exercises the complete existing bridge/core/codec.
**Tech Stack:** C11/GNUamd64/pthreads; Python3.11 stdlib; Linux proc/Unix sockets; existing cc; no GL/Panda linkage/import.
**Spec:** ../specs/2026-11-14-readback-delivery-boundary.md

## Global Constraints

Basec06a3a3eb8e215a8e40054433cf4c6c4c1d42bdc/all2734basefiles/299pins/originals/main/eightnativehistories unchanged. No additionalworktree/delegation/ambientloader/GLquery/native/provider/model/officialORT/publication/oldrequest. Core/state caps unchanged; delivery10000events,delete32,safeprocs256x63B,packet16KiB,stream64MiB,maps1MiB/4096rows,memoryranges<=1MiBeach/2MiBtotal. Onefreshreview/onefixpass/no rereview.

## Review Focus

1. Alias/proc NULL/mismatch/unknown routes preserve capabilities and exact original forwarding/errno on every failure.
2. Bootstrap replay preserves actual return-dependent order without extra GL calls, stale state, unsafe delete reads or hidden error recovery.
3. Tail arming preserves original returnPC/7args/callee-saved registers and only follows successful bridge/cache binding.
4. Code-range mapping checks reject PID/file/map/byte races and cannot admit arbitrary memory as the pinned target.
5. Credential/nonce/status/spool/exit bindings reject forged,partial,extra or failed finalization without claiming native authority.

### Task1: Typed delivery and bootstrap/tail

**Files:** native/readback_call_delivery.{h,c};native/readback_delivery_entry.S;
tests/fixtures/readback_delivery_fixture.c;tests/test_readback_call_delivery.py.
**Interfaces:** rd_context_size/install(dispatch,allowlist,eventcap);rd_attach(cache);
rd_bind_bridge(...pb_installargs);rd_observe;rd_finish;rd_get_stats;typed rd_* original
call wrappers and rd_get_proc/arb;rd_read_pixels tail. CPUcaller compiled from prior
fixture with preprocessor symbol aliases, preserving prior source bytes.

- [ ] RED CPUfixture/independent wire tests for all Review Focus1..3; missingdeliveryFAIL.
- [ ] Minimal dispatcher/bootstrap/tail, scoped codec interop; focusedPASS,ASan/UBSan originals/stream/counters; commit.

### Task2: Mapped executable code proof

**Files:** scripts/readback_process_mapping.py;tests/test_readback_process_mapping.py.
**Interfaces:** parse_maps(bytes);elf_ranges(bytes);verify_process_code(pid,path,sha,ranges,reported_addresses)->dict. Reviewed ELF VA/size ranges are external input, no ABI/native claim.

- [ ] RED bounded syntheticmaps/ELF/offset/protection/deleted/hash/byte mutations plus actual compiled heldchild success/rejection; missingcheckerFAIL.
- [ ] Implement pread/file/dev/inode/load-bias/starttime/stablemap check; focusedPASS. Actual probe uses only ownCPUchild, never renderer.

### Task3: Credential-bound producer/spool receipt

**Files:** scripts/readback_producer_channel.py;tests/test_readback_producer_channel.py;
CPUfixture controlpacket mode,docs/result/ledger/evidence.
**Interfaces:** recv_record(socket,expectedpid,uid,gid,nonce);run_cpu_probe(exe,sha,mode,codeprofile,nonce,timeout)->dict; returns metadata/CPUdecoded state, never nativeadmission.

- [ ] RED actualsocket credentials/truncation/rights cleanup/foreignsender, childnonce/status/extra/exit/spool/sink/map failures; missingchannelFAIL.
- [ ] Implement samechildcode+status+spool+codec binding; focusedPASS and realCPUprocess artifact receipts; fullsuitePASS.
- [ ] Onefreshwholebranchreview,oneImportant/CriticalRED→GREENfixpass+fullsuite,no rereview; ledgerallrulings/costs/declineditems.
- [ ] OwnDraft/exactpush+PRCI; finalallbase/299pins/original/main/nativehistory audit. Retain concrete nextnativeadmission gates; copy/remove only thisplan scratch.
