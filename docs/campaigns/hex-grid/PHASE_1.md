# Phase 1 — Typed axial geometry, finite domains and picking

Status: planned; no implementation, build, test or editor evidence is claimed by this document.

## Executable acceptance specification

Implement the following native automation rows under the exact prefix `Ck.HexGrid.Geometry.`. They must exercise the proposed public Utils functions, with independent expected values rather than round trips alone.

| Row suffix | Required observations |
| --- | --- |
| `CoordinatesAndTurns` | Signed coordinates remain signed; neighbors are `(1,0),(0,1),(-1,1),(-1,0),(0,-1),(1,-1)`; positive turn is `(-r,q+r)`; all six turns and inverse pairs agree with literal expected tables; sixth turn is identity. |
| `DistanceOracle` | Independently enumerate six-edge BFS through radius 8: 217 unique cells, shells `1,6,12,…,48`; returned distance equals BFS depth. Include widely separated int32 endpoints and an int64 answer. |
| `DomainValidation` | Disk radii 0/1/2 produce 1/7/19 cells; explicit negative cells and a hole survive canonical `(r,q)` sorting. Reject empty explicit, duplicate, negative radius, invalid discriminant, inactive alternative data, count over limit, and center-plus-offset overflow. Every failed output array is empty. |
| `ProjectionOracle` | Both orientations: compare literal analytic centers/corners and polygon half-plane membership independently. Six corners are counterclockwise and use the same chart as centers. |
| `PickingBoundaries` | Center, all six edge midpoints, three-cell vertices, perturbations on both sides, domain boundary, explicit hole. Lattice tie winner is smallest `(q,r)`; a missing winner is a miss, never a substitute neighboring member. |
| `WorldProjection` | Translation, arbitrary rigid rotation and uniform scale 0.5/2; point plane tolerance; nonunit ray direction; origin-on-plane; parallel, zero direction and behind-origin rays. Nonfinite, singular, negative/reflected/nonuniform transforms fail without NaN outputs. |
| `ArithmeticAndPrecision` | int32 extremes, overflow before narrowing, invalid enum casts, nonfinite/zero/negative radii, nonfinite world points and enormous but finite inputs. Execute the concrete precision vectors below: ordinary large addresses pick successfully; extreme integer addresses remain valid integers even when precise spatial picking returns PrecisionLoss. No UB, unbounded allocation, clamp or wrap. |

These seven rows are new work, not existing tests. The acceptance rubric above stands in for an unimplemented red test in this planning-only package. Before implementation, record the test-discovery result; absence of these rows is expected, never a passing baseline.

## Entry and source context

1. Read the host `AGENTS.md`, `Plugins/CkFoundation/AGENTS.md:1-46`, `Plugins/CkFoundation/DEVELOPMENT.md:257-355`, `Plugins/CkFoundation/Source/ARCHITECTURE.md`, and `Plugins/CkFoundation/Source/CkGrid/Claude.md:1-31`. Use current files if anchors drift; record drift in `PROGRESS.md`.
2. Load canonical `.claude/skills/ck-macros-and-codegen/SKILL.md`, `ck-change-control/SKILL.md`, `ck-angelscript-interop/SKILL.md` inside Foundation, and the host `build-test` wrapper/canonical Toolbox skill before verification. Toolbox rules override illustrative raw-editor commands in older interop references.
3. Verify the selected checkout is the CkPlugins host; inspect root/Foundation/CkTests status in place. Preserve unrelated changes; never create another checkout, worktree, copy, or clean generated artifacts. Any conflicting owned-file edit → stop and record the exact conflict.

4. Preserve a pre-change square save and its expected state before the first feature build, following VALIDATION's compatibility manifest. Existing documented donor fixtures may satisfy this. Record provenance and any missing donor in PROGRESS.

Read these actual precedents before editing:

| Source anchor | Relevance / consumers |
| --- | --- |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/CkGrid_Utils.h` and `.cpp:72` | Cartesian math belongs to a separate API. Do not add hex meanings to these callers. |
| `Plugins/CkFoundation/Source/CkCore/Public/CkCore/Math/Geometry/CkGeometry_Types.h:70-123` | `FCk_Frame3D` holds a rigid plane frame; undo validated uniform scale separately. |
| `Plugins/CkFoundation/Source/CkGrid/Private/Tests/Test_2dGridSystem_Spec_Resolve.cpp:7-47` | Native automation registration/flags; keep square row unchanged. |
| `Plugins/CkFoundation/Source/CkGrid/Public/CkGrid/2dGridSystem/Grid/Ck2dGridSystem_Fragment_Data.h:1-25` | Reflected enum/value conventions, not a source of axial semantics. |
| `Plugins/CkFoundation/.claude/skills/ck-angelscript-interop/SKILL.md:45-90` | C++/Blueprint/AS checks are separate gates. |
| `Plugins/CkFoundation/.claude/skills/ck-angelscript-interop/references/generator-operations.md:5-23` | Boot-generated wrappers, single writer and no manual generated edits. |

Callers introduced here: native geometry tests and the Phase 2 board factories/query adapters. Later footprint resolvers and editor tools call this same surface. Existing square/inventory/shader callers remain unchanged; do not extract shared code merely to satisfy a sharing target.

## Owned file inventory

Paths below are relative to `Plugins/CkFoundation/` unless stated otherwise. Create only:

- `Source/CkGrid/Public/CkGrid/HexGridSystem/Geometry/CkHexGrid_Geometry_Data.h`
- `Source/CkGrid/Public/CkGrid/HexGridSystem/Geometry/CkHexGrid_Geometry_Data.cpp` (hash/formatter or out-of-line value operations only when needed)
- `Source/CkGrid/Public/CkGrid/HexGridSystem/Geometry/CkHexGrid_Geometry_Utils.h`
- `Source/CkGrid/Public/CkGrid/HexGridSystem/Geometry/CkHexGrid_Geometry_Utils.cpp`
- `Source/CkGrid/Private/Tests/Test_HexGrid_Geometry.cpp`
- Generator-owned `Script/Generated/utils_hex_geometry.as` and relevant `_index.as` delta, if generated/tracked under current project policy; never hand-author them.

No build-rule or module-descriptor change is needed: this remains the existing CkGrid module (`CkGrid.Build.cs:8-27` already has Core/Engine/CkCore/Ecs dependencies). If compilation demonstrates an actual missing dependency, stop and document it before widening ownership. Campaign evidence updates belong in `PROGRESS.md`.

## Fixed data and API contract

All value structs are `USTRUCT(BlueprintType)`, exported `CKGRID_API`, with private reflected `_Members`, `CK_GENERATED_BODY`, house getters/setters and essential constructors. Use multiline function formatting from DEVELOPMENT, not the condensed spec below. Reflected members have `UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(AllowPrivateAccess=true))`; no raw public storage. Hash and equality compare Q/R exactly.

```cpp
FCk_HexCoord                 // int32 _Q=0, _R=0; constructor(Q,R); Get_S() -> int64
ECk_HexOrientation : uint8   // Pointy, Flat
ECk_HexRotation : uint8      // Turn0, Turn1, Turn2, Turn3, Turn4, Turn5
ECk_HexDomainKind : uint8    // Disk, Explicit
FCk_HexLayout               // Orientation=Pointy; double OuterRadius=100 local Unreal units
FCk_HexDomain               // Kind=Disk; Center=(0,0); int32 RingRadius=0;
                            // TArray<FCk_HexCoord> Coordinates (empty by default)
ECk_HexGeometryFailure : uint8
// None, InvalidCoordinate, InvalidDirection, InvalidRotation, InvalidOrientation, InvalidLayout,
// InvalidDomain, DuplicateCoordinate, LimitExceeded, Overflow, PrecisionLoss,
// UnsupportedTransform, OffPlane, ParallelRay, BehindRay, OutsideDomain
```

`S=-int64(Q)-int64(R)` is derived, never redundantly serialized; every int32 Q/R pair is representable. Reflected `OuterRadius` is the documented geometry unit boundary, not a duration or a generic gameplay scalar. Disk mode requires empty Coordinates. Explicit mode requires Center `(0,0)`, RingRadius `0`, nonempty Coordinates. Reject contradictory inactive fields rather than quietly interpreting them. Use `EditCondition`/`EditConditionHides` to show only the selected alternative; programmatic input still validates both branches.

`UCk_Utils_HexGeometry_UE : UBlueprintFunctionLibrary` is `UCLASS(NotBlueprintable)`, with no handle ScriptMixin. Every method below is static `UFUNCTION(BlueprintCallable, Category="Ck|Utils|HexGeometry")`, with stable `[Ck][HexGeometry] …` DisplayName. Output references are output pins, not `UPARAM(ref)` input pins. Return `bool` and always set the failure enum. Do not overload names for different spaces.

```cpp
bool TryRotate(const FCk_HexCoord& InOffset, ECk_HexRotation InRotation,
    FCk_HexCoord& OutOffset, ECk_HexGeometryFailure& OutFailure);
