"""Prepare only the independent native translucent middle fire layer.

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

OWNER = 'CkUsf.OpalDepthFirePreparation.v1'
TEXTURE_OWNER = 'CkUsf.OpalPolishPreparation.v1'
NAME = 'OpticalOpalFireLayer'
ROLE = 'FireLayer'
MAPS = {'OpalColor', 'OpalDomains', 'OpalDomainNormal', 'OpalPolishNormal', 'OpalRoughness'}


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _context():
    from opal_depth_settings import ASSET, FIRE_LOOK, TEXTURE_PREFIX
    recipe = FIRE_LOOK
    if ASSET != '/CkFoundation/CkUsf' or TEXTURE_PREFIX != ASSET+'/Textures/Optical/OpalPolish/T_OpalPolish_':
        raise RuntimeError('Exact framework/read-only Polish asset roots required')
    if (recipe['name'], recipe['source'], recipe['graph'], recipe['shading'], recipe['blend']) != (NAME, NAME, 6, 0, 0):
        raise RuntimeError('Exact independent translucent fire-layer identity required')
    if recipe['two_sided'] or recipe.get('directional_shading', False) or recipe.get('adaptive_base_glints', False):
        raise RuntimeError('Middle fire layer must be one-sided nondirectional without native glints')
    names = [key for key, _ in recipe['textures']+recipe['vectors']+recipe['scalars']]
    if len(names) != len({name.casefold() for name in names}) or any(key not in MAPS for _, key in recipe['textures']):
        raise RuntimeError('Unexpected/duplicate fire-layer material parameter')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    report_path = root/'Saved/UsfMaterialGallery/OpalDepthFire-Preparation.json'
    approved_path = root/'Saved/UsfMaterialGallery/OpalDepth-Preparation.json'
    approved = json.loads(approved_path.read_text(encoding='utf-8'))
    if approved.get('owner') != 'CkUsf.OpalDepthPreparation.v1' or not approved.get('ready_for_separate_scene_action'):
        raise RuntimeError('Complete the owned Core/Shell preparation before adding the fire layer')
    hashes = {}

    def checked(relative, expected=None):
        path = (root/relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(root) or not path.is_file():
            raise RuntimeError('Missing/outside fire-layer input: '+relative)
        digest = _sha(path)
        if expected is not None and digest != expected:
            raise RuntimeError('Preserve revised fire-layer input: '+relative)
        hashes[path.relative_to(root).as_posix()] = digest
        return path

    manifest_relative = 'Plugins/CkTests/Resources/CkUsf/OpalPolishV2/OpalTextures.json'
    manifest_path = checked(manifest_relative, approved['texture_manifest_sha256'])
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if set(manifest['maps']) != MAPS or set(approved['texture_checks']) != MAPS:
        raise RuntimeError('Exact five approved Polish maps required')
    checked(manifest['generator_source'], manifest['generator_sha256'])
    folder = manifest_path.parent.relative_to(root).as_posix()
    checked(folder+'/'+manifest['source']['path'], manifest['source']['sha256'])
    textures = {}
    for key, info in manifest['maps'].items():
        source = checked(folder+'/'+info['path'], info['sha256'])
        texture = unreal.load_asset(TEXTURE_PREFIX+key)
        expected_object = TEXTURE_PREFIX+key+'.T_OpalPolish_'+key
        if not isinstance(texture, unreal.Texture2D) or texture.get_path_name() != expected_object:
            raise RuntimeError('Preserve missing/revised approved texture: '+key)
        if unreal.EditorAssetLibrary.get_metadata_tag(texture, TEXTURE_OWNER) != info['sha256'] or unreal.EditorAssetLibrary.get_metadata_tag(texture, TEXTURE_OWNER+'.Manifest') != manifest_relative+':'+_sha(manifest_path):
            raise RuntimeError('Preserve changed approved texture ownership: '+key)
        if (texture.blueprint_get_size_x(), texture.blueprint_get_size_y()) != (2048, 2048):
            raise RuntimeError('Approved texture runtime dimensions are not complete 2048-square: '+key)
        imported = texture.get_editor_property('asset_import_data')
        if not imported or [str(Path(value).resolve()) for value in imported.extract_filenames()] != [str(source)]:
            raise RuntimeError('Preserve changed approved texture import source: '+key)
        for field, expected in approved['texture_checks'][key]['settings'].items():
            if str(texture.get_editor_property(field)) != expected:
                raise RuntimeError('Preserve changed approved texture setting: '+key+'/'+field)
        textures[key] = texture
    shader_relative = 'Plugins/CkFoundation/Source/CkUsf/Shaders/CkUsf/Looks/'+NAME+'.ush'
    shader = checked(shader_relative)
    shader_root = shader.parent.parent
    source = shader.read_text(encoding='utf-8-sig')
    if re.findall(r'^\s*//\s*@ckusf\s+(surface_graph|shading_model)\s+([^\r\n]+)', source, re.MULTILINE) != [('surface_graph', 'NativeTranslucentSlab')]:
        raise RuntimeError('Exact native translucent fire-layer source declaration required')
    signature = re.search(r'FCkUsf_TranslucentSlabOutput\s+CkUsf_Look_'+NAME+r'\s*\(([^)]*)\)\s*\{', source)
    expected = ['FCkUsf_SurfaceInput In']
    for parameter, _ in recipe['textures']:
        expected += ['Texture2D '+parameter, 'SamplerState '+parameter+'Sampler']
    expected += ['float3 '+key for key, _ in recipe['vectors']]+['float '+key for key, _ in recipe['scalars']]
    if not signature or [re.sub(r'\s+', '', value) for value in signature.group(1).split(',')] != [value.replace(' ', '') for value in expected]:
        raise RuntimeError('Exact ordered fire-layer shader signature required')
    visited = set()

    def dependencies(path):
        if path in visited:
            return
        visited.add(path)
        for include in re.findall(r'^\s*#\s*include\s+"([^"]+)"', path.read_text(encoding='utf-8-sig'), re.MULTILINE):
            if not include.startswith('/CkUsf/'):
                raise RuntimeError('Unexpected fire-layer shader dependency: '+include)
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
        output=report_path, prior=prior)


def _matching_claim(context):
    prior = context['prior']
    return (prior.get('owner') == OWNER and prior.get('recipe_pin') == context['recipe_pin']
            and prior.get('definition') == context['definition_object'] and prior.get('source_hashes') == context['source_hashes'])


def _definition(context, definition):
    if not isinstance(definition, unreal.CkUsf_LookDefinition) or unreal.EditorAssetLibrary.get_metadata_tag(definition, OWNER) != context['recipe_pin']:
        raise RuntimeError('Preserve differently owned/revised fire-layer definition')
    _verify_definition(definition, context['definition_path'], ROLE, context['recipe'], context['textures'])
    if definition.get_effective_generated_package_root() != '/CkFoundation/CkUsf/GeneratedLooks':
        raise RuntimeError('Preserve changed fire-layer generated package root')
    for field in ['_AdaptiveBaseGlints', '_SlabFuzz', '_SurfaceSceneColor', '_SceneColorReplacesBackground']:
        if definition.get_editor_property(field):
            raise RuntimeError('Preserve unexpected fire-layer option: '+field)
    if str(definition.get_editor_property('_WpoFunctionName')) not in ['', 'None'] or definition.get_editor_property('_ToonProfile') or definition.get_editor_property('_SubsurfaceProfile'):
        raise RuntimeError('Preserve unexpected fire-layer WPO/profile setting')


def _master(context, master, allow_pending=False):
    if not isinstance(master, unreal.Material) or master.get_path_name() != context['master_object']:
        raise RuntimeError('Preserve missing/changed fire-layer master class/path')
    owner_pin = unreal.EditorAssetLibrary.get_metadata_tag(master, OWNER)
    if owner_pin != context['recipe_pin'] and not (allow_pending and owner_pin == '' and _matching_claim(context)):
        raise RuntimeError('Preserve unclaimed/revised generated fire-layer master')
    if unreal.EditorAssetLibrary.get_metadata_tag(master, 'CkUsf.SourceDefinition.v1') != context['definition_object']:
        raise RuntimeError('Preserve changed fire-layer master source definition')
    front = unreal.MaterialEditingLibrary.get_material_property_input_node(master, unreal.MaterialProperty.MP_FRONT_MATERIAL)
    if not isinstance(front, unreal.MaterialExpressionSubstrateSlabBSDF) or not unreal.EditorAssetLibrary.get_metadata_tag(master, 'CkUsf.NativeSurfaceGraph.v1'):
        raise RuntimeError('Preserve changed native fire-layer topology')
    for kind, values in [('texture', context['recipe']['textures']), ('vector', context['recipe']['vectors']), ('scalar', context['recipe']['scalars'])]:
        names = {str(value) for value in getattr(unreal.MaterialEditingLibrary, 'get_'+kind+'_parameter_names')(master)}
        if names != {key for key, _ in values}:
            raise RuntimeError('Preserve changed fire-layer parameter roster: '+kind)
        for key, expected in values:
            actual = getattr(unreal.MaterialEditingLibrary, 'get_material_default_'+kind+'_parameter_value')(master, key)
            valid = (actual == context['textures'][expected] if kind == 'texture' else
                     all(abs(getattr(actual, component)-value)<1e-5 for component, value in zip('rgba', expected)) if kind == 'vector' else
                     abs(actual-expected)<1e-5)
            if not valid:
                raise RuntimeError('Preserve changed fire-layer default: '+key)


def _stats(master):
    stats = unreal.get_editor_subsystem(unreal.CkUsf_GeneratorSubsystem).get_compiled_substrate_stats(master)
    if not stats.valid or stats.compile_errors or stats.closure_count != 1 or stats.has_glint or stats.complex_special:
        raise RuntimeError('Fire layer must retain one compiled native closure without Glint/ComplexSpecial')
    return {key: list(getattr(stats, key)) if key == 'compile_errors' else getattr(stats, key)
            for key in ['valid', 'closure_count', 'uint_per_pixel', 'has_glint', 'complex_special', 'material_type', 'bsdf_features', 'compile_errors']}


def _report(context, pending=False, compiled=None):
    return dict(owner=OWNER, recipe_pin=context['recipe_pin'], source_hashes=context['source_hashes'],
        definition=context['definition_object'], master=context['master_object'], material=context['master_object'],
        preparation_pending=pending, ready_for_separate_scene_action=not pending, compiled=compiled)


def verify_existing():
    """Read-only scene preflight; no generation, save, or compilation."""
    context = _context()
    _definition(context, unreal.load_asset(context['definition_path']))
    master = unreal.load_asset(context['master_path'])
    _master(context, master)
    return master, _report(context, compiled=_stats(master))


def prepare():
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Prepare fire layer outside PIE')
    if unreal.SystemLibrary.get_console_variable_int_value('r.Substrate') != 1 or unreal.SystemLibrary.get_console_variable_int_value('r.Substrate.ProjectGBufferFormat') != 1:
        raise RuntimeError('Fire-layer preparation requires enabled Adaptive Substrate')
    context = _context()
    definition, master = unreal.load_asset(context['definition_path']), unreal.load_asset(context['master_path'])
    if unreal.EditorAssetLibrary.does_asset_exist(context['definition_path']):
        _definition(context, definition)
    if unreal.EditorAssetLibrary.does_asset_exist(context['master_path']):
        if not definition:
            raise RuntimeError('Preserve existing fire-layer master without its owned definition')
        _master(context, master, allow_pending=True)

    def write(report):
        context['output'].parent.mkdir(parents=True, exist_ok=True)
        context['output'].write_text(json.dumps(report, indent=2)+'\n')
        return report

    def save(asset):
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
            raise RuntimeError('Could not save owned fire-layer asset')

    if not definition:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class', unreal.CkUsf_LookDefinition)
        definition = unreal.AssetToolsHelpers.get_asset_tools().create_asset('DA_'+NAME, '/CkFoundation/CkUsf/Looks/Optical', unreal.CkUsf_LookDefinition, factory)
        if not isinstance(definition, unreal.CkUsf_LookDefinition):
            raise RuntimeError('Could not create independent fire-layer definition')
        recipe = context['recipe']
        params = [_param(key, 2, context['textures'][value].get_path_name(), index*10) for index, (key, value) in enumerate(recipe['textures'])]
        params += [_param(key, 1, value, index*10) for index, (key, value) in enumerate(recipe['vectors'])]
        params += [_param(key, 0, value, index*10) for index, (key, value) in enumerate(recipe['scalars'])]
        for field, value in [('_LookName', NAME), ('_UshIncludePath', '/CkUsf/Looks/'+NAME+'.ush'), ('_UshFunctionName', 'CkUsf_Look_'+NAME),
                             ('_Parameters', params), ('_TwoSided', False), ('_DirectionalShading', False), ('_AdaptiveBaseGlints', False)]:
            definition.set_editor_property(field, value)
        for field, value in [('_SurfaceGraph', 6), ('_Domain', 0), ('_ShadingModel', 0), ('_BlendMode', 0)]:
            definition.set_editor_property(field, type(definition.get_editor_property(field)).cast(value))
        unreal.EditorAssetLibrary.set_metadata_tag(definition, OWNER, context['recipe_pin'])
        _definition(context, definition)
        pending = write(_report(context, pending=True))
        save(definition)
        return pending
    if context['prior'].get('preparation_pending') and not _matching_claim(context):
        raise RuntimeError('Pending fire-layer generation requires its exact saved source/recipe claim')
    if not master:
        if _matching_claim(context) and context['prior'].get('preparation_pending'):
            return _report(context, pending=True)
        raise RuntimeError('Missing fire-layer master has no exact pending generation claim')
    errors = unreal.MaterialEditingLibrary.recompile_material(master)
    if errors:
        raise RuntimeError('Fire-layer shader errors: '+str(errors))
    unreal.MaterialEditingLibrary.get_statistics(master)
    compiled = _stats(master)
    unreal.EditorAssetLibrary.set_metadata_tag(master, OWNER, context['recipe_pin'])
    save(master)
    return write(_report(context, compiled=compiled))
