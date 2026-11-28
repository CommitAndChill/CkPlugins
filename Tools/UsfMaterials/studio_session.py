"""Input-independent editor validation. Import once; submit JSON commands under Saved.

Intended for a stable script schema. Finish AngelScript edits before importing.
Commands: state, gc, prepare, open, capture, end, quit. Never sends desktop input.
"""
from pathlib import Path
import gc
import importlib.util
import json
import os
import sys
import time
import traceback
import unreal
from advanced_bsdf_settings import LOOKS as ADVANCED_LOOKS

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
DIRECTORY = ROOT / 'Saved/UsfMaterialGallery'
DIRECTORY.mkdir(parents=True, exist_ok=True)
REQUEST = DIRECTORY / 'StudioRequest.json'
RESULT = DIRECTORY / 'StudioResult.json'
_handle = globals().get('_handle')
_busy = False
_pending = None
_task = None
_deadline = 0.0
_startup = None
_proof_objects = []
_library_proof = {}
_diagnostic_light = globals().get('_diagnostic_light')
_preview_cvars = globals().get('_preview_cvars', {})
_diagnostic_quantization = globals().get('_diagnostic_quantization')
_current_id = globals().get('_current_id')

LIBRARY = ['LibrarySilk', 'LibraryLeather', 'LibraryTile', 'LibraryOak', 'LibraryAluminum', 'LibraryPlastic',
           'LibraryCanvas', 'LibrarySuede', 'LibraryTerracotta', 'LibraryMarble', 'LibraryRubber', 'LibraryGlass',
           'LibraryVelvet', 'LibraryWalnut', 'LibraryGranite', 'LibraryBrass', 'LibraryFrostedGlass', 'LibraryCarbonFiber',
           'LibraryKnit', 'LibraryPatentLeather', 'LibraryPorcelain', 'LibraryTerrazzo', 'LibraryTranslucentPlastic', 'LibraryCork', 'LibraryDenim', 'LibraryConcrete', 'LibraryBrick', 'LibraryStainlessSteel', 'LibraryPlywood', 'LibraryCardboard', 'LibraryLinen', 'LibrarySmoothLeather', 'LibraryMosaic', 'LibraryPine', 'LibraryLimestone', 'LibraryGalvanizedSteel',
           'LibraryNylon', 'LibrarySlate', 'LibraryCopper', 'LibraryGlossyPlastic', 'LibraryWax', 'LibraryFiberglass', 'NativePorcelainSlab', 'NativeCeramicToon']
LIBRARY_SCALARS = {
    'LibrarySilk': ['Anisotropy', 'FiberRotation'],
    'LibraryLeather': ['PoreContrast'],
    'LibraryTile': ['GroutNormalStrength', 'GroutRoughness', 'GlazeWeight', 'GlazeRoughness'],
    'LibraryOak': ['FinishWeight', 'FinishRoughness'],
    'LibraryAluminum': ['Anisotropy', 'BrushRotation'],
    'LibraryPlastic': ['SpecularLevel'],
    'LibraryCanvas': ['WeaveContrast'],
    'LibrarySuede': ['NapWeight', 'NapContrast'],
    'LibraryTerracotta': ['FiringVariation'],
    'LibraryMarble': ['VeinContrast', 'Polish'],
    'LibraryRubber': ['SpecularLevel'],
    'LibraryGlass': ['SpecularLevel', 'TransmissionAmount', 'GlassCoverage', 'Ior'],
    'LibraryVelvet': ['FuzzWeight'],
    'LibraryWalnut': ['GrainContrast', 'FinishWeight', 'FinishRoughness'],
    'LibraryGranite': ['MineralContrast', 'Polish'],
    'LibraryBrass': ['FinishVariation', 'Anisotropy', 'BrushRotation'],
    'LibraryFrostedGlass': ['SpecularLevel', 'TransmissionAmount', 'GlassCoverage', 'BlurRadius'],
    'LibraryCarbonFiber': ['CoatWeight', 'CoatRoughness'],
    'LibraryKnit': ['FuzzWeight'],
    'LibraryPatentLeather': ['CoatWeight', 'CoatRoughness'],
    'LibraryPorcelain': ['GroutNormalStrength', 'GroutRoughness', 'GlazeWeight', 'GlazeRoughness'],
    'LibraryTerrazzo': ['AggregateContrast', 'Polish'],
    'LibraryTranslucentPlastic': ['BodyCoverage', 'TransmissionAmount', 'GlassCoverage', 'Ior'],
    'LibraryCork': ['PoreContrast'],
    'LibraryDenim': ['FuzzWeight'], 'LibraryConcrete': ['PoreContrast'],
    'LibraryBrick': ['UVAspect', 'FiringVariation'], 'LibraryStainlessSteel': ['MetalColorVariation', 'Polish'],
    'LibraryPlywood': ['FinishWeight', 'FinishRoughness'], 'LibraryCardboard': ['FiberContrast'],
    'LibraryLinen': ['FuzzWeight'], 'LibrarySmoothLeather': ['GrainContrast'],
    'LibraryMosaic': ['GroutNormalStrength', 'GroutRoughness', 'GlazeWeight', 'GlazeRoughness'],
    'LibraryPine': ['FinishWeight', 'FinishRoughness'], 'LibraryLimestone': ['PoreContrast'],
    'LibraryGalvanizedSteel': ['SpangleContrast'],
    'LibraryNylon': ['SheenWeight'], 'LibrarySlate': ['ReliefContrast'],
    'LibraryCopper': ['FinishVariation'], 'LibraryGlossyPlastic': ['GlossWeight'],
    'LibraryWax': ['ScatterWeight'], 'LibraryFiberglass': ['ResinWeight', 'ResinRoughness'],
    'NativePorcelainSlab': ['GroutNormalStrength', 'GroutRoughness'],
    'NativeCeramicToon': ['GroutNormalStrength', 'GroutRoughness']}

