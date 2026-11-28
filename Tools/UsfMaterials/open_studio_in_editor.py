"""User-run setup and PIE entry for the USF Materials studio validation."""
from pathlib import Path
import importlib.util
import time
import traceback
import unreal

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if editor.get_game_world():
    raise RuntimeError("Stop PIE before preparing the studio")
assert unreal.SystemLibrary.get_console_variable_int_value("r.Substrate") == 1, "Enable project Substrate and restart"
assert unreal.SystemLibrary.get_console_variable_int_value("r.Substrate.ProjectGBufferFormat") == 0, "Select Blendable GBuffer and restart"
root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
def prepare_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, root / 'Tools/UsfMaterials' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.prepare()


mesh = unreal.load_asset('/CkTests/CkUsf/Showcase/SM_UsdShaderBall')
starters = ('StudioCeramic', 'StudioCopper', 'StudioRubber', 'StudioLacquer', 'StudioWax', 'Toon')
needs_specimen = not mesh or unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'CkUsfStudio.ConversionVersion') != '3'
needs_starters = any(not unreal.EditorAssetLibrary.does_asset_exist('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_' + name) for name in starters)
if needs_specimen or needs_starters:
    prepare_module('ck_studio_specimen_preparation', 'prepare_shader_ball.py')
if not unreal.EditorAssetLibrary.does_asset_exist('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_IndustrialPaint'):
    prepare_module('ck_studio_industrial_preparation', 'prepare_industrial.py')
library = ('LibrarySilk', 'LibraryLeather', 'LibraryTile', 'LibraryOak', 'LibraryAluminum', 'LibraryPlastic')
if any(not unreal.EditorAssetLibrary.does_asset_exist('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_' + name) for name in library):
    prepare_module('ck_studio_library_preparation', 'prepare_batch1.py')
batch2 = ('LibraryCanvas', 'LibrarySuede', 'LibraryTerracotta', 'LibraryMarble', 'LibraryRubber', 'LibraryGlass')
if any(not unreal.EditorAssetLibrary.does_asset_exist('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_' + name) for name in batch2):
    prepare_module('ck_studio_batch2_preparation', 'prepare_batch2.py')
batch3 = ('LibraryVelvet', 'LibraryWalnut', 'LibraryGranite', 'LibraryBrass', 'LibraryFrostedGlass', 'LibraryCarbonFiber')
if any(not unreal.EditorAssetLibrary.does_asset_exist('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_' + name) for name in batch3):
    prepare_module('ck_studio_batch3_preparation', 'prepare_batch3.py')
batch4 = ('LibraryKnit', 'LibraryPatentLeather', 'LibraryPorcelain', 'LibraryTerrazzo', 'LibraryTranslucentPlastic', 'LibraryCork')
if any(not unreal.EditorAssetLibrary.does_asset_exist('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_' + name) for name in batch4):
    prepare_module('ck_studio_batch4_preparation', 'prepare_batch4.py')
batch5 = ('LibraryDenim', 'LibraryConcrete', 'LibraryBrick', 'LibraryStainlessSteel', 'LibraryPlywood', 'LibraryCardboard')
if any(not unreal.EditorAssetLibrary.does_asset_exist('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_' + name) for name in batch5):
    prepare_module('ck_studio_batch5_preparation', 'prepare_batch5.py')
batch6 = ('LibraryLinen', 'LibrarySmoothLeather', 'LibraryMosaic', 'LibraryPine', 'LibraryLimestone', 'LibraryGalvanizedSteel')
if any(not unreal.EditorAssetLibrary.does_asset_exist('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_' + name) for name in batch6):
    prepare_module('ck_studio_batch6_preparation', 'prepare_batch6.py')
batch7 = ('LibraryNylon', 'LibrarySlate', 'LibraryCopper', 'LibraryGlossyPlastic', 'LibraryWax', 'LibraryFiberglass')
if any(not unreal.EditorAssetLibrary.does_asset_exist('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_' + name) for name in batch7):
    prepare_module('ck_studio_batch7_preparation', 'prepare_batch7.py')
if (not unreal.EditorAssetLibrary.does_asset_exist('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_EnvironmentRiverPebbles')
        or not unreal.EditorAssetLibrary.does_asset_exist('/CkTests/CkUsf/Showcase/SM_UsfWoodlandGrid')
        or not unreal.EditorAssetLibrary.does_asset_exist('/CkFoundation/CkUsf/Textures/Environment/T_EnvironmentRiverPebbles_Height')):
    prepare_module('ck_studio_river_pebbles_preparation', 'prepare_river_pebbles.py')
dioramas = ('EnvironmentDioramaGrass', 'EnvironmentDioramaDirt', 'EnvironmentDioramaMud')
if any(not unreal.EditorAssetLibrary.does_asset_exist('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_' + name) for name in dioramas):
    prepare_module('ck_studio_diorama_preparation', 'prepare_diorama_patches.py')
if "TestGyms_CkTests_Level" not in editor.get_editor_world().get_path_name():
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError("Save your open map before switching to the gym")
    if not level.load_level("/CkTests/TestGyms/TestGyms_CkTests_Level"):
        raise RuntimeError("Gym map failed to load")
unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), "Ck.Usf.AutoReload 1")
settings = unreal.get_default_object(unreal.load_class(None, "/Script/CkTests.CkGym_StartupSettings"))
original = (settings.get_editor_property("StartupMode"), settings.get_editor_property("DefaultGymName"))
startup_api = unreal.get_default_object(unreal.load_class(None, "/Script/CkTests.Ck_Utils_GymStartup_UE"))
set_startup = getattr(startup_api, "request_set_startup_mode")
set_default_gym = getattr(startup_api, "request_set_default_gym_name")
started = time.monotonic()
handle = None


def restore():
    # Gym travel updates recents through SaveConfig, which also writes temporary
    # startup fields. Restore through the real setters so disk and CDO agree.
    set_startup(original[0])
    set_default_gym(original[1])
    if handle is not None:
        unreal.unregister_slate_post_tick_callback(handle)


def ready(delta):
    try:
        world = editor.get_game_world()
        if world:
            controller = unreal.GameplayStatics.get_player_controller(world, 0)
            actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
            if controller and any("UsfGym_ToonShowcase" in actor.get_class().get_name() for actor in actors):
                unreal.SystemLibrary.execute_console_command(world, "Ck_UsfGym_Control 4", controller)
                unreal.log("USF_STUDIO_MANUAL_CHECK: inspect forty-two library materials, four optional IndustrialPaint presets, river pebbles and three dioramas with POM/displacement pairs; save a look/shared-helper color change and confirm existing instances update without restarting; I toggles orbit light, P pauses, K resets phase, O toggles outline, L reloads materials, G reloads shared lighting")
                restore()
                return
        if time.monotonic()-started > 180:
            raise RuntimeError("Studio gym did not become ready within 180 seconds")
    except Exception:
        unreal.log_error(traceback.format_exc())
        restore()


try:
    settings.set_editor_property("StartupMode", type(original[0]).DEFAULT)
    settings.set_editor_property("DefaultGymName", "USF Materials")
    handle = unreal.register_slate_post_tick_callback(ready)
    level.editor_request_begin_play()
except Exception:
    restore()
    raise
