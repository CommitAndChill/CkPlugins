> **Superseded:** Start with [the current Oct12 handoff](CONTINUATION_PROMPT_multiplayer_readiness_oct12.md). The paused draft below is historical; Scene Node now has focused 50/50 post-rebase evidence.

# One-line summary

Continue CkPlugins production multiplayer readiness, one bounded family at a time: six families are verified/committed locally; Scene Node has an approved CkFoundation API extension and substantial **unbuilt, untested draft changes now committed and published for transfer**. The user explicitly stopped implementation because usage was running out. Resume Scene Node integration and verification first, then the remaining transport reviews.

> **Publication update:** The user subsequently requested committing and pushing all current work, including this handoff, for another machine. The approved Scene Node draft remains unfinished and unverified, but its edits and the other existing changes are preserved in explicit transfer commits on feature branches. The repo-state table below records the pre-publication snapshot; use the current checked-out HEADs and Handoff/MultiplayerOct11/publication.json for delivered revisions. Portable evidence is tracked under Handoff/MultiplayerOct11; references below to .scratch/multiplayer/<included filename> map there on the receiving machine. Raw old editor logs remain on the original machine. Resolve absolute paths against the receiving checkout. No new build, test, merge or implementation is part of this transfer.

# Repo state

Work only in `D:\Repos\CkPlugins_3`, in place. Never create or repurpose another checkout, worktree, clone, mirror or repository copy. Do not delete/recreate Binaries, Intermediate, DDC or generated build artifacts. Existing other checkouts are user data; do not touch them.

Freshly verified at this handoff:

| Repository | Branch | HEAD | Index |
|---|---|---|---|
| CkPlugins host | feature/multiplayer-test-readiness | 434f81df03becb64674a4fd08d699c73dbd2d4da | Empty |
| Plugins/CkFoundation | feature/multiplayer-test-readiness | 45323922ce3fca25dbc764bf473b68f9964a5412 | Empty |
| Plugins/CkTests | feature/multiplayer-test-readiness | 4417f861bf8d79f063e0225a10522a7e944a6e73 | Empty |

The table above records the pre-publication baseline. The user subsequently authorized all-current-work publication: CkFoundation dff47a5ae2aa5dcce8636ad34e2c8236b5f3fb8e, CkGameplayDebugger ac58b24e2c62bddf899b69bd5af476fdef062574, CkTests 4e785fc759c5eb9fec5d372424810fd18b9009a3, and CkAuto1faafede4d062d0e534f06edb537bbe88d58e854 were pushed and remotely verified. Host runtime/configuration/gitlinks are committed in4cccaec58df65ce2c1a4a00cc31ee959c007322b; the commit containing this handoff is the receiving host revision. Read Handoff/MultiplayerOct11/publication.json. No new runtime verification occurred. The user approved command-scoped Git identity `Saad K <saadrustam@gmail.com>`; use it for authorized scoped commits without changing global configuration. Original continuation step7 authorizes coherent, buildable local commits after verified gates. Never stage a whole dirty repository. Never put assistant/model/vendor/tool attribution in Git metadata.

Host dirt preserved: Config/DefaultGameplayTags.ini, Script/Generated/CkPlugins_EntitySpawnParams.as, Script/PlaceableTests/PlaceableTests_EntityScripts.as, untracked AutomationGate.json and earlier continuation prompts. Both plugins have extensive unrelated dirty work; especially preserve untracked `Source/CkTests/Private/Net/CkAutoTest_MultiplayerCorpus.spec.cpp`. Submodule Git metadata is outside the sandbox root; even read-only Git may require escalation. Root status can use `--ignore-submodules=all` to avoid that permission failure.

**No active Toolbox/editor for this project was found by fresh escalated CIM inspection. Saved/Logs/CkPlugins.log was unlocked. status.activeRun=null and sourceFrozen=false. No source/index freeze is active. No Scene Node gate has run; the draft is included in the published CkTests checkpoint history, not certified complete.**