LIBRARY += list(ADVANCED_LOOKS)
for _name, _recipe in ADVANCED_LOOKS.items():
    LIBRARY_SCALARS[_name] = [key for key, _ in _recipe['scalars']
        if key not in ['UVScale', 'UVRotation', 'NormalStrength', 'RoughnessScale', 'RoughnessBias', 'DebugView']]

ENVIRONMENT_SCALARS = ['UVScale', 'UVRotation', 'NormalStrength', 'RoughnessScale',
                       'RoughnessBias', 'ReliefCm', 'TileSizeCm', 'PomAmount',
                       'DisplacementAmount', 'StepCount', 'HeightMip', 'DebugView']
_environment_proof = {}

ENVIRONMENT_STATIONS = [('pom', 'Usf.Ground.Pom'), ('displacement', 'Usf.Ground.Displacement'),
                        ('grass_pom', 'Usf.Diorama.Grass.Pom'), ('grass_displacement', 'Usf.Diorama.Grass.Displacement'),
                        ('dirt_pom', 'Usf.Diorama.Dirt.Pom'), ('dirt_displacement', 'Usf.Diorama.Dirt.Displacement'),
                        ('mud_pom', 'Usf.Diorama.Mud.Pom'), ('mud_displacement', 'Usf.Diorama.Mud.Displacement')]


def _restore_environment_dither():
    global _diagnostic_quantization
    if _diagnostic_quantization is None:
        return
    saved = _diagnostic_quantization
    world = _editor().get_game_world() or _editor().get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, 'r.BackbufferQuantizationDitheringOverride ' + str(saved))
    if unreal.SystemLibrary.get_console_variable_int_value('r.BackbufferQuantizationDitheringOverride') != saved:
        raise RuntimeError('Environment quantization override did not restore; saved state retained')
    _diagnostic_quantization = None


def _inspection_state(world):
    if not world: return None
    actors=[actor for actor in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor)
            if 'Usf.InspectionOrbit' in list(map(str,actor.tags))]
    if len(actors)!=1: raise RuntimeError('Expected exactly one reusable inspection light')
    actor=actors[0]
    target=actor.get_editor_property('Target')
    light=actor.get_editor_property('MovingLight')
    rigs={}
    rig_bounds={}
    for specimen in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor):
        components={component.get_name():component for component in specimen.get_components_by_class(unreal.RectLightComponent)}
        names=['StudioKey','StudioFill','StudioRim']
        if all(name in components for name in names):
            rigs[specimen.get_path_name()]=[components[name].get_editor_property('intensity') for name in names]
            center,extent=specimen.get_actor_bounds(False)
            rig_bounds[specimen.get_path_name()]={'origin':[getattr(center,a) for a in ['x','y','z']], 'extent':[getattr(extent,a) for a in ['x','y','z']]}

    return {'actor':actor.get_path_name(),'enabled':bool(actor.get_editor_property('Enabled')),
            'paused':bool(actor.get_editor_property('Paused')),'phase':float(actor.get_editor_property('PhaseDegrees')),
            'radius':float(actor.get_editor_property('OrbitRadiusCm')),'height':float(actor.get_editor_property('OrbitHeightCm')),
            'speed':float(actor.get_editor_property('AngularSpeedDegrees')),
            'target':target.get_path_name() if target else None,'intensity':light.get_editor_property('intensity'),
            'light_class':light.get_class().get_name(), 'intensity_units':str(light.get_editor_property('intensity_units')),
            'source_radius':light.get_editor_property('source_radius'), 'attenuation_radius':light.get_editor_property('attenuation_radius'),
            'light_location':[getattr(light.get_world_location(),axis) for axis in ['x','y','z']],
            'rigs':rigs,'rig_bounds':rig_bounds}


def _environment(world):
    result = {}
    if world:
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
            matches = [(key, tag) for key, tag in ENVIRONMENT_STATIONS if tag in list(map(str, actor.tags))]
            if len(matches) > 1:
                raise RuntimeError('An environment actor has multiple registered mode tags')
            for key, _ in matches:
                if key in result:
                    raise RuntimeError('Duplicate ground specimen: ' + key)
                mesh = actor.get_component_by_class(unreal.StaticMeshComponent)
                if not isinstance(mesh, unreal.StaticMeshComponent):
                    raise RuntimeError('Ground requires its existing static mesh component')
                slot = mesh.get_material_index('Specimen')
                if slot < 0:
                    raise RuntimeError('Ground requires its named Specimen material slot')
                mid = mesh.get_material(slot)
                if not isinstance(mid, unreal.MaterialInstanceDynamic):
                    raise RuntimeError('Ground requires its existing generated MID')
                result[key] = (actor, mid, mid.get_editor_property('parent'))
    return result


