"""Owned offscreen optical studio; all commands execute on the editor thread."""
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
from tail_lamp_settings import ASSET, LOOKS

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
DIRECTORY = ROOT / 'Saved/UsfMaterialGallery'
REQUEST, RESULT = DIRECTORY / 'TailLampRequest.json', DIRECTORY / 'TailLampResult.json'
_scene, _pending, _busy = {}, None, False


def _write(data):
    temporary = RESULT.with_suffix('.pending')
    temporary.write_text(json.dumps(data, indent=2), encoding='utf-8')
    temporary.replace(RESULT)


def _world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def _state():
    state = dict(pid=os.getpid(), adaptive=unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat'), looks={})
    if _scene:
        state['variant'] = _scene.get('variant', 'original')
        settings = _scene['component'].get_editor_property('post_process_settings')
        state['rig'] = dict(exposure=settings.get_editor_property('auto_exposure_min_brightness'),
                            show_flags={str(item.show_flag_name): item.enabled for item in _scene['component'].get_editor_property('show_flag_settings')},
                            sky_intensity=_scene['sky'].light_component.get_editor_property('intensity'),
                            lights=[dict(intensity=actor.point_light_component.get_editor_property('intensity'),
                                         source_radius=actor.point_light_component.get_editor_property('source_radius')) for actor in _scene['lights']])
    generator = unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem)
    for name, (master, mid) in _scene.get('materials', {}).items():
        record = dict(master=master.get_path_name(), mid=mid.get_path_name(),
                      scalars={key: mid.get_scalar_parameter_value(key) for key, _ in LOOKS[name]['scalars']},
                      vectors={key: [getattr(mid.get_vector_parameter_value(key), c) for c in 'rgba'] for key, _ in LOOKS[name]['vectors']},
                      textures={key: mid.get_texture_parameter_value(key).get_path_name() for key, _ in LOOKS[name]['textures']})
        if name.endswith('Lens'):
            front = unreal.MaterialEditingLibrary.get_material_property_input_node(master, unreal.MaterialProperty.MP_FRONT_MATERIAL)
            # The public statistics call submits and finishes missing lazy shader
            # permutations. A rendered subset alone is insufficient for proof.
            unreal.MaterialEditingLibrary.get_statistics(master)
            stats = generator.get_compiled_substrate_stats(master)
            record.update(front=front.get_path_name(), front_class=front.get_class().get_name(),
                          compiled={key: list(getattr(stats, key)) if key == 'compile_errors' else getattr(stats, key) for key in ['valid', 'closure_count', 'uint_per_pixel', 'compile_errors']})
        state['looks'][name] = record
    return state


