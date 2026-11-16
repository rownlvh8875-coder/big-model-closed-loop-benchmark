# Sole review and one RED→GREEN fix pass

Read-only gpt-6-astra/high reviewed fc7aa92..dd9d703. Critical0/Important2/Minor0: XY-only reprojection admitted reversed/truncated/translated sampling segments; mesh/counter metadata accepted impossible node/vertex/primitive totals. Seven failing subcases reproduced safely before any target.

ONE fixpass: retain cachedfloat32 lensinverse/clamp; independently check inverse and reconstruct near(-1)→far(+1) segments includingworld endpoints/direction/length;strict source mesh/node/primitive metadata and complete/partial counter reconciliation. Three regression methods cover bothfindings and legitimate unfinished partialreads. RED→GREEN;14new/99combinedCPUtests andactionlintPASS. Full latestsourceCI required before onechildactivation. No rereview. DeferredMinors0.

Declined scope/executor rulings in ledger: actual600s completion;actualPanda/livegeometry;GPU/depth/cause/repair/Stage7;hostedCI/artifact/PR;hardpreemption inside inheritedPanda calls;unrelatedbaseline. Every ruling has cost. CPU endpoint tolerance32float32eps is separate from1e-9world/1e-12relative intersection comparison and never changes imageSHA.

Fixedsourcef7ee8e4 fullcanonicalfourjobsSUCCESS/1982tests/7skip eachunitlog before actual. Actualonechild completed7captures/14sourceimages in290.405s;1004CPUtriangles/2meshes independently recomputed. Road7knownyellow image exact;Road4two-pixel mismatch means fullsource qualificationFAIL,not a renderer/repair PASS. Native/display/container0,OOMfalse,removedtrue.