def _environment_state(world):
    result = {}
    for key, (actor, mid, parent) in _environment(world).items():
        mesh = actor.get_component_by_class(unreal.StaticMeshComponent)
        result[key] = {'actor': actor.get_path_name(), 'mid': mid.get_path_name(),
                       'parent': parent.get_path_name(), 'mesh': mesh.static_mesh.get_path_name(),
                       'values': {name: mid.get_scalar_parameter_value(name) for name in ENVIRONMENT_SCALARS},
                       'colors': {'TintColor': [getattr(mid.get_vector_parameter_value('TintColor'), c) for c in ['r', 'g', 'b', 'a']]},
                       'textures': {name + 'Map': mid.get_texture_parameter_value(name + 'Map').get_path_name()
                                    for name in ['BaseColor', 'Normal', 'Roughness', 'Height', 'AO']},
                       'scale': [getattr(actor.get_actor_scale3d(), c) for c in ['x', 'y', 'z']],
                       'rect_intensities': [light.get_editor_property('intensity') for light in actor.get_components_by_class(unreal.RectLightComponent)],
                       'same_mid': mid == _environment_proof[key][0] if key in _environment_proof else None,
                       'same_master': parent == _environment_proof[key][1] if key in _environment_proof else None}
    return result


def _library(world):
    records = {}
    if not world:
        return records
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if not any(part in actor.get_class().get_name() for part in ['UsfGym_StudioShowcase', 'UsfGym_LibraryShowcase']):
            continue
        mesh = actor.get_component_by_class(unreal.StaticMeshComponent)
        slot = mesh.get_material_index('Specimen') if mesh else -1
        mid = mesh.get_material(slot) if slot >= 0 else None
        if not isinstance(mid, unreal.MaterialInstanceDynamic):
            continue
        parent = mid.get_editor_property('parent')
        for name in LIBRARY:
            if parent.get_name() == 'M_CkUsf_Look_' + name:
                if name in records:
                    raise RuntimeError('Duplicate library specimen: ' + name)
                records[name] = (actor, mid, parent)
    return records


def _library_state(world):
    result = {}
    for name, (actor, mid, parent) in _library(world).items():
        bounds = unreal.SystemLibrary.get_component_bounds(actor.get_component_by_class(unreal.StaticMeshComponent))
        scalars = ['UVScale', 'UVRotation', 'NormalStrength', 'RoughnessScale', 'RoughnessBias', 'DebugView'] + LIBRARY_SCALARS[name]
        colors = ['TintColor'] + (['GroutColor'] if name in ['LibraryTile', 'LibraryPorcelain', 'LibraryMosaic', 'NativePorcelainSlab', 'NativeCeramicToon'] else []) + (['NapColor'] if name == 'LibrarySuede' else []) + (['FuzzColor'] if name in ['LibraryVelvet', 'LibraryKnit', 'LibraryDenim', 'LibraryLinen'] else []) + (['TransmissionTint'] if name == 'LibraryTranslucentPlastic' else [])
        if name in ADVANCED_LOOKS:
            colors = [key for key, _ in ADVANCED_LOOKS[name]['vectors']]
        textures = (['NormalMap', 'RoughnessMap'] if name in ['LibraryGlass', 'LibraryFrostedGlass'] else ['BaseColorMap', 'NormalMap', 'RoughnessMap']) + (['TileMask'] if name in ['LibraryTile', 'LibraryPorcelain', 'LibraryMosaic', 'NativePorcelainSlab', 'NativeCeramicToon'] else [])
        if name == 'LibraryWax':
            colors += ['ScatterTint']
        if name in ['LibrarySilk', 'LibraryAluminum']:
            textures += ['DirectionMap']
        if name == 'LibrarySilk':
            textures += ['AnisotropyMap']
        result[name] = {'mesh_bounds': {'origin': [getattr(bounds[0], axis) for axis in ['x', 'y', 'z']], 'extent': [getattr(bounds[1], axis) for axis in ['x', 'y', 'z']]}, 'actor': actor.get_path_name(), 'mid': mid.get_path_name(), 'parent': parent.get_path_name(),
                        'values': {key: mid.get_scalar_parameter_value(key) for key in scalars},
                        'colors': {key: [getattr(mid.get_vector_parameter_value(key), channel) for channel in ['r', 'g', 'b', 'a']] for key in colors},
                        'textures': {key: mid.get_texture_parameter_value(key).get_path_name() for key in textures},
                        'point_lights': [{'name': light.get_name(), 'tags': list(map(str, light.get_editor_property('component_tags'))),
                            'intensity': light.get_editor_property('intensity'), 'units': str(light.get_editor_property('intensity_units')),
                            'radius': light.get_editor_property('attenuation_radius'), 'source_radius': light.get_editor_property('source_radius'),
                            'location': [getattr(light.get_world_location(), axis) for axis in ['x', 'y', 'z']],
                            'world_scale': [getattr(light.get_world_scale(), axis) for axis in ['x', 'y', 'z']]}
                            for light in actor.get_components_by_class(unreal.PointLightComponent)],
                        'rect_intensities': [light.get_editor_property('intensity') for light in actor.get_components_by_class(unreal.RectLightComponent)],
                        'same_mid': mid == _library_proof[name][0] if name in _library_proof else None,
                        'same_master': parent == _library_proof[name][1] if name in _library_proof else None}
    return result


def _restore_diagnostic_light():
    global _diagnostic_light
    if _diagnostic_light is not None:
        for light, intensity in _diagnostic_light['rects']:
            light.set_intensity(intensity)
        point = _diagnostic_light['point']
        saved = _diagnostic_light['point_state']
        point.set_world_location(saved['location'], False, False)
        # Editor property mutation reconstructs AS actors and deletes dynamic components.
        # Restore through runtime setters so the existing rig and MIDs survive inspection.
        for key, value in saved['properties'].items():
            if key == 'lighting_channels':
                point.set_lighting_channels(value.channel0, value.channel1, value.channel2)
            else:
                getattr(point, 'set_' + key)(value)
        point.set_intensity(0)
        for light, intensity in _diagnostic_light.get('other_points', []):
            light.set_intensity(intensity)
        _diagnostic_light = None


