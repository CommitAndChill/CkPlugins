#include "CkPluginsEditorPerformanceSettings.h"

#if WITH_EDITOR
#include "HAL/IConsoleManager.h"
#include "UObject/UnrealType.h"
#endif

#if WITH_EDITOR
void UCkPluginsEditorPerformanceSettings::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
    if (GIsEditor && HasAnyFlags(RF_ClassDefaultObject) &&
        (!PropertyChangedEvent.Property || PropertyChangedEvent.GetPropertyName() ==
            GET_MEMBER_NAME_CHECKED(UCkPluginsEditorPerformanceSettings, MaximumEditorFPS)))
    {
        ApplyFrameRateLimit();
    }

    Super::PostEditChangeProperty(PropertyChangedEvent);
}

void UCkPluginsEditorPerformanceSettings::ApplyFrameRateLimit()
{
    MaximumEditorFPS = FMath::Max(0, MaximumEditorFPS);

    if (IConsoleVariable* MaxFPS = IConsoleManager::Get().FindConsoleVariable(TEXT("t.MaxFPS")))
    {
        // Use the usual settings priority so explicit console/INI overrides still take precedence.
        MaxFPS->Set(static_cast<float>(MaximumEditorFPS), ECVF_SetByProjectSetting);
    }
}
#endif
