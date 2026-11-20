# Phase 4 — Transactional authority placement and readiness

Implement this phase only, in the selected CkPlugins checkout. No worktrees, clones, alternate checkouts, clean-build artifact deletion, Git delivery or square behavior changes. This documentation-only planning session ran no build/tests. The acceptance matrix is the scored executable specification until the executor adds the named production-path tests.

## Entry, source anchors and ownership

Require accepted phases 1–3 in `PROGRESS.md`, including geometry, board publication and rule FIFO evidence. Inspect root/Foundation/CkTests status; preserve unrelated edits and staged work. Continue the authorized `feature/hex-grid` branch in place; if ownership is ambiguous, STOP before changing branches. Read `Plugins/CkFoundation/AGENTS.md:1-45`, `Source/AGENTS.md:1-5`, `DEVELOPMENT.md:364-427`, and canonical Foundation `.claude/skills/ckecs-architecture-contract/SKILL.md`, `ck-macros-and-codegen/SKILL.md`, `ck-change-control/SKILL.md`, `ck-angelscript-interop/SKILL.md`, `ck-lifecycle-teardown-campaign/SKILL.md`. Read CkTests' `CLAUDE.md`/`Script/Common/` and the Toolbox build-test skill before invoking them.

Inspect these existing source ranges; square is a compatibility fixture, not the new transaction implementation:

| Anchor | Why read it |
| --- | --- |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Placement/Ck2dGridPlacement_Utils.cpp:23-189`, `:264-370` | Validation ordering, immediate square mutation and premature record/stamp timing traps. |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Occupancy/Ck2dGridOccupancy_Utils.cpp:18-78`, `:151-220` | Grid lifetime owner, occupant death watch, pending-destroy-aware queries; hex needs a separate ref and immediate committed projection. |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Occupancy/Ck2dGridOccupancy_Fragment.h:24-78`, `_Processor.cpp:23-86` | Square record/stamps/scratch are eventual projection, not an admission lock. |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Placement/Ck2dGridPlacement_Fragment.h:18-33`, `_Fragment_Data.h:16-78`, `Ck2dGridPlacement_Result_Data.h:11-48` | Typed handle, signal macros and reflected result conventions. |
| `Plugins/CkFoundation/Source/CkEcs/Public/CkEcs/Request/CkRequest_Completion.h:15-126`, `CkRequest_Data.h` (`FCk_Request_Base`) | Exactly-once generic completion and cancellation; typed result is additive. |
| `Plugins/CkFoundation/Script/Generated/utils_2d_grid_placement.as:1-65` | Existing generated API shape; its legacy unregistered placement-handle workaround must not be inherited. |
| `Plugins/CkTests/Script/CkGrid/CkAutoTest_Grid_ReentrancyDuringBroadcast.as:1-89`, `CkAutoTest_Grid_ClearThenPlaceSameTick.as:1-90`, `CkAutoTest_Grid_ExternalOccupantDestructionCleanup.as:1-82` | Real consumer/lifetime/same-tick test fixtures; leave square behavior unchanged. |

New/edited production files, all under `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/HexGridSystem/`:

* `Placement/CkHexGridPlacement_Fragment_Data.h/.cpp`, `_Result_Data.h`, `_Fragment.h`, `_Utils.h/.cpp`: typed handle/spec/request/result/view/delegates and public query/mutation surface.
* `Occupancy/CkHexGridOccupancy_Fragment.h/.cpp`, `_Utils.h/.cpp`: private committed index and `ck::hex_grid` transaction helper; no public raw-stamp UFUNCTION. `Occupancy/CkHexGridOccupancy_Processor.h/.cpp` holds lifetime repair/EndPlay if required by actual scheduler ownership; it must not become a second admission drain.
* Extend `Grid/CkHexGrid_Fragment_Data.h`, `_Fragment.h`, `_Utils.h/.cpp`, `_Processor.h/.cpp`: readiness value/result, pending queries, existing board FIFO variants and authority drain/cancel handling.
* Extend `Cell/CkHexCell_Fragment.h` only for derived cell ID projection, and P3 blocker/rule state only where one transaction needs it. Do not add a second public rule state source.
* `Plugins/CkFoundation/Source/CkGrid/Private/Tests/Test_HexGrid_Placement.cpp`; AS public consumer `Plugins/CkTests/Script/CkGrid/HexGrid/CkAutoTest_HexGrid_Placement.as` with a CkTests native driver registered under the exact name `Ck.HexGrid.Placement.AS_Consumer`.
* Generated `Plugins/CkFoundation/Script/Generated/utils_hex_grid_placement.as`, `utils_hex_grid_occupancy.as`, `utils_hex_grid.as`, generated handle registry outputs as actually emitted. Do not hand-edit them.

