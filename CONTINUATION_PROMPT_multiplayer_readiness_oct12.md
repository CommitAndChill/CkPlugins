> **Feature transfer checkpoint:** The three plugin feature branches have been published and their exact heads verified. The root commit containing this handoff records those pins for feature-branch publication; dev remains unchanged.

# One-line summary

Continue production multiplayer readiness one bounded gym family at a time. Scene Node's focused production path is verified; Scene Node + Tween is the next separate review. This feature-branch package preserves the WIP and does not authorize merging it into dev.

# Repo state

- Receiving workspace: use an existing CkPlugins checkout. Resolve all paths below against it; the producing checkout was `D:\Repos\CkPlugins_3`.
- Root: `feature/multiplayer-test-readiness`, remote `https://github.com/CommitAndChill/CkPlugins.git`. The root contains fetched dev `d410f072f8b203df6d9dea575a630ad2a5c23c19` plus the rebased WIP and this handoff.
- Foundation: `feature/multiplayer-test-readiness-rebased`, tip `409985d1f1da88d1783f2fce282f37301506dcd5`, contains dev `562da71fd`.
- CkTests: the same plugin branch name, tip `ac511d1600745a650c8e76e8b2dfd448e0930345`, contains dev `4f4f4bc3`.
- GameplayDebugger: the same plugin branch name, tip `a7de739c1c8f2c702294668a3323d3b778bed9f6`, contains dev `e05ddc4e`.
- The code checkpoint, publication branches and all submodule pins are in `Handoff/MultiplayerOct11/publication-oct12.json`. The host gitlinks select the plugin tips above; do not replace them with plain dev tips and lose the WIP.
- No implementation remains unstaged. Machine-local scratch evidence, backup refs and rebase safety stashes remain on the producing machine; they are not needed to fetch the published plugin source. Older stashes are user data, not cleanup permission.
- The earlier unrelated cleanup committed seven portable build hooks, 38 source-backed gameplay tags and two historical navigation handoffs. It discarded 14 obsolete files and two superseded checkout-transfer stashes. The optional Saved profile remains machine-local.
- All prior WIP was preserved across the publication rebase: root 7/7, Foundation 35/35, Tests 163/163, Debugger 9/9, zero unmatched range-diff commits. Root gitlink conflicts select the corresponding rebased plugin heads; Tests' adapted context retains the new upstream Pixel Sprite registration and all multiplayer registrations.

# Active bugs or open questions

1. The older transport ledger missed Gait, Runtime Convex, Runtime Mesh and the new upstream Pixel Sprite gym. The reconciled registry has 96 entries, seven verified rows and 89 pending rows. No overall multiplayer-readiness claim is made.
2. Scene Node + Tween remains pending despite its incidental two passing cases in the SceneNode.Network selection. Audit actual production transport before claiming the family verified.
3. Abrupt GameState-loss quarantine and rendered acceptance remain explicitly unproved. Source loss is non-destructive quarantine; automatic lifetime reparenting or arbitrary actor destruction requires a new maintainer decision.
4. The feature history contains online-services research marked `[DROP BEFORE MERGE]`. A handoff push is not approval to merge that material or advance dev.

# Why prior fixes or investigations were insufficient

- Original Scene Node drafts had never compiled or run. After dev integration the first gate passed only 16/50.
- WithActor adds the production unnamed label, which the fresh-record admission seam rejected. Explicit existing-Transform opt-in now preserves that exact label while rejecting named labels and prior links.
- Client metadata observation ran before ECS output. GameState PostUpdateWork ordering plus a controller prerequisite on its exact bound state fixes installation of frozen metadata.
- Retirement checked for visual actors after the production actor cascade had already removed them. Exact actor-serial absence and complete known ECS deallocation now permit scope retirement; unknown/reentrant members remain quarantined.
- The actor-loss fixture incorrectly waited for all 23 handles after intentionally losing one. It now proves exact lost-node identity/deallocation and strictly checks the 22 survivors; the unregistered-child case retains all 23.
- A preceding transform callback can initiate another actor's destruction before its output visit. SyncToActor now checks validity and BeginDestroy before reading its root, retaining diagnostics for an invalid live root.
- Role 17's initial scale was 0.5 on authority and 1.0 on clients, while location/rotation and metadata agreed. ForceRefresh cleared the initial dirty mask. A private, preflighted Transform publication helper now publishes the committed initial L/R/S data into existing entries before refresh, without global mask or ordering changes.

# Available diagnostics and first evidence to collect

Read `Handoff/MultiplayerOct11/production-semantics-PROGRESS-oct11.md`, the transport ledger and `scene-node-production-oct12-green-evidence.json`. The publication manifest records the latest post-rebase build/gate and source identity. Older evidence remains historical and does not prove new revisions.

First inspect the current root and submodule branches, HEADs, indices and dirty paths. Confirm the host pins match the publication manifest before editing. Read applicable global/project instructions and the actual Foundation C++/AngelScript guides; the missing Foundation Script/CLAUDE.md is recovered at Handoff/MultiplayerOct11/AngelScript-guide-recovered.md with exact provenance and current-policy precedence. Read it plus the tracked gameplay and interop skills before script implementation; validate examples against the current source.

# Likely symptoms and causes

