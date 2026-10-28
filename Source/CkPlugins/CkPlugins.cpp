// Copyright Epic Games, Inc. All Rights Reserved.

#include "CkPlugins.h"
#include "Modules/ModuleManager.h"

#if WITH_EDITOR
#include "Engine/Engine.h"
#include "Misc/App.h"
#include "Misc/CoreDelegates.h"
#endif

DEFINE_LOG_CATEGORY_STATIC(LogCkPlugins, Log, All);

// --------------------------------------------------------------------------------------------------------------------

namespace ck_plugins
{
    // DefaultEngine.ini caps the interactive editor's smoothed frame rate at 30 to save CPU. Unattended editors are
    // automation (UnrealToolbox test lanes, CI), and the Ck tests are authored and gated at 60 Hz: at 30 Hz the net
    // tests saturate Iris, physics settles miss their timeouts, and frame-stepped expectations shift. A clone whose
    // GameUserSettings.ini says FrameRateLimit=60 runs at a flat 60 through t.MaxFPS, which replaces the smoothed
    // cap; a fresh clone (FrameRateLimit=0) fell through to the 30 cap. Raising the smoothed ceiling instead is not
    // enough: the running average dips after every PIE start and the net tests stay red.
    constexpr auto AutomationMaxFPS = 60.0f;
}

// --------------------------------------------------------------------------------------------------------------------

class FCkPluginsModule : public FDefaultGameModuleImpl
{
public:
    auto
        StartupModule()
        -> void override
    {
#if WITH_EDITOR
        // After UEditorEngine::Init, whose GameUserSettings ApplySettings writes t.MaxFPS from FrameRateLimit
        _PostEngineInitHandle = FCoreDelegates::OnPostEngineInit.AddStatic(&FCkPluginsModule::DoApply_AutomationMaxFPS);
#endif
    }

    auto
        ShutdownModule()
        -> void override
    {
#if WITH_EDITOR
        FCoreDelegates::OnPostEngineInit.Remove(_PostEngineInitHandle);
#endif
    }

private:
#if WITH_EDITOR
    static auto
        DoApply_AutomationMaxFPS()
        -> void
    {
        if (!GIsEditor || !FApp::IsUnattended() || IsRunningCommandlet() || GEngine == nullptr)
        { return; }

        // An explicit t.MaxFPS (ConsoleVariables.ini, -ExecCmds, a non-zero FrameRateLimit) is left alone
        if (GEngine->GetMaxFPS() > 0.0f)
        { return; }

        // SetMaxFPS keeps the set-by reason of the last write, so a later FrameRateLimit apply can still replace it
        GEngine->SetMaxFPS(ck_plugins::AutomationMaxFPS);

        UE_LOG(LogCkPlugins, Display, TEXT("Unattended editor: t.MaxFPS was unset, now [%.1f] (Ck tests are gated at 60 Hz)"),
            GEngine->GetMaxFPS());
    }

    FDelegateHandle _PostEngineInitHandle;
#endif
};

IMPLEMENT_PRIMARY_GAME_MODULE( FCkPluginsModule, CkPlugins, "CkPlugins" );
