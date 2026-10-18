# One-line summary

Continue proving the code-authored CkFoundation HTML/CSS-to-Slate/UMG pipeline; real inventory persistence now passes in a packaged Windows Game across two processes.

# Repo state

Use only `D:\Repos\CkPlugins_2`, branch `feature/reactor-umg-investigation`.
Foundation and Tests use local `feature/authored-pause-menu`; their tips are now
published and remotely verified on `feature/ui-gameplay-inventory-proof` in
`CommitAndChill/CkFoundation` (`87eb975`) and `CommitAndChill/CkTests` (`6428ea4`).
These feature histories have not been integrated into rewritten `dev` histories.
CkAuto now uses `feature/ui-package-clean-history` at published `origin/dev`
`11b7ee9495b86dabd1c26fa5d613a3bb8569e324`. Its verified Release binary is v1.61,
source `c467aeea`, SHA-256 `79edcb11ebe8eebf3ae33eba4656ece9098145bb0d4b59c8f1b5dbb509d0cf11`.
The host's previous `95b9265` pin to unpublished CkAuto `459138f` was corrected
by `73a9357` to published clean-history `11b7ee9`.
The user approved changing the host origin to `CommitAndChill/CkPlugins`.
Host feature publication succeeded and was remotely verified through `cfa6113`;
inspect subsequent documentation commits for the final tip. The destination had
no branches before publication. Its only/default branch is now
`feature/reactor-umg-investigation`; no separate PR base exists, so no host PR
was created. Agree the baseline/integration policy before creating another base
branch or integrating this work; do not fabricate a dev/main baseline.
The supplied credentials are only in local remote configuration, never tracked files.
Root commits already local: `9f82a92`, `d38a442`, `95b9265`; inspect later commits for delivery corrections.
New UI commits: Foundation `87eb975`; Tests `4d855a6`, `2176c4f`, `f8e4b09`, `6428ea4`.
No source rebase was started; preserve the verified UI source during integration.
The Git author configuration was absent; the closing commands used the existing repository author identity Saad K only for those invocations, without changing global config.
Old chainkemists remote divergence is superseded by the CommitAndChill fetch.
Foundation's initially reported 6931 incoming commits reflect shallow/re-written
ancestry, not 6931 independent changes. Inspect trees/range-diffs before integration.
Integrating incoming source can invalidate scoped evidence and needs appropriate checks.
Root recursive fetch also encountered unavailable submodule refs in remote history;
independent `git fetch --no-recurse-submodules origin dev` succeeded. Do not conceal or replicate broken remote gitlinks.
IMPORTANT: PhantomLauncher history was intentionally dropped from CkAuto and
must NEVER be republished. The legacy local branch `feature/windows-package-prerequisites`
at `459138f` contains it and remains unpublished; do not push it or mirror/all refs.
Rejected pushes led to recovering original shallow ancestry locally; one historical
PhantomLauncher LFS object was downloaded locally before the user clarified the drop.
No PhantomLauncher working files or old-history CkAuto ref were published/restored.
The selected clean CkAuto history has no PhantomLauncher path commits. Its guard
already matches the legacy fix and its Release binary has the same required runner
source, so no legacy CkAuto commit needs replaying. Do not continue legacy LFS retrieval.
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
2. Check the final host publication outcome and any approved host destination change. Submodule tips are published as described above; CkAuto must point to clean published `11b7ee9`, never legacy `459138f`. Fetch again and inspect rewritten history before integration; do not blindly replay dropped commits. If integration conflicts, stop and preserve them. Verify referenced commits on the remote before pushing the host branch and creating its PR.
3. Choose one remaining acceptance slice and state its exact scope. Reuse existing UI gym rather than create another skin/station.
4. Read build-test skill. All Unreal builds/tests use `CkAuto/UnrealToolbox.exe --project=D:\Repos\CkPlugins_2`; never raw engine commands. State planned Editor boots before launch, preflight active log locks, launch detached with Start-Process -WindowStyle Hidden and escalation for GUI, never --no-progress-window; monitor original PID and absolute output log.
5. Preserve current artifacts and use new output/stage names. Do not rerun passed gates merely to broaden claims. Any source change invalidates only relevant evidence; AS-only edits reuse binaries.
6. Check rendering at intended viewports and exact state, fonts, padding, alignment and reused key-hints. Physical input and visual claims need direct observations.
7. Record scoped results and remaining limits; commit logical slices with no assistant/model/tool attribution. CK integration may fast-forward; root work goes through a feature-branch PR.

# Suggested first message

“The packaged inventory save/load slice is verified. I’ll inspect the published state and existing acceptance notes, then identify the next bounded runtime/visual proof without repeating the completed package gate.”
