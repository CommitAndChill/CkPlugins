"""Prepare only the new original-artwork native layered opal variant.

prepare() explicitly saves the new owned definition/master. verify_existing()
returns (master, report) without saving, compiling, or scene changes.
"""
from pathlib import Path
import hashlib
import json
import re
import unreal
from prepare_native_bsdf import _param
from prepare_optical_seated import _verify_definition

OWNER = 'CkUsf.OpalLayeredFirePreparation.v1'
TEXTURE_OWNER = OWNER
NAME = 'OpticalOpalLayeredFire'
SOURCE_NAME = 'OpticalOpalLayered'
RESOURCE = 'Plugins/CkTests/Resources/CkUsf/OpalLayeredFireV1'
TEXTURE_ROOT = '/CkFoundation/CkUsf/Textures/Optical/OpalLayeredFire/T_OpalLayeredFire_'
ROLE = 'Opal'
MAPS = {'OpalColor', 'OpalDomains', 'OpalDomainNormal', 'OpalPolishNormal', 'OpalRoughness'}


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finish_textures():
    unreal.SystemLibrary.execute_console_command(
        unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),
        'Editor.AsyncTextureCompilationFinishAll')


def _png_contract(path,info,key):
    import struct
    data=path.read_bytes();width,height=info['width'],info['height']
    if not isinstance(width,int) or not isinstance(height,int) or width!=height or not 0<width<=2048 or (1<<(width-1).bit_length())!=2048:
        raise RuntimeError('Aligned square source must stretch to the required 2048 runtime POT: '+key)
    if len(data)<25 or data[:8]!=b'\x89PNG\r\n\x1a\n' or struct.unpack('>II',data[16:24])!=(width,height) or data[24]!=info['bit_depth'] or info['bit_depth']!=8 or info['srgb']!=(key=='OpalColor'):
        raise RuntimeError('New source PNG dimensions/bit depth/color space differ: '+key)


def _settings_for(key,info):
    normal=key.endswith('Normal')
    return dict(compression_settings=(unreal.TextureCompressionSettings.TC_NORMALMAP if normal else unreal.TextureCompressionSettings.TC_DEFAULT if info['srgb'] else unreal.TextureCompressionSettings.TC_MASKS),
        lod_group=(unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP if normal else unreal.TextureGroup.TEXTUREGROUP_WORLD if info['srgb'] else unreal.TextureGroup.TEXTUREGROUP_WORLD_SPECULAR),
        srgb=info['srgb'],address_x=unreal.TextureAddress.TA_CLAMP,address_y=unreal.TextureAddress.TA_CLAMP,
        mip_gen_settings=unreal.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,flip_green_channel=False,
        power_of_two_mode=unreal.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO)


def _check_texture(texture,key,info,source):
    if not isinstance(texture,unreal.Texture2D) or texture.get_path_name()!=TEXTURE_ROOT+key+'.T_OpalLayeredFire_'+key:
        raise RuntimeError('Unexpected new owned texture class/path: '+key)
    for field,value in _settings_for(key,info).items():
        if texture.get_editor_property(field)!=value:
            raise RuntimeError('Preserve changed new texture setting: '+key+'/'+field)
    if (texture.blueprint_get_size_x(),texture.blueprint_get_size_y())!=(2048,2048):
        raise RuntimeError('New texture runtime platform dimensions must be complete 2048-square: '+key)
    imported=texture.get_editor_property('asset_import_data')
    if not imported or [str(Path(value).resolve()) for value in imported.extract_filenames()]!=[str(source)]:
        raise RuntimeError('Preserve changed new texture import provenance: '+key)


def _texture_report(texture,key,info,manifest_path,manifest_relative):
    return dict(asset=texture.get_path_name(),source_sha256=info['sha256'],source_size=[info['width'],info['height']],
        runtime_size=[texture.blueprint_get_size_x(),texture.blueprint_get_size_y()],runtime_expected_size=[2048,2048],
        runtime_expected_mip_count=12,actual_mip_count_verified=False,
        settings={field:str(value) for field,value in _settings_for(key,info).items()},manifest_sha256=_sha(manifest_path))


