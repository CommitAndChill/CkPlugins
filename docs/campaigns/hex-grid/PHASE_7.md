# Phase 7 • Saved hex-board painting

**Release choice.** Schedule this phase when the Technical Director includes persistent painting in the release. P2 already supplies runtime picking, wire outlines, an authored board and a playable gym. P7 lets a level designer change that board asset in the editor and see the edit survive reopening. An executor can implement this slice after P1–P4 are accepted. Verify P5 recipe/revision rules too when it has landed.

## Acceptance rubric

| Proposed native row under `Ck.HexGrid.Editor.` | Required observation |
|---|---|
| `TypedSelection` | Hex spawner opens the hex mode, square spawner retains square behavior, unrelated actors are ignored. One root component produces one overlay. Active paint mode owns its own overlay. |
| `TransformedHitAndBrush` | Flat and pointy grids under translated, rotated, uniformly scaled and nonidentity local pivots. Disk brush radius 0 covers one address, radius 1 covers seven before clipping. Holes, absent edge winners, behind/parallel rays and unsupported transforms produce the P1/P2 results. |
| `TransactionalStroke` | A stroke validates the complete candidate, deduplicates cells, and triggers one asset transaction and one rebuild per affected loaded spawner for a changed stroke. A no-op, cancelled stroke or invalid candidate leaves the asset and undo stack intact. |
| `AssetRoundTrip` | A serialized native asset edited through the production stroke path reloads with identical logical cells/tags, brush state excluded. A transaction undo and redo restore the exact original and edited recipes. Affected live spawners reconstruct from the same asset. |

All four automated rows plus a real saved-package reopen and visual comparison are required. Save/reopen evidence includes a genuine hex DataAsset, a pre-existing square asset and a spawner with a nonidentity local pivot.

## Ownership, interfaces and call sites

| Owner | Contract |
|---|---|
| `Plugins/CkGameplayDebugger/Source/CkGridEditor/CkGridEditor_Module.cpp:18-69` | Reference the new concrete UEdMode for auto-discovery. Retain the single registered USceneComponent visualizer and late registration/unregister lifecycle. Dispatch both typed spawner cases through that visualizer. |
| `Private/Visualizer/Ck2dGridSystem_SpawnerVisualizer.cpp:17-79` in that module | Preserve the root-component and square-mode filters. Add a hex branch for drawing and HUD using hex mode/asset identity and P1/P2 geometry. No duplicate registration for USceneComponent. |
| `Private/EdMode/Ck2dGridSystem_EdMode.cpp:414-540` and `Private/Draw/Ck2dGridSystem_AuthoredOverlay.cpp:30-54` | Square paint and square Spec resolution remain existing callers. Introduce `UCk_HexGrid_EdMode` with distinct mode ID `Ck.HexGrid.PaintMode`, hex toolkit, brush and overlay under sibling EdMode/Draw paths. Keep authored and live runtime overlays distinguishable. |
| New hex EntityScript and native DataAsset in Foundation's `CkGrid/HexGridSystem/Authoring/` | Add a narrow, const, typed native accessor for the currently resolved authoring asset, for example `Get_ResolvedAuthoringSpec() const`. Null means pending/unavailable with no per-draw blocking load. Asset privately owns the editable Spec. Give the editor a scoped controlled operation to validate/replace a staged authored Spec under WITH_EDITOR. Never return a mutable runtime-fragment reference. |
| `CkGridEditor.Build.cs`, `Plugins/CkGameplayDebugger/CkDebugger.uplugin` and runtime `CkGrid.Build.cs` | All viewport, PDI, Slate, transaction and editor subscriptions remain on the editor side. Preserve the runtime target boundary. P8 exercises the packaged target. |
| `Plugins/CkTests/Script/Common/CkTests_GymRegistry.as:4-18`, `Plugins/CkTests/CLAUDE.md:109-148` | Extend the P2 hex station only as necessary to compare saved authoring, picked coordinate and runtime outline. Square gym, debugger EQS sample spacing and square inventory inspector keep their contracts. |

## Execution order

1. Check the integrated revisions, P1–P4 evidence and release scope. Capture the square visualizer's selection and painting behavior in the current editor before editing it. Keep work in the host checkout. Preserve existing assets and user edits. Read Foundation/host AGENTS, CkGridEditor module, CkTests authoring guides and build-test. If scope or prerequisite signatures differ, log the discrepancy and return to the lead.
2. Build one editor selection adapter from the spawner to its hex EntityScript, resolved Spec asset and composed world pivot. Reuse geometry conversion and domain lookup from CkGrid. Before an instance exists, compose the same authored pivot and spawn transform with the runtime transform order. Prove agreement with a real constructed spawner. Unresolved asset returns no editable selection.
3. Implement a local axial disk brush with membership clipping and canonical ordering. Support painting/erasing a selected cell tag and initial-disabled state. Use the P2/P3 authoring schema, including default tag semantics. Brush radius, paint mode, selected tag and overlay colors belong to editor tool state. Keep the grid's domain and named blockers editable through their typed asset properties.
4. Preview the candidate stroke without mutating the asset. Validate the complete candidate through the runtime authoring validator. On release, for a real change, open one FScopedTransaction, call Modify before changing the actual serialized DataAsset, post the property change, mark the package dirty and rebuild affected live spawners once. Use editor change/undo notifications to refresh affected loaded users of a shared asset. Verify zero or one rebuild per user as appropriate. Do not edit a transient CDO or overwrite a script-defined asset on compile. Content changes participate in P5's fingerprint policy: old, incompatible recipe projections reject explicitly.
5. Use the four named native rows through [Running a gate](VALIDATION.md#running-a-gate) and filter `Ck.HexGrid.Editor.`. Budget one incremental editor build, one focused fresh test run and one interactive editing session with a reopen. Announce actual boot needs and distinguish manual restarts from test boots. Capture before/after at the same camera position for flat, pointy and square fixtures, including an edge, hole and off-plane/parallel rejection.
6. **Editor verification.** Make an edit, undo, redo, save, close and reopen the asset/project through the supported editor path. Reconstruct the real runtime board, inspect the same coordinate via the P2 API and compare against the saved asset. Repeat with two instances sharing the asset. Switch from square to hex and back. Retain the asset identity, coordinates, observations and images in the gate record.

## Exit

Accept after all four native rows and the editor observations pass, logs are clean and square interaction still works. A drawing that looks right at the origin cannot establish pivot correctness. A regenerated in-memory script asset cannot establish saved painting. If a probe fails, repair the implicated adapter and repeat only the affected gate. If an unforeseen ownership or persistence decision is required, record it in PROGRESS.md and return to the lead.
