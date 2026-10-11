# Pixel sprite acceptance ledger

This maps REQUEST.md section 17 to production paths and executed checks. PROGRESS.md owns current results; source presence alone does not close an item.

| Requirement | Production path | Acceptance evidence / remaining check |
|---|---|---|
| Text-authored XPM | Tools/CkPixel/Examples and CLI | Robot/Character authored; Python suite passes |
| Native import | CkPixelSpriteEditor_Factory | FactoryReimport passes |
| Asset opening | AssetDefinition and neutral viewer delegate | Real AssetDefinition-bound viewer route passes in Gate10 |
| Accurate pixels | Xpm, Render, Resources, Canvas | Indexed/CPU tests and resource cache tests pass; rendered basic viewer inspected; Character head/face pixel assertions pass; both advanced Character and panned clipping outputs inspected after Gate2; sprites fit and canvas clipping holds |
| JSON sequences | Manifest/Load/Asset | Shared manifest and native file conformance pass |
| Authored durations | Animation evaluator, player, viewer State | Native decimal timing passes; player, AS player and advanced state pass; prepared cache and extreme manual inspection pass Gate2; corrected overflow-recovery regression passes FinalEditor1 |
| Timeline and scrubbing | Viewer Window | Basic seek/control test passes; visible thumbnail timeline and duration/playhead readout inspected in Gate10 screenshot |
| View controls and stepping | Viewer Canvas/Window/State | Basic real-renderer zoom/grid interactions pass; advanced source stepping/pan/state checks pass; physical splitter persistence, Center/Reset, exact-case source folder collapse/expand/navigation pass AuthoredReconcile2 |
| Onion and comparison | Viewer Canvas/Window and TryCompare_Grids | CPU comparison passes; viewer physical onion/comparison toggles and changed-count checks pass; visual clipping assertions pass Gate2 and output directly inspected |
| Nondestructive render modes | Render/Resources and viewer settings | Deterministic CPU mode tests pass; advanced nondestructive modes tested; authored output directly inspected in Gate2 |
| Source reimport | Factory and import dependency metadata | Indexed XPM reimport and rejected preservation pass; undo/redo passes Gate10; actual changed-JSON source ordering, durations, mode, anchors, metadata and dependency hashes pass Gate2 |
| Runtime player | Player, Widget, Preview | Blueprint VM passes; native PlayerWidget and operational AS control tests pass in Gate10 |
| Packaged rendering | Preview and PixelSpriteCookedRuntime scenario | Runtime2 Development Game build, actual cook/stage and fresh staged Gauntlet client pass; indexed Character load, exact authored timing, anchors, UMG readiness/advance and explicit completion verified; D3D12 screenshot directly inspected (Saved/PixelSpriteAcceptance/Runtime2-Packaged.png) |
| Parsing/timing/invalid tests | Native tests and shared fixtures | Native core passes in FinalEditor1; full gate completed with 31 failures, including five non-feature unlisted paths still requiring attribution (see FULL_GATE.md); feature viewer/catalog failures corrected and targeted reruns pass |
| Dependency direction | Runtime/editor/viewer descriptors and Build.cs | Editor and Development Game builds pass; Game UHT manifest excludes importer/viewer and retains CkPixelSprite |
| Repository conventions | New modules and shared guides | Unity disabled; self-contained Editor/Game compilation passes; CK formatting and bounded code/revision reviews completed |
| Debugger-hosted viewer | CkPixelArtViewer module and tool registration | Real rendered viewer and state pass AuthoredReconcile2 (2/2); launcher catalog passes CatalogReconcile1 (2/2) |

Optional initial limits are explicit: manifest layers and full X11 named-color tables reject; automatic event dispatch and animation-video export are not implemented. Ordinary alpha rendering, authored events/metadata retention and PNG/sheet export are supported. The atlas alternative was considered; bounded cached per-source textures are the implemented path.

All seventeen mandatory feature criteria have executed acceptance evidence. Focused/native gates and corrected viewer/catalog gates pass; advanced viewer and real Development packaged output were directly inspected. The full editor gate completed with failures recorded in FULL_GATE.md: five non-feature paths remain unattributed (three fail alone, two pass alone). The packaged client also logged two ZenLoader worker-thread flush diagnostics before the scenario initialized. Feature acceptance is established; repository-wide regression-free or clean-startup acceptance is not claimed. Pixel implementation is published to the relevant submodule dev branches; the authorized host sample/cook integration and verified pointers are included in CkPlugins delivery. Unrelated local work remains excluded.