The old `CONTINUATION_PROMPT_multiplayer_semantics_oct11.md` is historical: its frozen VoxelNav run was already reconciled and its old HEAD/run information is stale. Do not redo those steps.

Verified completed slices (each has focused evidence; none implies repository-wide readiness):

| Family | Local commit | Final focused evidence |
|---|---|---|
| VoxelNav | CkTests 1af8bf48f72e306c1e8f717add9bd02795bd7e3c | 4/4, production Transform; voxelnav-production-transform-oct11-green-evidence.json |
| GOAP main | CkTests 88be497ef3d5aa3f4a2940e2d4ecab169e1d5a12 | 1/1 local demo; goap-main-local-oct11-green-evidence.json |
| Transform | CkTests 5728190f49b79e4c18fdb618480fedc0f53eb073 | 2/2; transform-production-oct11-green-evidence.json |
| Sway | CkTests 41d2907a48acf760dd0b02a22d0bf886bf4595ef + CkFoundation 45323922ce3fca25dbc764bf473b68f9964a5412 | Sway2/2 + component compatibility2/2; sway-production-oct11-green-evidence.json |
| Replication | CkTests 3036139e83d85b55f32cc21b8bf5ce51280f615c | 2/2, production IntegerAttribute/all-pawn receipts; replication-production-oct11-green-evidence.json |
| Rotate Towards | CkTests 4417f861bf8d79f063e0225a10522a7e944a6e73 | 8/8; rotate-production-oct11-green-evidence.json |

Evidence paths above are under `.scratch/multiplayer/`. Registry ledger `.scratch/multiplayer/production-transport-review-oct11.json` has92 rows:6 verified,86 pending. GOAP main is explicitly **local-only and excluded from multiplayer readiness**, by user decision. Six GOAP variants remain pending. Historical31 shared/5 other/17 local-render classifications are not verification under the corrected criterion. Input Playground/moving Rope remain deferred for proper Jolt Character networking, without pose workarounds.

## Scene Node in-flight ownership

Exact path manifest: `.scratch/multiplayer/scene-node-inflight-owned-oct11.json`. It separates this-turn edits from pre-existing related gym infrastructure. Review both for a coherent eventual family commit, while preserving all unrelated dirt.

Foundation this-turn edits: `Source/CkEcsExt/Public/CkEcsExt/SceneNode/CkSceneNode_Utils.h` and `.cpp` only. Fresh diff stat88 insertions/15 deletions; header diff was wholly this API change.

CkTests worker changed17 paths:
- Public/CkSceneNodeGym_ActorLedger.h and Public/CkSceneNodeGym_EcsRoots.h.
- Private/CkSceneNodeGym_{ActorLedger,EcsRoots,NodeGraph,Motion,FrameSampler,Retirement}.cpp.
- Private/UnitTests/CkEcs/CkSceneNode_{ActorLedgerProbe,EcsRootsTestAccess,RetirementTestAccess}.h.
- Private/UnitTests/CkEcs/Test_SceneNode_{ActorLedger,EcsRoots,NodeGraph,Motion,StopReceipt,TimerCaptured}.spec.cpp.

Lead changed8 CkTests paths:
- Script/CkSceneNode/CkSceneNodeGym_{GameState,Shared,SourceVisuals}.as.
- Public/CkSceneNodeGym_RemoteVisuals.h and Private/CkSceneNodeGym_RemoteVisuals.cpp.
- Private/UnitTests/CkEcs/Test_SceneNode_RemoteVisuals.spec.cpp.
- NEW Private/UnitTests/CkEcs/Test_SceneNode_ExistingTransformAnchor.spec.cpp.
- Private/UnitTests/CkGym/Test_SceneNodeGym_ProductionTwoOwner_Network.spec.cpp.

Related pre-existing dirty gym infrastructure, not edited this turn: Script/CkSceneNode/CkSceneNodeGym_{GameMode,PlayerController,Catalog,StationCohort}.as. GameMode/PlayerController are tracked modified; Catalog/StationCohort and the lead's GameState/Shared/SourceVisuals/Remote native/tests are untracked. Native source-side worker paths are tracked.

