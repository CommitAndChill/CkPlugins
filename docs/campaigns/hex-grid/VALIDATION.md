# Phase 8 • Verification and release acceptance

**Sign-off requires** the named native test rows for P1–P6, demonstrated C++/Blueprint/AngelScript callers, demonstrated old-square compatibility, a staged packaged execution and measured resource usage. Include the four P7 rows and saved-asset evidence when the release includes painting. All results in this file are future acceptance criteria.

## Running a gate

Use the host checkout in place. Read `CkAuto/.claude/skills/build-test/SKILL.md` (preflight, selection, known reds, generated stubs, session locks) and `Plugins/CkFoundation/.claude/skills/ck-change-control/SKILL.md`. Before invoking Toolbox state the number of planned editor boots and reason, including discovery or AS generation when needed. Check project editor/log locks and other gate activity. Wait for required quiescence. In a managed session use the approved GUI/escalated launch for Start-Process. Give every run an absolute project path and its own output log.

The following is a **PowerShell invocation template for future executors**. Run it from the host, substituting the phase filter below. `-Build` includes the incremental editor build. The default is one serial test lane for a focused gate. `-Full` omits the substring filter and uses the Toolbox's normal machine lane policy. `-Discover` refreshes discovery when rows were added or renamed and is required on the final full gate. Estimate discovery, lane and generated-stub restarts from the actual local state. One invocation can launch more than one editor.

