# Continue after pinned Panda dispatch coverage

Currentbranchfeature/panda-dispatch-coverage-v1;base93475a36e8a68889aa632182dccd4cdc3dde39c0.
Exact finalHEAD/Draft/sourceCI is in this PR body and retained
output/stage7-panda-dispatch-coverage-01/final-verification.json. Do not reapply old
changes, publish Cloud/registry, modify main/sharedbase or reuse native requests.
Read RESULT/LEDGER and docs/evidence/panda-dispatch-coverage-01/proof-index.json.

Completed: loader-backed bounded ELF import reader; source lexical inventory;
exact Panda/source/current-delivery profile pins; explicit-name coverage and
installation planning gate; CLI with bounded canonical inputs/new output only.
Panda ELF is only read as data. New CPU inspection.so has unresolved GL-shaped
names and must NEVER be loaded or called. No native admission is produced.

Final1441tests/1434PASS/7skip95.257s;26focusedPASS0.573s;12CLIcases. One fresh
review0C/4I/0M; all4Important fixed with RED→GREEN tests in onepass, no rereview.
Hash-bound symbol extents, physical-line splicing, unsafe restores and FIFO handling
are covered; the fixed gate still grants no native authority.

Reproduce CPU unit checks:

```sh
/workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B -m unittest tests.test_readback_elf_imports tests.test_panda_dispatch_coverage
```

Reproduce pinned audit into a NEW output directory (existing outputs reject):

```sh
/workspace/.cloud-tools/stage7/first-divergence-cpu-replay/bin/python -B -m scripts.panda_dispatch_coverage --image output/stage7-readback-return-core/source-audit/libpandagl.so --source-dir docs/evidence/panda-dispatch-coverage-01/source --out output/panda-dispatch-coverage-next-audit
```

Audit exit0 means completed static inspection, while report runtime_admission_ready
and installation_qualified stayFalse. It does not mean the native gate passed.
Potential445names/429unclassified/16profile-prohibited names are conservative
possibilities across source branches.334literal names/268ELF spellings do not
prove which resolver branch ran.14needed libraries and741function imports also
do not attest the entire installed image or runtime environment.

Next implementation, under a fresh plan/namespace:

1. Build a source-integrated dispatch candidate against the pinned upstream tree.
   Preserve original calls/returns/NULL/errno and no extra GLqueries/readbacks.
   Intercept before first temporary legacy glXCreateContext (current table lacks
   it), plus New/Attribs/qualifiedSGIX context lifecycle. Cover unified extension
   returns, including compiled table, private GLXproc and POSIXsystem fallback.
   GOT-only/preload assumptions are insufficient; old environment stays unchanged.
2. Add/qualify buffer-deletion state handling and missing capture-state aliases.
   Explicitly classify harmless drawable/other names under a new reviewed profile
   rather than implement every broad-prefix name as a context mutation. Resolve
   conditional branch selection and safe256cap against the actual new build;
   do not blindly allowlist445source possibilities or increase caps to pass.
3. Bind the built candidate to actual mapped code, original dispatch/image/build/
   environment, provider Texture/buffer/commonGSG identities/native lifetimes and
   process/window/sink receipts. Existing CPU registry/tail/cache/core/channel are
   reusable components; none independently proves actual Panda coverage/driver state.
4. Only after those gates create a fresh bounded ON/OFF canary contract/allowance.
   Remaining native allowance0, original strict0/4FAIL/Stage7INCOMPLETE. Preserve
   PSSM/Chase/render/read counts and oldraw evidence. No cohort expansion or official
   model run before canary review; no naive texture extraction experiment replay.
