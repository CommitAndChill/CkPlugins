# Historical startup probe

The unchanged probe from f48d1e8 is retained as Test_ProjectBinaries.cpp.txt outside Source. Its original active form is also preserved in the reconciliation history. It is excluded from current automation, not marked passing or added to known reds.

On the reconciled tree, the incremental editor build passed. The focused CkPlugins.UiAuthoring.Startup.ProjectBinaries run failed (0 passed, 1 failed). Local receipt: Saved/Logs/DevReconcile-Startup.log.

Exact failures:

- Expected executable-helper project directory D:/Repos/CkPlugins_3; actual D:/Repos/CkPlugins.
- Expected first registered game binaries directory D:/Repos/CkPlugins_3/Binaries/Win64; actual D:/Repos/CkPlugins/Binaries/Win64.

The selected project file assertion and loaded CkUsfRenderer directory assertion did not fail. No AngelScript compilation errors were reported.

Focused source inspection found that FGenericPlatformMisc::GetEngineAndProjectAbsoluteDirsFromExecutable derives a directory from the executable location and project name before consulting the project dictionary. It does not read the selected project file in this implementation. FModuleManager::GetGameBinariesDirectory returns the first registered or pending game binaries directory. These observations explain how the probe can expose inconsistent paths while the renderer module is loaded from the selected checkout; they do not establish a complete engine startup fix.

Engine startup diagnosis and correction remain unresolved and outside this root-history reconciliation. No other checkout, engine source, helper assertion, or build output was changed to hide the result.
