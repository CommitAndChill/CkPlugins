// Copyright Epic Games, Inc. All Rights Reserved.

#include "CkPlugins.h"
#include "Modules/ModuleManager.h"

#if WITH_EDITOR
#include "CkPluginsEditorPerformanceSettings.h"
#include "Engine/Engine.h"
#include "Misc/CoreDelegates.h"
#endif

class FCkPluginsModule : public FDefaultGameModuleImpl
{
public:
    virtual void StartupModule() override
    {
        FDefaultGameModuleImpl::StartupModule();

#if WITH_EDITOR
        if (GIsEditor)
        {
            if (GEngine && GEngine->IsInitialized())
            {
                ApplyEditorFrameRateLimit();
            }
            else
            {
                // Editor initialization applies game settings; the editor preference must follow it.
                PostEngineInitHandle = FCoreDelegates::OnPostEngineInit.AddRaw(
                    this, &FCkPluginsModule::ApplyEditorFrameRateLimit);
            }
        }
#endif
    }

    virtual void ShutdownModule() override
    {
#if WITH_EDITOR
        FCoreDelegates::OnPostEngineInit.Remove(PostEngineInitHandle);
#endif
        FDefaultGameModuleImpl::ShutdownModule();
    }

#if WITH_EDITOR
private:
    void ApplyEditorFrameRateLimit()
    {
        if (GIsEditor)
        {
            GetMutableDefault<UCkPluginsEditorPerformanceSettings>()->ApplyFrameRateLimit();
        }
    }

    FDelegateHandle PostEngineInitHandle;
#endif
};

IMPLEMENT_PRIMARY_GAME_MODULE(FCkPluginsModule, CkPlugins, "CkPlugins");