def _set_diagnostic_light(world, actor, mode):
    global _diagnostic_light
    if mode == 'studio':
        _restore_diagnostic_light()
        return
    if _diagnostic_light and _diagnostic_light['actor'] == actor:
        _diagnostic_light['point'].set_intensity(60)
        return
    _restore_diagnostic_light()
    rects = [(light, light.get_editor_property('intensity')) for light in actor.get_components_by_class(unreal.RectLightComponent)]
    if len(rects) != 3:
        raise RuntimeError('Expected three studio lights for the diagnostic')
    points = list(actor.get_components_by_class(unreal.PointLightComponent))
    component = next((light for light in points if light.get_name() == 'DirectionalInspection'), None)
    if not component or component.get_editor_property('intensity') != 0:
        raise RuntimeError('The owned disabled directional-inspection component is unavailable')
    other_points = [(light, light.get_editor_property('intensity')) for light in points if light != component]
    point_state = {'location': component.get_world_location(), 'properties': {
        key: component.get_editor_property(key) for key in ['mobility', 'intensity_units', 'attenuation_radius',
            'source_radius', 'source_length', 'cast_shadows']}}
    point_state['properties']['lighting_channels'] = component.get_editor_property('lighting_channels').copy()
    _diagnostic_light = {'actor': actor, 'rects': rects, 'point': component, 'other_points': other_points, 'point_state': point_state}
    for light, intensity in other_points:
        light.set_intensity(0)
    component.set_world_location(actor.get_actor_location() + unreal.Vector(-140, -100, 140), False, False)
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_lighting_channels(False, True, False)
    component.set_intensity_units(unreal.LightUnits.CANDELAS)
    component.set_intensity(60)
    component.set_attenuation_radius(500)
    component.set_source_radius(0)
    component.set_source_length(0)
    component.set_cast_shadows(False)
    for light, intensity in rects:
        light.set_intensity(0)


def _editor():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)


def _industrial(world):
    return sorted((actor for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
                   if 'UsfGym_IndustrialShowcase' in actor.get_class().get_name()),
                  key=lambda actor: int(actor.get_name().rpartition('_')[2]))


def _write(value):
    value['id'] = _current_id
    RESULT.write_text(json.dumps(value, indent=2))


def _restore_startup():
    global _startup
    if _startup is not None:
        api = unreal.get_default_object(unreal.load_class(None, '/Script/CkTests.Ck_Utils_GymStartup_UE'))
        api.request_set_startup_mode(_startup[0])
        api.request_set_default_gym_name(_startup[1])
        _startup = None


def _native_bsdf_state(world):
    result = {}
    for name, (actor, mid, parent) in _library(world).items():
        if name not in ['NativePorcelainSlab', 'NativeCeramicToon'] and name not in ADVANCED_LOOKS:
            continue
        node = unreal.MaterialEditingLibrary.get_material_property_input_node(
            parent, unreal.MaterialProperty.MP_FRONT_MATERIAL)
        expected = (unreal.MaterialExpressionSubstrateSlabBSDF if name == 'NativePorcelainSlab'
                    else unreal.MaterialExpressionSubstrateToonBSDF)
        if name in ADVANCED_LOOKS:
            expected = (unreal.MaterialExpressionSubstrateSimpleClearCoatBSDF
                        if ADVANCED_LOOKS[name]['surface_graph'] == 3 else unreal.MaterialExpressionSubstrateSlabBSDF)
        if not isinstance(node, expected):
            raise RuntimeError('Native showcase has the wrong FrontMaterial node: ' + name)
        profile = node.get_editor_property('toon_profile') if name == 'NativeCeramicToon' else None
        result[name] = {'node': node.get_path_name(), 'class': node.get_class().get_name(),
                        'profile': profile.get_path_name() if profile else None}
    return result


def _state():
    world = _editor().get_game_world()
    records = []
    camera_state = None
    if world:
        pc = unreal.GameplayStatics.get_player_controller(world, 0)
        camera = unreal.GameplayStatics.get_player_camera_manager(world, 0)
        camera_state = {'pawn': str(pc.get_controlled_pawn().get_actor_location()),
                        'camera': str(camera.get_camera_location()),
                        'rotation': str(camera.get_camera_rotation()),
                        'control': str(pc.get_control_rotation())}
        for index, actor in enumerate(_industrial(world)):
            mesh = actor.get_component_by_class(unreal.StaticMeshComponent)
            slot = mesh.get_material_index('Specimen')
            mid = mesh.get_material(slot)
            values = {key: mid.get_scalar_parameter_value(key)
                      for key in ['Wear', 'RustAmount', 'DustAmount', 'MaskOffset', 'NormalStrength',
                                  'DebugView', 'MaskTiling', 'SurfaceTiling', 'PaintBlur', 'Wetness', 'ScratchAmount']}
            colors = {}
            for key in ['PaintColor', 'PrimerColor']:
                color = mid.get_vector_parameter_value(key)
                colors[key] = [color.r, color.g, color.b, color.a]
            textures = {key: mid.get_texture_parameter_value(key).get_path_name()
                        for key in ['DetailData', 'PlacementData']}
            parent = mid.get_editor_property('parent')
            records.append({'actor': actor.get_path_name(), 'mid': mid.get_path_name(),
                            'parent': parent.get_path_name(), 'values': values, 'colors': colors, 'textures': textures,
                            'same_mid': mid == _proof_objects[index][0] if _proof_objects else None,
                            'same_master': parent == _proof_objects[index][1] if _proof_objects else None})
    return {'pid': os.getpid(), 'world_time': unreal.GameplayStatics.get_time_seconds(world) if world else None, 'camera': camera_state, 'substrate': unreal.SystemLibrary.get_console_variable_int_value('r.Substrate'),
            'gbuffer': unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat'),
            'industrial': records, 'library': _library_state(world), 'environment': _environment_state(world),
            'native_bsdf': _native_bsdf_state(world),
            'inspection_orbit': _inspection_state(world),
            'render_cvars': {key: unreal.SystemLibrary.get_console_variable_float_value(key) for key in
                             ['r.ScreenPercentage', 'r.AntiAliasingMethod', 'r.SSR.Quality', 'r.DynamicRes.OperationMode',
                              'r.BackbufferQuantizationDitheringOverride']},
            'preview_quality': bool(_preview_cvars),
            'diagnostic_quantization': _diagnostic_quantization is not None,
            'diagnostic_light': {'actor': _diagnostic_light['actor'].get_path_name(),
                                 'saved_rect_intensities': [value for light, value in _diagnostic_light['rects']],
                                 'point': _diagnostic_light['point'].get_path_name()} if _diagnostic_light else None}