The obsolete, previously untracked `Script/CkSceneNode/CkSceneNodeGym_RemoteVisuals.as` was removed. Its native clone actor type was removed from RemoteVisuals.h/.cpp. A narrow search found no remaining SceneNode references to RemoteVisualActor/RemoteParent/RemoteChild. Do not restore clone transport to satisfy stale tests. Legacy local Cube/ChildCube demos are separate and untouched.

# Active bugs or open questions

User's criterion:
> "VoxelNav should work as a Client as well, and I should see the Agents moving. But the only reason I should see them move is because transform is replicated. Not because VoxelNav is replicating."
> "This same logic needs to be applied to all other gyms. And, we need to make sure previous work was done correctly as well."

Scene Node original transport was six authority roots + eleven SceneNodes -> FrameSampler17poses -> replicated Snapshot.WorldPoses -> seventeen locally spawned nonreplicated client actors. Its native admission deliberately rejected replication. This was a confirmed mismatch.

**CTO approval is already granted; do not ask again.** The user answered “Approve the bounded SceneNode API extension (Recommended)” to the exact proposal in `.scratch/multiplayer/scene-node-production-api-proposal-oct11.json`. Recommended scope:17 existing actor-backed WithActor Transform identities, movement replication disabled, original authority graph retained, foreign-component AnchorOffset preserved through one bounded public SceneNode composition API. Role0 scope becomes identity-only replicated, still18 actors total. There is no unresolved approval question.

Current draft needs integration review before any build. Specific known/unresolved issues at stop:

1. **Remote unknown census currently checks only direct Actor.Owner==scope.** It must reject unknown nested descendants/cycles safely without rejecting unrelated pending actors. HasNoUnknownDescendants in RemoteVisuals.cpp is the starting point.
2. **Unknown rejection occurs after applied-output readiness in TryInstall.** A transient pending Transform apply can return false before recording unknown closure; the new UnknownClosure test may therefore be timing-sensitive. Separate structural rejection from legitimate production-apply waiting. Frozen metadata sequences also need a deliberate path to close/hide on structural loss; the final conformance branch in GameState currently merely returns. Do not add pose writes or retry hacks.
3. **Retirement absence proof currently uses LiveActor, which excludes IsActorBeingDestroyed.** This may certify absence before physical level removal. Require actual captured actor-serial absence and ECS deallocation, including pending-kill state. Do not require valid source GS merely to observe a retained receipt's past identities.
4. **Visibility implementation is partial.** Source AS mesh/text defaults are now invisible; first valid authority publication shows exact finished roles, TryBegin client receipt shows exact source actors, Request_Retire/Fail hides captured owned components only. Request_CloseKnownProducers currently closes sampler/motion/ledger but does NOT hide authority visuals. Review intentional source presentation on failure. No client/gym pose writes are allowed. Request_SetVisualVisible changes only components owned by the exact captured SourceActor, without propagating visibility to foreign attached components.
5. **Remote public Get_State is BlueprintPure yet const_cast updates Retiring->Complete.** Review API/readiness side effects and avoid hiding or altering gameplay from an ostensibly pure helper without a deliberate contract. The current Get_IsInstalledConformant is pure/read-only and does not automatically latch frozen-sequence structural failures.
6. **Client pre-admission timeout:** TryBegin returns null while source metadata/owners/driver applies arrive; GameState `_RemoteAttempted` latches only after a receipt exists. There is no explicit elapsed bound on that initial wait yet. Existing native gate timeout can expose missing construction, but decide whether product admission needs a retained deadline/failure reason. Do not manufacture client PendingRetry callbacks just to silence warnings.
7. **Compile compatibility is wholly unverified.** New seam test uses actual SourceChild AS class and native WithActorScript Replicates; TryAddCaptured/self ContextOwner, force refresh and raw carrier drainage. Check UHT/AS method bindings, delegate/function signatures/includes and new declarations. A missing Request_SetLocation third delegate was corrected to `{}` before stop; no compile has confirmed it.
8. **Production fixture coverage gaps:** it now checks actual applied L/R/S, root bridge/mesh equals client ECS, per-generation authority histories and two frame matches for17slots, moved matches for eleven node roles, old handles deallocated before replacements. It does not yet assert IsVisible, distinct new-vs-old entity identities explicitly, no client timers explicitly, or abrupt GameState-loss behavior. Do not claim these until tests prove them. History stores at most512 source poses; inspect whether this is enough for existing timing and whether witnesses count distinct moved updates meaningfully.
9. Worker risks: EcsRoots unit test assumes all17 request carriers are allocated immediately after TryBegin (population+35); source Motion retirement reentrant unknown-actor case now expects17 production visual actors gone with scope/unknown retained; FrameSampler expects actor output==ECS at OnWorldPostActorTick. These need real gate evidence, not count-only review.
10. No compile, runtime test, source-wide normalization, final owned hash freeze or staged diff review has been done for Scene Node. Worker only checked CRLF/no BOM for its17 files. No readiness ledger decrement is justified yet.

