# Root history reconciliation

Unique non-pointer work from the multiplayer, online-services research, UI-pipeline, and shader branches was reconciled onto current dev. Historical submodule bumps were excluded; the published shader-reload pins and six obsolete-plugin removals remain intact. Earlier handoff results and paths are historical evidence, not acceptance of the current tree.

## Preserved work

- Online-services research: 73d037d and 0998234, equivalent to 0de0b94 and 434f81d. Retained despite their historical DROP BEFORE MERGE labels under the current preservation instruction; proposals remain research.
- Multiplayer tags, continuation, and evidence: af3dbeb, 9b56359, 2607c31, 1539a1c, ab2863f, 616d021, d9fb7d4. Tag additions were unioned with current registrations.
- UI host configuration, startup test, frame cap, and authoring guidance: f48d1e8, 63f5bea, f8a9936, 89b9b58. The missing UI_AUTHORING_RULES.md link was omitted while retaining presentation requirements and the current AUTHORING.md link.
- Inventory Gauntlet checkpoint: 9f82a92 is preserved in Handoff/UiPipeline/GauntletTests.inventory-checkpoint.json. Current CkTests lacks the named inventory runners; this file is archival and is not an active manifest. The active PixelSprite declarations are retained.
- UI continuation and unintegrated inspector draft: d38a442, cfa6113, 0c7013a, 3f89ded. The orphan CkEcsDebugger header remains a draft outside the production debugger module.

## Already integrated or superseded

- ab2863f build-profile source is byte-identical to current source (integrated through 9c55be3); its unique handoff edits were replayed.
- f44bef8 and af3dbeb generated spawn comments already match the current generated file (integrated through 9f86786); no generated output was replaced.
- 73a9357 remote URLs and 6e20b7c CkApplication removal/remote corrections are superseded by current canonical remotes and the complete obsolete-plugin removal.
- 9087317 editor guard documentation, 9cac142 AssetManagerEditor enablement, and 2d277c4 ISM specification fixes have patch-equivalent commits in current dev.

Historical CkAuto PhantomLauncher lineage is excluded. No existing secondary checkout or its occupied local branch was changed. Backup refs preserve the pre-reconciliation dev and shader branch tips.

The recovered startup probe failed on the current engine helper paths and is archived unchanged outside active compilation; see UiPipeline/StartupProbe.md for the failed receipt and remaining limitation.
