# Whole-branch and retained-data review

Reviewed base `3555a133ed3ae999cdcb86ab3867fe3f5005530e` through head `689b89cb5f481a362391e879c82f9aae11ce5a84`, including all three implementation modules, three test modules, specification, plan, ledger, result, and evidence index. Read-only checkout; no subagents, checkout mutations, replay, trace capture, GL, provider, model, or ORT execution. Only existing CPU Python and offline apitrace dump used.

### Strengths

- Distinct context/object-kind/lifetime/storage keys and separate read/draw FBO bindings avoid the common texture/renderbuffer name collision. Snapshot-before-write dependencies remain causal, and level-zero reads survive mip generation.
- Partial writes retain preceding possible producers. Reports consistently deny pixel reconstruction, executed fetch/write proof, GPU completion, sealed-frame association, and unique cause. Requested samples are expressly distinguished from measured allocation.
- Decoder authenticates the original trace and binary/package, restricts pickle globals, bounds stream/read/line/call/node/report sizes, checks verbose thread coverage against decoded counts, and closes/kills failed or stalled children. Focused tests independently passed: 31 tests, 0.158 seconds. Existing full-suite log reports 1316 tests, 7 skips, 116.057 seconds, PASS.
- Independently hashed both complete original trace files: sizes and SHA256 match the published pins. Every indexed evidence file and both retained full graphs match their recorded size/hash. Independently checked all 299 source_closure entries against the retained consumed request at source 09ad7e3272713ec86031ab8158e3f9fdf0cf245d: zero mismatches.
- Independently inspected original offline dumps, including ON0 resolve 7843 (read FBO3, draw FBO2), RGB draw8709 and pointer-only read8739; original program7 reflection shows tex sampler2D/location1/unit0; ON0 read37381 and ON1 read37387 are pointer-only reads. Attachment samples confirm texture3 in the Wide resolve target and textures5/6 in RGB outputs. Both full graphs contain 3602 nodes, causal dependencies, 60 reads and 60 extracted routes: 30 each of (FBO8, texture5, sampled2, FBO3→2, RBO4, requested4) and (FBO9, texture6, sampled3, FBO5→4, RBO7, requested4). These checks support the retained-cohort conclusions within their stated limitations.

### Issues

#### Critical (Must Fix)

None found.

#### Important (Should Fix)

1. **Sampler evidence can silently disappear or select the wrong texture when reflection is absent or late.** `scripts/gl_read_provenance.py:120`, `:257`, `:268`.
   - Trigger: a successfully linked program draws before all active uniforms have been reflected, or a valid glUniform1i assignment precedes glGetActiveUniform. GL reflection is an observation, not a prerequisite for setting uniform state.
   - Reproduced: removing reflection/location calls from a linked draw produces `SCOPED_COMMAND_PROVENANCE_COMPLETE` with an empty sampler list. In a two-texture fixture, get-location→set location1 to unit1→reflect tex→draw reports unit0/texture1 and `successful_link_default_zero`, despite the recorded assignment to unit1.
   - Effect: the supposedly conservative dependency graph omits a possible source or names the wrong one. Unsupported/missing sampler evidence is presented as complete, which violates the fail-closed boundary. This is not a pixel-simulation request.
   - Fix: retain recorded integer assignments by location regardless of when their types are learned; apply them only to reflected samplers. Track the recorded active-uniform count/index coverage per link generation and fail closed (or explicitly mark dependency coverage incomplete) when a draw lacks enough reflection to enumerate samplers. Add regressions for missing/partial reflection and assignment-before-reflection. Actual program7 dump inspected here has complete reflection before assignment; this finding does not establish that the retained RGB routes are wrong.

2. **Default framebuffer front/back selections are silently aliased.** `scripts/gl_read_provenance.py:70`, `:89`, `:246` (especially `if f is None:continue` at248).
   - Trigger: bind default framebuffer, glDrawBuffer(GL_FRONT), clear/draw, then glReadBuffer(GL_BACK) and read. Both selected buffers are currently represented as the hard-coded BACK slot.
   - Reproduced: that sequence reports the front clear as the potential writer of `default-drawable:111/color:1029` (BACK), and succeeds as complete.
   - Effect: independent resource planes acquire a false producer edge. The limitation that default contents are unknown does not justify inventing a command route between distinct buffers.
   - Fix: retain supported default drawable read/draw selection state and distinct resource keys, or reject unsupported default selection/use explicitly. Test front-versus-back and GL_NONE without changing the named-FBO behavior. The retained reported read routes use named FBOs, so their current camera route conclusion is not contradicted by this reproduction.

