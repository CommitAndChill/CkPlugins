# Phase 2 — Real board/cell entities, shared authoring factory and three-surface fixture

Status: planned. This document specifies future work and claims no compiled or rendered implementation.

## Acceptance rubric and phase boundary

Create these exact native automation rows under `Ck.HexGrid.Board.`:

| Row suffix | Required observations |
| --- | --- |
| `DomainAndRegistry` | Disk 0/1/2 and explicit negative/hole masks produce 1/7/19 and exact listed cells; stable `(r,q)` enumeration; real, distinct generational handles; two boards have disjoint registries even at identical coordinates. |
| `FactoryAtomicity` | TryAdd composes supplied Transform owner; TryCreate creates a distinct child. Invalid final disabled/tag coordinate, duplicate override, bad layout/domain/transform and limit excess produce invalid output with zero published cells/pivot/child leases/callbacks. Failed TryAdd preserves pre-existing owner features. |
| `AuthoringProductionPath` | Invoke the actual shared authoring resolver/factory used by the native EntityScript. Default tags, per-cell tags and disabled declarations agree with direct Spec construction. Real EntityScript/spawner path is separately exercised; hand-copying its post-Add loops is insufficient. |
| `PickingAndOutline` | Both orientations, all six edges/vertices, boundary and hole; transforms and ray/point rejections use Phase 1 winner/tolerances; world corners enclose the picked polygon and AABB is built from its vertices. |
| `OwnershipAndTeardown` | Coordinate/owning-grid readback uses stored data, not entity-number arithmetic. Destroy board, pump normal lifetime processing, then old grid/cell handles are stale and queries fail safely. Destroy/recreate never resurrects old cells. |
| `ThreeSurfaceFixture` | Native fixture executes public construction/enumeration/pick/teardown; AS consumer executes same API with both utils and valid mixin call forms. Blueprint execution evidence is required separately, not inferred from the native row's name. |

Phase 2 implements **layout composition** only: cells, immutable layout/domain, initial tags/disable state and spatial queries. `Has` says the typed feature is composed; it says nothing about multiplayer baseline, saved state, free cells or gameplay writes. Placement and blockers arrive later; persisted/network **state readiness** is implemented in Phases 4–6. Do not add a temporary always-ready flag, `Get_FirstAvailable`, empty occupancy answer or future readiness enum that consumers could mistake for hydrated gameplay state.

## Entry criteria and source context

Phase 1 is recorded complete with geometry symbols/tests/logs. Inspect current root/Foundation/CkTests status and preserve unrelated work in this checkout. If geometry has changed since its final gate, run its affected focused gate separately from this phase's literal Toolbox filter, per VALIDATION; otherwise do not pay for a duplicate baseline. No alternate checkout/worktree, clean rebuild or artifact deletion.

Read host/Foundation instructions and `Plugins/CkFoundation/DEVELOPMENT.md:257-355`, `Source/ARCHITECTURE.md:480` asset ownership section, `Script/AGENTS.md:1-5`, `Script/ARCHITECTURE.md`, plus canonical Foundation `ck-macros-and-codegen`, `ck-angelscript-interop`, `ck-change-control`, `ckecs-architecture-contract` skills and CkTests authoring instructions before editing. Load build-test before Toolbox.

| Actual source anchor | Why it matters / caller contract |
| --- | --- |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Grid/Ck2dGridSystem_Utils.cpp:29-99` | Pivot/cell composition, Add vs distinct-child Create; hex must preflight before allocation rather than clone this order blindly. |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Grid/Ck2dGridSystem_Fragment.h:39-67` and `.cpp:7-32` | Heap-owned noncopyable FEcsWorld; grid private registry idiom. |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Cell/Ck2dGridCell_Utils.cpp:14-48,62-90` | Lifetime owner setup and unsafe-to-generalize entity-number coordinate derivation. Hex stores coordinate and owner explicitly. |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Cell/Ck2dGridCell_Fragment.h:21-28` | Counted disable tag precedent. Avoid untracked direct enable/decrement once blockers exist. |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Grid/Ck2dGridSystem_Utils.h:17-41,58-86` | Typed handle cast macros, ScriptMixin arg0 and reflected factory patterns. |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Authoring/Ck2dGridSystem_Spec.h:37-71` and `Ck2dGridSystem_EntityScript.cpp:20-68` | Square authoring fields and post-compose loops; hex must reject a bad final declaration before publishing. |
| `Plugins/CkTests/Script/CkGrid/CkAutoTest_Grid_AuthoringSpecToRuntime.as:12-28` | Existing test explicitly bypasses real authoring due inaccessible properties; do not reproduce that test gap. |
| `Plugins/CkTests/Source/CkTests/Private/UnitTests/CkGrid_OccupancyScratch.spec.cpp:259-298` | Production transient owner/Net/PIE fixture composition and latent server action. Use relevant production setup, not a hand-built partial registry. |
| `Plugins/CkTests/Script/CkGrid/CkGridSystem_GymActor.as:37-80` | Existing spawner-driven gym construction; add separate hex fixture, leave square fixture unchanged. |
| `Plugins/CkTests/CLAUDE.md:31-67` | AS wrapper generation and map population; native/functional test names are different namespaces. |
| `Plugins/CkTests/Source/CkTests/Public/CkTests/Net/CkNetAutomation_Common.h:240-273` and `Private/Net/CkNetAutomation_Common.cpp:590-688` | Existing native-to-AS driver loads an AS class, spawns it in PIE worlds and polls terminal result fragments with a bounded timeout. |
| `Plugins/CkFoundation/.claude/skills/ck-angelscript-interop/references/generator-operations.md:5-23` | Generated utils and typed-handle registration lifecycle; no manual generated edits. |