def _prepare_textures(context,save):
    tools=unreal.AssetToolsHelpers.get_asset_tools();created=[]
    manifest_path=context['root']/context['texture_manifest']
    for key,candidate in context['candidates'].items():
        if context['textures'][key] is not None:
            continue  # Existing exact-owned maps are validated, never reimported/resaved.
        if unreal.EditorAssetLibrary.does_asset_exist(candidate['path']):
            raise RuntimeError('Concurrent texture destination appeared; preserve it: '+key)
        task=unreal.AssetImportTask();task.filename=str(candidate['source'])
        task.destination_path=TEXTURE_ROOT.rsplit('/',1)[0];task.destination_name='T_OpalLayeredFire_'+key
        task.automated,task.replace_existing,task.save=True,False,False
        tools.import_asset_tasks([task]);objects=task.get_objects()
        if len(objects)!=1 or not isinstance(objects[0],unreal.Texture2D) or objects[0].get_path_name()!=candidate['path']+'.T_OpalLayeredFire_'+key:
            raise RuntimeError('Unexpected new texture import result: '+key)
        texture=objects[0]
        for field,value in _settings_for(key,candidate['info']).items():
            texture.set_editor_property(field,value)
        context['textures'][key]=texture;created.append(key)
    if created:
        _finish_textures()
    # Check every imported map before the first save; never publish a partial ready set.
    for key,candidate in context['candidates'].items():
        _check_texture(context['textures'][key],key,candidate['info'],candidate['source'])
    for key in created:
        texture=context['textures'][key];info=context['candidates'][key]['info']
        unreal.EditorAssetLibrary.set_metadata_tag(texture,TEXTURE_OWNER,info['sha256'])
        unreal.EditorAssetLibrary.set_metadata_tag(texture,OWNER+'.Manifest',context['texture_manifest']+':'+_sha(manifest_path))
        save(texture)
    context['texture_checks']={key:_texture_report(texture,key,context['candidates'][key]['info'],manifest_path,context['texture_manifest']) for key,texture in context['textures'].items()}


