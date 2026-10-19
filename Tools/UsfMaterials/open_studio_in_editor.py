"""User-run setup and PIE entry for the USF Materials studio validation."""
from pathlib import Path
import runpy
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
runpy.run_path(str(root / "Tools/UsfMaterials/prepare_shader_ball.py"), run_name="__main__")
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
                unreal.log("USF_STUDIO_MANUAL_CHECK: inspect the logo-free model and six materials; save one Studio*.ush color change and confirm it updates without restarting; O toggles outline, L reloads materials, G reloads shared lighting")
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
