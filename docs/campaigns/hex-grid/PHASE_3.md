# Phase 3 — Object footprints, cell rules and named blocker votes

This is an implementation handoff, not evidence that implementation or tests exist. Work only in the selected CkPlugins checkout; do not create another checkout, worktree, clone or repository copy. Implement this phase only. The scored acceptance matrix below is the executable-spec substitute: planning is documentation-only, so no red test or Unreal boot was performed by the planner.

## Entry and required reading

1. Read root `AGENTS.md`, `Plugins/CkFoundation/AGENTS.md:1-45`, `Plugins/CkFoundation/Source/AGENTS.md:1-5`, `Plugins/CkFoundation/DEVELOPMENT.md:242-427`, and the canonical `.claude/skills/ck-macros-and-codegen/SKILL.md`, `ck-change-control/SKILL.md`, `ckecs-architecture-contract/SKILL.md`, `ck-angelscript-interop/SKILL.md` under Foundation. Before tests read `Plugins/CkTests/CLAUDE.md` and its `Script/Common/` test specification. Use `CkAuto/.claude/skills/build-test/SKILL.md` before Toolbox.
2. Inspect `git status --short` from the root and Foundation/CkTests submodules. Preserve unrelated edits and staged work. Check `docs/campaigns/hex-grid/PROGRESS.md`: phases 1 and 2 must be accepted, phase 3 next. Verify P1 geometry and P2 board suites recorded there passed on their delivered source. If missing or a required API differs, STOP and record an interface blocker; do not invent an adapter architecture.
3. Use the existing authorized feature branch, or create `feature/hex-grid` **in place** only when phase ownership and checkout state permit it. Do not checkout another branch over somebody else's changes. Do not commit, push, bump gitlinks or change integration branches unless the executor's user explicitly requests delivery.

## Source and caller inventory

Read these precise existing anchors before editing; they explain patterns and failure traps, not behavior to copy wholesale:

