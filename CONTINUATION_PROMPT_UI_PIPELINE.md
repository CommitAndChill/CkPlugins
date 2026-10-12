# One-line summary

Continue proving the code-authored CkFoundation HTML/CSS-to-Slate/UMG pipeline; real inventory persistence now passes in a packaged Windows Game across two processes.

# Repo state

Use only `D:\Repos\CkPlugins_2`, branch `feature/reactor-umg-investigation`.
Foundation and Tests use `feature/authored-pause-menu`; CkAuto contains the deployed Toolbox update.
The closing session committed the milestone locally, but publication is BLOCKED:
Git push cannot obtain credentials and `gh auth status` reports no signed-in host.
No push succeeded. Do not publish root gitlinks until all referenced submodule commits are published.
No rebase was started; preserve the verified source until authentication and integration are addressed.
New local commits: Foundation `87eb975`; Tests `4d855a6`, `2176c4f`, `f8e4b09`, `6428ea4`; CkAuto `459138f` on `feature/windows-package-prerequisites`.
The Git author configuration was absent; the closing commands used the existing repository author identity Saad K only for those invocations, without changing global config.
Fetched remote dev divergence before these commits: root 23 incoming/28 local,
Foundation 1 incoming/27 local, Tests 1 incoming/36 local, CkAuto 1 incoming/1 local.
Incoming source changes: Foundation outline thickness rejection (`3a52cf6`), Tests outline coverage (`cfabadb`), CkAuto storage rules (`aaaa432`). Integrating these can invalidate scoped evidence and needs appropriate post-rebase checks.
Root recursive fetch also encountered unavailable submodule refs in remote history;
independent `git fetch --no-recurse-submodules origin dev` succeeded. Do not conceal or replicate broken remote gitlinks.
`Script/Binds.Cache.Headers` is generated binary cache: preserve locally, do not commit.
Never create a worktree, clone, copy or alternate checkout, or clean Binaries/Intermediate/DDC.
The user's newest AGENTS instructions control: failures belong inside CK_ENSURE_IF_NOT bodies; Shipping omission is intentional.

# Active bugs or open questions

The user wants bespoke AAA-quality game UIs driven entirely through code, with shared components, correct fonts, padding, alignment, art, animation and interactions. Do not repeat earlier visual mistakes.
Next remaining acceptance slices: physical gamepad focus/virtual-cursor activation, independent UI scale/resolution, rendered packaged typography/art, repeated-open allocation/performance, larger collections/virtualization and multiplayer consumer integration. Pick a bounded next slice; do not claim the pipeline universally complete.

# Why prior evidence was insufficient

Earlier gyms and Editor tests proved fixtures and same-process disk recreation. They could not establish a real cooked Game or persistence after process exit. That gap is now closed for the local-authority gameplay inventory slice. The packaged tests assert menu admission and two projected entries; they do not inspect pixels or drive physical input.

# Available diagnostics and first evidence

- Editor build + 5/5 focused compatible menu tests: `Saved/Logs/GameplayInventory-Gate-10.log`, D3D12 SM6. C++ source unchanged since this gate.
- Development Win64 Game build: `Saved/Logs/GameplayInventory-Game-01.log`, 1227 actions, succeeded; Jolt import linker warnings.
- UnrealPak prerequisite and first successful stage: `GameplayInventory-Package-04.log`, 189-second prerequisite build. One test-script warning was then corrected.
- Final cook/stage: `Saved/Logs/GameplayInventory-Package-05.log`; stage `Saved/UiGameplayInventoryPackage/Stage-20261011-04`. Exit 0, StageValidated true; no fresh AS script compile diagnostics.
- Packaged `InventorySave`: `Saved/Logs/GameplayInventory-StagedSave-01.log.json`, PASS/exit0, 37 seconds.
- Separate fresh packaged `InventoryLoad`: `Saved/Logs/GameplayInventory-StagedLoad-01.log.json`, PASS/exit0, 16 seconds.
- Both `*-client.log` files contain explicit `TEST COMPLETE. EXIT CODE: 0`; 13 superclass binding warnings each, no script-file compile diagnostics, failed ensures, assertions or fatal errors.
- Staged test script SHA-256 equals source. Markup, stylesheet, backdrop, SourceSans3 and MarcellusSC files were verified in stage. Renderer D3D12 SM6, windowed 1280x720.

# Symptom map

| Symptom | Likely production path / evidence |
|---|---|
| Cards stale or absent | Gameplay adapter, model RefreshGameplay, collection projection |
| Duplicate discard | Pending request ownership / CommonUI virtual pointer route |
| Save rejected after remove | Deferred coordinator and item lifetime cleanup |
| Load partially visible | Candidate owner hydration must complete before publication |
| Text clips or misaligns | Read framework UI_AUTHORING_RULES and grammar, inspect rendered reference |
| Package cannot build UnrealPak | Toolbox v1.61 prerequisite receipt; no raw build workaround |
| Save scenario refuses existing slot | Intended one-shot test ownership; choose new baked nonce and recook |