Future callers are P5 save adapter, P6 replication adapter, and the P7 gym/editor consumer. They read committed state and issue public requests; none may access a raw public stamping function. No inventory/square consumers migrate.

## Fixed public values and signatures

All values below are reflected `USTRUCT(BlueprintType)` or `UENUM(BlueprintType)` with house CK macros, private UPROPERTY storage, generated getters; specs/requests get fluent setters. Type-safe placement handle is defined in `_Fragment_Data.h` and fully registered for AS conversions, validity, equality and `.H()`.

```cpp
enum class ECk_HexGridReadiness : uint8 {
    AwaitingRestore, AwaitingReplication, Ready, Unavailable, Destroying
};
enum class ECk_HexGridFailure : uint8 {
    None, NotReady, InvalidGrid, InvalidObject, InvalidPlacementId,
    InvalidFootprint, InvalidRotation, Overflow, AnchorOutsideDomain, OutsideDomain,
    Blocked, Occupied, TagMismatch, Disconnected, NotAuthority, Cancelled,
    CrossGridTransfer, InternalFailure, InvalidSchema, RecipeMismatch,
    InvalidProjection, DuplicatePlacementId, OccupantAlreadyPlaced,
    LateOccupantConflict, RestoreTimedOut, RestoreBaselineMissing,
    ReplicationTimedOut, Destroyed
};
FCk_HexGridReadiness_Result {
    ECk_HexGridReadiness State; ECk_HexGridFailure Failure; FGuid PlacementId;
};
FCk_HexGridPlacement_Spec {
    FCk_Handle_HexGridObject Object; // required live typed occupant for public Place
    FCk_HexCoord Anchor;
    ECk_HexRotation Rotation;
    ECk_HexGridConnectivity Connectivity = ECk_HexGridConnectivity::Ignore;
};
FCk_HexGridPlacement_View {
    FGuid PlacementId; FCk_Handle_HexGrid Grid; FCk_Handle Occupant;
    FCk_Handle_HexGridPlacement Handle; // session readback only, never a durable key
    ECk_HexGridOccupantState OccupantState; // Anonymous, AwaitingBinding, Bound, BindingConflict
    TArray<FCk_HexCoord> FootprintOffsets; // immutable captured shape, never a borrowed object pointer
    FGameplayTagContainer RequiredCellTags, ForbiddenCellTags;
    FCk_HexCoord Anchor; ECk_HexRotation Rotation;
    ECk_HexGridConnectivity Connectivity;
    TArray<FCk_HexCoord> Cells; // canonical (r,q)
};
FCk_HexGridPlacement_Result {
    bool Succeeded = false; ECk_HexGridFailure Failure;
    FGuid PlacementId; TArray<FCk_HexCoord> FailedCells;
    FCk_HexGridPlacement_View Placement; // new view on success; old view on failed replacement
};
```

Place creates a nonzero `FGuid` only at successful admission. IDs are scoped to the board and never keyed by occupant, cell, entity number or array index. Same-board replacement and Move preserve the ID. Remove terminates that ID; a later fresh Place receives a fresh ID. An invalid input ID is not an anonymous placement. Public Place cannot create reservations without live objects; private P5/P6 projection may restore anonymous records with valid durable IDs and captured footprint/tag policy. View.Handle is a convenient live-session typed handle with ordinary generational validity, not serialized; View.Grid is likewise session context. A failed preview has no handle. Removal notifications may carry a stale handle and remain meaningful through durable ID and captured old fields.

