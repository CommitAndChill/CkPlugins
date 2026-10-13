#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "CkPluginsEditorPerformanceSettings.generated.h"

/** Per-user editor performance preferences for this CkPlugins project. */
UCLASS(config=EditorPerProjectUserSettings, meta=(DisplayName="CkPlugins Performance"))
class CKPLUGINS_API UCkPluginsEditorPerformanceSettings : public UDeveloperSettings
{
    GENERATED_BODY()

public:
    /** Maximum editor process FPS, including PIE. Zero disables the cap. Standalone games are unaffected. */
    UPROPERTY(EditAnywhere, config, Category="Frame Rate", meta=(DisplayName="Maximum Editor FPS", ClampMin="0", UIMin="0"))
    int32 MaximumEditorFPS = 30;

#if WITH_EDITOR
    virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;

    /** Apply the loaded preference after editor engine initialization. */
    void ApplyFrameRateLimit();
#endif
};
