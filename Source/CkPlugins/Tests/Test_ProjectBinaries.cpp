#include "CoreMinimal.h"

#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS && PLATFORM_WINDOWS

#include "HAL/PlatformMisc.h"
#include "HAL/PlatformProcess.h"
#include "Misc/App.h"
#include "Misc/AutomationTest.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FCk_ProjectBinariesTest,
    "CkPlugins.UiAuthoring.Startup.ProjectBinaries",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

auto FCk_ProjectBinariesTest::RunTest(const FString&) -> bool
{
    if (!TestTrue(TEXT("Startup selected a project file"), FPaths::IsProjectFilePathSet()))
    { return false; }

    const FString ProjectFile = FPaths::ConvertRelativePathToFull(FPaths::GetProjectFilePath());
    if (!TestTrue(TEXT("Selected project file exists"), FPaths::FileExists(ProjectFile)))
    { return false; }

    const auto NormalizeDirectory = [](const FString& InDirectory) -> FString
    {
        FString Directory = FPaths::ConvertRelativePathToFull(InDirectory);
        FPaths::NormalizeDirectoryName(Directory);
        return Directory;
    };
    const FString ExpectedProjectDirectory = NormalizeDirectory(FPaths::GetPath(ProjectFile));
    const FString ExpectedBinariesDirectory = NormalizeDirectory(
        FPaths::Combine(ExpectedProjectDirectory, TEXT("Binaries"), FPlatformProcess::GetBinariesSubdirectory()));

    FString ResolvedProjectDirectory;
    FString ResolvedEngineDirectory;
    if (!TestTrue(TEXT("Executable helper resolves the selected project's binaries"),
        FPlatformMisc::GetEngineAndProjectAbsoluteDirsFromExecutable(ResolvedProjectDirectory, ResolvedEngineDirectory)))
    { return false; }
    TestEqual(TEXT("Executable helper preserves the selected project directory"),
        NormalizeDirectory(ResolvedProjectDirectory), ExpectedProjectDirectory);

    FModuleManager& Modules = FModuleManager::Get();
    const FString RegisteredBinariesPath = Modules.GetGameBinariesDirectory();
    if (!TestFalse(TEXT("Startup registered a nonempty game binaries directory"), RegisteredBinariesPath.IsEmpty()))
    { return false; }
    const FString RegisteredBinariesDirectory = NormalizeDirectory(RegisteredBinariesPath);
    TestEqual(TEXT("Startup registered the selected project's game binaries directory"),
        RegisteredBinariesDirectory, ExpectedBinariesDirectory);

    FModuleStatus RendererStatus;
    if (!TestTrue(TEXT("Module manager knows CkUsfRenderer"),
        Modules.QueryModule(FName{TEXT("CkUsfRenderer")}, RendererStatus)))
    { return false; }
    if (!TestTrue(TEXT("CkUsfRenderer is loaded"), RendererStatus.bIsLoaded)
        || !TestFalse(TEXT("Loaded module has a file path"), RendererStatus.FilePath.IsEmpty()))
    { return false; }
    // The Shared build environment loads plugin modules from <Project>/Plugins/<Plugin>/Binaries/<Platform>; both stay inside the selected project.
    const FString RendererDirectory = NormalizeDirectory(FPaths::GetPath(RendererStatus.FilePath));
    TestTrue(FString::Printf(TEXT("Loaded CkUsfRenderer belongs to the selected project (%s or <Project>/Plugins/<Plugin>/Binaries/%s), got %s"),
            *ExpectedBinariesDirectory, FPlatformProcess::GetBinariesSubdirectory(), *RendererDirectory),
        FPaths::IsUnderDirectory(RendererDirectory, ExpectedProjectDirectory));

    AddInfo(FString::Printf(TEXT("Startup evidence: executable=%s; configuration=%s; project=%s; game-binaries=%s; renderer=%s"),
        FPlatformProcess::ExecutablePath(), LexToString(FApp::GetBuildConfiguration()),
        *ProjectFile, *RegisteredBinariesDirectory, *RendererStatus.FilePath));
    return true;
}

#endif
