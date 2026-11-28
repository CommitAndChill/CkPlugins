"""Dedicated transient Adaptive studio. Explicit offscreen launch, no desktop input or gym travel.

JSON file commands run on the editor thread. Existing maps, startup configuration and
baseline masters are never saved. Only prepare_adaptive_bsdf creates owned new assets.
"""
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

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
DIRECTORY = ROOT / 'Saved/UsfMaterialGallery'
REQUEST = DIRECTORY / 'AdaptiveRequest.json'
RESULT = DIRECTORY / 'AdaptiveResult.json'
_handle = None
_pending = None
_scene = {}
_busy = False


def _write(value):
    temporary = RESULT.with_suffix('.pending')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(RESULT)


def _world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def _state():
    names = ['r.Substrate', 'r.Substrate.ProjectGBufferFormat', 'r.Substrate.ProjectClosuresPerPixel',
             'r.Substrate.ProjectClosuresPerPixelOverride', 'r.Substrate.BytesPerPixel']
    state = {'pid': os.getpid(), 'cvars': {name: unreal.SystemLibrary.get_console_variable_int_value(name) for name in names}, 'looks': {}}
    def xyz(value):
        return [getattr(value, axis) for axis in ['x', 'y', 'z']]
    if _scene:
        camera = _scene['capture']
        rotation = camera.get_actor_rotation()
        settings = _scene['component'].get_editor_property('post_process_settings')
        state['rig'] = {'camera_location': xyz(camera.get_actor_location()), 'camera_rotation': [rotation.pitch, rotation.yaw, rotation.roll],
            'exposure': settings.get_editor_property('auto_exposure_min_brightness'),
            'gi_method': str(settings.get_editor_property('dynamic_global_illumination_method')),
            'reflection_method': str(settings.get_editor_property('reflection_method')),
            'anti_aliasing_method_cvar': unreal.SystemLibrary.get_console_variable_int_value('r.AntiAliasingMethod'),
            'show_flags': {str(item.show_flag_name): item.enabled for item in _scene['component'].get_editor_property('show_flag_settings')},
            'sky_intensity': _scene['sky'].light_component.get_editor_property('intensity'),
            'sky_cubemap': _scene['sky'].light_component.get_editor_property('cubemap').get_path_name(),
            'sky_mobility': str(_scene['sky'].light_component.get_editor_property('mobility')),
            'lights': [{'position': xyz(light.get_actor_location()),
                        'intensity': light.point_light_component.get_editor_property('intensity')} for light in _scene['lights']]}
        state['selected_mid'] = _scene['mesh'].get_material(_scene['slot']).get_path_name()
    generator = unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem)
    for name, record in _scene.get('materials', {}).items():
        material, mid = record
        from adaptive_bsdf_settings import LOOKS
        node = unreal.MaterialEditingLibrary.get_material_property_input_node(material, unreal.MaterialProperty.MP_FRONT_MATERIAL)
        stats = unreal.MaterialEditingLibrary.get_statistics(material)
        compiled = generator.get_compiled_substrate_stats(material)
        state['looks'][name] = {'master': material.get_path_name(), 'mid': mid.get_path_name(),
            'front_node': node.get_path_name(), 'front_class': node.get_class().get_name(),
            'scalars': {key: mid.get_scalar_parameter_value(key) for key, _ in LOOKS[name]['scalars']},
            'vectors': {key: [getattr(mid.get_vector_parameter_value(key), channel) for channel in ['r', 'g', 'b', 'a']] for key, _ in LOOKS[name]['vectors']},
            'textures': {key: mid.get_texture_parameter_value(key).get_path_name() for key, _, _ in LOOKS[name]['textures']},
            'compiled': {key: list(getattr(compiled, key)) if key == 'compile_errors' else getattr(compiled, key) for key in ['valid', 'closure_count', 'uint_per_pixel', 'compile_errors']},
            'statistics': {key: getattr(stats, key) for key in ['num_pixel_shader_instructions', 'num_vertex_shader_instructions', 'num_samplers']}}
    return state


