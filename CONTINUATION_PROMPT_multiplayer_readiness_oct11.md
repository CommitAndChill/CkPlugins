# One-line summary

Continue applicable CkPlugins gyms, autotests and other tests for ClientServer and ListenServer, in this checkout, with much less parallel preparation; finish VoxelNav Flying Vs Grounded next.

# Repo state

Verified 2026-10-11 in D:\Repos\CkPlugins_3. Host, CkTests and CkFoundation use branch feature/multiplayer-test-readiness; all three indexes empty.

| Repository | HEAD | Dirty status entries |
|---|---|---:|
| Host | 434f81df03becb64674a4fd08d699c73dbd2d4da | 11 before this handoff |
| Plugins/CkTests | dc4818ca2b40436748fe01373f0fc02b583df9b6 | 447 |
| Plugins/CkFoundation | 367ff2d5973ae1d5b4e78b385707f65985e65da7 | 24 |

Preserve all existing dirt: much belongs to earlier migration work, not necessarily unrelated or finished. Especially preserve the untracked Source/CkTests/Private/Net/CkAutoTest_MultiplayerCorpus.spec.cpp. No push or host-pointer update has been performed for recent slices. Git metadata lives outside the writable checkout, so git operations may need escalation. Use exact path/hunk staging and scoped identity Saad K <saadrustam@gmail.com>.

Latest CkTests commits: 541f564782bacfb5a2e645b2fd8f37e44557c39c adds the MP selector pill; dc4818ca2b40436748fe01373f0fc02b583df9b6 completes the main seven-station GOAP bank. Earlier StateMachine, Chain, Dialog, EQS, GoapAutoReplan, Empire and FEAR slices are committed and have focused evidence in status.json. Do not reopen completed work without new evidence.

No UnrealToolbox process was present at handoff; the last run is archived and source/index are unfrozen. All old workers are completed or interrupted. VoxelNav work is SCRATCH ONLY, neither applied nor compiled. This document supersedes the older CONTINUATION_PROMPT_multiplayer_readiness.md.

# Active bugs or open questions

User: "For some gyms, it may not make sense to make them multiplayer ready. So skip those." Seventeen rendering/performance exclusions are recorded in .scratch/multiplayer/render-showcase-skip-oct11.md and status.json gymScopeOct11. Input Playground and moving remote-pawn Rope behavior are deferred until a separate proper network-ready CkFoundation Jolt Character effort. Do not add a pose RPC workaround. The committed shared Chain bank stays.

The user explicitly requested this fresh chat to reduce usage: "Save a concise handoff, start a fresh chat with a $continuatio-prompt, and ask the new conversation to do less parallel preparation." Work one bounded family end to end; no broad inventories or advance work on later families. Default to no more than one tightly scoped implementation/review worker, only when it saves total work. Use narrow reads and compact output. Earlier Astra Ultra preferences are stale; user described current setting as Sol High. Do not change model unasked.

MP means an authored multiplayer component, not readiness certification. There are 35 annotations. Architecture classification is 36/92 registered gyms (31 shared + 5 local/other), with 56 outside classification; 17 exclusions are separate. These are NOT completion percentages. Broader gym and non-gym certification remains.

# Why prior fixes or investigations were insufficient

Extended context, multiple workers, repeated source/log reading and preparing future families consumed usage. Stop repeating inventories, broad audits or equivalent boots. Previously completed focused gates cannot certify the entire dirty repository.

VoxelNav prototypes still need integration and a real network fixture. A source-forest helper initially assumed agent roots were direct world children; this is fixed in the CURRENT previews, not the older source patch. The usageSteeringOct11 status field may retain that obsolete blocker; the handoffTransferOct11 field and this note supersede it.

# Available diagnostics and the first evidence to collect

Read only selected status.json fields: goapMainAndSelectorDeliveryOct11, gymScopeOct11, handoffTransferOct11. Verify current HEAD/index and active Toolbox state before editing.

Latest evidence: .scratch/multiplayer/goap-main-badge-oct11-green-evidence.json. Incremental DebugGame Editor build succeeded; 8/8 physical tests passed across main GOAP, FEAR, Empire and AutoReplan in both modes, using one discovery and two runtime editor boots. Archived logs have no script errors, ensures or protocol errors; ordinary Iris warnings remain. NullRHI only: selector pixels were not inspected. Current integer-crowd-final-gate-manifest.json contains 810 entries. Do not overwrite archives or rerun completed commit helpers.

# Likely symptoms, causes and files

| Symptom | Likely cause / starting point |
|---|---|
| Agent forest rejected | Use current runtime TryGet_AgentForest(SourceRoot, AgentRoot, WorldRoot, out), not direct-world-child census |
| Busy control becomes a failure | GameState must retain previous complete frame while source replaces/reverses the pair |
| Initial source fails before bake | Wait for Get_IsBuilt before Request_StartPrepared/UpdateControl |
| Client has no moving bodies | Existing movers are not replicated; proposed controller renders passive value frames |
| Incorrect or duplicated restart | Check pair generation, control receipt and physical old-pair retirement |
| Claimed readiness exceeds evidence | MP annotation and architecture coverage are not certification |

# Critical files

Paths below are relative to this checkout.