Caller inventory: new geometry adapters, native/Blueprint/AS board fixtures, native authoring EntityScript, later footprint/placement/blocker code and Phase 7 editor dispatch. Existing CkInventory square utility calls, square EntityScript, square tests, editor tool and snapshot payloads must remain untouched.

## Owned files

Create under `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/HexGridSystem/`:

- `Grid/CkHexGrid_Fragment_Data.h/.cpp` — typed grid handle, Spec, board/query failures and debug options.
- `Grid/CkHexGrid_Fragment.h/.cpp` — immutable Params residue, private world/index/ordered handles, composition storage.
- `Grid/CkHexGrid_Utils.h/.cpp` — factories, preflight, typed lookup, geometry adapters and debug drawing.
- `Cell/CkHexCell_Fragment_Data.h/.cpp` — typed cell handle and reflected readback types only as needed.
- `Cell/CkHexCell_Fragment.h/.cpp` — coordinate/owner, tags, counted disable contribution.
- `Cell/CkHexCell_Utils.h/.cpp` — safe typed readback; cell creation private to grid factory.
- `Authoring/CkHexGrid_Spec.h/.cpp` — native authoring DataAsset and shared reflected resolver.
- `Authoring/CkHexGrid_EntityScript.h/.cpp` — real spawner adapter and construction rollback.

Also create `Plugins/CkFoundation/Source/CkGrid/Private/Tests/Test_HexGrid_Board.cpp`, `Plugins/CkTests/Script/CkGrid/CkHexGrid_BoardFixture.as`, `Plugins/CkTests/Script/CkGrid/CkHexGrid_GymActor.as`, `Plugins/CkTests/Source/CkTests/Private/UnitTests/CkHexGrid_Board.spec.cpp`, and Blueprint fixture `Plugins/CkTests/Content/CkGrid/HexGrid/BP_HexGrid_BoardFixture.uasset`. Script fixture is a `UCk_AutoTest_Base` consumer driven by the native named board row through `FCk_Latent_RunAsTestOnAllWorlds`; do not separately execute an equivalent mapped functional row in this phase. Generated `utils_hex_grid.as`, `utils_hex_cell.as`, `_index.as`, `CkTests_AutoTestActors.as` and handle metadata are generator-owned output only. Inspect any auto-populated map/external-actor delta caused by the new wrapper and retain only that fixture's generated entries; do not sweep unrelated asset deltas into this phase.

No processor is required for pure composition/readback. If actual lifecycle integration requires an EndPlay processor, use `Grid/CkHexGrid_Processor.h/.cpp`, self-register in its cpp and record why FEcsWorld/lifetime destruction alone was insufficient. Do not add an idle per-tick scan. No editor module dependency or custom toolkit is needed for basic debug outlines.

## Exact data placement and public surface

Use `FCk_Handle_HexGrid` and `FCk_Handle_HexCell` declarations in their `*_Fragment_Data.h` files with native make/break and typesafe formatter/validity macros. Register dynamic AS handle support through existing generator conventions; both `ck::IsValid` and `.H()` must work in the AS fixture. No square handle alias/cast is valid.