# Why prior fixes or investigations were insufficient

A green custom-snapshot fixture can prove that clients draw moving pictures while entirely bypassing production Transform replication. Each family's actual production state must be the tested transport. Keep lifecycle/control/text/solver diagnostics where justified; remove pose/state substitutes that conceal missing feature delivery.

Simply enabling replication would leave source actor, ECS root/node, carrier, exact graph and retirement admission incompatible. The draft adapts those proofs as one family. Replacing AnchorOffset with ordinary parent-driven SceneNode::Add would change its foreign-component semantics; that is why the approved API exists.

The current implementation is a draft, not a fix claim. Source review and Astra advice found several issues and three API fixes, but no build/test has run to establish correctness.

# Available diagnostics and the first evidence to collect

Start by rereading the actual draft diff and the pending issues above. Both prior agents have stopped; `/root/transform_trace` (Sol medium) completed native/source-test work and `/root/voxel_topology` (Astra high) completed bounded read-only API/ownership/lifetime reviews. Their process state does not imply ongoing edits. A fresh session should use a compact brief rather than depend on these agent contexts.

- `.scratch/multiplayer/status.json`: huge; parse only activeRun/sourceFrozen/productionTransportReviewOct11. Do not dump100k tokens or overwrite unrelated fields.
- `.scratch/multiplayer/production-semantics-PROGRESS-oct11.md`: compact current stop state.
- `.scratch/multiplayer/scene-node-production-api-proposal-oct11.json`: approved architecture and source evidence.
- `.scratch/multiplayer/scene-node-inflight-owned-oct11.json`: exact ownership/provenance boundary and frozen-at-stop hashes.
- `.scratch/multiplayer/production-transport-review-oct11.json`: remaining92-row review ledger.
- Per-family completed green evidence JSON files listed above, plus archived raw editor logs under .scratch/multiplayer.
- Latest completed output `Saved/Logs/MultiplayerRotateTowardsStaticPhaseOct11.log`:8/8, native build passed prior iteration, one final AS-only boot. Raw archive `.scratch/multiplayer/RotateTowardsStaticPhaseOct11-Editor.log`; it contains two expected UnknownChild rejection messages, not unexpected errors. Five observed Rotate family boots total.

Scratch code-generation helpers have **already been applied**. Do not blindly rerun `edit-scene-node-as.ps1` (non-idempotent), or copy the `scene-node-remote-production.*`, `scene-node-remote-tests.cpp`, `scene-node-existing-anchor-test.cpp` templates over production files: some templates are older than final in-flight edits. Production files and actual diffs are authoritative.

# Likely symptoms, causes and files