def _frame(request):
    world = _editor().get_game_world()
    if not world:
        raise RuntimeError('PIE is required for specimen capture')
    if request.get('environment'):
        actor = _environment(world)[request['environment']][0]
    elif request.get('look'):
        actor = _library(world)[request['look']][0]
    else:
        specimens = _industrial(world)
        index = int(request.get('preset', 1))
        if len(specimens) != 4 or index not in range(4):
            raise RuntimeError('Expected four industrial specimens and a preset index 0..3')
        actor = specimens[index]
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    target, extent = actor.get_actor_bounds(False)
    eye = target + unreal.Vector(-float(request.get('distance', 210)),
                                  float(request.get('side', 0)), float(request.get('height', 35)))
    pc.get_controlled_pawn().set_actor_location(eye, False, False)
    rotation = unreal.MathLibrary.find_look_at_rotation(eye, target)
    rotation.roll = float(request.get('roll', 0))
    pc.set_control_rotation(rotation)
    mesh = actor.get_component_by_class(unreal.StaticMeshComponent)
    mid = mesh.get_material(mesh.get_material_index('Specimen'))
    for key, parameter in [('debug', 'DebugView'), ('mask_tiling', 'MaskTiling'), ('wetness', 'Wetness')]:
        if key in request:
            mid.set_scalar_parameter_value(parameter, float(request[key]))
    allowed = ['UVScale', 'UVRotation', 'NormalStrength', 'RoughnessScale', 'RoughnessBias', 'DebugView'] + LIBRARY_SCALARS.get(request.get('look'), [])
    if request.get('environment'):
        allowed = ENVIRONMENT_SCALARS
    for key, value in request.get('parameters', {}).items():
        if key not in allowed:
            raise RuntimeError('Unsupported specimen parameter: ' + key)
        mid.set_scalar_parameter_value(key, float(value))
    colors = ['TintColor'] + (['NapColor'] if request.get('look') == 'LibrarySuede' else []) + (['GroutColor'] if request.get('look') in ['LibraryTile', 'LibraryPorcelain', 'LibraryMosaic', 'NativePorcelainSlab', 'NativeCeramicToon'] else []) + (['FuzzColor'] if request.get('look') in ['LibraryVelvet', 'LibraryKnit', 'LibraryDenim', 'LibraryLinen'] else [])
    colors += ['TransmissionTint'] if request.get('look') == 'LibraryTranslucentPlastic' else []
    colors += ['ScatterTint'] if request.get('look') == 'LibraryWax' else []
    if request.get('look') in ADVANCED_LOOKS:
        colors = [key for key, _ in ADVANCED_LOOKS[request['look']]['vectors']]
    for key, values in request.get('vectors', {}).items():
        if key not in colors or len(values) != 4:
            raise RuntimeError('Unknown library color or invalid RGBA: ' + key)
        mid.set_vector_parameter_value(key, unreal.LinearColor(*values))
    if request.get('lighting'):
        _set_diagnostic_light(world, actor, request['lighting'])


