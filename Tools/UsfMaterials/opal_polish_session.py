"""Owned offscreen opal-polish studio; commands execute serially on editor ticks."""
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
from opal_polish_settings import ASSET, LOOKS, TEXTURE_PREFIX

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
OUTPUT = ROOT / 'Saved/UsfMaterialGallery'
REQUEST, RESULT = OUTPUT/'OpalPolishRequest.json', OUTPUT/'OpalPolishResult.json'
SESSION = os.environ.get('CK_OPAL_POLISH_SESSION_ID', '')
if str(uuid.UUID(SESSION)) != SESSION:
    raise RuntimeError('Launch with the owned OpalPolish launcher')
_scene, _pending, _busy = {}, None, False
ROLES = {'Opal'}
if set(LOOKS) != ROLES:
    raise RuntimeError('Unexpected opal-polish material roster')


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


def state():
    result = dict(scene_created=bool(_scene), adaptive=unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat'), looks={})
    if not _scene:
        return result
    generator = unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem)
    for role, (master, mid) in _scene['materials'].items():
        recipe = LOOKS[role]
        unreal.MaterialEditingLibrary.get_statistics(master)
        stats = generator.get_compiled_substrate_stats(master)
        front = unreal.MaterialEditingLibrary.get_material_property_input_node(master, unreal.MaterialProperty.MP_FRONT_MATERIAL)
        result['looks'][role] = dict(master=master.get_path_name(), mid=mid.get_path_name(),
            scalars={key:mid.get_scalar_parameter_value(key) for key,_ in recipe['scalars']},
            vectors={key:[getattr(mid.get_vector_parameter_value(key),c) for c in 'rgba'] for key,_ in recipe['vectors']},
            textures={key:(mid.get_texture_parameter_value(key).get_path_name() if mid.get_texture_parameter_value(key) else None) for key,_ in recipe['textures']},
            front=front.get_path_name() if front else None,
            compiled={key:list(getattr(stats,key)) if key=='compile_errors' else getattr(stats,key) for key in ['valid','closure_count','uint_per_pixel','compile_errors']})
    settings = _scene['component'].get_editor_property('post_process_settings')
    result.update(subject=_scene['subject'], visible=dict(_scene['visible']), geometry=_scene['geometry'],
        actors={role:dict(mesh=actor.static_mesh_component.get_editor_property('static_mesh').get_path_name(),
                         sort_triangles=actor.static_mesh_component.get_editor_property('sort_triangles'),
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
        actor.static_mesh_component.set_editor_property('cast_shadow', visible and role != 'GlassCover')
        _scene['visible'][role] = visible


def subject_defaults(subject):
    if subject != 'opal':
        raise RuntimeError('Subject must be opal')
    visibility({'Opal':True})
    _scene['subject']='opal'
    _scene['stand'].set_actor_hidden_in_game(True)
    _scene['stand'].static_mesh_component.set_editor_property('cast_shadow',False)
    _scene['floor'].set_actor_location(unreal.Vector(0,0,.11),False,False)
    _scene['capture'].set_actor_location(unreal.Vector(24,-11,14),False,False)
    _scene['aim']=[0,0,4.1]
    for actor,(position,intensity,radius,length) in zip(_scene['lights'],[
            ((16,-12,20),5,2.2,5),((12,15,12),2.5,1.8,4),((-4,5,14),7,2,3)]):
        actor.set_actor_location(unreal.Vector(*position),False,False)
        actor.set_actor_rotation(unreal.Rotator(pitch=90,yaw=0,roll=0),False)
        for field,value in [('intensity',intensity),('source_radius',radius),('source_length',length)]:
            actor.point_light_component.set_editor_property(field,value)
    settings=_scene['component'].get_editor_property('post_process_settings')
    for field in ['auto_exposure_min_brightness','auto_exposure_max_brightness']:
        settings.set_editor_property(field,4.4)
    _scene['component'].set_editor_property('post_process_settings',settings)
    _scene['component'].set_editor_property('fov_angle',32)
    _scene['sky'].light_component.set_intensity(1.0)
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
        master = unreal.load_asset(ASSET+'/GeneratedLooks/M_CkUsf_Look_'+recipe['name'])
        meshpath = '/CkTests/CkUsf/Showcase/AmberHero/SM_AmberHero_Body'
        mesh = unreal.load_asset(meshpath)
        if not isinstance(master,unreal.Material) or not isinstance(mesh,unreal.StaticMesh):
            raise RuntimeError('Prepare persistent depth masters/meshes first: '+role)
        sources[role] = master,mesh
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
    _scene.update(world=world, materials={}, meshes={}, textures={}, visible={}, subject=None,geometry=geometry_record)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    def spawn(kind, location):
        return actors.spawn_actor_from_class(kind,unreal.Vector(*location))
    for role,(master,mesh) in sources.items():
        unreal.MaterialEditingLibrary.get_statistics(master)
        mid = unreal.MaterialLibrary.create_dynamic_material_instance(world,master)
        _scene['materials'][role] = master,mid
        for parameter,key in LOOKS[role]['textures']:
            texture = mid.get_texture_parameter_value(parameter)
            expected = TEXTURE_PREFIX+key
            if not isinstance(texture,unreal.Texture2D) or texture.get_path_name().split('.')[0] != expected:
                raise RuntimeError('Missing depth texture backing: '+role+'/'+parameter)
            _scene['textures'][texture.get_path_name()] = texture
        actor = spawn(unreal.StaticMeshActor,(0,0,0))
        actor.set_actor_label('OpalPolish_'+role)
        if role!='Opal':
            actor.set_actor_location(unreal.Vector(5.5,0,0),False,False)
            actor.set_actor_rotation(unreal.Rotator(pitch=90,yaw=0,roll=0),False)
        component = actor.static_mesh_component
        component.set_static_mesh(mesh)
        slot = component.get_material_index('Body' if role=='Opal' else role)
        if slot < 0:
            raise RuntimeError('Missing named material slot: '+role)
        component.set_material(slot,mid)
        component.set_editor_property('disallow_nanite',True)
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
    backdrop.set_actor_label('OpalPolish_PreviewEnvironment')
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
    target = unreal.RenderingLibrary.create_render_target2d(world,1600,1200,unreal.TextureRenderTargetFormat.RTF_RGBA8)
    for key,value in [('texture_target',target),('capture_source',unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR),('capture_every_frame',False),('capture_on_movement',False),('always_persist_rendering_state',True),('fov_angle',32)]:
        component.set_editor_property(key,value)
    component.set_editor_property('show_flag_settings',[unreal.EngineShowFlagsSetting(show_flag_name=name,enabled=True) for name in ['AntiAliasing','PostProcessing','TemporalAA','SkyLighting','ReflectionEnvironment','Refraction']])
    settings = component.get_editor_property('post_process_settings')
    for key,value in [('override_auto_exposure_min_brightness',True),('override_auto_exposure_max_brightness',True),('auto_exposure_min_brightness',4.8),('auto_exposure_max_brightness',4.8),('override_bloom_intensity',True),('bloom_intensity',.05),('override_lumen_front_layer_translucency_reflections',True),('lumen_front_layer_translucency_reflections',True),('override_dynamic_global_illumination_method',True),('dynamic_global_illumination_method',unreal.DynamicGlobalIlluminationMethod.LUMEN),('override_reflection_method',True),('reflection_method',unreal.ReflectionMethod.LUMEN)]:
        settings.set_editor_property(key,value)
    component.set_editor_property('post_process_settings',settings)
    component.set_editor_property('post_process_blend_weight',1)
    _scene.update(environment_mid=environment_mid,environment_actor=backdrop,reflection=reflection,stand=stand,floor=floor,sky=sky,lights=lights,capture=capture,component=component,target=target)
    subject_defaults('opal')
    return state()


def validate_capture(request):
    if not _scene or 'component' not in _scene:
        raise RuntimeError('Create the owned scene first')
    name = request.get('name','')
    if not isinstance(name,str) or Path(name).name!=name or not name.startswith('OpalPolish-') or not name.endswith('.png'):
        raise RuntimeError('Plain OpalPolish- prefixed PNG filename required')
    if request.get('subject',_scene['subject']) != 'opal':
        raise RuntimeError('Unknown subject')
    for field,roster,count in [('scalars','scalars',None),('vectors','vectors',4)]:
        for role,values in request.get(field,{}).items():
            if role not in ROLES or not isinstance(values,dict) or set(values)-set(dict(LOOKS[role][roster])):
                raise RuntimeError('Unknown material control')
            for value in values.values():
                if not (finite_vector(value,count) if count else isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)):
                    raise RuntimeError('Nonfinite material control')
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


def dispatch(request):
    global LOOKS
    action=request['action']
    if action=='state':
        return state()
    if action=='prepare':
        if _scene:
            raise RuntimeError('Prepare before scene creation')
        import importlib, prepare_opal_polish, opal_polish_settings
        importlib.reload(opal_polish_settings)
        importlib.reload(prepare_opal_polish)
        LOOKS=opal_polish_settings.LOOKS
        return prepare_opal_polish.prepare()
    if action=='scene':
        return scene()
    if action=='capture':
        capture_controls(request)
        return None
    if action=='quit':
        for texture in _scene.get('textures',{}).values():
            texture.set_force_mip_levels_to_be_resident(0,0)
        unreal.SystemLibrary.quit_editor()
        return dict(quit_requested=True)
    raise RuntimeError('Unknown opal-polish action')


def tick(delta):
    global _busy,_pending
    if _busy:
        return
    _busy=True
    request=None
    try:
        if _pending:
            request,frame=_pending
            _scene['component'].capture_scene()
            _pending=request,frame+1
            if frame>=request.get('settle_frames',24):
                path=OUTPUT/request['name']
                stamp=path.stat().st_mtime_ns if path.exists() else None
                unreal.RenderingLibrary.export_render_target(_scene['world'],_scene['target'],str(OUTPUT),request['name'])
                if not path.is_file() or path.stat().st_mtime_ns==stamp or path.stat().st_size<1000:
                    raise RuntimeError('Optical-depth capture export failed')
                path.write_bytes(canonical_png_bytes(path.read_bytes()))
                write(dict(id=request['id'],ok=True,capture=str(path),state=state()))
                _pending=None
        elif REQUEST.exists():
            request=json.loads(REQUEST.read_text())
            REQUEST.unlink()
            if request.get('session_id')!=SESSION or str(uuid.UUID(request['id']))!=request['id']:
                raise RuntimeError('Request ownership/UUID mismatch')
            result=dispatch(request)
            if request['action']=='capture':
                _pending=request,0
            else:
                write(dict(id=request['id'],ok=True,result=result))
    except Exception:
        message=traceback.format_exc()
        unreal.log_error(message)
        write(dict(id=request.get('id') if isinstance(request,dict) else None,ok=False,error=message))
        _pending=None
    finally:
        _busy=False


if unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat')!=1:
    raise RuntimeError('OpalPolish requires its separate Adaptive profile')
OUTPUT.mkdir(parents=True,exist_ok=True)
_handle=unreal.register_slate_post_tick_callback(tick)
write(dict(ok=True,ready=True))
unreal.log('USF_OPAL_POLISH_SESSION_READY')