| Symptom | Likely cause / files |
|---|---|
| No client receipt/visuals despite Active metadata | Actor source/gen/role/Owner cross-channel arrival or actual driver apply; ActorLedger, RemoteVisuals, GameState |
| Foreign anchor initial ECS pose correct, actor/driver still old | Lost Updated tag across next-frame cleanup; new API must retain queued ForceRefresh |
| Anchor pose accumulates offset every frame | Anchor belongs to or is attached beneath output actor; API attachment-cycle/same-owner guard |
| Pending-kill dependent admitted as leaf | Default ck::IsValid excludes pending kill; use IncludePendingKill for allocation/history proofs |
| Parent or child graph admission fails | Native roots17 slot ordering, exact direct parent/record, preconstructed node Transform, raw stale carriers; EcsRoots/NodeGraph |
| A generation never retires |41 known handles,17 script carriers, production owning-actor teardown, scope physical absence; Retirement, RemoteVisuals |
| UnknownClosure test flakes or frozen clients retain pictures | Unknown structural checks ordered behind transient driver readiness or not latched at same sequence |
| Native history matches but images not visible | Source defaults now hidden; explicit full-cohort visibility promotion missing or untimed |
| Focused old tests reject every actor immediately | Stale nonrep CDO expectations or wrong scope class; source unit tests/probe headers |
| Build passes but gate is false green | Fixture still measures metadata, missing visibility/no-client-simulation/replacement identity witnesses |
| No Error-severity log entry, but gym failed | ck::Error is colored PrintString; inspect raw LogBlueprintUserMessages, not just filtered Toolbox output |

# Critical files

1. `Plugins/CkFoundation/Source/CkEcsExt/Public/CkEcsExt/SceneNode/CkSceneNode_Utils.h/.cpp`: new approved TryAdd_AnchorToExistingTransform and common guarded composition/rollback.
2. `Plugins/CkTests/Source/CkTests/Public/CkSceneNodeGym_ActorLedger.h` + Private counterpart: exact18 actor identities, replicated scope and visual metadata.
3. `Plugins/CkTests/Source/CkTests/Public/CkSceneNodeGym_EcsRoots.h` + Private counterpart:17 actor-backed WithActor target/captured-carrier admission and self ContextOwner.
4. `Plugins/CkTests/Source/CkTests/Private/CkSceneNodeGym_NodeGraph.cpp`: original11-node parent/lifetime graph; node10 foreign anchor API.
5. `Plugins/CkTests/Source/CkTests/Private/CkSceneNodeGym_FrameSampler.cpp` + Retirement.cpp: source-only pose oracle,41-history closure, production17-actor teardown.
6. `Plugins/CkTests/Source/CkTests/Public/CkSceneNodeGym_RemoteVisuals.h` + Private counterpart: actual client replica binding, metadata receipts, visibility and retained retirement evidence; contains pending risks.
7. `Plugins/CkTests/Script/CkSceneNode/CkSceneNodeGym_GameState.as`, Shared.as, SourceVisuals.as: metadata-only snapshot, source/control lifecycle, hidden-before-admission source actors.
8. `Plugins/CkTests/Source/CkTests/Private/UnitTests/CkGym/Test_SceneNodeGym_ProductionTwoOwner_Network.spec.cpp`: real CS/LS, two owners, generations1->2->3, control isolation/local station identities, actual Transform witnesses.
9. `Plugins/CkTests/Source/CkTests/Private/UnitTests/CkEcs/Test_SceneNode_ExistingTransformAnchor.spec.cpp`, Test_SceneNode_RemoteVisuals.spec.cpp and source-side SceneNode tests: new seam, unknown/unrelated client failure handling, adapted exact lifecycle proofs.
10. `CkAuto/.claude/skills/build-test/SKILL.md` and `.scratch/multiplayer/launch-focused-run.ps1`, watch-focused-run.ps1: actual available build skill/launch helpers. Advertised .Codex wrapper target is absent here.

# Things ruled out