# Critical files

1. `Plugins/CkFoundation/Source/CkSlateLayout/UI_AUTHORING_RULES.md`: shared authoring lessons and acceptance.
2. Same directory `AUTHORING.md`: supported grammar.
3. `Plugins/CkTests/Documentation/UI/GameplayInventoryProof/README.md`: architecture and verified scope.
4. Same directory `WINDOWS_PACKAGE_GATE.md`: receipts, staged scenarios, limits/rerun rules.
5. `Plugins/CkTests/Source/CkTests/Private/UI/CkGameplayInventoryMenuAdapter.cpp`: authority validation, committed rows, deferred discard.
6. Same directory `CkGameplayInventoryProof.cpp`: local owner, exact catalog SaveGame, atomic hydration/rollback.
7. Same directory `CkPauseMenuProof.cpp`: authored surface, layer admission, input/pause lifetime.
8. Same directory `CkInventoryMenuProofModel.cpp`: fixtures versus gameplay projection.
9. `Plugins/CkTests/Script/CkUiAuthoring/CkGameplayInventory_PackageGauntlet.as`: packaged two-phase proof.
10. Root `GauntletTests.json`: InventorySave/InventoryLoad manifest.

# Things ruled out

Missing iOS GreenCheck/GreyCheck PNGs were GitDependencies-managed assets, not tracked source. Exactly two were restored from existing engine cache with pack/blob SHA-1 verification; no broad Setup/sync or engine source edit.
UnrealPak was a missing source-built program. Toolbox now handles it before cook. No raw UAT/build exception, duplicate checkout or artifact cleanup was used.
CommonUI handled Accept/focus alone was insufficient: native Editor test explicitly establishes hover then asserts one action plus real removal. This is not physical controller synchronization evidence.

# Architecture notes and gotchas

Gameplay inventory is local-authority standalone/listen-host only; client/dedicated requests reject. Nonreplicating transient owners still require explicit network metadata before construction.
Stable UI keys are world-scoped item handles, never persisted. Save payload uses schema version 1 plus exactly three catalog keys (potion/arrow/sword) and quantities including zero. Initial 6/24/1; after whole Potion-stack discard 0/24/1.
Requests are deferred: completion can precede lifetime cleanup. Save waits for full pending subtree drainage. Load validates entire payload and publishes only a fully ready candidate; accepted prior owner survives rejection.
Gameplay menu captures input without pausing ECS. Get_InventoryState is fixture state, not gameplay rows. Get_InventorySummary verifies gameplay projection counts.
The package test slot `CkUiPackage_20261011_a12a46_bf28` now exists. NEVER blindly rerun InventorySave or overwrite it. Change nonce and recook for another save/load pair. The gym's user slot is `CkUiGameplayInventoryProof`, never use it for automated tests.
Toolbox v1.61 clean published source `c467aeea`; vendored provenance passed without force. Source conversation `01a12a18-c21e-7880-8c32-1a991a9c461f` (FtxUiFramework). Coordination conversation `01a12a59-784e-7c21-996a-0ce53903c101` (CkPlugins_3); it was notified all our gates released engine locks.

# Concrete continuation flow

1. Read latest AGENTS, the two Foundation authoring docs, and gameplay proof notes. Inspect Git status, branch, remotes and publication without printing credential URLs.
2. Resolve GitHub authentication through the user's authorized credential mechanism, then publish local feature commits first. Fetch again, inspect remote advances, and apply the commit/push workflow. If integration conflicts, stop and preserve them; do not silently resolve or create a clean alternate checkout. Verify referenced commits on the remote before pushing the host branch and creating its PR.
3. Choose one remaining acceptance slice and state its exact scope. Reuse existing UI gym rather than create another skin/station.
4. Read build-test skill. All Unreal builds/tests use `CkAuto/UnrealToolbox.exe --project=D:\Repos\CkPlugins_2`; never raw engine commands. State planned Editor boots before launch, preflight active log locks, launch detached with Start-Process -WindowStyle Hidden and escalation for GUI, never --no-progress-window; monitor original PID and absolute output log.
5. Preserve current artifacts and use new output/stage names. Do not rerun passed gates merely to broaden claims. Any source change invalidates only relevant evidence; AS-only edits reuse binaries.
6. Check rendering at intended viewports and exact state, fonts, padding, alignment and reused key-hints. Physical input and visual claims need direct observations.
7. Record scoped results and remaining limits; commit logical slices with no assistant/model/tool attribution. CK integration may fast-forward; root work goes through a feature-branch PR.

# Suggested first message

“The packaged inventory save/load slice is verified. I’ll inspect the published state and existing acceptance notes, then identify the next bounded runtime/visual proof without repeating the completed package gate.”