`FCk_Request_HexGridPlacement_Place : FCk_Request_Base` contains Spec and a reflected `FCk_Delegate_HexGridPlacement_OnResult OnResult`. `Move` contains PlacementId, Anchor, Rotation, OnResult. `Remove` contains PlacementId, OnResult. Each has `CK_REQUEST_DEFINE_DEBUG_NAME`, essential constructor fields, `CK_PROPERTY` and optional OnResult setter. Declare the dynamic typed delegate with `(const FCk_HexGridPlacement_Result& InResult)`. Implement one terminal dispatcher that consumes/unbinds the typed delegate before invoking it and uses `TryFireCompletion` for generic completion; copies of a queued request must not create a second live completion channel.

`UCk_Utils_HexGridPlacement_UE` uses `ScriptMixin="FCk_Handle_HexGrid"` and these signatures:

```cpp
static FCk_HexGridPlacement_Result Get_CanPlace(const FCk_Handle_HexGrid& InGrid,
    const FCk_HexGridPlacement_Spec& InSpec);
static FCk_HexGridPlacement_Result Get_CanMove(const FCk_Handle_HexGrid& InGrid,
    FGuid InPlacementId, const FCk_HexCoord& InAnchor, ECk_HexRotation InRotation);
static FCk_Handle_HexGrid Request_Place(UPARAM(ref) FCk_Handle_HexGrid& InGrid,
    const FCk_Request_HexGridPlacement_Place& InRequest,
    const FCk_Delegate_Request_OnCompleted& InDelegate);
static FCk_Handle_HexGrid Request_Move(UPARAM(ref) FCk_Handle_HexGrid& InGrid,
    const FCk_Request_HexGridPlacement_Move& InRequest,
    const FCk_Delegate_Request_OnCompleted& InDelegate);
static FCk_Handle_HexGrid Request_Remove(UPARAM(ref) FCk_Handle_HexGrid& InGrid,
    const FCk_Request_HexGridPlacement_Remove& InRequest,
    const FCk_Delegate_Request_OnCompleted& InDelegate);
```

Queries are BlueprintPure. Mutations are BlueprintCallable/BlueprintAuthorityOnly, category `Ck|Utils|HexGridPlacement`, `AutoCreateRefTerm="InDelegate"`, no C++ delegate default. Chainable grid return identifies the target, never admission success. Preview returns candidate resolved cells through Placement with invalid ID for a fresh placement; it neither allocates an ID nor reserves cells. Admission repeats validation at drain time. Expected rejection uses ordinary typed result branches in Shipping as well as checked builds; internal impossible-state assertions use total ensure predicates with terminating recovery in the ensure body.

Occupancy API is read-only: `Get_Placements(Grid)->FCk_HexGridPlacements_Result` (`Succeeded, Failure, TArray<FCk_HexGridPlacement_View> Placements`), `TryGet_Placement(Grid,FGuid)->FCk_HexGridPlacement_Result`, `TryGet_PlacementAt(Grid,Coord)->FCk_HexGridPlacement_Result`, `TryGet_PlacementForOccupant(Object)->FCk_HexGridPlacement_Result`. Missing ID/cell/occupant returns `InvalidPlacementId` rather than a fabricated origin. Invalid/stale grid returns `InvalidGrid`. Pending board returns `NotReady`, terminal Unavailable returns its stored cause, never an apparently authoritative empty set. `Get_Readiness(Grid)->FCk_HexGridReadiness_Result`, `Get_IsReady(Grid)->bool`, `Get_IsPending(Grid)->bool` live on grid Utils; pending is true only for AwaitingRestore/AwaitingReplication. `Has` means feature presence and has no readiness semantics.