bool TryGet_Neighbor(const FCk_HexCoord& InCoordinate, ECk_HexDirection InDirection,
    FCk_HexCoord& OutNeighbor, ECk_HexGeometryFailure& OutFailure);
bool TryTranslate(const FCk_HexCoord& InAnchor, const FCk_HexCoord& InOffset,
    FCk_HexCoord& OutCoordinate, ECk_HexGeometryFailure& OutFailure);
bool TryGet_Distance(const FCk_HexCoord& InA, const FCk_HexCoord& InB,
    int64& OutDistance, ECk_HexGeometryFailure& OutFailure);
bool TryResolve_Domain(const FCk_HexDomain& InDomain,
    TArray<FCk_HexCoord>& OutCoordinates, ECk_HexGeometryFailure& OutFailure);
bool TryGet_LocalCenter(const FCk_HexCoord& InCoordinate, const FCk_HexLayout& InLayout,
    FVector2D& OutCenter, ECk_HexGeometryFailure& OutFailure);
bool TryGet_LocalCorners(const FCk_HexCoord& InCoordinate, const FCk_HexLayout& InLayout,
    TArray<FVector2D>& OutCorners, ECk_HexGeometryFailure& OutFailure);
bool TryGet_CoordFromLocal(const FVector2D& InPoint, const FCk_HexLayout& InLayout,
    FCk_HexCoord& OutCoordinate, ECk_HexGeometryFailure& OutFailure);
bool TryGet_CoordFromWorldPoint(const FVector& InPoint, const FTransform& InPivotWorld,
    const FCk_HexLayout& InLayout, FCk_HexCoord& OutCoordinate,
    ECk_HexGeometryFailure& OutFailure);
bool TryGet_CoordFromWorldRay(const FVector& InOrigin, const FVector& InDirection,
    const FTransform& InPivotWorld, const FCk_HexLayout& InLayout,
    FCk_HexCoord& OutCoordinate, FVector& OutWorldHit,
    ECk_HexGeometryFailure& OutFailure);
