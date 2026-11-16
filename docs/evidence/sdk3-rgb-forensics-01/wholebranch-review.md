# Sole fresh review and one fix pass

Read-only gpt-6-astra/high reviewed46b750e6..c0344d2;42focused tests/actionlint/diffcheckPASS,no native execution or edits. Important1: missing container.id and execution.container_id bothNone admitted. Important2: matching absent/replayed capture modes and command user0:0/GALLIUM_DRIVERllvmpipe admitted. Both regradedImportant by effect and fixed in one RED→GREEN pass with missing/null/empty/malformed IDs,mode,user,driver,duplicate-env and extra-capability cases. Command admission now checks exact native argv,resource/isolation options,readonly mounts,ownership and software-renderer environment.

Executor also found exact-source CI regression: frozen original trial source changed,breaking5tests+125errors in each canonical unit run. Existing public source-pin test reproducedRED. Original trial restored byte-identically; separate adapter executes the unchanged code under a private globals dictionary with only the observer constructor changed,leaving original globals untouched. Default path calls original function. New factory-dispatch and source-pin tests pass. Combined46focused/regression testsGREEN6.490s. Full canonical CI required before any target. No rereview.

DeferredMinor: expand corruption coverage to actual reordered/wrong-scene/oversized cases and decoder-specific EOF/trailing checks with adjusted compressed lengths. Current validation rejects them,but tests cover only subsets.

Declined-to-judge behaviors and executor rulings are retained in ledger: actual hosted4children/lifecycle/resources; exact-sourceCI/activation/artifact authentication; actual48image recomputation/reproduction; observer timing/memory/causality. All remain executor obligations; no native success,repair,expansion or Stage7 claim from review alone.