```powershell
function Invoke-HexGate {
    param([string]$Pattern, [string]$Label, [switch]$Build, [switch]$Discover, [switch]$Full)
    $projectRoot = (Resolve-Path (git rev-parse --show-toplevel)).Path
    if (-not $Full -and [string]::IsNullOrWhiteSpace($Pattern)) { throw 'Supply the phase filter.' }
    $stamp = Get-Date -Format yyyyMMdd-HHmmss-fff
    $logPath = Join-Path $projectRoot "Saved/Logs/hex-grid-$Label-$stamp.log"
    $launchArgs = @("--project=`"$projectRoot`"", "--output=`"$logPath`"", '--test', '--no-live')
    if ($Build) { $launchArgs += @('--build', '--target=Editor') }
    if ($Discover) { $launchArgs += '--discover-fresh' }
    if (-not $Full) { $launchArgs += @('--parallel', '1', '--test-pattern', "`"$Pattern`"") }
    $toolbox = Join-Path $projectRoot 'CkAuto/UnrealToolbox.exe'
    $job = Start-Process -FilePath $toolbox -ArgumentList $launchArgs -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
    Write-Output "Toolbox PID $($job.Id)   Log $logPath"
    $job.WaitForExit()
    $job.Refresh()
    if ($job.ExitCode -ne 0) { throw "Toolbox exit $($job.ExitCode). Inspect $logPath" }
}
Invoke-HexGate -Label geometry -Pattern 'Ck.HexGrid.Geometry.' -Build -Discover
```

Monitor the **same detached process** to completion; if the execution wrapper yields, retain its PID and log. Inspect the full fresh editor and Toolbox logs, exact selected rows, Test Completed outcomes, summary and known-reds/deferrals. An exit code alone, zero selected tests, missing AS completion, suppressed rows, a stale test cache or RUN INCOMPLETE is insufficient. Record any expected intentional diagnostics by test and cause. Inspect surprises including ensures, fatal/assert, UHT/AS errors, timeouts and missing expected worlds. Preserve the output outside log rotation before the next run. A blocking wait in this example belongs in one monitored background invocation. Do not launch a duplicate on timeout.

| Phase | One literal focused filter | Required new rows and additional evidence |
|---|---|---|
| 1 | `Ck.HexGrid.Geometry.` | 7 geometry rows, AS static calls and Blueprint pure-node execution. |
| 2 | `Ck.HexGrid.Board.` | 6 rows, native driver executes an AS fixture, Blueprint graph, gym/headless board. |
| 3 | `Ck.HexGrid.Rules.` | 9 rows including native-driven AS_Consumer, authored object and named blocker. |
| 4 | `Ck.HexGrid.Placement.` | 14 rows including native-driven AS_Consumer, terminal signal and queue evidence, BP result pins. |
| 5 | `Ck.HexGrid.Persistence.` | 5 rows, approved early-provenance matrix, production save/load reports and pre-existing square comparison owned by P8. |
| 6 | `Ck.HexGrid.Net.` | 7 rows including generated AS row, genuine late join and mixed-world reload. P6 also changes both P5 registrations in place, so rerun the relevant registration assertion on the split-apply contract. |
| 7, if selected | `Ck.HexGrid.Editor.` | 4 rows and saved DataAsset reopen/undo/redo evidence. |
| 8 | Full discovered project gate | Once on the integrated candidate, for example `Invoke-HexGate -Label acceptance -Full -Discover`. Add -Build when required by the actual revisions and Tier 4 gate. Record lane, discovery and boot counts. |

Toolbox consumes one AND-pattern per invocation. Never join test filters with a plus sign or comma. For the P6 registration rerun or changed prerequisites, use a separate focused invocation with the exact earlier name; orchestrate serially in one monitored batch and report one result table. Schedule the integration gate once per candidate. New net AS rows are generated native C++: run the supported generator, check the generated file's change, rebuild, then fresh-discover the name. The first boot that writes a stub cannot execute the newly written native object code. General AS functional rows normally appear under Project.Functional Tests; P2–P4 use explicit named native drivers so their phase filters really execute the AS bodies. Inspect generated files/maps for unrelated changes.

## Compatibility manifest

Before the first implementation build, retain representative pre-change square asset and serialized save fixtures with their source revision, original board dimensions, expected addresses, occupancy and identity. Use a known archived fixture if available or create a test fixture with the current pre-change build in this checkout. Do not overwrite user assets or rewind the shared checkout. Record fixture provenance. A save produced only after implementation cannot establish old-save compatibility.

P8 owns the pre-existing square regression runs. Verify the following names in the full gate output, including all four EdMode rows when the editor plugin is available. Preserve the old verdict and investigate any failure in the edited area. A known-red entry cannot waive a missing new hex assertion.

- `CkGrid.UnitTests.Authoring.SpecResolve` and `Ck.Grid.OccupancyScratch.LifecycleAndMapWorkload`
- `Ck.Grid.Net.AS_Grid_OccupancyReplicates`
- `Ck.Snapshot.Parity.GridPlacements_MPReload` and `Ck.Snapshot.Parity.InventorySpatial_MPReload`
- `Ck.Inventory.Net.SyncReplication.RemovalLifecycleAndTargetFirstTransfer`
- `CkGrid.UnitTests.EdMode.RayToCell`, `RectCells`, `TagColor`, `TagEnumeration` under the same prefix
- Existing functional grid and spatial inventory tests discovered by the host. Record actual fully qualified names, including returned functional-map rows. If host population omits a required row, inspect `AutomationGate.json`, fresh discovery and the CkTests generated map. Run the missing row through its supported scoped route and report coverage explicitly.

**Editor evidence.** Open and compile pre-change square consumer Blueprints and `Plugins/CkFoundation/Content/CkGrid/Utils_CkGrid_ML.uasset`. Inspect serialized references with Reference Viewer; record actual assets and pin signatures. Load the donor save on the new build. Compare exact old square placement/occupancy and spatial inventory results. Run C++, Blueprint and AS against the hex public types in a real level with both topologies. Check generated mixin/validity functions, success/failure pins and authority-only behavior. Preserve an attributed result for each surface.

**Framework scope.** Public additive hex APIs are Tier 2. Changed shared editor behavior needs the affected baseline and before/after evidence. Any approved CkEcs/CkSnapshot/replication-invariant change invokes the project's Tier 4 maintainer review, rebuild and full-suite gates. Establish trusted binaries through the project Toolbox in place. If fulfilling the rebuild gate would require destructive cleanup or an unsupported build operation, obtain the specific approval/method before it. Preserve intermediates and existing checkouts. Reuse a valid full-gate result on the exact same candidate. The code-review and failure-path conventions in the host AGENTS apply throughout.

## Packaged and scale gates

1. **Cooked Development build.** Use the project's supported staging pipeline and record target, package ID, source revisions, cooked map/asset paths and staged AS scripts. Include a runtime-compatible hex spawner/fixture and a square control. The CkTests runtime and its uncooked-only modules are split in `Plugins/CkTests/CkTests.uplugin:18-44`. Verify the fixture entry point is available in the staged runtime; keep editor-only test drivers out of it. Drive a real packaged process through create, pick, place, blocked move, save/load and teardown, and record exact IDs/cells plus fresh logs. Exercise a server with presentation disabled and a client joining after committed state where the shipping target supports network play. Verify zero required editor modules, missing assets or presentation loads on the server. An editor -game Gauntlet run and PIE supply different evidence from a staged game. If a staging artifact/target is unavailable, record which artifact is needed and leave this release gate open. Shipping configuration needs explicit authorization.
2. **Resource measurements.** Run the packaged Development performance fixture under fixed hardware, engine/build config, seed, orientations, transforms and occupancy policy. Compare disk radii 8, 32 and 64 (217, 3,169 and 12,481 cells) and a sparse explicit equivalent. Use empty, half-filled and dense scenarios, both one and multiple simultaneous boards, near the intended product maximum. Compare the same number of materialized square cells on the same build where operations are semantically comparable. Record actual grid sizes and occupancy counts. Separate build/teardown time, persistent and peak memory/bytes per cell, lookup, preview and accepted/failed move latencies, idle vs mutating processor cost, save bytes/time and late-join baseline bytes/time. Use warmed repeated samples and present median/p95, sample counts, units and variability. Measure peak/retained memory around a complete teardown and warn about allocator caches explicitly in the evidence.
3. **Release decision.** Technical Director records expected concurrent boards and target hardware, acceptable memory and frame/restore/join budgets. Compare actual measurements and leave unmeasured workloads unsupported. If limits fail, keep the measured supported range or return the design for changes before promising larger boards. Any change of representation, lazy cell materialization or streaming topology needs separate design approval. No threshold is inferred from the input-validation ceiling.
4. **Exit.** Reconcile P1–P7 evidence, raw fresh results and the scope decision in PROGRESS. List remaining failures or unobserved surfaces by name. A runtime-only release can explicitly defer P7. Core persistence, real late join, old-square compatibility and packaged runtime remain release criteria. Root/submodule publication is a separate user decision.

Source anchors for gate operation include `CkAuto/.claude/skills/build-test/SKILL.md:145-171,285-298,417-441,449-458`, `Plugins/CkTests/CLAUDE.md:31-95` and `AutomationGate.json`. The [phase index](PROMPT.md) links the exact per-row assertions.