- No gym pose snapshot/RPC, client clone or parallel client SceneNode/timer simulation substitutes for Transform replication.
- No low-level Request_Replicate(existingHandle, GameState bridge) or restore API misuse: generic direct lifetime owner/driver rules matter.
- No private gym insertion of framework replication containers or UnrealAnchor fragments to evade a missing public API.
- No second API for enabling replication on an existing Transform is needed in chosen route: all17 outputs use existing WithActor AddAndAttach production composition.
- A nonreplicated Actor.Owner scope **does not block visual WithActor construction**. Replicated role0 scope is for client provenance, not a construction workaround. Rootless scope requires bAlwaysRelevant.
- SceneNode::Add on the other10 existing Transform nodes has no Transform-OnAdded callback. The old same-call reentry test was renamed ActorLossAfterComposition; no new test/public hook was introduced. Do not claim preserved same-call callback coverage.
- Source loss deliberately means non-destructive quarantine, not automatic arbitrary cohort destruction. Reparenting lifetime to get GameState cascade would be a new architecture decision and is not authorized by the approved proposal.
- No full-suite/regression-free claim from focused green evidence; no renderer claim from NullRHI.

# Architecture notes and gotchas

## Approved Scene Node data flow

Authority: plain generationOwner under WorldRoot; six root targets + eleven node targets with original structural/lifetime parents, all backed by the existing17 SourceActors. Existing role0 scope is native `ACk_SceneNodeGym_ScopeActor_UE`, replicated/always relevant, movement off, no ECS script, Owner=GS. SourceActor metadata Source/gen/role replicated and assigned before FinishSpawning, movement off, registered subobjects enabled. Native script `UCk_SceneNodeGym_WithActorScript_UE` reports Replicates. Node10 follows a genuinely foreign Unreal component while output remains its own root bridge. Other10 use ordinary SceneNode::Add with preflight and whole-cohort fail-closed admission.

EcsRoots slots:0..5 six roots,6..16 eleven nodes. Root actor roles1,3,5,10,13,16; node roles2,4,6,7,8,9,11,12,14,15,17. All17 targets retained before composition; captured17 request carriers.35 initial creation identities=owner+17target+17carrier;41 retirement identities adds6 timers.24 live roles remainsowner+17target+6timers. Actors remain18 including scope.

Each fresh target inherited lifetime/context/net state. Clear the same four net fields as public generic spawn, override ContextOwner to self, then TryAddCaptured. Carrier request stores Owner/ContextOwner=direct lifetime Parent by design; construction processor reads live target override and self-owned WithActor replication omits external context override. WithActor special actor-order admission permits requesting children before parents have constructed Transform; NodeGraph begins only after all17 completed and carriers deallocated.

Authority WithActor replication is self-owned on its own Actor. Client production reconstruction places entity under local WorldRoot; **do not require authority-only generationOwner or scene lifetime chain on clients**. Client source/gen/role Actor metadata + scope->GS + exact owning actor/driver entity identity is the provenance contract. Owner reference arrival can lag driver construction; tolerate arrival order.

New API shares guarded parent-chain/record/numeric preflight with fresh-anchor path. Existing mode requires Transform+Previous, exact movable own actor root bridge, no existing SceneNode/anchor/record/layers, no allocated dependents including pending kill. Deallocated lifetime carrier history may remain. Reject same actor foreign anchor and attachment chains reaching output actor/root, malformed/cyclic/unregistered/cross-world anchors. Stage only new SceneNode fragments, roll them back on record failure while retaining original Transform/Previous/bridge/replication features. After success add ExternallyDriven, direct-write seed + Updated and canonical ForceRefresh queue. Existing fresh-anchor behavior remains unchanged.

Astra API review found and lead fixed: IncludePendingKill leaf proof, foreign-anchor feedback through own attached components, and late-frame initial publication loss. These fixes are source-reviewed only, not compiled/tested.

SceneNode FollowUnrealAnchor reads foreign component/socket and writes ECS Transform; Transform SyncToActor pushes actual own root. ExternallyDriven suppresses SyncFromActor overwriting foreign input. Sway's already committed component push fix runs after Camera/before PostTransform and has dirty marker FTag_Transform_Updated; preserve it, do not restore conflicting group membership.

