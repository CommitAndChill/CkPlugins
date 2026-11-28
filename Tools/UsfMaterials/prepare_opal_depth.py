"""Prepare the new clear shell and recessed native-glint core; reused assets stay read-only."""
from pathlib import Path
import hashlib
import json
import re
import struct
import unreal
from prepare_native_bsdf import _param
from prepare_optical_seated import _verify_definition

OWNER = 'CkUsf.OpalDepthPreparation.v1'
TEXTURE_OWNER = 'CkUsf.OpalPolishPreparation.v1'
BODY_OWNER = 'CkUsf.AmberHeroPreparation.v1'
MAPS = {'OpalColor', 'OpalDomains', 'OpalDomainNormal', 'OpalPolishNormal', 'OpalRoughness'}
BODY = '/CkTests/CkUsf/Showcase/AmberHero/SM_AmberHero_Body'
IDENTITIES = {'Core': ('OpticalOpalCore', 'OpticalOpalCore', 4),
              'Shell': ('OpticalOpalShell', 'OpticalOpalShell', 6)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    from opal_depth_settings import ASSET, LOOKS, TEXTURE_PREFIX
    if ASSET != '/CkFoundation/CkUsf' or set(LOOKS) != set(IDENTITIES):
        raise RuntimeError('Exact additive opal-depth Core/Shell roster required')
    if TEXTURE_PREFIX != ASSET+'/Textures/Optical/OpalPolish/T_OpalPolish_':
        raise RuntimeError('Approved read-only Polish texture prefix required')
    for role, recipe in LOOKS.items():
        if (recipe['name'], recipe['source'], recipe['graph']) != IDENTITIES[role]:
            raise RuntimeError('Unexpected opal-depth identity: '+role)
        if recipe['shading'] != 0 or recipe['blend'] != 0 or recipe['two_sided'] or recipe.get('directional_shading', False):
            raise RuntimeError('One-sided nondirectional native Inherit contracts required: '+role)
        if recipe.get('adaptive_base_glints', role == 'Core') != (role == 'Core'):
            raise RuntimeError('Only the Core opts into native base glints')
        keys = [key for _, key in recipe['textures']]
        expected = MAPS if role == 'Core' else {'OpalPolishNormal', 'OpalRoughness'}
        if len(keys) != len(expected) or set(keys) != expected:
            raise RuntimeError('Exact approved texture channels required: '+role)
        names = [key for key, _ in recipe['textures']+recipe['vectors']+recipe['scalars']]
        if len(names) != len(set(name.casefold() for name in names)):
            raise RuntimeError('Duplicate opal-depth material parameter: '+role)
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() or unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Prepare depth assets before scene creation/PIE in the owned editor')
    if any(unreal.SystemLibrary.get_console_variable_int_value(key) != value for key, value in
           [('r.Substrate', 1), ('r.Substrate.ProjectGBufferFormat', 1), ('r.Substrate.Glints', 1)]):
        raise RuntimeError('Enabled Adaptive Substrate with native glints is required')
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

    pair = resources/'OpalPolishV2'
    maps = receipt(pair, 'OpalTextures.json')
    if set(maps['maps']) != MAPS:
        raise RuntimeError('V2 opal manifest map identities differ')
    checked(pair, maps['source']['path'], maps['source']['sha256'])
    if maps['maps']['OpalColor']['sha256'] != maps['source']['sha256']:
        raise RuntimeError('V2 color must preserve original artwork bytes exactly')
    if maps['source'].get('prompt_support'):
        checked(pair, maps['source']['prompt_support'])
    manifest_path = (pair/'OpalTextures.json').relative_to(root).as_posix()
    manifest_pin = source_hashes[manifest_path]
    textures, candidates = {}, {}
    # Loading can return a placeholder while platform data compiles. The engine's
    # native completion command joins those jobs before reading runtime dimensions.
    loaded_textures = {key: unreal.load_asset(TEXTURE_PREFIX+key) for key in maps['maps']}
    unreal.SystemLibrary.execute_console_command(
        unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),
        'Editor.AsyncTextureCompilationFinishAll')

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
        if not isinstance(texture, unreal.Texture2D) or texture.get_path_name() != TEXTURE_PREFIX+key+'.T_OpalPolish_'+key:
            raise RuntimeError('Preserve unexpected new texture class/path: '+key)
        for field, expected in settings_for(key, info).items():
            if texture.get_editor_property(field) != expected:
                raise RuntimeError('Saved opal texture settings differ: '+key+'/'+field)
        expected_size = tuple(1 << (info[axis]-1).bit_length() for axis in ['width', 'height'])
        actual_size = (texture.blueprint_get_size_x(), texture.blueprint_get_size_y())
        if actual_size != expected_size:
            raise RuntimeError('Imported opal runtime dimensions differ: '+key+' actual='+str(actual_size)+' expected='+str(expected_size))
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
            raise RuntimeError('Selected V2 aligned sources must remain original 1254-square pixels: '+key)
        if info.get('runtime_name', 'T_OpalPolish_'+key) != 'T_OpalPolish_'+key:
            raise RuntimeError('Manifest runtime texture name differs: '+key)
        path = TEXTURE_PREFIX+key
        texture = loaded_textures[key]
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            if not isinstance(texture, unreal.Texture2D) or unreal.EditorAssetLibrary.get_metadata_tag(texture, TEXTURE_OWNER) != info['sha256'] or unreal.EditorAssetLibrary.get_metadata_tag(texture, TEXTURE_OWNER+'.Manifest') != manifest_path+':'+manifest_pin:
                raise RuntimeError('Preserve differently owned/revised new opal texture: '+key)
            check_texture(texture, key, info, source_file)
        if texture is None:
            raise RuntimeError('Missing approved Polish texture; no import/reimport allowed: '+key)
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
    visited = set()

    def dependencies(path):
        if path in visited:
            return
        visited.add(path)
        for include in re.findall(r'^\s*#\s*include\s+"([^"]+)"', path.read_text(encoding='utf-8-sig'), re.MULTILINE):
            if not include.startswith('/CkUsf/'):
                raise RuntimeError('Unexpected depth shader dependency: '+include)
            dependencies(checked(shaders, include[len('/CkUsf/'):]))

    for role, recipe in LOOKS.items():
        entry = checked(shaders, 'Looks/'+recipe['source']+'.ush')
        source = entry.read_text(encoding='utf-8-sig')
        graph = 'AdaptiveVertical' if role == 'Core' else 'NativeTranslucentSlab'
        declarations = re.findall(r'^\s*//\s*@ckusf\s+(surface_graph|shading_model)\s+([^\r\n]+)', source, re.MULTILINE)
        if declarations != [('surface_graph', graph)]:
            raise RuntimeError('Exact depth source graph declaration required: '+role)
        output = 'FCkUsf_AdaptiveVerticalOutput' if role == 'Core' else 'FCkUsf_TranslucentSlabOutput'
        signature = re.search(output+r'\s+CkUsf_Look_'+recipe['source']+r'\s*\(([^)]*)\)\s*\{', source)
        expected = ['FCkUsf_SurfaceInput In']
        for parameter, _ in recipe['textures']:
            expected += ['Texture2D '+parameter, 'SamplerState '+parameter+'Sampler']
        expected += ['float3 '+key for key, _ in recipe['vectors']]+['float '+key for key, _ in recipe['scalars']]
        if not signature or [re.sub(r'\s+', '', value) for value in signature.group(1).split(',')] != [value.replace(' ', '') for value in expected]:
            raise RuntimeError('Exact ordered depth shader signature required: '+role)
        dependencies(entry)

    pins = {role: hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest() for role, recipe in LOOKS.items()}
    definition_paths = {role: ASSET+'/Looks/Optical/DA_'+recipe['name'] for role, recipe in LOOKS.items()}
    definition_objects = {role: path+'.DA_'+LOOKS[role]['name'] for role, path in definition_paths.items()}
    master_paths = {role: ASSET+'/GeneratedLooks/M_CkUsf_Look_'+recipe['name'] for role, recipe in LOOKS.items()}
    output_path = root/'Saved/UsfMaterialGallery/OpalDepth-Preparation.json'
    prior = json.loads(output_path.read_text(encoding='utf-8')) if output_path.is_file() else {}
    matching_claim = (prior.get('owner') == OWNER and prior.get('recipe_pins') == pins
                      and prior.get('definitions') == definition_objects and prior.get('source_hashes') == source_hashes)
    definitions = {}
    masters = {}

    def verify_definition(role, definition):
        recipe = LOOKS[role]
        if not isinstance(definition, unreal.CkUsf_LookDefinition) or unreal.EditorAssetLibrary.get_metadata_tag(definition, OWNER) != pins[role]:
            raise RuntimeError('Preserve differently owned/revised depth definition: '+role)
        _verify_definition(definition, definition_paths[role], role, recipe, textures)
        if definition.get_editor_property('_AdaptiveBaseGlints') != (role == 'Core'):
            raise RuntimeError('Preserve changed depth native glints option: '+role)
        if definition.get_effective_generated_package_root() != ASSET+'/GeneratedLooks':
            raise RuntimeError('Preserve changed depth generated root: '+role)
        for field in ['_SlabFuzz', '_SurfaceSceneColor', '_SceneColorReplacesBackground']:
            if definition.get_editor_property(field):
                raise RuntimeError('Preserve unexpected depth option: '+role+'/'+field)
        if str(definition.get_editor_property('_WpoFunctionName')) not in ['', 'None'] or definition.get_editor_property('_ToonProfile') or definition.get_editor_property('_SubsurfaceProfile'):
            raise RuntimeError('Preserve unexpected depth WPO/profile setting: '+role)

    def verify_master(role, master):
        recipe = LOOKS[role]
        actual_pin = unreal.EditorAssetLibrary.get_metadata_tag(master, OWNER) if master else None
        if not isinstance(master, unreal.Material) or master.get_path_name() != master_paths[role]+'.M_CkUsf_Look_'+recipe['name'] or actual_pin not in [pins[role], '']:
            raise RuntimeError('Preserve differently owned/revised depth master: '+role)
        if not definitions[role] or unreal.EditorAssetLibrary.get_metadata_tag(master, 'CkUsf.SourceDefinition.v1') != definition_objects[role]:
            raise RuntimeError('Preserve depth master with changed source definition: '+role)
        if actual_pin == '' and not matching_claim:
            raise RuntimeError('Unclaimed generated depth master lacks exact persisted recipe/source pins: '+role)
        front = unreal.MaterialEditingLibrary.get_material_property_input_node(master, unreal.MaterialProperty.MP_FRONT_MATERIAL)
        node_type = unreal.MaterialExpressionSubstrateVerticalLayering if role == 'Core' else unreal.MaterialExpressionSubstrateSlabBSDF
        if not isinstance(front, node_type) or not unreal.EditorAssetLibrary.get_metadata_tag(master, 'CkUsf.NativeSurfaceGraph.v1'):
            raise RuntimeError('Preserve changed native depth topology: '+role)
        for kind, parameters in [('scalar', recipe['scalars']), ('vector', recipe['vectors']), ('texture', recipe['textures'])]:
            names = {str(value) for value in getattr(unreal.MaterialEditingLibrary, 'get_'+kind+'_parameter_names')(master)}
            if names != {key for key, _ in parameters}:
                raise RuntimeError('Generated depth master parameter roster differs: '+role+'/'+kind)
            for parameter, value in parameters:
                actual = getattr(unreal.MaterialEditingLibrary, 'get_material_default_'+kind+'_parameter_value')(master, parameter)
                if kind == 'texture':
                    valid = actual == textures[value]
                elif kind == 'vector':
                    valid = all(abs(getattr(actual, component)-expected)<1e-5 for component, expected in zip('rgba', value))
                else:
                    valid = abs(actual-value)<1e-5
                if not valid:
                    raise RuntimeError('Generated depth default differs: '+role+'/'+parameter)

    # Preflight both destinations and every reused input before creating either definition.
    for role in LOOKS:
        definitions[role] = unreal.load_asset(definition_paths[role])
        masters[role] = unreal.load_asset(master_paths[role])
        if unreal.EditorAssetLibrary.does_asset_exist(definition_paths[role]):
            verify_definition(role, definitions[role])
        if unreal.EditorAssetLibrary.does_asset_exist(master_paths[role]):
            verify_master(role, masters[role])
    texture_checks = {}
    for key, candidate in candidates.items():
        texture, info = textures[key], candidate['info']
        check_texture(texture, key, info, candidate['source'])
        texture_checks[key] = dict(asset=texture.get_path_name(), source_sha256=info['sha256'],
            source_size=[info['width'], info['height']], runtime_size=[texture.blueprint_get_size_x(), texture.blueprint_get_size_y()],
            runtime_size_scope='Completed platform-data dimensions, not currently resident mip dimensions',
            runtime_expected_size=[2048, 2048], runtime_expected_mip_count=12, actual_mip_count_verified=False,
            settings={field: str(value) for field, value in settings_for(key, info).items()}, manifest_sha256=manifest_pin)

    def save(asset):
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
            raise RuntimeError('Could not save owned depth asset: '+asset.get_path_name())

    def write_report(report):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2)+'\n')
        return report

    tools = unreal.AssetToolsHelpers.get_asset_tools()
    created = []
    for role, recipe in LOOKS.items():
        if definitions[role]:
            continue
        factory = unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class', unreal.CkUsf_LookDefinition)
        definition = tools.create_asset('DA_'+recipe['name'], ASSET+'/Looks/Optical', unreal.CkUsf_LookDefinition, factory)
        if not isinstance(definition, unreal.CkUsf_LookDefinition):
            raise RuntimeError('Could not create owned depth definition: '+role)
        params = [_param(parameter, 2, textures[key].get_path_name(), index*10) for index, (parameter, key) in enumerate(recipe['textures'])]
        params += [_param(key, 1, value, index*10) for index, (key, value) in enumerate(recipe['vectors'])]
        params += [_param(key, 0, value, index*10) for index, (key, value) in enumerate(recipe['scalars'])]
        for field, value in [('_LookName', recipe['name']), ('_UshIncludePath', '/CkUsf/Looks/'+recipe['source']+'.ush'),
                             ('_UshFunctionName', 'CkUsf_Look_'+recipe['source']), ('_Parameters', params),
                             ('_TwoSided', False), ('_DirectionalShading', False), ('_AdaptiveBaseGlints', role == 'Core')]:
            definition.set_editor_property(field, value)
        for field, value in [('_SurfaceGraph', recipe['graph']), ('_Domain', 0), ('_ShadingModel', 0), ('_BlendMode', 0)]:
            definition.set_editor_property(field, type(definition.get_editor_property(field)).cast(value))
        unreal.EditorAssetLibrary.set_metadata_tag(definition, OWNER, pins[role])
        definitions[role] = definition
        verify_definition(role, definition)
        created.append(role)
    if created:
        pending = dict(owner=OWNER, recipe_pins=pins, definitions=definition_objects, source_hashes=source_hashes,
                       preparation_pending=True, ready_for_separate_scene_action=False)
        # Persist the complete two-role claim before either save queues next-tick generation.
        write_report(pending)
        for role in created:
            save(definitions[role])
        return pending

    generator = unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem)
    if prior.get('preparation_pending') and not matching_claim:
        raise RuntimeError('Pending depth generation requires exact persisted recipe/source ownership evidence')
    if any(not masters[role] for role in LOOKS):
        if matching_claim and prior.get('preparation_pending'):
            return dict(prior, preparation_pending=True, ready_for_separate_scene_action=False)
        raise RuntimeError('Missing depth master has no exact pending generation claim; preserve session and inspect generator log')

    compiled = {}
    # Check both completed masters before stamping/saving either one.
    for role, master in masters.items():
        verify_master(role, master)
        errors = unreal.MaterialEditingLibrary.recompile_material(master)
        if errors:
            raise RuntimeError('Depth shader errors: '+role+'/'+str(errors))
        unreal.MaterialEditingLibrary.get_statistics(master)
        stats = generator.get_compiled_substrate_stats(master)
        glints = role == 'Core'
        if not stats.valid or stats.compile_errors or stats.closure_count != (2 if glints else 1) or stats.has_glint != glints or stats.complex_special != glints:
            raise RuntimeError('Depth compiled native closure/feature contract differs: '+role)
        compiled[role] = dict(valid=stats.valid, closure_count=stats.closure_count, uint_per_pixel=stats.uint_per_pixel,
            has_glint=stats.has_glint, complex_special=stats.complex_special, material_type=stats.material_type,
            bsdf_features=stats.bsdf_features, compile_errors=list(stats.compile_errors))
    for role, master in masters.items():
        unreal.EditorAssetLibrary.set_metadata_tag(master, OWNER, pins[role])
        save(master)
    ownership_metadata = {asset.get_path_name(): unreal.EditorAssetLibrary.get_metadata_tag(asset, OWNER)
                          for asset in list(definitions.values())+list(masters.values())}
    return write_report(dict(owner=OWNER, recipe_pins=pins, definitions=definition_objects, source_hashes=source_hashes,
        looks={role: master.get_path_name() for role, master in masters.items()},
        materials={role: master.get_path_name() for role, master in masters.items()},
        meshes={role: mesh.get_path_name() for role in LOOKS}, textures={key: texture.get_path_name() for key, texture in textures.items()},
        source_variant='OpalPolishV2_read_only', texture_manifest=manifest_path, texture_manifest_sha256=manifest_pin,
        source_provenance=maps['source']['provenance'], texture_checks=texture_checks, compiled=compiled,
        ownership_metadata=ownership_metadata, reused_read_only_assets=[mesh.get_path_name()]+[texture.get_path_name() for texture in textures.values()],
        preserved_prior_definitions_and_masters=True, preparation_pending=False, ready_for_separate_scene_action=True))