`FCk_HexGrid_Spec` fields: `FCk_HexLayout _Layout`, `FCk_HexDomain _Domain`, `FTransform _Pivot=Identity`, `FGameplayTagContainer _DefaultCellTags`, `TArray<FCk_HexCoord> _InitialDisabledCells`, `TArray<FCk_HexCellTagOverride> _PerCellTags`. `FCk_HexCellTagOverride` is reflected `{Coordinate, Tags}` with house accessors. Use an array so UHT/AS need not expose a custom-key map; reject duplicate coordinate overrides. All listed fields use reflected private properties and essential constructors per DEVELOPMENT. Authoring grouping is Board Shape/Layout/Initial Cells; Phase 3 adds Named Blockers/Placement Rules in its own slice.

Spec dissolves during factory call. Immutable Params retain only layout and default-tag policy actually queried later; canonical domain lives once in the index/ordered cells, not duplicated as the unexpanded Spec. Cell coordinate/owner live in one immutable identity fragment; cell tags and counted disable state live in runtime fragments/tags, never mirrored in Params. No Tunables fragment is justified; debug colors, line width, duration and selected outline are per-call presentation options, never gameplay state. Mesh/material assets are optional separate presentation and must not load during headless composition.

`UCk_Utils_HexGrid_UE : UBlueprintFunctionLibrary` uses `UCLASS(NotBlueprintable,meta=(ScriptMixin="FCk_Handle_HexGrid"))`. Factory first args are base/Transform handles and are called through static utils; board query first args are the typed grid and get valid mixins. All listed calls are UFUNCTION BlueprintCallable (Has may be BlueprintPure), Category `Ck|Utils|HexGrid`, explicit DisplayNames, output refs as output pins:

```cpp
enum class ECk_HexBoardFailure : uint8
// None, InvalidHandle, AlreadyComposed, InvalidSpec, CapacityExceeded, CompositionFailed,
// MissingCell, InvalidDirection, CoordinateOverflow, UnsupportedTransform, SpatialQueryFailed

bool TryAdd(UPARAM(ref) FCk_Handle_Transform& InOwner, const FCk_HexGrid_Spec& InSpec,
    FCk_Handle_HexGrid& OutGrid, ECk_HexBoardFailure& OutFailure);
bool TryCreate(UPARAM(ref) FCk_Handle& InOwner, const FTransform& InInitialTransform,
    const FCk_HexGrid_Spec& InSpec, FCk_Handle_HexGrid& OutGrid,
    ECk_HexBoardFailure& OutFailure);
bool Has(const FCk_Handle& InHandle);
bool TryGet_CellAt(const FCk_Handle_HexGrid& InGrid, const FCk_HexCoord& InCoordinate,
    FCk_Handle_HexCell& OutCell, ECk_HexBoardFailure& OutFailure);
bool TryGet_NeighborCell(const FCk_Handle_HexGrid& InGrid, const FCk_HexCoord& InFrom,
    ECk_HexDirection InDirection, FCk_Handle_HexCell& OutCell, ECk_HexBoardFailure& OutFailure);
TArray<FCk_Handle_HexCell> Get_Cells(const FCk_Handle_HexGrid& InGrid);
bool TryGet_CellFromWorldPoint(const FCk_Handle_HexGrid& InGrid, const FVector& InPoint,
    FCk_Handle_HexCell& OutCell, ECk_HexGeometryFailure& OutSpatialFailure,
    ECk_HexBoardFailure& OutFailure);
bool TryGet_CellFromWorldRay(const FCk_Handle_HexGrid& InGrid, const FVector& InOrigin,
    const FVector& InDirection, FCk_Handle_HexCell& OutCell, FVector& OutWorldHit,
    ECk_HexGeometryFailure& OutSpatialFailure, ECk_HexBoardFailure& OutFailure);
bool TryGet_CellWorldCenter(const FCk_Handle_HexGrid& InGrid, const FCk_HexCoord& InCoordinate,
    FVector& OutCenter, ECk_HexBoardFailure& OutFailure);
bool TryGet_CellWorldCorners(const FCk_Handle_HexGrid& InGrid, const FCk_HexCoord& InCoordinate,
    TArray<FVector>& OutCorners, ECk_HexBoardFailure& OutFailure);
void DebugDraw_Grid(const FCk_Handle_HexGrid& InGrid,
    const FCk_HexGrid_DebugDraw_Options& InOptions);
```