def _spawn_scene(refined=False):
    if _scene or unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Scene exists or dirty maps need preservation')
    world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    materials = {}
    for name in LOOKS:
        master = unreal.load_asset(ASSET + '/GeneratedLooks/M_CkUsf_Look_' + name)
        if not isinstance(master, unreal.Material):
            raise RuntimeError('Prepare lamp masters before scene: ' + name)
        materials[name] = (master, unreal.MaterialLibrary.create_dynamic_material_instance(world, master))
    variants = {'original': dict(materials)}
    if refined:
        from prepare_tail_lamp_refinement import REPLACEMENTS
        refined_materials = {name: (master, unreal.MaterialLibrary.create_dynamic_material_instance(world, master))
                             for name, (master, _) in materials.items()}
        for role, name in REPLACEMENTS.items():
            master = unreal.load_asset(ASSET + '/GeneratedLooks/M_CkUsf_Look_' + name)
            if not isinstance(master, unreal.Material):
                raise RuntimeError('Prepare refined material before scene: ' + name)
            refined_materials['OpticalTailLamp' + role] = (master, unreal.MaterialLibrary.create_dynamic_material_instance(world, master))
        variants['refined'] = refined_materials
    # Manual scene captures do not register a player viewport streaming view.
    # Request only the textures actually used by this owned assembly, without
    # disabling project texture streaming or modifying persistent texture assets.
    textures = {}
    for variant_materials in variants.values():
        for name, (_, mid) in variant_materials.items():
            for parameter, _ in LOOKS[name]['textures']:
                texture = mid.get_texture_parameter_value(parameter)
                if not isinstance(texture, unreal.Texture2D):
                    raise RuntimeError('Owned optical texture is missing: ' + parameter)
                textures[texture.get_path_name()] = texture
    for texture in textures.values():
        texture.set_force_mip_levels_to_be_resident(120.0, 0)
    meshes = {}
    for role in ['Lens', 'Reflector', 'Housing', 'LED', 'Gasket', 'Fastener', 'LEDPackage']:
        asset = unreal.load_asset('/CkTests/CkUsf/Showcase/TailLamp/SM_TailLamp_' + role)
        if not isinstance(asset, unreal.StaticMesh):
            raise RuntimeError('Lamp mesh missing: ' + role)
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector())
        actor.set_actor_label('OpticalTailLamp_' + role)
        component = actor.static_mesh_component
        component.set_static_mesh(asset)
        component.set_editor_property('disallow_nanite', True)
        component.set_editor_property('cast_shadow', role != 'Lens')
        slot = component.get_material_index(role)
        if slot < 0:
            raise RuntimeError('Named material slot missing: ' + role)
        component.set_material(slot, materials['OpticalTailLamp' + role][1])
        meshes[role] = actor
    plane = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -.25))
    plane.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
    plane.set_actor_scale3d(unreal.Vector(3, 3, 3))
    plane.static_mesh_component.set_material(0, materials['OpticalTailLampHousing'][1])
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    environment = unreal.load_asset('/Engine/EditorMaterials/AssetViewer/EpicQuadPanorama_CC+EV1')
    if not isinstance(environment, unreal.TextureCube):
        raise RuntimeError('Verified engine studio cubemap missing')
    sky.light_component.set_cubemap(environment)
    sky.light_component.set_intensity(3)
    sky.light_component.recapture_sky()
    lights = []
    for position, intensity, radius in [((35, -22, 38), 35, 1), ((15, 28, 15), 12, 2), ((-8, 8, 30), 25, 1)]:
        actor = actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(*position))
        light = actor.point_light_component
        light.set_mobility(unreal.ComponentMobility.MOVABLE)
        light.set_intensity_units(unreal.LightUnits.CANDELAS)
        light.set_intensity(intensity)
        light.set_attenuation_radius(300)
        light.set_source_radius(radius)
        lights.append(actor)
    capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(49, -25, 19))
    capture.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(capture.get_actor_location(), unreal.Vector(0, 0, 5)), False)
    component = capture.capture_component2d
    target = unreal.RenderingLibrary.create_render_target2d(world, 1600, 1000, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    component.set_editor_property('texture_target', target)
    component.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    component.set_editor_property('capture_every_frame', False)
    component.set_editor_property('capture_on_movement', False)
    component.set_editor_property('always_persist_rendering_state', True)
    component.set_editor_property('fov_angle', 35)
    component.set_editor_property('show_flag_settings', [unreal.EngineShowFlagsSetting(show_flag_name=name, enabled=True) for name in ['AntiAliasing', 'PostProcessing', 'TemporalAA', 'SkyLighting', 'ReflectionEnvironment', 'Refraction']])
    settings = component.get_editor_property('post_process_settings')
    for name, value in [('override_auto_exposure_min_brightness', True), ('override_auto_exposure_max_brightness', True),
                        ('auto_exposure_min_brightness', 4.2), ('auto_exposure_max_brightness', 4.2),
                        ('override_bloom_intensity', True), ('bloom_intensity', .15),
                        ('override_dynamic_global_illumination_method', True), ('dynamic_global_illumination_method', unreal.DynamicGlobalIlluminationMethod.LUMEN),
                        ('override_reflection_method', True), ('reflection_method', unreal.ReflectionMethod.LUMEN)]:
        settings.set_editor_property(name, value)
    component.set_editor_property('post_process_settings', settings)
    component.set_editor_property('post_process_blend_weight', 1)
    _scene.update(materials=materials, variants=variants, variant='original', textures=textures, meshes=meshes, sky=sky, lights=lights, capture=capture, component=component, target=target, plane=plane)
    unreal.SystemLibrary.execute_console_command(world, 'Ck.Usf.AutoReload 1')
    return _state()


def _dispatch(request):
    action = request['action']
    if action == 'prepare':
        if _scene:
            raise RuntimeError('Prepare before constructing the owned scene')
        import importlib
        import tail_lamp_settings
        import prepare_tail_lamp
        importlib.reload(tail_lamp_settings)
        importlib.reload(prepare_tail_lamp)
        return prepare_tail_lamp.prepare()
    if action == 'scene':
        return _spawn_scene(bool(request.get('refined', False)))
    if action == 'prepare_refined':
        if _scene:
            raise RuntimeError('Prepare refinement before constructing the owned scene')
        import importlib
        import prepare_tail_lamp_refinement
        return importlib.reload(prepare_tail_lamp_refinement).prepare()
    if action == 'state':
        return _state()
    if action == 'diagnostics':
        unreal.SystemLibrary.execute_console_command(_world(), 'InvestigateTexture T_TailLamp_LensNormal')
        return _state()
    if action == 'capture':
        variant = request.get('variant', _scene['variant'])
        if variant not in _scene['variants']:
            raise RuntimeError('Requested finish variant was not prepared for this scene')
        if variant != _scene['variant']:
            materials = _scene['variants'][variant]
            for role, actor in _scene['meshes'].items():
                component = actor.static_mesh_component
                component.set_material(component.get_material_index(role), materials['OpticalTailLamp' + role][1])
            # Keep the studio floor identical in matched finish comparisons.
            _scene.update(materials=materials, variant=variant)
        for texture in _scene['textures'].values():
            texture.set_force_mip_levels_to_be_resident(120.0, 0)
        filename = request['name']
        if Path(filename).name != filename or not filename.endswith('.png'):
            raise RuntimeError('Capture requires plain PNG filename')
        for name, values in request.get('scalars', {}).items():
            recipe = LOOKS[name]
            if set(values) - set(dict(recipe['scalars'])):
                raise RuntimeError('Unknown scalar control')
            for key, value in values.items():
                if not math.isfinite(value):
                    raise RuntimeError('Finite scalar required')
                _scene['materials'][name][1].set_scalar_parameter_value(key, value)
        for name, values in request.get('vectors', {}).items():
            if set(values) - set(dict(LOOKS[name]['vectors'])):
                raise RuntimeError('Unknown vector control')
            for key, value in values.items():
                _scene['materials'][name][1].set_vector_parameter_value(key, unreal.LinearColor(*value))
        _scene['meshes']['Lens'].set_actor_hidden_in_game(bool(request.get('hide_lens', False)))
        if 'camera' in request:
            _scene['capture'].set_actor_location(unreal.Vector(*request['camera']), False, False)
        _scene['capture'].set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(_scene['capture'].get_actor_location(), unreal.Vector(0, 0, 5)), False)
        if 'phase' in request:
            phase = math.radians(request['phase'])
            _scene['lights'][0].set_actor_location(unreal.Vector(40 * math.cos(phase), 40 * math.sin(phase), 35), False, False)
        if 'exposure' in request:
            settings = _scene['component'].get_editor_property('post_process_settings')
            settings.set_editor_property('auto_exposure_min_brightness', request['exposure'])
            settings.set_editor_property('auto_exposure_max_brightness', request['exposure'])
            _scene['component'].set_editor_property('post_process_settings', settings)
        if 'refraction' in request:
            flags = list(_scene['component'].get_editor_property('show_flag_settings'))
            for flag in flags:
                if str(flag.show_flag_name) == 'Refraction':
                    flag.enabled = bool(request['refraction'])
            _scene['component'].set_editor_property('show_flag_settings', flags)
        for key, property_name in [('intensities', 'intensity'), ('source_radii', 'source_radius')]:
            if key in request:
                values = request[key]
                if len(values) != 3 or any(not math.isfinite(value) or value < 0 or value > 1000 for value in values):
                    raise RuntimeError('Three bounded nonnegative light controls required')
                for actor, value in zip(_scene['lights'], values):
                    actor.point_light_component.set_editor_property(property_name, value)
        if 'sky_intensity' in request:
            value = request['sky_intensity']
            if not math.isfinite(value) or not 0 <= value <= 10:
                raise RuntimeError('Bounded nonnegative skylight intensity required')
            _scene['sky'].light_component.set_intensity(value)
        return None
    if action == 'quit':
        for texture in _scene.get('textures', {}).values():
            texture.set_force_mip_levels_to_be_resident(0.0, 0)
        unreal.SystemLibrary.quit_editor()
        return dict(quit_requested=True)
    raise RuntimeError('Unknown optical command: ' + action)