| Source | Purpose |
| --- | --- |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Object/Ck2dGridObject_Fragment_Data.h:27-65`, `Ck2dGridObject_Utils.cpp:15-110` | Reflected typed object, immutable params, rectangular resolver; hex must avoid extent normalization and empty success. |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Blocker/Ck2dGridBlocker_Utils.cpp:20-76`, `:137-171` | Label-before-record connect and exact release on death. |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Blocker/Ck2dGridBlocker_Processor.cpp:23-135`, `Ck2dGridBlocker_Processor.h:51-95` | Registered processor, queue drain and EndPlay; square coalesces requests before applying state and cannot supply hex ordered-observation semantics. |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Cell/Ck2dGridCell_Utils.cpp:95-214` | Effective tags and counted disable precedent; hex owns contributor state rather than exposing unmatched decrement. |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Authoring/Ck2dGridSystem_Spec.h:14-71`, `Ck2dGridSystem_EntityScript.cpp:44-71` | Existing authoring schema and consumers; hex rejects the entire authored batch instead of skipping bad references. |
| `Plugins/CkFoundation/Source/CkEcs/Public/CkEcs/Request/CkRequest_Completion.h:15-126` | Completion results/guard/cancellation. |
| `Plugins/CkFoundation/Script/Generated/utils_2d_grid_blocker.as:1-70`, `utils_2d_grid_object.as:1-70` | Generated wrapper shapes; never hand-edit these templates. |
| `Plugins/CkTests/Script/CkGrid/CkAutoTest_Grid_BlockerTwoOverlapRefcount.as:1-90`, `CkAutoTest_Grid_TagFilter.as:1-100`, `CkAutoTest_Grid_TagFilterForbidden.as:1-121` | Existing square regression callers. Preserve unchanged. |

Edit/add only the following production slice plus tests/generated outputs genuinely required by it. Paths below are relative to `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/HexGridSystem/`:

* `Object/CkHexGridObject_Fragment_Data.h/.cpp`, `_Fragment.h`, `_Utils.h/.cpp`: typed handle, immutable spec, explicit resolver.
* `Blocker/CkHexGridBlocker_Fragment_Data.h/.cpp`, `_Fragment.h`, `_Utils.h/.cpp`: typed contributor state, record, label, request type, lifetime release.
* `Grid/CkHexGrid_Fragment.h`, `_Processor.h/.cpp`: board-owned FIFO of rule commands, registered authority drain and EndPlay cancellation. Extend P2 files; no second independently ordered blocker drain.
* `Cell/CkHexCell_Fragment.h`, `_Utils.h/.cpp`: base blocked bit, one manual blocked bit, contributor votes, effective tags and queries.
* `Authoring/CkHexGrid_Spec.h/.cpp`, `CkHexGrid_EntityScript.h/.cpp`: extend P2 native authoring with cell rules and named blockers; preserve atomic publication.
* `Authoring/CkHexGridObject_Spec.h/.cpp`, `CkHexGridObject_EntityScript.h/.cpp`: native UDataAsset/object EntityScript pair using the same resolver as headless callers.
* `Plugins/CkFoundation/Script/Generated/utils_hex_grid_object.as`, `utils_hex_grid_blocker.as`, `utils_hex_cell.as`, `utils_hex_grid.as`: generated changes only. Keep dynamic/static handle registration following the existing generator; inspect `Source/CkEcs/Public/CkEcs/Handle/CkHandle_TypeSafe_AngelScript.h:29-89` if conversions fail.
* New native tests `Plugins/CkFoundation/Source/CkGrid/Private/Tests/Test_HexGrid_Rules.cpp`, and AS consumer `Plugins/CkTests/Script/CkGrid/HexGrid/CkAutoTest_HexGrid_Rules.as` (driven by a new native CkTests editor-context row `Ck.HexGrid.Rules.AS_Consumer` using `FCk_Latent_RunAsTestOnAllWorlds` with one actual PIE world, its AS class path, explicit terminal assertions and timeout).

No square API, save schema, replication payload, editor module or inventory consumer changes belong here.

## Fixed data and API contract

Use `USTRUCT(BlueprintType)`, `CK_GENERATED_BODY`, private reflected `UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(AllowPrivateAccess=true))`, `CK_PROPERTY` for specs and `CK_PROPERTY_GET` for results. Handles live in `_Fragment_Data.h` with the standard type-safe macros. Specs are immutable after Add; runtime rule state belongs in state fragments. Use `FCk_HexCoord`/`ECk_HexRotation` from P1 exclusively.

```cpp
enum class ECk_HexGridConnectivity : uint8 { Ignore, RequireConnected };
// Fields, with defaults (not a literal replacement for required house macros):
FCk_HexGridObject_Spec {
    TArray<FCk_HexCoord> FootprintOffsets; // default [{0,0}]
    FGameplayTagContainer RequiredCellTags;
    FGameplayTagContainer ForbiddenCellTags;
};
FCk_HexGridObject_ResolveResult {
    bool Succeeded = false;
    ECk_HexGridObject_Failure Failure; // None, InvalidOwner, AlreadyComposed, CompositionFailed, InvalidObject, EmptyFootprint,
                                      // DuplicateOffset, InvalidRotation, Overflow, TooManyCells,
                                      // InvalidConnectivity, Disconnected
    TArray<FCk_HexCoord> Cells;         // empty on failure; sorted (r,q) on success
};
FCk_HexGridBlocker_Spec {
    FCk_Handle_HexGrid Grid;
    TArray<FCk_HexCoord> Cells; // exact board coordinates, not an axial rectangle
    FGameplayTag Name;         // optional; nonempty names unique per board
    bool InitiallyActive = true;
};
```

`UCk_Utils_HexGridObject_UE` (`ScriptMixin="FCk_Handle_HexGridObject"`) exposes:

```cpp
static bool TryAdd(UPARAM(ref) FCk_Handle& InHandle,
    const FCk_HexGridObject_Spec& InSpec, FCk_Handle_HexGridObject& OutObject,
    ECk_HexGridObject_Failure& OutFailure);
