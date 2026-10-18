# One-line summary

Finish ALL CkPlugins gyms, autotests and other tests for ClientServer and ListenServer as quickly as correctness permits, using the existing checkout and infrastructure; the user has explicitly requested this new chat to resume paused work.

# Repo state

Checkout: `D:\Repos\CkPlugins_3`; branch `feature/multiplayer-test-readiness` in host, CkTests and CkFoundation. Verified at handoff:

- Host HEAD `434f81df03becb64674a4fd08d699c73dbd2d4da`, 10 dirty status entries.
- CkTests HEAD `28fbf2d0582e9aee4f32a65ff523e54b83bf7775`, 448 dirty entries, many from the ongoing migration. Do not assume those changes are unrelated or completed: reconcile ownership from evidence before editing/staging.
- CkFoundation HEAD `367ff2d5973ae1d5b4e78b385707f65985e65da7`, 24 dirty entries.
- Latest CkTests commits: `8b877fde` (Divergence one actor-owning primary and checked retirement), `28fbf2d0` (retirement callback regression). Both committed; no push or host-pointer commit for that slice.
- Latest Toolbox run finished, source freeze released, index empty at pause. Check again before launch; this note is not live state.
- Preserve all existing dirty work, including host configuration, generated scripts, other plugin pointers and the broader untracked corpus adapter. Never blanket stage, reset, clean or restore.
- Related shared repositories: `D:\Repos\FtxUiFramework` (approved launch fix previously integrated), `D:\Repos\UnrealEngineAngelscript` (approved engine fixes). Coordinate if further shared edits become necessary; prior approvals do not authorize arbitrary new engine changes.
- Commit author and committer: `Saad K <saadrustam@gmail.com>`, command-scoped identity. Frequent independent buildable commits; no AI attribution. Git metadata requires escalation because it is outside the checkout's writable root.

# Active bugs or open questions

User: "make sure ALL of our gyms and autotests and any other tests are multiplayer ready. Both Client Server and ListenServer." Shared authority simulation, each player gets their own overlay. Invalid Byte bounds are rejected, preserving last valid range. Failed partial station setup stays blocked until session restart; user rejected a complex per-object creator ledger.

Measured architecture coverage is 28/92 registered gyms (30.4%): 23 shared-authority, five adapted local/other policies, 64 outside classification. This is NOT engineering-effort completion or fully certified readiness. At least AStar, Grid System and Audio Advanced are authored unregistered candidates. Full autotest corpus certification remains outstanding. Never invent a new effort percentage.

Next scoped family: full nine-station StateMachine shared bank. Its Divergence prerequisites now pass, but the complete family is unfinished. Existing player controller spawns simulations per player and reruns spawn more actors. GraphWalk has two actor-owning roots sharing one actor bridge; other variants still use legacy roots.

# Why prior fixes or investigations were insufficient

A day of work produced substantial engine/harness groundwork but insufficient breadth. Repeated defensive investigation, preparation, review and verification consumed too much usage before completing families. Do not repeat completed investigations, rediscover archives or manufacture increasingly elaborate prerequisite layers. Complete bounded families end to end, reuse production helpers, and broaden only for a demonstrated blocker. Existing focused tests do not certify all gym behavior or all current dirty source together.

# Available diagnostics and the first evidence to collect

Read `.scratch/multiplayer/pause-checkpoint-oct09.md`, `progress-assessment-oct09.md`, and `statemachine-divergence-single-primary-oct09-evidence.json`. Latest gate: 13/13 physical rows, no archived ensures/script/protocol errors; ordinary Iris warnings remain. Includes authored delivery, paired isolation, callback mutation rejection in both topologies and two standalone actors. Incremental DebugGame C++ build succeeded before an AngelScript const-binding discovery failure; fixed getter, then two fresh boots passed. NullRHI only; do not claim pixels or hardware UI.

Use current branch/status and active processes as first live evidence. `.scratch/multiplayer/status.json` is large: read only selected fields. Archives contain manifests and immutable logs; do not overwrite them. Current manifest: `integer-crowd-final-gate-manifest.json` (574 entries at pause).

# Likely symptoms, causes and files

| Symptom | Likely cause / starting point |
|---|---|
| One simulation per player or duplicates on rerun | StateMachine GymPlayerController spawns source actors locally; lacks shared bank/session |
| Wrong pass actor bridge | Multiple WithActor roots; reuse the new retained primary plus actorless A/B design |
| Old callback mutates new generation | Missing exact receipt/generation and terminal closure checks; source/runtime helpers |
| Partial failed setup keeps running | Admission must publish atomically and remain terminally closed on failure |
| Clients repeat tests or write source state | Passive client mirrors/replicated result frames missing; corpus adapter and authored body fixtures |
| Iris ensure/path mismatch | Already investigated CK engine ensure and PIE descriptor normalization; consult archives before changing engine |

# Critical files and their roles

All paths below are relative to `D:\Repos\CkPlugins_3`:

1. `AGENTS.md`: checkout safety, framework and delivery requirements; read applicable nested guides.
2. `Plugins/CkTests/Script/CkStateMachine/CkStateMachine_GymPlayerController.as`: nine registrations and rerun callbacks.
3. `Plugins/CkTests/Script/CkStateMachine/CkStateMachine_GymSourceActor.as`: retained source primary, closure and pass receipts.
4. `Plugins/CkTests/Source/CkTests/Public/CkStateMachineGym_Runtime.h`: production validation/retirement API.
5. `Plugins/CkTests/Source/CkTests/Private/CkStateMachineGym_Runtime.cpp`: complete healthy forest proof and retirement.
6. `Plugins/CkTests/Source/CkTests/Private/CkStateMachineGym_PendingPrimary.cpp`: exact pending request cancellation.
7. `Plugins/CkTests/Source/CkTests/Private/UnitTests/CkStateMachine/Test_StateMachineGym_DivergenceIsolation.spec.cpp`: real paired topology and physical cleanup fixture.
8. `Plugins/CkTests/Source/CkTests/Private/UnitTests/CkStateMachine/Test_StateMachineGym_DivergenceRetirementCallback.spec.cpp`: real BeginDestroy callback mutation rejection.
9. `Plugins/CkTests/Source/CkTests/Private/Net/CkAutoTest_MultiplayerCorpus.spec.cpp`: broader in-flight corpus adapter; preserve/reconcile before delivery.
10. `.scratch/multiplayer/progress-assessment-oct09.md`: reconciled coverage, limitations and prior gate references.

# Things ruled out

Do not replicate the SceneNode itself merely to move an entity: transform replication is the relevant contract. The old unconditional CK first-packet ensure was removed while readiness/retry remained. PIE descriptor normalization is package-verified and preserves protocol/default-state checks; approved engine changes must remain surrounded by `//++CK` and `//--CK`. Latest Divergence source ownership and callback regression are green; do not rerun them alone without a change or unresolved concern. Historical passing row counts span revisions and cannot become a whole-suite percentage.

# Architecture notes and gotchas

StateMachine bank has AutoCycle, PauseResume, Complex, Hierarchical, GraphWalkRegression, DivergenceFirstBranch, DivergenceFirstBranchTimed, RacingEventDriven and EventDrivenMultiCondition. Six distinct source actor classes; all nine rows need one authority bank with ordered value frames and passive per-player overlays. Defer starts until complete admission; route owned rerun RPCs with one in-flight request; retire the old forest physically before replacement and preserve eight peer stations. Keep failures terminal, not cleanup-and-retry.

Factory construction callbacks may execute synchronously when bound: retain receipts first. Validate one prerequisite at a time. CK_ENSURE diagnostics cannot own recovery: compute safe validity once, diagnose, then ordinary if/explicit return. Retirement revalidates after callbacks; reject unknown ownership, do not destroy guessed descendants. Existing generic helpers/Selection examples should be reused when appropriate rather than creating parallel frameworks.

# Concrete diagnostic and verification flow

1. Treat this new chat as explicit resumption. Read handoff and AGENTS, invoke recommend-model-effort as required. User previously retained Astra Ultra; honor that unless user approves a change. Use bounded lower-cost Sol sidecars where genuinely independent and permitted, rather than duplicating lead analysis.
2. Inspect current status, active processes and selected checkpoint fields. No new worktree, clone, mirror, repo copy, alternate checkout or submodule initialization under another root. Work only here; do not delete Binaries/Intermediate/DDC/artifacts.
3. State a small acceptance checklist for full StateMachine family and a bounded boot count, then implement against existing infrastructure. Resolve critical architecture in main thread; delegate only specified disjoint edits/review. Do not perform another broad progress audit first.
4. Run builds/tests ONLY through `CkAuto/UnrealToolbox.exe`, absolute `--project=D:\Repos\CkPlugins_3`. Read build-test skill. Launch detached with PowerShell Start-Process -PassThru -WindowStyle Hidden, visible progress window; never --no-progress-window. Escalate for GUI launch, monitor PID/output to completion, never duplicate after timeout. --config only with --build. Reuse binaries for AngelScript-only changes.
5. Freeze source/index during run, normalize before final gate, verify physical rows plus fresh log ensures/script/protocol diagnostics. Prefer one compatible family gate covering both topologies and meaningful failure cases, not repeated equivalent boots. Explain new evidence before exceeding planned boots.
6. Commit exact independent reviewed paths using supplied identity, preserve unrelated changes and archive evidence. Report completed family, scoped passing evidence, remaining families and usage. Do not call a focused green gate full certification.
7. Continue the remaining backlog by coherent families, prioritizing reuse and end-to-end delivery; include authored unregistered gyms and non-gym tests. Integrate eligible submodule commits/pointers under repository rules only after checking shared state. Do not stop at a plan or require repeated permission for already-authorized reversible work. Escalate genuinely material new shared-engine/product decisions.

# Suggested first message

“I’m resuming in the existing checkout. I’ll finish the full StateMachine family using the tested Divergence groundwork, then move through remaining families with one scoped acceptance gate and clear verified progress per family.”