def _spawn_scene():
    if _scene:
        raise RuntimeError('The transient showcase already exists')
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Preserve dirty map packages before constructing this owned transient scene')
    world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    if not world:
        raise RuntimeError('Could not create the transient showcase world')
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mesh_asset = unreal.load_asset('/CkTests/CkUsf/Showcase/SM_UsdShaderBall')
    if not isinstance(mesh_asset, unreal.StaticMesh):
        raise RuntimeError('Approved logo-free shader ball is missing')
    ball = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector())
    mesh = ball.static_mesh_component
    mesh.set_static_mesh(mesh_asset)
    mesh.set_editor_property('disallow_nanite', True)
    specimen = mesh.get_material_index('Specimen')
    core = mesh.get_material_index('CoreBase')
    if specimen < 0 or core < 0 or specimen == core:
        raise RuntimeError('Approved shader-ball material slots differ')
    stand = unreal.load_asset('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_StudioRubber')
    if not isinstance(stand, unreal.Material):
        raise RuntimeError('Approved neutral CoreBase material is missing')
    mesh.set_material(core, stand)
    _, extent = ball.get_actor_bounds(False)
    origin, _ = ball.get_actor_bounds(False)
    center = unreal.Vector(origin.x, origin.y, origin.z + extent.z * 0.12)
    radius = max(extent.x, extent.y, extent.z)
    lights = []
    for location, intensity, source_radius in [((-3.0, 0.0, 2.0), 15, .24), ((-1.6, 2.6, 1.0), 5, .8), ((2.2, .2, 2.3), 8, .35)]:
        position = center + unreal.Vector(*(radius * value for value in location))
        light = actors.spawn_actor_from_class(unreal.PointLight, position)
        component = light.point_light_component
        component.set_mobility(unreal.ComponentMobility.MOVABLE)
        component.set_intensity_units(unreal.LightUnits.CANDELAS)
        component.set_intensity(intensity)
        component.set_attenuation_radius(radius * 12)
        component.set_source_radius(radius * source_radius)
        lights.append(light)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    environment = unreal.load_asset('/Engine/EditorMaterials/AssetViewer/EpicQuadPanorama_CC+EV1')
    if not isinstance(environment, unreal.TextureCube):
        raise RuntimeError('Engine asset-viewer environment cubemap is missing')
    sky.light_component.set_cubemap(environment)
    sky.light_component.set_intensity(10)
    sky.light_component.recapture_sky()
    capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, center + unreal.Vector(-radius * 4.8, -radius * .75, radius * .8))
    capture.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(capture.get_actor_location(), center), False)
    component = capture.capture_component2d
    target = unreal.RenderingLibrary.create_render_target2d(world, 1280, 960, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    component.set_editor_property('texture_target', target)
    component.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    component.set_editor_property('capture_every_frame', False)
    component.set_editor_property('capture_on_movement', False)
    component.set_editor_property('always_persist_rendering_state', True)
    component.set_editor_property('fov_angle', 35)
    component.set_editor_property('show_flag_settings', [unreal.EngineShowFlagsSetting(show_flag_name=name, enabled=True) for name in ['AntiAliasing', 'PostProcessing', 'TemporalAA', 'SkyLighting', 'ReflectionEnvironment']])
    settings = component.get_editor_property('post_process_settings')
    for name, value in [('override_auto_exposure_min_brightness', True), ('override_auto_exposure_max_brightness', True),
                        ('auto_exposure_min_brightness', 1.5), ('auto_exposure_max_brightness', 1.5),
                        ('override_bloom_intensity', True), ('bloom_intensity', .1),
                        ('override_dynamic_global_illumination_method', True),
                        ('dynamic_global_illumination_method', unreal.DynamicGlobalIlluminationMethod.LUMEN),
                        ('override_reflection_method', True), ('reflection_method', unreal.ReflectionMethod.LUMEN)]:
        settings.set_editor_property(name, value)
    component.set_editor_property('post_process_settings', settings)
    component.set_editor_property('post_process_blend_weight', 1)
    from adaptive_bsdf_settings import LOOKS
    materials = {}
    for name in LOOKS:
        material = unreal.load_asset('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_' + name)
        if not isinstance(material, unreal.Material):
            raise RuntimeError('Prepare Adaptive materials first: ' + name)
        mid = unreal.MaterialLibrary.create_dynamic_material_instance(world, material)
        materials[name] = (material, mid)
    _scene.update(world=world, ball=ball, mesh=mesh, slot=specimen, center=center, radius=radius,
                  lights=lights, sky=sky, capture=capture, component=component, target=target, materials=materials)
    mesh.set_material(specimen, next(iter(materials.values()))[1])
    unreal.SystemLibrary.execute_console_command(world, 'Ck.Usf.AutoReload 1')
    return _state()


def _dispatch(request):
    action = request['action']
    if action == 'prepare':
        import prepare_adaptive_bsdf
        return prepare_adaptive_bsdf.prepare()
    if action == 'refine':
        if _scene:
            raise RuntimeError('Refine owned assets before constructing the transient scene')
        import prepare_adaptive_bsdf
        return prepare_adaptive_bsdf.refine()
    if action == 'scene':
        return _spawn_scene()
    if action == 'state':
        return _state()
    if action == 'diagnostics':
        unreal.SystemLibrary.execute_console_command(_world(), 'r.SceneCapture.DumpMemory')
        # DumpMemory is scoped to its render frame: capture in that same tick.
        _scene['component'].capture_scene()
        return _state()
    if action == 'lighting':
        intensities = request.get('intensities', [light.point_light_component.get_editor_property('intensity') for light in _scene['lights']])
        exposure = float(request.get('exposure', _scene['component'].get_editor_property('post_process_settings').get_editor_property('auto_exposure_min_brightness')))
        sky_intensity = float(request.get('sky_intensity', _scene['sky'].light_component.get_editor_property('intensity')))
        pipeline = request.get('pipeline')
        if pipeline not in [None, 'classic', 'lumen']:
            raise RuntimeError('Unknown capture lighting pipeline')
        if len(intensities) != 3 or any(not math.isfinite(float(value)) or not 0 <= float(value) <= 10000 for value in intensities):
            raise RuntimeError('Three bounded nonnegative point-light intensities are required')
        if not math.isfinite(exposure) or not -5 <= exposure <= 20 or not math.isfinite(sky_intensity) or not 0 <= sky_intensity <= 10:
            raise RuntimeError('Lighting exposure or sky intensity is out of range')
        for light, intensity in zip(_scene['lights'], intensities):
            light.point_light_component.set_intensity(float(intensity))
        settings = _scene['component'].get_editor_property('post_process_settings')
        settings.set_editor_property('auto_exposure_min_brightness', exposure)
        settings.set_editor_property('auto_exposure_max_brightness', exposure)
        if pipeline:
            settings.set_editor_property('dynamic_global_illumination_method', unreal.DynamicGlobalIlluminationMethod.LUMEN if pipeline == 'lumen' else unreal.DynamicGlobalIlluminationMethod.NONE)
            settings.set_editor_property('reflection_method', unreal.ReflectionMethod.LUMEN if pipeline == 'lumen' else unreal.ReflectionMethod.NONE)
        _scene['component'].set_editor_property('post_process_settings', settings)
        _scene['sky'].light_component.set_intensity(sky_intensity)
        return _state()
    if action == 'capture':
        look = request['look']
        from adaptive_bsdf_settings import LOOKS
        recipe = LOOKS[look]
        material, mid = _scene['materials'][look]
        allowed = dict(recipe['scalars'])
        if set(request.get('scalars', {})) - set(allowed):
            raise RuntimeError('Unknown scalar in capture request')
        for key, value in request.get('scalars', {}).items():
            if key not in allowed:
                raise RuntimeError('Unknown scalar: ' + key)
            mid.set_scalar_parameter_value(key, float(value))
        _scene['mesh'].set_material(_scene['slot'], mid)
        phase = math.radians(float(request.get('phase', 0)))
        center, radius = _scene['center'], _scene['radius']
        _scene['lights'][0].set_actor_location(center + unreal.Vector(-math.cos(phase)*radius*3, math.sin(phase)*radius*3, radius*2), False, False)
        distance = float(request.get('distance', 4.8))
        capture = _scene['capture']
        capture.set_actor_location(center + unreal.Vector(-radius*distance, -radius*.75, radius*.8), False, False)
        capture.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(capture.get_actor_location(), center), False)
        filename = request['name']
        if Path(filename).name != filename or not filename.endswith('.png'):
            raise RuntimeError('Capture requires a plain PNG filename')
        return None
    if action == 'quit':
        unreal.SystemLibrary.quit_editor()
        return {'quit_requested': True}
    raise RuntimeError('Unknown Adaptive action: ' + action)