| Symptom | Evidence-backed cause or boundary | Files |
|---|---|---|
| Existing actor node rejected | Unnamed label versus fresh-record admission | Foundation Record_Utils.h, SceneNode_Utils.cpp |
| Role 17 correct L/R but wrong scale | Initial native seed publication lost through refresh | Foundation Transform_Utils.cpp, SceneNode_Utils.cpp |
| Frozen metadata one sequence behind | GameState/controller ordering relative to ECS | CkSceneNodeGym_GameState.as, PlayerController.as |
| Retirement unproven with only scope present | Stale child-presence guard | CkSceneNodeGym_Retirement.cpp |
| Root ensure after callback destroys actor | InitiateDestroy still reached by current output batch | CkTransform_Processor.cpp |
| Source disappears abruptly | Non-destructive quarantine; abrupt-source proof still owed | RemoteVisuals.cpp, GameState.as |
| A passing Tween smoke row seems sufficient | Production transport review remains separate | Transport ledger, SceneNodeTween scripts/tests |

# Critical files

1. This prompt: authoritative Oct12 resume point; older transfer prompts are historical.
2. `Handoff/MultiplayerOct11/production-semantics-PROGRESS-oct11.md`: current evidence and cleanup/publication boundaries.
3. `Handoff/MultiplayerOct11/production-transport-review-oct11.json`: full pending work list.
4. `Handoff/MultiplayerOct11/scene-node-production-oct12-green-evidence.json`: original 50-case focused result and immutable source hashes.
5. `Handoff/MultiplayerOct11/publication-oct12.json`: delivered branches/pins, rebase audit and latest verification.
6. `Plugins/CkFoundation/Source/CkEcsExt/Public/CkEcsExt/SceneNode/CkSceneNode_Utils.cpp`: total, atomic existing-Transform composition.
7. `Plugins/CkFoundation/Source/CkEcsExt/Public/CkEcsExt/Transform/CkTransform_Utils.cpp`: private seed-publication helpers and native transform path.
8. `Plugins/CkFoundation/Source/CkEcsExt/Public/CkEcsExt/Transform/CkTransform_Processor.cpp`: output lifetime eligibility.
9. `Plugins/CkTests/Source/CkTests/Private/CkSceneNodeGym_RemoteVisuals.cpp`: structural closure, pure queries, explicit advancement and native applied-pose proofs.
10. `Plugins/CkTests/Source/CkTests/Private/UnitTests/CkGym/Test_SceneNodeGym_ProductionTwoOwner_Network.spec.cpp`: actual two-owner production witnesses and diagnostics.

# Things ruled out

- Do not restore client pose clones, custom pose snapshots or client SceneNode/timer simulation to fix a failing receipt.
- Do not weaken pose tolerances, moving-witness counts or identity/deallocation checks to make tests green.
- Do not revive old source-side callback timing assumptions; the frame sampler is read-only.
- Do not claim rendered or abrupt GameState-loss acceptance from NullRHI results.
- Do not apply old preservation stashes or use navigation handoffs as authorization for operations in this multiplayer checkout.

# Architecture notes and gotchas

Scene Node uses 17 real SourceActor/WithActor Transform replicas plus an identity-only role-0 scope per generation. Authority owns the six roots, eleven SceneNodes and six motion timers. Client snapshots carry lifecycle/station metadata only. Native driver L/R/S, actual ECS Transform and actual component output provide presentation proof. Known retirement tracks 41 historical ECS identities and exact actor index/serial identity, not merely IsValid or iterator visibility.

Use lifetime-aware object references; no new raw pointers or const_cast without explicit approval. CK ensure predicates must be total, and failure action belongs in the inverted ensure body. Keep the intentional Shipping ensure policy; do not duplicate recovery to defeat it. Multi-step admission must reject without partially publishing a successful subset.

No linked worktree, clone, mirror, repository copy or alternative checkout is authorized. Work in the selected checkout. Preserve existing build artifacts and the optional storage profile. Build/test only through `CkAuto/UnrealToolbox.exe`, with absolute `--project=`, detached PowerShell `Start-Process ... -PassThru -WindowStyle Hidden`, progress window enabled, and a fresh `--output` log. Never use raw build/editor commands or `--no-progress-window`; never perform Shipping, cook or package work here without the required authorization.

# Diagnostic and verification flow

1. Fetch the root feature branch and its recorded submodule revisions in the existing selected checkout. Verify the remote heads against the publication manifest; do not merge or push dev.
2. Read this prompt and the publication manifest; verify remote branch/pins and clean ownership before switching or updating an existing checkout. Protect any new user dirt instead of blindly resetting it.
3. Confirm the active transport ledger inventory matches the current gym registry; do not drop the four newly reconciled pending rows.
4. Start with Scene Node + Tween. Trace authority simulation, actual client-visible state and its native production transport. Keep diagnostic telemetry separate from gameplay-state transport.
5. Identify a bounded missing production-path proof or concrete failure before changing implementation. Reuse real manager/task/entity state and compatible existing tests.
6. Apply the project delegation policy. Consult a bounded read-only Astra review for unresolved consequential replication/lifetime/persistence uncertainty or before a third attempted fix; retain lead decisions and reconcile its source evidence.
7. State editor-boot budget, choose a focused gate and build only when native/build inputs changed. AngelScript-only changes reuse current binaries. Freeze source/index from launch through process exit/log unlock and inspect raw logs, ensures, script errors/warnings and skipped/contaminated rows.
8. Mark only the actually verified row; a focused green test is not repository-wide acceptance. Update progress and precise remaining work.
9. Make scoped logical commits under command-scoped approved identity `Saad K <saadrustam@gmail.com>`, no AI attribution. Stage explicit paths only. Do not infer further push/dev merge approval from this completed handoff publication.

# Suggested first message

I have checked the local root and submodule pins and read the Oct12 evidence. I will review Scene Node + Tween's production transport first, preserve the existing checkout and local work, and keep the unresolved rendered and abrupt GameState-loss boundaries explicit.