Signals are reflected dynamic delegates carrying `(FCk_Handle_HexGrid InGrid, const FCk_HexGridPlacement_View& InPlacement)`: `FCk_Delegate_HexGridPlacement_ObjectPlaced`, `_ObjectMoved`, `_ObjectRemoved`. Add standard BindTo_/UnbindFrom_ functions with canonical binding/postfire policy defaults. A replacement emits one ObjectMoved (same durable ID); idempotent Move emits no state-change signal. Remove payload is the old immutable view, still useful after entity destruction. Rejection emits no success/state-change signal. Every committed signal observes **all** new maps, cell projection, records and backrefs; generic/typed terminal channels follow the state-change signal. Callback effects can change the world after that observation, so “Succeeded” proves the committed request outcome, not immunity to later requests.

Required C++/BP/AS parity examples:

```cpp
auto Req = FCk_Request_HexGridPlacement_Place{Spec};
Req.Set_OnResult(OnResult);
UCk_Utils_HexGridPlacement_UE::Request_Place(Grid, Req, {});
// Bind OnResult to read the eventual PlacementId; the returned Grid is not a placement.
```
```angelscript
auto Req = FCk_Request_HexGridPlacement_Place(Spec);
Req.Set_OnResult(FCk_Delegate_HexGridPlacement_OnResult(this, n"OnPlacementResult"));
utils_hex_grid_placement::Request_Place(Grid, Req);
auto State = utils_hex_grid::Get_Readiness(Grid);
auto Query = utils_hex_grid_occupancy::TryGet_Placement(Grid, PlacementId);
```

BP constructs the same request struct, binds typed result, branches on Succeeded/Failure and stores FGuid. It must not poll returned handle as completion. [EDITOR-VERIFY] compile this graph including Move/Remove and verify one typed rejection with no success signal.

## Transaction design and ordered implementation