`TryGet_NeighborCell` requires a present source and target. Use P1 integer neighbor math. Domain holes and edges return MissingCell, malformed directions return InvalidDirection, and unrepresentable targets return CoordinateOverflow. Cover all six neighbors, the boundary, a hole and failure outputs in DomainAndRegistry. `Get_Cells` on invalid/stale grid returns empty and never dereferences it. Try* false outputs reset; `None` only on true. Spatial-query failure preserves its precise geometry reason alongside board SpatialQueryFailed; absent winner is board MissingCell plus geometry OutsideDomain. Invalid grid gives InvalidHandle and spatial None; it is not a spatial miss. Unsupported parent transform gives UnsupportedTransform; integer lookup still succeeds. Debug drawing on invalid/unsupported input draws nothing and must use the safe geometry adapters.

`UCk_Utils_HexCell_UE` uses the analogous typed ScriptMixin. Expose `bool TryGet_Coordinate(const FCk_Handle_HexCell&, FCk_HexCoord&)`, `bool TryGet_Grid(const FCk_Handle_HexCell&, FCk_Handle_HexGrid&)`, `bool TryGet_Tags(const FCk_Handle_HexCell&, FGameplayTagContainer&)`, `bool TryGet_IsDisabled(const FCk_Handle_HexCell&, bool&)`. False clears output; true TryGet_Tags returns union of default and cell tags. These are reads only. Coordinate and grid outputs are validated against owning registry/version; no CastChecked on an unchecked lifetime owner. Use normal Has/Cast/invalid handle macro surface consistent with square precedent; do not expose public cell Create or raw registry mutation.

`UCk_HexGrid_AuthoringSpec : UDataAsset` holds one reflected `FCk_HexGrid_Spec _Spec`. Its reflected resolver `bool TryResolve(FCk_HexGrid_Spec& OutSpec, ECk_HexBoardFailure& OutFailure) const` calls the same native preflight used by factories. `UCk_HexGrid_EntityScript : UCk_GenericEntityScript_UE` holds `_Spec` asset reference and injected property named exactly `SpawnTransform`; Construct resolves and calls TryAdd on the supplied owner, never manually stamps post-Add exceptions. A test-accessible reflected spawn/asset input through existing spawn-param conventions must drive this real path. Keep the loaded asset strongly owned through resolution if soft loading is necessary; no raw pointer from a temporary loader result. The production direct Spec factory requires no asset at all.

## Numbered execution steps and decision gates

1. Add reflected types and native preflight. Resolve/validate complete domain/layout/pivot, every initial-disabled coordinate, every per-cell tag reference and override duplication before creating a pivot, registry, child or publishing callbacks. Enforce provisional 65,536 ceiling from Phase 1 and actual FEcsWorld/entity allocator capacity. Do not reserve/allocate based on unchecked authored counts. Invalid external Spec is an ordinary typed failure in Shipping. Internal composition invariants use total side-effect-safe ensures with failure return/rollback inside the ensure body.

   Gate: FactoryAtomicity malformed-final-entry cases produce zero grid additions and unchanged pre-existing owner feature/lifetime counts. If any partial feature/cell/child exists → repair staging/rollback before step 2; anything else → stop and record.

2. Implement one private commit path shared by TryAdd/TryCreate/authoring. Stage private FEcsWorld, map `TMap<FCk_HexCoord,FCk_Handle_HexCell>`, stable ordered handle array and validated immutable values; every map value is an actually allocated generational handle. Compose identity/tag/initial counted disable state before publishing grid Has/callback visibility. TryCreate validates before child allocation; rollback any child created on later internal failure. TryAdd rollback removes only fragments/pivot introduced by this attempt. Owner already composed → AlreadyComposed, never return/reconfigure old grid silently.

   Do not derive a cell from `Coordinate -> numeric entity ID` or reverse it. Attach lifetime owner via production lifetime APIs and store grid ownership explicitly. Two private registries can have identical local entity numbers; their worlds/generations remain distinct. Use the nonmovable-world heap ownership pattern, not copied FEcsWorld. Preserve owner Net Info where production fixture uses it; do not add unrelated fake fragments to bypass prerequisites.

   Gate: DomainAndRegistry and OwnershipAndTeardown prove actual owners/handles, two-world isolation and full retirement after normal lifecycle pumping. Stale readback must not ensure/crash; any other outcome → stop.

3. Add spatial wrappers and debug outline. Read current SceneNode pivot transform for every world query; a later unsupported parent transform rejects spatial calls while integer membership remains valid. Reuse Phase 1 picking and only then query membership. Return actual six transformed corners; build bounds from all vertices. Draw wire hexes with a distinct picked-cell outline, coordinate labels optionally; no rectangle surrogate. Debug options own colors, FCk_Time duration and line thickness (explicit engine-unit boundary). Do not create a custom UI or mesh asset dependency.

   Gate: PickingAndOutline compares an independent polygon oracle for both orientations, all six edges/vertices, transformed grids, outside and holes; exact tie missing winner remains missing. Any helper duplication → replace with Phase 1 call; other failure → stop.