def _dispatch(request):
    global _pending, _deadline, _startup, _proof_objects, _library_proof, _preview_cvars, _environment_proof, _diagnostic_quantization
    action = request['action']
    unreal.log('USF_SESSION_BEGIN ' + str(request))
    if action == 'refresh':
        if _diagnostic_quantization is not None:
            raise RuntimeError('End the environment quantization diagnostic before refreshing the module')
        importlib.reload(sys.modules[__name__])
        return {'refreshed': True}
    if action == 'native_bsdf_prepare':
        if _editor().get_game_world():
            raise RuntimeError('End PIE before generating native BSDF assets')
        import prepare_native_bsdf
        return prepare_native_bsdf.prepare()
    if action == 'native_toon_profile':
        if _editor().get_game_world():
            raise RuntimeError('End PIE before editing the native Toon profile')
        import prepare_native_toon_profile
        return prepare_native_toon_profile.prepare()
    if action == 'advanced_bsdf_prepare':
        if _editor().get_game_world():
            raise RuntimeError('End PIE before generating advanced native BSDF assets')
        import prepare_advanced_bsdf
        importlib.reload(prepare_advanced_bsdf)
        return prepare_advanced_bsdf.prepare()
    if action == 'advanced_bsdf_refine':
        if _editor().get_game_world():
            raise RuntimeError('End PIE before native BSDF default refinement')
        import refine_advanced_bsdf
        return refine_advanced_bsdf.prepare()
    if action == 'state':
        return _state()
    if action in ['environment_dither_begin', 'environment_dither_end']:
        if action == 'environment_dither_end':
            _restore_environment_dither()
            return _state()
        if _diagnostic_quantization is not None:
            raise RuntimeError('Environment quantization diagnostic is already active')
        world = _editor().get_game_world()
        if not world:
            raise RuntimeError('PIE is required for the environment quantization diagnostic')
        _diagnostic_quantization = unreal.SystemLibrary.get_console_variable_int_value('r.BackbufferQuantizationDitheringOverride')
        try:
            unreal.SystemLibrary.execute_console_command(world, 'r.BackbufferQuantizationDitheringOverride 32')
            if unreal.SystemLibrary.get_console_variable_int_value('r.BackbufferQuantizationDitheringOverride') != 32:
                raise RuntimeError('Environment quantization diagnostic override was not applied')
        except Exception:
            _restore_environment_dither()
            raise
        return _state()
    if action in ['orbit_on','orbit_off','orbit_pause','orbit_resume','orbit_phase','orbit_reset','orbit_intensity','orbit_respawn']:
        world=_editor().get_game_world()
        if not world: raise RuntimeError('Open the gym before orbit inspection')
        if action=='orbit_intensity':
            import math
            value=float(request['intensity'])
            if not math.isfinite(value) or not 0<=value<=1000: raise RuntimeError('Inspection intensity must be finite,0..1000 cd')
            state=_inspection_state(world)
            if not state['enabled']: raise RuntimeError('Enable the inspection light before adjusting it')
            actors=[actor for actor in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor)
                    if 'Usf.InspectionOrbit' in list(map(str,actor.tags))]
            light=actors[0].get_editor_property('MovingLight')
            if not isinstance(light,unreal.PointLightComponent): raise RuntimeError('Inspection must use its Point light')
            light.set_intensity(value)
            return _state()
        commands={'orbit_on':'Ck_UsfGym_SetOrbit true','orbit_off':'Ck_UsfGym_SetOrbit false',
                  'orbit_pause':'Ck_UsfGym_SetOrbitPaused true','orbit_resume':'Ck_UsfGym_SetOrbitPaused false',
                  'orbit_phase':'Ck_UsfGym_SetOrbitPhase '+str(request.get('phase',0)),
                  'orbit_reset':'Ck_UsfGym_ResetOrbit','orbit_respawn':'Ck_UsfGym_Control 0'}
        unreal.SystemLibrary.execute_console_command(world,commands[action],unreal.GameplayStatics.get_player_controller(world,0))
        return _state()
    if action == 'environment1_grid_state':
        mesh = unreal.load_asset('/CkTests/CkUsf/Showcase/SM_UsfGroundGrid')
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError('The owned ground mesh has not been imported')
        return {'path': mesh.get_path_name(),
                'slots': [str(item.material_slot_name) for item in mesh.static_materials],
                'imported_from': mesh.get_editor_property('asset_import_data').get_first_filename(),
                'source_tag': unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'CkUsfEnvironment.SourceSHA256')}
    if action in ['plastic_fill_on', 'plastic_fill_off']:
        world = _editor().get_game_world()
        actor = _library(world)['LibraryTranslucentPlastic'][0]
        lights = [light for light in actor.get_components_by_class(unreal.PointLightComponent)
                  if 'Usf.TranslucentBodyFill' in list(map(str, light.get_editor_property('component_tags')))]
        if len(lights) != 1:
            raise RuntimeError('Expected one owned plastic body fill')
        lights[0].set_intensity(80 if action == 'plastic_fill_on' else 0)
        return _state()
    if action in ['glass_pane_begin', 'glass_pane_end', 'surface_pane_begin', 'surface_pane_end']:
        world = _editor().get_game_world()
        if not world:
            raise RuntimeError('Glass pane inspection requires PIE')
        pc = unreal.GameplayStatics.get_player_controller(world, 0)
        enabled = action in ['glass_pane_begin', 'surface_pane_begin']
        look = request.get('look', 'LibraryGlass')
        if look not in ['LibraryGlass', 'LibraryFrostedGlass', 'LibraryTranslucentPlastic', 'LibraryPorcelain', 'LibraryMosaic']:
            raise RuntimeError('Pane inspection requires a glass look')
        unreal.SystemLibrary.execute_console_command(world, 'Ck_UsfGym_GlassPane ' + ('1' if enabled else '0') + ' ' + look + (' 1' if action.startswith('surface_pane') else ' 0'), pc)
        actors = [actor for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
                  if 'UsfGym_GlassPaneInspection' in actor.get_class().get_name()]
        if len(actors) != int(enabled):
            raise RuntimeError('Unexpected pane inspection actor count')
        return {'enabled': enabled, 'actors': [actor.get_path_name() for actor in actors]}
    if action in ['preview_quality', 'restore_quality']:
        if action == 'preview_quality':
            if _preview_cvars:
                raise RuntimeError('Preview quality is already active')
            _preview_cvars = {key: unreal.SystemLibrary.get_console_variable_float_value(key)
                              for key in ['r.AntiAliasingMethod', 'r.ScreenPercentage']}
            values = {'r.AntiAliasingMethod': 2, 'r.ScreenPercentage': 100}
        else:
            values = dict(_preview_cvars)
        for key, value in values.items():
            unreal.SystemLibrary.execute_console_command(_editor().get_game_world(), key + ' ' + str(value))
        if action == 'restore_quality':
            _preview_cvars = {}
        return _state()
    if action == 'select':
        world = _editor().get_game_world()
        index = int(request.get('preset', 1))
        if not world or index not in range(4):
            raise RuntimeError('Select requires the open gym and a preset index 0..3')
        pc = unreal.GameplayStatics.get_player_controller(world, 0)
        unreal.SystemLibrary.execute_console_command(world, 'Ck_UsfGym_Control 3', pc)
        available = _library(world)
        present = [name for name in LIBRARY if name in available]
        steps = 6 + present.index(request['look']) if request.get('look') else 6 + len(present) + index
        if request.get('environment'):
            steps = 6 + len(present) + 4 + [key for key, _ in ENVIRONMENT_STATIONS].index(request['environment'])
        for step in range(steps):
            unreal.SystemLibrary.execute_console_command(world, 'Ck_UsfGym_Control 1', pc)
        _frame(request)
        return _state()
    if action == 'proof_begin':
        world = _editor().get_game_world()
        objects = []
        for actor in _industrial(world):
            mesh = actor.get_component_by_class(unreal.StaticMeshComponent)
            mid = mesh.get_material(mesh.get_material_index('Specimen'))
            objects.append((mid, mid.get_editor_property('parent')))
        if len(objects) != 4:
            raise RuntimeError('Four industrial instances are required')
        _proof_objects = objects
        return _state()
    if action == 'library_proof_begin':
        objects = _library(_editor().get_game_world())
        # Advanced stations are optional until explicitly prepared; avoid editor asset APIs in PIE.
        # The requested proof driver separately requires every specimen in its target roster.
        required = set(LIBRARY) - set(ADVANCED_LOOKS)
        if not required.issubset(objects) or not set(objects).issubset(LIBRARY):
            raise RuntimeError('All declared library specimens are required')
        _library_proof = {name: (values[1], values[2]) for name, values in objects.items()}
        return _state()
    if action == 'environment_proof_begin':
        objects = _environment(_editor().get_game_world())
        if set(objects) != {key for key, _ in ENVIRONMENT_STATIONS}:
            raise RuntimeError('All eight river-pebble and diorama ground specimens are required')
        _environment_proof = {key: (values[1], values[2]) for key, values in objects.items()}
        return _state()
    if action == 'proof_end':
        _proof_objects = []
        _library_proof = {}
        _environment_proof = {}
        return {'proof_objects_released': True}
    if action == 'cost':
        material = unreal.load_asset('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_IndustrialPaint')
        stats = unreal.MaterialEditingLibrary.get_statistics(material)
        fields = ['num_pixel_shader_instructions', 'num_vertex_shader_instructions', 'num_samplers',
                  'num_pixel_texture_samples', 'num_vertex_texture_samples', 'num_uv_scalars']
        textures = []
        for name in ['T_IndustrialDetail', 'T_IndustrialPlacement']:
            texture = unreal.load_asset('/CkFoundation/CkUsf/Textures/Industrial/' + name)
            textures.append({'name': name, 'width': texture.blueprint_get_size_x(),
                             'height': texture.blueprint_get_size_y(),
                             'srgb': texture.get_editor_property('srgb'),
                             'compression': str(texture.get_editor_property('compression_settings')),
                             'mips': str(texture.get_editor_property('mip_gen_settings'))})
        unreal.SystemLibrary.execute_console_command(_editor().get_editor_world(), 'ListTextures')
        return {'statistics': {key: getattr(stats, key) for key in fields}, 'textures': textures, 'state': _state()}
    if action == 'batch6_texture_state':
        result = {}
        for channel in ['BaseColor', 'Normal', 'Roughness']:
            texture = unreal.load_asset('/CkFoundation/CkUsf/Textures/Library/T_LibraryLinen_' + channel)
            if texture:
                fields = ['srgb', 'compression_settings', 'address_x', 'address_y', 'mip_gen_settings',
                          'flip_green_channel', 'power_of_two_mode', 'resize_during_build_x', 'resize_during_build_y', 'lod_group']
                result[channel] = {key: str(texture.get_editor_property(key)) for key in fields}
                result[channel]['runtime_size'] = [texture.blueprint_get_size_x(), texture.blueprint_get_size_y()]
        result['enum_names'] = [key for key in dir(unreal.TextureGroup) if key.upper() == key and not key.startswith('_')]
        return result
    if action == 'library_cost':
        result = {}
        fields = ['num_pixel_shader_instructions', 'num_vertex_shader_instructions', 'num_samplers', 'num_uv_scalars']
        for name in LIBRARY:
            material = unreal.load_asset('/CkFoundation/CkUsf/GeneratedLooks/M_CkUsf_Look_' + name)
            stats = unreal.MaterialEditingLibrary.get_statistics(material)
            result[name] = {key: getattr(stats, key) for key in fields}
        unreal.SystemLibrary.execute_console_command(_editor().get_editor_world(), 'ListTextures')
        return result
    if action == 'gc':
        unreal.log('USF_SESSION_GC_BEFORE')
        collected = gc.collect()
        unreal.SystemLibrary.collect_garbage()
        unreal.log('USF_SESSION_GC_AFTER')
        return {'collected': collected}
    if action in ['prepare', 'library_prepare', 'aluminum_prepare', 'batch2_prepare', 'batch3_prepare', 'batch4_prepare', 'batch5_prepare', 'batch6_prepare', 'batch7_prepare', 'environment1_prepare', 'environment2_prepare', 'woodland_prepare', 'river_pebbles_prepare', 'diorama_prepare']:
        filename = {'prepare': 'prepare_industrial.py', 'library_prepare': 'prepare_batch1.py',
                    'aluminum_prepare': 'prepare_linear_aluminum.py', 'batch2_prepare': 'prepare_batch2.py', 'batch3_prepare': 'prepare_batch3.py', 'batch4_prepare': 'prepare_batch4.py', 'batch5_prepare': 'prepare_batch5.py', 'batch6_prepare': 'prepare_batch6.py', 'batch7_prepare': 'prepare_batch7.py', 'environment1_prepare': 'prepare_environment1.py', 'environment2_prepare': 'prepare_environment2.py', 'woodland_prepare': 'prepare_woodland.py', 'river_pebbles_prepare': 'prepare_river_pebbles.py', 'diorama_prepare': 'prepare_diorama_patches.py'}[action]
        spec = importlib.util.spec_from_file_location('ck_material_preparation', ROOT / 'Tools/UsfMaterials' / filename)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        module.prepare()
        return {'prepared': True}
    if action == 'open':
        if _editor().get_game_world():
            raise RuntimeError('PIE is already running')
        if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('Save the open map before gym travel')
        level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if not level.load_level('/CkTests/TestGyms/TestGyms_CkTests_Level'):
            raise RuntimeError('Gym map failed to load')
        settings = unreal.get_default_object(unreal.load_class(None, '/Script/CkTests.CkGym_StartupSettings'))
        _startup = (settings.get_editor_property('StartupMode'), settings.get_editor_property('DefaultGymName'))
        settings.set_editor_property('StartupMode', type(_startup[0]).DEFAULT)
        settings.set_editor_property('DefaultGymName', 'USF Materials')
        unreal.SystemLibrary.execute_console_command(_editor().get_editor_world(), 'Ck.Usf.AutoReload 1')
        _pending = {'phase': 'open', 'request': request}
        _deadline = time.monotonic() + 180
        level.editor_request_begin_play()
        return None
    if action == 'capture':
        name = request.get('name', 'Industrial')
        if Path(name).name != name or not name.endswith('.png'):
            raise RuntimeError('Capture name must be a PNG filename')
        _frame(request)
        _pending = {'phase': 'frame', 'request': request, 'frame_at': time.monotonic() + (3.0 if request.get('shot') else 0.5)}
        _deadline = time.monotonic() + 120
        return None
    if action == 'end':
        _restore_environment_dither()
        _restore_diagnostic_light()
        for key, value in _preview_cvars.items():
            unreal.SystemLibrary.execute_console_command(_editor().get_game_world(), key + ' ' + str(value))
        _preview_cvars = {}
        _proof_objects = []
        _library_proof = {}
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        _environment_proof = {}
        _pending = {'phase': 'end', 'request': request}
        _deadline = time.monotonic() + 60
        return None
    if action == 'quit':
        if _editor().get_game_world() or unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('End PIE and preserve dirty maps before quitting')
        unreal.SystemLibrary.quit_editor()
        return {'quit': True}
    raise RuntimeError('Unknown studio action: ' + action)