1. Add tests in the matrix first, using public P2/P3 creation and real registered scheduler/lifetime. A test may inspect an internal committed projection to assert consistency, but may not compose only a subset of production fragments. Compile-failure baseline is acceptable until new APIs exist; never spend a boot on an intentionally uncompilable tree.
2. Add private `FFragment_HexGridOccupancy` with committed `PlacementId -> view/placement entity`, `Coord -> PlacementId`, and a monotonic commit revision. Store occupant link in **new** `FFragment_HexGridOccupant_PlacementRef` with grid+ID. Never reuse `FFragment_2dGridOccupant_PlacementRef`: one square placement and one hex placement can coexist. A live occupant may have at most one hex placement across all hex boards. Repeated Place on its current board is replacement; attempting Place on another board fails CrossGridTransfer and retains old data. Grid is placement lifetime owner; occupant is watched, not lifetime owner.
3. Extend P3's board command FIFO with Place/Move/Remove and internal death-removal variants. Snapshot the queue at drain entry, process strictly enqueue order, and leave callback-enqueued commands for next drain. One authority processor owns all rule+placement commits. Authority check at submission and drain, with ordinary `NotAuthority` result. Reject pending/dead targets without a fragment read on invalid handles. A destroyed owner excludes drain and EndPlay cancels remaining commands.
4. For each command build a scratch candidate from the **current committed** projection. Validate grid/readiness, object/ID, occupant uniqueness, shape/enum/arithmetic, anchor membership, resolved cell domain, blocked votes, per-cell effective tags, six-neighbor footprint connectivity and collisions. Ordering of failure is exactly that list; FailedCells is distinct canonical (r,q), first reason stable, nonspatial failures empty. Self-ignore is permitted only for the single replaced ID, never every cell sharing the occupant. A valid anchor may lie in an empty shape hole; it must still belong to the board. Policy Ignore allows disconnected shapes; RequireConnected applies both preview and admission.
5. Stage any newly required entity/record/label/backref work before publishing. Use checked, failure-representable helpers; failure destroys staging entities/releases staging bindings and leaves old revision/maps/ID/cells/links untouched. Commit swaps authoritative maps and installs the complete derived cell/index/record/backref projection in one callback-free critical section. No callback, generic completion, success signal or reentrant user code may run inside this section. Do not rely on next-tick stamp reconciliation for admission. Helpers that cannot be made non-callbacking/rollback-safe are a STOP blocker; no partial commit plus later repair is allowed.
6. After commit and release of the commit guard, emit the selected state-change signal, typed terminal result, then generic completion. Successful no-op reports success with same ID/revision and no state-change signal. Failure invokes typed terminal result once then generic Failed (or Failed_NotEnqueued at boundary); failure leaves state unchanged. Queued owner teardown returns typed Cancelled + generic Failed_Cancelled. Cancelling requires a typed-aware visitor in addition to `FireCancelledForPending`; the generic helper alone cannot deliver the typed payload. Reentrant requests enqueue and cannot claim cells until next drain. Destroyed object between enqueue/drain rejects InvalidObject; queued commands keep no borrowed fragment references.
7. Lifetime callbacks enqueue internal remove by scoped ID for occupant or placement death, with exactly-once removal deduplication. Drain removes only the still-matching current backref, never a newer placement. Until that drain, dead occupants may return an invalid occupant handle but their durable committed reservation remains occupied; do not report free while cell->ID still owns it. Before each admission process already-pending deaths in original FIFO order, and reject pending-destroy occupant candidates. External death emits one ObjectRemoved when the removal commits. Board teardown sets Destroying synchronously, cancels remaining commands, detaches watches and clears owned projections without broadcasting success for dying board state. In a callback that destroys the grid, abort the rest of the detached drain and terminal-cancel its remaining entries once.
8. Implement readiness seam: a fresh ordinary board becomes Ready as soon as P2 atomic composition succeeds, including zero placements. No restore/net wait or one-tick setup barrier for that path. `Unavailable` stores terminal cause and ID; pending exposes `NotReady`. P5/P6 may set AwaitingRestore/AwaitingReplication **before constructed consumers** from verified construction context, and may transition Ready only after complete accepted projection. Structural domain, geometry and coordinates remain available during restore. Failure-bearing occupancy, rule and effective-tag reads indicate pending/unavailable before the baseline. P2's mutable cell TryGet functions return false with cleared output in that state, and P3 commands reject before enqueue. A caller can distinguish a stale handle from a pending owner via the grid/readiness APIs. P4 adds no guessed sleep/retry/timer and no replication-flag-only readiness inference. State-change readiness notification `FCk_Delegate_HexGrid_ReadinessChanged(Grid, const FCk_HexGridReadiness_Result&)` uses standard bind/unbind; signal after transition, pending and terminal both observable.
9. Expose only private C++ helpers in namespace `ck::hex_grid`: `ReadCommittedProjection(const FCk_Handle_HexGrid&)->FCk_HexGridCommittedProjection` and `TryCommitProjection(FCk_Handle_HexGrid&, const FCk_HexGridCommittedProjection&)->FCk_HexGridPlacement_Result`. Projection includes placement views, blocker contributor views, runtime manual blocked votes and cell-local tag changes relative to the authored recipe. Derive effective tags and counts after applying all sources. This helper validates the entire staged projection including final entry, duplicate IDs, cross-board occupant uniqueness and overlaps, then commits once; capture reads committed state even while public queries report NotReady. It does not infer recipe/schema/network policy. P5 adds wire adapters `ck::hex_grid::persistence::ReadCommittedProjection` and `TryReplaceCommittedProjection` with its separate payload types. Full projection validation must permit anonymous records only through this private hydration/net path; public Place still requires a live object. No save/replication wire schema is introduced in this phase.
10. Generate wrappers normally; inspect fresh logs for UHT/AS errors and unexpected ensures. Normalize source before final gate. Use `VALIDATION.md#running-a-gate` with exact filter below. Correct every compiler/UHT/AS error from a run before another editor boot. Branches: all named cases selected/pass and clean fresh log → exit; a reproducible case fails → record hypothesis and repair within budget; no selected tests, unproven atomic helper, prerequisite drift or any other result → STOP and record blocker.

## Acceptance matrix and run ownership

Require all 13 named native cases plus AS consumer (14/14), with assertions after every relevant callback:

