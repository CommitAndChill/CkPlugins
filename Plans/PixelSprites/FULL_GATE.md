# Final full-editor gate and targeted reconciliation

`Saved/Logs/PixelSprite-FinalEditor1.log`: Editor build succeeded, 4,099/4,099 configured tests executed; 4,068 passed, 31 failed, zero skipped or contaminated, exit 1. This is a completed failing full gate, not repository-wide regression-free evidence. Twenty-four failures are already listed in the repository's existing known-red files. None of those files was edited to change this verdict.

| New failure | Exact follow-up | Result and attribution limit |
|---|---|---|
| Ck.DebuggerLauncher.Catalog.AllCatalogTabsCloseAndReopen | PixelSprite-CatalogReconcile1.log | Corrected platform census for the newly registered viewer; catalog passes 2/2, including actual tab close/reopen. |
| Ck.PixelArtViewer.AuthoredWindow | PixelSprite-AuthoredReconcile1.log, PixelSprite-AuthoredReconcile2.log | Test drag used a synthetic captured move, which Slate suppresses. Folder lookup used case-insensitive FString equality and clicked the earlier animation `idle` rather than folder `Idle`. Real drag, exact-case tree-scoped lookup and physical collapsed-leaf rejection now pass; viewer state and authored checks pass 2/2. No production workaround. Fresh comparison, clipping and source hierarchy images inspected. |
| Ck.Snapshot.RuntimeArchetype.LiveRouteHuskIsReapedAndEnsured | PixelSprite-SnapshotIsolated1.log | Fails alone: expected one ensure, observed two. Server husk ensure plus client Record RemovalSuccess after authority rejection. No PixelSprite dependency found in this path; preexisting ownership has not been proved. |
| Project.Functional Tests.CkTests.AutoTests.AutoTests_CkTests_Level.Ck_AutoTest_Queue_ReserveDistanceRefreshPerf | PixelSprite-QueueIsolated1.log | Fails alone at 40.50-second timeout before benchmark output. Parallel load does not explain the isolated failure. No PixelSprite dependency found; ownership remains unproved. |
| Project.Functional Tests.CkTests.AutoTests.AutoTests_CkTests_Level.Ck_AutoTest_Sway_ChildSceneNodeFollowsSwayedPose | PixelSprite-SwayIsolated1.log | Fails alone at step 5: child must compose from swayed node pose in the same frame. No PixelSprite dependency found; ownership remains unproved. |
| Ck.RuntimeMesh.Render.CheckerSliceDisplay | PixelSprite-CheckerIsolated1.log | Passes alone 1/1. Full-run capture lacked expected blue material region. Shared-process interference has not been attributed, so this is not labeled preexisting or harmless. |
| Ck.UiAuthoring.IntentDebugger.InputHudControls | PixelSprite-IntentIsolated1.log | Passes alone 1/1. Full run handled click without expected setting/revision change. Shared Slate-state interference has not been attributed. |

All five non-feature follow-ups used a fresh editor, one lane and `--known-reds=off`. No unrelated production fixes, timeout increases or baseline additions were made. Remaining attribution would require focused with/without-change experiments in this checkout; no alternate checkout or clean full-suite rerun was created.

The full run passed the native PixelSprite parsing, timing, PlayerWidget, Blueprint VM, import/reimport, offline disk reload and actual AngelScript player paths. The corrected rendered viewer and catalog checks are established by the later targeted logs. Actual packaged rendering is tracked separately in ACCEPTANCE.md and PROGRESS.md.