def _poll():
    global _pending, _task
    if time.monotonic() > _deadline:
        raise RuntimeError('Studio operation timed out: ' + str(_pending))
    phase = _pending['phase']
    if phase == 'open':
        world = _editor().get_game_world()
        if world and len(_industrial(world)) == 4:
            _restore_startup()
            _frame(_pending['request'])
            return _state()
    elif phase == 'end':
        if not _editor().get_game_world():
            return {'ended': True}
    elif phase == 'frame':
        if time.monotonic() >= _pending['frame_at']:
            path = DIRECTORY / _pending['request']['name']
            _pending['previous_stamp'] = path.stat().st_mtime_ns if path.exists() else 0
            world = _editor().get_game_world()
            pc = unreal.GameplayStatics.get_player_controller(world, 0)
            route = 'Shot -nosuffix' if _pending['request'].get('shot') else 'HighResShot 1280x720'
            unreal.SystemLibrary.execute_console_command(world, route + ' filename="' + str(path) + '"', pc)
            _pending['phase'] = 'screenshot'
    elif phase == 'screenshot':
        path = DIRECTORY / _pending['request']['name']
        if path.exists() and path.stat().st_mtime_ns != _pending['previous_stamp'] and path.stat().st_size > 1000:
            route = 'Shot' if _pending['request'].get('shot') else 'HighResShot'
            return {'capture': str(path), 'capture_route': 'PIE player console -> GameViewportClient ' + route, 'state': _state()}
    return None


def _tick(delta):
    global _busy, _pending, _task, _current_id
    if _busy:
        return
    _busy = True
    try:
        if _diagnostic_quantization is not None and not _editor().get_game_world():
            _restore_environment_dither()
        if _pending is not None:
            result = _poll()
            if result is not None:
                _write({'ok': True, 'result': result})
                _pending = None
        elif REQUEST.exists():
            request = json.loads(REQUEST.read_text())
            REQUEST.unlink()
            _current_id = request.get('id')
            result = _dispatch(request)
            if result is not None:
                _write({'ok': True, 'result': result})
    except Exception:
        error = traceback.format_exc()
        unreal.log_error(error)
        _restore_startup()
        _pending = None
        _write({'ok': False, 'error': error})
    finally:
        _busy = False


def start():
    global _handle
    if _handle is None:
        _handle = unreal.register_slate_post_tick_callback(_tick)
        _write({'ok': True, 'ready': True, 'pid': os.getpid()})
        unreal.log('USF_SESSION_READY')