3. **Route equality omits the read endpoint and parts of the attachment identity.** `scripts/analyze_saved_gl_reads.py:18` and `:29`.
   - Trigger: same upstream RGB program/resolve route and marker, but a different read FBO or read attachment/texture lifetime. `_route_key` includes only the upstream resolve and bare sampled texture name. `read_fbos` is printed separately but never compared; read_buffer/source/source_descriptor are not part of equality.
   - Reproduced: changing a read's FBO to99 and source to a different attachment in a copied valid report leaves `same_route_topology=True`.
   - Effect: the headline equal-route count can claim the original read→RGBdraw→resolve topology is unchanged when the read endpoint changed. This is topology, not excluded raster or pixel equality.
   - Fix: include a normalized read endpoint (FBO, selected buffer, source descriptor/lifetime) and the relevant sampled/output resource identities in the comparison key, while continuing to exclude call ordinals and opaque host context pointers. Add changed endpoint/attachment/lifetime regressions. The independently audited retained reads currently have matching endpoint tuples; this is a comparator correctness gap, not evidence that those 60 pairs differ.

4. **The runner emits a preservation verification claim that it never verifies.** `scripts/analyze_saved_gl_reads.py:118`.
   - Trigger: run the CLI in a checkout with any old pinned source changed. Input verification checks native JSON/traces/tool, but never reads the source-closure request or hashes those source files. It nevertheless emits `source_pins_preserved=299`.
   - Effect: a new machine result falsely attests preservation, and downstream users cannot distinguish the historical independently audited receipt from an unchecked rerun. Independent validation makes the retained result true today but does not make this CLI field measured.
   - Fix: verify the pinned source closure before emitting the verified count, or remove/rename the field to an explicitly historical external claim with its immutable receipt reference and `verified_by_this_run=false`. Test that a changed source cannot produce a fresh affirmative preservation assertion. No request to consume or rerun the sealed allowance is implied.

#### Minor (Nice to Have)

None raised; no polishing requested.

### Recommendations

Use the authorized single Important/Critical TDD fix pass for the four items, preserve the retained actual evidence and failed attempts, and keep historical checks separate from what a new CLI invocation verifies. Existing actual topology evidence is useful and should not be promoted to physical-frame or pixel-content proof.

### Declined to judge

- Actual executed GPU writes, pixel values, sample fetches/LOD, full raster/vertex/uniform behavior, conditional execution, and GPU completion: explicitly outside this command-provenance reducer; conservative prior dependencies and uncertainty flags were assessed instead.
- Actual multisample allocation or resolved-pixel equality: only storage requests and recorded blit commands are available; no new GL queries are authorized.
- Original host primary-frame mapping as a physical association: inherited fixed schedule only, with pointer-only read destinations and no capture nonce; checked that reports retain this limitation.
- Cross-association to the newer sealed cohort, untraced equivalence, observer neutrality, root cause, renderer repair, official model input, and Stage7 completion: no evidence/authorization for these claims; reports correctly deny them.
- Repeating full ~2GiB aggregate pickle decoding or the entire full suite: existing authenticated full graphs and full-suite log were available; independently ran focused tests, hashed originals/evidence/source closure, and sampled offline dumps instead.
- Exact RSS/headroom, decoder child CPU, failed/debug-run totals, and end-to-end development costs: not measured by the provided receipt; parent CPU exclusions and memory limits are explicitly disclosed, so no substitute estimates were made.
- New captures, replay, native/provider/model/ORT execution, package installation, remote CI/publish/merge behavior, or post-review fixes: outside this read-only review and expressly unauthorized here.
- General full-OpenGL coverage beyond the explicitly scoped 2D/unshared reducer: not requested; rejecting unsupported inputs is acceptable. The Important issues above concern silently accepted inputs and affirmative metadata, not a request to implement broader GL.
- Runtime trust against concurrent privileged modification of authenticated files or a compromised pinned decoder/dependencies: outside the retained local immutable-input threat model; no new remote authentication claim was inferred.

### Assessment

**Ready to merge? With fixes.**

The retained-data conclusions are supported by independent hash and command-sample checks and retain appropriately narrow claims. Four Important correctness gaps allow accepted synthetic histories or a future rerun to produce false dependency/topology/preservation assertions; fix these in the single authorized pass before integration. No Critical finding and no retained pixel/frame-equivalence claim is supported.
