"""Prepare only OpticalOpalFire and its five new owned texture maps.

Run explicitly in a fresh owned Adaptive editor before scene creation. Existing
destinations must have this exact recipe and owner; no migration or reimport.
"""
from pathlib import Path
import hashlib
import json
import re
import struct
import unreal
from prepare_native_bsdf import _param
from prepare_optical_seated import _verify_definition

OWNER = 'CkUsf.OpalFirePreparation.v1'
TEXTURE_OWNER = OWNER
BODY_OWNER = 'CkUsf.AmberHeroPreparation.v1'
NAME = 'OpticalOpalFire'
SOURCE_NAME = 'OpticalOpalFire'
MAPS = {'OpalColor', 'OpalDomains', 'OpalDomainNormal', 'OpalPolishNormal', 'OpalRoughness'}
BODY = '/CkTests/CkUsf/Showcase/AmberHero/SM_AmberHero_Body'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    from opal_fire_settings import ASSET, LOOKS, TEXTURE_PREFIX
    if ASSET != '/CkFoundation/CkUsf' or set(LOOKS) != {'Opal'}:
        raise RuntimeError('Exact single-opal roster and framework asset root required')
    recipe = LOOKS['Opal']
    if (recipe['name'], recipe['source'], recipe['graph'], recipe['shading'], recipe['blend']) != (NAME, SOURCE_NAME, 4, 0, 0):
        raise RuntimeError('Exact OpticalOpalFire AdaptiveVertical/Inherit recipe required')
    if TEXTURE_PREFIX != ASSET+'/Textures/Optical/OpalFire/T_OpalFire_':
        raise RuntimeError('Exact new opal-fire texture destination required')
    if recipe['two_sided'] or recipe.get('directional_shading', False):
        raise RuntimeError('Opal fire uses one-sided nondirectional native slabs')
    if len(recipe['textures']) != 5 or {key for _, key in recipe['textures']} != MAPS:
        raise RuntimeError('The exact five OpalFireV1 opal map channels are required')
    parameter_names = [key for key, _ in recipe['textures']+recipe['vectors']+recipe['scalars']]
    if len(parameter_names) != len(set(parameter_names)):
        raise RuntimeError('Duplicate opal parameter name')
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() or unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Prepare opal fire before scene creation/PIE in the owned fresh editor')
    if unreal.SystemLibrary.get_console_variable_int_value('r.Substrate') != 1 or unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat') != 1:
        raise RuntimeError('Opal fire requires enabled Substrate and process-only Adaptive GBuffer')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    resources = root/'Plugins/CkTests/Resources/CkUsf'
    source_hashes = {}

    def checked(base, relative, expected=None):
        path = (base/relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(base.resolve()) or not path.is_file():
            raise RuntimeError('Missing/outside opal source: '+str(relative))
        digest = sha(path)
        if expected is not None and digest != expected:
            raise RuntimeError('Opal source hash differs: '+str(relative))
        source_hashes[path.relative_to(root).as_posix()] = digest
        return path

    def receipt(base, filename):
        path = checked(base, filename)
        record = json.loads(path.read_text(encoding='utf-8-sig'))
        if record['schema_version'] != 1:
            raise RuntimeError('Unexpected reused source schema: '+filename)
        checked(root, record['generator_source'], record['generator_sha256'])
        return record

    pair = resources/'OpalFireV1'
    maps = receipt(pair, 'OpalTextures.json')
    if set(maps['maps']) != MAPS:
        raise RuntimeError('OpalFireV1 opal manifest map identities differ')
    checked(pair, maps['source']['path'], maps['source']['sha256'])
    if maps['maps']['OpalColor']['sha256'] != maps['source']['sha256']:
        raise RuntimeError('OpalFireV1 color must preserve original artwork bytes exactly')
    if maps['source'].get('prompt_support'):
        checked(pair, maps['source']['prompt_support'])
    manifest_path = (pair/'OpalTextures.json').relative_to(root).as_posix()
    manifest_pin = source_hashes[manifest_path]
    textures, candidates = {}, {}

    def settings_for(key, info):
        normal = key.endswith('Normal')
        return dict(compression_settings=(unreal.TextureCompressionSettings.TC_NORMALMAP if normal else
                    unreal.TextureCompressionSettings.TC_DEFAULT if info['srgb'] else unreal.TextureCompressionSettings.TC_MASKS),
                    lod_group=(unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP if normal else
                               unreal.TextureGroup.TEXTUREGROUP_WORLD if info['srgb'] else unreal.TextureGroup.TEXTUREGROUP_WORLD_SPECULAR),
                    srgb=info['srgb'], address_x=unreal.TextureAddress.TA_CLAMP, address_y=unreal.TextureAddress.TA_CLAMP,
                    mip_gen_settings=unreal.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE, flip_green_channel=False,
                    power_of_two_mode=unreal.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO)

    def check_texture(texture, key, info, source_file):
        if not isinstance(texture, unreal.Texture2D) or texture.get_path_name() != TEXTURE_PREFIX+key+'.T_OpalFire_'+key:
            raise RuntimeError('Preserve unexpected new texture class/path: '+key)
        for field, expected in settings_for(key, info).items():
            if texture.get_editor_property(field) != expected:
                raise RuntimeError('Saved opal texture settings differ: '+key+'/'+field)
        expected_size = tuple(1 << (info[axis]-1).bit_length() for axis in ['width', 'height'])
        if (texture.blueprint_get_size_x(), texture.blueprint_get_size_y()) != expected_size:
            raise RuntimeError('Imported opal runtime dimensions differ: '+key)
        import_data = texture.get_editor_property('asset_import_data')
        if not import_data or [str(Path(value).resolve()) for value in import_data.extract_filenames()] != [str(source_file)]:
            raise RuntimeError('New opal texture import source differs: '+key)

    for key, info in maps['maps'].items():
        source_file = checked(pair, info['path'], info['sha256'])
        data = source_file.read_bytes()
        if len(data) < 25 or data[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', data[16:24]) != (info['width'], info['height']) or data[24] != info['bit_depth']:
            raise RuntimeError('New opal PNG dimensions/bit depth differ: '+key)
        if info['srgb'] != (key == 'OpalColor'):
            raise RuntimeError('New opal source color space differs: '+key)
        if (info['width'], info['height']) != (1254, 1254):
            raise RuntimeError('Selected OpalFireV1 aligned sources must remain original 1254-square pixels: '+key)
        if info.get('runtime_name', 'T_OpalFire_'+key) != 'T_OpalFire_'+key:
            raise RuntimeError('Manifest runtime texture name differs: '+key)
        path = TEXTURE_PREFIX+key
        texture = unreal.load_asset(path)
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            if not isinstance(texture, unreal.Texture2D) or unreal.EditorAssetLibrary.get_metadata_tag(texture, TEXTURE_OWNER) != info['sha256'] or unreal.EditorAssetLibrary.get_metadata_tag(texture, OWNER+'.Manifest') != manifest_path+':'+manifest_pin:
                raise RuntimeError('Preserve differently owned/revised new opal texture: '+key)
            check_texture(texture, key, info, source_file)
        textures[key] = texture
        candidates[key] = dict(source=source_file, path=path, info=info)
    amber = resources/'AmberHeroV1'
    manifest = receipt(amber, 'Manifest.json')
    body = manifest['meshes']['Body']
    checked(amber, body['path'], body['sha256'])
    checked(amber, body['mtl']['path'], body['mtl']['sha256'])
    if body['slot'] != 'Body' or not body['closed_edge_manifold'] or not body['consistent_edge_winding'] or body['degenerate_triangles'] != 0 or body['signed_volume_cm3'] <= 0:
        raise RuntimeError('Reused body topology contract differs')
    mesh = unreal.load_asset(BODY)
    if not isinstance(mesh, unreal.StaticMesh) or unreal.EditorAssetLibrary.get_metadata_tag(mesh, BODY_OWNER) != body['sha256'] or 'Body' not in [str(item.material_slot_name) for item in mesh.static_materials]:
        raise RuntimeError('Preserve missing/revised AmberHero body; no reimport allowed')
    shaders = root/'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf'
    entry = checked(shaders, 'Looks/'+SOURCE_NAME+'.ush')
    source = entry.read_text(encoding='utf-8-sig')
    declarations = re.findall(r'^\s*//\s*@ckusf\s+(surface_graph|shading_model)\s+([^\r\n]+)', source, re.MULTILINE)
    if declarations != [('surface_graph', 'AdaptiveVertical')]:
        raise RuntimeError('Exact new AdaptiveVertical opal entrypoint required')
    signature = re.search(r'FCkUsf_AdaptiveVerticalOutput\s+CkUsf_Look_'+SOURCE_NAME+r'\s*\(([^)]*)\)\s*\{', source)
    expected = ['FCkUsf_SurfaceInput In']
    for parameter, _ in recipe['textures']:
        expected += ['Texture2D '+parameter, 'SamplerState '+parameter+'Sampler']
    expected += ['float3 '+key for key, _ in recipe['vectors']]+['float '+key for key, _ in recipe['scalars']]
    if not signature or [re.sub(r'\s+', '', value) for value in signature.group(1).split(',')] != [value.replace(' ', '') for value in expected]:
        raise RuntimeError('Exact ordered opal texture/sampler/vector/scalar signature required')
    visited = set()

    def dependencies(path):
        if path in visited:
            return
        visited.add(path)
        for include in re.findall(r'^\s*#\s*include\s+"([^"]+)"', path.read_text(encoding='utf-8-sig'), re.MULTILINE):
            if not include.startswith('/CkUsf/'):
                raise RuntimeError('Unexpected opal shader dependency: '+include)
            dependencies(checked(shaders, include[len('/CkUsf/'):]))
    dependencies(entry)
    pin = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()
    definition_path = ASSET+'/Looks/Optical/DA_'+NAME
    definition_object = definition_path+'.DA_'+NAME
    master_path = ASSET+'/GeneratedLooks/M_CkUsf_Look_'+NAME
    definition = unreal.load_asset(definition_path)
    master = unreal.load_asset(master_path)
    if unreal.EditorAssetLibrary.does_asset_exist(definition_path):
        if not isinstance(definition, unreal.CkUsf_LookDefinition) or unreal.EditorAssetLibrary.get_metadata_tag(definition, OWNER) != pin:
            raise RuntimeError('Preserve differently owned/revised opal fire definition; no migration')
        if any(texture is None for texture in textures.values()):
            raise RuntimeError('Preserve existing opal definition with missing owned texture dependencies')
        _verify_definition(definition, definition_path, 'Opal', recipe, textures)
        if definition.get_effective_generated_package_root() != ASSET+'/GeneratedLooks':
            raise RuntimeError('Preserve changed generated-material root')
        for field in ['_SlabFuzz', '_SurfaceSceneColor', '_SceneColorReplacesBackground']:
            if definition.get_editor_property(field):
                raise RuntimeError('Preserve unexpected existing opal option: '+field)
        if str(definition.get_editor_property('_WpoFunctionName')) not in ['', 'None'] or definition.get_editor_property('_ToonProfile') or definition.get_editor_property('_SubsurfaceProfile'):
            raise RuntimeError('Preserve unexpected existing opal WPO/profile setting')
    if unreal.EditorAssetLibrary.does_asset_exist(master_path):
        if not isinstance(master, unreal.Material) or not definition or unreal.EditorAssetLibrary.get_metadata_tag(master, OWNER) != pin or unreal.EditorAssetLibrary.get_metadata_tag(master, 'CkUsf.SourceDefinition.v1') != definition_object:
            raise RuntimeError('Preserve differently owned/revised opal fire master; no migration')
        front = unreal.MaterialEditingLibrary.get_material_property_input_node(master, unreal.MaterialProperty.MP_FRONT_MATERIAL)
        if not isinstance(front, unreal.MaterialExpressionSubstrateVerticalLayering) or not unreal.EditorAssetLibrary.get_metadata_tag(master, 'CkUsf.NativeSurfaceGraph.v1'):
            raise RuntimeError('Preserve changed native opal fire topology')
    # Every source and all seven new destinations passed preflight before any import/save.
    tools = unreal.AssetToolsHelpers.get_asset_tools()

    def save(asset):
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
            raise RuntimeError('Could not save owned opal fire asset: '+asset.get_path_name())

    texture_checks = {}
    for key, candidate in candidates.items():
        texture = textures[key]
        info = candidate['info']
        if texture is None:
            task = unreal.AssetImportTask()
            task.filename = str(candidate['source'])
            task.destination_path = TEXTURE_PREFIX.rsplit('/', 1)[0]
            task.destination_name = 'T_OpalFire_'+key
            task.automated, task.replace_existing, task.save = True, False, False
            tools.import_asset_tasks([task])
            objects = task.get_objects()
            if len(objects) != 1 or not isinstance(objects[0], unreal.Texture2D) or objects[0].get_path_name() != candidate['path']+'.T_OpalFire_'+key:
                raise RuntimeError('Unexpected new opal texture import: '+key)
            texture = objects[0]
            # Compression can reset normal/sRGB settings. Apply compression, then LOD, then sRGB.
            for field, value in settings_for(key, info).items():
                texture.set_editor_property(field, value)
            unreal.EditorAssetLibrary.set_metadata_tag(texture, TEXTURE_OWNER, info['sha256'])
            unreal.EditorAssetLibrary.set_metadata_tag(texture, OWNER+'.Manifest', manifest_path+':'+manifest_pin)
            save(texture)
            texture = unreal.load_asset(candidate['path'])
        check_texture(texture, key, info, candidate['source'])
        textures[key] = texture
        texture_checks[key] = dict(asset=texture.get_path_name(), source_sha256=info['sha256'], source_size=[info['width'], info['height']],
            runtime_size=[texture.blueprint_get_size_x(), texture.blueprint_get_size_y()],
            runtime_size_scope='Completed platform-data dimensions, not currently resident mip dimensions',
            runtime_resampling='Explicit StretchToPowerOfTwo; all aligned maps preserve the full UV domain',
            runtime_expected_size=[2048, 2048], runtime_expected_mip_count=12, actual_mip_count_verified=False,
            settings={field: str(value) for field, value in settings_for(key, info).items()}, manifest_sha256=manifest_pin)

    if not definition:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class', unreal.CkUsf_LookDefinition)
        definition = tools.create_asset('DA_'+NAME, ASSET+'/Looks/Optical', unreal.CkUsf_LookDefinition, factory)
        if not isinstance(definition, unreal.CkUsf_LookDefinition):
            raise RuntimeError('Could not create owned opal fire definition')
        params = [_param(parameter, 2, textures[key].get_path_name(), index*10) for index, (parameter, key) in enumerate(recipe['textures'])]
        params += [_param(key, 1, value, index*10) for index, (key, value) in enumerate(recipe['vectors'])]
        params += [_param(key, 0, value, index*10) for index, (key, value) in enumerate(recipe['scalars'])]
        for field, value in [('_LookName', NAME), ('_UshIncludePath', '/CkUsf/Looks/'+SOURCE_NAME+'.ush'), ('_UshFunctionName', 'CkUsf_Look_'+SOURCE_NAME), ('_Parameters', params), ('_TwoSided', False), ('_DirectionalShading', False)]:
            definition.set_editor_property(field, value)
        for field, value in [('_SurfaceGraph', 4), ('_Domain', 0), ('_ShadingModel', 0), ('_BlendMode', 0)]:
            definition.set_editor_property(field, type(definition.get_editor_property(field)).cast(value))
        unreal.EditorAssetLibrary.set_metadata_tag(definition, OWNER, pin)
        save(definition)
    generator = unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem)
    if not master:
        generator.generate_look_material_for(definition)
        master = unreal.load_asset(master_path)
    if not isinstance(master, unreal.Material) or unreal.EditorAssetLibrary.get_metadata_tag(master, 'CkUsf.SourceDefinition.v1') != definition_object:
        raise RuntimeError('Owned opal fire generation failed')
    errors = unreal.MaterialEditingLibrary.recompile_material(master)
    if errors:
        raise RuntimeError('Opal fire shader errors: '+str(errors))
    unreal.MaterialEditingLibrary.get_statistics(master)
    stats = generator.get_compiled_substrate_stats(master)
    if not stats.valid or stats.compile_errors or stats.closure_count != 2:
        raise RuntimeError('Opal fire must compile as two retained native closures')
    unreal.EditorAssetLibrary.set_metadata_tag(master, OWNER, pin)
    save(master)
    report = dict(owner=OWNER, looks={'Opal': master.get_path_name()}, materials={'Opal': master.get_path_name()},
        definitions={'Opal': definition.get_path_name()}, meshes={'Opal': mesh.get_path_name()},
        textures={key: texture.get_path_name() for key, texture in textures.items()}, recipe_pins={'Opal': pin},
        source_variant='OpalFireV1', texture_manifest=manifest_path, texture_manifest_sha256=manifest_pin,
        source_hashes=source_hashes, reused_read_only_assets=[mesh.get_path_name()], texture_checks=texture_checks,
        compiled=dict(valid=stats.valid, closure_count=stats.closure_count, uint_per_pixel=stats.uint_per_pixel, compile_errors=list(stats.compile_errors)),
        source_provenance=maps['source']['provenance'], preserved_prior_definitions_and_masters=True, ready_for_separate_scene_action=True)
    output = root/'Saved/UsfMaterialGallery/OpalFire-Preparation.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    return report