Runtime client binding currently scans exact source/gen/role production Actor identities once a complete cohort is ready; it creates only a local receipt component. No clones, entity creation or SetActorTransform. Snapshot WorldPoses removed. Native FCkSceneNodeGym_Frame.WorldPoses remains a **source-only oracle**; client metadata-frame factory rejects any nonempty poses. Solver/display text and R ownership remain legitimate diagnostic/control transport.

## Source loss contract

GameState Request_Fail/EndPlay closes sampler/motion/ActorLedger and explicitly has no destructive fallback. Retirement interrupted by SourceEndPlay becomes Unproven and retains creator IDs/source claim. Existing Motion tests cover known visual loss and foreign descendants, requiring inert retained producers/unknown members. They do not prove abrupt GameState destruction. Client visibility closure may hide only precisely known components, never write poses/destroy/adopt actors. Mark retirement complete only after actual absence. Automatic lifetime reparenting/destruction needs separate CTO scope approval.

## Workflow constraints

Main thread settings were user-confirmed Sol/medium. Opening recommendation already given once in this conversation; fresh session follows its applicable opening rule. Explicit tiered-delegation invocation and user AGENTS permit lowest-cost capable scoped work; at most one ordinary worker, except a required bounded Astra consultation. Use Sol medium for bounded implementation, low for inventory; Astra high for unresolved consequential architecture/replication/lifetime after focused reads, xhigh before a third attempted fix of the same surviving symptom. Advice is not verification. Main lead retains decisions/integration/final proof.

Read current AGENTS/framework guides and applicable skills. Actual docs previously found include CkFoundation/CLAUDE.md, Source/CLAUDE.md and Source/CkEcsExt/Claude.md; advertised Script/AGENTS.md was missing. Do not guess stale guide paths.

Batch independent functions.exec tools with Promise.allSettled and inspect each result. Keep source mutations/approvals/dependencies sequential. rg first; PowerShell cannot pass literal wildcard file paths to rg as if shell-expanded. Python WindowsApps alias is unavailable; use PowerShell or apply_patch. Set-Content defaults can alter BOM/line endings; normalize owned files to CRLF UTF8 without BOM before final gate. Avoid mechanical whole-repo normalization.

Unreal gates only via detached `CkAuto/UnrealToolbox.exe`, absolute `--project=D:\Repos\CkPlugins_3`. Never raw Build.bat/UBT/UnrealEditor-Cmd, never `--no-progress-window`. Before launch state planned editor-boot count and reason. C++ changes require incremental build, editor closed. Native build/discovery may entail2-3 boots; AS-only cached serial gate can be1. Tests pattern ANDs dotted tokens, no OR. Explicit --serial-lane=<dotted segment> and --parallel=1; otherwise parallel lanes may appear. Do not launch duplicate after timeout; monitor existing PID/output. Escalated GUI Start-Process required; -WindowStyle Hidden hides parent console only, progress remains visible.

Freeze all source and Git indexes from launch until verified process exit/log unlock/frozen hashes. Inspect physical pass/fail/skipped/contaminated counts, fresh raw Saved/Logs/CkPlugins.log, touched-AS warnings, compile errors, ensures, dirty-pump limits/new marker conflicts. Raw ck::Error is colored PrintString/LogBlueprintUserMessages and absent from filtered Toolbox error summaries; archive raw log before next boot. Existing unsolicited primary WithActor display PendingRetry expiries are a separately documented framework callback-bookkeeping limitation; distinguish family spawn failures by exact script/source rather than sweeping them away.

# Concrete diagnostic and verification flow