4. Add native asset/EntityScript adapter with the shared preflight/commit path, then drive actual authored construction plus direct construction from native and AS. In Phase 2 the Spec has no blocker declarations. Phase 3 adds them to preflight/staging **before** any published cells; it must add a bad-final-blocker fixture then. Phases 4–6 may add versioned recipe and readiness fields later; do not predeclare an unimplemented persisted identity here.

   Gate: AuthoringProductionPath proves asset-to-EntityScript-to-factory, not just an AS reconstruction of field mapping. Missing/inaccessible spawn input → add explicit reflected testable production input using existing entity-script conventions, not a testing-only friend bypass. If asset loader cannot retain ownership safely → stop and record. Never silently skip invalid tag/disabled coordinates.

5. Build the basic three-surface fixture. One canonical radius-2 disk at radius 100 and one explicit mask with `(0,0)` removed; run both orientations under identity and rotated/translated/scale-2 pivots. Native and AS construct/enumerate/pick/read corners and coordinate/tags/state, retain a cell, then destroy board and demonstrate false stale queries. AS must compile and execute static factory and typed query mixin forms, plus `ck::IsValid` and `.H()`. Define `UCk_HexGrid_BoardFixture : UCk_AutoTest_Base`, drive it from `DoBeginPlay`, and call FinishSuccess only after all checks including normal lifecycle teardown; FinishFailure on any failed assertion. Native `ThreeSurfaceFixture` starts one PIE world, waits ready, calls `FCk_Latent_RunAsTestOnAllWorlds(this, TEXT("/Script/Angelscript.Ck_HexGrid_BoardFixture"), 30.0f)`, and ends/waits for all PIE worlds. The existing helper loads the class and polls a terminal result; do not pass if class loading, construction or completion is absent. This exercises no multiplayer state claim despite the helper's Net namespace.

   `[EDITOR-VERIFY]`: create/compile/save/run BP_HexGrid_BoardFixture using the same public factory, enum/make pins, array output, point/ray pick, corner readback and teardown. Record graph screenshot, output values and result. Gym toggles pointy/flat at reconstruction, moves the board, picks at all six edges, highlights exact polygon and shows holes; no live retopology mutation. Screenshot computed outline on each orientation and include failing outside/hole picks. If editor access is unavailable, leave manual gates pending and do not mark phase accepted.

6. Normalize diff before final build. Follow [VALIDATION.md § Running a gate](VALIDATION.md#running-a-gate), exact phase filter `Ck.HexGrid.Board.`, output stem `hex-grid-phase-2`. Plan **one fresh final test boot** after incremental C++ build; it also runs AS compilation/generation. Binding bootstrap may need a second boot only with explicit logged self-heal evidence; report it before launching. Fix every compiler/UHT error before boot. Native tests in Foundation and real-world/AS driving tests in CkTests share this prefix, with unique row names from the acceptance table. Do not silently substitute `Project.Functional Tests.*` or a broad CkGrid filter. If the existing harness cannot expose the named AS/native bridge row, stop and amend the harness plan explicitly before claiming discovery.

   Expected: all six named rows discovered/pass, AS fixture completion observed, fresh logs clean of unexpected ensures/AS errors. Missing row, no callback or zero tests → failure. If only new board code changed, do not run square persistence/multiplayer workloads here; accepting Phase 8 owns those. Known unrelated failure → retain outputs and record blocker; anything else → stop.

## Exit and recovery

Phase exits only with build/UHT and all six board rows passing, C++/AS runtime evidence, Blueprint/gym evidence (or explicitly pending human acceptance, which blocks acceptance), exact log/results paths, and reviewed generated deltas. Record checked safety ceiling, geometry tolerances, caller/symbol inventory and rollback accounting in `PROGRESS.md`; update status header. No save/net/placement readiness claim follows from a successfully composed board.

Keep rejected Specs and their zero-publish assertions as regression fixtures. A failed commit path may destroy its private staged world/pivot/child only; never destroy caller-owned pre-existing components or unrelated work. If FEcsWorld teardown, retained handles or parent lifetime behavior contradict assumptions, capture exact source/log evidence and consult Astra before changing lifetime architecture. Two attempted fixes with the same symptom → stop before a third, follow stuck protocol and continue only safe independent work. Never evade locks with another checkout or remove generated/build directories.
