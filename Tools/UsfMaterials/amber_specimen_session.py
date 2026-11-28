"""Owned offscreen amber studio. Serial requests execute on the editor thread."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import json
import math
import os
import time
import traceback
import unreal
from canonical_capture_png import canonical_png_bytes
from amber_specimen_settings import ASSET, LOOKS

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
REQUEST, RESULT = OUTPUT / 'AmberRequest.json', OUTPUT / 'AmberResult.json'
_scene, _pending, _busy = {}, None, False


def write(data):
    temporary = RESULT.with_suffix('.pending')
    temporary.write_text(json.dumps(data, indent=2))
    temporary.replace(RESULT)


def state():
    result = dict(pid=os.getpid(), adaptive=unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat'), looks={})
    if not _scene:
        return result
    generator = unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem)
    for role, (master, mid) in _scene['materials'].items():
        recipe = LOOKS[role]
        record = dict(master=master.get_path_name(), mid=mid.get_path_name(),
            scalars={key: mid.get_scalar_parameter_value(key) for key, _ in recipe['scalars']},
            vectors={key: [getattr(mid.get_vector_parameter_value(key), channel) for channel in 'rgba'] for key, _ in recipe['vectors']},
            textures={key: mid.get_texture_parameter_value(key).get_path_name() for key, _ in recipe['textures']})
        if role == 'Body':
            unreal.MaterialEditingLibrary.get_statistics(master)
            front = unreal.MaterialEditingLibrary.get_material_property_input_node(master, unreal.MaterialProperty.MP_FRONT_MATERIAL)
            stats = generator.get_compiled_substrate_stats(master)
            record.update(front=front.get_path_name(), compiled={key: list(getattr(stats, key)) if key == 'compile_errors' else getattr(stats, key) for key in ['valid', 'closure_count', 'uint_per_pixel', 'compile_errors']})
        result['looks'][role] = record
    settings = _scene['component'].get_editor_property('post_process_settings')
    camera = _scene['capture'].get_actor_location()
    result['rig'] = dict(camera=[camera.x, camera.y, camera.z],
        exposure=settings.get_editor_property('auto_exposure_min_brightness'),
        sky=_scene['sky'].light_component.get_editor_property('intensity'),
        lights=[dict(position=[actor.get_actor_location().x, actor.get_actor_location().y, actor.get_actor_location().z],
                     intensity=actor.point_light_component.get_editor_property('intensity'),
                     radius=actor.point_light_component.get_editor_property('source_radius')) for actor in _scene['lights']])
    result['visible'] = dict(_scene['visible'])
    if 'hero' in _scene:
        hero = _scene['hero']
        result['hero'] = dict(bubbles=hero['bubble_count'],
            leaf_shadow=hero['leaf_actor'].static_mesh_component.get_editor_property('cast_shadow'),
            debris_shadow=hero['debris_actor'].static_mesh_component.get_editor_property('cast_shadow'),
            leaf_tint=[getattr(hero['leaf'].get_vector_parameter_value('TintColor'), c) for c in 'rgba'],
            leaf_transmission=hero['leaf'].get_scalar_parameter_value('TransmissionStrength'))
    return result


def scene():
    if _scene or unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Preserve the existing scene/dirty maps')
    world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    materials, meshes, textures = {}, {}, {}
    for role, recipe in LOOKS.items():
        master = unreal.load_asset(ASSET + '/GeneratedLooks/M_CkUsf_Look_' + recipe['name'])
        if not isinstance(master, unreal.Material):
            raise RuntimeError('Prepare amber masters first')
        unreal.MaterialEditingLibrary.get_statistics(master)
        mid = unreal.MaterialLibrary.create_dynamic_material_instance(world, master)
        materials[role] = (master, mid)
        for parameter, _ in recipe['textures']:
            texture = mid.get_texture_parameter_value(parameter)
            if not isinstance(texture, unreal.Texture2D):
                raise RuntimeError('Missing amber texture backing')
            textures[texture.get_path_name()] = texture
        mesh = unreal.load_asset('/CkTests/CkUsf/Showcase/AmberSpecimen/SM_AmberSpecimen_' + role)
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError('Missing amber mesh')
        actor = subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector())
        actor.set_actor_label('AmberSpecimen_' + role)
        component = actor.static_mesh_component
        component.set_static_mesh(mesh)
        slot = component.get_material_index(role)
        if slot < 0:
            raise RuntimeError('Missing amber named slot')
        component.set_material(slot, mid)
        component.set_editor_property('disallow_nanite', True)
        component.set_editor_property('cast_shadow', role != 'Body')
        meshes[role] = actor
    neutral = unreal.load_asset(ASSET + '/GeneratedLooks/M_CkUsf_Look_OpticalTailLampHousing')
    if not isinstance(neutral, unreal.Material):
        raise RuntimeError('Verified charcoal studio material missing')
    stand = subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(-.45, 0, -.35))
    stand.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cylinder'))
    stand.set_actor_scale3d(unreal.Vector(.048, .075, .007))
    stand.static_mesh_component.set_material(0, neutral)
    floor = subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -.72))
    floor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
    floor.set_actor_scale3d(unreal.Vector(2, 2, 2))
    floor.static_mesh_component.set_material(0, neutral)
    sky = subsystem.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    environment = unreal.load_asset('/Engine/EditorMaterials/AssetViewer/EpicQuadPanorama_CC+EV1')
    if not isinstance(environment, unreal.TextureCube):
        raise RuntimeError('Verified studio cubemap missing')
    sky.light_component.set_cubemap(environment)
    sky.light_component.set_intensity(1.4)
    sky.light_component.recapture_sky()
    lights = []
    for position, intensity, radius in [((16, -14, 19), 18, .8), ((12, 16, 10), 7, 1.2), ((-4, 5, 14), 14, 1)]:
        actor = subsystem.spawn_actor_from_class(unreal.PointLight, unreal.Vector(*position))
        light = actor.point_light_component
        light.set_mobility(unreal.ComponentMobility.MOVABLE)
        light.set_intensity_units(unreal.LightUnits.CANDELAS)
        light.set_intensity(intensity)
        light.set_attenuation_radius(180)
        light.set_source_radius(radius)
        lights.append(actor)
    capture = subsystem.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(29, -10, 12))
    component = capture.capture_component2d
    target = unreal.RenderingLibrary.create_render_target2d(world, 1600, 1200, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    for key, value in [('texture_target', target), ('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR),
                       ('capture_every_frame', False), ('capture_on_movement', False), ('always_persist_rendering_state', True), ('fov_angle', 32)]:
        component.set_editor_property(key, value)
    capture.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(capture.get_actor_location(), unreal.Vector(0, 0, 3.8)), False)
    component.set_editor_property('show_flag_settings', [unreal.EngineShowFlagsSetting(show_flag_name=name, enabled=True) for name in ['AntiAliasing', 'PostProcessing', 'TemporalAA', 'SkyLighting', 'ReflectionEnvironment', 'Refraction']])
    settings = component.get_editor_property('post_process_settings')
    for name, value in [('override_auto_exposure_min_brightness', True), ('override_auto_exposure_max_brightness', True),
                        ('auto_exposure_min_brightness', 4.8), ('auto_exposure_max_brightness', 4.8),
                        ('override_bloom_intensity', True), ('bloom_intensity', .05),
                        ('override_dynamic_global_illumination_method', True), ('dynamic_global_illumination_method', unreal.DynamicGlobalIlluminationMethod.LUMEN),
                        ('override_reflection_method', True), ('reflection_method', unreal.ReflectionMethod.LUMEN)]:
        settings.set_editor_property(name, value)
    component.set_editor_property('post_process_settings', settings)
    component.set_editor_property('post_process_blend_weight', 1)
    for texture in textures.values():
        texture.set_force_mip_levels_to_be_resident(120, 0)
    _scene.update(world=world, materials=materials, meshes=meshes, textures=textures, sky=sky, lights=lights,
                  capture=capture, component=component, target=target, visible={role: True for role in LOOKS})
    unreal.SystemLibrary.execute_console_command(world, 'Ck.Usf.AutoReload 1')
    return state()


def dispatch(request):
    action = request['action']
    if action == 'state':
        return state()
    if action == 'prepare':
        if _scene:
            raise RuntimeError('Prepare before owned scene creation')
        import importlib
        import prepare_amber_specimen
        return importlib.reload(prepare_amber_specimen).prepare()
    if action == 'scene':
        return scene()
    if action == 'hero':
        if not _scene:
            scene()
        if 'hero' in _scene:
            raise RuntimeError('Preserve existing hero scene; no duplicate assembly')
        import amber_hero_scene
        return amber_hero_scene.apply(_scene)
    if action == 'capture':
        filename = request['name']
        if Path(filename).name != filename or not filename.endswith('.png'):
            raise RuntimeError('Plain PNG filename required')
        controls = request.get('hero_controls', {})
        if controls:
            if 'hero' not in _scene or set(controls) - {'leaf_shadow', 'debris_shadow', 'leaf_tint', 'leaf_transmission'}:
                raise RuntimeError('Known hero controls require the hero scene')
            for key in ['leaf_shadow', 'debris_shadow']:
                if key in controls and not isinstance(controls[key], bool):
                    raise RuntimeError('Shadow controls must be boolean')
            if 'leaf_tint' in controls and (len(controls['leaf_tint']) != 4 or any(not math.isfinite(v) or not 0 <= v <= 2 for v in controls['leaf_tint'])):
                raise RuntimeError('Four bounded leaf tint channels required')
            if 'leaf_transmission' in controls and (not math.isfinite(controls['leaf_transmission']) or not 0 <= controls['leaf_transmission'] <= 2):
                raise RuntimeError('Bounded leaf transmission required')
            for key, actor in [('leaf_shadow', 'leaf_actor'), ('debris_shadow', 'debris_actor')]:
                if key in controls:
                    _scene['hero'][actor].static_mesh_component.set_editor_property('cast_shadow', controls[key])
            if 'leaf_tint' in controls:
                _scene['hero']['leaf'].set_vector_parameter_value('TintColor', unreal.LinearColor(*controls['leaf_tint']))
            if 'leaf_transmission' in controls:
                _scene['hero']['leaf'].set_scalar_parameter_value('TransmissionStrength', controls['leaf_transmission'])
        for role, values in request.get('scalars', {}).items():
            if set(values) - set(dict(LOOKS[role]['scalars'])) or any(not math.isfinite(value) for value in values.values()):
                raise RuntimeError('Unknown/nonfinite amber scalar')
            for key, value in values.items():
                _scene['materials'][role][1].set_scalar_parameter_value(key, value)
        for role, values in request.get('vectors', {}).items():
            if set(values) - set(dict(LOOKS[role]['vectors'])) or any(len(v) != 4 or any(not math.isfinite(x) for x in v) for v in values.values()):
                raise RuntimeError('Unknown/nonfinite amber vector')
            for key, value in values.items():
                _scene['materials'][role][1].set_vector_parameter_value(key, unreal.LinearColor(*value))
        for role, visible in request.get('visible', {}).items():
            _scene['meshes'][role].set_actor_hidden_in_game(not bool(visible))
            _scene['visible'][role] = bool(visible)
        if 'camera' in request:
            _scene['capture'].set_actor_location(unreal.Vector(*request['camera']), False, False)
        _scene['capture'].set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(_scene['capture'].get_actor_location(), unreal.Vector(0, 0, 3.8)), False)
        if 'phase' in request:
            phase = math.radians(request['phase'])
            _scene['lights'][0].set_actor_location(unreal.Vector(22 * math.cos(phase), 22 * math.sin(phase), 19), False, False)
        if 'exposure' in request:
            settings = _scene['component'].get_editor_property('post_process_settings')
            settings.set_editor_property('auto_exposure_min_brightness', request['exposure'])
            settings.set_editor_property('auto_exposure_max_brightness', request['exposure'])
            _scene['component'].set_editor_property('post_process_settings', settings)
        for key, field in [('intensities', 'intensity'), ('source_radii', 'source_radius')]:
            if key in request:
                values = request[key]
                if len(values) != 3 or any(not math.isfinite(value) or not 0 <= value <= 1000 for value in values):
                    raise RuntimeError('Three finite bounded light controls required')
                for actor, value in zip(_scene['lights'], values):
                    actor.point_light_component.set_editor_property(field, value)
        if 'sky' in request:
            value = request['sky']
            if not math.isfinite(value) or not 0 <= value <= 10:
                raise RuntimeError('Bounded skylight intensity required')
            _scene['sky'].light_component.set_intensity(value)
        for texture in _scene['textures'].values():
            texture.set_force_mip_levels_to_be_resident(120, 0)
        return None
    if action == 'quit':
        for texture in _scene.get('textures', {}).values():
            texture.set_force_mip_levels_to_be_resident(0, 0)
        unreal.SystemLibrary.quit_editor()
        return dict(quit_requested=True)
    raise RuntimeError('Unknown amber command')


def tick(delta):
    global _pending, _busy
    if _busy:
        return
    _busy = True
    request = None
    try:
        if _pending:
            request, deadline = _pending
            _scene['component'].capture_scene()
            if time.monotonic() >= deadline:
                path = OUTPUT / request['name']
                stamp = path.stat().st_mtime_ns if path.exists() else None
                unreal.RenderingLibrary.export_render_target(_scene['world'], _scene['target'], str(OUTPUT), request['name'])
                if not path.is_file() or path.stat().st_mtime_ns == stamp or path.stat().st_size < 1000:
                    raise RuntimeError('Amber capture export failed')
                path.write_bytes(canonical_png_bytes(path.read_bytes()))
                write(dict(id=request['id'], ok=True, capture=str(path), state=state()))
                _pending = None
        elif REQUEST.exists():
            request = json.loads(REQUEST.read_text())
            REQUEST.unlink()
            result = dispatch(request)
            if request['action'] == 'capture':
                _pending = (request, time.monotonic() + 3)
            else:
                write(dict(id=request['id'], ok=True, result=result))
    except Exception:
        message = traceback.format_exc()
        unreal.log_error(message)
        write(dict(id=request.get('id') if request else None, ok=False, error=message))
        _pending = None
    finally:
        _busy = False


if unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat') != 1:
    raise RuntimeError('Amber requires the separate Adaptive profile')
OUTPUT.mkdir(parents=True, exist_ok=True)
_handle = unreal.register_slate_post_tick_callback(tick)
write(dict(ok=True, ready=True, pid=os.getpid()))
unreal.log('USF_AMBER_SESSION_READY')