```

Pure projection addresses the infinite lattice. Phase 2 performs exact domain membership after this winner is selected. All false returns reset payload outputs (`{}`, zero, empty array); failure is non-None. True sets None; never infer success from `(0,0)`. Validation failures are ordinary branches that remain in Shipping. No method allocates ECS entities, emits callbacks, or reads a world singleton.

## Numbered implementation steps and gates

1. Implement checked integer operations first. Use the CoordinatesAndTurns row's direction table for TryGet_Neighbor. Assert invalid direction and a step beyond int32 return InvalidDirection and Overflow respectively. Positive turn is `(-R,Q+R)` using int64 intermediate on every step; keep all intermediate coordinates widened and reject only a final result outside int32 Q/R. An intermediate S-derived component outside int32 must not reject a later representable final rotation. Translation widens before adding. Distance is `max(abs(dq),abs(dr),abs(dq+dr))` using int64 throughout, including subtraction. Validate enum values explicitly; never modulo an invalid enum into a valid turn.

   Gate: compare literal turn fixtures and int32 endpoints in `CoordinatesAndTurns`/`DistanceOracle`. Expected: valid results or explicit overflow, never wrapped output. If a fixture contradicts the specified chart → fix implementation/test oracle once from the formulas; anything else → stop and record.

2. Expand disk domains only after count/coordinate/capacity preflight. Compute `1+3*n*(n+1)` with checked arithmetic or cap-before-multiply, not an unchecked int32/int64 expression. Provisional materialization ceiling is **65,536 cells**, applied to both disk and explicit input before allocating/reserving. Radius 147 yields 65,269; 148 yields 66,157 and fails LimitExceeded. This is a conservative allocation guard, not a performance target or production supported-scale promise; Phase 7 profiling/CTO approval owns that decision. Reserve only after the bound passes. Check translated extreme coordinates before publishing any output. Sort `(r,q)`, detect duplicates explicitly, never clip invalid entries. Build temporary output and move only on success. Native internal resolved-domain storage may use a set for membership; no reflected `TSet<FCk_HexCoord>` requirement is imposed on AS.

   Gate: all domain rubric cases pass, including failure on the final explicit entry and near int32 disk center. If output is partially populated → clear on failure and fix staging before proceeding. Actual registry limits are checked again in Phase 2; anything else → stop.

3. Implement local chart formulas in double precision. Let `a=OuterRadius>0`, finite. Pointy centers: `(sqrt(3)*a*(q+r/2),1.5*a*r)`; flat: `(1.5*a*q,sqrt(3)*a*(r+q/2))`. Corners start at 30° for pointy/0° for flat, increase by 60° toward chart +Y. Radius is center-to-corner. Reject nonfinite computed values and precision that cannot distinguish adjacent cell centers (verify neighboring projected separation before accepting an extreme query). Do not impose an arbitrary Q/R cutoff.

4. Invert the same basis, derive fractional cube S, round/repair largest residual, then compare the rounded candidate and its six neighbors in a radius-normalized chart. Keep candidates widened until selecting the winner. Compute candidate distances after subtracting the nearby candidate center, not by subtracting two squared distances of huge global positions. Enumeration order `(r,q)` and tie order `(q,r)` are deliberately different contracts.

   Use this **proposed numerical policy**, independent of board size and integer membership. `epsilon = std::numeric_limits<double>::epsilon()` (not Unreal's float SMALL_NUMBER). For a local query, set `B = 1 + max(abs(x/a), abs(y/a), abs(fractionalQ), abs(fractionalR), abs(fractionalS))`. For world-point queries also include `(maxAbs(InPoint) + maxAbs(PivotTranslation)) / (a * uniformScale)` in that maximum; this accounts for cancellation when subtracting a distant pivot. For ray queries include the same term for origin and computed hit, and multiply B by `max(1, 1/abs(dot(unitDirection,planeNormal)))` to account for intersection conditioning. Calculate these bounds with overflow checks; nonfinite bounds return PrecisionLoss. Let normalized positional uncertainty `E = max(1e-12, 128 * epsilon * B)`. Reject spatial queries with `E > 1e-5` as PrecisionLoss. This threshold limits admitted numerical ambiguity to a declared fraction of the cell radius; it is not a restriction on Q/R storage, disk center, logical lookup, rotation or distance.

   For an admitted query, compare ordinary Euclidean candidate distances in radius units. A candidate is tied with the minimum when `distance <= minimumDistance + 4*E`; select lexicographically smallest **(q,r)** among those candidates. Thus an admitted point within the explicit uncertainty band may select either geometric side according to the stable tie rule; outside that band the nearest cell must win. The maximum tie band is `4e-5` of outer radius. This is a conservative portable policy to be tested, not a claim of correctly rounded exact predicates. Do not silently enlarge the E cap to make a fixture pass. A demonstrated bound failure requires a recorded numerical-policy review.

   First reject fractional coordinates plainly beyond any representable neighbor (outside int32 Q/R by more than four cells) as Overflow, using comparisons before integer casts. Otherwise evaluate the precision bound before rounding/narrowing. If the final winning lattice coordinate is outside int32, return Overflow; do not choose a farther representable neighbor. Broad-range integer coordinates stay valid even when their floating spatial queries reject. No global fixed tie tolerance may be used as a reason to reject otherwise admitted large-coordinate queries.

   Concrete vectors (`a=1`, identity pivot unless stated; build expected points directly from formulas, not the production center helper):

   | Input | Expected |
   | --- | --- |
   | Pointy edge `P=(sqrt(3)/2,0)` | Tie `(0,0)`; `P+(-1e-7,0)` → `(0,0)`; `P+(1e-7,0)` → `(1,0)`. |
   | Flat edge `P=(0.75,sqrt(3)/4)`, unit normal `N=(sqrt(3)/2,0.5)` | Tie `(0,0)`; `P-1e-7*N` → `(0,0)`; `P+1e-7*N` → `(1,0)`. |
   | Pointy vertex `V=(sqrt(3)/2,0.5)` | Tie among `(0,0),(1,0),(0,1)` → `(0,0)`; move V by `1e-7` toward each of those analytic centers → that cell. |
   | Flat vertex `V=(1,0)` | Tie among `(0,0),(1,0),(1,-1)` → `(0,0)`; move V by `1e-7` toward each analytic center → that cell. |
   | Both orientations, analytic center of `C=(1000000,-1000000)` | Successful pick C; no PrecisionLoss. At midpoint of C and `C+(1,0)`, exact tie → C; move by `±1e-3` along unit center-to-center direction → respective cell. These displacements comfortably exceed the computed uncertainty band. |
   | Both orientations, analytic center of `C=(INT32_MAX,INT32_MAX)` | Coordinate/explicit-domain integer validation succeeds; precise local/world pick returns PrecisionLoss under this E cap, with reset output. It must not overflow during bound/round preparation. |
   | Pointy `C=(INT32_MIN,INT32_MIN)` and opposite endpoint | Derived S is `4294967296`; distance to `(INT32_MAX,INT32_MAX)` is `8589934590` in int64; integer API succeeds independently of spatial rejection. |
   | Any orientation, finite normalized point `(1e100,0)` | Overflow before any narrowing/allocation. |
   | Any orientation, world pivot translation `(1e20,0,0)`, radius 100, point equal to that pivot | PrecisionLoss: loss of radius-scale precision in world input must not silently become an origin-cell success. |
   | Internal bound helper with `B0 = 1e-5 / (128*epsilon)` and `B1 = std::nextafter(B0, +infinity)` | E(B0) equals the double cap and is admitted; E(B1) exceeds the cap and rejects. Scaling by `128*epsilon` is a power-of-two operation for binary64; compare computed doubles, not decimal rounded log text. |

   Place the E computation in one native internal helper used by all spatial entry points; test its threshold directly. Do not add a public tuning knob for these numerical constants. For boundary vectors at translated large C use the large-vector `1e-3` displacements, not the small-origin `1e-7` displacements. Include a hole/exterior case where the lexicographic winner is absent: return OutsideDomain at the board adapter, even though another tied cell belongs to the domain.

   Gate: `ProjectionOracle`, `PickingBoundaries` and `ArithmeticAndPrecision` match the concrete vectors and independent half-plane/literal fixtures; modest-origin perturbations are `1e-7 * a`, large-coordinate edge perturbations `1e-3 * a`. Assert E and the selected reason as well as success/failure. Round-trip-only evidence is insufficient. If ties vary by orientation or iteration order → fix deterministic winner, not epsilon-nudge world inputs. Anything else → stop.

5. Validate full pivot transforms before inversion: finite components, normalized nondegenerate quaternion, finite positive scale and uniformity within relative `1e-9`; reject negative components/reflection and singular/nonuniform scale. Use `FCk_Frame3D` for rigid frame and explicit scale conversion. Validate resulting world coordinates too. Point queries accept absolute signed plane distance at most `1e-7 * a * uniformScale`; larger distance is OffPlane. Rays must be finite and nonzero; normalize safely, intersect the actual pivot XY plane, reject absolute normal dot <=`1e-12` as ParallelRay and negative intersection distance as BehindRay; origin on plane is distance zero and accepted. Point projection is not an implicit orthogonal-project API. Same picking code must later serve gym and editor.

   Gate: `WorldProjection`/`ArithmeticAndPrecision` pass all finite/invalid cases without ensures. If a world point cannot be numerically distinguished, return PrecisionLoss, not a guessed coordinate. Anything else → stop.

6. Normalize formatting/line endings; inspect the complete owned diff. Run the build and test gate through [VALIDATION.md § Running a gate](VALIDATION.md#running-a-gate), using exact test filter `Ck.HexGrid.Geometry.` and unique phase output stem `hex-grid-phase-1`. Announce **one fresh final editor boot** planned (native tests plus binding generation); use incremental Toolbox build first. Compilation failure → fix every reported compiler/UHT error before a boot. A red runtime gate permits one evidence-led correction and final rerun; before additional boots explain new evidence and update budget. Never launch a duplicate process after a timeout.

   Expected: all seven named rows discovered and pass; no unexpected ensures, AS compile errors or warnings naming new files in fresh logs. Missing rows/zero tests is failure. Known unrelated failure → preserve evidence and record blocker without expanding scope; any other outcome → stop. This phase does not claim the Phase 2 real-world/Blueprint consumer gate.

## Exit, recovery and fences

- Seven named geometry rows pass in the final tree; Toolbox result/log paths and timestamps recorded. Build/UHT succeeds. Generated native/static geometry bindings are visible and no hand-written generated output exists.
- Review Blueprint function discovery/pins/enums and run a small Blueprint graph for rotation, domain, point/ray and false-output reset `[EDITOR-VERIFY]`; exercise generated AS static calls with representative success/failure arguments. If either requires a real board, that scenario belongs to Phase 2; pure helpers must still be called here. Mark human checks pending until actually observed, never infer them from UHT.
- Record tests, exact filters, unresolved manual checks, new symbols and limit/tolerance decisions in `PROGRESS.md`; mark Phase 1 done only when its required checks actually pass. The accepting session does not repeat this gate absent changed geometry; Phase 8 owns final compatibility regression.
- On failure preserve logs and unfinished edits in this checkout. Do not clean Binaries/Intermediate/DDC, disable ensures, delete generated files, alter engine flags, or replace typed axial coordinates with FIntPoint in the public API. Two failed fixes for the same symptom → stop, follow stuck protocol and request bounded Astra consultation before a third.
- No AABB-derived hex picking, generic public grid interface, shader-pattern reuse as gameplay geometry, persistence wire data, cell entities, placement eligibility, cross-grid intersection, or implicit network identity is introduced here.
