# One-line summary

Correct multiplayer-readiness scope across CkPlugins gyms: exercise each feature's actual authority, replication, ownership and client behavior; begin by correcting the in-flight VoxelNav conversion, then review previous work against the same standard, one bounded family at a time.

# Repo state

Work only in `D:\Repos\CkPlugins_3`, in place. No worktrees, clones, mirrors, repository copies, alternate checkouts, or repurposing another existing checkout.

Host HEAD freshly verified: `434f81df03becb64674a4fd08d699c73dbd2d4da`, branch `feature/multiplayer-test-readiness`; host index empty. Host dirty paths include `Config/DefaultGameplayTags.ini`, `Script/Generated/CkPlugins_EntitySpawnParams.as`, `Script/PlaceableTests/PlaceableTests_EntityScripts.as`, untracked `AutomationGate.json`, and previous continuation prompts. Preserve all existing work.

Last verified submodule state in the parent session: CkTests HEAD `dc4818ca2b40436748fe01373f0fc02b583df9b6`; CkFoundation HEAD `367ff2d5973ae1d5b4e78b385707f65985e65da7`; both on `feature/multiplayer-test-readiness`, with empty indexes at that check. These were not freshly reverified when this handoff was written: sandbox access to their external Git metadata was denied. Recheck before staging or committing. Both contain substantial pre-existing dirty work; preserve it, especially untracked `Source/CkTests/Private/Net/CkAutoTest_MultiplayerCorpus.spec.cpp`.

VoxelNav has been integrated into production files but remains uncommitted/unpushed according to current status. Exact ten owned paths are recorded in `.scratch/multiplayer/voxelnav-flying-owned-oct11.json`. Native incremental build passed after correcting internal cast calls. Two subsequent editor boots failed AngelScript compilation on unavailable native-base `Super` calls; those calls were removed afterward. The latest gate is not certified complete.

**Active-run hazard:** status records `VoxelNavFlyingOct11Script`, Toolbox PID `20516`, source frozen, log `Saved/Logs/MultiplayerVoxelNavFlyingOct11Script.log`. It waited on another checkout's engine writer lock for over forty minutes. The latest log read now shows editor startup at `2026-10-11 01:56` Pacific. This is a point-in-time observation, not a current process guarantee. The detached run and its watcher may survive the interrupted parent turn. Reconcile them before any source/index mutation or another launch. Do not touch the other checkout or its build.

# Active bugs or open questions

The user's correction supersedes the old instruction to finish the saved VoxelNav snapshot architecture:

> "VoxelNav should work as a Client as well, and I should see the Agents moving. But the only reason I should see them move is because transform is replicated. Not because VoxelNav is replicating."

> "This same logic needs to be applied to all other gyms. And, we need to make sure previous work was done correctly as well."

The intended client experience is seeing the same authoritative agents through production Transform replication. This does not authorize duplicate client navigation simulation, replication of navigation internals, or a gym-specific pose transport. Establish the production entity/spawn/composition/replication lifecycle needed to deliver those Transform features; flipping one replication enum without proving the whole delivery path is insufficient.

Review previously committed and dirty conversions too. Earlier instructions not to reopen completed families are superseded for this targeted architecture review. A previous focused green gate proves only its tested contract, which may itself have used the wrong transport.

# Why prior fixes or investigations were insufficient

The prior work treated "make the gym shared" as a reason to build replicated GameState value frames and owned R/T protocols. That was an unconfirmed product assumption. A custom frame can make clients draw moving agents while bypassing the production feature that should replicate their movement.

The current VoxelNav source and agent transforms explicitly use `DoesNotReplicate`. Its replicated GameState `Snapshot` contains `FCkVoxelNavGym_AgentFrame.Transform`, and the controller draws those values. This is a confirmed architectural mismatch with the user's clarified requirement, regardless of whether the queued test becomes green.

Do not generalize that every snapshot is wrong. UI summaries, explicit remote debugging, and feature-defined replicated state can be appropriate. Assess whether each field belongs to an existing production replication feature and whether its gym transport is concealing a missing or broken production path.

# Available diagnostics and the first evidence to collect

First inspect only current `activeRun`, `sourceFrozen`, `voxelNavFlyingGroundedOct11`, and the latest gate log/process record. Status may be stale. Monitor an existing run to completion rather than launching a duplicate; keep source/index frozen while it is active. Preserve its logs and label any results as evidence for the superseded snapshot implementation, not approval to commit it.

Then trace one VoxelNav agent from authority spawn through the production replication driver, client entity/script composition, replicated Transform application, and client presentation. Use adjacent production examples and focused tests. Determine whether the gap is gym authoring or a production framework defect before editing.