| Name under `Ck.HexGrid.Placement.` | Mandatory measured behavior |
| --- | --- |
| `PreviewAndFailureReasons` | Preview has zero writes/IDs; malformed/default/stale inputs total; each listed failure surfaced with correct cells, no success signal. |
| `SameDrainConflict` | Two same-cell Place commands: first succeeds, second Occupied; one owner, two terminal results; reversing order reverses winner. |
| `MixedRulesOrdering` | Disable→Place rejects; enable→Place accepts; rule completion sees its own committed state. |
| `ReentrantSignal` | First signal sees exact current projection; nested request waits next drain; no simultaneous cell owner. |
| `RemoveThenReplace` | Remove ID A then fresh Place B in one drain releases first; fresh ID differs; reverse order rejects collision. |
| `SelfOverlappingMove` | Partially overlapping move preserves ID; old-only cells free, shared/new cells owned by same ID in callback. |
| `FailedReplacementRetainsOld` | Last-cell blocked/tag/collision/overflow failure retains ID, anchor, rotation, cells, record/backref/revision, no moved/removed signal. |
| `UniquenessAndTopologies` | Same occupant same board replacement retains ID; other hex board fails CrossGridTransfer; concurrent square membership untouched. |
| `ConnectivityAndHoleAnchor` | Six-direction connectivity, separated policy case, anchor in shape hole accepted when board member, outside-board anchor rejected even if offsets all fit. |
| `DeathOrders` | Occupant/placement/grid destruction each order; no leaked watches/record/cell owner; exactly one removal where board remains live; no use of stale ref. |
| `CancellationAndCompletion` | Destroy before drain and during callback cancel every remaining detached/queued request, typed+generic exactly once, failures agree, no false success. |
| `Readiness` | Fresh board immediately Ready; injected private pending blocks mutation/query with NotReady; Unavailable reports terminal cause; capture/private projection remains readable. |
| `ProjectionAtomicity` | Two anonymous internal records coexist by ID; duplicate ID/occupant or final overlap rejects entire projection and retains prior maps/reservations; public anonymous Place rejected. |
| `AS_Consumer` | A native CkTests editor-context wrapper executes the AS body via `FCk_Latent_RunAsTestOnAllWorlds` in a real PIE world and requires terminal success. Native-created real board/object invokes preview/Place/Move/Remove, result FGuid survives readback, typed placement handle .H()/validity works, generic completion agrees. |

Exact final filter: `Ck.HexGrid.Placement.`. Executor owns one incremental C++ build and one fresh filtered final boot. A second boot is budgeted only for a demonstrated runtime defect; announce actual count/reason first. No extra boot for each compile error. Accepting session owns the later wide square/persistence/net acceptance invocation; do not both pay for it. Keep BP parity as explicit [EDITOR-VERIFY] evidence or pending, never infer it from source alone.

Exit: record command/output/log paths, selected counts/names, state/signal/completion assertion results, files changed, generated binding status, pending BP evidence and remaining risks in `PROGRESS.md`. P4 becomes accepted only after acceptance review, P5 next. Blocked means preserve work, record exact failing contract and stop this session; do not improvise cross-board transfer, repair via delayed reconciliation, add indefinite readiness wait or start P5.

## Rejected approaches

* Public raw stamps, synchronous success before cell ownership, and eventual Record reconciliation as admission: allow same-drain double claims; rejected.
* Occupant identity as placement identity: collapses anonymous reservations and cannot retain durable moves/removes; rejected.
* Remove-old-then-validate-new: destroys valid placement on failed replacement; rejected.
* Sharing square backref or changing square timing: violates independent topology membership and compatibility; rejected.
* Returning a placement handle synchronously from deferred Place: invents provisional identity and encourages acceptance inference; chainable board return plus terminal typed result is the documented request convention.
* Polling empty projection as readiness, permanent restored marker, arbitrary boot waits, or unchecked mutation from net Apply: reserved for P5/P6's verified construction/hydration policy, not a substitute for it.