def _tick(delta):
    global _busy, _pending
    if _busy:
        return
    _busy = True
    request = None
    try:
        if _pending:
            request, deadline = _pending
            _scene['component'].capture_scene()
            if time.monotonic() >= deadline:
                path = DIRECTORY / request['name']
                previous_stamp = path.stat().st_mtime_ns if path.exists() else None
                unreal.RenderingLibrary.export_render_target(_world(), _scene['target'], str(DIRECTORY), request['name'])
                if not path.is_file() or path.stat().st_size < 1000 or path.stat().st_mtime_ns == previous_stamp:
                    raise RuntimeError('Optical scene export failed')
                path.write_bytes(canonical_png_bytes(path.read_bytes()))
                _write(dict(id=request['id'], ok=True, capture=str(path), state=_state()))
                _pending = None
        elif REQUEST.exists():
            request = json.loads(REQUEST.read_text(encoding='utf-8'))
            REQUEST.unlink()
            result = _dispatch(request)
            if request['action'] == 'capture':
                _pending = (request, time.monotonic() + 3)
            else:
                _write(dict(id=request['id'], ok=True, result=result))
    except Exception:
        error = traceback.format_exc()
        unreal.log_error(error)
        _write(dict(id=request.get('id') if request else None, ok=False, error=error))
        _pending = None
    finally:
        _busy = False


DIRECTORY.mkdir(parents=True, exist_ok=True)
if unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat') != 1:
    raise RuntimeError('Optical session requires separate Adaptive startup profile')
_handle = unreal.register_slate_post_tick_callback(_tick)
_write(dict(ok=True, ready=True, pid=os.getpid()))
unreal.log('USF_TAIL_LAMP_SESSION_READY')