def _context(finish_texture_compilation=False,allow_missing=False):
    from opal_layered_settings import ASSET, LOOKS, TEXTURE_PREFIX
    if set(LOOKS) != {'Opal'}:
        raise RuntimeError('Exact single Opal recipe required')
    recipe = LOOKS['Opal']
    if ASSET != '/CkFoundation/CkUsf' or TEXTURE_PREFIX != TEXTURE_ROOT:
        raise RuntimeError('Exact framework/read-only Polish asset roots required')
    if (recipe['name'], recipe['source'], recipe['graph'], recipe['shading'], recipe['blend']) != (NAME, SOURCE_NAME, 8, 0, 0):
        raise RuntimeError('Exact independent translucent layered-opal identity required')
    if recipe['two_sided'] or recipe.get('directional_shading', False) or recipe.get('adaptive_base_glints', False):
        raise RuntimeError('Layered opal must be one-sided nondirectional without native glints')
    names = [key for key, _ in recipe['textures']+recipe['vectors']+recipe['scalars']]
    if len(names) != len({name.casefold() for name in names}) or len(recipe['textures'])!=5 or {key for _,key in recipe['textures']}!=MAPS:
        raise RuntimeError('Unexpected/duplicate layered-opal material parameter')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    report_path = root/'Saved/UsfMaterialGallery/OpalLayeredFire-Preparation.json'
    hashes = {}

    def checked(relative, expected=None):
        path = (root/relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(root) or not path.is_file():
            raise RuntimeError('Missing/outside layered-opal input: '+relative)
        digest = _sha(path)
        if expected is not None and digest != expected:
            raise RuntimeError('Preserve revised layered-opal input: '+relative)
        hashes[path.relative_to(root).as_posix()] = digest
        return path

    manifest_relative = RESOURCE+'/OpalTextures.json'
    manifest_path = checked(manifest_relative)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    if manifest['schema_version']!=1 or set(manifest['maps'])!=MAPS:
        raise RuntimeError('Exact schema1 five-map new original-artwork manifest required')
    checked(manifest['generator_source'],manifest['generator_sha256'])
    folder=manifest_path.parent.relative_to(root).as_posix()
    checked(folder+'/'+manifest['source']['path'],manifest['source']['sha256'])
    if manifest['maps']['OpalColor']['sha256']!=manifest['source']['sha256']:
        raise RuntimeError('New color texture must preserve original artwork bytes')
    if manifest['source'].get('prompt_support'):
        checked(folder+'/'+manifest['source']['prompt_support'],manifest['source'].get('prompt_sha256'))
    loaded={key:unreal.load_asset(TEXTURE_PREFIX+key) for key in MAPS}
    if finish_texture_compilation:
        _finish_textures()
    textures={};candidates={};texture_checks={};dimensions=set()
    for key,info in manifest['maps'].items():
        source_file=checked(folder+'/'+info['path'],info['sha256'])
        _png_contract(source_file,info,key)
        dimensions.add((info['width'],info['height']))
        expected_name='T_OpalLayeredFire_'+key
        if info.get('runtime_name',expected_name)!=expected_name:
            raise RuntimeError('Manifest runtime destination differs: '+key)
        texture=loaded[key];path=TEXTURE_PREFIX+key
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            if not isinstance(texture,unreal.Texture2D) or unreal.EditorAssetLibrary.get_metadata_tag(texture,TEXTURE_OWNER)!=info['sha256'] or unreal.EditorAssetLibrary.get_metadata_tag(texture,OWNER+'.Manifest')!=manifest_relative+':'+_sha(manifest_path):
                raise RuntimeError('Preserve differently owned/revised new texture: '+key)
            _check_texture(texture,key,info,source_file)
        elif texture is not None:
            raise RuntimeError('Preserve unexpected in-memory texture destination: '+key)
        elif not allow_missing:
            raise RuntimeError('New owned texture missing; run explicit prepare before scene: '+key)
        textures[key]=texture
        if texture is not None:
            texture_checks[key]=_texture_report(texture,key,info,manifest_path,manifest_relative)
        candidates[key]=dict(path=path,source=source_file,info=info)
    if len(dimensions)!=1:
        raise RuntimeError('All five new maps must share exactly aligned dimensions')
    # Reuse the approved closed body without import, save, or metadata changes.
    body_manifest_relative = 'Plugins/CkTests/Resources/CkUsf/AmberHeroV1/Manifest.json'
    body_manifest_path = checked(body_manifest_relative)
    body_manifest = json.loads(body_manifest_path.read_text(encoding='utf-8'))
    checked(body_manifest['generator_source'],body_manifest['generator_sha256'])
    body = body_manifest['meshes']['Body']
    body_folder=body_manifest_path.parent.relative_to(root).as_posix()
    checked(body_folder+'/'+body['path'],body['sha256'])
    checked(body_folder+'/'+body['mtl']['path'],body['mtl']['sha256'])
    mesh = unreal.load_asset('/CkTests/CkUsf/Showcase/AmberHero/SM_AmberHero_Body')
    if not isinstance(mesh,unreal.StaticMesh) or unreal.EditorAssetLibrary.get_metadata_tag(mesh,'CkUsf.AmberHeroPreparation.v1')!=body['sha256'] or 'Body' not in [str(value.material_slot_name) for value in mesh.static_materials]:
        raise RuntimeError('Preserve missing/revised approved Body mesh')
    if not body['closed_edge_manifold'] or not body['consistent_edge_winding'] or body['degenerate_triangles']!=0 or body['signed_volume_cm3']<=0:
        raise RuntimeError('Approved closed-body topology contract differs')
    shader_relative = 'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/'+SOURCE_NAME+'.ush'
    shader = checked(shader_relative)
    shader_root = shader.parent.parent
    source = shader.read_text(encoding='utf-8-sig')
    if re.findall(r'^\s*//\s*@ckusf\s+(surface_graph|shading_model)\s+([^\r\n]+)', source, re.MULTILINE) != [('surface_graph', 'NativeTranslucentVertical')]:
        raise RuntimeError('Exact native translucent layered-opal source declaration required')
    signature = re.search(r'FCkUsf_TranslucentVerticalOutput\s+CkUsf_Look_'+SOURCE_NAME+r'\s*\(([^)]*)\)\s*\{', source)
    expected = ['FCkUsf_SurfaceInput In']
    for parameter, _ in recipe['textures']:
        expected += ['Texture2D '+parameter, 'SamplerState '+parameter+'Sampler']
    expected += ['float3 '+key for key, _ in recipe['vectors']]+['float '+key for key, _ in recipe['scalars']]
    if not signature or [re.sub(r'\s+', '', value) for value in signature.group(1).split(',')] != [value.replace(' ', '') for value in expected]:
        raise RuntimeError('Exact ordered layered-opal shader signature required')
    visited = set()

    def dependencies(path):
        if path in visited:
            return
        visited.add(path)
        for include in re.findall(r'^\s*#\s*include\s+"([^"]+)"', path.read_text(encoding='utf-8-sig'), re.MULTILINE):
            if not include.startswith('/CkUsf/'):
                raise RuntimeError('Unexpected layered-opal shader dependency: '+include)
            child = shader_root/include[len('/CkUsf/'):]
            dependencies(checked(child.relative_to(root).as_posix()))
    dependencies(shader)
    pin = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()
    definition_path = ASSET+'/Looks/Optical/DA_'+NAME
    master_path = ASSET+'/GeneratedLooks/M_CkUsf_Look_'+NAME
    prior = json.loads(report_path.read_text(encoding='utf-8')) if report_path.is_file() else {}
    return dict(root=root, recipe=recipe, textures=textures, source_hashes=hashes, recipe_pin=pin,
        definition_path=definition_path, definition_object=definition_path+'.DA_'+NAME,
        master_path=master_path, master_object=master_path+'.M_CkUsf_Look_'+NAME,
        output=report_path, prior=prior,mesh=mesh,texture_checks=texture_checks,candidates=candidates,
        texture_manifest=manifest_relative,texture_manifest_sha256=_sha(manifest_path),source_provenance=manifest['source']['provenance'])


def _matching_claim(context):
    prior = context['prior']
    return (prior.get('owner') == OWNER and prior.get('recipe_pin') == context['recipe_pin']
            and prior.get('definition') == context['definition_object'] and prior.get('source_hashes') == context['source_hashes'])


def _definition(context, definition):
    if not isinstance(definition, unreal.CkUsf_LookDefinition) or unreal.EditorAssetLibrary.get_metadata_tag(definition, OWNER) != context['recipe_pin']:
        raise RuntimeError('Preserve differently owned/revised layered-opal definition')
    _verify_definition(definition, context['definition_path'], ROLE, context['recipe'], context['textures'])
    if definition.get_effective_generated_package_root() != '/CkFoundation/CkUsf/GeneratedLooks':
        raise RuntimeError('Preserve changed layered-opal generated package root')
    for field in ['_AdaptiveBaseGlints', '_SlabFuzz', '_SurfaceSceneColor', '_SceneColorReplacesBackground']:
        if definition.get_editor_property(field):
            raise RuntimeError('Preserve unexpected layered-opal option: '+field)
    if str(definition.get_editor_property('_WpoFunctionName')) not in ['', 'None'] or definition.get_editor_property('_ToonProfile') or definition.get_editor_property('_SubsurfaceProfile'):
        raise RuntimeError('Preserve unexpected layered-opal WPO/profile setting')


def _master(context, master, allow_pending=False):
    if not isinstance(master, unreal.Material) or master.get_path_name() != context['master_object']:
        raise RuntimeError('Preserve missing/changed layered-opal master class/path')
    owner_pin = unreal.EditorAssetLibrary.get_metadata_tag(master, OWNER)
    if owner_pin != context['recipe_pin'] and not (allow_pending and owner_pin == '' and _matching_claim(context)):
        raise RuntimeError('Preserve unclaimed/revised generated layered-opal master')
    if unreal.EditorAssetLibrary.get_metadata_tag(master, 'CkUsf.SourceDefinition.v1') != context['definition_object']:
        raise RuntimeError('Preserve changed layered-opal master source definition')
    front = unreal.MaterialEditingLibrary.get_material_property_input_node(master, unreal.MaterialProperty.MP_FRONT_MATERIAL)
    if not isinstance(front, unreal.MaterialExpressionSubstrateVerticalLayering) or not unreal.EditorAssetLibrary.get_metadata_tag(master, 'CkUsf.NativeSurfaceGraph.v1'):
        raise RuntimeError('Preserve changed native layered-opal topology')
    for kind, values in [('texture', context['recipe']['textures']), ('vector', context['recipe']['vectors']), ('scalar', context['recipe']['scalars'])]:
        names = {str(value) for value in getattr(unreal.MaterialEditingLibrary, 'get_'+kind+'_parameter_names')(master)}
        if names != {key for key, _ in values}:
            raise RuntimeError('Preserve changed layered-opal parameter roster: '+kind)
        for key, expected in values:
            actual = getattr(unreal.MaterialEditingLibrary, 'get_material_default_'+kind+'_parameter_value')(master, key)
            valid = (actual == context['textures'][expected] if kind == 'texture' else
                     all(abs(getattr(actual, component)-value)<1e-5 for component, value in zip('rgba', expected)) if kind == 'vector' else
                     abs(actual-expected)<1e-5)
            if not valid:
                raise RuntimeError('Preserve changed layered-opal default: '+key)


def _stats(master):
    stats = unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem).get_compiled_substrate_stats(master)
    if not stats.valid or stats.compile_errors or stats.closure_count != 2 or stats.has_glint or stats.complex_special:
        raise RuntimeError('Layered opal must retain two retained compiled native closures without Glint/ComplexSpecial')
    return {key: list(getattr(stats, key)) if key == 'compile_errors' else getattr(stats, key)
            for key in ['valid', 'closure_count', 'uint_per_pixel', 'has_glint', 'complex_special', 'material_type', 'bsdf_features', 'compile_errors']}