1. Read this prompt fully, current instructions and approved proposal. Verify HEAD/indexes and no active Toolbox/editor again. Preserve unrelated work. User stop was intentional; only resume implementation when this prompt is explicitly used to continue.
2. Inspect exact manifest/diffs. Reconcile the17 worker native/source-test paths with the lead's8 paths and four pre-existing related AS files. Do not restore stale scratch templates. Check31 candidate integration paths, not the entire repository.
3. Finish bounded RemoteVisuals/GameState integration: structural unknown closure (nested/cyclic), legitimate transient driver wait, frozen-sequence failure latching, physical actor+ECS absence, visibility promotion/closure, role0 world/source identity and public helper semantics. Do not add pose transport or automatic destructive quarantine recovery.
4. Validate Foundation API total/atomic paths and preserve fresh-anchor behavior. ExistingTransform seam test covers null/default/own-root/own-child/foreign-attached/unregistered/static/cross-world/unsafe offset/allocated+pending-kill-dependent rejection, duplicate rejection, late-frame stationary-anchor initial push and independent anchor/parent movement. Confirm its assertions and signatures compile; add genuine missing state invariants as needed.
5. Review production fixture: all17 actual source actors per world, client actual driver L/R/S ever-applied/no pending/native ECS equals applied, actual root/mesh equals ECS and fresh same-generation authority history on two frames, eleven moving node witnesses, generations1->2->3 old deallocation/new identities, no client SceneNode/timers, visible state, actual owner controls/stations and normal retirement. Abrupt-source quarantine must be explicitly tested or explicitly unclaimed. Preserve unknown-closure and source-side exact fail-closed tests.
6. Review worker source tests for exact17 targets/17 carriers/41 history and unchanged6 timer/root counts; check immediate-carrier timing and reentrant unknownActor expectations. Do not weaken production invariants merely to turn old probes green. Consult bounded Astra if material uncertainty remains; same failure twice means consultation before third edit.
7. Normalize exact owned files, construct final hash manifest and ensure indexes remainempty. Choose a focused compatible test inventory. Likely relevant prefixes: Ck.SceneNode.Network.Gym.ProductionTwoOwner (CS/LS), Ck.SceneNode.Network.ExistingTransform.ForeignAnchor (CS/LS), Ck.SceneNode.Network.PreallocatedAnchor.FreshLeaf (compatible existing API), Ck.SceneNode.Network.Gym.Remote.UnknownClosure/UnrelatedPending and the changed source-side SceneNode tests. Inspect actual declared names/pattern matching to avoid unintentionally pulling SceneNode+Tween future family. Do not claim a gate that omits changed source-side tests.
8. State boot budget, then one incremental --build --test focused invocation when integration is complete. Launch through escalated PowerShell:
   `Start-Process -FilePath '.\CkAuto\UnrealToolbox.exe' -ArgumentList <arguments including --project=D:\Repos\CkPlugins_3, --output=<fresh absolute log>, --parallel=1, --serial-lane=<matching segment>> -PassThru -WindowStyle Hidden`
   Freeze source/index, monitor existing process/log through completion. Explain any new boots needed by new evidence before launch. Do not delete build artifacts or borrow another checkout.
9. Reconcile physical result rows and raw diagnostics/frozen hashes/exits/unlock. Separate expected adversarial rejection traces from real failures. Zero touched-AS warnings required. Archive raw log. Renderer remains unverified under NullRHI; focused green means focused green only.
10. Once verified, scoped local commits: Foundation approved API separately coherent, CkTests coupled Scene Node implementation/tests/infrastructure. Use approved author command-scoped; stage explicitpaths/hunks, inspect staged diff and ownership, indexesempty after. No push/gitlink without new delivery authorization. Record exact evidence/limitations. MarkSceneNode verified only then (86->85 pending if sameone-rowfamily), no overall readiness claim.
11. Continue the next bounded family from transport ledger, reviewing previously completed/historical conversions against production feature semantics. Scene Node+Tween is a separate pending family unless actual dependency proves inseparable; do not prepare future families while current gate runs. Maintain evidence, explicit remaining list and precise continuation state.

# Suggested first message

"I'll resume the approved Scene Node draft by reviewing client binding and the exact actor/ECS retirement proofs. No Scene Node build or test has run yet, so I'll finish integration and a focused production-replication gate before marking it verified or starting another family."
