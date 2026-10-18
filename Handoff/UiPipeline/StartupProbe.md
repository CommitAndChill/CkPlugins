# Selected-project startup regression

The unchanged probe from f48d1e8 is restored to Source/CkPlugins/Tests/Test_ProjectBinaries.cpp. Its source blob remains 96ace1b48306192f88ab5f027f3fba38d54efe75; no assertion was weakened and no known-red exemption was added.

## Historical failure

During root-history reconciliation, the focused CkPlugins.UiAuthoring.Startup.ProjectBinaries run failed (0 passed, 1 failed). Receipt: Saved/Logs/DevReconcile-Startup.log.

- Expected executable-helper project directory D:/Repos/CkPlugins_3; actual D:/Repos/CkPlugins.
- Expected first registered game binaries directory D:/Repos/CkPlugins_3/Binaries/Win64; actual D:/Repos/CkPlugins/Binaries/Win64.

The selected project file and loaded CkUsfRenderer directory assertions did not fail.

## Engine correction

Engine fix commit: `8f7b57f90eea9bd09f9f5355a660477467452e05` in CommitAndChill/UnrealEngine-Angelscript (main-ck).

The dependent engine at D:/Repos/UnrealEngineAngelscript was updated in place to fetched origin/main-ck dde876d318b32990ee8c74d47540411b912a1817. Its prior StaticJIT change is already represented upstream. The pre-existing Iris DataStreamChannel.cpp edit was preserved unchanged.

FGenericPlatformMisc::GetEngineAndProjectAbsoluteDirsFromExecutable now prefers an existing physical selected project descriptor before sibling-name and project-dictionary discovery. It converts the entire descriptor to an absolute path before extracting and normalizing its containing directory. It does not require the selected project to already have a Binaries directory.

Executable-derived engine-directory validation remains unchanged. When no physical selected descriptor is available, legacy executable-layout and dictionary discovery remain unchanged. LaunchEngineLoop already selects the descriptor before invoking this helper, so no startup reordering or module-manager workaround was required.

## Verification

UnrealToolbox incremental editor build passed against the updated engine. The restored CkPlugins.UiAuthoring.Startup.ProjectBinaries test passed: 1 total, 1 passed, 0 failed, 0 contaminated; editor exit code 0. Receipt: Saved/Logs/SelectedProject-Startup.log.

The test checks the helper result, the actual first registered game-binaries directory, and the loaded CkUsfRenderer location. This is editor startup evidence; packaged, virtual-descriptor, no-descriptor, and explicit relative-descriptor scenarios were not executed separately.

The compatible real-renderer CkTests.UnitTests.CkUsf.ShaderReloadUpdatesExistingMID regression also passed: 1 total, 1 passed, 0 failed, 0 contaminated; editor exit code 0. Receipt: Saved/Logs/SelectedProject-ShaderReload.log. Both fresh logs contain no AngelScript compilation errors or ensures. A final engine fetch confirmed main-ck remained at the revision above.