def _report(context, pending=False, compiled=None):
    return dict(owner=OWNER, recipe_pin=context['recipe_pin'], source_hashes=context['source_hashes'],
        definition=context['definition_object'], master=context['master_object'], material=context['master_object'],
        preparation_pending=pending, ready_for_separate_scene_action=not pending, compiled=compiled,
        mesh=context['mesh'].get_path_name(),textures={key:value.get_path_name() if value else None for key,value in context['textures'].items()},
        reused_read_only_assets=[context['mesh'].get_path_name()],new_owned_textures={key:value.get_path_name() if value else None for key,value in context['textures'].items()},
        texture_checks=context['texture_checks'],texture_manifest=context['texture_manifest'],
        texture_manifest_sha256=context['texture_manifest_sha256'],source_provenance=context['source_provenance'])


def verify_existing():
    """Read-only scene preflight; no generation, save, or compilation."""
    context = _context()
    _definition(context, unreal.load_asset(context['definition_path']))
    master = unreal.load_asset(context['master_path'])
    _master(context, master)
    return master, _report(context, compiled=_stats(master))


def prepare():
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() or unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Prepare layered opal outside PIE')
    if unreal.SystemLibrary.get_console_variable_int_value('r.Substrate') != 1 or unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat') != 1:
        raise RuntimeError('Layered-opal preparation requires enabled Adaptive Substrate')
    context = _context(finish_texture_compilation=True,allow_missing=True)
    definition, master = unreal.load_asset(context['definition_path']), unreal.load_asset(context['master_path'])
    if unreal.EditorAssetLibrary.does_asset_exist(context['definition_path']):
        if any(value is None for value in context['textures'].values()):
            raise RuntimeError('Preserve existing definition with missing owned texture dependencies')
        _definition(context, definition)
    if unreal.EditorAssetLibrary.does_asset_exist(context['master_path']):
        if not definition:
            raise RuntimeError('Preserve existing layered-opal master without its owned definition')
        _master(context, master, allow_pending=True)

    def write(report):
        context['output'].parent.mkdir(parents=True, exist_ok=True)
        context['output'].write_text(json.dumps(report, indent=2)+'\n')
        return report

    def save(asset):
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
            raise RuntimeError('Could not save owned layered-opal asset')

    _prepare_textures(context,save)
    if not definition:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class', unreal.CkUsf_LookDefinition)
        definition = unreal.AssetToolsHelpers.get_asset_tools().create_asset('DA_'+NAME, '/CkFoundation/CkUsf/Looks/Optical', unreal.CkUsf_LookDefinition, factory)
        if not isinstance(definition, unreal.CkUsf_LookDefinition):
            raise RuntimeError('Could not create independent layered-opal definition')
        recipe = context['recipe']
        params = [_param(key, 2, context['textures'][value].get_path_name(), index*10) for index, (key, value) in enumerate(recipe['textures'])]
        params += [_param(key, 1, value, index*10) for index, (key, value) in enumerate(recipe['vectors'])]
        params += [_param(key, 0, value, index*10) for index, (key, value) in enumerate(recipe['scalars'])]
        for field, value in [('_LookName', NAME), ('_UshIncludePath', '/CkUsf/Looks/'+SOURCE_NAME+'.ush'), ('_UshFunctionName', 'CkUsf_Look_'+SOURCE_NAME),
                             ('_Parameters', params), ('_TwoSided', False), ('_DirectionalShading', False), ('_AdaptiveBaseGlints', False)]:
            definition.set_editor_property(field, value)
        for field, value in [('_SurfaceGraph', 8), ('_Domain', 0), ('_ShadingModel', 0), ('_BlendMode', 0)]:
            definition.set_editor_property(field, type(definition.get_editor_property(field)).cast(value))
        unreal.EditorAssetLibrary.set_metadata_tag(definition, OWNER, context['recipe_pin'])
        _definition(context, definition)
        pending = write(_report(context, pending=True))
        save(definition)
        return pending
    if context['prior'].get('preparation_pending') and not _matching_claim(context):
        raise RuntimeError('Pending layered-opal generation requires its exact saved source/recipe claim')
    if not master:
        if _matching_claim(context) and context['prior'].get('preparation_pending'):
            return _report(context, pending=True)
        raise RuntimeError('Missing layered-opal master has no exact pending generation claim')
    errors = unreal.MaterialEditingLibrary.recompile_material(master)
    if errors:
        raise RuntimeError('Layered-opal shader errors: '+str(errors))
    unreal.MaterialEditingLibrary.get_statistics(master)
    compiled = _stats(master)
    unreal.EditorAssetLibrary.set_metadata_tag(master, OWNER, context['recipe_pin'])
    save(master)
    return write(_report(context, compiled=compiled))