static bool TryCreate(UPARAM(ref) FCk_Handle& InOwner,
    const FCk_HexGridObject_Spec& InSpec, FCk_Handle_HexGridObject& OutObject,
    ECk_HexGridObject_Failure& OutFailure);
static bool Has(const FCk_Handle& InHandle);
static FCk_HexGridObject_ResolveResult TryResolve_Cells(
    const FCk_Handle_HexGridObject& InObject, const FCk_HexCoord& InAnchor,
    ECk_HexRotation InRotation, ECk_HexGridConnectivity InConnectivity);
static FCk_HexGridObject_Spec Get_Spec(const FCk_Handle_HexGridObject& InObject);
```

These are UFUNCTIONs: Add/Create BlueprintCallable, Has/resolver/getters BlueprintPure; failures ordinary result branches in all builds. TryCreate validates before creating the child. Resolve uses P1 checked rotation/translation, no corner rebasing, canonical output, nonempty distinct input, and the same bounded cell-count limit as P1 domain materialization. Offsets **need not include (0,0)**; an anchor can sit in a footprint hole. Domain membership is a placement concern in P4. RequireConnected means the footprint's own six-edge induced graph is connected; Ignore permits separated islands. It never means connection to an unrelated placed object.

`UCk_Utils_HexGridBlocker_UE` provides reflected `TryAdd(FCk_Handle&, const FCk_HexGridBlocker_Spec&, FCk_Handle_HexGridBlocker& OutBlocker, ECk_HexGridBlocker_Failure& OutFailure)->bool`, corresponding `TryCreate` with the same output convention, `Has`, `Get_Grid`, `Get_BlockedCells`, `Get_IsActive`, `Get_Blockers(Grid)`, and `Get_BlockerWithTag(Grid,FGameplayTag)`. Failure enum: `None, InvalidGrid, InvalidOwner, AlreadyComposed, CompositionFailed, EmptyCells, DuplicateCell, OutsideDomain, DuplicateName, NotAuthority, Unavailable`. Empty named lookup returns invalid; never choose arbitrarily among duplicates. `Request_SetActive(UPARAM(ref) FCk_Handle_HexGridBlocker&, bool InActive, const FCk_Delegate_Request_OnCompleted& InDelegate)->FCk_Handle_HexGridBlocker` queues onto the **board's** FIFO and carries the blocker target. Generic completion stays the last parameter, no C++ default; `AutoCreateRefTerm="InDelegate"`. This chainable return is the submitted target, not a success indication.

`UCk_Utils_HexCell_UE` keeps P2's `TryGet_Tags` (effective defaults union current local tags) and `TryGet_IsDisabled` (effective blocked count > 0). Add `TryGet_LocalTags(Cell, OutTags)->bool` for inspecting the mutable local contribution. False clears outputs. `Request_SetBlocked(Cell&, bool, Completion)->FCk_Handle_HexCell` owns one idempotent manual vote. `Request_AddTag`/`Request_RemoveTag` queue idempotent local tag changes. Each uses the same last-parameter completion contract. Invalid/stale cells must return/reject safely without interpreting a recycled child entity index as a coordinate.

Authoring additions are fixed: `FCk_HexGridAuthoredBlocker` is a reflected value with `{TArray<FCk_HexCoord> Cells, FGameplayTag Name, bool InitiallyActive=true}` and house accessors. Add `TArray<FCk_HexGridAuthoredBlocker> _Blockers` to `FCk_HexGrid_Spec` inside the board AuthoringSpec's existing `_Spec` property. Its Cells are exact addresses in the already-resolved domain; no clipping or independent shape math. `UCk_HexGridObject_AuthoringSpec : UDataAsset` owns one reflected `FCk_HexGridObject_Spec _ObjectSpec` and exposes `Get_ObjectSpec`. `UCk_HexGridObject_EntityScript` owns soft `Spec` asset reference under existing loader/GC rules and composes through the public TryAdd resolver. A null, missing or malformed asset installs no object feature. After construction settles, callers read the feature-specific result from `Get_ObjectFailure()`. The generic EntityScript constructed notification may still fire on rejection. Use the framework's actual asset construction/loader pattern, never a synchronous asset load in a runtime getter.

During prepublication board construction, stage authored blocker contributions in the same factory transaction. Once published, TryAdd/TryCreate for runtime blockers validates and composes an inactive contributor with an ID and a pending activation request in the same board FIFO if InitiallyActive was requested. A successful factory return proves composition. Its votes become visible on the ordered activation commit. Get_IsActive reflects the committed vote. A failed enqueue rolls back that composition; destruction of a pending contributor safely cancels its activation. Reentrant construction can never change already-observed cell votes before its turn. Add this timeline to OrderedToggleCompletion. Disallow new public contributor composition on a waiting, destroying, non-authoritative or unavailable board.

Each board-FIFO entry retains its original completion owner separately from the board hosting the queue: blocker SetActive completes against the blocker, cell mutation against the cell. If target dies before drain, cancel that entry once even when board remains live. Add the concrete `FCk_Request_HexGridBlocker_SetActive`, `FCk_Request_HexCell_SetBlocked`, `FCk_Request_HexCell_AddTag`, `FCk_Request_HexCell_RemoveTag` types in their feature's `_Fragment_Data.h`, each deriving `FCk_Request_Base`, with exact datum and target encoded in the private queued wrapper. All future P4 placement requests complete against the board, so extending the FIFO never changes P3 completion ownership.

Blueprint exposes the same result fields and enum failure pins; use `UPARAM(ref)` for mutable owner inputs. AS generated namespaces are `utils_hex_grid_object`, `utils_hex_grid_blocker`, `utils_hex_cell`. Required smoke expressions:

```angelscript
ECk_HexGridObject_Failure Failure;
FCk_Handle_HexGridObject Obj;
const bool Added = utils_hex_grid_object::TryAdd(Owner, ObjectSpec, Obj, Failure);
// Branch on Added before using Obj. Failure clears the typed output.
auto Resolved = utils_hex_grid_object::TryResolve_Cells(
    Obj, Anchor, Rotation, ECk_HexGridConnectivity::Ignore);