1. AGENTS.md and applicable nested framework guides: safety and engineering requirements.
2. .scratch/multiplayer/status.json: selected delivery, exclusion and handoff fields.
3. .scratch/multiplayer/voxelnav-flying-grounded-inventory-oct11.md: authored two-agent scene.
4. .scratch/multiplayer/voxelnav-flying-grounded-source-preview-oct11/CkVoxelNavGym_FlyingVsGrounded_Source.as: CURRENT source proposal.
5. .scratch/multiplayer/voxelnav-two-root-preview-oct11/: current native Wire.h, Runtime.h and Runtime.cpp proposals.
6. .scratch/multiplayer/voxelnav-flying-controller-oct11.patch: controller/GameMode proposal; full PC also in corresponding .as.txt.
7. .scratch/multiplayer/voxelnav-flying-gamestate-layout-oct11.patch: GameState/layout proposal; full files also in voxelnav-flying-{gamestate,layout}-oct11.as.txt.
8. Plugins/CkTests/Source/CkTests/Private/UnitTests/CkGoap/Test_GoapFEARGym_SharedWorld.spec.cpp: reusable real travel/owner/reflection/retirement fixture.
9. Plugins/CkTests/Script/Common/CkTests_GymRegistry.as: registration and authored MP flags.
10. .scratch/multiplayer/launch-focused-run.ps1 and watch-focused-run.ps1: approved Toolbox launch/monitor helpers.

# Things ruled out

No new worktrees, clones, mirrors, repository copies or alternate checkouts, including verification/delegation. Do not repurpose existing duplicates or delete Binaries, Intermediate, DDC or build artifacts. No local character-pose networking band-aid. No complex creator ledger; reuse existing validated census helpers. Do not replicate SceneNode merely to move an entity.

InputKeyBinding and GameSettings stay local/unmarked; RenderTarget has a real replicated whiteboard and stays MP. ProjectilesLagComp currently demonstrates local synthetic lag and is not MP. Historical CK first-packet/PIE descriptor issues were investigated; consult evidence before reopening engine changes.

# Architecture notes and gotchas

VoxelNav uses one authority source, one persistent baked volume and two agents: flying (-1000,-400,1000) and grounded (-1000,400,1000), initially heading to X=1000. R replaces both agents against the same volume while preserving direction; T reverses both goals. No player-pose dependency. Leave Stress and Foundation untouched.

Current source supports prepared/build/start lifecycle, exact build and movement receipts, physical old-pair retirement, terminal blocking and bounded waypoint frames (128). Native runtime now validates the complete source forest, then derives agent descendants; source preview calls that new API and checks MoveEpisode overflow. The older voxelnav-flying-grounded-source-oct11.patch is STALE: use the current preview. voxelnav-two-wire-runtime-oct11.py can regenerate the three current native previews.

Empty FInstancedStruct() is supported. Do not call UpdateControl while unbuilt; start once after build and poll until started. During R/T, TryGet_Frame may temporarily fail: retain busy values instead of failing the session. Recast readiness needs a positive check, not merely voxel-bake completion. Proposed GS reuses the EQS fixture/provider approach and restores provider on EndPlay. Worker static review found no API mismatch, but nothing has compiled. Passive visuals begin after the first complete baked frame; pre-bake progress is not displayed.

Keep source simulation on authority, client presentation passive, controls owned and sequenced, and failed admission terminal/atomic. Validate prerequisites independently; CK_ENSURE is diagnostic only and must have a separate ordinary failure return. Factory callbacks can be synchronous: retain receipts first.

# Concrete diagnostic and verification flow

1. Read this handoff and applicable instructions, do the required brief model/effort check, then inspect only current VoxelNav proposals and production APIs they call. Do not repeat the completed breadth audit.
2. Review GS/controller against current source/native previews; verify Get_SourceRoot(int32 Index) exists for native testing. Integrate exact owned files, preserving all unrelated changes. Add the MP registration with the delivered component.
3. Write a focused production-path native fixture for ClientServer and ListenServer, using actual gym travel and two owner clients (plus listen host). Prove one authority volume/two agents, passive matching owner frames, R/T controls, fresh receipts, physical old-pair cleanup, malformed/stale requests rejected without mutation, and terminal source-loss cleanup. Reuse existing boilerplate rather than building another framework.
4. For movement proof, issue R after all owners are ready, then observe fresh flight/climb/pitch versus grounded movement; startup motion may otherwise finish before observation. R preserves source/volume identity and direction; T preserves pair identity and reverses goals.
5. Normalize formatting/line endings and extend the 810-entry manifest only for owned paths. Read build-test skill. State the editor boot budget before launch (aim one discovery plus one runtime boot; explain evidence if more are necessary).
6. Build/test ONLY through CkAuto/UnrealToolbox.exe with --project=D:\Repos\CkPlugins_3. Launch detached with PowerShell Start-Process -PassThru -WindowStyle Hidden, request GUI escalation, retain the progress window, never pass --no-progress-window. Monitor PID and output; never launch a duplicate after timeout. C++ requires incremental build; AS-only changes reuse binaries.
7. Freeze source/index during the gate. Verify physical rows and fresh logs, archive exact evidence, then commit independent buildable slices with precise staging. Do not claim full-suite validation. Continue applicable families sequentially; defer architecture-dependent gyms and maintain explicit exclusions. Escalate material product/architecture decisions only.

# Suggested first message

"I'm continuing in the existing checkout with one bounded family at a time. I'll review the saved VoxelNav proposals, finish their network fixture, and run a focused gate; broader preparation stays stopped."