def _tick(delta):
    global _busy, _pending
    if _busy:
        return
    _busy = True
    try:
        if _pending:
            request, deadline = _pending
            _scene['component'].capture_scene()
            if time.monotonic() >= deadline:
                path = DIRECTORY / request['name']
                previous_stamp = path.stat().st_mtime_ns if path.exists() else None
                unreal.RenderingLibrary.export_render_target(_world(), _scene['target'], str(DIRECTORY), request['name'])
                if not path.is_file() or path.stat().st_size < 1000 or path.stat().st_mtime_ns == previous_stamp:
                    raise RuntimeError('Scene capture export failed: ' + str(path))
                # UE5.8's exporter writes allocation slack after IEND. Preserve PNG bytes
                # through its validated terminator without decoding or changing pixels.
                path.write_bytes(canonical_png_bytes(path.read_bytes()))
                _write({'id': request['id'], 'ok': True, 'capture': str(path), 'state': _state()})
                _pending = None
        elif REQUEST.exists():
            request = json.loads(REQUEST.read_text(encoding='utf-8'))
            REQUEST.unlink()
            result = _dispatch(request)
            if request['action'] == 'capture':
                _pending = (request, time.monotonic() + 3)
            else:
                _write({'id': request['id'], 'ok': True, 'result': result})
    except Exception:
        error = traceback.format_exc()
        unreal.log_error(error)
        _write({'id': request.get('id') if 'request' in locals() else None, 'ok': False, 'error': error})
        _pending = None
    finally:
        _busy = False


if _handle is None:
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    if unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat') != 1:
        raise RuntimeError('This session requires the approved Adaptive startup profile')
    _handle = unreal.register_slate_post_tick_callback(_tick)
    _write({'ok': True, 'ready': True, 'pid': os.getpid()})
    unreal.log('USF_ADAPTIVE_SESSION_READY')