Blocker.Request_SetActive(false); // generated optional generic completion
// Explicit Has / IsValid and .H() must compile for both new handle types.
```

## Numbered implementation and decision gates

1. Add production-path native tests for the matrix below, initially demonstrating absence/failure of the planned feature where compilation permits. Do not boot an intentionally uncompilable tree. Capture source-level missing-symbol baseline instead when necessary. Gate: named tests exercise public composition and real scheduler/lifetime, not manually fabricated fragments. If existing test infrastructure cannot run the required lifetime path, STOP with the precise missing harness.
2. Implement object validation before feature installation. Authoring uses the same immutable spec and resolver; a malformed shape creates zero object features/children. Gate: six rotations preserve cardinality and six turns recover every offset; overflow has an explicit failed result with empty cells. Any disagreement with P1 checked helpers → STOP, do not duplicate hex arithmetic.
3. Integrate all authored cell/tag/blocker references into P2's **prepublication validation**. Validate the complete list, including its final item, before publishing any cells, labels, records, signals or child leases. Duplicate blocker names reject; anonymous blockers may overlap. Base disabled cells exist in domain; excluded cells do not. Gate: a bad final blocker/tag reference leaves zero published board/cells/blockers/leases/callbacks. If P2 cannot roll back atomically, STOP and record the prerequisite defect.
4. Implement board FIFO and one authority rules processor. Snapshot/copy-remove the queue at drain entry; commands added by callbacks wait for the next drain. Apply each command fully before its completion. Never coalesce toggles if that hides intermediate committed states. SetActive(true) twice contributes one vote; false twice removes none beyond its own vote. Base blocked bit and manual vote survive blocker release. EndPlay releases only the contributor's recorded applied set and completes pending commands `Failed_Cancelled` once. Destroying board cancels outstanding commands without touching dead cell handles. Register processor/dependencies with canonical CK macros, exclude initiate-destroy owners. Gate: false→true→false in one drain produces observations false/true/false at each callback.
5. Generate wrappers via the normal startup/codegen route; do not patch generated .as files manually. Use the native, BP and AS same functions. [EDITOR-VERIFY] create an object authoring asset and board asset, compile a BP using TryAdd/resolve/failure enum and blocker query/toggle; observe explicit failure pins and six rotations. Record this as pending if no human/editor evidence exists; do not claim BP parity from UHT alone.
6. Normalize formatting before the final build/test gate. Use `VALIDATION.md#running-a-gate` exactly with the phase filter below. Fix **all** compiler/UHT/AS errors from a run before another boot. Gate branches: all expected tests selected and pass, zero unexpected ensures/script compile errors → exit; a specific failing matrix row → record its hypothesis and fix within budget; no tests selected, different APIs, unrelated dirty ownership, or unexplained fresh logs → STOP and update blockers.

