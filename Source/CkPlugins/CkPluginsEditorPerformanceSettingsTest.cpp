#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CkPluginsEditorPerformanceSettings.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/AutomationTest.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "UObject/UnrealType.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FCkPluginsEditorPerformanceSettingsTest,
    "CkPlugins.EditorPerformance.UserSettings",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FCkPluginsEditorPerformanceSettingsTest::RunTest(const FString& Parameters)
{
    UCkPluginsEditorPerformanceSettings* Settings = GetMutableDefault<UCkPluginsEditorPerformanceSettings>();
    IConsoleVariable* MaxFPS = IConsoleManager::Get().FindConsoleVariable(TEXT("t.MaxFPS"));
    FProperty* FPSProperty = FindFProperty<FProperty>(Settings->GetClass(),
        GET_MEMBER_NAME_CHECKED(UCkPluginsEditorPerformanceSettings, MaximumEditorFPS));
    if (!TestNotNull(TEXT("Engine FPS console variable exists"), MaxFPS) ||
        !TestNotNull(TEXT("FPS preference property exists"), FPSProperty))
    {
        return false;
    }

    TestEqual(TEXT("Preferences register in the editor container"), Settings->GetContainerName(), FName(TEXT("Editor")));
    TestEqual(TEXT("Preferences use per-project user config"), Settings->GetClass()->ClassConfigName,
        FName(TEXT("EditorPerProjectUserSettings")));
    TestFalse(TEXT("Normal UI saves do not write repo defaults"), Settings->GetClass()->HasAnyClassFlags(CLASS_DefaultConfig));
    TestEqual(TEXT("Startup applied the loaded FPS preference"), MaxFPS->GetFloat(), static_cast<float>(Settings->MaximumEditorFPS));

    // Preserve the user's in-memory preference and never write their actual settings file.
    const int32 OriginalPreference = Settings->MaximumEditorFPS;
    const float OriginalFPS = MaxFPS->GetFloat();
    const EConsoleVariableFlags OriginalPriority = static_cast<EConsoleVariableFlags>(MaxFPS->GetFlags() & ECVF_SetByMask);
    const FString TestConfig = FConfigCacheIni::NormalizeConfigIniPath(
        FPaths::CreateTempFilename(*FPaths::ProjectSavedDir(), TEXT("CkPluginsEditorFPS"), TEXT(".ini")));
    ON_SCOPE_EXIT
    {
        Settings->MaximumEditorFPS = OriginalPreference;
        MaxFPS->Set(OriginalFPS, OriginalPriority);
        GConfig->UnloadFile(TestConfig);
        IFileManager::Get().Delete(*TestConfig);
    };

    auto ChangePreference = [Settings, FPSProperty](int32 FPS)
    {
        Settings->MaximumEditorFPS = FPS;
        FPropertyChangedEvent Event(FPSProperty, EPropertyChangeType::ValueSet);
        Settings->PostEditChangeProperty(Event);
    };

    ChangePreference(60);
    TestEqual(TEXT("Editing FPS applies immediately"), MaxFPS->GetFloat(), 60.0f);
    Settings->SaveConfig(CPF_Config, *TestConfig);
    TestTrue(TEXT("User preference serialization writes the config file"), IFileManager::Get().FileExists(*TestConfig));

    ChangePreference(0);
    TestEqual(TEXT("Zero disables the editor FPS cap"), MaxFPS->GetFloat(), 0.0f);
    UCkPluginsEditorPerformanceSettings* ReloadedSettings = NewObject<UCkPluginsEditorPerformanceSettings>();
    ReloadedSettings->LoadConfig(nullptr, *TestConfig);
    TestEqual(TEXT("Saved preference survives config reload"), ReloadedSettings->MaximumEditorFPS, 60);
    TestEqual(TEXT("Loading an ordinary settings object does not change the running editor cap"), MaxFPS->GetFloat(), 0.0f);

    ChangePreference(-1);
    TestEqual(TEXT("Negative config values normalize to uncapped"), Settings->MaximumEditorFPS, 0);
    TestEqual(TEXT("Negative values do not produce an invalid FPS cap"), MaxFPS->GetFloat(), 0.0f);
    return !HasAnyErrors();
}

#endif