Historical evidence lives in `.scratch/multiplayer/status.json` and family-specific archives. The latest completed GOAP bank evidence is `.scratch/multiplayer/goap-main-badge-oct11-green-evidence.json` (8 physical rows passed, NullRHI only). This does not establish compliance with the new transport criterion. The current source hash manifest has 819 entries as last recorded; it is a source freeze record, not completion coverage.

# Likely symptoms, causes and files

| Symptom | Likely cause / starting point |
|---|---|
| Client sees agents only through gym wire transforms | Nonreplicated source/agents plus GameState `Snapshot`; VoxelNav Source, GameState, Wire and controller files |
| Transform marked replicated but clients have no entities or visuals | Missing production spawn/driver/composition/receipt path; inspect CkEcs Net, EntityScript and Transform paths |
| Client runs navigation or movement processors unnecessarily | Feature composition/authority gates copied wholesale; inspect actual processor admission and net role |
| Earlier gym gate is green but production replication remains untested | Fixture compares custom snapshots instead of actual client entities/features; inspect each family's native fixture |
| Every gym gets RPC controls and an MP badge | Eligibility inferred from R/T buttons or shared drawing, rather than an actual multiplayer contract |
| Gate remains active or results absent | Existing Toolbox process/engine lock or AS compile failure; current run record and fresh output log |

# Critical files

1. `.scratch/multiplayer/status.json` - prior deliveries, exclusions, family evidence and active-run state; do not overwrite unrelated fields.
2. `.scratch/multiplayer/voxelnav-flying-owned-oct11.json` - exact ownership boundary for the ten in-flight VoxelNav paths.
3. `Plugins/CkTests/Script/CkVoxelNav/CkVoxelNavGym_FlyingVsGrounded_Source.as` - current authority simulation; source and agent Transform replication presently disabled.
4. `Plugins/CkTests/Script/CkVoxelNav/CkVoxelNavGym_FlyingVsGrounded_GameState.as` - fixtures, admission and current replicated snapshot transport.
5. `Plugins/CkTests/Script/CkVoxelNav/CkVoxelNavGym_FlyingVsGrounded_PlayerController.as` - client presentation currently reads wire transforms; controls and local stations.
6. `Plugins/CkTests/Source/CkTests/Public/CkVoxelNavGym_Wire.h` and `Private/CkVoxelNavGym_Runtime.cpp` - current frame payload/validation and forest helpers; retain only justified responsibilities.
7. `Plugins/CkTests/Source/CkTests/Private/UnitTests/CkVoxelNav/Test_VoxelNavFlyingVsGroundedGym_SharedWorld.spec.cpp` - real travel/owners fixture, currently proves custom-frame delivery rather than production Transform replication.
8. `Plugins/CkTests/Script/Common/CkTests_GymRegistry.as` - authored MP flags; annotation is not readiness certification.
9. `Plugins/CkFoundation/Source/CkEcs/` and `Source/CkEcsExt/Public/CkEcsExt/Transform/` - production entity replication lifecycle and Transform delivery; locate exact relevant files with narrow searches.
10. `.scratch/multiplayer/launch-focused-run.ps1`, `watch-focused-run.ps1`, and `CkAuto/.claude/skills/build-test/SKILL.md` - existing launch/monitor tooling and available canonical build guidance. Root wrapper references a missing `.Codex` path in this checkout; read the actual skill before launching.

# Things ruled out

- Do not finish or commit the VoxelNav pose-snapshot port simply because it is already implemented or its old gate passes.
- Do not replace production Transform replication with pose RPCs, replicated gym transforms, SceneNode replication, or a parallel client simulation to make the picture match.
- Do not convert a server-only algorithm into a replicated algorithm merely to give its gym an MP badge.
- Do not treat server-only as a reason to hide authoritative replicated entities from clients; VoxelNav agents must remain visible through their replicated Transform state.
- Do not wholesale revert previous commits or discard dirty work. Separate justified infrastructure, actual defects, unnecessary gym transport and valid tests using exact paths/hunks.
- Do not reopen unrelated engine investigations, run broad suites automatically, create another checkout, or delete/recreate Binaries, Intermediate, DDC or build artifacts.

Existing local rendering/performance exclusions remain relevant. Input Playground and moving remote-pawn Rope were deferred for proper Jolt Character networking; no pose-RPC workaround. Revisit their scope only when evidence or the user's new criterion warrants it.

# Architecture notes and gotchas

Use each production feature's own network semantics:

- Authority-only simulation can have multiplayer implications through the state it drives, such as Transform, attributes, ownership or spawned entities. Test that state through its actual production replication mechanism.
- Features with actual client/server ownership, RPC, replicated gameplay state, interaction, prediction or reconciliation need explicit network coverage for those behaviors.
- Client-local presentation/settings/render/performance gyms do not become meaningful multiplayer work merely by broadcasting their controls or duplicating their visuals.
- A remote diagnostic view is a separate product capability. Do not create one as an implicit substitute for a feature's replication contract.

For each reviewed gym, record a compact row: actual role/contract, client-visible state, production transport owner, existing gym transport, keep/fix/skip decision, evidence and focused gate. MP flags express an authored multiplayer component; they are not percentages or certification.

VoxelNav `Volume::Add` creates a child entity, unlike CrowdAgent/Path composition on an existing agent; the in-flight source now retains the returned child. Native public conversion is `CastChecked`, not internal `DoCastChecked`. The last script correction removed `Super` calls unavailable on native AStaticMeshActor/GameState bases. Preserve these factual API corrections where applicable while replacing the wrong network architecture.

Follow the latest user/global/project instructions, including the once-per-conversation opening recommendation, automatic Astra consultation triggers, failure-path policy, and exact staging. Keep decisions and integration in the main thread. Use at most one scoped worker when it reduces total usage, except a required bounded Astra consultation. Material uncertainty about replication/lifetime after focused inspection requires consultation before risky implementation; the same symptom surviving two fixes requires it before a third edit. Advice is not verification.

# Concrete diagnostic and verification flow

1. Read this prompt fully and current applicable instructions. Do not resume the old handoff's architecture blindly. Verify active Toolbox/process/log state and ownership of the selected checkout before editing; reconcile the existing frozen run without touching another checkout.
2. Establish VoxelNav's desired production contract: one authoritative baked volume and two agents; clients observe corresponding replicated agent entities/Transforms, while navigation and authoritative movement remain on the server. R/T ownership is secondary and must not become the transport for movement.
3. Trace actual spawn, replication admission, client composition and Transform delivery using narrow production reads. Determine whether a framework fix is required. Consult Astra for unresolved consequential replication/lifetime decisions and raise material scope changes to the CTO.
4. Replace or remove the in-flight custom pose transport with the appropriate production replication/presentation path. Preserve unrelated changes and useful validated lifecycle/fixture work; do not assume all ten files remain necessary. Do not just toggle Transform replication and declare success.
5. Adapt the real-travel fixture to inspect actual authoritative and client agent entities, production replication receipts and their applied Transforms. Prove fresh authority-driven motion visible to both clients and the listen host, no duplicate client movers/nav simulation, restart/retirement and source-loss cleanup through the correct lifecycle. Retain focused malformed/stale input coverage where applicable. Snapshot equality alone is insufficient.
6. Normalize owned changes, state editor-boot budget and reason, then build/test only through `CkAuto/UnrealToolbox.exe --project=D:\Repos\CkPlugins_3`. Launch detached with `Start-Process -FilePath '.\CkAuto\UnrealToolbox.exe' -ArgumentList <args> -PassThru -WindowStyle Hidden`, requesting GUI/escalated permission as required; retain the progress window and never pass `--no-progress-window`. Reuse binaries for AS-only changes; incremental build for C++ changes. Freeze source/index, monitor existing PID/output, inspect physical rows and fresh logs for script errors/ensures. Explain any additional boots before launching them.
7. Record exact evidence and limitations, then commit only a buildable, coherent corrected VoxelNav slice with precise staging and repository message conventions. Never claim repository-wide readiness from a focused gate. Do not automatically publish or bump host/downstream pointers without reconciling delivery authorization and state.
8. Make a compact transport/eligibility triage of previous conversions from their actual files and delivery records. This user explicitly requests reviewing prior work; do not exempt committed or previously green families. Prioritize gym-specific pose/state transports that might bypass production replication. Use narrow per-family inspection, not a new broad source dump.
9. Review and, where needed, correct one prior family end to end. Keep valid feature replication, ownership fixes and useful tests; remove unjustified substitute transports or mark local-only gyms appropriately. Gate only the affected production contract plus compatible sibling coverage. Record keep/fix/skip with evidence; preserve unresolved work honestly.
10. Continue remaining eligible gyms sequentially under the same rule. Do not prepare multiple future families in parallel. Give each bounded slice a clear completion criterion and stop point; maintain an explicit remaining/review list so open-ended work does not silently expand.

# Suggested first message

"I'll first reconcile the existing frozen Toolbox run, then trace VoxelNav agents through production entity and Transform replication. I'll correct that bounded family before reviewing earlier gym conversions against the same feature-specific multiplayer rule."