## Measurable acceptance and verification budget

Every row scores 1 only with named assertions and recorded evidence; require 9/9:

| Automation name under `Ck.HexGrid.Rules.` | Assertions |
| --- | --- |
| `FootprintValidation` | Empty/duplicate/invalid rotation/checked overflow reject, zero children; hole anchor preserved; valid shape count unchanged under all turns. |
| `Connectivity` | All six neighbor directions connect; separated islands fail RequireConnected and pass Ignore; empty shape never succeeds. |
| `EffectiveTags` | Defaults union locals; hierarchical HasAll required/HasAny forbidden semantics; local removal cannot remove a default tag; every footprint cell inspected. |
| `AuthoredAtomicity` | Last invalid tag/blocked/blocker coordinate and duplicate named blocker reject entire board without partial published objects/records/callbacks. |
| `VoteOwnership` | Two blockers same cell, manual/base votes, release either order; destroy active/inactive/repeated toggle never underflows or frees another vote. |
| `OrderedToggleCompletion` | Three toggles in one drain each observe committed state, exactly one completion, repeat no-op Succeeded. |
| `TeardownAndCancellation` | Board/blocker first destruction in both orders; pending cancellation once; stale handle query safe; no leaked record/delegate. |
| `NamedQueries` | Unique names resolve correct handle; anonymous recorded; duplicate rejected without replacing existing label; dead entries absent. |
| `AS_Consumer` | Real object + authored board caller resolves/tag-queries/toggles, handles validate and .H() compiles. |

Exact executor filter: `Ck.HexGrid.Rules.`. Record selected counts (must include all nine names; additional parameterized cases allowed). Executor owns one incremental build plus one fresh final filtered boot. Budget a second boot only for a reproduced runtime failure; state boot count and reason before Toolbox. Accepting session owns the later wide square+hex integration gate, not a duplicate of this final invocation. No C++ clean rebuild, deletion of binaries/intermediate/DDC or Shipping run.

Exit: record changed files, command/output paths, test counts, log findings, generated binding result, BP evidence/pending status and risks in `PROGRESS.md`; mark P3 accepted only after the designated reviewer accepts these rows, then P4 next. Leave unrelated work intact. Any blocker: preserve current files, mark P3 blocked with exact failing row/source/error, end the executor session without proceeding to placement.

## Rejected approaches and fences

* Rectangle extents/normalized rotation lose authored hex pivot and holes: rejected.
* Unmatched raw disable increment/decrement lets callers release other contributors: rejected; named contributor owns its recorded set and active bit.
* A separate blocker drain beside placement's future drain makes mixed command order scheduler-dependent: rejected; one board FIFO is extended in P4.
* Skipping malformed authored entries publishes a successful subset: rejected; validate whole batch first.
* Copying square coalescing or changing square timing/public symbols broadens compatibility scope: rejected.
* Internal invariant failures use a total side-effect-free `CK_ENSURE_IF_NOT` with terminating cleanup inside its body; operational/user-data failures use ordinary typed branches. Never add empty ensures plus duplicate guards, and never alter Shipping check flags.
