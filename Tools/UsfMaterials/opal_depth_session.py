"""Owned offscreen opal-depth studio; commands execute serially on editor ticks."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import json
import hashlib
import math
import os
import time
import traceback
import uuid
import unreal
from canonical_capture_png import canonical_png_bytes
from opal_depth_settings import ASSET, LOOKS, TEXTURE_PREFIX, FIRE_LOOK

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
REQUEST, RESULT = OUTPUT/'OpalDepthRequest.json', OUTPUT/'OpalDepthResult.json'
SESSION = os.environ.get('CK_OPAL_DEPTH_SESSION_ID', '')
if str(uuid.UUID(SESSION)) != SESSION:
    raise RuntimeError('Launch with the owned OpalDepth launcher')
_scene, _busy = {}, False
_preparing = None
_primary = None
ROLES = {'Core','Shell','FireLayer'}
DEFAULT_CORE_INSET_CM = .1
BODY_CENTER = (0.0,0.0,4.06)
BODY_HALF_EXTENTS = (2.1,5.5,3.94)
if set(LOOKS) != {'Core','Shell'}:
    raise RuntimeError('Unexpected opal-depth material roster')


def role_recipe(role):
    return FIRE_LOOK if role=='FireLayer' else LOOKS[role]


def validate_core_inset(value):
    if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or not .03<=value<=.3:
        raise RuntimeError('Finite core_inset_cm from .03 to .3 required')
    return float(value)


def inset_geometry(role,core_inset_cm=DEFAULT_CORE_INSET_CM):
    core_inset_cm=validate_core_inset(core_inset_cm)
    if role not in ROLES:
        raise RuntimeError('Known inset role required')
    inset=core_inset_cm if role=='Core' else core_inset_cm*.5 if role=='FireLayer' else 0.0
    scale=tuple(1-inset/half for half in BODY_HALF_EXTENTS)
    position=tuple(center*(1-component) for center,component in zip(BODY_CENTER,scale))
    return dict(inset_cm=inset,scale=scale,position=position)


def apply_insets(core_inset_cm=DEFAULT_CORE_INSET_CM):
    # Derive and validate every role before the first actor mutation.
    geometry={role:inset_geometry(role,core_inset_cm) for role in ROLES}
    for role,values in geometry.items():
        actor=_scene['meshes'][role]
        actor.set_actor_location(unreal.Vector(*values['position']),False,False)
        actor.set_actor_scale3d(unreal.Vector(*values['scale']))
    _scene['insets_cm']={role:values['inset_cm'] for role,values in geometry.items()}


def write(data):
    data.update(session_id=SESSION, pid=os.getpid())
    temporary = RESULT.with_suffix('.pending')
    temporary.write_text(json.dumps(data, indent=2))
    temporary.replace(RESULT)


def xyz(value):
    return [value.x, value.y, value.z]


def rotation(actor):
    value = actor.get_actor_rotation()
    return dict(pitch=value.pitch,yaw=value.yaw,roll=value.roll)


def finite_vector(value, count=3):
    return isinstance(value, list) and len(value) == count and all(isinstance(x, (int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in value)


def primary_camera_state():
    camera=_scene.get('primary_camera')
    if camera is None:
        return None
    component=camera.get_component_by_class(unreal.CameraComponent)
    settings=component.get_editor_property('post_process_settings')
    fields=['override_auto_exposure_min_brightness','override_auto_exposure_max_brightness',
        'auto_exposure_min_brightness','auto_exposure_max_brightness','override_bloom_intensity','bloom_intensity',
        'override_lumen_front_layer_translucency_reflections','lumen_front_layer_translucency_reflections',
        'override_dynamic_global_illumination_method','dynamic_global_illumination_method',
        'override_reflection_method','reflection_method']
    values={field:settings.get_editor_property(field) for field in fields}
    for field in ['dynamic_global_illumination_method','reflection_method']:
        values[field]=str(values[field])
    return dict(path=camera.get_path_name(),position=xyz(camera.get_actor_location()),rotation=rotation(camera),
        fov=component.get_editor_property('field_of_view'),aspect_ratio=component.get_editor_property('aspect_ratio'),
        constrain_aspect_ratio=component.get_editor_property('constrain_aspect_ratio'),
        post_process_blend_weight=component.get_editor_property('post_process_blend_weight'),postprocess=values)


def state():
    result = dict(scene_created=bool(_scene), adaptive=unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat'), native_glints=unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.Glints'), looks={})
    if not _scene:
        return result
    generator = unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem)
    for role, (master, mid) in _scene['materials'].items():
        recipe = role_recipe(role)
        unreal.MaterialEditingLibrary.get_statistics(master)
        stats = generator.get_compiled_substrate_stats(master)
        front = unreal.MaterialEditingLibrary.get_material_property_input_node(master, unreal.MaterialProperty.MP_FRONT_MATERIAL)
        source_role=role
        result['looks'][role] = dict(master=master.get_path_name(), mid=mid.get_path_name(),
            source_recipe_role=source_role,source_recipe_pin=hashlib.sha256(json.dumps(role_recipe(source_role),sort_keys=True).encode()).hexdigest(),
            runtime_recipe_pin=hashlib.sha256(json.dumps(recipe,sort_keys=True).encode()).hexdigest(),
            runtime_default_scalar_overrides={},
            scalars={key:mid.get_scalar_parameter_value(key) for key,_ in recipe['scalars']},
            vectors={key:[getattr(mid.get_vector_parameter_value(key),c) for c in 'rgba'] for key,_ in recipe['vectors']},
            textures={key:(mid.get_texture_parameter_value(key).get_path_name() if mid.get_texture_parameter_value(key) else None) for key,_ in recipe['textures']},
            front=front.get_path_name() if front else None,
            compiled={key:list(getattr(stats,key)) if key=='compile_errors' else getattr(stats,key) for key in ['valid','closure_count','uint_per_pixel','has_glint','complex_special','material_type','bsdf_features','compile_errors']})
    settings = _scene['component'].get_editor_property('post_process_settings')
    result.update(primary_camera_state=primary_camera_state(),subject=_scene['subject'], visible=dict(_scene['visible']), geometry=_scene['geometry'],fire_layer_preparation=_scene['fire_layer_preparation'],
        actors={role:dict(inset_cm=_scene['insets_cm'][role],
                         actual_axis_insets_cm=[half*(1-value) for half,value in zip(BODY_HALF_EXTENTS,xyz(actor.get_actor_scale3d()))],
                         mesh=actor.static_mesh_component.get_editor_property('static_mesh').get_path_name(),
                         sort_triangles=actor.static_mesh_component.get_editor_property('sort_triangles'),
                         translucency_sort_priority=actor.static_mesh_component.get_editor_property('translucency_sort_priority'),
                         position=xyz(actor.get_actor_location()),rotation=rotation(actor),scale=xyz(actor.get_actor_scale3d()))
                for role,actor in _scene['meshes'].items()},
        rig=dict(camera=xyz(_scene['capture'].get_actor_location()), target=_scene['aim'],
            sorted_triangles_supported=unreal.SystemLibrary.get_console_variable_int_value('r.OIT.SortedTriangles'),
            exposure=settings.get_editor_property('auto_exposure_min_brightness'),
            front_layer_reflections=settings.get_editor_property('lumen_front_layer_translucency_reflections'),
            sky=_scene['sky'].light_component.get_editor_property('intensity'),
            fov=_scene['component'].get_editor_property('fov_angle'),
            environment=dict(intensity=_scene['environment_mid'].get_scalar_parameter_value('Intensity'),rotation=_scene['environment_mid'].get_scalar_parameter_value('CubemapRotation'),reflection_brightness=_scene['reflection'].get_editor_property('brightness')),
            floor=xyz(_scene['floor'].get_actor_location()), stand_visible=False,
            lights=[dict(position=xyz(a.get_actor_location()),intensity=a.point_light_component.get_editor_property('intensity'),
                         rotation=rotation(a),radius=a.point_light_component.get_editor_property('source_radius'),length=a.point_light_component.get_editor_property('source_length')) for a in _scene['lights']]))
    return result


def visibility(values):
    for role, visible in values.items():
        actor = _scene['meshes'][role]
        actor.set_actor_hidden_in_game(not visible)
        actor.static_mesh_component.set_editor_property('cast_shadow', visible and role == 'Core')
        _scene['visible'][role] = visible


def subject_defaults(subject):
    if subject != 'opal':
        raise RuntimeError('Subject must be opal')
    visibility({'Core':True,'Shell':True,'FireLayer':True})
    apply_insets(DEFAULT_CORE_INSET_CM)
    _scene['subject']='opal'
    _scene['stand'].set_actor_hidden_in_game(True)
    _scene['stand'].static_mesh_component.set_editor_property('cast_shadow',False)
    _scene['floor'].set_actor_location(unreal.Vector(0,0,.11),False,False)
    _scene['capture'].set_actor_location(unreal.Vector(24,-11,14),False,False)
    _scene['aim']=[0,0,4.1]
    for actor,(position,intensity,radius,length) in zip(_scene['lights'],[
            ((16,-12,20),5,.6,9),((12,15,12),2.5,.12,0),((-4,5,14),7,1,5)]):
        actor.set_actor_location(unreal.Vector(*position),False,False)
        actor.set_actor_rotation(unreal.Rotator(pitch=90,yaw=0,roll=0),False)
        for field,value in [('intensity',intensity),('source_radius',radius),('source_length',length)]:
            actor.point_light_component.set_editor_property(field,value)
    settings=_scene['component'].get_editor_property('post_process_settings')
    for field in ['auto_exposure_min_brightness','auto_exposure_max_brightness']:
        settings.set_editor_property(field,4.4)
    _scene['component'].set_editor_property('post_process_settings',settings)
    _scene['component'].set_editor_property('fov_angle',32)
    _scene['sky'].light_component.set_intensity(.35)
    _scene['environment_mid'].set_scalar_parameter_value('Intensity',10)
    _scene['environment_mid'].set_scalar_parameter_value('CubemapRotation',0)
    _scene['reflection'].set_editor_property('brightness',1)
    _scene['capture'].set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(_scene['capture'].get_actor_location(),unreal.Vector(*_scene['aim'])),False)


def scene():
    if _scene or unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Preserve existing scene/dirty maps')
    geometry_path=ROOT/'Plugins/CkTests/Resources/CkUsf/AmberHeroV1/Manifest.json'
    geometry_data=geometry_path.read_bytes()
    geometry_record=dict(path=str(geometry_path.relative_to(ROOT)),sha256=hashlib.sha256(geometry_data).hexdigest(),
        reused_mesh='/CkTests/CkUsf/Showcase/AmberHero/SM_AmberHero_Body')
    # Resolve all persistent assets before replacing the owned map. Never prepare here.
    sources = {}
    for role, recipe in LOOKS.items():
        if (recipe['name'],recipe['source'],recipe['graph']) != ('OpticalOpal'+role,'OpticalOpal'+role,4 if role=='Core' else 6):
            raise RuntimeError('Exact owned Core/Shell native recipe required: '+role)
        master = unreal.load_asset(ASSET+'/GeneratedLooks/M_CkUsf_Look_'+recipe['name'])
        meshpath = '/CkTests/CkUsf/Showcase/AmberHero/SM_AmberHero_Body'
        mesh = unreal.load_asset(meshpath)
        if not isinstance(master,unreal.Material) or not isinstance(mesh,unreal.StaticMesh):
            raise RuntimeError('Prepare persistent opal-depth master/body first: '+role)
        from prepare_optical_seated import _verify_definition
        from prepare_opal_depth import OWNER
        pin = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()
        definition_path = ASSET+'/Looks/Optical/DA_'+recipe['name']
        definition = unreal.load_asset(definition_path)
        if not isinstance(definition, unreal.CkUsf_LookDefinition) or definition.get_editor_property('_AdaptiveBaseGlints') != (role=='Core'):
            raise RuntimeError('Prepared role-specific native Core/Shell definition required before scene creation')
        if any(unreal.EditorAssetLibrary.get_metadata_tag(asset, OWNER) != pin for asset in [definition, master]):
            raise RuntimeError('Prepared depth recipe ownership/pin differs: '+json.dumps(dict(expected_pin=pin,metadata={asset.get_path_name():unreal.EditorAssetLibrary.get_metadata_tag(asset,OWNER) for asset in [definition,master]})))
        if unreal.EditorAssetLibrary.get_metadata_tag(master, 'CkUsf.SourceDefinition.v1') != definition.get_path_name():
            raise RuntimeError('Prepared depth source definition differs')
        _verify_definition(definition, definition_path, role, recipe, {key: unreal.load_asset(TEXTURE_PREFIX+key) for _, key in recipe['textures']})
        unreal.MaterialEditingLibrary.get_statistics(master)
        compiled = unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem).get_compiled_substrate_stats(master)
        if not compiled.valid or compiled.compile_errors or compiled.closure_count != (2 if role=='Core' else 1) or compiled.has_glint != (role=='Core') or (role=='Core' and not compiled.complex_special):
            raise RuntimeError('Prepare valid native Core glints and Shell translucency before scene creation: '+role)
        for kind,parameters in [('scalar',recipe['scalars']),('vector',recipe['vectors']),('texture',recipe['textures'])]:
            if {str(value) for value in getattr(unreal.MaterialEditingLibrary,'get_'+kind+'_parameter_names')(master)} != {key for key,_ in parameters}:
                raise RuntimeError('Prepared master parameter roster differs: '+role+'/'+kind)
            for parameter,value in parameters:
                actual=getattr(unreal.MaterialEditingLibrary,'get_material_default_'+kind+'_parameter_value')(master,parameter)
                valid=(actual==unreal.load_asset(TEXTURE_PREFIX+value)) if kind=='texture' else (all(abs(getattr(actual,c)-v)<1e-5 for c,v in zip('rgba',value)) if kind=='vector' else abs(actual-value)<1e-5)
                if not valid:
                    raise RuntimeError('Prepared master default differs: '+role+'/'+parameter)
        sources[role] = master,mesh
    from prepare_opal_depth_fire import verify_existing
    fire_master,fire_report = verify_existing()
    if (FIRE_LOOK['name'],FIRE_LOOK['source'],FIRE_LOOK['graph']) != ('OpticalOpalFireLayer','OpticalOpalFireLayer',6):
        raise RuntimeError('Exact new native transmitting FireLayer recipe required')
    if not isinstance(fire_master,unreal.Material) or fire_master.get_path_name() != ASSET+'/GeneratedLooks/M_CkUsf_Look_OpticalOpalFireLayer.M_CkUsf_Look_OpticalOpalFireLayer':
        raise RuntimeError('Exact verified FireLayer master required')
    if fire_report.get('preparation_pending') or fire_report['recipe_pin'] != hashlib.sha256(json.dumps(FIRE_LOOK,sort_keys=True).encode()).hexdigest():
        raise RuntimeError('FireLayer preparation is incomplete or differs from current settings')
    sources['FireLayer'] = fire_master,sources['Core'][1]
    neutral = unreal.load_asset(ASSET+'/GeneratedLooks/M_CkUsf_Look_OpticalTailLampHousing')
    environment = unreal.load_asset('/Engine/EditorMaterials/AssetViewer/EpicQuadPanorama_CC+EV1')
    if not isinstance(neutral,unreal.Material) or not isinstance(environment,unreal.TextureCube):
        raise RuntimeError('Verified charcoal master/studio cubemap missing')
    sky_mesh = unreal.load_asset('/Engine/EditorMeshes/AssetViewer/Sphere_inversenormals')
    sky_material = unreal.load_asset('/Engine/EditorMaterials/AssetViewer/M_SkyBox')
    if not isinstance(sky_mesh,unreal.StaticMesh) or not isinstance(sky_material,unreal.Material):
        raise RuntimeError('Standard Unreal preview environment assets missing')
    world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    # Mark ownership immediately, so a failure cannot cause a second blank-map replacement.
    _scene.update(world=world, materials={}, meshes={}, textures={}, visible={}, subject=None,geometry=geometry_record,fire_layer_preparation=fire_report)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    def spawn(kind, location):
        return actors.spawn_actor_from_class(kind,unreal.Vector(*location))
    for role,(master,mesh) in sources.items():
        unreal.MaterialEditingLibrary.get_statistics(master)
        mid = unreal.MaterialLibrary.create_dynamic_material_instance(world,master)
        _scene['materials'][role] = master,mid
        for parameter,key in role_recipe(role)['textures']:
            texture = mid.get_texture_parameter_value(parameter)
            expected = TEXTURE_PREFIX+key
            if not isinstance(texture,unreal.Texture2D) or texture.get_path_name().split('.')[0] != expected:
                raise RuntimeError('Missing opal-depth texture backing: '+role+'/'+parameter)
            _scene['textures'][texture.get_path_name()] = texture
        actor = spawn(unreal.StaticMeshActor,(0,0,0))
        actor.set_actor_label('OpalDepth_'+role)
        component = actor.static_mesh_component
        component.set_static_mesh(mesh)
        slot = component.get_material_index('Body')
        if slot < 0:
            raise RuntimeError('Missing named material slot: '+role)
        component.set_material(slot,mid)
        component.set_editor_property('disallow_nanite',True)
        component.set_editor_property('cast_shadow',role=='Core')
        if role in ['FireLayer','Shell']:
            component.set_editor_property('translucency_sort_priority',1 if role=='FireLayer' else 2)
        if role in ['FireLayer','Shell'] and unreal.SystemLibrary.get_console_variable_int_value('r.OIT.SortedTriangles')==1:
            component.set_editor_property('sort_triangles',True)
        _scene['meshes'][role] = actor
    stand = spawn(unreal.StaticMeshActor,(-.45,0,-.35))
    stand.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cylinder'))
    stand.set_actor_scale3d(unreal.Vector(.048,.075,.007))
    stand.static_mesh_component.set_material(0,neutral)
    floor = spawn(unreal.StaticMeshActor,(0,0,-.72))
    floor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
    floor.set_actor_scale3d(unreal.Vector(2,2,2))
    floor.static_mesh_component.set_material(0,neutral)
    sky = spawn(unreal.SkyLight,(0,0,0))
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property('source_type',unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sky.light_component.set_cubemap(environment)
    sky.light_component.set_intensity(.8)
    sky.light_component.recapture_sky()
    environment_mid = unreal.MaterialLibrary.create_dynamic_material_instance(world,sky_material)
    environment_mid.set_texture_parameter_value('SkyBox',environment)
    environment_mid.set_scalar_parameter_value('Intensity',20)
    environment_mid.set_scalar_parameter_value('CubemapRotation',0)
    backdrop = spawn(unreal.StaticMeshActor,(0,0,0))
    backdrop.set_actor_label('OpalDepth_PreviewEnvironment')
    backdrop.set_actor_scale3d(unreal.Vector(2000,2000,2000))
    backdrop.static_mesh_component.set_static_mesh(sky_mesh)
    backdrop.static_mesh_component.set_material(0,environment_mid)
    backdrop.static_mesh_component.set_editor_property('cast_shadow',False)
    reflection_actor = spawn(unreal.SphereReflectionCapture,(0,0,3))
    reflection = reflection_actor.get_component_by_class(unreal.SphereReflectionCaptureComponent)
    reflection.set_editor_property('reflection_source_type',type(reflection.get_editor_property('reflection_source_type')).cast(1))
    reflection.set_editor_property('cubemap',environment)
    reflection.set_editor_property('brightness',3)
    reflection.set_editor_property('influence_radius',300)
    lights = []
    for position,intensity,radius,length in [((16,-14,19),7,.7,10),((12,16,10),3,.45,7),((-4,5,14),10,1.2,4)]:
        actor = spawn(unreal.PointLight,position)
        light = actor.point_light_component
        light.set_mobility(unreal.ComponentMobility.MOVABLE)
        light.set_intensity_units(unreal.LightUnits.CANDELAS)
        light.set_intensity(intensity)
        light.set_attenuation_radius(180)
        light.set_source_radius(radius)
        light.set_source_length(length)
        lights.append(actor)
    capture = spawn(unreal.SceneCapture2D,(24,-11,17))
    component = capture.capture_component2d
    for key,value in [('capture_source',unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR),('capture_every_frame',False),('capture_on_movement',False),('always_persist_rendering_state',True),('fov_angle',32)]:
        component.set_editor_property(key,value)
    component.set_editor_property('show_flag_settings',[unreal.EngineShowFlagsSetting(show_flag_name=name,enabled=True) for name in ['AntiAliasing','PostProcessing','TemporalAA','SkyLighting','ReflectionEnvironment','Refraction']])
    settings = component.get_editor_property('post_process_settings')
    for key,value in [('override_auto_exposure_min_brightness',True),('override_auto_exposure_max_brightness',True),('auto_exposure_min_brightness',4.8),('auto_exposure_max_brightness',4.8),('override_bloom_intensity',True),('bloom_intensity',.05),('override_lumen_front_layer_translucency_reflections',True),('lumen_front_layer_translucency_reflections',True),('override_dynamic_global_illumination_method',True),('dynamic_global_illumination_method',unreal.DynamicGlobalIlluminationMethod.LUMEN),('override_reflection_method',True),('reflection_method',unreal.ReflectionMethod.LUMEN)]:
        settings.set_editor_property(key,value)
    component.set_editor_property('post_process_settings',settings)
    component.set_editor_property('post_process_blend_weight',1)
    _scene.update(environment_mid=environment_mid,environment_actor=backdrop,reflection=reflection,stand=stand,floor=floor,sky=sky,lights=lights,capture=capture,component=component)
    subject_defaults('opal')
    # UE 5.8 gathers persistent special-tile allocation from primary views only.
    # Keep an owned offscreen primary view on the same material before captures.
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
        capture.get_actor_location(),capture.get_actor_rotation())
    level_editor=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    level_editor.editor_invalidate_viewports()
    primary_camera()
    return state()


def validate_capture(request):
    if not _scene or 'component' not in _scene:
        raise RuntimeError('Create the owned scene first')
    name = request.get('name','')
    if not isinstance(name,str) or Path(name).name!=name or not name.startswith('OpalDepth-') or not name.endswith('.png'):
        raise RuntimeError('Plain OpalDepth- prefixed PNG filename required')
    if (OUTPUT/name).exists():
        raise RuntimeError('Preserve existing OpalDepth capture; select a fresh owned filename')
    if request.get('subject',_scene['subject']) != 'opal':
        raise RuntimeError('Unknown subject')
    for field,roster,count in [('scalars','scalars',None),('vectors','vectors',4)]:
        for role,values in request.get(field,{}).items():
            if role not in ROLES or not isinstance(values,dict) or set(values)-set(dict(role_recipe(role)[roster])):
                raise RuntimeError('Unknown material control')
            for value in values.values():
                if not (finite_vector(value,count) if count else isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)):
                    raise RuntimeError('Nonfinite material control')
    if 'core_inset_cm' in request:
        validate_core_inset(request['core_inset_cm'])
    visible=request.get('visible',{})
    if not isinstance(visible,dict) or set(visible)-ROLES or any(not isinstance(v,bool) for v in visible.values()):
        raise RuntimeError('Known boolean visibility controls required')
    for field in ['camera','target']:
        if field in request and not finite_vector(request[field]):
            raise RuntimeError('Three finite camera/target coordinates required')
    for field,maximum in [('intensities',1000),('source_radii',100),('source_lengths',100)]:
        if field in request and (not finite_vector(request[field]) or any(not 0<=v<=maximum for v in request[field])):
            raise RuntimeError('Three bounded light controls required')
    if 'light_positions' in request and (not isinstance(request['light_positions'],list) or len(request['light_positions'])!=3 or any(not finite_vector(v) for v in request['light_positions'])):
        raise RuntimeError('Three light positions required')
    if 'light_rotations' in request and (not isinstance(request['light_rotations'],list) or len(request['light_rotations'])!=3 or any(not finite_vector(v) for v in request['light_rotations'])):
        raise RuntimeError('Three finite pitch/yaw/roll light rotations required')
    if not isinstance(request.get('settle_frames',24),int) or not 2 <= request.get('settle_frames',24) <= 120:
        raise RuntimeError('Integer settle_frames from 2 to 120 required')
    if 'front_reflections' in request and not isinstance(request['front_reflections'],bool):
        raise RuntimeError('Reflection control must be boolean')
    for field,low,high in [('environment_intensity',0,1000),('environment_rotation',0,1),('reflection_brightness',0,100),('sky',0,10),('exposure',-10,24),('fov',5,100)]:
        value=request.get(field,low)
        if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or not low<=value<=high:
            raise RuntimeError('Bounded '+field+' required')
    camera=request.get('camera', [24,-11,14] if request.get('subject')=='opal' else xyz(_scene['capture'].get_actor_location()))
    target=request.get('target', [0,0,4.1] if request.get('subject')=='opal' else _scene['aim'])
    if sum((a-b)**2 for a,b in zip(camera,target)) < .0001:
        raise RuntimeError('Camera and target must differ')


def capture_controls(request):
    validate_capture(request)  # Complete validation before the first mutation.
    if 'subject' in request:
        subject_defaults(request['subject'])
    if 'core_inset_cm' in request:
        apply_insets(request['core_inset_cm'])
    for role,values in request.get('scalars',{}).items():
        for key,value in values.items():
            _scene['materials'][role][1].set_scalar_parameter_value(key,value)
    for role,values in request.get('vectors',{}).items():
        for key,value in values.items():
            _scene['materials'][role][1].set_vector_parameter_value(key,unreal.LinearColor(*value))
    visibility(request.get('visible',{}))
    if 'camera' in request:
        _scene['capture'].set_actor_location(unreal.Vector(*request['camera']),False,False)
    if 'target' in request:
        _scene['aim']=request['target']
    _scene['capture'].set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(_scene['capture'].get_actor_location(),unreal.Vector(*_scene['aim'])),False)
    if 'fov' in request:
        _scene['component'].set_editor_property('fov_angle',request['fov'])
    if 'exposure' in request:
        settings=_scene['component'].get_editor_property('post_process_settings')
        for field in ['auto_exposure_min_brightness','auto_exposure_max_brightness']:
            settings.set_editor_property(field,request['exposure'])
        _scene['component'].set_editor_property('post_process_settings',settings)
    for key,field in [('intensities','intensity'),('source_radii','source_radius'),('source_lengths','source_length')]:
        if key in request:
            for actor,value in zip(_scene['lights'],request[key]):
                actor.point_light_component.set_editor_property(field,value)
    if 'light_positions' in request:
        for actor,position in zip(_scene['lights'],request['light_positions']):
            actor.set_actor_location(unreal.Vector(*position),False,False)
    if 'light_rotations' in request:
        for actor,angles in zip(_scene['lights'],request['light_rotations']):
            actor.set_actor_rotation(unreal.Rotator(pitch=angles[0],yaw=angles[1],roll=angles[2]),False)
    for control,parameter in [('environment_intensity','Intensity'),('environment_rotation','CubemapRotation')]:
        if control in request:
            _scene['environment_mid'].set_scalar_parameter_value(parameter,request[control])
    if 'reflection_brightness' in request:
        _scene['reflection'].set_editor_property('brightness',request['reflection_brightness'])
    if 'front_reflections' in request:
        settings=_scene['component'].get_editor_property('post_process_settings')
        settings.set_editor_property('lumen_front_layer_translucency_reflections',request['front_reflections'])
        _scene['component'].set_editor_property('post_process_settings',settings)
    if 'sky' in request:
        _scene['sky'].light_component.set_intensity(request['sky'])
    for texture in _scene['textures'].values():
        texture.set_force_mip_levels_to_be_resident(120,0)


def primary_camera():
    """Mirror the owned capture rig into a real primary-viewport CameraActor."""
    camera = _scene.get('primary_camera')
    if camera is None:
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        camera = actors.spawn_actor_from_class(unreal.CameraActor,_scene['capture'].get_actor_location())
        if not isinstance(camera,unreal.CameraActor):
            raise RuntimeError('Could not create owned primary screenshot camera')
        camera.set_actor_label('OpalDepth_PrimaryCaptureCamera')
        _scene['primary_camera'] = camera
    camera.set_actor_location(_scene['capture'].get_actor_location(),False,False)
    camera.set_actor_rotation(_scene['capture'].get_actor_rotation(),False)
    component = camera.get_component_by_class(unreal.CameraComponent)
    if not isinstance(component,unreal.CameraComponent):
        raise RuntimeError('Owned primary CameraComponent missing')
    for field,value in [('field_of_view',_scene['component'].get_editor_property('fov_angle')),
                        ('aspect_ratio',1600/1200),('constrain_aspect_ratio',True),
                        ('post_process_settings',_scene['component'].get_editor_property('post_process_settings')),
                        ('post_process_blend_weight',1.0)]:
        component.set_editor_property(field,value)
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
        camera.get_actor_location(),camera.get_actor_rotation())
    level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    level_editor.editor_invalidate_viewports()
    return camera


def dispatch(request):
    global LOOKS,FIRE_LOOK
    action=request['action']
    if action=='state':
        return state()
    if action=='prepare':
        if _scene:
            raise RuntimeError('Prepare before scene creation')
        import importlib, prepare_opal_depth, opal_depth_settings
        importlib.reload(opal_depth_settings)
        importlib.reload(prepare_opal_depth)
        LOOKS=opal_depth_settings.LOOKS
        FIRE_LOOK=opal_depth_settings.FIRE_LOOK
        result=prepare_opal_depth.prepare()
        if result.get('preparation_pending'):
            return result
        import prepare_opal_depth_fire
        importlib.reload(prepare_opal_depth_fire)
        # FireLayer generation is confined to explicit preparation; scene only validates it.
        fire=prepare_opal_depth_fire.prepare()
        pending=bool(fire.get('preparation_pending'))
        return dict(result,fire_layer=fire,preparation_pending=pending,ready_for_separate_scene_action=not pending)
    if action=='scene':
        return scene()
    if action in ['capture','capture_primary']:
        capture_controls(request)
        return None
    if action=='quit':
        for texture in _scene.get('textures',{}).values():
            texture.set_force_mip_levels_to_be_resident(0,0)
        unreal.SystemLibrary.quit_editor()
        return dict(quit_requested=True)
    raise RuntimeError('Unknown opal-depth action')


def tick(delta):
    global _busy,_preparing,_primary
    if _busy:
        return
    _busy=True
    request=None
    try:
        if _primary:
            request = _primary['request']
            path = OUTPUT/request['name']
            if _primary.get('task') is None:
                if path.exists():
                    raise RuntimeError('Preserve existing primary screenshot destination')
                _primary['frames'] += 1
                if _primary['frames'] >= request.get('settle_frames',24):
                    # This native API locks/pilots the viewport CameraActor immediately,
                    # then its own core ticker requests a primary high-resolution screenshot.
                    # Retain the task strongly and let editor ticks perform all rendering/I/O.
                    task = unreal.AutomationLibrary.take_high_res_screenshot(1600,1200,str(path.resolve()),
                        camera=_scene['primary_camera'],mask_enabled=False,capture_hdr=False,
                        comparison_notes='Owned OpalDepth primary-view diagnostic',delay=.5,force_game_view=True)
                    _scene['primary_screenshot_task'] = task
                    if not task or not task.is_valid_task():
                        raise RuntimeError('Native primary screenshot task was not accepted')
                    _primary.update(task=task,started=time.monotonic())
            else:
                task = _primary['task']
                if time.monotonic()-_primary['started'] > 120:
                    raise RuntimeError('Native primary screenshot timed out; inspect existing editor/task, do not retry blindly')
                if task.is_task_done() and path.is_file():
                    data = path.read_bytes()
                    canonical_png_bytes(data)  # Validate native PNG container without altering pixels/bytes.
                    import struct
                    if len(data)<24 or struct.unpack('>II',data[16:24]) != (1600,1200):
                        raise RuntimeError('Native primary screenshot dimensions differ')
                    write(dict(id=request['id'],ok=True,capture=str(path),state=state(),
                        capture_backend='AutomationLibrary.take_high_res_screenshot primary editor viewport',
                        primary_camera=_scene['primary_camera'].get_path_name(),primary_camera_state=primary_camera_state(),native_task_done=True,
                        native_task_valid=task.is_valid_task(),primary_camera_delay_seconds=.5))
                    _primary = None
        elif _preparing:
            request = _preparing['request']
            if time.monotonic() >= _preparing['deadline']:
                raise RuntimeError('Deferred definition generation timed out; inspect the owned session and pending preparation claim')
            # A pending result means only that generation has not produced every master.
            # Return to the existing editor ticks; shader/ownership/validation exceptions
            # propagate immediately through the normal failure response, never retried.
            result = dispatch(request)
            if not result.get('preparation_pending'):
                _preparing = None
                write(dict(id=request['id'],ok=True,result=result))
        elif REQUEST.exists():
            request=json.loads(REQUEST.read_text())
            REQUEST.unlink()
            if request.get('session_id')!=SESSION or str(uuid.UUID(request['id']))!=request['id']:
                raise RuntimeError('Request ownership/UUID mismatch')
            result=dispatch(request)
            if request['action'] in ['capture','capture_primary']:
                primary_camera()
                _primary=dict(request=request,frames=0,task=None)
            elif request['action']=='prepare' and result.get('preparation_pending'):
                _preparing=dict(request=request,deadline=time.monotonic()+120)
            else:
                write(dict(id=request['id'],ok=True,result=result))
    except Exception:
        message=traceback.format_exc()
        unreal.log_error(message)
        write(dict(id=request.get('id') if isinstance(request,dict) else None,ok=False,error=message))
        _preparing=None
        _primary=None
    finally:
        _busy=False


if any(unreal.SystemLibrary.get_console_variable_int_value(key)!=1 for key in ['r.Substrate','r.Substrate.ProjectGBufferFormat','r.Substrate.Glints']):
    raise RuntimeError('OpalDepth requires its separate Adaptive profile')
OUTPUT.mkdir(parents=True,exist_ok=True)
_handle=unreal.register_slate_post_tick_callback(tick)
write(dict(ok=True,ready=True))
unreal.log('USF_OPAL_DEPTH_SESSION_READY')
